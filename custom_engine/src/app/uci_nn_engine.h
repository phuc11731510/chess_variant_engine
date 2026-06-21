#pragma once
#include <string>

// Runs the UCI-NN engine loop (MCTS + ONNX) on stdin/stdout.
void run_uci_nn(const std::string& weights, const std::string& provider, int fixed_batch);
