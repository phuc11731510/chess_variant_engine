"""fzw.py -- the weight file (.fzw) of the CUDA network runner ("fzcuda"), and a CPU model of what the runner computes.

WHY. The engine used to run the network through ONNX Runtime (the .pt was turned into an .onnx on every Colab machine, which
needed pip onnx / onnxscript / onnxruntime-gpu, ~250 MB). The CUDA runner (src/lczero_chess/neural/fz/) reads the weights
straight from a small binary file made from the .pt by torch alone:

    python fzw.py convert gen17.pt gen17.fzw             # .pt -> .fzw  (about 10 MB, FP16 weights, FP32 norm / bias vectors)
    python fzw.py check   gen17.pt [--n 64] [--tanh]     # CPU model of the runner vs the FP32 net: how far off is FP16?
    python fzw.py ref  gen17.pt P P.ref                  # FP32 PyTorch outputs for the positions P that `custom_engine --fzcuda-dump P` wrote
    python fzw.py taps gen17.pt P                        # compare P.taps (the GPU's intermediate values, from --test-fzcuda) with the CPU model

THE FILE (little endian; the C++ reader is src/lczero_chess/neural/fz/fzw_format.h and must agree with this one):
    header, 128 bytes   magic "FZW1", version, d_model, layers, heads, ffn_mult, planes (204), planes_padded (208), squares (100),
                        move_types (115), head_cols (160), value_tokens (32), mlh_tokens (8), hidden (128), n_tensors,
                        crc32 of everything after the header, total size
    directory           n_tensors x 64 bytes: name[32], dtype (0 = FP16, 1 = FP32), rows, cols, pad, offset, nbytes
    data                every tensor at a multiple of 256 bytes; matrices row-major [rows, cols]

    A weight matrix is stored exactly as PyTorch keeps it, [out, in] row-major (cuBLASLt then reads it as the transposed
    operand without any repacking). What differs from the .pt:
      embed.w      [d, 208]     the 204 input planes padded with 4 zero columns (K must be a multiple of 8 for tensor cores)
      embed.posb   [100, d]     pos_embed + the bias of embed (one table added after the product)
      head.w       [160, d]     rows 0..114 policy | 115..146 value projection | 147..154 moves-left projection | 5 zero rows
      head.b       [160]        the matching biases (FP32)
      b<i>.relbias [H, 361]     the 19 x 19 relative-offset table of every head (the runner indexes it with the offset itself)

THE ARITHMETIC the runner does (and simulate() below repeats, so the FP16 error can be measured without a GPU): all matrices
and the residual stream are FP16, every product accumulates in FP32, LayerNorm / softmax / GELU are evaluated in FP32. Where a
value is rounded to FP16 is part of the contract (see the numbered comments in simulate()).
"""
import argparse
import os
import struct
import sys
import zlib

import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nn_layout import (AUX_BASE, MOVE_TYPES, NUM_PLANES, SQUARES)  # noqa: E402

MAGIC = b"FZW1"
VERSION = 1
HEADER_BYTES = 128
ENTRY_BYTES = 64
ALIGN = 256
PLANES_PADDED = 208            # NUM_PLANES (204) rounded up to a multiple of 8
HEAD_COLS = 160                # policy (115) + value tokens (32) + moves-left tokens (8) = 155, padded to a multiple of 32
VALUE_TOKENS = 32
MLH_TOKENS = 8
HIDDEN = 128
REL = 19 * 19                  # the relative-offset table of one head
LN_EPS = 1e-5
F16, F32 = 0, 1
FP16_TOLERANCE = (0.01, 0.01, 1.0)   # total variation of softmax(policy), |WDL|, |moves left| in plies: train.FP16_TOLERANCE (test_fzw.py checks)
CHECK_POSITIONS = 32

assert NUM_PLANES == 204 and PLANES_PADDED % 8 == 0
assert MOVE_TYPES + VALUE_TOKENS + MLH_TOKENS <= HEAD_COLS


# ---------------------------------------------------------------------------------------------------------------------
# writing and reading
# ---------------------------------------------------------------------------------------------------------------------

def _np(t):
    return t.detach().cpu().numpy().astype(np.float32)


def pack_tensors(sd):
    """The (name, dtype, 2-D numpy array) list of the file, from the state_dict of a FairyNet (model.py)."""
    d = sd["embed.weight"].shape[0]
    layers = 1 + max(int(k.split(".")[1]) for k in sd if k.startswith("blocks."))
    heads = sd["blocks.0.attn.rel_bias"].shape[0]
    ffn = sd["blocks.0.ff1.weight"].shape[0] // d
    if d % 64 or d // heads != 32:
        raise ValueError(f"the CUDA runner needs d_model a multiple of 64 and 32 per head (got d_model {d}, {heads} heads)")
    out = []

    def add(name, dtype, a):
        a = np.ascontiguousarray(_np(a) if hasattr(a, "detach") else a, dtype=np.float32)
        out.append((name, dtype, a.reshape(1, -1) if a.ndim == 1 else a))

    emb = np.zeros((d, PLANES_PADDED), np.float32)
    emb[:, :NUM_PLANES] = _np(sd["embed.weight"])
    add("embed.w", F16, emb)
    add("embed.posb", F32, _np(sd["pos_embed"]).reshape(SQUARES, d) + _np(sd["embed.bias"])[None, :])
    for i in range(layers):
        p = f"blocks.{i}."
        add(f"b{i}.ln1.g", F32, sd[p + "ln1.weight"])
        add(f"b{i}.ln1.b", F32, sd[p + "ln1.bias"])
        add(f"b{i}.qkv.w", F16, sd[p + "attn.qkv.weight"])
        add(f"b{i}.qkv.b", F16, sd[p + "attn.qkv.bias"])
        add(f"b{i}.relbias", F32, sd[p + "attn.rel_bias"])
        add(f"b{i}.proj.w", F16, sd[p + "attn.proj.weight"])
        add(f"b{i}.proj.b", F32, sd[p + "attn.proj.bias"])
        add(f"b{i}.ln2.g", F32, sd[p + "ln2.weight"])
        add(f"b{i}.ln2.b", F32, sd[p + "ln2.bias"])
        add(f"b{i}.ff1.w", F16, sd[p + "ff1.weight"])
        add(f"b{i}.ff1.b", F16, sd[p + "ff1.bias"])
        add(f"b{i}.ff2.w", F16, sd[p + "ff2.weight"])
        add(f"b{i}.ff2.b", F32, sd[p + "ff2.bias"])
    add("final.ln.g", F32, sd["final_ln.weight"])
    add("final.ln.b", F32, sd["final_ln.bias"])
    hw = np.zeros((HEAD_COLS, d), np.float32)
    hb = np.zeros((HEAD_COLS,), np.float32)
    o = 0
    for w, b in (("pol_head", MOVE_TYPES), ("val_proj", VALUE_TOKENS), ("mlh_proj", MLH_TOKENS)):
        hw[o:o + b] = _np(sd[w + ".weight"])
        hb[o:o + b] = _np(sd[w + ".bias"])
        o += b
    add("head.w", F16, hw)
    add("head.b", F32, hb)
    add("val.fc1.w", F16, sd["val_fc1.weight"])
    add("val.fc1.b", F32, sd["val_fc1.bias"])
    add("val.fc2.w", F32, sd["val_fc2.weight"])
    add("val.fc2.b", F32, sd["val_fc2.bias"])
    add("mlh.fc1.w", F16, sd["mlh_fc1.weight"])
    add("mlh.fc1.b", F32, sd["mlh_fc1.bias"])
    add("mlh.fc2.w", F32, sd["mlh_fc2.weight"])
    add("mlh.fc2.b", F32, sd["mlh_fc2.bias"])
    return (d, layers, heads, ffn), out


def write_fzw(path, sd):
    (d, layers, heads, ffn), tensors = pack_tensors(sd)
    n = len(tensors)
    off = HEADER_BYTES + n * ENTRY_BYTES
    entries, blobs = [], []
    for name, dtype, a in tensors:
        off = (off + ALIGN - 1) // ALIGN * ALIGN
        raw = (a.astype(np.float16) if dtype == F16 else a.astype(np.float32)).tobytes()
        entries.append(struct.pack("<32sIIIIQQ", name.encode(), dtype, a.shape[0], a.shape[1], 0, off, len(raw)))
        blobs.append((off, raw))
        off += len(raw)
    body = bytearray(off - HEADER_BYTES)
    body[:n * ENTRY_BYTES] = b"".join(entries)
    for o, raw in blobs:
        body[o - HEADER_BYTES:o - HEADER_BYTES + len(raw)] = raw
    head = struct.pack("<4s13I", MAGIC, VERSION, d, layers, heads, ffn, NUM_PLANES, PLANES_PADDED, SQUARES, MOVE_TYPES,
                       HEAD_COLS, VALUE_TOKENS, MLH_TOKENS, HIDDEN)
    head += struct.pack("<II", n, zlib.crc32(bytes(body)) & 0xFFFFFFFF) + struct.pack("<Q", HEADER_BYTES + len(body))
    head = head.ljust(HEADER_BYTES, b"\0")
    tmp = path + ".dang_ghi"
    with open(tmp, "wb") as f:
        f.write(head)
        f.write(body)
    os.replace(tmp, path)


def read_fzw(path):
    """({'d','layers','heads','ffn'}, {name: float32 array}) -- the FP16 tensors come back as float32 holding the FP16 values."""
    raw = open(path, "rb").read()
    if raw[:4] != MAGIC:
        raise ValueError("not a .fzw file")
    f = struct.unpack("<4s13I", raw[:56])
    n, crc, total = struct.unpack("<IIQ", raw[56:72])
    if total != len(raw):
        raise ValueError(f"truncated: {len(raw)} bytes, the header says {total}")
    if zlib.crc32(raw[HEADER_BYTES:]) & 0xFFFFFFFF != crc:
        raise ValueError("crc32 mismatch")
    meta = dict(version=f[1], d=f[2], layers=f[3], heads=f[4], ffn=f[5])
    tensors = {}
    for k in range(n):
        name, dtype, r, c, _, off, nb = struct.unpack("<32sIIIIQQ", raw[HEADER_BYTES + k * ENTRY_BYTES:HEADER_BYTES + (k + 1) * ENTRY_BYTES])
        a = np.frombuffer(raw, np.float16 if dtype == F16 else np.float32, r * c, off).reshape(r, c)
        tensors[name.rstrip(b"\0").decode()] = a.astype(np.float32)
    return meta, tensors


# ---------------------------------------------------------------------------------------------------------------------
# the CPU model of the runner
# ---------------------------------------------------------------------------------------------------------------------

def _h(t):
    """Round to FP16 (and back to float32): a value the runner stores in half precision."""
    return t.half().float()


def _layernorm(s, g, b):
    mu = s.mean(-1, keepdim=True)
    var = ((s - mu) ** 2).mean(-1, keepdim=True)
    return (s - mu) * torch.rsqrt(var + LN_EPS) * g + b


def _gelu(x, tanh):
    return F.gelu(x, approximate="tanh" if tanh else "none")


def rel_index():
    r = np.arange(SQUARES) // 10
    f = np.arange(SQUARES) % 10
    return ((r[None, :] - r[:, None] + 9) * 19 + (f[None, :] - f[:, None] + 9)).astype(np.int64)


def simulate(w, planes, tanh_ff1=False, taps=None):
    """What the runner computes for planes [B, 204, 10, 10] (float32): (policy logits [B, 11500], WDL [B, 3], moves left [B, 1]).
    Every 'round to FP16' below is a place where the runner keeps a half-precision value in memory. `taps` (a dict, optional)
    receives the intermediate values of the first position under the names the engine's --test-fzcuda writes to P.taps."""
    def tap(name, t):
        if taps is not None:
            taps[name] = t[0].numpy() if t.dim() > 1 else t.numpy()
    B = planes.shape[0]
    d = w["embed.w"].shape[0]
    layers = 1 + max(int(k[1:].split(".")[0]) for k in w if k.startswith("b") and k[1].isdigit())
    heads = w["b0.relbias"].shape[0]
    dh = d // heads
    T = {k: torch.from_numpy(v) for k, v in w.items()}
    x0 = torch.from_numpy(np.ascontiguousarray(planes, np.float32)).flatten(2).transpose(1, 2)            # [B, 100, 204]
    x0 = _h(F.pad(x0, (0, PLANES_PADDED - NUM_PLANES)))                                  # (1) input planes in FP16
    tap("x0", x0)
    e = _h(x0 @ T["embed.w"].T)                                                                            # (2) embedding product
    tap("embed", e)
    s = e + T["embed.posb"]
    x = _h(s)                                                                                              # (3) residual stream
    ln = _h(_layernorm(s, T["b0.ln1.g"], T["b0.ln1.b"]))                                                   # (4) LayerNorm output
    tap("x_in", x)
    tap("ln_in", ln)
    idx = torch.from_numpy(rel_index())
    for i in range(layers):
        p = f"b{i}."
        qkv = _h(ln @ T[p + "qkv.w"].T + T[p + "qkv.b"])                                                   # (5) qkv product + bias
        if i == 0:
            tap("qkv0", qkv)
        q, k, v = qkv.reshape(B, SQUARES, 3, heads, dh).permute(2, 0, 3, 1, 4)                             # [B, H, T, dh]
        sc = (q @ k.transpose(-1, -2)) / np.sqrt(dh) + T[p + "relbias"][:, idx][None]                      # scores: FP32
        pe = torch.exp(sc - sc.amax(-1, keepdim=True))
        den = pe.sum(-1, keepdim=True)
        o = _h((_h(pe) @ v) / den)                                                                         # (6) P in FP16, O in FP16
        o = o.transpose(1, 2).reshape(B, SQUARES, d)
        if i == 0:
            tap("att0", o)
        y = _h(o @ T[p + "proj.w"].T)                                                                      # (7) attention output product
        s = x + y + T[p + "proj.b"]
        x = _h(s)
        ln = _h(_layernorm(s, T[p + "ln2.g"], T[p + "ln2.b"]))
        if i == 0:
            tap("ln2_0", ln)
        a = _h(_gelu(ln @ T[p + "ff1.w"].T + T[p + "ff1.b"], tanh_ff1))                                    # (8) ff1 product + bias + GELU
        if i == 0:
            tap("ff0", a)
        y = _h(a @ T[p + "ff2.w"].T)                                                                       # (9) ff2 product
        s = x + y + T[p + "ff2.b"]
        x = _h(s)
        g, b = ((T[f"b{i + 1}.ln1.g"], T[f"b{i + 1}.ln1.b"]) if i + 1 < layers else (T["final.ln.g"], T["final.ln.b"]))
        ln = _h(_layernorm(s, g, b))
        if i == 0:
            tap("x1", x)
    tap("ln_final", ln)
    hh = ln @ T["head.w"].T + T["head.b"]                                                                  # [B, 100, 160], FP32
    tap("head", hh)
    pol = hh[..., :MOVE_TYPES].transpose(1, 2).reshape(B, SQUARES * MOVE_TYPES)                            # type * 100 + square
    vt = _h(_gelu(hh[..., MOVE_TYPES:MOVE_TYPES + VALUE_TOKENS], False)).reshape(B, SQUARES * VALUE_TOKENS)       # (10)
    mt = _h(_gelu(hh[..., MOVE_TYPES + VALUE_TOKENS:MOVE_TYPES + VALUE_TOKENS + MLH_TOKENS], False)).reshape(B, SQUARES * MLH_TOKENS)
    va = _gelu(vt @ T["val.fc1.w"].T + T["val.fc1.b"], False)                                              # FP32 from here on
    ma = _gelu(mt @ T["mlh.fc1.w"].T + T["mlh.fc1.b"], False)
    wdl = torch.softmax(va @ T["val.fc2.w"].T + T["val.fc2.b"], dim=1)
    mlh = ma @ T["mlh.fc2.w"].T + T["mlh.fc2.b"]
    if taps is not None:
        taps["wdlm"] = torch.cat([wdl[0], mlh[0]]).numpy().reshape(1, 4)
    return pol.numpy(), wdl.numpy(), mlh.numpy()


# ---------------------------------------------------------------------------------------------------------------------
# comparison with the FP32 net, positions the engine dumped, command line
# ---------------------------------------------------------------------------------------------------------------------

def check_inputs(n=CHECK_POSITIONS, seed=0):
    """n synthetic input positions shaped like real ones (sparse 0/1 piece planes, scalar auxiliary planes): train.check_inputs."""
    rng = np.random.default_rng(seed)
    x = (rng.random((n, NUM_PLANES, 10, 10)) < 0.08).astype(np.float32)
    x[:, AUX_BASE:] = rng.random((n, NUM_PLANES - AUX_BASE, 1, 1)).astype(np.float32)
    return x


def load_net(pt):
    from model import FairyNet
    sd = torch.load(pt, map_location="cpu")
    d = sd["embed.weight"].shape[0]
    layers = 1 + max(int(k.split(".")[1]) for k in sd if k.startswith("blocks."))
    heads = sd["blocks.0.attn.rel_bias"].shape[0]
    net = FairyNet(d_model=d, layers=layers, heads=heads)
    net.load_state_dict(sd)
    net.eval()
    return sd, net


def run_fp32(net, planes):
    with torch.no_grad():
        p, v, m = net(torch.from_numpy(np.ascontiguousarray(planes, np.float32)))
        return p.numpy(), torch.softmax(v, 1).numpy(), m.numpy()


def differences(ref, out):
    """(max total variation of softmax(policy), max |WDL|, max |mlh|, worst policy logit) between two (policy, wdl, mlh)."""
    def sm(a):
        e = np.exp(a - a.max(1, keepdims=True))
        return e / e.sum(1, keepdims=True)
    tv = 0.5 * np.abs(sm(ref[0].astype(np.float64)) - sm(out[0].astype(np.float64))).sum(1).max()
    return float(tv), float(np.abs(ref[1] - out[1]).max()), float(np.abs(ref[2] - out[2]).max()), float(np.abs(ref[0] - out[0]).max())


POSITION_RECORD = np.dtype([("planes", [("lo", "<u8"), ("hi", "<u8"), ("v", "<f4"), ("pad", "<f4", (3,))], (NUM_PLANES,)),
                            ("count", "<u2"), ("index", "<u2", (384,))])    # what `custom_engine --fzcuda-dump` writes: 7298 bytes


def decode_planes(raw, n):
    """The first n positions of a positions file -> [n, 204, 10, 10] float32 (what UnpackInputPlanes would give the ONNX net)."""
    a = np.frombuffer(raw, POSITION_RECORD, n)["planes"]
    out = np.zeros((n, NUM_PLANES, 10, 10), np.float32)
    for r in range(10):
        for f in range(10):
            b = r * 12 + f                       # Stockfish square: 12 files per rank
            bit = ((a["hi"] >> np.uint64(b - 64)) & np.uint64(1)) if b >= 64 else ((a["lo"] >> np.uint64(b)) & np.uint64(1))
            out[:, :, r, f] = np.where(bit == 1, a["v"], 0.0)
    return out


def cmd_check(a):
    sd, net = load_net(a.pt)
    meta, w = read_fzw(a.fzw) if a.fzw else (None, None)
    if w is None:
        tmp = a.pt + ".tmp.fzw"
        write_fzw(tmp, sd)
        meta, w = read_fzw(tmp)
        os.remove(tmp)
    x = check_inputs(a.n, seed=1)
    ref = run_fp32(net, x)
    for tanh in ((False, True) if a.tanh else (False,)):
        out = simulate(w, x, tanh_ff1=tanh)
        tv, wdl, mlh, lg = differences(ref, out)
        print(f"ff1 GELU {'tanh' if tanh else 'erf '}: TV policy {tv:.5f} | |WDL| {wdl:.5f} | |mlh| {mlh:.4f} plies | |logit| {lg:.4f}"
              f"   (limits {FP16_TOLERANCE})")


def cmd_ref(a):
    sd, net = load_net(a.pt)
    raw = open(a.positions, "rb").read()
    n = len(raw) // POSITION_RECORD.itemsize
    planes = decode_planes(raw, n)
    pol, wdl, mlh = run_fp32(net, planes)
    with open(a.out, "wb") as f:
        f.write(struct.pack("<II", n, 0))
        f.write(pol.astype("<f4").tobytes() + wdl.astype("<f4").tobytes() + mlh.astype("<f4").tobytes())
    print(f"[fzw] {n} positions -> {a.out} (FP32 PyTorch reference: policy [n,11500], WDL [n,3], mlh [n,1])")


def cmd_taps(a):
    """Compares P.taps (the GPU's intermediate values of the first position) with the CPU model, stage by stage: the first
    stage that leaves the CPU model is where the GPU code is wrong."""
    sd, net = load_net(a.pt)
    tmp = a.pt + ".tmp.fzw"
    write_fzw(tmp, sd)
    meta, w = read_fzw(tmp)
    os.remove(tmp)
    raw = open(a.positions, "rb").read()
    planes = decode_planes(raw, 1)
    taps = {}
    simulate(w, planes, tanh_ff1=a.tanh, taps=taps)
    data = open(a.positions + ".taps", "rb").read()
    off, bad = 0, 0
    print(f"{'stage':10s} {'shape':>10s} {'max |err|':>11s} {'mean |err|':>11s} {'max |ref|':>11s}  verdict")
    while off < len(data):
        name = data[off:off + 16].split(b"\0")[0].decode()
        rows, cols = struct.unpack("<II", data[off + 16:off + 24])
        got = np.frombuffer(data, "<f4", rows * cols, off + 24).reshape(rows, cols)
        off += 24 + rows * cols * 4
        want = taps.get(name)
        if want is None:
            print(f"{name:10s} (not in the CPU model)")
            continue
        want = want.reshape(rows, cols)
        err = np.abs(got.astype(np.float64) - want)
        scale = max(float(np.abs(want).max()), 1e-6)
        ok = float(err.max()) <= 4e-3 * max(scale, 1.0) and np.isfinite(got).all()
        bad += not ok
        print(f"{name:10s} {rows:4d}x{cols:<5d} {err.max():11.3e} {err.mean():11.3e} {scale:11.3e}  {'ok' if ok else 'DIFFERS'}")
    print("all stages agree with the CPU model" if not bad else f"{bad} stage(s) differ: the first one listed is where to look")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("convert")
    c.add_argument("pt")
    c.add_argument("fzw")
    k = sub.add_parser("check")
    k.add_argument("pt")
    k.add_argument("--fzw", default="")
    k.add_argument("--n", type=int, default=64)
    k.add_argument("--tanh", action="store_true", help="also model the tanh GELU of the cuBLASLt epilogue")
    r = sub.add_parser("ref")
    r.add_argument("pt")
    r.add_argument("positions")
    r.add_argument("out")
    t = sub.add_parser("taps")
    t.add_argument("pt")
    t.add_argument("positions")
    t.add_argument("--tanh", action="store_true", help="the CPU model uses the tanh GELU of the cuBLASLt epilogue")
    a = ap.parse_args()
    if a.cmd == "convert":
        write_fzw(a.fzw, torch.load(a.pt, map_location="cpu"))
        print(f"[fzw] {a.pt} -> {a.fzw} ({os.path.getsize(a.fzw) / 1e6:.1f} MB)")
    elif a.cmd == "check":
        cmd_check(a)
    elif a.cmd == "ref":
        cmd_ref(a)
    else:
        cmd_taps(a)


if __name__ == "__main__":
    main()
