"""T6 training: transformer (model.py) + qMix loss + SWA + ONNX export (+ I/O verify).

Loss = w_p * policy CE + w_v * value WDL CE + w_m * moves-left Huber (lc0), all weights 1; L2 is the
AdamW weight_decay, not a term of the loss. The policy term is the mean over the positions that HAVE a
policy target (full search); positions searched with the reduced playout cap (fast_search = 1) train the
value and moves-left heads only. Value target (qMix, 8.2.1) is mixed in the dataset. SWA (8.2.4)
averages the last epochs' weights. Export matches the engine I/O contract exactly (FP32).

Usage:
    python train.py --data selfplay_data --epochs 20 --batch 32 --out model_gen1.onnx
"""

import argparse
import os
import random
import sys
import time

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, Subset
from torch.optim.swa_utils import AveragedModel, SWALR

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import FairyNet, ExportNet, NUM_PLANES, POLICY_SIZE  # noqa: E402
from nn_layout import AUX_BASE, AUX_PLANES  # noqa: E402
from dataset import (FairyDataset, collate_packed, game_mtimes, list_games,  # noqa: E402
                     newest_generation, split_games, unpack_batch)
from run_seed import resolve_seed  # noqa: E402


def policy_ce(logits, pi):
    """Cross-entropy of every position, [B]. Masked (lc0 convention): pi < 0 marks ILLEGAL moves -> mask
    them out of the softmax so the denominator only spans legal moves. Legal-unvisited have pi=0 (target
    0), legal-visited have the visit fraction."""
    illegal = pi < 0
    masked_logits = logits.masked_fill(illegal, float("-inf"))
    logp = F.log_softmax(masked_logits, dim=1)
    logp = logp.masked_fill(illegal, 0.0)          # avoid 0 * -inf = NaN
    target = pi.clamp(min=0.0)
    return -(target * logp).sum(dim=1)


def policy_loss(logits, pi, has_policy=None):
    """Mean over the positions. With `has_policy` ([B]: 1 = full search, 0 = reduced playout cap) the mean is
    over the positions WITH a policy target: sum / max(1, how many), not sum / B -- dividing by B would
    halve this term whenever half of the batch has no policy target."""
    ce = policy_ce(logits, pi)
    if has_policy is None:
        return ce.mean()
    return (ce * has_policy).sum() / has_policy.sum().clamp(min=1.0)


def value_loss(logits, target_wdl):
    return -(target_wdl * F.log_softmax(logits, dim=1)).sum(dim=1).mean()


# lc0 (tfprocess.py moves_left_loss): target and output divided by 20, Huber with delta 10 / 20, mean.
MLH_SCALE = 20.0
MLH_DELTA = 10.0


def mlh_loss(pred, plies_left):
    """pred, plies_left: [B] plies. Mean over the positions whose target is filled in (plies_left > 0)."""
    mask = (plies_left > 0).to(pred.dtype)
    loss = F.huber_loss(pred / MLH_SCALE, plies_left / MLH_SCALE, reduction="none", delta=MLH_DELTA / MLH_SCALE)
    return (loss * mask).sum() / mask.sum().clamp(min=1.0)


def split_val(val):
    """The dataset's per-position target row [B,5] -> (wdl [B,3], plies_left [B], has_policy [B])."""
    return val[:, :3], val[:, 3], val[:, 4]


def compute_losses(outputs, pi, val):
    """(policy, value, moves-left) losses of one batch from the net's three outputs."""
    p_logits, v_logits, mlh = outputs
    wdl, plies, has_policy = split_val(val)
    return (policy_loss(p_logits.float(), pi, has_policy), value_loss(v_logits.float(), wdl),
            mlh_loss(mlh.float().squeeze(1), plies))


def device_batches(loader, device, channels_last=False):
    """(x, pi, value) on `device` for each batch of `loader`. Packed batches
    (collate_packed) are rebuilt there by unpack_batch; dense ones are moved.
    channels_last: x in that memory format (same values; faster convolutions
    with --amp on tensor-core GPUs, T4: -13% per training step)."""
    fmt = torch.channels_last if channels_last else torch.contiguous_format
    for batch in loader:
        if len(batch) == 5:
            yield unpack_batch(batch, device, channels_last)
        else:
            x, pi, val = batch
            yield (x.to(device, non_blocking=True).contiguous(memory_format=fmt),
                   pi.to(device, non_blocking=True), val.to(device, non_blocking=True))


def swa_tail_steps(total_steps, count, every):
    """The optimizer steps at which tail SWA takes its snapshots: the last step `total_steps`, then every
    `every` steps back from it, `count` snapshots at most, and none before step 1. A run too short for
    `count` snapshots simply gets fewer (586 steps, 10, 20 -> 406, 426, ..., 586; 100 steps -> 20, 40, ..., 100;
    7 steps -> 7). Ascending."""
    return sorted(s for s in (total_steps - k * every for k in range(max(0, count))) if s >= 1)


@torch.no_grad()
def update_bn(loader, model, device, channels_last=False):
    """torch.optim.swa_utils.update_bn (same steps: reset the BatchNorm running
    statistics, momentum None = cumulative average over one pass in train mode),
    fed through device_batches so packed batches work."""
    momenta = {}
    for m in model.modules():
        if isinstance(m, torch.nn.modules.batchnorm._BatchNorm):
            m.reset_running_stats()
            momenta[m] = m.momentum
    if not momenta:
        return
    was_training = model.training
    model.train()
    for m in momenta:
        m.momentum = None
    for x, _, _ in device_batches(loader, device, channels_last):
        model(x)
    for m in momenta:
        m.momentum = momenta[m]
    model.train(was_training)


def evaluate(net, loader, device, use_amp=False, channels_last=False):
    """(policy loss, value loss, moves-left loss): the mean over every POSITION `loader` yields (the policy
    one over the positions that have a policy target), with the weights fixed (eval mode: no dropout, no
    gradient). Each position counts once, so the numbers do not depend on the batch size: 9000 positions
    give the average of their 9000 losses."""
    was_training = net.training
    net.eval()
    tp = tv = tm = n = n_pol = 0.0
    with torch.no_grad(), torch.autocast(device_type=device, enabled=use_amp):
        for x, pi, val in device_batches(loader, device, channels_last):
            p_logits, v_logits, mlh = net(x)
            wdl, plies, has_policy = split_val(val)
            bs = x.size(0)
            tp += (policy_ce(p_logits.float(), pi) * has_policy).sum().item()
            n_pol += has_policy.sum().item()
            tv += value_loss(v_logits.float(), wdl).item() * bs
            tm += mlh_loss(mlh.float().squeeze(1), plies).item() * bs
            n += bs
    net.train(was_training)
    return tp / max(n_pol, 1.0), tv / n, tm / n


ONNX_OPSET = 18      # the engine's ONNX Runtime (1.18) understands up to opset 21; 18 has every operator used


def export_onnx(net, path):
    """FP32 ONNX with the three outputs the engine reads: policy (raw logits), value (softmaxed WDL), mlh.
    The new (dynamo) exporter first, as the plan chose; if it fails (say, a torch/onnxscript mismatch on
    the machine), the legacy TorchScript exporter -- the graph is made of basic operators, so both work."""
    net.eval()
    exp = ExportNet(net).eval()
    dummy = torch.randn(2, NUM_PLANES, 10, 10)
    try:
        batch = torch.export.Dim("batch", min=1, max=1024)
        torch.onnx.export(
            exp, (dummy,), path,
            input_names=["input"], output_names=["policy", "value", "mlh"],
            dynamic_shapes={"x": {0: batch}},
            opset_version=ONNX_OPSET,
            dynamo=True, report=False,
            external_data=False,     # the weights INSIDE the one .onnx file: the release holds only gen<n>.onnx
        )
        how = "dynamo exporter"
    except Exception as e:      # noqa: BLE001 - any exporter failure falls back
        print(f"[export] dynamo exporter failed ({type(e).__name__}: {str(e)[:200]}); using the legacy exporter")
        torch.onnx.export(
            exp, dummy, path,
            input_names=["input"], output_names=["policy", "value", "mlh"],
            dynamic_axes={"input": {0: "batch"}, "policy": {0: "batch"}, "value": {0: "batch"},
                          "mlh": {0: "batch"}},
            opset_version=ONNX_OPSET,
            dynamo=False,
        )
        how = "legacy exporter"
    print(f"[export] wrote {path} ({how}, opset {ONNX_OPSET}, FP32)")


def verify_onnx(path, net=None):
    """Checks the exported graph's I/O contract and, when `net` is given, that the
    .onnx computes what the PyTorch net does (the .pt saved next to it)."""
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
    assert ins[0][0] == "input" and list(ins[0][1]) == ["batch", NUM_PLANES, 10, 10], f"bad input {ins[0]}"
    out_names = {n for n, _ in outs}
    assert out_names == {"policy", "value", "mlh"}, f"bad outputs {out_names}"
    for n, d in outs:
        if n == "policy":
            assert list(d) == ["batch", POLICY_SIZE], f"bad policy shape {d}"
        if n == "value":
            assert list(d) == ["batch", 3], f"bad value shape {d}"
        if n == "mlh":
            assert list(d) == ["batch", 1], f"bad mlh shape {d}"
    opsets = {o.domain or "ai.onnx": o.version for o in m.opset_import}
    assert opsets.get("ai.onnx", 0) <= 21, f"opset {opsets} is newer than the engine's ONNX Runtime understands"
    assert not any(t.data_type == 10 for t in m.graph.initializer), "the graph has FP16 weights; the engine runs FP32"
    assert not any(t.data_location == onnx.TensorProto.EXTERNAL for t in m.graph.initializer),         "the weights are in an external .data file; the .onnx alone (as uploaded to the release) would not load"
    assert not os.path.exists(path + ".data"), f"{path}.data exists: remove it, the .onnx must be self-contained"
    print(f"[verify] opset {opsets}, {len(m.graph.node)} nodes, ops: "
          f"{sorted({n.op_type for n in m.graph.node})}")

    sess = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
    x = np.random.randn(2, NUM_PLANES, 10, 10).astype(np.float32)
    pol, val, mlh = sess.run(["policy", "value", "mlh"], {"input": x})
    assert pol.shape == (2, POLICY_SIZE), pol.shape
    assert val.shape == (2, 3), val.shape
    assert mlh.shape == (2, 1), mlh.shape
    vsum = val.sum(axis=1)
    assert np.allclose(vsum, 1.0, atol=1e-4), f"value (WDL) must sum to 1, got {vsum}"
    # the batch axis is dynamic: another batch size must run too
    pol5, _, _ = sess.run(["policy", "value", "mlh"], {"input": np.random.randn(5, NUM_PLANES, 10, 10).astype(np.float32)})
    assert pol5.shape == (5, POLICY_SIZE), pol5.shape
    print(f"[verify] runtime OK: policy{pol.shape} value{val.shape} mlh{mlh.shape} value_sum={vsum}")
    if net is not None:
        # Same numbers from ONNX Runtime and PyTorch, on inputs shaped like real
        # planes (0/1 squares, scalar aux planes), not only the right shapes.
        rng = np.random.default_rng(0)
        xr = (rng.random((8, NUM_PLANES, 10, 10)) < 0.08).astype(np.float32)
        xr[:, AUX_BASE:] = rng.random((8, AUX_PLANES, 1, 1)).astype(np.float32)
        o_pol, o_val, o_mlh = sess.run(["policy", "value", "mlh"], {"input": xr})
        was_training = net.training
        net.eval()
        with torch.no_grad():
            t_pol, t_val, t_mlh = ExportNet(net)(torch.from_numpy(xr))
        net.train(was_training)
        dp = float(np.abs(o_pol - t_pol.numpy()).max())
        dv = float(np.abs(o_val - t_val.numpy()).max())
        dm = float(np.abs(o_mlh - t_mlh.numpy()).max())
        print(f"[verify] onnx vs torch: max |policy logit| {dp:.2e}, max |WDL| {dv:.2e}, max |mlh| {dm:.2e}")
        assert dp < 1e-3 and dv < 1e-4 and dm < 1e-3, "the .onnx does not compute what the PyTorch net does"
    print("[verify] PASS: ONNX I/O contract matches engine (policy=logits, value=softmax WDL, mlh=plies).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--q-ratio", type=float, default=0.25)
    ap.add_argument("--downsample", type=float, default=1.0)
    ap.add_argument("--d-model", type=int, default=192, help="transformer width (fresh train only)")
    ap.add_argument("--layers", type=int, default=10, help="transformer layers (fresh train only)")
    ap.add_argument("--heads", type=int, default=6, help="attention heads per layer (fresh train only)")
    ap.add_argument("--out", default="model_gen1.onnx")
    ap.add_argument("--init-from", default="", help="warm-start: load .pt weights of previous gen")
    ap.add_argument("--threads", type=int, default=0)
    ap.add_argument("--workers", type=int, default=None,
                    help="DataLoader worker processes (default: auto = CPU count on GPU, else 0)")
    ap.add_argument("--pin-memory", action="store_true", help="pin host memory (faster CPU->GPU copy)")
    # NOT streaming: it keeps every raw record (dense POLICY_SIZE-float policy + planes as
    # Python ints: 51 KB each, measured, vs 4.8 KB in the default sparse cache), then
    # rebuilds each item from it. Its help used to say "lower RAM" -- the opposite.
    ap.add_argument("--no-cache", action="store_true",
                    help="keep the RAW records and rebuild each item from them (~10x the RAM of "
                         "the default sparse cache; for debugging only)")
    ap.add_argument("--diff-focus", action="store_true", help="prefer 'surprising' positions (8.2.6)")
    ap.add_argument("--df-slope", type=float, default=1.0, help="diff_focus: keep-prob slope")
    ap.add_argument("--df-kld-w", type=float, default=0.5, help="diff_focus: policy_kld weight")
    ap.add_argument("--df-min", type=float, default=0.2, help="diff_focus: min keep prob")
    ap.add_argument("--weight-decay", type=float, default=1e-4, help="L2 regularization (8.2.5)")
    ap.add_argument("--value-weight", type=float, default=1.0, help="value-loss weight vs policy")
    ap.add_argument("--mlh-weight", type=float, default=1.0, help="moves-left-loss weight vs policy (lc0 example: 1)")
    ap.add_argument("--swa-start-frac", type=float, default=0.75, help="start SWA at this fraction of epochs")
    ap.add_argument("--swa-lr", type=float, default=0.0, help="SWA LR (0 => lr*0.5)")
    ap.add_argument("--swa-steps", type=int, default=0,
                    help="lc0-style SWA: fold the weights into the average every N optimizer "
                         "steps from the start, LR untouched (0 = per-epoch SWA, --swa-start-frac)")
    ap.add_argument("--swa-max-n", type=int, default=10,
                    help="lc0-style SWA: cap on the running-average count -- once reached, each "
                         "new snapshot weighs 1/(max_n+1) (a moving average of ~the last max_n)")
    ap.add_argument("--swa-tail", type=int, default=0,
                    help="tail SWA (the FairyZero runs): average N snapshots of the weights, EQUAL "
                         "weights, taken at the LAST optimizer step and every --swa-tail-every steps "
                         "back from it (never before step 1: a run too short for N snapshots takes "
                         "fewer). LR untouched. 0 = off. Not with --swa-steps")
    ap.add_argument("--swa-tail-every", type=int, default=20,
                    help="tail SWA: optimizer steps between two snapshots, counted back from the last step")
    ap.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"],
                    help="training device (auto = cuda if available, else cpu)")
    ap.add_argument("--amp", action="store_true",
                    help="mixed-precision FP16 training; NOT used by the FairyZero runs (FP32 only, owner's "
                         "decision 2026-11-20); ignored on CPU")
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
    ap.add_argument("--seed", type=int, default=None,
                    help="seed of the run: shuffling, down-sampling, the validation split "
                         "(default: random for every run, printed; pass it back to repeat a run)")
    ap.add_argument("--warmup-steps", type=int, default=0, help="linear LR warmup over N optimizer steps")
    ap.add_argument("--lr-values", default="", help="step LR schedule values, comma-separated (overrides --lr)")
    ap.add_argument("--lr-boundaries", default="", help="step LR schedule boundaries, comma-separated")
    # #5 — more lczero-training-style knobs.
    ap.add_argument("--dropout", type=float, default=0.0, help="dropout in value head (warm-start safe)")
    ap.add_argument("--accum-steps", type=int, default=1, help="gradient accumulation steps (big effective batch)")
    ap.add_argument("--max-steps", type=int, default=0, help="stop after N optimizer steps (0 = use --epochs)")
    ap.add_argument("--max-records", type=int, default=0, help="cap #records loaded (0 = all)")
    ap.add_argument("--val-frac", type=float, default=0.04,
                    help="hold out this fraction of the GAMES -- the newest by modification time, "
                         "i.e. the latest self-play -- as a validation set, and print its losses "
                         "before training, after each epoch and for the exported model (0 = off)")
    ap.add_argument("--val-newest-gen", action="store_true",
                    help="score the STARTING weights once on every game of the newest generation "
                         "(highest games_gen<g> folder: games the warm-start net played and never "
                         "trained on), then train on ALL games including those; no other [val] "
                         "lines. Needs --val-frac 0")
    ap.add_argument("--report-every", type=int, default=0, help="print running loss every N steps (0 = per-epoch)")
    ap.add_argument("--save-every", type=int, default=0, help="export an ONNX checkpoint every N steps (0 = only final)")
    args = ap.parse_args()
    if args.swa_tail < 0 or args.swa_tail_every < 1:
        sys.exit(f"--swa-tail must be >= 0 and --swa-tail-every >= 1, got {args.swa_tail} and {args.swa_tail_every}")
    if args.swa_tail > 0 and args.swa_steps > 0:
        sys.exit("--swa-tail and --swa-steps are two different SWA schemes: use one of them")
    args.seed = resolve_seed(args.seed, "train")
    if args.threads > 0:
        torch.set_num_threads(args.threads)

    device = ("cuda" if torch.cuda.is_available() else "cpu") if args.device == "auto" else args.device
    if device == "cuda" and not torch.cuda.is_available():
        print("[train] WARNING: --device cuda but no CUDA available; falling back to cpu")
        device = "cpu"
    use_amp = args.amp and device == "cuda"
    # DataLoader throughput (#1): with the sparse cache, every __getitem__ rebuilds the
    # [NUM_PLANES,10,10] planes on the CPU, so without worker processes the GPU starves waiting
    # for them. Default workers to the CPU count ONLY on GPU (Linux/Colab 'fork' shares
    # the cache cheaply via copy-on-write); keep 0 on CPU-only, where Windows 'spawn'
    # would pickle the whole in-RAM cache into each worker. pin_memory only speeds
    # host->GPU copies, so auto-enable it with cuda.
    workers = args.workers
    if workers is None:
        workers = min(os.cpu_count() or 2, 8) if device == "cuda" else 0
    pin = args.pin_memory or (device == "cuda")
    cl = False                     # channels_last was for the convolutions; the transformer has none
    packed = args.sparse_cache and not args.no_cache
    print(f"[train] device={device}  amp={use_amp}  sparse_cache={args.sparse_cache}  "
          f"workers={workers}  pin_memory={pin}  channels_last={cl}  planes_on_device={packed}")

    torch.manual_seed(args.seed)
    if not 0.0 <= args.val_frac < 1.0:
        sys.exit(f"--val-frac must be in [0, 1), got {args.val_frac}")
    if args.val_newest_gen and args.val_frac > 0:
        sys.exit("--val-newest-gen trains on every game: use it with --val-frac 0")
    games = list_games(args.data)
    mtimes = game_mtimes(games) if args.val_frac > 0 else [0.0] * len(games)
    train_games, val_games = split_games(games, args.val_frac, mtimes)
    if args.val_frac > 0 and not val_games:
        print(f"[val] {len(games)} game(s) are too few for --val-frac {args.val_frac}: "
              "no validation set")
    ds = FairyDataset(args.data, q_ratio=args.q_ratio, downsample_keep=args.downsample,
                      cache=not args.no_cache, diff_focus=args.diff_focus,
                      df_slope=args.df_slope, df_kld_w=args.df_kld_w, df_min=args.df_min,
                      sparse=args.sparse_cache, max_records=args.max_records,
                      games=train_games, label="train" if val_games else "", seed=args.seed,
                      packed=packed)
    collate = collate_packed if packed else None
    dl = DataLoader(ds, batch_size=args.batch, shuffle=True, drop_last=False,
                    num_workers=workers, pin_memory=pin, collate_fn=collate,
                    persistent_workers=(workers > 0))

    # Validation: the held-out games in full (no down-sampling / diff_focus: the
    # natural mix), next to as many TRAINING positions drawn at random. Both are
    # evaluated the same way (fixed weights, eval mode); the loss printed for each
    # epoch while training is a running mean over changing weights in train mode,
    # so only these two numbers compare: val above train = what does not carry
    # over to unseen games (a value head memorizing games shows up there).
    val_loaders = None
    if val_games:
        ds_val = FairyDataset(args.data, q_ratio=args.q_ratio, cache=not args.no_cache,
                              sparse=args.sparse_cache, games=val_games, label="validation",
                              packed=packed)
        train_part = random.Random(args.seed + 1).sample(range(len(ds)), min(len(ds), len(ds_val)))
        def eval_loader(d):
            return DataLoader(d, batch_size=max(args.batch, 256), shuffle=False,
                              num_workers=workers, pin_memory=pin, collate_fn=collate,
                              persistent_workers=(workers > 0))
        val_loaders = (eval_loader(Subset(ds, train_part)), eval_loader(ds_val))
        print(f"[val] {len(val_games)} of {len(games)} games held out ({len(ds_val)} positions), "
              f"compared with {len(train_part)} training positions")
        stamp = dict(zip(games, mtimes))
        day = lambda t: time.strftime("%Y-%m-%d %H:%M", time.localtime(t))
        print(f"[val] validation games modified {day(min(stamp[g] for g in val_games))} .. "
              f"{day(max(stamp[g] for g in val_games))}; training games up to "
              f"{day(max(stamp[g] for g in train_games))}")

    # --val-newest-gen: the newest generation's games, scored ONCE with the starting
    # weights below, and trained on like every other game (they are in train_games).
    first_val = None
    if args.val_newest_gen:
        gen, newest = newest_generation(games)
        if not newest:
            print("[val] --val-newest-gen: no games_gen<g> folder in the data paths -- no score")
        else:
            ds_first = FairyDataset(args.data, q_ratio=args.q_ratio, cache=not args.no_cache,
                                    sparse=args.sparse_cache, games=newest,
                                    label=f"newest generation {gen}", packed=packed)
            first_val = (gen, len(newest), len(ds_first),
                         DataLoader(ds_first, batch_size=max(args.batch, 256), shuffle=False,
                                    num_workers=workers, pin_memory=pin, collate_fn=collate))

    def report(what, model):
        if val_loaders is None:
            return
        tp, tv, tm = evaluate(model, val_loaders[0], device, use_amp, cl)
        vp, vv, vm = evaluate(model, val_loaders[1], device, use_amp, cl)
        print(f"  [val] {what:<14}  train: policy={tp:.4f} value={tv:.4f} mlh={tm:.4f}  |  "
              f"validation: policy={vp:.4f} value={vv:.4f} mlh={vm:.4f}", flush=True)

    net = FairyNet(d_model=args.d_model, layers=args.layers, heads=args.heads, dropout=args.dropout)
    if args.init_from:
        net.load_state_dict(torch.load(args.init_from, map_location="cpu"))
        print(f"[warm-start] loaded weights from {args.init_from}")
    net.to(device)
    if cl:
        net.to(memory_format=torch.channels_last)
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
    accum = max(1, args.accum_steps)
    # --swa-steps N (lc0 tfprocess.update_swa): every N optimizer steps
    #   swa = swa * n/(n+1) + w/(n+1),  n = min(snapshots so far, swa_max_n)
    # the first snapshot is a plain copy; LR is never changed for SWA. Otherwise
    # (per-epoch SWA) the average is taken at the end of the late epochs below.
    lc0_swa = args.swa_steps > 0
    # --swa-tail N: tail SWA. The optimizer steps the run will take are known up front (micro-batches
    # of all epochs // accumulation, cut by --max-steps; a last incomplete accumulation group is never
    # stepped), so the snapshot steps are fixed now: the last step and every --swa-tail-every back.
    tail_swa = args.swa_tail > 0
    total_steps = (len(dl) * args.epochs) // accum
    if args.max_steps:
        total_steps = min(total_steps, args.max_steps)
    tail_steps = swa_tail_steps(total_steps, args.swa_tail, args.swa_tail_every) if tail_swa else []
    tail_set = set(tail_steps)
    if lc0_swa:
        max_n = max(1, args.swa_max_n)

        def capped_avg(avg_p, p, num):
            return avg_p + (p - avg_p) / (torch.clamp(num, max=max_n) + 1)

        swa_net = AveragedModel(net, avg_fn=capped_avg)
    else:
        swa_net = AveragedModel(net)    # default average: every snapshot weighs the same
    # SWA averages the weights at the end of the epochs that START after
    # `swa_start_frac` of the training: with 20 epochs and 0.75 that is epochs
    # 16-20. It used to be max(1, int(E * frac)), one epoch early: epochs 15-20,
    # and with the usual `--epochs 2` both epochs (the average then included the
    # half-trained weights of epoch 1). `--swa-start-frac 0` averages every epoch.
    swa_start = (args.epochs + 1 if (lc0_swa or tail_swa)   # step-based modes: no per-epoch SWA / SWALR
                 else min(args.epochs, int(args.epochs * args.swa_start_frac) + 1))
    swa_sched = SWALR(opt, swa_lr=(args.swa_lr if args.swa_lr > 0 else args.lr * 0.5))

    if tail_swa:
        swa_desc = (f"tail: {len(tail_steps)} snapshot(s) at steps {tail_steps[0]}..{tail_steps[-1]} "
                    f"every {args.swa_tail_every} (the last of {total_steps} steps), equal weights, LR unchanged"
                    if tail_steps else f"tail: no snapshot (the run has {total_steps} optimizer steps)")
    elif lc0_swa:
        swa_desc = f"every {args.swa_steps} steps, max_n {max_n} (lc0), LR unchanged"
    else:
        swa_desc = f"averages the end of epochs {swa_start}..{args.epochs}"
    print(f"[train] params={sum(p.numel() for p in net.parameters())/1e6:.2f}M swa: {swa_desc}")
    report("start weights", net)
    if first_val is not None:
        gen, n_games, n_pos, loader = first_val
        vp, vv, vm = evaluate(net, loader, device, use_amp, cl)
        print(f"  [val] start weights on generation {gen} (all {n_games} games, {n_pos} positions, "
              f"never trained on; trained on below): policy={vp:.4f} value={vv:.4f} mlh={vm:.4f}", flush=True)
        del loader, first_val   # frees the scoring copy of those games
    global_step = 0         # counts OPTIMIZER steps (after accumulation)
    micro = 0                # counts micro-batches
    stop = False
    opt.zero_grad(set_to_none=True)
    for epoch in range(1, args.epochs + 1):
        if stop:
            break
        net.train()
        tp = tv = tm = n = n_pol = 0.0
        in_swa = epoch >= swa_start
        for x, pi, val in device_batches(dl, device, cl):
            if use_lr_sched and not in_swa:        # custom schedule controls LR pre-SWA
                for g in opt.param_groups:
                    g["lr"] = lr_for_step(global_step)
            # autocast runs matmuls/convs in FP16 but keeps softmax/log_softmax in
            # FP32, so the masked policy CE (with -inf fills) stays numerically safe.
            with torch.autocast(device_type=device, enabled=use_amp):
                lp, lv, lm = compute_losses(net(x), pi, val)
                loss = (args.policy_weight * lp + args.value_weight * lv + args.mlh_weight * lm) / accum
            scaler.scale(loss).backward()
            bs = x.size(0)
            n_has = float(val[:, 4].sum().item())     # positions with a policy target in this batch
            tp += lp.item() * n_has; n_pol += n_has
            tv += lv.item() * bs; tm += lm.item() * bs; n += bs
            micro += 1
            if micro % accum == 0:                  # one optimizer step per `accum` micro-batches
                if args.grad_clip > 0:
                    scaler.unscale_(opt)
                    torch.nn.utils.clip_grad_norm_(net.parameters(), args.grad_clip)
                scaler.step(opt)
                scaler.update()
                opt.zero_grad(set_to_none=True)
                global_step += 1
                if lc0_swa and global_step % args.swa_steps == 0:
                    swa_net.update_parameters(net)
                if tail_swa and global_step in tail_set:
                    swa_net.update_parameters(net)
                if args.report_every and global_step % args.report_every == 0:
                    print(f"  step {global_step:7d}: policy_loss={tp/max(n_pol, 1.0):.4f}  value_loss={tv/n:.4f}  "
                          f"mlh_loss={tm/n:.4f}", flush=True)
                if args.save_every and global_step % args.save_every == 0:
                    ckpt = f"{os.path.splitext(args.out)[0]}_step{global_step}.pt"
                    torch.save(net.state_dict(), ckpt)
                    print(f"  [ckpt] {ckpt}")
                if args.max_steps and global_step >= args.max_steps:
                    stop = True; break
        if in_swa:
            swa_net.update_parameters(net)
            swa_sched.step()
        print(f"  epoch {epoch:3d}: policy_loss={tp/max(n_pol, 1.0):.4f}  value_loss={tv/n:.4f}  mlh_loss={tm/n:.4f}")
        report(f"epoch {epoch}", net)

    if int(swa_net.n_averaged) == 0:
        # Stopped (--max-steps) before the first SWA epoch ended. The averaged
        # model is then still the deep copy made BEFORE training, and exporting
        # it -- as this used to -- wrote out the untrained starting weights.
        print("[swa] WARNING: training stopped before any SWA snapshot was taken; exporting "
              "the trained weights as they are (no average)")
        report("exported model", net)
        final = net.to("cpu", memory_format=torch.contiguous_format)
    else:
        # Recompute BN running stats for the SWA-averaged weights, then export.
        print(f"[swa] averaged {int(swa_net.n_averaged)} "
              f"{'snapshot(s)' if (lc0_swa or tail_swa) else 'epoch(s)'}")
        if tail_swa and (int(swa_net.n_averaged) != len(tail_steps) or global_step != total_steps):
            print(f"[swa] WARNING: tail SWA planned {len(tail_steps)} snapshot(s) over {total_steps} steps, "
                  f"took {int(swa_net.n_averaged)} over {global_step} (the data changed length?)")
        update_bn(dl, swa_net, device, cl)
        report("exported model", swa_net.module)
        # Move back to CPU for a portable checkpoint + a CPU-graph ONNX export
        # (the dummy input in export_onnx lives on CPU).
        final = swa_net.module.to("cpu", memory_format=torch.contiguous_format)
    ckpt = os.path.splitext(args.out)[0] + ".pt"
    torch.save(final.state_dict(), ckpt)
    print(f"[ckpt] saved {ckpt}")

    export_onnx(final, args.out)
    verify_onnx(args.out, final)


if __name__ == "__main__":
    main()
