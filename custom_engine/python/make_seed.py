"""Generate the gen-0 bootstrap network (random weights) from the CANONICAL
architecture in model.py — the single source of truth for the whole AlphaZero
loop (warm-start requires every generation to share this architecture).

This SUPERSEDES create_zero_elo_net.py (which used a scale-only SE that does not
match lc0 / model.py). Writes both:
  <out>.onnx : engine-loadable seed (value softmax in-graph)
  <out>.pt   : raw FairyNet state_dict for warm-starting generation 1

Usage:
    python make_seed.py --out model_gen0.onnx
"""

import argparse
import os
import sys

import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import FairyNet  # noqa: E402
from train import export_onnx, verify_onnx  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="model_gen0.onnx")
    ap.add_argument("--channels", type=int, default=128)
    ap.add_argument("--blocks", type=int, default=10)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    net = FairyNet(channels=args.channels, blocks=args.blocks)
    net.eval()

    params = sum(p.numel() for p in net.parameters()) / 1e6
    ckpt = os.path.splitext(args.out)[0] + ".pt"
    torch.save(net.state_dict(), ckpt)
    print(f"[seed] {params:.2f}M params -> saved {ckpt}")

    export_onnx(net, args.out)
    verify_onnx(args.out)
    print(f"[seed] gen-0 bootstrap ready: {args.out}")


if __name__ == "__main__":
    main()
