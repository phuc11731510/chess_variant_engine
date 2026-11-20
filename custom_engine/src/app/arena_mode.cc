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

namespace {
// c_puct of every arena search unless --cpuct overrides it (owner's decision, 2026-11-20; the PCR shallow searches of
// self-play use the same 1.25, the full ones 1.5).
constexpr float kArenaCpuct = 1.25f;
}  // namespace

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
    // Owner's decisions (2026-11-20): the arena searches EVERY move with the same constant number of playouts
    // (--visits, the cell passes 400), a constant c_puct (kArenaCpuct unless --cpuct is given), no Dirichlet noise,
    // and draws EVERY move of the game with temperature --temperature (default 0.5: weight (N / N_max)^(1 / T)),
    // exactly as self-play draws its moves. There is no opening phase any more (the old --temp-cutoff).
    const float temperature = o.sp_temperature;
    const float cpuct = o.sp_cpuct >= 0.0f ? o.sp_cpuct : kArenaCpuct;

    std::cout << "\n=== ARENA: A=" << model_a << "  vs  B=" << model_b
              << "  (" << games << " games, visits=" << visits
              << ", provider=" << o.sp_provider << ") ===" << std::endl;
    std::cout << "[arena] search: PUCT, " << visits << " playouts every move (cpuct " << cpuct
              << ", no noise); every move drawn with temperature " << temperature << std::endl;
    setup_custom_variant();
    // Start positions. With --start-fen FILE every PAIR of games (2k and 2k+1, A is White in the even one) starts
    // from line k of the book (wrapping round), so each position is played once with each color: the two sides of a
    // random start position are not symmetric, and this is what keeps the colors fair. A single FEN, or no
    // --start-fen (the fixed placeholder lczero::ChessBoard::kStartposFen), starts every game from that position.
    std::string fen = lczero::ChessBoard::kStartposFen;
    std::vector<std::string> arena_fens;
    if (!o.sp_start_fen.empty()) {
        const std::string why = LoadStartFens(o.sp_start_fen, &arena_fens, &fen);
        if (!why.empty()) {
            std::cerr << "[arena] FATAL: " << why << std::endl;
            return 1;
        }
    }
    if (!arena_fens.empty()) {
        std::cout << "[arena] start positions: " << arena_fens.size() << " FENs from " << o.sp_start_fen
                  << ", each played by a PAIR of games with the colors swapped ("
                  << (games + 1) / 2 << " position(s) needed for " << games << " games"
                  << (static_cast<int>(arena_fens.size()) < (games + 1) / 2 ? "; the book wraps round" : "")
                  << ")" << std::endl;
    } else if (!o.sp_start_fen.empty()) {
        std::cout << "[arena] start position: one FEN for every game" << std::endl;
    } else {
        std::cout << "[arena] start position: the fixed placeholder (no --start-fen)" << std::endl;
    }

    // Backend options per provider (same selection as self-play / --uci-nn).
    // CUDA (Colab, needs -Duse_cuda): fixed batch. DML (Windows iGPU, needs
    // -Duse_dml): the explicit provider= key is REQUIRED or onnxruntime silently
    // runs on CPU. CPU: just intra-op threads.
    std::string bopts;
    if (o.sp_provider == "cuda" || o.sp_provider == "tensorrt") {
        bopts = "provider=" + o.sp_provider + ",fixed_batch=" + std::to_string(o.sp_fixed_batch);
        for (const auto& kv : o.sp_cuda_opts) bopts += ",cuda." + kv;
        for (const auto& kv : o.sp_trt_opts) bopts += ",trt." + kv;
        if (!o.sp_extra_batches.empty()) {
            bopts += ",extra_batches=";
            for (size_t i = 0; i < o.sp_extra_batches.size(); ++i)
                bopts += (i ? ":" : "") + std::to_string(o.sp_extra_batches[i]);
        }
    } else if (o.sp_provider == "dml") {
        bopts = "provider=dml,threads=" + std::to_string(std::max(1, o.sp_backend_threads));
    } else {
        bopts = "threads=" + std::to_string(std::max(1, o.sp_backend_threads));
    }
    std::cout << "[arena] backend: " << bopts << std::endl;

    auto build_opts = [&](lczero::OptionsParser& parser, const std::string& weights) {
        lczero::classic::SearchParams::Populate(&parser);
        parser.GetMutableDefaultsOptions()->Set<float>(lczero::SharedBackendParams::kPolicySoftmaxTemp, o.sp_policy_temp);
        parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kHistoryFill, "always");  // ghi lai cho dung; mang luon ma hoa ALWAYS (onnx_backend.cc)
        parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kNoiseEpsilonId, 0.0f);
        parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kCpuctId, cpuct);
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
    // A's results by color (index 0: A is White, 1: A is Black). With random start positions the two sides of a
    // position are not symmetric, so a soft stop that splits a pair of games (see the book note above) shows up as
    // unequal game counts here instead of silently biasing the score.
    int a_col_games[2] = {0, 0}, a_col_wins[2] = {0, 0}, a_col_draws[2] = {0, 0};
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
            // Games 2k and 2k+1 share a start position (colors swapped); see the book note above.
            const std::string& game_fen =
                arena_fens.empty() ? fen : arena_fens[static_cast<size_t>(g / 2) % arena_fens.size()];
            tree->ResetToPosition(game_fen, {});
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
                // The same draw as self-play, for every move of the game.
                const lczero::classic::EdgeAndNode played_edge = lczero::SelectMoveEdge(root, temperature);
                if (played_edge.GetMove().is_null()) break;
                lczero::Move played = played_edge.GetMove();
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
            const int col = a_is_white ? 0 : 1;
            ++a_col_games[col];
            if (result == lczero::GameResult::WHITE_WON || result == lczero::GameResult::BLACK_WON) {
                const bool white_won = (result == lczero::GameResult::WHITE_WON);
                if (white_won == a_is_white) { a_wins++; ++a_col_wins[col]; } else b_wins++;
            } else {
                draws++;  // DRAW or cutoff (UNDECIDED)
                ++a_col_draws[col];
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
            if (o.arena_show_moves) {
                std::cout << "    start: " << game_fen << std::endl;
                std::cout << "    moves: " << moves_str << std::endl;
            }
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
    std::cout << "  by color: A as White " << a_col_wins[0] << "W/" << a_col_draws[0] << "D/"
              << (a_col_games[0] - a_col_wins[0] - a_col_draws[0]) << "L (" << a_col_games[0]
              << " games) | A as Black " << a_col_wins[1] << "W/" << a_col_draws[1] << "D/"
              << (a_col_games[1] - a_col_wins[1] - a_col_draws[1]) << "L (" << a_col_games[1] << " games)";
    if (a_col_games[0] != a_col_games[1])
        std::cout << "  [colors NOT balanced: a pair of games was split (soft stop or an odd --games)]";
    std::cout << std::endl;
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
