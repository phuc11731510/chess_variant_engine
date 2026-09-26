#pragma once
#include <cstdint>
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
         arena_mode=false, audit_generation_mode=false, bench_nn_mode=false, bench_cpu_mode=false,
         test_search_logic_mode=false, test_history_mode=false, audit_rules_mode=false,
         test_neural_mode=false, test_cli_mode=false;
    // Command-line errors (unknown flag, missing value, bad number): main() prints
    // them and exits 2 instead of running with a default the user did not ask for.
    std::vector<std::string> errors;
    bool play_human_white=true;
    std::string rt_prefix="roundtrip";
    std::string weights_file="weights_0_elo.onnx";
    bool weights_given=false;  // --weights was on the command line (not the default above)
    bool games_given=false;    // --games was on the command line (--audit-rules has its own default)
    uint64_t zobrist_seed=0;   // --zobrist-seed: repeat a run's Zobrist keys (0 = random each run)
    int sp_games=100, sp_visits=200, sp_parallel=1, sp_threads_per_game=1;
    int sp_max_moves=200, sp_temp_cutoff=30, sp_backend_threads=1, sp_fixed_batch=16;
    double sp_max_seconds=0.0;  // --max-seconds: wall-clock budget for self-play (0 = off)
    std::string sp_stop_file;   // --stop-file: self-play takes no NEW game once this file exists ("" = off)
    std::string sp_out="selfplay_data";
    std::string sp_provider="cpu";
    float sp_noise_eps=0.25f, sp_noise_alpha=0.3f, sp_policy_temp=1.0f, sp_cpuct=-1.0f;
    std::string sp_start_fen;
    float sp_resign_threshold=-2.0f, sp_no_resign_frac=0.10f;
    int sp_resign_consecutive=3, sp_resign_earliest=0;
    std::vector<std::pair<std::string,std::string>> sp_search_opts;
    bool sp_show_nps=false;   // --show-nps: print aggregate MCTS NPS during self-play
    bool sp_cuda_graph=false;  // --cuda-graph: EXPERIMENTAL, bat CUDA Graph capture (chi ONNX Runtime CUDA EP, doi hoi --fixed-batch > 0). Chua kiem chung tren phan cung that -- dung --bench-nn de do ca toc do lan tinh dung dan truoc khi dung cho selfplay/arena that.
    bool sp_batch_aggregate=false;  // --batch-aggregate: gom batch NN xuyên nhiều ván (A4, GPU)
    int sp_batch_timeout_us=2000;   // --batch-timeout-us: cửa sổ gộp batch (chống treo)
    std::string arena_a, arena_b;
    bool arena_show_moves=false;   // --arena-moves: in danh sách nước đi mỗi ván arena
};

EngineOptions parse_cli(int argc, char* argv[]);
