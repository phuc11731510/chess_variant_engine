"""Runs the real make_seed.py / train.py end to end on a tiny net and synthetic
records, and checks what they write (not just that they finish):

  1. make_seed.py: the .onnx computes what the .pt does (verify_onnx parity).
  2. --max-steps stopping before the first SWA epoch exports TRAINED weights.
     (It used to export the averaged model, which at that point was still the
     copy of the starting weights: an untrained net with a trained file name.)
  3. --epochs 2: SWA averages epoch 2 only ("from 75% of the training"), and
     --swa-start-frac 0 averages both epochs.
  4. --data with a part that matches no file is an error (it used to be skipped).
  5. The exported .pt and .onnx agree (verify_onnx parity inside train.py).

Run:  python test_train_pipeline.py        (~1 minute on a CPU)
"""

import gzip
import os
import subprocess
import sys
import tempfile

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import trainingdata_reader as R  # noqa: E402

PASS, FAIL = 0, 0


def check(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [ok] {msg}")
    else:
        FAIL += 1
        print(f"  [FAIL] {msg}")


def write_games(path, n_records, seed):
    """Synthetic but well-formed version-4 records (random planes, a masked policy
    over 40 legal moves, alternating side to move, one decisive result)."""
    rng = np.random.default_rng(seed)
    with gzip.open(path, "wb") as f:
        for i in range(n_records):
            pi = np.full(R.POLICY_SIZE, -1.0, dtype=np.float32)
            legal = rng.choice(R.POLICY_SIZE, size=40, replace=False)
            v = rng.random(40).astype(np.float32)
            pi[legal] = v / v.sum()
            planes = (rng.random((R.HISTORY_PLANES, 2)) < 0.1) * rng.integers(
                1, 2**62, size=(R.HISTORY_PLANES, 2))
            stm = i % 2
            z = 1.0 if stm == 0 else -1.0
            fields = ([4, 1] + pi.tolist() + [int(x) for x in planes.reshape(-1)] +
                      [i % 100, 1, 8, 1, 8, 0, 0, 8, 8, stm,
                       z, 0.0, 0.1, 0.2, 0.3 * z, 0.1, 0.3 * z, 0.1, 0.2 * z, 0.2, 0.5,
                       800, int(legal[0]), int(legal[0])])
            f.write(R._STRUCT.pack(*fields))


def run(args, cwd):
    p = subprocess.run([sys.executable] + args, cwd=cwd, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def same_weights(a, b):
    """Learned parameters only: BatchNorm running statistics are recomputed by
    SWA's update_bn, so they differ even when not a single weight was trained."""
    sa, sb = torch.load(a, map_location="cpu"), torch.load(b, map_location="cpu")
    keys = [k for k in sa if "running_" not in k and "num_batches_tracked" not in k]
    return sa.keys() == sb.keys() and all(torch.equal(sa[k], sb[k]) for k in keys)


def main():
    net_args = ["--channels", "8", "--blocks", "1", "--se-ratio", "8"]
    with tempfile.TemporaryDirectory() as tmp:
        data = os.path.join(tmp, "game.gz")
        write_games(data, 192, seed=1)
        seed_onnx = os.path.join(tmp, "seed.onnx")
        seed_pt = os.path.join(tmp, "seed.pt")

        print("\n[1] make_seed.py")
        rc, out = run([os.path.join(HERE, "make_seed.py"), "--out", seed_onnx, "--seed", "3"] + net_args, tmp)
        check(rc == 0 and os.path.exists(seed_pt), "make_seed.py wrote the seed")
        check("onnx vs torch" in out, "make_seed.py compared the .onnx with the .pt")

        base = [os.path.join(HERE, "train.py"), "--data", data, "--batch", "32", "--init-from", seed_pt,
                "--workers", "0", "--device", "cpu"] + net_args

        print("\n[2] --max-steps before the first SWA epoch")
        out_a = os.path.join(tmp, "a.onnx")
        rc, out = run(base + ["--epochs", "20", "--max-steps", "3", "--out", out_a], tmp)
        check(rc == 0, "train.py --max-steps 3 finished")
        check("training stopped before any SWA epoch ended" in out, "said that no SWA epoch was averaged")
        check(os.path.exists(out_a.replace(".onnx", ".pt")) and
              not same_weights(out_a.replace(".onnx", ".pt"), seed_pt),
              "the exported weights are the trained ones, not the starting weights")
        check("onnx vs torch" in out, "train.py compared the exported .onnx with the .pt")

        print("\n[3] SWA epochs")
        out_b = os.path.join(tmp, "b.onnx")
        rc, out = run(base + ["--epochs", "2", "--out", out_b], tmp)
        check(rc == 0 and "averages the end of epochs 2..2" in out and "averaged 1 epoch(s)" in out,
              "--epochs 2: SWA averages epoch 2 only")
        out_c = os.path.join(tmp, "c.onnx")
        rc, out = run(base + ["--epochs", "2", "--swa-start-frac", "0", "--out", out_c], tmp)
        check(rc == 0 and "averages the end of epochs 1..2" in out and "averaged 2 epoch(s)" in out,
              "--swa-start-frac 0: SWA averages both epochs")

        print("\n[4] --data with a part that matches nothing")
        rc, out = run(base + ["--epochs", "1", "--data", data + "," + os.path.join(tmp, "gen9.zip"),
                              "--out", os.path.join(tmp, "d.onnx")], tmp)
        check(rc != 0 and "no training files matched" in out and "gen9.zip" in out,
              "a missing generation stops the training")

    print("\n" + "=" * 60)
    print(f"RESULT: {PASS} passed, {FAIL} failed")
    print("=" * 60)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
