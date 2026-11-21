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
#include "app/backend_factory.h"
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
        const std::string fen = lczero::ChessBoard::kStartposFen;

        // Start positions, checked before the network is loaded (fail fast).
        std::string start_fen = fen;  // default = startpos
        std::vector<std::string> start_fens;
        if (!o.sp_start_fen.empty()) {
            // Every start position is checked before the first game (CheckStartFen:
            // Fairy-Stockfish itself accepts a FEN without "8+8" as 1+1, etc.).
            // The same reader serves --arena (variant_setup.cc).
            const std::string why = LoadStartFens(o.sp_start_fen, &start_fens, &start_fen);
            if (!why.empty()) {
                std::cerr << "[selfplay] FATAL: " << why << std::endl;
                Threads.set(0);
                return 1;
            }
            if (!start_fens.empty())
                std::cout << "[selfplay] opening book: " << start_fens.size()
                          << " FENs from " << o.sp_start_fen << std::endl;
        }

        lczero::OptionsParser parser;
        lczero::classic::SearchParams::Populate(&parser);
        parser.GetMutableDefaultsOptions()->Set<float>(lczero::SharedBackendParams::kPolicySoftmaxTemp, o.sp_policy_temp);
        parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kHistoryFill, "always");  // ghi lai cho dung; mang luon ma hoa ALWAYS (onnx_backend.cc)
        parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kNoiseEpsilonId, o.sp_noise_eps);
        parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kNoiseAlphaId, o.sp_noise_alpha);
        // Self-play search parameters of lc0's own self-play (upstream/lc0
        // src/selfplay/tournament.cc), not the UCI defaults, which are tuned for
        // playing strength (2026-09-28, owner's decision):
        //   cpuct 1.5 FIXED for the full searches (owner's choice 2026-11-20; it was 1.3, lc0
        //     self-play 1.2; the shallow searches of PCR use --fast-cpuct, 1.25), cpuct-factor 0
        //     -- UCI: 1.745 growing with visits (factor 3.894);
        //   fpu reduction 0 (an unvisited move starts at its parent's Q) -- UCI 0.33;
        //   two-fold-draws off: the variant's rule is THREEFOLD repetition, a
        //     search scoring the first repetition as a draw skews the q targets;
        //   sticky-endgames off;
        //   task-workers 0: the search's helper threads spin for work and take
        //     the 2 vCPUs from the other games (T4, 16 games aggregated: +13%).
        // --cpuct and --search-opt still override.
        auto* sd = parser.GetMutableDefaultsOptions();
        sd->Set<float>(lczero::classic::BaseSearchParams::kCpuctId, o.sp_cpuct >= 0.0f ? o.sp_cpuct : 1.5f);
        sd->Set<float>(lczero::classic::BaseSearchParams::kCpuctFactorId, 0.0f);
        sd->Set<float>(lczero::classic::BaseSearchParams::kFpuValueId, 0.0f);
        sd->Set<bool>(lczero::classic::BaseSearchParams::kTwoFoldDrawsId, false);
        sd->Set<bool>(lczero::classic::BaseSearchParams::kStickyEndgamesId, false);
        sd->Set<int>(lczero::classic::BaseSearchParams::kTaskWorkersPerSearchWorkerId, 0);
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
        if (o.sp_provider == "cuda" || o.sp_provider == "tensorrt" || o.sp_provider == "fzcuda") {
            sp_backend_opts = "provider=" + o.sp_provider + ",fixed_batch=" + std::to_string(o.sp_fixed_batch);
            for (const auto& kv : o.sp_cuda_opts) sp_backend_opts += ",cuda." + kv;
            for (const auto& kv : o.sp_trt_opts) sp_backend_opts += ",trt." + kv;
            if (!o.sp_extra_batches.empty()) {
                sp_backend_opts += ",extra_batches=";
                for (size_t i = 0; i < o.sp_extra_batches.size(); ++i)
                    sp_backend_opts += (i ? ":" : "") + std::to_string(o.sp_extra_batches[i]);
            }
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
        // Options of the shallow searches of PCR: a child of sp_options (so --search-opt and every
        // other default apply to them as well) that overrides only c_puct and the noise epsilon.
        // Declared here, after sp_options and before the games, so it outlives every search.
        lczero::OptionsDict fast_options(&sp_options);
        fast_options.Set<float>(lczero::classic::BaseSearchParams::kCpuctId, o.sp_fast_cpuct);
        fast_options.Set<float>(lczero::classic::BaseSearchParams::kNoiseEpsilonId, o.sp_fast_noise_eps);

        std::unique_ptr<lczero::Backend> backend;
        lczero::BatchingBackend* batcher = nullptr;  // owned by `backend`
        try {
            std::unique_ptr<lczero::Backend> inner = make_network_backend(sp_options);
            // A4: gom batch NN xuyên nhiều ván -> 1 inference đầy hơn (tốt cho GPU).
            // Chèn GIỮA cache và Onnx: ZeroHeapCache -> BatchingBackend -> OnnxBackend.
            if (o.sp_batch_aggregate) {
                // Dynamic producer count: RunSelfPlay registers parallel x
                // threads_per_game producers and removes a worker's threads when
                // it stops taking games (soft-stop tail), so the last batches do
                // not each wait out the timeout for games that already ended.
                const int producers =
                    std::max(1, o.sp_parallel) * std::max(1, o.sp_threads_per_game);
                auto batching = std::make_unique<lczero::BatchingBackend>(
                    std::move(inner), /*expected_producers=dynamic*/ 0, o.sp_batch_timeout_us);
                batcher = batching.get();
                inner = std::move(batching);
                std::cout << "[selfplay] batch-aggregate ON (producers=" << producers
                          << " dong, timeout=" << o.sp_batch_timeout_us << "us)" << std::endl;
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
        cfg.plan.full_visits = o.sp_visits;
        cfg.plan.fast_visits = o.sp_fast_visits;
        cfg.plan.fast_prob = o.sp_fast_prob;
        cfg.plan.temperature = o.sp_temperature;
        cfg.plan.fast_options = &fast_options;
        cfg.max_moves = o.sp_max_moves;
        cfg.parallel = o.sp_parallel;
        cfg.threads_per_game = o.sp_threads_per_game;
        cfg.resign_threshold = o.sp_resign_threshold;
        cfg.resign_consecutive = o.sp_resign_consecutive;
        cfg.resign_earliest_move = o.sp_resign_earliest;
        cfg.no_resign_frac = o.sp_no_resign_frac;
        cfg.show_nps = o.sp_show_nps;
        if (batcher) {
            cfg.producer_enter = [batcher] { batcher->ProducerEnter(); };
            cfg.producer_leave = [batcher] { batcher->ProducerLeave(); };
        }
        {   // what every move will be searched and chosen with (one line the log keeps)
            const float full_cpuct = sp_options.Get<float>(lczero::classic::BaseSearchParams::kCpuctId);
            const float full_eps = sp_options.Get<float>(lczero::classic::BaseSearchParams::kNoiseEpsilonId);
            std::cout << "[selfplay] search: PUCT, full " << o.sp_visits << " playouts (cpuct " << full_cpuct
                      << ", noise eps " << full_eps << ")";
            if (o.sp_fast_prob > 0.0f)
                std::cout << "; PCR: " << 100.0 * o.sp_fast_prob << "% of the moves shallow, "
                          << o.sp_fast_visits << " playouts (cpuct " << o.sp_fast_cpuct
                          << ", noise eps " << o.sp_fast_noise_eps << "), policy target not trained";
            else
                std::cout << "; PCR off";
            std::cout << "; every move drawn with temperature " << o.sp_temperature << std::endl;
        }
        if (o.sp_resign_threshold > -1.0f) {
            std::cout << "[selfplay] resign: best_q<=" << o.sp_resign_threshold
                      << " for " << o.sp_resign_consecutive << " moves, no-resign frac="
                      << o.sp_no_resign_frac << std::endl;
        }
        lczero::RunSelfPlay(cfg, backend.get(), sp_options);
    return 0;
}
