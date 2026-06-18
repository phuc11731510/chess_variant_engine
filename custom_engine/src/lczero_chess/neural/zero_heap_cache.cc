#include "neural/zero_heap_cache.h"
#include "neural/shared_params.h"
#include "utils/exception.h"
#include <cassert>
#include <cstring>
#include <algorithm>

namespace lczero {

// Helper to hash position history
static uint64_t ComputeEvalPositionHash(const EvalPosition& pos) {
    if (!pos.history) return 0;
    return pos.history->Last().Hash();
}

// ==========================================
// ZeroHeapCacheComputation Implementation
// ==========================================

class ZeroHeapCacheComputation : public BackendComputation {
 public:
  ZeroHeapCacheComputation(std::unique_ptr<BackendComputation> wrapped, ZeroHeapCache* cache, size_t max_batch_size)
      : wrapped_(std::move(wrapped)), cache_(cache), max_batch_size_(max_batch_size), num_entries_(0) {
      // Initialize temporary buffers for Zero-Heap integration
      for (size_t i = 0; i < max_batch_size_; ++i) {
          temp_results_[i].q = 0.0f;
          temp_results_[i].d = 0.0f;
          temp_results_[i].m = 0.0f;
          temp_results_[i].p.reserve(384);
          temp_results_[i].p.clear();
      }
  }
  
  ~ZeroHeapCacheComputation() override = default;

  size_t UsedBatchSize() const override {
      return wrapped_->UsedBatchSize();
  }

  AddInputResult AddInput(const EvalPosition& pos, EvalResultPtr result) override {
      assert(pos.legal_moves.size() == result.p.size() || result.p.empty());
      
      const uint64_t hash = ComputeEvalPositionHash(pos);
      const uint16_t num_moves = pos.legal_moves.size();
      
      // 1. Check if hit in static lockless cache
      if (cache_->TryRead(hash, num_moves, result)) {
          return AddInputResult::FETCHED_IMMEDIATELY;
      }
      
      // 2. Cache Miss: queue for real neural inference
      if (num_entries_ >= max_batch_size_) {
          throw Exception("ZeroHeapCache: Batch size limit exceeded.");
      }
      
      size_t entry_idx = num_entries_++;
      entries_[entry_idx] = Entry{.hash = hash, .result_ptr = result};
      
      // Allocate temporary results dynamically without using malloc/heap
      temp_results_[entry_idx].p.resize(num_moves);
      
      // Route input to the underlying backend computation
      return wrapped_->AddInput(pos, temp_results_[entry_idx].AsPtr());
  }

  void ComputeBlocking() override {
      if (wrapped_->UsedBatchSize() == 0) {
          num_entries_ = 0;
          return;
      }
      
      // Trigger execution of wrapped ONNX Runtime session
      wrapped_->ComputeBlocking();
      
      // Copy outputs to client results and store in Cache
      for (size_t i = 0; i < num_entries_; ++i) {
          const auto& entry = entries_[i];
          auto& temp = temp_results_[i];
          
          // Copy to final pointer destination
          if (entry.result_ptr.q) *entry.result_ptr.q = temp.q;
          if (entry.result_ptr.d) *entry.result_ptr.d = temp.d;
          if (entry.result_ptr.m) *entry.result_ptr.m = temp.m;
          
          uint16_t num_moves = temp.p.size();
          size_t copy_moves = std::min(static_cast<size_t>(num_moves), entry.result_ptr.p.size());
          if (copy_moves > 0) {
              std::memcpy(entry.result_ptr.p.data(), temp.p.data(), copy_moves * sizeof(float));
          }
          
          // Insert into cache buckets
          cache_->Insert(entry.hash, num_moves, temp.q, temp.d, temp.m, temp.p);
      }
      
      // Reset tracker
      num_entries_ = 0;
  }

 private:
  struct Entry {
    uint64_t hash;
    EvalResultPtr result_ptr;
  };

  std::unique_ptr<BackendComputation> wrapped_;
  ZeroHeapCache* cache_;
  size_t max_batch_size_;
  
  size_t num_entries_ = 0;
  alignas(64) Entry entries_[MaxBatchSize];
  alignas(64) EvalResult temp_results_[MaxBatchSize];
};

// ==========================================
// ZeroHeapCache Implementation
// ==========================================

ZeroHeapCache::ZeroHeapCache(std::unique_ptr<Backend> wrapped, const OptionsDict& options)
    : wrapped_backend_(std::move(wrapped)) {
    // Default capacity matches option size setup
    int cache_size = options.GetOrDefault<int>(SharedBackendParams::kNNCacheSizeId, 65536);
    SetCacheSize(cache_size);
}

BackendAttributes ZeroHeapCache::GetAttributes() const {
    return wrapped_backend_->GetAttributes();
}

std::unique_ptr<BackendComputation> ZeroHeapCache::CreateComputation() {
    return std::make_unique<ZeroHeapCacheComputation>(
        wrapped_backend_->CreateComputation(),
        this,
        wrapped_backend_->GetAttributes().maximum_batch_size
    );
}

std::optional<EvalResult> ZeroHeapCache::GetCachedEvaluation(const EvalPosition& pos) {
    const uint64_t hash = ComputeEvalPositionHash(pos);
    const uint16_t num_moves = pos.legal_moves.size();
    
    // Direct index allocation
    if (cache_size_ == 0) return std::nullopt;
    size_t idx = hash % cache_size_;
    auto& bucket = cache_buckets_[idx];
    
    // Read atomic verify
    uint32_t seq1 = bucket.sequence.load(std::memory_order_acquire);
    if (seq1 % 2 != 0) return std::nullopt;
    
    uint64_t stored_hash = bucket.hash.load(std::memory_order_relaxed);
    if (stored_hash != hash) return std::nullopt;
    
    CachedValue cv = bucket.value;
    
    std::atomic_thread_fence(std::memory_order_acquire);
    
    uint32_t seq2 = bucket.sequence.load(std::memory_order_acquire);
    if (seq1 != seq2) return std::nullopt;
    if (cv.num_moves != num_moves) return std::nullopt;
    
    size_t copy_moves = std::min(static_cast<size_t>(num_moves), static_cast<size_t>(384));
    EvalResult result;
    result.q = cv.q;
    result.d = cv.d;
    result.m = cv.m;
    result.p.resize(copy_moves);
    if (copy_moves > 0) {
        std::memcpy(result.p.data(), cv.p, copy_moves * sizeof(float));
    }
    
    return result;
}

void ZeroHeapCache::ClearCache() {
    for (size_t i = 0; i < cache_size_; ++i) {
        auto& bucket = cache_buckets_[i];
        bucket.hash.store(0, std::memory_order_relaxed);
        bucket.sequence.store(0, std::memory_order_relaxed);
    }
}

void ZeroHeapCache::SetCacheSize(size_t size) {
    if (size == 0) {
        cache_buckets_.reset();
        cache_size_ = 0;
        return;
    }
    
    // Allocate array once during initialization/resize (prevents runtime re-allocations)
    cache_buckets_ = std::make_unique<CacheBucket[]>(size);
    cache_size_ = size;
    ClearCache();
}

void ZeroHeapCache::UpdateConfiguration(const OptionsDict& opts) {
    wrapped_backend_->UpdateConfiguration(opts);
    
    // Re-verify weights matching
    if (!wrapped_backend_->IsSameConfiguration(opts)) {
        ClearCache();
    }
}

bool ZeroHeapCache::IsSameConfiguration(const OptionsDict& opts) const {
    return wrapped_backend_->IsSameConfiguration(opts);
}

// Lockless thread-safe Seqlock Reading
bool ZeroHeapCache::TryRead(uint64_t hash, uint16_t num_moves, EvalResultPtr& out) {
    if (cache_size_ == 0) return false;
    
    size_t idx = hash % cache_size_;
    auto& bucket = cache_buckets_[idx];
    
    uint32_t seq1 = bucket.sequence.load(std::memory_order_acquire);
    if (seq1 % 2 != 0) return false;
    
    uint64_t stored_hash = bucket.hash.load(std::memory_order_relaxed);
    if (stored_hash != hash) return false;
    
    // Fetch copy structure
    CachedValue cv = bucket.value;
    
    std::atomic_thread_fence(std::memory_order_acquire);
    
    uint32_t seq2 = bucket.sequence.load(std::memory_order_acquire);
    if (seq1 != seq2) return false;
    if (cv.num_moves != num_moves) return false;
    
    // Target buffer mapping
    if (out.q) *out.q = cv.q;
    if (out.d) *out.d = cv.d;
    if (out.m) *out.m = cv.m;
    size_t copy_moves = std::min({static_cast<size_t>(num_moves), out.p.size(), static_cast<size_t>(384)});
    if (copy_moves > 0) {
        std::memcpy(out.p.data(), cv.p, copy_moves * sizeof(float));
    }
    
    return true;
}

// Lockless thread-safe Seqlock Writing
void ZeroHeapCache::Insert(uint64_t hash, uint16_t num_moves, float q, float d, float m, std::span<const float> p) {
    if (cache_size_ == 0) return;
    
    size_t idx = hash % cache_size_;
    auto& bucket = cache_buckets_[idx];
    
    uint32_t seq = bucket.sequence.load(std::memory_order_relaxed);
    while (true) {
        if ((seq & 1) != 0) {
            return; // Another thread is writing, skip caching to avoid stall
        }
        if (bucket.sequence.compare_exchange_strong(seq, seq + 1, std::memory_order_acquire, std::memory_order_relaxed)) {
            break;
        }
    }
    
    bucket.hash.store(hash, std::memory_order_relaxed);
    bucket.value.q = q;
    bucket.value.d = d;
    bucket.value.m = m;
    bucket.value.num_moves = num_moves;
    size_t copy_moves = std::min(static_cast<size_t>(num_moves), static_cast<size_t>(384));
    if (copy_moves > 0) {
        std::memcpy(bucket.value.p, p.data(), copy_moves * sizeof(float));
    }
    
    bucket.sequence.store(seq + 2, std::memory_order_release); // End writing lock
}

// Factory function
std::unique_ptr<CachingBackend> CreateMemCache(std::unique_ptr<Backend> wrapped,
                                               const OptionsDict& options) {
    return std::make_unique<ZeroHeapCache>(std::move(wrapped), options);
}

} // namespace lczero
