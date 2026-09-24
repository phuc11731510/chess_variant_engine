// Shared scaffolding for the built-in self-tests (src/tests/*.cc).
//
// Every test file includes this header, which reproduces the exact include set
// and `using namespace Stockfish` that the tests were written against when they
// all lived in one engine_tests.cc, plus the tiny mock backend used by the
// search tests when no ONNX weights are available.
#pragma once

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
#include <random>
#include <algorithm>
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
#include "app/search_opts.h"
#include "neural/batching_backend.h"


using namespace Stockfish;

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

// ---------------------------------------------------------------------------
// Deterministic backend for the STRICT search tests (test_search_logic.cc,
// test_history.cc).
//
// Every evaluation is a pure function of the position (DetKey of
// history->Last()), so a test can recompute exactly what the search was told
// about any node and check the tree's bookkeeping against it. DetKey, not the
// Zobrist key: those are drawn anew every run, and a "net" that changed with
// them made the strict tests pass or fail by the seed.
// Unlike MockBackend it:
//   * returns NON-uniform priors and non-zero values, so sign and ordering
//     mistakes are visible instead of cancelling out;
//   * really ENQUEUES and fills results in ComputeBlocking (the path the ONNX
//     backend takes) and, optionally, answers a deterministic subset at once
//     (FETCHED_IMMEDIATELY, the cache-hit path) to exercise out-of-order eval;
//   * is thread-safe in AddInput (atomic slot reservation). lc0's search calls
//     AddInput from several task threads at once, so this is the reference for
//     the BackendComputation contract the real backends must also meet;
//   * lets the test pick runs_on_cpu / batch size (task workers only start for
//     non-CPU backends, so runs_on_cpu=false is how a test reaches that code).
// ---------------------------------------------------------------------------
namespace fztest {

inline uint64_t Mix64(uint64_t x) {  // splitmix64 finalizer
    x += 0x9E3779B97F4A7C15ULL;
    x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9ULL;
    x = (x ^ (x >> 27)) * 0x94D049BB133111EBULL;
    return x ^ (x >> 31);
}

// A position's identity that does not depend on the run's Zobrist seed: the
// fields Hash() covers (pieces, side to move, castling rooks, e.p. squares,
// checks left) mixed with fixed constants. Tests only; not fast.
inline uint64_t DetKey(const lczero::Position& pos) {
    const Stockfish::Position& p = pos.GetBoard().GetRawPosition();
    uint64_t h = Mix64(0xD1B54A32D192ED03ULL + uint64_t(p.side_to_move()));
    for (Stockfish::Bitboard b = p.pieces(); b;) {
        const Stockfish::Square s = Stockfish::pop_lsb(b);
        h = Mix64(h ^ (uint64_t(s) << 16 | uint64_t(p.piece_on(s))));
    }
    for (Stockfish::CastlingRights cr : {Stockfish::WHITE_OO, Stockfish::WHITE_OOO,
                                         Stockfish::BLACK_OO, Stockfish::BLACK_OOO})
        h = Mix64(h ^ (p.can_castle(cr) ? 0x10000ULL + uint64_t(p.castling_rook_square(cr)) : 7ULL));
    for (Stockfish::Bitboard b = p.ep_squares(); b;)
        h = Mix64(h ^ (0x20000ULL + uint64_t(Stockfish::pop_lsb(b))));
    return Mix64(h ^ (uint64_t(p.checks_remaining(Stockfish::WHITE)) << 8 |
                      uint64_t(p.checks_remaining(Stockfish::BLACK))));
}

struct DetEval { float q; float d; };

// q in [-0.9, 0.9] * (1 - d), d in [0, 0.4]: always a valid W/D/L triple.
inline DetEval DetValue(uint64_t key) {
    const uint64_t h = Mix64(key);
    const float d = 0.4f * static_cast<float>(h & 0xFFFF) / 65535.0f;
    const float u = static_cast<float>((h >> 16) & 0xFFFF) / 65535.0f;
    return {0.9f * (1.0f - d) * (2.0f * u - 1.0f), d};
}

// Non-uniform prior over the n legal moves, in GenerateLegalMoves() order.
inline void DetPolicy(uint64_t key, size_t n, float* out) {
    double sum = 0.0;
    for (size_t i = 0; i < n; ++i) {
        out[i] = 1.0f + static_cast<float>(Mix64(key ^ (0x9E3779B1ULL * (i + 1))) % 97);
        sum += out[i];
    }
    for (size_t i = 0; i < n; ++i) out[i] = static_cast<float>(out[i] / sum);
}

inline void DetFill(uint64_t key, size_t n, lczero::EvalResultPtr r) {
    const DetEval e = DetValue(key);
    if (r.q) *r.q = e.q;
    if (r.d) *r.d = e.d;
    if (r.m) *r.m = 0.0f;
    if (!r.p.empty()) DetPolicy(key, std::min(n, r.p.size()), r.p.data());
}

class DetComputation : public lczero::BackendComputation {
public:
    explicit DetComputation(int immediate_mod)
        : immediate_mod_(immediate_mod), slots_(kSlots) {}
    size_t UsedBatchSize() const override {
        return used_.load(std::memory_order_acquire);
    }
    AddInputResult AddInput(const lczero::EvalPosition& pos,
                            lczero::EvalResultPtr result) override {
        const uint64_t key = DetKey(pos.history->Last());
        const size_t n = pos.legal_moves.size();
        if (immediate_mod_ > 0 && Mix64(key ^ 0x5bd1e995ULL) % immediate_mod_ == 0) {
            DetFill(key, n, result);
            return FETCHED_IMMEDIATELY;
        }
        const size_t slot = used_.fetch_add(1, std::memory_order_acq_rel);
        if (slot >= kSlots) throw std::runtime_error("DetComputation: too many inputs");
        slots_[slot] = Slot{key, n, result};
        return ENQUEUED_FOR_EVAL;
    }
    void ComputeBlocking() override {
        const size_t n = used_.load(std::memory_order_acquire);
        for (size_t i = 0; i < n; ++i) DetFill(slots_[i].key, slots_[i].n, slots_[i].result);
        used_.store(0, std::memory_order_release);
    }
private:
    static constexpr size_t kSlots = 1024;
    struct Slot { uint64_t key = 0; size_t n = 0; lczero::EvalResultPtr result; };
    const int immediate_mod_;
    std::atomic<size_t> used_{0};
    std::vector<Slot> slots_;
};

class DetBackend : public lczero::Backend {
public:
    // immediate_mod > 0: about 1/immediate_mod of the positions are answered
    // at once (FETCHED_IMMEDIATELY), the rest are enqueued.
    DetBackend(bool runs_on_cpu, int batch, int immediate_mod)
        : runs_on_cpu_(runs_on_cpu), batch_(batch), immediate_mod_(immediate_mod) {}
    lczero::BackendAttributes GetAttributes() const override {
        return lczero::BackendAttributes{
            .has_mlh = false,
            .has_wdl = true,
            .runs_on_cpu = runs_on_cpu_,
            .suggested_num_search_threads = 1,
            .recommended_batch_size = batch_,
            .maximum_batch_size = 4 * batch_};
    }
    std::unique_ptr<lczero::BackendComputation> CreateComputation() override {
        return std::make_unique<DetComputation>(immediate_mod_);
    }
private:
    const bool runs_on_cpu_;
    const int batch_;
    const int immediate_mod_;
};

// Owns the OptionsParser whose dictionary a Search reads. The dictionary is a
// reference into the parser, so this object must outlive every Search built
// from it. Starts from the self-play baseline with noise OFF.
struct TestSearchOptions {
    lczero::OptionsParser parser;
    TestSearchOptions() {
        lczero::classic::SearchParams::Populate(&parser);
        auto* d = parser.GetMutableDefaultsOptions();
        d->Set<float>(lczero::SharedBackendParams::kPolicySoftmaxTemp, 1.0f);
        d->Set<std::string>(lczero::SharedBackendParams::kHistoryFill, "no");
        d->Set<float>(lczero::classic::BaseSearchParams::kNoiseEpsilonId, 0.0f);
    }
    // Same names as `--search-opt name=value`; aborts on an unknown name.
    void Set(const std::string& name, const std::string& value) {
        if (!ApplySearchOpt(parser.GetMutableDefaultsOptions(), name, value)) {
            std::cerr << "[FAIL] test setup: unknown search option " << name << std::endl;
            std::exit(1);
        }
    }
    void SetNoise(float eps, float alpha) {
        auto* d = parser.GetMutableDefaultsOptions();
        d->Set<float>(lczero::classic::BaseSearchParams::kNoiseEpsilonId, eps);
        d->Set<float>(lczero::classic::BaseSearchParams::kNoiseAlphaId, alpha);
    }
    const lczero::OptionsDict& Dict() { return parser.GetOptionsDict(); }
};

// Runs one search on the tree's current head until `playouts` NEW playouts.
inline void RunTestSearch(lczero::classic::NodeTree* tree, lczero::Backend* backend,
                          const lczero::OptionsDict& options, int playouts,
                          int threads) {
    auto search = std::make_unique<lczero::classic::Search>(
        *tree, backend, std::make_unique<SilentUciResponder>(), lczero::MoveList{},
        std::chrono::steady_clock::now(),
        std::make_unique<PlayoutCountStopper>(playouts), false, false, options,
        nullptr);
    search->RunBlocking(threads);
}

// Real-board UCI string of a canonical move played from `history.Last()`.
inline std::string MoveUci(const lczero::PositionHistory& history, lczero::Move m) {
    return CanonicalMoveToUci(m, history.IsBlackToMove());
}

// Canonical move from a real-board UCI string, or a null move if not legal.
inline lczero::Move ParseLegalMove(const lczero::PositionHistory& history,
                                   const std::string& uci) {
    for (const auto& m : history.Last().GetBoard().GenerateLegalMoves()) {
        if (MoveUci(history, m) == uci) return m;
    }
    return lczero::Move();
}

}  // namespace fztest
