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

// Compact mode (nn-cache-compact): the priors live in one ring arena of floats,
// each entry holding only its real move count (average ~62, not a 384 slot).
// `pos` is the entry's monotonic arena position; its priors are still intact
// while (arena head - pos) <= arena size, which readers check after copying.
struct CompactBucket {
  std::atomic<uint64_t> hash{0};
  std::atomic<uint32_t> sequence{0}; // Seqlock
  uint16_t num_moves = 0;
  float q = 0, d = 0, m = 0;
  uint64_t pos = 0;
  uint32_t check = 0;  // checksum of the priors: an arena range can also be hit by a slow
                       // writer of an OLDER entry, which the head test cannot see
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

  // Compact mode.
  static constexpr size_t kArenaMovesPerEntry = 64;  // arena budget per entry (avg ~62 moves)
  bool compact_ = false;
  std::unique_ptr<CompactBucket[]> compact_buckets_;
  std::unique_ptr<float[]> arena_;
  size_t arena_size_ = 0;
  std::atomic<uint64_t> arena_head_{0};
  // Copy the arena range [pos, pos + n) (wrapping) out to dst / in from src.
  void ArenaRead(uint64_t pos, size_t n, float* dst) const;
  void ArenaWrite(uint64_t pos, size_t n, const float* src);
  bool CompactRead(uint64_t hash, uint16_t num_moves, bool probe, float* q, float* d, float* m,
                   float* p, size_t p_cap);
};

// Factory function equivalent to original CreateMemCache
std::unique_ptr<CachingBackend> CreateMemCache(std::unique_ptr<Backend> wrapped,
                                               const OptionsDict& options);

} // namespace lczero
