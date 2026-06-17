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

promotionRegionWhite = *9 *10
promotionRegionBlack = *2 *1
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

promotionRegionWhite = *9 *10
promotionRegionBlack = *2 *1
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
    std::string fen = "vrhabkberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHABKBERV w - - 7+7 0 1";
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
        lczero::classic::NodeTree tree;
        tree.ResetToPosition(fen, {}); // set to FEN
        
        auto uci_responder = std::make_unique<TestUciResponder>();
        auto stopper = std::make_unique<NodeLimitStopper>(800); // Stop after 800 nodes
        auto start_time = std::chrono::steady_clock::now();
        
        lczero::classic::Search search(
            tree,
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
        
        search.RunBlocking(4); // Run search on 4 threads
        
        auto result = search.GetBestMove();
        best_moves.push_back(result.first.ToString());
        std::cout << "[RUN " << run << "] Finished playouts: " << search.GetTotalPlayouts() 
                  << " | Best move: " << result.first.ToString() << " (RNG: " << lczero::Random::Get().GetFloat(1.0f) << ")" << std::endl;
    }

    std::cout << "\n=== MCTS RANDOMNESS TEST RESULTS ===" << std::endl;
    for (size_t i = 0; i < best_moves.size(); ++i) {
        std::cout << "Run " << (i + 1) << ": " << best_moves[i] << std::endl;
    }
    std::cout << "====================================" << std::endl;
}

int main(int argc, char* argv[]) {
    bool test_mcts_mode = false;
    bool selfplay_mode = false;
    bool test_ep_mode = false;
    bool test_board_mode = false;
    std::string weights_file = "weights_0_elo.onnx";
    for (int i = 1; i < argc; ++i) {
        if (std::string(argv[i]) == "--selfplay") {
            selfplay_mode = true;
        } else if (std::string(argv[i]) == "--test-ep") {
            test_ep_mode = true;
        } else if (std::string(argv[i]) == "--test-board") {
            test_board_mode = true;
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
    } else if (test_mcts_mode) {
        run_mcts_tests(weights_file);
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
