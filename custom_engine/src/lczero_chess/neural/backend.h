#pragma once

#include <cstdint>
#include <memory>
#include <optional>
#include <span>
#include <vector>

#include "chess/position.h"
#include "utils/optionsdict.h"

#include <cassert>

namespace lczero {

constexpr size_t MaxBatchSize = 64;

// Minimalistic static vector to avoid heap allocation
template <typename T, size_t N>
class StaticVector {
 public:
  StaticVector() : size_(0) {}

  void resize(size_t new_size) {
    if (new_size > N) {
      new_size = N;
    }
    size_ = new_size;
  }

  size_t size() const { return size_; }
  bool empty() const { return size_ == 0; }
  void clear() { size_ = 0; }
  void reserve(size_t new_cap) {
    assert(new_cap <= N);
  }

  T& operator[](size_t idx) { return data_[idx]; }
  const T& operator[](size_t idx) const { return data_[idx]; }

  T* begin() { return data_; }
  const T* begin() const { return data_; }
  T* end() { return data_ + size_; }
  const T* end() const { return data_ + size_; }

  T* data() { return data_; }
  const T* data() const { return data_; }

  // Implicit conversion to std::span for seamless integration
  operator std::span<T>() { return std::span<T>(data_, size_); }
  operator std::span<const T>() const { return std::span<const T>(data_, size_); }

 private:
  T data_[N];
  size_t size_;
};

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
#if 0
  std::vector<float> p;
#else
  StaticVector<float, 384> p;
#endif

  EvalResultPtr AsPtr() {
    return EvalResultPtr{.q = &q, .d = &d, .m = &m, .p = p};
  }
};

struct EvalPosition {
  const PositionHistory* history;
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

  virtual void UpdateConfiguration(const OptionsDict& opts) {}
  virtual bool IsSameConfiguration(const OptionsDict& opts) const { return true; }
};

}  // namespace lczero
