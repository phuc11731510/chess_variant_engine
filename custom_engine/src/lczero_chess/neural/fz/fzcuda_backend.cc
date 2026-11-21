#include "neural/fz/fzcuda_backend.h"

#include <algorithm>
#include <chrono>
#include <cstddef>
#include <cstring>
#include <iostream>
#include <sstream>

#include "chess/encoder.h"
#include "neural/network_output.h"
#include "neural/fz/plane_pack.h"
#include "neural/onnx_backend.h"  // OnnxCountRun / OnnxCountCompute: the shared evaluation counters
#include "neural/shared_params.h"
#include "utils/exception.h"

namespace lczero {

static_assert(kInputPlanes == fz::kStagePlanes, "the network has a different number of input planes");
static_assert(fz::kMaxBatch == static_cast<int>(MaxBatchSize), "fz::kMaxBatch and MaxBatchSize must agree");
static_assert(fz::kStageMaxLegal == 384, "EvalResult::p holds at most 384 priors");

namespace {

class FzCudaComputation : public BackendComputation {
 public:
  FzCudaComputation(std::shared_ptr<fz::Net> net, float softmax_temp)
      : net_(std::move(net)), stage_(net_->AcquireStage()), softmax_temp_(softmax_temp), results_(MaxBatchSize) {}
  ~FzCudaComputation() override { net_->ReleaseStage(stage_); }

  size_t UsedBatchSize() const override { return enqueued_.load(std::memory_order_acquire); }

  AddInputResult AddInput(const EvalPosition& pos, EvalResultPtr result) override {
    // The slot is reserved first and atomically: the search calls AddInput from several task threads at once, each of which
    // must write only its own slot (see OnnxComputation::AddInput).
    const size_t slot = enqueued_.fetch_add(1, std::memory_order_acq_rel);
    if (slot >= MaxBatchSize) {
      enqueued_.fetch_sub(1, std::memory_order_acq_rel);
      throw Exception("FzCuda Backend: Maximum batch size exceeded!");
    }
    results_[slot] = result;

    const size_t n = std::min(pos.legal_moves.size(), static_cast<size_t>(fz::kStageMaxLegal));
    uint16_t* index = stage_->move_index + slot * fz::kStageMaxLegal;
    for (size_t i = 0; i < n; ++i) {
      const uint16_t v = MoveToNNIndex(pos.legal_moves[i], 0);
      index[i] = v < kPolicySize ? v : fz::kNoPolicySlot;  // an unmapped move gets probability 0, as in the ONNX path
    }
    stage_->move_count[slot] = static_cast<uint16_t>(n);

    // Same encoding as the ONNX path (ALWAYS: a history board that does not exist yet is a copy of the game's first position),
    // but nothing is unpacked: the masks go to the GPU as they are, 6.5 KB per position instead of 81.6 KB of floats.
    alignas(64) InputPlanes planes;
    int transform = 0;
    EncodePositionForNN(*pos.history, kMoveHistory, FillEmptyHistory::ALWAYS, &planes, &transform);
    fz::PackPlanes(planes, static_cast<uint8_t*>(stage_->planes) + slot * fz::kPackedPlanesBytes);
    return ENQUEUED_FOR_EVAL;
  }

  void ComputeBlocking() override {
    // Every AddInput has returned by now (the search joins its task threads first), so the count is final.
    const size_t enqueued = enqueued_.load(std::memory_order_acquire);
    if (enqueued == 0) return;
    const auto t_compute = std::chrono::steady_clock::now();

    const auto t_run = std::chrono::steady_clock::now();
    net_->Run(stage_, static_cast<int>(enqueued));
    const auto t_done = std::chrono::steady_clock::now();
    OnnxCountRun(enqueued, enqueued, ElapsedNs(t_run, t_done));  // no padding: the runner takes any batch size

    for (size_t b = 0; b < enqueued; ++b) {
      const size_t n = std::min(static_cast<size_t>(stage_->move_count[b]), static_cast<size_t>(fz::kStageMaxLegal));
      alignas(64) float legal_logits[fz::kStageMaxLegal + 8];  // FillEvalResult wants room for n rounded up to 8
      std::memcpy(legal_logits, stage_->logits + b * fz::kStageMaxLegal, n * sizeof(float));
      const float* wdlm = stage_->wdlm + b * 4;
      FillEvalResult(results_[b], wdlm, wdlm[3], legal_logits, n, softmax_temp_, "FzCuda Backend");
    }
    enqueued_.store(0, std::memory_order_release);
    OnnxCountCompute(ElapsedNs(t_compute, std::chrono::steady_clock::now()));
  }

 private:
  static uint64_t ElapsedNs(std::chrono::steady_clock::time_point a, std::chrono::steady_clock::time_point b) {
    return static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(b - a).count());
  }

  std::shared_ptr<fz::Net> net_;
  fz::Stage* stage_;
  float softmax_temp_;
  std::atomic<size_t> enqueued_{0};
  std::vector<EvalResultPtr> results_;
};

std::vector<std::string> Split(const std::string& s, char delimiter) {
  std::vector<std::string> out;
  std::istringstream in(s);
  std::string token;
  while (std::getline(in, token, delimiter)) out.push_back(token);
  return out;
}

}  // namespace

BackendAttributes FzCudaBackend::GetAttributes() const {
  return BackendAttributes{.has_mlh = true,
                           .has_wdl = true,
                           .runs_on_cpu = false,
                           .suggested_num_search_threads = 2,
                           .recommended_batch_size = batch_,
                           .maximum_batch_size = batch_};
}

std::unique_ptr<BackendComputation> FzCudaBackend::CreateComputation() {
  return std::make_unique<FzCudaComputation>(net_, softmax_temp_);
}

void FzCudaBackend::UpdateConfiguration(const OptionsDict& opts) {
  weights_path_ = opts.Get<std::string>(SharedBackendParams::kWeightsId);
  backend_opts_ = opts.GetOrDefault<std::string>(SharedBackendParams::kBackendOptionsId, "");
  softmax_temp_ = opts.GetOrDefault<float>(SharedBackendParams::kPolicySoftmaxTemp, 1.0f);
  if (weights_path_.size() < 4 || weights_path_.compare(weights_path_.size() - 4, 4, ".fzw") != 0)
    throw Exception("FzCuda Backend: --weights must be a .fzw file (python/fzw.py convert gen<N>.pt gen<N>.fzw), got " +
                    weights_path_);

  fz::NetOptions net_options;
  batch_ = fz::kMaxBatch;
  for (const std::string& opt : Split(backend_opts_, ',')) {
    const auto kv = Split(opt, '=');
    if (kv.size() != 2) continue;
    try {
      if (kv[0] == "fixed_batch") {
        const int n = std::stoi(kv[1]);
        if (n > 0) batch_ = std::min(n, fz::kMaxBatch);
      } else if (kv[0] == "contexts") {
        net_options.contexts = std::clamp(std::stoi(kv[1]), 1, 8);
      } else if (kv[0] == "autotune") {
        net_options.autotune = kv[1] != "0";
      } else if (kv[0] == "split") {
        net_options.split = std::clamp(std::stoi(kv[1]), 1, 2);
      } else if (kv[0] != "provider") {
        std::cerr << "[FzCuda Backend] Warning: backend option '" << kv[0] << "' is not used by provider fzcuda" << std::endl;
      }
    } catch (const std::exception&) {
      throw Exception("FzCuda Backend: bad backend option '" + opt + "'");
    }
  }
  net_ = std::shared_ptr<fz::Net>(fz::Net::Create(weights_path_, net_options));
}

bool FzCudaBackend::IsSameConfiguration(const OptionsDict& opts) const {
  if (!opts.Exists<std::string>(SharedBackendParams::kWeightsId)) return false;
  return opts.Get<std::string>(SharedBackendParams::kWeightsId) == weights_path_ &&
         opts.GetOrDefault<std::string>(SharedBackendParams::kBackendOptionsId, "") == backend_opts_;
}

}  // namespace lczero
