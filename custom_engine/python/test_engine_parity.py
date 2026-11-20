"""End-to-end parity: the C++ engine and PyTorch must see the same network.

For every position of the round-trip set, compares what the ENGINE computes
(C++ encoder -> UnpackInputPlanes -> ONNX Runtime -> softmax over the legal
moves via MoveToNNIndex, through the self-play backend stack) with what the
TRAINER computes (the stored record -> trainingdata_reader.reconstruct_planes ->
FairyNet from the .pt -> softmax over the same policy indices). One test covers
every link of the C++ <-> Python contract at once: record planes, plane
layout, policy index order, value order (W, D, L), the value softmax added at
export, the export itself (.pt vs .onnx), and the engine's softmax.

Usage:
    custom_engine --emit-roundtrip <prefix> --weights net.onnx
    python test_engine_parity.py <prefix> net.pt [--onnx net.onnx] [--d-model 192 --layers 10 --heads 6]
"""

import argparse
import os
import struct
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import FairyNet  # noqa: E402
from trainingdata_reader import read_records, reconstruct_planes  # noqa: E402


def read_engine_eval(path, n_cases):
    """<prefix>_eval.bin: per case float q, float d, float m (moves left), uint32 n, n x (uint16 idx, float p)."""
    out = []
    with open(path, "rb") as f:
        data = f.read()
    off = 0
    for _ in range(n_cases):
        q, d, m, n = struct.unpack_from("<fffI", data, off)
        off += 16
        idx = np.empty(n, dtype=np.int64)
        p = np.empty(n, dtype=np.float64)
        for i in range(n):
            idx[i], p[i] = struct.unpack_from("<Hf", data, off)
            off += 6
        out.append((q, d, m, idx, p))
    if off != len(data):
        raise ValueError(f"{path}: {len(data) - off} trailing bytes (case count mismatch?)")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prefix")
    ap.add_argument("pt")
    ap.add_argument("--onnx", default="", help="also run this .onnx with onnxruntime (export check)")
    ap.add_argument("--d-model", type=int, default=192)
    ap.add_argument("--layers", type=int, default=10)
    ap.add_argument("--heads", type=int, default=6)
    ap.add_argument("--tol", type=float, default=1e-4)
    args = ap.parse_args()

    records = read_records(args.prefix + "_records.gz")
    engine = read_engine_eval(args.prefix + "_eval.bin", len(records))
    print(f"{len(records)} positions from {args.prefix}")

    net = FairyNet(d_model=args.d_model, layers=args.layers, heads=args.heads)
    net.load_state_dict(torch.load(args.pt, map_location="cpu"))
    net.eval()
    x = torch.from_numpy(np.stack([reconstruct_planes(r) for r in records]))
    with torch.no_grad():
        logits, v, mlh = net(x)
        wdl = torch.softmax(v, dim=1).double().numpy()
        mlh = mlh.double().clamp(min=0.0).numpy()[:, 0]      # the engine uses max(output, 0)
        logits = logits.double().numpy()

    sess = None
    if args.onnx:
        import onnxruntime as ort
        sess = ort.InferenceSession(args.onnx, providers=["CPUExecutionProvider"])
        o_pol, o_val, o_mlh = sess.run(["policy", "value", "mlh"], {"input": x.numpy()})

    worst = dict(q=0.0, d=0.0, m=0.0, p=0.0, onnx_p=0.0, onnx_v=0.0)
    bad = 0
    for k, (q, d, m, idx, p) in enumerate(engine):
        if len(set(idx.tolist())) != len(idx) or (idx >= 11500).any():
            print(f"[FAIL] case {k}: policy indices not unique / out of range")
            bad += 1
            continue
        tq = wdl[k, 0] - wdl[k, 2]
        l = logits[k, idx]
        tp = np.exp(l - l.max())
        tp /= tp.sum()
        dq, dd, dp = abs(q - tq), abs(d - wdl[k, 1]), float(np.abs(p - tp).max()) if len(p) else 0.0
        dm = abs(m - mlh[k]) / max(1.0, abs(mlh[k]))     # relative: moves left is ~50, not in [0, 1]
        worst["q"] = max(worst["q"], dq)
        worst["d"] = max(worst["d"], dd)
        worst["m"] = max(worst["m"], dm)
        worst["p"] = max(worst["p"], dp)
        if max(dq, dd, dm, dp) > args.tol:
            bad += 1
            if bad <= 8:
                print(f"[FAIL] case {k}: engine q={q:.6f} d={d:.6f} vs torch q={tq:.6f} d={wdl[k, 1]:.6f}; "
                      f"max prior diff {dp:.3g} over {len(p)} moves")
        if sess is not None:
            worst["onnx_p"] = max(worst["onnx_p"], float(np.abs(o_pol[k] - logits[k]).max()))
            worst["onnx_v"] = max(worst["onnx_v"], float(np.abs(o_val[k] - wdl[k]).max()))

    print(f"engine vs torch: max |q| {worst['q']:.2e}  max |d| {worst['d']:.2e}  max |prior| {worst['p']:.2e}  "
          f"max |moves left| (relative) {worst['m']:.2e}")
    if sess is not None:
        print(f"onnx vs torch  : max |policy logit| {worst['onnx_p']:.2e}  max |WDL| {worst['onnx_v']:.2e}")
        if worst["onnx_p"] > 1e-3 or worst["onnx_v"] > args.tol:
            print("[FAIL] the .onnx does not compute what the .pt does")
            bad += 1
    if bad:
        print(f"[FAIL] {bad} position(s) differ between the engine and PyTorch")
        sys.exit(1)
    print("[PASS] engine (C++ encoder + ONNX + softmax) == PyTorch (record planes + FairyNet) "
          "on every position")


if __name__ == "__main__":
    main()
