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
         test_neural_mode=false, test_cli_mode=false,
         test_fzcuda_mode=false, bench_fzcuda_mode=false, fzcuda_dump_mode=false;  // the CUDA runner (neural/fz/)
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
    // Playout cap randomization (self-play only; 2026-11-20): with probability --fast-prob a move
    // is searched shallowly with --fast-visits playouts, --fast-cpuct and --fast-noise-eps
    // instead of --visits / --cpuct / --noise-epsilon; its record is marked fast_search = 1 (the
    // trainer skips its policy target). 0 (the default) = every move is a full search.
    float sp_fast_prob=0.0f, sp_fast_cpuct=1.25f, sp_fast_noise_eps=0.125f;
    int sp_fast_visits=200;
    // --temperature: self-play AND the arena draw EVERY move with weight (N / N_max)^(1 / T) (0 = most visited).
    float sp_temperature=0.5f;
    // --temp-elo-cutoff <Elo>: a move more than this many Elo below the most visited one is never drawn (0 = off; see selfplay_game.h).
    float sp_elo_cutoff=0.0f;
    bool sp_temp_cutoff_given=false;  // --temp-cutoff (the arena's old opening length) is now an error everywhere
    std::string sp_start_fen;
    std::string fz_dump;       // --fzcuda-dump FILE: positions file for python/fzw.py ref
    std::string fz_positions;  // --fz-positions FILE: that file, read back by --test-fzcuda / --bench-fzcuda
    float sp_resign_threshold=-2.0f, sp_no_resign_frac=0.10f;
    int sp_resign_consecutive=3, sp_resign_earliest=0;
    std::vector<std::pair<std::string,std::string>> sp_search_opts;
    bool sp_show_nps=false;   // --show-nps: print aggregate MCTS NPS during self-play
    bool sp_cuda_graph=false;  // --cuda-graph: EXPERIMENTAL, bat CUDA Graph capture (chi ONNX Runtime CUDA EP, doi hoi --fixed-batch > 0). Chua kiem chung tren phan cung that -- dung --bench-nn de do ca toc do lan tinh dung dan truoc khi dung cho selfplay/arena that.
    // --cuda-opt key=value (repeatable): ONNX Runtime CUDA EP option (e.g.
    // cudnn_conv_algo_search=HEURISTIC, prefer_nhwc=1), passed as-is to
    // UpdateCUDAProviderOptions -- an unknown key stops the run. --provider cuda only.
    std::vector<std::string> sp_cuda_opts;
    // --fz-opt key=value (repeatable): option of the CUDA runner for --provider fzcuda (contexts=2, autotune=0, graph=0, ff1=cublas; see
    // neural/fz/fzcuda_backend.h).
    std::vector<std::string> sp_fz_opts;
    // --trt-opt key=value (repeatable): ORT TensorRT EP option for --provider tensorrt
    // (e.g. trt_engine_cache_path=/content/trt_cache, trt_builder_optimization_level=5).
    std::vector<std::string> sp_trt_opts;
    // --nnapi-opt key=value (repeatable): NNAPI EP flag for --provider nnapi (Android): fp16=1, cpu_disabled=1, cpu_only=1.
    std::vector<std::string> sp_nnapi_opts;
    // --extra-batches 16,32,48 (B3): also load the net pinned at these smaller
    // batch sizes; a Run with fewer inputs uses the smallest that fits.
    std::vector<int> sp_extra_batches;
    // --bench-batches 1,8,16: --bench-nn measures only these batch sizes (default 1..256; a phone CPU needs minutes per size).
    std::vector<int> bench_batches;
    std::string ort_profile;  // --ort-profile PREFIX (--bench-nn): ORT per-node timing JSON
    bool sp_batch_aggregate=false;  // --batch-aggregate: gom batch NN xuyên nhiều ván (A4, GPU)
    int sp_batch_timeout_us=2000;   // --batch-timeout-us: cửa sổ gộp batch (chống treo)
    std::string arena_a, arena_b;
    bool arena_show_moves=false;   // --arena-moves: in danh sách nước đi mỗi ván arena
};

EngineOptions parse_cli(int argc, char* argv[]);
