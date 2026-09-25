"""Extreme / edge-case tests for the Python training pipeline (audit shield).

Pure-Python + torch only (no engine, no CUDA) — fast and deterministic. Targets the
convention-sensitive logic where a silent bug would corrupt training without crashing:
  1. binary record layout round-trips (struct pack/unpack, 45940 B, field order)
  2. wdl_from_qd invariants over a (q,d) sweep incl. inconsistent inputs
  3. qMix value target = q_ratio*q + (1-q_ratio)*z (exact)
  4. sparse cache == dense cache, bit-identical, over fuzz + degenerate records
  5. masked policy loss: ZERO gradient on illegal logits + value-correct + invariance
  6. reconstruct_planes aux-plane semantics (edge, rule50, checks, castling, ep)
  7. bitboard decode: s=rank*12+file mapping + padding columns never leak
  8. archive.py pack -> read_records_from_zip == reading the dir (bit-faithful)
  9. audit_generation.py passes clean games and catches each kind of corruption
 10. diff_focus keeps records without a raw eval at the average rate

Run:  python test_extreme.py
"""

import os
import sys
import glob
import gzip
import math
import tempfile
import subprocess

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import dataset as D
import trainingdata_reader as R
from train import policy_loss

PASS, FAIL = 0, 0


def check(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [ok] {msg}")
    else:
        FAIL += 1
        print(f"  [FAIL] {msg}")


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def set_cell(pair, rank, file):
    """Set bit s=rank*12+file in a [lo,hi] uint64 pair (12-stride, like the C++)."""
    s = rank * 12 + file
    if s < 64:
        pair[0] |= np.uint64(1) << np.uint64(s)
    else:
        pair[1] |= np.uint64(1) << np.uint64(s - 64)


def make_rec(seed=0, n_legal=40, with_zeros=True):
    """A synthetic record dict with the keys the dataset/reader consume."""
    r = np.random.default_rng(seed)
    pi = np.full(R.POLICY_SIZE, -1.0, dtype=np.float32)
    if n_legal > 0:
        legal = r.choice(R.POLICY_SIZE, size=n_legal, replace=False)
        v = r.random(n_legal).astype(np.float32)
        v /= v.sum()
        pi[legal] = v
        if with_zeros and n_legal >= 5:
            pi[legal[:3]] = 0.0           # legal-unvisited slots (pi==0, must survive)
    pp = r.integers(0, 2**63, size=R.HISTORY_PLANES * 2, dtype=np.uint64)
    return dict(
        piece_planes=tuple(int(x) for x in pp),
        ep_mask=(int(r.integers(0, 2**63)), int(r.integers(0, 2**63))),
        castling_us_ooo_sq=0, castling_us_oo_sq=19,       # a1, j2 (canonical)
        castling_them_ooo_sq=255, castling_them_oo_sq=95,
        rule50_count=37, checks_remaining_us=6, checks_remaining_them=7,
        side_to_move=seed % 2, probabilities=pi,
        result_q=float(r.choice([-1.0, 0.0, 1.0])), result_d=0.0,
        best_q=float(r.uniform(-1, 1)), best_d=float(r.uniform(0, 0.4)),
    )


class _DS(D.FairyDataset):
    def __init__(self, q_ratio=0.2):
        self.q_ratio = q_ratio
        self.sparse = True


# --------------------------------------------------------------------------- #
# 1. binary record layout round-trip
# --------------------------------------------------------------------------- #
def test_struct_layout():
    print("\n[1] binary record layout (pack -> unpack)")
    check(R.RECORD_SIZE == 45940, f"record size == 45940 (got {R.RECORD_SIZE})")
    pi = [-1.0] * R.POLICY_SIZE
    pi[123] = 0.25; pi[7777] = 0.75
    pp = list(range(R.HISTORY_PLANES * 2))           # 0,1,2,... distinct sentinels
    fields = ([5, 1] + pi + pp +
              [200, 0, 19, 255, 94,                  # rule50 + 4 castling squares
               0xAAAA, 0xBBBB,                       # ep_mask
               6, 7, 1,                              # checks_us/them, side
               1.0, 0.0, 0.2, 0.1, -0.3, 0.15, 0.4, 0.05, 0.6, 0.2, 1.234,  # 11 floats
               300, 123, 7777])                      # visits, played_idx, best_idx
    rec = R.unpack_record(R._STRUCT.pack(*fields))
    check(rec["version"] == 5 and rec["input_format"] == 1, "version/input_format")
    # A version or input format the reader does not know must be refused, not read.
    for bad_version, bad_format in ((0, 1), (6, 1), (7, 1), (5, 2)):
        try:
            R.unpack_record(R._STRUCT.pack(*([bad_version, bad_format] + fields[2:])))
            refused = False
        except ValueError:
            refused = True
        check(refused, f"version {bad_version} / input format {bad_format} refused")
    check(abs(rec["probabilities"][123] - 0.25) < 1e-6 and
          abs(rec["probabilities"][7777] - 0.75) < 1e-6, "probabilities[idx] preserved")
    check(rec["piece_planes"][0] == 0 and rec["piece_planes"][431] == 431, "piece_planes order")
    # 1b. The fast path (np.frombuffer + a struct for the tail) must give exactly
    # what unpacking every field with _STRUCT gives, on random full-range values.
    g = np.random.default_rng(1)
    rnd = ([5, 1] + [float(x) for x in g.standard_normal(R.POLICY_SIZE).astype(np.float32)] +
           [int(x) for x in g.integers(0, 2**64, size=len(pp), dtype=np.uint64)] +
           [int(g.integers(0, 256)), 3, 12, 255, 99,
            int(g.integers(0, 2**64, dtype=np.uint64)), int(g.integers(0, 2**64, dtype=np.uint64)),
            5, 8, 0] + [float(x) for x in g.standard_normal(11).astype(np.float32)] +
           [int(g.integers(0, 2**32)), int(g.integers(0, 2**16)), int(g.integers(0, 2**16))])
    buf = R._STRUCT.pack(*rnd)
    fast, ref = R.unpack_record(buf), R._STRUCT.unpack(buf)
    npl = R.POLICY_SIZE + len(pp)
    check(fast["probabilities"].dtype == np.float32 and
          fast["probabilities"].tobytes() == np.array(ref[2:2 + R.POLICY_SIZE], np.float32).tobytes(),
          "fast unpack: probabilities bit-identical to the full struct")
    check(fast["piece_planes"].dtype == np.uint64 and
          fast["piece_planes"].tolist() == list(ref[2 + R.POLICY_SIZE:2 + npl]),
          "fast unpack: piece_planes identical (full uint64 range)")
    check(fast["piece_planes"].base is None, "fast unpack: piece_planes owns its memory")
    tail = ref[2 + npl:]
    got = ([fast["rule50_count"]] + [fast[k] for k in R.CASTLING_KEYS] + list(fast["ep_mask"]) +
           [fast[k] for k in ("checks_remaining_us", "checks_remaining_them", "side_to_move",
                              "result_q", "result_d", "root_q", "root_d", "best_q", "best_d",
                              "played_q", "played_d", "orig_q", "orig_d", "policy_kld",
                              "visits", "played_idx", "best_idx")])
    check(got == list(tail), "fast unpack: every tail field identical")
    check(rec["rule50_count"] == 200 and rec["castling_us_ooo_sq"] == 0 and
          rec["castling_us_oo_sq"] == 19 and rec["castling_them_ooo_sq"] == 255 and
          rec["castling_them_oo_sq"] == 94, "scalar aux fields (castling squares)")
    # Up to version 4 the castling bytes were files (the rook on its first rank):
    # read as squares, us on rank 0 and them on rank 9.
    old = R.unpack_record(R._STRUCT.pack(*([4, 1] + fields[2:2 + R.POLICY_SIZE + len(pp)] +
                                           [200, 1, 8, 255, 4] + fields[7 + R.POLICY_SIZE + len(pp):])))
    check([old[k] for k in R.CASTLING_KEYS] == [1, 8, 255, 94],
          f"version-4 castling files -> squares (got {[old[k] for k in R.CASTLING_KEYS]})")
    # A byte that is neither a square/file nor 0xFF is refused.
    for version, bad in ((5, 100), (5, 254), (4, 10)):
        try:
            R.unpack_record(R._STRUCT.pack(*([version, 1] + fields[2:2 + R.POLICY_SIZE + len(pp)] +
                                             [200, bad, 255, 255, 255] +
                                             fields[7 + R.POLICY_SIZE + len(pp):])))
            refused = False
        except ValueError:
            refused = True
        check(refused, f"castling byte {bad} in a version-{version} record refused")
    check(rec["ep_mask"] == (0xAAAA, 0xBBBB), "ep_mask pair")
    check(rec["checks_remaining_us"] == 6 and rec["checks_remaining_them"] == 7 and
          rec["side_to_move"] == 1, "checks + side")
    check(abs(rec["result_q"] - 1.0) < 1e-6 and abs(rec["best_q"] - (-0.3)) < 1e-6 and
          abs(rec["policy_kld"] - 1.234) < 1e-5, "value/kld floats in order")
    check(rec["visits"] == 300 and rec["played_idx"] == 123 and rec["best_idx"] == 7777,
          "visits/played_idx/best_idx")


# --------------------------------------------------------------------------- #
# 2. wdl_from_qd invariants
# --------------------------------------------------------------------------- #
def test_wdl_from_qd():
    print("\n[2] wdl_from_qd invariants")
    # corners
    check(np.allclose(D.wdl_from_qd(1.0, 0.0), [1, 0, 0]), "pure win -> [1,0,0]")
    check(np.allclose(D.wdl_from_qd(-1.0, 0.0), [0, 0, 1]), "pure loss -> [0,0,1]")
    check(np.allclose(D.wdl_from_qd(0.0, 1.0), [0, 1, 0]), "pure draw -> [0,1,0]")
    ok_sum = ok_qd = ok_rng = True
    for q in np.linspace(-1, 1, 21):
        for d in np.linspace(0, 1, 11):
            w = D.wdl_from_qd(q, d)
            if abs(w.sum() - 1.0) > 1e-5:
                ok_sum = False
            if (w < -1e-6).any() or (w > 1 + 1e-6).any():
                ok_rng = False
            # when (q,d) is a CONSISTENT distribution (w,l>=0), w-l must equal q
            if (1 - d - abs(q)) >= 0:                 # consistent region
                if abs((w[0] - w[2]) - q) > 1e-5:
                    ok_qd = False
    check(ok_sum, "sum(WDL) == 1 over full (q,d) sweep")
    check(ok_rng, "WDL in [0,1] over full (q,d) sweep")
    check(ok_qd, "w - l == q in the consistent region")
    # inconsistent input must not crash and stays a valid distribution
    bad = D.wdl_from_qd(1.0, 1.0)
    check(abs(bad.sum() - 1.0) < 1e-5 and (bad >= 0).all(), "inconsistent (q=1,d=1) -> valid dist")


# --------------------------------------------------------------------------- #
# 3. qMix
# --------------------------------------------------------------------------- #
def test_qmix():
    print("\n[3] qMix value target")
    for qr in (0.0, 0.2, 0.5, 1.0):
        ds = _DS(q_ratio=qr)
        rec = make_rec(seed=3)
        v = ds._value(rec)
        z = D.wdl_from_qd(rec["result_q"], rec["result_d"])
        q = D.wdl_from_qd(rec["best_q"], rec["best_d"])
        expect = qr * q + (1 - qr) * z
        check(np.allclose(v, expect, atol=1e-6), f"q_ratio={qr}: value == qr*q+(1-qr)*z")
    check(np.allclose(_DS(0.0)._value(make_rec(3)),
                      D.wdl_from_qd(make_rec(3)["result_q"], make_rec(3)["result_d"])),
          "q_ratio=0 -> pure z (result)")


# --------------------------------------------------------------------------- #
# 3b. search-Q sign of legacy (version-1) records
# --------------------------------------------------------------------------- #
def test_legacy_search_q_sign():
    print("\n[3b] search-Q sign: version-1 records are flipped back, version 2 kept")
    ds = _DS(q_ratio=0.2)
    base = make_rec(seed=11)
    base.update(result_q=1.0, result_d=0.0, best_q=0.6, best_d=0.2,
                root_q=0.5, root_d=0.2, played_q=0.4, played_d=0.2,
                orig_q=0.33, orig_d=0.1)
    # The same search, as the fixed engine (v2) and the old engine (v1) wrote it.
    v2 = dict(base, version=2)
    v1 = dict(base, version=1, best_q=-0.6, root_q=-0.5, played_q=-0.4)
    good = 0.2 * D.wdl_from_qd(0.6, 0.2) + 0.8 * D.wdl_from_qd(1.0, 0.0)
    check(np.allclose(ds._value(v2), good, atol=1e-6), "v2: value target uses best_q as stored")
    check(np.allclose(ds._value(v1), good, atol=1e-6), "v1: value target undoes the legacy sign")
    for key, want in (("best_q", 0.6), ("root_q", 0.5), ("played_q", 0.4)):
        check(abs(D.search_q(v1, key) - want) < 1e-9 and abs(D.search_q(v2, key) - want) < 1e-9,
              f"search_q({key}) is side-to-move for v1 and v2")
    check(abs(D.orig_q(v1) - 0.33) < 1e-9, "v1: a real orig_q (raw net) is kept")
    fallback = dict(v1, orig_q=v1["best_q"], orig_d=v1["best_d"])   # cache-miss copy of best_q
    check(abs(D.orig_q(fallback) - 0.6) < 1e-9, "v1: orig_q copied from best_q is flipped too")
    check(abs(D.search_q(make_rec(seed=3)) - make_rec(seed=3)["best_q"]) < 1e-9,
          "records without a version field are treated as current")


# --------------------------------------------------------------------------- #
# 4. sparse == dense
# --------------------------------------------------------------------------- #
def test_sparse_equals_dense():
    print("\n[4] sparse cache == dense cache (bit-identical)")
    ds = _DS()
    cases = {"fuzz": [make_rec(s) for s in range(200)],
             "single-legal": [make_rec(900, n_legal=1, with_zeros=False)],
             "all-legal-zeros": [make_rec(901, n_legal=50, with_zeros=True)],
             "no-legal": [make_rec(902, n_legal=0)]}
    for name, recs in cases.items():
        all_ok = True
        for r in recs:
            xd, pid, vd = ds._build(r)
            xs, pis, vs = ds._build_from_compact(ds._compact(r))
            if not (torch.equal(xd, xs) and torch.equal(pid, pis) and torch.equal(vd, vs)):
                all_ok = False
                break
        check(all_ok, f"{name}: sparse==dense over {len(recs)} record(s)")
    # the sparse pi keeps EXACTLY the legal mask (pi>=0) and -1 elsewhere
    r = make_rec(5, n_legal=40)
    _, pis, _ = ds._build_from_compact(ds._compact(r))
    legal_dense = (r["probabilities"] >= 0).sum()
    check(int((pis >= 0).sum()) == int(legal_dense), "sparse keeps exact #legal slots")
    check(bool((pis[r["probabilities"] < 0] == -1).all()), "illegal slots stay -1 after rebuild")


# --------------------------------------------------------------------------- #
# 5. masked policy loss
# --------------------------------------------------------------------------- #
def test_policy_loss_masking():
    print("\n[5] masked policy loss (illegal gets ZERO gradient)")
    torch.manual_seed(0)
    N = R.POLICY_SIZE
    logits = torch.randn(1, N, requires_grad=True)
    pi = torch.full((1, N), -1.0)
    legal = [10, 200, 333, 9000, 12]
    fracs = [0.5, 0.3, 0.2, 0.0, 0.0]                 # incl legal-unvisited (0.0)
    for i, f in zip(legal, fracs):
        pi[0, i] = f
    loss = policy_loss(logits, pi)
    loss.backward()
    g = logits.grad[0]
    illegal_mask = (pi[0] < 0)
    check(torch.count_nonzero(g[illegal_mask]).item() == 0, "grad == 0 on ALL illegal logits")
    check(torch.count_nonzero(g[~illegal_mask]).item() > 0, "grad != 0 on legal logits")
    # value-correct: equals manual CE over the legal sub-distribution
    legal_idx = torch.tensor(legal)
    logp_legal = torch.log_softmax(logits[0, legal_idx].detach(), dim=0)
    tgt = torch.tensor(fracs)
    manual = -(tgt * logp_legal).sum()
    check(abs(manual.item() - loss.item()) < 1e-4, "loss == manual masked CE over legal moves")
    # invariance: arbitrarily changing ILLEGAL logits must not change the loss
    l2 = logits.detach().clone()
    l2[0, illegal_mask] += 100.0
    loss2 = policy_loss(l2, pi)
    check(abs(loss2.item() - loss.item()) < 1e-4, "loss invariant to illegal-logit values")


# --------------------------------------------------------------------------- #
# 6. reconstruct_planes aux semantics
# --------------------------------------------------------------------------- #
def test_reconstruct_aux():
    print("\n[6] reconstruct_planes aux-plane semantics")
    AB = R.AUX_BASE
    rec = dict(
        piece_planes=tuple([0] * (R.HISTORY_PLANES * 2)),
        ep_mask=[np.uint64(0), np.uint64(0)],
        castling_us_ooo_sq=2, castling_us_oo_sq=255,       # c1
        castling_them_ooo_sq=97, castling_them_oo_sq=255,  # h10
        rule50_count=50, checks_remaining_us=3, checks_remaining_them=7,
    )
    ep = [np.uint64(0), np.uint64(0)]
    set_cell(ep, 4, 6)                                # ep bit at (rank4,file6)
    rec["ep_mask"] = (int(ep[0]), int(ep[1]))
    pl = R.reconstruct_planes(rec)
    check(np.allclose(pl[AB + 7], 1.0), "aux7 board-edge plane all ones")
    check(np.allclose(pl[AB + 6], 0.0), "aux6 unused plane all zeros")
    check(np.allclose(pl[AB + 5], 0.5), "aux5 rule50 == 50/100")
    check(np.allclose(pl[AB + 8], 3 / 10) and np.allclose(pl[AB + 9], 7 / 10),
          "aux8/9 checks == n/10")
    # castling: one bit on the rook's square; 0xFF -> nothing
    check(pl[AB + 0, 0, 2] == 1.0 and pl[AB + 0].sum() == 1.0, "us_ooo square 2 -> (rank0,file2)")
    check(pl[AB + 1].sum() == 0.0, "us_oo == 0xFF -> empty plane")
    check(pl[AB + 2, 9, 7] == 1.0 and pl[AB + 2].sum() == 1.0, "them_ooo square 97 -> (rank9,file7)")
    check(pl[AB + 3].sum() == 0.0, "them_oo == 0xFF -> empty plane")
    # castling on any rank (a shuffled start): the bit lands on that rank
    rec.update(castling_us_ooo_sq=11, castling_us_oo_sq=18,   # b2, i2
               castling_them_ooo_sq=81, castling_them_oo_sq=88)  # b9, i9
    pl = R.reconstruct_planes(rec)
    got = [tuple(np.argwhere(pl[AB + k] == 1.0).ravel()) for k in range(4)]
    check(got == [(1, 1), (1, 8), (8, 1), (8, 8)] and all(pl[AB + k].sum() == 1.0 for k in range(4)),
          f"castling rooks on ranks 2 / 9 -> their squares (got {got})")
    check(pl[AB + 4, 4, 6] == 1.0 and pl[AB + 4].sum() == 1.0, "ep plane decodes (rank4,file6)")


# --------------------------------------------------------------------------- #
# 7. bitboard decode mapping + padding never leaks
# --------------------------------------------------------------------------- #
def test_bitboard_decode():
    print("\n[7] bitboard decode (s=rank*12+file) + padding isolation")
    pp = np.zeros((R.HISTORY_PLANES, 2), dtype=np.uint64)
    p = [np.uint64(0), np.uint64(0)]
    set_cell(p, 0, 0)        # corner (0,0)   -> s=0   word0 bit0
    set_cell(p, 9, 9)        # corner (9,9)   -> s=117 word1 bit53
    set_cell(p, 1, 0)        # (1,0)          -> s=12
    set_cell(p, 0, 9)        # (0,9)          -> s=9
    # stray bits in PADDING columns (file 10,11) must be ignored by the board grid
    p[0] |= np.uint64(1) << np.uint64(10)             # s=10 -> (rank0,file10) padding
    p[0] |= np.uint64(1) << np.uint64(11)             # s=11 -> (rank0,file11) padding
    pp[0] = p
    plane = R._unpack_block(pp)[0]
    expect = {(0, 0), (9, 9), (1, 0), (0, 9)}
    got = set(map(tuple, np.argwhere(plane == 1.0)))
    check(got == expect, f"decoded cells exactly {sorted(expect)} (got {sorted(got)})")
    check(plane.sum() == 4.0, "padding-column bits (file 10/11) do NOT leak onto board")
    # reference scalar decoder agrees with the vectorized one
    ref = np.zeros((10, 10), dtype=np.float32)
    R._set_mask_bits(ref, int(p[0]), int(p[1]))
    check(np.array_equal(ref, plane), "_set_mask_bits reference == _unpack_block vectorized")


# --------------------------------------------------------------------------- #
# 8. archive pack -> read-from-zip == read-from-dir
# --------------------------------------------------------------------------- #
def test_archive_roundtrip():
    print("\n[8] archive pack -> read-from-zip == read-from-dir")
    with tempfile.TemporaryDirectory() as tmp:
        # write 2 gens x 2 games of REAL packed records
        for gen in ("gen0", "gen1"):
            d = os.path.join(tmp, "games", gen)
            os.makedirs(d)
            for g in range(2):
                with gzip.open(os.path.join(d, f"game_{g}.gz"), "wb") as f:
                    for s in range(4):
                        rec = make_rec(seed=hash((gen, g, s)) % (2**31))
                        pi = [-1.0] * R.POLICY_SIZE
                        for k in np.argwhere(rec["probabilities"] >= 0).ravel():
                            pi[int(k)] = float(rec["probabilities"][int(k)])
                        pp = list(rec["piece_planes"])
                        fields = ([5, 1] + pi + pp +
                                  [rec["rule50_count"], rec["castling_us_ooo_sq"],
                                   rec["castling_us_oo_sq"], rec["castling_them_ooo_sq"],
                                   rec["castling_them_oo_sq"],
                                   rec["ep_mask"][0], rec["ep_mask"][1],
                                   rec["checks_remaining_us"], rec["checks_remaining_them"],
                                   rec["side_to_move"],
                                   rec["result_q"], rec["result_d"], 0, 0,
                                   rec["best_q"], rec["best_d"], 0, 0, 0, 0, 0, 200, 0, 0])
                        f.write(R._STRUCT.pack(*fields))
        bundle = os.path.join(tmp, "b.zip")
        rc = subprocess.run([sys.executable, os.path.join(HERE, "archive.py"),
                             "pack", os.path.join(tmp, "games"), "--out", bundle],
                            capture_output=True, text=True)
        check(rc.returncode == 0 and os.path.exists(bundle), "archive.py pack produced bundle")
        dir_files = sorted(glob.glob(os.path.join(tmp, "games", "**", "*.gz"), recursive=True))
        dir_recs = []
        for fp in dir_files:
            dir_recs += R.read_records(fp)
        zip_recs = R.read_records_from_zip(bundle)
        check(len(dir_recs) == len(zip_recs) == 16, f"record count 16 (got {len(zip_recs)})")

        def keyset(rs):
            return sorted(hash((tuple(np.round(r["probabilities"], 6)), tuple(r["piece_planes"])))
                          for r in rs)
        check(keyset(dir_recs) == keyset(zip_recs), "zip records == dir records (bit-faithful)")


# --------------------------------------------------------------------------- #
# 9. audit_generation.py catches corrupted games (and passes clean ones)
# --------------------------------------------------------------------------- #
def _audit_game(rng, n_plies, white_result, version=4):
    """A well-formed game: alternating side to move, one final result, pi over 30
    legal moves, best = most visited, repetition-free boards."""
    recs = []
    for ply in range(n_plies):
        stm = ply % 2
        pi = np.full(R.POLICY_SIZE, -1.0, dtype=np.float32)
        legal = rng.choice(R.POLICY_SIZE, size=30, replace=False)
        v = rng.random(30).astype(np.float32)
        pi[legal] = v / v.sum()
        best = int(legal[int(np.argmax(v))])
        pp = [0] * (R.HISTORY_PLANES * 2)
        pp[0] = int(rng.integers(1, 2**62))           # a different board every ply
        pp[2] = int(rng.integers(1, 2**62))
        zq = white_result if stm == 0 else -white_result
        rec = dict(version=version, pi=pi, pp=pp, stm=stm, result_q=float(zq),
                   result_d=1.0 if white_result == 0 else 0.0, best=best, played=best,
                   best_q=0.1, best_d=0.2, orig_q=0.05, orig_d=0.25, kld=0.3)
        recs.append(rec)
    return recs


def _audit_pack(rec):
    fields = ([rec["version"], 1] + rec["pi"].tolist() + rec["pp"] +
              [3, 255, 255, 255, 255, 0, 0, 8, 8, rec["stm"],
               rec["result_q"], rec["result_d"], 0.1, 0.2, rec["best_q"], rec["best_d"],
               rec["best_q"], rec["best_d"], rec["orig_q"], rec["orig_d"], rec["kld"],
               800, rec["played"], rec["best"]])
    return R._STRUCT.pack(*fields)


def _run_audit(games, tmp, name):
    import zipfile
    path = os.path.join(tmp, name + ".zip")
    with zipfile.ZipFile(path, "w") as zf:
        for k, g in enumerate(games):
            zf.writestr(f"game_{k}.gz", gzip.compress(b"".join(_audit_pack(r) for r in g)))
    p = subprocess.run([sys.executable, os.path.join(HERE, "audit_generation.py"), path],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    counts = {}
    for line in p.stdout.splitlines():
        line = line.strip()
        if ":" in line and line.split(":")[0].replace("_", "").isalnum():
            k, _, v = line.partition(":")
            if v.strip().isdigit():
                counts[k.strip()] = int(v)
    return p.returncode, counts


def test_audit_generation():
    print("\n[9] audit_generation.py: clean games pass, each corruption is caught")
    rng = np.random.default_rng(9)
    clean = [_audit_game(rng, 24, +1), _audit_game(rng, 17, -1), _audit_game(rng, 30, 0)]
    with tempfile.TemporaryDirectory() as tmp:
        rc, c = _run_audit(clean, tmp, "clean")
        check(rc == 0 and c.get("game_result") == 0, f"clean games pass (rc={rc})")

        def corrupted(key, mutate):
            games = [[dict(r) for r in g] for g in clean]
            mutate(games)
            rc, c = _run_audit(games, tmp, key)
            check(rc == 1 and c.get(key, 0) >= 1, f"{key}: caught (rc={rc}, count={c.get(key)})")

        corrupted("game_result", lambda g: g[0][5].update(result_q=-g[0][5]["result_q"]))
        corrupted("stm_alternation", lambda g: g[1][4].update(stm=1 - g[1][4]["stm"],
                                                               result_q=-g[1][4]["result_q"]))
        def illegal_best(g):
            r = g[2][3]
            r["best"] = int(np.nonzero(r["pi"] < 0)[0][0])
        corrupted("move_idx", illegal_best)
        def not_most_visited(g):
            r = g[0][7]
            legal = np.nonzero(r["pi"] >= 0)[0]
            r["best"] = int(legal[np.argmin(r["pi"][legal])])
            r["played"] = r["best"]
        corrupted("best_not_most_visited", not_most_visited)
        corrupted("orig_copy_v4", lambda g: g[1][2].update(orig_q=0.1, orig_d=0.2, kld=0.0))


# --------------------------------------------------------------------------- #
# 10. diff_focus: records without a raw eval (data < v4) are neither dropped
#     like dull positions nor kept like surprising ones, whatever the file order
# --------------------------------------------------------------------------- #
def test_diff_focus_unknown_orig():
    print("\n[10] diff_focus keeps records without a raw eval at the average rate")
    rng = np.random.default_rng(10)
    n = 1500

    def pack(rule50, orig_q, kld):
        pi = np.full(R.POLICY_SIZE, -1.0, dtype=np.float32)
        legal = rng.choice(R.POLICY_SIZE, size=20, replace=False)
        pi[legal] = 1.0 / 20
        pp = [int(x) for x in rng.integers(1, 2**62, size=R.HISTORY_PLANES * 2)]
        best_q, best_d = 0.1, 0.2
        orig_d = best_d if orig_q == best_q else 0.3
        fields = ([3, 1] + pi.tolist() + pp +
                  [rule50, 255, 255, 255, 255, 0, 0, 8, 8, 0,
                   1.0, 0.0, 0.1, 0.2, best_q, best_d, best_q, best_d, orig_q, orig_d, kld,
                   800, int(legal[0]), int(legal[0])])
        return R._STRUCT.pack(*fields)

    with tempfile.TemporaryDirectory() as tmp:
        # "a_..." is read first: the records without a raw eval come before any other.
        with gzip.open(os.path.join(tmp, "a_unknown.gz"), "wb") as f:
            for _ in range(n):
                f.write(pack(11, 0.1, 0.0))                  # orig == best, kld 0: the copy
        with gzip.open(os.path.join(tmp, "b_known.gz"), "wb") as f:
            for _ in range(n):
                f.write(pack(22, 0.7, 0.0))                  # surprise 0.6 -> keep 0.2 + 0.6 = 0.8
        ds = D.FairyDataset(tmp, diff_focus=True, df_slope=1.0, df_kld_w=0.5, df_min=0.2)
        kept_unknown = sum(1 for c in ds._cached if c["rule50_count"] == 11) / n
        kept_known = sum(1 for c in ds._cached if c["rule50_count"] == 22) / n
    check(abs(kept_known - 0.8) < 0.05, f"known records kept at {kept_known:.3f} (keep prob 0.8)")
    check(abs(kept_unknown - 0.8) < 0.05,
          f"records without a raw eval kept at {kept_unknown:.3f}, the average rate "
          f"(0.2 would treat them as dull positions, 1.0 as surprising ones)")


def main():
    print("=" * 60)
    print("EXTREME TESTS — Python training pipeline")
    print("=" * 60)
    test_struct_layout()
    test_wdl_from_qd()
    test_qmix()
    test_legacy_search_q_sign()
    test_sparse_equals_dense()
    test_policy_loss_masking()
    test_reconstruct_aux()
    test_bitboard_decode()
    test_archive_roundtrip()
    test_audit_generation()
    test_diff_focus_unknown_orig()
    print("\n" + "=" * 60)
    print(f"RESULT: {PASS} passed, {FAIL} failed")
    print("=" * 60)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
