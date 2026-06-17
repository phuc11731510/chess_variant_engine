#pragma once

#include <memory>
#include <vector>
#include <atomic>
#include <span>
#include "neural/backend.h"
#include "utils/optionsdict.h"

namespace lczero {

class CachingBackend : public Backend {
 public:
  virtual ~CachingBackend() override = default;
  virtual void ClearCache() = 0;
  virtual void SetCacheSize(size_t size) = 0;
};

struct CachedValue {
  float q;
  float d;
  float m;
  uint16_t num_moves;
  alignas(64) float p[384];
};

struct CacheBucket {
  std::atomic<uint64_t> hash{0};
  std::atomic<uint32_t> sequence{0}; // Seqlock
  CachedValue value;
};

class ZeroHeapCache : public CachingBackend {
 public:
  ZeroHeapCache(std::unique_ptr<Backend> wrapped, const OptionsDict& options);
  ~ZeroHeapCache() override = default;

  BackendAttributes GetAttributes() const override;
  std::unique_ptr<BackendComputation> CreateComputation() override;
  std::optional<EvalResult> GetCachedEvaluation(const EvalPosition& pos) override;

  void ClearCache() override;
  void SetCacheSize(size_t size) override;

  void UpdateConfiguration(const OptionsDict& opts) override;
  bool IsSameConfiguration(const OptionsDict& opts) const override;

  // Lockless thread-safe Seqlock API
  bool TryRead(uint64_t hash, uint16_t num_moves, EvalResultPtr& out);
  void Insert(uint64_t hash, uint16_t num_moves, float q, float d, float m, std::span<const float> p);

 private:
  std::unique_ptr<Backend> wrapped_backend_;
  std::unique_ptr<CacheBucket[]> cache_buckets_;
  size_t cache_size_ = 0;
};

// Factory function equivalent to original CreateMemCache
std::unique_ptr<CachingBackend> CreateMemCache(std::unique_ptr<Backend> wrapped,
                                               const OptionsDict& options);

} // namespace lczero
