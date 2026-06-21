#pragma once
#include <string>
#include <vector>
#include <utility>

// All command-line state, parsed once by parse_cli() and passed to the mode runners.
struct EngineOptions {
    bool test_mcts_mode=false, selfplay_mode=false, test_ep_mode=false, test_board_mode=false,
         test_policy_mode=false, test_trainingdata_mode=false, test_extract_mode=false,
         test_selfplay_mode=false, emit_roundtrip_mode=false, test_perft_mode=false,
         test_bits_mode=false, test_rules_mode=false, test_adapter_mode=false, test_nn_mode=false,
         uci_nn_mode=false, test_uci_mode=false, test_encoder_mode=false, play_mode=false,
         arena_mode=false;
    bool play_human_white=true;
    std::string rt_prefix="roundtrip";
    std::string weights_file="weights_0_elo.onnx";
    int sp_games=100, sp_visits=200, sp_parallel=1, sp_threads_per_game=1;
    int sp_max_moves=200, sp_temp_cutoff=30, sp_backend_threads=1, sp_fixed_batch=16;
    std::string sp_out="selfplay_data";
    std::string sp_provider="cpu";
    float sp_noise_eps=0.25f, sp_noise_alpha=0.3f, sp_policy_temp=1.0f, sp_cpuct=-1.0f;
    std::string sp_start_fen;
    float sp_resign_threshold=-2.0f, sp_no_resign_frac=0.10f;
    int sp_resign_consecutive=3, sp_resign_earliest=0;
    std::vector<std::pair<std::string,std::string>> sp_search_opts;
    std::string arena_a, arena_b;
};

EngineOptions parse_cli(int argc, char* argv[]);
