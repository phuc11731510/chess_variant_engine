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
    """Set 1.0 at every board square present in a 128-bit mask (s = rank*12+file)."""
    for word, bits in ((0, lo), (1, hi)):
        while bits:
            b = bits & (-bits)        # lowest set bit
            s = word * 64 + (b.bit_length() - 1)
            bits ^= b
            rank, file = divmod(s, 12)
            if rank < BOARD and file < BOARD:
                plane[rank, file] = 1.0


def reconstruct_planes(rec):
    """Rebuild the dense [226, 10, 10] float32 NN input from a record.

    Must reproduce the C++ UnpackInputPlanes output bit/value-exactly.
    """
    planes = np.zeros((NUM_PLANES, BOARD, BOARD), dtype=np.float32)
    pp = rec["piece_planes"]
    for p in range(HISTORY_PLANES):
        _set_mask_bits(planes[p], pp[2 * p], pp[2 * p + 1])
    # aux 4: en passant plane (bitboard mask).
    _set_mask_bits(planes[AUX_BASE + 4], rec["ep_mask"][0], rec["ep_mask"][1])
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


def read_records(filename):
    """Read all records from a .gz (or raw .bin) file."""
    opener = gzip.open if filename.endswith(".gz") else open
    out = []
    with opener(filename, "rb") as f:
        while True:
            buf = f.read(RECORD_SIZE)
            if not buf:
                break
            if len(buf) != RECORD_SIZE:
                raise ValueError(f"truncated record ({len(buf)} bytes) in {filename}")
            out.append(unpack_record(buf))
    return out


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
