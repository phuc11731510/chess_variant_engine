#include "neural/batching_backend.h"

#include <atomic>

namespace lczero {

namespace {

// Thin producer-side computation. Its AddInput forwards each leaf to the shared
// aggregated computation SYNCHRONOUSLY (encode happens now), and its
// ComputeBlocking blocks until the server has evaluated this group's slots.
class BatchingComputation : public BackendComputation {
 public:
  explicit BatchingComputation(BatchingBackend* backend) : backend_(backend) {}

  size_t UsedBatchSize() const override {
    return used_.load(std::memory_order_acquire);
  }

  AddInputResult AddInput(const EvalPosition& pos,
                          EvalResultPtr result) override {
    // AddSlot is serialized by the backend's mutex, but this counter is not:
    // lc0's search calls AddInput from several task threads at once.
    backend_->AddSlot(pos, result, &group_);
    used_.fetch_add(1, std::memory_order_acq_rel);
    return ENQUEUED_FOR_EVAL;
  }

  void ComputeBlocking() override {
    if (used_.load(std::memory_order_acquire) == 0) return;
    backend_->Flush(&group_);
    used_.store(0, std::memory_order_release);
  }

 private:
  BatchingBackend* backend_;
  BatchingBackend::Group group_;
  std::atomic<size_t> used_{0};
};

}  // namespace

BatchingBackend::BatchingBackend(std::unique_ptr<Backend> wrapped,
                                 int expected_producers, int timeout_us)
    : wrapped_(std::move(wrapped)),
      expected_producers_(expected_producers < 0 ? 1 : expected_producers),
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
  for (auto& b : bufs_)
    if (!b) b = wrapped_->CreateComputation();
}

void BatchingBackend::AddSlot(const EvalPosition& pos, EvalResultPtr result,
                              Group* g) {
  std::unique_lock<std::mutex> lk(mu_);
  EnsureSharedLocked();
  // Wait for room in the FILLING buffer. The other buffer may be running on
  // the device meanwhile: that is the point (B2) -- leaves for the next Run
  // are encoded while the current one computes.
  cv_space_.wait(lk, [&] {
    return stop_ || bufs_[fill_]->UsedBatchSize() < MaxBatchSize;
  });
  if (stop_) return;

  BackendComputation* buf = bufs_[fill_].get();
  const size_t slot = buf->UsedBatchSize();
  // Encodes the position and copies legal moves NOW (pos is still valid).
  buf->AddInput(pos, result);
  slot_owner_[fill_][slot] = g;
  ++g->remaining;

  if (!have_pending_) {
    have_pending_ = true;
    first_pending_ = std::chrono::steady_clock::now();
  }
  // A full buffer must be launched even if not all producers have arrived.
  if (buf->UsedBatchSize() >= MaxBatchSize) cv_server_.notify_one();
}

void BatchingBackend::Flush(Group* g) {
  std::unique_lock<std::mutex> lk(mu_);
  if (g->remaining == 0) return;  // all its slots were already evaluated
  // Counted as waiting only while some of its slots are still pending; the
  // server uncounts it the moment its last slot is evaluated, so a producer
  // that was just released (and will submit again soon) never looks blocked.
  g->in_flush = true;
  ++waiting_;
  cv_server_.notify_one();  // all-producers-blocked may now be true
  cv_done_.wait(lk, [&] { return stop_ || g->remaining == 0; });
  g->in_flush = false;
}

void BatchingBackend::ProducerEnter() {
  if (expected_producers_ != 0) return;
  std::lock_guard<std::mutex> lk(mu_);
  ++active_producers_;
}

void BatchingBackend::ProducerLeave() {
  if (expected_producers_ != 0) return;
  {
    std::lock_guard<std::mutex> lk(mu_);
    --active_producers_;
  }
  cv_server_.notify_one();  // the games still searching may all be blocked now
}

void BatchingBackend::ServerLoop() {
  std::unique_lock<std::mutex> lk(mu_);
  while (!stop_) {
    cv_server_.wait(lk, [&] {
      return stop_ || (bufs_[fill_] && bufs_[fill_]->UsedBatchSize() > 0);
    });
    if (stop_) break;

    // Decide when to launch the filling buffer: as soon as it is full OR every
    // producer that can still submit is blocked waiting for results (nothing
    // more will arrive) OR the aggregation timeout elapses (forward progress).
    while (!stop_) {
      const size_t n = bufs_[fill_]->UsedBatchSize();
      if (n == 0) break;
      if (n >= MaxBatchSize) break;
      if (waiting_ >= (expected_producers_ == 0 ? active_producers_ : expected_producers_))
        break;
      if (timeout_us_ <= 0) break;
      const auto deadline = first_pending_ + std::chrono::microseconds(timeout_us_);
      if (cv_server_.wait_until(lk, deadline) == std::cv_status::timeout) break;
    }
    if (stop_) break;

    const int run = fill_;
    const size_t n = bufs_[run]->UsedBatchSize();
    have_pending_ = false;
    if (n == 0) continue;

    // Swap: producers fill the other (empty) buffer while this one runs.
    fill_ = 1 - run;
    cv_space_.notify_all();
    lk.unlock();
    bufs_[run]->ComputeBlocking();  // ORT Run + softmax; writes results; resets to 0.
    lk.lock();

    // Mark each processed slot's group done; release a fully-evaluated group.
    bool released = false;
    for (size_t s = 0; s < n; ++s) {
      Group* g = slot_owner_[run][s];
      slot_owner_[run][s] = nullptr;
      if (g && --g->remaining == 0 && g->in_flush) {
        --waiting_;
        released = true;
      }
    }
    if (released) cv_done_.notify_all();
    cv_space_.notify_all();
    // Leaves that arrived while the device was busy: the aggregation window for
    // a NOT full buffer starts now, when the device is free again -- as before
    // B2 -- so the producers just released still get to join this batch.
    if (have_pending_) first_pending_ = std::chrono::steady_clock::now();
  }
}

}  // namespace lczero
