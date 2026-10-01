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
#include <filesystem>
#include <memory>
#include <map>
#include <functional>
#include <algorithm>
#include "search/classic/search.h"
#include "search/classic/params.h"
#include "neural/backend.h"
#include "neural/shared_params.h"
#include "neural/onnx_backend.h"
#include "neural/batching_backend.h"
#include "neural/zero_heap_cache.h"
#include "utils/random.h"
#include "chess/callbacks.h"
#include "app/arena_mode.h"
#include "app/cli.h"
#include "app/variant_setup.h"
#include "app/backend_factory.h"
#include "app/search_support.h"
#include "app/uci_coords.h"
#include "app/search_opts.h"

using namespace Stockfish;

int run_arena(const EngineOptions& o) {
    if (o.arena_a.empty() || o.arena_b.empty()) {
        std::cerr << "[arena] need --model-a <onnx> and --model-b <onnx>" << std::endl;
        return 1;
    }
    const std::string& model_a = o.arena_a;
    const std::string& model_b = o.arena_b;
    const int games = o.sp_games;
    const int visits = o.sp_visits;
    const int max_moves = o.sp_max_moves;
    const int temp_cutoff = o.sp_temp_cutoff;

    std::cout << "\n=== ARENA: A=" << model_a << "  vs  B=" << model_b
              << "  (" << games << " games, visits=" << visits
              << ", provider=" << o.sp_provider << ") ===" << std::endl;
    setup_custom_variant();
    const std::string fen =
        "vrhbqkberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHBQKBERV w BIbi - 8+8 0 1";

    // Backend options per provider (same selection as self-play / --uci-nn).
    // CUDA (Colab, needs -Duse_cuda): fixed batch. DML (Windows iGPU, needs
    // -Duse_dml): the explicit provider= key is REQUIRED or onnxruntime silently
    // runs on CPU. CPU: just intra-op threads.
    std::string bopts;
    if (o.sp_provider == "cuda" || o.sp_provider == "tensorrt") {
        bopts = "provider=" + o.sp_provider + ",fixed_batch=" + std::to_string(o.sp_fixed_batch);
        for (const auto& kv : o.sp_cuda_opts) bopts += ",cuda." + kv;
        for (const auto& kv : o.sp_trt_opts) bopts += ",trt." + kv;
    } else if (o.sp_provider == "dml") {
        bopts = "provider=dml,threads=" + std::to_string(std::max(1, o.sp_backend_threads));
    } else {
        bopts = "threads=" + std::to_string(std::max(1, o.sp_backend_threads));
    }
    std::cout << "[arena] backend: " << bopts << std::endl;

    auto build_opts = [&](lczero::OptionsParser& parser, const std::string& weights) {
        lczero::classic::SearchParams::Populate(&parser);
        parser.GetMutableDefaultsOptions()->Set<float>(lczero::SharedBackendParams::kPolicySoftmaxTemp, o.sp_policy_temp);
        parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kHistoryFill, "no");
        parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kNoiseEpsilonId, 0.0f);
        if (o.sp_cpuct >= 0.0f)
            parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kCpuctId, o.sp_cpuct);
        parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kWeightsId, weights);
        parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kBackendOptionsId, bopts);
        // --search-opt applies to BOTH nets (arena used to ignore it silently).
        std::string err;
        for (const auto& kv : o.sp_search_opts) {
            err = ApplySearchOptChecked(parser.GetMutableDefaultsOptions(), kv.first, kv.second);
            if (!err.empty()) break;
        }
        return err;
    };

    lczero::OptionsParser pa, pb;
    const std::string opt_error = build_opts(pa, model_a);
    build_opts(pb, model_b);
    if (!opt_error.empty()) {
        std::cerr << "[arena] " << opt_error << std::endl;
        return 1;
    }
    for (const auto& kv : o.sp_search_opts)
        std::cout << "[arena] search-opt " << kv.first << "=" << kv.second << " (both nets)" << std::endl;
    const lczero::OptionsDict& opts_a = pa.GetOptionsDict();
    const lczero::OptionsDict& opts_b = pb.GetOptionsDict();

    // --batch-aggregate (as self-play): each net gets its own BatchingBackend that
    // gathers the leaves of every game currently searching with that net into one
    // Run (cache -> BatchingBackend -> Onnx). Which games use which net changes
    // every move, so the producer count is dynamic: each search is bracketed by
    // ProducerEnter/Leave on its net's batcher.
    std::unique_ptr<lczero::Backend> ba, bb;
    lczero::BatchingBackend* agg_a = nullptr;
    lczero::BatchingBackend* agg_b = nullptr;
    auto make_backend = [&](const lczero::OptionsDict& opts, lczero::BatchingBackend** agg) {
        if (!o.sp_batch_aggregate) return arena_make_backend(opts);
        auto raw = std::make_unique<lczero::OnnxBackend>();
        raw->UpdateConfiguration(opts);
        auto batching = std::make_unique<lczero::BatchingBackend>(
            std::move(raw), /*expected_producers=dynamic*/ 0, o.sp_batch_timeout_us);
        *agg = batching.get();
        return std::unique_ptr<lczero::Backend>(
            lczero::CreateMemCache(std::move(batching), opts));
    };
    try {
        ba = make_backend(opts_a, &agg_a);
        bb = make_backend(opts_b, &agg_b);
        if (o.sp_batch_aggregate)
            std::cout << "[arena] batch-aggregate ON (per net, timeout="
                      << o.sp_batch_timeout_us << "us)" << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "[arena] backend load failed: " << e.what() << std::endl;
        std::exit(1);
    }

    // --parallel N: N games at once (like self-play), sharing the two backends. One game = one
    // search per move, so alone it feeds the GPU small batches; N concurrent games fill them
    // (self-play --parallel 4 ~2750 nps vs sequential arena ~1600 on T4). Game g still has A as
    // White iff g is even, so colors stay balanced (with an even game count) whatever the order
    // games finish in. Results/printing under one mutex; totals are exact, not sampled.
    const int workers = std::max(1, std::min(o.sp_parallel, games));
    int a_wins = 0, b_wins = 0, draws = 0, done = 0;
    const bool show_nps = o.sp_show_nps;          // --show-nps: aggregate MCTS NPS
    std::atomic<int64_t> total_nodes{0};
    // Throughput breakdown (B4): time inside Search::RunBlocking vs building the
    // Search, summed over workers; and the tail after the first worker ran out
    // of games (fewer than `workers` games feeding the GPU).
    std::atomic<int64_t> search_us{0}, setup_us{0}, searches{0};
    std::atomic<int64_t> tail_start_us{-1}, nodes_at_tail{0};
    std::atomic<int> next_game{0};
    std::mutex mu;
    const auto arena_start = std::chrono::steady_clock::now();
    if (workers > 1) std::cout << "[arena] " << workers << " games in parallel" << std::endl;

    // Soft stop, as self-play: --max-seconds (wall clock) or --stop-file (the phone's loop
    // when several machines together reached the target) only stop taking NEW games; games
    // in flight finish and count. Checked once per game, never in the search.
    std::atomic<bool> stopped_by_time{false}, stopped_by_file{false};
    if (o.sp_max_seconds > 0.0) std::cout << "[arena] gioi han thoi gian: " << o.sp_max_seconds << "s" << std::endl;
    if (!o.sp_stop_file.empty()) std::cout << "[arena] dung mem khi co tep: " << o.sp_stop_file << std::endl;
    auto should_stop = [&]() {
        if (o.sp_max_seconds > 0.0 &&
            std::chrono::duration<double>(std::chrono::steady_clock::now() - arena_start).count() >=
                o.sp_max_seconds) {
            if (!stopped_by_time.exchange(true)) {
                std::lock_guard<std::mutex> lk(mu);
                std::cout << "[arena] Dat nguong thoi gian " << o.sp_max_seconds
                          << "s -> ngung nhan van moi (da xong " << done
                          << " van, cac van dang chay se hoan tat)." << std::endl;
            }
            return true;
        }
        std::error_code fe;
        if (!o.sp_stop_file.empty() && std::filesystem::exists(o.sp_stop_file, fe)) {
            if (!stopped_by_file.exchange(true)) {
                std::lock_guard<std::mutex> lk(mu);
                std::cout << "[arena] Co tep dung " << o.sp_stop_file
                          << " -> ngung nhan van moi (da xong " << done
                          << " van, cac van dang chay se hoan tat)." << std::endl;
            }
            return true;
        }
        return false;
    };

    auto worker = [&]() {
        auto tree = std::make_unique<lczero::classic::NodeTree>();
        while (true) {
            if (should_stop()) break;
            const int g = next_game.fetch_add(1);
            if (g >= games) break;
            const bool a_is_white = (g % 2 == 0);        // alternate colors for fairness
            tree->ResetToPosition(fen, {});
            lczero::GameResult result = lczero::GameResult::UNDECIDED;
            std::string moves_str;                       // --arena-moves: UCI move list
            int64_t game_nodes = 0;

            for (int ply = 0; ply < max_moves; ++ply) {
                const bool white_to_move = !tree->IsBlackToMove();
                const bool a_to_move = (white_to_move == a_is_white);
                lczero::Backend* backend = a_to_move ? ba.get() : bb.get();
                const lczero::OptionsDict& sopts = a_to_move ? opts_a : opts_b;

                tree->TrimTreeAtHead();  // fresh search: no stale evals from the OTHER net
                auto responder = std::make_unique<SilentUciResponder>();
                auto stopper = std::make_unique<NodeLimitStopper>(visits);
                auto start = std::chrono::steady_clock::now();
                auto search = std::make_unique<lczero::classic::Search>(
                    *tree, backend, std::move(responder), lczero::MoveList{}, start,
                    std::move(stopper), false, false, sopts, nullptr);
                lczero::BatchingBackend* agg = a_to_move ? agg_a : agg_b;
                if (agg) agg->ProducerEnter();
                const auto t_search = std::chrono::steady_clock::now();
                search->RunBlocking(1);
                const auto t_done = std::chrono::steady_clock::now();
                if (agg) agg->ProducerLeave();
                search_us.fetch_add(std::chrono::duration_cast<std::chrono::microseconds>(
                                        t_done - t_search).count());
                setup_us.fetch_add(std::chrono::duration_cast<std::chrono::microseconds>(
                                       t_search - start).count());
                searches.fetch_add(1);

                lczero::classic::Node* root = tree->GetCurrentHead();
                game_nodes += static_cast<int64_t>(root->GetN());
                lczero::classic::EdgeAndNode best;
                uint64_t total = 0, best_n = 0;
                for (const auto& e : root->Edges()) {
                    total += e.GetN();
                    if (e.GetN() >= best_n) { best_n = e.GetN(); best = e; }
                }
                if (best.GetMove().is_null()) break;

                lczero::Move played = best.GetMove();       // greedy by default
                if (ply < temp_cutoff && total > 0) {       // temperature opening for diversity
                    const double toss = lczero::Random::Get().GetDouble(static_cast<double>(total));
                    double acc = 0.0;
                    for (const auto& e : root->Edges()) {
                        acc += static_cast<double>(e.GetN());
                        if (acc > toss) { played = e.GetMove(); break; }
                    }
                }
                if (o.arena_show_moves) {
                    if ((ply % 2) == 0) moves_str += std::to_string(ply / 2 + 1) + ".";
                    moves_str += CanonicalMoveToUci(played, !white_to_move) + " ";
                }
                tree->MakeMove(played);
                result = tree->GetPositionHistory().ComputeGameResult();
                if (result != lczero::GameResult::UNDECIDED) break;
            }
            total_nodes.fetch_add(game_nodes);

            std::lock_guard<std::mutex> lk(mu);
            if (result == lczero::GameResult::WHITE_WON || result == lczero::GameResult::BLACK_WON) {
                const bool white_won = (result == lczero::GameResult::WHITE_WON);
                if (white_won == a_is_white) a_wins++; else b_wins++;
            } else {
                draws++;  // DRAW or cutoff (UNDECIDED)
            }
            ++done;
            std::cout << "  game " << done << "/" << games;
            if (workers > 1) std::cout << " (#" << (g + 1) << ")";
            std::cout << " (A plays " << (a_is_white ? "White" : "Black") << "): result="
                      << (int)result << "   [A " << a_wins << " W / " << draws << " D / "
                      << b_wins << " L]";
            if (show_nps) {
                const double secs = std::chrono::duration<double>(
                    std::chrono::steady_clock::now() - arena_start).count();
                const long nps = (secs > 0.0) ? std::lround(total_nodes.load() / secs) : 0;
                std::cout << "  | " << nps << " nps (tong)";
            }
            std::cout << std::endl;
            if (o.arena_show_moves) std::cout << "    moves: " << moves_str << std::endl;
        }
    };
    std::vector<std::thread> pool;
    pool.reserve(workers);
    std::atomic<int> done_at_tail{0};
    for (int w = 0; w < workers; ++w)
        pool.emplace_back([&] {
            worker();
            int64_t none = -1;
            const int64_t now_us = std::chrono::duration_cast<std::chrono::microseconds>(
                                       std::chrono::steady_clock::now() - arena_start).count();
            if (tail_start_us.compare_exchange_strong(none, now_us)) {
                std::lock_guard<std::mutex> lk(mu);
                done_at_tail = done;
            }
        });
    for (auto& t : pool) t.join();

    // Scored over the games actually played (fewer than --games after a soft stop).
    const double score_a = (a_wins + 0.5 * draws) / std::max(1, done);
    std::cout << "\n[arena] Finished " << done << "/" << games << " games";
    if (stopped_by_time.load()) std::cout << " (dung som do dat nguong --max-seconds)";
    else if (stopped_by_file.load()) std::cout << " (dung som do tep --stop-file)";
    std::cout << std::endl;
    std::cout << "\n=== ARENA RESULT ===" << std::endl;
    std::cout << "  A wins=" << a_wins << "  draws=" << draws << "  B wins=" << b_wins << std::endl;
    std::cout << "  A score = " << score_a << "  (>0.5 => A stronger than B)" << std::endl;
    if (show_nps) {
        const double secs = std::chrono::duration<double>(
            std::chrono::steady_clock::now() - arena_start).count();
        const long nps = (secs > 0.0) ? std::lround(total_nodes.load() / secs) : 0;
        std::cout << "  speed: " << nps << " nps (" << total_nodes.load() << " playouts in "
                  << secs << "s)" << std::endl;
    }
    // Where the time goes (same counters as the self-play summary). The NN
    // counters are global, i.e. both nets together.
    {
        const double secs = std::chrono::duration<double>(
            std::chrono::steady_clock::now() - arena_start).count();
        const auto ev = lczero::OnnxGetEvalCounters();
        const int64_t n_search = searches.load();
        std::cout << "  --- Throughput ---\n";
        if (done > 0 && secs > 0.0)
            std::cout << "  Van/gio            : " << (done * 3600.0 / secs) << "\n";
        if (ev.runs > 0 && secs > 0.0) {
            const double waste =
                ev.padded > 0 ? 100.0 * (ev.padded - ev.real) / ev.padded : 0.0;
            std::cout << "  NN eval/giay       : " << (ev.real / secs) << "\n"
                      << "  NN eval/playout    : "
                      << (total_nodes.load() > 0
                              ? static_cast<double>(ev.real) / total_nodes.load() : 0.0) << "\n"
                      << "  Run()/giay         : " << (ev.runs / secs) << "\n"
                      << "  Batch TB moi Run() : " << (static_cast<double>(ev.real) / ev.runs)
                      << "  (so lan Run: " << ev.runs << ")\n"
                      << "  Phi do pad         : " << waste << "%  ("
                      << (ev.padded - ev.real) << "/" << ev.padded << " o batch)\n";
        }
        if (n_search > 0 && secs > 0.0) {
            // Per worker: share of wall time inside RunBlocking / building the
            // Search; the rest is move selection, MakeMove, result check, waiting.
            const double wall_us = secs * 1e6 * workers;
            std::cout << "  Tim kiem (RunBlocking): " << 100.0 * search_us.load() / wall_us
                      << "% thoi gian moi luong, TB " << search_us.load() / 1000.0 / n_search
                      << " ms/nuoc (" << n_search << " nuoc)\n"
                      << "  Dung Search moi nuoc  : " << 100.0 * setup_us.load() / wall_us
                      << "% thoi gian, TB " << setup_us.load() / 1000.0 / n_search << " ms/nuoc\n";
        }
        const int64_t tail = tail_start_us.load();
        if (tail >= 0 && secs > 0.0) {
            const double tail_s = secs - tail / 1e6;
            std::cout << "  Duoi (sau khi luong dau tien het van): " << tail_s << " s = "
                      << 100.0 * tail_s / secs << "% thoi gian, xong them "
                      << (done - done_at_tail.load()) << " van\n";
        }
        std::cout << std::flush;
    }
    // One machine-readable line for the phone's loop (sums the machines of one arena).
    std::cout << "FZ_ARENA W=" << a_wins << " D=" << draws << " L=" << b_wins
              << " N=" << done << std::endl;
    return 0;
}
