#pragma once
#include <string>

// Entry points for the engine's built-in self-tests (invoked from main()).
void run_ep_tests();
void run_board_tests();
void run_mcts_tests(const std::string& weights_path = "weights_0_elo.onnx");
void run_extract_tests(const std::string& weights_path = "weights_0_elo.onnx");
void run_selfplay_tests(const std::string& weights_path = "weights_0_elo.onnx");
void run_policy_tests();
void run_trainingdata_tests();
void run_roundtrip_emit(const std::string& prefix);
void run_perft_tests();
void run_bits_tests();
void run_rules_tests();
void run_adapter_tests();
void run_nn_tests();
void run_uci_tests();
void run_encoder_tests();
