#include "neural/fz/fz_net.h"

#include <cublasLt.h>
#include <cuda_fp16.h>
#include <cuda_runtime.h>
#include <dlfcn.h>

#include <algorithm>
#include <condition_variable>
#include <cstdio>
#include <iostream>
#include <map>
#include <mutex>
#include <sstream>
#include <tuple>

#include "neural/fz/fz_kernels.cuh"
#include "neural/fz/fzw_format.h"
#include "utils/exception.h"

namespace lczero::fz {

namespace {

[[noreturn]] void Fail(const std::string& what, const char* file, int line) {
  throw Exception("fzcuda: " + what + " (" + file + ":" + std::to_string(line) + ")");
}
#define FZ_CUDA(call)                                                                            \
  do {                                                                                           \
    const cudaError_t fz_e = (call);                                                             \
    if (fz_e != cudaSuccess) Fail(std::string(#call) + ": " + cudaGetErrorString(fz_e), __FILE__, __LINE__); \
  } while (0)
#define FZ_LT(call)                                                                              \
  do {                                                                                           \
    const cublasStatus_t fz_s = (call);                                                          \
    if (fz_s != CUBLAS_STATUS_SUCCESS) Fail(std::string(#call) + ": cuBLASLt status " + std::to_string(int(fz_s)), __FILE__, __LINE__); \
  } while (0)

// ---------------------------------------------------------------------------------------------------------------------
// cuBLASLt, loaded at run time. The binary has no link-time dependency on any CUDA library but the (static) runtime: a machine
// without libcublasLt.so.12 still runs every other mode (ONNX Runtime) and fails here with a message instead of at start-up.
// ---------------------------------------------------------------------------------------------------------------------

struct LtApi {
  void* lib = nullptr;
  decltype(&cublasLtCreate) Create = nullptr;
  decltype(&cublasLtDestroy) Destroy = nullptr;
  decltype(&cublasLtGetVersion) GetVersion = nullptr;
  decltype(&cublasLtMatmulDescCreate) MatmulDescCreate = nullptr;
  decltype(&cublasLtMatmulDescDestroy) MatmulDescDestroy = nullptr;
  decltype(&cublasLtMatmulDescSetAttribute) MatmulDescSetAttribute = nullptr;
  decltype(&cublasLtMatrixLayoutCreate) MatrixLayoutCreate = nullptr;
  decltype(&cublasLtMatrixLayoutDestroy) MatrixLayoutDestroy = nullptr;
  decltype(&cublasLtMatmulPreferenceCreate) PreferenceCreate = nullptr;
  decltype(&cublasLtMatmulPreferenceDestroy) PreferenceDestroy = nullptr;
  decltype(&cublasLtMatmulPreferenceSetAttribute) PreferenceSetAttribute = nullptr;
  decltype(&cublasLtMatmulAlgoGetHeuristic) AlgoGetHeuristic = nullptr;
  decltype(&cublasLtMatmul) Matmul = nullptr;

  static const LtApi& Get() {
    static const LtApi api = Load();
    return api;
  }

 private:
  template <typename F>
  static void Sym(void* lib, const char* name, F* out) {
    *out = reinterpret_cast<F>(dlsym(lib, name));
    if (*out == nullptr) throw Exception(std::string("fzcuda: libcublasLt has no symbol ") + name);
  }

  static LtApi Load() {
    LtApi a;
    // CUDA 12 only: the enum values and structures of the header this was built with are those of the 12.x ABI.
    for (const char* name : {"libcublasLt.so.12", "libcublasLt.so"}) {
      a.lib = dlopen(name, RTLD_NOW | RTLD_LOCAL);
      if (a.lib) break;
    }
    if (!a.lib)
      throw Exception(
          "fzcuda: cannot load libcublasLt.so.12 (the cuBLAS of CUDA 12: on Colab it is in the pip package nvidia-cublas-cu12, "
          "which run.sh puts on LD_LIBRARY_PATH). Use --provider cuda (ONNX Runtime) on this machine.");
    Sym(a.lib, "cublasLtCreate", &a.Create);
    Sym(a.lib, "cublasLtDestroy", &a.Destroy);
    Sym(a.lib, "cublasLtGetVersion", &a.GetVersion);
    Sym(a.lib, "cublasLtMatmulDescCreate", &a.MatmulDescCreate);
    Sym(a.lib, "cublasLtMatmulDescDestroy", &a.MatmulDescDestroy);
    Sym(a.lib, "cublasLtMatmulDescSetAttribute", &a.MatmulDescSetAttribute);
    Sym(a.lib, "cublasLtMatrixLayoutCreate", &a.MatrixLayoutCreate);
    Sym(a.lib, "cublasLtMatrixLayoutDestroy", &a.MatrixLayoutDestroy);
    Sym(a.lib, "cublasLtMatmulPreferenceCreate", &a.PreferenceCreate);
    Sym(a.lib, "cublasLtMatmulPreferenceDestroy", &a.PreferenceDestroy);
    Sym(a.lib, "cublasLtMatmulPreferenceSetAttribute", &a.PreferenceSetAttribute);
    Sym(a.lib, "cublasLtMatmulAlgoGetHeuristic", &a.AlgoGetHeuristic);
    Sym(a.lib, "cublasLtMatmul", &a.Matmul);
    return a;
  }
};

constexpr size_t kWorkspaceBytes = 32u << 20;  // cuBLASLt scratch per context

enum class Epilogue { kNone, kBias, kGeluBias };

// Y[M, N] = X[M, K] * W[N, K]^T (+ bias) (+ GELU), everything row-major, X and W FP16, Y FP16 or FP32.
struct GemmShape {
  int n = 0, k = 0;
  bool out_f32 = false;
  Epilogue epi = Epilogue::kNone;
  bool bias_f32 = false;
  std::tuple<int, int, bool, int, bool> Key() const { return {n, k, out_f32, static_cast<int>(epi), bias_f32}; }
  std::string Name(int m) const {
    return std::to_string(m) + "x" + std::to_string(k) + " * " + std::to_string(n) + "x" + std::to_string(k) + "^T" +
           (out_f32 ? " ->f32" : "") + (epi == Epilogue::kGeluBias ? " +bias+gelu" : epi == Epilogue::kBias ? " +bias" : "");
  }
};

// Everything one batch in flight needs on the GPU.
struct Context {
  cudaStream_t stream = nullptr;
  cublasLtHandle_t lt = nullptr;
  void* mem = nullptr;  // one allocation, carved into the buffers below
  PlaneGpu* planes = nullptr;
  uint16_t* move_index = nullptr;
  uint16_t* move_count = nullptr;
  __half *x0 = nullptr, *x = nullptr, *ln = nullptr, *y = nullptr, *qkv = nullptr, *att = nullptr, *ff = nullptr;
  __half *vtok = nullptr, *mtok = nullptr;
  float *head = nullptr, *logits = nullptr, *fc1v = nullptr, *fc1m = nullptr, *wdlm = nullptr;
  void* workspace = nullptr;
};

struct StageStorage {
  Stage stage{};
  void* block = nullptr;
};

// Watches a forward pass: Mark() is called after each stage, Tap() at the points whose values --fzcuda-taps compares with the CPU
// model. Both are called while the stage's launches are only queued, so an observer enqueues its own work on the stream.
struct Observer {
  virtual ~Observer() = default;
  virtual void Mark(const char* name) = 0;
  virtual void Tap(const char* name, const void* device, int rows, int cols, bool half) = 0;
};

// Times the stages: an event after each.
struct StageClock : Observer {
  cudaStream_t stream;
  std::vector<std::pair<std::string, cudaEvent_t>> marks;
  cudaEvent_t start = nullptr;
  explicit StageClock(cudaStream_t s) : stream(s) {
    FZ_CUDA(cudaEventCreate(&start));
    FZ_CUDA(cudaEventRecord(start, stream));
  }
  ~StageClock() override {
    cudaEventDestroy(start);
    for (auto& m : marks) cudaEventDestroy(m.second);
  }
  void Mark(const char* name) override {
    cudaEvent_t e;
    FZ_CUDA(cudaEventCreate(&e));
    FZ_CUDA(cudaEventRecord(e, stream));
    marks.emplace_back(name, e);
  }
  void Tap(const char*, const void*, int, int, bool) override {}
};

// Copies the tapped activations to the host, in stream order (so each holds the value at that point of the pass).
struct TapSink : Observer {
  cudaStream_t stream;
  struct Item {
    std::string name;
    int rows, cols;
    bool half;
    std::vector<uint8_t> raw;
  };
  std::vector<Item> items;
  explicit TapSink(cudaStream_t s) : stream(s) { items.reserve(32); }  // no reallocation: the copies target these vectors
  void Mark(const char*) override {}
  void Tap(const char* name, const void* device, int rows, int cols, bool half) override {
    items.push_back({name, rows, cols, half, std::vector<uint8_t>(size_t(rows) * cols * (half ? 2 : 4))});
    FZ_CUDA(cudaMemcpyAsync(items.back().raw.data(), device, items.back().raw.size(), cudaMemcpyDeviceToHost, stream));
  }
};

}  // namespace

// ---------------------------------------------------------------------------------------------------------------------
// Net::Impl
// ---------------------------------------------------------------------------------------------------------------------

struct Net::Impl {
  class Gemm;

  NetOptions options;
  const LtApi* lt = nullptr;
  cudaDeviceProp prop{};
  int d = 0, layers = 0, heads = 0, ffn = 0, head_cols = 0;
  uint8_t* blob = nullptr;  // the weights file image on the GPU
  size_t blob_bytes = 0;
  int lt_version = 0;

  struct LayerWeights {
    const float *ln1_g, *ln1_b, *relbias, *proj_b, *ln2_g, *ln2_b, *ff2_b;
  };
  std::vector<LayerWeights> lw;
  const float *posb = nullptr, *final_g = nullptr, *final_b = nullptr;
  const float *v2_w = nullptr, *v2_b = nullptr, *m2_w = nullptr, *m2_b = nullptr;

  std::vector<std::unique_ptr<Gemm>> qkv, proj, ff1, ff2;
  std::unique_ptr<Gemm> embed, head, fc1v, fc1m;

  std::vector<std::unique_ptr<Context>> contexts;
  std::vector<Context*> free_contexts;
  std::mutex pool_mu;
  std::condition_variable pool_cv;

  std::vector<std::unique_ptr<StageStorage>> stages;
  std::vector<Stage*> free_stages;
  std::mutex stage_mu;

  std::map<std::tuple<int, int, bool, int, bool, int>, cublasLtMatmulAlgo_t> algo_cache;
  std::mutex algo_mu;

  ~Impl();
  void Init(const std::string& path);
  void AllocContext(Context* c);
  Context* Acquire();
  void Release(Context* c);
  void Forward(Context& c, int batch, Observer* obs);
  cublasLtMatmulAlgo_t ChooseAlgo(Context& c, const GemmShape& shape, int m, const void* bias, cublasLtMatmulDesc_t desc,
                                  cublasLtMatrixLayout_t a, cublasLtMatrixLayout_t b, cublasLtMatrixLayout_t cd,
                                  const void* w, const void* x, void* y);
};

// One weight matrix and its product, with the cuBLASLt descriptors and algorithm for each batch size seen so far.
class Net::Impl::Gemm {
 public:
  Gemm(Impl* owner, const GemmShape& shape, const void* w, const void* bias) : owner_(owner), shape_(shape), w_(w), bias_(bias) {}
  ~Gemm() {
    const LtApi& lt = *owner_->lt;
    for (auto& [m, p] : plans_) {
      lt.MatmulDescDestroy(p.desc);
      lt.MatrixLayoutDestroy(p.a);
      lt.MatrixLayoutDestroy(p.b);
      lt.MatrixLayoutDestroy(p.c);
    }
  }

  void Run(Context& c, int m, const void* x, void* y) {
    const Plan& p = PlanFor(c, m, x, y);
    const float alpha = 1.0f, beta = 0.0f;
    FZ_LT(owner_->lt->Matmul(c.lt, p.desc, &alpha, w_, p.a, x, p.b, &beta, y, p.c, y, p.c, &p.algo, c.workspace, kWorkspaceBytes,
                             c.stream));
  }

 private:
  struct Plan {
    cublasLtMatmulDesc_t desc = nullptr;
    cublasLtMatrixLayout_t a = nullptr, b = nullptr, c = nullptr;
    cublasLtMatmulAlgo_t algo{};
  };

  const Plan& PlanFor(Context& c, int m, const void* x, void* y) {
    std::lock_guard<std::mutex> lock(mu_);
    auto it = plans_.find(m);
    if (it != plans_.end()) return it->second;
    const LtApi& lt = *owner_->lt;
    Plan p;
    FZ_LT(lt.MatmulDescCreate(&p.desc, CUBLAS_COMPUTE_32F, CUDA_R_32F));
    // cuBLAS is column-major. W is [N, K] row-major = a [K x N] column-major matrix used transposed; X [M, K] row-major =
    // [K x M] column-major; Y [M, N] row-major = [N x M] column-major. So Y = op(A) B with A = W (transposed), B = X.
    const cublasOperation_t trans = CUBLAS_OP_T;
    FZ_LT(lt.MatmulDescSetAttribute(p.desc, CUBLASLT_MATMUL_DESC_TRANSA, &trans, sizeof(trans)));
    if (shape_.epi != Epilogue::kNone) {
      const cublasLtEpilogue_t epi = shape_.epi == Epilogue::kGeluBias ? CUBLASLT_EPILOGUE_GELU_BIAS : CUBLASLT_EPILOGUE_BIAS;
      FZ_LT(lt.MatmulDescSetAttribute(p.desc, CUBLASLT_MATMUL_DESC_EPILOGUE, &epi, sizeof(epi)));
      FZ_LT(lt.MatmulDescSetAttribute(p.desc, CUBLASLT_MATMUL_DESC_BIAS_POINTER, &bias_, sizeof(bias_)));
      const cudaDataType_t bt = shape_.bias_f32 ? CUDA_R_32F : CUDA_R_16F;
      FZ_LT(lt.MatmulDescSetAttribute(p.desc, CUBLASLT_MATMUL_DESC_BIAS_DATA_TYPE, &bt, sizeof(bt)));
    }
    FZ_LT(lt.MatrixLayoutCreate(&p.a, CUDA_R_16F, shape_.k, shape_.n, shape_.k));
    FZ_LT(lt.MatrixLayoutCreate(&p.b, CUDA_R_16F, shape_.k, m, shape_.k));
    FZ_LT(lt.MatrixLayoutCreate(&p.c, shape_.out_f32 ? CUDA_R_32F : CUDA_R_16F, shape_.n, m, shape_.n));
    p.algo = owner_->ChooseAlgo(c, shape_, m, bias_, p.desc, p.a, p.b, p.c, w_, x, y);
    return plans_.emplace(m, p).first->second;
  }

  Impl* owner_;
  GemmShape shape_;
  const void* w_;
  const void* bias_;
  std::mutex mu_;
  std::map<int, Plan> plans_;
};

cublasLtMatmulAlgo_t Net::Impl::ChooseAlgo(Context& c, const GemmShape& shape, int m, const void* bias, cublasLtMatmulDesc_t desc,
                                           cublasLtMatrixLayout_t a, cublasLtMatrixLayout_t b, cublasLtMatrixLayout_t cd,
                                           const void* w, const void* x, void* y) {
  const auto key = std::tuple_cat(shape.Key(), std::make_tuple(m));
  std::lock_guard<std::mutex> lock(algo_mu);
  auto hit = algo_cache.find(key);
  if (hit != algo_cache.end()) return hit->second;

  cublasLtMatmulPreference_t pref = nullptr;
  FZ_LT(lt->PreferenceCreate(&pref));
  const size_t ws = kWorkspaceBytes;
  const uint32_t align = 16;
  FZ_LT(lt->PreferenceSetAttribute(pref, CUBLASLT_MATMUL_PREF_MAX_WORKSPACE_BYTES, &ws, sizeof(ws)));
  for (auto attr : {CUBLASLT_MATMUL_PREF_MIN_ALIGNMENT_A_BYTES, CUBLASLT_MATMUL_PREF_MIN_ALIGNMENT_B_BYTES,
                    CUBLASLT_MATMUL_PREF_MIN_ALIGNMENT_C_BYTES, CUBLASLT_MATMUL_PREF_MIN_ALIGNMENT_D_BYTES})
    FZ_LT(lt->PreferenceSetAttribute(pref, attr, &align, sizeof(align)));

  const bool tune = options.autotune && m == kMaxBatch * kTokens;
  constexpr int kCandidates = 8;
  cublasLtMatmulHeuristicResult_t res[kCandidates];
  int returned = 0;
  const cublasStatus_t st = lt->AlgoGetHeuristic(c.lt, desc, a, b, cd, cd, pref, tune ? kCandidates : 1, res, &returned);
  lt->PreferenceDestroy(pref);
  if (st != CUBLAS_STATUS_SUCCESS || returned == 0)
    throw Exception("fzcuda: cuBLASLt has no algorithm for the product " + shape.Name(m) + " (status " +
                    std::to_string(int(st)) + ")");

  cublasLtMatmulAlgo_t best = res[0].algo;
  double best_ms = -1.0;
  if (tune && returned > 1) {
    cudaEvent_t e0, e1;
    FZ_CUDA(cudaEventCreate(&e0));
    FZ_CUDA(cudaEventCreate(&e1));
    const float alpha = 1.0f, beta = 0.0f;
    for (int i = 0; i < returned; ++i) {
      auto run = [&] {
        return lt->Matmul(c.lt, desc, &alpha, w, a, x, b, &beta, y, cd, y, cd, &res[i].algo, c.workspace, kWorkspaceBytes, c.stream);
      };
      if (run() != CUBLAS_STATUS_SUCCESS) continue;  // an algorithm the heuristic offers but that does not run here
      FZ_CUDA(cudaEventRecord(e0, c.stream));
      constexpr int kReps = 5;
      for (int r = 0; r < kReps; ++r) run();
      FZ_CUDA(cudaEventRecord(e1, c.stream));
      FZ_CUDA(cudaEventSynchronize(e1));
      float ms = 0;
      FZ_CUDA(cudaEventElapsedTime(&ms, e0, e1));
      ms /= kReps;
      if (best_ms < 0 || ms < best_ms) {
        best_ms = ms;
        best = res[i].algo;
      }
    }
    cudaEventDestroy(e0);
    cudaEventDestroy(e1);
    if (options.verbose && best_ms >= 0)
      std::cout << "[fzcuda] " << shape.Name(m) << ": " << best_ms << " ms (best of " << returned << " algorithms)" << std::endl;
  }
  algo_cache.emplace(key, best);
  return best;
}

void Net::Impl::AllocContext(Context* c) {
  const size_t M = size_t{kMaxBatch} * kTokens, B = kMaxBatch;
  const size_t D = d, F = size_t(ffn) * d;
  // Each buffer starts on a 256-byte boundary.
  size_t total = 0;
  auto take = [&total](size_t bytes) {
    const size_t off = total;
    total += (bytes + 255) / 256 * 256;
    return off;
  };
  const size_t o_planes = take(B * kPlanes * sizeof(PlaneGpu)), o_midx = take(B * kMaxLegal * 2), o_mcnt = take(B * 2);
  const size_t o_x0 = take(M * kPlanesPadded * 2), o_x = take(M * D * 2), o_ln = take(M * D * 2), o_y = take(M * D * 2);
  const size_t o_qkv = take(M * 3 * D * 2), o_att = take(M * D * 2), o_ff = take(M * F * 2);
  const size_t o_head = take(M * head_cols * 4), o_logits = take(B * kMaxLegal * 4);
  const size_t o_vtok = take(B * kTokens * kValueTokens * 2), o_mtok = take(B * kTokens * kMlhTokens * 2);
  const size_t o_fc1v = take(B * kHidden * 4), o_fc1m = take(B * kHidden * 4), o_wdlm = take(B * 4 * 4);
  const size_t o_ws = take(kWorkspaceBytes);
  FZ_CUDA(cudaMalloc(&c->mem, total));
  FZ_CUDA(cudaMemset(c->mem, 0, total));  // no NaN garbage: a product on never-written memory is still a finite number
  auto at = [c](size_t off) { return static_cast<uint8_t*>(c->mem) + off; };
  c->planes = reinterpret_cast<PlaneGpu*>(at(o_planes));
  c->move_index = reinterpret_cast<uint16_t*>(at(o_midx));
  c->move_count = reinterpret_cast<uint16_t*>(at(o_mcnt));
  c->x0 = reinterpret_cast<__half*>(at(o_x0));
  c->x = reinterpret_cast<__half*>(at(o_x));
  c->ln = reinterpret_cast<__half*>(at(o_ln));
  c->y = reinterpret_cast<__half*>(at(o_y));
  c->qkv = reinterpret_cast<__half*>(at(o_qkv));
  c->att = reinterpret_cast<__half*>(at(o_att));
  c->ff = reinterpret_cast<__half*>(at(o_ff));
  c->head = reinterpret_cast<float*>(at(o_head));
  c->logits = reinterpret_cast<float*>(at(o_logits));
  c->vtok = reinterpret_cast<__half*>(at(o_vtok));
  c->mtok = reinterpret_cast<__half*>(at(o_mtok));
  c->fc1v = reinterpret_cast<float*>(at(o_fc1v));
  c->fc1m = reinterpret_cast<float*>(at(o_fc1m));
  c->wdlm = reinterpret_cast<float*>(at(o_wdlm));
  c->workspace = at(o_ws);
  FZ_CUDA(cudaStreamCreateWithFlags(&c->stream, cudaStreamNonBlocking));
  FZ_LT(lt->Create(&c->lt));
}

void Net::Impl::Init(const std::string& path) {
  int devices = 0;
  if (cudaGetDeviceCount(&devices) != cudaSuccess || devices == 0)
    throw Exception("fzcuda: no CUDA GPU found (cudaGetDeviceCount failed or returned 0)");
  FZ_CUDA(cudaSetDevice(0));
  cudaSetDeviceFlags(cudaDeviceScheduleBlockingSync);  // a thread waiting for the GPU sleeps instead of spinning on a vCPU
  FZ_CUDA(cudaGetDeviceProperties(&prop, 0));
  if (prop.major * 10 + prop.minor < 75)
    throw Exception(std::string("fzcuda: the GPU ") + prop.name + " is older than compute capability 7.5 (tensor-core mma m16n8k8)");
  lt = &LtApi::Get();
  lt_version = static_cast<int>(lt->GetVersion());

  const auto file = FzwFile::Open(path);
  const FzwHeader& h = file->header();
  d = h.d_model;
  layers = h.layers;
  heads = h.heads;
  ffn = h.ffn_mult;
  head_cols = h.head_cols;
  if (h.planes != kPlanes || h.planes_padded != kPlanesPadded || h.squares != kTokens || h.move_types != kMoveTypes ||
      h.value_tokens != kValueTokens || h.mlh_tokens != kMlhTokens || h.hidden != kHidden || head_cols != 160)
    throw Exception("fzcuda: the weights file was made for another network layout than this engine's");
  if (d % 64 != 0 || d > 512 || static_cast<int>(heads) * kHeadDim != d || layers < 1 || ffn < 1)
    throw Exception("fzcuda: unsupported network size (d_model " + std::to_string(d) + ", " + std::to_string(heads) +
                    " heads): the runner needs d_model a multiple of 64, at most 512, with 32 per head");

  blob_bytes = file->size();
  FZ_CUDA(cudaMalloc(&blob, blob_bytes));
  FZ_CUDA(cudaMemcpy(blob, file->data(), blob_bytes, cudaMemcpyHostToDevice));
  auto dev = [&](const void* host) { return blob + (static_cast<const uint8_t*>(host) - file->data()); };
  auto f32 = [&](const std::string& n, uint32_t r, uint32_t cc) { return reinterpret_cast<const float*>(dev(file->Get(n, kFzwF32, r, cc))); };
  auto f16 = [&](const std::string& n, uint32_t r, uint32_t cc) { return dev(file->Get(n, kFzwF16, r, cc)); };

  const uint32_t D = d, F = ffn * d;
  posb = f32("embed.posb", kTokens, D);
  final_g = f32("final.ln.g", 1, D);
  final_b = f32("final.ln.b", 1, D);
  v2_w = f32("val.fc2.w", 3, kHidden);
  v2_b = f32("val.fc2.b", 1, 3);
  m2_w = f32("mlh.fc2.w", 1, kHidden);
  m2_b = f32("mlh.fc2.b", 1, 1);

  embed = std::make_unique<Gemm>(this, GemmShape{d, kPlanesPadded, false, Epilogue::kNone, false}, f16("embed.w", D, kPlanesPadded), nullptr);
  head = std::make_unique<Gemm>(this, GemmShape{head_cols, d, true, Epilogue::kBias, true}, f16("head.w", head_cols, D),
                                f32("head.b", 1, head_cols));
  fc1v = std::make_unique<Gemm>(this, GemmShape{kHidden, kTokens * kValueTokens, true, Epilogue::kBias, true},
                                f16("val.fc1.w", kHidden, kTokens * kValueTokens), f32("val.fc1.b", 1, kHidden));
  fc1m = std::make_unique<Gemm>(this, GemmShape{kHidden, kTokens * kMlhTokens, true, Epilogue::kBias, true},
                                f16("mlh.fc1.w", kHidden, kTokens * kMlhTokens), f32("mlh.fc1.b", 1, kHidden));
  for (int i = 0; i < layers; ++i) {
    const std::string p = "b" + std::to_string(i) + ".";
    LayerWeights w;
    w.ln1_g = f32(p + "ln1.g", 1, D);
    w.ln1_b = f32(p + "ln1.b", 1, D);
    w.relbias = f32(p + "relbias", heads, kRelEntries);
    w.proj_b = f32(p + "proj.b", 1, D);
    w.ln2_g = f32(p + "ln2.g", 1, D);
    w.ln2_b = f32(p + "ln2.b", 1, D);
    w.ff2_b = f32(p + "ff2.b", 1, D);
    lw.push_back(w);
    qkv.push_back(std::make_unique<Gemm>(this, GemmShape{3 * d, d, false, Epilogue::kBias, false}, f16(p + "qkv.w", 3 * D, D),
                                         f16(p + "qkv.b", 1, 3 * D)));
    proj.push_back(std::make_unique<Gemm>(this, GemmShape{d, d, false, Epilogue::kNone, false}, f16(p + "proj.w", D, D), nullptr));
    ff1.push_back(std::make_unique<Gemm>(this, GemmShape{ffn * d, d, false, Epilogue::kGeluBias, false}, f16(p + "ff1.w", F, D),
                                         f16(p + "ff1.b", 1, F)));
    ff2.push_back(std::make_unique<Gemm>(this, GemmShape{d, ffn * d, false, Epilogue::kNone, false}, f16(p + "ff2.w", D, F), nullptr));
  }

  const int n = std::max(1, options.contexts);
  for (int i = 0; i < n; ++i) {
    contexts.push_back(std::make_unique<Context>());
    AllocContext(contexts.back().get());
    free_contexts.push_back(contexts.back().get());
  }
  // Warm-up at the largest batch: creates every cuBLASLt plan (and times the candidate algorithms) before the first real batch.
  Context& c0 = *contexts[0];
  Forward(c0, kMaxBatch, nullptr);
  FZ_CUDA(cudaStreamSynchronize(c0.stream));
}

Net::Impl::~Impl() {
  for (auto& c : contexts) {
    if (c->lt) lt->Destroy(c->lt);
    if (c->stream) cudaStreamDestroy(c->stream);
    if (c->mem) cudaFree(c->mem);
  }
  qkv.clear();
  proj.clear();
  ff1.clear();
  ff2.clear();
  embed.reset();
  head.reset();
  fc1v.reset();
  fc1m.reset();
  if (blob) cudaFree(blob);
  for (auto& s : stages) cudaFreeHost(s->block);
}

Context* Net::Impl::Acquire() {
  std::unique_lock<std::mutex> lock(pool_mu);
  pool_cv.wait(lock, [this] { return !free_contexts.empty(); });
  Context* c = free_contexts.back();
  free_contexts.pop_back();
  return c;
}

void Net::Impl::Release(Context* c) {
  {
    std::lock_guard<std::mutex> lock(pool_mu);
    free_contexts.push_back(c);
  }
  pool_cv.notify_one();
}

// The whole network, as launches on c.stream (nothing here waits for the GPU).
void Net::Impl::Forward(Context& c, int batch, Observer* obs) {
  const int M = batch * kTokens;
  cudaStream_t s = c.stream;
  auto mark = [&](const char* name) {
    if (obs) obs->Mark(name);
  };
  // The first position's tokens (the first 100 rows of a [M, cols] buffer).
  auto tap = [&](const char* name, const void* device, int cols, bool half) {
    if (obs) obs->Tap(name, device, kTokens, cols, half);
  };

  LaunchExpandInput(c.planes, c.x0, batch, s);
  mark("expand input");
  tap("x0", c.x0, kPlanesPadded, true);
  embed->Run(c, M, c.x0, c.y);
  mark("embed product");
  tap("embed", c.y, d, true);
  LaunchAddLayerNorm(c.y, nullptr, posb, kTokens, lw[0].ln1_g, lw[0].ln1_b, c.x, c.ln, M, d, s);
  mark("add + layernorm");
  tap("x_in", c.x, d, true);
  tap("ln_in", c.ln, d, true);
  for (int i = 0; i < layers; ++i) {
    const LayerWeights& w = lw[i];
    qkv[i]->Run(c, M, c.ln, c.qkv);
    mark("qkv product");
    if (i == 0) tap("qkv0", c.qkv, 3 * d, true);
    LaunchAttention(c.qkv, w.relbias, c.att, batch, heads, s);
    mark("attention");
    if (i == 0) tap("att0", c.att, d, true);
    proj[i]->Run(c, M, c.att, c.y);
    mark("proj product");
    LaunchAddLayerNorm(c.x, c.y, w.proj_b, 1, w.ln2_g, w.ln2_b, c.x, c.ln, M, d, s);
    mark("add + layernorm");
    if (i == 0) tap("ln2_0", c.ln, d, true);
    ff1[i]->Run(c, M, c.ln, c.ff);
    mark("ff1 product + gelu");
    if (i == 0) tap("ff0", c.ff, ffn * d, true);
    ff2[i]->Run(c, M, c.ff, c.y);
    mark("ff2 product");
    const float* g = i + 1 < layers ? lw[i + 1].ln1_g : final_g;
    const float* b = i + 1 < layers ? lw[i + 1].ln1_b : final_b;
    LaunchAddLayerNorm(c.x, c.y, w.ff2_b, 1, g, b, c.x, c.ln, M, d, s);
    mark("add + layernorm");
    if (i == 0) tap("x1", c.x, d, true);
  }
  tap("ln_final", c.ln, d, true);
  head->Run(c, M, c.ln, c.head);
  mark("head product");
  tap("head", c.head, head_cols, false);
  LaunchGatherPolicy(c.head, c.move_index, c.move_count, c.logits, batch, head_cols, s);
  LaunchHeadTokens(c.head, c.vtok, c.mtok, batch, head_cols, s);
  mark("policy gather + head tokens");
  fc1v->Run(c, batch, c.vtok, c.fc1v);
  fc1m->Run(c, batch, c.mtok, c.fc1m);
  LaunchFinalHeads(c.fc1v, c.fc1m, v2_w, v2_b, m2_w, m2_b, c.wdlm, batch, s);
  mark("value / moves-left heads");
  if (obs) obs->Tap("wdlm", c.wdlm, 1, 4, false);
  FZ_CUDA(cudaGetLastError());
}

// ---------------------------------------------------------------------------------------------------------------------
// Net
// ---------------------------------------------------------------------------------------------------------------------

Net::Net(std::unique_ptr<Impl> impl) : impl_(std::move(impl)) {}
Net::~Net() = default;

std::unique_ptr<Net> Net::Create(const std::string& fzw_path, const NetOptions& options) {
  static_assert(kMaxBatch == 64, "update the buffers and the cli limit together");
  auto impl = std::make_unique<Impl>();
  impl->options = options;
  impl->Init(fzw_path);
  std::unique_ptr<Net> net(new Net(std::move(impl)));
  if (options.verbose) std::cout << "[fzcuda] " << net->Describe() << std::endl;
  return net;
}

std::string Net::Describe() const {
  std::ostringstream o;
  o << impl_->prop.name << " (sm_" << impl_->prop.major << impl_->prop.minor << ", " << impl_->prop.multiProcessorCount
    << " SMs); network d_model " << impl_->d << ", " << impl_->layers << " layers, " << impl_->heads << " heads, weights "
    << impl_->blob_bytes / 1000000.0 << " MB; cuBLASLt " << impl_->lt_version / 10000 << "." << (impl_->lt_version / 100) % 100
    << "." << impl_->lt_version % 100 << "; " << impl_->contexts.size() << " contexts, batches up to " << kMaxBatch;
  return o.str();
}

int Net::d_model() const { return impl_->d; }
int Net::layers() const { return impl_->layers; }

Stage* Net::AcquireStage() {
  {
    std::lock_guard<std::mutex> lock(impl_->stage_mu);
    if (!impl_->free_stages.empty()) {
      Stage* s = impl_->free_stages.back();
      impl_->free_stages.pop_back();
      return s;
    }
  }
  FZ_CUDA(cudaSetDevice(0));
  auto st = std::make_unique<StageStorage>();
  const size_t planes = size_t{kMaxBatch} * kStagePlanes * sizeof(PlaneGpu), midx = size_t{kMaxBatch} * kStageMaxLegal * 2,
               mcnt = 256, logits = size_t{kMaxBatch} * kStageMaxLegal * 4, wdlm = size_t{kMaxBatch} * 16;
  FZ_CUDA(cudaHostAlloc(&st->block, planes + midx + mcnt + logits + wdlm, cudaHostAllocPortable));
  uint8_t* p = static_cast<uint8_t*>(st->block);
  st->stage.planes = p;
  st->stage.move_index = reinterpret_cast<uint16_t*>(p + planes);
  st->stage.move_count = reinterpret_cast<uint16_t*>(p + planes + midx);
  st->stage.logits = reinterpret_cast<float*>(p + planes + midx + mcnt);
  st->stage.wdlm = reinterpret_cast<float*>(p + planes + midx + mcnt + logits);
  std::lock_guard<std::mutex> lock(impl_->stage_mu);
  impl_->stages.push_back(std::move(st));
  return &impl_->stages.back()->stage;
}

void Net::ReleaseStage(Stage* stage) {
  std::lock_guard<std::mutex> lock(impl_->stage_mu);
  impl_->free_stages.push_back(stage);
}

namespace {
struct Lease {
  Net::Impl* impl;
  Context* c;
  explicit Lease(Net::Impl* i) : impl(i), c(i->Acquire()) {}
  ~Lease() { impl->Release(c); }
};
}  // namespace

void Net::Run(Stage* st, int batch) {
  if (batch < 1 || batch > kMaxBatch) throw Exception("fzcuda: batch size " + std::to_string(batch) + " is outside 1.." + std::to_string(kMaxBatch));
  FZ_CUDA(cudaSetDevice(0));
  Lease lease(impl_.get());
  Context& c = *lease.c;
  cudaStream_t s = c.stream;
  FZ_CUDA(cudaMemcpyAsync(c.planes, st->planes, size_t(batch) * kPlanes * sizeof(PlaneGpu), cudaMemcpyHostToDevice, s));
  FZ_CUDA(cudaMemcpyAsync(c.move_index, st->move_index, size_t(batch) * kMaxLegal * 2, cudaMemcpyHostToDevice, s));
  FZ_CUDA(cudaMemcpyAsync(c.move_count, st->move_count, size_t(batch) * 2, cudaMemcpyHostToDevice, s));
  impl_->Forward(c, batch, nullptr);
  FZ_CUDA(cudaMemcpyAsync(st->logits, c.logits, size_t(batch) * kMaxLegal * 4, cudaMemcpyDeviceToHost, s));
  FZ_CUDA(cudaMemcpyAsync(st->wdlm, c.wdlm, size_t(batch) * 16, cudaMemcpyDeviceToHost, s));
  FZ_CUDA(cudaStreamSynchronize(s));
}

std::vector<Tap> Net::Taps(Stage* st, int batch) {
  if (batch < 1 || batch > kMaxBatch) throw Exception("fzcuda: batch size " + std::to_string(batch) + " is outside 1.." + std::to_string(kMaxBatch));
  FZ_CUDA(cudaSetDevice(0));
  Lease lease(impl_.get());
  Context& c = *lease.c;
  cudaStream_t s = c.stream;
  FZ_CUDA(cudaMemcpyAsync(c.planes, st->planes, size_t(batch) * kPlanes * sizeof(PlaneGpu), cudaMemcpyHostToDevice, s));
  FZ_CUDA(cudaMemcpyAsync(c.move_index, st->move_index, size_t(batch) * kMaxLegal * 2, cudaMemcpyHostToDevice, s));
  FZ_CUDA(cudaMemcpyAsync(c.move_count, st->move_count, size_t(batch) * 2, cudaMemcpyHostToDevice, s));
  TapSink sink(s);
  impl_->Forward(c, batch, &sink);
  FZ_CUDA(cudaStreamSynchronize(s));
  std::vector<Tap> out;
  for (const auto& it : sink.items) {
    Tap t;
    t.name = it.name;
    t.rows = it.rows;
    t.cols = it.cols;
    t.values.resize(size_t(it.rows) * it.cols);
    for (size_t i = 0; i < t.values.size(); ++i)
      t.values[i] = it.half ? __half2float(reinterpret_cast<const __half*>(it.raw.data())[i])
                            : reinterpret_cast<const float*>(it.raw.data())[i];
    out.push_back(std::move(t));
  }
  return out;
}

std::vector<StageTime> Net::Profile(int batch, int reps) {
  FZ_CUDA(cudaSetDevice(0));
  Lease lease(impl_.get());
  Context& c = *lease.c;
  FZ_CUDA(cudaMemsetAsync(c.planes, 0, size_t(batch) * kPlanes * sizeof(PlaneGpu), c.stream));
  FZ_CUDA(cudaMemsetAsync(c.move_count, 0, size_t(batch) * 2, c.stream));
  for (int i = 0; i < 3; ++i) impl_->Forward(c, batch, nullptr);
  FZ_CUDA(cudaStreamSynchronize(c.stream));
  std::vector<StageTime> out;
  std::map<std::string, size_t> index;
  double total = 0;
  for (int r = 0; r < reps; ++r) {
    StageClock clock(c.stream);
    impl_->Forward(c, batch, &clock);
    FZ_CUDA(cudaStreamSynchronize(c.stream));
    cudaEvent_t prev = clock.start;
    for (auto& [name, ev] : clock.marks) {
      float ms = 0;
      FZ_CUDA(cudaEventElapsedTime(&ms, prev, ev));
      prev = ev;
      auto it = index.find(name);
      if (it == index.end()) {
        index[name] = out.size();
        out.push_back({name, 0.0});
        it = index.find(name);
      }
      out[it->second].ms += ms / reps;
      total += ms / reps;
    }
  }
  out.push_back({"TOTAL", total});
  return out;
}

}  // namespace lczero::fz
