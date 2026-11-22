"""Test of python/fzw.py: the .fzw file (write / read / damage detection), agreement with the C++ reader's header
(src/lczero_chess/neural/fz/fzw_format.h), and the CPU model of the CUDA runner against the FP32 network.

Run:  python test_fzw.py        (CPU only, a few seconds)
"""
import os
import re
import struct
import sys
import tempfile

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fzw  # noqa: E402
import lay_mang  # noqa: E402
from model import FairyNet  # noqa: E402
import train  # noqa: E402

PASS = FAIL = 0


def check(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [ok] {msg}")
    else:
        FAIL += 1
        print(f"  [FAIL] {msg}")


def small_net(d_model=64, layers=2, heads=2, seed=0):
    """A network with random (not the tiny training-start) weights, so that every stage of the runner matters."""
    torch.manual_seed(seed)
    net = FairyNet(d_model=d_model, layers=layers, heads=heads)
    with torch.no_grad():
        for p in net.parameters():
            p.add_(torch.randn_like(p) * 0.05)
    net.eval()
    return net


def test_header_matches_cpp():
    print("header and constants against fzw_format.h")
    h = open(os.path.join(HERE, "..", "src", "lczero_chess", "neural", "fz", "fzw_format.h"), encoding="utf-8").read()
    check(re.search(r"kFzwMagic\[4\] = \{'F', 'Z', 'W', '1'\}", h) is not None and fzw.MAGIC == b"FZW1", "magic FZW1")
    check(f"kFzwVersion = {fzw.VERSION}" in h, f"version {fzw.VERSION}")
    check(f"kFzwHeaderBytes = {fzw.HEADER_BYTES}" in h, f"header {fzw.HEADER_BYTES} bytes")
    check(f"kFzwEntryBytes = {fzw.ENTRY_BYTES}" in h, f"directory entry {fzw.ENTRY_BYTES} bytes")
    check("kFzwF16 = 0, kFzwF32 = 1" in h and (fzw.F16, fzw.F32) == (0, 1), "dtype codes")
    # the fields of FzwHeader, in order, as 32-bit words after the magic
    fields = re.search(r"struct FzwHeader \{(.*?)\};", h, re.S).group(1)
    names = re.findall(r"uint32_t ([^;]+);", fields)
    n32 = sum(len(n.split(",")) for n in names)
    check(n32 == 13 + 2, f"{n32} 32-bit header fields before total_size (13 layout values + n_tensors + crc32)")
    c = open(os.path.join(HERE, "..", "src", "lczero_chess", "neural", "fz", "fz_kernels.cuh"), encoding="utf-8").read()
    for name, val in (("kPlanes", 204), ("kPlanesPadded", fzw.PLANES_PADDED), ("kMoveTypes", 115), ("kValueTokens", fzw.VALUE_TOKENS),
                      ("kMlhTokens", fzw.MLH_TOKENS), ("kHidden", fzw.HIDDEN), ("kRelEntries", fzw.REL)):
        check(re.search(rf"\b{name} = {val}\b", c) is not None, f"{name} = {val} in fz_kernels.cuh")
    check(fzw.HEAD_COLS == 160, "head columns 160 (the C++ loader refuses another value)")


def test_roundtrip_and_damage():
    print("write / read / damage")
    net = small_net()
    sd = net.state_dict()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "n.fzw")
        fzw.write_fzw(path, sd)
        meta, w = fzw.read_fzw(path)
        check(meta["d"] == 64 and meta["layers"] == 2 and meta["heads"] == 2 and meta["ffn"] == 4, f"architecture read back {meta}")
        want = sd["blocks.1.attn.qkv.weight"].numpy().astype(np.float16).astype(np.float32)
        check(np.array_equal(w["b1.qkv.w"], want), "a weight matrix comes back as the FP16 value of the original")
        check(np.array_equal(w["b0.relbias"], sd["blocks.0.attn.rel_bias"].numpy()), "the relative-bias table is exact FP32")
        check(w["embed.w"].shape == (64, 208) and not w["embed.w"][:, 204:].any(), "embedding padded with 4 zero columns")
        want_posb = sd["pos_embed"].numpy().reshape(100, 64) + sd["embed.bias"].numpy()[None, :]
        check(np.allclose(w["embed.posb"], want_posb), "pos_embed + embed.bias folded into one table")
        check(w["head.w"].shape == (160, 64) and not w["head.w"][155:].any(), "head rows 155..159 are zero padding")
        check(np.array_equal(w["head.w"][115:147], sd["val_proj.weight"].numpy().astype(np.float16).astype(np.float32)),
              "value projection rows follow the 115 policy rows")
        offsets = [struct.unpack("<Q", open(path, "rb").read()[fzw.HEADER_BYTES + k * fzw.ENTRY_BYTES + 48:][:8])[0] for k in range(5)]
        check(all(o % 256 == 0 for o in offsets), "tensor data starts at multiples of 256 bytes")
        raw = bytearray(open(path, "rb").read())
        bad = bytearray(raw)
        bad[len(bad) // 2] ^= 0x40
        open(path + ".bad", "wb").write(bad)
        try:
            fzw.read_fzw(path + ".bad")
            check(False, "a flipped bit is detected")
        except ValueError as e:
            check("crc32" in str(e), "a flipped bit is detected (crc32)")
        open(path + ".cut", "wb").write(raw[:-1000])
        try:
            fzw.read_fzw(path + ".cut")
            check(False, "a truncated file is detected")
        except ValueError as e:
            check("truncated" in str(e), "a truncated file is detected")
        open(path + ".foreign", "wb").write(b"NOPE" + bytes(raw[4:]))
        try:
            fzw.read_fzw(path + ".foreign")
            check(False, "a foreign file is detected")
        except ValueError:
            check(True, "a foreign file (wrong magic) is detected")


def test_model_vs_fp32():
    print("the CPU model of the runner against the FP32 network (random weights, 2 layers)")
    net = small_net()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "n.fzw")
        fzw.write_fzw(path, net.state_dict())
        _, w = fzw.read_fzw(path)
    x = train.check_inputs(48, seed=3)
    ref = fzw.run_fp32(net, x)
    out = fzw.simulate(w, x)
    tv, wdl, mlh, logit = fzw.differences(ref, out)
    check(tv < 0.01 and wdl < 0.01 and mlh < 1.0, f"TV {tv:.5f}, |WDL| {wdl:.5f}, |mlh| {mlh:.4f}, |logit| {logit:.4f} (limits 0.01, 0.01, 1)")
    out_t = fzw.simulate(w, x, tanh_ff1=True)
    tv_t, wdl_t, mlh_t, _ = fzw.differences(ref, out_t)
    check(tv_t < 0.01 and wdl_t < 0.01 and mlh_t < 1.0, f"with the tanh GELU of the cuBLASLt epilogue: TV {tv_t:.5f}, |WDL| {wdl_t:.5f}")
    taps = {}
    fzw.simulate(w, x[:1], taps=taps)
    check({"x0", "embed", "x_in", "ln_in", "qkv0", "att0", "ln2_0", "ff0", "x1", "ln_final", "head", "wdlm"} <= set(taps),
          "every tap the engine writes (--test-fzcuda) exists in the model")
    check(taps["wdlm"].shape == (1, 4) and abs(taps["wdlm"][0, :3].sum() - 1) < 1e-5, "wdlm tap: a softmax and the moves left")
    # one position alone gives what it gives inside a batch (up to the last FP16 bit of a few values: the matrix product sums in
    # another order for another batch size, and a value on a rounding boundary then falls the other way -- logits move ~1e-4)
    one = fzw.simulate(w, x[5:6])
    check(np.allclose(one[0][0], out[0][5], atol=2e-3), "a position gives the same logits alone and in a batch (to FP16 rounding)")


def test_lay_mang_fzw():
    print("lay_mang.py fzw: .pt -> .fzw with the safety check")
    check(fzw.FP16_TOLERANCE == train.FP16_TOLERANCE, "same FP16 limits as train.py")
    check(np.array_equal(fzw.check_inputs(8, seed=2), train.check_inputs(8, seed=2)), "same check positions as train.py")
    net = small_net(seed=5)
    with tempfile.TemporaryDirectory() as tmp:
        pt, out = os.path.join(tmp, "gen3.pt"), os.path.join(tmp, "gen3.fzw")
        torch.save(net.state_dict(), pt)
        check(lay_mang.lay_fzw(out, "", False) == 0 and os.path.getsize(out) > 0, "converts a good net (exit code 0)")
        meta, _ = fzw.read_fzw(out)
        check(meta["d"] == 64 and meta["layers"] == 2, "the file is a readable .fzw of that net")
        mtime = os.path.getmtime(out)
        check(lay_mang.lay_fzw(out, "", False) == 0 and os.path.getmtime(out) == mtime, "an existing .fzw is left alone")
        # a net with a NaN weight must not give a file: the runner would feed NaN into the search
        bad = {k: v.clone() for k, v in net.state_dict().items()}
        bad["blocks.0.ff1.weight"][0, 0] = float("nan")
        bad_pt, bad_out = os.path.join(tmp, "gen4.pt"), os.path.join(tmp, "gen4.fzw")
        torch.save(bad, bad_pt)
        check(lay_mang.lay_fzw(bad_out, "", False) == 1 and not os.path.exists(bad_out) and not os.path.exists(bad_out + ".dang_chuyen"),
              "a net with a NaN weight: exit code 1, no file, no leftover")


def test_decode_planes():
    print("decoding the engine's positions file")
    # one position: plane 0 = squares a1 and b1 (Stockfish squares 0 and 1) with value 1; plane 200 = all squares, value 0.5
    rec = np.zeros(1, fzw.POSITION_RECORD)
    rec["planes"][0, 0]["lo"] = 0b11
    rec["planes"][0, 0]["v"] = 1.0
    rec["planes"][0, 200]["lo"] = ~np.uint64(0)
    rec["planes"][0, 200]["hi"] = ~np.uint64(0)
    rec["planes"][0, 200]["v"] = 0.5
    rec["planes"][0, 1]["hi"] = np.uint64(1) << np.uint64(60 - 64 + 0) if False else np.uint64(0)
    # square 12*5+3 = 63 (lo bit 63) and 12*5+4 = 64 (hi bit 0): ranks and files of the 12-wide layout
    rec["planes"][0, 2]["lo"] = np.uint64(1) << np.uint64(63)
    rec["planes"][0, 2]["hi"] = np.uint64(1)
    rec["planes"][0, 2]["v"] = 1.0
    p = fzw.decode_planes(rec.tobytes(), 1)
    check(p[0, 0, 0, 0] == 1 and p[0, 0, 0, 1] == 1 and p[0, 0].sum() == 2, "plane 0: squares (rank 1, files a and b)")
    check((p[0, 200] == 0.5).all(), "an all-squares plane fills the 10 x 10 board only")
    check(p[0, 2, 5, 3] == 1 and p[0, 2, 5, 4] == 1 and p[0, 2].sum() == 2, "squares 63 and 64 land on rank 6, files d and e")
    check(fzw.POSITION_RECORD.itemsize == 204 * 32 + 2 + 384 * 2, "record size 7298 bytes")


if __name__ == "__main__":
    test_header_matches_cpp()
    test_roundtrip_and_damage()
    test_model_vs_fp32()
    test_lay_mang_fzw()
    test_decode_planes()
    print("=" * 60)
    print(f"RESULT: {PASS} passed, {FAIL} failed")
    print("=" * 60)
    sys.exit(1 if FAIL else 0)
