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


def xuat_onnx(mang, duong_dan, fp16=False):
    """Xuất ONNX với tên nút input_planes, policy, wdl (dùng khi bọc bằng onnx2leela)."""
    m = MangXuat(mang).eval()
    x = torch.zeros(1, 112, 8, 8)
    if fp16:
        m = m.half()
        x = x.half()
    torch.onnx.export(m, (x,), duong_dan, input_names=["input_planes"], output_names=["policy", "wdl"],
                      dynamic_axes={"input_planes": {0: "batch"}, "policy": {0: "batch"}, "wdl": {0: "batch"}},
                      opset_version=17, dynamo=False)
