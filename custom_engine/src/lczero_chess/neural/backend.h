#pragma once

#include <cstdint>
#include <memory>
#include <optional>
#include <span>
#include <vector>

#include "chess/position.h"
#include "utils/optionsdict.h"

namespace lczero {

struct BackendAttributes {
  bool has_mlh;
  bool has_wdl;
  bool runs_on_cpu;
  int suggested_num_search_threads;
  int recommended_batch_size;
  int maximum_batch_size;
};

struct EvalResultPtr {
  float* q = nullptr;
  float* d = nullptr;
  float* m = nullptr;
  std::span<float> p = {};
};

struct EvalResult {
  float q;
  float d;
  float m;
  std::vector<float> p;

  EvalResultPtr AsPtr() {
    return EvalResultPtr{.q = &q, .d = &d, .m = &m, .p = p};
  }
};

struct EvalPosition {
  std::span<const Position> pos;
  std::span<const Move> legal_moves;
};

class BackendComputation {
 public:
  virtual ~BackendComputation() = default;
  virtual size_t UsedBatchSize() const = 0;
  enum AddInputResult {
    ENQUEUED_FOR_EVAL = 0,
    FETCHED_IMMEDIATELY = 1,
  };
  virtual AddInputResult AddInput(
      const EvalPosition& pos,
      EvalResultPtr result) = 0;
  virtual void ComputeBlocking() = 0;
};

class Backend {
 public:
  virtual ~Backend() = default;
  virtual BackendAttributes GetAttributes() const = 0;
  virtual std::unique_ptr<BackendComputation> CreateComputation() = 0;

  virtual std::vector<EvalResult> EvaluateBatch(
      std::span<const EvalPosition> positions) {
    return {};
  }
  virtual std::optional<EvalResult> GetCachedEvaluation(const EvalPosition&) {
    return std::nullopt;
  }
};

}  // namespace lczero
