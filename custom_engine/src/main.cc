#include <iostream>
#include <string>
#include <vector>
#include <sstream>
#include <cassert>

#include "bitboard.h"
#include "endgame.h"
#include "position.h"
#include "psqt.h"
#include "search.h"
#include "syzygy/tbprobe.h"
#include "thread.h"
#include "tt.h"
#include "uci.h"
#include "piece.h"
#include "variant.h"
#include "xboard.h"
#include "movegen.h"
#include "chess/board.h"
#include "chess/position.h"
#include "chess/gamestate.h"
#include "chess/encoder.h"
#include "trainingdata/trainingdata_v1.h"
#include "trainingdata/writer.h"
#include "selfplay/training_extract.h"
#include "selfplay/selfplay_game.h"
#include "selfplay/selfplay_driver.h"
#include <cstring>
#include <cstdlib>
#include <fstream>
#include <cstdio>
#include <cmath>
#include <thread>
#include <atomic>
#include <mutex>
#include <chrono>
#include <memory>
#include <map>
#include <functional>
#include <algorithm>
#include "search/classic/search.h"
#include "search/classic/params.h"
#include "neural/backend.h"
#include "neural/shared_params.h"
#include "neural/onnx_backend.h"
#include "neural/zero_heap_cache.h"
#include "utils/random.h"
#include "chess/callbacks.h"
#include "app/variant_setup.h"
#include "app/search_opts.h"
#include "app/arena_mode.h"
#include "app/uci_nn_engine.h"
#include "app/play_mode.h"
#include "tests/engine_tests.h"

using namespace Stockfish;

int main(int argc, char* argv[]) {
    bool test_mcts_mode = false;
    bool selfplay_mode = false;
    bool test_ep_mode = false;
    bool test_board_mode = false;
    bool test_policy_mode = false;
    bool test_trainingdata_mode = false;
    bool test_extract_mode = false;
    bool test_selfplay_mode = false;
    bool emit_roundtrip_mode = false;
    bool test_perft_mode = false;
    bool test_bits_mode = false;
    bool test_rules_mode = false;
    bool test_adapter_mode = false;
    bool test_nn_mode = false;
    bool uci_nn_mode = false;
    bool test_uci_mode = false;
    bool test_encoder_mode = false;
    bool play_mode = false;
    bool play_human_white = true;
    std::string rt_prefix = "roundtrip";
    std::string weights_file = "weights_0_elo.onnx";
    // Self-play driver options.
    int sp_games = 100, sp_visits = 200, sp_parallel = 1, sp_threads_per_game = 1;
    int sp_max_moves = 200, sp_temp_cutoff = 30, sp_backend_threads = 1;
    int sp_fixed_batch = 16;
    std::string sp_out = "selfplay_data";
    std::string sp_provider = "cpu";  // "cpu" or "cuda" (CUDA EP needs a -Duse_cuda build)
    // Self-play search hyperparameters (tunable).
    float sp_noise_eps = 0.25f, sp_noise_alpha = 0.3f, sp_policy_temp = 1.0f, sp_cpuct = -1.0f;
    std::string sp_start_fen;  // empty=default startpos; a FEN; or a path to a file of FENs
    // Early resignation (plan A5). Threshold <= -1.0 (the default) disables it.
    float sp_resign_threshold = -2.0f, sp_no_resign_frac = 0.10f;
    int sp_resign_consecutive = 3, sp_resign_earliest = 0;
    std::vector<std::pair<std::string, std::string>> sp_search_opts;  // --search-opt k=v (T8.3/#4b)
    // Arena (model-vs-model evaluation) options.
    bool arena_mode = false;
    std::string arena_a, arena_b;
    for (int i = 1; i < argc; ++i) {
        if (std::string(argv[i]) == "--selfplay") {
            selfplay_mode = true;
        } else if (std::string(argv[i]) == "--games" && i + 1 < argc) {
            sp_games = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--out" && i + 1 < argc) {
            sp_out = argv[++i];
        } else if (std::string(argv[i]) == "--visits" && i + 1 < argc) {
            sp_visits = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--parallel" && i + 1 < argc) {
            sp_parallel = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--threads-per-game" && i + 1 < argc) {
            sp_threads_per_game = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--max-moves" && i + 1 < argc) {
            sp_max_moves = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--temp-cutoff" && i + 1 < argc) {
            sp_temp_cutoff = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--backend-threads" && i + 1 < argc) {
            sp_backend_threads = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--provider" && i + 1 < argc) {
            sp_provider = argv[++i];
        } else if (std::string(argv[i]) == "--fixed-batch" && i + 1 < argc) {
            sp_fixed_batch = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--noise-epsilon" && i + 1 < argc) {
            sp_noise_eps = static_cast<float>(std::atof(argv[++i]));
        } else if (std::string(argv[i]) == "--noise-alpha" && i + 1 < argc) {
            sp_noise_alpha = static_cast<float>(std::atof(argv[++i]));
        } else if (std::string(argv[i]) == "--policy-temp" && i + 1 < argc) {
            sp_policy_temp = static_cast<float>(std::atof(argv[++i]));
        } else if (std::string(argv[i]) == "--cpuct" && i + 1 < argc) {
            sp_cpuct = static_cast<float>(std::atof(argv[++i]));
        } else if (std::string(argv[i]) == "--start-fen" && i + 1 < argc) {
            sp_start_fen = argv[++i];
        } else if (std::string(argv[i]) == "--resign-threshold" && i + 1 < argc) {
            sp_resign_threshold = static_cast<float>(std::atof(argv[++i]));
        } else if (std::string(argv[i]) == "--resign-consecutive" && i + 1 < argc) {
            sp_resign_consecutive = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--resign-earliest-move" && i + 1 < argc) {
            sp_resign_earliest = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--search-opt" && i + 1 < argc) {
            std::string kv = argv[++i];                    // "name=value"
            auto eq = kv.find('=');
            if (eq != std::string::npos) sp_search_opts.emplace_back(kv.substr(0, eq), kv.substr(eq + 1));
        } else if (std::string(argv[i]) == "--no-resign-frac" && i + 1 < argc) {
            sp_no_resign_frac = static_cast<float>(std::atof(argv[++i]));
        } else if (std::string(argv[i]) == "--arena") {
            arena_mode = true;
        } else if (std::string(argv[i]) == "--model-a" && i + 1 < argc) {
            arena_a = argv[++i];
        } else if (std::string(argv[i]) == "--model-b" && i + 1 < argc) {
            arena_b = argv[++i];
        } else if (std::string(argv[i]) == "--weights" && i + 1 < argc) {
            weights_file = argv[++i];
        } else if (std::string(argv[i]) == "--test-ep") {
            test_ep_mode = true;
        } else if (std::string(argv[i]) == "--test-board") {
            test_board_mode = true;
        } else if (std::string(argv[i]) == "--test-policy") {
            test_policy_mode = true;
        } else if (std::string(argv[i]) == "--test-trainingdata") {
            test_trainingdata_mode = true;
        } else if (std::string(argv[i]) == "--test-extract") {
            test_extract_mode = true;
        } else if (std::string(argv[i]) == "--test-selfplay") {
            test_selfplay_mode = true;
        } else if (std::string(argv[i]) == "--emit-roundtrip") {
            emit_roundtrip_mode = true;
            if (i + 1 < argc && argv[i + 1][0] != '-') rt_prefix = argv[++i];
        } else if (std::string(argv[i]) == "--test-perft") {
            test_perft_mode = true;
        } else if (std::string(argv[i]) == "--test-bits") {
            test_bits_mode = true;
        } else if (std::string(argv[i]) == "--test-rules") {
            test_rules_mode = true;
        } else if (std::string(argv[i]) == "--test-adapter") {
            test_adapter_mode = true;
        } else if (std::string(argv[i]) == "--test-nn") {
            test_nn_mode = true;
        } else if (std::string(argv[i]) == "--test-mcts") {
            test_mcts_mode = true;
            if (i + 1 < argc && argv[i + 1][0] != '-') {
                weights_file = argv[i + 1];
            }
        } else if (std::string(argv[i]) == "--uci-nn") {
            uci_nn_mode = true;
        } else if (std::string(argv[i]) == "--test-uci") {
            test_uci_mode = true;
        } else if (std::string(argv[i]) == "--test-encoder") {
            test_encoder_mode = true;
        } else if (std::string(argv[i]) == "--play") {
            play_mode = true;
        } else if (std::string(argv[i]) == "--play-black") {
            play_mode = true; play_human_white = false;
        }
    }

    std::cout << engine_info() << " (Custom Variant Engine)" << std::endl;

    pieceMap.init();
    variants.init();
    CommandLine::init(argc, argv);
    UCI::init(Options);
    Tune::init();
    PSQT::init(variants.find(Options["UCI_Variant"])->second);
    Bitboards::init();
    Position::init();
    Bitbases::init();
    Endgames::init();
    Threads.set(size_t(Options["Threads"]));
    Search::clear(); // After threads are up
    Eval::NNUE::init();

    if (test_ep_mode) {
        run_ep_tests();
    } else if (test_board_mode) {
        run_board_tests();
    } else if (test_policy_mode) {
        run_policy_tests();
    } else if (test_trainingdata_mode) {
        run_trainingdata_tests();
    } else if (test_extract_mode) {
        run_extract_tests(weights_file);
    } else if (test_selfplay_mode) {
        run_selfplay_tests(weights_file);
    } else if (emit_roundtrip_mode) {
        run_roundtrip_emit(rt_prefix);
    } else if (test_perft_mode) {
        run_perft_tests();
    } else if (test_bits_mode) {
        run_bits_tests();
    } else if (test_rules_mode) {
        run_rules_tests();
    } else if (test_adapter_mode) {
        run_adapter_tests();
    } else if (test_nn_mode) {
        run_nn_tests();
    } else if (test_uci_mode) {
        run_uci_tests();
    } else if (test_encoder_mode) {
        run_encoder_tests();
    } else if (uci_nn_mode) {
        run_uci_nn(weights_file, sp_provider, sp_fixed_batch);
    } else if (play_mode) {
        run_play(weights_file, sp_provider, sp_fixed_batch, sp_visits, play_human_white);
    } else if (arena_mode) {
        if (arena_a.empty() || arena_b.empty()) {
            std::cerr << "[arena] need --model-a <onnx> and --model-b <onnx>" << std::endl;
            return 1;
        }
        run_arena(arena_a, arena_b, sp_games, sp_visits, sp_max_moves, sp_temp_cutoff,
                  sp_provider, sp_fixed_batch);
    } else if (test_mcts_mode) {
        run_mcts_tests(weights_file);
    } else if (selfplay_mode) {
        std::cout << "=== Self-play data generation ===" << std::endl;
        setup_custom_variant();
        const std::string fen =
            "vrhabkberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHABKBERV w BIbi - 7+7 0 1";

        lczero::OptionsParser parser;
        lczero::classic::SearchParams::Populate(&parser);
        parser.GetMutableDefaultsOptions()->Set<float>(lczero::SharedBackendParams::kPolicySoftmaxTemp, sp_policy_temp);
        parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kHistoryFill, "no");
        parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kNoiseEpsilonId, sp_noise_eps);
        parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kNoiseAlphaId, sp_noise_alpha);
        if (sp_cpuct >= 0.0f)
            parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kCpuctId, sp_cpuct);
        // T8.3 #4b: arbitrary lc0 search params for self-play via --search-opt name=value.
        for (const auto& kv : sp_search_opts) {
            if (ApplySearchOpt(parser.GetMutableDefaultsOptions(), kv.first, kv.second))
                std::cout << "[selfplay] search-opt " << kv.first << "=" << kv.second << std::endl;
            else
                std::cout << "[selfplay] WARNING: unknown --search-opt '" << kv.first << "' (ignored)" << std::endl;
        }
        parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kWeightsId, weights_file);
        // Backend options. CPU: game-level parallelism + low intra-op threads.
        // CUDA (Colab GPU, needs a -Duse_cuda build): provider=cuda + fixed_batch.
        std::string sp_backend_opts;
        if (sp_provider == "cuda") {
            sp_backend_opts = "provider=cuda,fixed_batch=" + std::to_string(std::max(1, sp_fixed_batch));
        } else {
            sp_backend_opts = "threads=" + std::to_string(std::max(1, sp_backend_threads));
        }
        parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kBackendOptionsId, sp_backend_opts);
        std::cout << "[selfplay] backend: " << sp_backend_opts << std::endl;
        const lczero::OptionsDict& sp_options = parser.GetOptionsDict();

        std::unique_ptr<lczero::Backend> backend;
        try {
            auto raw_backend = std::make_unique<lczero::OnnxBackend>();
            raw_backend->UpdateConfiguration(sp_options);
            backend = lczero::CreateMemCache(std::move(raw_backend), sp_options);
        } catch (const std::exception& e) {
            std::cerr << "[selfplay] FATAL: could not load backend: " << e.what() << std::endl;
            Threads.set(0);
            return 1;
        }

        lczero::SelfPlayConfig cfg;
        cfg.start_fen = fen;  // default = startpos
        if (!sp_start_fen.empty()) {
            std::ifstream ff(sp_start_fen);
            if (ff) {  // an opening book: one FEN per line (# = comment)
                std::string line;
                while (std::getline(ff, line)) {
                    if (!line.empty() && line[0] != '#') cfg.start_fens.push_back(line);
                }
                std::cout << "[selfplay] opening book: " << cfg.start_fens.size()
                          << " FENs from " << sp_start_fen << std::endl;
            } else {
                cfg.start_fen = sp_start_fen;  // a single FEN string
            }
        }
        cfg.out_dir = sp_out;
        cfg.num_games = sp_games;
        cfg.visits = sp_visits;
        cfg.max_moves = sp_max_moves;
        cfg.temp_cutoff_ply = sp_temp_cutoff;
        cfg.parallel = sp_parallel;
        cfg.threads_per_game = sp_threads_per_game;
        cfg.resign_threshold = sp_resign_threshold;
        cfg.resign_consecutive = sp_resign_consecutive;
        cfg.resign_earliest_move = sp_resign_earliest;
        cfg.no_resign_frac = sp_no_resign_frac;
        if (sp_resign_threshold > -1.0f) {
            std::cout << "[selfplay] resign: best_q<=" << sp_resign_threshold
                      << " for " << sp_resign_consecutive << " moves, no-resign frac="
                      << sp_no_resign_frac << std::endl;
        }
        lczero::RunSelfPlay(cfg, backend.get(), sp_options);
    } else {
        UCI::loop(argc, argv);
    }

    Threads.set(0);
    variants.clear_all();
    pieceMap.clear_all();
    delete XBoard::stateMachine;
    return 0;
}
