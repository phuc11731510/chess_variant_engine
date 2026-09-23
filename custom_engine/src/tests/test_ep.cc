// En passant (+ en passant with promotion) rule tests: --test-ep.

#include "tests/test_common.h"

void run_ep_tests() {
    // The real variant definition (app/variant_setup.cc). This file used to parse
    // its own copy of the INI, which drifted from the real one twice (it lacked
    // promotionPieceTypes once, and castling all along) -- a test of a copy is
    // not a test of the engine.
    std::cout << "Loading custom variant for testing..." << std::endl;
    const Variant* v = setup_custom_variant();

    // TEST 1: Straight EP capture (b5b4)
    {
        std::cout << "\n--- TEST 1: Straight EP Capture (b5b4) ---" << std::endl;
        Position pos;
        StateListPtr states(new std::deque<StateInfo>(1));
        // White King on f1, Black King on f10. White Sergeant on a3, Black Sergeant on b5.
        std::string fen = "5k4/10/10/10/10/1s8/10/S9/10/5K4 w - - 8+8 0 1";
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
        std::string fen = "5k4/10/10/10/10/s9/10/S9/10/5K4 w - - 8+8 0 1";
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
            std::string fen = "5k4/10/10/10/10/1s8/10/S9/10/5K4 w - - 8+8 0 1";
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
            std::string fen = "5k4/10/10/10/10/s9/10/S9/10/5K4 w - - 8+8 0 1";
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
            std::string fen = "5k4/10/10/10/10/1s8/10/S9/10/5K4 w - - 8+8 0 1";
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

    // TEST 4: En passant + promotion must NOT be offered if it exposes the
    // mover's OWN king to check. This is the classic "two pawns vanish from the
    // same rank" pin: White Pawn d7 captures Black Pawn e7 en passant, landing on
    // e8 (a promotion square) -- BOTH d7 and e7 empty out on the SAME move, and if
    // White's King and a Black Rook sit on that rank with nothing else between,
    // the capture reveals check on White's own king and must be illegal.
    //
    // Position::legal()'s EN_PASSANT branch (position.cpp, PRE-EXISTING code, not
    // touched by the ep+promotion feature) decides this purely from which SQUARES
    // empty out (`from`, capture_square(to)) and which fills (`to`) -- it never
    // looks at WHAT piece ends up on `to`, so promotion cannot bypass it. Verified
    // here empirically rather than trusted from reading alone: same geometry,
    // exposed (rook present) vs safe (rook removed) -- the move must flip from
    // absent to present.
    {
        std::cout << "\n--- TEST 4: EP+Promotion must not reveal own king to check ---" << std::endl;
        // Why 0-or-6, never a partial count: legality here depends ONLY on which
        // squares empty out / fill in (see Position::legal()'s EN_PASSANT branch,
        // mục 8a of this session's walkthrough) -- never on WHICH of the 6
        // promotion pieces ends up on `to`. So either all 6 variants are illegal
        // (exposed) or all 6 are legal (safe); it can never be some other number.

        auto count_d7e8 = [&](const std::string& fen) {
            Position pos;
            StateListPtr states(new std::deque<StateInfo>(1));
            pos.set(v, fen, false, &states->back(), Threads.main());
            int n = 0;
            for (const auto& m : MoveList<LEGAL>(pos))
                if (from_sq(m.move) == make_square(FILE_D, RANK_7) && to_sq(m.move) == make_square(FILE_E, RANK_8))
                    ++n;
            return n;
        };

        // Exposed: White King b7, Black Rook j7, nothing else on rank 7 between
        // them once d7 (mover) and e7 (captured pawn) vanish -> open rook check.
        const std::string exposed = "9k/10/10/1K1Pp4r/10/10/10/10/10/10 w - e8 8+8 0 1";
        // Safe control: identical position, Black Rook removed -> same capture,
        // same landing-in-promotion-zone geometry, but no discovered check.
        const std::string safe    = "9k/10/10/1K1Pp5/10/10/10/10/10/10 w - e8 8+8 0 1";

        const int n_exposed = count_d7e8(exposed);
        const int n_safe = count_d7e8(safe);

        if (n_exposed != 0) {
            std::cerr << "[FAIL] d7xe8 e.p.(+promo) is offered as LEGAL while it exposes White's "
                         "own King to the Black Rook on rank 7 -- found " << n_exposed
                      << " such move(s)! Position::legal()'s EN_PASSANT branch is not protecting "
                         "the ep+promotion case." << std::endl;
            std::exit(1);
        }
        if (n_safe == 0) {
            std::cerr << "[FAIL] test is vacuous: with the checking rook removed, d7xe8 e.p.(+promo) "
                         "should be legal (6 promotion choices) but NONE were found -- the fixture "
                         "itself is broken, not (necessarily) the engine." << std::endl;
            std::exit(1);
        }
        std::cout << "  [OK] exposed position: 0 legal d7xe8 e.p. moves (correctly excluded, "
                     "own King would be in check)" << std::endl;
        std::cout << "  [OK] safe control: " << n_safe << " legal d7xe8 e.p.(+promo) move(s) found "
                     "(fixture is not vacuous -- same geometry IS legal without the rook)" << std::endl;
        std::cout << "[PASS] EP+Promotion own-king-safety test passed!" << std::endl;
    }

    // TEST 5: En passant + promotion must be OFFERED as a check EVASION when the
    // captured pawn is the one giving check. This is the tricky mirror image of
    // TEST 4: en passant captures on `capture_square(to)`, not on `to` itself, so
    // the generic "landing square must be the checker's square" evasion filter
    // used for ordinary captures does not directly apply -- an engine that only
    // checked "is `to` the checker's square" would WRONGLY drop this move. Black
    // pawn double-steps d9-d7, giving check to White's King on e6 directly (not
    // discovered); White Pawn e7 can capture it en passant, landing on d8 (a
    // promotion square) -- removing the checking pawn resolves the check.
    {
        std::cout << "\n--- TEST 5: EP+Promotion offered as check evasion (captures the checker) ---" << std::endl;
        Position pos;
        StateListPtr states(new std::deque<StateInfo>(1));
        std::string fen = "9k/10/10/3pP5/4K5/10/10/10/10/10 w - d8 8+8 0 1";
        pos.set(v, fen, false, &states->back(), Threads.main());

        if (!pos.checkers()) {
            std::cerr << "[FAIL] test setup error: White King should be in check from the Black "
                         "Pawn on d7!" << std::endl;
            std::exit(1);
        }

        int n_e7d8 = 0;
        for (const auto& m : MoveList<LEGAL>(pos))
            if (from_sq(m.move) == make_square(FILE_E, RANK_7) && to_sq(m.move) == make_square(FILE_D, RANK_8))
                ++n_e7d8;

        if (n_e7d8 == 0) {
            std::cerr << "[FAIL] e7xd8 e.p.(+promo) — capturing the CHECKING pawn — is missing from "
                         "legal evasions. An evasion filter that only checks 'does `to` equal the "
                         "checker's square' would wrongly drop this (en passant captures on a "
                         "DIFFERENT square than `to`)." << std::endl;
            std::exit(1);
        }
        std::cout << "  [OK] " << n_e7d8 << " legal e7xd8 e.p.(+promo) evasion move(s) found "
                     "(correctly resolves check by capturing the checking pawn)" << std::endl;
        std::cout << "[PASS] EP+Promotion check-evasion test passed!" << std::endl;
    }

    // TEST 6: same own-king-safety property as TEST 4, but along a FILE instead
    // of a rank. TEST 4 relied on BOTH `from` and capture_square(to) vacating on
    // the same rank (the classic two-pawns-disappear pin). This is a DIFFERENT
    // mechanism: vacating `from` ALONE (regardless of what happens to the
    // captured piece's square) can open a FILE if `from` was the only blocker
    // between the King and an enemy Rook on that file. White King d1, White Pawn
    // d7 blocking the d-file, Black Rook d10. Black Pawn double-steps e9-e7
    // (ep-square e8); White's d7 pawn captures DIAGONALLY en passant to e8 --
    // OFF the d-file -- which empties d7 and opens the file. Verifies
    // Position::legal()'s generic `attackers_to(ksq, occupied, ~us)` (not
    // rank-specific code) really does cover this geometry too, not just TEST 4's.
    {
        std::cout << "\n--- TEST 6: EP+Promotion must not reveal own king to check (FILE, not rank) ---" << std::endl;

        auto count_d7e8 = [&](const std::string& fen) {
            Position pos;
            StateListPtr states(new std::deque<StateInfo>(1));
            pos.set(v, fen, false, &states->back(), Threads.main());
            int n = 0;
            for (const auto& m : MoveList<LEGAL>(pos))
                if (from_sq(m.move) == make_square(FILE_D, RANK_7) && to_sq(m.move) == make_square(FILE_E, RANK_8))
                    ++n;
            return n;
        };

        // Exposed: Black Rook d10, nothing else on the d-file between it and
        // White's King at d1 once d7 (the only blocker) vacates -> open file check.
        const std::string exposed = "3r5k/10/10/3Pp5/10/10/10/10/10/3K6 w - e8 8+8 0 1";
        // Safe control: identical position, Black Rook removed.
        const std::string safe    = "9k/10/10/3Pp5/10/10/10/10/10/3K6 w - e8 8+8 0 1";

        const int n_exposed = count_d7e8(exposed);
        const int n_safe = count_d7e8(safe);

        if (n_exposed != 0) {
            std::cerr << "[FAIL] d7xe8 e.p.(+promo) is offered as LEGAL while it opens the d-file "
                         "onto White's own King (Black Rook d10) -- found " << n_exposed
                      << " such move(s)! The FILE case of own-king exposure is not being caught."
                      << std::endl;
            std::exit(1);
        }
        if (n_safe == 0) {
            std::cerr << "[FAIL] test is vacuous: with the checking rook removed, d7xe8 e.p.(+promo) "
                         "should be legal (6 promotion choices) but NONE were found." << std::endl;
            std::exit(1);
        }
        std::cout << "  [OK] exposed position: 0 legal d7xe8 e.p. moves (correctly excluded, "
                     "own King would be file-checked)" << std::endl;
        std::cout << "  [OK] safe control: " << n_safe << " legal d7xe8 e.p.(+promo) move(s) found "
                     "(fixture is not vacuous)" << std::endl;
        std::cout << "[PASS] EP+Promotion own-king-safety (file) test passed!" << std::endl;
    }

    // TEST 7: TEST 4's rank-exposure property, but for the SERGEANT capturing
    // STRAIGHT (the fK component pawns cannot use at all). This exercises a
    // DIFFERENT code path than TEST 4/5/6: the Sergeant's straight en-passant
    // capture is generated by generate_moves() (the generic per-piece-type
    // mover, Pt as a runtime parameter), not generate_pawn_moves() (hard-coded
    // to literal PAWN) -- see commit 52439cc's two separate hunks (mục 2b of
    // this session's walkthrough). Position::legal()'s EN_PASSANT branch is
    // shared code, so it SHOULD protect both the same way; verified here rather
    // than assumed. Board: White Sergeant d7 captures straight to d8 (a Black
    // Sergeant on c7, arrived via an Alfil-style diagonal double-step, is the
    // victim -- reusing the exact geometry already proven in run_perft_tests'
    // "2sS6 ... d8" fixture). White King b7 + Black Rook j7 on rank 7: removing
    // BOTH d7 (mover) and c7 (captured) from rank 7 opens it.
    {
        std::cout << "\n--- TEST 7: Sergeant straight EP+Promotion, rank exposure ---" << std::endl;

        auto count_d7d8 = [&](const std::string& fen) {
            Position pos;
            StateListPtr states(new std::deque<StateInfo>(1));
            pos.set(v, fen, false, &states->back(), Threads.main());
            int n = 0;
            for (const auto& m : MoveList<LEGAL>(pos))
                if (from_sq(m.move) == make_square(FILE_D, RANK_7) && to_sq(m.move) == make_square(FILE_D, RANK_8))
                    ++n;
            return n;
        };

        // NOTE: the ep FEN token here is "d8c7" -- TWO squares, not one. The
        // parser (position.cpp, "4. En passant square") reads consecutive valid
        // file+rank pairs into a single st->epSquares BITBOARD, not just one
        // square. capture_square() then resolves via `ep_squares() & pieces()`
        // (position.h ~1504): whichever of the listed squares actually HAS a
        // piece on it (the landing square never does) IS the captured piece's
        // real square. This is REQUIRED whenever capture_square differs from
        // `to`'s file -- i.e. exactly the straight-capture-of-a-diagonally-
        // arrived-piece case this test targets. A single-square "d8" token
        // silently falls back to a same-FILE search from `to` (the plain-pawn
        // formula) and finds nothing here, misresolving capture_square --
        // caught empirically: an earlier version of this fixture used a bare
        // "d8" and capture_square(d8) resolved to a1 (a stray default), making
        // TEST 7 wrongly PASS the exposed case as legal. See run_perft_tests'
        // "b4b5"-style fixtures for the same two-square convention already in
        // use elsewhere in this codebase.
        const std::string exposed = "9k/10/10/1KsS5r/10/10/10/10/10/10 w - d8c7 8+8 0 1";
        const std::string safe    = "9k/10/10/1KsS6/10/10/10/10/10/10 w - d8c7 8+8 0 1";

        const int n_exposed = count_d7d8(exposed);
        const int n_safe = count_d7d8(safe);

        if (n_exposed != 0) {
            std::cerr << "[FAIL] Sergeant d7xd8 e.p.(+promo, straight) is offered as LEGAL while it "
                         "exposes White's own King to the Black Rook on rank 7 -- found " << n_exposed
                      << " such move(s)!" << std::endl;
            std::exit(1);
        }
        if (n_safe == 0) {
            std::cerr << "[FAIL] test is vacuous: with the checking rook removed, Sergeant d7xd8 "
                         "e.p.(+promo) should be legal (6 promotion choices) but NONE were found."
                      << std::endl;
            std::exit(1);
        }
        std::cout << "  [OK] exposed position: 0 legal Sergeant d7xd8 e.p. moves" << std::endl;
        std::cout << "  [OK] safe control: " << n_safe << " legal Sergeant d7xd8 e.p.(+promo) move(s) "
                     "found (fixture is not vacuous)" << std::endl;
        std::cout << "[PASS] Sergeant straight EP+Promotion rank-safety test passed!" << std::endl;
    }

    // TEST 8: a case that is IMPOSSIBLE with a plain Pawn. For a diagonal
    // capture (Pawn, or Sergeant using fK's diagonal component), capture_square
    // always shares `to`'s FILE -- so vacating it can never open a file check on
    // its own, because `to` immediately refills that same file with the
    // promoted piece. The Sergeant's STRAIGHT capture breaks that symmetry:
    // `from` and `to` share a file (d), but capture_square(to) does NOT (it's
    // c7, from the victim's diagonal Alfil double-step) -- so capture_square's
    // file (c) stays open after the move, unmasked by anything landing on it.
    // White King c1, Black Rook c10, nothing else on the c-file but the Black
    // Sergeant (victim) at c7: capturing it en passant should reveal a file
    // check that has NOTHING to do with the mover's own d7/d8 squares at all.
    {
        std::cout << "\n--- TEST 8: Sergeant straight EP+Promotion, file exposure via the CAPTURED square ---" << std::endl;

        auto count_d7d8 = [&](const std::string& fen) {
            Position pos;
            StateListPtr states(new std::deque<StateInfo>(1));
            pos.set(v, fen, false, &states->back(), Threads.main());
            int n = 0;
            for (const auto& m : MoveList<LEGAL>(pos))
                if (from_sq(m.move) == make_square(FILE_D, RANK_7) && to_sq(m.move) == make_square(FILE_D, RANK_8))
                    ++n;
            return n;
        };

        // ep token "d8c7" -- see TEST 7's note on why the two-square form is
        // required whenever capture_square differs from `to`'s file.
        const std::string exposed = "2r6k/10/10/2sS6/10/10/10/10/10/2K7 w - d8c7 8+8 0 1";
        const std::string safe    = "9k/10/10/2sS6/10/10/10/10/10/2K7 w - d8c7 8+8 0 1";

        const int n_exposed = count_d7d8(exposed);
        const int n_safe = count_d7d8(safe);

        if (n_exposed != 0) {
            std::cerr << "[FAIL] Sergeant d7xd8 e.p.(+promo, straight) is offered as LEGAL while it "
                         "exposes White's own King to the Black Rook on the c-FILE (via the captured "
                         "piece's square, not the mover's) -- found " << n_exposed << " such move(s)! "
                         "This is the case a rank-only or `to`-only check would miss entirely."
                      << std::endl;
            std::exit(1);
        }
        if (n_safe == 0) {
            std::cerr << "[FAIL] test is vacuous: with the checking rook removed, Sergeant d7xd8 "
                         "e.p.(+promo) should be legal (6 promotion choices) but NONE were found."
                      << std::endl;
            std::exit(1);
        }
        std::cout << "  [OK] exposed position: 0 legal Sergeant d7xd8 e.p. moves (correctly excluded, "
                     "own King file-checked via the CAPTURED piece's square)" << std::endl;
        std::cout << "  [OK] safe control: " << n_safe << " legal Sergeant d7xd8 e.p.(+promo) move(s) "
                     "found (fixture is not vacuous)" << std::endl;
        std::cout << "[PASS] Sergeant straight EP+Promotion capture-square-file-safety test passed!" << std::endl;
    }

    // TEST 9: end-to-end, REAL PLAY (do_move twice, no hand-written ep token at
    // all) for the exact geometry TEST 7/8 needed a hand-added "d8c7" ep token
    // for. This closes the gap those tests left open: it confirms do_move's OWN
    // bookkeeping after an Alfil-style diagonal double-step marks BOTH the
    // pass-through square AND the victim's actual square in st->epSquares (not
    // just the midpoint) -- so capture_square() resolves correctly (via the
    // "marked piece" branch, position.h ~1504) from ordinary self-play, not only
    // from a hand-constructed FEN. Then plays the straight en-passant capture
    // itself and verifies the victim is ACTUALLY removed from the board -- the
    // strongest possible check, stronger than "a legal move with this shape
    // exists": a resolver that silently pointed at the wrong square could still
    // generate a plausible-looking move while corrupting the board on do_move.
    {
        std::cout << "\n--- TEST 9: Sergeant straight EP+Promotion via REAL PLAY (do_move, not a hand ep token) ---" << std::endl;
        Position pos;
        StateListPtr states(new std::deque<StateInfo>(1));
        std::string fen = "9k/4s5/10/3S6/10/10/10/10/10/K9 b - - 8+8 0 1";
        pos.set(v, fen, false, &states->back(), Threads.main());

        std::string m1_str = "e9c7";
        Move m1 = UCI::to_move(pos, m1_str);
        if (m1 == MOVE_NONE) { std::cerr << "[FAIL] setup: e9c7 (Alfil double-step) not legal" << std::endl; std::exit(1); }
        states->emplace_back();
        pos.do_move(m1, states->back());

        const Bitboard eps = pos.ep_squares();
        const Square c7 = make_square(FILE_C, RANK_7), d8 = make_square(FILE_D, RANK_8);
        if (!(eps & c7) || !(eps & d8)) {
            std::cerr << "[FAIL] after e9c7 (real do_move), st->epSquares does not contain both the "
                         "pass-through square (d8) and the victim's own square (c7) -- only the "
                         "midpoint was marked. capture_square() would misresolve on a real self-play "
                         "board, not just on a hand-written FEN." << std::endl;
            std::exit(1);
        }
        if (pos.capture_square(d8) != c7) {
            std::cerr << "[FAIL] capture_square(d8) = " << UCI::square(pos, pos.capture_square(d8))
                      << ", expected c7, after REAL do_move (not a hand ep token)." << std::endl;
            std::exit(1);
        }

        std::string m2_str = "d7d8r";  // straight capture, promote to Rook
        Move m2 = UCI::to_move(pos, m2_str);
        if (m2 == MOVE_NONE || type_of(m2) != EN_PASSANT) {
            std::cerr << "[FAIL] d7d8r not recognized as a legal EN_PASSANT move after real play "
                         "(got type=" << (m2 == MOVE_NONE ? -1 : (int)type_of(m2)) << ")" << std::endl;
            std::exit(1);
        }
        states->emplace_back();
        pos.do_move(m2, states->back());

        if (pos.piece_on(c7) != NO_PIECE) {
            std::cerr << "[FAIL] Black Sergeant still on c7 after White's straight e.p. capture -- "
                         "the victim was NOT actually removed from the board. This is the corruption "
                         "scenario a wrong capture_square() resolution would cause: the move looks "
                         "legal and plausible, but the board silently keeps a piece that should be "
                         "gone." << std::endl;
            std::exit(1);
        }
        if (type_of(pos.piece_on(d8)) != ROOK || color_of(pos.piece_on(d8)) != WHITE) {
            std::cerr << "[FAIL] d8 does not hold a White Rook after d7d8r e.p." << std::endl;
            std::exit(1);
        }
        std::cout << "  [OK] real do_move marks BOTH c7 and d8 in epSquares after the diagonal "
                     "double-step (not just the midpoint)" << std::endl;
        std::cout << "  [OK] capture_square(d8) = c7, resolved correctly from real play" << std::endl;
        std::cout << "  [OK] Black Sergeant actually removed from c7; White Rook actually on d8"
                  << std::endl;
        std::cout << "[PASS] Sergeant straight EP+Promotion real-play end-to-end test passed!" << std::endl;
    }

    // TEST 10: the DIAGONAL analogue of TEST 6 -- vacating `from` alone opens a
    // diagonal onto White's own King, exercised by a Bishop this time (the only
    // piece in this variant whose checking geometry is purely diagonal, so a
    // pass here cannot be hiding behind a Rook's rank/file coverage the way a
    // Queen test could). White Pawn g7 sits on the a1-j10 diagonal; capturing
    // DIAGONALLY LEFT en passant to f8 (promotion zone) leaves that diagonal --
    // note capturing RIGHT to h8 would NOT leave it (h8 is also on a1-j10), so
    // this geometry specifically isolates the "mover's own square was the only
    // blocker" mechanism, same as TEST 6 but on the diagonal instead of a file.
    {
        std::cout << "\n--- TEST 10: EP+Promotion must not reveal own king to check (DIAGONAL, Bishop) ---" << std::endl;

        auto count_g7f8 = [&](const std::string& fen) {
            Position pos;
            StateListPtr states(new std::deque<StateInfo>(1));
            pos.set(v, fen, false, &states->back(), Threads.main());
            int n = 0;
            for (const auto& m : MoveList<LEGAL>(pos))
                if (from_sq(m.move) == make_square(FILE_G, RANK_7) && to_sq(m.move) == make_square(FILE_F, RANK_8))
                    ++n;
            return n;
        };

        // Exposed: Black Bishop j10, nothing else on the a1-j10 diagonal between
        // it and White's King at a1 once g7 (the only blocker) vacates.
        const std::string exposed = "k8b/10/10/5pP3/10/10/10/10/10/K9 w - f8 8+8 0 1";
        // Safe control: identical position, Black Bishop removed.
        const std::string safe    = "k9/10/10/5pP3/10/10/10/10/10/K9 w - f8 8+8 0 1";

        const int n_exposed = count_g7f8(exposed);
        const int n_safe = count_g7f8(safe);

        if (n_exposed != 0) {
            std::cerr << "[FAIL] g7xf8 e.p.(+promo) is offered as LEGAL while it opens the a1-j10 "
                         "diagonal onto White's own King (Black Bishop j10) -- found " << n_exposed
                      << " such move(s)! The DIAGONAL case of own-king exposure is not being caught."
                      << std::endl;
            std::exit(1);
        }
        if (n_safe == 0) {
            std::cerr << "[FAIL] test is vacuous: with the checking bishop removed, g7xf8 e.p.(+promo) "
                         "should be legal (6 promotion choices) but NONE were found." << std::endl;
            std::exit(1);
        }
        std::cout << "  [OK] exposed position: 0 legal g7xf8 e.p. moves (correctly excluded, "
                     "own King would be diagonally checked)" << std::endl;
        std::cout << "  [OK] safe control: " << n_safe << " legal g7xf8 e.p.(+promo) move(s) found "
                     "(fixture is not vacuous)" << std::endl;
        std::cout << "[PASS] EP+Promotion own-king-safety (diagonal) test passed!" << std::endl;
    }

    std::cout << "\n========================================" << std::endl;
    std::cout << "ALL EN PASSANT TESTS PASSED SUCCESSFULLY!" << std::endl;
    std::cout << "========================================" << std::endl;
}
