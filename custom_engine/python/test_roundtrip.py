"""T5 round-trip test: Python reconstruction must match C++ UnpackInputPlanes.

Usage:
    # 1) emit ground truth from C++:
    #    custom_engine.exe --emit-roundtrip python/rt
    # 2) verify here:
    python test_roundtrip.py [prefix]   # default prefix = <this dir>/rt
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trainingdata_reader import (  # noqa: E402
    RECORD_SIZE, read_records, reconstruct_planes, ShuffleBuffer, downsample,
)


def main():
    prefix = sys.argv[1] if len(sys.argv) > 1 else \
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "rt")
    rec_file = prefix + "_records.gz"
    dense_file = prefix + "_dense.bin"

    print(f"RECORD_SIZE = {RECORD_SIZE} (expect 45940)")
    records = read_records(rec_file)
    dense = np.fromfile(dense_file, dtype=np.float32).reshape(-1, 226, 10, 10)
    assert len(records) == dense.shape[0], \
        f"case count mismatch: {len(records)} records vs {dense.shape[0]} dense"
    print(f"Loaded {len(records)} cases from {os.path.basename(rec_file)}")

    ok = True
    for i, rec in enumerate(records):
        recon = reconstruct_planes(rec)
        gt = dense[i]
        if not np.allclose(recon, gt, atol=1e-6):
            ok = False
            diff = np.abs(recon - gt)
            bad = np.argwhere(diff > 1e-6)
            print(f"[FAIL] case {i}: {len(bad)} mismatched cells (max diff {diff.max():.6g})")
            for (p, r, c) in bad[:6]:
                print(f"   plane {p} ({r},{c}): recon={recon[p, r, c]} gt={gt[p, r, c]}")
            continue

        psum = float(rec["probabilities"].sum())
        n_planes_set = int((recon != 0).any(axis=(1, 2)).sum())
        print(f"[OK] case {i}: planes match exactly  | side_to_move={rec['side_to_move']} "
              f"rule50={rec['rule50_count']} checks=({rec['checks_remaining_us']},{rec['checks_remaining_them']}) "
              f"castle_files=({rec['castling_us_ooo_file']},{rec['castling_us_oo_file']},"
              f"{rec['castling_them_ooo_file']},{rec['castling_them_oo_file']}) "
              f"non-empty planes={n_planes_set} | sum(pi)={psum:.4f} "
              f"result_q={rec['result_q']} orig_q={rec['orig_q']:.3f} kld={rec['policy_kld']:.3f} "
              f"visits={rec['visits']}")

        # Field-level checks (synthetic values written by C++ emit).
        assert abs(psum - 1.0) < 1e-5, f"sum(pi)={psum}"
        assert abs(rec["result_q"] - (-1.0)) < 1e-6
        assert abs(rec["orig_q"] - 0.123) < 1e-4
        assert abs(rec["policy_kld"] - 0.456) < 1e-4
        assert rec["visits"] == 777
        assert abs(rec["probabilities"][2005] - 0.75) < 1e-6
        assert abs(rec["probabilities"][100] - 0.25) < 1e-6

    # ShuffleBuffer + downsampling smoke test (Section 8.2.2 / 8.2.3).
    sb = ShuffleBuffer(3)
    items, out = list(range(10)), []
    for it in items:
        r = sb.insert_or_replace(it)
        if r is not None:
            out.append(r)
    while True:
        r = sb.extract()
        if r is None:
            break
        out.append(r)
    assert sorted(out) == items, f"shuffle lost/duplicated items: {sorted(out)}"
    kept = downsample(list(range(1000)), 0.5)
    print(f"[OK] ShuffleBuffer preserved all {len(out)} items; "
          f"downsample(0.5) kept {len(kept)}/1000")

    if ok:
        print("\n[PASS] T5 round-trip: Python reconstruction matches C++ "
              "UnpackInputPlanes exactly; record fields unpack correctly.")
    else:
        print("\n[FAIL] T5 round-trip mismatch.")
        sys.exit(1)


if __name__ == "__main__":
    main()
