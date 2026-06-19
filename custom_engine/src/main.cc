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
#include <cstdio>
#include <cmath>
#include "search/classic/search.h"
#include "search/classic/params.h"
#include "neural/backend.h"
#include "neural/shared_params.h"
#include "neural/onnx_backend.h"
#include "neural/zero_heap_cache.h"
#include "utils/random.h"
#include "chess/callbacks.h"

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

promotionRegionWhite = *8 *9 *10
promotionRegionBlack = *3 *2 *1
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

    // TEST 3: EP FEN Round-trip
    {
        std::cout << "\n--- TEST 3: EP FEN Round-trip (Straight & Diagonal, Stockfish & Adapter) ---" << std::endl;
        
        // Sub-test 3.1: Straight EP Round-trip using Stockfish::Position (FS Layer)
        {
            Position pos;
            StateListPtr states(new std::deque<StateInfo>(1));
            std::string fen = "5k4/10/10/10/10/1s8/10/S9/10/5K4 w - - 7+7 0 1";
            pos.set(v, fen, false, &states->back(), Threads.main());

            std::string move_str_a3c5 = "a3c5";
            Move m_a3c5 = UCI::to_move(pos, move_str_a3c5);
            states->emplace_back();
            pos.do_move(m_a3c5, states->back());
            std::string fen_after = pos.fen();
            std::cout << "  FEN after a3c5 (Straight): " << fen_after << std::endl;

            Position pos2;
            StateListPtr states2(new std::deque<StateInfo>(1));
            pos2.set(v, fen_after, false, &states2->back(), Threads.main());

            bool b5b4_found = false;
            Move m_b5b4 = MOVE_NONE;
            for (const auto& m : MoveList<LEGAL>(pos2)) {
                if (UCI::move(pos2, m) == "b5b4") {
                    b5b4_found = true;
                    m_b5b4 = m;
                }
            }

            if (!b5b4_found || type_of(m_b5b4) != EN_PASSANT) {
                std::cerr << "[FAIL] b5b4 straight EP not found or invalid type after FEN round-trip!" << std::endl;
                std::exit(1);
            }

            states2->emplace_back();
            pos2.do_move(m_b5b4, states2->back());
            if (pos2.piece_on(make_square(FILE_C, RANK_5)) != NO_PIECE) {
                std::cerr << "[FAIL] White Sergeant still on c5 after straight EP capture on parsed board!" << std::endl;
                std::exit(1);
            }
            std::cout << "  Sub-test 3.1: Straight EP via FS layer passed!" << std::endl;
        }

        // Sub-test 3.2: Diagonal EP Round-trip using Stockfish::Position (FS Layer)
        {
            Position pos;
            StateListPtr states(new std::deque<StateInfo>(1));
            std::string fen = "5k4/10/10/10/10/s9/10/S9/10/5K4 w - - 7+7 0 1";
            pos.set(v, fen, false, &states->back(), Threads.main());

            std::string move_str_a3c5 = "a3c5";
            Move m_a3c5 = UCI::to_move(pos, move_str_a3c5);
            states->emplace_back();
            pos.do_move(m_a3c5, states->back());
            std::string fen_after = pos.fen();
            std::cout << "  FEN after a3c5 (Diagonal): " << fen_after << std::endl;

            Position pos2;
            StateListPtr states2(new std::deque<StateInfo>(1));
            pos2.set(v, fen_after, false, &states2->back(), Threads.main());

            bool a5b4_found = false;
            Move m_a5b4 = MOVE_NONE;
            for (const auto& m : MoveList<LEGAL>(pos2)) {
                if (UCI::move(pos2, m) == "a5b4") {
                    a5b4_found = true;
                    m_a5b4 = m;
                }
            }

            if (!a5b4_found || type_of(m_a5b4) != EN_PASSANT) {
                std::cerr << "[FAIL] a5b4 diagonal EP not found or invalid type after FEN round-trip!" << std::endl;
                std::exit(1);
            }

            states2->emplace_back();
            pos2.do_move(m_a5b4, states2->back());
            if (pos2.piece_on(make_square(FILE_C, RANK_5)) != NO_PIECE) {
                std::cerr << "[FAIL] White Sergeant still on c5 after diagonal EP capture on parsed board!" << std::endl;
                std::exit(1);
            }
            std::cout << "  Sub-test 3.2: Diagonal EP via FS layer passed!" << std::endl;
        }

        // Sub-test 3.3: Round-trip using lczero::ChessBoard (Adapter Layer)
        {
            lczero::ChessBoard board1;
            std::string fen = "5k4/10/10/10/10/1s8/10/S9/10/5K4 w - - 7+7 0 1";
            board1.SetFromFen(fen);

            lczero::Move m_a3c5 = board1.ParseMove("a3c5");
            board1.ApplyMove(m_a3c5);
            std::string fen_after = board1.GetRawPosition().fen();

            lczero::ChessBoard board2;
            board2.SetFromFen(fen_after);

            bool b5b4_found = false;
            lczero::MoveList moves = board2.GenerateLegalMoves();
            for (size_t i = 0; i < moves.size(); ++i) {
                if (board2.MoveToString(moves[i]) == "b5b4") {
                    b5b4_found = true;
                }
            }

            if (!b5b4_found) {
                std::cerr << "[FAIL] b5b4 EP not found in legal moves on adapter ChessBoard!" << std::endl;
                std::exit(1);
            }

            lczero::Move m_b5b4 = board2.ParseMove("b5b4");
            board2.ApplyMove(m_b5b4);

            if (board2.GetRawPosition().piece_on(make_square(FILE_C, RANK_5)) != NO_PIECE) {
                std::cerr << "[FAIL] White Sergeant still on c5 after EP capture on adapter ChessBoard!" << std::endl;
                std::exit(1);
            }
            std::cout << "  Sub-test 3.3: EP Round-trip via Adapter ChessBoard passed!" << std::endl;
        }

        std::cout << "[PASS] EP FEN Round-trip test passed!" << std::endl;
    }

    std::cout << "\n========================================" << std::endl;
    std::cout << "ALL EN PASSANT TESTS PASSED SUCCESSFULLY!" << std::endl;
    std::cout << "========================================" << std::endl;
}

void run_board_tests() {
    std::cout << "\n========================================" << std::endl;
    std::cout << "RUNNING CHESSBOARD BRIDGE TESTS" << std::endl;
    std::cout << "========================================\n" << std::endl;

    // Load custom variant
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

promotionRegionWhite = *8 *9 *10
promotionRegionBlack = *3 *2 *1
mandatoryPawnPromotion = true
promotionPieceTypes = b h m n v y

castling = true
castlingKingsideFile = h
castlingQueensideFile = d
castlingRookKingsideFile = i
castlingRookQueensideFile = b

stalemateValue = loss
checkCounting = true
)";

    std::istringstream ss(ini_text);
    variants.parse_istream<false>(ss);

    const Variant* v = variants.find("custom_10x10_variant")->second;
    if (!v) {
        std::cerr << "[FAIL] Failed to find custom_10x10_variant!" << std::endl;
        std::exit(1);
    }
    UCI::init_variant(v);
    PSQT::init(v);

    // TEST 1: Default initialization and legal moves count (should be 34)
    {
        std::cout << "TEST 1: Default initialization..." << std::endl;
        lczero::ChessBoard board;
        
        // Output startpos FEN
        std::cout << "Startpos FEN: " << lczero::ChessBoard::kStartposFen << std::endl;
        std::cout << "Board state:\n" << board.GetRawPosition() << std::endl;

        auto moves = board.GenerateLegalMoves();
        std::cout << "Found " << moves.size() << " legal moves." << std::endl;
        for (const auto& m : moves) {
            std::cout << "  " << board.MoveToString(m) << std::endl;
        }

        if (moves.size() != 34) {
            std::cerr << "[FAIL] Legal moves size is " << moves.size() << ", expected 34!" << std::endl;
            std::exit(1);
        }
        std::cout << "[PASS] TEST 1 passed!\n" << std::endl;
    }

    // TEST 2: ApplyMove and UndoMove consistency
    {
        std::cout << "TEST 2: ApplyMove & UndoMove consistency..." << std::endl;
        lczero::ChessBoard board;
        std::string original_fen = board.GetRawPosition().fen();
        
        auto moves = board.GenerateLegalMoves();
        if (moves.empty()) {
            std::cerr << "[FAIL] No legal moves found!" << std::endl;
            std::exit(1);
        }

        lczero::Move m = moves[0];
        std::cout << "Applying move: " << board.MoveToString(m) << std::endl;
        board.ApplyMove(m);
        std::string post_move_fen = board.GetRawPosition().fen();
        std::cout << "Post-move FEN: " << post_move_fen << std::endl;

        std::cout << "Undoing move..." << std::endl;
        board.UndoMove();
        std::string reverted_fen = board.GetRawPosition().fen();
        std::cout << "Reverted FEN: " << reverted_fen << std::endl;

        if (original_fen != reverted_fen) {
            std::cerr << "[FAIL] FEN discrepancy after Apply/Undo! Original: " << original_fen << ", Reverted: " << reverted_fen << std::endl;
            std::exit(1);
        }
        std::cout << "[PASS] TEST 2 passed!\n" << std::endl;
    }

    // TEST 3: Stalemate = Loss rule verification
    {
        std::cout << "TEST 3: Stalemate = Loss verification..." << std::endl;
        // White King on a1, Black King on j10, Black Rook on b2 protected by Rook on b10.
        std::string stalemate_fen = "1r7k/10/10/10/10/10/10/10/1r8/K9 w - - 7+7 0 1";
        lczero::ChessBoard board(stalemate_fen);
        std::cout << "Stalemate position:\n" << board.GetRawPosition() << std::endl;

        auto history = std::make_unique<lczero::PositionHistory>();
        history->Reset(board, 0, 1);

        lczero::GameResult result = history->ComputeGameResult();
        if (result != lczero::GameResult::BLACK_WON) {
            std::cerr << "[FAIL] Stalemate result is not BLACK_WON! Got: " << (int)result << std::endl;
            std::exit(1);
        }
        std::cout << "[PASS] TEST 3 passed! (Stalemate correctly marked as Loss)\n" << std::endl;
    }

    // TEST 4: 7-checks limit rule verification
    {
        std::cout << "TEST 4: 7-checks limit verification..." << std::endl;
        
        // Case A: White checks remaining = 0
        {
            std::string checks_0_fen = "k9/10/10/10/10/10/10/10/10/K9 w - - 0+7 0 1";
            lczero::ChessBoard board(checks_0_fen);
            auto history = std::make_unique<lczero::PositionHistory>();
            history->Reset(board, 0, 1);

            lczero::GameResult result = history->ComputeGameResult();
            if (result != lczero::GameResult::WHITE_WON) {
                std::cerr << "[FAIL] 0 checks remaining for White did not result in WHITE_WON! Got: " << (int)result << std::endl;
                std::exit(1);
            }
        }

        // Case B: Black checks remaining = 0
        {
            std::string checks_0_fen = "k9/10/10/10/10/10/10/10/10/K9 w - - 7+0 0 1";
            lczero::ChessBoard board(checks_0_fen);
            auto history = std::make_unique<lczero::PositionHistory>();
            history->Reset(board, 0, 1);

            lczero::GameResult result = history->ComputeGameResult();
            if (result != lczero::GameResult::BLACK_WON) {
                std::cerr << "[FAIL] 0 checks remaining for Black did not result in BLACK_WON! Got: " << (int)result << std::endl;
                std::exit(1);
            }
        }

        std::cout << "[PASS] TEST 4 passed! (7-checks limit correctly ends the game)\n" << std::endl;
    }

    // TEST 5: Encoder & Unpacker validation
    {
        std::cout << "TEST 5: Encoder & Unpacker validation..." << std::endl;
        
        lczero::ChessBoard board;
        auto history = std::make_unique<lczero::PositionHistory>();
        history->Reset(board, 0, 1);
        
        lczero::InputPlanes planes;
        int transform = -1;
        lczero::EncodePositionForNN(*history, 8, lczero::FillEmptyHistory::NO, &planes, &transform);
        
        // Xác minh kích thước mặt phẳng
        constexpr size_t expected_planes = lczero::kAuxPlaneBase + lczero::kAuxPlanesCount; // 226
        if (planes.size() != expected_planes) {
            std::cerr << "[FAIL] Expected " << expected_planes << " planes, got " << planes.size() << std::endl;
            std::exit(1);
        }
        if (transform != 0) {
            std::cerr << "[FAIL] Expected transform 0, got " << transform << std::endl;
            std::exit(1);
        }
        
        // Giả lập một vài giá trị trên các mặt phẳng
        // Mặt phẳng 0: Bật ô A1 (SQ_A1 = 0)
        planes[0].mask = Stockfish::square_bb(Stockfish::SQ_A1);
        planes[0].value = 1.0f;
        
        // Mặt phẳng 7: Điền toàn bộ giá trị 0.5f (Biên bàn cờ)
        planes[7].Fill(0.5f);
        
        // Bung ra mảng float
        constexpr int width = 10;
        constexpr int height = 10;
        constexpr int plane_size = width * height;
        std::vector<float> float_planes(expected_planes * plane_size, 0.0f);
        
        lczero::UnpackInputPlanes(planes, float_planes.data(), width, height);
        
        // Xác minh mặt phẳng 0
        // Ô SQ_A1 (rank 0, file 0) phải là 1.0f, các ô khác là 0.0f
        if (float_planes[0] != 1.0f) {
            std::cerr << "[FAIL] Plane 0 index 0 (SQ_A1) should be 1.0f, got " << float_planes[0] << std::endl;
            std::exit(1);
        }
        for (int i = 1; i < plane_size; ++i) {
            if (float_planes[i] != 0.0f) {
                std::cerr << "[FAIL] Plane 0 index " << i << " should be 0.0f, got " << float_planes[i] << std::endl;
                std::exit(1);
            }
        }
        
        // Xác minh mặt phẳng 7 (tất cả là 0.5f)
        const float* plane7_start = float_planes.data() + 7 * plane_size;
        for (int i = 0; i < plane_size; ++i) {
            if (plane7_start[i] != 0.5f) {
                std::cerr << "[FAIL] Plane 7 index " << i << " should be 0.5f, got " << plane7_start[i] << std::endl;
                std::exit(1);
            }
        }
        
        // Xác minh mặt phẳng 1 (không có gì, tất cả là 0.0f)
        const float* plane1_start = float_planes.data() + 1 * plane_size;
        for (int i = 0; i < plane_size; ++i) {
            if (plane1_start[i] != 0.0f) {
                std::cerr << "[FAIL] Plane 1 index " << i << " should be 0.0f, got " << plane1_start[i] << std::endl;
                std::exit(1);
            }
        }
        
        // Xác minh cơ chế tái sử dụng buffer tĩnh hoạt động bình thường
        lczero::EncodePositionForNN(*history, 8, lczero::FillEmptyHistory::NO, &planes, nullptr);
        // Tất cả các plane sau khi encode mới phải được reset về 0 TRƯỚC KHI xử lý (vì A1 không có Pawn ở startpos nên bit này phải bằng 0)
        if (planes[0].mask & Stockfish::square_bb(Stockfish::SQ_A1)) {
            std::cerr << "[FAIL] Plane 0 mask was not reset to 0 after re-encoding" << std::endl;
            std::exit(1);
        }
        
        std::cout << "[PASS] TEST 5 passed! (Encoder & Unpacker validation correct)\n" << std::endl;
    }

    // TEST 6: MCTS Relative & Absolute Result Verification (Checkmate & Stalemate & 7-checks)
    {
        std::cout << "TEST 6: MCTS Relative & Absolute Result Verification..." << std::endl;

        // Part A: White is checkmated. It is White's turn to move (board.flipped() == false).
        // White King on a1, Black Rooks on b1 and b2.
        std::string white_checkmated_fen = "9k/10/10/10/10/10/10/10/1r8/Kr8 w - - 7+7 0 1";
        lczero::ChessBoard board_white_cm(white_checkmated_fen);
        auto history_white_cm = std::make_unique<lczero::PositionHistory>();
        history_white_cm->Reset(board_white_cm, 0, 1);

        auto moves_white_cm = board_white_cm.GenerateLegalMoves();
        if (!moves_white_cm.empty() || !board_white_cm.IsUnderCheck()) {
            std::cerr << "[FAIL] Test setup error: White should be checkmated!" << std::endl;
            std::exit(1);
        }

        // Check Absolute Game Result (BLACK_WON - Black won the game)
        lczero::GameResult abs_white_cm = history_white_cm->ComputeGameResult();
        if (abs_white_cm != lczero::GameResult::BLACK_WON) {
            std::cerr << "[FAIL] Absolute checkmate on White should return BLACK_WON, but got: " 
                      << (int)abs_white_cm << std::endl;
            std::exit(1);
        }
        std::cout << "  - White checkmated returns absolute BLACK_WON (Correct)" << std::endl;

        // Check Relative MCTS Result (WHITE_WON - relative Win for the player who just moved: Black)
        lczero::GameResult res_white_cm = history_white_cm->ComputeMctsResult(moves_white_cm);
        if (res_white_cm != lczero::GameResult::WHITE_WON) {
            std::cerr << "[FAIL] Checkmate on White should return WHITE_WON in MCTS, but got: " 
                      << (int)res_white_cm << std::endl;
            std::exit(1);
        }
        std::cout << "  - White checkmated returns relative GameResult::WHITE_WON (Correct)" << std::endl;

        // Part B: Black is checkmated. It is Black's turn to move (board.flipped() == true).
        // Black King on a10, White Rooks on b10 and b9.
        std::string black_checkmated_fen = "kR8/1R8/10/10/10/10/10/10/10/9K b - - 7+7 0 1";
        lczero::ChessBoard board_black_cm(black_checkmated_fen);
        auto history_black_cm = std::make_unique<lczero::PositionHistory>();
        history_black_cm->Reset(board_black_cm, 0, 1);

        auto moves_black_cm = board_black_cm.GenerateLegalMoves();
        if (!moves_black_cm.empty() || !board_black_cm.IsUnderCheck()) {
            std::cerr << "[FAIL] Test setup error: Black should be checkmated!" << std::endl;
            std::exit(1);
        }

        // Check Absolute Game Result (WHITE_WON - White won the game)
        lczero::GameResult abs_black_cm = history_black_cm->ComputeGameResult();
        if (abs_black_cm != lczero::GameResult::WHITE_WON) {
            std::cerr << "[FAIL] Absolute checkmate on Black should return WHITE_WON, but got: " 
                      << (int)abs_black_cm << std::endl;
            std::exit(1);
        }
        std::cout << "  - Black checkmated returns absolute WHITE_WON (Correct)" << std::endl;

        // Check Relative MCTS Result (WHITE_WON - relative Win for the player who just moved: White)
        lczero::GameResult res_black_cm = history_black_cm->ComputeMctsResult(moves_black_cm);
        if (res_black_cm != lczero::GameResult::WHITE_WON) {
            std::cerr << "[FAIL] Checkmate on Black should return WHITE_WON in MCTS, but got: " 
                      << (int)res_black_cm << std::endl;
            std::exit(1);
        }
        std::cout << "  - Black checkmated returns relative GameResult::WHITE_WON (Correct)" << std::endl;

        // Part C: Verify 7-checks in both absolute and MCTS.
        // Scenario 1: White has 0 checks remaining (White won absolute).
        {
            // Case A: Black to move (board.flipped() == true). White just checked.
            std::string white_win_black_turn = "k9/10/10/10/10/10/10/10/10/K9 b - - 0+7 0 1";
            lczero::ChessBoard board(white_win_black_turn);
            auto history = std::make_unique<lczero::PositionHistory>();
            history->Reset(board, 0, 1);

            // Absolute check
            lczero::GameResult abs = history->ComputeGameResult();
            if (abs != lczero::GameResult::WHITE_WON) {
                std::cerr << "[FAIL] White win 7-checks absolute should be WHITE_WON, got: " << (int)abs << std::endl;
                std::exit(1);
            }
            // MCTS check (relative Win for White, who just moved)
            lczero::GameResult res = history->ComputeMctsResult(board.GenerateLegalMoves());
            if (res != lczero::GameResult::WHITE_WON) {
                std::cerr << "[FAIL] White win 7-checks (Black's turn) MCTS should be WHITE_WON, got: " << (int)res << std::endl;
                std::exit(1);
            }

            // Case B: White to move (board.flipped() == false). Black just moved (but White won).
            std::string white_win_white_turn = "k9/10/10/10/10/10/10/10/10/K9 w - - 0+7 0 1";
            lczero::ChessBoard board_wt(white_win_white_turn);
            auto history_wt = std::make_unique<lczero::PositionHistory>();
            history_wt->Reset(board_wt, 0, 1);

            // Absolute check
            lczero::GameResult abs_wt = history_wt->ComputeGameResult();
            if (abs_wt != lczero::GameResult::WHITE_WON) {
                std::cerr << "[FAIL] White win 7-checks absolute should be WHITE_WON, got: " << (int)abs_wt << std::endl;
                std::exit(1);
            }
            // MCTS check (relative Loss for Black, who just moved)
            lczero::GameResult res_wt = history_wt->ComputeMctsResult(board_wt.GenerateLegalMoves());
            if (res_wt != lczero::GameResult::BLACK_WON) {
                std::cerr << "[FAIL] White win 7-checks (White's turn) MCTS should be BLACK_WON, got: " << (int)res_wt << std::endl;
                std::exit(1);
            }
        }

        // Scenario 2: Black has 0 checks remaining (Black won absolute).
        {
            // Case C: White to move (board.flipped() == false). Black just checked.
            std::string black_win_white_turn = "k9/10/10/10/10/10/10/10/10/K9 w - - 7+0 0 1";
            lczero::ChessBoard board(black_win_white_turn);
            auto history = std::make_unique<lczero::PositionHistory>();
            history->Reset(board, 0, 1);

            // Absolute check
            lczero::GameResult abs = history->ComputeGameResult();
            if (abs != lczero::GameResult::BLACK_WON) {
                std::cerr << "[FAIL] Black win 7-checks absolute should be BLACK_WON, got: " << (int)abs << std::endl;
                std::exit(1);
            }
            // MCTS check (relative Win for Black, who just moved)
            lczero::GameResult res = history->ComputeMctsResult(board.GenerateLegalMoves());
            if (res != lczero::GameResult::WHITE_WON) {
                std::cerr << "[FAIL] Black win 7-checks (White's turn) MCTS should be WHITE_WON, got: " << (int)res << std::endl;
                std::exit(1);
            }

            // Case D: Black to move (board.flipped() == true). White just moved (but Black won).
            std::string black_win_black_turn = "k9/10/10/10/10/10/10/10/10/K9 b - - 7+0 0 1";
            lczero::ChessBoard board_bt(black_win_black_turn);
            auto history_bt = std::make_unique<lczero::PositionHistory>();
            history_bt->Reset(board_bt, 0, 1);

            // Absolute check
            lczero::GameResult abs_bt = history_bt->ComputeGameResult();
            if (abs_bt != lczero::GameResult::BLACK_WON) {
                std::cerr << "[FAIL] Black win 7-checks absolute should be BLACK_WON, got: " << (int)abs_bt << std::endl;
                std::exit(1);
            }
            // MCTS check (relative Loss for White, who just moved)
            lczero::GameResult res_bt = history_bt->ComputeMctsResult(board_bt.GenerateLegalMoves());
            if (res_bt != lczero::GameResult::BLACK_WON) {
                std::cerr << "[FAIL] Black win 7-checks (Black's turn) MCTS should be BLACK_WON, got: " << (int)res_bt << std::endl;
                std::exit(1);
            }
        }
        std::cout << "  - [VERIFIED] All 7-checks absolute and relative evaluations checked successfully." << std::endl;

        std::cout << "[PASS] TEST 6 passed! (MCTS and Game absolute/relative checkmate and 7-checks values verified)\n" << std::endl;
    }

    // TEST 7: Castling Generation, Encoding, and Execution
    {
        std::cout << "TEST 7: Castling Generation, Encoding, and Execution..." << std::endl;
        
        // Dựng thế cờ trắng nhập thành (f1->i1 hoặc f1->b1)
        // 1r3k2r1/10/10/10/10/10/10/10/10/1R3K2R1 w BIbi - 7+7 0 1
        std::string castling_fen = "1r3k2r1/10/10/10/10/10/10/10/10/1R3K2R1 w BIbi - 7+7 0 1";
        lczero::ChessBoard board(castling_fen);
        std::cout << "Castling Board State:\n" << board.GetRawPosition() << std::endl;
        
        // 1. GenerateLegalMoves: check if Kingside (f1i1) and Queenside (f1b1) castling are generated
        auto moves = board.GenerateLegalMoves();
        bool found_oo = false;
        bool found_ooo = false;
        lczero::Move move_oo = lczero::MOVE_NONE;
        lczero::Move move_ooo = lczero::MOVE_NONE;
        
        std::cout << "Generated Moves:" << std::endl;
        for (const auto& m : moves) {
            std::string m_str = board.MoveToString(m);
            std::cout << "  " << m_str << " (type: " << (int)Stockfish::type_of(m.raw()) << ")" << std::endl;
            if (m_str == "f1h1") {
                found_oo = true;
                move_oo = m;
            } else if (m_str == "f1d1") {
                found_ooo = true;
                move_ooo = m;
            }
        }
        
        if (!found_oo) {
            std::cerr << "[FAIL] Kingside castling f1h1 not found in legal moves!" << std::endl;
            std::exit(1);
        }
        if (!found_ooo) {
            std::cerr << "[FAIL] Queenside castling f1d1 not found in legal moves!" << std::endl;
            std::exit(1);
        }
        std::cout << "  - [VERIFIED] Both Kingside (f1h1) and Queenside (f1d1) castling moves are generated." << std::endl;
        
        // 2. MoveToNNIndex check:
        // Kingside f1->i1 (dx = 3, dy = 0). Hướng Đông-3 (East-3)
        // type_idx = 2 * 9 + 2 = 20. from_flat = 5. index = 2005.
        // Queenside f1->b1 (dx = -4, dy = 0). Hướng Tây-4 (West-4)
        // type_idx = 6 * 9 + 3 = 57. from_flat = 5. index = 5705.
        uint16_t index_oo = lczero::MoveToNNIndex(move_oo, 0);
        uint16_t index_ooo = lczero::MoveToNNIndex(move_ooo, 0);
        
        std::cout << "f1i1 Index: " << index_oo << std::endl;
        std::cout << "f1b1 Index: " << index_ooo << std::endl;
        
        if (index_oo != 2005) {
            std::cerr << "[FAIL] Kingside castling index mismatch! Expected 2005, got " << index_oo << std::endl;
            std::exit(1);
        }
        if (index_ooo != 5705) {
            std::cerr << "[FAIL] Queenside castling index mismatch! Expected 5705, got " << index_ooo << std::endl;
            std::exit(1);
        }
        
        // Ensure they decode back to equivalent NORMAL moves with same square coordinates
        lczero::Move decoded_oo = lczero::MoveFromNNIndex(index_oo, 0);
        lczero::Move decoded_ooo = lczero::MoveFromNNIndex(index_ooo, 0);
        
        if (board.MoveToString(decoded_oo) != "f1i1") {
            std::cerr << "[FAIL] Kingside castling index did not decode back! Got: " << board.MoveToString(decoded_oo) << std::endl;
            std::exit(1);
        }
        if (board.MoveToString(decoded_ooo) != "f1b1") {
            std::cerr << "[FAIL] Queenside castling index did not decode back! Got: " << board.MoveToString(decoded_ooo) << std::endl;
            std::exit(1);
        }
        std::cout << "  - [VERIFIED] MoveToNNIndex maps castling to sliding slots uniquely (2005 and 5705) and decodes back to coordinate-equivalent normal moves." << std::endl;
        
        // 3. Encoder check for aux planes 216-219:
        // Before castling, rights are BIbi.
        // For White: Queenside (B / b1) is plane 216, Kingside (I / i1) is plane 217.
        // For Black: Queenside (b / b10) is plane 218, Kingside (i / i10) is plane 219.
        auto history = std::make_unique<lczero::PositionHistory>();
        history->Reset(board, 0, 1);
        
        lczero::InputPlanes planes;
        int transform = -1;
        lczero::EncodePositionForNN(*history, 8, lczero::FillEmptyHistory::NO, &planes, &transform);
        
        // Verify White castling rights
        // Plane 216 (Queenside): White Rook on b1 (SQ_B1 = 1)
        if (!(planes[216].mask & Stockfish::square_bb(Stockfish::SQ_B1))) {
            std::cerr << "[FAIL] Plane 216 should cover White Rook on b1!" << std::endl;
            std::exit(1);
        }
        // Plane 217 (Kingside): White Rook on i1 (SQ_I1 = 8)
        if (!(planes[217].mask & Stockfish::square_bb(Stockfish::SQ_I1))) {
            std::cerr << "[FAIL] Plane 217 should cover White Rook on i1!" << std::endl;
            std::exit(1);
        }
        // Verify Black castling rights
        // Plane 218 (Queenside): Black Rook on b10 (SQ_B10 = 109)
        if (!(planes[218].mask & Stockfish::square_bb(Stockfish::SQ_B10))) {
            std::cerr << "[FAIL] Plane 218 should cover Black Rook on b10!" << std::endl;
            std::exit(1);
        }
        // Plane 219 (Kingside): Black Rook on i10 (SQ_I10 = 116)
        if (!(planes[219].mask & Stockfish::square_bb(Stockfish::SQ_I10))) {
            std::cerr << "[FAIL] Plane 219 should cover Black Rook on i10!" << std::endl;
            std::exit(1);
        }
        
        std::cout << "  - [VERIFIED] Encoder writes castling rights to aux planes 216-219 correctly." << std::endl;
        
        // 4. ApplyMove: Kingside castling
        // King f1 (file 5) -> Destination h1 (file 7)
        // Rook i1 (file 8) -> Destination g1 (file 6)
        std::cout << "Applying Kingside castling (f1i1)..." << std::endl;
        board.ApplyMove(move_oo);
        
        const auto& raw_pos = board.GetRawPosition();
        if (raw_pos.piece_on(Stockfish::SQ_H1) != Stockfish::W_KING) {
            std::cerr << "[FAIL] After f1i1, White King is not on h1! Got: " << raw_pos.piece_on(Stockfish::SQ_H1) << std::endl;
            std::exit(1);
        }
        if (raw_pos.piece_on(Stockfish::SQ_G1) != Stockfish::W_ROOK) {
            std::cerr << "[FAIL] After f1i1, White Rook is not on g1! Got: " << raw_pos.piece_on(Stockfish::SQ_G1) << std::endl;
            std::exit(1);
        }
        std::cout << "  - [VERIFIED] ApplyMove executed Kingside castling correctly (King on h1, Rook on g1)." << std::endl;
        
        // Undo and test Queenside castling
        std::cout << "Undoing castling..." << std::endl;
        board.UndoMove();
        
        // Apply Queenside castling:
        // King f1 (file 5) -> Destination d1 (file 3)
        // Rook b1 (file 1) -> Destination e1 (file 4)
        std::cout << "Applying Queenside castling (f1b1)..." << std::endl;
        board.ApplyMove(move_ooo);
        
        if (raw_pos.piece_on(Stockfish::SQ_D1) != Stockfish::W_KING) {
            std::cerr << "[FAIL] After f1b1, White King is not on d1! Got: " << raw_pos.piece_on(Stockfish::SQ_D1) << std::endl;
            std::exit(1);
        }
        if (raw_pos.piece_on(Stockfish::SQ_E1) != Stockfish::W_ROOK) {
            std::cerr << "[FAIL] After f1b1, White Rook is not on e1! Got: " << raw_pos.piece_on(Stockfish::SQ_E1) << std::endl;
            std::exit(1);
        }
        std::cout << "  - [VERIFIED] ApplyMove executed Queenside castling correctly (King on d1, Rook on e1)." << std::endl;
        
        // 5. Test Black Castling with Flip logic
        std::cout << "Testing Black Castling (with Flip logic)..." << std::endl;
        std::string black_castling_fen = "1r3k2r1/10/10/10/10/10/10/10/10/1R3K2R1 b BIbi - 7+7 0 1";
        lczero::ChessBoard board_black(black_castling_fen);
        
        auto moves_black = board_black.GenerateLegalMoves();
        bool found_black_oo = false;
        bool found_black_ooo = false;
        lczero::Move move_black_oo = lczero::MOVE_NONE;
        lczero::Move move_black_ooo = lczero::MOVE_NONE;
        
        for (const auto& m : moves_black) {
            std::string m_str = board_black.MoveToString(m);
            if (m_str == "f10h10") {
                found_black_oo = true;
                move_black_oo = m;
            } else if (m_str == "f10d10") {
                found_black_ooo = true;
                move_black_ooo = m;
            }
        }
        
        if (!found_black_oo) {
            std::cerr << "[FAIL] Black Kingside castling f10h10 not found!" << std::endl;
            std::exit(1);
        }
        if (!found_black_ooo) {
            std::cerr << "[FAIL] Black Queenside castling f10d10 not found!" << std::endl;
            std::exit(1);
        }
        
        // Remap to NN index (should be mapped to the same index as White because it is flipped to White's perspective)
        uint16_t index_black_oo = lczero::MoveToNNIndex(move_black_oo, 0);
        uint16_t index_black_ooo = lczero::MoveToNNIndex(move_black_ooo, 0);
        
        if (index_black_oo != 2005) {
            std::cerr << "[FAIL] Black Kingside castling index mismatch! Expected 2005, got " << index_black_oo << std::endl;
            std::exit(1);
        }
        if (index_black_ooo != 5705) {
            std::cerr << "[FAIL] Black Queenside castling index mismatch! Expected 5705, got " << index_black_ooo << std::endl;
            std::exit(1);
        }
        std::cout << "  - [VERIFIED] Black castling moves map to identical indices (2005 and 5705) via Flip logic." << std::endl;
        
        // ApplyMove Black castling
        // Kingside: King f10 (file 5) -> Destination h10 (file 7)
        // Rook i10 (file 8) -> Destination g10 (file 6)
        std::cout << "Applying Black Kingside castling (f10h10)..." << std::endl;
        board_black.ApplyMove(move_black_oo);
        
        const auto& raw_pos_black = board_black.GetRawPosition();
        if (raw_pos_black.piece_on(Stockfish::SQ_H10) != Stockfish::B_KING) {
            std::cerr << "[FAIL] After f10h10, Black King is not on h10! Got: " << raw_pos_black.piece_on(Stockfish::SQ_H10) << std::endl;
            std::exit(1);
        }
        if (raw_pos_black.piece_on(Stockfish::SQ_G10) != Stockfish::B_ROOK) {
            std::cerr << "[FAIL] After f10h10, Black Rook is not on g10! Got: " << raw_pos_black.piece_on(Stockfish::SQ_G10) << std::endl;
            std::exit(1);
        }
        std::cout << "  - [VERIFIED] ApplyMove executed Black Kingside castling correctly (King on h10, Rook on g10)." << std::endl;
        
        // Undo and test Queenside
        std::cout << "Undoing Black castling..." << std::endl;
        board_black.UndoMove();
        
        std::cout << "Applying Black Queenside castling (f10d10)..." << std::endl;
        board_black.ApplyMove(move_black_ooo);
        if (raw_pos_black.piece_on(Stockfish::SQ_D10) != Stockfish::B_KING) {
            std::cerr << "[FAIL] After f10d10, Black King is not on d10! Got: " << raw_pos_black.piece_on(Stockfish::SQ_D10) << std::endl;
            std::exit(1);
        }
        if (raw_pos_black.piece_on(Stockfish::SQ_E10) != Stockfish::B_ROOK) {
            std::cerr << "[FAIL] After f10d10, Black Rook is not on e10! Got: " << raw_pos_black.piece_on(Stockfish::SQ_E10) << std::endl;
            std::exit(1);
        }
        std::cout << "  - [VERIFIED] ApplyMove executed Black Queenside castling correctly (King on d10, Rook on e10)." << std::endl;
        
        std::cout << "[PASS] TEST 7 passed! (Castling generation, encoding, and execution verified for White & Black)\n" << std::endl;
    }

    std::cout << "========================================" << std::endl;
    std::cout << "ALL CHESSBOARD BRIDGE TESTS PASSED!" << std::endl;
    std::cout << "========================================\n" << std::endl;
}

class MockComputation : public lczero::BackendComputation {
public:
    MockComputation() : enqueued_(0) {}
    size_t UsedBatchSize() const override { return enqueued_; }
    AddInputResult AddInput(const lczero::EvalPosition& pos, lczero::EvalResultPtr result) override {
        size_t num_legal = pos.legal_moves.size();
        if (num_legal > 0 && !result.p.empty()) {
            float prob = 1.0f / num_legal;
            for (size_t i = 0; i < num_legal && i < result.p.size(); ++i) {
                result.p[i] = prob;
            }
        }
        if (result.q) *result.q = 0.0f;
        if (result.d) *result.d = 1.0f;
        if (result.m) *result.m = 50.0f;
        enqueued_ = 1;
        return FETCHED_IMMEDIATELY;
    }
    void ComputeBlocking() override { enqueued_ = 0; }
private:
    size_t enqueued_;
};

class MockBackend : public lczero::Backend {
public:
    lczero::BackendAttributes GetAttributes() const override {
        return lczero::BackendAttributes{
            .has_mlh = false,
            .has_wdl = false,
            .runs_on_cpu = true,
            .suggested_num_search_threads = 1,
            .recommended_batch_size = 1,
            .maximum_batch_size = 1
        };
    }
    std::unique_ptr<lczero::BackendComputation> CreateComputation() override {
        return std::make_unique<MockComputation>();
    }
};

class TestUciResponder : public lczero::UciResponder {
public:
    void OutputBestMove(lczero::BestMoveInfo* info) override {
        std::cout << "[MCTS TEST] Bestmove: " << info->bestmove.ToString() << std::endl;
    }
    void OutputThinkingInfo(std::vector<lczero::ThinkingInfo>* infos) override {
        if (infos && !infos->empty()) {
            const auto& info = infos->front();
            std::cout << "[MCTS TEST] info depth " << info.depth 
                      << " seldepth " << info.seldepth 
                      << " nodes " << info.nodes 
                      << " nps " << info.nps 
                      << " score cp " << (info.score ? *info.score : 0);
            if (!info.pv.empty()) {
                std::cout << " pv";
                for (auto m : info.pv) {
                    std::cout << " " << m.ToString();
                }
            }
            std::cout << std::endl;
        }
    }
};

class NodeLimitStopper : public lczero::classic::SearchStopper {
public:
    NodeLimitStopper(int64_t max_nodes) : max_nodes_(max_nodes) {}
    bool ShouldStop(const lczero::classic::IterationStats& stats, lczero::classic::StoppersHints*) override {
        return stats.total_nodes >= max_nodes_;
    }
    void OnSearchDone(const lczero::classic::IterationStats&) override {}
private:
    int64_t max_nodes_;
};

void run_mcts_tests(const std::string& weights_path = "weights_0_elo.onnx") {
    std::cout << "\n========================================" << std::endl;
    std::cout << "RUNNING MCTS INTEGRATION TESTS..." << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << "Weights path: " << weights_path << std::endl;

    // Load custom variant
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

promotionRegionWhite = *8 *9 *10
promotionRegionBlack = *3 *2 *1
mandatoryPawnPromotion = true
promotionPieceTypes = b h m n v y

castling = true
castlingKingsideFile = h
castlingQueensideFile = d
castlingRookKingsideFile = i
castlingRookQueensideFile = b

stalemateValue = loss
checkCounting = true
)";

    std::istringstream ss(ini_text);
    variants.parse_istream<false>(ss);

    const Variant* v = variants.find("custom_10x10_variant")->second;
    if (!v) {
        std::cerr << "[FAIL] Failed to find custom_10x10_variant!" << std::endl;
        std::exit(1);
    }
    UCI::init_variant(v);
    PSQT::init(v);

    // 1. Dựng thế cờ 10x10 variant
    std::string fen = "vrhabkberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHABKBERV w BIbi - 7+7 0 1";
    lczero::ChessBoard board(fen);
    
    // 2. Setup options
    lczero::OptionsParser parser;
    lczero::classic::SearchParams::Populate(&parser);
    parser.GetMutableDefaultsOptions()->Set<float>(lczero::SharedBackendParams::kPolicySoftmaxTemp, 1.0f);
    parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kHistoryFill, "no");
    
    // Kích hoạt Nhiễu Dirichlet và Nhiệt độ cực đại để tạo ngẫu nhiên tuyệt đối
    parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kNoiseEpsilonId, 1.0f);
    parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kNoiseAlphaId, 0.3f);
    parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kTemperatureId, 10.0f);
    parser.GetMutableDefaultsOptions()->Set<int>(lczero::classic::BaseSearchParams::kTempDecayMovesId, 15);
    
    parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kWeightsId, weights_path);
    parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kBackendOptionsId, "threads=4,inter_op_threads=2");
    const lczero::OptionsDict& options = parser.GetOptionsDict();
    
    std::unique_ptr<lczero::Backend> backend;
    try {
        auto raw_backend = std::make_unique<lczero::OnnxBackend>();
        raw_backend->UpdateConfiguration(options);
        backend = lczero::CreateMemCache(std::move(raw_backend), options);
        std::cout << "[MCTS TEST] Loaded OnnxBackend successfully." << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "[MCTS TEST] Error loading OnnxBackend: " << e.what() << std::endl;
        std::cerr << "[MCTS TEST] Falling back to MockBackend!" << std::endl;
        backend = std::make_unique<MockBackend>();
    }

    std::cout << "Starting 5 MCTS test runs (800 playouts) with 100% Noise & Temp=10.0..." << std::endl;
    std::cout << "RNG Test: " << lczero::Random::Get().GetFloat(1.0f) << ", " 
              << lczero::Random::Get().GetFloat(1.0f) << ", " 
              << lczero::Random::Get().GetFloat(1.0f) << std::endl;
    
    std::vector<std::string> best_moves;
    for (int run = 1; run <= 5; ++run) {
        auto tree = std::make_unique<lczero::classic::NodeTree>();
        tree->ResetToPosition(fen, {}); // set to FEN
        
        auto uci_responder = std::make_unique<TestUciResponder>();
        auto stopper = std::make_unique<NodeLimitStopper>(800); // Stop after 800 nodes
        auto start_time = std::chrono::steady_clock::now();
        
        auto search = std::make_unique<lczero::classic::Search>(
            *tree,
            backend.get(),
            std::move(uci_responder),
            lczero::MoveList{},
            start_time,
            std::move(stopper),
            false, // infinite
            false, // ponder
            options,
            nullptr // syzygy_tb
        );
        
        search->RunBlocking(4); // Run search on 4 threads
        
        auto result = search->GetBestMove();
        best_moves.push_back(result.first.ToString());
        std::cout << "[RUN " << run << "] Finished playouts: " << search->GetTotalPlayouts() 
                  << " | Best move: " << result.first.ToString() << " (RNG: " << lczero::Random::Get().GetFloat(1.0f) << ")" << std::endl;
    }

    std::cout << "\n=== MCTS RANDOMNESS TEST RESULTS ===" << std::endl;
    for (size_t i = 0; i < best_moves.size(); ++i) {
        std::cout << "Run " << (i + 1) << ": " << best_moves[i] << std::endl;
    }
    std::cout << "====================================" << std::endl;
}

// Silent responder to avoid search log spam during the T2 test.
class SilentUciResponder : public lczero::UciResponder {
public:
    void OutputBestMove(lczero::BestMoveInfo*) override {}
    void OutputThinkingInfo(std::vector<lczero::ThinkingInfo>*) override {}
};

// T2: extract pi (from visits) + policy_kld (from raw NN prior) + z (parity).
// Plays a short game and verifies: sum(pi) == 1.0, policy_kld finite & >= 0,
// and z assigned with correct side-to-move parity.
void run_extract_tests(const std::string& weights_path = "weights_0_elo.onnx") {
    std::cout << "\n========================================" << std::endl;
    std::cout << "RUNNING T2 (EXTRACT pi / policy_kld / z) TESTS..." << std::endl;
    std::cout << "========================================\n" << std::endl;

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
promotionRegionWhite = *8 *9 *10
promotionRegionBlack = *3 *2 *1
mandatoryPawnPromotion = true
promotionPieceTypes = b h m n v y
castling = true
castlingKingsideFile = h
castlingQueensideFile = d
castlingRookKingsideFile = i
castlingRookQueensideFile = b
stalemateValue = loss
checkCounting = true
)";
    std::istringstream ss(ini_text);
    variants.parse_istream<false>(ss);
    const Variant* v = variants.find("custom_10x10_variant")->second;
    if (!v) { std::cerr << "[FAIL] custom_10x10_variant not found!" << std::endl; std::exit(1); }
    UCI::init_variant(v);
    PSQT::init(v);

    std::string fen = "vrhabkberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHABKBERV w BIbi - 7+7 0 1";

    lczero::OptionsParser parser;
    lczero::classic::SearchParams::Populate(&parser);
    parser.GetMutableDefaultsOptions()->Set<float>(lczero::SharedBackendParams::kPolicySoftmaxTemp, 1.0f);
    parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kHistoryFill, "no");
    parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kNoiseEpsilonId, 0.25f);
    parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kNoiseAlphaId, 0.3f);
    parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kWeightsId, weights_path);
    parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kBackendOptionsId, "threads=2");
    const lczero::OptionsDict& options = parser.GetOptionsDict();

    std::unique_ptr<lczero::Backend> backend;
    bool has_cache = true;
    try {
        auto raw_backend = std::make_unique<lczero::OnnxBackend>();
        raw_backend->UpdateConfiguration(options);
        backend = lczero::CreateMemCache(std::move(raw_backend), options);
        std::cout << "[T2] OnnxBackend + MemCache loaded." << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "[T2] OnnxBackend failed (" << e.what()
                  << "); using MockBackend (no cache, kld=0)." << std::endl;
        backend = std::make_unique<MockBackend>();
        has_cache = false;
    }

    auto tree = std::make_unique<lczero::classic::NodeTree>();
    tree->ResetToPosition(fen, {});

    std::vector<lczero::TrainingDataV1> records;
    std::vector<bool> stm_black;
    const int kMaxMoves = 6;
    const int kVisits = 64;
    lczero::GameResult final_result = lczero::GameResult::UNDECIDED;

    for (int m = 0; m < kMaxMoves; ++m) {
        auto responder = std::make_unique<SilentUciResponder>();
        auto stopper = std::make_unique<NodeLimitStopper>(kVisits);
        auto start = std::chrono::steady_clock::now();
        auto search = std::make_unique<lczero::classic::Search>(
            *tree, backend.get(), std::move(responder), lczero::MoveList{},
            start, std::move(stopper), false, false, options, nullptr);
        search->RunBlocking(2);

        lczero::classic::Node* root = tree->GetCurrentHead();
        lczero::TrainingDataV1 rec;
        std::memset(&rec, 0, sizeof(rec));
        rec.version = lczero::kTrainingDataVersion;
        rec.input_format = lczero::kInputFormat10x10;
        bool black = tree->IsBlackToMove();
        rec.side_to_move = black ? 1 : 0;

        lczero::Move best = lczero::FillSearchTargets(
            root, tree->GetPositionHistory(), backend.get(), rec);

        double sum = 0.0;
        for (int i = 0; i < lczero::kPolicySize; ++i) sum += rec.probabilities[i];
        if (std::abs(sum - 1.0) > 1e-3) {
            std::cerr << "[FAIL] move " << m << ": sum(pi) = " << sum
                      << " (expected 1.0)" << std::endl;
            std::exit(1);
        }
        if (!std::isfinite(rec.policy_kld) || rec.policy_kld < -1e-6f) {
            std::cerr << "[FAIL] move " << m << ": invalid policy_kld = "
                      << rec.policy_kld << std::endl;
            std::exit(1);
        }
        std::cout << "  move " << m << " (" << (black ? "black" : "white")
                  << "): sum(pi)=" << sum << " visits=" << rec.visits
                  << " root_q=" << rec.root_q << " best_q=" << rec.best_q
                  << " orig_q=" << rec.orig_q << " kld=" << rec.policy_kld
                  << std::endl;

        records.push_back(rec);
        stm_black.push_back(black);

        tree->MakeMove(best);
        lczero::GameResult r = tree->GetPositionHistory().ComputeGameResult();
        if (r != lczero::GameResult::UNDECIDED) { final_result = r; break; }
    }

    if (records.empty()) { std::cerr << "[FAIL] no records produced!" << std::endl; std::exit(1); }
    std::cout << "[PASS] sum(pi)==1.0 and policy_kld valid for all "
              << records.size() << " positions." << std::endl;
    if (has_cache) {
        bool any_positive = false;
        for (const auto& r : records) if (r.policy_kld > 0.0f) any_positive = true;
        std::cout << (any_positive
            ? "  policy_kld > 0 observed (search diverged from raw NN prior). OK."
            : "  [WARN] all policy_kld == 0 (possible cache miss).") << std::endl;
    }

    // z parity: use the real outcome if the game ended, else inject WHITE_WON
    // purely to exercise AssignResult's parity logic.
    lczero::GameResult test_result =
        (final_result != lczero::GameResult::UNDECIDED) ? final_result
                                                        : lczero::GameResult::WHITE_WON;
    std::cout << "  Assigning z with result=" << (int)test_result
              << (final_result == lczero::GameResult::UNDECIDED
                      ? " (injected for parity test)" : " (actual game result)")
              << std::endl;
    for (size_t i = 0; i < records.size(); ++i)
        lczero::AssignResult(records[i], test_result, stm_black[i]);

    for (size_t i = 0; i < records.size(); ++i) {
        const float q = records[i].result_q, d = records[i].result_d;
        if (test_result == lczero::GameResult::DRAW) {
            if (q != 0.0f || d != 1.0f) {
                std::cerr << "[FAIL] draw z wrong at " << i << std::endl; std::exit(1);
            }
        } else {
            const bool white_won = (test_result == lczero::GameResult::WHITE_WON);
            const bool stm_white = !stm_black[i];
            const float expected = (white_won == stm_white) ? 1.0f : -1.0f;
            if (q != expected || d != 0.0f) {
                std::cerr << "[FAIL] z parity wrong at " << i << ": stm_black="
                          << stm_black[i] << " got q=" << q << " expected " << expected << std::endl;
                std::exit(1);
            }
        }
    }
    std::cout << "[PASS] z parity correct for all positions." << std::endl;

    std::cout << "\n========================================" << std::endl;
    std::cout << "ALL T2 (EXTRACT) TESTS PASSED!" << std::endl;
    std::cout << "========================================\n" << std::endl;
}

// T3: full self-play game -> writes all positions to a .gz, then verifies the
// file round-trips with a result assigned to every record.
void run_selfplay_tests(const std::string& weights_path = "weights_0_elo.onnx") {
    std::cout << "\n========================================" << std::endl;
    std::cout << "RUNNING T3 (SELF-PLAY 1 GAME) TESTS..." << std::endl;
    std::cout << "========================================\n" << std::endl;

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
promotionRegionWhite = *8 *9 *10
promotionRegionBlack = *3 *2 *1
mandatoryPawnPromotion = true
promotionPieceTypes = b h m n v y
castling = true
castlingKingsideFile = h
castlingQueensideFile = d
castlingRookKingsideFile = i
castlingRookQueensideFile = b
stalemateValue = loss
checkCounting = true
)";
    std::istringstream ss(ini_text);
    variants.parse_istream<false>(ss);
    const Variant* v = variants.find("custom_10x10_variant")->second;
    if (!v) { std::cerr << "[FAIL] custom_10x10_variant not found!" << std::endl; std::exit(1); }
    UCI::init_variant(v);
    PSQT::init(v);

    std::string fen = "vrhabkberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHABKBERV w BIbi - 7+7 0 1";

    lczero::OptionsParser parser;
    lczero::classic::SearchParams::Populate(&parser);
    parser.GetMutableDefaultsOptions()->Set<float>(lczero::SharedBackendParams::kPolicySoftmaxTemp, 1.0f);
    parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kHistoryFill, "no");
    parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kNoiseEpsilonId, 0.25f);
    parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kNoiseAlphaId, 0.3f);
    parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kWeightsId, weights_path);
    parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kBackendOptionsId, "threads=2");
    const lczero::OptionsDict& options = parser.GetOptionsDict();

    std::unique_ptr<lczero::Backend> backend;
    try {
        auto raw_backend = std::make_unique<lczero::OnnxBackend>();
        raw_backend->UpdateConfiguration(options);
        backend = lczero::CreateMemCache(std::move(raw_backend), options);
        std::cout << "[T3] OnnxBackend + MemCache loaded." << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "[T3] OnnxBackend failed (" << e.what()
                  << "); using MockBackend." << std::endl;
        backend = std::make_unique<MockBackend>();
    }

    const std::string out_file =
        std::string("test_selfplay_game") + lczero::TrainingDataWriter::Extension();

    std::cout << "Playing 1 game (visits=32, max_moves=30, temp_cutoff_ply=8)..." << std::endl;
    lczero::GameResult result = lczero::PlayOneGame(
        fen, backend.get(), options, /*visits=*/32, /*max_moves=*/30,
        /*temp_cutoff_ply=*/8, out_file, /*search_threads=*/2);
    std::cout << "Game finished: result=" << (int)result << ", file=" << out_file << std::endl;

    // --- Verify the file round-trips and every record is valid ---
    std::vector<lczero::TrainingDataV1> recs;
    if (!lczero::ReadTrainingData(out_file, recs)) {
        std::cerr << "[FAIL] Could not read back " << out_file << std::endl; std::exit(1);
    }
    if (recs.empty()) { std::cerr << "[FAIL] No records in file!" << std::endl; std::exit(1); }

    for (size_t i = 0; i < recs.size(); ++i) {
        const auto& r = recs[i];
        if (r.version != lczero::kTrainingDataVersion ||
            r.input_format != lczero::kInputFormat10x10) {
            std::cerr << "[FAIL] rec " << i << ": bad version/input_format" << std::endl; std::exit(1);
        }
        double sum = 0.0;
        for (int k = 0; k < lczero::kPolicySize; ++k) sum += r.probabilities[k];
        if (std::abs(sum - 1.0) > 1e-3) {
            std::cerr << "[FAIL] rec " << i << ": sum(pi)=" << sum << std::endl; std::exit(1);
        }
        const bool z_draw = (r.result_d == 1.0f && r.result_q == 0.0f);
        const bool z_decisive = (r.result_d == 0.0f && (r.result_q == 1.0f || r.result_q == -1.0f));
        if (!z_draw && !z_decisive) {
            std::cerr << "[FAIL] rec " << i << ": z not assigned (q=" << r.result_q
                      << " d=" << r.result_d << ")" << std::endl; std::exit(1);
        }
    }

    // The first (startpos) record must have non-empty piece planes (pieces exist).
    bool any_plane = false;
    for (int p = 0; p < 26; ++p)
        if (recs[0].piece_planes[p][0] != 0 || recs[0].piece_planes[p][1] != 0) any_plane = true;
    if (!any_plane) {
        std::cerr << "[FAIL] startpos record has all-empty piece planes!" << std::endl; std::exit(1);
    }

    std::cout << "  Records written/read: " << recs.size()
              << " | side_to_move[0]=" << (int)recs[0].side_to_move
              << " rule50[0]=" << (int)recs[0].rule50_count
              << " checks_us[0]=" << (int)recs[0].checks_remaining_us
              << " castle_us_oo_file[0]=" << (int)recs[0].castling_us_oo_file
              << std::endl;
    std::cout << "[PASS] All " << recs.size()
              << " records valid (pi=1, z assigned, planes non-empty)." << std::endl;

    std::remove(out_file.c_str());

    std::cout << "\n========================================" << std::endl;
    std::cout << "ALL T3 (SELF-PLAY) TESTS PASSED!" << std::endl;
    std::cout << "========================================\n" << std::endl;
}

void run_policy_tests() {
    std::cout << "\n========================================" << std::endl;
    std::cout << "RUNNING POLICY ENCODER/DECODER BIJECTION TESTS..." << std::endl;
    std::cout << "========================================\n" << std::endl;

    int total_tested = 0;
    int valid_decoded = 0;
    int mismatches = 0;

    for (int idx = 0; idx < 10600; ++idx) {
        total_tested++;
        Stockfish::Move move = lczero::MoveFromNNIndex(idx, 0);
        if (move == Stockfish::MOVE_NONE) {
            continue; // Not a valid square-move combination on 10x10 board (e.g. sliding out of bounds)
        }

        valid_decoded++;
        uint16_t re_encoded = lczero::MoveToNNIndex(move, 0);
        if (re_encoded != idx) {
            mismatches++;
            std::cout << "Mismatch found at index " << idx << ":" << std::endl;
            std::cout << "  Decoded Move: " << move << " (from " << Stockfish::from_sq(move) << " to " << Stockfish::to_sq(move) << ")" << std::endl;
            std::cout << "  Re-encoded Index: " << re_encoded << std::endl;
        }
    }

    std::cout << "Total Policy Indices: " << total_tested << std::endl;
    std::cout << "Valid 10x10 Moves Decoded: " << valid_decoded << std::endl;
    std::cout << "Mismatches: " << mismatches << std::endl;

    if (mismatches == 0) {
        std::cout << "\n[PASS] POLICY BIJECTION TEST PASSED SUCCESSFULLY!" << std::endl;
    } else {
        std::cerr << "\n[FAIL] POLICY BIJECTION TEST FAILED WITH " << mismatches << " MISMATCHES!" << std::endl;
        std::exit(1);
    }
}

// Fills every byte of a record with a deterministic, record-specific pattern so
// the round-trip compares all 45940 bytes (not just a few named fields).
static void fill_deterministic(lczero::TrainingDataV1& rec, int seed) {
    auto* bytes = reinterpret_cast<uint8_t*>(&rec);
    for (size_t k = 0; k < sizeof(rec); ++k) {
        bytes[k] = static_cast<uint8_t>((seed * 131 + static_cast<int>(k) * 7 + 17) & 0xFF);
    }
    // Set a couple of named fields to sane values for human-readable sanity.
    rec.version = lczero::kTrainingDataVersion;
    rec.input_format = lczero::kInputFormat10x10;
}

// T1: verify TrainingDataV1 layout (45940 bytes) and Writer/Reader round-trip.
void run_trainingdata_tests() {
    std::cout << "\n========================================" << std::endl;
    std::cout << "RUNNING TRAINING DATA (T1) TESTS..." << std::endl;
    std::cout << "========================================\n" << std::endl;

    // TEST 1: struct layout size is locked at 45940 bytes.
    std::cout << "TEST 1: sizeof(TrainingDataV1) = " << sizeof(lczero::TrainingDataV1)
              << " (expected 45940)" << std::endl;
    if (sizeof(lczero::TrainingDataV1) != 45940) {
        std::cerr << "[FAIL] Unexpected struct size!" << std::endl;
        std::exit(1);
    }
    std::cout << "[PASS] TEST 1: layout size correct.\n" << std::endl;

    // TEST 2: write N records, read them back, compare bit-for-bit.
    std::cout << "TEST 2: Writer/Reader round-trip (bit-exact)..." << std::endl;
    const int kNumRecords = 5;
    std::vector<lczero::TrainingDataV1> originals(kNumRecords);
    for (int n = 0; n < kNumRecords; ++n) fill_deterministic(originals[n], n + 1);

    std::string fname =
        std::string("test_trainingdata_t1") + lczero::TrainingDataWriter::Extension();

    {
        lczero::TrainingDataWriter writer(fname);
        if (!writer.IsOpen()) {
            std::cerr << "[FAIL] Could not open output file: " << fname << std::endl;
            std::exit(1);
        }
        for (const auto& r : originals) writer.WriteChunk(r);
        writer.Finalize();
    }
    std::cout << "  - Wrote " << kNumRecords << " records to " << fname << std::endl;

    std::vector<lczero::TrainingDataV1> readback;
    if (!lczero::ReadTrainingData(fname, readback)) {
        std::cerr << "[FAIL] ReadTrainingData failed (open or truncated)!" << std::endl;
        std::exit(1);
    }
    if (readback.size() != originals.size()) {
        std::cerr << "[FAIL] Record count mismatch: wrote " << originals.size()
                  << ", read " << readback.size() << std::endl;
        std::exit(1);
    }
    for (int n = 0; n < kNumRecords; ++n) {
        if (std::memcmp(&originals[n], &readback[n], sizeof(lczero::TrainingDataV1)) != 0) {
            std::cerr << "[FAIL] Record " << n << " differs after round-trip!" << std::endl;
            std::exit(1);
        }
    }
    std::remove(fname.c_str());
    std::cout << "  - Read back " << readback.size()
              << " records, all bytes match." << std::endl;
    std::cout << "[PASS] TEST 2: round-trip bit-exact.\n" << std::endl;

    std::cout << "========================================" << std::endl;
    std::cout << "ALL TRAINING DATA (T1) TESTS PASSED!" << std::endl;
    std::cout << "========================================\n" << std::endl;
}

// Parses + registers the custom 10x10 variant from an inline ini (so self-play
// and tests don't depend on an external variants.ini being loaded).
static const Variant* setup_custom_variant() {
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
promotionRegionWhite = *8 *9 *10
promotionRegionBlack = *3 *2 *1
mandatoryPawnPromotion = true
promotionPieceTypes = b h m n v y
castling = true
castlingKingsideFile = h
castlingQueensideFile = d
castlingRookKingsideFile = i
castlingRookQueensideFile = b
stalemateValue = loss
checkCounting = true
)";
    std::istringstream ss(ini_text);
    variants.parse_istream<false>(ss);
    const Variant* v = variants.find("custom_10x10_variant")->second;
    if (!v) {
        std::cerr << "[FATAL] custom_10x10_variant not found!" << std::endl;
        std::exit(1);
    }
    UCI::init_variant(v);
    PSQT::init(v);
    return v;
}

int main(int argc, char* argv[]) {
    bool test_mcts_mode = false;
    bool selfplay_mode = false;
    bool test_ep_mode = false;
    bool test_board_mode = false;
    bool test_policy_mode = false;
    bool test_trainingdata_mode = false;
    bool test_extract_mode = false;
    bool test_selfplay_mode = false;
    std::string weights_file = "weights_0_elo.onnx";
    // Self-play driver options.
    int sp_games = 100, sp_visits = 200, sp_parallel = 1, sp_threads_per_game = 1;
    int sp_max_moves = 200, sp_temp_cutoff = 30;
    std::string sp_out = "selfplay_data";
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
        } else if (std::string(argv[i]) == "--test-mcts") {
            test_mcts_mode = true;
            if (i + 1 < argc && argv[i + 1][0] != '-') {
                weights_file = argv[i + 1];
            }
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
    } else if (test_mcts_mode) {
        run_mcts_tests(weights_file);
    } else if (selfplay_mode) {
        std::cout << "=== Self-play data generation ===" << std::endl;
        setup_custom_variant();
        const std::string fen =
            "vrhabkberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHABKBERV w BIbi - 7+7 0 1";

        lczero::OptionsParser parser;
        lczero::classic::SearchParams::Populate(&parser);
        parser.GetMutableDefaultsOptions()->Set<float>(lczero::SharedBackendParams::kPolicySoftmaxTemp, 1.0f);
        parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kHistoryFill, "no");
        parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kNoiseEpsilonId, 0.25f);
        parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kNoiseAlphaId, 0.3f);
        parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kWeightsId, weights_file);
        parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kBackendOptionsId, "threads=2");
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
        cfg.start_fen = fen;
        cfg.out_dir = sp_out;
        cfg.num_games = sp_games;
        cfg.visits = sp_visits;
        cfg.max_moves = sp_max_moves;
        cfg.temp_cutoff_ply = sp_temp_cutoff;
        cfg.parallel = sp_parallel;
        cfg.threads_per_game = sp_threads_per_game;
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
