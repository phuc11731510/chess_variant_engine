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

using namespace Stockfish;

void run_ep_tests() {
    std::cout << "Loading custom variant for testing..." << std::endl;
    std::string ini_text = R"(
[custom_10x10_variant]
maxRank = 10
maxFile = j

pawn = p
knight = n
bishop = b
rook = r
queen = q
king = k:KN

amazon = a
chancellor = e
archbishop = h
centaur = m
customPiece1 = v:CN
customPiece2 = y:AD
customPiece3 = s:fKifmnDifmnA

pawnTypes = p s
promotionPawnTypes = p s
enPassantTypes = p s
nMoveRuleTypes = p s

doubleStep = true
doubleStepRegionWhite = *1 *2 *3
doubleStepRegionBlack = *10 *9 *8

promotionRegionWhite = *9 *10
promotionRegionBlack = *2 *1
mandatoryPawnPromotion = true

stalemateValue = loss
checkCounting = true
)";

    std::istringstream ss(ini_text);
    variants.parse_istream<false>(ss);

    const Variant* v = variants.find("custom_10x10_variant")->second;
    if (!v) {
        std::cerr << "[FAIL] Failed to find custom_10x10_variant!" << std::endl;
        std::exit(1);
    }    UCI::init_variant(v);
    PSQT::init(v);

    // TEST 1: Straight EP capture (b5b4)
    {
        std::cout << "\n--- TEST 1: Straight EP Capture (b5b4) ---" << std::endl;
        Position pos;
        StateListPtr states(new std::deque<StateInfo>(1));
        // White King on f1, Black King on f10. White Sergeant on a3, Black Sergeant on b5.
        std::string fen = "5k4/10/10/10/10/1s8/10/S9/10/5K4 w - - 7+7 0 1";
        pos.set(v, fen, false, &states->back(), Threads.main());

        std::cout << "Initial board state:\n" << pos << std::endl;

        std::cout << "Legal moves in initial position:" << std::endl;
        for (const auto& m : MoveList<LEGAL>(pos)) {
            std::cout << "  " << UCI::move(pos, m) << std::endl;
        }

        std::string move_str_a3c5 = "a3c5";
        Move m_a3c5 = UCI::to_move(pos, move_str_a3c5);
        if (m_a3c5 == MOVE_NONE) {
            std::cerr << "[FAIL] a3c5 is not a valid move in initial position!" << std::endl;
            std::exit(1);
        }

        states->emplace_back();
        pos.do_move(m_a3c5, states->back());
        std::cout << "After a3c5:\n" << pos << std::endl;

        std::cout << "Legal moves for Black:" << std::endl;
        bool b5b4_found = false;
        Move m_b5b4 = MOVE_NONE;
        for (const auto& m : MoveList<LEGAL>(pos)) {
            std::string move_str = UCI::move(pos, m);
            std::cout << "  " << move_str << std::endl;
            if (move_str == "b5b4") {
                b5b4_found = true;
                m_b5b4 = m;
            }
        }

        if (!b5b4_found) {
            std::cerr << "[FAIL] b5b4 not found in legal moves after a3c5!" << std::endl;
            std::exit(1);
        }

        // Verify it is indeed an en passant move type
        if (type_of(m_b5b4) != EN_PASSANT) {
            std::cerr << "[FAIL] b5b4 is NOT registered as EN_PASSANT move type! Type=" << type_of(m_b5b4) << std::endl;
            std::exit(1);
        }

        states->emplace_back();
        pos.do_move(m_b5b4, states->back());
        std::cout << "After b5b4:\n" << pos << std::endl;

        // Check if White Sergeant on c5 is removed
        Square sq_c5 = make_square(FILE_C, RANK_5);
        Piece p_c5 = pos.piece_on(sq_c5);
        if (p_c5 != NO_PIECE) {
            std::cerr << "[FAIL] White Sergeant is still on c5 after b5b4 straight EP capture!" << std::endl;
            std::exit(1);
        }

        std::cout << "[PASS] straight EP capture test passed!" << std::endl;
    }

    // TEST 2: Diagonal EP capture (a5b4)
    {
        std::cout << "\n--- TEST 2: Diagonal EP Capture (a5b4) ---" << std::endl;
        Position pos;
        StateListPtr states(new std::deque<StateInfo>(1));
        // White King on f1, Black King on f10. White Sergeant on a3, Black Sergeant on a5.
        std::string fen = "5k4/10/10/10/10/s9/10/S9/10/5K4 w - - 7+7 0 1";
        pos.set(v, fen, false, &states->back(), Threads.main());

        std::cout << "Initial board state:\n" << pos << std::endl;

        std::string move_str_a3c5 = "a3c5";
        Move m_a3c5 = UCI::to_move(pos, move_str_a3c5);
        if (m_a3c5 == MOVE_NONE) {
            std::cerr << "[FAIL] a3c5 is not a valid move in initial position!" << std::endl;
            std::exit(1);
        }

        states->emplace_back();
        pos.do_move(m_a3c5, states->back());
        std::cout << "After a3c5:\n" << pos << std::endl;

        std::cout << "Legal moves for Black:" << std::endl;
        bool a5b4_found = false;
        Move m_a5b4 = MOVE_NONE;
        for (const auto& m : MoveList<LEGAL>(pos)) {
            std::string move_str = UCI::move(pos, m);
            std::cout << "  " << move_str << std::endl;
            if (move_str == "a5b4") {
                a5b4_found = true;
                m_a5b4 = m;
            }
        }

        if (!a5b4_found) {
            std::cerr << "[FAIL] a5b4 not found in legal moves after a3c5!" << std::endl;
            std::exit(1);
        }

        // Verify it is indeed an en passant move type
        if (type_of(m_a5b4) != EN_PASSANT) {
            std::cerr << "[FAIL] a5b4 is NOT registered as EN_PASSANT move type! Type=" << type_of(m_a5b4) << std::endl;
            std::exit(1);
        }

        states->emplace_back();
        pos.do_move(m_a5b4, states->back());
        std::cout << "After a5b4:\n" << pos << std::endl;

        // Check if White Sergeant on c5 is removed
        Square sq_c5 = make_square(FILE_C, RANK_5);
        Piece p_c5 = pos.piece_on(sq_c5);
        if (p_c5 != NO_PIECE) {
            std::cerr << "[FAIL] White Sergeant is still on c5 after a5b4 diagonal EP capture!" << std::endl;
            std::exit(1);
        }

        std::cout << "[PASS] diagonal EP capture test passed!" << std::endl;
    }

    std::cout << "\n========================================" << std::endl;
    std::cout << "ALL EN PASSANT TESTS PASSED SUCCESSFULLY!" << std::endl;
    std::cout << "========================================" << std::endl;
}

int main(int argc, char* argv[]) {
    bool selfplay_mode = false;
    bool test_ep_mode = false;
    for (int i = 1; i < argc; ++i) {
        if (std::string(argv[i]) == "--selfplay") {
            selfplay_mode = true;
        } else if (std::string(argv[i]) == "--test-ep") {
            test_ep_mode = true;
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
    } else if (selfplay_mode) {
        std::cout << "Starting custom selfplay mode..." << std::endl;
        // Selfplay logic will go here
    } else {
        UCI::loop(argc, argv);
    }

    Threads.set(0);
    variants.clear_all();
    pieceMap.clear_all();
    delete XBoard::stateMachine;
    return 0;
}
