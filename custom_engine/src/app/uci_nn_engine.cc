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
#include "app/uci_nn_engine.h"
#include "app/variant_setup.h"
#include "app/backend_factory.h"
#include "app/uci_coords.h"
#include "app/search_opts.h"
#include "app/search_support.h"

using namespace Stockfish;

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
            } else if (cmd == "d") {
                // Fairy-Stockfish debug command: dump the current position (board
                // art + "Fen: ..." + Key/Checkers) in REAL coordinates.
                if (tree_) {
                    std::cout << tree_->GetPositionHistory().Last().GetBoard().GetRawPosition()
                              << std::endl;
                } else {
                    std::cout << "info string no position set (send 'position ...' first)"
                              << std::endl;
                }
            } else if (cmd == "legalmoves") {
                // GUI helper: liệt kê TẤT CẢ nước hợp lệ ở thế hiện tại, MỘT dòng,
                // UCI toạ-độ-thật. Hiệu năng: movegen native (không brute-force) +
                // một buffer std::string đã reserve + một lần Send (không flush
                // từng token, không std::endl). movegen mới là chi phí chính.
                if (tree_) {
                    const auto& board = tree_->GetPositionHistory().Last().GetBoard();
                    const bool black = tree_->IsBlackToMove();
                    const lczero::MoveList moves = board.GenerateLegalMoves();
                    std::string line;
                    line.reserve(moves.size() * 8 + 16);   // ~ "e10i6h " mỗi nước
                    line += "legalmoves";
                    for (const lczero::Move& m : moves) {
                        line += ' ';
                        line += CanonicalMoveToUci(m, black);
                    }
                    Send(line);
                } else {
                    Send("legalmoves");
                }
            } else if (cmd == "result") {
                // GUI helper: kết quả ván ở thế hiện tại.
                const char* r = "undecided";
                if (tree_) {
                    switch (tree_->GetPositionHistory().ComputeGameResult()) {
                        case lczero::GameResult::WHITE_WON: r = "white"; break;
                        case lczero::GameResult::BLACK_WON: r = "black"; break;
                        case lczero::GameResult::DRAW:      r = "draw";  break;
                        default: break;  // UNDECIDED -> "undecided"
                    }
                }
                Send(std::string("result ") + r);
            } else if (cmd == "fen") {
                // GUI helper: FEN sạch một dòng (toạ độ thật) để GUI vẽ bàn cờ,
                // khỏi phải parse tranh ASCII của lệnh `d`.
                if (tree_) {
                    Send("fen " + tree_->GetPositionHistory().Last()
                                      .GetBoard().GetRawPosition().fen());
                } else {
                    Send("info string no position set (send 'position ...' first)");
                }
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
        Send("option name Provider type combo default cpu var cpu var cuda var dml");
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
        std::string bopts;
        if (provider_ == "cuda")
            bopts = "provider=cuda,fixed_batch=" + std::to_string(std::max(1, fixed_batch_));
        else if (provider_ == "dml")   // DirectML: dynamic batch; threads= covers any CPU-fallback ops
            bopts = "provider=dml,threads=" + std::to_string(std::max(1, backend_threads_));
        else
            bopts = "threads=" + std::to_string(std::max(1, backend_threads_));
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
