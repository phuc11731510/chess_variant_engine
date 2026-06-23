#include "neural/batching_backend.h"

namespace lczero {

namespace {

// Thin producer-side computation. Its AddInput forwards each leaf to the shared
// aggregated computation SYNCHRONOUSLY (encode happens now), and its
// ComputeBlocking blocks until the server has evaluated this group's slots.
class BatchingComputation : public BackendComputation {
 public:
  explicit BatchingComputation(BatchingBackend* backend) : backend_(backend) {}

  size_t UsedBatchSize() const override { return used_; }

  AddInputResult AddInput(const EvalPosition& pos,
                          EvalResultPtr result) override {
    backend_->AddSlot(pos, result, &group_);
    ++used_;
    return ENQUEUED_FOR_EVAL;
  }

  void ComputeBlocking() override {
    if (used_ == 0) return;
    backend_->Flush(&group_);
    used_ = 0;
  }

 private:
  BatchingBackend* backend_;
  BatchingBackend::Group group_;
  size_t used_ = 0;
};

}  // namespace

BatchingBackend::BatchingBackend(std::unique_ptr<Backend> wrapped,
                                 int expected_producers, int timeout_us)
    : wrapped_(std::move(wrapped)),
      expected_producers_(expected_producers < 1 ? 1 : expected_producers),
      timeout_us_(timeout_us < 0 ? 0 : timeout_us) {
  server_ = std::thread(&BatchingBackend::ServerLoop, this);
}

BatchingBackend::~BatchingBackend() {
  {
    std::lock_guard<std::mutex> lk(mu_);
    stop_ = true;
  }
  cv_server_.notify_all();
  cv_space_.notify_all();
  cv_done_.notify_all();
  if (server_.joinable()) server_.join();
}

std::unique_ptr<BackendComputation> BatchingBackend::CreateComputation() {
  return std::make_unique<BatchingComputation>(this);
}

void BatchingBackend::EnsureSharedLocked() {
  if (!shared_) shared_ = wrapped_->CreateComputation();
}

void BatchingBackend::AddSlot(const EvalPosition& pos, EvalResultPtr result,
                              Group* g) {
  std::unique_lock<std::mutex> lk(mu_);
  EnsureSharedLocked();
  // Wait for a free slot: not while the server is running, and not while full.
  cv_space_.wait(lk, [&] {
    return stop_ || (!running_ && shared_->UsedBatchSize() < MaxBatchSize);
  });
  if (stop_) return;

  const size_t slot = shared_->UsedBatchSize();
  // Encodes the position and copies legal moves NOW (pos is still valid).
  shared_->AddInput(pos, result);
  slot_owner_[slot] = g;
  ++g->remaining;

  if (!have_pending_) {
    have_pending_ = true;
    first_pending_ = std::chrono::steady_clock::now();
  }
  // A full buffer must be launched even if not all producers have arrived.
  if (shared_->UsedBatchSize() >= MaxBatchSize) cv_server_.notify_one();
}

void BatchingBackend::Flush(Group* g) {
  std::unique_lock<std::mutex> lk(mu_);
  ++submitted_groups_;
  cv_server_.notify_one();  // all-producers-blocked may now be true
  cv_done_.wait(lk, [&] { return stop_ || g->remaining == 0; });
  --submitted_groups_;
}

void BatchingBackend::ServerLoop() {
  std::unique_lock<std::mutex> lk(mu_);
  while (!stop_) {
    cv_server_.wait(lk, [&] {
      return stop_ || (shared_ && shared_->UsedBatchSize() > 0);
    });
    if (stop_) break;

    // Decide when to launch: as soon as the buffer is full OR every expected
    // producer is blocked waiting (nothing more will arrive this round) OR the
    // aggregation timeout elapses (forward-progress guarantee).
    while (!stop_) {
      const size_t n = shared_->UsedBatchSize();
      if (n == 0) break;
      if (n >= MaxBatchSize) break;
      if (submitted_groups_ >= expected_producers_) break;
      if (timeout_us_ <= 0) break;
      const auto deadline = first_pending_ + std::chrono::microseconds(timeout_us_);
      if (cv_server_.wait_until(lk, deadline) == std::cv_status::timeout) break;
    }
    if (stop_) break;

    const size_t n = shared_->UsedBatchSize();
    if (n == 0) {
      have_pending_ = false;
      continue;
    }

    // Run inference outside the lock; producers stay parked (running_ == true).
    running_ = true;
    lk.unlock();
    shared_->ComputeBlocking();  // ORT Run + softmax; writes results; resets to 0.
    lk.lock();

    // Mark each processed slot's group done; release a fully-evaluated group.
    for (size_t s = 0; s < n; ++s) {
      Group* g = slot_owner_[s];
      slot_owner_[s] = nullptr;
      if (g) --g->remaining;
    }
    running_ = false;
    have_pending_ = false;
    cv_done_.notify_all();   // wake producers whose group hit remaining == 0
    cv_space_.notify_all();  // slots are free again
  }
}

}  // namespace lczero
