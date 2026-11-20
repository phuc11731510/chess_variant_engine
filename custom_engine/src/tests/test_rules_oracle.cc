// Independent rules oracle for the 10x10 variant: --audit-rules.
//
// Every other movegen test compares the engine with ITSELF (adapter vs the raw
// Fairy-Stockfish position underneath, perft vs perft, FEN round-trips). They
// catch wrapping bugs, but a rule that Fairy-Stockfish implements differently
// from what the variant intends would pass all of them.
//
// This file re-implements the rules from their written description (see the
// table below and LUAT_BIEN_THE.md), with no code shared with Fairy-Stockfish, and
// plays random games through the production path (lczero::PositionHistory over
// Fairy-Stockfish). At every position it requires, exactly:
//   1. the legal move set (from, to, promotion piece, move kind);
//   2. for EVERY legal move: the resulting board, side to move, en-passant squares,
//      checks remaining, rule-50 counter and in-check flag, gives_check(), the number
//      of checking pieces, and that undo_move() restores the position and its key;
//   3. the incremental Zobrist key == the key of the same position set from FEN
//      (for the played move and for every special move);
//   4. PositionHistory::ComputeGameResult() and the repetition count;
//   5. the NN input planes (EncodePositionForNN + UnpackInputPlanes) and the
//      scalar fields of the training record;
//   6. MoveToNNIndex of every legal move (and injectivity);
//   7. the ASCII notation of every legal move: unique within the position, made only of
//      the characters a-j, 0-9 and one promotion letter, and parsed back to the same move.
//
// Rules as implemented here (White's view; Black mirrors, forward = down). "Move only" = never
// captures; "step" = one square. Leapers jump over pieces, the others are blocked as stated.
//   board 10x10 (a-j, 1-10). K = the royal piece ("Hoang gia"; Fairy-Stockfish
//   insists on the letter k): moves or captures one square in any of 8 directions;
//   in the ring of 16 squares around that 3x3 it only MOVES (to an empty square), and only when
//   not blocked: 2 straight (the square between empty), 2 diagonal (the square between
//   empty), a knight move (the square next to it in the long direction empty: the
//   Xiangqi horse). It attacks (can capture on, gives check on) only its 8 neighbours.
//   N knight (jumps); R rook; Q queen.
//   B (letter b) = bishop + a Wazir step (1 orthogonal) that only moves.
//   M (centaur) = king step + Xiangqi horse (blocked as above), both move and capture.
//   V (wildebeest) = camel leap (1,3) + knight leap, jumping.
//   Y (alibaba) = leaps (2,2) and (0,2)/(2,0), jumping, + a Wazir step that only moves.
//   C (cannon) = Xiangqi cannon (moves like a rook without capturing; captures by hopping
//   over exactly one piece of any colour along a rank/file onto the first piece behind it)
//   + a Wazir step that moves and captures.
//   G (grasshopper) = in the 8 queen directions: along the ray to the first piece, hops over it and
//   lands on the square right behind it (empty: a move, enemy: a capture) + a king step.
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
//   Promotion (P and S, two tiers): reaching rank 8 (Black: 3) the piece may stay as it is
//      or become N, B, Y, C or G; reaching rank 9 (Black: 2) it must become one of
//      N, B, R, Q, M, V, Y, C, G. This includes captures and en-passant captures.
//   No castling.
//   Checks: after each move, every piece of the mover that attacks the
//      opponent's king counts one check (a single check 1, a double check 2).
//      7 checks win immediately, before any other rule.
//   No legal move (checkmate or stalemate) loses. 100 plies without a capture,
//      a P/S move or a promotion draws unless the side to move is checkmated.
//      A position occurring for the third time draws (position = board, side to
//      move, en-passant state, checks remaining).

#include "tests/test_common.h"

#include <cctype>
#include <set>

namespace {
namespace orc {

enum : int8_t { E_ = 0, P_ = 1, N_, R_, Q_, K_, B_, M_, V_, Y_, S_, C_, G_, NPT };
constexpr int kW = 0, kB = 1;
const char* kTypeChar = ".pnrqkbmvyscg";   // index = type

inline int sq_of(int f, int r) { return r * 10 + f; }
inline int fl(int s) { return s % 10; }
inline int rk(int s) { return s / 10; }
inline bool on_board(int f, int r) { return f >= 0 && f < 10 && r >= 0 && r < 10; }
inline int col(int8_t pc) { return pc > 0 ? kW : kB; }
inline int typ(int8_t pc) { return pc > 0 ? pc : -pc; }
inline int8_t mk(int c, int t) { return static_cast<int8_t>(c == kW ? t : -t); }
inline int sgn(int v) { return (v > 0) - (v < 0); }

const int kKnight[8][2] = {{1, 2}, {2, 1}, {2, -1}, {1, -2}, {-1, -2}, {-2, -1}, {-2, 1}, {-1, 2}};
const int kCamel[8][2] = {{1, 3}, {3, 1}, {3, -1}, {1, -3}, {-1, -3}, {-3, -1}, {-3, 1}, {-1, 3}};
const int kKStep[8][2] = {{0, 1}, {1, 1}, {1, 0}, {1, -1}, {0, -1}, {-1, -1}, {-1, 0}, {-1, 1}};
const int kAlfil[4][2] = {{2, 2}, {2, -2}, {-2, -2}, {-2, 2}};
const int kDabbaba[4][2] = {{0, 2}, {2, 0}, {0, -2}, {-2, 0}};
const int kOrth[4][2] = {{0, 1}, {1, 0}, {0, -1}, {-1, 0}};
const int kDiag[4][2] = {{1, 1}, {1, -1}, {-1, -1}, {-1, 1}};
const int8_t kPromosAll[9] = {N_, B_, R_, Q_, M_, V_, Y_, C_, G_};   // rank 9 (Black 2): compulsory
const int8_t kPromosOpt[5] = {N_, B_, Y_, C_, G_};                   // rank 8 (Black 3): a choice

struct OState {
    int8_t b[100];
    int stm = kW;
    int ep_mid = -1, ep_victim = -1;   // passed square / square of the double-stepper
    bool ep_two = false;               // Fairy-Stockfish also marks the victim square (Sergeant)
    int checks[2] = {7, 7};
    int rule50 = 0;
};

enum Kind : uint8_t { KN_NORMAL = 0, KN_EP = 1, KN_PROMO = 2, KN_OTHER = 7 };

struct OMove {
    int8_t from = 0, to = 0;
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
    return s;
}

int find_king(const OState& st, int c) {
    const int8_t k = mk(c, K_);
    for (int s = 0; s < 100; ++s)
        if (st.b[s] == k) return s;
    return -1;
}

// Does the piece on square p attack square s, i.e. could it capture an enemy piece standing on s? (Whether
// something stands there does not matter: the hopping pieces need the screen, not the target.)
bool piece_attacks(const OState& st, int p, int s) {
    const int8_t pc = st.b[p];
    if (!pc || p == s) return false;
    const int t = typ(pc);
    const int df = fl(s) - fl(p), dr = rk(s) - rk(p);
    const int adf = std::abs(df), adr = std::abs(dr);
    const int fwd = col(pc) == kW ? 1 : -1;
    auto empty_at = [&](int f, int r) { return on_board(f, r) && !st.b[sq_of(f, r)]; };
    const bool kstep = std::max(adf, adr) == 1;
    const bool knight = (adf == 1 && adr == 2) || (adf == 2 && adr == 1);
    // Xiangqi horse: the square next to the piece in the long direction must be empty.
    const bool horse_ok = knight && empty_at(fl(p) + (adf == 2 ? sgn(df) : 0), rk(p) + (adr == 2 ? sgn(dr) : 0));
    const bool orth = (df == 0) != (dr == 0), diag = adf == adr && adf != 0;
    // The pieces strictly between p and s along a rank, file or diagonal; `last` = the square just before s holds one.
    auto between = [&](int& n, bool& last) {
        const int sf = sgn(df), sr = sgn(dr);
        n = 0;
        last = false;
        for (int f = fl(p) + sf, r = rk(p) + sr; f != fl(s) || r != rk(s); f += sf, r += sr) {
            if (st.b[sq_of(f, r)]) ++n;
            last = st.b[sq_of(f, r)] != 0 && f + sf == fl(s) && r + sr == rk(s);
        }
    };
    switch (t) {
        case P_: return dr == fwd && adf == 1;
        case S_: return dr == fwd && adf <= 1;
        case N_: return knight;
        case K_: return kstep;
        case R_: case Q_: case B_: {
            const bool line = ((t == R_ || t == Q_) && orth) || ((t == B_ || t == Q_) && diag);
            if (!line) return false;
            int n; bool last;
            between(n, last);
            return n == 0;
        }
        case M_: return kstep || horse_ok;
        case V_: return knight || (adf == 1 && adr == 3) || (adf == 3 && adr == 1);
        case Y_: return (adf == 2 && adr == 2) || (adf == 2 && adr == 0) || (adf == 0 && adr == 2);
        case C_: {
            if (adf + adr == 1) return true;                 // the Wazir step
            if (!orth) return false;
            int n; bool last;
            between(n, last);
            return n == 1;                                   // exactly one screen
        }
        case G_: {
            if (kstep) return true;
            if (!(orth || diag)) return false;
            int n; bool last;
            between(n, last);
            return n == 1 && last;                           // the one piece in the way is the one right before s
        }
        default: return false;
    }
}

// Is square s attacked by colour c (as if an enemy piece stood on it)?
bool attacked(const OState& st, int s, int c) {
    for (int p = 0; p < 100; ++p)
        if (st.b[p] && col(st.b[p]) == c && piece_attacks(st, p, s)) return true;
    return false;
}

bool in_check(const OState& st) {
    const int k = find_king(st, st.stm);
    return k >= 0 && attacked(st, k, st.stm ^ 1);
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
    // Promotion tiers: rank 8 (index 7; Black: index 2) a choice, rank 9 and 10 (Black: 2, 1) compulsory.
    auto compulsory_zone = [&](int r) { return us == kW ? r >= 8 : r <= 1; };
    auto optional_zone = [&](int r) { return us == kW ? r == 7 : r == 2; };
    auto dbl_region = [&](int r) { return us == kW ? r <= 2 : r >= 7; };
    auto add = [&](int from, int to, int8_t promo, uint8_t kind, bool dbl) {
        OMove m; m.from = int8_t(from); m.to = int8_t(to); m.promo = promo; m.kind = kind; m.dbl = dbl;
        out.push_back(m);
    };
    auto add_pawnlike = [&](int from, int to, bool ep) {
        const int r = rk(to);
        if (compulsory_zone(r)) {
            for (int8_t p : kPromosAll) add(from, to, p, ep ? KN_EP : KN_PROMO, false);
        } else if (optional_zone(r)) {
            add(from, to, 0, ep ? KN_EP : KN_NORMAL, false);
            for (int8_t p : kPromosOpt) add(from, to, p, ep ? KN_EP : KN_PROMO, false);
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
            continue;
        }
        if (t == S_) {
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
            continue;
        }
        // Every other piece: collect its destination squares (a square reached two ways is ONE move).
        bool dest[100] = {};
        auto empty = [&](int ff, int rr) { return on_board(ff, rr) && !st.b[sq_of(ff, rr)]; };
        auto enemy = [&](int ff, int rr) { return on_board(ff, rr) && st.b[sq_of(ff, rr)] && col(st.b[sq_of(ff, rr)]) == them; };
        auto move_capture = [&](int ff, int rr) { if (empty(ff, rr) || enemy(ff, rr)) dest[sq_of(ff, rr)] = true; };
        auto move_only = [&](int ff, int rr) { if (empty(ff, rr)) dest[sq_of(ff, rr)] = true; };
        auto horse = [&](bool capture) {   // Xiangqi horse: the square next to it in the long direction is empty
            for (const auto& d : kKnight)
                if (empty(f + (std::abs(d[0]) == 2 ? sgn(d[0]) : 0), r + (std::abs(d[1]) == 2 ? sgn(d[1]) : 0))) {
                    if (capture) move_capture(f + d[0], r + d[1]);
                    else move_only(f + d[0], r + d[1]);
                }
        };
        auto slide = [&](const int (*dirs)[2], int n) {
            for (int i = 0; i < n; ++i)
                for (int k = 1;; ++k) {
                    const int ff = f + dirs[i][0] * k, rr = r + dirs[i][1] * k;
                    if (!on_board(ff, rr)) break;
                    if (st.b[sq_of(ff, rr)]) { if (enemy(ff, rr)) dest[sq_of(ff, rr)] = true; break; }
                    dest[sq_of(ff, rr)] = true;
                }
        };
        auto wazir = [&](bool capture) {
            for (const auto& d : kOrth) {
                if (capture) move_capture(f + d[0], r + d[1]);
                else move_only(f + d[0], r + d[1]);
            }
        };
        switch (t) {
            case N_: for (const auto& d : kKnight) move_capture(f + d[0], r + d[1]); break;
            case R_: slide(kOrth, 4); break;
            case Q_: slide(kOrth, 4); slide(kDiag, 4); break;
            case K_:
                for (const auto& d : kKStep) move_capture(f + d[0], r + d[1]);
                for (const auto& d : kDabbaba) if (empty(f + d[0] / 2, r + d[1] / 2)) move_only(f + d[0], r + d[1]);
                for (const auto& d : kAlfil) if (empty(f + d[0] / 2, r + d[1] / 2)) move_only(f + d[0], r + d[1]);
                horse(false);
                break;
            case B_: slide(kDiag, 4); wazir(false); break;
            case M_: for (const auto& d : kKStep) move_capture(f + d[0], r + d[1]); horse(true); break;
            case V_:
                for (const auto& d : kKnight) move_capture(f + d[0], r + d[1]);
                for (const auto& d : kCamel) move_capture(f + d[0], r + d[1]);
                break;
            case Y_:
                for (const auto& d : kAlfil) move_capture(f + d[0], r + d[1]);
                for (const auto& d : kDabbaba) move_capture(f + d[0], r + d[1]);
                wazir(false);
                break;
            case C_:
                for (const auto& d : kOrth) {
                    int k = 1;
                    for (;; ++k) {   // quiet moves up to the first piece (the screen)
                        const int ff = f + d[0] * k, rr = r + d[1] * k;
                        if (!on_board(ff, rr)) break;
                        if (st.b[sq_of(ff, rr)]) break;
                        dest[sq_of(ff, rr)] = true;
                    }
                    for (++k;; ++k) {   // behind the screen: the first piece, if an enemy, is captured
                        const int ff = f + d[0] * k, rr = r + d[1] * k;
                        if (!on_board(ff, rr)) break;
                        if (st.b[sq_of(ff, rr)]) { if (enemy(ff, rr)) dest[sq_of(ff, rr)] = true; break; }
                    }
                }
                wazir(true);
                break;
            case G_:
                for (const auto& d : kKStep) move_capture(f + d[0], r + d[1]);
                for (const auto& d : kKStep) {
                    int k = 1;
                    while (empty(f + d[0] * k, r + d[1] * k)) ++k;         // to the screen
                    if (!on_board(f + d[0] * k, r + d[1] * k)) continue;    // no screen on this ray
                    move_capture(f + d[0] * (k + 1), r + d[1] * (k + 1));   // right behind it
                }
                break;
            default: break;
        }
        for (int to = 0; to < 100; ++to)
            if (dest[to]) add(s, to, 0, KN_NORMAL, false);
    }
}

// Plays m (assumed pseudo-legal). Counts the checks it gives: one per checking
// piece. *checkers gets that number.
OState apply(const OState& st, const OMove& m, bool* gives_check = nullptr, int* checkers = nullptr) {
    OState n = st;
    const int us = st.stm, them = us ^ 1;
    const int8_t pc = st.b[m.from];
    const int t = typ(pc);
    n.ep_mid = n.ep_victim = -1;
    n.ep_two = false;
    bool capture = st.b[m.to] != 0;
    if (m.kind == KN_EP) { n.b[st.ep_victim] = 0; capture = true; }
    n.b[m.to] = m.promo ? mk(us, m.promo) : pc;
    n.b[m.from] = 0;
    if (m.dbl) {
        n.ep_mid = (m.from + m.to) / 2;
        n.ep_victim = m.to;
        n.ep_two = (t == S_);
    }
    n.rule50 = (capture || t == P_ || t == S_) ? 0 : st.rule50 + 1;
    n.stm = them;
    const int ks = find_king(n, them);
    const int nchk = ks >= 0 ? attackers_count(n, ks, us) : 0;
    if (nchk > 0) n.checks[us] = std::max(n.checks[us] - nchk, 0);
    if (gives_check) *gives_check = nchk > 0;
    if (checkers) *checkers = nchk;
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
// Black is to move): promotions 88 + piece*3 + (dx+1) with pieces N B R Q M V Y C G;
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
            case N_: pi = 0; break; case B_: pi = 1; break; case R_: pi = 2; break;
            case Q_: pi = 3; break; case M_: pi = 4; break; case V_: pi = 5; break;
            case Y_: pi = 6; break; case C_: pi = 7; break; case G_: pi = 8; break;
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

bool parse_fen(const std::string& fen, OState& st);

// Dense [kInputPlanes][100] NN input for the current position, lc0 layout (see encoder.h).
void planes_of(const std::vector<OState>& hist, const std::vector<int>& reps, float* dense) {
    std::fill(dense, dense + lczero::kInputPlanes * 100, 0.0f);
    const OState& cur = hist.back();
    const int us = cur.stm, them = us ^ 1;
    auto canon = [&](int s) { return (us == kB ? 9 - rk(s) : rk(s)) * 10 + fl(s); };
    // The plane of each piece type within the 12 of one side: P N R Q K, then b m v y s c g.
    static const int plane_of_type[NPT] = {-1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11};
    const int n = static_cast<int>(hist.size());
    // lc0 ALWAYS: every history board that does not exist yet is a copy of the first position of the game.
    for (int d = 0; d < 8; ++d) {
        const OState& h = hist[d < n ? n - 1 - d : 0];
        for (int s = 0; s < 100; ++s) {
            const int8_t pc = h.b[s];
            if (!pc) continue;
            const int pl = d * lczero::kPlanesPerBoard + (col(pc) == us ? 0 : lczero::kPieceKinds) + plane_of_type[typ(pc)];
            dense[pl * 100 + canon(s)] = 1.0f;
        }
        if (reps[d < n ? n - 1 - d : 0] >= 1)
            std::fill(dense + (d * lczero::kPlanesPerBoard + 2 * lczero::kPieceKinds) * 100,
                      dense + (d * lczero::kPlanesPerBoard + 2 * lczero::kPieceKinds + 1) * 100, 1.0f);
    }
    auto set = [&](int p, int s) { dense[(lczero::kAuxPlaneBase + p) * 100 + canon(s)] = 1.0f; };
    auto fill = [&](int p, float v) { std::fill(dense + (lczero::kAuxPlaneBase + p) * 100, dense + (lczero::kAuxPlaneBase + p + 1) * 100, v); };
    if (cur.ep_mid >= 0) {
        set(lczero::kAuxEnPassant, cur.ep_mid);
        if (cur.ep_two) set(lczero::kAuxEnPassant, cur.ep_victim);
    }
    fill(lczero::kAuxRule50, static_cast<float>(cur.rule50) / 100.0f);
    fill(lczero::kAuxChecksUs, static_cast<float>(cur.checks[us]) / 10.0f);
    fill(lczero::kAuxChecksThem, static_cast<float>(cur.checks[them]) / 10.0f);
}

// FEN reader, independent of Fairy-Stockfish's.
bool parse_fen(const std::string& fen, OState& st) {
    std::istringstream ss(fen);
    std::string place, side, castling, ep, checks;
    int r50 = 0, fullmove = 1;
    if (!(ss >> place >> side >> castling >> ep >> checks)) return false;
    ss >> r50 >> fullmove;
    if (castling != "-") return false;   // no castling in this game
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
        case PAWN: return orc::P_;   case KNIGHT: return orc::N_;   case ROOK: return orc::R_;
        case QUEEN: return orc::Q_;  case KING: return orc::K_;
        case CUSTOM_PIECE_1: return orc::B_; case CUSTOM_PIECE_2: return orc::M_;
        case CUSTOM_PIECE_3: return orc::V_; case CUSTOM_PIECE_4: return orc::Y_;
        case CUSTOM_PIECE_5: return orc::S_; case CUSTOM_PIECE_6: return orc::C_;
        case CUSTOM_PIECE_7: return orc::G_;
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
    if (max_plies <= 0) max_plies = 200;
    // The oracle implements the rule text; the engine's rules come from the variant definition. A changed
    // definition must fail here by name, not as mismatches.
    if (variant->castling || !variant->checkCounting || !variant->mandatoryPawnPromotion) {
        std::cerr << "[FAIL] AUDIT-RULES: the variant's definition (castling = false, checkCounting, "
                     "mandatoryPawnPromotion) is not the rule this oracle implements; update "
                     "test_rules_oracle.cc and LUAT_BIEN_THE.md with it" << std::endl;
        std::exit(1);
    }

    // Start positions. Besides the real one, positions that make the rare rules
    // (e.p. with promotion, the promotion tiers, the hopping pieces, repetitions, the rule-50 limit, mate and
    // stalemate, the last check) frequent enough that every one is exercised.
    struct Start { const char* fen; bool shuffle; };
    const std::vector<Start> starts = {
        {lczero::ChessBoard::kStartposFen, false},
        {"k9/10/2p1p5/10/3C2g3/10/4P1P3/10/10/K9 w - - 7+7 0 1", false},               // Cannon and Grasshopper with screens
        {"k9/1b1m1y1v2/10/10/10/10/10/10/1B1M1Y1V2/K9 w - - 7+7 0 1", false},          // every other piece, both sides
        {"k9/1b1m1y1v2/10/10/10/10/10/10/1B1M1Y1V2/K9 b - - 7+7 0 1", false},          // same, Black first
        {"4k5/3s1s4/10/2P1S1P3/10/10/10/10/10/4K5 b - - 7+7 0 1", false},              // Black S double steps -> White e.p.(+promo)
        {"4k5/10/10/10/10/10/2p1s1p3/10/3S1S4/4K5 w - - 7+7 0 1", false},              // mirror
        {"4k5/10/4s5/10/3S6/10/10/10/10/4K5 b - - 7+7 0 1", false},                    // S e8-c6 / e8-e6, then S d6 takes e.p. (no promo)
        {"4k5/10/10/10/10/3s6/10/4S5/10/4K5 w - - 7+7 0 1", false},                    // mirror
        {"4k5/10/10/PPPPP5/10/10/ppppp5/10/10/4K5 w - - 7+7 0 1", false},              // pawns to rank 8 (a choice) / rank 4 -> 3
        {"4k5/10/PPPPP5/10/10/10/10/ppppp5/10/4K5 w - - 7+7 0 1", false},              // pawns to rank 9 (compulsory) / rank 3 -> 2
        {"4k5/10/10/SSSS6/10/10/ssss6/10/10/4K5 w - - 7+7 0 1", false},                // Sergeants to rank 8 / 3
        {"4k5/10/SSSS6/10/10/10/10/ssss6/10/4K5 w - - 7+7 0 1", false},                // Sergeants to rank 9 / 2
        {"k9/2Q7/7R2/10/10/10/10/10/10/9K b - - 7+7 0 1", false},                      // stalemate = loss
        {"k9/1Q8/2K7/10/10/10/10/10/10/10 b - - 7+7 0 1", false},                      // checkmate
        {"k9/9Q/9R/10/10/10/10/10/10/9K w - - 7+7 0 1", false},                        // mates / stalemates from a few pieces
        {"n3k5/10/10/10/10/10/10/10/10/4K4N w - - 7+7 0 1", true},                     // repetitions, rule50 = 0
        {"n3k5/10/10/10/10/10/10/10/10/4K4N w - - 7+7 10 1", true},                    // repetitions across rule50 = 14
        {"n3k5/10/10/10/10/10/10/10/10/4K4N b - - 7+7 37 1", true},                    // repetitions, rule50 >= 14
        {"4k5/10/2m7/10/10/10/10/7M2/10/4K5 w - - 7+7 86 1", false},                   // rule-50 limit
        {"k9/2Q7/7R2/10/10/10/10/10/10/9K b - - 7+7 100 60", false},                   // stalemate on ply 100 = draw
        {"k9/1Q8/2K7/10/10/10/10/10/10/10 b - - 7+7 100 60", false},                   // mate on ply 100 = loss
        {"k9/10/10/10/10/10/10/10/10/9K b - - 0+7 5 30", false},                       // White already gave 7 checks
        {"4k5/10/10/10/4N5/10/10/10/10/K3R5 w - - 2+7 0 1", false},                    // Ne6-d8/f8: double check = the last 2 checks
        {"4k5/10/10/10/4N5/10/10/10/10/K3R5 w - - 5+7 0 1", false},                    // double checks mid-count
        {"k9/4s5/10/3P6/10/10/10/10/10/K9 b - - 7+7 0 1", false},                      // S e9-e7 straight, P d7 takes e.p. on e8 (a choice)
        {"k9/4s5/10/5P4/10/10/10/10/10/K9 b - - 7+7 0 1", false},                      // same, P f7
        {"k9/4s5/10/3P1P4/10/10/10/10/10/K9 b - - 7+7 0 1", false},                    // same, P d7 and f7
        {"k9/4s5/10/4P5/10/10/10/10/10/K9 b - - 7+7 0 1", false},                      // S e9-c7 / e9-g7 diagonal, P e7 takes e.p. on d8 / f8
        {"k9/4s5/10/4P5/10/10/10/10/10/K9 b - - 7+7 0 1", false},                      // same (another random game)
        {"k3s5/10/3P6/10/10/10/10/10/10/K9 b - - 7+7 0 1", false},                     // S e10-e8, P d8 takes e.p. on e9 (compulsory)
        {"k3s5/10/3P1P4/10/10/10/10/10/10/K9 b - - 7+7 0 1", false},                   // same, P d8 and f8
        {"R1M1k5/10/10/10/10/4C5/10/10/10/9K w - - 7+7 0 1", false},                   // Cc10-e9: check by the Centaur + discovered Rook + Cannon with it as screen = a triple check
        {"k3c4g/10/3p1p4/10/2G3C3/10/3P1P4/10/1c6g1/K9 w - - 7+7 0 1", false},         // Cannons and Grasshoppers of both sides, own and enemy screens
        {"k3c4g/10/3p1p4/10/2G3C3/10/3P1P4/10/1c6g1/K9 b - - 7+7 0 1", false},         // same, Black first
        {"k3s5/10/4P5/10/10/10/10/10/10/K9 b - - 7+7 0 1", false},                     // S e10-c8 / e10-g8 diagonal, P e8 takes e.p. on d9 / f9 (compulsory)
        {"k9/4s5/10/4P5/10/10/10/10/10/K9 b - - 7+7 0 1", false},                      // S e9-c7 / e9-g7 diagonal (third game)
        {"k9/4s5/10/4P5/10/10/10/10/10/K9 b - - 7+7 0 1", false},                      // (fourth game)
    };

    // By default 5 games from every start (the RNG is seeded: the same games each run).
    if (num_games <= 0) num_games = 5 * static_cast<int>(starts.size());

    std::mt19937_64 rng(0xFA1B5EEDULL);
    uint64_t positions = 0, moves_checked = 0, planes_checked = 0, keys_checked = 0, notations_checked = 0;
    int failures = 0;
    std::map<std::string, uint64_t> cover;   // feature -> count (played or available)

    auto fail = [&](const std::string& what, const std::string& fen) {
        ++failures;
        if (failures <= 25) std::cerr << "[MISMATCH] " << what << "\n    FEN: " << fen << std::endl;
    };

    // The ASCII notation of a move: from-square, to-square, optionally one promotion letter. A square is a
    // file letter a-j and a rank 1-10. Returns whether `s` is of that form; sets `promo` to the letter or 0.
    auto notation_ok = [](const std::string& s, char& promo) {
        size_t i = 0;
        auto square = [&]() {
            if (i >= s.size() || s[i] < 'a' || s[i] > 'j') return false;
            ++i;
            size_t digits = 0;
            while (i < s.size() && std::isdigit(static_cast<unsigned char>(s[i])) && digits < 2) { ++i; ++digits; }
            return digits >= 1;
        };
        promo = 0;
        if (!square() || !square()) return false;
        if (i < s.size()) {
            if (std::string("nbrqmvycg").find(s[i]) == std::string::npos) return false;
            promo = s[i++];
        }
        return i == s.size();
    };

    std::vector<orc::OMove> olegal;
    std::vector<float> dense_engine(lczero::kInputPlanes * 100), dense_rules(lczero::kInputPlanes * 100);

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
                    if (popcount(p.checkers()) != ochk)
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
                    const int dx = std::abs(orc::fl(om.to) - orc::fl(om.from)), dy = std::abs(orc::rk(om.to) - orc::rk(om.from));
                    const bool captured = ost.b[om.to] != 0 || om.kind == orc::KN_EP;
                    if (om.kind == orc::KN_EP) {
                        std::string k = mover == orc::P_ ? "e.p. by pawn" :
                                        orc::fl(om.from) == orc::fl(om.to) ? "e.p. by sergeant, straight"
                                                                           : "e.p. by sergeant, diagonal";
                        cover[om.promo ? k + " + promotion" : k]++;
                        cover[ost.ep_two ? "e.p. of a sergeant double step" : "e.p. of a pawn double step"]++;
                    }
                    if (om.promo) {
                        const int zone_rank = black ? 2 : 7;
                        cover[orc::rk(om.to) == zone_rank ? "promotion on rank 8/3 (a choice)" : "promotion on rank 9/2 (compulsory)"]++;
                        cover[std::string("promotion to ") + orc::kTypeChar[om.promo]]++;
                    }
                    if (om.kind == orc::KN_PROMO) cover[mover == orc::P_ ? "promotion, pawn" : "promotion, sergeant"]++;
                    if ((mover == orc::P_ || mover == orc::S_) && !om.promo && orc::rk(om.to) == (black ? 2 : 7))
                        cover["promotion declined on rank 8/3"]++;
                    if (om.dbl)
                        cover[mover == orc::P_ ? "double step, pawn" :
                              orc::fl(om.from) == orc::fl(om.to) ? "double step, sergeant straight"
                                                                 : "double step, sergeant diagonal"]++;
                    if (ogc) cover["move giving check"]++;
                    if (ochk >= 2) cover["move giving double check"]++;
                    if (ochk >= 3) cover["move giving triple check"]++;
                    {   // which pieces give the check (the hopping ones need a screen: it can appear or vanish)
                        const int ks = orc::find_king(on, on.stm);
                        for (int pp = 0; ks >= 0 && pp < 100; ++pp)
                            if (on.b[pp] && orc::col(on.b[pp]) == ost.stm && orc::piece_attacks(on, pp, ks)) {
                                const int ct = orc::typ(on.b[pp]);
                                if (ct == orc::C_) cover["check by a cannon"]++;
                                if (ct == orc::G_) cover["check by a grasshopper"]++;
                                if ((ct == orc::C_ || ct == orc::G_) && pp != om.to) cover["check by a cannon or grasshopper that did not move"]++;
                            }
                    }
                    if (mover == orc::K_ && std::max(dx, dy) == 2) cover["royal ring move (2 squares away)"]++;
                    if (mover == orc::M_ && ((dx == 1 && dy == 2) || (dx == 2 && dy == 1))) cover["centaur horse move"]++;
                    if ((mover == orc::B_ || mover == orc::Y_) && dx + dy == 1) cover["wazir step of bishop / alibaba"]++;
                    if (mover == orc::C_ && captured && dx + dy > 1) cover["cannon capture over a screen"]++;
                    if (mover == orc::G_ && std::max(dx, dy) >= 2)
                        cover[captured ? "grasshopper hop capture" : "grasshopper hop move"]++;
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
                                            lczero::FillEmptyHistory::ALWAYS, &planes, &transform);
                lczero::UnpackInputPlanes(planes, dense_engine.data(), 10, 10);
                orc::planes_of(ohist, oreps, dense_rules.data());
                ++planes_checked;
                for (int i = 0; i < lczero::kInputPlanes * 100; ++i)
                    if (dense_engine[i] != dense_rules[i]) {
                        fail("NN input plane " + std::to_string(i / 100) + " cell " + std::to_string(i % 100) +
                             ": engine " + std::to_string(dense_engine[i]) + ", rules " + std::to_string(dense_rules[i]), fen);
                        break;
                    }
                lczero::TrainingDataV1 rec;
                std::memset(&rec, 0, sizeof(rec));
                lczero::EncodePlanesIntoRecord(*history, rec);
                const int us = cur.stm, them = us ^ 1;
                if (rec.side_to_move != (us == orc::kB ? 1 : 0) ||
                    rec.rule50_count != std::min(cur.rule50, 255) ||
                    rec.checks_remaining_us != cur.checks[us] || rec.checks_remaining_them != cur.checks[them])
                    fail("training-record scalar fields differ from the rules", fen);
            }

            // (5) Policy index and ASCII notation of every legal move.
            {
                const lczero::MoveList canon = history->Last().GetBoard().GenerateLegalMoves();
                std::vector<int> seen;
                std::set<std::string> notations;
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

                    // Notation: the engine's string (UCI::move), the adapter's (MoveToString), the form
                    // [a-j][1-10][a-j][1-10][promotion letter], a promotion letter exactly for a promotion, and
                    // read back (UCI::to_move, ParseMove) to the very same move.
                    const std::string s = UCI::move(raw, real.raw());
                    ++notations_checked;
                    char promo = 0;
                    if (!notation_ok(s, promo))
                        fail("notation of " + orc::mname(it->second) + " is not ASCII squares + one promotion letter: '" + s + "'", fen);
                    else if ((promo != 0) != (it->second.promo != 0) ||
                             (promo && promo != orc::kTypeChar[it->second.promo]))
                        fail("notation '" + s + "' does not carry the promotion of " + orc::mname(it->second), fen);
                    if (history->Last().GetBoard().MoveToString(m) != s)
                        fail("MoveToString(" + orc::mname(it->second) + ") differs from UCI::move: '" + s + "'", fen);
                    if (!notations.insert(s).second) fail("two legal moves are written '" + s + "'", fen);
                    std::string back_in = s;
                    if (UCI::to_move(raw, back_in) != real.raw())
                        fail("UCI::to_move('" + s + "') is not " + orc::mname(it->second), fen);
                    const lczero::Move parsed = history->Last().GetBoard().ParseMove(s);
                    if (parsed.raw() != m.raw())
                        fail("ParseMove('" + s + "') is not the canonical move " + orc::mname(it->second), fen);
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
            } else if (u < 0.35) {   // a special move; an e.p. capture first, as it only lasts one move
                std::vector<size_t> special, ep;
                for (size_t i = 0; i < olegal.size(); ++i) {
                    if (olegal[i].kind != orc::KN_NORMAL || olegal[i].dbl) special.push_back(i);
                    if (olegal[i].kind == orc::KN_EP) ep.push_back(i);
                }
                if (!ep.empty()) special.swap(ep);
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
              << moves_checked << "  NN inputs checked=" << planes_checked << "  keys vs FEN=" << keys_checked
              << "  notations=" << notations_checked << std::endl;
    std::cout << "  coverage:" << std::endl;
    for (const auto& kv : cover) std::cout << "    " << kv.first << ": " << kv.second << std::endl;

    // Every rule must actually have been exercised (no vacuous pass).
    const std::vector<std::string> required = {
        "positions, Black to move", "e.p. by pawn", "e.p. by sergeant, straight", "e.p. by sergeant, diagonal",
        "e.p. by pawn + promotion", "e.p. by sergeant, straight + promotion", "e.p. by sergeant, diagonal + promotion",
        "e.p. of a pawn double step", "e.p. of a sergeant double step",
        "promotion, pawn", "promotion, sergeant", "promotion on rank 8/3 (a choice)", "promotion on rank 9/2 (compulsory)",
        "promotion declined on rank 8/3", "promotion to n", "promotion to b", "promotion to r", "promotion to q",
        "promotion to m", "promotion to v", "promotion to y", "promotion to c", "promotion to g",
        "double step, pawn", "double step, sergeant straight", "double step, sergeant diagonal",
        "move giving check", "move giving double check", "move giving triple check", "check by a cannon", "check by a grasshopper",
        "check by a cannon or grasshopper that did not move",
        "royal ring move (2 squares away)", "centaur horse move", "wazir step of bishop / alibaba",
        "cannon capture over a screen", "grasshopper hop move", "grasshopper hop capture",
        "repeated position", "end: repetition draw", "end: rule-50 draw",
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
