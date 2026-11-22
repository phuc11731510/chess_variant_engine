"""Generate the gen-0 bootstrap network (random weights) from the CANONICAL
architecture in model.py — the single source of truth for the whole AlphaZero
loop (warm-start requires every generation to share this architecture).

This SUPERSEDES create_zero_elo_net.py (which used a scale-only SE that does not
match lc0 / model.py). Writes both:
  <out>.onnx : engine-loadable seed (value softmax in-graph)
  <out>.pt   : raw FairyNet state_dict for warm-starting generation 1
With --out model_gen0.pt only the .pt is written (no onnx packages needed).

Usage:
    python make_seed.py --out model_gen0.onnx
    python make_seed.py --out model_gen0.pt
"""

import argparse
import os
import sys

import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import FairyNet  # noqa: E402
from train import export_onnx, verify_onnx  # noqa: E402  (train.py imports onnx lazily, so a .pt run needs no onnx package)
from run_seed import resolve_seed  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="model_gen0.onnx")
    ap.add_argument("--d-model", type=int, default=192, help="must match train.py --d-model for warm-start")
    ap.add_argument("--layers", type=int, default=10, help="must match train.py --layers for warm-start")
    ap.add_argument("--heads", type=int, default=6, help="must match train.py --heads for warm-start")
    ap.add_argument("--seed", type=int, default=None,
                    help="seed of the starting weights (default: random for every run, printed)")
    args = ap.parse_args()
    args.seed = resolve_seed(args.seed, "make_seed")

    # Create the output directory if it doesn't exist yet (e.g. a fresh checkout
    # has no models/ dir), so torch.save / ONNX export don't fail.
    out_dir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)

    torch.manual_seed(args.seed)
    net = FairyNet(d_model=args.d_model, layers=args.layers, heads=args.heads)
    net.eval()

    params = sum(p.numel() for p in net.parameters()) / 1e6
    ckpt = os.path.splitext(args.out)[0] + ".pt"
    torch.save(net.state_dict(), ckpt)
    print(f"[seed] {params:.2f}M params -> saved {ckpt}")

    if args.out.endswith(".pt"):     # --out gen0.pt: the checkpoint alone (the CUDA runner reads .fzw made from it)
        print(f"[seed] gen-0 bootstrap ready: {ckpt} (no .onnx: python/lay_mang.py fzw makes the .fzw)")
        return
    export_onnx(net, args.out)
    verify_onnx(args.out, net)
    print(f"[seed] gen-0 bootstrap ready: {args.out}")


if __name__ == "__main__":
    main()
