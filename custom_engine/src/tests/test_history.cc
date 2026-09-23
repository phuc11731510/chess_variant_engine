// Position-history, hashing and game-end tests: --test-history
//
// These cover the pieces the search leans on for "is this the same position?"
// and "is this game over?", each of which can go wrong without any error:
//
//   1. NodeTree trims the played history (200 -> 100 plies, node.cc). Over long
//      random games, the trimmed history must stay indistinguishable from an
//      untrimmed one: same position/key/rule50/ply, same repetition counts
//      (while rule50 < 100), same NN input planes, and copies of it must still
//      undo moves correctly (the StateInfo chain is re-linked by hand).
//   2. Zobrist keys: the incrementally updated key equals the key rebuilt from
//      the FEN, and positions that differ only by en-passant rights (including
//      a Sergeant's straight double step, whose two e.p. squares share a file)
//      have different keys.
//   3. The NN cache key tells a first occurrence from a repeated one (the NN
//      input carries a repetition plane, so their evaluations differ).
//   4. Game-end precedence matches Fairy-Stockfish: a checkmate delivered on
//      the 100th quiet ply is a checkmate; a stalemate on it is a 50-move draw
//      (stalemate otherwise loses in this variant) -- in the game result AND in
//      the MCTS terminal result.
//   5. N-check wins are reported from the right side, for both colours.
//   6. Repetitions (count, threefold draw, NN plane) at every rule-50 count.
//
// Every sub-test runs even if an earlier one failed; exit 1 at the end if any did.

#include "tests/test_common.h"

namespace {

int g_failures = 0;

using lczero::GameResult;

#define EXPECT(cond, msg)                                         \
    do {                                                          \
        if (!(cond)) {                                            \
            ++g_failures;                                         \
            std::cerr << "[FAIL] " << msg << std::endl;           \
        }                                                         \
    } while (0)

const Variant* g_variant = nullptr;

std::string FenOf(const lczero::PositionHistory& h) {
    return h.Last().GetBoard().GetRawPosition().fen();
}

// ---------------------------------------------------------------------------
// 1. Trimmed history == untrimmed history.
// ---------------------------------------------------------------------------

// Picks a legal move for a LONG game with many repetitions: prefers undoing the
// mover's own previous move, avoids checks once the mover is 2 checks from
// winning (so the game does not end by n-checks). Null when no legal move.
lczero::Move PickLongGameMove(const lczero::PositionHistory& h, lczero::Move own_prev,
                              std::mt19937& rng) {
    const auto legal = h.Last().GetBoard().GenerateLegalMoves();
    if (legal.empty()) return lczero::Move();
    const Position& raw = h.Last().GetBoard().GetRawPosition();
    const bool avoid_checks = raw.checks_remaining(raw.side_to_move()) <= 2;
    std::vector<lczero::Move> ok, undo;
    for (const auto& m : legal) {
        lczero::Move real = m;
        if (h.IsBlackToMove()) real.Flip(RANK_10);
        if (avoid_checks && raw.gives_check(real.raw())) continue;
        ok.push_back(m);
        if (!own_prev.is_null() && type_of(m.raw()) == NORMAL &&
            from_sq(m.raw()) == to_sq(own_prev.raw()) &&
            to_sq(m.raw()) == from_sq(own_prev.raw())) {
            undo.push_back(m);
        }
    }
    if (ok.empty()) ok.assign(legal.begin(), legal.end());
    if (!undo.empty() && rng() % 100 < 45) return undo[rng() % undo.size()];
    return ok[rng() % ok.size()];
}

bool SamePlanes(const lczero::PositionHistory& a, const lczero::PositionHistory& b,
                int* first_diff) {
    lczero::InputPlanes pa, pb;
    int ta = 0, tb = 0;
    lczero::EncodePositionForNN(a, lczero::kMoveHistory, lczero::FillEmptyHistory::FEN_ONLY, &pa, &ta);
    lczero::EncodePositionForNN(b, lczero::kMoveHistory, lczero::FillEmptyHistory::FEN_ONLY, &pb, &tb);
    for (size_t i = 0; i < pa.size(); ++i) {
        if (!(pa[i].mask == pb[i].mask) || pa[i].value != pb[i].value) {
            *first_diff = static_cast<int>(i);
            return false;
        }
    }
    return true;
}

void TestTrimmedHistory() {
    std::cout << "\n--- 1. Trimmed history (NodeTree, 200 -> 100 plies) == untrimmed history ---" << std::endl;
    const int kGames = 4, kMaxPlies = 480;
    long compared = 0, repeated_after_trim = 0, trims_seen = 0, copy_checks = 0;
    int longest = 0;
    for (int game = 0; game < kGames; ++game) {
        std::mt19937 rng(1000 + game);
        auto tree = std::make_unique<lczero::classic::NodeTree>();
        tree->ResetToPosition(kUciStartFen, {});
        auto ref = std::make_unique<lczero::PositionHistory>();
        ref->Reset(lczero::Position::FromFen(kUciStartFen));
        std::vector<lczero::Move> played;
        int bad = 0;
        for (int ply = 0; ply < kMaxPlies && bad < 3; ++ply) {
            const lczero::Move own_prev = played.size() >= 2 ? played[played.size() - 2] : lczero::Move();
            const lczero::Move m = PickLongGameMove(*ref, own_prev, rng);
            if (m.is_null()) break;
            const int len_before = tree->GetPositionHistory().GetLength();
            tree->MakeMove(m);
            ref->Append(m);
            played.push_back(m);
            if (tree->GetPositionHistory().GetLength() < len_before) ++trims_seen;
            longest = std::max(longest, ply + 1);

            const auto& a = tree->GetPositionHistory();
            const auto& b = *ref;
            const auto& pa = a.Last();
            const auto& pb = b.Last();
            ++compared;
            bool ok = true;
            auto mismatch = [&](const std::string& what) {
                ok = false;
                if (++bad <= 3) {
                    std::cerr << "    game " << game << " ply " << ply + 1 << " (tree history length "
                              << a.GetLength() << "): " << what << std::endl;
                }
            };
            if (FenOf(a) != FenOf(b)) mismatch("FEN differs: " + FenOf(a) + " vs " + FenOf(b));
            if (pa.Hash() != pb.Hash()) mismatch("key differs");
            if (pa.GetRule50Ply() != pb.GetRule50Ply()) mismatch("rule50 differs");
            if (pa.GetGamePly() != pb.GetGamePly()) mismatch("game ply differs");
            if (pb.GetRule50Ply() < 100) {
                if (pa.GetRepetitions() != pb.GetRepetitions()) {
                    mismatch("repetitions " + std::to_string(pa.GetRepetitions()) + " vs " +
                             std::to_string(pb.GetRepetitions()));
                }
                if (pa.GetPliesSincePrevRepetition() != pb.GetPliesSincePrevRepetition()) {
                    mismatch("plies since previous repetition differ");
                }
                if (pb.GetRepetitions() > 0 && ply >= 200) ++repeated_after_trim;
            }
            int plane = -1;
            if (!SamePlanes(a, b, &plane)) mismatch("NN input plane " + std::to_string(plane) + " differs");

            // Copies of the trimmed history must still append and undo correctly
            // (their StateInfo chain is re-linked by hand in the copy code).
            if (ply % 17 == 0) {
                const auto legal = pa.GetBoard().GenerateLegalMoves();
                if (legal.size() >= 1) {
                    auto c1 = std::make_unique<lczero::PositionHistory>(a);
                    auto c2 = std::make_unique<lczero::PositionHistory>();
                    *c2 = a;
                    for (auto* c : {c1.get(), c2.get()}) {
                        c->Append(legal[rng() % legal.size()]);
                        const auto next = c->Last().GetBoard().GenerateLegalMoves();
                        if (!next.empty()) {
                            c->Append(next[rng() % next.size()]);
                            c->Pop();
                        }
                        c->Pop();
                        ++copy_checks;
                        if (FenOf(*c) != FenOf(a) || c->Last().Hash() != pa.Hash()) {
                            mismatch("a copy of the history did not return to the same position after "
                                     "Append/Pop: " + FenOf(*c));
                        }
                    }
                }
            }
            if (!ok) ++g_failures;
        }
    }
    std::cout << "  " << compared << " positions compared, longest game " << longest
              << " plies, trims " << trims_seen << ", repeated positions after ply 200: "
              << repeated_after_trim << ", copy/undo checks " << copy_checks << std::endl;
    EXPECT(longest >= 300, "no game got past 300 plies: the trim was barely exercised");
    EXPECT(trims_seen > 0, "the history was never trimmed");
    EXPECT(repeated_after_trim > 0, "no repetition after the trim: repetition tracking not exercised");
}

// ---------------------------------------------------------------------------
// 2. Zobrist keys.
// ---------------------------------------------------------------------------
Key KeyFromFen(const std::string& fen) {
    Position p;
    StateInfo st;
    p.set(g_variant, fen, false, &st, nullptr);
    return p.key();
}

std::string WithoutEp(const std::string& fen) {
    std::istringstream in(fen);
    std::vector<std::string> f;
    for (std::string t; in >> t;) f.push_back(t);
    if (f.size() > 3) f[3] = "-";
    std::string out;
    for (size_t i = 0; i < f.size(); ++i) out += (i ? " " : "") + f[i];
    return out;
}

void TestZobristKeys() {
    std::cout << "\n--- 2. Zobrist keys (incremental == from-FEN; en-passant rights count) ---" << std::endl;
    // (a) Random games: the key do_move maintains == the key set() rebuilds.
    std::mt19937 rng(4242);
    long checked = 0, mismatches = 0, with_ep = 0;
    for (int game = 0; game < 150; ++game) {
        Position pos;
        StateListPtr states(new std::deque<StateInfo>(1));
        pos.set(g_variant, kUciStartFen, false, &states->back(), Threads.main());
        for (int ply = 0; ply < 200; ++ply) {
            MoveList<LEGAL> legal(pos);
            if (legal.size() == 0) break;
            states->emplace_back();
            pos.do_move(legal.begin()[rng() % legal.size()], states->back());
            if (pos.checks_remaining(WHITE) <= 0 || pos.checks_remaining(BLACK) <= 0) break;
            ++checked;
            if (pos.ep_squares()) ++with_ep;
            if (KeyFromFen(pos.fen()) != pos.key() && ++mismatches <= 3) {
                std::cerr << "    incremental key != key from FEN at " << pos.fen() << std::endl;
            }
        }
    }
    std::cout << "  random games: " << checked << " positions (" << with_ep
              << " with e.p. rights), incremental/FEN key mismatches=" << mismatches << std::endl;
    EXPECT(mismatches == 0, mismatches << " positions whose incremental key != key rebuilt from FEN");

    // (b) The same board with and without e.p. rights must hash differently,
    // after a REAL double step (do_move, not a hand-written e.p. token).
    struct EpCase { const char* fen; const char* move; const char* what; };
    const EpCase cases[] = {
        {"9k/4s5/10/3S6/10/10/10/10/10/K9 b - - 8+8 0 1", "e9e7",
         "Sergeant STRAIGHT double step (e.p. squares e8+e7, same file)"},
        {"9k/4s5/10/3S6/10/10/10/10/10/K9 b - - 8+8 0 1", "e9c7",
         "Sergeant DIAGONAL double step (e.p. squares d8+c7)"},
        {"9k/10/4p5/3P6/10/10/10/10/10/K9 b - - 8+8 0 1", "e8e6",
         "pawn double step (e.p. square e7)"},
    };
    for (const auto& c : cases) {
        Position pos;
        StateListPtr states(new std::deque<StateInfo>(1));
        pos.set(g_variant, c.fen, false, &states->back(), Threads.main());
        std::string mv = c.move;
        const Move m = UCI::to_move(pos, mv);
        if (m == MOVE_NONE) {
            ++g_failures;
            std::cerr << "[FAIL] setup: " << c.move << " not legal in " << c.fen << std::endl;
            continue;
        }
        states->emplace_back();
        pos.do_move(m, states->back());
        const std::string fen = pos.fen();
        const Key with = pos.key();
        const Key without = KeyFromFen(WithoutEp(fen));
        std::cout << "  " << c.what << ": FEN " << fen << " -> keys "
                  << (with != without ? "differ" : "EQUAL") << std::endl;
        EXPECT(bool(pos.ep_squares()), c.what << ": no e.p. rights were set (setup)");
        EXPECT(with != without, c.what << ": the key ignores the e.p. rights, so this position "
               "and the same board without them count as repetitions of each other and share "
               "NN-cache entries");
        EXPECT(KeyFromFen(fen) == with, c.what << ": key rebuilt from the FEN differs");
    }
}

// ---------------------------------------------------------------------------
// 3. NN cache key: first occurrence vs repetition.
// ---------------------------------------------------------------------------
void TestCacheKeyRepetitions() {
    std::cout << "\n--- 3. NN cache key distinguishes a repeated position ---" << std::endl;
    fztest::TestSearchOptions opts;
    auto cache = lczero::CreateMemCache(std::make_unique<fztest::DetBackend>(true, 8, 0), opts.Dict());
    auto first = std::make_unique<lczero::PositionHistory>();
    first->Reset(lczero::Position::FromFen(kUciStartFen));
    auto again = std::make_unique<lczero::PositionHistory>();
    again->Reset(lczero::Position::FromFen(kUciStartFen));
    for (const char* uci : {"e2d4", "e9d7", "d4e2", "d7e9"}) {  // knights out and back
        const lczero::Move m = fztest::ParseLegalMove(*again, uci);
        if (m.is_null()) {
            ++g_failures;
            std::cerr << "[FAIL] setup: " << uci << " not legal" << std::endl;
            return;
        }
        again->Append(m);
    }
    EXPECT(again->Last().Hash() == first->Last().Hash(), "setup: not back to the start position");
    EXPECT(again->Last().GetRepetitions() == 1, "setup: repetition count is "
           << again->Last().GetRepetitions() << ", expected 1");
    // The NN sees the repetition: plane 26 of the current board is set only for `again`.
    int plane = -1;
    lczero::InputPlanes p1, p2;
    int t = 0;
    lczero::EncodePositionForNN(*first, lczero::kMoveHistory, lczero::FillEmptyHistory::FEN_ONLY, &p1, &t);
    lczero::EncodePositionForNN(*again, lczero::kMoveHistory, lczero::FillEmptyHistory::FEN_ONLY, &p2, &t);
    const bool rep_plane_differs = !(p1[26].mask == p2[26].mask) || p1[26].value != p2[26].value;
    (void)plane;
    // Cache the first occurrence, then ask for the repeated one.
    const auto legal = first->Last().GetBoard().GenerateLegalMoves();
    lczero::EvalResult r;
    r.p.resize(legal.size());
    auto comp = cache->CreateComputation();
    comp->AddInput(lczero::EvalPosition{first.get(),
                                        std::span<const lczero::Move>(legal.data(), legal.size())},
                   r.AsPtr());
    comp->ComputeBlocking();
    const bool hit = cache->GetCachedEvaluation(lczero::EvalPosition{
                         again.get(), std::span<const lczero::Move>(legal.data(), legal.size())})
                         .has_value();
    std::cout << "  NN input differs (repetition plane): " << (rep_plane_differs ? "yes" : "no")
              << "; cache lookup for the repetition: " << (hit ? "HIT (stale eval)" : "miss")
              << std::endl;
    EXPECT(rep_plane_differs, "setup: the NN input does not mark the repetition");
    EXPECT(!hit, "the NN cache returned the eval of the FIRST occurrence for the repeated "
           "position although the network input differs (lc0 hashes repetitions into the key)");
}

// ---------------------------------------------------------------------------
// 4. Game-end precedence (checkmate / stalemate on the 100th quiet ply).
// ---------------------------------------------------------------------------
GameResult GameResultOf(const std::string& fen) {
    auto h = std::make_unique<lczero::PositionHistory>();
    h->Reset(lczero::Position::FromFen(fen));
    return h->ComputeGameResult();
}

GameResult MctsResultOf(const std::string& fen) {
    auto h = std::make_unique<lczero::PositionHistory>();
    h->Reset(lczero::Position::FromFen(fen));
    return h->ComputeMctsResult(h->Last().GetBoard().GenerateLegalMoves());
}

const char* Name(GameResult r) {
    switch (r) {
        case GameResult::WHITE_WON: return "WHITE_WON";
        case GameResult::BLACK_WON: return "BLACK_WON";
        case GameResult::DRAW: return "DRAW";
        default: return "UNDECIDED";
    }
}

void TestGameEndPrecedence() {
    std::cout << "\n--- 4. Game-end precedence vs Fairy-Stockfish (50-move rule vs mate/stalemate) ---" << std::endl;
    // Black king a10 mated by Qb9 (guarded by Rb1) / stalemated by Qb7 + Rj9.
    const std::string mate = "k9/1Q8/10/10/10/10/10/10/10/1R7K b - - 8+8 ";
    const std::string stale = "k9/9R/10/1Q8/10/10/10/10/10/9K b - - 8+8 ";
    struct Case { std::string fen; GameResult game, mcts; const char* what; };
    // ComputeGameResult is absolute (WHITE_WON = White won); ComputeMctsResult is
    // relative to the side that just moved (WHITE_WON = the mover won).
    const Case cases[] = {
        {mate + "10 80", GameResult::WHITE_WON, GameResult::WHITE_WON, "checkmate, rule50=10"},
        {mate + "100 80", GameResult::WHITE_WON, GameResult::WHITE_WON, "checkmate, rule50=100"},
        {stale + "10 80", GameResult::WHITE_WON, GameResult::WHITE_WON, "stalemate (= loss), rule50=10"},
        {stale + "100 80", GameResult::DRAW, GameResult::DRAW, "stalemate, rule50=100 (50-move draw)"},
    };
    for (const auto& c : cases) {
        // Preconditions straight from Fairy-Stockfish.
        Position pos;
        StateInfo st;
        pos.set(g_variant, c.fen, false, &st, nullptr);
        const bool no_moves = MoveList<LEGAL>(pos).size() == 0;
        const bool in_check = bool(pos.checkers());
        const bool want_check = std::string(c.what).find("checkmate") == 0;
        if (!no_moves || in_check != want_check) {
            ++g_failures;
            std::cerr << "[FAIL] setup: " << c.fen << " is not a " << c.what << std::endl;
            continue;
        }
        Value fsf = VALUE_NONE;
        const bool fsf_ends_by_rule = pos.is_optional_game_end(fsf, 0);
        const GameResult g = GameResultOf(c.fen), m = MctsResultOf(c.fen);
        std::cout << "  " << c.what << ": FSF " << (fsf_ends_by_rule ? "rule-ends (draw)" : "mate/stalemate")
                  << " | game=" << Name(g) << " mcts=" << Name(m) << std::endl;
        EXPECT(g == c.game, c.what << ": ComputeGameResult=" << Name(g) << ", Fairy-Stockfish's rules give "
               << Name(c.game));
        EXPECT(m == c.mcts, c.what << ": ComputeMctsResult=" << Name(m) << ", expected " << Name(c.mcts));
    }
}

// ---------------------------------------------------------------------------
// 5. N-check wins, both colours, both result functions.
// ---------------------------------------------------------------------------
void TestCheckCountResults() {
    std::cout << "\n--- 5. N-check wins reported from the right side ---" << std::endl;
    struct Case { const char* fen; GameResult game, mcts; const char* what; };
    const Case cases[] = {
        // White has given all its checks; Black to move.
        {"4k5/10/10/10/10/10/10/10/10/R3K5 b - - 0+8 0 1", GameResult::WHITE_WON,
         GameResult::WHITE_WON, "White completed its checks (Black to move)"},
        // Black has given all its checks; White to move.
        {"r3k5/10/10/10/10/10/10/10/10/4K5 w - - 8+0 0 1", GameResult::BLACK_WON,
         GameResult::WHITE_WON, "Black completed its checks (White to move)"},
    };
    for (const auto& c : cases) {
        const GameResult g = GameResultOf(c.fen), m = MctsResultOf(c.fen);
        std::cout << "  " << c.what << ": game=" << Name(g) << " mcts=" << Name(m) << std::endl;
        EXPECT(g == c.game, c.what << ": ComputeGameResult=" << Name(g));
        EXPECT(m == c.mcts, c.what << ": ComputeMctsResult=" << Name(m)
               << " (must be WHITE_WON = 'the side that just moved won')");
    }
}

// ---------------------------------------------------------------------------
// 6. Repetitions are counted at every rule-50 count.
// ---------------------------------------------------------------------------
// Knights out and back (4 plies), twice, from positions whose rule-50 counter
// starts at r. Plies 4-7 repeat plies 0-3 (repetitions = 1, NN repetition plane
// set); ply 8 is the start position's third occurrence (threefold draw). Fairy-Stockfish's own n-fold check (is_optional_game_end,
// which compares raw Zobrist keys along the StateInfo chain) is the reference.
// Until 2026-09-23 PositionHistory compared Fairy-Stockfish's key(), which XORs
// in a rule-50 bucket from rule50 = 14 on, so a repetition was only seen when
// every occurrence had rule50 < 14; test 3 above starts at rule50 = 0 and could
// not notice.
void TestRepetitionAnyRule50() {
    std::cout << "\n--- 6. Repetitions and threefold draws at every rule-50 count ---" << std::endl;
    const char* moves[4] = {"j1i3", "a10b8", "i3j1", "b8a10"};
    int cases = 0;
    for (int r50 : {0, 5, 9, 10, 13, 14, 15, 20, 37, 50, 90}) {
        const std::string fen =
            "n3k5/10/10/10/10/10/10/10/10/4K4N w - - 8+8 " + std::to_string(r50) + " 40";
        auto h = std::make_unique<lczero::PositionHistory>();
        h->Reset(lczero::Position::FromFen(fen));
        for (int ply = 1; ply <= 8; ++ply) {
            const lczero::Move m = fztest::ParseLegalMove(*h, moves[(ply - 1) % 4]);
            if (m.is_null()) {
                ++g_failures;
                std::cerr << "[FAIL] setup: " << moves[(ply - 1) % 4] << " not legal" << std::endl;
                break;
            }
            h->Append(m);
            const int reps = h->Last().GetRepetitions();
            // Plies 4-7 repeat plies 0-3 once; ply 8 is the start position's third time.
            const int want_reps = ply < 4 ? 0 : ply < 8 ? 1 : 2;
            const GameResult res = h->ComputeGameResult();
            const GameResult want = ply == 8 ? GameResult::DRAW : GameResult::UNDECIDED;
            Value v = VALUE_NONE;
            const bool fsf_draw = h->Last().GetBoard().GetRawPosition().is_optional_game_end(v, 0);
            lczero::InputPlanes planes;
            int t = 0;
            lczero::EncodePositionForNN(*h, lczero::kMoveHistory,
                                        lczero::FillEmptyHistory::FEN_ONLY, &planes, &t);
            const bool rep_plane = bool(planes[26].mask) && planes[26].value == 1.0f;
            EXPECT(reps == want_reps, "rule50 start " << r50 << ", ply " << ply << ": repetitions "
                   << reps << ", expected " << want_reps);
            EXPECT(res == want, "rule50 start " << r50 << ", ply " << ply << ": ComputeGameResult "
                   << Name(res) << ", expected " << Name(want));
            EXPECT(fsf_draw == (ply == 8), "setup: Fairy-Stockfish's n-fold check says "
                   << fsf_draw << " at rule50 start " << r50 << ", ply " << ply);
            EXPECT(rep_plane == (want_reps >= 1), "rule50 start " << r50 << ", ply " << ply
                   << ": NN repetition plane " << (rep_plane ? "set" : "clear"));
        }
        ++cases;
    }
    std::cout << "  " << cases << " rule-50 starts x 8 plies checked (repetitions, result, "
                 "Fairy-Stockfish n-fold, NN repetition plane)" << std::endl;
}

}  // namespace

void run_history_tests() {
    std::cout << "\n========================================" << std::endl;
    std::cout << "RUNNING HISTORY / HASH / GAME-END TESTS..." << std::endl;
    std::cout << "========================================" << std::endl;
    g_variant = setup_custom_variant();

    TestTrimmedHistory();
    TestZobristKeys();
    TestCacheKeyRepetitions();
    TestGameEndPrecedence();
    TestCheckCountResults();
    TestRepetitionAnyRule50();

    std::cout << "\n========================================" << std::endl;
    if (g_failures == 0) {
        std::cout << "[PASS] ALL HISTORY / HASH / GAME-END TESTS PASSED" << std::endl;
        std::cout << "========================================" << std::endl;
    } else {
        std::cerr << "[FAIL] " << g_failures << " history/hash/game-end check(s) failed" << std::endl;
        std::cout << "========================================" << std::endl;
        std::exit(1);
    }
}
