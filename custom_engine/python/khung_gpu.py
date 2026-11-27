# -*- coding: utf-8 -*-
"""Khung TFLite cho GPU của app Android (LiteRT, GPU delegate qua OpenCL): một tệp .tflite mẫu + bảng ghép, để app tự tạo
mạng GPU của mỗi đời từ gen<N>.pt (như khung_mang.py làm cho ONNX), không cần PyTorch / TensorFlow trên máy bảng.

Đồ thị khác khung ONNX ở chỗ GPU delegate chỉ nhận tensor <= 4 chiều và không nhận Gather: qkv được cắt bằng Slice, đầu
attention là [B,6,100,32], bảng thiên lệch vị trí tương đối được lấy sẵn thành hằng [1,6,100,100]. Lô cố định (GPU cần hình
cố định). onnx2tf đổi ONNX sang TFLite (đầu vào thành NHWC [B,10,10,204]); khi đổi, nó có thể chuyển vị hay cắt các trọng số,
nên bảng ghép được TÌM ra: dựng khung bằng trọng số dò (số ngẫu nhiên khác nhau ở mọi tensor), rồi với mỗi tensor của .pt và mỗi
phép biến đổi có thể (giữ nguyên, chuyển vị, cắt ba phần q/k/v, lấy bảng thiên lệch), tìm byte của nó trong tệp .tflite.
Kiểm cuối: vá khung bằng trọng số thật (đúng cách app làm) rồi so đầu ra TFLite (CPU) với khung ONNX chạy bằng ONNX Runtime.

Chạy trong môi trường có tensorflow + onnx2tf + ai-edge-litert + onnxruntime (không cần torch):
    python khung_gpu.py dung --lo 16 --kiem <thư mục khung ONNX đã đổi của một mạng thật, vd gen201_khung>
    python khung_gpu.py va --tu <thư mục khung ONNX của một mạng> --ra gen201_gpu.tflite   # vá như app (thử bằng adb)
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from khung_mang import _Do  # noqa: E402

ASSETS = os.path.normpath(os.path.join(HERE, "..", "..", "gui", "assets", "mang"))
NUM_PLANES, SQUARES, POLICY_SIZE = 204, 100, 11500
LN_CHIA = 32.0   # xem ln() trong dung_onnx


def rel_index():
    r, f = np.arange(SQUARES) // 10, np.arange(SQUARES) % 10
    return (r[None, :] - r[:, None] + 9) * 19 + (f[None, :] - f[:, None] + 9)


def doc_trong_so(thu_muc, bang):
    raw = open(os.path.join(thu_muc, bang["tep_trong_so"]), "rb").read()
    return {t["ten"]: np.frombuffer(raw, "<f4", t["so_byte"] // 4, t["vi_tri"]).reshape(t["hinh"]) for t in bang["tensor"]}


def dung_onnx(W, B, kt):
    d, heads, layers = kt["d_model"], kt["heads"], kt["layers"]
    dh = d // heads
    g, inits, idx = _Do(), [], rel_index()

    def w(name, arr):
        inits.append(numpy_helper.from_array(np.ascontiguousarray(arr, dtype=np.float32), name))
        return name

    def lin(x, p):
        return g.nut("Add", [g.nut("MatMul", [x, w(p + ".wT", W[p + ".weight"].T)]), w(p + ".b", W[p + ".bias"])])

    def ln(x, p):
        # LayerNorm viết tay, an toàn với FP16 của GPU (giới hạn 65504): dòng dư của gen201 lệch tới ~625 quanh trung bình
        # (phương sai ~2940 ở final_ln), nên bình phương / tổng 192 phần tử tràn FP16. Chia x cho LN_CHIA trước khi lấy
        # trung bình và bình phương: (x - m) / căn(v + eps) không đổi khi x, m chia cùng số và eps chia bình phương số đó.
        xs = g.nut("Mul", [x, g.hang(1.0 / LN_CHIA, np.float32)])
        ds = g.nut("Sub", [xs, g.nut("ReduceMean", [xs, g.hang([-1])], keepdims=1)])
        var = g.nut("ReduceMean", [g.nut("Mul", [ds, ds]), g.hang([-1])], keepdims=1)
        y = g.nut("Div", [ds, g.nut("Sqrt", [g.nut("Add", [var, g.hang(1e-5 / LN_CHIA ** 2, np.float32)])])])
        return g.nut("Add", [g.nut("Mul", [y, w(p + ".g", W[p + ".weight"])]), w(p + ".bb", W[p + ".bias"])])

    def gelu(x):
        e = g.nut("Erf", [g.nut("Mul", [x, g.hang(0.7071067811865476, np.float32)])])
        return g.nut("Mul", [g.nut("Mul", [x, g.hang(0.5, np.float32)]), g.nut("Add", [e, g.hang(1.0, np.float32)])])

    h = g.nut("Transpose", [g.nut("Reshape", ["input", g.hang([B, NUM_PLANES, SQUARES])])], perm=[0, 2, 1])
    h = g.nut("Add", [lin(h, "embed"), w("pos", W["pos_embed"])])
    for i in range(layers):
        p = f"blocks.{i}"
        qkv = lin(ln(h, p + ".ln1"), p + ".attn.qkv")

        def part(j):
            s = g.nut("Slice", [qkv, g.hang([j * d]), g.hang([(j + 1) * d]), g.hang([2])])
            return g.nut("Transpose", [g.nut("Reshape", [s, g.hang([B, SQUARES, heads, dh])])], perm=[0, 2, 1, 3])

        q, k, v = part(0), part(1), part(2)
        att = g.nut("MatMul", [g.nut("Mul", [q, g.hang(1.0 / np.sqrt(dh), np.float32)]), g.nut("Transpose", [k], perm=[0, 1, 3, 2])])
        att = g.nut("Softmax", [g.nut("Add", [att, w(p + ".relb", W[p + ".attn.rel_bias"][:, idx][None])])], axis=-1)
        o = g.nut("Reshape", [g.nut("Transpose", [g.nut("MatMul", [att, v])], perm=[0, 2, 1, 3]), g.hang([B, SQUARES, d])])
        h = g.nut("Add", [h, lin(o, p + ".attn.proj")])
        h = g.nut("Add", [h, lin(gelu(lin(ln(h, p + ".ln2"), p + ".ff1")), p + ".ff2")])
    h = ln(h, "final_ln")
    pol = g.nut("Reshape", [g.nut("Transpose", [lin(h, "pol_head")], perm=[0, 2, 1]), g.hang([B, POLICY_SIZE])])
    vv = g.nut("Reshape", [gelu(lin(h, "val_proj")), g.hang([B, 1, W["val_fc1.weight"].shape[1]])])
    vv = g.nut("Softmax", [g.nut("Reshape", [lin(gelu(lin(vv, "val_fc1")), "val_fc2"), g.hang([B, 3])])], axis=1)
    m = g.nut("Reshape", [gelu(lin(h, "mlh_proj")), g.hang([B, 1, W["mlh_fc1.weight"].shape[1]])])
    m = g.nut("Reshape", [lin(gelu(lin(m, "mlh_fc1")), "mlh_fc2"), g.hang([B, 1])])
    g.nodes += [helper.make_node("Identity", [x], [t], name="ra_" + t) for x, t in ((pol, "policy"), (vv, "value"), (m, "mlh"))]
    io = lambda t, *dims: helper.make_tensor_value_info(t, TensorProto.FLOAT, [B, *dims])
    graph = helper.make_graph(g.nodes, "fz_gpu", [io("input", NUM_PLANES, 10, 10)],
                              [io("policy", POLICY_SIZE), io("value", 3), io("mlh", 1)], initializer=g.consts + inits)
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 18)])
    model.ir_version = 8
    return model


def phep(ten, a, kt):
    """Các cách một tensor của .pt có thể nằm trong .tflite: [(mã phép, mảng)]."""
    d = kt["d_model"]
    out = [("id", a)]
    if a.ndim == 2:
        out.append(("T", a.T))
    if ten.endswith("attn.rel_bias"):
        out.append(("relb", a[:, rel_index()]))
    if ten.endswith("attn.qkv.weight"):
        for j in range(3):
            out += [(f"q{j}", a[j * d:(j + 1) * d]), (f"qT{j}", a[j * d:(j + 1) * d].T)]
    if ten.endswith("attn.qkv.bias"):
        out += [(f"q{j}", a[j * d:(j + 1) * d]) for j in range(3)]
    return out


def bien_doi(ma, a, d):
    """Áp mã phép lên tensor thật (đúng như app làm, lib/mang/doi_gpu.dart)."""
    if ma == "id":
        return a
    if ma == "T":
        return a.T
    if ma == "relb":
        return a[:, rel_index()]
    j = int(ma[-1])
    s = a[j * d:(j + 1) * d]
    return s.T if ma.startswith("qT") else s


def va(data, ghep, W, d):
    """Byte của .tflite mạng thật: khung [data] với mỗi chỗ ghép thay bằng tensor thật đã biến đổi (như app)."""
    buf = bytearray(data)
    for r in ghep:
        b = np.ascontiguousarray(bien_doi(r["phep"], W[r["ten"]], d), "<f4").tobytes()
        assert len(b) == r["so_byte"], r
        buf[r["vi_tri"]:r["vi_tri"] + r["so_byte"]] = b
    return bytes(buf)


def chay_onnx2tf(onnx_path, out_dir):
    subprocess.run([sys.executable, "-m", "onnx2tf", "-i", onnx_path, "-o", out_dir, "-n"], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = os.path.splitext(os.path.basename(onnx_path))[0]
    return os.path.join(out_dir, base + "_float32.tflite")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lenh", choices=["dung", "va"])
    ap.add_argument("--lo", type=int, default=16)
    ap.add_argument("--ra", default=ASSETS, help="dung: thư mục ghi khung; va: tệp .tflite ghi ra")
    ap.add_argument("--kiem", help="dung: thư mục khung ONNX + trong_so.bin của một mạng thật để kiểm")
    ap.add_argument("--tu", help="va: thư mục khung ONNX + trong_so.bin của mạng cần vá")
    args = ap.parse_args()
    bang = json.load(open(os.path.join(ASSETS, "bang_ghep.json"), encoding="utf-8"))
    kt = bang["kien_truc"]
    if args.lenh == "va":
        meta = json.load(open(os.path.join(ASSETS, f"bang_ghep_gpu_b{args.lo}.json"), encoding="utf-8"))
        data = open(os.path.join(ASSETS, meta["tep"]), "rb").read()
        open(args.ra, "wb").write(va(data, meta["ghep"], doc_trong_so(args.tu, bang), kt["d_model"]))
        print(f"[khung_gpu] {args.ra}")
        return
    if not args.kiem:
        sys.exit("dung cần --kiem")
    rng = np.random.default_rng(12345)
    probe = {t["ten"]: rng.standard_normal(t["hinh"]).astype(np.float32) * 0.05 + rng.uniform(-1, 1) for t in bang["tensor"]}
    tmp = tempfile.mkdtemp(prefix="fz_gpu_")
    try:
        p_onnx = os.path.join(tmp, f"khung_gpu_b{args.lo}.onnx")
        onnx.save(dung_onnx(probe, args.lo, kt), p_onnx)
        tfl = chay_onnx2tf(p_onnx, os.path.join(tmp, "tf"))
        data = open(tfl, "rb").read()
        ghep, thieu = [], []
        for t in bang["tensor"]:
            a = probe[t["ten"]]
            cho = {}
            for ma, arr in phep(t["ten"], a, kt):
                b = np.ascontiguousarray(arr, "<f4").tobytes()
                pos = data.find(b)
                while pos >= 0:   # hai phép ra cùng byte (vd [1,128] và chuyển vị của nó): giữ phép đầu tiên
                    cho.setdefault(pos, {"ten": t["ten"], "phep": ma, "vi_tri": pos, "so_byte": len(b)})
                    pos = data.find(b, pos + 1)
            cho = list(cho.values())
            # qkv bị cắt thành 3 phần: mỗi phần là một bản ghi; còn lại cần đúng một chỗ
            if not cho:
                thieu.append(t["ten"])
            ghep += cho
        if thieu:
            sys.exit(f"[khung_gpu] không tìm thấy trong .tflite: {thieu[:8]} ... ({len(thieu)})")
        # Một phần (vd q của qkv.bias) nằm TRONG bản đầy đủ của cùng tensor: vá bản đầy đủ là đủ, bỏ chỗ nằm trong.
        ghep.sort(key=lambda r: (r["vi_tri"], -r["so_byte"]))
        gon = []
        for r in ghep:
            if gon and r["vi_tri"] + r["so_byte"] <= gon[-1]["vi_tri"] + gon[-1]["so_byte"]:
                assert r["ten"] == gon[-1]["ten"], f"chỗ ghép của hai tensor lồng nhau: {gon[-1]} {r}"
                continue
            gon.append(r)
        ghep = gon
        for a, b in zip(ghep, ghep[1:]):
            assert a["vi_tri"] + a["so_byte"] <= b["vi_tri"], f"hai chỗ ghép chồng nhau: {a} {b}"
        os.makedirs(args.ra, exist_ok=True)
        ten_tfl = f"khung_gpu_b{args.lo}.tflite"
        # Byte của các chỗ ghép luôn bị app ghi đè: để 0 trong khung (APK nén được, ~22 MB trọng số dò -> gần như 0).
        khung = bytearray(data)
        for r in ghep:
            khung[r["vi_tri"]:r["vi_tri"] + r["so_byte"]] = bytes(r["so_byte"])
        open(os.path.join(args.ra, ten_tfl), "wb").write(khung)
        data = bytes(khung)
        meta = {"phien_ban": 1, "lo": args.lo, "kien_truc": kt, "tep": ten_tfl, "co_tep": len(data),
                "dau_vao": "NHWC [lo,10,10,204]", "ghep": ghep}
        json.dump(meta, open(os.path.join(args.ra, f"bang_ghep_gpu_b{args.lo}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"[khung_gpu] {ten_tfl}: {len(data)} byte, {len(ghep)} chỗ ghép cho {len(bang['tensor'])} tensor; "
              f"phép: {sorted({r['phep'] for r in ghep})}")

        # Kiểm: vá bằng trọng số thật đúng như app, chạy TFLite (CPU) và so với khung ONNX (ONNX Runtime).
        p_that = os.path.join(tmp, "that.tflite")
        open(p_that, "wb").write(va(data, ghep, doc_trong_so(args.kiem, bang), kt["d_model"]))
        import onnxruntime as ort
        from ai_edge_litert.interpreter import Interpreter
        x = (np.random.default_rng(0).random((args.lo, NUM_PLANES, 10, 10)) < 0.08).astype(np.float32)
        x[:, 192:] = np.random.default_rng(1).random((args.lo, 12, 1, 1))
        ref = ort.InferenceSession(os.path.join(args.kiem, "khung.onnx"), providers=["CPUExecutionProvider"]).run(
            ["policy", "value", "mlh"], {"input": x})
        it = Interpreter(model_path=p_that)
        it.allocate_tensors()
        it.set_tensor(it.get_input_details()[0]["index"], np.ascontiguousarray(x.transpose(0, 2, 3, 1)))
        it.invoke()
        got = {o["name"]: it.get_tensor(o["index"]) for o in it.get_output_details()}
        sm = lambda z: np.exp(z - z.max(1, keepdims=True)) / np.exp(z - z.max(1, keepdims=True)).sum(1, keepdims=True)
        tv = 0.5 * np.abs(sm(ref[0].astype(np.float64)) - sm(got["policy"].astype(np.float64))).sum(1).max()
        dv, dm = np.abs(ref[1] - got["value"]).max(), np.abs(ref[2] - got["mlh"]).max()
        print(f"[kiem] TFLite (vá như app) so với ONNX: khoảng cách biến phân chính sách {tv:.2e}, |WDL| {dv:.2e}, |mlh| {dm:.2e}")
        ok = tv < 1e-3 and dv < 1e-3 and dm < 0.05
        print("[kiem] ĐẠT" if ok else "[kiem] KHÔNG ĐẠT")
        sys.exit(0 if ok else 1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
