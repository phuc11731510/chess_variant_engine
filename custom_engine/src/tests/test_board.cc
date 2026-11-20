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
        // White royal on a1, Black royal on j10, Black Queen c2 and Rook h3: every square the royal can go to is covered.
        std::string stalemate_fen = "9k/10/10/10/10/10/10/7r2/2q7/K9 w - - 7+7 0 1";
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
        constexpr size_t expected_planes = lczero::kAuxPlaneBase + lczero::kAuxPlanesCount; // 204
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
        // White royal on a1 checked by the Queen on b2, which the Black royal on c3 protects.
        std::string white_checkmated_fen = "10/10/10/10/10/10/10/2k7/1q8/K9 w - - 7+7 0 1";
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
        // Black royal on a10 checked by the Queen on b9, which the White royal on c8 protects.
        std::string black_checkmated_fen = "k9/1Q8/2K7/10/10/10/10/10/10/10 b - - 7+7 0 1";
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

    // TEST 7: the royal piece's ring (squares it can only MOVE to, blocked on the way) and the ASCII notation
    // of the moves to the promotion ranks (a choice on rank 8, compulsory on rank 9; Black: 3 and 2).
    {
        std::cout << "TEST 7: royal ring, promotion notation..." << std::endl;
        int bad = 0;
        auto fail = [&](const std::string& what) { ++bad; std::cerr << "[FAIL] TEST 7: " << what << std::endl; };
        auto sq_str = [](int f, int r) { return std::string(1, char('a' + f)) + std::to_string(r + 1); };
        // The legal moves of the piece on `from` (as real-board strings), sorted. Every one is also parsed back and
        // checked to be one of the adapter's moves, and the strings must be pairwise different.
        auto moves_from = [&](const std::string& fen, const std::string& from) {
            lczero::ChessBoard b(fen);
            std::vector<std::string> v;
            for (const auto& m : b.GenerateLegalMoves()) {
                const std::string s = b.MoveToString(m);
                if (s.compare(0, from.size(), from) != 0 || !(s[from.size()] >= 'a' && s[from.size()] <= 'j')) continue;
                if (b.ParseMove(s).raw() != m.raw()) fail("ParseMove('" + s + "') is not the move it was written from");
                v.push_back(s);
            }
            std::sort(v.begin(), v.end());
            if (std::adjacent_find(v.begin(), v.end()) != v.end()) fail("two moves are written the same in " + fen);
            return v;
        };
        auto expect = [&](const char* what, const std::string& fen, const std::string& from, std::vector<std::string> want) {
            std::sort(want.begin(), want.end());
            const auto got = moves_from(fen, from);
            if (got != want) {
                std::string g, w;
                for (const auto& s : got) g += s + " ";
                for (const auto& s : want) w += s + " ";
                fail(std::string(what) + "\n   fen " + fen + "\n   got  " + g + "\n   want " + w);
            }
        };
        auto cat = [](std::vector<std::string> a, const std::vector<std::string>& b) { a.insert(a.end(), b.begin(), b.end()); return a; };
        auto with = [](const std::string& move, const std::string& letters) {
            std::vector<std::string> v;
            for (char c : letters) v.push_back(move + c);
            return v;
        };

        // Royal on e5, nothing around it: its 8 neighbours and the 16 squares of the ring (2 straight, 2 diagonal, 8 horse).
        {
            std::vector<std::string> want;
            for (int dx = -2; dx <= 2; ++dx)
                for (int dy = -2; dy <= 2; ++dy)
                    if (dx || dy) want.push_back("e5" + sq_str(4 + dx, 4 + dy));
            expect("royal e5 alone: 24 moves", "9k/10/10/10/10/4K5/10/10/10/10 w - - 7+7 0 1", "e5", want);
        }
        // An own pawn on e6: e6 is taken, e7 is blocked (the square between), d7 and f7 are blocked (the horse's leg).
        {
            std::vector<std::string> want;
            for (int dx = -2; dx <= 2; ++dx)
                for (int dy = -2; dy <= 2; ++dy) {
                    const std::string to = sq_str(4 + dx, 4 + dy);
                    if ((dx || dy) && to != "e6" && to != "e7" && to != "d7" && to != "f7") want.push_back("e5" + to);
                }
            expect("royal e5, own pawn e6: e7, d7, f7 blocked", "9k/10/10/10/4P5/4K5/10/10/10/10 w - - 7+7 0 1", "e5", want);
        }
        // The pawn on f5 blocks its side: g5 (straight), g4 and g6 (the horse's leg is the square next to it).
        {
            std::vector<std::string> want;
            for (int dx = -2; dx <= 2; ++dx)
                for (int dy = -2; dy <= 2; ++dy) {
                    const std::string to = sq_str(4 + dx, 4 + dy);
                    if ((dx || dy) && to != "f5" && to != "g5" && to != "g4" && to != "g6") want.push_back("e5" + to);
                }
            expect("royal e5, own pawn f5: g5, g4, g6 blocked", "9k/10/10/10/10/4KP4/10/10/10/10 w - - 7+7 0 1", "e5", want);
        }

        // A pawn reaching rank 8 stays (e7e8) or becomes n y g b c; reaching rank 9 it must become one of the nine.
        const std::string rank8 = "bcgny", rank9 = "bcgmnqrvy";
        expect("pawn e7: rank 8 is a choice", "9k/10/10/4P5/10/10/10/10/10/K9 w - - 7+7 0 1", "e7",
               cat({"e7e8"}, with("e7e8", rank8)));
        expect("pawn e8: rank 9 is compulsory", "9k/10/4P5/10/10/10/10/10/10/K9 w - - 7+7 0 1", "e8", with("e8e9", rank9));
        // Black is the mirror image: rank 3 a choice, rank 2 compulsory.
        expect("black pawn e4: rank 3 is a choice", "k9/10/10/10/10/10/4p5/10/10/K9 b - - 7+7 0 1", "e4",
               cat({"e4e3"}, with("e4e3", rank8)));
        expect("black pawn e3: rank 2 is compulsory", "k9/10/10/10/10/10/10/4p5/10/K9 b - - 7+7 0 1", "e3", with("e3e2", rank9));
        // A capture onto the promotion rank is written the same way, and the letters b, c, g (also file letters) stay unambiguous.
        expect("pawn e7 x d8 and push", "9k/10/3r6/4P5/10/10/10/10/10/K9 w - - 7+7 0 1", "e7",
               cat(cat({"e7e8", "e7d8"}, with("e7e8", rank8)), with("e7d8", rank8)));
        // A rank-10 square is written with two digits, and the letters never get mixed up with it.
        expect("rook a1: the whole file, a10 included", "k9/10/10/10/10/10/10/10/10/R8K w - - 7+7 0 1", "a1",
               {"a1a2", "a1a3", "a1a4", "a1a5", "a1a6", "a1a7", "a1a8", "a1a9", "a1a10", "a1b1", "a1c1", "a1d1", "a1e1", "a1f1", "a1g1", "a1h1", "a1i1"});

        if (bad) std::exit(1);
        std::cout << "[PASS] TEST 7 passed! (royal ring and blocking, promotion notation on both sides)\n" << std::endl;
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
        "5k4/10/10/10/10/1s8/10/S9/10/5K4 w - - 7+7 0 1",
        "9k/10/10/10/10/10/10/7r2/2q7/K9 w - - 7+7 0 1",
        "4k5/10/10/10/10/10/10/10/10/R8K b - - 1+7 0 1",  // BLACK to move
        // --- en passant LANDING ON A PROMOTION SQUARE ---------------------------
        // promotionRegionWhite = *8 *9 *10 and doubleStepRegionBlack = *10 *9 *8
        // overlap, so an ep capture can land inside White's promotion region.
        // Black pawn just played d9-d7; the ep square d8 is a promotion square, so
        // Pe7xd8 e.p. MUST promote, and promotionPieceTypes = b m n r v y makes SIX
        // legal moves that differ only in the promoted piece.
        "k9/10/10/3pP5/10/10/10/10/10/K9 w - d8 7+7 0 1",
        // Same case, but the ep square comes from the Sergeant's Alfil double-step
        // (s = fKifmnDifmnA): black s played d9-f7, passing through e8.
        "k9/10/10/3P1s4/10/10/10/10/10/K9 w - e8 7+7 0 1",
        // The Sergeant CAPTURES en passant too, and fK lets it do so BOTH straight
        // ahead and diagonally -- a pawn can only do the latter. Both must be covered.
        //   (a) straight: black s played e9-c7 (Alfil) through d8; white Sd7xd8 e.p.
        "k9/10/10/2sS6/10/10/10/10/10/K9 w - d8 7+7 0 1",
        //   (b) diagonal: black s played d9-d7 (Dabbaba) through d8; white Se7xd8 e.p.
        "k9/10/10/3sS5/10/10/10/10/10/K9 w - d8 7+7 0 1",
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
        "4k5/10/10/10/10/10/10/10/10/R8K b - - 7+7 0 1",          // Black to move
        "5k4/10/10/10/10/10/10/10/10/5K4 w - - 7+7 0 1",
        "9k/10/10/10/10/10/10/7r2/2q7/K9 w - - 7+7 0 1",
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
