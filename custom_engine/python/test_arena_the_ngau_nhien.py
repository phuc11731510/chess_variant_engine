"""Test of `--arena --start-fen`: the arena starts from the same kind of random start positions as self-play.

Game g (0-based) has A as White iff g is even. With a book, games 2k and 2k+1 start from line k of the book (wrapping
round), so each position is played once with each color -- the two sides of a random start position are not
symmetric. A single FEN starts every game from it; no --start-fen keeps the fixed placeholder. A bad or empty book
stops the arena before any game with the file name and line number.

Needs the engine binary (custom_engine/build). Run:  python test_arena_the_ngau_nhien.py
"""

import os
import random
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
PASS = FAIL = 0
PLACEHOLDER = "vrcbqkbgrv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRCBQKBGRV w - - 7+7 0 1"


def check(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [ok] {msg}")
    else:
        FAIL += 1
        print(f"  [FAIL] {msg}")


def find_engine():
    for p in (os.path.join(HERE, "..", "build", "custom_engine.exe"), os.path.join(HERE, "..", "build", "custom_engine"),
              os.path.join(HERE, "..", "build-linux", "custom_engine")):
        if os.path.isfile(p):
            return os.path.abspath(p)
    return None


def run(args, cwd):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=1200)
    return p.returncode, p.stdout + p.stderr


def games_of(out):
    """[(game number #1.., 'White'|'Black' = A's color, start FEN)] in the order the arena printed them."""
    rows, lines = [], out.splitlines()
    for i, ln in enumerate(lines):
        m = re.search(r"game \d+/\d+ \(#(\d+)\) \(A plays (White|Black)\)", ln)
        if m:
            fen = next((l.split("start:", 1)[1].strip() for l in lines[i + 1:i + 4] if "start:" in l), None)
            rows.append((int(m[1]), m[2], fen))
    return sorted(rows)


def main():
    engine = find_engine()
    if not engine:
        print("[skip] no engine binary under custom_engine/build (build it first)")
        return
    import sinh_the_khoi_dau as G
    with tempfile.TemporaryDirectory() as tmp:
        net = os.path.join(tmp, "net.onnx")
        rc, out = run([sys.executable, os.path.join(HERE, "make_seed.py"), "--out", net, "--seed", "5",
                       "--d-model", "16", "--layers", "1", "--heads", "2"], tmp)
        check(rc == 0 and os.path.exists(net), "a tiny network")
        if rc != 0:
            print(out[-500:])
            return
        rng = random.Random(3)
        fens = [G.lay_the(rng)[0] for _ in range(3)]
        book = os.path.join(tmp, "book.txt")
        open(book, "w").write("# arena book\n" + "\n".join(fens[:2]) + "\r\n\n" + fens[2] + "\n")   # comment, \r\n, blank
        base = [engine, "--arena", "--model-a", net, "--model-b", net, "--visits", "4", "--max-moves", "4",
                "--provider", "cpu", "--parallel", "2", "--arena-moves"]
        cwd = os.path.dirname(engine)

        print("\n[1] a book: one position per pair of games, colors swapped")
        rc, out = run(base + ["--games", "6", "--start-fen", book], cwd)
        g = games_of(out)
        check(rc == 0 and len(g) == 6, f"6 games played (exit {rc}, {len(g)} parsed)")
        check([x[1] for x in g] == ["White", "Black"] * 3, "A is White in games #1, #3, #5 and Black in #2, #4, #6")
        check([x[2] for x in g] == [fens[0], fens[0], fens[1], fens[1], fens[2], fens[2]],
              "games #1/#2 start from line 1, #3/#4 from line 2, #5/#6 from line 3 (comment and blank lines skipped)")
        check("3 FENs from" in out and "3 position(s) needed for 6 games" in out and "wraps round" not in out,
              "the arena says how many positions it uses")
        check(re.search(r"by color: A as White \d+W/\d+D/\d+L \(3 games\) \| A as Black \d+W/\d+D/\d+L \(3 games\)", out)
              and "NOT balanced" not in out, "the result lists A's games by color: 3 as White, 3 as Black")

        print("\n[1b] many games at once: 4 in parallel keep the pairing")
        rc, out = run(base[:-3] + ["--parallel", "4", "--arena-moves", "--games", "8", "--start-fen", book], cwd)
        g = games_of(out)
        check(rc == 0 and [x[2] for x in g] == [fens[0], fens[0], fens[1], fens[1], fens[2], fens[2], fens[0], fens[0]]
              and [x[1] for x in g] == ["White", "Black"] * 4,
              "8 games, 4 at a time: the same pairs of positions and the same colors as one at a time")
        rc, out = run(base + ["--games", "3", "--start-fen", book], cwd)
        check(rc == 0 and "(2 games) | A as Black" in out and "NOT balanced" in out,
              "an odd number of games is reported as colors not balanced")

        print("\n[2] more pairs than book lines: the book wraps round")
        rc, out = run(base + ["--games", "8", "--start-fen", book], cwd)
        g = games_of(out)
        check(rc == 0 and [x[2] for x in g] == [fens[0], fens[0], fens[1], fens[1], fens[2], fens[2], fens[0], fens[0]],
              "8 games on a 3-line book: pairs 1..4 use lines 1, 2, 3, 1")
        rc, out = run(base + ["--games", "2", "--start-fen", book], cwd)
        check(rc == 0 and "1 position(s) needed for 2 games" in out, "2 games need 1 position")

        print("\n[3] a single FEN, and the fixed placeholder")
        rc, out = run(base + ["--games", "4", "--start-fen", fens[1]], cwd)
        g = games_of(out)
        check(rc == 0 and len(g) == 4 and all(x[2] == fens[1] for x in g) and "one FEN for every game" in out,
              "--start-fen <FEN>: every game starts from it")
        rc, out = run(base + ["--games", "4"], cwd)
        g = games_of(out)
        check(rc == 0 and len(g) == 4 and all(x[2] == PLACEHOLDER for x in g) and "fixed placeholder" in out,
              "no --start-fen: the fixed placeholder, as before")

        print("\n[4] a bad book stops the arena before any game")
        bad = os.path.join(tmp, "bad.txt")
        open(bad, "w").write(fens[0] + "\n" + "4k5/10/10/10/10/10/10/10/10/R3K4R w - - 0 1\n")
        rc, out = run(base + ["--games", "2", "--start-fen", bad], cwd)
        check(rc != 0 and "FATAL" in out and "bad.txt:2:" in out and "game 1/" not in out,
              "a line without the N+N checks field: FATAL with file:line, no game played")
        empty = os.path.join(tmp, "empty.txt")
        open(empty, "w").write("# nothing\n\n")
        rc, out = run(base + ["--games", "2", "--start-fen", empty], cwd)
        check(rc != 0 and "no FEN in" in out, "a book with no FEN is refused")
        rc, out = run(base + ["--games", "2", "--start-fen", "not a fen"], cwd)
        check(rc != 0 and "neither a readable file nor a valid FEN" in out, "a path that is no file and no FEN is refused")

        print("\n[5] constant search: same playouts every move, c_puct 1.25, every move drawn with temperature 0.5")
        rc, out = run(base + ["--games", "2", "--start-fen", book], cwd)
        check(rc == 0 and "[arena] search: PUCT, 4 playouts every move (cpuct 1.25, no noise); "
                          "every move drawn with temperature 0.5" in out,
              "defaults: c_puct 1.25, temperature 0.5, no noise, the --visits playouts every move")
        rc, out = run(base + ["--games", "2", "--start-fen", book, "--cpuct", "2", "--temperature", "0"], cwd)
        check(rc == 0 and "(cpuct 2, no noise); every move drawn with temperature 0" in out,
              "--cpuct and --temperature override the defaults")
        rc, out = run(base + ["--games", "2", "--start-fen", book, "--temp-cutoff", "8"], cwd)
        check(rc != 0 and "--temp-cutoff no longer exists" in out and "game 1/" not in out,
              "the old opening flag --temp-cutoff is refused (no silent change of behaviour)")

        def moves_of(extra, fen):
            rc2, o2 = run([engine, "--arena", "--model-a", net, "--model-b", net, "--visits", "16", "--max-moves", "6",
                           "--provider", "cpu", "--parallel", "1", "--arena-moves", "--games", "1",
                           "--start-fen", fen] + extra, cwd)
            m = re.search(r"moves: (.*)", o2)
            return m.group(1).strip() if (rc2 == 0 and m) else None
        # (Temperature 0 is not checked for repeatability: it draws evenly among the MOST visited moves, and a random
        # net with 16 playouts leaves many moves tied on the maximum.)
        sampled = {moves_of(["--temperature", "1"], fens[0]) for _ in range(6)}
        check(None not in sampled and len(sampled) > 1,
              f"temperature 1: moves are drawn with weight N (6 runs gave {len(sampled)} different games)")

    print("\n" + "=" * 60)
    print(f"RESULT: {PASS} passed, {FAIL} failed")
    print("=" * 60)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
