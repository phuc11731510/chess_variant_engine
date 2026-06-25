"""Audit the INTEGRITY of a generation of self-play training data.

Reads every record in a .zip bundle (or .gz file, or a directory of them) and
checks — directly on the data you will train on — that:
  * the record layout parses (no struct/layout drift),
  * value targets are in range and result_q/result_d are self-consistent,
  * the policy is a valid masked distribution (illegal == -1, legal sum == 1,
    >= 1 legal move per position),
  * input planes are non-empty (guards the historical "NN sees no pieces" bug),
  * scalar aux (side-to-move, checks-remaining) are in range.

Also reports the result distribution (win/draw/loss from the side-to-move's
perspective): a near 50/50 win/loss split is empirical confirmation that the
value-target perspective is correct.

Complements the C++ `--audit-generation` mode (which differential-checks MOVEGEN
adapter-vs-raw-Fairy-Stockfish over random games). This one audits the saved DATA;
that one audits the move-generation process that produced it.

Usage:
  python audit_generation.py <game_gen_N.zip | game.gz | dir>
"""
import sys, os, glob
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from trainingdata_reader import iter_records, iter_records_from_zip


def _records(path):
    if os.path.isdir(path):
        files = []
        for ext in ("*.gz", "*.bin", "*.zip"):
            files += glob.glob(os.path.join(path, ext))
    else:
        files = [path]
    if not files:
        raise SystemExit(f"[audit] no .gz/.bin/.zip under: {path}")
    for f in files:
        it = iter_records_from_zip(f) if f.endswith(".zip") else iter_records(f)
        for r in it:
            yield r


def wdl(q, d):
    return (q + 1.0 - d) / 2.0, d, (1.0 - d - q) / 2.0


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: python audit_generation.py <zip|gz|dir>")
    path = sys.argv[1]
    n = 0
    err = dict(value=0, polsum=0, nolegal=0, neg_not_m1=0, plane_empty=0, stm=0, checks=0)
    resq = {}
    legal_counts = []
    bad = []

    for r in _records(path):
        n += 1
        rq, rd = r["result_q"], r["result_d"]
        resq[round(rq, 3)] = resq.get(round(rq, 3), 0) + 1
        w, dd, l = wdl(rq, rd)
        if not (-1.001 <= rq <= 1.001 and -0.001 <= rd <= 1.001 and w >= -1e-4 and l >= -1e-4 and dd >= -1e-4):
            err["value"] += 1
            if len(bad) < 8: bad.append(("VALUE", n, rq, rd))
        p = r["probabilities"]
        legal = p[p >= 0.0]
        neg = p[p < 0.0]
        if neg.size and not np.allclose(neg, -1.0):
            err["neg_not_m1"] += 1
        if legal.size == 0:
            err["nolegal"] += 1
        else:
            s = float(legal.sum())
            if abs(s - 1.0) > 1e-2:
                err["polsum"] += 1
                if len(bad) < 8: bad.append(("POLSUM", n, s))
            legal_counts.append(int(legal.size))
        pp = r["piece_planes"]
        if not any(pp[i] != 0 for i in range(min(24, len(pp)))):
            err["plane_empty"] += 1
        if r["side_to_move"] not in (0, 1):
            err["stm"] += 1
        if not (0 <= r["checks_remaining_us"] <= 7 and 0 <= r["checks_remaining_them"] <= 7):
            err["checks"] += 1

    print(f"=== AUDIT (data integrity): {path} ===")
    print(f"records: {n}")
    print(f"result_q dist: {dict(sorted(resq.items()))}")
    if legal_counts:
        lc = np.array(legal_counts)
        print(f"legal moves/pos: min={lc.min()} max={lc.max()} mean={lc.mean():.1f}")
    print("--- errors ---")
    for k, v in err.items():
        print(f"  {k}: {v}")
    if bad:
        print("--- first failing records ---")
        for b in bad: print("  ", b)
    ok = all(v == 0 for v in err.values())
    print("=== " + ("PASS — data clean" if ok else "FAIL — see errors") + " ===")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
