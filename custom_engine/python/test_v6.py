"""Tests for the v6 game container (trainingdata_v6.py) and its use in training.

    python test_v6.py                      # synthetic cases only
    python test_v6.py games_genN.zip       # + real games: v5 -> v6 bit-exact, dataset equality

1. Synthetic games: chained history, broken chain, first record, a policy that
   is not n/sum(n) (stored as float), no legal move, zero visits, max values.
2. Damaged files: truncated, flipped byte, trailing bytes, bad magic -> ValueError.
3. Real data (if given): every game v5 -> v6 -> decode equals v5 in every bit
   of every field; FairyDataset over the v5 bundle, the v6 bundle and a MIXED
   bundle (half v5, half v6) builds identical compact caches and identical
   packed training samples; load time of each.
"""

import gzip
import io
import lzma
import os
import sys
import tempfile
import time
import zipfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trainingdata_reader as tr  # noqa: E402
import trainingdata_v6 as v6  # noqa: E402

FAILS = []


def check(ok, what):
    print(("  [PASS] " if ok else "  [FAIL] ") + what)
    if not ok:
        FAILS.append(what)


def same(a, b):
    for k, v in a.items():
        w = b[k]
        if isinstance(v, np.ndarray):
            if v.tobytes() != np.asarray(w, v.dtype).tobytes():
                return False
        elif isinstance(v, float):
            if np.float32(v).tobytes() != np.float32(w).tobytes():
                return False
        elif v != w:
            return False
    return True


# --------------------------------------------------------------------------- #
rng = np.random.default_rng(20260928)


def rand_board():
    """27 planes x (lo, hi): a few pieces on real squares (files 0-9, ranks 0-9)."""
    b = np.zeros((27, 2), np.uint64)
    for _ in range(rng.integers(2, 30)):
        p = int(rng.integers(0, 26))
        s = int(rng.integers(0, 10)) * 12 + int(rng.integers(0, 10))
        b[p, s // 64] |= np.uint64(1) << np.uint64(s % 64)
    if rng.random() < 0.2:                       # repetition plane: all squares
        b[26, 0] = np.uint64(0xFFFFFFFFFFFFFFFF)
        b[26, 1] = np.uint64(0x00FFFFFFFFFFFFFF)
    return b


def synth_game(n, broken_at=(), float_at=(), empty_at=(), zero_at=()):
    """A game whose history chains like the engine's, except at `broken_at`."""
    recs, prev = [], None
    for k in range(n):
        planes = np.zeros((8, 27, 2), np.uint64)
        planes[0] = rand_board()
        if prev is not None and k not in broken_at:
            planes[1:] = v6.other_frame(prev)[:7]
        elif k in broken_at:
            for d in range(1, 8):
                planes[d] = rand_board()
        prev = planes
        pi = np.full(10600, -1.0, np.float32)
        visits = 801
        if k not in empty_at:
            legal = np.sort(rng.choice(10600, size=int(rng.integers(1, 120)), replace=False))
            if k in float_at:
                pi[legal] = rng.random(len(legal)).astype(np.float32)
            elif k in zero_at:
                pi[legal] = 0.0
                visits = 1
            else:
                cnt = rng.multinomial(800, rng.dirichlet(np.ones(len(legal)) * 0.3))
                pi[legal] = cnt.astype(np.float32) / np.float32(800)
        r = {"version": 6, "input_format": 1, "probabilities": pi,
             "piece_planes": planes.reshape(-1), "rule50_count": int(rng.integers(0, 256)),
             "castling_us_ooo_sq": 0xFF, "castling_us_oo_sq": int(rng.integers(0, 100)),
             "castling_them_ooo_sq": 90, "castling_them_oo_sq": 0xFF,
             "ep_mask": (int(rng.integers(0, 2**63)), int(rng.integers(0, 2**63))),
             "checks_remaining_us": 8, "checks_remaining_them": int(rng.integers(0, 9)),
             "side_to_move": k & 1, "visits": visits,
             "played_idx": int(rng.integers(0, 10600)), "best_idx": 65535}
        for key in v6.FLOAT_KEYS:
            r[key] = float(np.float32(rng.standard_normal()))
        r["policy_kld"] = float(np.float32(3.4e38))
        recs.append(r)
    return recs


def header(data):
    return v6._HEADER.unpack_from(lzma.decompress(data))


print("== 1. Synthetic games ==")
cases = {
    "chained 60 records": dict(n=60),
    "broken chain at 7 and 30": dict(n=40, broken_at=(7, 30)),
    "float policy at 3, 11": dict(n=20, float_at=(3, 11)),
    "no legal move at 0, 5": dict(n=10, empty_at=(0, 5)),
    "zero visits at 2": dict(n=6, zero_at=(2,)),
    "one record": dict(n=1),
}
for label, kw in cases.items():
    recs = synth_game(**kw)
    data = v6.encode_game(recs)
    back = v6.decode_game(data)
    ok = len(back) == len(recs) and all(same(a, b) for a, b in zip(recs, back))
    h = header(data)
    full = 1 + len(kw.get("broken_at", ()))
    check(ok and h[7] == full, f"{label}: bit-exact round trip, {h[7]} full record(s)")
    sp = v6.decode_game(data, dense=False)
    check(all("probabilities" not in r for r in sp) and
          all(np.array_equal(r["legal_pi"], b["probabilities"][r["legal_idx"]]) for r, b in zip(sp, back)),
          f"{label}: dense=False gives the same sparse policy")
recs = synth_game(12, float_at=(4,))
check(header(v6.encode_game(recs))[6] == np.count_nonzero(recs[4]["probabilities"] >= 0),
      "float policy counted in the header (LF)")

print("== 2. Damaged files ==")
good = v6.encode_game(synth_game(15))
raw = lzma.decompress(good)
bad = {
    "truncated xz": good[:-7],
    "flipped byte in xz": good[:40] + bytes([good[40] ^ 0x55]) + good[41:],
    "trailing payload bytes": lzma.compress(raw + b"\0", format=lzma.FORMAT_XZ),
    "short payload": lzma.compress(raw[:-3], format=lzma.FORMAT_XZ),
    "bad magic": lzma.compress(b"XXXX" + raw[4:], format=lzma.FORMAT_XZ),
    "first record not full": lzma.compress(raw[:v6._HEADER.size] + b"\0" + raw[v6._HEADER.size + 1:],
                                           format=lzma.FORMAT_XZ),
}
for label, data in bad.items():
    try:
        v6.decode_game(data, label)
        check(False, f"{label}: rejected")
    except ValueError:
        check(True, f"{label}: rejected with ValueError")

# --------------------------------------------------------------------------- #
if len(sys.argv) > 1:
    import dataset as ds  # noqa: E402  (torch)
    src = sys.argv[1]
    print(f"== 3. Real games: {src} ==")
    tmp = tempfile.mkdtemp()
    z5, z6, zmix = (os.path.join(tmp, f) for f in ("v5.zip", "v6.zip", "mix.zip"))
    t_enc, n_rec, n_game, exact = 0.0, 0, 0, True
    size5 = size6 = 0
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(z5, "w") as a, \
            zipfile.ZipFile(z6, "w") as b, zipfile.ZipFile(zmix, "w") as m:
        for info in zin.infolist():
            if not info.filename.endswith(".gz"):
                continue
            blob = zin.read(info.filename)
            raw = gzip.decompress(blob)
            recs = [tr.unpack_record(raw[i:i + tr.RECORD_SIZE]) for i in range(0, len(raw), tr.RECORD_SIZE)]
            t = time.perf_counter()
            x = v6.encode_game(recs)
            t_enc += time.perf_counter() - t
            back = v6.decode_game(x, info.filename)
            exact &= len(back) == len(recs) and all(same(p, q) for p, q in zip(recs, back))
            name6 = info.filename[:-3] + ".xz"
            for zf, nm, d in ((a, info.filename, blob), (b, name6, x),
                              (m, *((name6, x) if n_game % 2 else (info.filename, blob)))):
                zi = zipfile.ZipInfo(nm, date_time=info.date_time)
                zf.writestr(zi, d)
            n_rec += len(recs)
            n_game += 1
            size5 += len(blob)
            size6 += len(x)
    check(exact, f"{n_game} games, {n_rec} positions: v5 -> v6 -> decode bit-exact in every field")
    print(f"  size: v5 {size5 / n_rec:.1f} B/position, v6 {size6 / n_rec:.1f} B/position "
          f"({size5 / size6:.2f}x smaller); encode {t_enc / n_rec * 1e6:.0f} us/position")

    def load(z):
        t = time.perf_counter()
        d = ds.FairyDataset(z, q_ratio=0.2, cache=True, sparse=True, seed=7, packed=True)
        return d, time.perf_counter() - t

    d5, t5 = load(z5)
    d6, t6 = load(z6)
    dm, tm = load(zmix)
    print(f"  FairyDataset load: v5 {t5:.1f} s, v6 {t6:.1f} s ({t5 / t6:.1f}x faster), mixed {tm:.1f} s")
    keys = ("piece_planes", "ep_mask", "pi_idx", "pi_val", "value")

    def same_cache(x, y):
        if len(x._cached) != len(y._cached):
            return False
        for c, e in zip(x._cached, y._cached):
            for k in keys:
                if np.asarray(c[k]).tobytes() != np.asarray(e[k]).tobytes() or \
                        np.asarray(c[k]).dtype != np.asarray(e[k]).dtype:
                    return False
            for k in ("castling_us_ooo_sq", "castling_us_oo_sq", "castling_them_ooo_sq",
                      "castling_them_oo_sq", "rule50_count", "checks_remaining_us",
                      "checks_remaining_them"):
                if c[k] != e[k]:
                    return False
        return True

    check(same_cache(d5, d6), "v5 and v6 bundles: identical compact cache (every field, dtype)")
    check(same_cache(d5, dm), "mixed v5/v6 bundle: identical compact cache")
    import torch  # noqa: E402
    batch = [d6[i] for i in range(0, len(d6), max(1, len(d6) // 512))]
    batch5 = [d5[i] for i in range(0, len(d5), max(1, len(d5) // 512))]
    x6 = ds.unpack_batch(ds.collate_packed(batch), "cpu")
    x5 = ds.unpack_batch(ds.collate_packed(batch5), "cpu")
    check(all(torch.equal(p, q) for p, q in zip(x5, x6)),
          "training tensors (planes, policy, value) identical for v5 and v6")

print(f"\n{'ALL PASS' if not FAILS else str(len(FAILS)) + ' FAIL(S)'}")
sys.exit(1 if FAILS else 0)
