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
#include "neural/batching_backend.h"
#include "utils/random.h"
#include "chess/callbacks.h"
#include "app/variant_setup.h"
#include "app/search_opts.h"
#include "app/cli.h"
#include "app/selfplay_mode.h"

using namespace Stockfish;

int run_selfplay(const EngineOptions& o) {
        std::cout << "=== Self-play data generation ===" << std::endl;
        setup_custom_variant();
        const std::string fen =
            "vrhbqkberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHBQKBERV w BIbi - 8+8 0 1";

        // Start positions, checked before the network is loaded (fail fast).
        std::string start_fen = fen;  // default = startpos
        std::vector<std::string> start_fens;
        if (!o.sp_start_fen.empty()) {
            // Every start position is checked before the first game (CheckStartFen:
            // Fairy-Stockfish itself accepts a FEN without "8+8" as 1+1, etc.).
            auto trim = [](std::string s) {
                const auto b = s.find_first_not_of(" \t\r\n");
                if (b == std::string::npos) return std::string();
                return s.substr(b, s.find_last_not_of(" \t\r\n") - b + 1);
            };
            std::ifstream ff(o.sp_start_fen);
            if (ff) {  // an opening book: one FEN per line (# = comment)
                std::string line;
                for (int line_no = 1; std::getline(ff, line); ++line_no) {
                    line = trim(line);   // a book saved on Windows ends its lines in \r
                    if (line.empty() || line[0] == '#') continue;
                    const std::string why = CheckStartFen(line);
                    if (!why.empty()) {
                        std::cerr << "[selfplay] FATAL: " << o.sp_start_fen << ":" << line_no
                                  << ": " << why << "\n  " << line << std::endl;
                        Threads.set(0);
                        return 1;
                    }
                    start_fens.push_back(line);
                }
                if (start_fens.empty()) {
                    std::cerr << "[selfplay] FATAL: no FEN in " << o.sp_start_fen << std::endl;
                    Threads.set(0);
                    return 1;
                }
                std::cout << "[selfplay] opening book: " << start_fens.size()
                          << " FENs from " << o.sp_start_fen << std::endl;
            } else {
                start_fen = trim(o.sp_start_fen);  // a single FEN string
                const std::string why = CheckStartFen(start_fen);
                if (!why.empty()) {
                    std::cerr << "[selfplay] FATAL: --start-fen is neither a readable file nor a "
                                 "valid FEN: " << why << "\n  " << start_fen << std::endl;
                    Threads.set(0);
                    return 1;
                }
            }
        }

        lczero::OptionsParser parser;
        lczero::classic::SearchParams::Populate(&parser);
        parser.GetMutableDefaultsOptions()->Set<float>(lczero::SharedBackendParams::kPolicySoftmaxTemp, o.sp_policy_temp);
        parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kHistoryFill, "no");
        parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kNoiseEpsilonId, o.sp_noise_eps);
        parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kNoiseAlphaId, o.sp_noise_alpha);
        if (o.sp_cpuct >= 0.0f)
            parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kCpuctId, o.sp_cpuct);
        // No speculative prefetch by default (lc0's default is 32). Prefetch only
        // fills the NN cache with guesses; it never changes what the search
        // computes. Measured 2026-09-23 on a Colab T4: +37% playouts/s without it
        // (the GPU was saturated either way; prefetch spent ~27% of its slots on
        // guesses and padding). `--search-opt max-prefetch=N` still overrides.
        parser.GetMutableDefaultsOptions()->Set<int>(lczero::classic::SearchParams::kMaxPrefetchBatchId, 0);
        // T8.3 #4b: arbitrary lc0 search params for self-play via --search-opt name=value.
        // One that cannot be applied stops the run (it used to be a warning line
        // lost in the log, and the data was generated without it).
        for (const auto& kv : o.sp_search_opts) {
            const std::string err =
                ApplySearchOptChecked(parser.GetMutableDefaultsOptions(), kv.first, kv.second);
            if (!err.empty()) {
                std::cerr << "[selfplay] FATAL: " << err << std::endl;
                Threads.set(0);
                return 1;
            }
            std::cout << "[selfplay] search-opt " << kv.first << "=" << kv.second << std::endl;
        }
        parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kWeightsId, o.weights_file);
        // Backend options. CPU: game-level parallelism + low intra-op threads.
        // CUDA (Colab GPU, needs a -Duse_cuda build): provider=cuda + fixed_batch.
        std::string sp_backend_opts;
        if (o.sp_provider == "cuda") {
            sp_backend_opts = "provider=cuda,fixed_batch=" + std::to_string(std::max(1, o.sp_fixed_batch));
        } else if (o.sp_provider == "dml") {
            // Windows iGPU (needs a -Duse_dml build). The explicit provider= key is
            // REQUIRED or onnxruntime silently runs on CPU.
            sp_backend_opts = "provider=dml,threads=" + std::to_string(std::max(1, o.sp_backend_threads));
        } else {
            sp_backend_opts = "threads=" + std::to_string(std::max(1, o.sp_backend_threads));
        }
        parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kBackendOptionsId, sp_backend_opts);
        std::cout << "[selfplay] backend: " << sp_backend_opts << std::endl;
        const lczero::OptionsDict& sp_options = parser.GetOptionsDict();

        std::unique_ptr<lczero::Backend> backend;
        try {
            auto raw_backend = std::make_unique<lczero::OnnxBackend>();
            raw_backend->UpdateConfiguration(sp_options);
            std::unique_ptr<lczero::Backend> inner = std::move(raw_backend);
            // A4: gom batch NN xuyên nhiều ván -> 1 inference đầy hơn (tốt cho GPU).
            // Chèn GIỮA cache và Onnx: ZeroHeapCache -> BatchingBackend -> OnnxBackend.
            if (o.sp_batch_aggregate) {
                const int producers =
                    std::max(1, o.sp_parallel) * std::max(1, o.sp_threads_per_game);
                inner = std::make_unique<lczero::BatchingBackend>(
                    std::move(inner), producers, o.sp_batch_timeout_us);
                std::cout << "[selfplay] batch-aggregate ON (producers=" << producers
                          << ", timeout=" << o.sp_batch_timeout_us << "us)" << std::endl;
                if (o.sp_provider == "cpu") {
                    std::cout << "[selfplay] NOTE: --batch-aggregate is a GPU optimization; "
                                 "on CPU it serializes inference onto one thread and is SLOWER. "
                                 "Use it with --provider cuda/dml." << std::endl;
                }
            }
            backend = lczero::CreateMemCache(std::move(inner), sp_options);
        } catch (const std::exception& e) {
            std::cerr << "[selfplay] FATAL: could not load backend: " << e.what() << std::endl;
            Threads.set(0);
            return 1;
        }

        lczero::SelfPlayConfig cfg;
        cfg.start_fen = start_fen;
        cfg.start_fens = std::move(start_fens);
        cfg.out_dir = o.sp_out;
        cfg.num_games = o.sp_games;
        cfg.max_seconds = o.sp_max_seconds;
        cfg.stop_file = o.sp_stop_file;
        cfg.visits = o.sp_visits;
        cfg.max_moves = o.sp_max_moves;
        cfg.temp_cutoff_ply = o.sp_temp_cutoff;
        cfg.parallel = o.sp_parallel;
        cfg.threads_per_game = o.sp_threads_per_game;
        cfg.resign_threshold = o.sp_resign_threshold;
        cfg.resign_consecutive = o.sp_resign_consecutive;
        cfg.resign_earliest_move = o.sp_resign_earliest;
        cfg.no_resign_frac = o.sp_no_resign_frac;
        cfg.show_nps = o.sp_show_nps;
        if (o.sp_resign_threshold > -1.0f) {
            std::cout << "[selfplay] resign: best_q<=" << o.sp_resign_threshold
                      << " for " << o.sp_resign_consecutive << " moves, no-resign frac="
                      << o.sp_no_resign_frac << std::endl;
        }
        lczero::RunSelfPlay(cfg, backend.get(), sp_options);
    return 0;
}
