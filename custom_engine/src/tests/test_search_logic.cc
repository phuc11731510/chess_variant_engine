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
//
// Every sub-test runs even if an earlier one failed; the process exits 1 at the
// end if anything failed.

#include "tests/test_common.h"
#include "app/fairyzero_ffi.h"
#include "app/uci_nn_engine.h"
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
                                "MSYSNNSYSM/VRHBQKBERV b BIbi - 8+8 0 1"}) {
            auto tree = std::make_unique<NodeTree>();
            tree->ResetToPosition(fen, {});
            fztest::RunTestSearch(tree.get(), backend.get(), opts.Dict(), 1, 1);
            auto rec = FreshRecord();
            lczero::FillSearchTargets(tree->GetCurrentHead(), tree->GetPositionHistory(),
                                      backend.get(), rec);
            const float net_q =
                fztest::DetValue(tree->GetPositionHistory().Last().Hash()).q;
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
    const fztest::DetEval own = fztest::DetValue(hist->Last().Hash());
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
        const uint64_t key = pos[i].history->Last().Hash();
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
        "k9/10/1r1r1r1r1r/P1S1P1S1P1/1P1P1P1P1P/1Q2E2H2/10/2R3R3/1B2V2V1B/M3K4M w - - 8+8 0 1";
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
        {"4k5/10/10/10/10/10/10/10/10/R3K4R w - - 8+8 0 1", 300},    // ends by the rules
        {"n3k5/10/10/10/10/10/10/10/10/4K4N b - - 8+8 20 1", 300},   // quiet: repetition / rule 50
    };
    for (const auto& c : cases) {
        const lczero::GameResult res = lczero::PlayOneGame(
            c.fen, &backend, opts.Dict(), /*visits=*/48, c.max_moves, /*temp_cutoff_ply=*/10,
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
                  r.checks_remaining_them == want.checks_remaining_them &&
                  r.castling_us_ooo_file == want.castling_us_ooo_file &&
                  r.castling_us_oo_file == want.castling_us_oo_file &&
                  r.castling_them_ooo_file == want.castling_them_ooo_file &&
                  r.castling_them_oo_file == want.castling_them_oo_file,
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
            if (static_cast<int>(i) >= 10)   // greedy after the temperature cutoff
                check(r.played_idx == r.best_idx || r.probabilities[r.played_idx] == top, i,
                      "played a non-best move after the temperature cutoff");
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
