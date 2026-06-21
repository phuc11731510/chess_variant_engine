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
#include "app/variant_setup.h"
#include "app/backend_factory.h"
#include "app/uci_coords.h"
#include "app/search_opts.h"
#include "app/search_support.h"
#include "tests/engine_tests.h"

using namespace Stockfish;


void run_arena(const std::string& model_a, const std::string& model_b, int games,
               int visits, int max_moves, int temp_cutoff,
               const std::string& provider, int fixed_batch) {
    std::cout << "\n=== ARENA: A=" << model_a << "  vs  B=" << model_b
              << "  (" << games << " games, visits=" << visits << ") ===" << std::endl;
    setup_custom_variant();
    const std::string fen =
        "vrhabkberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHABKBERV w BIbi - 7+7 0 1";

    auto build_opts = [&](lczero::OptionsParser& parser, const std::string& weights) {
        lczero::classic::SearchParams::Populate(&parser);
        parser.GetMutableDefaultsOptions()->Set<float>(lczero::SharedBackendParams::kPolicySoftmaxTemp, 1.0f);
        parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kHistoryFill, "no");
        parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kNoiseEpsilonId, 0.0f);
        parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kWeightsId, weights);
        const std::string bopts = (provider == "cuda")
            ? "provider=cuda,fixed_batch=" + std::to_string(std::max(1, fixed_batch))
            : "threads=1";
        parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kBackendOptionsId, bopts);
    };

    lczero::OptionsParser pa, pb;
    build_opts(pa, model_a);
    build_opts(pb, model_b);
    const lczero::OptionsDict& opts_a = pa.GetOptionsDict();
    const lczero::OptionsDict& opts_b = pb.GetOptionsDict();

    std::unique_ptr<lczero::Backend> ba, bb;
    try {
        ba = arena_make_backend(opts_a);
        bb = arena_make_backend(opts_b);
    } catch (const std::exception& e) {
        std::cerr << "[arena] backend load failed: " << e.what() << std::endl;
        std::exit(1);
    }

    int a_wins = 0, b_wins = 0, draws = 0;
    auto tree = std::make_unique<lczero::classic::NodeTree>();

    for (int g = 0; g < games; ++g) {
        const bool a_is_white = (g % 2 == 0);            // alternate colors for fairness
        tree->ResetToPosition(fen, {});
        lczero::GameResult result = lczero::GameResult::UNDECIDED;

        for (int ply = 0; ply < max_moves; ++ply) {
            const bool white_to_move = !tree->IsBlackToMove();
            const bool a_to_move = (white_to_move == a_is_white);
            lczero::Backend* backend = a_to_move ? ba.get() : bb.get();
            const lczero::OptionsDict& sopts = a_to_move ? opts_a : opts_b;

            tree->TrimTreeAtHead();  // fresh search: no stale evals from the OTHER net
            auto responder = std::make_unique<SilentUciResponder>();
            auto stopper = std::make_unique<NodeLimitStopper>(visits);
            auto start = std::chrono::steady_clock::now();
            auto search = std::make_unique<lczero::classic::Search>(
                *tree, backend, std::move(responder), lczero::MoveList{}, start,
                std::move(stopper), false, false, sopts, nullptr);
            search->RunBlocking(1);

            lczero::classic::Node* root = tree->GetCurrentHead();
            lczero::classic::EdgeAndNode best;
            uint64_t total = 0, best_n = 0;
            for (const auto& e : root->Edges()) {
                total += e.GetN();
                if (e.GetN() >= best_n) { best_n = e.GetN(); best = e; }
            }
            if (best.GetMove().is_null()) break;

            lczero::Move played = best.GetMove();           // greedy by default
            if (ply < temp_cutoff && total > 0) {           // temperature opening for diversity
                const double toss = lczero::Random::Get().GetDouble(static_cast<double>(total));
                double acc = 0.0;
                for (const auto& e : root->Edges()) {
                    acc += static_cast<double>(e.GetN());
                    if (acc > toss) { played = e.GetMove(); break; }
                }
            }
            tree->MakeMove(played);
            result = tree->GetPositionHistory().ComputeGameResult();
            if (result != lczero::GameResult::UNDECIDED) break;
        }

        if (result == lczero::GameResult::WHITE_WON || result == lczero::GameResult::BLACK_WON) {
            const bool white_won = (result == lczero::GameResult::WHITE_WON);
            if (white_won == a_is_white) a_wins++; else b_wins++;
        } else {
            draws++;  // DRAW or cutoff (UNDECIDED)
        }
        std::cout << "  game " << (g + 1) << "/" << games << " (A plays "
                  << (a_is_white ? "White" : "Black") << "): result=" << (int)result
                  << "   [A " << a_wins << " W / " << draws << " D / " << b_wins << " L]" << std::endl;
    }

    const double score_a = (a_wins + 0.5 * draws) / std::max(1, games);
    std::cout << "\n=== ARENA RESULT ===" << std::endl;
    std::cout << "  A wins=" << a_wins << "  draws=" << draws << "  B wins=" << b_wins << std::endl;
    std::cout << "  A score = " << score_a << "  (>0.5 => A stronger than B)" << std::endl;
}

// ============================================================================
// T8.1 — UCI engine driving MCTS + ONNX (the "real" AlphaZero engine, terminal).
// ============================================================================

// Variant startpos (same as arena/self-play).
class InfiniteStopper : public lczero::classic::SearchStopper {
public:
    bool ShouldStop(const lczero::classic::IterationStats&, lczero::classic::StoppersHints*) override {
        return false;
    }
    void OnSearchDone(const lczero::classic::IterationStats&) override {}
};

// Stopper by NEW playouts this search (nodes_since_movestart) — matches the
// self-play PlayoutStopper, which is proven to drive a real multi-playout search
// (NodeLimitStopper's total_nodes = playouts + initial_visits can mis-fire).
class PlayoutCountStopper : public lczero::classic::SearchStopper {
public:
    explicit PlayoutCountStopper(int64_t max_new) : max_new_(max_new) {}
    bool ShouldStop(const lczero::classic::IterationStats& s, lczero::classic::StoppersHints*) override {
        return s.nodes_since_movestart >= max_new_;
    }
    void OnSearchDone(const lczero::classic::IterationStats&) override {}
private:
    int64_t max_new_;
};

// Stopper that fires after a wall-clock budget (for `go movetime`).
class TimeStopper : public lczero::classic::SearchStopper {
public:
    explicit TimeStopper(int64_t ms)
        : deadline_(std::chrono::steady_clock::now() + std::chrono::milliseconds(ms)) {}
    bool ShouldStop(const lczero::classic::IterationStats&, lczero::classic::StoppersHints*) override {
        return std::chrono::steady_clock::now() >= deadline_;
    }
    void OnSearchDone(const lczero::classic::IterationStats&) override {}
private:
    std::chrono::steady_clock::time_point deadline_;
};

// q in [-1,1] (side-to-move win-loss) -> UCI centipawns (lc0 logistic mapping).
static int QToCp(float q) {
    q = std::max(-0.9999f, std::min(0.9999f, q));
    double cp = 111.714640912 * std::tan(1.5620688421 * static_cast<double>(q));
    cp = std::max(-12000.0, std::min(12000.0, cp));
    return static_cast<int>(std::lround(cp));
}
// q (win-loss) + d (draw) -> WDL permille (w+d+l == 1000), side-to-move POV.
static void WdlPermille(float q, float d, int& w, int& dr, int& l) {
    float ww = (q + 1.0f - d) / 2.0f, ll = (1.0f - d - q) / 2.0f, dd = d;
    ww = std::max(0.0f, std::min(1.0f, ww));
    ll = std::max(0.0f, std::min(1.0f, ll));
    dd = std::max(0.0f, std::min(1.0f, dd));
    float s = ww + dd + ll;
    if (s <= 1e-6f) { w = 0; dr = 1000; l = 0; return; }
    w = static_cast<int>(std::lround(ww / s * 1000.0f));
    l = static_cast<int>(std::lround(ll / s * 1000.0f));
    dr = 1000 - w - l;
}

// Real UciResponder: forwards lc0's periodic search stats as UCI `info` lines
// (scalars only; the PV is added by our own final info, computed when the tree
// is stable). Runs on lc0's thread; output is serialized by the engine's Send.
class UciInfoResponder : public lczero::UciResponder {
public:
    explicit UciInfoResponder(std::function<void(const std::string&)> send)
        : send_(std::move(send)) {}
    void OutputBestMove(lczero::BestMoveInfo*) override {}   // we emit bestmove ourselves
    void OutputThinkingInfo(std::vector<lczero::ThinkingInfo>* infos) override {
        for (const auto& ti : *infos) {
            std::ostringstream os;
            os << "info";
            if (ti.depth >= 0)    os << " depth " << ti.depth;
            if (ti.seldepth >= 0) os << " seldepth " << ti.seldepth;
            if (ti.multipv >= 0)  os << " multipv " << ti.multipv;
            if (ti.score)         os << " score cp " << *ti.score;
            if (ti.wdl)           os << " wdl " << ti.wdl->w << " " << ti.wdl->d << " " << ti.wdl->l;
            if (ti.nodes >= 0)    os << " nodes " << ti.nodes;
            if (ti.nps >= 0)      os << " nps " << ti.nps;
            if (ti.time >= 0)     os << " time " << ti.time;
            if (ti.hashfull >= 0) os << " hashfull " << ti.hashfull;
            send_(os.str());
        }
    }
private:
    std::function<void(const std::string&)> send_;
};

// T8.3 — passthrough of lc0 search params: maps a UCI/lc0 option NAME + string
// value into the OptionsDict. Returns false for names it doesn't handle (so the
// caller can ignore unknowns). Curated high-value set; extend by adding cases.
static lczero::classic::EdgeAndNode SampleByTemperature(
    const std::vector<lczero::classic::EdgeAndNode>& edges, int temp_permille) {
    if (temp_permille <= 0 || edges.empty()) return edges.empty() ? lczero::classic::EdgeAndNode() : edges[0];
    const double T = std::min(10.0, std::max(0.01, temp_permille / 1000.0));
    std::vector<double> w(edges.size());
    double total = 0.0;
    for (size_t i = 0; i < edges.size(); ++i) {
        w[i] = std::pow(static_cast<double>(edges[i].GetN()) + 1e-9, 1.0 / T);
        total += w[i];
    }
    if (total <= 0.0) return edges[0];
    double toss = lczero::Random::Get().GetDouble(total), acc = 0.0;
    for (size_t i = 0; i < edges.size(); ++i) { acc += w[i]; if (acc > toss) return edges[i]; }
    return edges.back();
}

// UCI engine state machine. One search runs on a worker thread (U1.8a) so the
// main thread keeps reading stdin and can deliver `stop`/`quit` immediately.
class UciNnEngine {
public:
    UciNnEngine(std::string weights, std::string provider, int fixed_batch)
        : weights_(std::move(weights)), provider_(std::move(provider)), fixed_batch_(fixed_batch) {
        tree_ = std::make_unique<lczero::classic::NodeTree>();
        tree_->ResetToPosition(kUciStartFen, {});
    }
    ~UciNnEngine() { StopSearch(); }

    void Loop() {
        std::string line;
        while (std::getline(std::cin, line)) {
            ReapIfDone();
            std::istringstream is(line);
            std::string cmd;
            if (!(is >> cmd)) continue;            // blank line -> ignore (robustness)
            if (cmd == "uci") {
                HandleUci();
            } else if (cmd == "isready") {
                EnsureBackend();                   // sync: only ready AFTER (re)build
                Send("readyok");
            } else if (cmd == "setoption") {
                HandleSetOption(is);
            } else if (cmd == "ucinewgame") {
                StopSearch();
                tree_ = std::make_unique<lczero::classic::NodeTree>();  // free old tree (U1.8c)
                tree_->ResetToPosition(kUciStartFen, {});
                current_startfen_.clear(); current_moves_.clear();
            } else if (cmd == "position") {
                StopSearch();
                HandlePosition(is);
            } else if (cmd == "go") {
                HandleGo(is);
            } else if (cmd == "stop") {
                StopSearch();                      // emits bestmove (U1.8a)
            } else if (cmd == "ponderhit") {
                // Predicted move was played: finalize the ponder search now
                // (basic ponder — returns the move found while pondering).
                StopSearch();
            } else if (cmd == "debug" || cmd == "register") {
                // Accept & ignore (robustness).
            } else if (cmd == "quit") {
                AbortSearch();
                break;
            }
            // Unknown commands are ignored per the UCI spec.
        }
    }

private:
    void Send(const std::string& s) {
        std::lock_guard<std::mutex> lk(io_mu_);
        std::cout << s << "\n" << std::flush;
    }

    void HandleUci() {
        Send("id name FairyZero (10x10 MCTS+NN)");
        Send("id author FairyZero");
        Send("option name WeightsFile type string default " + weights_);
        Send("option name Visits type spin default 800 min 1 max 100000000");
        Send("option name Provider type combo default cpu var cpu var cuda");
        Send("option name FixedBatch type spin default 16 min 1 max 1024");
        Send("option name Threads type spin default 1 min 1 max 256");
        Send("option name BackendThreads type spin default 1 min 1 max 256");
        Send("option name PolicySoftmaxTemp type string default 1.359");
        Send("option name MoveOverheadMs type spin default 30 min 0 max 10000");
        Send("option name MultiPV type spin default 1 min 1 max 64");
        Send("option name Ponder type check default false");
        Send("option name Temperature type spin default 0 min 0 max 10000");   // permille; difficulty
        Send("option name TempCutoffPly type spin default 0 min 0 max 1000");   // temp only first N plies (0=always)
        Send("option name ReuseTree type check default true");                  // keep MCTS tree across moves
        // Plus any lc0 search param by its native name (T8.3 passthrough), e.g.:
        // setoption name cpuct value 2.0 ; setoption name draw-score value -0.2
        Send("uciok");
    }

    // setoption name <Name> [value <Val>]
    void HandleSetOption(std::istringstream& is) {
        std::string tok, name, value;
        bool in_value = false;
        while (is >> tok) {
            if (tok == "name") continue;
            if (tok == "value") { in_value = true; continue; }
            if (in_value) value += (value.empty() ? "" : " ") + tok;
            else name += (name.empty() ? "" : " ") + tok;
        }
        auto to_int = [&](int def) { try { return std::stoi(value); } catch (...) { return def; } };
        if (name == "WeightsFile") { if (!value.empty()) { weights_ = value; backend_dirty_ = true; } }
        else if (name == "Provider") { if (!value.empty()) { provider_ = value; backend_dirty_ = true; } }
        else if (name == "FixedBatch") { fixed_batch_ = to_int(fixed_batch_); backend_dirty_ = true; }
        else if (name == "BackendThreads") { backend_threads_ = to_int(backend_threads_); backend_dirty_ = true; }
        else if (name == "PolicySoftmaxTemp") { try { policy_temp_ = std::stof(value); backend_dirty_ = true; } catch (...) {} }
        else if (name == "Visits") { default_visits_ = to_int(default_visits_); }
        else if (name == "Threads") { search_threads_ = std::max(1, to_int(search_threads_)); }
        else if (name == "MoveOverheadMs") { move_overhead_ms_ = std::max(0, to_int(move_overhead_ms_)); }
        else if (name == "MultiPV") { multipv_ = std::max(1, to_int(multipv_)); }
        else if (name == "Ponder") { /* accepted; ponder activated via `go ponder` */ }
        else if (name == "Temperature") { temperature_ = std::max(0, to_int(temperature_)); }
        else if (name == "TempCutoffPly") { temp_cutoff_ply_ = std::max(0, to_int(temp_cutoff_ply_)); }
        else if (name == "ReuseTree") { reuse_tree_ = (value == "true" || value == "1"); }
        else if (!name.empty()) { search_opts_[name] = value; }  // lc0 search-param passthrough (applied at `go`)
        // Unknown / unmatched names are silently ignored at `go` (robustness).
    }

    // position [startpos | fen <FEN...>] [moves <m1> <m2> ...]
    void HandlePosition(std::istringstream& is) {
        std::string tok;
        if (!(is >> tok)) return;
        std::string fen;
        if (tok == "startpos") {
            fen = kUciStartFen;
            is >> tok;                              // consume optional "moves"
        } else if (tok == "fen") {
            std::vector<std::string> parts;
            while (is >> tok && tok != "moves") parts.push_back(tok);
            for (size_t i = 0; i < parts.size(); ++i) fen += (i ? " " : "") + parts[i];
        } else {
            return;                                 // malformed
        }
        std::vector<std::string> moves;
        if (tok == "moves") { std::string mv; while (is >> mv) moves.push_back(mv); }

        // --- T8.x: tree reuse. If the new line is the SAME start + an EXTENSION
        // of the moves we already applied, advance the existing tree (keeping the
        // already-searched subtree's visit stats) instead of rebuilding cold. ---
        bool reused = false;
        if (reuse_tree_ && tree_ && !current_startfen_.empty() && fen == current_startfen_ &&
            moves.size() >= current_moves_.size() &&
            std::equal(current_moves_.begin(), current_moves_.end(), moves.begin())) {
            bool ok = true;
            for (size_t k = current_moves_.size(); k < moves.size(); ++k) {
                const bool black = tree_->IsBlackToMove();
                const auto& board = tree_->GetPositionHistory().Last().GetBoard();
                lczero::Move m = UciToCanonicalMove(board, moves[k], black);
                if (m.is_null()) { ok = false; break; }
                tree_->MakeMove(m);                 // descends into child subtree (keeps visits)
            }
            if (ok) { tree_->TrimTreeAtHead(); reused = true; }  // free non-head branches
        }

        if (!reused) {                              // rebuild a fresh tree
            tree_ = std::make_unique<lczero::classic::NodeTree>();
            try {
                tree_->ResetToPosition(fen, {});    // bool = tree-reuse flag, not success
            } catch (const std::exception& e) {
                Send(std::string("info string bad FEN, using startpos: ") + e.what());
                tree_->ResetToPosition(kUciStartFen, {});
                current_startfen_.clear(); current_moves_.clear();
                return;
            }
            for (const std::string& mv : moves) {
                const bool black = tree_->IsBlackToMove();
                const auto& board = tree_->GetPositionHistory().Last().GetBoard();
                lczero::Move m = UciToCanonicalMove(board, mv, black);
                if (m.is_null()) break;             // illegal/unknown move: stop applying
                tree_->MakeMove(m);
            }
        }
        current_startfen_ = fen;
        current_moves_ = moves;
    }

    // go [nodes N | movetime ms | infinite | depth d | wtime/btime/winc/binc/movestogo |
    //     searchmoves m... | ponder]
    void HandleGo(std::istringstream& is) {
        StopSearch();
        if (!EnsureBackend()) { Send("bestmove 0000"); return; }
        int64_t nodes = 0, movetime = 0, wtime = 0, btime = 0, winc = 0, binc = 0, movestogo = 0;
        bool infinite = false, ponder = false;
        lczero::MoveList searchmoves;
        std::string tok;
        while (is >> tok) {
            if (tok == "nodes") is >> nodes;
            else if (tok == "movetime") is >> movetime;
            else if (tok == "wtime") is >> wtime;
            else if (tok == "btime") is >> btime;
            else if (tok == "winc") is >> winc;
            else if (tok == "binc") is >> binc;
            else if (tok == "movestogo") is >> movestogo;
            else if (tok == "infinite") infinite = true;
            else if (tok == "ponder") ponder = true;
            else if (tok == "depth" || tok == "mate") { std::string ign; is >> ign; }
            else if (tok == "searchmoves") {
                // the rest of the line is a list of moves (real coords)
                const bool black = tree_->IsBlackToMove();
                const auto& board = tree_->GetPositionHistory().Last().GetBoard();
                std::string mv;
                while (is >> mv) {
                    lczero::Move m = UciToCanonicalMove(board, mv, black);
                    if (!m.is_null()) searchmoves.push_back(m);
                }
            }
            // unknown go-params ignored
        }

        // --- time management: pick a budget for the side to move (U1.5) ---
        const bool root_black = tree_->IsBlackToMove();
        int64_t budget_ms = 0;
        if (movetime > 0) {
            budget_ms = movetime;
        } else if (wtime > 0 || btime > 0) {
            const int64_t mytime = root_black ? btime : wtime;
            const int64_t myinc  = root_black ? binc : winc;
            const int mtg = movestogo > 0 ? movestogo : 30;   // assume ~30 moves left
            budget_ms = mytime / mtg + static_cast<int64_t>(myinc * 0.8);
        }
        if (budget_ms > 0) budget_ms = std::max<int64_t>(1, budget_ms - move_overhead_ms_);

        std::unique_ptr<lczero::classic::SearchStopper> stopper;
        const bool no_stop = infinite || ponder;              // run until stop/ponderhit
        if (no_stop)            stopper = std::make_unique<InfiniteStopper>();
        else if (budget_ms > 0) stopper = std::make_unique<TimeStopper>(budget_ms);
        else                    stopper = std::make_unique<PlayoutCountStopper>(nodes > 0 ? nodes : default_visits_);

        // Apply MultiPV + any lc0 search-param passthrough (no backend rebuild).
        auto* od = parser_->GetMutableDefaultsOptions();
        od->Set<int>(lczero::classic::SearchParams::kMultiPvId, std::max(1, multipv_));
        for (const auto& kv : search_opts_) ApplySearchOpt(od, kv.first, kv.second);

        auto responder = std::make_unique<UciInfoResponder>(
            [this](const std::string& s) { Send(s); });      // periodic info
        search_start_ = std::chrono::steady_clock::now();
        search_ = std::make_unique<lczero::classic::Search>(
            *tree_, backend_.get(), std::move(responder), searchmoves,
            search_start_, std::move(stopper), no_stop,
            /*ponder=*/ponder, parser_->GetOptionsDict(), nullptr);
        searching_.store(true);
        const int threads = search_threads_;
        search_thread_ = std::thread([this, threads]() {
            search_->RunBlocking(threads);     // blocks until stopper fires OR Stop()
            EmitBestMove();
            searching_.store(false);
        });
    }

    // Builds a principal-variation string (real coords) by following the
    // max-visit child chain from `first`. `black` = side-to-move at `first`.
    // Safe to call only when the tree is stable (workers joined). Returns the
    // number of plies via `out_len`.
    std::string ComputePvUci(lczero::classic::EdgeAndNode first, bool black,
                             int maxlen, int* out_len) {
        std::string pv;
        int len = 0;
        lczero::classic::EdgeAndNode e = first;
        while (!e.GetMove().is_null() && len < maxlen) {
            if (!pv.empty()) pv += " ";
            pv += CanonicalMoveToUci(e.GetMove(), black);
            ++len;
            lczero::classic::Node* child = e.node();
            if (!child || child->GetN() == 0) break;
            lczero::classic::EdgeAndNode bestc;
            uint64_t bn = 0;
            for (const auto& ce : child->Edges()) if (ce.GetN() >= bn) { bn = ce.GetN(); bestc = ce; }
            if (bestc.GetMove().is_null()) break;
            e = bestc;
            black = !black;
        }
        if (out_len) *out_len = len;
        return pv;
    }

    void EmitBestMove() {
        lczero::classic::Node* root = tree_ ? tree_->GetCurrentHead() : nullptr;
        if (!root) { Send("bestmove 0000"); return; }
        const bool root_black = tree_->IsBlackToMove();

        // Root edges sorted by visits (best first).
        std::vector<lczero::classic::EdgeAndNode> edges;
        for (const auto& e : root->Edges()) edges.push_back(e);
        std::sort(edges.begin(), edges.end(),
                  [](const lczero::classic::EdgeAndNode& a, const lczero::classic::EdgeAndNode& b) {
                      return a.GetN() > b.GetN();
                  });
        if (edges.empty() || edges[0].GetMove().is_null()) { Send("bestmove 0000"); return; }

        const int64_t nodes = static_cast<int64_t>(root->GetN());
        const int64_t ms = std::max<int64_t>(1,
            std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::steady_clock::now() - search_start_).count());
        const int64_t nps = nodes * 1000 / ms;
        const int K = std::min<int>(std::max(1, multipv_), static_cast<int>(edges.size()));

        // Final `info` lines (one per MultiPV; multipv 1 = best move). These carry
        // the PV (computed safely now that workers have joined).
        for (int i = K - 1; i >= 0; --i) {
            // Value of PLAYING edges[i], from our perspective: negate child's WL.
            const float q = -edges[i].GetWL(static_cast<float>(-root->GetWL()));
            const float d = edges[i].GetD(root->GetD());
            int w, dr, l; WdlPermille(q, d, w, dr, l);
            int pvlen = 0;
            const std::string pv = ComputePvUci(edges[i], root_black, 24, &pvlen);
            std::ostringstream os;
            os << "info depth " << pvlen << " multipv " << (i + 1)
               << " score cp " << QToCp(q) << " wdl " << w << " " << dr << " " << l
               << " nodes " << nodes << " nps " << nps << " time " << ms
               << " pv " << pv;
            Send(os.str());
        }

        // Move selection: greedy (best) by default; with Temperature>0 (and within
        // TempCutoffPly) sample by visit counts -> weaker/more varied (difficulty).
        lczero::classic::EdgeAndNode chosen = edges[0];
        const int ply = static_cast<int>(tree_->GetPositionHistory().GetPositions().size()) - 1;
        if (temperature_ > 0 && (temp_cutoff_ply_ == 0 || ply < temp_cutoff_ply_)) {
            chosen = SampleByTemperature(edges, temperature_);
        }

        // bestmove (+ ponder = the predicted reply = 2nd move of the chosen line).
        std::string out = "bestmove " + CanonicalMoveToUci(chosen.GetMove(), root_black);
        lczero::classic::Node* child = chosen.node();
        if (child && child->GetN() > 0) {
            lczero::classic::EdgeAndNode pe; uint64_t pn = 0;
            for (const auto& ce : child->Edges()) if (ce.GetN() >= pn) { pn = ce.GetN(); pe = ce; }
            if (!pe.GetMove().is_null())
                out += " ponder " + CanonicalMoveToUci(pe.GetMove(), !root_black);
        }
        Send(out);
    }

    bool EnsureBackend() {
        if (!backend_dirty_ && backend_) return true;
        parser_ = std::make_unique<lczero::OptionsParser>();
        lczero::classic::SearchParams::Populate(parser_.get());
        auto* d = parser_->GetMutableDefaultsOptions();
        d->Set<float>(lczero::SharedBackendParams::kPolicySoftmaxTemp, policy_temp_);
        d->Set<std::string>(lczero::SharedBackendParams::kHistoryFill, "no");
        d->Set<float>(lczero::classic::BaseSearchParams::kNoiseEpsilonId, 0.0f);  // play hard: no noise
        d->Set<std::string>(lczero::SharedBackendParams::kWeightsId, weights_);
        const std::string bopts = (provider_ == "cuda")
            ? "provider=cuda,fixed_batch=" + std::to_string(std::max(1, fixed_batch_))
            : "threads=" + std::to_string(std::max(1, backend_threads_));
        d->Set<std::string>(lczero::SharedBackendParams::kBackendOptionsId, bopts);
        try {
            backend_ = arena_make_backend(parser_->GetOptionsDict());
            backend_dirty_ = false;
            return true;
        } catch (const std::exception& e) {
            backend_.reset();
            Send(std::string("info string failed to load backend: ") + e.what());
            return false;
        }
    }

    void StopSearch() {        // graceful: stop + reap (also emits bestmove)
        if (search_ && searching_.load()) search_->Stop();
        if (search_thread_.joinable()) search_thread_.join();
        search_.reset();
        searching_.store(false);
    }
    void AbortSearch() {       // quit: no bestmove
        if (search_ && searching_.load()) search_->Abort();
        if (search_thread_.joinable()) search_thread_.join();
        search_.reset();
        searching_.store(false);
    }
    void ReapIfDone() {        // join a search that self-terminated (nodes/movetime)
        if (search_thread_.joinable() && !searching_.load()) {
            search_thread_.join();
            search_.reset();
        }
    }

    std::string weights_, provider_;
    int fixed_batch_;
    int backend_threads_ = 1, search_threads_ = 1;
    int default_visits_ = 800, move_overhead_ms_ = 30, multipv_ = 1;
    int temperature_ = 0, temp_cutoff_ply_ = 0;   // difficulty: move-selection temperature (permille)
    bool reuse_tree_ = true;                       // keep MCTS tree across moves (T8.x)
    float policy_temp_ = 1.359f;                    // lc0 default (PolicySoftmaxTemp)
    bool backend_dirty_ = true;
    std::chrono::steady_clock::time_point search_start_;
    std::string current_startfen_;                 // for tree-reuse prefix matching
    std::vector<std::string> current_moves_;
    std::map<std::string, std::string> search_opts_;  // lc0 search-param passthrough (T8.3)

    std::unique_ptr<lczero::OptionsParser> parser_;
    std::unique_ptr<lczero::Backend> backend_;
    std::unique_ptr<lczero::classic::NodeTree> tree_;
    std::unique_ptr<lczero::classic::Search> search_;
    std::thread search_thread_;
    std::atomic<bool> searching_{false};
    std::mutex io_mu_;
};

void run_uci_nn(const std::string& weights, const std::string& provider, int fixed_batch) {
    setup_custom_variant();
    UciNnEngine engine(weights, provider, fixed_batch);
    engine.Loop();
}

// --play: a minimal ASCII terminal game vs the MCTS+NN engine (T8.x). For quick
// human testing without a GUI; the real interface is --uci-nn.
static void PrintAsciiBoard(const Stockfish::Position& pos) {
    auto pc_char = [](Stockfish::Piece pc) -> char {
        char c = '?';
        switch (Stockfish::type_of(pc)) {
            case Stockfish::PAWN: c='p';break;        case Stockfish::KNIGHT: c='n';break;
            case Stockfish::BISHOP: c='b';break;      case Stockfish::ROOK: c='r';break;
            case Stockfish::QUEEN: c='q';break;        case Stockfish::KING: c='k';break;
            case Stockfish::AMAZON: c='a';break;       case Stockfish::CHANCELLOR: c='e';break;
            case Stockfish::ARCHBISHOP: c='h';break;   case Stockfish::CENTAUR: c='m';break;
            case Stockfish::CUSTOM_PIECE_1: c='v';break; case Stockfish::CUSTOM_PIECE_2: c='y';break;
            case Stockfish::CUSTOM_PIECE_3: c='s';break; default: break;
        }
        return (Stockfish::color_of(pc) == Stockfish::WHITE) ? static_cast<char>(c - 32) : c;
    };
    std::cout << "\n      a  b  c  d  e  f  g  h  i  j\n";
    for (int r = 9; r >= 0; --r) {
        std::cout << "  " << (r + 1 < 10 ? " " : "") << (r + 1) << " ";
        for (int f = 0; f < 10; ++f) {
            Stockfish::Piece pc = pos.piece_on(static_cast<Stockfish::Square>(r * 12 + f));
            std::cout << " " << (pc == Stockfish::NO_PIECE ? '.' : pc_char(pc)) << " ";
        }
        std::cout << "\n";
    }
    std::cout << std::endl;
}

void run_play(const std::string& weights, const std::string& provider, int fixed_batch,
              int visits, bool human_white) {
    setup_custom_variant();
    lczero::OptionsParser parser;
    lczero::classic::SearchParams::Populate(&parser);
    auto* d = parser.GetMutableDefaultsOptions();
    d->Set<float>(lczero::SharedBackendParams::kPolicySoftmaxTemp, 1.359f);  // lc0 default
    d->Set<std::string>(lczero::SharedBackendParams::kHistoryFill, "no");
    d->Set<float>(lczero::classic::BaseSearchParams::kNoiseEpsilonId, 0.0f);
    d->Set<std::string>(lczero::SharedBackendParams::kWeightsId, weights);
    d->Set<std::string>(lczero::SharedBackendParams::kBackendOptionsId,
        provider == "cuda" ? "provider=cuda,fixed_batch=" + std::to_string(std::max(1, fixed_batch))
                           : "threads=1");
    std::unique_ptr<lczero::Backend> backend;
    try { backend = arena_make_backend(parser.GetOptionsDict()); }
    catch (const std::exception& e) { std::cerr << "[play] backend load failed: " << e.what() << std::endl; return; }
    const lczero::OptionsDict& opts = parser.GetOptionsDict();

    auto tree = std::make_unique<lczero::classic::NodeTree>();
    tree->ResetToPosition(kUciStartFen, {});
    std::cout << "\n=== FairyZero --play (visits=" << visits << ") ===\n"
              << "You are " << (human_white ? "WHITE (uppercase, bottom)" : "BLACK (lowercase, top)")
              << ". Enter moves like 'b3b4' (promotion 'a9a10v'); type 'quit' to exit." << std::endl;

    lczero::GameResult result = lczero::GameResult::UNDECIDED;
    while (result == lczero::GameResult::UNDECIDED) {
        const Stockfish::Position& pos = tree->GetPositionHistory().Last().GetBoard().GetRawPosition();
        PrintAsciiBoard(pos);
        const bool black_to_move = tree->IsBlackToMove();
        const bool human_turn = ((!black_to_move) == human_white);
        if (human_turn) {
            std::cout << "Your move: " << std::flush;
            std::string mv;
            if (!std::getline(std::cin, mv)) break;
            if (mv == "quit" || mv == "q") break;
            // strip whitespace
            while (!mv.empty() && (mv.back() == '\r' || mv.back() == ' ')) mv.pop_back();
            const auto& board = tree->GetPositionHistory().Last().GetBoard();
            lczero::Move m = UciToCanonicalMove(board, mv, black_to_move);
            if (m.is_null()) { std::cout << "  illegal move, try again." << std::endl; continue; }
            tree->MakeMove(m);
        } else {
            auto responder = std::make_unique<SilentUciResponder>();
            auto stopper = std::make_unique<PlayoutCountStopper>(visits);
            auto search = std::make_unique<lczero::classic::Search>(
                *tree, backend.get(), std::move(responder), lczero::MoveList{},
                std::chrono::steady_clock::now(), std::move(stopper), false, false, opts, nullptr);
            search->RunBlocking(1);
            lczero::classic::Node* root = tree->GetCurrentHead();
            lczero::classic::EdgeAndNode best; uint64_t bn = 0;
            for (const auto& e : root->Edges()) if (e.GetN() >= bn) { bn = e.GetN(); best = e; }
            if (best.GetMove().is_null()) break;
            std::cout << "AI plays: " << CanonicalMoveToUci(best.GetMove(), black_to_move)
                      << "  (" << root->GetN() << " nodes)" << std::endl;
            tree->MakeMove(best.GetMove());
        }
        result = tree->GetPositionHistory().ComputeGameResult();
    }
    PrintAsciiBoard(tree->GetPositionHistory().Last().GetBoard().GetRawPosition());
    if (result == lczero::GameResult::WHITE_WON)      std::cout << "*** WHITE wins ***" << std::endl;
    else if (result == lczero::GameResult::BLACK_WON) std::cout << "*** BLACK wins ***" << std::endl;
    else if (result == lczero::GameResult::DRAW)      std::cout << "*** DRAW ***" << std::endl;
    else std::cout << "(game ended)" << std::endl;
}

// --test-uci: conformance for the move I/O (risk #1) — no backend needed.
int main(int argc, char* argv[]) {
    bool test_mcts_mode = false;
    bool selfplay_mode = false;
    bool test_ep_mode = false;
    bool test_board_mode = false;
    bool test_policy_mode = false;
    bool test_trainingdata_mode = false;
    bool test_extract_mode = false;
    bool test_selfplay_mode = false;
    bool emit_roundtrip_mode = false;
    bool test_perft_mode = false;
    bool test_bits_mode = false;
    bool test_rules_mode = false;
    bool test_adapter_mode = false;
    bool test_nn_mode = false;
    bool uci_nn_mode = false;
    bool test_uci_mode = false;
    bool test_encoder_mode = false;
    bool play_mode = false;
    bool play_human_white = true;
    std::string rt_prefix = "roundtrip";
    std::string weights_file = "weights_0_elo.onnx";
    // Self-play driver options.
    int sp_games = 100, sp_visits = 200, sp_parallel = 1, sp_threads_per_game = 1;
    int sp_max_moves = 200, sp_temp_cutoff = 30, sp_backend_threads = 1;
    int sp_fixed_batch = 16;
    std::string sp_out = "selfplay_data";
    std::string sp_provider = "cpu";  // "cpu" or "cuda" (CUDA EP needs a -Duse_cuda build)
    // Self-play search hyperparameters (tunable).
    float sp_noise_eps = 0.25f, sp_noise_alpha = 0.3f, sp_policy_temp = 1.0f, sp_cpuct = -1.0f;
    std::string sp_start_fen;  // empty=default startpos; a FEN; or a path to a file of FENs
    // Early resignation (plan A5). Threshold <= -1.0 (the default) disables it.
    float sp_resign_threshold = -2.0f, sp_no_resign_frac = 0.10f;
    int sp_resign_consecutive = 3, sp_resign_earliest = 0;
    std::vector<std::pair<std::string, std::string>> sp_search_opts;  // --search-opt k=v (T8.3/#4b)
    // Arena (model-vs-model evaluation) options.
    bool arena_mode = false;
    std::string arena_a, arena_b;
    for (int i = 1; i < argc; ++i) {
        if (std::string(argv[i]) == "--selfplay") {
            selfplay_mode = true;
        } else if (std::string(argv[i]) == "--games" && i + 1 < argc) {
            sp_games = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--out" && i + 1 < argc) {
            sp_out = argv[++i];
        } else if (std::string(argv[i]) == "--visits" && i + 1 < argc) {
            sp_visits = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--parallel" && i + 1 < argc) {
            sp_parallel = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--threads-per-game" && i + 1 < argc) {
            sp_threads_per_game = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--max-moves" && i + 1 < argc) {
            sp_max_moves = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--temp-cutoff" && i + 1 < argc) {
            sp_temp_cutoff = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--backend-threads" && i + 1 < argc) {
            sp_backend_threads = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--provider" && i + 1 < argc) {
            sp_provider = argv[++i];
        } else if (std::string(argv[i]) == "--fixed-batch" && i + 1 < argc) {
            sp_fixed_batch = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--noise-epsilon" && i + 1 < argc) {
            sp_noise_eps = static_cast<float>(std::atof(argv[++i]));
        } else if (std::string(argv[i]) == "--noise-alpha" && i + 1 < argc) {
            sp_noise_alpha = static_cast<float>(std::atof(argv[++i]));
        } else if (std::string(argv[i]) == "--policy-temp" && i + 1 < argc) {
            sp_policy_temp = static_cast<float>(std::atof(argv[++i]));
        } else if (std::string(argv[i]) == "--cpuct" && i + 1 < argc) {
            sp_cpuct = static_cast<float>(std::atof(argv[++i]));
        } else if (std::string(argv[i]) == "--start-fen" && i + 1 < argc) {
            sp_start_fen = argv[++i];
        } else if (std::string(argv[i]) == "--resign-threshold" && i + 1 < argc) {
            sp_resign_threshold = static_cast<float>(std::atof(argv[++i]));
        } else if (std::string(argv[i]) == "--resign-consecutive" && i + 1 < argc) {
            sp_resign_consecutive = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--resign-earliest-move" && i + 1 < argc) {
            sp_resign_earliest = std::atoi(argv[++i]);
        } else if (std::string(argv[i]) == "--search-opt" && i + 1 < argc) {
            std::string kv = argv[++i];                    // "name=value"
            auto eq = kv.find('=');
            if (eq != std::string::npos) sp_search_opts.emplace_back(kv.substr(0, eq), kv.substr(eq + 1));
        } else if (std::string(argv[i]) == "--no-resign-frac" && i + 1 < argc) {
            sp_no_resign_frac = static_cast<float>(std::atof(argv[++i]));
        } else if (std::string(argv[i]) == "--arena") {
            arena_mode = true;
        } else if (std::string(argv[i]) == "--model-a" && i + 1 < argc) {
            arena_a = argv[++i];
        } else if (std::string(argv[i]) == "--model-b" && i + 1 < argc) {
            arena_b = argv[++i];
        } else if (std::string(argv[i]) == "--weights" && i + 1 < argc) {
            weights_file = argv[++i];
        } else if (std::string(argv[i]) == "--test-ep") {
            test_ep_mode = true;
        } else if (std::string(argv[i]) == "--test-board") {
            test_board_mode = true;
        } else if (std::string(argv[i]) == "--test-policy") {
            test_policy_mode = true;
        } else if (std::string(argv[i]) == "--test-trainingdata") {
            test_trainingdata_mode = true;
        } else if (std::string(argv[i]) == "--test-extract") {
            test_extract_mode = true;
        } else if (std::string(argv[i]) == "--test-selfplay") {
            test_selfplay_mode = true;
        } else if (std::string(argv[i]) == "--emit-roundtrip") {
            emit_roundtrip_mode = true;
            if (i + 1 < argc && argv[i + 1][0] != '-') rt_prefix = argv[++i];
        } else if (std::string(argv[i]) == "--test-perft") {
            test_perft_mode = true;
        } else if (std::string(argv[i]) == "--test-bits") {
            test_bits_mode = true;
        } else if (std::string(argv[i]) == "--test-rules") {
            test_rules_mode = true;
        } else if (std::string(argv[i]) == "--test-adapter") {
            test_adapter_mode = true;
        } else if (std::string(argv[i]) == "--test-nn") {
            test_nn_mode = true;
        } else if (std::string(argv[i]) == "--test-mcts") {
            test_mcts_mode = true;
            if (i + 1 < argc && argv[i + 1][0] != '-') {
                weights_file = argv[i + 1];
            }
        } else if (std::string(argv[i]) == "--uci-nn") {
            uci_nn_mode = true;
        } else if (std::string(argv[i]) == "--test-uci") {
            test_uci_mode = true;
        } else if (std::string(argv[i]) == "--test-encoder") {
            test_encoder_mode = true;
        } else if (std::string(argv[i]) == "--play") {
            play_mode = true;
        } else if (std::string(argv[i]) == "--play-black") {
            play_mode = true; play_human_white = false;
        }
    }

    std::cout << engine_info() << " (Custom Variant Engine)" << std::endl;

    pieceMap.init();
    variants.init();
    CommandLine::init(argc, argv);
    UCI::init(Options);
    Tune::init();
    PSQT::init(variants.find(Options["UCI_Variant"])->second);
    Bitboards::init();
    Position::init();
    Bitbases::init();
    Endgames::init();
    Threads.set(size_t(Options["Threads"]));
    Search::clear(); // After threads are up
    Eval::NNUE::init();

    if (test_ep_mode) {
        run_ep_tests();
    } else if (test_board_mode) {
        run_board_tests();
    } else if (test_policy_mode) {
        run_policy_tests();
    } else if (test_trainingdata_mode) {
        run_trainingdata_tests();
    } else if (test_extract_mode) {
        run_extract_tests(weights_file);
    } else if (test_selfplay_mode) {
        run_selfplay_tests(weights_file);
    } else if (emit_roundtrip_mode) {
        run_roundtrip_emit(rt_prefix);
    } else if (test_perft_mode) {
        run_perft_tests();
    } else if (test_bits_mode) {
        run_bits_tests();
    } else if (test_rules_mode) {
        run_rules_tests();
    } else if (test_adapter_mode) {
        run_adapter_tests();
    } else if (test_nn_mode) {
        run_nn_tests();
    } else if (test_uci_mode) {
        run_uci_tests();
    } else if (test_encoder_mode) {
        run_encoder_tests();
    } else if (uci_nn_mode) {
        run_uci_nn(weights_file, sp_provider, sp_fixed_batch);
    } else if (play_mode) {
        run_play(weights_file, sp_provider, sp_fixed_batch, sp_visits, play_human_white);
    } else if (arena_mode) {
        if (arena_a.empty() || arena_b.empty()) {
            std::cerr << "[arena] need --model-a <onnx> and --model-b <onnx>" << std::endl;
            return 1;
        }
        run_arena(arena_a, arena_b, sp_games, sp_visits, sp_max_moves, sp_temp_cutoff,
                  sp_provider, sp_fixed_batch);
    } else if (test_mcts_mode) {
        run_mcts_tests(weights_file);
    } else if (selfplay_mode) {
        std::cout << "=== Self-play data generation ===" << std::endl;
        setup_custom_variant();
        const std::string fen =
            "vrhabkberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHABKBERV w BIbi - 7+7 0 1";

        lczero::OptionsParser parser;
        lczero::classic::SearchParams::Populate(&parser);
        parser.GetMutableDefaultsOptions()->Set<float>(lczero::SharedBackendParams::kPolicySoftmaxTemp, sp_policy_temp);
        parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kHistoryFill, "no");
        parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kNoiseEpsilonId, sp_noise_eps);
        parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kNoiseAlphaId, sp_noise_alpha);
        if (sp_cpuct >= 0.0f)
            parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kCpuctId, sp_cpuct);
        // T8.3 #4b: arbitrary lc0 search params for self-play via --search-opt name=value.
        for (const auto& kv : sp_search_opts) {
            if (ApplySearchOpt(parser.GetMutableDefaultsOptions(), kv.first, kv.second))
                std::cout << "[selfplay] search-opt " << kv.first << "=" << kv.second << std::endl;
            else
                std::cout << "[selfplay] WARNING: unknown --search-opt '" << kv.first << "' (ignored)" << std::endl;
        }
        parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kWeightsId, weights_file);
        // Backend options. CPU: game-level parallelism + low intra-op threads.
        // CUDA (Colab GPU, needs a -Duse_cuda build): provider=cuda + fixed_batch.
        std::string sp_backend_opts;
        if (sp_provider == "cuda") {
            sp_backend_opts = "provider=cuda,fixed_batch=" + std::to_string(std::max(1, sp_fixed_batch));
        } else {
            sp_backend_opts = "threads=" + std::to_string(std::max(1, sp_backend_threads));
        }
        parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kBackendOptionsId, sp_backend_opts);
        std::cout << "[selfplay] backend: " << sp_backend_opts << std::endl;
        const lczero::OptionsDict& sp_options = parser.GetOptionsDict();

        std::unique_ptr<lczero::Backend> backend;
        try {
            auto raw_backend = std::make_unique<lczero::OnnxBackend>();
            raw_backend->UpdateConfiguration(sp_options);
            backend = lczero::CreateMemCache(std::move(raw_backend), sp_options);
        } catch (const std::exception& e) {
            std::cerr << "[selfplay] FATAL: could not load backend: " << e.what() << std::endl;
            Threads.set(0);
            return 1;
        }

        lczero::SelfPlayConfig cfg;
        cfg.start_fen = fen;  // default = startpos
        if (!sp_start_fen.empty()) {
            std::ifstream ff(sp_start_fen);
            if (ff) {  // an opening book: one FEN per line (# = comment)
                std::string line;
                while (std::getline(ff, line)) {
                    if (!line.empty() && line[0] != '#') cfg.start_fens.push_back(line);
                }
                std::cout << "[selfplay] opening book: " << cfg.start_fens.size()
                          << " FENs from " << sp_start_fen << std::endl;
            } else {
                cfg.start_fen = sp_start_fen;  // a single FEN string
            }
        }
        cfg.out_dir = sp_out;
        cfg.num_games = sp_games;
        cfg.visits = sp_visits;
        cfg.max_moves = sp_max_moves;
        cfg.temp_cutoff_ply = sp_temp_cutoff;
        cfg.parallel = sp_parallel;
        cfg.threads_per_game = sp_threads_per_game;
        cfg.resign_threshold = sp_resign_threshold;
        cfg.resign_consecutive = sp_resign_consecutive;
        cfg.resign_earliest_move = sp_resign_earliest;
        cfg.no_resign_frac = sp_no_resign_frac;
        if (sp_resign_threshold > -1.0f) {
            std::cout << "[selfplay] resign: best_q<=" << sp_resign_threshold
                      << " for " << sp_resign_consecutive << " moves, no-resign frac="
                      << sp_no_resign_frac << std::endl;
        }
        lczero::RunSelfPlay(cfg, backend.get(), sp_options);
    } else {
        UCI::loop(argc, argv);
    }

    Threads.set(0);
    variants.clear_all();
    pieceMap.clear_all();
    delete XBoard::stateMachine;
    return 0;
}
