// --test-neural [--weights net.onnx] : strict checks of the NN layer
// (src/lczero_chess/neural/) and of what the self-play records take from it.
//
//   1. SoftmaxLegal against an exact softmax in double (every n up to 384,
//      temperatures 0.25..4, logit spreads up to 60, NaN/inf, tails).
//   2. IsWdlDistribution and OnnxBufferSlots (the fixed-batch buffer sizing).
//   3. [--weights] OnnxBackend against an INDEPENDENT reference: a separate ORT
//      session run on one position at a time, exact softmax over MoveToNNIndex.
//      Dynamic batch and fixed batches 1/7/16/24/48/64, every batch size that
//      matters (1, f-1, f, f+1, 37, 64), temperatures 1 and 0.25.
//   4. ZeroHeapCache: a hit returns exactly what the miss computed, the
//      existence probe used by prefetch, move-count mismatch, clearing on a
//      weights change, and a torn-read stress test of the seqlock.
//   5. BatchingBackend: exact results for 6 producers with groups that span
//      server rounds, fewer producers than expected (the timeout path).
//   6. FillSearchTargets: orig_q/orig_d/policy_kld are the root's raw eval even
//      when the root's cache entry has been overwritten (a 1-bucket cache).

#include "tests/test_common.h"
#include <limits>
#include "onnxruntime_cxx_api.h"

namespace {

int g_fail = 0;          // all sections
int g_section_fail = 0;  // the current section (only its first 8 are printed)

#define EXPECT(cond, msg)                                                        \
    do {                                                                         \
        if (!(cond)) {                                                           \
            ++g_fail;                                                            \
            if (++g_section_fail <= 8) std::cerr << "  [FAIL] " << msg << std::endl; \
        }                                                                        \
    } while (0)

// Runs one section and says how it went.
template <typename F>
void Section(const char* name, F&& body) {
    g_section_fail = 0;
    body();
    if (g_section_fail)
        std::cerr << "  => " << name << ": " << g_section_fail << " failed check(s)" << std::endl;
    else
        std::cout << "  => " << name << ": ok" << std::endl;
}

// Exact softmax in double: p_i = exp((l_i - max) / t) / sum.
std::vector<double> ExactSoftmax(const std::vector<float>& l, double t) {
    double m = -std::numeric_limits<double>::infinity();
    for (float x : l) m = std::max(m, static_cast<double>(x));
    std::vector<double> p(l.size());
    double s = 0.0;
    for (size_t i = 0; i < l.size(); ++i) s += (p[i] = std::exp((l[i] - m) / t));
    for (double& x : p) x /= s;
    return p;
}

// ---------------------------------------------------------------------------
// 1. SoftmaxLegal
// ---------------------------------------------------------------------------
void TestSoftmax() {
    std::cout << "--- 1. SoftmaxLegal vs exact softmax ---" << std::endl;
    std::mt19937 rng(12345);
    double worst_rel = 0.0, worst_abs = 0.0;
    long checked = 0;
    const float temps[] = {0.25f, 0.5f, 1.0f, 1.359f, 2.0f, 4.0f};
    const float spreads[] = {0.5f, 2.0f, 8.0f, 20.0f, 60.0f};
    for (size_t n = 1; n <= 384; n += (n < 70 ? 1 : 37)) {
        for (float t : temps) {
            for (float spread : spreads) {
                std::uniform_real_distribution<float> u(-spread, spread);
                std::vector<float> l(n);
                const float offset = u(rng) * 10.0f;  // the absolute level must not matter
                for (auto& x : l) x = u(rng) + offset;
                alignas(64) float scratch[384 + 8];
                std::copy(l.begin(), l.end(), scratch);
                float out[384];
                const float mx = *std::max_element(l.begin(), l.end());
                const float sum = lczero::SoftmaxLegal(scratch, n, t, mx, out, 384);
                const std::vector<double> ref = ExactSoftmax(l, t);
                EXPECT(std::isfinite(sum) && sum >= 1.0f, "n=" << n << " sum=" << sum);
                double total = 0.0;
                for (size_t i = 0; i < n; ++i) {
                    total += out[i];
                    const double a = std::fabs(out[i] - ref[i]);
                    worst_abs = std::max(worst_abs, a);
                    // Relative accuracy wherever exp() is not clamped (x >= -80).
                    if ((l[i] - mx) / t >= -80.0f) {
                        worst_rel = std::max(worst_rel, a / ref[i]);
                        ++checked;
                    }
                }
                EXPECT(std::fabs(total - 1.0) < 1e-5, "n=" << n << " t=" << t << " sum(p)=" << total);
            }
        }
    }
    std::cout << "  " << checked << " probabilities: max relative error " << worst_rel
              << ", max absolute error " << worst_abs << std::endl;
    // A few float ulps for exp, plus the summation of up to 384 terms.
    EXPECT(worst_rel < 2e-5, "SoftmaxLegal relative error " << worst_rel << " >= 2e-5");

    // Logits far below -100: only the differences may matter (the old code
    // padded with a constant -100, which then dominated the sum).
    {
        std::vector<float> l = {-500.0f, -501.0f, -502.5f};
        alignas(64) float scratch[16];
        std::copy(l.begin(), l.end(), scratch);
        float out[3];
        lczero::SoftmaxLegal(scratch, 3, 1.0f, -500.0f, out, 3);
        const auto ref = ExactSoftmax(l, 1.0);
        for (int i = 0; i < 3; ++i)
            EXPECT(std::fabs(out[i] - ref[i]) < 1e-6, "very negative logits: p" << i << "=" << out[i]
                                                          << " want " << ref[i]);
    }
    // max_out < n: only max_out outputs written, normalised over all n.
    {
        std::vector<float> l = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11};
        alignas(64) float scratch[16];
        std::copy(l.begin(), l.end(), scratch);
        float out[16];
        std::fill(out, out + 16, -7.0f);
        lczero::SoftmaxLegal(scratch, l.size(), 1.0f, 11.0f, out, 5);
        const auto ref = ExactSoftmax(l, 1.0);
        for (int i = 0; i < 5; ++i) EXPECT(std::fabs(out[i] - ref[i]) < 1e-7, "max_out: p" << i);
        for (int i = 5; i < 16; ++i) EXPECT(out[i] == -7.0f, "max_out: wrote past max_out at " << i);
    }
    // Broken nets must not turn into a plausible distribution.
    {
        const float nan = std::numeric_limits<float>::quiet_NaN();
        const float inf = std::numeric_limits<float>::infinity();
        alignas(64) float s1[16] = {0.5f, nan, 0.1f};
        float out[16];
        EXPECT(!std::isfinite(lczero::SoftmaxLegal(s1, 3, 1.0f, 0.5f, out, 16)), "a NaN logit is not reported");
        alignas(64) float s2[16] = {nan, nan, nan, nan, nan, nan, nan, nan, nan};
        EXPECT(!std::isfinite(lczero::SoftmaxLegal(s2, 9, 1.0f, -inf, out, 16)), "all-NaN logits not reported");
        alignas(64) float s3[16] = {-inf, -inf};
        EXPECT(!std::isfinite(lczero::SoftmaxLegal(s3, 2, 1.0f, -inf, out, 16)), "all -inf logits not reported");
        alignas(64) float s4[16] = {inf, 0.0f};
        EXPECT(!std::isfinite(lczero::SoftmaxLegal(s4, 2, 1.0f, inf, out, 16)), "a +inf logit not reported");
    }
}

// ---------------------------------------------------------------------------
// 2. Small helpers
// ---------------------------------------------------------------------------
void TestHelpers() {
    std::cout << "--- 2. IsWdlDistribution, OnnxBufferSlots ---" << std::endl;
    const float nan = std::numeric_limits<float>::quiet_NaN();
    const float ok[3] = {0.5f, 0.3f, 0.2f}, edge[3] = {1.0f, 0.0f, 0.0f};
    const float logits[3] = {1.2f, -0.5f, 3.0f}, sum_off[3] = {0.5f, 0.3f, 0.25f};
    const float has_nan[3] = {0.5f, nan, 0.5f}, negative[3] = {1.1f, 0.0f, -0.1f};
    EXPECT(lczero::IsWdlDistribution(ok), "valid WDL rejected");
    EXPECT(lczero::IsWdlDistribution(edge), "1/0/0 rejected");
    EXPECT(!lczero::IsWdlDistribution(logits), "raw logits accepted as WDL");
    EXPECT(!lczero::IsWdlDistribution(sum_off), "sum 1.05 accepted");
    EXPECT(!lczero::IsWdlDistribution(has_nan), "NaN accepted");
    EXPECT(!lczero::IsWdlDistribution(negative), "negative probability accepted");

    EXPECT(lczero::OnnxBufferSlots(false, 16) == lczero::MaxBatchSize, "dynamic batch slots");
    for (size_t f = 1; f <= lczero::MaxBatchSize; ++f) {
        const size_t s = lczero::OnnxBufferSlots(true, f);
        // The last Run() of a full computation ends at ceil(64/f)*f.
        const size_t need = (lczero::MaxBatchSize + f - 1) / f * f;
        EXPECT(s == need && s % f == 0 && s >= lczero::MaxBatchSize,
               "OnnxBufferSlots(" << f << ") = " << s << ", need " << need);
    }
}

// ---------------------------------------------------------------------------
// Positions used by the backend tests: random games from the start position,
// plus special positions (Black to move with e.p., castling, few moves).
// ---------------------------------------------------------------------------
std::vector<std::unique_ptr<lczero::PositionHistory>> MakePositions(size_t count) {
    std::vector<std::unique_ptr<lczero::PositionHistory>> out;
    std::mt19937_64 rng(0xFA17ULL);
    const char* fens[] = {
        lczero::ChessBoard::kStartposFen,
        "1r3k2r1/2p4p2/10/4n5/10/10/5B4/10/2P4P2/1R3K2R1 w BIbi - 8+8 0 1",
        "4k5/3s1s4/10/2P1S1P3/10/10/10/10/10/4K5 b - - 8+8 0 1",
        "k9/10/10/3pP5/10/10/10/10/10/K9 w - d8 8+8 0 1",
    };
    size_t f = 0;
    while (out.size() < count) {
        auto h = std::make_unique<lczero::PositionHistory>();
        h->Reset(lczero::Position::FromFen(fens[f++ % 4]));
        for (int ply = 0; ply < 70 && out.size() < count; ++ply) {
            const lczero::MoveList lm = h->Last().GetBoard().GenerateLegalMoves();
            if (lm.empty() || h->ComputeGameResult() != lczero::GameResult::UNDECIDED) break;
            if (ply % 9 == 0 || ply < 2) out.push_back(std::make_unique<lczero::PositionHistory>(*h));
            h->Append(lm[static_cast<size_t>(rng() % lm.size())]);
        }
    }
    return out;
}

struct RefEval {
    float w, d, l;
    std::vector<float> logits;     // raw policy logit of each legal move, legal order
};

// ---------------------------------------------------------------------------
// 3. OnnxBackend vs an independent ORT session
// ---------------------------------------------------------------------------
void TestOnnxBackend(const std::string& weights) {
    std::cout << "--- 3. OnnxBackend vs an independent ORT session (" << weights << ") ---"
              << std::endl;
    auto positions = MakePositions(64);
    std::vector<lczero::MoveList> legal;
    for (const auto& h : positions) legal.push_back(h->Last().GetBoard().GenerateLegalMoves());

    // Reference: its own env/session/options, one position per Run().
    std::vector<RefEval> ref;
    {
        Ort::Env env(ORT_LOGGING_LEVEL_WARNING, "fz_ref");
        Ort::SessionOptions so;
        so.SetIntraOpNumThreads(1);
#ifdef _WIN32
        std::wstring wpath(weights.begin(), weights.end());
        Ort::Session session(env, wpath.c_str(), so);
#else
        Ort::Session session(env, weights.c_str(), so);
#endif
        Ort::MemoryInfo mem = Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault);
        std::vector<float> input(lczero::InputBufferUnitSize), policy(lczero::PolicyOutputSize),
            value(3);
        for (size_t k = 0; k < positions.size(); ++k) {
            lczero::InputPlanes planes;
            int t = 0;
            lczero::EncodePositionForNN(*positions[k], lczero::kMoveHistory,
                                        lczero::FillEmptyHistory::FEN_ONLY, &planes, &t);
            lczero::UnpackInputPlanes(planes, input.data(), 10, 10);
            const int64_t ishape[4] = {1, 226, 10, 10}, pshape[2] = {1, 10600}, vshape[2] = {1, 3};
            Ort::Value in = Ort::Value::CreateTensor<float>(mem, input.data(), input.size(), ishape, 4);
            Ort::Value outs[2] = {
                Ort::Value::CreateTensor<float>(mem, policy.data(), policy.size(), pshape, 2),
                Ort::Value::CreateTensor<float>(mem, value.data(), value.size(), vshape, 2)};
            const char* in_names[] = {"input"};
            const char* out_names[] = {"policy", "value"};
            session.Run(Ort::RunOptions{nullptr}, in_names, &in, 1, out_names, outs, 2);
            RefEval r{value[0], value[1], value[2], {}};
            for (const auto& m : legal[k]) r.logits.push_back(policy[lczero::MoveToNNIndex(m, 0)]);
            ref.push_back(std::move(r));
        }
    }

    struct Config { const char* opts; float temp; };
    const Config configs[] = {
        {"threads=1", 1.0f},                 {"threads=1,fixed_batch=1", 1.0f},
        {"threads=1,fixed_batch=7", 1.0f},   {"threads=1,fixed_batch=16", 1.0f},
        {"threads=1,fixed_batch=24", 1.0f},  {"threads=1,fixed_batch=48", 1.0f},
        {"threads=1,fixed_batch=64", 1.0f},  {"threads=1,fixed_batch=16", 0.25f},
        {"threads=1", 0.25f},
    };
    double worst_q = 0.0, worst_p = 0.0;
    for (const Config& c : configs) {
        lczero::OptionsParser parser;
        auto* d = parser.GetMutableDefaultsOptions();
        d->Set<std::string>(lczero::SharedBackendParams::kWeightsId, weights);
        d->Set<std::string>(lczero::SharedBackendParams::kBackendOptionsId, c.opts);
        d->Set<float>(lczero::SharedBackendParams::kPolicySoftmaxTemp, c.temp);
        lczero::OnnxBackend backend;
        backend.UpdateConfiguration(parser.GetOptionsDict());
        int f = 64;
        if (const char* fb = std::strstr(c.opts, "fixed_batch=")) f = std::atoi(fb + 12);
        std::vector<int> sizes = {1, f - 1, f, f + 1, 37, 64};
        size_t next = 0;  // positions are used round-robin across batches
        for (int bs : sizes) {
            if (bs < 1 || bs > 64) continue;
            std::vector<lczero::EvalResult> res(bs);
            std::vector<size_t> which(bs);
            auto comp = backend.CreateComputation();
            for (int i = 0; i < bs; ++i) {
                which[i] = next++ % positions.size();
                res[i].p.resize(legal[which[i]].size());
                const lczero::EvalPosition ep{
                    positions[which[i]].get(),
                    std::span<const lczero::Move>(legal[which[i]].data(), legal[which[i]].size())};
                comp->AddInput(ep, res[i].AsPtr());
            }
            comp->ComputeBlocking();
            for (int i = 0; i < bs; ++i) {
                const RefEval& r = ref[which[i]];
                const double dq = std::fabs(res[i].q - (r.w - r.l)), dd = std::fabs(res[i].d - r.d);
                worst_q = std::max({worst_q, dq, dd});
                EXPECT(dq < 1e-4 && dd < 1e-4, c.opts << " T=" << c.temp << " batch " << bs << " slot "
                                                      << i << ": q/d off by " << dq << "/" << dd);
                const auto p = ExactSoftmax(r.logits, c.temp);
                double dp = 0.0;
                for (size_t m = 0; m < p.size(); ++m) dp = std::max(dp, std::fabs(res[i].p[m] - p[m]));
                worst_p = std::max(worst_p, dp);
                EXPECT(dp < 1e-4, c.opts << " T=" << c.temp << " batch " << bs << " slot " << i
                                         << ": prior off by " << dp);
            }
        }
    }
    std::cout << "  " << (sizeof(configs) / sizeof(configs[0])) << " backend configs x 6 batch sizes: "
              << "max |q|/|d| diff " << worst_q << ", max prior diff " << worst_p << std::endl;
}

// ---------------------------------------------------------------------------
// 4. ZeroHeapCache
// ---------------------------------------------------------------------------
// Counts evaluations, answers like DetBackend, and has a configuration (its
// weights path) so the cache's clearing on a weights change can be tested.
class CountingBackend : public lczero::Backend {
public:
    std::atomic<int> evals{0};
    std::string weights = "a.onnx";
    lczero::BackendAttributes GetAttributes() const override {
        return {false, true, true, 1, 16, 64};
    }
    class Comp : public lczero::BackendComputation {
    public:
        explicit Comp(CountingBackend* b) : b_(b) {}
        size_t UsedBatchSize() const override { return n_; }
        AddInputResult AddInput(const lczero::EvalPosition& pos, lczero::EvalResultPtr r) override {
            slots_.push_back({fztest::DetKey(pos.history->Last()), pos.legal_moves.size(), r});
            ++n_;
            return ENQUEUED_FOR_EVAL;
        }
        void ComputeBlocking() override {
            for (auto& s : slots_) {
                fztest::DetFill(s.key ^ std::hash<std::string>()(b_->weights), s.n, s.r);
                ++b_->evals;
            }
            slots_.clear();
            n_ = 0;
        }
    private:
        struct S { uint64_t key; size_t n; lczero::EvalResultPtr r; };
        CountingBackend* b_;
        std::vector<S> slots_;
        size_t n_ = 0;
    };
    std::unique_ptr<lczero::BackendComputation> CreateComputation() override {
        return std::make_unique<Comp>(this);
    }
    void UpdateConfiguration(const lczero::OptionsDict& o) override {
        weights = o.Get<std::string>(lczero::SharedBackendParams::kWeightsId);
    }
    bool IsSameConfiguration(const lczero::OptionsDict& o) const override {
        return o.Get<std::string>(lczero::SharedBackendParams::kWeightsId) == weights;
    }
};

bool Eval(lczero::Backend* b, const lczero::PositionHistory& h, const lczero::MoveList& moves,
          lczero::EvalResult* out) {
    out->p.resize(moves.size());
    auto comp = b->CreateComputation();
    const auto r = comp->AddInput(
        lczero::EvalPosition{&h, std::span<const lczero::Move>(moves.data(), moves.size())},
        out->AsPtr());
    comp->ComputeBlocking();
    return r == lczero::BackendComputation::FETCHED_IMMEDIATELY;
}

void TestCache() {
    std::cout << "--- 4. ZeroHeapCache ---" << std::endl;
    auto positions = MakePositions(8);
    lczero::OptionsParser parser;
    parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kWeightsId, "a.onnx");
    parser.GetMutableDefaultsOptions()->Set<int>(lczero::SharedBackendParams::kNNCacheSizeId, 4096);
    auto counting = std::make_unique<CountingBackend>();
    CountingBackend* inner = counting.get();
    auto cache = lczero::CreateMemCache(std::move(counting), parser.GetOptionsDict());

    const auto& h = *positions[3];
    const lczero::MoveList moves = h.Last().GetBoard().GenerateLegalMoves();
    const lczero::EvalPosition probe{&h, {}};
    const lczero::EvalPosition full{&h, std::span<const lczero::Move>(moves.data(), moves.size())};

    EXPECT(!cache->GetCachedEvaluation(probe), "probe hit before anything was evaluated");
    lczero::EvalResult miss, hit;
    EXPECT(!Eval(cache.get(), h, moves, &miss), "first evaluation was not a miss");
    EXPECT(inner->evals == 1, "the wrapped backend ran " << inner->evals << " times, not 1");
    EXPECT(Eval(cache.get(), h, moves, &hit), "second evaluation was not a hit");
    EXPECT(inner->evals == 1, "a cache hit reached the wrapped backend");
    bool same = hit.q == miss.q && hit.d == miss.d;
    for (size_t i = 0; i < moves.size(); ++i) same = same && hit.p[i] == miss.p[i];
    EXPECT(same, "a cache hit returned something else than the evaluation it cached");

    // The existence probe of lc0's PrefetchIntoCache (no moves): must hit.
    const auto pr = cache->GetCachedEvaluation(probe);
    EXPECT(pr.has_value(), "existence probe (no legal moves) missed a cached position");
    if (pr) EXPECT(pr->q == miss.q && pr->p.empty(), "probe returned a wrong value or a policy");
    const auto fu = cache->GetCachedEvaluation(full);
    EXPECT(fu && fu->p.size() == moves.size(), "full lookup missed");
    // A different move count is a different position as far as the policy goes.
    lczero::MoveList fewer;
    for (size_t i = 0; i + 1 < moves.size(); ++i) fewer.push_back(moves[i]);
    EXPECT(!cache->GetCachedEvaluation(
               lczero::EvalPosition{&h, std::span<const lczero::Move>(fewer.data(), fewer.size())}),
           "lookup with another move count hit");

    // Same weights: entries survive. New weights: the old net's evals must go.
    cache->UpdateConfiguration(parser.GetOptionsDict());
    EXPECT(cache->GetCachedEvaluation(full).has_value(), "cache cleared on an unchanged configuration");
    lczero::OptionsParser parser_b;
    parser_b.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kWeightsId, "b.onnx");
    cache->UpdateConfiguration(parser_b.GetOptionsDict());
    EXPECT(!cache->GetCachedEvaluation(full).has_value(),
           "after loading other weights the cache still served the old net's evaluation");

    // Seqlock: writers and readers hammer 2 buckets. Every value written is a
    // pure function of one counter c, so a torn read (half old, half new) shows.
    {
        lczero::OptionsParser ps;
        ps.GetMutableDefaultsOptions()->Set<int>(lczero::SharedBackendParams::kNNCacheSizeId, 2);
        lczero::ZeroHeapCache zc(std::make_unique<CountingBackend>(), ps.GetOptionsDict());
        constexpr uint16_t kMoves = 96;
        std::atomic<bool> stop{false};
        std::atomic<long> reads{0}, torn{0};
        std::vector<std::thread> threads;
        for (int w = 0; w < 3; ++w)
            threads.emplace_back([&, w] {
                std::vector<float> p(kMoves);
                for (uint32_t c = 1; !stop.load(std::memory_order_relaxed); ++c) {
                    const float base = static_cast<float>((c * 3 + w) % 100000);
                    for (int i = 0; i < kMoves; ++i) p[i] = base + i;
                    zc.Insert(1 + (c & 3), kMoves, base, base + 0.5f, base + 0.25f, p);
                }
            });
        for (int r = 0; r < 3; ++r)
            threads.emplace_back([&] {
                lczero::EvalResult out;
                out.p.resize(kMoves);
                for (uint32_t c = 0; !stop.load(std::memory_order_relaxed); ++c) {
                    lczero::EvalResultPtr ptr = out.AsPtr();
                    if (!zc.TryRead(1 + (c & 3), kMoves, ptr)) continue;
                    ++reads;
                    bool ok = out.d == out.q + 0.5f && out.m == out.q + 0.25f;
                    for (int i = 0; i < kMoves; ++i) ok = ok && out.p[i] == out.q + i;
                    if (!ok) ++torn;
                }
            });
        std::this_thread::sleep_for(std::chrono::milliseconds(600));
        stop = true;
        for (auto& t : threads) t.join();
        std::cout << "  seqlock stress: " << reads.load() << " successful reads, " << torn.load()
                  << " torn" << std::endl;
        EXPECT(reads > 1000, "seqlock stress: only " << reads.load() << " reads succeeded");
        EXPECT(torn == 0, "seqlock stress: " << torn.load() << " torn reads");
    }
}

// ---------------------------------------------------------------------------
// 5. BatchingBackend
// ---------------------------------------------------------------------------
void TestBatching() {
    std::cout << "--- 5. BatchingBackend (6 producers) ---" << std::endl;
    auto positions = MakePositions(48);
    std::vector<lczero::MoveList> legal;
    for (const auto& h : positions) legal.push_back(h->Last().GetBoard().GenerateLegalMoves());
    for (int expected : {8, 2}) {  // 8 > real producers: launches on timeout / full buffer
        lczero::BatchingBackend batching(std::make_unique<fztest::DetBackend>(false, 64, 0),
                                         expected, 300);
        std::atomic<long> wrong{0}, total{0};
        const auto t0 = std::chrono::steady_clock::now();
        std::vector<std::thread> threads;
        for (int t = 0; t < 6; ++t)
            threads.emplace_back([&, t] {
                std::mt19937 rng(100 + t);
                for (int g = 0; g < 120; ++g) {
                    const int n = 1 + static_cast<int>(rng() % 40);  // groups span server rounds
                    std::vector<lczero::EvalResult> res(n);
                    std::vector<size_t> which(n);
                    auto comp = batching.CreateComputation();
                    for (int i = 0; i < n; ++i) {
                        which[i] = rng() % positions.size();
                        res[i].p.resize(legal[which[i]].size());
                        comp->AddInput(lczero::EvalPosition{positions[which[i]].get(),
                                                            std::span<const lczero::Move>(
                                                                legal[which[i]].data(),
                                                                legal[which[i]].size())},
                                       res[i].AsPtr());
                    }
                    comp->ComputeBlocking();
                    for (int i = 0; i < n; ++i) {
                        lczero::EvalResult want;
                        want.p.resize(legal[which[i]].size());
                        fztest::DetFill(fztest::DetKey(positions[which[i]]->Last()), legal[which[i]].size(),
                                        want.AsPtr());
                        bool ok = res[i].q == want.q && res[i].d == want.d;
                        for (size_t m = 0; m < want.p.size(); ++m) ok = ok && res[i].p[m] == want.p[m];
                        if (!ok) ++wrong;
                        ++total;
                    }
                }
            });
        for (auto& th : threads) th.join();
        const double secs =
            std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
        std::cout << "  expected_producers=" << expected << ": " << total.load() << " results, "
                  << wrong.load() << " wrong, " << secs << " s" << std::endl;
        EXPECT(wrong == 0, "BatchingBackend returned " << wrong.load() << " wrong results");
        EXPECT(secs < 60.0, "BatchingBackend took " << secs << " s (stalled?)");
    }
}

// ---------------------------------------------------------------------------
// 6. FillSearchTargets: the root's raw eval, even after its cache entry is gone
// ---------------------------------------------------------------------------
void TestRawRootEval() {
    std::cout << "--- 6. FillSearchTargets: orig_q/policy_kld with an evicted root ---" << std::endl;
    for (int cache_size : {1, 1 << 16}) {  // 1 bucket: the root is always evicted
        fztest::TestSearchOptions so;
        so.parser.GetMutableDefaultsOptions()->Set<int>(lczero::SharedBackendParams::kNNCacheSizeId,
                                                       cache_size);
        auto backend = lczero::CreateMemCache(std::make_unique<fztest::DetBackend>(true, 8, 0),
                                              so.Dict());
        int checked = 0;
        for (const char* fen : {lczero::ChessBoard::kStartposFen,
                                "1r3k2r1/2p4p2/10/4n5/10/10/5B4/10/2P4P2/1R3K2R1 w BIbi - 8+8 0 1",
                                "4k5/3s1s4/10/2P1S1P3/10/10/10/10/10/4K5 b - - 8+8 0 1"}) {
            auto tree = std::make_unique<lczero::classic::NodeTree>();
            tree->ResetToPosition(fen, {});
            for (int move = 0; move < 4; ++move) {
                tree->TrimTreeAtHead();
                fztest::RunTestSearch(tree.get(), backend.get(), so.Dict(), 96, 1);
                lczero::TrainingDataV1 rec;
                std::memset(&rec, 0, sizeof(rec));
                const lczero::Move best =
                    lczero::FillSearchTargets(tree->GetCurrentHead(), tree->GetPositionHistory(),
                                              backend.get(), rec);
                // Expected: DetBackend's evaluation of the root, computed here.
                const auto& h = tree->GetPositionHistory();
                const lczero::MoveList legal = h.Last().GetBoard().GenerateLegalMoves();
                const fztest::DetEval e = fztest::DetValue(fztest::DetKey(h.Last()));
                std::vector<float> prior(legal.size());
                fztest::DetPolicy(fztest::DetKey(h.Last()), legal.size(), prior.data());
                double kld = 0.0;
                for (size_t i = 0; i < legal.size(); ++i) {
                    const float pi = rec.probabilities[lczero::MoveToNNIndex(legal[i], 0)];
                    if (pi > 0.0f) kld += pi * std::log(pi / std::max(1e-12, double(prior[i])));
                }
                EXPECT(rec.orig_q == e.q && rec.orig_d == e.d,
                       "cache " << cache_size << ", " << fen << " move " << move << ": orig_q/d = "
                                << rec.orig_q << "/" << rec.orig_d << ", raw eval " << e.q << "/" << e.d
                                << " (best_q " << rec.best_q << ")");
                EXPECT(std::fabs(rec.policy_kld - kld) < 1e-4,
                       "cache " << cache_size << ": policy_kld " << rec.policy_kld << ", want " << kld);
                ++checked;
                tree->MakeMove(best);
                if (tree->GetPositionHistory().ComputeGameResult() != lczero::GameResult::UNDECIDED)
                    break;
            }
        }
        std::cout << "  cache of " << cache_size << " bucket(s): " << checked << " records checked"
                  << std::endl;
    }
}

}  // namespace

void run_neural_tests(const std::string& weights_path) {
    std::cout << "=== --test-neural: NN layer ===" << std::endl;
    setup_custom_variant();
    Section("1. softmax", TestSoftmax);
    Section("2. helpers", TestHelpers);
    if (std::ifstream(weights_path).good()) {
        Section("3. OnnxBackend", [&] { TestOnnxBackend(weights_path); });
    } else {
        std::cout << "--- 3. [SKIP] OnnxBackend vs ORT: no weights file '" << weights_path
                  << "' (pass --weights <net.onnx>) ---" << std::endl;
    }
    Section("4. cache", TestCache);
    Section("5. batching", TestBatching);
    Section("6. raw root eval", TestRawRootEval);
    if (g_fail) {
        std::cerr << "[FAIL] --test-neural: " << g_fail << " check(s) failed" << std::endl;
        std::exit(1);
    }
    std::cout << "[PASS] --test-neural" << std::endl;
}
