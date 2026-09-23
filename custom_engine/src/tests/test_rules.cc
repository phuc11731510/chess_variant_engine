// Game-rule and move-generation tests:
//   --test-rules, --test-bits, --test-perft, --audit-generation.

#include "tests/test_common.h"

// ============================================================================
// RULES: repetition (3-fold) / rule50 (100-ply) / DYNAMIC 7-check counting.
// ============================================================================
void run_rules_tests() {
    std::cout << "\n=== RULES: repetition / rule50 / dynamic 7-check ===" << std::endl;
    setup_custom_variant();

    // Plays `ucis` from `fen` and returns the game result after EVERY ply
    // (index 0 = the start position), so a test can require the game to end
    // exactly on the right ply and not earlier.
    auto drive = [](const std::string& fen, const std::vector<std::string>& ucis) {
        auto h = std::make_unique<lczero::PositionHistory>();
        h->Reset(lczero::Position::FromFen(fen));   // rule50 and ply taken from the FEN
        std::vector<lczero::GameResult> out{h->ComputeGameResult()};
        for (const auto& uci : ucis) {
            lczero::Move m = h->Last().GetBoard().ParseMove(uci);
            if (m.is_null()) { std::cerr << "[FAIL] illegal move " << uci << " in " << fen << std::endl; std::exit(1); }
            h->Append(m);
            out.push_back(h->ComputeGameResult());
        }
        return out;
    };
    // The game must stay UNDECIDED until the last ply, which must give `last`.
    auto expect_end = [](const std::vector<lczero::GameResult>& res, lczero::GameResult last,
                         const char* what) {
        for (size_t i = 0; i + 1 < res.size(); ++i)
            if (res[i] != lczero::GameResult::UNDECIDED) {
                std::cerr << "[FAIL] " << what << ": game already over after ply " << i
                          << " (result " << (int)res[i] << ")" << std::endl;
                std::exit(1);
            }
        if (res.back() != last) {
            std::cerr << "[FAIL] " << what << ": final result " << (int)res.back()
                      << ", expected " << (int)last << std::endl;
            std::exit(1);
        }
    };
    const std::vector<std::string> shuffle2 = {"a1b1", "a10b10", "b1a1", "b10a10",
                                               "a1b1", "a10b10", "b1a1", "b10a10"};

    // 1. 3-fold repetition: kings shuffle back to the start twice -> DRAW on the
    // 8th ply (the third occurrence), not on the 4th (the second).
    expect_end(drive("k9/10/10/10/10/10/10/10/10/K9 w - - 8+8 0 1", shuffle2),
               lczero::GameResult::DRAW, "3-fold repetition from rule50=0");
    std::cout << "  [OK] 3-fold repetition -> DRAW exactly on the third occurrence" << std::endl;
    // 1b. The same with the rule-50 counter already at 30 (repetitions used to be
    // missed from rule50 = 14 on, see test_history.cc test 6).
    expect_end(drive("k9/10/10/10/10/10/10/10/10/K9 w - - 8+8 30 20", shuffle2),
               lczero::GameResult::DRAW, "3-fold repetition from rule50=30");
    std::cout << "  [OK] 3-fold repetition with rule50 = 30..38 -> DRAW" << std::endl;
    // 2. rule50: start at 99, one non-zeroing king move -> 100 plies -> DRAW.
    expect_end(drive("k9/10/10/10/10/10/10/10/10/K9 w - - 8+8 99 1", {"a1b1"}),
               lczero::GameResult::DRAW, "rule50 reaching 100");
    std::cout << "  [OK] rule50 reaches 100 plies -> DRAW (not at 99)" << std::endl;
    // 3. N-check: White needs 1 more check, delivers it -> WHITE_WON.
    expect_end(drive("4k5/10/10/10/10/10/10/10/10/R8K w - - 1+8 0 1", {"a1e1"}),
               lczero::GameResult::WHITE_WON, "last check");
    std::cout << "  [OK] White delivers its last check -> WHITE_WON" << std::endl;

    // 4. Check-counting must fire for a check that exists ONLY because of an
    // en-passant-with-promotion (see position.cpp gives_check's ep+promo block,
    // commit 52439cc): a check the PRE-promotion pawn geometrically could not
    // give. White pawn e7 x d7 e.p. (Black just double-stepped d9-d7 through
    // d8), landing on d8 -- a White promotion-zone square -- and promoting to
    // Rook. A plain pawn on d8 attacks c9/e9, NOT d10, so the resulting check on
    // the Black king (d10) along the open d-file exists ONLY via the promoted
    // Rook. checksRemaining[WHITE] starts at 1: if gives_check() ever stops
    // special-casing ep+promo, this check goes undetected, the counter does not
    // reach 0, and the game does NOT end -- a sharp, binary regression signal.
    expect_end(drive("3k6/10/10/3pP5/10/10/10/10/10/K9 w - d8 1+8 0 1", {"e7d8r"}),
               lczero::GameResult::WHITE_WON,
               "ep+promotion-only check (gives_check() ep+promo branch may be broken)");
    std::cout << "  [OK] check delivered SOLELY by an en-passant promotion (pawn->rook) "
                 "correctly decrements check-counting -> WHITE_WON" << std::endl;

    // 5. A double check counts TWO checks (variant rule; upstream Fairy-Stockfish
    // counts one per checking move). Ne6-d8 checks with the knight and uncovers
    // the rook on the e-file.
    {
        const std::string dbl = "4k5/10/10/10/4N5/10/10/10/10/K3R5 w - - ";
        expect_end(drive(dbl + "2+8 0 1", {"e6d8"}), lczero::GameResult::WHITE_WON,
                   "double check with 2 checks left");
        auto h = std::make_unique<lczero::PositionHistory>();
        h->Reset(lczero::Position::FromFen(dbl + "3+8 0 1"));
        h->Append(h->Last().GetBoard().ParseMove("e6d8"));
        const auto& raw = h->Last().GetBoard().GetRawPosition();
        if (popcount(raw.checkers()) != 2 || int(raw.checks_remaining(WHITE)) != 1 ||
            h->ComputeGameResult() != lczero::GameResult::UNDECIDED) {
            std::cerr << "[FAIL] double check with 3 checks left: checkers=" << popcount(raw.checkers())
                      << " remaining=" << int(raw.checks_remaining(WHITE)) << " (expected 2 and 1)" << std::endl;
            std::exit(1);
        }
        std::cout << "  [OK] a double check counts 2 checks (2 left -> win; 3 left -> 1 left)" << std::endl;
    }

    // Sergeant double-step on its SECOND move. doubleStepRegionWhite = *1 *2 *3, so a
    // white sergeant that single-stepped onto a region rank (1-3) must STILL be able to
    // double-step. Scenario: sergeant single-steps j2->i3 (diagonal), black replies, and
    // we expect the straight double-step i3->i5 to be among the legal moves.
    {
        std::string fen = "k9/10/10/10/10/10/10/10/9S/K9 w - - 8+8 0 1";
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
            "5k4/10/10/10/4p5/4P5/10/10/10/5K4 w - - 8+8 0 1",
            "1r7k/10/10/10/10/10/10/10/1r8/K9 w - - 8+8 0 1",
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
        {"5k4/10/10/10/10/1s8/10/S9/10/5K4 w - - 8+8 0 1", 4},        // sparse: Sergeant + kings
        {"5k4/10/10/10/4p5/4P5/10/10/10/5K4 w - - 8+8 0 1", 4},       // pawn tension
        // --- undo_move stress cases: perft_raw exercises do_move/undo_move; the
        // adapter rebuilds from FEN with NO undo, so a MATCH proves undo is correct
        // for the move types present at the root (printed below per case). ---
        {"5k4/10/10/10/10/10/1Pp7/10/10/5K4 b - b3b4 8+8 0 1", 3},    // ep+PROMO by pawn (c4xb3=, rank-3 zone)
        {"5k4/10/10/1pS7/10/10/10/10/10/5K4 w - b8b7 8+8 0 1", 3},    // ep+PROMO by Sergeant (c7xb8=, rank-8 zone)
        {"5k4/10/10/10/10/10/10/10/10/1R3K2R1 w BI - 8+8 0 1", 3},    // castling both sides (king-takes-rook undo)
        // plain-ep combos (captured piece restored by stored type in undo_move):
        {"5k4/10/10/10/10/1Ss7/10/10/10/5K4 b - b4b5 8+8 0 1", 3},    // sergeant-ep-sergeant (c5xb4, rank-4: no promo)
        {"5k4/10/10/10/10/1Sp7/10/10/10/5K4 b - b4b5 8+8 0 1", 3},    // pawn-ep-sergeant (c5xb4)
        {"5k4/10/10/10/1pS7/10/10/10/10/5K4 w - b7b6 8+8 0 1", 3},    // sergeant-ep-pawn (c6xb7)
    };

    bool all_ok = true;
    for (const auto& c : cases) {
        lczero::ChessBoard board(std::string(c.fen));   // adapter board (reused; perft copies)
        std::cout << "FEN: " << c.fen << std::endl;
        // Coverage report: which special move types sit at the ROOT, so a green
        // result provably exercises ep+promo / castling / plain-ep undo (each is
        // do_move'd then undo_move'd at depth>=2 by perft_raw).
        {
            Stockfish::StateInfo cst;
            Stockfish::Position cpos;
            cpos.set(v, c.fen, false, &cst, nullptr);
            int nEpPromo = 0, nCastle = 0, nPlainEp = 0;
            for (const auto& em : Stockfish::MoveList<Stockfish::LEGAL>(cpos)) {
                if (Stockfish::type_of(em.move) == Stockfish::CASTLING) ++nCastle;
                else if (Stockfish::type_of(em.move) == Stockfish::EN_PASSANT) {
                    if (Stockfish::ep_promotion_type(em.move) != Stockfish::NO_PIECE_TYPE) ++nEpPromo;
                    else ++nPlainEp;
                }
            }
            std::cout << "   root special moves: ep+promo=" << nEpPromo
                      << "  castling=" << nCastle << "  plain-ep=" << nPlainEp << std::endl;
        }
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
// AUDIT-GENERATION: a differential movegen fuzzer over the REAL game distribution.
// Plays many random games; at EVERY position it asserts (1) the adapter's legal
// move SET is IDENTICAL to raw Fairy-Stockfish's (not just the count — two
// movesets of equal size that differ in content, e.g. one direction miscoded as
// another, would pass a count-only check silently; this catches that), and (2)
// every move's NN policy index is in range AND injective per position. This is
// the "catch-all" for hidden movegen/rule bugs in positions the fixed tests never
// reach (near-8-checks, EP races, promotion, castling edges). No plane->position
// decoder needed: positions are carried forward by FEN (which also exercises the
// FEN round-trip).
//
// Caveat this does NOT cover: "adapter" and "raw" both bottom out in the SAME
// Stockfish::MoveList<LEGAL><Position> underneath (the adapter wraps, not
// reimplements, movegen) — so this proves the adapter never diverges from the
// core engine, not that the core engine's generation matches the INTENDED rules
// of variants.ini. That is what the hand-built FEN cases in run_ep_tests /
// run_rules_tests / run_adapter_tests / run_perft_tests are for.
// ============================================================================
void run_audit_generation(int num_games, int max_moves) {
    std::cout << "\n=== AUDIT-GENERATION: differential movegen fuzzer "
                 "(adapter vs raw Fairy-Stockfish over random games) ===" << std::endl;
    setup_custom_variant();
    if (num_games <= 0) num_games = 1000;
    if (max_moves <= 0) max_moves = 150;

    std::mt19937_64 rng(0xC0FFEEULL);
    uint64_t positions = 0, total_moves = 0;
    uint64_t set_mismatch = 0, nn_oob = 0, nn_collision = 0, terminal_games = 0;
    uint64_t set_mismatch_white = 0, set_mismatch_black = 0, positions_white = 0, positions_black = 0;
    int reported = 0;

    for (int g = 0; g < num_games; ++g) {
        std::string fen = lczero::ChessBoard::kStartposFen;
        for (int ply = 0; ply < max_moves; ++ply) {
            lczero::ChessBoard board(fen);
            lczero::MoveList adp = board.GenerateLegalMoves();
            const Position& raw_pos = board.GetRawPosition();

            ++positions;
            total_moves += adp.size();

            // (1) differential: adapter legal-move SET must equal raw Fairy-Stockfish's,
            // not just its size. Sort both by the raw Move's integer encoding (a stable,
            // cross-system-notation-free key — see the NN-interface test for the same
            // trick) and merge-walk them so every one-sided move gets reported, not just
            // the fact that a difference exists.
            // GenerateLegalMoves() hands out CANONICAL moves: for Black to move it
            // flips every move (board.cc, "the NN always sees its own pieces moving
            // up the board") before returning, and ApplyMove() flips back on the way
            // in -- self-consistent for real play, but it means adp's raw encoding
            // is NOT directly comparable to raw_pos's un-flipped Stockfish::Move for
            // Black positions. Flip the raw side the same way before keying, or every
            // Black-to-move position "mismatches" by construction (caught empirically:
            // an earlier version of this check flagged 99.9% of Black positions here,
            // 0% of White ones, before this flip was added -- a test bug, not an
            // engine bug; see the walkthrough for this session).
            auto key = [](Move m) { return static_cast<uint32_t>(m); };
            const bool black_to_move = raw_pos.side_to_move() == BLACK;
            std::vector<Move> raw_moves;
            raw_moves.reserve(adp.size() + 4);
            for (const auto& em : MoveList<LEGAL>(raw_pos)) {
                lczero::Move m(em.move);
                if (black_to_move) m.Flip(raw_pos.max_rank());
                raw_moves.push_back(m.raw());
            }
            std::sort(raw_moves.begin(), raw_moves.end(),
                      [&](Move a, Move b) { return key(a) < key(b); });

            std::vector<lczero::Move> adp_moves;
            adp_moves.reserve(adp.size());
            for (size_t i = 0; i < adp.size(); ++i) adp_moves.push_back(adp[i]);
            std::sort(adp_moves.begin(), adp_moves.end(),
                      [&](const lczero::Move& a, const lczero::Move& b) { return key(a.raw()) < key(b.raw()); });

            bool any_diff = false;
            for (size_t ri = 0, ai = 0; ri < raw_moves.size() || ai < adp_moves.size(); ) {
                const uint32_t rk = ri < raw_moves.size() ? key(raw_moves[ri]) : 0xFFFFFFFFu;
                const uint32_t ak = ai < adp_moves.size() ? key(adp_moves[ai].raw()) : 0xFFFFFFFFu;
                if (rk < ak) {
                    any_diff = true;
                    if (reported++ < 12)
                        std::cerr << "[MISMATCH] only in RAW (adapter missing): "
                                  << UCI::move(raw_pos, raw_moves[ri]) << "  FEN: " << fen << std::endl;
                    ++ri;
                } else if (ak < rk) {
                    any_diff = true;
                    if (reported++ < 12)
                        std::cerr << "[MISMATCH] only in ADAPTER (raw missing): "
                                  << board.MoveToString(adp_moves[ai]) << "  FEN: " << fen << std::endl;
                    ++ai;
                } else {
                    ++ri; ++ai;
                }
            }
            if (any_diff) {
                ++set_mismatch;
                if (raw_pos.side_to_move() == WHITE) ++set_mismatch_white; else ++set_mismatch_black;
            }
            if (raw_pos.side_to_move() == WHITE) ++positions_white; else ++positions_black;

            // (2) NN policy index: in-range and injective for this position.
            std::vector<int> seen;
            seen.reserve(adp.size());
            for (size_t i = 0; i < adp.size(); ++i) {
                const int idx = static_cast<int>(lczero::MoveToNNIndex(adp[i], 0));
                if (idx >= 10600) {
                    ++nn_oob;
                    if (reported++ < 12)
                        std::cerr << "[NN-OOB] idx=" << idx << " move=" << board.MoveToString(adp[i])
                                  << "  FEN: " << fen << std::endl;
                }
                if (std::find(seen.begin(), seen.end(), idx) != seen.end()) {
                    ++nn_collision;
                    if (reported++ < 12)
                        std::cerr << "[NN-COLLISION] idx=" << idx << " move=" << board.MoveToString(adp[i])
                                  << "  FEN: " << fen << std::endl;
                } else {
                    seen.push_back(idx);
                }
            }

            if (adp.size() == 0) { ++terminal_games; break; }

            // advance: pick a random legal move, apply on a copy, carry FEN forward.
            const lczero::Move mv = adp[static_cast<size_t>(rng() % adp.size())];
            lczero::ChessBoard child(board);
            child.ApplyMove(mv);   // return = "did move reset rule50?", NOT success — ignore (as perft does)
            fen = child.GetRawPosition().fen();
        }
    }

    std::cout << "  games=" << num_games << "  positions audited=" << positions
              << "  legal moves checked=" << total_moves
              << "  (terminal-ending games=" << terminal_games << ")" << std::endl;
    std::cout << "  coverage by side to move: white=" << positions_white
              << " (mismatch " << set_mismatch_white << ")   black=" << positions_black
              << " (mismatch " << set_mismatch_black << ")" << std::endl;
    // Black-to-move is where GenerateLegalMoves()'s canonical Flip() (board.cc) is
    // exercised at all -- if random play ever stopped reaching a Black move (e.g. a
    // future max_moves=1 misconfiguration), the flip-comparison above would pass
    // vacuously and silently lose coverage of exactly the thing that broke this
    // check once already this session (see walkthrough).
    if (positions_black == 0) {
        std::cerr << "[FAIL] AUDIT-GENERATION never reached a Black-to-move position -- "
                     "the move-set check's Flip()-handling is untested." << std::endl;
        std::exit(1);
    }
    std::cout << "  move-set mismatches=" << set_mismatch
              << "  NN out-of-range=" << nn_oob
              << "  NN collisions=" << nn_collision << std::endl;
    if (set_mismatch == 0 && nn_oob == 0 && nn_collision == 0) {
        std::cout << "[PASS] AUDIT-GENERATION: adapter movegen == raw FS and NN mapping clean over "
                  << positions << " real positions." << std::endl;
    } else {
        std::cerr << "[FAIL] AUDIT-GENERATION found discrepancies (see above)." << std::endl;
        std::exit(1);
    }
}
