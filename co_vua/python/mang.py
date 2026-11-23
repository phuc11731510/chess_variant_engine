"""Mạng cờ vua của dự án (THIET_KE_CO_VUA.md 12.1): tích chập có SE, hai đầu ra policy và value (WDL).

Thân: lớp đầu 112 -> 64 kênh (3x3), rồi 11 khối dư, mỗi khối hai tích chập 3x3 kèm BN và SE tỉ lệ 8
(SE kiểu lc0: ra hệ số nhân và hệ số cộng cho từng kênh).
Policy head: tích chập 3x3 64 -> 64 (BN, ReLU), rồi 1x1 64 -> 73, rồi lấy 1858 ô theo bảng của lc0.
Value head: tích chập 1x1 64 -> 32 (BN, ReLU), kết nối đầy đủ 2048 -> 128 -> 3. Hai đầu ra lấy theo
mạng của dự án cờ biến thể (custom_engine/python/model.py), chỉ đổi cỡ bàn cờ và số loại nước.

Đầu ra khi xuất ONNX cho lc0: policy là logit (lc0 tự làm softmax trên các nước hợp lệ), WDL là xác
suất (lc0 không làm softmax cho mạng bọc bằng onnx2leela). Mặt phẳng 109 (luật 50 nước) vào mạng
dưới dạng số nửa nước thô, mạng tự chia cho 99.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F

from ma_hoa import GOM_POLICY

KENH = 64
SO_KHOI = 11
TI_LE_SE = 8


class SE(nn.Module):
    def __init__(self, c, ti_le):
        super().__init__()
        self.fc1 = nn.Linear(c, c // ti_le)
        self.fc2 = nn.Linear(c // ti_le, 2 * c)

    def forward(self, x):
        s = x.mean(dim=(2, 3))
        s = self.fc2(F.relu(self.fc1(s)))
        nhan, cong = s.chunk(2, dim=1)
        return x * torch.sigmoid(nhan)[:, :, None, None] + cong[:, :, None, None]


class KhoiDu(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.c1 = nn.Conv2d(c, c, 3, padding=1, bias=False)
        self.b1 = nn.BatchNorm2d(c)
        self.c2 = nn.Conv2d(c, c, 3, padding=1, bias=False)
        self.b2 = nn.BatchNorm2d(c)
        self.se = SE(c, TI_LE_SE)

    def forward(self, x):
        y = F.relu(self.b1(self.c1(x)))
        y = self.se(self.b2(self.c2(y)))
        return F.relu(x + y)


class MangCoVua(nn.Module):
    def __init__(self, kenh=KENH, so_khoi=SO_KHOI):
        super().__init__()
        self.dau = nn.Conv2d(112, kenh, 3, padding=1, bias=False)
        self.dau_bn = nn.BatchNorm2d(kenh)
        self.than = nn.Sequential(*[KhoiDu(kenh) for _ in range(so_khoi)])
        self.p_conv = nn.Conv2d(kenh, kenh, 3, padding=1, bias=False)
        self.p_bn = nn.BatchNorm2d(kenh)
        self.p_ra = nn.Conv2d(kenh, 73, 1)
        self.v_conv = nn.Conv2d(kenh, 32, 1, bias=False)
        self.v_bn = nn.BatchNorm2d(32)
        self.v_fc1 = nn.Linear(32 * 64, 128)
        self.v_fc2 = nn.Linear(128, 3)
        self.register_buffer("gom", torch.as_tensor(GOM_POLICY, dtype=torch.long), persistent=False)
        thang = torch.ones(112, 1, 1)
        thang[109] = 1.0 / 99.0
        self.register_buffer("thang_dau_vao", thang, persistent=False)

    def forward(self, x):
        """x: (B, 112, 8, 8). Trả về (logit policy (B, 1858), logit WDL (B, 3))."""
        x = x * self.thang_dau_vao
        x = F.relu(self.dau_bn(self.dau(x)))
        x = self.than(x)
        p = F.relu(self.p_bn(self.p_conv(x)))
        p = self.p_ra(p).flatten(1)[:, self.gom]
        v = F.relu(self.v_bn(self.v_conv(x))).flatten(1)
        v = self.v_fc2(F.relu(self.v_fc1(v)))
        return p, v


class MangXuat(nn.Module):
    """Bọc để xuất ONNX: policy giữ logit, WDL qua softmax."""

    def __init__(self, mang):
        super().__init__()
        self.mang = mang

    def forward(self, x):
        p, v = self.mang(x)
        return p, torch.softmax(v, dim=1)


def so_tham_so(mang):
    return sum(t.numel() for t in mang.parameters())


# ---------------------------------------------------------------- FP16 cho suy luận (chép cách của fz: train.py fp16_onnx)
# Mạng huấn luyện giữ fp32 (.pt); chỉ tệp .onnx cho engine được đổi sang nửa chính xác (đầu vào và đầu ra vẫn fp32,
# có nút Cast ở hai đầu). Các kiểm tra truyền thống của suy luận fp16 đều làm ở đây:
#   1. đồ thị fp16 chạy trên GPU được so với đồ thị fp32 chạy trên CPU (chuẩn đúng), trên các thế cờ thật nếu người gọi
#      có (lô huấn luyện đầu tiên), không thì thế cờ tổng hợp;
#   2. không có NaN hay vô cực ở đầu ra nào (tràn fp16 hiện ra như vậy);
#   3. xác suất nước đi và WDL phải sát bản fp32 trong FP16_DUNG_SAI;
#   4. softmax chạy trong nhân CUDA của ONNX Runtime, cộng dồn bằng fp32.
# Không kiểm được (không có GPU, không có onnxruntime-gpu) hoặc kiểm không đạt thì GIỮ NGUYÊN tệp fp32 và in lý do:
# nửa chính xác chỉ là tối ưu, không bao giờ làm mất mạng xuất. CV_ONNX_FP16=0 trong môi trường thì tắt hẳn.
# Đo trên T4 (23/11, mạng đời 20, engine thật, 128 ván song song, 800 lượt thăm): engine chạy đồ thị FP16 CHẬM hơn fp32
# (6 060-6 340 lần chạy mạng mỗi giây với vào/ra fp32, 6 700-6 900 với vào/ra fp16; fp32: 7 900-8 000), dù ONNX Runtime đơn lẻ
# nhanh gấp 1,6-1,9 lần ở lô từ 128: nút thắt của engine là CPU, không phải GPU. Vì vậy MẶC ĐỊNH tệp ONNX cho engine là fp32;
# AMP trong huấn luyện thì vẫn dùng (nhanh gấp 4,65 lần). Muốn thử lại fp16 cho engine: đặt True ở đây, hoặc --onnx-fp16.
ONNX_FP16_MAC_DINH = False
FP16_DUNG_SAI = (0.01, 0.01)       # lớn nhất trên các thế cờ kiểm: khoảng cách biến thiên toàn phần của softmax(policy), |WDL|
FP16_SO_THE = 64


def dau_vao_kiem(n=FP16_SO_THE, seed=0):
    """n thế cờ tổng hợp dạng như thế thật: mặt phẳng quân thưa 0/1, nhập thành, bên đi, bộ đếm luật 50 nước (số thô)."""
    import numpy as np
    rng = np.random.default_rng(seed)
    x = np.zeros((n, 112, 8, 8), np.float32)
    x[:, :104] = (rng.random((n, 104, 8, 8)) < 0.04)
    x[:, 104:109] = (rng.random((n, 5, 1, 1)) < 0.5)
    x[:, 109] = rng.integers(0, 99, (n, 1, 1))
    x[:, 111] = 1.0
    return x


def _softmax(a):
    import numpy as np
    e = np.exp(a - a.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)


def fp16_khac_biet(chuan, ra):
    """(TV lớn nhất của softmax(policy), |WDL| lớn nhất) giữa hai kết quả (policy, wdl); None nếu `ra` có NaN / vô cực.
    Dùng khoảng cách biến thiên toàn phần vì đó là thứ search thấy: logit lệch 0,01 ở nơi các logit cách nhau 20 không tính."""
    import numpy as np
    if not all(np.isfinite(a).all() for a in ra):
        return None
    tv = 0.5 * np.abs(_softmax(chuan[0].astype(np.float64)) - _softmax(ra[0].astype(np.float64))).sum(axis=1).max()
    return float(tv), float(np.abs(chuan[1] - ra[1]).max())


def fp16_onnx(duong_dan, x=None):
    """Đổi trọng số và phép tính của đồ thị fp32 tại `duong_dan` sang fp16 NGAY TẠI CHỖ, sau các kiểm tra ở trên.
    True nếu tệp giờ là đồ thị fp16; False (tệp fp32 giữ nguyên) nếu không dùng được, kèm lý do in ra."""
    import os
    tam = duong_dan + ".fp16"
    try:
        import numpy as np
        import onnx
        import onnxruntime as ort
        from onnxruntime.transformers.onnx_model import OnnxModel
        if "CUDAExecutionProvider" not in ort.get_available_providers():
            print("[xuat] FP16 KHÔNG dùng: onnxruntime này không có CUDA để kiểm đồ thị fp16 "
                  "(pip install onnxruntime-gpu trên máy GPU); giữ đồ thị fp32")
            return False
        xs = dau_vao_kiem() if x is None else np.asarray(x, dtype=np.float32)
        chuan = ort.InferenceSession(duong_dan, providers=["CPUExecutionProvider"]).run(["policy", "wdl"], {"input_planes": xs})
        om = OnnxModel(onnx.load(duong_dan))
        om.convert_float_to_float16(keep_io_types=True)
        om.save_model_to_file(tam)
        phien = ort.InferenceSession(tam, providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
        if phien.get_providers()[0] != "CUDAExecutionProvider":
            print("[xuat] FP16 KHÔNG dùng: phiên kiểm không chạy được trên CUDA; giữ đồ thị fp32")
            return False
        ra = phien.run(["policy", "wdl"], {"input_planes": xs})
        kb = fp16_khac_biet(chuan, ra)
        if kb is None:
            print("[xuat] FP16 KHÔNG dùng: đầu ra có NaN hoặc vô cực (tràn); giữ đồ thị fp32")
            return False
        if any(d > t for d, t in zip(kb, FP16_DUNG_SAI)):
            print(f"[xuat] FP16 KHÔNG dùng: lệch fp32 (TV policy, |WDL|) = ({kb[0]:.4f}, {kb[1]:.4f}) > {FP16_DUNG_SAI}; giữ đồ thị fp32")
            return False
        os.replace(tam, duong_dan)
        print(f"[xuat] đồ thị FP16 (trọng số và phép tính nửa chính xác, vào/ra fp32), đã kiểm trên GPU với fp32 qua {len(xs)} thế: "
              f"TV policy {kb[0]:.1e}, |WDL| {kb[1]:.1e}")
        return True
    except Exception as e:      # noqa: BLE001 -- nửa chính xác chỉ là tối ưu: không bao giờ để nó làm mất mạng xuất
        print(f"[xuat] FP16 bỏ qua ({type(e).__name__}: {str(e)[:200]}); giữ đồ thị fp32")
        return False
    finally:
        if os.path.exists(tam):
            os.remove(tam)


def xuat_onnx(mang, duong_dan, fp16=None, x_that=None):
    """Xuất ONNX (fp32) với tên nút input_planes, policy, wdl (dùng khi bọc bằng onnx2leela). fp16=True: rồi đổi sang
    đồ thị fp16 nếu qua các kiểm tra của fp16_onnx (x_that: các thế cờ thật để kiểm). Trả về True nếu tệp là fp16."""
    import os
    if fp16 is None:
        fp16 = ONNX_FP16_MAC_DINH
    m = MangXuat(mang).eval()
    x = torch.zeros(1, 112, 8, 8)
    torch.onnx.export(m, (x,), duong_dan, input_names=["input_planes"], output_names=["policy", "wdl"],
                      dynamic_axes={"input_planes": {0: "batch"}, "policy": {0: "batch"}, "wdl": {0: "batch"}},
                      opset_version=17, dynamo=False)
    if fp16 and os.environ.get("CV_ONNX_FP16", "") != "0":
        return fp16_onnx(duong_dan, x_that)
    return False
