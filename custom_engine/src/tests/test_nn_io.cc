// Neural-network interface tests (move <-> policy index, input planes):
//   --test-policy, --test-nn, --test-encoder.

#include "tests/test_common.h"

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
        lczero::ChessBoard start(std::string{lczero::ChessBoard::kStartposFen});
        nn_check_moves(start, 3, total, unmapped, geo_fail, inj_fail);
        lczero::ChessBoard promo(std::string("5k4/P9/10/10/10/10/10/10/10/5K4 w - - 8+8 0 1"));
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
        {"4k5/10/10/10/10/10/10/10/10/5K4 w - - 8+8 0 1", "two kings (White)"},
        {"4k5/10/10/10/10/10/10/10/10/5K4 b - - 3+5 0 1", "two kings (Black, flip)"},
        {"1r7k/10/10/10/10/10/10/10/1r8/K9 w - - 6+8 0 1", "rooks vs lone king (asym)"},
        {"5k4/10/10/10/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM w - - 8+8 0 1", "many White minors+pawns"},
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
        const float exp_cu = static_cast<float>(pos.checks_remaining(us)) / 10.0f;
        const float exp_ct = static_cast<float>(pos.checks_remaining(them)) / 10.0f;
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
        enc("4k5/10/10/10/10/10/10/10/10/5K4 w - - 8+8 0 1", a);   // white king f1
        enc("4k5/10/10/10/10/10/10/10/10/6K3 w - - 8+8 0 1", b);   // white king g1
        int diff = 0;
        for (size_t p = 0; p < a.size(); ++p) if (Stockfish::popcount(a[p].mask ^ b[p].mask)) ++diff;
        if (diff == 0) { std::cerr << "  [FAIL] injectivity: distinct positions encoded identically!\n"; ++fail; }
        else std::cout << "  [OK] injectivity: king f1 vs g1 differ in " << diff << " plane(s)" << std::endl;
    }

    if (fail == 0) std::cout << "[PASS] ENCODER ground-truth tests (NN input faithfully represents the board)." << std::endl;
    else { std::cerr << "[FAIL] " << fail << " encoder ground-truth failures." << std::endl; std::exit(1); }
}
