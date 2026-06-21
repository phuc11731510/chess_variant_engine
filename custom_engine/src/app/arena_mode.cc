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
#include "app/arena_mode.h"
#include "app/variant_setup.h"
#include "app/backend_factory.h"
#include "app/search_support.h"

using namespace Stockfish;

void run_arena(const std::string& model_a, const std::string& model_b, int games,
               int visits, int max_moves, int temp_cutoff,
               const std::string& provider, int fixed_batch) {
    std::cout << "\n=== ARENA: A=" << model_a << "  vs  B=" << model_b
              << "  (" << games << " games, visits=" << visits << ") ===" << std::endl;
    setup_custom_variant();
    const std::string fen =
        "vrhabkberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHABKBERV w BIbi - 7+7 0 1";

    auto build_opts = [&](lczero::OptionsParser& parser, const std::string& weights) {
        lczero::classic::SearchParams::Populate(&parser);
        parser.GetMutableDefaultsOptions()->Set<float>(lczero::SharedBackendParams::kPolicySoftmaxTemp, 1.0f);
        parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kHistoryFill, "no");
        parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kNoiseEpsilonId, 0.0f);
        parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kWeightsId, weights);
        const std::string bopts = (provider == "cuda")
            ? "provider=cuda,fixed_batch=" + std::to_string(std::max(1, fixed_batch))
            : "threads=1";
        parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kBackendOptionsId, bopts);
    };

    lczero::OptionsParser pa, pb;
    build_opts(pa, model_a);
    build_opts(pb, model_b);
    const lczero::OptionsDict& opts_a = pa.GetOptionsDict();
    const lczero::OptionsDict& opts_b = pb.GetOptionsDict();

    std::unique_ptr<lczero::Backend> ba, bb;
    try {
        ba = arena_make_backend(opts_a);
        bb = arena_make_backend(opts_b);
    } catch (const std::exception& e) {
        std::cerr << "[arena] backend load failed: " << e.what() << std::endl;
        std::exit(1);
    }

    int a_wins = 0, b_wins = 0, draws = 0;
    auto tree = std::make_unique<lczero::classic::NodeTree>();

    for (int g = 0; g < games; ++g) {
        const bool a_is_white = (g % 2 == 0);            // alternate colors for fairness
        tree->ResetToPosition(fen, {});
        lczero::GameResult result = lczero::GameResult::UNDECIDED;

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
            search->RunBlocking(1);

            lczero::classic::Node* root = tree->GetCurrentHead();
            lczero::classic::EdgeAndNode best;
            uint64_t total = 0, best_n = 0;
            for (const auto& e : root->Edges()) {
                total += e.GetN();
                if (e.GetN() >= best_n) { best_n = e.GetN(); best = e; }
            }
            if (best.GetMove().is_null()) break;

            lczero::Move played = best.GetMove();           // greedy by default
            if (ply < temp_cutoff && total > 0) {           // temperature opening for diversity
                const double toss = lczero::Random::Get().GetDouble(static_cast<double>(total));
                double acc = 0.0;
                for (const auto& e : root->Edges()) {
                    acc += static_cast<double>(e.GetN());
                    if (acc > toss) { played = e.GetMove(); break; }
                }
            }
            tree->MakeMove(played);
            result = tree->GetPositionHistory().ComputeGameResult();
            if (result != lczero::GameResult::UNDECIDED) break;
        }

        if (result == lczero::GameResult::WHITE_WON || result == lczero::GameResult::BLACK_WON) {
            const bool white_won = (result == lczero::GameResult::WHITE_WON);
            if (white_won == a_is_white) a_wins++; else b_wins++;
        } else {
            draws++;  // DRAW or cutoff (UNDECIDED)
        }
        std::cout << "  game " << (g + 1) << "/" << games << " (A plays "
                  << (a_is_white ? "White" : "Black") << "): result=" << (int)result
                  << "   [A " << a_wins << " W / " << draws << " D / " << b_wins << " L]" << std::endl;
    }

    const double score_a = (a_wins + 0.5 * draws) / std::max(1, games);
    std::cout << "\n=== ARENA RESULT ===" << std::endl;
    std::cout << "  A wins=" << a_wins << "  draws=" << draws << "  B wins=" << b_wins << std::endl;
    std::cout << "  A score = " << score_a << "  (>0.5 => A stronger than B)" << std::endl;
}

// ============================================================================
// T8.1 — UCI engine driving MCTS + ONNX (the "real" AlphaZero engine, terminal).
// ============================================================================

// Variant startpos (same as arena/self-play).
