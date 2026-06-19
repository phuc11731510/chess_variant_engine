"""Independent bit-level test of the Python decoder (`_set_mask_bits`).

Verifies, for every board square, that a 128-bit mask with exactly bit
s = rank*12 + file set decodes to exactly cell (rank, file) and nothing else;
and that padding-column bits (file 10, 11) never leak onto the 10x10 board.

This is the Python counterpart of the C++ `--test-bits` E1 check, so both sides
of the C++/Python bit handling are verified in isolation (the round-trip test
then ties them together).
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trainingdata_reader import _set_mask_bits  # noqa: E402


def split_bit(s):
    """A 128-bit mask with only bit s set, as (lo64, hi64)."""
    lo = (1 << s) if s < 64 else 0
    hi = (1 << (s - 64)) if s >= 64 else 0
    return lo, hi


def main():
    ok = True

    # 1. Every board square (rank,file in 0..9) -> exactly cell (rank,file).
    for rank in range(10):
        for file in range(10):
            s = rank * 12 + file
            lo, hi = split_bit(s)
            plane = np.zeros((10, 10), dtype=np.float32)
            _set_mask_bits(plane, lo, hi)
            nz = np.argwhere(plane != 0)
            if len(nz) != 1 or tuple(nz[0]) != (rank, file):
                print(f"[FAIL] s={s} (r{rank},f{file}) -> {[tuple(x) for x in nz]}")
                ok = False

    # 2. Padding columns (file 10, 11) must NEVER leak onto the board.
    for rank in range(10):
        for file in (10, 11):
            s = rank * 12 + file
            lo, hi = split_bit(s)
            plane = np.zeros((10, 10), dtype=np.float32)
            _set_mask_bits(plane, lo, hi)
            if plane.any():
                print(f"[FAIL] padding s={s} (r{rank},f{file}) leaked onto board")
                ok = False

    # 3. A full-board mask (all 100 board squares set) -> all 100 cells = 1.0.
    lo_all = hi_all = 0
    for rank in range(10):
        for file in range(10):
            s = rank * 12 + file
            if s < 64:
                lo_all |= (1 << s)
            else:
                hi_all |= (1 << (s - 64))
    plane = np.zeros((10, 10), dtype=np.float32)
    _set_mask_bits(plane, lo_all, hi_all)
    if int(plane.sum()) != 100:
        print(f"[FAIL] full-board mask set {int(plane.sum())} cells, expected 100")
        ok = False

    if ok:
        print("[PASS] Python decoder: all 100 board squares map exactly; "
              "padding rejected; full-board mask fills 100 cells.")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
