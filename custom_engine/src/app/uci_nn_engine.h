#pragma once
#include <memory>
#include <string>

namespace lczero { class Backend; }

// Runs the UCI-NN engine loop (MCTS + ONNX) on stdin/stdout.
void run_uci_nn(const std::string& weights, const std::string& provider, int fixed_batch);

// Tests only: like fz_create (app/fairyzero_ffi.h) -- drive it with fz_send /
// fz_poll / fz_destroy -- but the engine searches with `backend` instead of
// loading a network, so UCI behaviour can be tested without weights.
void* fz_create_with_backend(std::unique_ptr<lczero::Backend> backend);
