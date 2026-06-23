#pragma once

#include <chrono>
#include <condition_variable>
#include <memory>
#include <mutex>
#include <optional>
#include <thread>

#include "neural/backend.h"

namespace lczero {

// BatchingBackend (plan A4) — aggregates NN eval requests from MANY concurrent
// self-play games into ONE shared backend computation, so the network runs
// FULLER batches (far better GPU utilization) instead of many tiny per-game
// inferences. It sits between the cache and the real (Onnx) backend:
//
//     ZeroHeapCache  ->  BatchingBackend  ->  OnnxBackend
//
// CORRECTNESS / lifetime: the wrapped computation's AddInput is invoked
// SYNCHRONOUSLY inside the producer's AddInput (it encodes the position and
// copies the legal moves immediately, while the search's per-node `history`
// workspace and local move list are still valid). ONLY the ORT Run is deferred
// to the server thread. This reuses the entire tuned encode+run+softmax path
// without duplicating it, and avoids reading mutated/destroyed search state.
//
// The server launches a batch when the shared computation is full, when all
// expected producers are blocked waiting, or when a small timeout elapses
// (the timeout guarantees forward progress / no hang). Groups whose slots span
// two server rounds are handled via a per-group remaining-slot counter.
class BatchingBackend : public Backend {
 public:
  // `expected_producers` = number of concurrent submitting threads
  // (parallel games * threads_per_game); used only as an early-flush hint.
  BatchingBackend(std::unique_ptr<Backend> wrapped, int expected_producers,
                  int timeout_us);
  ~BatchingBackend() override;

  BackendAttributes GetAttributes() const override {
    return wrapped_->GetAttributes();
  }
  std::unique_ptr<BackendComputation> CreateComputation() override;
  std::optional<EvalResult> GetCachedEvaluation(const EvalPosition& p) override {
    return wrapped_->GetCachedEvaluation(p);
  }
  void UpdateConfiguration(const OptionsDict& o) override {
    wrapped_->UpdateConfiguration(o);
  }
  bool IsSameConfiguration(const OptionsDict& o) const override {
    return wrapped_->IsSameConfiguration(o);
  }

  // Per-minibatch group owned by a BatchingComputation. `remaining` counts this
  // group's enqueued slots not yet evaluated by the server.
  struct Group {
    int remaining = 0;
  };

  // Called by BatchingComputation (the producer side).
  void AddSlot(const EvalPosition& pos, EvalResultPtr result, Group* g);
  void Flush(Group* g);

 private:
  void ServerLoop();
  void EnsureSharedLocked();  // must hold mu_

  std::unique_ptr<Backend> wrapped_;
  std::unique_ptr<BackendComputation> shared_;  // single aggregated computation
  const int expected_producers_;
  const int timeout_us_;

  std::mutex mu_;
  std::condition_variable cv_server_;  // wakes the server
  std::condition_variable cv_space_;   // producers waiting for slot space
  std::condition_variable cv_done_;    // producers waiting for their group
  bool running_ = false;               // server is inside ComputeBlocking
  bool stop_ = false;
  int submitted_groups_ = 0;           // producers currently blocked in Flush
  bool have_pending_ = false;
  std::chrono::steady_clock::time_point first_pending_;
  Group* slot_owner_[MaxBatchSize] = {};

  std::thread server_;
};

}  // namespace lczero
