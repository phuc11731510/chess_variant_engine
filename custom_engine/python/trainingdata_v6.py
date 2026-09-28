"""Compact per-game training-data container (".xz", data version 6).

One self-play game = one file. Instead of N fixed 45940-byte records (92% of
which is a dense probabilities[10600] array that is -1 almost everywhere), the
game is stored column by column and xz-compressed. Measured on 100 real games
(gen4): 472 -> ~100 bytes per position, LOSSLESS -- decode() rebuilds every
record bit-identical to the 45940-byte form (test_v6.py checks every field of
every record of real data).

Three facts make it small:
  1. Policy: only the legal moves are stored (sorted NN indices, delta-coded),
     with their INTEGER visit counts. The engine computes pi = float(n) /
     float(sum n), so pi is rebuilt exactly. A record whose pi does not fit that
     form is stored with float32 values instead (FLAG_FLOAT_PI; never produced by
     the engine, only possible when converting unusual old data).
  2. History planes: plies 1..7 of a position are plies 0..6 of the position
     before it, seen from the other side (swap us/them planes, mirror ranks).
     Only ply 0 is stored; a record whose history does NOT chain that way (the
     first record of a game, or a broken chain) is stored in full (FLAG_FULL).
     The writer checks the chain itself, so the rebuild is exact by construction.
  3. Column layout: all indices together, all counts together, all boards
     together... so xz sees long runs of similar bytes.

Payload (little-endian), then xz (LZMA2 preset 9e, 1 MiB dictionary, CRC64):
  header  4s magic "FZD6", u32 container revision (=1), u32 data_version,
          u32 input_format, u32 N records, u32 L legal entries (all records),
          u32 LF legal entries stored as float32, u32 F full records
  u8   flags[N]                 bit0 FLAG_FULL, bit1 FLAG_FLOAT_PI
  u16  n_legal[N]
  u16  legal_delta[L]           per record: first index, then differences (> 0)
  u16  counts[L - LF]           records without FLAG_FLOAT_PI, in order
  f32  pi_float[LF]             records with FLAG_FLOAT_PI, in order
  u64  cur[N][27][2]            ply-0 board planes
  u64  hist[F][7][27][2]        plies 1..7 of the FLAG_FULL records, in order
  u8   rule50[N]
  u8   castling[4][N]           us_ooo, us_oo, them_ooo, them_oo (rook square / 0xFF)
  u64  ep[N][2]
  u8   checks_us[N], checks_them[N], side_to_move[N]
  f32  floats[11][N]            result_q/d, root_q/d, best_q/d, played_q/d, orig_q/d, policy_kld
  u32  visits[N]
  u16  played_idx[N], best_idx[N]

data_version keeps the MEANING of the fields (1..5 for converted old games, 6
for games the engine writes in this container): dataset.py's sign / castling /
orig_q rules still apply per version. The C++ writer/reader
(src/lczero_chess/trainingdata/) implement the same layout.
"""

import lzma
import struct

import numpy as np

MAGIC = b"FZD6"
CONTAINER_REVISION = 1
DATA_VERSION = 6
FLAG_FULL = 1
FLAG_FLOAT_PI = 2
PLY_PLANES = 27
N_PLY = 8
REP_PLANE = 26
POLICY_SIZE = 10600
_HEADER = struct.Struct("<4s7I")
FLOAT_KEYS = ("result_q", "result_d", "root_q", "root_d", "best_q", "best_d",
              "played_q", "played_d", "orig_q", "orig_d", "policy_kld")
CASTLING_KEYS = ("castling_us_ooo_sq", "castling_us_oo_sq",
                 "castling_them_ooo_sq", "castling_them_oo_sq")
# xz settings: strongest preset; the dictionary only needs to cover one game
# (~90 KB raw, the longest a few hundred KB), which keeps the encoder at ~11 MB
# of RAM instead of ~674 MB for plain `xz -9`.
XZ_FILTERS = [{"id": lzma.FILTER_LZMA2, "preset": 9 | lzma.PRESET_EXTREME, "dict_size": 1 << 20}]

_M12 = np.uint64(0xFFF)


# --------------------------------------------------------------------------- #
# Frame change: the same board seen by the other side.
# --------------------------------------------------------------------------- #
def _row(lo, hi, r):
    """12-bit row r (bits 12r..12r+11) of 128-bit masks given as uint64 arrays."""
    b = 12 * r
    if b + 12 <= 64:
        return (lo >> np.uint64(b)) & _M12
    if b >= 64:
        return (hi >> np.uint64(b - 64)) & _M12
    return ((lo >> np.uint64(b)) | (hi << np.uint64(64 - b))) & _M12


def _mirror(words):
    """Mirror ranks (row r <-> row 9-r) of masks words[..., 2] (lo, hi)."""
    lo, hi = words[..., 0], words[..., 1]
    out = np.zeros_like(words)
    for r in range(10):
        v = _row(lo, hi, r)
        b = 12 * (9 - r)
        if b + 12 <= 64:
            out[..., 0] |= v << np.uint64(b)
        elif b >= 64:
            out[..., 1] |= v << np.uint64(b - 64)
        else:
            out[..., 0] |= v << np.uint64(b)
            out[..., 1] |= v >> np.uint64(64 - b)
    return out


def other_frame(ply):
    """Board planes [..., 27, 2] seen by the other side: us/them groups swapped,
    ranks mirrored. The repetition plane is a flag (all squares or none): copied."""
    out = np.empty_like(ply)
    out[..., 0:13, :] = _mirror(ply[..., 13:26, :])
    out[..., 13:26, :] = _mirror(ply[..., 0:13, :])
    out[..., REP_PLANE, :] = ply[..., REP_PLANE, :]
    return out


# --------------------------------------------------------------------------- #
# Encode (Python side: converting old games, tests; the engine has its own).
# --------------------------------------------------------------------------- #
def _policy_counts(pi, visits):
    """Integer visit counts n with float32(n) / float32(sum n) == pi exactly, or
    None. The engine's total is the sum of the root's edge visits, normally
    visits - 1 (the root's own visit); a few neighbours are tried too."""
    if not len(pi):
        return np.zeros(0, np.uint16)
    p64 = pi.astype(np.float64)
    for t in (visits - 1, visits, visits - 2, visits + 1):
        if t < 0 or t > 0xFFFF * len(pi):
            continue
        n = np.rint(p64 * t)
        if n.max(initial=0) > 0xFFFF or int(n.sum()) != t:
            continue
        n = n.astype(np.uint16)
        back = (np.zeros(len(n), np.float32) if t == 0 else
                n.astype(np.float32) / np.float32(t))
        if np.array_equal(back.view(np.uint32), pi.view(np.uint32)):
            return n
    return None


def encode_game(records):
    """Records (dicts as trainingdata_reader.unpack_record returns, one game in
    order) -> the compressed .xz bytes. Lossless: decode_game() gives them back."""
    if not records:
        raise ValueError("a game needs at least one record")
    ver, fmt = records[0]["version"], records[0]["input_format"]
    n = len(records)
    flags = np.zeros(n, np.uint8)
    n_legal = np.zeros(n, np.uint16)
    deltas, counts, pif = [], [], []
    cur = np.empty((n, PLY_PLANES, 2), np.uint64)
    hist = []
    seq = None          # board planes of the chain so far, in THIS record's frame
    for k, r in enumerate(records):
        if r["version"] != ver or r["input_format"] != fmt:
            raise ValueError("records of one game must share version and input format")
        pi = np.asarray(r["probabilities"], np.float32)
        legal = np.nonzero(pi >= 0)[0]
        if len(legal) > 0xFFFF:
            raise ValueError("too many legal moves")
        n_legal[k] = len(legal)
        deltas.append(np.diff(legal, prepend=0).astype(np.uint16))
        c = _policy_counts(pi[legal], int(r["visits"]))
        if c is None:
            flags[k] |= FLAG_FLOAT_PI
            pif.append(pi[legal])
        else:
            counts.append(c)
        planes = np.asarray(r["piece_planes"], np.uint64).reshape(N_PLY, PLY_PLANES, 2)
        cur[k] = planes[0]
        # Chain: the previous record's plies 0..6 in this record's frame.
        if seq is None or not np.array_equal(planes[1:], seq[:N_PLY - 1]):
            flags[k] |= FLAG_FULL
            hist.append(planes[1:])
        seq = other_frame(planes)
    lf = sum(len(x) for x in pif)
    l_total = int(n_legal.sum(dtype=np.int64))
    cols = [
        _HEADER.pack(MAGIC, CONTAINER_REVISION, ver, fmt, n, l_total, lf, len(hist)),
        flags.tobytes(), n_legal.astype("<u2").tobytes(),
        _cat(deltas, "<u2"), _cat(counts, "<u2"), _cat(pif, "<f4"),
        cur.astype("<u8").tobytes(), _cat(hist, "<u8"),
        np.array([r["rule50_count"] for r in records], np.uint8).tobytes(),
    ]
    for key in CASTLING_KEYS:
        cols.append(np.array([r[key] for r in records], np.uint8).tobytes())
    cols.append(np.array([r["ep_mask"] for r in records], "<u8").tobytes())
    for key in ("checks_remaining_us", "checks_remaining_them", "side_to_move"):
        cols.append(np.array([r[key] for r in records], np.uint8).tobytes())
    for key in FLOAT_KEYS:
        cols.append(np.array([r[key] for r in records], "<f4").tobytes())
    cols.append(np.array([r["visits"] for r in records], "<u4").tobytes())
    cols.append(np.array([r["played_idx"] for r in records], "<u2").tobytes())
    cols.append(np.array([r["best_idx"] for r in records], "<u2").tobytes())
    return lzma.compress(b"".join(cols), format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64,
                         filters=XZ_FILTERS)


def _cat(arrs, dt):
    return np.concatenate(arrs).astype(dt).tobytes() if arrs else b""


# --------------------------------------------------------------------------- #
# Decode.
# --------------------------------------------------------------------------- #
class _Cursor:
    def __init__(self, buf, where):
        self.buf, self.pos, self.where = buf, _HEADER.size, where

    def take(self, dtype, count):
        dt = np.dtype(dtype)
        end = self.pos + dt.itemsize * count
        if end > len(self.buf):
            raise ValueError(f"truncated v6 game ({self.where})")
        a = np.frombuffer(self.buf, dt, count, self.pos)
        self.pos = end
        return a


def decode_arrays(data, where=""):
    """Compressed game -> dict of whole-game arrays (the fast path for training):
      version, input_format, n,
      legal_idx  uint16[L], legal_start int64[N+1] (record k owns [s[k], s[k+1])),
      legal_pi   float32[L],
      planes     uint64[N, 8, 27, 2] (all 8 plies, rebuilt),
      rule50, castling uint8[4, N], ep uint64[N, 2], checks_us, checks_them, stm,
      floats     dict key -> float32[N], visits, played_idx, best_idx.
    Raises ValueError on a damaged or inconsistent file."""
    try:
        buf = lzma.decompress(data, format=lzma.FORMAT_XZ)
    except lzma.LZMAError as e:
        raise ValueError(f"damaged v6 game ({where}): {e}") from None
    if len(buf) < _HEADER.size:
        raise ValueError(f"truncated v6 game ({where})")
    magic, rev, ver, fmt, n, l_total, lf, f = _HEADER.unpack_from(buf, 0)
    if magic != MAGIC or rev != CONTAINER_REVISION:
        raise ValueError(f"not a v6 game (magic {magic!r}, revision {rev}) ({where})")
    c = _Cursor(buf, where)
    flags = c.take(np.uint8, n)
    n_legal = c.take("<u2", n).astype(np.int64)
    if int(n_legal.sum()) != l_total or lf > l_total:
        raise ValueError(f"inconsistent v6 legal-move counts ({where})")
    delta = c.take("<u2", l_total).astype(np.int64)
    fl = (flags & FLAG_FLOAT_PI) != 0
    n_float = int(n_legal[fl].sum())
    if n_float != lf or int(np.count_nonzero(flags & FLAG_FULL)) != f:
        raise ValueError(f"inconsistent v6 flags ({where})")
    if flags.max(initial=0) > (FLAG_FULL | FLAG_FLOAT_PI) or (n and not flags[0] & FLAG_FULL):
        raise ValueError(f"invalid v6 flags ({where})")
    counts = c.take("<u2", l_total - lf)
    pif = c.take("<f4", lf)
    cur = c.take("<u8", n * PLY_PLANES * 2).reshape(n, PLY_PLANES, 2)
    hist = c.take("<u8", f * (N_PLY - 1) * PLY_PLANES * 2).reshape(f, N_PLY - 1, PLY_PLANES, 2)
    rule50 = c.take(np.uint8, n)
    castling = c.take(np.uint8, 4 * n).reshape(4, n)
    ep = c.take("<u8", 2 * n).reshape(n, 2)
    checks_us, checks_them, stm = (c.take(np.uint8, n) for _ in range(3))
    floats = {k: c.take("<f4", n) for k in FLOAT_KEYS}
    visits = c.take("<u4", n)
    played_idx = c.take("<u2", n)
    best_idx = c.take("<u2", n)
    if c.pos != len(buf):
        raise ValueError(f"v6 game has {len(buf) - c.pos} trailing bytes ({where})")

    # Policy: indices from the deltas (cumulative sum restarted per record).
    start = np.zeros(n + 1, np.int64)
    np.cumsum(n_legal, out=start[1:])
    cs = np.cumsum(delta)
    base = np.repeat(np.concatenate(([0], cs))[start[:-1]], n_legal)
    idx = cs - base
    if l_total:
        first = np.zeros(l_total, bool)
        first[start[:-1][n_legal > 0]] = True
        if (delta[~first] == 0).any() or idx.max() >= POLICY_SIZE:
            raise ValueError(f"invalid v6 legal-move indices ({where})")
    rec_of = np.repeat(np.arange(n), n_legal)
    pi = np.empty(l_total, np.float32)
    in_float = fl[rec_of]
    pi[in_float] = pif
    if l_total - lf:
        cnt = counts.astype(np.float32)
        tot = np.bincount(rec_of[~in_float], weights=counts, minlength=n)  # exact (< 2^53)
        t = tot.astype(np.float32)[rec_of[~in_float]]
        with np.errstate(invalid="ignore", divide="ignore"):
            pi[~in_float] = np.where(t > 0, cnt / np.where(t > 0, t, 1), np.float32(0))

    return {
        "version": ver, "input_format": fmt, "n": n,
        "legal_idx": idx.astype(np.uint16), "legal_start": start, "legal_pi": pi,
        "planes": _rebuild_planes(flags, cur, hist),
        "rule50": rule50, "castling": castling, "ep": ep,
        "checks_us": checks_us, "checks_them": checks_them, "stm": stm,
        "floats": floats, "visits": visits, "played_idx": played_idx, "best_idx": best_idx,
    }


def _rebuild_planes(flags, cur, hist):
    """All 8 plies of every record from ply 0 + the full records' plies 1..7.

    Canonical frame A = the frame of even records (record parity is absolute).
    Board of record j in A: cur[j] if j is even, else other_frame(cur[j]). A
    segment starts at each FLAG_FULL record s; its plies before s come from s's
    stored plies (in s's frame -> A the same way). Record k of the segment reads
    plies k-0..k-7 of the segment's A sequence, then goes back to its own frame."""
    n = len(flags)
    out = np.empty((n, N_PLY, PLY_PLANES, 2), np.uint64)
    if n == 0:
        return out
    odd = (np.arange(n) & 1).astype(bool)
    cur_a = cur.copy()
    cur_a[odd] = other_frame(cur[odd])
    starts = np.nonzero(flags & FLAG_FULL)[0]
    ends = np.append(starts[1:], n)
    for h, (s, e) in enumerate(zip(starts, ends)):
        pre = hist[h][::-1]                           # plies s-7 .. s-1, in s's frame
        if s & 1:
            pre = other_frame(pre)
        seq = np.concatenate((pre, cur_a[s:e]))       # A frame; seq[7 + (k-s)] = record k
        seq_b = other_frame(seq)                      # the same boards in the odd frame
        k = np.arange(s, e)
        take = (7 + (k - s))[:, None] - np.arange(N_PLY)[None, :]
        even = (k & 1) == 0
        out[s:e][even] = seq[take[even]]              # frame change once per board,
        out[s:e][~even] = seq_b[take[~even]]          # not once per (record, ply)
    return out


def decode_game(data, where="", dense=True):
    """Compressed game -> list of record dicts, the same keys and values as
    trainingdata_reader.unpack_record gives for the 45940-byte form, plus
    'legal_idx' / 'legal_pi' (the sparse policy, which dataset.py uses instead of
    scanning the dense one). 'probabilities' is a read-only float32[10600] view;
    dense=False leaves it out (saves building 42 KB per position)."""
    a = decode_arrays(data, where)
    n, start = a["n"], a["legal_start"]
    probs = None
    if dense:
        probs = np.full((n, POLICY_SIZE), -1.0, np.float32)
        rec_of = np.repeat(np.arange(n), np.diff(start))
        probs[rec_of, a["legal_idx"]] = a["legal_pi"]
        probs.flags.writeable = False
    planes = a["planes"].reshape(n, N_PLY * PLY_PLANES * 2)
    fl = {k: a["floats"][k].tolist() for k in FLOAT_KEYS}
    rule50, visits = a["rule50"].tolist(), a["visits"].tolist()
    cast = [a["castling"][i].tolist() for i in range(4)]
    ep = a["ep"].tolist()
    cu, ct, stm = a["checks_us"].tolist(), a["checks_them"].tolist(), a["stm"].tolist()
    pidx, bidx = a["played_idx"].tolist(), a["best_idx"].tolist()
    out = []
    for k in range(n):
        r = {"version": a["version"], "input_format": a["input_format"],
             "piece_planes": planes[k],
             "legal_idx": a["legal_idx"][start[k]:start[k + 1]],
             "legal_pi": a["legal_pi"][start[k]:start[k + 1]],
             "rule50_count": rule50[k]}
        if probs is not None:
            r["probabilities"] = probs[k]
        for i, key in enumerate(CASTLING_KEYS):
            r[key] = cast[i][k]
        r["ep_mask"] = tuple(ep[k])
        r["checks_remaining_us"] = cu[k]
        r["checks_remaining_them"] = ct[k]
        r["side_to_move"] = stm[k]
        for key in FLOAT_KEYS:
            r[key] = fl[key][k]
        r["visits"] = visits[k]
        r["played_idx"] = pidx[k]
        r["best_idx"] = bidx[k]
        out.append(r)
    return out
