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
#include "app/cli.h"
#include "app/selfplay_mode.h"

using namespace Stockfish;

int run_selfplay(const EngineOptions& o) {
        std::cout << "=== Self-play data generation ===" << std::endl;
        setup_custom_variant();
        const std::string fen =
            "vrhbakberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHBAKBERV w BIbi - 7+7 0 1";

        lczero::OptionsParser parser;
        lczero::classic::SearchParams::Populate(&parser);
        parser.GetMutableDefaultsOptions()->Set<float>(lczero::SharedBackendParams::kPolicySoftmaxTemp, o.sp_policy_temp);
        parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kHistoryFill, "no");
        parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kNoiseEpsilonId, o.sp_noise_eps);
        parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kNoiseAlphaId, o.sp_noise_alpha);
        if (o.sp_cpuct >= 0.0f)
            parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kCpuctId, o.sp_cpuct);
        // T8.3 #4b: arbitrary lc0 search params for self-play via --search-opt name=value.
        for (const auto& kv : o.sp_search_opts) {
            if (ApplySearchOpt(parser.GetMutableDefaultsOptions(), kv.first, kv.second))
                std::cout << "[selfplay] search-opt " << kv.first << "=" << kv.second << std::endl;
            else
                std::cout << "[selfplay] WARNING: unknown --search-opt '" << kv.first << "' (ignored)" << std::endl;
        }
        parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kWeightsId, o.weights_file);
        // Backend options. CPU: game-level parallelism + low intra-op threads.
        // CUDA (Colab GPU, needs a -Duse_cuda build): provider=cuda + fixed_batch.
        std::string sp_backend_opts;
        if (o.sp_provider == "cuda") {
            sp_backend_opts = "provider=cuda,fixed_batch=" + std::to_string(std::max(1, o.sp_fixed_batch));
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
            backend = lczero::CreateMemCache(std::move(raw_backend), sp_options);
        } catch (const std::exception& e) {
            std::cerr << "[selfplay] FATAL: could not load backend: " << e.what() << std::endl;
            Threads.set(0);
            return 1;
        }

        lczero::SelfPlayConfig cfg;
        cfg.start_fen = fen;  // default = startpos
        if (!o.sp_start_fen.empty()) {
            std::ifstream ff(o.sp_start_fen);
            if (ff) {  // an opening book: one FEN per line (# = comment)
                std::string line;
                while (std::getline(ff, line)) {
                    if (!line.empty() && line[0] != '#') cfg.start_fens.push_back(line);
                }
                std::cout << "[selfplay] opening book: " << cfg.start_fens.size()
                          << " FENs from " << o.sp_start_fen << std::endl;
            } else {
                cfg.start_fen = o.sp_start_fen;  // a single FEN string
            }
        }
        cfg.out_dir = o.sp_out;
        cfg.num_games = o.sp_games;
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
