"""Tests of thong_ke_doi.py: the two per-generation statistics computed from training records.

  A. Hand-built records: the move-index decoder is the inverse of encoder.cc's MoveToNNIndex (every square, every
     slide / knight / camel / promotion offset); the number of pieces left subtracts one exactly when the last
     move captured (slide, knight, camel, promotion, en passant by a Sergeant or a diagonal pawn, but not a straight
     pawn step into the en passant square); the attack scores and the result of a game.
  B. REAL games: the engine plays a few games (random start positions plus small endings, a tiny network, CPU) and
     prints, per game, the number of pieces on the final board and the two attack scores it counted itself. The numbers
     taken from the game FILES by thong_ke_doi.py must be identical, game by game. Skipped (not failed) when the
     engine binary is not built.

Run:  python test_thong_ke_doi.py
"""

import os
import re
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import thong_ke_doi as S  # noqa: E402
import trainingdata_reader as R  # noqa: E402
from nn_layout import BOARD, HISTORY_PLANES, PIECE_KINDS, PROMOTION_BASE, KNIGHT_BASE, CAMEL_BASE  # noqa: E402

PASS = FAIL = 0


def check(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [ok] {msg}")
    else:
        FAIL += 1
        print(f"  [FAIL] {msg}")


# ---- an independent encoder of moves (transcribed from encoder.cc MoveToNNIndex, for the round trip) ----------------
def encode(file, rank, dx, dy, promo=None):
    frm = rank * BOARD + file
    if promo is not None:
        return (PROMOTION_BASE + promo * 3 + (dx + 1)) * 100 + frm
    knight = {(1, 2): 0, (2, 1): 1, (2, -1): 2, (1, -2): 3, (-1, -2): 4, (-2, -1): 5, (-2, 1): 6, (-1, 2): 7}
    camel = {(1, 3): 0, (3, 1): 1, (3, -1): 2, (1, -3): 3, (-1, -3): 4, (-3, -1): 5, (-3, 1): 6, (-1, 3): 7}
    if (dx, dy) in knight:
        return (KNIGHT_BASE + knight[(dx, dy)]) * 100 + frm
    if (dx, dy) in camel:
        return (CAMEL_BASE + camel[(dx, dy)]) * 100 + frm
    adx, ady = abs(dx), abs(dy)
    if dx == 0 and dy != 0:
        d, dist = (0, dy) if dy > 0 else (4, -dy)
    elif dy == 0 and dx != 0:
        d, dist = (2, dx) if dx > 0 else (6, -dx)
    elif adx == ady and dx != 0:
        d, dist = ({(1, 1): 1, (1, -1): 3, (-1, -1): 5, (-1, 1): 7}[(dx // adx, dy // ady)], adx)
    else:
        raise ValueError((dx, dy))
    return (d * 9 + dist - 1) * 100 + frm


def planes_with(ours, theirs):
    """piece_planes uint64[200, 2]: `ours` / `theirs` map a piece kind (0-11) to a list of (file, rank)."""
    pp = np.zeros((HISTORY_PLANES, 2), dtype=np.uint64)
    for base, side in ((0, ours), (PIECE_KINDS, theirs)):
        for kind, squares in side.items():
            for f, r in squares:
                s = r * 12 + f
                pp[base + kind, s // 64] |= np.uint64(1) << np.uint64(s % 64)
    return pp


def mask_of(squares):
    m = [0, 0]
    for f, r in squares:
        s = r * 12 + f
        m[s // 64] |= 1 << (s % 64)
    return tuple(m)


def rec(ours, theirs, played, stm=0, ep=(), q=0.0, d=1.0):
    return {"piece_planes": planes_with(ours, theirs), "ep_mask": mask_of(ep), "side_to_move": stm,
            "played_idx": played, "result_q": q, "result_d": d}


def test_decoder():
    print("\n[A1] decode_move is the inverse of MoveToNNIndex")
    bad = n = 0
    for rank in range(BOARD):
        for file in range(BOARD):
            offsets = [(dx, dy) for dx in range(-9, 10) for dy in range(-9, 10)
                       if (dx or dy) and 0 <= file + dx < BOARD and 0 <= rank + dy < BOARD
                       and (dx == 0 or dy == 0 or abs(dx) == abs(dy) or (abs(dx), abs(dy)) in
                            {(1, 2), (2, 1), (1, 3), (3, 1)})]
            for dx, dy in offsets:
                n += 1
                bad += S.decode_move(encode(file, rank, dx, dy)) != (file, rank, dx, dy)
            for piece in range(9):
                for dx in (-1, 0, 1):
                    n += 1
                    bad += S.decode_move(encode(file, rank, dx, 1, promo=piece)) != (file, rank, dx, 1)
    check(bad == 0, f"{n} (square, move) pairs round-trip, {bad} wrong")
    try:
        S.decode_move(115 * 100)
        check(False, "a move type past the table is refused")
    except ValueError:
        check(True, "a move type past the table is refused")


def test_last_move_capture():
    print("\n[A2] pieces left = pieces on the last recorded board, minus one when the last move captured")
    ROOK, KNIGHT, PAWN_, SERG, QUEEN, KING = 2, 1, 0, 9, 3, 4

    def left(ours, theirs, played, ep=()):
        return S.game_stats([rec(ours, theirs, played, ep=ep)])["pieces"]

    base_theirs = {PAWN_: [(0, 5)], KING: [(9, 9)]}
    ours = {ROOK: [(0, 0)], KING: [(5, 0)]}
    total = 4
    check(left(ours, base_theirs, encode(0, 0, 0, 5)) == total - 1, "rook slides 5 north onto a pawn: a capture")
    check(left(ours, base_theirs, encode(0, 0, 0, 3)) == total, "rook slides 3 north to an empty square: not a capture")
    check(left({KNIGHT: [(4, 4)], KING: [(5, 0)]}, {PAWN_: [(7, 7)], KING: [(9, 9)]}, encode(4, 4, 2, 2)) == total,
          "a diagonal slide (+2,+2) that is not a knight jump, onto an empty square: not a capture")
    check(left({KNIGHT: [(4, 4)], KING: [(5, 0)]}, {PAWN_: [(6, 5)], KING: [(9, 9)]}, encode(4, 4, 2, 1)) == total - 1,
          "knight jump (+2,+1) onto a pawn: a capture")
    check(left({KNIGHT: [(4, 4)], KING: [(5, 0)]}, {PAWN_: [(5, 7)], KING: [(9, 9)]}, encode(4, 4, 1, 3)) == total - 1,
          "camel jump (+1,+3) onto a pawn: a capture")
    check(left({KNIGHT: [(4, 4)], KING: [(5, 0)]}, {PAWN_: [(5, 7)], KING: [(9, 9)]}, encode(4, 4, -1, 3)) == total,
          "camel jump (-1,+3) to an empty square: not a capture")
    check(left({PAWN_: [(3, 8)], KING: [(5, 0)]}, {QUEEN: [(4, 9)], KING: [(9, 9)]}, encode(3, 8, 1, 1, promo=3)) == total - 1,
          "pawn captures diagonally onto the last rank and promotes: a capture")
    check(left({PAWN_: [(3, 8)], KING: [(5, 0)]}, {QUEEN: [(4, 9)], KING: [(9, 9)]}, encode(3, 8, 0, 1, promo=3)) == total,
          "pawn promotes straight ahead (the queen stands diagonally): not a capture")

    # en passant: the square the double-stepper jumped over is empty; the passer stands next to it
    theirs_pawn = {PAWN_: [(4, 4)], KING: [(9, 9)]}
    ep = [(4, 5)]
    check(left({SERG: [(3, 4)], KING: [(5, 0)]}, theirs_pawn, encode(3, 4, 1, 1), ep) == total - 1,
          "Sergeant moves diagonally onto the en passant square: a capture")
    check(left({SERG: [(4, 3)], KING: [(5, 0)]}, theirs_pawn, encode(4, 3, 0, 2), ep) == total - 1,
          "Sergeant steps straight onto the en passant square: always a capture")
    check(left({PAWN_: [(3, 4)], KING: [(5, 0)]}, theirs_pawn, encode(3, 4, 1, 1), ep) == total - 1,
          "pawn moves diagonally onto the en passant square: a capture")
    check(left({PAWN_: [(4, 4)], KING: [(5, 0)]}, {PAWN_: [(3, 5)], KING: [(9, 9)]}, encode(4, 4, 0, 1), [(4, 5)]) == total,
          "pawn steps STRAIGHT onto the en passant square: a normal move, not a capture")
    check(left({ROOK: [(4, 0)], KING: [(5, 0)]}, theirs_pawn, encode(4, 0, 0, 5), ep) == total,
          "a rook moving onto an en passant square does not capture (only pawn-like pieces can)")


def test_scores():
    print("\n[A3] attack scores and results")
    P, K, R_ = 0, 4, 2
    # White to move: 2 own pieces in the enemy half (ranks 5-9), 1 enemy piece in our half (ranks 0-4).
    r0 = rec({P: [(1, 5), (2, 6), (3, 1)], K: [(5, 0)]}, {P: [(4, 3)], K: [(9, 9)]}, encode(5, 0, 0, 1), stm=0, q=1.0, d=0.0)
    # Black to move (frame flipped: black's pieces at the bottom): 1 own piece in the enemy half, 3 enemy pieces in ours.
    r1 = rec({K: [(5, 0)], R_: [(2, 7)]}, {P: [(0, 1), (1, 2), (2, 4)], K: [(9, 9)]}, encode(5, 0, 0, 1), stm=1, q=-1.0, d=0.0)
    g = S.game_stats([r0, r1])
    # white: r0 us_att = 2 ; r1 them_att = 3  -> 5.   black: r0 them_att = 1 ; r1 us_att = 1 -> 2.
    check(g["white_attack"] == 5 and g["black_attack"] == 2, f"white {g['white_attack']} (want 5), black {g['black_attack']} (want 2)")
    check(g["plies"] == 2 and g["result"] == "W", "two plies; the first record's side to move (White) has q=+1: White won")
    check(S.game_stats([rec({K: [(0, 0)]}, {K: [(9, 9)]}, encode(0, 0, 1, 0), stm=1, q=1.0, d=0.0)])["result"] == "B",
          "Black to move with q=+1: Black won")
    check(S.game_stats([rec({K: [(0, 0)]}, {K: [(9, 9)]}, encode(0, 0, 1, 0), stm=0, q=-1.0, d=0.0)])["result"] == "B",
          "White to move with q=-1: Black won")
    check(S.game_stats([rec({K: [(0, 0)]}, {K: [(9, 9)]}, encode(0, 0, 1, 0), stm=0, q=0.0, d=1.0)])["result"] == "D",
          "q=0, d=1: a draw")

    games = [  # attack W/B, result
        {"plies": 10, "pieces": 20, "white_attack": 9, "black_attack": 3, "result": "W"},   # more attacker (W) won
        {"plies": 10, "pieces": 30, "white_attack": 2, "black_attack": 8, "result": "W"},   # more attacker (B) lost
        {"plies": 10, "pieces": 40, "white_attack": 5, "black_attack": 5, "result": "B"},   # equal attack: not counted
        {"plies": 10, "pieces": 50, "white_attack": 7, "black_attack": 1, "result": "D"},   # draw: not counted
        {"plies": 10, "pieces": 60, "white_attack": 1, "black_attack": 6, "result": "B"},   # more attacker (B) won
    ]
    s = S.summarize(games)
    check(s["games"] == 5 and s["white_wins"] == 2 and s["black_wins"] == 2 and s["draws"] == 1, "results counted")
    check(abs(s["avg_pieces"] - 40.0) < 1e-12, "average pieces left")
    check(s["decisive_clear"] == 3 and s["more_attacker_won"] == 2, f"the more-attacking side won {s['more_attacker_won']}/{s['decisive_clear']} (want 2/3)")
    check(s["white_more"] == 2 and s["black_more"] == 2, "games where each side attacked more: 2 White, 2 Black (one equal)")
    check(S.summarize([]) is None, "no games: no statistics")
    check("2/3 decisive games (66.7%)" in S.format_report("x", s), "the report prints 2/3 (66.7%)")


# ---- B. real games ----------------------------------------------------------------------------------------------
def find_engine():
    for p in (os.path.join(HERE, "..", "build", "custom_engine.exe"), os.path.join(HERE, "..", "build", "custom_engine"),
              os.path.join(HERE, "..", "build-linux", "custom_engine")):
        if os.path.isfile(p):
            return os.path.abspath(p)
    return None


def run(args, cwd, env=None, timeout=1800):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
    return p.returncode, p.stdout + p.stderr


def test_real_games():
    print("\n[B] the engine's own per-game numbers == the numbers taken from the game files")
    engine = find_engine()
    if not engine:
        print("  [skip] no engine binary under custom_engine/build (build it first)")
        return
    with tempfile.TemporaryDirectory() as tmp:
        net = os.path.join(tmp, "net.onnx")
        rc, out = run([sys.executable, os.path.join(HERE, "make_seed.py"), "--out", net, "--seed", "7",
                       "--d-model", "16", "--layers", "1", "--heads", "2"], tmp)
        check(rc == 0 and os.path.exists(net), "a tiny network for the engine")
        if rc != 0:
            print(out[-600:])
            return
        import sinh_the_khoi_dau as G
        import random
        rng = random.Random(11)
        fens = [G.lay_the(rng)[0] for _ in range(6)]
        fens += ["r3k4r/pppppppppp/10/10/10/10/10/10/PPPPPPPPPP/R3K4R w - - 7+7 0 1",
                 "4k5/10/10/10/10/10/10/10/10/R3K4R w - - 7+7 0 1",
                 "n3k5/10/10/10/10/10/10/10/10/4K4N b - - 7+7 20 1",
                 "4k5/10/10/10/10/3q6/10/10/3Q6/4K5 w - - 7+7 0 1"]
        book = os.path.join(tmp, "book.txt")
        open(book, "w").write("\n".join(fens) + "\n")
        games_dir = os.path.join(tmp, "games_gen3")     # named like a generation, for train.py --stats-newest-gen below
        rc, out = run([engine, "--selfplay", "--games", str(len(fens)), "--parallel", "4", "--visits", "4",
                       "--max-moves", "150", "--temperature", "0.5", "--provider", "cpu", "--weights", net,
                       "--out", games_dir, "--start-fen", book], os.path.dirname(engine))
        check(rc == 0, "the engine finished the self-play" + ("" if rc == 0 else "\n" + out[-800:]))
        rows = re.findall(r"\(game (\d+) -> result=(-?\d+), pieces=(\d+), cong W=(\d+) B=(\d+)", out)
        check(len(rows) == len(fens), f"the engine printed one line per game ({len(rows)} of {len(fens)})")
        files = {os.path.basename(f).rsplit(".", 1)[0]: os.path.join(games_dir, f) for f in os.listdir(games_dir)}
        mine, same, ended, captured_last = {}, 0, 0, 0
        for g, _res, pieces, wa, ba in rows:
            recs = list(R.iter_records(files[f"game_{g}"], sparse=True))
            st = S.game_stats(recs)
            mine[g] = st
            ok = st["pieces"] == int(pieces) and st["white_attack"] == int(wa) and st["black_attack"] == int(ba)
            same += ok
            if not ok:
                print(f"    game {g}: engine pieces={pieces} W={wa} B={ba}; from the file pieces={st['pieces']} "
                      f"W={st['white_attack']} B={st['black_attack']} ({st['plies']} plies)")
            ended += st["plies"] < 150
            planes = np.stack([np.asarray(recs[-1]["piece_planes"], dtype=np.uint64).reshape(-1, 2)[:2 * PIECE_KINDS]])
            captured_last += int(_board_total(planes)) - st["pieces"]
        check(same == len(rows) and rows, f"pieces left, White's and Black's attack score: identical for {same} of {len(rows)} games")
        print(f"      coverage: {ended} game(s) ended by the rules before the 150-ply cap; "
              f"{captured_last} game(s) whose last move was a capture")
        m = re.search(r"White wins: (\d+) \| Black wins: (\d+) \| Draws: (\d+)", out)
        s = S.summarize(list(mine.values()))
        check(m and (int(m[1]), int(m[2]), int(m[3])) == (s["white_wins"], s["black_wins"], s["draws"]),
              f"results agree with the engine's summary ({m.groups() if m else None} vs "
              f"{(s['white_wins'], s['black_wins'], s['draws'])})")
        m = re.search(r"Ben cong nhieu hon THANG: (\d+)/(\d+)", out)
        check(m and (int(m[1]), int(m[2])) == (s["more_attacker_won"], s["decisive_clear"]),
              f"'the side that attacked more won' agrees with the engine ({m.groups() if m else None} vs "
              f"{(s['more_attacker_won'], s['decisive_clear'])})")

        # The same numbers through train.py --stats-newest-gen (a warm start from the tiny network, one step).
        rc, out = run([sys.executable, os.path.join(HERE, "train.py"), "--data", games_dir, "--init-from",
                       net.replace(".onnx", ".pt"), "--epochs", "1", "--max-steps", "1", "--batch", "32", "--workers",
                       "0", "--device", "cpu", "--val-frac", "0", "--stats-newest-gen", "--d-model", "16", "--layers",
                       "1", "--heads", "2", "--out", os.path.join(tmp, "o.onnx")], tmp)
        want = S.format_report("newest generation 3", s)
        check(rc == 0 and want in out, "train.py --stats-newest-gen prints exactly this report before training"
              + ("" if rc == 0 and want in out else "\n" + out[-900:]))
        import shutil
        plain_dir = os.path.join(tmp, "van_khong_ten_doi")       # the same games, in a folder that names no generation
        shutil.copytree(games_dir, plain_dir)
        rc, out = run([sys.executable, os.path.join(HERE, "train.py"), "--data", plain_dir,
                       "--init-from", net.replace(".onnx", ".pt"), "--epochs", "1", "--max-steps", "1", "--batch", "32",
                       "--workers", "0", "--device", "cpu", "--val-frac", "0", "--stats-newest-gen", "--d-model", "16",
                       "--layers", "1", "--heads", "2", "--out", os.path.join(tmp, "o2.onnx")], tmp)
        check(rc == 0 and "no games_gen<g> folder" in out and "[ckpt] saved" in out,
              "data without a games_gen<g> folder: a note, and the training still runs")


def _board_total(planes):
    return S._board_bits(planes)[0].sum()


def main():
    test_decoder()
    test_last_move_capture()
    test_scores()
    test_real_games()
    print("\n" + "=" * 60)
    print(f"RESULT: {PASS} passed, {FAIL} failed")
    print("=" * 60)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
