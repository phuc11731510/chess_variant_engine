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
#include "app/play_mode.h"
#include "app/variant_setup.h"
#include "app/backend_factory.h"
#include "app/uci_coords.h"
#include "app/search_support.h"

using namespace Stockfish;

static void PrintAsciiBoard(const Stockfish::Position& pos) {
    auto pc_char = [](Stockfish::Piece pc) -> char {
        char c = '?';
        switch (Stockfish::type_of(pc)) {
            case Stockfish::PAWN: c='p';break;        case Stockfish::KNIGHT: c='n';break;
            case Stockfish::BISHOP: c='b';break;      case Stockfish::ROOK: c='r';break;
            case Stockfish::QUEEN: c='q';break;        case Stockfish::KING: c='k';break;
            case Stockfish::AMAZON: c='a';break;       case Stockfish::CHANCELLOR: c='e';break;
            case Stockfish::ARCHBISHOP: c='h';break;   case Stockfish::CENTAUR: c='m';break;
            case Stockfish::CUSTOM_PIECE_1: c='v';break; case Stockfish::CUSTOM_PIECE_2: c='y';break;
            case Stockfish::CUSTOM_PIECE_3: c='s';break; default: break;
        }
        return (Stockfish::color_of(pc) == Stockfish::WHITE) ? static_cast<char>(c - 32) : c;
    };
    std::cout << "\n      a  b  c  d  e  f  g  h  i  j\n";
    for (int r = 9; r >= 0; --r) {
        std::cout << "  " << (r + 1 < 10 ? " " : "") << (r + 1) << " ";
        for (int f = 0; f < 10; ++f) {
            Stockfish::Piece pc = pos.piece_on(static_cast<Stockfish::Square>(r * 12 + f));
            std::cout << " " << (pc == Stockfish::NO_PIECE ? '.' : pc_char(pc)) << " ";
        }
        std::cout << "\n";
    }
    std::cout << std::endl;
}

void run_play(const std::string& weights, const std::string& provider, int fixed_batch,
              int visits, bool human_white) {
    setup_custom_variant();
    lczero::OptionsParser parser;
    lczero::classic::SearchParams::Populate(&parser);
    auto* d = parser.GetMutableDefaultsOptions();
    d->Set<float>(lczero::SharedBackendParams::kPolicySoftmaxTemp, 1.359f);  // lc0 default
    d->Set<std::string>(lczero::SharedBackendParams::kHistoryFill, "no");
    d->Set<float>(lczero::classic::BaseSearchParams::kNoiseEpsilonId, 0.0f);
    d->Set<std::string>(lczero::SharedBackendParams::kWeightsId, weights);
    std::string play_bopts;
    if (provider == "cuda")      play_bopts = "provider=cuda,fixed_batch=" + std::to_string(std::max(1, fixed_batch));
    else if (provider == "dml")  play_bopts = "provider=dml,threads=1";
    else                         play_bopts = "threads=1";
    d->Set<std::string>(lczero::SharedBackendParams::kBackendOptionsId, play_bopts);
    std::unique_ptr<lczero::Backend> backend;
    try { backend = arena_make_backend(parser.GetOptionsDict()); }
    catch (const std::exception& e) { std::cerr << "[play] backend load failed: " << e.what() << std::endl; return; }
    const lczero::OptionsDict& opts = parser.GetOptionsDict();

    auto tree = std::make_unique<lczero::classic::NodeTree>();
    tree->ResetToPosition(kUciStartFen, {});
    std::cout << "\n=== FairyZero --play (visits=" << visits << ") ===\n"
              << "You are " << (human_white ? "WHITE (uppercase, bottom)" : "BLACK (lowercase, top)")
              << ". Enter moves like 'b3b4' (promotion 'a9a10v'); type 'quit' to exit." << std::endl;

    lczero::GameResult result = lczero::GameResult::UNDECIDED;
    while (result == lczero::GameResult::UNDECIDED) {
        const Stockfish::Position& pos = tree->GetPositionHistory().Last().GetBoard().GetRawPosition();
        PrintAsciiBoard(pos);
        const bool black_to_move = tree->IsBlackToMove();
        const bool human_turn = ((!black_to_move) == human_white);
        if (human_turn) {
            std::cout << "Your move: " << std::flush;
            std::string mv;
            if (!std::getline(std::cin, mv)) break;
            if (mv == "quit" || mv == "q") break;
            // strip whitespace
            while (!mv.empty() && (mv.back() == '\r' || mv.back() == ' ')) mv.pop_back();
            const auto& board = tree->GetPositionHistory().Last().GetBoard();
            lczero::Move m = UciToCanonicalMove(board, mv, black_to_move);
            if (m.is_null()) { std::cout << "  illegal move, try again." << std::endl; continue; }
            tree->MakeMove(m);
        } else {
            auto responder = std::make_unique<SilentUciResponder>();
            auto stopper = std::make_unique<PlayoutCountStopper>(visits);
            auto search = std::make_unique<lczero::classic::Search>(
                *tree, backend.get(), std::move(responder), lczero::MoveList{},
                std::chrono::steady_clock::now(), std::move(stopper), false, false, opts, nullptr);
            search->RunBlocking(1);
            lczero::classic::Node* root = tree->GetCurrentHead();
            lczero::classic::EdgeAndNode best; uint64_t bn = 0;
            for (const auto& e : root->Edges()) if (e.GetN() >= bn) { bn = e.GetN(); best = e; }
            if (best.GetMove().is_null()) break;
            std::cout << "AI plays: " << CanonicalMoveToUci(best.GetMove(), black_to_move)
                      << "  (" << root->GetN() << " nodes)" << std::endl;
            tree->MakeMove(best.GetMove());
        }
        result = tree->GetPositionHistory().ComputeGameResult();
    }
    PrintAsciiBoard(tree->GetPositionHistory().Last().GetBoard().GetRawPosition());
    if (result == lczero::GameResult::WHITE_WON)      std::cout << "*** WHITE wins ***" << std::endl;
    else if (result == lczero::GameResult::BLACK_WON) std::cout << "*** BLACK wins ***" << std::endl;
    else if (result == lczero::GameResult::DRAW)      std::cout << "*** DRAW ***" << std::endl;
    else std::cout << "(game ended)" << std::endl;
}

// --test-uci: conformance for the move I/O (risk #1) — no backend needed.
