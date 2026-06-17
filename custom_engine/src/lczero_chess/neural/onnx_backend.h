#pragma once

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
constexpr size_t PolicyOutputSize = 11800; // 118 directions/promotions * 100 squares
constexpr size_t ValueOutputSize = 3;     // WDL (Win, Draw, Loss)

class OnnxComputation : public BackendComputation {
 public:
  OnnxComputation(Ort::Session* session, Ort::MemoryInfo& memory_info);
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
  
  // Static Zero-Heap buffers
  alignas(64) float input_buffer_[MaxBatchSize * InputBufferUnitSize];
  alignas(64) float policy_output_buffer_[MaxBatchSize * PolicyOutputSize];
  alignas(64) float value_output_buffer_[MaxBatchSize * ValueOutputSize];
  
  EvalResultPtr results_[MaxBatchSize];
  StaticVector<Move, 384> position_moves_[MaxBatchSize];
  bool position_is_black_[MaxBatchSize];
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
  int intra_op_threads_ = 1;
  int inter_op_threads_ = 1;
};

} // namespace lczero
