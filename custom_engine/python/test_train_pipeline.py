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
  6. Validation split (--val-frac): the newest whole games by modification
     time (also games inside a .zip), one policy and one value number
     per evaluation that do not depend on the batch size, printed before
     training, after each epoch and for the exported model.
  7. Run seeds: without --seed every run draws its own ten-digit seed and
     prints it; the same --seed repeats a training run weight for weight.

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
    """Synthetic but well-formed current-version records (random planes, a masked policy
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
            fields = ([7, 1] + pi.tolist() + [int(x) for x in planes.reshape(-1)] +
                      [i % 100, 0, 0, 7, 7, stm,
                       z, 0.0, 0.1, 0.2, 0.3 * z, 0.1, 0.3 * z, 0.1, 0.2 * z, 0.2, 0.5,
                       800, int(legal[0]), int(legal[0]), 1, 0])
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


def test_validation(tmp, base, seed_pt, net_args):
    import re
    import dataset as D
    import train as T
    from torch.utils.data import DataLoader
    from model import FairyNet

    # 3 generations x 20 games x 8 positions (a rolling window of 60 games).
    gens = []
    for g in range(3):
        d = os.path.join(tmp, "games", f"gen{g}")
        os.makedirs(d)
        for k in range(20):
            f = os.path.join(d, f"game_{k}.gz")
            write_games(f, 8, seed=100 * g + k)
            t = 1.7e9 + 1000 * g + 10 * (19 - k)   # gen2 newest; in a gen, game_0 newest
            os.utime(f, (t, t))
        gens.append(d)
    data = ",".join(gens)
    games = D.list_games(data)
    check(len(games) == 60 and all(m is None for _, m in games), "60 games, one per .gz file")

    mt = D.game_mtimes(games)
    train_g, val_g = D.split_games(games, 0.04, mt)
    names = lambda gs: sorted(os.path.relpath(p, os.path.join(tmp, "games")).replace(os.sep, "/")
                              for p, _ in gs)
    check(len(val_g) == 2 and len(train_g) == 58, f"4% of 60 games = 2 held out (got {len(val_g)})")
    check(not set(train_g) & set(val_g) and sorted(train_g + val_g) == sorted(games),
          "every game on exactly one side")
    check(names(val_g) == ["gen2/game_0.gz", "gen2/game_1.gz"],
          f"the 2 newest by modification time, not by name ({names(val_g)})")
    check(D.split_games(games, 0.0, mt)[1] == [] and D.split_games(games[:10], 0.04, mt[:10])[1] == [],
          "--val-frac 0, or too few games: nothing held out")

    # Games inside a .zip bundle are split one by one, like files.
    bundle = os.path.join(tmp, "window.zip")
    rc, _ = run([os.path.join(HERE, "archive.py"), "pack", os.path.join(tmp, "games"), "--out", bundle], tmp)
    zgames = D.list_games(bundle)
    ztrain, zval = D.split_games(zgames, 0.04, D.game_mtimes(zgames))
    check(sorted(m.split("/", 1)[1] for _, m in zval) == ["gen2/game_0.gz", "gen2/game_1.gz"],
          f"inside a .zip: the newest by the time the .zip keeps ({sorted(m for _, m in zval)})")
    dsv = D.FairyDataset(bundle, games=zval, label="validation")
    dst = D.FairyDataset(bundle, games=ztrain, label="train")
    check(rc == 0 and len(zgames) == 60 and len(dsv) == 2 * 8 and len(dst) == 58 * 8,
          f"a .zip is split by the games inside it ({len(zgames)} games, {len(dsv)} + {len(dst)} positions)")

    # One number per set: the mean over positions, whatever the batch size.
    torch.manual_seed(0)
    net = FairyNet(d_model=16, layers=1, heads=2)
    a = T.evaluate(net, DataLoader(dst, batch_size=7), "cpu")
    b = T.evaluate(net, DataLoader(dst, batch_size=len(dst)), "cpu")
    x, pi, val = next(iter(DataLoader(dst, batch_size=len(dst))))
    net.eval()
    with torch.no_grad():
        pl, vl, ml = net(x)
        per_pos_p = -(pi.clamp(min=0) * torch.log_softmax(pl.masked_fill(pi < 0, float("-inf")), 1)
                      .masked_fill(pi < 0, 0.0)).sum(1)
        per_pos_v = -(val[:, :3] * torch.log_softmax(vl, 1)).sum(1)
        mlh_all = T.mlh_loss(ml.squeeze(1), val[:, 3]).item()
    check(abs(a[0] - b[0]) < 1e-5 and abs(a[1] - b[1]) < 1e-5 and abs(a[2] - b[2]) < 1e-4 and
          abs(a[0] - per_pos_p.mean().item()) < 1e-5 and abs(a[1] - per_pos_v.mean().item()) < 1e-5 and
          abs(a[2] - mlh_all) < 1e-4,
          f"evaluate() = mean of the per-position losses, batch 7 or {len(dst)} "
          f"(policy {a[0]:.5f} / {b[0]:.5f}, value {a[1]:.5f} / {b[1]:.5f}, mlh {a[2]:.4f} / {b[2]:.4f})")

    # train.py end to end: 4 reports (start, epoch 1, epoch 2, exported model).
    args = list(base)
    args[args.index("--data") + 1] = data
    rc, out = run(args + ["--epochs", "2", "--out", os.path.join(tmp, "v.onnx")], tmp)
    lines = [l for l in out.splitlines() if "[val] " in l and "validation: policy=" in l]
    whats = [re.search(r"\[val\] (.+?)\s+train:", l).group(1).strip() for l in lines]
    nums_ok = all(len(re.findall(r"=\d+\.\d{4}", l)) == 6 for l in lines)   # policy, value, mlh: train and validation
    check(rc == 0 and "[val] 2 of 60 games held out (16 positions), compared with 16 training positions" in out,
          "train.py holds out 2 of the 60 games")
    check(whats == ["start weights", "epoch 1", "epoch 2", "exported model"] and nums_ok,
          f"--epochs 2 prints 4 validation lines with 6 numbers each (got {whats})")
    rc, out = run(args + ["--epochs", "1", "--val-frac", "0", "--out", os.path.join(tmp, "w.onnx")], tmp)
    check(rc == 0 and "[val]" not in out, "--val-frac 0: no validation")


def test_seeds(tmp, base, net_args):
    import re
    def seed_of(out, tag):
        m = re.search(rf"\[{tag}\] seed (\d+) \(random for this run; --seed \1 repeats it\)", out)
        return int(m.group(1)) if m else None

    rc, out = run([os.path.join(HERE, "make_seed.py"), "--out", os.path.join(tmp, "s1.onnx")] + net_args, tmp)
    s = seed_of(out, "make_seed")
    check(rc == 0 and s is not None and 10**9 <= s <= 10**10 - 1,
          f"make_seed.py draws and prints a ten-digit seed ({s})")

    data = os.path.join(tmp, "games")                      # the 60 games of [6]
    args = list(base)
    args[args.index("--data") + 1] = ",".join(os.path.join(data, g) for g in ("gen0", "gen1", "gen2"))
    seeds, pts = [], []
    for k in range(2):
        pt = os.path.join(tmp, f"r{k}.onnx")
        rc, out = run(args + ["--epochs", "1", "--out", pt], tmp)
        seeds.append(seed_of(out, "train"))
        pts.append(pt.replace(".onnx", ".pt"))
    check(all(x is not None and 10**9 <= x <= 10**10 - 1 for x in seeds) and seeds[0] != seeds[1],
          f"train.py: each run draws its own ten-digit seed ({seeds})")
    check(not same_weights(pts[0], pts[1]), "two random-seed runs train differently (other shuffles)")

    outs = []
    for k in range(2):
        pt = os.path.join(tmp, f"f{k}.onnx")
        rc, out = run(args + ["--epochs", "1", "--seed", "1234567890", "--out", pt], tmp)
        outs.append((rc, out, pt.replace(".onnx", ".pt")))
    held = [re.search(r"\[val\] (\d+) of", o).group(1) for _, o, _ in outs]
    check(all(rc == 0 and "[train] seed 1234567890 (--seed)" in o for rc, o, _ in outs) and
              same_weights(outs[0][2], outs[1][2]) and held[0] == held[1],
          "--seed 1234567890 twice: the same run, weight for weight")
    rc, out = run(args + ["--epochs", "1", "--seed", "-5", "--out", os.path.join(tmp, "n.onnx")], tmp)
    check(rc != 0 and "--seed must be >= 0" in out, "--seed -5 is refused")


def test_tail_swa(tmp, base):
    """Tail SWA averages (equal weights) the weights at the LAST optimizer step and every K steps back from it,
    at most N snapshots, none before step 1. The data is 192 records at --batch 32: 6 optimizer steps per epoch."""
    import train as T
    # The steps themselves.
    check(T.swa_tail_steps(586, 10, 20) == list(range(406, 587, 20)), "586 steps: 406, 426, ..., 586 (10 snapshots)")
    check(T.swa_tail_steps(100, 10, 20) == [20, 40, 60, 80, 100], "100 steps: only 5 fit, never step 0")
    check(T.swa_tail_steps(181, 10, 20) == list(range(1, 182, 20)), "181 steps: 1, 21, ..., 181 (the 10th is step 1)")
    check(T.swa_tail_steps(180, 10, 20) == list(range(20, 181, 20)), "180 steps: step 0 is left out -> 9 snapshots")
    check(T.swa_tail_steps(7, 10, 20) == [7], "7 steps: just the last one")
    check(T.swa_tail_steps(0, 10, 20) == [] and T.swa_tail_steps(50, 0, 20) == [], "no steps or no snapshots: none")
    check(T.swa_tail_steps(50, 3, 20) == [10, 30, 50], "the count caps the number of snapshots")

    # The training loop takes exactly those snapshots.
    def tail(extra, name):
        return run(base + extra + ["--out", os.path.join(tmp, name)], tmp)

    rc, out = tail(["--epochs", "5", "--swa-tail", "10", "--swa-tail-every", "2"], "t1.onnx")      # 30 steps
    check(rc == 0 and "tail: 10 snapshot(s) at steps 12..30 every 2" in out and "averaged 10 snapshot(s)" in out
          and "WARNING: tail SWA" not in out, "30 steps, 10 every 2: steps 12..30, 10 snapshots averaged")
    rc, out = tail(["--epochs", "2", "--swa-tail", "10", "--swa-tail-every", "2"], "t2.onnx")      # 12 steps
    check(rc == 0 and "tail: 6 snapshot(s) at steps 2..12" in out and "averaged 6 snapshot(s)" in out,
          "12 steps: not enough for 10 -> 6 snapshots, no failure")
    rc, out = tail(["--epochs", "5", "--max-steps", "5", "--swa-tail", "3", "--swa-tail-every", "2"], "t3.onnx")
    check(rc == 0 and "tail: 3 snapshot(s) at steps 1..5" in out and "averaged 3 snapshot(s)" in out,
          "--max-steps 5: the last step is 5, snapshots at 5, 3, 1")
    rc, out = tail(["--epochs", "2", "--accum-steps", "4", "--swa-tail", "10", "--swa-tail-every", "1"], "t4.onnx")
    check(rc == 0 and "tail: 3 snapshot(s) at steps 1..3" in out and "averaged 3 snapshot(s)" in out
          and "WARNING: tail SWA" not in out, "--accum-steps 4: 12 micro-batches are 3 optimizer steps")

    # The weights. Same seed, same data order: the three runs follow one trajectory.
    def weights(extra, name):
        path = os.path.join(tmp, name)
        rc, _ = run(base + ["--seed", "5"] + extra + ["--out", path], tmp)
        return rc, torch.load(path.replace(".onnx", ".pt"), map_location="cpu")

    rc_a, w_last = weights(["--epochs", "20", "--max-steps", "6"], "w6.onnx")   # the weights after step 6
    rc_b, w_prev = weights(["--epochs", "20", "--max-steps", "5"], "w5.onnx")   # ... after step 5
    rc_c, w_one = weights(["--epochs", "1", "--swa-tail", "1"], "s1.onnx")      # tail SWA, one snapshot
    rc_d, w_two = weights(["--epochs", "1", "--swa-tail", "2", "--swa-tail-every", "1"], "s2.onnx")
    check(rc_a == rc_b == rc_c == rc_d == 0, "the four weight runs finished")
    floats = [k for k, v in w_last.items() if v.is_floating_point() and "running_" not in k]
    check(all(torch.equal(w_one[k], w_last[k]) for k in floats),
          "--swa-tail 1 exports exactly the weights of the last step (the snapshot step is right)")
    check(all(torch.allclose(w_two[k], (w_prev[k] + w_last[k]) / 2, atol=1e-6) for k in floats)
          and not all(torch.equal(w_two[k], w_last[k]) for k in floats),
          "--swa-tail 2 --swa-tail-every 1 exports the plain mean of the weights after steps 5 and 6")

    rc, out = tail(["--swa-steps", "25", "--swa-tail", "10"], "t5.onnx")
    check(rc != 0 and "two different SWA schemes" in out, "--swa-steps together with --swa-tail is refused")
    rc, out = tail(["--swa-tail", "10", "--swa-tail-every", "0"], "t6.onnx")
    check(rc != 0 and "--swa-tail-every >= 1" in out, "--swa-tail-every 0 is refused")


def main():
    net_args = ["--d-model", "16", "--layers", "1", "--heads", "2"]
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
        check("training stopped before any SWA snapshot was taken" in out, "said that no SWA snapshot was averaged")
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

        print("\n[3b] tail SWA (--swa-tail N --swa-tail-every K)")
        test_tail_swa(tmp, base)

        print("\n[3c] --out *.pt: the checkpoint alone (CUDA runner: no onnx export, no onnx package needed)")
        out_p = os.path.join(tmp, "p.pt")
        rc, out = run(base + ["--epochs", "1", "--max-steps", "3", "--out", out_p], tmp)
        check(rc == 0 and os.path.exists(out_p) and not os.path.exists(os.path.join(tmp, "p.onnx")) and "onnx vs torch" not in out,
              "train.py --out p.pt wrote p.pt and no .onnx")
        check(not same_weights(out_p, seed_pt), "that checkpoint holds the trained weights")
        out_s = os.path.join(tmp, "q.pt")
        rc, out = run([os.path.join(HERE, "make_seed.py"), "--out", out_s, "--seed", "4"] + net_args, tmp)
        check(rc == 0 and os.path.exists(out_s) and not os.path.exists(os.path.join(tmp, "q.onnx")),
              "make_seed.py --out q.pt wrote q.pt and no .onnx")

        print("\n[4] --data with a part that matches nothing")
        rc, out = run(base + ["--epochs", "1", "--data", data + "," + os.path.join(tmp, "gen9.zip"),
                              "--out", os.path.join(tmp, "d.onnx")], tmp)
        check(rc != 0 and "no training files matched" in out and "gen9.zip" in out,
              "a missing generation stops the training")
        check("too few for --val-frac" in run(base + ["--epochs", "1", "--out", os.path.join(tmp, "e.onnx")],
                                              tmp)[1],
              "one game: no validation set, and it says so")

        print("\n[6] validation split")
        test_validation(tmp, base, seed_pt, net_args)

        print("\n[7] run seeds")
        test_seeds(tmp, base, net_args)

    print("\n" + "=" * 60)
    print(f"RESULT: {PASS} passed, {FAIL} failed")
    print("=" * 60)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
