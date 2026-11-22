// STRICT search-logic tests: --test-search-logic [--weights <net.onnx>]
//
// --test-mcts is a smoke test (it prints best moves and asserts nothing). The
// tests here assert properties that the search and the self-play extraction
// MUST have, each chosen because breaking it corrupts training data silently:
//
//   1. Search-target perspective: root_q / best_q / played_q in a training
//      record are from the SIDE TO MOVE's perspective (what train.py assumes),
//      checked on forced wins for both colours, against the raw net value, and
//      against lc0's own canonical reporting (Search::GetBestEval).
//   2. Dirichlet noise reaches the root of EVERY self-play move, not only the
//      first move of the game.
//   3. Tree bookkeeping after multi-threaded searches with task workers,
//      collisions, out-of-order evals, prefetch and tree reuse: N = 1 + sum of
//      child N, no leaked virtual loss, Q/D equal to the exact average of what
//      the deterministic backend returned, priors normalized and sorted.
//   4. BackendComputation::AddInput may be called from several threads at once
//      (lc0's search does so whenever one gather yields >= 20 new leaves and
//      task workers are active), for every backend the engine ships.
//   5. No reachable position loses legal moves to the 384-per-node capacity.
//   6. The UCI engine's ReuseTree really keeps the searched subtree (needs
//      --weights: it drives the real engine through its C ABI).
//   7. Thousands of short searches in parallel games (a Search, i.e. a new set
//      of threads, per move) neither crash nor hang. This caught the per-thread
//      Node slab allocator corrupting memory at thread exit on MinGW.
//   8. A game file written by PlayOneGame replays exactly: planes, pi mask,
//      best/played indices, game end and z of every record.
//   9. Self-play soft stop (--stop-file): no new game once the file exists, the
//      games in flight finish into complete files.
//  10. Playout cap randomization and the move choice: the weights (N/N_max)^(1/T)
//      and their sampling, the coin, the visits and fast_search mark of both search
//      kinds, and that each kind searches with its own c_puct / noise options.
//
// Every sub-test runs even if an earlier one failed; the process exits 1 at the
// end if anything failed.

#include "tests/test_common.h"
#include "app/fairyzero_ffi.h"
#include "app/uci_nn_engine.h"
#include <filesystem>
#include <iomanip>

namespace {

using lczero::classic::Node;
using lczero::classic::NodeTree;
using lczero::GameResult;

int g_failures = 0;

#define EXPECT(cond, msg)                                         \
    do {                                                          \
        if (!(cond)) {                                            \
            ++g_failures;                                         \
            std::cerr << "[FAIL] " << msg << std::endl;           \
        }                                                         \
    } while (0)

// Most-visited root edge (ties -> the last one, like FillSearchTargets).
lczero::classic::EdgeAndNode MostVisited(const Node* root) {
    lczero::classic::EdgeAndNode best;
    uint32_t best_n = 0;
    for (const auto& e : root->Edges()) {
        if (e.GetN() >= best_n) { best_n = e.GetN(); best = e; }
    }
    return best;
}

bool UniqueMostVisited(const Node* root) {
    uint32_t top = 0, second = 0;
    for (const auto& e : root->Edges()) {
        const uint32_t n = e.GetN();
        if (n > top) { second = top; top = n; }
        else if (n > second) second = n;
    }
    return top > second;
}

lczero::TrainingDataV1 FreshRecord() {
    lczero::TrainingDataV1 rec;
    std::memset(&rec, 0, sizeof(rec));
    return rec;
}

// ---------------------------------------------------------------------------
// 1. Perspective of the search targets written to the training record.
// ---------------------------------------------------------------------------
void TestSearchTargetPerspective() {
    std::cout << "\n--- 1. Search-target perspective (root_q / best_q / played_q) ---" << std::endl;

    // (a) Forced wins. The side to move needs ONE more check and has exactly
    // one checking move, so that move ends the game in its favour. Whatever the
    // net says about the other moves, the value of the best move for the side
    // to move is +1, and the root value is positive once the search found it.
    struct WinCase { const char* fen; const char* win; const char* who; };
    const WinCase cases[] = {
        {"4k5/10/10/10/10/10/10/10/10/R3K5 w - - 1+8 0 1", "a1a10", "White"},
        {"r3k5/10/10/10/10/10/10/10/10/4K5 b - - 8+1 0 1", "a10a1", "Black"},
    };
    for (const auto& c : cases) {
        fztest::DetBackend backend(/*runs_on_cpu=*/true, /*batch=*/8, /*immediate_mod=*/0);
        fztest::TestSearchOptions opts;
        // Optimistic first-play urgency at the root: every root move is tried
        // once before any is tried again, so the search finds the win whatever
        // prior the deterministic net gives it. With lc0's default (untried
        // moves valued well below the parent) a move given ~0.1% is never tried
        // in 400 playouts -- which fake net that is must not decide a test of
        // the record's signs.
        opts.Set("fpu-strategy-at-root", "absolute");
        opts.Set("fpu-value-at-root", "1");
        auto tree = std::make_unique<NodeTree>();
        tree->ResetToPosition(c.fen, {});
        const lczero::Move win = fztest::ParseLegalMove(tree->GetPositionHistory(), c.win);
        if (win.is_null()) {
            ++g_failures;
            std::cerr << "[FAIL] setup: " << c.win << " is not legal in " << c.fen << std::endl;
            continue;
        }
        fztest::RunTestSearch(tree.get(), &backend, opts.Dict(), 400, 1);
        const Node* root = tree->GetCurrentHead();
        auto rec = FreshRecord();
        const lczero::Move best =
            lczero::FillSearchTargets(root, tree->GetPositionHistory(), &backend, rec);
        std::cout << "  " << c.who << " to move, winning move " << c.win
                  << ": search best=" << fztest::MoveUci(tree->GetPositionHistory(), best)
                  << " best_q=" << rec.best_q << " root_q=" << rec.root_q << std::endl;
        EXPECT(best == win, c.who << ": the search did not pick the forced win " << c.win);
        EXPECT(rec.best_q > 0.99f,
               c.who << ": best_q=" << rec.best_q << " for a move that WINS for the side to "
               "move (must be +1). The record stores the opponent's view: train.py mixes "
               "best_q into the value target with the wrong sign.");
        EXPECT(rec.root_q > 0.0f,
               c.who << ": root_q=" << rec.root_q << " in a position the side to move wins "
               "(must be > 0).");

        // played_q goes through RecordPlayedMove when the played move is not the
        // max-visit one. Pretend the winning move was sampled instead of `best`.
        lczero::classic::EdgeAndNode win_edge;
        for (const auto& e : root->Edges()) if (e.GetMove() == win) win_edge = e;
        auto rec2 = FreshRecord();
        lczero::RecordPlayedMove(win_edge, lczero::Move(), rec2);
        EXPECT(rec2.played_q > 0.99f,
               c.who << ": played_q=" << rec2.played_q << " for the winning move (must be +1).");
    }

    // (b) One playout: the only information in the tree is the net's own value
    // of the root, so root_q must equal the raw net value orig_q EXACTLY (both
    // side-to-move). Uses the real NN cache so orig_q is the cached raw eval.
    {
        fztest::TestSearchOptions opts;
        auto backend = lczero::CreateMemCache(
            std::make_unique<fztest::DetBackend>(true, 8, 0), opts.Dict());
        for (const char* fen : {kUciStartFen,
                                "vrhbqkberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/"
                                "MSYSNNSYSM/VRHBQKBERV b BIbi - 7+7 0 1"}) {
            auto tree = std::make_unique<NodeTree>();
            tree->ResetToPosition(fen, {});
            fztest::RunTestSearch(tree.get(), backend.get(), opts.Dict(), 1, 1);
            auto rec = FreshRecord();
            lczero::FillSearchTargets(tree->GetCurrentHead(), tree->GetPositionHistory(),
                                      backend.get(), rec);
            const float net_q =
                fztest::DetValue(fztest::DetKey(tree->GetPositionHistory().Last())).q;
            std::cout << "  1 playout, " << (tree->IsBlackToMove() ? "Black" : "White")
                      << " to move: net q=" << net_q << " orig_q=" << rec.orig_q
                      << " root_q=" << rec.root_q << std::endl;
            EXPECT(std::abs(rec.orig_q - net_q) < 1e-6f,
                   "orig_q=" << rec.orig_q << " is not the raw net value " << net_q);
            EXPECT(std::abs(rec.root_q - net_q) < 1e-5f,
                   "root_q=" << rec.root_q << " after ONE playout must equal the net's own "
                   "side-to-move value " << net_q << " (sign flipped?)");
        }
    }

    // (c) Normal position, real search: best_q must equal lc0's canonical value
    // of the best move, Search::GetBestEval().wl (what the UCI score is built
    // from). Only compared when the most-visited move is unique.
    {
        fztest::DetBackend backend(true, 8, 0);
        fztest::TestSearchOptions opts;
        int compared = 0;
        auto tree = std::make_unique<NodeTree>();
        tree->ResetToPosition(kUciStartFen, {});
        for (int ply = 0; ply < 6; ++ply) {
            auto search = std::make_unique<lczero::classic::Search>(
                *tree, &backend, std::make_unique<SilentUciResponder>(), lczero::MoveList{},
                std::chrono::steady_clock::now(), std::make_unique<PlayoutCountStopper>(300),
                false, false, opts.Dict(), nullptr);
            search->RunBlocking(1);
            const Node* root = tree->GetCurrentHead();
            const lczero::classic::Eval canonical = search->GetBestEval();
            auto rec = FreshRecord();
            const lczero::Move best =
                lczero::FillSearchTargets(root, tree->GetPositionHistory(), &backend, rec);
            if (UniqueMostVisited(root)) {
                ++compared;
                EXPECT(std::abs(rec.best_q - canonical.wl) < 1e-6f,
                       "ply " << ply << ": best_q=" << rec.best_q
                              << " but lc0's GetBestEval().wl=" << canonical.wl
                              << " (side-to-move value of the same move)");
            }
            search.reset();
            tree->MakeMove(best);
        }
        std::cout << "  best_q vs Search::GetBestEval() compared on " << compared
                  << " positions" << std::endl;
        EXPECT(compared >= 3, "too few positions with a unique best move to compare");
    }
}

// ---------------------------------------------------------------------------
// 2. Dirichlet noise at the root of every self-play move.
// ---------------------------------------------------------------------------
void TestNoiseEveryMove() {
    std::cout << "\n--- 2. Dirichlet noise at the root of EVERY self-play move ---" << std::endl;
    // MockBackend returns a UNIFORM prior, so any spread in the root priors can
    // only come from the noise. The search is the production per-move search.
    MockBackend backend;
    fztest::TestSearchOptions opts;
    opts.SetNoise(0.25f, 0.3f);
    auto tree = std::make_unique<NodeTree>();
    tree->ResetToPosition(kUciStartFen, {});
    int noisy_moves = 0;
    const int kPlies = 8;
    for (int ply = 0; ply < kPlies; ++ply) {
        lczero::SearchSelfPlayMove(tree.get(), &backend, opts.Dict(), 48, 1);
        const Node* root = tree->GetCurrentHead();
        float pmin = 1.0f, pmax = 0.0f;
        double psum = 0.0;
        for (const auto& e : root->Edges()) {
            pmin = std::min(pmin, e.GetP());
            pmax = std::max(pmax, e.GetP());
            psum += e.GetP();
        }
        const bool noisy = (pmax - pmin) > 0.005f;
        if (noisy) ++noisy_moves;
        std::cout << "  ply " << ply << ": root priors " << (noisy ? "noisy  " : "UNIFORM")
                  << " (max-min=" << (pmax - pmin) << ", sum=" << psum
                  << ", root N=" << root->GetN() << ")" << std::endl;
        EXPECT(noisy, "ply " << ply << ": the root of this move's search got NO Dirichlet "
                      "noise (priors still uniform) although noise-eps=0.25");
        EXPECT(std::abs(psum - 1.0) < 0.02, "ply " << ply << ": root priors sum to " << psum);
        tree->MakeMove(MostVisited(root).GetMove());
    }
    std::cout << "  noisy roots: " << noisy_moves << "/" << kPlies << std::endl;
}

// ---------------------------------------------------------------------------
// 3. Tree bookkeeping invariants.
// ---------------------------------------------------------------------------
struct InvariantReport {
    long nodes = 0, terminals = 0, errors = 0;
    double max_wl_err = 0.0, max_d_err = 0.0;
};

void CheckSubtree(const Node* node, lczero::PositionHistory* hist, InvariantReport* r,
                  int depth) {
    ++r->nodes;
    auto broken = [&](const std::string& what) {
        if (r->errors++ < 8) std::cerr << "    invariant broken at depth " << depth << ": " << what << std::endl;
    };
    if (node->GetNInFlight() != 0) {
        broken("n_in_flight=" + std::to_string(node->GetNInFlight()) +
               " after the search ended (leaked virtual loss)");
    }
    if (node->IsTerminal()) {
        ++r->terminals;
        return;
    }
    // The node's own evaluation, exactly as the deterministic backend gave it.
    const fztest::DetEval own = fztest::DetValue(fztest::DetKey(hist->Last()));
    uint64_t child_n = 0;
    double wl_sum = -static_cast<double>(own.q);  // stored from the mover's view
    double d_sum = own.d;
    double psum = 0.0;
    float prev_p = 2.0f;
    bool sorted = true, finite = true;
    int edges = 0;
    for (const auto& e : node->Edges()) {
        ++edges;
        const float p = e.GetP();
        if (!std::isfinite(p) || p < 0.0f || p > 1.0f) finite = false;
        psum += p;
        // Terminal losses get P=0 after sorting (Node::MakeTerminal): skip them.
        if (!e.IsTerminal()) {
            if (p > prev_p + 1e-6f) sorted = false;
            prev_p = p;
        }
        const uint32_t n = e.GetN();
        if (n == 0) continue;
        child_n += n;
        wl_sum += -static_cast<double>(e.node()->GetWL()) * n;
        d_sum += static_cast<double>(e.node()->GetD()) * n;
    }
    const uint32_t n = node->GetN();
    if (edges == 0) broken("expanded non-terminal node without edges");
    if (n != 1 + child_n) {
        broken("N=" + std::to_string(n) + " but 1 + sum(child N)=" + std::to_string(1 + child_n));
    }
    const double wl_err = std::abs(node->GetWL() - wl_sum / n);
    const double d_err = std::abs(node->GetD() - d_sum / n);
    r->max_wl_err = std::max(r->max_wl_err, wl_err);
    r->max_d_err = std::max(r->max_d_err, d_err);
    if (wl_err > 1e-3) {
        broken("WL=" + std::to_string(node->GetWL()) + " but the exact average of the backed-up "
               "values is " + std::to_string(wl_sum / n));
    }
    if (d_err > 1e-3) {
        broken("D=" + std::to_string(node->GetD()) + " but the exact average is " +
               std::to_string(d_sum / n));
    }
    if (!finite) broken("a prior is NaN/negative/>1");
    if (std::abs(psum - 1.0) > 0.02) broken("priors sum to " + std::to_string(psum));
    if (!sorted) broken("edges not sorted by prior (PickNodesToExtend relies on it)");
    for (const auto& e : node->Edges()) {
        if (e.GetN() == 0) continue;
        hist->Append(e.GetMove());
        CheckSubtree(e.node(), hist, r, depth + 1);
        hist->Pop();
    }
}

bool CheckTree(const char* label, NodeTree* tree) {
    auto hist = std::make_unique<lczero::PositionHistory>(tree->GetPositionHistory());
    InvariantReport r;
    CheckSubtree(tree->GetCurrentHead(), hist.get(), &r, 0);
    std::cout << "  " << label << ": " << r.nodes << " nodes (" << r.terminals
              << " terminal), root N=" << tree->GetCurrentHead()->GetN()
              << ", max |WL err|=" << r.max_wl_err << ", max |D err|=" << r.max_d_err
              << ", broken=" << r.errors << std::endl;
    EXPECT(r.errors == 0, label << ": " << r.errors << " tree invariant violation(s)");
    EXPECT(r.nodes > 500, label << ": tree too small to be a meaningful check");
    return r.errors == 0;
}

void TestTreeInvariants() {
    std::cout << "\n--- 3. Tree bookkeeping invariants (threads, task workers, OOO, reuse) ---" << std::endl;
    struct Config {
        const char* label;
        int threads, minibatch, task_workers, prefetch, immediate_mod, playouts;
    };
    const Config configs[] = {
        // One search thread, big minibatch, 2 task workers: gathers of >= 20
        // leaves are split across threads (the path ProcessPickedTask runs in).
        {"1 thread, minibatch 32, 2 task workers, OOO", 1, 32, 2, 0, 4, 3000},
        {"2 threads, minibatch 32, 2 task workers, prefetch 32", 2, 32, 2, 32, 4, 3000},
        {"4 threads, minibatch 16, 1 task worker, collisions", 4, 16, 1, 0, 0, 3000},
    };
    for (const auto& c : configs) {
        fztest::DetBackend backend(/*runs_on_cpu=*/false, c.minibatch, c.immediate_mod);
        fztest::TestSearchOptions opts;
        opts.Set("minibatch-size", std::to_string(c.minibatch));
        opts.Set("task-workers", std::to_string(c.task_workers));
        opts.Set("max-prefetch", std::to_string(c.prefetch));
        auto tree = std::make_unique<NodeTree>();
        tree->ResetToPosition(kUciStartFen, {});
        fztest::RunTestSearch(tree.get(), &backend, opts.Dict(), c.playouts, c.threads);
        CheckTree(c.label, tree.get());
        // Tree reuse (UCI engine / arena style): keep the played move's subtree
        // and search on top of it.
        const lczero::Move best = MostVisited(tree->GetCurrentHead()).GetMove();
        tree->MakeMove(best);
        fztest::RunTestSearch(tree.get(), &backend, opts.Dict(), c.playouts / 2, c.threads);
        CheckTree("  ... after MakeMove + reused-tree search", tree.get());
    }
}

// ---------------------------------------------------------------------------
// 4. Concurrent AddInput (the BackendComputation thread-safety contract).
// ---------------------------------------------------------------------------
struct TestPosition {
    std::unique_ptr<lczero::PositionHistory> history;
    lczero::MoveList legal;
};

std::vector<TestPosition> DistinctPositions(size_t count) {
    std::vector<TestPosition> out;
    std::set<uint64_t> keys;
    std::mt19937 rng(12345);
    while (out.size() < count) {
        TestPosition tp;
        tp.history = std::make_unique<lczero::PositionHistory>();
        tp.history->Reset(lczero::Position::FromFen(kUciStartFen));
        const int plies = 2 + static_cast<int>(rng() % 12);
        bool ok = true;
        for (int i = 0; i < plies && ok; ++i) {
            const auto legal = tp.history->Last().GetBoard().GenerateLegalMoves();
            if (legal.empty()) { ok = false; break; }
            tp.history->Append(legal[rng() % legal.size()]);
        }
        tp.legal = tp.history->Last().GetBoard().GenerateLegalMoves();
        if (!ok || tp.legal.empty()) continue;
        if (!keys.insert(tp.history->Last().Hash()).second) continue;
        out.push_back(std::move(tp));
    }
    return out;
}

struct ExpectedEval {
    float q, d;
    std::vector<float> p;
};

// Adds `threads * per_thread` distinct positions to ONE computation from
// `threads` threads released at the same instant, evaluates, and compares every
// result with `expected`. Returns the number of wrong/missing results.
long ConcurrentRound(lczero::Backend* backend, const std::vector<TestPosition>& pos,
                     const std::vector<ExpectedEval>& expected, int threads,
                     int per_thread, int round, float tol, size_t* used_batch) {
    const int total = threads * per_thread;
    auto comp = backend->CreateComputation();
    std::vector<lczero::EvalResult> res(total);
    std::vector<int> which(total);
    for (int i = 0; i < total; ++i) {
        which[i] = (round * 17 + i) % static_cast<int>(pos.size());
        res[i].q = res[i].d = res[i].m = -7.0f;  // sentinel: "never written"
        res[i].p.resize(pos[which[i]].legal.size());
        for (auto& x : res[i].p) x = -7.0f;
    }
    // Distinct positions within a round (so a cache cannot answer them).
    std::set<int> uniq(which.begin(), which.end());
    if (static_cast<int>(uniq.size()) != total) {
        std::cerr << "[FAIL] test setup: positions repeat within a round" << std::endl;
        std::exit(1);
    }
    std::atomic<int> ready{0};
    std::atomic<bool> go{false};
    std::vector<std::thread> pool;
    for (int t = 0; t < threads; ++t) {
        pool.emplace_back([&, t] {
            ready.fetch_add(1);
            while (!go.load(std::memory_order_acquire)) {}
            for (int k = 0; k < per_thread; ++k) {
                const int i = t * per_thread + k;
                const TestPosition& tp = pos[which[i]];
                comp->AddInput(lczero::EvalPosition{tp.history.get(),
                                                    std::span<const lczero::Move>(
                                                        tp.legal.data(), tp.legal.size())},
                               res[i].AsPtr());
            }
        });
    }
    while (ready.load() < threads) {}
    go.store(true, std::memory_order_release);
    for (auto& th : pool) th.join();
    *used_batch = comp->UsedBatchSize();
    comp->ComputeBlocking();
    long wrong = 0;
    for (int i = 0; i < total; ++i) {
        const ExpectedEval& e = expected[which[i]];
        bool ok = std::abs(res[i].q - e.q) <= tol && std::abs(res[i].d - e.d) <= tol;
        for (size_t k = 0; ok && k < e.p.size(); ++k) ok = std::abs(res[i].p[k] - e.p[k]) <= tol;
        if (!ok) ++wrong;
    }
    return wrong;
}

void RunConcurrentCase(const char* label, lczero::Backend* backend,
                       lczero::CachingBackend* cache_to_clear,
                       const std::vector<TestPosition>& pos,
                       const std::vector<ExpectedEval>& expected, int rounds, float tol) {
    const int kThreads = 4, kPerThread = 8;
    long wrong = 0, short_batches = 0;
    for (int round = 0; round < rounds; ++round) {
        if (cache_to_clear) cache_to_clear->ClearCache();
        size_t used = 0;
        wrong += ConcurrentRound(backend, pos, expected, kThreads, kPerThread, round, tol, &used);
        if (used != static_cast<size_t>(kThreads * kPerThread)) ++short_batches;
    }
    std::cout << "  " << label << ": " << rounds << " rounds x " << kThreads * kPerThread
              << " concurrent AddInput -> wrong/missing results=" << wrong
              << ", rounds with a lost slot (UsedBatchSize != 32)=" << short_batches << std::endl;
    EXPECT(wrong == 0 && short_batches == 0,
           label << ": concurrent AddInput lost or mixed up results (" << wrong
                 << " bad results, " << short_batches << " short batches). The search calls "
                 "AddInput from task threads whenever a gather has >= 20 new leaves.");
}

void TestConcurrentAddInput(const std::string& weights_path) {
    std::cout << "\n--- 4. Concurrent AddInput on every backend computation ---" << std::endl;
    const auto pos = DistinctPositions(64);
    std::vector<ExpectedEval> det(pos.size());
    for (size_t i = 0; i < pos.size(); ++i) {
        const uint64_t key = fztest::DetKey(pos[i].history->Last());
        const auto e = fztest::DetValue(key);
        det[i].q = e.q;
        det[i].d = e.d;
        det[i].p.resize(pos[i].legal.size());
        fztest::DetPolicy(key, det[i].p.size(), det[i].p.data());
    }
    fztest::TestSearchOptions opts;
    {
        fztest::DetBackend reference(false, 32, 0);
        RunConcurrentCase("reference DetBackend", &reference, nullptr, pos, det, 300, 0.0f);
    }
    {
        auto cache = lczero::CreateMemCache(std::make_unique<fztest::DetBackend>(false, 32, 0),
                                            opts.Dict());
        RunConcurrentCase("NN cache (ZeroHeapCache) over DetBackend", cache.get(), cache.get(),
                          pos, det, 300, 0.0f);
    }
    {
        lczero::BatchingBackend batching(std::make_unique<fztest::DetBackend>(false, 32, 0),
                                         /*expected_producers=*/1, /*timeout_us=*/2000);
        RunConcurrentCase("--batch-aggregate (BatchingBackend) over DetBackend", &batching,
                          nullptr, pos, det, 100, 0.0f);
    }
    std::ifstream probe(weights_path);
    if (!probe.good()) {
        std::cout << "  [SKIP] ONNX backend cases: weights not found (" << weights_path
                  << "); pass --weights <net.onnx> to include them." << std::endl;
        return;
    }
    probe.close();
    fztest::TestSearchOptions onnx_opts;
    auto* d = onnx_opts.parser.GetMutableDefaultsOptions();
    d->Set<std::string>(lczero::SharedBackendParams::kWeightsId, weights_path);
    d->Set<std::string>(lczero::SharedBackendParams::kBackendOptionsId, "threads=2");
    auto make_onnx = [&] {
        auto b = std::make_unique<lczero::OnnxBackend>();
        b->UpdateConfiguration(onnx_opts.Dict());
        return b;
    };
    // Reference values: every position evaluated ALONE, single-threaded.
    std::vector<ExpectedEval> ref(pos.size());
    {
        auto onnx = make_onnx();
        for (size_t i = 0; i < pos.size(); ++i) {
            lczero::EvalResult r;
            r.p.resize(pos[i].legal.size());
            auto comp = onnx->CreateComputation();
            comp->AddInput(lczero::EvalPosition{pos[i].history.get(),
                                                std::span<const lczero::Move>(
                                                    pos[i].legal.data(), pos[i].legal.size())},
                           r.AsPtr());
            comp->ComputeBlocking();
            ref[i].q = r.q;
            ref[i].d = r.d;
            ref[i].p.assign(r.p.begin(), r.p.end());
        }
    }
    {
        auto onnx = make_onnx();
        RunConcurrentCase("OnnxBackend (CPU, real net)", onnx.get(), nullptr, pos, ref, 12, 2e-3f);
    }
    {
        auto cache = lczero::CreateMemCache(make_onnx(), onnx_opts.Dict());
        RunConcurrentCase("NN cache over OnnxBackend (the self-play stack)", cache.get(),
                          cache.get(), pos, ref, 12, 2e-3f);
    }
}

// ---------------------------------------------------------------------------
// 5. Legal-move capacity (lczero::MoveList holds at most 384 moves).
// ---------------------------------------------------------------------------
void TestLegalMoveCapacity() {
    std::cout << "\n--- 5. Legal moves per position vs the 384 capacity ---" << std::endl;
    const Variant* v = variants.find("custom_10x10_variant")->second;
    std::mt19937 rng(777);
    long positions = 0, truncated = 0;
    size_t max_moves = 0;
    double sum_moves = 0.0;
    std::string max_fen;
    for (int game = 0; game < 300; ++game) {
        Position pos;
        StateListPtr states(new std::deque<StateInfo>(1));
        pos.set(v, kUciStartFen, false, &states->back(), Threads.main());
        for (int ply = 0; ply < 300; ++ply) {
            MoveList<LEGAL> raw(pos);
            if (raw.size() == 0) break;
            const lczero::ChessBoard board(pos.fen());
            const size_t adapter = board.GenerateLegalMoves().size();
            ++positions;
            sum_moves += raw.size();
            if (adapter != raw.size()) ++truncated;
            if (raw.size() > max_moves) { max_moves = raw.size(); max_fen = pos.fen(); }
            const Move m = raw.begin()[rng() % raw.size()];
            states->emplace_back();
            pos.do_move(m, states->back());
            if (pos.checks_remaining(WHITE) <= 0 || pos.checks_remaining(BLACK) <= 0) break;
        }
    }
    std::cout << "  random games: " << positions << " positions, mean legal moves="
              << (positions ? sum_moves / positions : 0.0) << ", max=" << max_moves
              << " at " << max_fen << std::endl;
    EXPECT(truncated == 0, truncated << " positions lost legal moves to the 384 cap");
    EXPECT(max_moves <= 384, "a random-game position has " << max_moves << " legal moves (> 384)");

    // A deliberately extreme (and unrealistic) position: White's long-range
    // pieces on an open board, five pawn-type pieces on the 7th rank that can
    // each promote to 6 types by pushing or by capturing a rook on the 8th, and
    // five more pawns behind them. Reported, not asserted: it shows the headroom.
    const char* extreme =
        "k9/10/1r1r1r1r1r/P1S1P1S1P1/1P1P1P1P1P/1Q2E2H2/10/2R3R3/1B2V2V1B/M3K4M w - - 7+7 0 1";
    Position pos;
    StateListPtr states(new std::deque<StateInfo>(1));
    pos.set(v, extreme, false, &states->back(), Threads.main());
    MoveList<LEGAL> raw(pos);
    const size_t adapter = lczero::ChessBoard(pos.fen()).GenerateLegalMoves().size();
    std::cout << "  extreme hand-built position: " << raw.size() << " legal moves (adapter sees "
              << adapter << ")" << (raw.size() > 384 ? "  <-- would be TRUNCATED" : "") << std::endl;
}

// ---------------------------------------------------------------------------
// 6. UCI engine: ReuseTree really keeps the searched subtree.
// ---------------------------------------------------------------------------
// Drives the real UCI engine through its C ABI (the same path the GUI uses):
// search, then send the position after the engine's own best move, then search
// with a budget of 1 new playout. The reported `nodes` is the root's visit
// count, so with a reused tree it carries the visits that move's subtree already
// had (a large share of the first search); with a rebuilt tree it is only the
// handful of playouts of the first gathers. Both settings are run and compared.
// Runs the ReuseTree comparison on one engine handle; `label` names the backend.
// `minutes` bounds each search (a CPU network can be slow; DetBackend is instant).
void RunUciReuseComparison(void* h, const char* label, int minutes) {
    // Sends a `go` and collects output until its bestmove.
    auto go = [&](const char* cmd, std::vector<std::string>* lines) {
        fz_send(h, cmd);
        char buf[4096];
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::minutes(minutes);
        while (std::chrono::steady_clock::now() < deadline) {
            if (fz_poll(h, buf, sizeof(buf)) > 0) {
                lines->emplace_back(buf);
                if (lines->back().rfind("bestmove", 0) == 0) return true;
            } else {
                std::this_thread::sleep_for(std::chrono::milliseconds(5));
            }
        }
        return false;
    };
    auto last_nodes = [](const std::vector<std::string>& lines) {
        long long nodes = -1;
        for (const auto& l : lines) {
            std::istringstream in(l);
            for (std::string t; in >> t;) {
                if (t == "nodes") in >> nodes;
            }
        }
        return nodes;
    };
    fz_send(h, "uci");
    long long root_visits[2] = {-1, -1};  // [ReuseTree false, ReuseTree true]
    for (int reuse = 0; reuse < 2; ++reuse) {
        fz_send(h, "ucinewgame");
        fz_send(h, reuse ? "setoption name ReuseTree value true"
                         : "setoption name ReuseTree value false");
        fz_send(h, "position startpos");
        std::vector<std::string> first, second;
        const auto t0 = std::chrono::steady_clock::now();
        const bool ok1 = go("go nodes 2000", &first);
        std::string bestmove;
        if (ok1) {
            std::istringstream in(first.back());
            std::string t;
            in >> t >> bestmove;
        }
        if (!ok1 || bestmove.empty()) {
            ++g_failures;
            std::cerr << "[FAIL] " << label << ": the first search gave no bestmove within "
                      << minutes << " min" << std::endl;
            return;
        }
        const double secs = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
        const std::string pos = "position startpos moves " + bestmove;
        fz_send(h, pos.c_str());
        EXPECT(go("go nodes 1", &second), label << ": second search gave no bestmove");
        root_visits[reuse] = last_nodes(second);
        std::cout << "  " << label << ", ReuseTree " << (reuse ? "true " : "false")
                  << ": 2000 playouts in " << std::fixed << std::setprecision(1) << secs
                  << " s; after '" << pos << "' + 'go nodes 1' the root has "
                  << root_visits[reuse] << " visits" << std::endl;
    }
    // The best move of a 2000-playout search has at least the average share of
    // the visits (~2000 / 70 legal moves = 28), while the rebuilt tree only gets
    // what one gather adds (up to ~40 with NN-cache hits evaluated out of order).
    EXPECT(root_visits[1] >= root_visits[0] + 20,
           label << ": ReuseTree=true kept no more visits than a rebuilt tree (" << root_visits[1]
           << " vs " << root_visits[0] << "): the searched subtree was thrown away");
}

void TestUciTreeReuse(const std::string& weights_path) {
    std::cout << "\n--- 6. UCI engine: ReuseTree keeps the searched subtree ---" << std::endl;
    // Always: the UCI engine (the path the GUI drives) with the deterministic
    // backend -- fast, and independent of the speed of the machine.
    if (void* h = fz_create_with_backend(std::make_unique<fztest::DetBackend>(true, 8, 0))) {
        RunUciReuseComparison(h, "DetBackend", 2);
        fz_destroy(h);
    } else {
        ++g_failures;
        std::cerr << "[FAIL] fz_create_with_backend failed" << std::endl;
    }
    // With --weights: the same through fz_create and the real ONNX backend. On a
    // slow CPU 2000 playouts take minutes (7 playouts/s measured on a throttled
    // laptop), so the bound is generous.
    std::ifstream probe(weights_path);
    if (!probe.good()) {
        std::cout << "  [SKIP] real network: needs --weights <net.onnx>" << std::endl;
        return;
    }
    probe.close();
    void* h = fz_create(weights_path.c_str(), "cpu");
    if (!h) {
        ++g_failures;
        std::cerr << "[FAIL] fz_create failed" << std::endl;
        return;
    }
    RunUciReuseComparison(h, "ONNX network", 20);
    fz_destroy(h);
}

// ---------------------------------------------------------------------------
// 7. Search lifecycle stress: many short searches, several games in parallel.
// ---------------------------------------------------------------------------
// Self-play builds a new Search (a new nodes_mutex_, a watchdog thread and
// worker threads that all lock it at once) for every single move, in several
// games at the same time. Thousands of short searches exercise exactly that
// start-up/tear-down window, with and without tree reuse. A failure here is an
// abort (assertion) or a hang, not a message.
//
// History: node.cc used to carry a per-thread slab allocator for Node whose
// cache was a thread_local with a destructor. On MinGW that thread_local lives
// in emulated TLS, which winpthreads frees BEFORE the destructor runs at thread
// exit; the destructor then pushed garbage into the shared free list. This test
// hung or crashed within a minute with it, and passes in seconds without it.
void TestSearchLifecycleStress() {
    std::cout << "\n--- 7. Search lifecycle stress (short searches, parallel games) ---" << std::endl;
    const int kGames = 3, kMovesPerGame = 250;
    for (bool reuse : {false, true}) {
        std::atomic<long> searches{0};
        auto play = [&](int seed) {
            fztest::DetBackend backend(/*runs_on_cpu=*/false, 16, 4);
            fztest::TestSearchOptions opts;
            opts.Set("task-workers", "1");
            auto tree = std::make_unique<NodeTree>();
            tree->ResetToPosition(kUciStartFen, {});
            std::mt19937 rng(seed);
            for (int ply = 0; ply < kMovesPerGame; ++ply) {
                if (!reuse) tree->TrimTreeAtHead();
                fztest::RunTestSearch(tree.get(), &backend, opts.Dict(), 24, 2);
                searches.fetch_add(1);
                const Node* root = tree->GetCurrentHead();
                if (root->GetNumEdges() == 0) break;
                // Mostly the best move, sometimes a random visited one.
                lczero::Move m = MostVisited(root).GetMove();
                if (rng() % 4 == 0) {
                    std::vector<lczero::Move> visited;
                    for (const auto& e : root->Edges()) if (e.GetN() > 0) visited.push_back(e.GetMove());
                    if (!visited.empty()) m = visited[rng() % visited.size()];
                }
                tree->MakeMove(m);
                if (tree->GetPositionHistory().ComputeGameResult() != lczero::GameResult::UNDECIDED) {
                    tree->ResetToPosition(kUciStartFen, {});
                }
            }
        };
        const auto t0 = std::chrono::steady_clock::now();
        std::vector<std::thread> games;
        for (int g = 0; g < kGames; ++g) games.emplace_back(play, 100 + g);
        for (auto& t : games) t.join();
        const double secs = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
        std::cout << "  " << (reuse ? "tree reuse " : "fresh tree ") << ": " << searches.load()
                  << " searches (" << kGames << " games in parallel, 2 threads + watchdog each) in "
                  << secs << " s, no crash" << std::endl;
    }
}

// ---------------------------------------------------------------------------
// 8. A self-play game file replays exactly.
// ---------------------------------------------------------------------------
// PlayOneGame (the production path) writes one record per position. Replaying
// the recorded moves from the start position must reproduce every record: its
// 216 history planes and scalar fields are those of the replayed position; pi
// is -1 exactly on the illegal indices and sums to 1 over the legal ones;
// best_idx is a most-visited move; the move at played_idx is legal and leads
// to the next record; no record lies after the end of the game; the game ends
// where the rules say (or at max_moves, adjudicated a draw); z has the right
// sign for the side to move of every record.
void TestSelfPlayRecordsReplay() {
    std::cout << "\n--- 8. A self-play game file replays exactly ---" << std::endl;
    fztest::DetBackend backend(/*runs_on_cpu=*/true, /*batch=*/8, /*immediate_mod=*/0);
    fztest::TestSearchOptions opts;
    opts.SetNoise(0.25f, 0.3f);
    const std::string file =
        std::string("test_selfplay_replay") + lczero::TrainingDataWriter::Extension();
    struct Case { const char* fen; int max_moves; };
    const Case cases[] = {
        {lczero::ChessBoard::kStartposFen, 60},                       // cut at max_moves
        {"4k5/10/10/10/10/10/10/10/10/R3K4R w - - 7+7 0 1", 300},    // ends by the rules
        {"n3k5/10/10/10/10/10/10/10/10/4K4N b - - 7+7 20 1", 300},   // quiet: repetition / rule 50
    };
    lczero::SelfPlaySearchPlan plan;   // PCR off: every move is a full search of 48 playouts
    plan.full_visits = 48;
    plan.temperature = 0.5f;
    for (const auto& c : cases) {
        const lczero::GameResult res = lczero::PlayOneGame(
            c.fen, &backend, opts.Dict(), plan, c.max_moves,
            file, /*search_threads=*/1, /*verbose=*/false);
        std::vector<lczero::TrainingDataV1> recs;
        if (!lczero::ReadTrainingData(file, recs) || recs.empty()) {
            ++g_failures;
            std::cerr << "[FAIL] " << c.fen << ": no readable game file" << std::endl;
            continue;
        }
        auto h = std::make_unique<lczero::PositionHistory>();
        h->Reset(lczero::Position::FromFen(c.fen));
        int bad = 0;
        auto check = [&](bool ok, size_t i, const std::string& what) {
            if (!ok && bad++ < 5) {
                ++g_failures;
                std::cerr << "[FAIL] " << c.fen << ", record " << i << ": " << what << std::endl;
            }
        };
        bool replayed_all = true;
        for (size_t i = 0; i < recs.size(); ++i) {
            const auto& r = recs[i];
            check(h->ComputeGameResult() == GameResult::UNDECIDED, i, "recorded after the end of the game");
            lczero::TrainingDataV1 want = FreshRecord();
            lczero::EncodePlanesIntoRecord(*h, want);
            check(std::memcmp(r.piece_planes, want.piece_planes, sizeof(want.piece_planes)) == 0 &&
                  std::memcmp(r.ep_mask, want.ep_mask, sizeof(want.ep_mask)) == 0 &&
                  r.rule50_count == want.rule50_count && r.side_to_move == want.side_to_move &&
                  r.checks_remaining_us == want.checks_remaining_us &&
                  r.checks_remaining_them == want.checks_remaining_them,
                  i, "planes/scalars differ from the replayed position");
            check(r.version == lczero::kTrainingDataVersion && r.input_format == lczero::kInputFormat10x10,
                  i, "version / input_format");
            check(r.visits >= 48, i, "root visits " + std::to_string(r.visits) + " < 48");
            const lczero::MoveList legal = h->Last().GenerateLegalMoves();
            std::vector<char> is_legal(lczero::kPolicySize, 0);
            for (const auto& m : legal) is_legal[lczero::MoveToNNIndex(m, 0)] = 1;
            bool mask_ok = true;
            double sum = 0.0;
            float top = -1.0f;
            for (int k = 0; k < lczero::kPolicySize; ++k) {
                const float p = r.probabilities[k];
                if (is_legal[k]) {
                    mask_ok &= p >= 0.0f;
                    sum += p;
                    top = std::max(top, p);
                } else {
                    mask_ok &= p == -1.0f;
                }
            }
            check(mask_ok, i, "pi is not -1 exactly on the illegal moves");
            check(std::abs(sum - 1.0) < 1e-4, i, "sum(pi) = " + std::to_string(sum));
            check(r.best_idx < lczero::kPolicySize && is_legal[r.best_idx] && r.probabilities[r.best_idx] == top,
                  i, "best_idx is not a most-visited legal move");
            lczero::Move played;
            for (const auto& m : legal)
                if (lczero::MoveToNNIndex(m, 0) == r.played_idx) played = m;
            check(!played.is_null(), i, "played_idx is not a legal move");
            if (played.is_null()) { replayed_all = false; break; }
            // Every move is drawn with weight N^2 (T = 0.5): a move nobody visited is never played,
            // and PCR is off here, so no record is marked as a shallow search.
            check(r.probabilities[r.played_idx] > 0.0f, i, "played a move that was never visited");
            check(r.fast_search == 0, i, "fast_search set although PCR is off");
            h->Append(played);
        }
        if (!replayed_all) continue;
        const GameResult end = h->ComputeGameResult();
        const bool capped = end == GameResult::UNDECIDED;
        check(!capped || static_cast<int>(recs.size()) == c.max_moves, recs.size(),
              "the file stops before the game ended");
        const GameResult want_res = capped ? GameResult::DRAW : end;
        check(res == want_res, recs.size(), "PlayOneGame returned a different result than the replay");
        for (size_t i = 0; i < recs.size(); ++i) {
            const auto& r = recs[i];
            float q = 0.0f, d = 1.0f;
            if (want_res != GameResult::DRAW) {
                const bool stm_white = r.side_to_move == 0;
                q = ((want_res == GameResult::WHITE_WON) == stm_white) ? 1.0f : -1.0f;
                d = 0.0f;
            }
            check(r.result_q == q && r.result_d == d, i, "z has the wrong value or sign");
        }
        std::cout << "  " << recs.size() << " records replayed, game "
                  << (capped ? "cut at max_moves (draw)" : "ended by the rules") << ", result "
                  << static_cast<int>(want_res) << (bad ? "" : "  OK") << std::endl;
        std::remove(file.c_str());
    }
}

// ---------------------------------------------------------------------------
// 9. Soft stop on demand (--stop-file): once the file exists RunSelfPlay takes no
// new game, and the games in flight still finish into complete files. The phone
// menu relies on this to stop several machines together at a total game count.
void TestSelfPlayStopFile() {
    std::cout << "\n--- 9. Self-play soft stop (--stop-file) ---" << std::endl;
    namespace fs = std::filesystem;
    fztest::DetBackend backend(/*runs_on_cpu=*/true, /*batch=*/8, /*immediate_mod=*/0);
    fztest::TestSearchOptions opts;
    opts.SetNoise(0.25f, 0.3f);
    const fs::path dir = "test_stop_file_games", stop = "test_stop_file.flag";
    const std::string ext = lczero::TrainingDataWriter::Extension();
    // Finished games (<ext>) and leftovers of unfinished ones (<ext>.tmp) in dir.
    auto count = [&](int* tmp) {
        int n = 0, t = 0;
        std::error_code ec;
        for (const auto& e : fs::directory_iterator(dir, ec)) {
            const std::string f = e.path().filename().string();
            if (f.size() > ext.size() && f.compare(f.size() - ext.size(), ext.size(), ext) == 0) ++n;
            else ++t;
        }
        if (tmp) *tmp = t;
        return n;
    };
    auto run = [&](int games) {
        lczero::SelfPlayConfig cfg;
        cfg.start_fen = lczero::ChessBoard::kStartposFen;
        cfg.out_dir = dir.string();
        cfg.num_games = games;
        cfg.plan.full_visits = 16;
        cfg.max_moves = 30;
        cfg.parallel = 2;
        cfg.stop_file = stop.string();
        lczero::RunSelfPlay(cfg, &backend, opts.Dict());
    };
    std::error_code ec;
    // a) The file is there from the start: no game at all.
    fs::remove_all(dir, ec);
    { std::ofstream(stop.string()) << ""; }
    run(50);
    int tmp = 0;
    EXPECT(count(&tmp) == 0 && tmp == 0, "stop file present at start: " << count(nullptr) << " game(s) played");
    // b) The file appears while running (after 3 games): stops long before --games.
    fs::remove(stop, ec);
    fs::remove_all(dir, ec);
    std::atomic<bool> over{false};
    std::thread watcher([&] {
        while (!over.load()) {
            if (count(nullptr) >= 3) { std::ofstream(stop.string()) << ""; return; }
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
    });
    run(100000);
    over = true;
    watcher.join();
    const int n = count(&tmp);
    EXPECT(n >= 3 && n < 100, "stop file during the run: " << n << " games (want 3.. a few more)");
    EXPECT(tmp == 0, tmp << " unfinished file(s) left behind");
    int bad = 0;
    for (const auto& e : fs::directory_iterator(dir, ec)) {
        std::vector<lczero::TrainingDataV1> recs;
        if (!lczero::ReadTrainingData(e.path().string(), recs) || recs.empty()) ++bad;
    }
    EXPECT(bad == 0, bad << " game file(s) unreadable after the soft stop");
    std::cout << "  stop file at start: 0 games; appeared after 3: " << n << " games, all complete"
              << (n >= 3 && n < 100 && tmp == 0 && bad == 0 ? "  OK" : "") << std::endl;
    fs::remove(stop, ec);
    fs::remove_all(dir, ec);
}

// ---------------------------------------------------------------------------
// 10. Playout cap randomization (PCR) and the move choice.
// ---------------------------------------------------------------------------
// Before EVERY move of a self-play game a coin picks a full search (plan.full_visits, the plain
// options) or a shallow one (plan.fast_visits, plan.fast_options: its own c_puct and Dirichlet
// epsilon); a shallow move's record carries fast_search = 1 so the trainer leaves its policy
// target out. The move played is drawn for EVERY move with weight (N / N_max)^(1 / T), T = 0.5
// meaning N^2, while the policy label stays the visit fraction.
void TestPlayoutCapRandomization() {
    std::cout << "\n--- 10. Playout cap randomization and the move choice ---" << std::endl;
    // Earlier tests leave cout on one decimal; this one prints probabilities.
    const std::ios_base::fmtflags saved_flags = std::cout.flags();
    const std::streamsize saved_precision = std::cout.precision();
    std::cout << std::fixed << std::setprecision(4);
    auto close = [](double a, double b, double tol = 1e-12) { return std::abs(a - b) < tol; };
    namespace bp = lczero::classic;

    // a) The weights of the move choice, worked out by hand.
    const std::vector<uint32_t> visits = {100, 50, 25, 0};
    const auto p5 = lczero::MoveChoiceProbabilities(visits, 0.5f);
    {
        const double z = 10000.0 + 2500.0 + 625.0;   // N^2
        EXPECT(p5.size() == 4 && close(p5[0], 10000.0 / z) && close(p5[1], 2500.0 / z) &&
                   close(p5[2], 625.0 / z) && p5[3] == 0.0,
               "T=0.5 on visits 100/50/25/0 is not 10000/2500/625/0 normalised");
        const auto p1 = lczero::MoveChoiceProbabilities(visits, 1.0f);
        EXPECT(close(p1[0], 100.0 / 175) && close(p1[1], 50.0 / 175) && close(p1[2], 25.0 / 175) &&
                   p1[3] == 0.0,
               "T=1 is not the visit fraction");
        const auto p2 = lczero::MoveChoiceProbabilities(visits, 2.0f);   // square root of N
        const double w1 = std::sqrt(0.5), z2 = 1.0 + w1 + 0.5;
        EXPECT(close(p2[0], 1.0 / z2) && close(p2[1], w1 / z2) && close(p2[2], 0.5 / z2) && p2[3] == 0.0,
               "T=2 is not proportional to sqrt(N)");
        const auto g = lczero::MoveChoiceProbabilities({7, 7, 3}, 0.0f);
        EXPECT(close(g[0], 0.5) && close(g[1], 0.5) && g[2] == 0.0, "T=0 must share the most visited moves");
        const auto gn = lczero::MoveChoiceProbabilities({7, 9, 3}, -1.0f);
        EXPECT(gn[0] == 0.0 && gn[1] == 1.0 && gn[2] == 0.0, "T<0 must be the most visited move");
        const auto none = lczero::MoveChoiceProbabilities({0, 0, 0}, 0.5f);
        EXPECT(none.size() == 3 && none[0] == 0.0 && none[1] == 0.0 && none[2] == 0.0,
               "nothing visited must give all zeros");
        EXPECT(lczero::MoveChoiceProbabilities({}, 0.5f).empty(), "no moves must give an empty vector");
        // A tiny T underflows the weaker moves to 0 instead of overflowing like N^(1/T) would.
        const auto tiny = lczero::MoveChoiceProbabilities({800, 400, 1}, 0.001f);
        EXPECT(std::isfinite(tiny[0]) && tiny[0] > 0.999999 && tiny[2] == 0.0 &&
                   close(tiny[0] + tiny[1] + tiny[2], 1.0, 1e-9),
               "T=0.001 is not (almost) greedy and finite");
        // Every distribution sums to 1.
        bool sums = true;
        for (const float t : {0.1f, 0.5f, 1.0f, 3.0f})
            for (const auto& v : std::vector<std::vector<uint32_t>>{{1}, {5, 0, 5}, {800, 3, 2, 1}}) {
                double s = 0;
                for (const double x : lczero::MoveChoiceProbabilities(v, t)) s += x;
                sums &= close(s, 1.0, 1e-9);
            }
        EXPECT(sums, "a move-choice distribution does not sum to 1");
    }
    // b) The Elo cutoff (2026-11-22): moves more than 70.44 Elo below the most visited one are struck out; the others keep the
    // weight T = 0.5 gives them in the WHOLE visit distribution, so the survivors are that distribution renormalised.
    {
        // 70.44 Elo is a score of 0.6 against 0.5: Q = 0.2 against Q = 0. The clamp makes a proven win / loss +-1200 Elo.
        EXPECT(close(lczero::EloOfValue(0.0), 0.0, 1e-9) && close(lczero::EloOfValue(0.2), 400.0 * std::log10(1.5), 1e-9) &&
                   close(lczero::EloOfValue(-0.2), -400.0 * std::log10(1.5), 1e-9) &&
                   close(lczero::EloOfValue(1.0), 400.0 * std::log10(999.0), 1e-9) &&
                   close(lczero::EloOfValue(-1.0), -400.0 * std::log10(999.0), 1e-9) &&
                   close(lczero::EloOfValue(5.0), lczero::EloOfValue(1.0)),
               "EloOfValue: 0 -> 0, +-0.2 -> +-70.44, +-1 (and beyond) -> +-1199.6");
        constexpr float kCut = 70.44f;
        const std::vector<uint32_t> v = {600, 300, 100, 0};
        const auto plain = lczero::MoveChoiceProbabilities(v, 0.5f);
        // Nothing to strike out: every value within 70.44 Elo of the first move's. The result is the plain T = 0.5 distribution.
        {
            const auto p = lczero::MoveChoiceProbabilities(v, {0.0f, -0.19f, 0.1f, -1.0f}, 0.5f, kCut);
            bool same = p.size() == plain.size();
            for (size_t i = 0; same && i < p.size(); ++i) same = close(p[i], plain[i]);
            EXPECT(same, "nothing struck out must leave the plain distribution");
        }
        // Boundary: Q = -0.2 is 70.4365 Elo below Q = 0 (kept: 70.4365 < 70.44); Q = -0.21 is 74.0 below (struck out).
        {
            const auto kept = lczero::MoveChoiceProbabilities({100, 50}, {0.0f, -0.2f}, 0.5f, kCut);
            const auto gone = lczero::MoveChoiceProbabilities({100, 50}, {0.0f, -0.21f}, 0.5f, kCut);
            EXPECT(close(kept[1], 0.2) && close(kept[0], 0.8) && gone[0] == 1.0 && gone[1] == 0.0,
                   "a move 70.4365 Elo below must stay and one 74 Elo below must go: " << kept[1] << " " << gone[1]);
        }
        // The third move is struck out; the survivors are the T = 0.5 weights 360000 : 90000 of the WHOLE distribution
        // (600 / 300 / 100 -> N^2 = 360000 / 90000 / 10000) renormalised: 0.8 / 0.2. Computing the weights over the survivors' visits
        // alone gives the same numbers (a power law), and this pins it.
        {
            const auto p = lczero::MoveChoiceProbabilities(v, {0.0f, -0.1f, -0.5f, 0.0f}, 0.5f, kCut);
            EXPECT(close(p[0], 0.8) && close(p[1], 0.2) && p[2] == 0.0 && p[3] == 0.0,
                   "struck-out third move: " << p[0] << " " << p[1] << " " << p[2]);
            EXPECT(close(p[1] / p[0], plain[1] / plain[0]), "survivors keep the ratio the whole distribution gives them");
        }
        // The most visited move always stays, whatever the others are; all others struck out gives it probability 1.
        {
            const auto p = lczero::MoveChoiceProbabilities({800, 799, 700}, {0.0f, -0.9f, -0.95f}, 0.5f, kCut);
            EXPECT(p[0] == 1.0 && p[1] == 0.0 && p[2] == 0.0, "the most visited move is the only one left");
        }
        // The reference is the most visited move, not the best valued: a rarely visited move of high value does not strike out the rest.
        {
            const auto p = lczero::MoveChoiceProbabilities({800, 10}, {0.0f, 0.9f}, 0.5f, kCut);
            EXPECT(p[0] > 0.999 && p[1] > 0.0, "a move with a higher value than the most visited one must not be struck out");
        }
        // Equal visits: the reference is the one of higher value (the other is 74 Elo below and goes).
        {
            const auto p = lczero::MoveChoiceProbabilities({500, 500, 20}, {-0.21f, 0.0f, 0.0f}, 0.5f, kCut);
            EXPECT(p[0] == 0.0 && p[1] > 0.99 && p[2] > 0.0, "tie in visits: the cutoff reads from the higher valued move");
        }
        // A proven win (Q = 1, +1200 clamped) strikes out a 0.95-valued move (+511.5): 688 Elo below; a 0.998 one (s = 0.999) stays.
        {
            const auto p = lczero::MoveChoiceProbabilities({600, 300, 100}, {1.0f, 0.95f, 0.998f}, 0.5f, kCut);
            EXPECT(p[1] == 0.0 && p[0] > 0.0 && p[2] > 0.0, "a clearly worse move next to a proven win is struck out");
        }
        // Not visited: weight 0 whatever its value; the value of an unvisited move is never read.
        {
            const auto p = lczero::MoveChoiceProbabilities({10, 0}, {0.0f, std::nanf("")}, 0.5f, kCut);
            EXPECT(p[0] == 1.0 && p[1] == 0.0, "an unvisited move must not be drawn");
        }
        // Off: cutoff 0, negative, NaN; values of the wrong length; T <= 0 (the most visited move only).
        {
            const std::vector<float> val = {0.0f, -0.9f, -0.9f, 0.0f};
            for (const float off : {0.0f, -5.0f, std::nanf("")}) {
                const auto p = lczero::MoveChoiceProbabilities(v, val, 0.5f, off);
                bool same = true;
                for (size_t i = 0; i < p.size(); ++i) same &= close(p[i], plain[i]);
                EXPECT(same, "cutoff " << off << " must be off");
            }
            const auto wrong = lczero::MoveChoiceProbabilities(v, {0.0f}, 0.5f, kCut);
            EXPECT(close(wrong[1], plain[1]), "values of the wrong length must leave the plain distribution");
            const auto greedy = lczero::MoveChoiceProbabilities(v, val, 0.0f, kCut);
            EXPECT(greedy[0] == 1.0 && greedy[1] == 0.0, "T = 0 plays the most visited move with the cutoff too");
            const auto nan_ref = lczero::MoveChoiceProbabilities(v, {std::nanf(""), -0.9f, -0.9f, 0.0f}, 0.5f, kCut);
            EXPECT(close(nan_ref[1], plain[1]), "a NaN reference value strikes nothing out");
        }
        // Every distribution still sums to 1 and is finite, over many random cases.
        {
            bool ok = true;
            for (int t = 0; t < 2000; ++t) {
                const int n = 1 + static_cast<int>(lczero::Random::Get().GetDouble(30.0));
                std::vector<uint32_t> vis(n);
                std::vector<float> val(n);
                for (int i = 0; i < n; ++i) {
                    vis[i] = static_cast<uint32_t>(lczero::Random::Get().GetDouble(801.0));
                    val[i] = static_cast<float>(lczero::Random::Get().GetDouble(2.0) - 1.0);
                }
                const auto p = lczero::MoveChoiceProbabilities(vis, val, 0.5f, kCut);
                double s = 0;
                for (const double x : p) {
                    ok &= std::isfinite(x) && x >= 0.0;
                    s += x;
                }
                uint32_t nmax = 0;
                for (const uint32_t x : vis) nmax = std::max(nmax, x);
                ok &= nmax == 0 ? s == 0.0 : close(s, 1.0, 1e-9);
            }
            EXPECT(ok, "a distribution with the cutoff does not sum to 1 / has a bad entry");
        }
    }
    // The sampler: cumulative, and the last entry when rounding leaves a gap at the top.
    {
        const std::vector<double> p = {0.5, 0.0, 0.5};
        EXPECT(lczero::SampleIndex(p, 0.0) == 0 && lczero::SampleIndex(p, 0.4999) == 0 &&
                   lczero::SampleIndex(p, 0.5) == 2 && lczero::SampleIndex(p, 0.9999) == 2 &&
                   lczero::SampleIndex(p, 1.0) == 2,
               "SampleIndex does not follow the cumulative distribution");
        EXPECT(lczero::SampleIndex({0.0, 0.0}, 0.3) == -1 && lczero::SampleIndex({}, 0.3) == -1,
               "SampleIndex of an all-zero distribution must be -1");
    }
    // Drawing 200000 moves with T = 0.5 reproduces the weights (4 sigma <= 0.0045).
    {
        std::vector<int> count(4, 0);
        const int draws = 200000;
        for (int i = 0; i < draws; ++i)
            ++count[lczero::SampleIndex(p5, lczero::Random::Get().GetDouble(1.0))];
        double worst = 0;
        for (int k = 0; k < 4; ++k) worst = std::max(worst, std::abs(count[k] / double(draws) - p5[k]));
        EXPECT(count[3] == 0 && worst < 0.0045,
               "drawn move frequencies differ from the weights by " << worst);
        std::cout << "  move choice T=0.5 on visits 100/50/25/0: drawn " << count[0] / double(draws) << " / "
                  << count[1] / double(draws) << " / " << count[2] / double(draws) << " / " << count[3]
                  << " (weights " << p5[0] << " / " << p5[1] << " / " << p5[2] << " / 0), worst gap "
                  << worst << std::endl;
    }

    // b) The coin.
    {
        auto rate = [](float prob) {
            int hits = 0;
            const int n = 100000;
            for (int i = 0; i < n; ++i) hits += lczero::ChooseFastSearch(prob) ? 1 : 0;
            return hits / double(n);
        };
        const double r5 = rate(0.5f), r25 = rate(0.25f);
        EXPECT(std::abs(r5 - 0.5) < 0.008 && std::abs(r25 - 0.25) < 0.008,
               "coin rates " << r5 << " / " << r25 << " for 0.5 / 0.25");
        EXPECT(rate(0.0f) == 0.0 && rate(-1.0f) == 0.0 && rate(1.0f) == 1.0 && rate(2.0f) == 1.0 &&
                   rate(std::nanf("")) == 0.0,
               "the coin must never land shallow at 0 and always at 1");
        std::cout << "  coin: 0.5 -> " << r5 << ", 0.25 -> " << r25 << std::endl;
    }

    // c) The two searches read different c_puct and noise epsilon, the rest is shared.
    fztest::DetBackend backend(/*runs_on_cpu=*/true, /*batch=*/8, /*immediate_mod=*/0);
    fztest::TestSearchOptions opts;
    opts.SetNoise(0.25f, 0.3f);
    opts.Set("cpuct", "1.5");
    opts.Set("minibatch-size", "4");   // a search overshoots its playout cap by at most one mini-batch
    lczero::OptionsDict fast(&opts.Dict());
    fast.Set<float>(bp::BaseSearchParams::kCpuctId, 1.25f);
    fast.Set<float>(bp::BaseSearchParams::kNoiseEpsilonId, 0.125f);
    {
        const bp::SearchParams full_p(opts.Dict()), fast_p(fast);
        EXPECT(close(full_p.GetCpuct(false), 1.5, 1e-6) && close(full_p.GetCpuct(true), 1.5, 1e-6) &&
                   close(full_p.GetNoiseEpsilon(), 0.25, 1e-6),
               "full-search options: cpuct " << full_p.GetCpuct(false) << " / root " << full_p.GetCpuct(true)
               << ", noise " << full_p.GetNoiseEpsilon());
        EXPECT(close(fast_p.GetCpuct(false), 1.25, 1e-6) && close(fast_p.GetCpuct(true), 1.25, 1e-6) &&
                   close(fast_p.GetNoiseEpsilon(), 0.125, 1e-6) &&
                   fast_p.GetNoiseAlpha() == full_p.GetNoiseAlpha() &&
                   fast_p.GetMiniBatchSize() == full_p.GetMiniBatchSize(),
               "shallow-search options: cpuct " << fast_p.GetCpuct(false) << " / root " << fast_p.GetCpuct(true)
               << ", noise " << fast_p.GetNoiseEpsilon() << " (alpha and mini-batch must be shared)");
    }

    // d) Games with PCR: the coin, the visits, the marks.
    const std::string file = std::string("test_pcr_game") + lczero::TrainingDataWriter::Extension();
    {
        struct Run { float prob; float temp; const char* name; float elo = 0.0f; };
        // The last two draw with the Elo cutoff: the production value, and 0.1 Elo, which strikes out every move the search
        // does not rate (almost) equal to the most visited one, so the check below on the records is not vacuous.
        const Run runs[] = {{0.5f, 0.5f, "PCR 50%, T=0.5"}, {0.0f, 0.5f, "PCR off, T=0.5"},
                            {1.0f, 0.5f, "all shallow"}, {0.0f, 0.0f, "PCR off, T=0 (greedy)"},
                            {0.5f, 0.5f, "PCR 50%, T=0.5, Elo cutoff 70.44", 70.44f},
                            {0.5f, 0.5f, "PCR 50%, T=0.5, Elo cutoff 0.1", 0.1f}};
        for (const Run& run : runs) {
            lczero::SelfPlaySearchPlan plan;
            plan.full_visits = 64;
            plan.fast_visits = 16;
            plan.fast_prob = run.prob;
            plan.temperature = run.temp;
            plan.elo_cutoff = run.elo;
            plan.fast_options = &fast;
            int total = 0, shallow = 0, off_best = 0, bad = 0, over_full = 0, over_fast = 0;
            int under = 0, mismatch = 0, over_cut = 0;
            for (int game = 0; game < 6; ++game) {
                int moves = -1, fast_moves = -1;
                lczero::PlayOneGame(lczero::ChessBoard::kStartposFen, &backend, opts.Dict(), plan, 40, file,
                                    /*search_threads=*/1, /*verbose=*/false, -2.0f, 3, true, 0, nullptr,
                                    nullptr, nullptr, nullptr, &moves, &fast_moves);
                std::vector<lczero::TrainingDataV1> recs;
                if (!lczero::ReadTrainingData(file, recs) || recs.empty()) { ++bad; continue; }
                int marked = 0;
                for (const auto& r : recs) {
                    const bool is_fast = r.fast_search == 1;
                    bad += (r.fast_search > 1) ? 1 : 0;
                    marked += is_fast ? 1 : 0;
                    const int want = is_fast ? 16 : 64;
                    under += (static_cast<int>(r.visits) < want) ? 1 : 0;
                    (is_fast ? over_fast : over_full) =
                        std::max(is_fast ? over_fast : over_full, static_cast<int>(r.visits) - want);
                    double sum = 0.0;
                    float top = -1.0f;
                    for (int k = 0; k < lczero::kPolicySize; ++k)
                        if (r.probabilities[k] > 0.0f) { sum += r.probabilities[k]; top = std::max(top, r.probabilities[k]); }
                    bad += (std::abs(sum - 1.0) > 1e-3) ? 1 : 0;   // the label is the visit fraction, shallow or not
                    off_best += (r.probabilities[r.played_idx] < top) ? 1 : 0;
                    // The move played is never more than the cutoff below the best move (both values are W - L of the root mover).
                    if (run.elo > 0.0f &&
                        lczero::EloOfValue(r.best_q) - lczero::EloOfValue(r.played_q) > static_cast<double>(run.elo) + 1e-6)
                        ++over_cut;
                }
                mismatch += (moves != static_cast<int>(recs.size()) || fast_moves != marked) ? 1 : 0;
                total += static_cast<int>(recs.size());
                shallow += marked;
            }
            std::remove(file.c_str());
            const double frac = total > 0 ? shallow / double(total) : 0.0;
            std::cout << "  " << run.name << ": " << total << " records, " << shallow << " shallow (" << frac
                      << "), root visits overshoot at most +" << over_full << " (full, 64) / +" << over_fast
                      << " (shallow, 16), played a non-best move in " << off_best << std::endl;
            EXPECT(total >= 200 && bad == 0, run.name << ": unreadable game or bad record (" << bad << ")");
            EXPECT(under == 0, run.name << ": " << under << " record(s) searched fewer playouts than their cap");
            EXPECT(over_full <= 16 && over_fast <= 16,
                   run.name << ": a search overshot its playout cap by " << std::max(over_full, over_fast));
            EXPECT(mismatch == 0, run.name << ": out_moves / out_fast_moves differ from the records");
            EXPECT(over_cut == 0, run.name << ": " << over_cut << " move(s) played more than " << run.elo << " Elo below the best");
            if (run.prob == 0.5f) EXPECT(std::abs(frac - 0.5) < 0.15, "PCR 50%: shallow fraction " << frac);
            if (run.prob == 0.0f) EXPECT(shallow == 0, run.name << ": " << shallow << " shallow record(s)");
            if (run.prob == 1.0f) EXPECT(shallow == total, run.name << ": not every record is shallow");
            // T = 0 plays the most visited move; T = 0.5 draws, so on 48+ moves it often is not.
            if (run.temp == 0.0f) EXPECT(off_best == 0, run.name << ": played " << off_best << " non-best move(s)");
            if (run.temp == 0.5f && run.prob == 0.0f)
                EXPECT(off_best >= total / 10, run.name << ": only " << off_best << " of " << total
                                                          << " moves were not the most visited");
        }
    }

    // e) The options of each kind really reach its searches. Noise is the probe: a search is
    // deterministic without it (one thread, deterministic net) and differs run to run with it.
    {
        lczero::SelfPlaySearchPlan plan;
        plan.full_visits = 32;
        plan.fast_visits = 32;
        plan.temperature = 0.5f;
        auto first_pi = [&](const lczero::OptionsDict& o, const lczero::OptionsDict* fo, float prob) {
            plan.fast_prob = prob;
            plan.fast_options = fo;
            lczero::PlayOneGame(lczero::ChessBoard::kStartposFen, &backend, o, plan, 1, file, 1, false);
            std::vector<lczero::TrainingDataV1> recs;
            std::vector<float> pi;
            if (lczero::ReadTrainingData(file, recs) && !recs.empty())
                pi.assign(recs[0].probabilities, recs[0].probabilities + lczero::kPolicySize);
            std::remove(file.c_str());
            return pi;
        };
        fztest::TestSearchOptions noisy, quiet;
        noisy.SetNoise(1.0f, 0.3f);
        quiet.SetNoise(0.0f, 0.3f);
        lczero::OptionsDict fast_quiet(&noisy.Dict()), fast_noisy(&quiet.Dict());
        fast_quiet.Set<float>(bp::BaseSearchParams::kNoiseEpsilonId, 0.0f);
        fast_noisy.Set<float>(bp::BaseSearchParams::kNoiseEpsilonId, 1.0f);
        // Full options noisy, shallow quiet.
        const auto a1 = first_pi(noisy.Dict(), &fast_quiet, 1.0f), a2 = first_pi(noisy.Dict(), &fast_quiet, 1.0f);
        const auto b1 = first_pi(noisy.Dict(), &fast_quiet, 0.0f), b2 = first_pi(noisy.Dict(), &fast_quiet, 0.0f);
        // Full options quiet, shallow noisy.
        const auto c1 = first_pi(quiet.Dict(), &fast_noisy, 1.0f), c2 = first_pi(quiet.Dict(), &fast_noisy, 1.0f);
        const auto d1 = first_pi(quiet.Dict(), &fast_noisy, 0.0f), d2 = first_pi(quiet.Dict(), &fast_noisy, 0.0f);
        const bool ok = !a1.empty() && !b1.empty() && !c1.empty() && !d1.empty();
        EXPECT(ok, "no record from the options probe games");
        if (ok) {
            EXPECT(a1 == a2, "shallow search with noise epsilon 0 is not repeatable: it used the full (noisy) options");
            EXPECT(b1 != b2, "full search with noise epsilon 1 repeated itself: noise did not reach it");
            EXPECT(c1 != c2, "shallow search with noise epsilon 1 repeated itself: it did not use fast_options");
            EXPECT(d1 == d2, "full search with noise epsilon 0 is not repeatable: it used fast_options");
            std::cout << "  options probe: shallow-with-quiet-options repeatable " << (a1 == a2)
                      << ", full-with-noise differs " << (b1 != b2) << ", shallow-with-noise differs "
                      << (c1 != c2) << ", full-quiet repeatable " << (d1 == d2) << std::endl;
        }
    }
    std::cout.flags(saved_flags);
    std::cout.precision(saved_precision);
}

}  // namespace

void run_search_logic_tests(const std::string& weights_path) {
    std::cout << "\n========================================" << std::endl;
    std::cout << "RUNNING STRICT SEARCH-LOGIC TESTS..." << std::endl;
    std::cout << "========================================" << std::endl;
    setup_custom_variant();

    TestSearchTargetPerspective();
    TestNoiseEveryMove();
    TestTreeInvariants();
    TestConcurrentAddInput(weights_path);
    TestLegalMoveCapacity();
    TestUciTreeReuse(weights_path);
    TestSearchLifecycleStress();
    TestSelfPlayRecordsReplay();
    TestSelfPlayStopFile();
    TestPlayoutCapRandomization();

    std::cout << "\n========================================" << std::endl;
    if (g_failures == 0) {
        std::cout << "[PASS] ALL STRICT SEARCH-LOGIC TESTS PASSED" << std::endl;
        std::cout << "========================================" << std::endl;
    } else {
        std::cerr << "[FAIL] " << g_failures << " strict search-logic check(s) failed" << std::endl;
        std::cout << "========================================" << std::endl;
        std::exit(1);
    }
}
