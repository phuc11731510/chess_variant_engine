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
    ap.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"],
                    help="training device (auto = cuda if available, else cpu)")
    ap.add_argument("--amp", action="store_true",
                    help="mixed-precision FP16 training (Colab GPU, 5.3); ignored on CPU")
    ap.add_argument("--sparse-cache", dest="sparse_cache", action="store_true", default=True,
                    help="cache policy targets sparsely to avoid Colab OOM (8.2.2); default ON")
    ap.add_argument("--dense-cache", dest="sparse_cache", action="store_false",
                    help="cache dense tensors instead (more RAM; the old behavior)")
    # T8.3 — extra hyperparameters (lczero-training parity).
    ap.add_argument("--optimizer", default="adamw", choices=["adamw", "sgd", "nadam"],
                    help="optimizer (lc0 canonical = sgd+momentum)")
    ap.add_argument("--momentum", type=float, default=0.9, help="momentum for --optimizer sgd")
    ap.add_argument("--policy-weight", type=float, default=1.0, help="policy-loss weight")
    ap.add_argument("--grad-clip", type=float, default=0.0, help="clip grad-norm (0 = off)")
    ap.add_argument("--seed", type=int, default=0, help="RNG seed (reproducibility)")
    ap.add_argument("--warmup-steps", type=int, default=0, help="linear LR warmup over N optimizer steps")
    ap.add_argument("--lr-values", default="", help="step LR schedule values, comma-separated (overrides --lr)")
    ap.add_argument("--lr-boundaries", default="", help="step LR schedule boundaries, comma-separated")
    # #5 — more lczero-training-style knobs.
    ap.add_argument("--se-ratio", type=int, default=8, help="SE block squeeze ratio (fresh train only)")
    ap.add_argument("--dropout", type=float, default=0.0, help="dropout in value head (warm-start safe)")
    ap.add_argument("--accum-steps", type=int, default=1, help="gradient accumulation steps (big effective batch)")
    ap.add_argument("--max-steps", type=int, default=0, help="stop after N optimizer steps (0 = use --epochs)")
    ap.add_argument("--max-records", type=int, default=0, help="cap #records loaded (0 = all)")
    ap.add_argument("--report-every", type=int, default=0, help="print running loss every N steps (0 = per-epoch)")
    ap.add_argument("--save-every", type=int, default=0, help="export an ONNX checkpoint every N steps (0 = only final)")
    args = ap.parse_args()
    if args.threads > 0:
        torch.set_num_threads(args.threads)

    device = ("cuda" if torch.cuda.is_available() else "cpu") if args.device == "auto" else args.device
    if device == "cuda" and not torch.cuda.is_available():
        print("[train] WARNING: --device cuda but no CUDA available; falling back to cpu")
        device = "cpu"
    use_amp = args.amp and device == "cuda"
    print(f"[train] device={device}  amp={use_amp}  sparse_cache={args.sparse_cache}")

    torch.manual_seed(args.seed)
    ds = FairyDataset(args.data, q_ratio=args.q_ratio, downsample_keep=args.downsample,
                      cache=not args.no_cache, diff_focus=args.diff_focus,
                      df_slope=args.df_slope, df_kld_w=args.df_kld_w, df_min=args.df_min,
                      sparse=args.sparse_cache, max_records=args.max_records)
    dl = DataLoader(ds, batch_size=args.batch, shuffle=True, drop_last=False,
                    num_workers=args.workers, pin_memory=args.pin_memory,
                    persistent_workers=(args.workers > 0))

    net = FairyNet(channels=args.channels, blocks=args.blocks,
                   se_ratio=args.se_ratio, dropout=args.dropout)
    if args.init_from:
        net.load_state_dict(torch.load(args.init_from, map_location="cpu"))
        print(f"[warm-start] loaded weights from {args.init_from}")
    net.to(device)
    if args.optimizer == "sgd":
        opt = torch.optim.SGD(net.parameters(), lr=args.lr, momentum=args.momentum,
                              weight_decay=args.weight_decay, nesterov=args.momentum > 0)
    elif args.optimizer == "nadam":
        opt = torch.optim.NAdam(net.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    else:
        opt = torch.optim.AdamW(net.parameters(), lr=args.lr, weight_decay=args.weight_decay)

    # Optional step-based LR schedule (lc0-style: linear warmup -> piecewise constant).
    lr_vals = [float(v) for v in args.lr_values.split(",") if v.strip()]
    lr_bnds = [int(b) for b in args.lr_boundaries.split(",") if b.strip()]
    def lr_for_step(step):
        if args.warmup_steps > 0 and step < args.warmup_steps:
            return args.lr * (step + 1) / args.warmup_steps
        if not lr_vals:
            return args.lr
        k = sum(1 for b in lr_bnds if step >= b)           # piecewise-constant index
        return lr_vals[min(k, len(lr_vals) - 1)]
    use_lr_sched = bool(lr_vals) or args.warmup_steps > 0

    # GradScaler keeps FP16 gradients from underflowing; a no-op when use_amp=False.
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
    print(f"[train] optimizer={args.optimizer} grad_clip={args.grad_clip} "
          f"lr_sched={'on' if use_lr_sched else f'const {args.lr}'} seed={args.seed}")
    swa_net = AveragedModel(net)
    swa_start = max(1, int(args.epochs * args.swa_start_frac))
    swa_sched = SWALR(opt, swa_lr=(args.swa_lr if args.swa_lr > 0 else args.lr * 0.5))

    print(f"[train] params={sum(p.numel() for p in net.parameters())/1e6:.2f}M "
          f"swa_start_epoch={swa_start}")
    accum = max(1, args.accum_steps)
    global_step = 0          # counts OPTIMIZER steps (after accumulation)
    micro = 0                # counts micro-batches
    stop = False
    opt.zero_grad(set_to_none=True)
    for epoch in range(1, args.epochs + 1):
        if stop:
            break
        net.train()
        tp = tv = n = 0.0
        in_swa = epoch >= swa_start
        for x, pi, val in dl:
            if use_lr_sched and not in_swa:        # custom schedule controls LR pre-SWA
                for g in opt.param_groups:
                    g["lr"] = lr_for_step(global_step)
            x = x.to(device, non_blocking=True)
            pi = pi.to(device, non_blocking=True)
            val = val.to(device, non_blocking=True)
            # autocast runs matmuls/convs in FP16 but keeps softmax/log_softmax in
            # FP32, so the masked policy CE (with -inf fills) stays numerically safe.
            with torch.autocast(device_type=device, enabled=use_amp):
                p_logits, v_logits = net(x)
                lp = policy_loss(p_logits, pi)
                lv = value_loss(v_logits, val)
                loss = (args.policy_weight * lp + args.value_weight * lv) / accum
            scaler.scale(loss).backward()
            bs = x.size(0)
            tp += lp.item() * bs; tv += lv.item() * bs; n += bs
            micro += 1
            if micro % accum == 0:                  # one optimizer step per `accum` micro-batches
                if args.grad_clip > 0:
                    scaler.unscale_(opt)
                    torch.nn.utils.clip_grad_norm_(net.parameters(), args.grad_clip)
                scaler.step(opt)
                scaler.update()
                opt.zero_grad(set_to_none=True)
                global_step += 1
                if args.report_every and global_step % args.report_every == 0:
                    print(f"  step {global_step:7d}: policy_loss={tp/n:.4f}  value_loss={tv/n:.4f}", flush=True)
                if args.save_every and global_step % args.save_every == 0:
                    ckpt = f"{os.path.splitext(args.out)[0]}_step{global_step}.pt"
                    torch.save(net.state_dict(), ckpt)
                    print(f"  [ckpt] {ckpt}")
                if args.max_steps and global_step >= args.max_steps:
                    stop = True; break
        if in_swa:
            swa_net.update_parameters(net)
            swa_sched.step()
        print(f"  epoch {epoch:3d}: policy_loss={tp/n:.4f}  value_loss={tv/n:.4f}")

    # Recompute BN running stats for the SWA-averaged weights, then export.
    print("[swa] updating BatchNorm statistics on the averaged model...")
    update_bn(dl, swa_net, device=device)

    # Move back to CPU for a portable checkpoint + a CPU-graph ONNX export
    # (the dummy input in export_onnx lives on CPU).
    final = swa_net.module.to("cpu")
    ckpt = os.path.splitext(args.out)[0] + ".pt"
    torch.save(final.state_dict(), ckpt)
    print(f"[ckpt] saved {ckpt}")

    export_onnx(final, args.out)
    verify_onnx(args.out)


if __name__ == "__main__":
    main()
