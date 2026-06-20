"""T6 training: ResNet 10x128 + qMix loss + SWA + ONNX export (+ I/O verify).

Loss (8.2.5) = policy CE + value WDL CE + L2 (via AdamW weight_decay).
Value target (qMix, 8.2.1) is mixed in the dataset. SWA (8.2.4) averages the
last epochs' weights. Export matches the engine I/O contract exactly.

Usage:
    python train.py --data selfplay_data --epochs 20 --batch 32 --out model_gen1.onnx
"""

import argparse
import os
import sys

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torch.optim.swa_utils import AveragedModel, SWALR, update_bn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import FairyNet, ExportNet, NUM_PLANES, POLICY_SIZE  # noqa: E402
from dataset import FairyDataset  # noqa: E402


def policy_loss(logits, pi):
    # Masked cross-entropy (lc0 convention): pi < 0 marks ILLEGAL moves -> mask
    # them out of the softmax so the denominator only spans legal moves. Legal-
    # unvisited have pi=0 (target 0), legal-visited have the visit fraction.
    illegal = pi < 0
    masked_logits = logits.masked_fill(illegal, float("-inf"))
    logp = F.log_softmax(masked_logits, dim=1)
    logp = logp.masked_fill(illegal, 0.0)          # avoid 0 * -inf = NaN
    target = pi.clamp(min=0.0)
    return -(target * logp).sum(dim=1).mean()


def value_loss(logits, target_wdl):
    return -(target_wdl * F.log_softmax(logits, dim=1)).sum(dim=1).mean()


def export_onnx(net, path):
    net.eval()
    exp = ExportNet(net).eval()
    dummy = torch.randn(1, NUM_PLANES, 10, 10)
    # dynamo=False -> legacy TorchScript exporter: stable, no emoji console prints,
    # produces clean graphs that the engine's onnxruntime loads reliably.
    torch.onnx.export(
        exp, dummy, path,
        input_names=["input"], output_names=["policy", "value"],
        dynamic_axes={"input": {0: "batch"}, "policy": {0: "batch"}, "value": {0: "batch"}},
        opset_version=17,
        dynamo=False,
    )
    print(f"[export] wrote {path}")


def verify_onnx(path):
    import onnx
    import onnxruntime as ort
    m = onnx.load(path)
    onnx.checker.check_model(m)

    def io_info(vi):
        dims = [d.dim_param or d.dim_value for d in vi.type.tensor_type.shape.dim]
        return vi.name, dims

    ins = [io_info(i) for i in m.graph.input]
    outs = [io_info(o) for o in m.graph.output]
    print(f"[verify] inputs={ins}")
    print(f"[verify] outputs={outs}")
    assert ins[0][0] == "input" and list(ins[0][1]) == ["batch", 226, 10, 10], f"bad input {ins[0]}"
    out_names = {n for n, _ in outs}
    assert out_names == {"policy", "value"}, f"bad outputs {out_names}"
    for n, d in outs:
        if n == "policy":
            assert list(d) == ["batch", 10600], f"bad policy shape {d}"
        if n == "value":
            assert list(d) == ["batch", 3], f"bad value shape {d}"

    sess = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
    x = np.random.randn(2, 226, 10, 10).astype(np.float32)
    pol, val = sess.run(["policy", "value"], {"input": x})
    assert pol.shape == (2, 10600), pol.shape
    assert val.shape == (2, 3), val.shape
    vsum = val.sum(axis=1)
    assert np.allclose(vsum, 1.0, atol=1e-4), f"value (WDL) must sum to 1, got {vsum}"
    print(f"[verify] runtime OK: policy{pol.shape} value{val.shape} value_sum={vsum}")
    print("[verify] PASS: ONNX I/O contract matches engine (policy=logits, value=softmax WDL).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--q-ratio", type=float, default=0.2)
    ap.add_argument("--downsample", type=float, default=1.0)
    ap.add_argument("--channels", type=int, default=128)
    ap.add_argument("--blocks", type=int, default=10)
    ap.add_argument("--out", default="model_gen1.onnx")
    ap.add_argument("--init-from", default="", help="warm-start: load .pt weights of previous gen")
    ap.add_argument("--threads", type=int, default=0)
    ap.add_argument("--workers", type=int, default=0, help="DataLoader worker processes")
    ap.add_argument("--pin-memory", action="store_true", help="pin host memory (faster CPU->GPU copy)")
    ap.add_argument("--no-cache", action="store_true", help="stream records (lower RAM for big data)")
    ap.add_argument("--diff-focus", action="store_true", help="prefer 'surprising' positions (8.2.6)")
    ap.add_argument("--df-slope", type=float, default=1.0, help="diff_focus: keep-prob slope")
    ap.add_argument("--df-kld-w", type=float, default=0.5, help="diff_focus: policy_kld weight")
    ap.add_argument("--df-min", type=float, default=0.2, help="diff_focus: min keep prob")
    ap.add_argument("--weight-decay", type=float, default=1e-4, help="L2 regularization (8.2.5)")
    ap.add_argument("--value-weight", type=float, default=1.0, help="value-loss weight vs policy")
    ap.add_argument("--swa-start-frac", type=float, default=0.75, help="start SWA at this fraction of epochs")
    ap.add_argument("--swa-lr", type=float, default=0.0, help="SWA LR (0 => lr*0.5)")
    args = ap.parse_args()
    if args.threads > 0:
        torch.set_num_threads(args.threads)

    torch.manual_seed(0)
    ds = FairyDataset(args.data, q_ratio=args.q_ratio, downsample_keep=args.downsample,
                      cache=not args.no_cache, diff_focus=args.diff_focus,
                      df_slope=args.df_slope, df_kld_w=args.df_kld_w, df_min=args.df_min)
    dl = DataLoader(ds, batch_size=args.batch, shuffle=True, drop_last=False,
                    num_workers=args.workers, pin_memory=args.pin_memory,
                    persistent_workers=(args.workers > 0))

    net = FairyNet(channels=args.channels, blocks=args.blocks)
    if args.init_from:
        net.load_state_dict(torch.load(args.init_from, map_location="cpu"))
        print(f"[warm-start] loaded weights from {args.init_from}")
    opt = torch.optim.AdamW(net.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    swa_net = AveragedModel(net)
    swa_start = max(1, int(args.epochs * args.swa_start_frac))
    swa_sched = SWALR(opt, swa_lr=(args.swa_lr if args.swa_lr > 0 else args.lr * 0.5))

    print(f"[train] params={sum(p.numel() for p in net.parameters())/1e6:.2f}M "
          f"swa_start_epoch={swa_start}")
    for epoch in range(1, args.epochs + 1):
        net.train()
        tp = tv = n = 0.0
        for x, pi, val in dl:
            opt.zero_grad()
            p_logits, v_logits = net(x)
            lp = policy_loss(p_logits, pi)
            lv = value_loss(v_logits, val)
            (lp + args.value_weight * lv).backward()
            opt.step()
            bs = x.size(0)
            tp += lp.item() * bs; tv += lv.item() * bs; n += bs
        if epoch >= swa_start:
            swa_net.update_parameters(net)
            swa_sched.step()
        print(f"  epoch {epoch:3d}: policy_loss={tp/n:.4f}  value_loss={tv/n:.4f}")

    # Recompute BN running stats for the SWA-averaged weights, then export.
    print("[swa] updating BatchNorm statistics on the averaged model...")
    update_bn(dl, swa_net)

    ckpt = os.path.splitext(args.out)[0] + ".pt"
    torch.save(swa_net.module.state_dict(), ckpt)
    print(f"[ckpt] saved {ckpt}")

    export_onnx(swa_net.module, args.out)
    verify_onnx(args.out)


if __name__ == "__main__":
    main()
