#pragma once

#include <atomic>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>
#include "neural/backend.h"
#include "utils/optionsdict.h"
#include "onnxruntime_cxx_api.h"

namespace lczero {

constexpr size_t InputPlanesCount = 226;
constexpr size_t BoardWidth = 10;
constexpr size_t BoardHeight = 10;
constexpr size_t InputBufferUnitSize = InputPlanesCount * BoardWidth * BoardHeight; // 22600
constexpr size_t PolicyOutputSize = 10600; // 106 directions/promotions * 100 squares
constexpr size_t ValueOutputSize = 3;     // WDL (Win, Draw, Loss)

// --- Instrumentation: what actually reached the neural network ---------------
//
// The search's playout counter does NOT measure device work: several playouts
// can share one evaluation (cache hits, collisions), and the fixed-batch profile
// pads short batches so the device runs slots nobody asked for. These counters
// measure the real thing, which is what decides whether the GPU is saturated.
//
//   real   : positions the search actually submitted.
//   padded : slots the device computed, including fixed-batch zero padding.
//            (padded - real) / padded = fraction of GPU time thrown away.
//   runs   : number of session->Run() calls; real/runs = mean effective batch.
//
// Process-wide and lock-free; all backends funnel through OnnxComputation.
struct OnnxEvalCounters {
  uint64_t real = 0;
  uint64_t padded = 0;
  uint64_t runs = 0;
};
OnnxEvalCounters OnnxGetEvalCounters();
void OnnxResetEvalCounters();

// Output post-processing, exposed for --test-neural.
//
// SoftmaxLegal: out_p[i] = exp((logits[i] - max_logit) / temp) / sum, for
// i < n (n <= 384). `logits` is scratch (overwritten) and must be 32-byte
// aligned with room for n rounded up to 8. `max_logit` is max(logits[0..n)).
// Returns the sum of the exponentials (>= 1 for finite input; not finite when
// the net produced NaN/inf). Accurate to a few float ulps on x86 (AVX2) and ARM.
float SoftmaxLegal(float* logits, size_t n, float temp, float max_logit, float* out_p,
                   size_t max_out);
// True when a value-head row is a WDL distribution (finite, each in [0,1], sum
// 1 within 1e-3), i.e. the net ends with a softmax like python/train.py exports.
bool IsWdlDistribution(const float* wdl);

// Buffer slots an OnnxComputation needs: MaxBatchSize inputs, rounded up to a
// multiple of the fixed batch so the last, zero-padded Run() stays inside.
size_t OnnxBufferSlots(bool fixed_batch, size_t fixed_batch_size);

class OnnxComputation : public BackendComputation {
 public:
  OnnxComputation(Ort::Session* session, Ort::MemoryInfo& memory_info, float softmax_temp, bool fixed_batch, size_t fixed_batch_size);
  ~OnnxComputation() override = default;

  size_t UsedBatchSize() const override {
    return enqueued_.load(std::memory_order_acquire);
  }
  
  AddInputResult AddInput(
      const EvalPosition& pos,
      EvalResultPtr result) override;
      
  void ComputeBlocking() override;

 private:
  Ort::Session* session_;
  Ort::MemoryInfo& memory_info_;
  
  // Slots handed out so far. Atomic because lc0's search calls AddInput from
  // several task threads at once (SearchWorker::ProcessPickedTask), each of
  // which must get its own slot; ComputeBlocking runs after they all finished.
  std::atomic<size_t> enqueued_{0};
  
  // Heap buffers, not fixed arrays: a fresh OnnxComputation is built for EVERY
  // Run(), and zero-filled arrays of MaxBatchSize cost a flat ~3.6 ms per Run on
  // a Colab T4 (see the ctor). Nothing is memset; every byte ORT reads is written.
  const size_t capacity_;  // inputs AddInput accepts (MaxBatchSize)
  const size_t slots_;     // buffer slots, >= capacity_ (OnnxBufferSlots)
  std::unique_ptr<float[]> input_buffer_;         // slots_ * InputBufferUnitSize
  std::unique_ptr<float[]> policy_output_buffer_; // slots_ * PolicyOutputSize
  std::unique_ptr<float[]> value_output_buffer_;  // slots_ * ValueOutputSize

  std::vector<EvalResultPtr> results_;
  std::vector<StaticVector<Move, 384>> position_moves_;
  float softmax_temp_;
  bool fixed_batch_;
  size_t fixed_batch_size_;
};

class OnnxBackend : public Backend {
 public:
  OnnxBackend();
  ~OnnxBackend() override = default;

  BackendAttributes GetAttributes() const override;
  std::unique_ptr<BackendComputation> CreateComputation() override;
  
  void UpdateConfiguration(const OptionsDict& opts) override;
  bool IsSameConfiguration(const OptionsDict& opts) const override;

 private:
  void InitializeSession();

  Ort::Env env_;
  Ort::SessionOptions session_options_;
  Ort::MemoryInfo memory_info_;
  std::unique_ptr<Ort::Session> session_;
  
  std::string weights_path_;
  std::string backend_opts_;
  std::string provider_ = "cpu";
  bool fixed_batch_ = false;
  size_t fixed_batch_size_ = 16;
  bool cuda_graph_ = false;  // EXPERIMENTAL: "cuda_graph=1" backend opt, CUDA-only, needs fixed_batch_. See InitializeSession().
  int intra_op_threads_ = 1;
  int inter_op_threads_ = 1;
  float softmax_temp_ = 1.0f;
};

} // namespace lczero
