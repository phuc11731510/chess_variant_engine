#include "app/cli.h"
#include <string>
#include <cstdlib>

EngineOptions parse_cli(int argc, char* argv[]) {
    EngineOptions o;
    for (int i = 1; i < argc; ++i) {
        if (std::string(argv[i]) == "--selfplay") {
            o.selfplay_mode = true;
        } else if (std::string(argv[i]) == "--games" && i + 1 < argc) {
            o.sp_games = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--out" && i + 1 < argc) {
            o.sp_out = argv[++i];
        } else if (std::string(argv[i]) == "--visits" && i + 1 < argc) {
            o.sp_visits = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--parallel" && i + 1 < argc) {
            o.sp_parallel = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--threads-per-game" && i + 1 < argc) {
            o.sp_threads_per_game = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--max-moves" && i + 1 < argc) {
            o.sp_max_moves = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--temp-cutoff" && i + 1 < argc) {
            o.sp_temp_cutoff = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--backend-threads" && i + 1 < argc) {
            o.sp_backend_threads = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--provider" && i + 1 < argc) {
            o.sp_provider = argv[++i];
        } else if (std::string(argv[i]) == "--fixed-batch" && i + 1 < argc) {
            o.sp_fixed_batch = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--noise-epsilon" && i + 1 < argc) {
            o.sp_noise_eps = static_cast<float>(std::atof(argv[++i]));
        } else if (std::string(argv[i]) == "--noise-alpha" && i + 1 < argc) {
            o.sp_noise_alpha = static_cast<float>(std::atof(argv[++i]));
        } else if (std::string(argv[i]) == "--policy-temp" && i + 1 < argc) {
            o.sp_policy_temp = static_cast<float>(std::atof(argv[++i]));
        } else if (std::string(argv[i]) == "--cpuct" && i + 1 < argc) {
            o.sp_cpuct = static_cast<float>(std::atof(argv[++i]));
        } else if (std::string(argv[i]) == "--start-fen" && i + 1 < argc) {
            o.sp_start_fen = argv[++i];
        } else if (std::string(argv[i]) == "--resign-threshold" && i + 1 < argc) {
            o.sp_resign_threshold = static_cast<float>(std::atof(argv[++i]));
        } else if (std::string(argv[i]) == "--resign-consecutive" && i + 1 < argc) {
            o.sp_resign_consecutive = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--resign-earliest-move" && i + 1 < argc) {
            o.sp_resign_earliest = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--search-opt" && i + 1 < argc) {
            std::string kv = argv[++i];                    // "name=value"
            auto eq = kv.find('=');
            if (eq != std::string::npos) o.sp_search_opts.emplace_back(kv.substr(0, eq), kv.substr(eq + 1));
        } else if (std::string(argv[i]) == "--no-resign-frac" && i + 1 < argc) {
            o.sp_no_resign_frac = static_cast<float>(std::atof(argv[++i]));
        } else if (std::string(argv[i]) == "--show-nps") {
            o.sp_show_nps = true;                          // print aggregate MCTS NPS
        } else if (std::string(argv[i]) == "--batch-aggregate") {
            o.sp_batch_aggregate = true;                   // A4: gom batch NN xuyên nhiều ván
        } else if (std::string(argv[i]) == "--batch-timeout-us" && i + 1 < argc) {
            o.sp_batch_timeout_us = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--arena") {
            o.arena_mode = true;
        } else if (std::string(argv[i]) == "--model-a" && i + 1 < argc) {
            o.arena_a = argv[++i];
        } else if (std::string(argv[i]) == "--model-b" && i + 1 < argc) {
            o.arena_b = argv[++i];
        } else if (std::string(argv[i]) == "--weights" && i + 1 < argc) {
            o.weights_file = argv[++i];
        } else if (std::string(argv[i]) == "--test-ep") {
            o.test_ep_mode = true;
        } else if (std::string(argv[i]) == "--test-board") {
            o.test_board_mode = true;
        } else if (std::string(argv[i]) == "--test-policy") {
            o.test_policy_mode = true;
        } else if (std::string(argv[i]) == "--test-trainingdata") {
            o.test_trainingdata_mode = true;
        } else if (std::string(argv[i]) == "--test-extract") {
            o.test_extract_mode = true;
        } else if (std::string(argv[i]) == "--test-selfplay") {
            o.test_selfplay_mode = true;
        } else if (std::string(argv[i]) == "--emit-roundtrip") {
            o.emit_roundtrip_mode = true;
            if (i + 1 < argc && argv[i + 1][0] != '-') o.rt_prefix = argv[++i];
        } else if (std::string(argv[i]) == "--test-perft") {
            o.test_perft_mode = true;
        } else if (std::string(argv[i]) == "--test-bits") {
            o.test_bits_mode = true;
        } else if (std::string(argv[i]) == "--test-rules") {
            o.test_rules_mode = true;
        } else if (std::string(argv[i]) == "--test-adapter") {
            o.test_adapter_mode = true;
        } else if (std::string(argv[i]) == "--test-nn") {
            o.test_nn_mode = true;
        } else if (std::string(argv[i]) == "--test-mcts") {
            o.test_mcts_mode = true;
            if (i + 1 < argc && argv[i + 1][0] != '-') {
                o.weights_file = argv[i + 1];
            }
        } else if (std::string(argv[i]) == "--uci-nn") {
            o.uci_nn_mode = true;
        } else if (std::string(argv[i]) == "--test-uci") {
            o.test_uci_mode = true;
        } else if (std::string(argv[i]) == "--test-encoder") {
            o.test_encoder_mode = true;
        } else if (std::string(argv[i]) == "--play") {
            o.play_mode = true;
        } else if (std::string(argv[i]) == "--play-black") {
            o.play_mode = true; o.play_human_white = false;
        }
    }
    return o;
}
