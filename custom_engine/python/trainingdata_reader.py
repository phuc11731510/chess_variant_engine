"""Reader for FairyZero TrainingDataV1 records (10x10 variant).

Mirrors the C++ struct `TrainingDataV1` (#pragma pack(1), 45940 bytes) and the
plane reconstruction of `UnpackInputPlanes` / `EncodePlanesIntoRecord`.

THE 3 CONVENTIONS THIS MUST MATCH (locked by the T5 round-trip test):
  1. policy index = MoveToNNIndex (probabilities[10600]).
  2. value order  = [Win, Draw, Loss] from side-to-move (q = win - loss).
  3. input planes = [226, 10, 10]; piece-plane bit s = rank*12 + file (Stockfish
     12-stride). Aux planes rebuilt from scalars; castling: us->rank0, them->rank9.
"""

import gzip
import random
import struct
import zipfile

import numpy as np

POLICY_SIZE = 10600
HISTORY_PLANES = 216          # 27 planes/ply * 8 ply
NUM_PLANES = 226
AUX_BASE = 216
NO_CASTLING_FILE = 0xFF
BOARD = 10

# Little-endian, packed (matches #pragma pack(1)). Field order == the C++ struct.
_FMT = ("<"
        "II"                       # version, input_format
        f"{POLICY_SIZE}f"          # probabilities[10600]
        f"{HISTORY_PLANES * 2}Q"   # piece_planes[216][2]  (lo,hi per plane)
        "5B"                       # rule50, 4x castling-file
        "2Q"                       # ep_mask[2]
        "3B"                       # checks_us, checks_them, side_to_move
        "11f"                      # result_q/d, root_q/d, best_q/d, played_q/d, orig_q/d, policy_kld
        "I"                        # visits
        "2H")                      # played_idx, best_idx
_STRUCT = struct.Struct(_FMT)
RECORD_SIZE = _STRUCT.size
assert RECORD_SIZE == 45940, f"record size {RECORD_SIZE} != 45940 (layout drift!)"


def unpack_record(buf):
    """Unpack a 45940-byte record into a dict."""
    v = _STRUCT.unpack(buf)
    i = 0
    r = {}
    r["version"] = v[i]; i += 1
    r["input_format"] = v[i]; i += 1
    r["probabilities"] = np.array(v[i:i + POLICY_SIZE], dtype=np.float32); i += POLICY_SIZE
    r["piece_planes"] = v[i:i + HISTORY_PLANES * 2]; i += HISTORY_PLANES * 2
    r["rule50_count"] = v[i]; i += 1
    r["castling_us_ooo_file"] = v[i]; i += 1
    r["castling_us_oo_file"] = v[i]; i += 1
    r["castling_them_ooo_file"] = v[i]; i += 1
    r["castling_them_oo_file"] = v[i]; i += 1
    r["ep_mask"] = (v[i], v[i + 1]); i += 2
    r["checks_remaining_us"] = v[i]; i += 1
    r["checks_remaining_them"] = v[i]; i += 1
    r["side_to_move"] = v[i]; i += 1
    r["result_q"] = v[i]; r["result_d"] = v[i + 1]; i += 2
    r["root_q"] = v[i]; r["root_d"] = v[i + 1]; i += 2
    r["best_q"] = v[i]; r["best_d"] = v[i + 1]; i += 2
    r["played_q"] = v[i]; r["played_d"] = v[i + 1]; i += 2
    r["orig_q"] = v[i]; r["orig_d"] = v[i + 1]; i += 2
    r["policy_kld"] = v[i]; i += 1
    r["visits"] = v[i]; i += 1
    r["played_idx"] = v[i]; r["best_idx"] = v[i + 1]; i += 2
    return r


def _set_mask_bits(plane, lo, hi):
    """Reference (scalar) decoder: set 1.0 at every board square present in a
    128-bit mask (s = rank*12+file). Kept as a slow-but-obvious reference that
    `test_bits.py` validates; `reconstruct_planes` uses the vectorized path."""
    for word, bits in ((0, lo), (1, hi)):
        while bits:
            b = bits & (-bits)        # lowest set bit
            s = word * 64 + (b.bit_length() - 1)
            bits ^= b
            rank, file = divmod(s, 12)
            if rank < BOARD and file < BOARD:
                plane[rank, file] = 1.0


# Precomputed (word, bit) maps for the 100 board cells (file 0-9, rank 0-9).
# Cell (rank,file) holds bit s = rank*12+file -> word s//64, bit s%64. Padding
# columns (file 10,11) are never indexed, so they cannot leak onto the board.
_S_GRID = (np.arange(BOARD)[:, None] * 12 + np.arange(BOARD)[None, :])  # [10,10] int
_WORD_GRID = (_S_GRID // 64).astype(np.intp)                            # [10,10] 0/1
_BIT_GRID = (_S_GRID % 64).astype(np.uint64)                            # [10,10]


def _unpack_block(words):
    """Vectorized bitboard unpack. `words`: uint64 array [..., 2] (lo, hi).
    Returns float32 [..., 10, 10] = 1.0 where the corresponding board bit is set.
    Produces output bit-identical to _set_mask_bits, ~10-50x faster (no Python loop)."""
    sel = words[..., _WORD_GRID]                 # [..., 10, 10] pick lo/hi per cell
    return ((sel >> _BIT_GRID) & np.uint64(1)).astype(np.float32)


def reconstruct_planes(rec):
    """Rebuild the dense [226, 10, 10] float32 NN input from a record.

    Must reproduce the C++ UnpackInputPlanes output bit/value-exactly.
    """
    planes = np.zeros((NUM_PLANES, BOARD, BOARD), dtype=np.float32)
    pp = np.asarray(rec["piece_planes"], dtype=np.uint64).reshape(HISTORY_PLANES, 2)
    planes[:HISTORY_PLANES] = _unpack_block(pp)                      # 216 history planes
    # aux 4: en passant plane (bitboard mask).
    planes[AUX_BASE + 4] = _unpack_block(np.asarray(rec["ep_mask"], dtype=np.uint64))
    # aux 0..3: castling rook squares. us -> bottom rank 0, them -> top rank 9.
    files = [rec["castling_us_ooo_file"], rec["castling_us_oo_file"],
             rec["castling_them_ooo_file"], rec["castling_them_oo_file"]]
    ranks = [0, 0, BOARD - 1, BOARD - 1]
    for k in range(4):
        if files[k] != NO_CASTLING_FILE:
            planes[AUX_BASE + k, ranks[k], files[k]] = 1.0
    # aux 5: rule50 normalized; aux 6: unused (zeros); aux 7: board-edge (all ones).
    planes[AUX_BASE + 5, :, :] = rec["rule50_count"] / 100.0
    planes[AUX_BASE + 7, :, :] = 1.0
    # aux 8/9: remaining checks normalized (7-check rule).
    planes[AUX_BASE + 8, :, :] = rec["checks_remaining_us"] / 7.0
    planes[AUX_BASE + 9, :, :] = rec["checks_remaining_them"] / 7.0
    return planes


def _iter_stream(f, where=""):
    """Yield fixed-size records from an open binary stream until EOF.

    A generator (not a list) so callers can compact+discard each record's dense
    probabilities[10600] (~42KB) immediately instead of holding them all at once."""
    while True:
        buf = f.read(RECORD_SIZE)
        if not buf:
            break
        if len(buf) != RECORD_SIZE:
            raise ValueError(f"truncated record ({len(buf)} bytes) in {where}")
        yield unpack_record(buf)


def _read_stream(f, where=""):
    """Read fixed-size records from an open binary stream until EOF (eager list)."""
    return list(_iter_stream(f, where))


def iter_records(filename):
    """Stream records from a .gz (or raw .bin) file one at a time (low peak RAM)."""
    opener = gzip.open if filename.endswith(".gz") else open
    with opener(filename, "rb") as f:
        yield from _iter_stream(f, filename)


def read_records(filename):
    """Read all records from a .gz (or raw .bin) file (eager; see iter_records)."""
    return list(iter_records(filename))


def iter_records_from_zip(zip_path):
    """Stream records from a .zip bundle of .gz/.bin games one at a time.

    Unlike read_records_from_zip (which materializes EVERY record's dense
    probabilities[10600] before returning), this yields one record at a time so
    the caller can compact+discard it. Peak RAM stays ~10x lower — this is what
    used to exhaust Colab's RAM at load time before a single training step ran."""
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if name.endswith("/"):
                continue
            with zf.open(name) as raw:
                if name.endswith(".gz"):
                    with gzip.GzipFile(fileobj=raw) as f:
                        yield from _iter_stream(f, f"{zip_path}:{name}")
                elif name.endswith(".bin"):
                    yield from _iter_stream(raw, f"{zip_path}:{name}")


def read_records_from_zip(zip_path):
    """Read all records from a .zip bundle of .gz/.bin games (eager list).

    Lets training run directly on the transfer bundle (e.g. one file downloaded
    from Google Drive on Colab) without unpacking it to disk first. For training
    prefer iter_records_from_zip to keep peak RAM low."""
    return list(iter_records_from_zip(zip_path))


class ShuffleBuffer:
    """Streaming Fisher-Yates shuffle buffer (ported from lc0 shufflebuffer.py).

    insert_or_replace: fills until `capacity`, then returns a uniformly random
    displaced item (so a long stream is fully shuffled within RAM bounds).
    """

    def __init__(self, capacity):
        assert capacity > 0
        self.capacity = capacity
        self.buf = []

    def insert_or_replace(self, item):
        if len(self.buf) < self.capacity:
            self.buf.append(item)
            return None
        j = random.randint(0, len(self.buf) - 1)
        out = self.buf[j]
        self.buf[j] = item
        return out

    def extract(self):
        if not self.buf:
            return None
        j = random.randint(0, len(self.buf) - 1)
        self.buf[j], self.buf[-1] = self.buf[-1], self.buf[j]
        return self.buf.pop()


def downsample(records, keep_prob, rng=random):
    """Keep each record with probability keep_prob (decorrelate within a game)."""
    return [r for r in records if rng.random() < keep_prob]
