"""T6 training: transformer (model.py) + qMix loss + SWA + ONNX export (+ I/O verify).

Loss = w_p * policy CE + w_v * value WDL CE + w_m * moves-left Huber (lc0), all weights 1; L2 is the
AdamW weight_decay, not a term of the loss. The policy term is the mean over the positions that HAVE a
policy target (full search); positions searched with the reduced playout cap (fast_search = 1) train the
value and moves-left heads only. The value term is likewise the mean over the positions that HAVE a value
target: all of them, or with --value-per-game K only K drawn from each game (the others carry an all-zero
W/D/L row). Value target is mixed in the dataset: the qMix (8.2.1), or with --td-lambda the game result mixed
with a TD(lambda) return over the later search values (dataset.td_value_targets). --mirror flips each training
position left-right with probability 1/2 every time it is drawn (dataset.mirror_batch). SWA (8.2.4)
averages the last epochs' weights. Export matches the engine I/O contract exactly (FP32).

Usage:
    python train.py --data selfplay_data --epochs 20 --batch 32 --out model_gen1.onnx   # model_gen1.pt + the ONNX file
    python train.py --data selfplay_data --epochs 20 --batch 32 --out model_gen1.pt     # the checkpoint only (CUDA runner)
"""

import argparse
import os
import random
import sys
import math
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
                     mirror_batch, newest_generation, newest_n_games, split_games, unpack_batch)
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


def policy_loss(logits, pi, has_policy=None, weight=None):
    """Mean over the positions. With `has_policy` ([B]: 1 = full search, 0 = reduced playout cap) the mean is
    over the positions WITH a policy target: sum / max(1, how many), not sum / B -- dividing by B would
    halve this term whenever half of the batch has no policy target. `weight` ([B], the surprise weights, mean 1
    over the data): each position's loss times its weight, still divided by the number of positions."""
    ce = policy_ce(logits, pi)
    if weight is not None:
        ce = ce * weight
    if has_policy is None:
        return ce.mean()
    return (ce * has_policy).sum() / has_policy.sum().clamp(min=1.0)


def value_loss(logits, target_wdl, weight=None):
    """Mean over the positions that HAVE a value target. A row of zeros (--value-per-game: a position whose value
    target was left out) counts for nothing; with every row a distribution (always, without that flag) this is the
    plain mean over the batch. `weight`: as in policy_loss."""
    ce = -(target_wdl * F.log_softmax(logits, dim=1)).sum(dim=1)
    has = has_value(target_wdl).to(ce.dtype)
    if weight is not None:
        ce = ce * weight
    return (ce * has).sum() / has.sum().clamp(min=1.0)


def has_value(target_wdl):
    """[B] bool: the rows that carry a value target (a W/D/L distribution, not the all-zero 'no target' row)."""
    return target_wdl.sum(dim=1) > 0.5


# lc0 (tfprocess.py moves_left_loss): target and output divided by 20, Huber with delta 10 / 20, mean.
MLH_SCALE = 20.0
MLH_DELTA = 10.0


def mlh_loss(pred, plies_left):
    """pred, plies_left: [B] plies. Mean over the positions whose target is filled in (plies_left > 0)."""
    mask = (plies_left > 0).to(pred.dtype)
    loss = F.huber_loss(pred / MLH_SCALE, plies_left / MLH_SCALE, reduction="none", delta=MLH_DELTA / MLH_SCALE)
    return (loss * mask).sum() / mask.sum().clamp(min=1.0)


def split_val(val):
    """The dataset's per-position target row [B,7] (or [B,5]) -> (wdl [B,3], plies_left [B], has_policy [B])."""
    return val[:, :3], val[:, 3], val[:, 4]


def split_weights(val):
    """(value weight [B], policy weight [B]) of the target rows (FairyDataset columns 5, 6), or (None, None) for
    rows without them."""
    return (val[:, 5], val[:, 6]) if val.size(1) >= 7 else (None, None)


def compute_losses(outputs, pi, val):
    """(policy, value, moves-left) TRAINING losses of one batch from the net's three outputs, with the surprise
    weights of the targets (all 1 unless --surprise-*-beta). evaluate() scores without them."""
    p_logits, v_logits, mlh = outputs
    wdl, plies, has_policy = split_val(val)
    w_value, w_policy = split_weights(val)
    return (policy_loss(p_logits.float(), pi, has_policy, w_policy), value_loss(v_logits.float(), wdl, w_value),
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
    one over the positions that have a policy target, the value one over those that have a value target), with
    the weights fixed (eval mode: no dropout, no gradient). Each position counts once, so the numbers do not
    depend on the batch size: 9000 positions give the average of their 9000 losses."""
    was_training = net.training
    net.eval()
    tp = tv = tm = n = n_pol = n_val = 0.0
    with torch.no_grad(), torch.autocast(device_type=device, enabled=use_amp):
        for x, pi, val in device_batches(loader, device, channels_last):
            p_logits, v_logits, mlh = net(x)
            wdl, plies, has_policy = split_val(val)
            bs = x.size(0)
            nv = has_value(wdl).sum().item()
            tp += (policy_ce(p_logits.float(), pi) * has_policy).sum().item()
            n_pol += has_policy.sum().item()
            tv += value_loss(v_logits.float(), wdl).item() * nv
            n_val += nv
            tm += mlh_loss(mlh.float().squeeze(1), plies).item() * bs
            n += bs
    net.train(was_training)
    return tp / max(n_pol, 1.0), tv / max(n_val, 1.0), tm / n


ONNX_OPSET = 18      # the engine's ONNX Runtime (1.18) understands up to opset 21; 18 has every operator used


FUSE_TOLERANCE = (1e-4, 1e-5, 1e-3)   # max |policy logit|, |WDL|, |mlh| the fused graph may differ from the plain one


def fuse_onnx(path, net):
    """Fuses the exported graph in place, staying FP32 and computing the same function: LayerNorm after a residual add
    becomes SkipLayerNormalization, the GELU (written with Erf) and the bias before it become Gelu / BiasGelu (ONNX Runtime's
    own passes leave most of them alone). This small transformer is bound by the memory traffic of its many small elementwise
    kernels, not by the matrix products, so fusing them is worth about 30%: measured on a T4 in the engine (ORT 1.20.1,
    16 games, 800/200 playouts) 1585 -> 2026 NN eval/s, 1690 -> 2164 nps, outputs equal to 7e-7.
    Returns True if `path` now holds the fused graph. Any failure, or a fused graph that does not give the same numbers as
    the plain one on realistic inputs, leaves `path` untouched (and says why)."""
    fused = path + ".gop"
    try:
        import onnxruntime as ort
        from onnxruntime.transformers import optimizer
        d_model, heads = net.embed.out_features, net.blocks[0].attn.heads
        om = optimizer.optimize_model(path, model_type="bert", num_heads=heads, hidden_size=d_model, use_gpu=False,
                                      opt_level=1)
        om.save_model_to_file(fused)
        x = check_inputs(8)
        outs = []
        for p in (path, fused):
            sess = ort.InferenceSession(p, providers=["CPUExecutionProvider"])
            outs.append(sess.run(["policy", "value", "mlh"], {"input": x}))
        diffs = [float(np.abs(a - b).max()) for a, b in zip(*outs)]
        if any(d > tol for d, tol in zip(diffs, FUSE_TOLERANCE)):
            print(f"[export] fusion NOT used: the fused graph differs from the plain one by {diffs} (> {FUSE_TOLERANCE})")
            return False
        os.replace(fused, path)
        print(f"[export] fused graph (SkipLayerNormalization / BiasGelu / Gelu, still FP32): "
              f"max |policy logit| {diffs[0]:.1e}, |WDL| {diffs[1]:.1e}, |mlh| {diffs[2]:.1e} from the plain graph")
        return True
    except Exception as e:      # noqa: BLE001 - fusion is an optimisation: never lose the export because of it
        print(f"[export] fusion skipped ({type(e).__name__}: {str(e)[:200]}); the plain graph is kept")
        return False
    finally:
        if os.path.exists(fused):
            os.remove(fused)


FP16_TOLERANCE = (0.01, 0.01, 1.0)    # max over the checked positions: total variation of softmax(policy), |WDL|, |mlh| plies
FP16_CHECK_POSITIONS = 64


def check_inputs(n=FP16_CHECK_POSITIONS, seed=0):
    """n synthetic input positions shaped like real ones (sparse 0/1 piece planes, scalar auxiliary planes)."""
    rng = np.random.default_rng(seed)
    x = (rng.random((n, NUM_PLANES, 10, 10)) < 0.08).astype(np.float32)
    x[:, AUX_BASE:] = rng.random((n, AUX_PLANES, 1, 1)).astype(np.float32)
    return x


def _softmax(a):
    e = np.exp(a - a.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)


def fp16_differences(ref, out):
    """(max total-variation distance of softmax(policy), max |WDL|, max |mlh|) between two (policy, value, mlh) results,
    or None if `out` has a NaN / infinity. The total variation is what the search sees: how far the move
    probabilities move, so a logit that is off by 0.01 where the logits are 20 apart does not count as a defect."""
    if not all(np.isfinite(a).all() for a in out):
        return None
    tv = 0.5 * np.abs(_softmax(ref[0].astype(np.float64)) - _softmax(out[0].astype(np.float64))).sum(axis=1).max()
    return float(tv), float(np.abs(ref[1] - out[1]).max()), float(np.abs(ref[2] - out[2]).max())


def fuse_attention_onnx(path, net):
    """Replaces, in the exported FP32 graph at `path`, the attention of every layer -- Reshape / Transpose / 3 Gather / Mul /
    Transpose / MatMul / Add(bias) / Softmax / MatMul / Transpose / Reshape, about 12 small kernels plus a 4D bias -- by ONE
    com.microsoft::MultiHeadAttention node (Split of the qkv product into q, k, v; the learned relative-position bias as the
    node's relative_position_bias input; scale 1/sqrt(dh)). ONNX Runtime's CUDA kernel runs it as fused attention in half
    precision. Measured on a T4 (PyTorch, FP16, batch 64): attention as one fused kernel 11.7 -> 8.4 ms (x1.39).
    Pure graph surgery on the graph the exporter writes, so it looks for the pattern layer by layer and gives up (returns
    False, file untouched) unless every layer matches. The constants of the bias come from `net` (the same weights).
    Meant for the half-precision GPU graph (fp16_onnx); the CPU provider is not asked to run it."""
    import onnx
    from collections import defaultdict
    from onnx import helper, numpy_helper, TensorProto
    try:
        m = onnx.load(path)
        g = m.graph
        heads, d = net.blocks[0].attn.heads, net.embed.out_features
        dh = d // heads
        init = {t.name: t for t in g.initializer}
        prod = {o: n for n in g.node for o in n.output}
        cons = defaultdict(list)
        for n in g.node:
            for i in n.input:
                cons[i].append(n)

        def const_val(name):
            return numpy_helper.to_array(init[name]) if name in init else None

        def parent(name, op):
            n = prod.get(name)
            return n if n is not None and n.op_type == op else None

        def perm_of(n):
            return [int(v) for v in next((a.ints for a in n.attribute if a.name == "perm"), [])]

        def axis_of(n):
            return next((a.i for a in n.attribute if a.name == "axis"), 0)

        def trace(name, is_k):
            """Walk back from q, k^T or v (as the product sees it) to the Reshape [B,T,3,H,dh] of the qkv product; the graph
            comes in two layouts, according to the onnxruntime that optimised it:
              A: Reshape -> Transpose(2,0,3,1,4) -> Gather(axis 0, i) [-> Transpose(0,1,3,2) for k]
              B: Reshape -> Gather(axis 2, i) -> Transpose(0,2,1,3) [(0,2,3,1) for k, which is already k^T]
            Returns (component index, the Reshape) or None."""
            n = prod.get(name)
            if n is None:
                return None
            if n.op_type == "Transpose" and perm_of(n) == ([0, 1, 3, 2] if is_k else None):      # layout A, k
                n = prod.get(n.input[0])
            elif n.op_type == "Transpose" and perm_of(n) == ([0, 2, 3, 1] if is_k else [0, 2, 1, 3]):  # layout B
                gth = prod.get(n.input[0])
                if gth is None or gth.op_type != "Gather" or axis_of(gth) != 2:
                    return None
                i, view = const_val(gth.input[1]), parent(gth.input[0], "Reshape")
                return (int(i), view) if i is not None and i.size == 1 and view is not None else None
            if n is None or n.op_type != "Gather" or axis_of(n) != 0:                           # layout A
                return None
            i, perm = const_val(n.input[1]), prod.get(n.input[0])
            if i is None or i.size != 1 or perm is None or perm.op_type != "Transpose" or perm_of(perm) != [2, 0, 3, 1, 4]:
                return None
            view = parent(perm.input[0], "Reshape")
            return (int(i), view) if view is not None else None

        found = []     # (softmax, qkv product output, final reshape node, [nodes to remove])
        for S in (n for n in g.node if n.op_type == "Softmax"):
            add = parent(S.input[0], "Add")
            if add is None:
                continue
            mm = parent(add.input[0], "MatMul") or parent(add.input[1], "MatMul")
            if mm is None or len(S.output) != 1 or len(cons[S.output[0]]) != 1:
                continue
            mul = parent(mm.input[0], "Mul")
            av = cons[S.output[0]][0]
            if mul is None or av.op_type != "MatMul" or av.input[0] != S.output[0]:
                continue
            sc = const_val(mul.input[1])
            if sc is None or sc.size != 1 or abs(float(sc) - dh ** -0.5) > 1e-6:
                continue
            tq, tk, tv = trace(mul.input[0], False), trace(mm.input[1], True), trace(av.input[1], False)
            if None in (tq, tk, tv) or [tq[0], tk[0], tv[0]] != [0, 1, 2] or not (tq[1] is tk[1] is tv[1]):
                continue
            t2 = cons[av.output[0]][0] if len(cons[av.output[0]]) == 1 else None
            r2 = cons[t2.output[0]][0] if t2 is not None and t2.op_type == "Transpose" and len(cons[t2.output[0]]) == 1 else None
            if r2 is None or r2.op_type != "Reshape":
                continue
            # Only the nodes of the product itself are removed here; everything upstream (Reshape, Transpose, Gather, the old bias
            # constants) loses its last consumer and goes in the dead-code pass below.
            found.append((S, tq[1].input[0], r2, [mul, mm, add, S, av, t2, r2], None))
        if len(found) != len(net.blocks):
            print(f"[export] attention fusion skipped: found {len(found)} attention blocks, the net has {len(net.blocks)}")
            return False
        new_nodes, drop = {}, set()
        for i, (S, qkv, r2, nodes, bias_in) in enumerate(found):
            attn = net.blocks[i].attn
            bias = attn.rel_bias.detach()[:, attn.rel_index].unsqueeze(0).float().numpy()          # [1, H, T, T]
            bname = f"fz_mha_bias_{i}"
            g.initializer.append(numpy_helper.from_array(bias, bname))
            sname = f"fz_mha_split_{i}"
            g.initializer.append(numpy_helper.from_array(np.array([d, d, d], dtype=np.int64), sname))
            q, k, v = f"fz_mha_q_{i}", f"fz_mha_k_{i}", f"fz_mha_v_{i}"
            split = helper.make_node("Split", [qkv, sname], [q, k, v], name=f"fz_mha_split_node_{i}", axis=2)
            mha = helper.make_node("MultiHeadAttention", [q, k, v, "", "", bname], [r2.output[0]], name=f"fz_mha_node_{i}",
                                   domain="com.microsoft", num_heads=heads, scale=float(dh ** -0.5))
            new_nodes[id(r2)] = [split, mha]
            drop.update(id(n) for n in nodes)
        nodes_out = []
        for n in g.node:
            if id(n) in new_nodes:
                nodes_out.extend(new_nodes[id(n)])
            elif id(n) not in drop:
                nodes_out.append(n)
        # dead-code elimination (the shape-building nodes, the old bias gather) and unused initializers
        needed = {o.name for o in g.output}
        keep = []
        for n in reversed(nodes_out):
            if any(o in needed for o in n.output):
                keep.append(n)
                needed.update(x for x in n.input if x)
        keep.reverse()
        del g.node[:]
        g.node.extend(keep)
        used = {x for n in keep for x in n.input}
        kept_init = [t for t in g.initializer if t.name in used]
        del g.initializer[:]
        g.initializer.extend(kept_init)
        if not any(o.domain == "com.microsoft" for o in m.opset_import):
            m.opset_import.append(helper.make_opsetid("com.microsoft", 1))
        onnx.save(m, path)
        return True
    except Exception as e:      # noqa: BLE001 - an optimisation: the unfused graph stays valid
        print(f"[export] attention fusion skipped ({type(e).__name__}: {str(e)[:200]})")
        return False


def fp16_onnx(path, net, x=None):
    """Turns the weights and the arithmetic of the (fused) FP32 graph at `path` into FP16 in place, for the GPU engine: the
    T4's tensor cores run FP16 about 8 times faster than its FP32 units, and measured in the engine (T4, ORT 1.20.1, 16
    games) this is 4,965-5,044 nps against 1,865-2,164 for the fused FP32 graph. Inputs and outputs stay FP32 (Cast nodes at
    the two ends); the training weights (.pt) stay FP32 -- only this inference file is half precision.
    The traditional safety checks of FP16 inference, all done here:
      1. the conversion is checked on a GPU against the FP32 graph run on the CPU (exact reference), on `x` (real positions
         when the caller has them: the last training batch) or on synthetic positions;
      2. no NaN or infinity in any output (an FP16 overflow shows up as that);
      3. the move probabilities, the WDL and the moves-left number must stay within FP16_TOLERANCE of the FP32 ones;
      4. softmax and LayerNorm run inside ONNX Runtime's CUDA kernels, which accumulate in FP32.
    If anything fails -- no GPU / no onnxruntime-gpu to check with, a conversion error, a NaN, a difference over the tolerance --
    the FP32 file is left untouched and the reason is printed. Returns True if `path` now holds the FP16 graph."""
    mha = path + ".mha"
    made = []                      # temporary half-precision candidates, removed at the end
    try:
        import shutil
        import time
        import onnx
        import onnxruntime as ort
        from onnxruntime.transformers.onnx_model import OnnxModel
        if "CUDAExecutionProvider" not in ort.get_available_providers():
            print("[export] FP16 NOT used: this onnxruntime has no CUDA execution provider to check the half-precision graph "
                  "with (pip install onnxruntime-gpu on a GPU machine); the FP32 graph is kept")
            return False
        xs = check_inputs() if x is None else np.asarray(x, dtype=np.float32)
        ref = ort.InferenceSession(path, providers=["CPUExecutionProvider"]).run(["policy", "value", "mlh"], {"input": xs})
        # Candidates: the ordinary attention, and attention as ONE com.microsoft::MultiHeadAttention node per layer. Every candidate
        # must pass the checks; of those that do, the FASTER one on this GPU is kept (measured here, 20 runs of 64 positions):
        # on a T4 with ONNX Runtime 1.32 the fused node was slower (14.2 ms against 11.9 ms for a batch of 64), so it is never
        # assumed to be a win.
        candidates = [("ordinary attention", path)]
        if os.environ.get("FZ_ONNX_KHONG_MHA", "") != "1":          # FZ_ONNX_KHONG_MHA=1: do not even try the fused node
            shutil.copyfile(path, mha)
            if fuse_attention_onnx(mha, net):
                candidates.append(("fused attention", mha))
        timing_x = check_inputs(64, seed=9)
        passed = []
        for k, (label, src) in enumerate(candidates):
            tmp = f"{path}.fp16_{k}"
            made.append(tmp)
            try:
                om = OnnxModel(onnx.load(src))
                om.convert_float_to_float16(keep_io_types=True)
                om.save_model_to_file(tmp)
                sess = ort.InferenceSession(tmp, providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
                out = sess.run(["policy", "value", "mlh"], {"input": xs})
            except Exception as e:      # noqa: BLE001 - e.g. the fused node does not run on this onnxruntime: try the others
                print(f"[export] FP16 with {label}: failed ({type(e).__name__}: {str(e)[:160]})")
                continue
            diff = fp16_differences(ref, out)
            if diff is None:
                print(f"[export] FP16 with {label}: NaN or infinity in the outputs (overflow); not used")
                continue
            if any(d > t for d, t in zip(diff, FP16_TOLERANCE)):
                print(f"[export] FP16 with {label}: differs from FP32 by (policy TV, WDL, mlh) = "
                      f"({diff[0]:.4f}, {diff[1]:.4f}, {diff[2]:.3f}) > {FP16_TOLERANCE}; not used")
                continue
            for _ in range(5):
                sess.run(None, {"input": timing_x})
            t0 = time.time()
            for _ in range(20):
                sess.run(None, {"input": timing_x})
            passed.append(((time.time() - t0) / 20, label, tmp, diff))
        if not passed:
            print("[export] FP16 NOT used: no half-precision candidate passed the check; the FP32 graph is kept")
            return False
        dt, label, best, diff = min(passed)
        os.replace(best, path)
        others = ", ".join(f"{lb} {t * 1000:.1f} ms" for t, lb, _, _ in sorted(passed))
        print(f"[export] FP16 graph, {label} (weights and arithmetic in half precision, inputs/outputs FP32), checked on the GPU "
              f"against FP32 over {len(xs)} positions: policy TV {diff[0]:.1e}, |WDL| {diff[1]:.1e}, |mlh| {diff[2]:.1e} plies; "
              f"fastest of the checked candidates for a batch of 64 ({others})")
        return True
    except Exception as e:      # noqa: BLE001 - half precision is an optimisation: never lose the export because of it
        print(f"[export] FP16 skipped ({type(e).__name__}: {str(e)[:200]}); the FP32 graph is kept")
        return False
    finally:
        for f in made + [mha]:
            if os.path.exists(f):
                os.remove(f)


def export_onnx(net, path, fuse=True, fp16=False, sample=None):
    """FP32 ONNX with the three outputs the engine reads: policy (raw logits), value (softmaxed WDL), mlh.
    The new (dynamo) exporter first, as the plan chose; if it fails (say, a torch/onnxscript mismatch on
    the machine), the legacy TorchScript exporter -- the graph is made of basic operators, so both work.
    With `fuse` (the default, unless the environment sets FZ_ONNX_KHONG_GOP=1) the graph is then fused by fuse_onnx (about 30% more
    evaluations per second in the engine on a T4); the numbers stay the same to the tolerance in FUSE_TOLERANCE.
    With `fp16` (GPU machines; FZ_ONNX_FP16=0 in the environment turns it off) the graph is finally converted to half precision by
    fp16_onnx, which checks it and keeps the FP32 file when anything is off. `sample`: real input positions for that check."""
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
    if fuse and os.environ.get("FZ_ONNX_KHONG_GOP", "") != "1":
        fuse_onnx(path, net)
    if fp16 and os.environ.get("FZ_ONNX_FP16", "") != "0":
        return fp16_onnx(path, net, sample)
    return False


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
    # FP16 weights are only legitimate in a graph made by fp16_onnx (a GPU file, checked there); the I/O stays FP32.
    is16 = any(t.data_type == onnx.TensorProto.FLOAT16 for t in m.graph.initializer)
    assert m.graph.input[0].type.tensor_type.elem_type == onnx.TensorProto.FLOAT and all(
        o.type.tensor_type.elem_type == onnx.TensorProto.FLOAT for o in m.graph.output), "the graph's inputs/outputs must be FP32"
    assert not any(t.data_location == onnx.TensorProto.EXTERNAL for t in m.graph.initializer),         "the weights are in an external .data file; the .onnx alone (as uploaded to the release) would not load"
    assert not os.path.exists(path + ".data"), f"{path}.data exists: remove it, the .onnx must be self-contained"
    print(f"[verify] opset {opsets}, {len(m.graph.node)} nodes, {'FP16 weights, ' if is16 else ''}ops: "
          f"{sorted({n.op_type for n in m.graph.node})}")

    if is16:
        # Half precision runs on the GPU only (the CPU provider has no FP16 kernels for these operators).
        if "CUDAExecutionProvider" not in ort.get_available_providers():
            print("[verify] FP16 graph: no CUDA provider here -> the runtime check was done when it was exported (fp16_onnx)")
            print("[verify] PASS: ONNX I/O contract matches engine (policy=logits, value=softmax WDL, mlh=plies).")
            return
        sess = ort.InferenceSession(path, providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
    else:
        sess = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
    x = np.random.randn(2, NUM_PLANES, 10, 10).astype(np.float32)
    pol, val, mlh = sess.run(["policy", "value", "mlh"], {"input": x})
    assert pol.shape == (2, POLICY_SIZE), pol.shape
    assert val.shape == (2, 3), val.shape
    assert mlh.shape == (2, 1), mlh.shape
    vsum = val.sum(axis=1)
    assert np.allclose(vsum, 1.0, atol=2e-3 if is16 else 1e-4), f"value (WDL) must sum to 1, got {vsum}"
    # the batch axis is dynamic: another batch size must run too
    pol5, _, _ = sess.run(["policy", "value", "mlh"], {"input": np.random.randn(5, NUM_PLANES, 10, 10).astype(np.float32)})
    assert pol5.shape == (5, POLICY_SIZE), pol5.shape
    print(f"[verify] runtime OK: policy{pol.shape} value{val.shape} mlh{mlh.shape} value_sum={vsum}")
    if net is not None:
        # Same numbers from ONNX Runtime and PyTorch, on inputs shaped like real
        # planes (0/1 squares, scalar aux planes), not only the right shapes.
        xr = check_inputs(8)
        o_pol, o_val, o_mlh = sess.run(["policy", "value", "mlh"], {"input": xr})
        was_training = net.training
        net.eval()
        with torch.no_grad():
            t_pol, t_val, t_mlh = ExportNet(net)(torch.from_numpy(xr))
        net.train(was_training)
        if is16:
            # Half precision: judged by what the search uses (see fp16_differences), against the FP32 PyTorch net.
            diff = fp16_differences((t_pol.numpy(), t_val.numpy(), t_mlh.numpy()), (o_pol, o_val, o_mlh))
            print(f"[verify] FP16 onnx vs FP32 torch: policy TV {diff[0]:.1e}, max |WDL| {diff[1]:.1e}, max |mlh| {diff[2]:.1e}"
                  if diff else "[verify] FP16 onnx gives a NaN or an infinity")
            assert diff is not None and all(d <= t for d, t in zip(diff, FP16_TOLERANCE)), \
                "the FP16 .onnx does not compute what the PyTorch net does"
        else:
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
    ap.add_argument("--out", default="model_gen1.onnx",
                    help="the .pt checkpoint is always written next to it (same name); a name ending in .pt writes the checkpoint "
                         "only, any other name also exports the ONNX network of the engine's ONNX Runtime path")
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
                    help="mixed-precision FP16 training (the FairyZero runs, owner's decision 2026-11-20): FP32 master "
                         "weights and optimizer, FP16 matrix products (torch.autocast), softmax / layer norm / the three losses "
                         "in FP32, dynamic loss scaling (GradScaler), gradients clipped after unscaling (--grad-clip), "
                         "steps with an infinite/NaN gradient skipped and counted, the run stopped if they do not stop; "
                         "ignored on CPU")
    ap.add_argument("--onnx-fp16", action="store_true",
                    help="export the .onnx for the GPU engine in FP16 (inputs/outputs FP32), after checking on the GPU that "
                         "it gives the FP32 numbers (policy / WDL / mlh within a small tolerance, no NaN); otherwise the FP32 "
                         "graph is kept and the reason printed. Needs onnxruntime-gpu. FZ_ONNX_FP16=0 in the environment "
                         "turns it off")
    ap.add_argument("--sparse-cache", dest="sparse_cache", action="store_true", default=True,
                    help="cache policy targets sparsely to avoid Colab OOM (8.2.2); default ON")
    ap.add_argument("--dense-cache", dest="sparse_cache", action="store_false",
                    help="cache dense tensors instead (more RAM; the old behavior)")
    # T8.3 â€” extra hyperparameters (lczero-training parity).
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
    # #5 â€” more lczero-training-style knobs.
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
    ap.add_argument("--val-newest-games", type=int, default=0, metavar="N",
                    help="like --val-newest-gen, but the N NEWEST games by modification time (whatever generation) are "
                         "scored once with the STARTING weights, then trained on like every other game: none is held out "
                         "from training. In the continuous loop these are about the games played since the starting net "
                         "began its last training. Prints the seconds it took. Needs --val-frac 0; not with --val-newest-gen")
    ap.add_argument("--stats-newest-gen", action="store_true",
                    help="before training, print two statistics of the games of the newest generation "
                         "(highest games_gen<g> folder, every machine's games): the average number of pieces left "
                         "when a game ended, and how often the side that attacked more won (thong_ke_doi.py). "
                         "A failure only prints a warning")
    ap.add_argument("--value-per-game", type=int, default=0, metavar="K",
                    help="train the value head on only K positions drawn at random from each training game, drawn "
                         "again every run (a game of K positions or fewer: all of them; 0 = every position, the "
                         "default); the value loss is the mean over the drawn positions. Every position keeps its "
                         "policy and moves-left targets; the validation / scoring sets are unchanged. Cell 07: 21")
    ap.add_argument("--td-lambda", type=float, default=None, metavar="LAMBDA",
                    help="value target of the TRAINING positions = --td-z-weight x the game result + the rest x the "
                         "TD(LAMBDA) return over the later search values of the game (0..1; 1 = the result, 0 = the "
                         "next position's search value) instead of the qMix; --q-ratio then only sets the targets the "
                         "validation / scoring sets are scored against. Off by default. Cell 07: 0.8")
    ap.add_argument("--td-z-weight", type=float, default=0.5, metavar="W",
                    help="with --td-lambda: the share of the game result in the value target (0..1, default 0.5)")
    ap.add_argument("--mirror", action="store_true",
                    help="flip every training position left-right (files a<->j, policy to the mirrored moves) with "
                         "probability 1/2 each time it is drawn: the rules are left-right symmetric (no castling). "
                         "The validation / scoring sets are not flipped")
    ap.add_argument("--surprise-policy-beta", type=float, default=0.0, metavar="BETA",
                    help="weight each training position's POLICY loss by (1 - BETA) + BETA x min(S / mean S, "
                         "--surprise-cap), normalized to mean 1, S = policy_kld of a full search (the net that "
                         "played vs its search); mean and normalization per network that played (0 = off, the "
                         "default). The validation / scoring sets are unweighted. Cell 07: 0.5")
    ap.add_argument("--surprise-value-beta", type=float, default=0.0, metavar="BETA",
                    help="the same for the VALUE loss, S = KL(TD return || raw W/D/L eval of the net that played); "
                         "needs --td-lambda (0 = off, the default). Cell 07: 0.25")
    ap.add_argument("--surprise-cap", type=float, default=10.0, metavar="X",
                    help="cap of S / mean S in the surprise weights (>= 1, default 10)")
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
    if args.value_per_game < 0:
        sys.exit(f"--value-per-game must be >= 0, got {args.value_per_game}")
    if args.td_lambda is not None and not (0.0 <= args.td_lambda <= 1.0 and 0.0 <= args.td_z_weight <= 1.0):
        sys.exit(f"--td-lambda and --td-z-weight must be in [0, 1], got {args.td_lambda} and {args.td_z_weight}")
    if not (0.0 <= args.surprise_policy_beta <= 1.0 and 0.0 <= args.surprise_value_beta <= 1.0
            and args.surprise_cap >= 1.0):
        sys.exit("--surprise-policy-beta / --surprise-value-beta must be in [0, 1] and --surprise-cap >= 1")
    if args.surprise_value_beta > 0 and args.td_lambda is None:
        sys.exit("--surprise-value-beta measures the surprise against the TD return: it needs --td-lambda")
    if args.diff_focus and (args.surprise_policy_beta > 0 or args.surprise_value_beta > 0):
        sys.exit("--diff-focus and the surprise weights are two ways to favor surprising positions: use one")
    if args.val_newest_games < 0:
        sys.exit(f"--val-newest-games must be >= 0, got {args.val_newest_games}")
    if args.val_newest_games and args.val_frac > 0:
        sys.exit("--val-newest-games trains on every game: use it with --val-frac 0")
    if args.val_newest_games and args.val_newest_gen:
        sys.exit("--val-newest-games and --val-newest-gen both score the starting weights once: use one of them")
    games = list_games(args.data)
    mtimes = game_mtimes(games) if (args.val_frac > 0 or args.val_newest_games > 0) else [0.0] * len(games)
    train_games, val_games = split_games(games, args.val_frac, mtimes)
    if args.val_frac > 0 and not val_games:
        print(f"[val] {len(games)} game(s) are too few for --val-frac {args.val_frac}: "
              "no validation set")
    ds = FairyDataset(args.data, q_ratio=args.q_ratio, downsample_keep=args.downsample,
                      cache=not args.no_cache, diff_focus=args.diff_focus,
                      df_slope=args.df_slope, df_kld_w=args.df_kld_w, df_min=args.df_min,
                      sparse=args.sparse_cache, max_records=args.max_records,
                      games=train_games, label="train" if val_games else "", seed=args.seed,
                      packed=packed, value_per_game=args.value_per_game,
                      td_lambda=args.td_lambda, td_z_weight=args.td_z_weight,
                      surprise_policy_beta=args.surprise_policy_beta, surprise_value_beta=args.surprise_value_beta,
                      surprise_cap=args.surprise_cap)
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
    # --val-newest-games N: the same, for the N newest games by modification time (whatever generation they are).
    # No game is held out of training in either case.
    first_val = None
    if args.val_newest_gen or args.val_newest_games:
        t_build = time.time()
        if args.val_newest_gen:
            gen, newest = newest_generation(games)
            what, label = f"generation {gen}", f"newest generation {gen}"
            nothing = "[val] --val-newest-gen: no games_gen<g> folder in the data paths -- no score"
            never = "never trained on; trained on below"
        else:
            newest = newest_n_games(games, mtimes, args.val_newest_games)
            what, label = f"the {len(newest)} newest games", f"{len(newest)} newest games"
            nothing = "[val] --val-newest-games: no games -- no score"
            never = "newest by file time, normally never trained on; trained on below"
        if not newest:
            print(nothing)
        else:
            ds_first = FairyDataset(args.data, q_ratio=args.q_ratio, cache=not args.no_cache,
                                    sparse=args.sparse_cache, games=newest,
                                    label=label, packed=packed)
            first_val = (what, len(newest), len(ds_first), never, time.time() - t_build,
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

    # GradScaler = dynamic loss scaling, the standard guard of FP16 training (Micikevicius et al. 2018): the loss is
    # multiplied by a scale (starts 65536) so small gradients do not flush to zero in FP16; the gradients are divided back
    # before the optimizer sees them; a step whose gradient has an infinity / NaN is SKIPPED and the scale is halved; after
    # 2000 clean steps it doubles. A no-op when use_amp=False.
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
    amp_skipped = 0        # optimizer steps skipped because of an infinite / NaN gradient
    amp_streak = 0         # ... in a row
    amp_bad_loss = 0       # micro-batches whose loss itself was not finite
    guard_x = None         # first training batch (real positions), for the FP16 export check
    AMP_MAX_STREAK = 16    # 16 skipped steps in a row = the scale fell from 65536 to 1: something diverged, not an overflow
    print(f"[train] optimizer={args.optimizer} grad_clip={args.grad_clip} "
          f"lr_sched={'on' if use_lr_sched else f'const {args.lr}'} seed={args.seed}")
    if args.warmup_steps > 0:      # the schedule as the loop will apply it (optimizer steps, 1-based): first, last warmup, after
        print(f"[train] lr warmup {args.warmup_steps} steps: step 1 = {lr_for_step(0):.2e}, step {args.warmup_steps} = "
              f"{lr_for_step(args.warmup_steps - 1):.2e}, then {lr_for_step(args.warmup_steps):.2e}")
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
    if args.stats_newest_gen:
        try:
            import thong_ke_doi
            thong_ke_doi.newest_generation_report(args.data)
        except Exception as e:          # a statistic must never stop a training run
            print(f"[stats] WARNING: could not compute the statistics of the newest generation: {e!r}", flush=True)
    report("start weights", net)
    if first_val is not None:
        what, n_games, n_pos, never, secs_read, loader = first_val
        t_eval = time.time()
        vp, vv, vm = evaluate(net, loader, device, use_amp, cl)
        secs_score = time.time() - t_eval
        print(f"  [val] start weights on {what} (all {n_games} games, {n_pos} positions, "
              f"{never}): policy={vp:.4f} value={vv:.4f} mlh={vm:.4f}  "
              f"({secs_read + secs_score:.0f} s: {secs_read:.0f} s to read + {secs_score:.0f} s to score)", flush=True)
        del loader, first_val   # frees the scoring copy of those games
    # --mirror: which rows of each training batch are flipped, drawn on the training device from the run's seed
    # (the same --seed repeats a run exactly, also with --mirror).
    mirror_gen = None
    if args.mirror:
        mirror_gen = torch.Generator(device=device)
        mirror_gen.manual_seed(args.seed + 2)
        print("[train] mirror: every training position flipped left-right with probability 1/2 each time it is drawn")
    global_step = 0         # counts OPTIMIZER steps (after accumulation)
    micro = 0                # counts micro-batches
    stop = False
    opt.zero_grad(set_to_none=True)
    for epoch in range(1, args.epochs + 1):
        if stop:
            break
        net.train()
        tp = tv = tm = n = n_pol = n_val = 0.0
        in_swa = epoch >= swa_start
        for x, pi, val in device_batches(dl, device, cl):
            if mirror_gen is not None:
                x, pi = mirror_batch(x, pi, torch.rand(x.size(0), device=device, generator=mirror_gen) < 0.5)
            if use_lr_sched and not in_swa:        # custom schedule controls LR pre-SWA
                for g in opt.param_groups:
                    g["lr"] = lr_for_step(global_step)
            # autocast runs matmuls/convs in FP16 but keeps softmax/log_softmax in
            # FP32, so the masked policy CE (with -inf fills) stays numerically safe.
            with torch.autocast(device_type=device, enabled=use_amp):
                lp, lv, lm = compute_losses(net(x), pi, val)
                loss = (args.policy_weight * lp + args.value_weight * lv + args.mlh_weight * lm) / accum
            scaler.scale(loss).backward()
            if guard_x is None:
                guard_x = x[:FP16_CHECK_POSITIONS].detach().float().cpu().numpy()   # real positions for the export check
            bs = x.size(0)
            # The three losses and how many positions have a policy / value target, read back in ONE device sync.
            lp_v, lv_v, lm_v, n_has, n_v = torch.stack([
                lp.detach().float(), lv.detach().float(), lm.detach().float(),
                val[:, 4].sum().float(), has_value(val[:, :3]).sum().float()]).tolist()
            if use_amp and not all(math.isfinite(v) for v in (lp_v, lv_v, lm_v)):
                amp_bad_loss += 1                     # a forward overflow: its gradient is NaN, the scaler skips the step;
            else:                                     # keep the NaN out of the running means
                tp += lp_v * n_has; n_pol += n_has
                tv += lv_v * n_v; n_val += n_v
                tm += lm_v * bs; n += bs
            micro += 1
            if micro % accum == 0:                  # one optimizer step per `accum` micro-batches
                if args.grad_clip > 0:
                    scaler.unscale_(opt)            # clip the TRUE gradient, not the scaled one
                    torch.nn.utils.clip_grad_norm_(net.parameters(), args.grad_clip)
                scale_before = scaler.get_scale()
                scaler.step(opt)                    # skipped by the scaler if the gradient has an inf / NaN
                scaler.update()
                if use_amp and scaler.get_scale() < scale_before:
                    amp_skipped += 1
                    amp_streak += 1
                    if amp_streak >= AMP_MAX_STREAK:
                        sys.exit(f"[amp] {amp_streak} optimizer steps in a row had an infinite/NaN gradient (loss scale "
                                 f"{scaler.get_scale():g}): the run diverged or a weight is NaN, not an FP16 overflow. "
                                 f"Stopped; nothing exported. Re-run without --amp to compare.")
                else:
                    amp_streak = 0
                opt.zero_grad(set_to_none=True)
                global_step += 1
                if lc0_swa and global_step % args.swa_steps == 0:
                    swa_net.update_parameters(net)
                if tail_swa and global_step in tail_set:
                    swa_net.update_parameters(net)
                if args.report_every and global_step % args.report_every == 0:
                    print(f"  step {global_step:7d}: policy_loss={tp/max(n_pol, 1.0):.4f}  value_loss={tv/max(n_val, 1.0):.4f}  "
                          f"mlh_loss={tm/max(n, 1.0):.4f}", flush=True)
                if args.save_every and global_step % args.save_every == 0:
                    ckpt = f"{os.path.splitext(args.out)[0]}_step{global_step}.pt"
                    torch.save(net.state_dict(), ckpt)
                    print(f"  [ckpt] {ckpt}")
                if args.max_steps and global_step >= args.max_steps:
                    stop = True; break
        if in_swa:
            swa_net.update_parameters(net)
            swa_sched.step()
        print(f"  epoch {epoch:3d}: policy_loss={tp/max(n_pol, 1.0):.4f}  value_loss={tv/max(n_val, 1.0):.4f}  mlh_loss={tm/max(n, 1.0):.4f}")
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
    if use_amp:
        print(f"[amp] {amp_skipped} of {global_step} optimizer steps skipped (a gradient had an infinity/NaN: the step is not "
              f"taken and the loss scale halves), {amp_bad_loss} micro-batches had a non-finite loss; final loss scale "
              f"{scaler.get_scale():g}")
        if amp_skipped > max(20, 0.1 * global_step):
            print(f"[amp] WARNING: more than 10% of the steps were skipped ({amp_skipped} of {global_step}); the run "
                  f"trained on fewer batches than planned. Compare with a run without --amp.")
    not_finite = [name for name, p in final.named_parameters() if not torch.isfinite(p).all()]
    if not_finite:                    # never export (or save as the next generation) a network with a NaN weight
        sys.exit(f"[train] {len(not_finite)} weight tensor(s) are not finite (e.g. {not_finite[0]}): nothing exported")
    ckpt = os.path.splitext(args.out)[0] + ".pt"
    torch.save(final.state_dict(), ckpt)
    print(f"[ckpt] saved {ckpt}")

    if args.out.endswith(".pt"):      # --out gen5.pt: the checkpoint alone (the CUDA runner reads .fzw made from it, lay_mang.py fzw)
        print("[export] --out is a .pt: no .onnx written (the engine's CUDA runner takes .fzw, python/lay_mang.py fzw)")
        return
    export_onnx(final, args.out, fp16=args.onnx_fp16, sample=guard_x)
    verify_onnx(args.out, final)


if __name__ == "__main__":
    main()
