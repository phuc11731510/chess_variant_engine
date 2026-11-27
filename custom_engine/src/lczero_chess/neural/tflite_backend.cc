#include "neural/tflite_backend.h"

#include <dlfcn.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
#include <sstream>
#include <vector>

#include "chess/encoder.h"
#include "chess/nn_layout.h"
#include "neural/network_output.h"
#include "neural/shared_params.h"
#include "utils/exception.h"

namespace lczero {

namespace {

constexpr size_t kPlanes = kInputPlanes;                       // 204
constexpr size_t kSquares = kBoardSize * kBoardSize;           // 100
constexpr size_t kUnit = kPlanes * kSquares;                   // floats per position
constexpr size_t kPolicy = kPolicySize;

// --- The part of the TFLite C API (tensorflow/lite/core/c/c_api.h) and of the GPU delegate (delegates/gpu/delegate.h)
// this backend uses: opaque handles + plain functions, stable across LiteRT 1.x. Resolved with dlsym.
using TfLiteStatus = int;  // kTfLiteOk = 0
struct TfLiteModel;
struct TfLiteInterpreterOptions;
struct TfLiteInterpreter;
struct TfLiteTensor;
struct TfLiteDelegate;

// TfLiteGpuDelegateOptionsV2 (delegate_options.h): the first fields have been the same since V2; the tail is padding so
// whatever the library's TfLiteGpuDelegateOptionsV2Default() writes past them (newer / debug fields) has room.
struct GpuOptions {
  int32_t is_precision_loss_allowed;
  int32_t inference_preference;   // 1 = SUSTAINED_SPEED
  int32_t inference_priority1;    // 2 = MIN_LATENCY
  int32_t inference_priority2;
  int32_t inference_priority3;
  int64_t experimental_flags;
  int32_t max_delegated_partitions;
  const char* serialization_dir;
  const char* model_token;
  unsigned char tail[256];
};

struct Api {
  TfLiteModel* (*ModelCreateFromFile)(const char*);
  void (*ModelDelete)(TfLiteModel*);
  TfLiteInterpreterOptions* (*OptionsCreate)();
  void (*OptionsDelete)(TfLiteInterpreterOptions*);
  void (*OptionsSetNumThreads)(TfLiteInterpreterOptions*, int32_t);
  void (*OptionsAddDelegate)(TfLiteInterpreterOptions*, TfLiteDelegate*);
  TfLiteInterpreter* (*InterpreterCreate)(const TfLiteModel*, const TfLiteInterpreterOptions*);
  void (*InterpreterDelete)(TfLiteInterpreter*);
  TfLiteStatus (*AllocateTensors)(TfLiteInterpreter*);
  TfLiteStatus (*Invoke)(TfLiteInterpreter*);
  int32_t (*GetInputCount)(const TfLiteInterpreter*);
  TfLiteTensor* (*GetInput)(const TfLiteInterpreter*, int32_t);
  int32_t (*GetOutputCount)(const TfLiteInterpreter*);
  const TfLiteTensor* (*GetOutput)(const TfLiteInterpreter*, int32_t);
  int32_t (*NumDims)(const TfLiteTensor*);
  int32_t (*Dim)(const TfLiteTensor*, int32_t);
  size_t (*ByteSize)(const TfLiteTensor*);
  const char* (*Name)(const TfLiteTensor*);
  TfLiteStatus (*CopyFrom)(TfLiteTensor*, const void*, size_t);
  TfLiteStatus (*CopyTo)(const TfLiteTensor*, void*, size_t);
  GpuOptions (*GpuOptionsDefault)();
  TfLiteDelegate* (*GpuCreate)(const GpuOptions*);
  void (*GpuDelete)(TfLiteDelegate*);
};

template <typename F>
void Sym(void* lib, const char* name, F* out) {
  *out = reinterpret_cast<F>(dlsym(lib, name));
  if (!*out) throw Exception(std::string("GPU backend: ") + name + " not found in the LiteRT library");
}

// Opened once per process (the libraries stay loaded).
const Api& LoadApi() {
  static Api api{};
  static std::string error;
  static std::once_flag once;
  std::call_once(once, [] {
    try {
      // RTLD_GLOBAL: the GPU delegate library resolves TFLite symbols against the core one.
      void* core = dlopen("libtensorflowlite_jni.so", RTLD_NOW | RTLD_GLOBAL);
      if (!core) throw Exception(std::string("GPU backend: libtensorflowlite_jni.so not found (") + dlerror() + ")");
      void* gpu = dlopen("libtensorflowlite_gpu_jni.so", RTLD_NOW | RTLD_GLOBAL);
      if (!gpu) throw Exception(std::string("GPU backend: libtensorflowlite_gpu_jni.so not found (") + dlerror() + ")");
      Sym(core, "TfLiteModelCreateFromFile", &api.ModelCreateFromFile);
      Sym(core, "TfLiteModelDelete", &api.ModelDelete);
      Sym(core, "TfLiteInterpreterOptionsCreate", &api.OptionsCreate);
      Sym(core, "TfLiteInterpreterOptionsDelete", &api.OptionsDelete);
      Sym(core, "TfLiteInterpreterOptionsSetNumThreads", &api.OptionsSetNumThreads);
      Sym(core, "TfLiteInterpreterOptionsAddDelegate", &api.OptionsAddDelegate);
      Sym(core, "TfLiteInterpreterCreate", &api.InterpreterCreate);
      Sym(core, "TfLiteInterpreterDelete", &api.InterpreterDelete);
      Sym(core, "TfLiteInterpreterAllocateTensors", &api.AllocateTensors);
      Sym(core, "TfLiteInterpreterInvoke", &api.Invoke);
      Sym(core, "TfLiteInterpreterGetInputTensorCount", &api.GetInputCount);
      Sym(core, "TfLiteInterpreterGetInputTensor", &api.GetInput);
      Sym(core, "TfLiteInterpreterGetOutputTensorCount", &api.GetOutputCount);
      Sym(core, "TfLiteInterpreterGetOutputTensor", &api.GetOutput);
      Sym(core, "TfLiteTensorNumDims", &api.NumDims);
      Sym(core, "TfLiteTensorDim", &api.Dim);
      Sym(core, "TfLiteTensorByteSize", &api.ByteSize);
      Sym(core, "TfLiteTensorName", &api.Name);
      Sym(core, "TfLiteTensorCopyFromBuffer", &api.CopyFrom);
      Sym(core, "TfLiteTensorCopyToBuffer", &api.CopyTo);
      Sym(gpu, "TfLiteGpuDelegateOptionsV2Default", &api.GpuOptionsDefault);
      Sym(gpu, "TfLiteGpuDelegateV2Create", &api.GpuCreate);
      Sym(gpu, "TfLiteGpuDelegateV2Delete", &api.GpuDelete);
    } catch (const std::exception& e) {
      error = e.what();
    }
  });
  if (!error.empty()) throw Exception(error);
  return api;
}

std::vector<std::string> Split(const std::string& s, char c) {
  std::vector<std::string> out;
  std::istringstream in(s);
  for (std::string t; std::getline(in, t, c);) out.push_back(t);
  return out;
}

class TfliteComputation : public BackendComputation {
 public:
  explicit TfliteComputation(TfliteBackend* be)
      : be_(be), slots_((MaxBatchSize + be->batch() - 1) / be->batch() * be->batch()),
        input_(new float[slots_ * kUnit]), policy_(new float[slots_ * kPolicy]), value_(new float[slots_ * 3]),
        mlh_(new float[slots_]), results_(MaxBatchSize), moves_(MaxBatchSize) {}

  size_t UsedBatchSize() const override { return enqueued_.load(std::memory_order_acquire); }

  AddInputResult AddInput(const EvalPosition& pos, EvalResultPtr result) override {
    const size_t slot = enqueued_.fetch_add(1, std::memory_order_acq_rel);
    if (slot >= MaxBatchSize) {
      enqueued_.fetch_sub(1, std::memory_order_acq_rel);
      throw Exception("GPU backend: maximum batch size exceeded");
    }
    results_[slot] = result;
    const size_t n = std::min(pos.legal_moves.size(), size_t{384});
    moves_[slot].resize(n);
    for (size_t i = 0; i < n; ++i) moves_[slot][i] = pos.legal_moves[i];
    alignas(64) InputPlanes planes;
    int transform = 0;
    EncodePositionForNN(*pos.history, kMoveHistory, FillEmptyHistory::ALWAYS, &planes, &transform);
    UnpackInputPlanes(planes, input_.get() + slot * kUnit, kBoardSize, kBoardSize);
    return ENQUEUED_FOR_EVAL;
  }

  void ComputeBlocking() override {
    const size_t n = enqueued_.load(std::memory_order_acquire);
    if (n == 0) return;
    const size_t b = be_->batch();
    for (size_t off = 0; off < n; off += b) {
      const size_t real = std::min(b, n - off);
      if (real < b) std::memset(input_.get() + (off + real) * kUnit, 0, (b - real) * kUnit * sizeof(float));
      be_->Run(input_.get() + off * kUnit, policy_.get() + off * kPolicy, value_.get() + off * 3, mlh_.get() + off);
    }
    for (size_t i = 0; i < n; ++i) {
      const float* raw = policy_.get() + i * kPolicy;
      const size_t legal = moves_[i].size();
      alignas(64) float logits[384];
      for (size_t j = 0; j < legal; ++j) {
        const uint16_t idx = MoveToNNIndex(moves_[i][j], 0);
        logits[j] = idx < kPolicy ? raw[idx] : -std::numeric_limits<float>::infinity();
      }
      FillEvalResult(results_[i], value_.get() + i * 3, mlh_[i], logits, legal, be_->softmax_temp(), "GPU backend");
    }
    enqueued_.store(0, std::memory_order_release);
  }

 private:
  TfliteBackend* be_;
  const size_t slots_;
  std::unique_ptr<float[]> input_, policy_, value_, mlh_;
  std::vector<EvalResultPtr> results_;
  std::vector<StaticVector<Move, 384>> moves_;
  std::atomic<size_t> enqueued_{0};
};

}  // namespace

struct TfliteBackend::Impl {
  const Api* api = nullptr;
  TfLiteModel* model = nullptr;
  TfLiteInterpreterOptions* options = nullptr;
  TfLiteDelegate* gpu = nullptr;
  TfLiteInterpreter* interp = nullptr;
  TfLiteTensor* input = nullptr;
  const TfLiteTensor* out_policy = nullptr;
  const TfLiteTensor* out_value = nullptr;
  const TfLiteTensor* out_mlh = nullptr;
  std::vector<float> nhwc;

  void Free() {
    if (!api) return;
    if (interp) api->InterpreterDelete(interp);
    if (options) api->OptionsDelete(options);
    if (gpu) api->GpuDelete(gpu);
    if (model) api->ModelDelete(model);
    interp = nullptr; options = nullptr; gpu = nullptr; model = nullptr;
  }
};

TfliteBackend::TfliteBackend() : impl_(std::make_unique<Impl>()) {
  worker_ = std::thread([this] { WorkerLoop(); });
}

TfliteBackend::~TfliteBackend() {
  try {
    OnWorker([this] { impl_->Free(); });
  } catch (...) {
  }
  {
    std::lock_guard<std::mutex> lk(mu_);
    stop_ = true;
  }
  cv_.notify_all();
  worker_.join();
}

void TfliteBackend::WorkerLoop() {
  std::unique_lock<std::mutex> lk(mu_);
  for (;;) {
    cv_.wait(lk, [this] { return stop_ || !job_done_; });
    if (!job_done_) {
      auto f = std::move(job_);
      lk.unlock();
      std::exception_ptr err;
      try {
        f();
      } catch (...) {
        err = std::current_exception();
      }
      lk.lock();
      job_error_ = err;
      job_done_ = true;
      cv_.notify_all();
      continue;
    }
    if (stop_) return;
  }
}

void TfliteBackend::OnWorker(const std::function<void()>& f) {
  std::lock_guard<std::mutex> one(call_mu_);
  std::unique_lock<std::mutex> lk(mu_);
  cv_.wait(lk, [this] { return job_done_; });
  job_ = f;
  job_done_ = false;
  job_error_ = nullptr;
  cv_.notify_all();
  cv_.wait(lk, [this] { return job_done_; });
  if (job_error_) std::rethrow_exception(job_error_);
}

BackendAttributes TfliteBackend::GetAttributes() const {
  return BackendAttributes{.has_mlh = true, .has_wdl = true, .runs_on_cpu = false, .suggested_num_search_threads = 1,
                           .recommended_batch_size = static_cast<int>(batch_),
                           .maximum_batch_size = static_cast<int>(MaxBatchSize)};
}

std::unique_ptr<BackendComputation> TfliteBackend::CreateComputation() {
  if (batch_ == 0) throw Exception("GPU backend: no network loaded");
  return std::make_unique<TfliteComputation>(this);
}

bool TfliteBackend::IsSameConfiguration(const OptionsDict& opts) const {
  return opts.Get<std::string>(SharedBackendParams::kWeightsId) == weights_path_ &&
         opts.GetOrDefault<std::string>(SharedBackendParams::kBackendOptionsId, "") == backend_opts_;
}

void TfliteBackend::UpdateConfiguration(const OptionsDict& opts) {
  weights_path_ = opts.Get<std::string>(SharedBackendParams::kWeightsId);
  backend_opts_ = opts.GetOrDefault<std::string>(SharedBackendParams::kBackendOptionsId, "");
  softmax_temp_ = opts.GetOrDefault<float>(SharedBackendParams::kPolicySoftmaxTemp, 1.0f);
  bool fp32 = false;
  for (const auto& kv : Split(backend_opts_, ',')) {
    const auto p = Split(kv, '=');
    if (p.size() != 2) continue;
    if (p[0] == "threads") cpu_threads_ = std::max(1, std::atoi(p[1].c_str()));
    if (p[0] == "gpu.fp32") fp32 = p[1] == "1" || p[1] == "true";
  }
  OnWorker([this, fp32] {
    Impl& m = *impl_;
    m.Free();
    m.api = &LoadApi();
    const Api& a = *m.api;
    m.model = a.ModelCreateFromFile(weights_path_.c_str());
    if (!m.model) throw Exception("GPU backend: cannot read " + weights_path_);
    GpuOptions go = a.GpuOptionsDefault();
    go.is_precision_loss_allowed = fp32 ? 0 : 1;   // FP16 arithmetic (4x the FP32 speed on a Mali-G57)
    go.inference_preference = 1;                    // SUSTAINED_SPEED: many invokes of the same graph
    go.inference_priority1 = fp32 ? 1 : 2;          // MAX_PRECISION / MIN_LATENCY
    m.gpu = a.GpuCreate(&go);
    if (!m.gpu) throw Exception("GPU backend: the GPU delegate could not be created (no OpenCL / OpenGL ES 3.1?)");
    m.options = a.OptionsCreate();
    a.OptionsSetNumThreads(m.options, cpu_threads_);
    a.OptionsAddDelegate(m.options, m.gpu);
    m.interp = a.InterpreterCreate(m.model, m.options);
    if (!m.interp) throw Exception("GPU backend: the interpreter could not be built (the graph does not run on this GPU?)");
    if (a.AllocateTensors(m.interp) != 0) throw Exception("GPU backend: AllocateTensors failed");
    if (a.GetInputCount(m.interp) != 1) throw Exception("GPU backend: the network must have one input");
    m.input = a.GetInput(m.interp, 0);
    if (a.NumDims(m.input) != 4 || a.Dim(m.input, 1) != kBoardSize || a.Dim(m.input, 2) != kBoardSize ||
        a.Dim(m.input, 3) != static_cast<int32_t>(kPlanes))
      throw Exception("GPU backend: input must be NHWC [batch,10,10,204] (python/khung_gpu.py)");
    batch_ = static_cast<size_t>(a.Dim(m.input, 0));
    if (batch_ == 0 || batch_ > MaxBatchSize) throw Exception("GPU backend: bad batch size in the network");
    m.out_policy = m.out_value = m.out_mlh = nullptr;
    for (int32_t i = 0; i < a.GetOutputCount(m.interp); ++i) {
      const TfLiteTensor* t = a.GetOutput(m.interp, i);
      const std::string name = a.Name(t);
      if (name == "policy") m.out_policy = t;
      else if (name == "value") m.out_value = t;
      else if (name == "mlh") m.out_mlh = t;
    }
    if (!m.out_policy || !m.out_value || !m.out_mlh) throw Exception("GPU backend: outputs policy / value / mlh not found");
    if (a.ByteSize(m.out_policy) != batch_ * kPolicy * 4 || a.ByteSize(m.out_value) != batch_ * 12 ||
        a.ByteSize(m.out_mlh) != batch_ * 4)
      throw Exception("GPU backend: output sizes do not match the batch");
    m.nhwc.assign(batch_ * kUnit, 0.0f);
  });
  std::cout << "[GPU Backend] " << weights_path_ << ": TFLite GPU delegate, batch " << batch_
            << (fp32 ? ", FP32" : ", FP16") << std::endl;
}

void TfliteBackend::Run(const float* nchw, float* policy, float* value, float* mlh) {
  OnWorker([&] {
    Impl& m = *impl_;
    const Api& a = *m.api;
    // NCHW [b,204,100] -> NHWC [b,100,204]
    for (size_t b = 0; b < batch_; ++b) {
      const float* src = nchw + b * kUnit;
      float* dst = m.nhwc.data() + b * kUnit;
      for (size_t c = 0; c < kPlanes; ++c)
        for (size_t s = 0; s < kSquares; ++s) dst[s * kPlanes + c] = src[c * kSquares + s];
    }
    if (a.CopyFrom(m.input, m.nhwc.data(), m.nhwc.size() * sizeof(float)) != 0) throw Exception("GPU backend: input copy failed");
    if (a.Invoke(m.interp) != 0) throw Exception("GPU backend: Invoke failed");
    if (a.CopyTo(m.out_policy, policy, batch_ * kPolicy * 4) != 0 || a.CopyTo(m.out_value, value, batch_ * 12) != 0 ||
        a.CopyTo(m.out_mlh, mlh, batch_ * 4) != 0)
      throw Exception("GPU backend: output copy failed");
  });
}

}  // namespace lczero
