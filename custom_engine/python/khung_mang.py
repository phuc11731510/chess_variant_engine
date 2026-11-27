# -*- coding: utf-8 -*-
"""Khung mạng cho app Android: một .onnx CHỈ có đồ thị, mọi trọng số nằm ở tệp ngoài `trong_so.bin`.

Release NN_Model chỉ giữ gen<N>.pt; máy bảng không có PyTorch. App tự đổi .pt sang dạng engine chạy được bằng cách
chép nguyên byte của từng tensor trong .pt vào `trong_so.bin` theo `bang_ghep.json`, rồi đặt cạnh một bản sao của khung.

Đồ thị dựng tay bằng onnx.helper (không qua bộ xuất của torch) để mỗi trọng số của khung là ĐÚNG MỘT tensor của
state_dict, cùng tên, cùng hình dạng, cùng byte (float32, thứ tự hàng). Phép chuyển vị của Linear và phép lấy bảng
thiên lệch vị trí tương đối là nút trong đồ thị; ONNX Runtime gấp các nút hằng đó lúc nạp (tối ưu mức cơ bản, chạy trước khi
chia đồ thị cho NNAPI / XNNPACK), nên lúc chạy không tốn gì thêm.

    python khung_mang.py dung   [--ra ../../gui/assets/mang]            # viết khung.onnx + bang_ghep.json
    python khung_mang.py kiem   gen201.pt [--khung ../../gui/assets/mang] # đổi gen201.pt như app, so với PyTorch

Kiến trúc cố định (model.FairyNet mặc định: d_model 192, 10 lớp, 6 đầu, FFN x4). .pt lệch hình dạng thì app báo lỗi.
"""
import argparse
import json
import math
import os
import sys

import numpy as np
import onnx
from onnx import TensorProto, helper

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import FairyNet, _relative_index  # noqa: E402
from nn_layout import NUM_PLANES, POLICY_SIZE, SQUARES  # noqa: E402

OPSET = 18                      # như train.ONNX_OPSET: ONNX Runtime 1.18 của app hiểu tới opset 21
TEP_TRONG_SO = "trong_so.bin"
CANH = 64                       # mỗi tensor bắt đầu ở vị trí chia hết cho 64 byte
PHIEN_BAN = 1
MAC_DINH_RA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "gui", "assets", "mang"))


def bang_tensor(net):
    """[(tên, hình dạng)] theo đúng thứ tự state_dict, và vị trí byte của từng tensor trong trong_so.bin."""
    sd = net.state_dict()
    bang, vi_tri = [], 0
    for ten, t in sd.items():
        assert t.dtype.is_floating_point and t.element_size() == 4, f"{ten}: {t.dtype}"
        so_byte = t.numel() * 4
        bang.append({"ten": ten, "hinh": list(t.shape), "vi_tri": vi_tri, "so_byte": so_byte})
        vi_tri = (vi_tri + so_byte + CANH - 1) // CANH * CANH
    return bang, vi_tri


class _Do:
    """Bộ dựng đồ thị: mỗi phép thêm một nút, tên trung gian tự sinh."""

    def __init__(self):
        self.nodes, self.consts, self._n = [], [], 0

    def ten(self, goi=""):
        self._n += 1
        return f"t{self._n}{'_' + goi if goi else ''}"

    def nut(self, op, vao, goi="", **attr):
        """Mỗi nút có tên riêng: ORT đặt tên nút gộp theo tên nút gốc, nút không tên thì các nút gộp trùng tên."""
        ra = self.ten(goi or op.lower())
        self.nodes.append(helper.make_node(op, vao, [ra], name="n_" + ra, **attr))
        return ra

    def hang(self, gia_tri, kieu=np.int64):
        ten = self.ten("c")
        self.consts.append(onnx.numpy_helper.from_array(np.asarray(gia_tri, dtype=kieu), ten))
        return ten

    def linear(self, x, goc):
        """x @ W^T + b với W [ra, vào] (cách lưu của nn.Linear): chuyển vị là nút hằng, ORT gấp lúc nạp."""
        wt = self.nut("Transpose", [goc + ".weight"], "wt", perm=[1, 0])
        return self.nut("Add", [self.nut("MatMul", [x, wt]), goc + ".bias"])

    def gelu(self, x):
        """GELU chính xác như F.gelu mặc định: 0,5 x (1 + erf(x / căn 2))."""
        e = self.nut("Erf", [self.nut("Mul", [x, self.hang(1.0 / math.sqrt(2.0), np.float32)])])
        return self.nut("Mul", [self.nut("Mul", [x, self.hang(0.5, np.float32)]),
                                self.nut("Add", [e, self.hang(1.0, np.float32)])])

    def ln(self, x, goc):
        return self.nut("LayerNormalization", [x, goc + ".weight", goc + ".bias"], "ln", axis=-1, epsilon=1e-5)


def dung_do_thi(d_model=192, layers=10, heads=6):
    net = FairyNet(d_model=d_model, layers=layers, heads=heads)
    bang, tong = bang_tensor(net)
    dh = d_model // heads
    g = _Do()
    chi_so = g.hang(_relative_index().numpy())                                   # [100,100] int64
    h = g.nut("Transpose", [g.nut("Reshape", ["input", g.hang([-1, NUM_PLANES, SQUARES])])], perm=[0, 2, 1])
    h = g.nut("Add", [g.linear(h, "embed"), "pos_embed"])                       # [B,100,d]
    for i in range(layers):
        p = f"blocks.{i}"
        a = g.ln(h, p + ".ln1")
        qkv = g.nut("Transpose", [g.nut("Reshape", [g.linear(a, p + ".attn.qkv"), g.hang([-1, SQUARES, 3, heads, dh])])],
                    perm=[2, 0, 3, 1, 4])                                        # [3,B,H,T,dh]
        q, k, v = (g.nut("Gather", [qkv, g.hang(j)], axis=0) for j in range(3))
        bias = g.nut("Unsqueeze", [g.nut("Gather", [p + ".attn.rel_bias", chi_so], axis=1), g.hang([0])])   # [1,H,T,T]
        att = g.nut("MatMul", [g.nut("Mul", [q, g.hang(1.0 / math.sqrt(dh), np.float32)]),
                               g.nut("Transpose", [k], perm=[0, 1, 3, 2])])
        att = g.nut("Softmax", [g.nut("Add", [att, bias])], axis=-1)
        o = g.nut("Reshape", [g.nut("Transpose", [g.nut("MatMul", [att, v])], perm=[0, 2, 1, 3]), g.hang([-1, SQUARES, d_model])])
        h = g.nut("Add", [h, g.linear(o, p + ".attn.proj")])
        f = g.linear(g.gelu(g.linear(g.ln(h, p + ".ln2"), p + ".ff1")), p + ".ff2")
        h = g.nut("Add", [h, f])
    h = g.ln(h, "final_ln")
    pol = g.nut("Reshape", [g.nut("Transpose", [g.linear(h, "pol_head")], perm=[0, 2, 1]), g.hang([-1, POLICY_SIZE])])
    # Hai đầu FC giữ dạng 3 chiều [B,1,k]: ở dạng 2 chiều ORT gộp MatMul+Add thành Gemm, mà Gemm của XNNPACK (ORT 1.18)
    # giữ hình dạng của lần chạy đầu nên hỏng khi cỡ lô đổi (MCTS gửi lô 1..16).
    v = g.nut("Reshape", [g.gelu(g.linear(h, "val_proj")), g.hang([-1, 1, net.val_fc1.in_features])])
    v = g.nut("Reshape", [g.linear(g.gelu(g.linear(v, "val_fc1")), "val_fc2"), g.hang([-1, 3])])
    v = g.nut("Softmax", [v], axis=1)
    m = g.nut("Reshape", [g.gelu(g.linear(h, "mlh_proj")), g.hang([-1, 1, net.mlh_fc1.in_features])])
    m = g.nut("Reshape", [g.linear(g.gelu(g.linear(m, "mlh_fc1")), "mlh_fc2"), g.hang([-1, 1])])
    g.nodes += [helper.make_node("Identity", [x], [ten], name="ra_" + ten) for x, ten in ((pol, "policy"), (v, "value"), (m, "mlh"))]

    ws = []
    for r in bang:                                                               # trọng số: chỉ tên + chỗ trong tệp ngoài
        t = TensorProto(name=r["ten"], data_type=TensorProto.FLOAT, dims=r["hinh"])
        t.data_location = TensorProto.EXTERNAL
        for k_, v_ in (("location", TEP_TRONG_SO), ("offset", str(r["vi_tri"])), ("length", str(r["so_byte"]))):
            e = t.external_data.add(); e.key, e.value = k_, v_
        ws.append(t)
    io = lambda ten, *dims: helper.make_tensor_value_info(ten, TensorProto.FLOAT, ["batch", *dims])
    graph = helper.make_graph(g.nodes, "fairyzero_khung", [io("input", NUM_PLANES, 10, 10)],
                              [io("policy", POLICY_SIZE), io("value", 3), io("mlh", 1)], initializer=g.consts + ws)
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", OPSET)], producer_name="khung_mang.py")
    model.ir_version = 8                                                         # ORT 1.18 đọc tới IR 9
    ghep = {"phien_ban": PHIEN_BAN, "kien_truc": {"d_model": d_model, "layers": layers, "heads": heads},
            "tep_trong_so": TEP_TRONG_SO, "tong_byte": tong, "tensor": bang}
    return model, ghep


def ghi_trong_so(sd, ghep, duong_dan):
    """Cách app làm, viết bằng Python: chép byte float32 của từng tensor vào đúng vị trí; lệch tên / hình dạng thì dừng."""
    buf = bytearray(ghep["tong_byte"])
    con = set(sd)
    for r in ghep["tensor"]:
        t = sd[r["ten"]]
        con.discard(r["ten"])
        assert list(t.shape) == r["hinh"], f"{r['ten']}: {list(t.shape)} != {r['hinh']}"
        b = t.detach().cpu().contiguous().numpy().astype("<f4").tobytes()
        buf[r["vi_tri"]:r["vi_tri"] + r["so_byte"]] = b
    assert not con, f".pt có tensor lạ: {sorted(con)}"
    with open(duong_dan, "wb") as f:
        f.write(buf)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="lenh", required=True)
    a = sub.add_parser("dung"); a.add_argument("--ra", default=MAC_DINH_RA)
    b = sub.add_parser("kiem"); b.add_argument("pt"); b.add_argument("--khung", default=MAC_DINH_RA)
    b.add_argument("--thu-muc", default=None, help="nơi ghi khung + trong_so.bin của mạng đã đổi (mặc định cạnh .pt)")
    args = ap.parse_args()

    if args.lenh == "dung":
        model, ghep = dung_do_thi()
        os.makedirs(args.ra, exist_ok=True)
        p = os.path.join(args.ra, "khung.onnx")
        onnx.save(model, p)                                   # trọng số đã là EXTERNAL: chỉ đồ thị + hằng nhỏ
        with open(os.path.join(args.ra, "bang_ghep.json"), "w", encoding="utf-8") as f:
            json.dump(ghep, f, ensure_ascii=False, indent=1)
        print(f"[khung] {p}: {os.path.getsize(p)} byte, {len(model.graph.node)} nút; {len(ghep['tensor'])} tensor, "
              f"trong_so.bin {ghep['tong_byte']} byte")
        return

    import shutil
    import torch
    import onnxruntime as ort
    from train import check_inputs
    with open(os.path.join(args.khung, "bang_ghep.json"), encoding="utf-8") as f:
        ghep = json.load(f)
    out = args.thu_muc or os.path.splitext(args.pt)[0] + "_khung"
    os.makedirs(out, exist_ok=True)
    shutil.copy(os.path.join(args.khung, "khung.onnx"), os.path.join(out, "khung.onnx"))
    sd = torch.load(args.pt, map_location="cpu")
    ghi_trong_so(sd, ghep, os.path.join(out, TEP_TRONG_SO))
    net = FairyNet(**ghep["kien_truc"]); net.load_state_dict(sd); net.eval()
    x = check_inputs(64)
    with torch.no_grad():
        p_, v_, m_ = net(torch.from_numpy(x))
        ref = (p_.numpy(), torch.softmax(v_, 1).numpy(), m_.numpy())
    s = ort.InferenceSession(os.path.join(out, "khung.onnx"), providers=["CPUExecutionProvider"])
    got = s.run(["policy", "value", "mlh"], {"input": x})
    for ten, r, o in zip(("policy", "value", "mlh"), ref, got):
        print(f"[kiem] {ten}: hình {o.shape}, lệch tuyệt đối lớn nhất {np.abs(r - o).max():.2e}")
    tv = 0.5 * np.abs(torch.softmax(torch.from_numpy(ref[0]), 1).numpy() - torch.softmax(torch.from_numpy(got[0]), 1).numpy()).sum(1).max()
    print(f"[kiem] khoảng cách biến phân lớn nhất của chính sách {tv:.2e}; thư mục {out}")
    ok = tv < 1e-4 and np.abs(ref[1] - got[1]).max() < 1e-4 and np.abs(ref[2] - got[2]).max() < 1e-2
    print("[kiem] ĐẠT" if ok else "[kiem] KHÔNG ĐẠT")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
