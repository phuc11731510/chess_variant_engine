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
#include "tests/engine_tests.h"
#include "app/variant_setup.h"
#include "app/uci_coords.h"
#include "app/search_support.h"


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
promotionPieceTypes = b m n r v y

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
        
        // Xác minh mặt phẳng 1 (us KNIGHT): startpos có 2 Mã trắng ở e2,f2
        // => tensor index 14 (rank1,file4) và 15 (rank1,file5) phải là 1.0f, còn lại 0.0f.
        // (Đây là kiểm tra trực tiếp việc encode quân cờ — chính chỗ trước đây bị lỗi
        //  value=0.0f khiến mọi plane quân cờ bung ra toàn 0.)
        const float* plane1_start = float_planes.data() + 1 * plane_size;
        for (int i = 0; i < plane_size; ++i) {
            float expected = (i == 14 || i == 15) ? 1.0f : 0.0f;
            if (plane1_start[i] != expected) {
                std::cerr << "[FAIL] Plane 1 (knight) index " << i << " should be "
                          << expected << ", got " << plane1_start[i] << std::endl;
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

void run_mcts_tests(const std::string& weights_path) {
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
promotionPieceTypes = b m n r v y

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
    std::string fen = "vrhbakberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHBAKBERV w BIbi - 7+7 0 1";
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

// T2: extract pi (from visits) + policy_kld (from raw NN prior) + z (parity).
// Plays a short game and verifies: sum(pi) == 1.0, policy_kld finite & >= 0,
// and z assigned with correct side-to-move parity.
void run_extract_tests(const std::string& weights_path) {
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
promotionPieceTypes = b m n r v y
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

    std::string fen = "vrhbakberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHBAKBERV w BIbi - 7+7 0 1";

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

        double sum = 0.0;  // sum over LEGAL-visited moves (pi<0 = illegal sentinel)
        for (int i = 0; i < lczero::kPolicySize; ++i)
            if (rec.probabilities[i] > 0.0f) sum += rec.probabilities[i];
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
void run_selfplay_tests(const std::string& weights_path) {
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
promotionPieceTypes = b m n r v y
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

    std::string fen = "vrhbakberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHBAKBERV w BIbi - 7+7 0 1";

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
        double sum = 0.0;  // sum over LEGAL-visited moves (pi<0 = illegal sentinel)
        for (int k = 0; k < lczero::kPolicySize; ++k)
            if (r.probabilities[k] > 0.0f) sum += r.probabilities[k];
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
void run_roundtrip_emit(const std::string& prefix) {
    std::cout << "=== Emitting round-trip ground-truth data ===" << std::endl;
    setup_custom_variant();

    lczero::TrainingDataWriter writer(prefix + "_records.gz");
    std::ofstream dense_out(prefix + "_dense.bin", std::ios::binary);
    if (!dense_out) { std::cerr << "[FAIL] cannot open dense output" << std::endl; std::exit(1); }
    int num_cases = 0;

    auto emit = [&](const lczero::PositionHistory& h) {
        lczero::InputPlanes planes;
        int t = 0;
        lczero::EncodePositionForNN(h, lczero::kMoveHistory,
                                    lczero::FillEmptyHistory::FEN_ONLY, &planes, &t);
        std::vector<float> dense(226 * 100, 0.0f);
        lczero::UnpackInputPlanes(planes, dense.data(), 10, 10);
        dense_out.write(reinterpret_cast<const char*>(dense.data()),
                        dense.size() * sizeof(float));

        lczero::TrainingDataV1 rec;
        std::memset(&rec, 0, sizeof(rec));
        rec.version = lczero::kTrainingDataVersion;
        rec.input_format = lczero::kInputFormat10x10;
        lczero::EncodePlanesIntoRecord(h, rec);
        // Synthetic scalar/policy fields to verify field-level unpack in Python.
        rec.probabilities[100] = 0.25f;
        rec.probabilities[2005] = 0.75f;
        rec.result_q = -1.0f; rec.result_d = 0.0f;
        rec.root_q = 0.1f; rec.best_q = 0.5f; rec.orig_q = 0.123f;
        rec.policy_kld = 0.456f; rec.visits = 777;
        rec.played_idx = 2005; rec.best_idx = 2005;
        writer.WriteChunk(rec);
        ++num_cases;
    };

    // Case 0: startpos (white to move, castling BIbi, checks 7+7, no ep).
    {
        auto board = std::make_unique<lczero::ChessBoard>();
        auto h = std::make_unique<lczero::PositionHistory>();
        h->Reset(*board, 0, 1);
        emit(*h);
    }
    // Case 1: black to move with an active Sergeant en-passant (no castling).
    {
        auto board = std::make_unique<lczero::ChessBoard>(
            std::string("5k4/10/10/10/10/1s8/10/S9/10/5K4 w - - 7+7 0 1"));
        auto h = std::make_unique<lczero::PositionHistory>();
        h->Reset(*board, 0, 1);
        lczero::Move m = board->ParseMove("a3c5");
        if (!m.is_null()) h->Append(m);
        emit(*h);
    }
    // Case 2: position after several moves -> populates HISTORY plies 1-7.
    // This exercises the LightweightPosition board snapshot + per-ply flip path
    // (which T5's startpos/ep cases barely touched).
    {
        auto board = std::make_unique<lczero::ChessBoard>();
        auto h = std::make_unique<lczero::PositionHistory>();
        h->Reset(*board, 0, 1);
        for (int k = 0; k < 7; ++k) {
            lczero::MoveList lm = h->Last().GenerateLegalMoves();
            if (lm.empty()) break;
            h->Append(lm[0]);  // deterministic: first legal move
        }
        emit(*h);
    }

    writer.Finalize();
    dense_out.close();
    std::cout << "[roundtrip] Emitted " << num_cases << " cases -> "
              << prefix << "_records.gz / " << prefix << "_dense.bin" << std::endl;
}

// ============================================================================
// PERFT cross-check: validates the ADAPTER move mechanics (GenerateLegalMoves +
// flip + ApplyMove + board copy) against RAW Fairy-Stockfish (do_move/undo_move).
// Both use the same movegen, so any node-count mismatch == an adapter-layer bug
// in flip / state handling / copy. This is the gold-standard test for the FS
// boundary that a random NN can never expose.
// ============================================================================
static uint64_t perft_raw(Stockfish::Position& pos, int depth) {
    if (depth == 0) return 1;
    uint64_t nodes = 0;
    Stockfish::StateInfo st;
    for (const auto& em : Stockfish::MoveList<Stockfish::LEGAL>(pos)) {
        if (depth == 1) { ++nodes; continue; }
        pos.do_move(em.move, st);
        nodes += perft_raw(pos, depth - 1);
        pos.undo_move(em.move);
    }
    return nodes;
}

static uint64_t perft_adapter(const lczero::ChessBoard& board, int depth) {
    if (depth == 0) return 1;
    lczero::MoveList moves = board.GenerateLegalMoves();
    if (depth == 1) return moves.size();
    uint64_t nodes = 0;
    for (size_t i = 0; i < moves.size(); ++i) {
        lczero::ChessBoard child(board);     // copy (mirrors MCTS hot path)
        child.ApplyMove(moves[i]);           // flips internally for Black
        nodes += perft_adapter(child, depth - 1);
    }
    return nodes;
}

void run_perft_tests() {
    std::cout << "\n=== PERFT cross-check (adapter path vs raw Fairy-Stockfish) ===" << std::endl;
    const Variant* v = setup_custom_variant();

    struct Case { const char* fen; int max_depth; };
    const std::vector<Case> cases = {
        {lczero::ChessBoard::kStartposFen, 3},
        {"5k4/10/10/10/10/1s8/10/S9/10/5K4 w - - 7+7 0 1", 4},        // sparse: Sergeant + kings
        {"5k4/10/10/10/4p5/4P5/10/10/10/5K4 w - - 7+7 0 1", 4},       // pawn tension
    };

    bool all_ok = true;
    for (const auto& c : cases) {
        lczero::ChessBoard board(std::string(c.fen));   // adapter board (reused; perft copies)
        std::cout << "FEN: " << c.fen << std::endl;
        for (int d = 1; d <= c.max_depth; ++d) {
            Stockfish::StateInfo st;
            Stockfish::Position pos;
            pos.set(v, c.fen, false, &st, nullptr);     // fresh raw pos per depth
            const uint64_t raw = perft_raw(pos, d);
            const uint64_t adp = perft_adapter(board, d);
            const bool ok = (raw == adp);
            all_ok &= ok;
            std::cout << "  depth " << d << ": raw=" << raw << " adapter=" << adp
                      << (ok ? "  OK" : "  *** MISMATCH ***") << std::endl;
        }
    }
    if (all_ok) {
        std::cout << "\n[PASS] PERFT: adapter path matches raw Fairy-Stockfish at all depths." << std::endl;
    } else {
        std::cerr << "\n[FAIL] PERFT mismatch — adapter wrapping diverges from raw FS!" << std::endl;
        std::exit(1);
    }
}

// ============================================================================
// BIT-LEVEL verification (paranoid): proves the raw bit handling of the 128-bit
// Bitboard <-> serialized [lo,hi] words, and that every piece lands on exactly
// the right plane bit. A wrong bit-shift / lo-hi swap / overlap is caught here.
// ============================================================================
void run_bits_tests() {
    std::cout << "\n=== BIT-LEVEL verification (extreme paranoia) ===" << std::endl;
    setup_custom_variant();

    const Stockfish::Bitboard low64 = Stockfish::Bitboard(0xFFFFFFFFFFFFFFFFULL);
    // Cast via unsigned long long first to avoid the ambiguous Bitboard->uint64_t
    // conversion on Linux (where uint64_t = unsigned long). See training_extract.cc.
    auto split = [&](const Stockfish::Bitboard& m, uint64_t out[2]) {
        out[0] = static_cast<uint64_t>(static_cast<unsigned long long>(m & low64));  // squares 0-63
        out[1] = static_cast<uint64_t>(static_cast<unsigned long long>(m >> 64));    // squares 64-127
    };

    // E1: square_bb(s) must serialize to EXACTLY bit s for all 120 squares
    // (covers the 64-bit word boundary and the high word).
    {
        bool ok = true;
        for (int s = 0; s < 120; ++s) {
            Stockfish::Bitboard b = Stockfish::square_bb(static_cast<Stockfish::Square>(s));
            uint64_t w[2];
            split(b, w);
            int bits = __builtin_popcountll(w[0]) + __builtin_popcountll(w[1]);
            int global = w[1] ? (64 + __builtin_ctzll(w[1])) : __builtin_ctzll(w[0]);
            if (bits != 1 || global != s) {
                std::cerr << "[FAIL] E1 square " << s << ": popcount=" << bits
                          << " serialized_bit=" << global << std::endl;
                ok = false;
            }
        }
        if (!ok) std::exit(1);
        std::cout << "  [OK] E1: square_bb(s) -> exactly serialized bit s for ALL 120 squares" << std::endl;
    }

    // E2: occupancy invariant — for white-to-move positions, the union of the 26
    // ply-0 piece planes must equal the board occupancy EXACTLY, with no square in
    // two planes (catches mis-placement, overlap, or padding leakage).
    {
        const std::vector<std::string> wfens = {
            lczero::ChessBoard::kStartposFen,
            "5k4/10/10/10/4p5/4P5/10/10/10/5K4 w - - 7+7 0 1",
            "1r7k/10/10/10/10/10/10/10/1r8/K9 w - - 7+7 0 1",
        };
        for (const auto& fen : wfens) {
            auto board = std::make_unique<lczero::ChessBoard>(fen);
            auto h = std::make_unique<lczero::PositionHistory>();
            h->Reset(*board, 0, 1);
            lczero::InputPlanes planes; int t = 0;
            lczero::EncodePositionForNN(*h, lczero::kMoveHistory,
                                        lczero::FillEmptyHistory::FEN_ONLY, &planes, &t);
            Stockfish::Bitboard plane_union = Stockfish::Bitboard(static_cast<uint64_t>(0));
            int total_bits = 0;
            for (int p = 0; p <= 25; ++p) {
                plane_union = plane_union | planes[p].mask;
                total_bits += Stockfish::popcount(planes[p].mask);
            }
            const auto& pos = board->GetRawPosition();
            Stockfish::Bitboard occ = pos.pieces();
            int occ_count = Stockfish::popcount(occ);
            bool no_overlap = (Stockfish::popcount(plane_union) == total_bits);
            bool match = !bool(plane_union ^ occ);
            if (!no_overlap || !match || total_bits != occ_count) {
                std::cerr << "[FAIL] E2 occupancy: " << fen << " planes_bits=" << total_bits
                          << " occ=" << occ_count << " overlap=" << (!no_overlap)
                          << " union_match=" << match << std::endl;
                std::exit(1);
            }
            std::cout << "  [OK] E2 occupancy: " << occ_count
                      << " pieces each on exactly 1 plane at the exact square" << std::endl;
        }
    }
    std::cout << "[PASS] BIT-LEVEL tests." << std::endl;
}

// ============================================================================
// RULES: repetition (3-fold) / rule50 (100-ply) / DYNAMIC 7-check counting.
// ============================================================================
void run_rules_tests() {
    std::cout << "\n=== RULES: repetition / rule50 / dynamic 7-check ===" << std::endl;
    setup_custom_variant();

    auto drive = [](const std::string& fen, int rule50, const std::vector<std::string>& ucis,
                    lczero::GameResult& out) {
        auto board = std::make_unique<lczero::ChessBoard>(fen);
        auto h = std::make_unique<lczero::PositionHistory>();
        h->Reset(*board, rule50, 1);
        out = h->ComputeGameResult();
        for (const auto& uci : ucis) {
            lczero::Move m = h->Last().GetBoard().ParseMove(uci);
            if (m.is_null()) { std::cerr << "[FAIL] illegal move " << uci << " in " << fen << std::endl; std::exit(1); }
            h->Append(m);
            out = h->ComputeGameResult();
        }
    };

    // 1. 3-fold repetition: kings shuffle back to the start twice -> DRAW.
    {
        lczero::GameResult res;
        drive("k9/10/10/10/10/10/10/10/10/K9 w - - 7+7 0 1", 0,
              {"a1b1","a10b10","b1a1","b10a10","a1b1","a10b10","b1a1","b10a10"}, res);
        if (res != lczero::GameResult::DRAW) { std::cerr << "[FAIL] 3-fold repetition not DRAW (got " << (int)res << ")" << std::endl; std::exit(1); }
        std::cout << "  [OK] 3-fold repetition -> DRAW" << std::endl;
    }
    // 2. rule50: start at 99, one non-zeroing king move -> 100 plies -> DRAW.
    {
        lczero::GameResult res;
        drive("k9/10/10/10/10/10/10/10/10/K9 w - - 7+7 99 1", 99, {"a1b1"}, res);
        if (res != lczero::GameResult::DRAW) { std::cerr << "[FAIL] rule50=100 not DRAW (got " << (int)res << ")" << std::endl; std::exit(1); }
        std::cout << "  [OK] rule50 reaches 100 plies -> DRAW" << std::endl;
    }
    // 3. Dynamic 7-check: White needs 1 more check, delivers it -> WHITE_WON.
    {
        lczero::GameResult res;
        drive("4k5/10/10/10/10/10/10/10/10/R8K w - - 1+7 0 1", 0, {"a1e1"}, res);
        if (res != lczero::GameResult::WHITE_WON) { std::cerr << "[FAIL] dynamic 7th check not WHITE_WON (got " << (int)res << ")" << std::endl; std::exit(1); }
        std::cout << "  [OK] White delivers final (7th) check -> WHITE_WON" << std::endl;
    }

    // Sergeant double-step on its SECOND move. doubleStepRegionWhite = *1 *2 *3, so a
    // white sergeant that single-stepped onto a region rank (1-3) must STILL be able to
    // double-step. Scenario: sergeant single-steps j2->i3 (diagonal), black replies, and
    // we expect the straight double-step i3->i5 to be among the legal moves.
    {
        std::string fen = "k9/10/10/10/10/10/10/10/9S/K9 w - - 7+7 0 1";
        auto board = std::make_unique<lczero::ChessBoard>(fen);
        auto h = std::make_unique<lczero::PositionHistory>();
        h->Reset(*board, 0, 1);

        const lczero::Move m1 = h->Last().GetBoard().ParseMove("j2i3");  // sergeant single-step
        if (m1.is_null()) { std::cerr << "[FAIL] sergeant single-step j2i3 is illegal" << std::endl; std::exit(1); }
        h->Append(m1);
        const lczero::Move m2 = h->Last().GetBoard().ParseMove("a10b10");  // black king reply
        if (m2.is_null()) { std::cerr << "[FAIL] black reply a10b10 is illegal" << std::endl; std::exit(1); }
        h->Append(m2);

        // White to move again, sergeant now on i3 (rank 3, a double-step region rank).
        bool can_double_step = false;
        const lczero::ChessBoard& b2 = h->Last().GetBoard();
        const lczero::MoveList moves = b2.GenerateLegalMoves();
        for (size_t i = 0; i < moves.size(); ++i) {
            if (b2.MoveToString(moves[i]) == "i3i5") { can_double_step = true; break; }
        }
        if (!can_double_step) {
            std::cerr << "[FAIL] sergeant cannot double-step i3i5 on its 2nd move "
                         "(it single-stepped onto a double-step-region rank, so it should)."
                      << std::endl;
            std::exit(1);
        }
        std::cout << "  [OK] sergeant double-steps i3i5 on its 2nd move (region-based double-step)" << std::endl;
    }

    std::cout << "[PASS] RULES tests." << std::endl;
}

// ============================================================================
// ADAPTER round-trip: FEN idempotence + MoveToString<->ParseMove (both colors).
// ============================================================================
void run_adapter_tests() {
    std::cout << "\n=== ADAPTER: FEN + move-string round-trip ===" << std::endl;
    setup_custom_variant();

    const std::vector<std::string> fens = {
        lczero::ChessBoard::kStartposFen,
        "5k4/10/10/10/10/1s8/10/S9/10/5K4 w - - 7+7 0 1",
        "1r7k/10/10/10/10/10/10/10/1r8/K9 w - - 7+7 0 1",
        "4k5/10/10/10/10/10/10/10/10/R8K b - - 1+7 0 1",  // BLACK to move
    };

    for (const auto& fen : fens) {
        lczero::ChessBoard b1(fen);
        std::string f1 = b1.GetRawPosition().fen();
        lczero::ChessBoard b2(f1);
        std::string f2 = b2.GetRawPosition().fen();
        if (f1 != f2) { std::cerr << "[FAIL] FEN not idempotent:\n  " << f1 << "\n  " << f2 << std::endl; std::exit(1); }
    }
    std::cout << "  [OK] FEN round-trip idempotent for " << fens.size() << " positions" << std::endl;

    int total = 0;
    for (const auto& fen : fens) {
        lczero::ChessBoard board(fen);
        lczero::MoveList moves = board.GenerateLegalMoves();  // canonical frame
        for (size_t i = 0; i < moves.size(); ++i) {
            std::string s = board.MoveToString(moves[i]);
            lczero::Move back = board.ParseMove(s);
            if (!(back == moves[i])) {
                std::cerr << "[FAIL] move round-trip mismatch: '" << s
                          << "' did not parse back to the same canonical move" << std::endl;
                std::exit(1);
            }
            ++total;
        }
    }
    std::cout << "  [OK] MoveToString<->ParseMove for " << total << " legal moves (incl. Black-to-move)" << std::endl;
    std::cout << "[PASS] ADAPTER round-trip tests." << std::endl;
}

// ============================================================================
// NN-INTERFACE tests: MoveToNNIndex / MoveFromNNIndex / UnpackInputPlanes.
// These are the adapter<->(MCTS/NN) boundary. The existing --test-policy only
// checks the idx->move->idx direction; here we add the FORWARD direction from
// every geometric move-shape AND from every real legal move, plus a dedicated
// value-semantics test of UnpackInputPlanes (not just the indirect round-trip).
// ============================================================================

// Recursively check that every legal move at every node maps to an in-range
// index, decodes back to the same from/to geometry, and is injective per node.
static void nn_check_moves(const lczero::ChessBoard& board, int depth,
                           long& total, long& unmapped, long& geo_fail, long& inj_fail) {
    lczero::MoveList moves = board.GenerateLegalMoves();
    std::vector<int> idxs;
    idxs.reserve(moves.size());
    for (size_t i = 0; i < moves.size(); ++i) {
        const uint16_t idx = lczero::MoveToNNIndex(moves[i], 0);
        ++total;
        if (idx >= 10600) {
            ++unmapped;
            if (unmapped <= 5) std::cerr << "  [UNMAPPED] " << moves[i].ToString() << std::endl;
            continue;
        }
        idxs.push_back(idx);
        Stockfish::Move back = lczero::MoveFromNNIndex(idx, 0);
        if (Stockfish::from_sq(back) != Stockfish::from_sq(moves[i]) ||
            Stockfish::to_sq(back) != Stockfish::to_sq(moves[i])) {
            ++geo_fail;
            if (geo_fail <= 5) std::cerr << "  [GEO] " << moves[i].ToString() << " idx=" << idx << std::endl;
        }
    }
    std::sort(idxs.begin(), idxs.end());
    for (size_t i = 1; i < idxs.size(); ++i)
        if (idxs[i] == idxs[i - 1]) { ++inj_fail; break; }

    if (depth > 1) {
        for (size_t i = 0; i < moves.size(); ++i) {
            lczero::ChessBoard child(board);
            child.ApplyMove(moves[i]);
            nn_check_moves(child, depth - 1, total, unmapped, geo_fail, inj_fail);
        }
    }
}

void run_nn_tests() {
    std::cout << "\n=== NN-INTERFACE tests (MoveToNNIndex / MoveFromNNIndex / UnpackInputPlanes) ===" << std::endl;
    setup_custom_variant();

    auto make_sq = [](int r, int f) { return Stockfish::make_square((Stockfish::File)f, (Stockfish::Rank)r); };
    auto inb = [](int r, int f) { return r >= 0 && r < 10 && f >= 0 && f < 10; };

    // --- Part 1: EXHAUSTIVE geometric enumeration of every move-shape ---
    // forward direction (move -> idx), exact round-trip, in-range, no collisions.
    {
        std::vector<uint32_t> owner(10600, 0xFFFFFFFFu);
        long enumc = 0, range_err = 0, rt_err = 0, collide = 0;
        auto check = [&](Stockfish::Move m) {
            ++enumc;
            const uint16_t idx = lczero::MoveToNNIndex(m, 0);
            if (idx >= 10600) { ++range_err; return; }
            Stockfish::Move back = lczero::MoveFromNNIndex(idx, 0);
            if (back != m) { ++rt_err; if (rt_err <= 5) std::cerr << "  [RT] idx=" << idx << std::endl; }
            const uint32_t raw = static_cast<uint32_t>(m);
            if (owner[idx] != 0xFFFFFFFFu && owner[idx] != raw) { ++collide; if (collide <= 5) std::cerr << "  [COLLIDE] idx=" << idx << std::endl; }
            owner[idx] = raw;
        };
        const int sdx[8] = {0,1,1,1,0,-1,-1,-1}, sdy[8] = {1,1,0,-1,-1,-1,0,1};
        const int ndx[8] = {1,2,2,1,-1,-2,-2,-1}, ndy[8] = {2,1,-1,-2,-2,-1,1,2};
        const int cdx[8] = {1,3,3,1,-1,-3,-3,-1}, cdy[8] = {3,1,-1,-3,-3,-1,1,3};
        const Stockfish::PieceType promos[6] = {Stockfish::BISHOP, Stockfish::ROOK,
            Stockfish::CENTAUR, Stockfish::KNIGHT, Stockfish::CUSTOM_PIECE_1, Stockfish::CUSTOM_PIECE_2};
        for (int r = 0; r < 10; ++r) for (int f = 0; f < 10; ++f) {
            for (int d = 0; d < 8; ++d) for (int dist = 1; dist <= 9; ++dist) {
                int tr = r + sdy[d] * dist, tf = f + sdx[d] * dist;
                if (inb(tr, tf)) check(Stockfish::make_move(make_sq(r, f), make_sq(tr, tf)));
            }
            for (int k = 0; k < 8; ++k) { int tr = r + ndy[k], tf = f + ndx[k]; if (inb(tr, tf)) check(Stockfish::make_move(make_sq(r, f), make_sq(tr, tf))); }
            for (int k = 0; k < 8; ++k) { int tr = r + cdy[k], tf = f + cdx[k]; if (inb(tr, tf)) check(Stockfish::make_move(make_sq(r, f), make_sq(tr, tf))); }
            for (int pi = 0; pi < 6; ++pi) for (int dir = -1; dir <= 1; ++dir) {
                int tr = r + 1, tf = f + dir;
                if (inb(tr, tf)) check(Stockfish::make<Stockfish::PROMOTION>(make_sq(r, f), make_sq(tr, tf), promos[pi]));
            }
        }
        if (range_err || rt_err || collide) {
            std::cerr << "[FAIL] Part 1: range_err=" << range_err << " rt_err=" << rt_err << " collide=" << collide << std::endl;
            std::exit(1);
        }
        std::cout << "  [OK] Part 1: " << enumc << " geometric move-shapes -> all in-range, exact round-trip, ZERO collisions" << std::endl;
    }

    // --- Part 2: every REAL legal move (depth-3 from startpos + promotion FEN) ---
    // Critical safety: a 65535 here would mean an out-of-bounds write into pi[10600].
    {
        long total = 0, unmapped = 0, geo_fail = 0, inj_fail = 0;
        lczero::ChessBoard start(std::string(lczero::ChessBoard::kStartposFen));
        nn_check_moves(start, 3, total, unmapped, geo_fail, inj_fail);
        lczero::ChessBoard promo(std::string("5k4/P9/10/10/10/10/10/10/10/5K4 w - - 7+7 0 1"));
        nn_check_moves(promo, 2, total, unmapped, geo_fail, inj_fail);
        if (unmapped || geo_fail || inj_fail) {
            std::cerr << "[FAIL] Part 2: unmapped=" << unmapped << " geo_fail=" << geo_fail << " inj_fail=" << inj_fail << std::endl;
            std::exit(1);
        }
        std::cout << "  [OK] Part 2: " << total << " real legal moves -> none unmapped, geometry round-trips, injective per position" << std::endl;
    }

    // --- Part 3: UnpackInputPlanes value semantics (independent of round-trip) ---
    {
        lczero::InputPlanes planes;
        for (auto& p : planes) { p.mask = 0; p.value = 1.0f; }
        planes[0].mask = Stockfish::square_bb((Stockfish::Square)(5 * 12 + 3)); planes[0].value = 0.7f;  // single (5,3)
        planes[5].Fill(0.3f);                                                                            // AllSquares
        planes[10].mask = Stockfish::square_bb((Stockfish::Square)(2 * 12 + 10)); planes[10].value = 0.9f; // PADDING (file10)
        planes[20].mask = Stockfish::square_bb((Stockfish::Square)(0)) | Stockfish::square_bb((Stockfish::Square)(9 * 12 + 9)); planes[20].value = 0.5f;

        std::vector<float> out(226 * 100, 0.0f);
        lczero::UnpackInputPlanes(planes, out.data(), 10, 10);
        auto cell = [&](int p, int r, int f) { return out[p * 100 + r * 10 + f]; };

        bool ok = true;
        for (int r = 0; r < 10; ++r) for (int f = 0; f < 10; ++f) {
            float e0 = (r == 5 && f == 3) ? 0.7f : 0.0f;
            float e20 = ((r == 0 && f == 0) || (r == 9 && f == 9)) ? 0.5f : 0.0f;
            if (cell(0, r, f) != e0)    { ok = false; std::cerr << "[FAIL] P3 plane0 (" << r << "," << f << ")=" << cell(0, r, f) << "\n"; }
            if (cell(5, r, f) != 0.3f)  { ok = false; std::cerr << "[FAIL] P3 plane5 AllSquares (" << r << "," << f << ")=" << cell(5, r, f) << "\n"; }
            if (cell(10, r, f) != 0.0f) { ok = false; std::cerr << "[FAIL] P3 plane10 PADDING leaked (" << r << "," << f << ")=" << cell(10, r, f) << "\n"; }
            if (cell(20, r, f) != e20)  { ok = false; std::cerr << "[FAIL] P3 plane20 (" << r << "," << f << ")=" << cell(20, r, f) << "\n"; }
            if (cell(1, r, f) != 0.0f)  { ok = false; std::cerr << "[FAIL] P3 plane1 untouched leaked\n"; }
        }
        if (!ok) std::exit(1);
        std::cout << "  [OK] Part 3: UnpackInputPlanes -> single-value, AllSquares fast-path, padding-reject, plane-independence ALL correct" << std::endl;
    }

    std::cout << "[PASS] NN-INTERFACE tests." << std::endl;
}

// ============================================================================
// ARENA: play two ONNX models against each other to measure relative strength
// (T7 "later generation beats earlier"). Colors alternate each game; openings
// use temperature sampling for diversity, mid/endgame is greedy (max-visit).
// Noise is OFF (deterministic evaluation). Reports A's score in [0,1].
// ============================================================================
void run_uci_tests() {
    std::cout << "\n=== UCI move-I/O conformance (--test-uci) ===" << std::endl;
    setup_custom_variant();
    // FENs incl Black-to-move, rank-10 destinations, promotion-ready, castling.
    const std::vector<std::string> fens = {
        kUciStartFen,
        "4k5/10/10/10/10/10/10/10/10/R8K b - - 7+7 0 1",          // Black to move
        "5k4/10/10/10/10/10/10/10/10/5K4 w - - 7+7 0 1",
        "1r7k/10/10/10/10/10/10/10/1r8/K9 w - - 7+7 0 1",
    };
    long total = 0;
    int fail = 0;
    for (const auto& fen : fens) {
        auto tree = std::make_unique<lczero::classic::NodeTree>();  // heap: 512-ply history
        tree->ResetToPosition(fen, {});   // bool = tree-reuse flag, NOT success
        const bool black = tree->IsBlackToMove();
        const auto& board = tree->GetPositionHistory().Last().GetBoard();
        lczero::MoveList legal = board.GenerateLegalMoves();
        for (size_t i = 0; i < legal.size(); ++i) {
            const std::string uci = CanonicalMoveToUci(legal[i], black);
            // well-formed: 4-5 chars, file a-j, has a rank
            bool ok_fmt = uci.size() >= 4 && uci.size() <= 6 && uci[0] >= 'a' && uci[0] <= 'j';
            lczero::Move back = UciToCanonicalMove(board, uci, black);
            if (!ok_fmt || !(back == legal[i])) {
                if (fail < 10) std::cerr << "[FAIL] round-trip '" << uci << "' (black=" << black << ")" << std::endl;
                ++fail;
            }
            ++total;
        }
    }
    std::cout << "  move round-trip: " << (total - fail) << "/" << total
              << " over " << fens.size() << " positions (incl Black-to-move)" << std::endl;

    // Absolute sanity: from startpos (White, no flip) a known pawn push exists.
    {
        auto tree = std::make_unique<lczero::classic::NodeTree>();
        tree->ResetToPosition(kUciStartFen, {});
        const auto& board = tree->GetPositionHistory().Last().GetBoard();
        lczero::Move m = UciToCanonicalMove(board, "b3b4", /*black=*/false);
        if (m.is_null()) { std::cerr << "[FAIL] startpos: b3b4 not a legal move (coord/flip bug?)" << std::endl; ++fail; }
        else std::cout << "  absolute check: startpos b3b4 is legal (White coords un-flipped) [OK]" << std::endl;
    }

    // position-sync: startpos+moves vs the resulting FEN -> same head position.
    {
        auto t1 = std::make_unique<lczero::classic::NodeTree>();
        t1->ResetToPosition(kUciStartFen, {});
        const auto& b0 = t1->GetPositionHistory().Last().GetBoard();
        lczero::Move m = UciToCanonicalMove(b0, "b3b4", false);
        if (!m.is_null()) {
            t1->MakeMove(m);
            const std::string fen_after = t1->GetPositionHistory().Last().GetBoard().GetRawPosition().fen();
            auto t2 = std::make_unique<lczero::classic::NodeTree>();
            t2->ResetToPosition(fen_after, {});
            const std::string fen_rebuilt = t2->GetPositionHistory().Last().GetBoard().GetRawPosition().fen();
            if (fen_after != fen_rebuilt) { std::cerr << "[FAIL] position-sync FEN mismatch" << std::endl; ++fail; }
            else std::cout << "  position-sync: startpos+b3b4 FEN round-trips [OK]" << std::endl;
        }
    }

    if (fail == 0) std::cout << "[PASS] UCI move-I/O conformance." << std::endl;
    else { std::cerr << "[FAIL] " << fail << " UCI conformance failures." << std::endl; std::exit(1); }
}

// ============================================================================
// --test-encoder : ground-truth check that EncodePositionForNN produces input
// planes that FAITHFULLY represent the board (no "fake data" fed to the NN).
// We re-derive the expected planes from the board's own piece_on()/state — an
// INDEPENDENT path from the encoder's loop — and assert exact agreement. The
// strongest checks (occupancy-union, per-type counts, king-count) cannot both
// be wrong the same way, so they catch dropped pieces, phantom bits, piece-type
// mislabeling, us/them swaps, and a wrong Black-to-move canonical flip.
// ============================================================================
void run_encoder_tests() {
    std::cout << "\n=== ENCODER ground-truth tests (board -> NN planes) ===" << std::endl;
    setup_custom_variant();

    // Documented piece-type -> plane index (0..12), written INDEPENDENTLY of the
    // encoder's switch. A mismatch (e.g. knight<->bishop swap) shows up as a
    // per-type bit-count error below.
    auto type_plane = [](Stockfish::PieceType pt) -> int {
        switch (pt) {
            case Stockfish::PAWN: return 0;           case Stockfish::KNIGHT: return 1;
            case Stockfish::BISHOP: return 2;         case Stockfish::ROOK: return 3;
            case Stockfish::QUEEN: return 4;          case Stockfish::KING: return 5;
            case Stockfish::AMAZON: return 6;         case Stockfish::CHANCELLOR: return 7;
            case Stockfish::ARCHBISHOP: return 8;     case Stockfish::CENTAUR: return 9;
            case Stockfish::CUSTOM_PIECE_1: return 10; case Stockfish::CUSTOM_PIECE_2: return 11;
            case Stockfish::CUSTOM_PIECE_3: return 12; default: return -1;
        }
    };

    const std::string startw = std::string(kUciStartFen);
    std::string startb = startw; startb[startw.find(" w ") + 1] = 'b';  // same board, Black to move
    struct Case { std::string fen; const char* name; };
    std::vector<Case> cases = {
        {startw, "startpos (White to move)"},
        {startb, "startpos board, Black to move (flip + us/them swap)"},
        {"4k5/10/10/10/10/10/10/10/10/5K4 w - - 7+7 0 1", "two kings (White)"},
        {"4k5/10/10/10/10/10/10/10/10/5K4 b - - 3+5 0 1", "two kings (Black, flip)"},
        {"1r7k/10/10/10/10/10/10/10/1r8/K9 w - - 6+7 0 1", "rooks vs lone king (asym)"},
        {"5k4/10/10/10/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM w - - 7+7 0 1", "many White minors+pawns"},
    };

    int fail = 0;
    auto popc = [](Stockfish::Bitboard b) { return Stockfish::popcount(b); };

    for (const auto& c : cases) {
        auto tree = std::make_unique<lczero::classic::NodeTree>();   // heap (512-ply history)
        tree->ResetToPosition(c.fen, {});
        const lczero::PositionHistory& hist = tree->GetPositionHistory();
        const Stockfish::Position& pos = hist.Last().GetBoard().GetRawPosition();
        const Stockfish::Color us = tree->IsBlackToMove() ? Stockfish::BLACK : Stockfish::WHITE;
        const Stockfish::Color them = ~us;
        const bool flip = (us == Stockfish::BLACK);
        auto dest = [&](int s) -> Stockfish::Square {
            Stockfish::Square sq = static_cast<Stockfish::Square>(s);
            return flip ? Stockfish::relative_square(Stockfish::BLACK, sq, Stockfish::RANK_10) : sq;
        };

        lczero::InputPlanes planes;
        int transform = -1;
        lczero::EncodePositionForNN(hist, lczero::kMoveHistory,
                                    lczero::FillEmptyHistory::NO, &planes, &transform);

        // --- Build EXPECTED occupancy/per-type masks from the board itself ---
        Stockfish::Bitboard exp_all = 0, exp_us = 0, exp_them = 0;
        Stockfish::Bitboard exp_type_us[13] = {0}, exp_type_them[13] = {0};
        int piece_count = 0;
        for (int rank = 0; rank < 10; ++rank) {
            for (int file = 0; file < 10; ++file) {
                const int s = rank * 12 + file;
                Stockfish::Piece pc = pos.piece_on(static_cast<Stockfish::Square>(s));
                if (pc == Stockfish::NO_PIECE) continue;
                ++piece_count;
                const int ti = type_plane(Stockfish::type_of(pc));
                const Stockfish::Bitboard bit = Stockfish::square_bb(dest(s));
                exp_all |= bit;
                if (Stockfish::color_of(pc) == us) { exp_us |= bit; if (ti >= 0) exp_type_us[ti] |= bit; }
                else                               { exp_them |= bit; if (ti >= 0) exp_type_them[ti] |= bit; }
            }
        }

        // --- GOT: union the current-step (d=0) piece planes from the encoder ---
        Stockfish::Bitboard got_all = 0, got_us = 0, got_them = 0;
        for (int p = 0; p <= 12; ++p) { got_us |= planes[p].mask; }       // us pieces
        for (int p = 13; p <= 25; ++p) { got_them |= planes[p].mask; }    // them pieces
        got_all = got_us | got_them;

        int errs = 0;
        // (1) occupancy union must match EXACTLY (catches dropped/phantom squares).
        if (popc(got_all ^ exp_all) != 0) { std::cerr << "  [FAIL] " << c.name << ": occupancy union mismatch\n"; ++errs; }
        // (2) total bits == piece count (no collision/overwrite loses a bit).
        if (popc(got_all) != piece_count) { std::cerr << "  [FAIL] " << c.name << ": bit-count " << popc(got_all) << " != pieces " << piece_count << "\n"; ++errs; }
        // (3) us/them split correct (side-to-move pieces in planes 0..12).
        if (popc(got_us ^ exp_us) != 0)   { std::cerr << "  [FAIL] " << c.name << ": us-plane union mismatch (color/flip bug)\n"; ++errs; }
        if (popc(got_them ^ exp_them) != 0){ std::cerr << "  [FAIL] " << c.name << ": them-plane union mismatch\n"; ++errs; }
        // (4) per-piece-type placement (catches piece-type mislabeling/swaps).
        for (int t = 0; t <= 12; ++t) {
            if (popc(planes[t].mask ^ exp_type_us[t]) != 0)        { std::cerr << "  [FAIL] " << c.name << ": us type-plane " << t << " mismatch\n"; ++errs; }
            if (popc(planes[13 + t].mask ^ exp_type_them[t]) != 0) { std::cerr << "  [FAIL] " << c.name << ": them type-plane " << (13+t) << " mismatch\n"; ++errs; }
        }
        // (5) king invariant: exactly one king per side present on the board.
        if (popc(exp_type_us[5]) == 1 && popc(planes[5].mask) != 1)   { std::cerr << "  [FAIL] " << c.name << ": us-king plane != 1 bit\n"; ++errs; }
        if (popc(exp_type_them[5]) == 1 && popc(planes[18].mask) != 1){ std::cerr << "  [FAIL] " << c.name << ": them-king plane != 1 bit\n"; ++errs; }

        // --- Aux planes vs board ground truth (unpack to float, check cells) ---
        constexpr int PS = 100;
        std::vector<float> fp((lczero::kAuxPlaneBase + lczero::kAuxPlanesCount) * PS, -1.0f);
        lczero::UnpackInputPlanes(planes, fp.data(), 10, 10);
        auto auxcell = [&](int k, int rank, int file) { return fp[(lczero::kAuxPlaneBase + k) * PS + rank * 10 + file]; };
        const float exp_r50 = static_cast<float>(hist.Last().GetRule50Ply()) / 100.0f;
        const float exp_cu = static_cast<float>(pos.checks_remaining(us)) / 7.0f;
        const float exp_ct = static_cast<float>(pos.checks_remaining(them)) / 7.0f;
        for (int rk = 0; rk < 10 && errs < 40; ++rk) for (int fl = 0; fl < 10; ++fl) {
            if (auxcell(7, rk, fl) != 1.0f)       { std::cerr << "  [FAIL] " << c.name << ": aux7 border != 1\n"; ++errs; break; }
            if (auxcell(6, rk, fl) != 0.0f)       { std::cerr << "  [FAIL] " << c.name << ": aux6 unused != 0\n"; ++errs; break; }
            if (std::abs(auxcell(5, rk, fl) - exp_r50) > 1e-6) { std::cerr << "  [FAIL] " << c.name << ": aux5 rule50 mismatch\n"; ++errs; break; }
            if (std::abs(auxcell(8, rk, fl) - exp_cu) > 1e-6)  { std::cerr << "  [FAIL] " << c.name << ": aux8 checks_us mismatch\n"; ++errs; break; }
            if (std::abs(auxcell(9, rk, fl) - exp_ct) > 1e-6)  { std::cerr << "  [FAIL] " << c.name << ": aux9 checks_them mismatch\n"; ++errs; break; }
        }
        // Castling planes: bit count == #rights, placed at the (flipped) rook squares.
        auto castle_expect = [&](Stockfish::CastlingRights cr) -> Stockfish::Bitboard {
            if (!pos.can_castle(cr)) return Stockfish::Bitboard(0);
            return Stockfish::square_bb(dest(pos.castling_rook_square(cr)));
        };
        const auto us_ooo = (us == Stockfish::WHITE) ? Stockfish::WHITE_OOO : Stockfish::BLACK_OOO;
        const auto us_oo  = (us == Stockfish::WHITE) ? Stockfish::WHITE_OO  : Stockfish::BLACK_OO;
        const auto th_ooo = (us == Stockfish::WHITE) ? Stockfish::BLACK_OOO : Stockfish::WHITE_OOO;
        const auto th_oo  = (us == Stockfish::WHITE) ? Stockfish::BLACK_OO  : Stockfish::WHITE_OO;
        if (popc(planes[lczero::kAuxPlaneBase + 0].mask ^ castle_expect(us_ooo)) != 0) { std::cerr << "  [FAIL] " << c.name << ": castle aux0 (us OOO) mismatch\n"; ++errs; }
        if (popc(planes[lczero::kAuxPlaneBase + 1].mask ^ castle_expect(us_oo))  != 0) { std::cerr << "  [FAIL] " << c.name << ": castle aux1 (us OO) mismatch\n"; ++errs; }
        if (popc(planes[lczero::kAuxPlaneBase + 2].mask ^ castle_expect(th_ooo)) != 0) { std::cerr << "  [FAIL] " << c.name << ": castle aux2 (them OOO) mismatch\n"; ++errs; }
        if (popc(planes[lczero::kAuxPlaneBase + 3].mask ^ castle_expect(th_oo))  != 0) { std::cerr << "  [FAIL] " << c.name << ": castle aux3 (them OO) mismatch\n"; ++errs; }

        if (errs == 0) std::cout << "  [OK] " << c.name << ": " << piece_count
                                 << " pieces -> planes faithful (occupancy/type/us-them/king/aux/castling)" << std::endl;
        fail += errs;
    }

    // --- Injectivity: two positions differing by one piece must differ in planes ---
    {
        auto enc = [&](const std::string& fen, lczero::InputPlanes& out) {
            auto t = std::make_unique<lczero::classic::NodeTree>();
            t->ResetToPosition(fen, {});
            int tr = 0;
            lczero::EncodePositionForNN(t->GetPositionHistory(), lczero::kMoveHistory,
                                        lczero::FillEmptyHistory::NO, &out, &tr);
        };
        lczero::InputPlanes a, b;
        enc("4k5/10/10/10/10/10/10/10/10/5K4 w - - 7+7 0 1", a);   // white king f1
        enc("4k5/10/10/10/10/10/10/10/10/6K3 w - - 7+7 0 1", b);   // white king g1
        int diff = 0;
        for (size_t p = 0; p < a.size(); ++p) if (Stockfish::popcount(a[p].mask ^ b[p].mask)) ++diff;
        if (diff == 0) { std::cerr << "  [FAIL] injectivity: distinct positions encoded identically!\n"; ++fail; }
        else std::cout << "  [OK] injectivity: king f1 vs g1 differ in " << diff << " plane(s)" << std::endl;
    }

    if (fail == 0) std::cout << "[PASS] ENCODER ground-truth tests (NN input faithfully represents the board)." << std::endl;
    else { std::cerr << "[FAIL] " << fail << " encoder ground-truth failures." << std::endl; std::exit(1); }
}

