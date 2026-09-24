// ChessBoard adapter (lczero <-> Fairy-Stockfish bridge) and UCI move I/O tests:
//   --test-board, --test-adapter, --test-uci.

#include "tests/test_common.h"

void run_board_tests() {
    std::cout << "\n========================================" << std::endl;
    std::cout << "RUNNING CHESSBOARD BRIDGE TESTS" << std::endl;
    std::cout << "========================================\n" << std::endl;

    // Load custom variant
    setup_custom_variant();   // the real definition, not a copy

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
        std::string stalemate_fen = "1r7k/10/10/10/10/10/10/10/1r8/K9 w - - 8+8 0 1";
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

    // TEST 4: 8-checks limit rule verification
    {
        std::cout << "TEST 4: 8-checks limit verification..." << std::endl;
        
        // Case A: White checks remaining = 0
        {
            std::string checks_0_fen = "k9/10/10/10/10/10/10/10/10/K9 w - - 0+8 0 1";
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
            std::string checks_0_fen = "k9/10/10/10/10/10/10/10/10/K9 w - - 8+0 0 1";
            lczero::ChessBoard board(checks_0_fen);
            auto history = std::make_unique<lczero::PositionHistory>();
            history->Reset(board, 0, 1);

            lczero::GameResult result = history->ComputeGameResult();
            if (result != lczero::GameResult::BLACK_WON) {
                std::cerr << "[FAIL] 0 checks remaining for Black did not result in BLACK_WON! Got: " << (int)result << std::endl;
                std::exit(1);
            }
        }

        std::cout << "[PASS] TEST 4 passed! (8-checks limit correctly ends the game)\n" << std::endl;
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

    // TEST 6: MCTS Relative & Absolute Result Verification (Checkmate & Stalemate & 8-checks)
    {
        std::cout << "TEST 6: MCTS Relative & Absolute Result Verification..." << std::endl;

        // Part A: White is checkmated. It is White's turn to move (board.flipped() == false).
        // White King on a1, Black Rooks on b1 and b2.
        std::string white_checkmated_fen = "9k/10/10/10/10/10/10/10/1r8/Kr8 w - - 8+8 0 1";
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
        std::string black_checkmated_fen = "kR8/1R8/10/10/10/10/10/10/10/9K b - - 8+8 0 1";
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

        // Part C: Verify 8-checks in both absolute and MCTS.
        // Scenario 1: White has 0 checks remaining (White won absolute).
        {
            // Case A: Black to move (board.flipped() == true). White just checked.
            std::string white_win_black_turn = "k9/10/10/10/10/10/10/10/10/K9 b - - 0+8 0 1";
            lczero::ChessBoard board(white_win_black_turn);
            auto history = std::make_unique<lczero::PositionHistory>();
            history->Reset(board, 0, 1);

            // Absolute check
            lczero::GameResult abs = history->ComputeGameResult();
            if (abs != lczero::GameResult::WHITE_WON) {
                std::cerr << "[FAIL] White win 8-checks absolute should be WHITE_WON, got: " << (int)abs << std::endl;
                std::exit(1);
            }
            // MCTS check (relative Win for White, who just moved)
            lczero::GameResult res = history->ComputeMctsResult(board.GenerateLegalMoves());
            if (res != lczero::GameResult::WHITE_WON) {
                std::cerr << "[FAIL] White win 8-checks (Black's turn) MCTS should be WHITE_WON, got: " << (int)res << std::endl;
                std::exit(1);
            }

            // Case B: White to move (board.flipped() == false). Black just moved (but White won).
            std::string white_win_white_turn = "k9/10/10/10/10/10/10/10/10/K9 w - - 0+8 0 1";
            lczero::ChessBoard board_wt(white_win_white_turn);
            auto history_wt = std::make_unique<lczero::PositionHistory>();
            history_wt->Reset(board_wt, 0, 1);

            // Absolute check
            lczero::GameResult abs_wt = history_wt->ComputeGameResult();
            if (abs_wt != lczero::GameResult::WHITE_WON) {
                std::cerr << "[FAIL] White win 8-checks absolute should be WHITE_WON, got: " << (int)abs_wt << std::endl;
                std::exit(1);
            }
            // MCTS check (relative Loss for Black, who just moved)
            lczero::GameResult res_wt = history_wt->ComputeMctsResult(board_wt.GenerateLegalMoves());
            if (res_wt != lczero::GameResult::BLACK_WON) {
                std::cerr << "[FAIL] White win 8-checks (White's turn) MCTS should be BLACK_WON, got: " << (int)res_wt << std::endl;
                std::exit(1);
            }
        }

        // Scenario 2: Black has 0 checks remaining (Black won absolute).
        {
            // Case C: White to move (board.flipped() == false). Black just checked.
            std::string black_win_white_turn = "k9/10/10/10/10/10/10/10/10/K9 w - - 8+0 0 1";
            lczero::ChessBoard board(black_win_white_turn);
            auto history = std::make_unique<lczero::PositionHistory>();
            history->Reset(board, 0, 1);

            // Absolute check
            lczero::GameResult abs = history->ComputeGameResult();
            if (abs != lczero::GameResult::BLACK_WON) {
                std::cerr << "[FAIL] Black win 8-checks absolute should be BLACK_WON, got: " << (int)abs << std::endl;
                std::exit(1);
            }
            // MCTS check (relative Win for Black, who just moved)
            lczero::GameResult res = history->ComputeMctsResult(board.GenerateLegalMoves());
            if (res != lczero::GameResult::WHITE_WON) {
                std::cerr << "[FAIL] Black win 8-checks (White's turn) MCTS should be WHITE_WON, got: " << (int)res << std::endl;
                std::exit(1);
            }

            // Case D: Black to move (board.flipped() == true). White just moved (but Black won).
            std::string black_win_black_turn = "k9/10/10/10/10/10/10/10/10/K9 b - - 8+0 0 1";
            lczero::ChessBoard board_bt(black_win_black_turn);
            auto history_bt = std::make_unique<lczero::PositionHistory>();
            history_bt->Reset(board_bt, 0, 1);

            // Absolute check
            lczero::GameResult abs_bt = history_bt->ComputeGameResult();
            if (abs_bt != lczero::GameResult::BLACK_WON) {
                std::cerr << "[FAIL] Black win 8-checks absolute should be BLACK_WON, got: " << (int)abs_bt << std::endl;
                std::exit(1);
            }
            // MCTS check (relative Loss for White, who just moved)
            lczero::GameResult res_bt = history_bt->ComputeMctsResult(board_bt.GenerateLegalMoves());
            if (res_bt != lczero::GameResult::BLACK_WON) {
                std::cerr << "[FAIL] Black win 8-checks (Black's turn) MCTS should be BLACK_WON, got: " << (int)res_bt << std::endl;
                std::exit(1);
            }
        }
        std::cout << "  - [VERIFIED] All 8-checks absolute and relative evaluations checked successfully." << std::endl;

        std::cout << "[PASS] TEST 6 passed! (MCTS and Game absolute/relative checkmate and 8-checks values verified)\n" << std::endl;
    }

    // TEST 7: Castling Generation, Encoding, and Execution
    {
        std::cout << "TEST 7: Castling Generation, Encoding, and Execution..." << std::endl;
        
        // Dựng thế cờ trắng nhập thành (f1->i1 hoặc f1->b1)
        // 1r3k2r1/10/10/10/10/10/10/10/10/1R3K2R1 w BIbi - 8+8 0 1
        std::string castling_fen = "1r3k2r1/10/10/10/10/10/10/10/10/1R3K2R1 w BIbi - 8+8 0 1";
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
        std::string black_castling_fen = "1r3k2r1/10/10/10/10/10/10/10/10/1R3K2R1 b BIbi - 8+8 0 1";
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

    // TEST 8: castling on any rank (castlingAnyRank: a shuffled start may put the
    // royal piece and its rooks on rank 2), the castling rook's square in the
    // Zobrist key, and FEN output that reads back to the same rooks.
    {
        std::cout << "TEST 8: Castling on any rank, rook square in the key, FEN round-trip..." << std::endl;
        int bad = 0;
        auto fail = [&](const std::string& what) { ++bad; std::cerr << "[FAIL] " << what << std::endl; };
        auto moves_of = [](const lczero::ChessBoard& b) {
            std::vector<std::string> v;
            for (const auto& m : b.GenerateLegalMoves()) v.push_back(b.MoveToString(m));
            return v;
        };
        auto has = [](const std::vector<std::string>& v, const std::string& m) {
            return std::find(v.begin(), v.end(), m) != v.end();
        };
        auto play = [&](lczero::ChessBoard& b, const std::string& uci) {
            for (const auto& m : b.GenerateLegalMoves())
                if (b.MoveToString(m) == uci) { b.ApplyMove(m); return true; }
            fail("move " + uci + " is not legal in " + b.GetRawPosition().fen());
            return false;
        };
        auto castling_field = [](const std::string& fen) {
            std::istringstream ss(fen);
            std::string board, side, castling;
            ss >> board >> side >> castling;
            return castling;
        };

        // (a) White castles on rank 2, Black on rank 9; landing files h/g and d/e.
        const std::string r29 = "10/1r3k2r1/10/10/10/10/10/10/1R3K2R1/10 w BIbi - 8+8 0 1";
        {
            lczero::ChessBoard b(r29);
            const auto mv = moves_of(b);
            if (!has(mv, "f2h2") || !has(mv, "f2d2")) fail("rank-2 castling f2h2 / f2d2 not generated");
            if (play(b, "f2h2")) {
                const Position& p = b.GetRawPosition();
                if (p.piece_on(SQ_H2) != W_KING || p.piece_on(SQ_G2) != W_ROOK || p.piece_on(SQ_F2) || p.piece_on(SQ_I2))
                    fail("after f2h2 the king is not on h2 with the rook on g2");
                if (p.can_castle(WHITE_CASTLING) || !p.can_castle(BLACK_OO) || !p.can_castle(BLACK_OOO))
                    fail("after f2h2 White keeps a right or Black lost one");
                if (play(b, "f9d9") && (p.piece_on(SQ_D9) != B_KING || p.piece_on(SQ_E9) != B_ROOK || p.piece_on(SQ_B9)))
                    fail("after f9d9 the black king is not on d9 with the rook on e9");
            }
            // K/Q name the same rooks on the king's rank.
            lczero::ChessBoard kq("10/1r3k2r1/10/10/10/10/10/10/1R3K2R1/10 w KQkq - 8+8 0 1");
            const Position& p = kq.GetRawPosition();
            if (p.castling_rook_square(WHITE_OO) != SQ_I2 || p.castling_rook_square(WHITE_OOO) != SQ_B2 ||
                p.castling_rook_square(BLACK_OO) != SQ_I9 || p.castling_rook_square(BLACK_OOO) != SQ_B9 ||
                kq.Hash() != lczero::ChessBoard(r29).Hash())
                fail("KQkq on ranks 2/9 does not give the rights of BIbi");
        }

        // (a2) A royal piece already on its castling file does not move: the move
        // is written king -> rook ("h2i2"), never "h2h2", and reads back.
        {
            lczero::ChessBoard b("4k5/10/10/10/10/10/10/10/7K1R/10 w J - 8+8 0 1");
            const auto mv = moves_of(b);
            if (!has(mv, "h2j2") || has(mv, "h2h2")) fail("castling of a king on h2 must be written h2j2");
            const lczero::Move m = b.ParseMove("h2j2");
            if (m.is_null() || b.MoveToString(m) != "h2j2") fail("h2j2 does not read back");
            if (play(b, "h2j2") &&
                (b.GetRawPosition().piece_on(SQ_H2) != W_KING || b.GetRawPosition().piece_on(SQ_G2) != W_ROOK))
                fail("after h2j2 the king is not on h2 with the rook on g2");
        }

        // (b) All the safety rules hold off rank 1: the b2 rook shields the d2
        // target from the a2 rook, so queenside castling is illegal.
        {
            const auto mv = moves_of(lczero::ChessBoard("4k5/10/10/10/10/10/10/10/rR3K2R1/10 w BI - 8+8 0 1"));
            if (has(mv, "f2d2") || !has(mv, "f2h2")) fail("rook shield on rank 2: f2d2 must be illegal, f2h2 legal");
        }

        // (c) The i2 rook going to g2 opens the j1 bishop's diagonal to d7: the
        // castling move gives check, and it counts.
        {
            lczero::ChessBoard b("r9/10/10/3k6/10/10/10/10/1R3K2R1/B8B w BI - 8+8 0 1");
            if (play(b, "f2h2") && (!b.IsUnderCheck() || b.GetRawPosition().checks_remaining(WHITE) != 7))
                fail("discovered check by castling on rank 2 not seen (in check " +
                     std::to_string(b.IsUnderCheck()) + ", White's checks left " +
                     std::to_string(int(b.GetRawPosition().checks_remaining(WHITE))) + ")");
        }

        // (d) Same board, same rights mask (White queenside), different rook: the
        // keys differ (repetitions, NN cache), and so do the legal moves.
        {
            lczero::ChessBoard a("4k5/10/10/10/10/10/10/10/10/RR3K4 w A - 8+8 0 1");
            lczero::ChessBoard bb("4k5/10/10/10/10/10/10/10/10/RR3K4 w B - 8+8 0 1");
            if (a.GetRawPosition().castling_rook_square(WHITE_OOO) != SQ_A1 ||
                bb.GetRawPosition().castling_rook_square(WHITE_OOO) != SQ_B1)
                fail("castling rights A / B not read as the a1 / b1 rook");
            if (a.Hash() == bb.Hash()) fail("same key for the a1 and the b1 castling rook");
            if (has(moves_of(a), "f1d1") || !has(moves_of(bb), "f1d1"))
                fail("f1d1 must be legal with the b1 rook only");
        }

        // (e) fen() writes K/Q only where reading back finds the same rook, else
        // the file; reading fen() back gives the same rights and the same key.
        {
            struct Case { const char* fen; const char* field; };
            const Case cases[] = {
                {"1r3k2r1/10/10/10/10/10/10/10/10/1R3K2R1 w BIbi - 8+8 0 1", "KQkq"},
                {"4k5/10/10/10/10/10/10/10/10/RR3K4 w A - 8+8 0 1", "A"},      // Q would be b1
                {"4k5/10/10/10/10/10/10/10/10/RR3K4 w B - 8+8 0 1", "Q"},
                {"10/k9/10/10/10/10/10/10/3K2R1R1/10 w G - 8+8 0 1", "G"},      // K would be i2
                {"10/1r3k3r/10/10/10/10/10/10/10/5K4 b jb - 8+8 0 1", "jq"},    // k finds no rook on j
                {"10/10/10/10/1r3k3r/10/10/R3K2R2/10/10 b AHbj - 8+8 0 1", "KAjq"},
            };
            for (const Case& c : cases) {
                lczero::ChessBoard b(c.fen);
                const std::string out = b.GetRawPosition().fen();
                if (castling_field(out) != c.field)
                    fail(std::string("fen() of ") + c.fen + " writes castling '" + castling_field(out) +
                         "', expected '" + c.field + "'");
                lczero::ChessBoard back(out);
                const Position& p = b.GetRawPosition();
                const Position& q = back.GetRawPosition();
                for (CastlingRights cr : {WHITE_OO, WHITE_OOO, BLACK_OO, BLACK_OOO})
                    if (p.can_castle(cr) != q.can_castle(cr) ||
                        (p.can_castle(cr) && p.castling_rook_square(cr) != q.castling_rook_square(cr)))
                        fail(std::string("reading back fen() of ") + c.fen + " changed a castling right");
                if (b.Hash() != back.Hash()) fail(std::string("key changed reading back fen() of ") + c.fen);
            }
        }

        // (f) The training record stores each rook's square in the canonical
        // frame (ranks flipped when Black is to move).
        {
            for (const char* side : {"w", "b"}) {
                lczero::PositionHistory h;
                h.Reset(lczero::Position::FromFen(std::string("10/1r3k2r1/10/10/10/10/10/10/1R3K2R1/10 ") + side +
                                                  " BIbi - 8+8 0 1"));
                lczero::TrainingDataV1 rec;
                std::memset(&rec, 0, sizeof(rec));
                lczero::EncodePlanesIntoRecord(h, rec);
                // Either side: our rooks b/i on our 2nd rank (11, 18), theirs on our 9th (81, 88).
                if (rec.castling_us_ooo_sq != 11 || rec.castling_us_oo_sq != 18 ||
                    rec.castling_them_ooo_sq != 81 || rec.castling_them_oo_sq != 88)
                    fail(std::string("record castling squares (") + side + " to move): " +
                         std::to_string(rec.castling_us_ooo_sq) + " " + std::to_string(rec.castling_us_oo_sq) + " " +
                         std::to_string(rec.castling_them_ooo_sq) + " " + std::to_string(rec.castling_them_oo_sq) +
                         ", expected 11 18 81 88");
            }
        }

        if (bad) {
            std::cerr << "[FAIL] TEST 8: " << bad << " failure(s)" << std::endl;
            std::exit(1);
        }
        std::cout << "[PASS] TEST 8 passed! (castling on ranks 2/9, rook shield, discovered check, "
                     "rook square in the key, FEN round-trip, record squares)\n" << std::endl;
    }

    // TEST 9: the Zobrist keys come from a seed -- random for every run, in
    // [1e9, 1e10 - 1], repeatable with --zobrist-seed -- and every seed builds the
    // cuckoo (upcoming-repetition) tables with a wide margin.
    {
        std::cout << "TEST 9: Zobrist seed..." << std::endl;
        int bad = 0;
        auto fail = [&](const std::string& what) { ++bad; std::cerr << "[FAIL] " << what << std::endl; };
        constexpr uint64_t lo = 1000000000ULL, hi = 9999999999ULL;
        const uint64_t run_seed = Position::zobrist_seed();
        if (run_seed < lo || run_seed > hi) fail("this run's seed " + std::to_string(run_seed) + " out of range");

        // Draws: in range, all different, every leading digit about 1/9 of the time.
        std::set<uint64_t> seen;
        int lead[10] = {};
        for (int i = 0; i < 1800; ++i) {
            const uint64_t s = Position::random_zobrist_seed();
            if (s < lo || s > hi) fail("random seed " + std::to_string(s) + " out of range");
            seen.insert(s);
            ++lead[s / lo % 10];
        }
        if (seen.size() != 1800) fail("1800 random seeds gave only " + std::to_string(seen.size()) + " values");
        for (int d = 1; d <= 9; ++d)   // expected 200 each, standard deviation ~13
            if (lead[d] < 140 || lead[d] > 260)
                fail("leading digit " + std::to_string(d) + " drawn " + std::to_string(lead[d]) + " times of 1800");

        // Same seed, same keys; another seed, other keys.
        auto start_key = [] { return lczero::ChessBoard().Hash(); };
        const uint64_t a = 1234567890ULL, b = 9876543210ULL;
        if (Position::init(a) != a || Position::zobrist_seed() != a) fail("init(1234567890) used another seed");
        const uint64_t ka = start_key();
        Position::init(b);
        const uint64_t kb = start_key();
        Position::init(a);
        if (start_key() != ka || ka == kb) fail("the start position's key does not follow the seed");

        // Random seeds: the cuckoo insertions settle far below the bound.
        int worst = 0;
        for (int i = 0; i < 100; ++i) {
            const uint64_t s = Position::random_zobrist_seed();
            if (Position::init(s) != s) fail("seed " + std::to_string(s) + " was replaced");
            worst = std::max(worst, Position::zobrist_cuckoo_max_kicks());
        }
        if (worst > 200) fail("a cuckoo insertion needed " + std::to_string(worst) + " moves");
        Position::init(run_seed);   // back to this run's keys (endgame tables were built with them)

        if (bad) {
            std::cerr << "[FAIL] TEST 9: " << bad << " failure(s)" << std::endl;
            std::exit(1);
        }
        std::cout << "[PASS] TEST 9 passed! (seed " << run_seed << "; 1800 draws in range; same seed = same "
                     "keys; 100 random seeds, longest cuckoo insertion " << worst << " moves)\n" << std::endl;
    }

    std::cout << "========================================" << std::endl;
    std::cout << "ALL CHESSBOARD BRIDGE TESTS PASSED!" << std::endl;
    std::cout << "========================================\n" << std::endl;
}

// ============================================================================
// ADAPTER round-trip: FEN idempotence + MoveToString<->ParseMove (both colors).
// ============================================================================
void run_adapter_tests() {
    std::cout << "\n=== ADAPTER: FEN + move-string round-trip ===" << std::endl;
    setup_custom_variant();

    const std::vector<std::string> fens = {
        lczero::ChessBoard::kStartposFen,
        "5k4/10/10/10/10/1s8/10/S9/10/5K4 w - - 8+8 0 1",
        "1r7k/10/10/10/10/10/10/10/1r8/K9 w - - 8+8 0 1",
        "4k5/10/10/10/10/10/10/10/10/R8K b - - 1+8 0 1",  // BLACK to move
        // --- en passant LANDING ON A PROMOTION SQUARE ---------------------------
        // promotionRegionWhite = *8 *9 *10 and doubleStepRegionBlack = *10 *9 *8
        // overlap, so an ep capture can land inside White's promotion region.
        // Black pawn just played d9-d7; the ep square d8 is a promotion square, so
        // Pe7xd8 e.p. MUST promote, and promotionPieceTypes = b m n r v y makes SIX
        // legal moves that differ only in the promoted piece.
        "k9/10/10/3pP5/10/10/10/10/10/K9 w - d8 8+8 0 1",
        // Same case, but the ep square comes from the Sergeant's Alfil double-step
        // (s = fKifmnDifmnA): black s played d9-f7, passing through e8.
        "k9/10/10/3P1s4/10/10/10/10/10/K9 w - e8 8+8 0 1",
        // The Sergeant CAPTURES en passant too, and fK lets it do so BOTH straight
        // ahead and diagonally -- a pawn can only do the latter. Both must be covered.
        //   (a) straight: black s played e9-c7 (Alfil) through d8; white Sd7xd8 e.p.
        "k9/10/10/2sS6/10/10/10/10/10/K9 w - d8 8+8 0 1",
        //   (b) diagonal: black s played d9-d7 (Dabbaba) through d8; white Se7xd8 e.p.
        "k9/10/10/3sS5/10/10/10/10/10/K9 w - d8 8+8 0 1",
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

    // Move strings must be UNIQUE among a position's legal moves. ParseMove (and
    // Stockfish::UCI::to_move under it) resolves a string by scanning the legal
    // moves and returning the FIRST whose string matches, so two legal moves that
    // stringify identically make all but one unreachable through ANY string
    // interface -- silently, with no error. The ep-capture-with-promotion case
    // above is exactly that: six moves collapse to one string unless the promoted
    // piece is appended.
    int ep_promo_total = 0;
    for (const auto& fen : fens) {
        lczero::ChessBoard board(fen);
        lczero::MoveList moves = board.GenerateLegalMoves();
        std::map<std::string, int> seen;
        int ep_promo_here = 0;
        for (size_t i = 0; i < moves.size(); ++i) {
            const Stockfish::Move sm = moves[i].raw();
            if (Stockfish::type_of(sm) == Stockfish::EN_PASSANT
                && Stockfish::ep_promotion_type(sm) != Stockfish::NO_PIECE_TYPE)
                ++ep_promo_here;

            const std::string s = board.MoveToString(moves[i]);
            if (++seen[s] == 2) {
                std::cerr << "[FAIL] two distinct legal moves share the UCI string '"
                          << s << "'\n         in FEN: " << fen << std::endl;
                std::exit(1);
            }
        }
        ep_promo_total += ep_promo_here;
        if (ep_promo_here)
            std::cout << "  [info] " << ep_promo_here
                      << " en-passant-with-promotion move(s) in: " << fen << std::endl;
    }
    // Guard the fixtures themselves: if a FEN above ever stops producing the case,
    // the uniqueness check would pass vacuously and the coverage would be lost.
    if (ep_promo_total == 0) {
        std::cerr << "[FAIL] no en-passant-with-promotion move in ANY test position --\n"
                     "         the fixtures no longer cover the case this test exists for"
                  << std::endl;
        std::exit(1);
    }
    std::cout << "  [OK] UCI strings unique within each position ("
              << ep_promo_total << " ep-with-promotion moves covered)" << std::endl;
    std::cout << "[PASS] ADAPTER round-trip tests." << std::endl;
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
        "4k5/10/10/10/10/10/10/10/10/R8K b - - 8+8 0 1",          // Black to move
        "5k4/10/10/10/10/10/10/10/10/5K4 w - - 8+8 0 1",
        "1r7k/10/10/10/10/10/10/10/1r8/K9 w - - 8+8 0 1",
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
