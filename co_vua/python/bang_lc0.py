"""Lấy hai bảng của lc0 từ mã nguồn engine (co_vua/engine) và lưu vào bang_lc0.npz.

- kMoveStrs (src/neural/encoder.cc): 1858 nước đi theo thứ tự chỉ số đầu ra policy, viết theo góc nhìn
  bên đang đi (bên Đen thì đã lật hàng). Phong cấp mã thường không có hậu tố.
- kConvPolicyMap (src/neural/tables/policy_map.h): với đầu ra tích chập 73 x 8 x 8 của policy head,
  phần tử thứ i (kênh * 64 + ô) ứng với chỉ số policy nào (-1 nếu không dùng).

Chạy lại script này khi đổi bản lc0:  py -I bang_lc0.py
"""
import re
from pathlib import Path

import numpy as np

GOC = Path(__file__).resolve().parent
SRC = GOC.parent / "engine" / "src"


def doc_mang_c(van_ban, ten):
    m = re.search(ten + r"\[\]\s*=\s*\{(.*?)\};", van_ban, re.S)
    if not m:
        raise ValueError(f"không thấy {ten}")
    return m.group(1)


def main():
    enc = (SRC / "neural" / "encoder.cc").read_text(encoding="utf-8")
    nuoc = re.findall(r'"([a-h][1-8][a-h][1-8][qrb]?)"', doc_mang_c(enc, "kMoveStrs"))
    assert len(nuoc) == 1858, len(nuoc)

    pm = (SRC / "neural" / "tables" / "policy_map.h").read_text(encoding="utf-8")
    ban_do = np.array([int(x) for x in re.findall(r"-?\d+", doc_mang_c(pm, "kConvPolicyMap"))], np.int32)
    assert len(ban_do) == 73 * 64, len(ban_do)
    # Đảo ngược: chỉ số policy j lấy từ phần tử nào của đầu ra tích chập đã làm phẳng.
    gom = np.full(1858, -1, np.int64)
    for i, j in enumerate(ban_do):
        if j >= 0:
            assert gom[j] == -1, j
            gom[j] = i
    assert (gom >= 0).all()

    np.savez(GOC / "bang_lc0.npz", nuoc=np.array(nuoc), gom_policy=gom)
    print("Đã ghi bang_lc0.npz:", len(nuoc), "nước;", int((ban_do >= 0).sum()), "ô của đầu ra tích chập được dùng")


if __name__ == "__main__":
    main()
