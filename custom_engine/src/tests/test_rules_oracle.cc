// Independent rules oracle for the 10x10 variant: --audit-rules.
//
// Every other movegen test compares the engine with ITSELF (adapter vs the raw
// Fairy-Stockfish position underneath, perft vs perft, FEN round-trips). They
// catch wrapping bugs, but a rule that Fairy-Stockfish implements differently
// from what the variant intends would pass all of them.
//
// This file re-implements the rules from their written description (see the
// table below), with no code shared with Fairy-Stockfish, and plays random games
// through the production path (lczero::PositionHistory over Fairy-Stockfish).
// At every position it requires, exactly:
//   1. the legal move set (from, to, promotion piece, move kind);
//   2. for EVERY legal move: the resulting board, side to move, castling rights,
//      en-passant squares, checks remaining, rule-50 counter and in-check flag,
//      gives_check(), and that undo_move() restores the position and its key;
//   3. the incremental Zobrist key == the key of the same position set from FEN
//      (for the played move and for every special move);
//   4. PositionHistory::ComputeGameResult() and the repetition count;
//   5. the 226 NN input planes (EncodePositionForNN + UnpackInputPlanes) and the
//      scalar fields of the training record;
//   6. MoveToNNIndex of every legal move (and injectivity).
//
// Rules as implemented here (White's view; Black mirrors, forward = down):
//   board 10x10 (a-j, 1-10). K = the royal piece ("Hoang gia"; Fairy-Stockfish
//   insists on the letter k): king step + knight leap. In the code below
//   "king" always means this royal piece.
//   N knight; B, R, Q; A = Q+N; E(chancellor) = R+N; H(archbishop) = B+N;
//   M(centaur) = king step + N; V (wildebeest) = camel (1,3) + N; Y (alibaba)
//   = alfil (2,2) and dabbaba (2,0) leaps (jumping).
//   P: 1 forward (quiet), 2 forward from ranks 1-3 if both squares empty,
//      captures 1 diagonally forward.
//   S (Sergeant): moves AND captures 1 square forward, forward-left or
//      forward-right. From ranks 1-3 it may also move (never capture) 2 squares
//      straight forward or 2 diagonally forward; the square in between must be
//      empty.
//   En passant: after a P or S double step, on the very next move only, an
//      enemy P (diagonally) or S (any of its three forward directions) may move
//      onto the passed square and capture the piece that double-stepped. A
//      Sergeant moving onto that square always captures (there is no quiet
//      alternative); a Pawn pushing straight onto it does not capture.
//   Promotion: a P or S ending on ranks 8-10 must promote to B, M, N, R, V or
//      Y. This includes captures and en-passant captures.
//   Castling: king f1 + rook i1 -> king h1, rook g1 (g1, h1 empty); king f1 +
//      rook b1 -> king d1, rook e1 (c1, d1, e1 empty). Not out of, through or
//      into check. Rights are lost when the king moves, or when that rook moves
//      or is captured on its square.
//   Checks: after each move, every piece of the mover that attacks the
//      opponent's king counts one check (a single check 1, a double check 2).
//      8 checks win immediately, before any other rule.
//   No legal move (checkmate or stalemate) loses. 100 plies without a capture,
//      a P/S move or a promotion draws unless the side to move is checkmated.
//      A position occurring for the third time draws (position = board, side to
//      move, castling rights, en-passant state, checks remaining).

#include "tests/test_common.h"

#include <cctype>

namespace {
namespace orc {

enum : int8_t { E_ = 0, P_ = 1, N_, B_, R_, Q_, K_, A_, C_, H_, M_, V_, Y_, S_, NPT };
constexpr int kW = 0, kB = 1;
const char* kTypeChar = ".pnbrqkaehmvys";   // C_ (chancellor) is written 'e'

inline int sq_of(int f, int r) { return r * 10 + f; }
inline int fl(int s) { return s % 10; }
inline int rk(int s) { return s / 10; }
inline bool on_board(int f, int r) { return f >= 0 && f < 10 && r >= 0 && r < 10; }
inline int col(int8_t pc) { return pc > 0 ? kW : kB; }
inline int typ(int8_t pc) { return pc > 0 ? pc : -pc; }
inline int8_t mk(int c, int t) { return static_cast<int8_t>(c == kW ? t : -t); }

inline bool has_knight(int t) { return t == N_ || t == K_ || t == A_ || t == C_ || t == H_ || t == M_ || t == V_; }
inline bool has_kstep(int t) { return t == K_ || t == M_; }
inline bool has_camel(int t) { return t == V_; }
inline bool has_ad(int t) { return t == Y_; }
inline bool slides_orth(int t) { return t == R_ || t == Q_ || t == A_ || t == C_; }
inline bool slides_diag(int t) { return t == B_ || t == Q_ || t == A_ || t == H_; }

const int kKnight[8][2] = {{1, 2}, {2, 1}, {2, -1}, {1, -2}, {-1, -2}, {-2, -1}, {-2, 1}, {-1, 2}};
const int kCamel[8][2] = {{1, 3}, {3, 1}, {3, -1}, {1, -3}, {-1, -3}, {-3, -1}, {-3, 1}, {-1, 3}};
const int kKStep[8][2] = {{0, 1}, {1, 1}, {1, 0}, {1, -1}, {0, -1}, {-1, -1}, {-1, 0}, {-1, 1}};
const int kAlfil[4][2] = {{2, 2}, {2, -2}, {-2, -2}, {-2, 2}};
const int kDabbaba[4][2] = {{0, 2}, {2, 0}, {0, -2}, {-2, 0}};
const int kOrth[4][2] = {{0, 1}, {1, 0}, {0, -1}, {-1, 0}};
const int kDiag[4][2] = {{1, 1}, {1, -1}, {-1, -1}, {-1, 1}};
const int8_t kPromos[6] = {B_, M_, N_, R_, V_, Y_};

struct OState {
    int8_t b[100];
    int stm = kW;
    bool castle[2][2] = {{false, false}, {false, false}};  // [colour][0 = rook i, 1 = rook b]
    int ep_mid = -1, ep_victim = -1;   // passed square / square of the double-stepper
    bool ep_two = false;               // Fairy-Stockfish also marks the victim square (Sergeant)
    int checks[2] = {8, 8};
    int rule50 = 0;
};

enum Kind : uint8_t { KN_NORMAL = 0, KN_EP = 1, KN_PROMO = 2, KN_CASTLE = 3, KN_OTHER = 7 };

struct OMove {
    int8_t from = 0, to = 0;   // castling: to = the rook's square ("king takes rook")
    int8_t promo = 0;
    uint8_t kind = KN_NORMAL;
    bool dbl = false;          // double step of a P or S
    uint32_t key() const {
        return (uint32_t(uint8_t(from)) << 16) | (uint32_t(uint8_t(to)) << 8) |
               (uint32_t(uint8_t(promo)) << 3) | kind;
    }
};

std::string sqname(int s) {
    return std::string(1, char('a' + fl(s))) + std::to_string(rk(s) + 1);
}
std::string mname(const OMove& m) {
    std::string s = sqname(m.from) + sqname(m.to);
    if (m.promo) s += kTypeChar[m.promo];
    if (m.kind == KN_EP) s += "(ep)";
    if (m.kind == KN_CASTLE) s += "(castle)";
    return s;
}

int find_king(const OState& st, int c) {
    const int8_t k = mk(c, K_);
    for (int s = 0; s < 100; ++s)
        if (st.b[s] == k) return s;
    return -1;
}

// Is square s attacked by colour c?
bool attacked(const OState& st, int s, int c) {
    const int f = fl(s), r = rk(s);
    auto at = [&](int ff, int rr) -> int8_t { return on_board(ff, rr) ? st.b[sq_of(ff, rr)] : int8_t(0); };
    auto mine = [&](int8_t pc) { return pc != 0 && col(pc) == c; };
    const int fwd = (c == kW) ? 1 : -1;
    for (int df = -1; df <= 1; ++df) {   // a P/S of colour c one rank "behind" s
        const int8_t pc = at(f + df, r - fwd);
        if (!mine(pc)) continue;
        if (typ(pc) == S_) return true;
        if (typ(pc) == P_ && df != 0) return true;
    }
    for (const auto& d : kKnight) { const int8_t pc = at(f + d[0], r + d[1]); if (mine(pc) && has_knight(typ(pc))) return true; }
    for (const auto& d : kKStep)  { const int8_t pc = at(f + d[0], r + d[1]); if (mine(pc) && has_kstep(typ(pc))) return true; }
    for (const auto& d : kCamel)  { const int8_t pc = at(f + d[0], r + d[1]); if (mine(pc) && has_camel(typ(pc))) return true; }
    for (const auto& d : kAlfil)  { const int8_t pc = at(f + d[0], r + d[1]); if (mine(pc) && has_ad(typ(pc))) return true; }
    for (const auto& d : kDabbaba){ const int8_t pc = at(f + d[0], r + d[1]); if (mine(pc) && has_ad(typ(pc))) return true; }
    for (int pass = 0; pass < 2; ++pass) {
        const auto& dirs = pass == 0 ? kOrth : kDiag;
        for (const auto& d : dirs) {
            for (int k = 1;; ++k) {
                const int ff = f + d[0] * k, rr = r + d[1] * k;
                if (!on_board(ff, rr)) break;
                const int8_t pc = st.b[sq_of(ff, rr)];
                if (!pc) continue;
                if (mine(pc) && (pass == 0 ? slides_orth(typ(pc)) : slides_diag(typ(pc)))) return true;
                break;
            }
        }
    }
    return false;
}

bool in_check(const OState& st) {
    const int k = find_king(st, st.stm);
    return k >= 0 && attacked(st, k, st.stm ^ 1);
}

// Does the piece on square p attack square s? Written piece by piece (not
// reusing attacked(), which scans outward from s) so the check count below is
// a second, independent computation.
bool piece_attacks(const OState& st, int p, int s) {
    const int8_t pc = st.b[p];
    if (!pc || p == s) return false;
    const int t = typ(pc);
    const int df = fl(s) - fl(p), dr = rk(s) - rk(p);
    const int adf = std::abs(df), adr = std::abs(dr);
    const int fwd = col(pc) == kW ? 1 : -1;
    if (t == P_) return dr == fwd && adf == 1;
    if (t == S_) return dr == fwd && adf <= 1;
    if (has_knight(t) && ((adf == 1 && adr == 2) || (adf == 2 && adr == 1))) return true;
    if (has_kstep(t) && std::max(adf, adr) == 1) return true;
    if (has_camel(t) && ((adf == 1 && adr == 3) || (adf == 3 && adr == 1))) return true;
    if (has_ad(t) && ((adf == 2 && adr == 2) || (adf == 2 && adr == 0) || (adf == 0 && adr == 2))) return true;
    const bool orth = (df == 0) != (dr == 0), diag = adf == adr && adf != 0;
    if ((orth && slides_orth(t)) || (diag && slides_diag(t))) {
        const int sf = (df > 0) - (df < 0), sr = (dr > 0) - (dr < 0);
        for (int f = fl(p) + sf, r = rk(p) + sr; f != fl(s) || r != rk(s); f += sf, r += sr)
            if (st.b[sq_of(f, r)]) return false;
        return true;
    }
    return false;
}

// How many pieces of colour c attack square s.
int attackers_count(const OState& st, int s, int c) {
    int n = 0;
    for (int p = 0; p < 100; ++p)
        if (st.b[p] && col(st.b[p]) == c && piece_attacks(st, p, s)) ++n;
    return n;
}

void gen_pseudo(const OState& st, std::vector<OMove>& out) {
    const int us = st.stm, them = us ^ 1;
    const int fwd = us == kW ? 1 : -1;
    auto promo_zone = [&](int r) { return us == kW ? r >= 7 : r <= 2; };
    auto dbl_region = [&](int r) { return us == kW ? r <= 2 : r >= 7; };
    auto add = [&](int from, int to, int8_t promo, uint8_t kind, bool dbl) {
        OMove m; m.from = int8_t(from); m.to = int8_t(to); m.promo = promo; m.kind = kind; m.dbl = dbl;
        out.push_back(m);
    };
    auto add_pawnlike = [&](int from, int to, bool ep) {
        if (promo_zone(rk(to))) {
            for (int8_t p : kPromos) add(from, to, p, ep ? KN_EP : KN_PROMO, false);
        } else {
            add(from, to, 0, ep ? KN_EP : KN_NORMAL, false);
        }
    };
    for (int s = 0; s < 100; ++s) {
        const int8_t pc = st.b[s];
        if (!pc || col(pc) != us) continue;
        const int t = typ(pc), f = fl(s), r = rk(s);
        if (t == P_) {
            if (on_board(f, r + fwd) && !st.b[sq_of(f, r + fwd)]) {
                add_pawnlike(s, sq_of(f, r + fwd), false);
                if (dbl_region(r) && on_board(f, r + 2 * fwd) && !st.b[sq_of(f, r + 2 * fwd)])
                    add(s, sq_of(f, r + 2 * fwd), 0, KN_NORMAL, true);
            }
            for (int df : {-1, 1}) {
                if (!on_board(f + df, r + fwd)) continue;
                const int to = sq_of(f + df, r + fwd);
                if (to == st.ep_mid) add_pawnlike(s, to, true);
                else if (st.b[to] && col(st.b[to]) == them) add_pawnlike(s, to, false);
            }
        } else if (t == S_) {
            for (int df = -1; df <= 1; ++df) {
                if (!on_board(f + df, r + fwd)) continue;
                const int to = sq_of(f + df, r + fwd);
                if (to == st.ep_mid) add_pawnlike(s, to, true);
                else if (!st.b[to] || col(st.b[to]) == them) add_pawnlike(s, to, false);
            }
            if (dbl_region(r)) {
                for (int df : {0, -2, 2}) {
                    const int tf = f + df, tr = r + 2 * fwd;
                    if (!on_board(tf, tr)) continue;
                    if (st.b[sq_of(f + df / 2, r + fwd)] || st.b[sq_of(tf, tr)]) continue;
                    add(s, sq_of(tf, tr), 0, KN_NORMAL, true);
                }
            }
        } else {
            auto leap = [&](int ff, int rr) {
                if (!on_board(ff, rr)) return;
                const int to = sq_of(ff, rr);
                if (st.b[to] && col(st.b[to]) == us) return;
                add(s, to, 0, KN_NORMAL, false);
            };
            if (has_knight(t)) for (const auto& d : kKnight) leap(f + d[0], r + d[1]);
            if (has_kstep(t))  for (const auto& d : kKStep)  leap(f + d[0], r + d[1]);
            if (has_camel(t))  for (const auto& d : kCamel)  leap(f + d[0], r + d[1]);
            if (has_ad(t)) {
                for (const auto& d : kAlfil)   leap(f + d[0], r + d[1]);
                for (const auto& d : kDabbaba) leap(f + d[0], r + d[1]);
            }
            for (int pass = 0; pass < 2; ++pass) {
                if (pass == 0 ? !slides_orth(t) : !slides_diag(t)) continue;
                const auto& dirs = pass == 0 ? kOrth : kDiag;
                for (const auto& d : dirs) {
                    for (int k = 1;; ++k) {
                        const int ff = f + d[0] * k, rr = r + d[1] * k;
                        if (!on_board(ff, rr)) break;
                        const int to = sq_of(ff, rr);
                        if (st.b[to]) {
                            if (col(st.b[to]) == them) add(s, to, 0, KN_NORMAL, false);
                            break;
                        }
                        add(s, to, 0, KN_NORMAL, false);
                    }
                }
            }
        }
    }
    // Castling (the attack conditions here; "not into check" by the legality filter).
    const int br = us == kW ? 0 : 9;
    const int ksq = sq_of(5, br);
    if (st.b[ksq] == mk(us, K_) && !attacked(st, ksq, them)) {
        if (st.castle[us][0] && st.b[sq_of(8, br)] == mk(us, R_) &&
            !st.b[sq_of(6, br)] && !st.b[sq_of(7, br)] &&
            !attacked(st, sq_of(6, br), them) && !attacked(st, sq_of(7, br), them))
            add(ksq, sq_of(8, br), 0, KN_CASTLE, false);
        if (st.castle[us][1] && st.b[sq_of(1, br)] == mk(us, R_) &&
            !st.b[sq_of(2, br)] && !st.b[sq_of(3, br)] && !st.b[sq_of(4, br)] &&
            !attacked(st, sq_of(4, br), them) && !attacked(st, sq_of(3, br), them))
            add(ksq, sq_of(1, br), 0, KN_CASTLE, false);
    }
}

// Plays m (assumed pseudo-legal). Counts the checks it gives: one per checking
// piece. *checkers gets that number (-1 if the two attack computations disagree).
OState apply(const OState& st, const OMove& m, bool* gives_check = nullptr, int* checkers = nullptr) {
    OState n = st;
    const int us = st.stm, them = us ^ 1;
    const int8_t pc = st.b[m.from];
    const int t = typ(pc);
    n.ep_mid = n.ep_victim = -1;
    n.ep_two = false;
    if (m.kind == KN_CASTLE) {
        const int br = rk(m.from);
        const bool kside = fl(m.to) > fl(m.from);
        n.b[m.from] = 0;
        n.b[m.to] = 0;
        n.b[sq_of(kside ? 7 : 3, br)] = mk(us, K_);
        n.b[sq_of(kside ? 6 : 4, br)] = mk(us, R_);
        n.castle[us][0] = n.castle[us][1] = false;
        n.rule50 = st.rule50 + 1;
    } else {
        bool capture = st.b[m.to] != 0;
        if (m.kind == KN_EP) { n.b[st.ep_victim] = 0; capture = true; }
        n.b[m.to] = m.promo ? mk(us, m.promo) : pc;
        n.b[m.from] = 0;
        if (t == K_) n.castle[us][0] = n.castle[us][1] = false;
        for (int s : {int(m.from), int(m.to)})
            for (int c = 0; c < 2; ++c) {
                const int cbr = c == kW ? 0 : 9;
                if (s == sq_of(8, cbr)) n.castle[c][0] = false;
                if (s == sq_of(1, cbr)) n.castle[c][1] = false;
            }
        if (m.dbl) {
            n.ep_mid = (m.from + m.to) / 2;
            n.ep_victim = m.to;
            n.ep_two = (t == S_);
        }
        n.rule50 = (capture || t == P_ || t == S_) ? 0 : st.rule50 + 1;
    }
    n.stm = them;
    const int ks = find_king(n, them);
    const bool gc = ks >= 0 && attacked(n, ks, us);
    const int nchk = ks >= 0 ? attackers_count(n, ks, us) : 0;
    if (gc) n.checks[us] = std::max(n.checks[us] - nchk, 0);
    if (gives_check) *gives_check = gc;
    if (checkers) *checkers = (gc == (nchk > 0)) ? nchk : -1;
    return n;
}

void gen_legal(const OState& st, std::vector<OMove>& out) {
    out.clear();
    if (st.checks[st.stm ^ 1] <= 0) return;   // the last move already won by checks
    std::vector<OMove> ps;
    ps.reserve(160);
    gen_pseudo(st, ps);
    for (const auto& m : ps) {
        const OState n = apply(st, m);
        const int k = find_king(n, st.stm);
        if (k >= 0 && attacked(n, k, st.stm ^ 1)) continue;
        out.push_back(m);
    }
}

// Exact identity of a position for the repetition rule (rule-50 excluded).
std::string rep_key(const OState& st) {
    std::string k(reinterpret_cast<const char*>(st.b), 100);
    k += char(st.stm);
    k += char(st.castle[0][0] | (st.castle[0][1] << 1) | (st.castle[1][0] << 2) | (st.castle[1][1] << 3));
    k += char(st.ep_mid + 1);
    k += char(st.ep_victim + 1);
    k += char(st.checks[0]);
    k += char(st.checks[1]);
    return k;
}

lczero::GameResult result_of(const OState& st, int reps, bool no_moves) {
    using GR = lczero::GameResult;
    if (st.checks[kW] <= 0) return GR::WHITE_WON;
    if (st.checks[kB] <= 0) return GR::BLACK_WON;
    const GR stm_loses = st.stm == kW ? GR::BLACK_WON : GR::WHITE_WON;
    if (st.rule50 >= 100) return (no_moves && in_check(st)) ? stm_loses : GR::DRAW;
    if (reps >= 2) return GR::DRAW;
    if (no_moves) return stm_loses;
    return GR::UNDECIDED;
}

// Policy index from the documented layout (canonical frame: ranks flipped when
// Black is to move): promotions 88 + piece*3 + (dx+1) with pieces B R M N V Y;
// knight 72-79 and camel 80-87 clockwise from (+1,+2)/(+1,+3); everything else
// a ray N NE E SE S SW W NW x distance 1-9. Index = type*100 + rank*10 + file.
int nn_index(const OMove& m, bool black) {
    int f0 = fl(m.from), r0 = rk(m.from), f1 = fl(m.to), r1 = rk(m.to);
    if (black) { r0 = 9 - r0; r1 = 9 - r1; }
    const int dx = f1 - f0, dy = r1 - r0;
    int type = -1;
    if (m.promo) {
        int pi = -1;
        switch (m.promo) {
            case B_: pi = 0; break; case R_: pi = 1; break; case M_: pi = 2; break;
            case N_: pi = 3; break; case V_: pi = 4; break; case Y_: pi = 5; break;
            default: break;
        }
        if (pi < 0 || dx < -1 || dx > 1) return -1;
        type = 88 + pi * 3 + (dx + 1);
    } else {
        for (int i = 0; i < 8 && type < 0; ++i)
            if (dx == kKnight[i][0] && dy == kKnight[i][1]) type = 72 + i;
        for (int i = 0; i < 8 && type < 0; ++i)
            if (dx == kCamel[i][0] && dy == kCamel[i][1]) type = 80 + i;
        if (type < 0) {
            const int adx = std::abs(dx), ady = std::abs(dy);
            if ((dx == 0) == (dy == 0) && adx != ady) return -1;   // not a ray
            const int sx = (dx > 0) - (dx < 0), sy = (dy > 0) - (dy < 0);
            static const int dir_of[3][3] = {{5, 6, 7}, {4, -1, 0}, {3, 2, 1}};  // [sx+1][sy+1]
            const int dir = dir_of[sx + 1][sy + 1];
            const int dist = std::max(adx, ady);
            if (dir < 0 || dist < 1 || dist > 9) return -1;
            type = dir * 9 + (dist - 1);
        }
    }
    return type * 100 + r0 * 10 + f0;
}

// Dense [226][100] NN input for the current position, lc0 layout (see encoder.h).
void planes_of(const std::vector<OState>& hist, const std::vector<int>& reps, float* dense) {
    std::fill(dense, dense + 226 * 100, 0.0f);
    const OState& cur = hist.back();
    const int us = cur.stm, them = us ^ 1;
    auto canon = [&](int s) { return (us == kB ? 9 - rk(s) : rk(s)) * 10 + fl(s); };
    static const int plane_of_type[NPT] = {-1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12};
    const int n = static_cast<int>(hist.size());
    for (int d = 0; d < 8 && d < n; ++d) {
        const OState& h = hist[n - 1 - d];
        for (int s = 0; s < 100; ++s) {
            const int8_t pc = h.b[s];
            if (!pc) continue;
            const int pl = d * 27 + (col(pc) == us ? 0 : 13) + plane_of_type[typ(pc)];
            dense[pl * 100 + canon(s)] = 1.0f;
        }
        if (reps[n - 1 - d] >= 1)
            std::fill(dense + (d * 27 + 26) * 100, dense + (d * 27 + 27) * 100, 1.0f);
    }
    auto set = [&](int p, int s) { dense[(216 + p) * 100 + canon(s)] = 1.0f; };
    auto fill = [&](int p, float v) { std::fill(dense + (216 + p) * 100, dense + (217 + p) * 100, v); };
    if (cur.castle[us][1])   set(0, sq_of(1, us == kW ? 0 : 9));
    if (cur.castle[us][0])   set(1, sq_of(8, us == kW ? 0 : 9));
    if (cur.castle[them][1]) set(2, sq_of(1, them == kW ? 0 : 9));
    if (cur.castle[them][0]) set(3, sq_of(8, them == kW ? 0 : 9));
    if (cur.ep_mid >= 0) {
        set(4, cur.ep_mid);
        if (cur.ep_two) set(4, cur.ep_victim);
    }
    fill(5, static_cast<float>(cur.rule50) / 100.0f);
    fill(7, 1.0f);
    fill(8, static_cast<float>(cur.checks[us]) / 10.0f);
    fill(9, static_cast<float>(cur.checks[them]) / 10.0f);
}

// FEN reader, independent of Fairy-Stockfish's.
bool parse_fen(const std::string& fen, OState& st) {
    std::istringstream ss(fen);
    std::string place, side, castling, ep, checks;
    int r50 = 0, fullmove = 1;
    if (!(ss >> place >> side >> castling >> ep >> checks)) return false;
    ss >> r50 >> fullmove;
    std::memset(st.b, 0, sizeof(st.b));
    int r = 9, f = 0;
    for (size_t i = 0; i < place.size(); ++i) {
        const char c = place[i];
        if (c == '/') { --r; f = 0; continue; }
        if (std::isdigit(static_cast<unsigned char>(c))) {
            int n = c - '0';
            if (i + 1 < place.size() && std::isdigit(static_cast<unsigned char>(place[i + 1]))) n = n * 10 + (place[++i] - '0');
            f += n;
            continue;
        }
        const char* p = std::strchr(kTypeChar + 1, std::tolower(static_cast<unsigned char>(c)));
        if (!p || r < 0 || f > 9) return false;
        st.b[sq_of(f, r)] = mk(std::isupper(static_cast<unsigned char>(c)) ? kW : kB, int(p - kTypeChar));
        ++f;
    }
    st.stm = side == "b" ? kB : kW;
    for (char c : castling) {
        if (c == 'K' || c == 'I') st.castle[kW][0] = true;
        if (c == 'Q' || c == 'B') st.castle[kW][1] = true;
        if (c == 'k' || c == 'i') st.castle[kB][0] = true;
        if (c == 'q' || c == 'b') st.castle[kB][1] = true;
    }
    std::vector<int> eps;
    for (size_t i = 0; i + 1 < ep.size();) {
        if (ep[i] < 'a' || ep[i] > 'j') break;
        const int ef = ep[i] - 'a';
        size_t j = i + 1;
        int er = 0;
        while (j < ep.size() && std::isdigit(static_cast<unsigned char>(ep[j]))) er = er * 10 + (ep[j++] - '0');
        eps.push_back(sq_of(ef, er - 1));
        i = j;
    }
    st.ep_mid = st.ep_victim = -1;
    st.ep_two = false;
    for (int s : eps)
        if (!st.b[s]) st.ep_mid = s;
    if (st.ep_mid >= 0) {
        if (eps.size() == 2) { st.ep_victim = eps[0] == st.ep_mid ? eps[1] : eps[0]; st.ep_two = true; }
        else st.ep_victim = st.ep_mid + (st.stm == kW ? -10 : 10);
    }
    const auto plus = checks.find('+');
    if (plus == std::string::npos) return false;
    st.checks[kW] = std::stoi(checks.substr(0, plus));
    st.checks[kB] = std::stoi(checks.substr(plus + 1));
    st.rule50 = r50;
    return true;
}

}  // namespace orc

// ---------------------------------------------------------------------------
// Fairy-Stockfish side: observable state, move conversion.
// ---------------------------------------------------------------------------
int8_t fsf_type(PieceType pt) {
    switch (pt) {
        case PAWN: return orc::P_;   case KNIGHT: return orc::N_;   case BISHOP: return orc::B_;
        case ROOK: return orc::R_;   case QUEEN: return orc::Q_;    case KING: return orc::K_;
        case AMAZON: return orc::A_; case CHANCELLOR: return orc::C_; case ARCHBISHOP: return orc::H_;
        case CENTAUR: return orc::M_; case CUSTOM_PIECE_1: return orc::V_;
        case CUSTOM_PIECE_2: return orc::Y_; case CUSTOM_PIECE_3: return orc::S_;
        default: return 99;
    }
}
inline int osq(Square s) { return int(rank_of(s)) * 10 + int(file_of(s)); }
inline Square fsq(int s) { return make_square(File(orc::fl(s)), Rank(orc::rk(s))); }

orc::OMove to_oracle(Move m) {
    orc::OMove om;
    om.from = int8_t(osq(from_sq(m)));
    om.to = int8_t(osq(to_sq(m)));
    switch (type_of(m)) {
        case NORMAL: om.kind = orc::KN_NORMAL; break;
        case CASTLING: om.kind = orc::KN_CASTLE; break;
        case PROMOTION: om.kind = orc::KN_PROMO; om.promo = fsf_type(promotion_type(m)); break;
        case EN_PASSANT:
            om.kind = orc::KN_EP;
            if (ep_promotion_type(m) != NO_PIECE_TYPE) om.promo = fsf_type(ep_promotion_type(m));
            break;
        default: om.kind = orc::KN_OTHER; break;
    }
    return om;
}

// Everything the rules define about a position, read from Fairy-Stockfish.
struct Observed {
    int8_t b[100];
    int stm;
    bool castle[2][2];
    std::vector<int> ep;   // sorted oracle squares
    int checks[2];
    int rule50;
};

Observed observe(const Position& p) {
    Observed o;
    for (int s = 0; s < 100; ++s) {
        const Piece pc = p.piece_on(fsq(s));
        o.b[s] = pc == NO_PIECE ? 0 : orc::mk(color_of(pc) == WHITE ? orc::kW : orc::kB, fsf_type(type_of(pc)));
    }
    o.stm = p.side_to_move() == WHITE ? orc::kW : orc::kB;
    o.castle[orc::kW][0] = p.can_castle(WHITE_OO);
    o.castle[orc::kW][1] = p.can_castle(WHITE_OOO);
    o.castle[orc::kB][0] = p.can_castle(BLACK_OO);
    o.castle[orc::kB][1] = p.can_castle(BLACK_OOO);
    for (Bitboard b = p.ep_squares(); b;) o.ep.push_back(osq(pop_lsb(b)));
    std::sort(o.ep.begin(), o.ep.end());
    o.checks[orc::kW] = int(p.checks_remaining(WHITE));
    o.checks[orc::kB] = int(p.checks_remaining(BLACK));
    o.rule50 = p.rule50_count();
    return o;
}

Observed expected(const orc::OState& st) {
    Observed o;
    std::memcpy(o.b, st.b, 100);
    o.stm = st.stm;
    std::memcpy(o.castle, st.castle, sizeof(o.castle));
    if (st.ep_mid >= 0) {
        o.ep.push_back(st.ep_mid);
        if (st.ep_two) o.ep.push_back(st.ep_victim);
        std::sort(o.ep.begin(), o.ep.end());
    }
    o.checks[0] = st.checks[0];
    o.checks[1] = st.checks[1];
    o.rule50 = st.rule50;
    return o;
}

// "" when equal, else a description of the first difference.
std::string diff(const Observed& a, const Observed& e) {
    for (int s = 0; s < 100; ++s)
        if (a.b[s] != e.b[s]) {
            auto name = [](int8_t pc) {
                if (!pc) return std::string("empty");
                if (orc::typ(pc) >= orc::NPT) return std::string("unknown piece");
                const char c = orc::kTypeChar[orc::typ(pc)];
                return std::string(1, orc::col(pc) == orc::kW ? char(std::toupper(c)) : c);
            };
            return "square " + orc::sqname(s) + ": engine " + name(a.b[s]) + ", rules " + name(e.b[s]);
        }
    if (a.stm != e.stm) return "side to move";
    for (int c = 0; c < 2; ++c)
        for (int k = 0; k < 2; ++k)
            if (a.castle[c][k] != e.castle[c][k])
                return std::string("castling right ") + (c ? "black " : "white ") + (k ? "queenside" : "kingside");
    if (a.ep != e.ep) {
        std::string s = "e.p. squares: engine {";
        for (int q : a.ep) s += orc::sqname(q) + " ";
        s += "} rules {";
        for (int q : e.ep) s += orc::sqname(q) + " ";
        return s + "}";
    }
    if (a.checks[0] != e.checks[0] || a.checks[1] != e.checks[1])
        return "checks remaining: engine " + std::to_string(a.checks[0]) + "+" + std::to_string(a.checks[1]) +
               ", rules " + std::to_string(e.checks[0]) + "+" + std::to_string(e.checks[1]);
    if (a.rule50 != e.rule50)
        return "rule-50 counter: engine " + std::to_string(a.rule50) + ", rules " + std::to_string(e.rule50);
    return "";
}

const char* result_name(lczero::GameResult r) {
    switch (r) {
        case lczero::GameResult::UNDECIDED: return "UNDECIDED";
        case lczero::GameResult::WHITE_WON: return "WHITE_WON";
        case lczero::GameResult::BLACK_WON: return "BLACK_WON";
        case lczero::GameResult::DRAW: return "DRAW";
    }
    return "?";
}

}  // namespace

// ============================================================================
void run_rules_oracle_audit(int num_games, int max_plies) {
    std::cout << "\n=== AUDIT-RULES: engine vs an independent re-implementation of the rules ===" << std::endl;
    const Variant* variant = setup_custom_variant();
    if (num_games <= 0) num_games = 100;
    if (max_plies <= 0) max_plies = 200;

    // Start positions. Besides the real one, positions that make the rare rules
    // (castling, e.p. with promotion, repetitions, the rule-50 limit, mate and
    // stalemate, the last check) frequent enough that every one is exercised.
    struct Start { const char* fen; bool shuffle; };
    const std::vector<Start> starts = {
        {lczero::ChessBoard::kStartposFen, false},
        {"1r3k2r1/2p4p2/10/4n5/10/10/5B4/10/2P4P2/1R3K2R1 w BIbi - 8+8 0 1", false},   // castling
        {"1r3k2r1/10/10/10/10/10/10/10/10/1R3K2R1 b BIbi - 8+8 0 1", false},           // castling, black first
        {"4k5/3s1s4/10/2P1S1P3/10/10/10/10/10/4K5 b - - 8+8 0 1", false},              // Black S double steps -> White e.p.(+promo)
        {"4k5/10/10/10/10/10/2p1s1p3/10/3S1S4/4K5 w - - 8+8 0 1", false},              // mirror
        {"4k5/10/4s5/10/3S6/10/10/10/10/4K5 b - - 8+8 0 1", false},                    // S e8-c6 / e8-e6, then S d6 takes e.p. (no promo)
        {"4k5/10/10/10/10/3s6/10/4S5/10/4K5 w - - 8+8 0 1", false},                    // mirror
        {"4k5/10/10/PPPPP5/10/10/ppppp5/10/10/4K5 w - - 8+8 0 1", false},              // promotions
        {"4k5/10/10/SSSS6/10/10/ssss6/10/10/4K5 w - - 8+8 0 1", false},                // Sergeant promotions
        {"k9/10/2K7/10/10/10/10/10/10/9Q w - - 9+9 0 1", false},                       // mates / stalemates
        {"n3k5/10/10/10/10/10/10/10/10/4K4N w - - 8+8 0 1", true},                     // repetitions, rule50 = 0
        {"n3k5/10/10/10/10/10/10/10/10/4K4N w - - 8+8 10 1", true},                    // repetitions across rule50 = 14
        {"n3k5/10/10/10/10/10/10/10/10/4K4N b - - 8+8 37 1", true},                    // repetitions, rule50 >= 14
        {"4k5/10/2m7/10/10/10/10/7M2/10/4K5 w - - 8+8 86 1", false},                   // rule-50 limit
        {"k9/10/2K7/10/10/10/10/10/10/10 b - - 8+8 0 1", false},                       // stalemate = loss
        {"k3R5/10/2K7/10/10/10/10/10/10/10 b - - 8+8 0 1", false},                     // checkmate
        {"k9/10/2K7/10/10/10/10/10/10/10 b - - 8+8 100 60", false},                    // stalemate on ply 100 = draw
        {"k3R5/10/2K7/10/10/10/10/10/10/10 b - - 8+8 100 60", false},                  // mate on ply 100 = loss
        {"k9/10/10/10/10/10/10/10/10/9K b - - 0+8 5 30", false},                       // White already gave 8 checks
        {"4k5/10/10/10/4N5/10/10/10/10/K3R5 w - - 2+8 0 1", false},                  // Ne6-d8/f8: double check = the last 2 checks
        {"4k5/10/10/10/4N5/10/10/10/10/K3R5 w - - 5+8 0 1", false},                  // double checks mid-count
    };

    std::mt19937_64 rng(0xFA1B5EEDULL);
    uint64_t positions = 0, moves_checked = 0, planes_checked = 0, keys_checked = 0;
    int failures = 0;
    std::map<std::string, uint64_t> cover;   // feature -> count (played or available)

    auto fail = [&](const std::string& what, const std::string& fen) {
        ++failures;
        if (failures <= 25) std::cerr << "[MISMATCH] " << what << "\n    FEN: " << fen << std::endl;
    };

    std::vector<orc::OMove> olegal;
    std::vector<float> dense_engine(226 * 100), dense_rules(226 * 100);

    for (int g = 0; g < num_games; ++g) {
        const Start& start = starts[static_cast<size_t>(g) % starts.size()];
        orc::OState ost;
        if (!orc::parse_fen(start.fen, ost)) {
            std::cerr << "[FAIL] oracle cannot read FEN " << start.fen << std::endl;
            std::exit(1);
        }
        auto history = std::make_unique<lczero::PositionHistory>();
        history->Reset(lczero::Position::FromFen(start.fen));

        std::vector<orc::OState> ohist{ost};
        std::vector<std::string> okeys{orc::rep_key(ost)};
        std::vector<int> oreps{0};
        std::vector<orc::OMove> oplayed;
        int last_checkers = 0;   // checking pieces after the last move played

        for (int ply = 0; ply <= max_plies; ++ply) {
            const Position& raw = history->Last().GetBoard().GetRawPosition();
            const std::string fen = raw.fen();
            const bool black = raw.side_to_move() == BLACK;
            ++positions;
            cover[black ? "positions, Black to move" : "positions, White to move"]++;

            // (0) The position itself.
            {
                const std::string d = diff(observe(raw), expected(ost));
                if (!d.empty()) { fail("position differs: " + d, fen); break; }
                if (history->Last().GetRule50Ply() != ost.rule50)
                    fail("lczero rule-50 ply " + std::to_string(history->Last().GetRule50Ply()) +
                         " != " + std::to_string(ost.rule50), fen);
            }

            // (1) Legal move set.
            orc::gen_legal(ost, olegal);
            std::vector<Move> elegal;
            for (const auto& em : MoveList<LEGAL>(raw)) elegal.push_back(em.move);
            std::map<uint32_t, orc::OMove> by_key;
            for (const auto& m : olegal) by_key[m.key()] = m;
            std::map<uint32_t, int> checks_of;   // move -> checking pieces after it (filled in (2))
            {
                std::map<uint32_t, Move> ekeys;
                for (Move m : elegal) ekeys[to_oracle(m).key()] = m;
                bool same = ekeys.size() == elegal.size() && by_key.size() == olegal.size();
                for (const auto& kv : ekeys)
                    if (!by_key.count(kv.first)) {
                        same = false;
                        fail("engine-only move " + orc::mname(to_oracle(kv.second)), fen);
                    }
                for (const auto& kv : by_key)
                    if (!ekeys.count(kv.first)) {
                        same = false;
                        fail("rules-only move " + orc::mname(kv.second), fen);
                    }
                if (!same) break;
            }
            // The adapter's canonical list is the same set, flipped for Black.
            {
                const lczero::MoveList canon = history->Last().GetBoard().GenerateLegalMoves();
                std::vector<uint32_t> a, b;
                for (const auto& m : canon) {
                    lczero::Move real = m;
                    if (black) real.Flip(RANK_10);
                    a.push_back(static_cast<uint32_t>(real.raw()));
                }
                for (Move m : elegal) b.push_back(static_cast<uint32_t>(m));
                std::sort(a.begin(), a.end());
                std::sort(b.begin(), b.end());
                if (a != b) fail("GenerateLegalMoves() != Fairy-Stockfish legal moves", fen);
            }

            // (2) Every legal move: resulting state, gives_check, undo.
            {
                StateInfo st0 = *raw.state();
                Position p;
                p.copy_from(raw, &st0);
                const Observed before = observe(p);
                const Key key_before = p.state()->key;
                const Bitboard checkers_before = p.checkers();
                for (Move m : elegal) {
                    const orc::OMove om = by_key[to_oracle(m).key()];
                    bool ogc = false;
                    int ochk = 0;
                    const orc::OState on = orc::apply(ost, om, &ogc, &ochk);
                    checks_of[om.key()] = ochk;
                    const bool egc = p.gives_check(m);
                    StateInfo st1;
                    p.do_move(m, st1);
                    ++moves_checked;
                    const std::string d = diff(observe(p), expected(on));
                    if (!d.empty()) fail("after " + orc::mname(om) + ": " + d, fen);
                    if (egc != ogc)
                        fail("gives_check(" + orc::mname(om) + ") = " + std::to_string(egc) +
                             ", rules say " + std::to_string(ogc), fen);
                    if (bool(p.checkers()) != orc::in_check(on))
                        fail("in-check after " + orc::mname(om) + " differs", fen);
                    if (ochk < 0)
                        fail("oracle self-check: its two attack computations disagree after " + orc::mname(om), fen);
                    else if (popcount(p.checkers()) != ochk)
                        fail("checking pieces after " + orc::mname(om) + ": engine " +
                             std::to_string(popcount(p.checkers())) + ", rules " + std::to_string(ochk), fen);
                    const bool special = om.kind != orc::KN_NORMAL || om.dbl || om.promo;
                    if (special) {   // incremental key == key from scratch
                        StateInfo qs;
                        Position q;
                        q.set(variant, p.fen(), false, &qs, nullptr);
                        ++keys_checked;
                        if (qs.key != p.state()->key)
                            fail("incremental key != key from FEN after " + orc::mname(om), fen);
                    }
                    p.undo_move(m);
                    const std::string u = diff(observe(p), before);
                    if (!u.empty() || p.state()->key != key_before || p.checkers() != checkers_before)
                        fail("undo_move(" + orc::mname(om) + ") did not restore: " +
                             (u.empty() ? std::string("key/checkers") : u), fen);

                    // Coverage of the rule being exercised.
                    const int mover = orc::typ(ost.b[om.from]);
                    if (om.kind == orc::KN_EP) {
                        std::string k = mover == orc::P_ ? "e.p. by pawn" :
                                        orc::fl(om.from) == orc::fl(om.to) ? "e.p. by sergeant, straight"
                                                                           : "e.p. by sergeant, diagonal";
                        cover[om.promo ? k + " + promotion" : k]++;
                        cover[ost.ep_two ? "e.p. of a sergeant double step" : "e.p. of a pawn double step"]++;
                    }
                    if (om.kind == orc::KN_PROMO) cover[mover == orc::P_ ? "promotion, pawn" : "promotion, sergeant"]++;
                    if (om.kind == orc::KN_CASTLE)
                        cover[std::string(black ? "castling black " : "castling white ") +
                              (orc::fl(om.to) > orc::fl(om.from) ? "kingside" : "queenside")]++;
                    if (om.dbl)
                        cover[mover == orc::P_ ? "double step, pawn" :
                              orc::fl(om.from) == orc::fl(om.to) ? "double step, sergeant straight"
                                                                 : "double step, sergeant diagonal"]++;
                    if (ogc) cover["move giving check"]++;
                    if (ochk >= 2) cover["move giving double check"]++;
                    if (mover == orc::K_ && std::abs(orc::fl(om.to) - orc::fl(om.from)) +
                                                std::abs(orc::rk(om.to) - orc::rk(om.from)) == 3 &&
                        om.kind != orc::KN_CASTLE)
                        cover["king knight-jump"]++;
                }
            }

            // (3) Game result and repetition count.
            const orc::OState& cur = ost;
            const lczero::GameResult eres = history->ComputeGameResult();
            const lczero::GameResult ores = orc::result_of(cur, oreps.back(), olegal.empty());
            if (history->Last().GetRepetitions() != oreps.back())
                fail("repetitions: engine " + std::to_string(history->Last().GetRepetitions()) +
                     ", rules " + std::to_string(oreps.back()) + " (rule50=" + std::to_string(cur.rule50) + ")", fen);
            if (eres != ores) {
                fail(std::string("game result: engine ") + result_name(eres) + ", rules " + result_name(ores) +
                     " (repetitions " + std::to_string(oreps.back()) + ", rule50 " + std::to_string(cur.rule50) + ")", fen);
                break;
            }
            if (oreps.back() >= 1) cover["repeated position"]++;

            // (4) NN input planes and the training record's scalar fields.
            {
                lczero::InputPlanes planes;
                int transform = 0;
                lczero::EncodePositionForNN(*history, lczero::kMoveHistory,
                                            lczero::FillEmptyHistory::FEN_ONLY, &planes, &transform);
                lczero::UnpackInputPlanes(planes, dense_engine.data(), 10, 10);
                orc::planes_of(ohist, oreps, dense_rules.data());
                ++planes_checked;
                for (int i = 0; i < 226 * 100; ++i)
                    if (dense_engine[i] != dense_rules[i]) {
                        fail("NN input plane " + std::to_string(i / 100) + " cell " + std::to_string(i % 100) +
                             ": engine " + std::to_string(dense_engine[i]) + ", rules " + std::to_string(dense_rules[i]), fen);
                        break;
                    }
                lczero::TrainingDataV1 rec;
                std::memset(&rec, 0, sizeof(rec));
                lczero::EncodePlanesIntoRecord(*history, rec);
                const int us = cur.stm, them = us ^ 1;
                auto file_or_none = [](bool right, int f) { return right ? uint8_t(f) : lczero::kNoCastlingFile; };
                if (rec.side_to_move != (us == orc::kB ? 1 : 0) ||
                    rec.rule50_count != std::min(cur.rule50, 255) ||
                    rec.checks_remaining_us != cur.checks[us] || rec.checks_remaining_them != cur.checks[them] ||
                    rec.castling_us_ooo_file != file_or_none(cur.castle[us][1], 1) ||
                    rec.castling_us_oo_file != file_or_none(cur.castle[us][0], 8) ||
                    rec.castling_them_ooo_file != file_or_none(cur.castle[them][1], 1) ||
                    rec.castling_them_oo_file != file_or_none(cur.castle[them][0], 8))
                    fail("training-record scalar fields differ from the rules", fen);
            }

            // (5) Policy index of every legal move.
            {
                const lczero::MoveList canon = history->Last().GetBoard().GenerateLegalMoves();
                std::vector<int> seen;
                for (const auto& m : canon) {
                    lczero::Move real = m;
                    if (black) real.Flip(RANK_10);
                    const auto it = by_key.find(to_oracle(real.raw()).key());
                    if (it == by_key.end()) continue;   // already reported above
                    const int want = orc::nn_index(it->second, black);
                    const int got = lczero::MoveToNNIndex(m, 0);
                    if (want < 0 || got != want)
                        fail("MoveToNNIndex(" + orc::mname(it->second) + ") = " + std::to_string(got) +
                             ", layout says " + std::to_string(want), fen);
                    seen.push_back(got);
                }
                std::sort(seen.begin(), seen.end());
                if (std::adjacent_find(seen.begin(), seen.end()) != seen.end())
                    fail("two legal moves share a policy index", fen);
            }

            if (ores != lczero::GameResult::UNDECIDED) {
                if (ores == lczero::GameResult::DRAW) cover[cur.rule50 >= 100 ? "end: rule-50 draw" : "end: repetition draw"]++;
                else if (cur.checks[orc::kW] <= 0 || cur.checks[orc::kB] <= 0) {
                    cover["end: last check"]++;
                    if (last_checkers >= 2) cover["end: last checks by a double check"]++;
                }
                else cover[orc::in_check(cur) ? "end: checkmate" : "end: stalemate"]++;
                break;
            }
            if (ply == max_plies) break;

            // (6) Pick and play a move: sometimes a special one, in "shuffle"
            // games often the move that undoes our previous one (repetitions).
            size_t pick = static_cast<size_t>(rng() % olegal.size());
            const double u = std::uniform_real_distribution<double>(0.0, 1.0)(rng);
            if (start.shuffle && oplayed.size() >= 2 && u < 0.7) {
                const orc::OMove& prev = oplayed[oplayed.size() - 2];
                for (size_t i = 0; i < olegal.size(); ++i)
                    if (olegal[i].from == prev.to && olegal[i].to == prev.from && olegal[i].kind == orc::KN_NORMAL) { pick = i; break; }
            } else if (u < 0.35) {
                std::vector<size_t> special;
                for (size_t i = 0; i < olegal.size(); ++i)
                    if (olegal[i].kind != orc::KN_NORMAL || olegal[i].dbl) special.push_back(i);
                if (!special.empty()) pick = special[static_cast<size_t>(rng() % special.size())];
            } else if (u < 0.5) {   // a checking move, preferring the most checking pieces
                int best = 0;
                for (size_t i = 0; i < olegal.size(); ++i) best = std::max(best, checks_of[olegal[i].key()]);
                std::vector<size_t> checking;
                for (size_t i = 0; i < olegal.size(); ++i)
                    if (best > 0 && checks_of[olegal[i].key()] == best) checking.push_back(i);
                if (!checking.empty()) pick = checking[static_cast<size_t>(rng() % checking.size())];
            }
            const orc::OMove om = olegal[pick];
            last_checkers = checks_of[om.key()];
            Move em = MOVE_NONE;
            for (Move m : elegal)
                if (to_oracle(m).key() == om.key()) em = m;
            lczero::Move canon(em);
            if (black) canon.Flip(RANK_10);
            history->Append(canon);
            ost = orc::apply(ost, om);
            oplayed.push_back(om);
            ohist.push_back(ost);
            const std::string k = orc::rep_key(ost);
            int reps = 0;
            for (const auto& prev : okeys) reps += (prev == k);
            okeys.push_back(k);
            oreps.push_back(reps);
            {   // the played move's key from scratch, whatever it was
                const Position& now = history->Last().GetBoard().GetRawPosition();
                StateInfo qs;
                Position q;
                q.set(variant, now.fen(), false, &qs, nullptr);
                ++keys_checked;
                if (qs.key != now.state()->key) fail("incremental key != key from FEN after the played move", fen);
            }
        }
    }

    std::cout << "  games=" << num_games << "  positions=" << positions << "  moves checked (do/undo)="
              << moves_checked << "  NN inputs checked=" << planes_checked << "  keys vs FEN=" << keys_checked << std::endl;
    std::cout << "  coverage:" << std::endl;
    for (const auto& kv : cover) std::cout << "    " << kv.first << ": " << kv.second << std::endl;

    // Every rule must actually have been exercised (no vacuous pass).
    const std::vector<std::string> required = {
        "positions, Black to move", "e.p. by pawn", "e.p. by sergeant, straight", "e.p. by sergeant, diagonal",
        "e.p. by pawn + promotion", "e.p. by sergeant, straight + promotion", "e.p. by sergeant, diagonal + promotion",
        "e.p. of a pawn double step", "e.p. of a sergeant double step",
        "promotion, pawn", "promotion, sergeant", "castling white kingside", "castling white queenside",
        "castling black kingside", "castling black queenside", "double step, pawn",
        "double step, sergeant straight", "double step, sergeant diagonal", "move giving check",
        "move giving double check",
        "king knight-jump", "repeated position", "end: repetition draw", "end: rule-50 draw",
        "end: last check", "end: checkmate", "end: stalemate"};
    for (const auto& r : required)
        if (!cover.count(r)) {
            std::cerr << "[FAIL] AUDIT-RULES never exercised: " << r << " (increase --games)" << std::endl;
            ++failures;
        }
    if (failures) {
        std::cerr << "[FAIL] AUDIT-RULES: " << failures << " mismatch(es)." << std::endl;
        std::exit(1);
    }
    std::cout << "[PASS] AUDIT-RULES: engine == independent rules over " << positions << " positions." << std::endl;
}
