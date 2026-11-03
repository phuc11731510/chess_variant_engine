"""Đọc tệp kết quả của chế độ `lc0 treeplay` (định dạng ghi ở đầu co_vua/engine/src/treeplay/treeplay.cc).

Mỗi bản ghi là kết quả của một việc: một ván (G) hoặc một lần search lại (S). Nước đi là số 16 bit
của lc0 (Move::raw_data), toạ độ tuyệt đối: ô đi ở bit 6-11, ô đến ở bit 0-5, ô = hàng*8 + cột;
nhập thành ghi là "vua ăn xe".
"""
import struct
import sys
from dataclasses import dataclass

import numpy as np

MAGIC = b"CVG1"
_DAU = struct.Struct("<4sIQBbBBHH")            # magic, cỡ, id, loại, kết quả, kết thúc, dự trữ, số nước đường đi, số lần search
_LAN = struct.Struct("<HHIfffff")             # nước đã đi, số nước đã thăm, N, best_q, best_d, raw_q, raw_d, p0
KIEU_NUOC_THAM = np.dtype([("nuoc", "<u2"), ("n", "<u2"), ("q", "<f2"), ("d", "<f2"),
                           ("p_nhieu", "<f2"), ("p_tho", "<f2")])
KET_THUC = {0: "hết ván theo luật", 1: "chạm giới hạn nửa nước", 2: "search lại"}


@dataclass
class LanSearch:
    nuoc_di: int          # nước đã đi (search lại: nước tốt nhất)
    N: int                # tổng lượt thăm của các nước con
    best_q: float
    best_d: float
    raw_q: float          # đánh giá thô của mạng
    raw_d: float
    p0: float             # tổng prior (đã trộn nhiễu) của các nước không được thăm
    tham: np.ndarray      # mảng KIEU_NUOC_THAM, mỗi phần tử một nước đã thăm


@dataclass
class BanGhi:
    id: int
    search_lai: bool
    ket_qua: int          # góc nhìn Trắng: +1, 0, -1
    ket_thuc: int         # khoá của KET_THUC
    duong_di: list        # các nước của việc (số 16 bit)
    lan: list             # LanSearch theo thứ tự nửa nước


def doc(duong_dan):
    """Trả về danh sách BanGhi. Bản ghi cuối bị cắt dở (máy dừng giữa lúc ghi) thì bỏ qua."""
    b = open(duong_dan, "rb").read()
    ket_qua, i = [], 0
    while i + _DAU.size <= len(b):
        magic, co, id_, loai, kq, kt, _, so_dd, so_lan = _DAU.unpack_from(b, i)
        if magic != MAGIC:
            raise ValueError(f"sai magic ở byte {i}")
        if i + co > len(b):
            break
        j = i + _DAU.size
        duong_di = list(struct.unpack_from(f"<{so_dd}H", b, j))
        j += 2 * so_dd
        lan = []
        for _ in range(so_lan):
            nuoc, so_tham, N, bq, bd, rq, rd, p0 = _LAN.unpack_from(b, j)
            j += _LAN.size
            tham = np.frombuffer(b, KIEU_NUOC_THAM, so_tham, j)
            j += KIEU_NUOC_THAM.itemsize * so_tham
            lan.append(LanSearch(nuoc, N, bq, bd, rq, rd, p0, tham))
        if j != i + co:
            raise ValueError(f"bản ghi id {id_}: đọc {j - i} byte, cỡ ghi là {co}")
        ket_qua.append(BanGhi(id_, loai == 1, kq, kt, duong_di, lan))
        i += co
    return ket_qua


def sang_uci(m):
    """Số 16 bit của lc0 (toạ độ tuyệt đối) sang chuỗi UCI cờ vua thường."""
    tu, den = (m >> 6) & 63, m & 63
    if (m >> 12) & 7 == 1:                       # nhập thành: vua ăn xe -> vua đi hai ô
        den = (tu & ~7) | (6 if (den & 7) > (tu & 7) else 2)
    s = "abcdefgh"[tu & 7] + str(tu // 8 + 1) + "abcdefgh"[den & 7] + str(den // 8 + 1)
    if m & 0x4000:
        s += "nqrb"[(m >> 12) & 3]
    return s


if __name__ == "__main__":
    for r in doc(sys.argv[1]):
        loai = "S" if r.search_lai else "G"
        print(f"{loai} id={r.id} kết quả={r.ket_qua:+d} ({KET_THUC[r.ket_thuc]}) "
              f"đường đi={' '.join(map(sang_uci, r.duong_di)) or '-'} số lần search={len(r.lan)}")
        for k, l in enumerate(r.lan[:3]):
            tong_n = int(l.tham["n"].astype(np.int64).sum())
            tong_p = float(l.tham["p_nhieu"].astype(np.float64).sum()) + l.p0
            print(f"   lần {k}: đi {sang_uci(l.nuoc_di)}, N={l.N}, tổng n={tong_n}, {len(l.tham)} nước đã thăm, "
                  f"best_q={l.best_q:+.3f}, raw_q={l.raw_q:+.3f}, tổng prior={tong_p:.3f}")
        if r.lan and not r.search_lai:
            print("   các nước đã đi:", " ".join(sang_uci(l.nuoc_di) for l in r.lan[:12]),
                  "..." if len(r.lan) > 12 else "")
