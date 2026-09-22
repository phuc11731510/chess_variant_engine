#pragma once

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

class OnnxComputation : public BackendComputation {
 public:
  OnnxComputation(Ort::Session* session, Ort::MemoryInfo& memory_info, float softmax_temp, bool fixed_batch, size_t fixed_batch_size);
  ~OnnxComputation() override = default;

  size_t UsedBatchSize() const override { return enqueued_; }
  
  AddInputResult AddInput(
      const EvalPosition& pos,
      EvalResultPtr result) override;
      
  void ComputeBlocking() override;

 private:
  Ort::Session* session_;
  Ort::MemoryInfo& memory_info_;
  
  size_t enqueued_ = 0;
  
  // Buffers sized to the batch this computation will ACTUALLY run, not to
  // MaxBatchSize. They used to be fixed-size arrays of MaxBatchSize, which made
  // every OnnxComputation ~8.5 MB at MaxBatchSize 64 and ~34 MB at 256 -- and a
  // fresh one is built for EVERY Run(), so that allocation landed on every NN
  // call regardless of how small the real batch was. Measured on a Colab T4 it
  // showed up as a flat ~3.6 ms per Run once the redundant ctor memset was gone.
  // With a CUDA fixed-batch profile of 16 the real need is 1.4 MB, not 34 MB.
  const size_t capacity_;                  // slots this computation can hold
  std::unique_ptr<float[]> input_buffer_;         // capacity_ * InputBufferUnitSize
  std::unique_ptr<float[]> policy_output_buffer_; // capacity_ * PolicyOutputSize
  std::unique_ptr<float[]> value_output_buffer_;  // capacity_ * ValueOutputSize

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
  int intra_op_threads_ = 1;
  int inter_op_threads_ = 1;
  float softmax_temp_ = 1.0f;
};

} // namespace lczero
