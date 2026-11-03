"""Đo dung lượng và thời gian thao tác trên một cây trò chơi giả (THIET_KE_CO_VUA.md 12.6).

Cây giả có hình dạng giống cây thật: ván đầu đi từ gốc, các ván sau rẽ từ một node chọn
ngẫu nhiên rồi đi tiếp tới hết ván. Số liệu search (lượt thăm, Q, prior) là số ngẫu nhiên:
chỉ dung lượng và thời gian là có ý nghĩa, còn các giá trị G, E tính ra thì không.

Cây lưu theo kiểu "mảng số gọn": mỗi trường là một mảng numpy, các nước đã thăm của mọi
node nối liền trong một mảng (node i chiếm đoạn off[i]..off[i+1]).

Chạy:  py -I do_cay_gia.py [số node] [số nước đã thăm trung bình mỗi node]
"""
import heapq
import sys
import time

import numpy as np

try:
    import psutil
except ImportError:
    psutil = None

SO_LUOT_THAM = 800
OMEGA2 = 0.04


def rss_mb():
    return psutil.Process().memory_info().rss / 2**20 if psutil else float("nan")


class DongHo:
    def __init__(self):
        self.ket_qua = []

    def do(self, ten, ham, *args):
        t = time.perf_counter()
        r = ham(*args)
        self.ket_qua.append((ten, time.perf_counter() - t))
        print(f"  {ten:<45} {self.ket_qua[-1][1]:7.2f} giây   RAM {rss_mb():7.0f} MB", flush=True)
        return r


def tao_cay(so_node, k_tb, rng):
    """Sinh cây giả. Trả về dict các mảng của cây."""
    k = rng.integers(max(1, k_tb // 2), k_tb * 3 // 2 + 1, so_node).astype(np.int32)
    off = np.zeros(so_node + 1, np.int64)
    np.cumsum(k, out=off[1:])
    tong = int(off[-1])
    w = rng.exponential(1.0, tong).astype(np.float32) ** 2
    s = np.add.reduceat(w, off[:-1])
    ti_le = w / np.repeat(s, k)
    n = np.maximum(1, ti_le * SO_LUOT_THAM).astype(np.uint16)
    # Nước có chỉ số 0 trong danh sách của mỗi node là nước được chơi khi đi tiếp (temperature 0).
    n[off[:-1]] = SO_LUOT_THAM
    cay = {
        "k": k, "off": off, "n": n,
        "q": rng.uniform(-0.3, 0.3, tong).astype(np.float16),
        "p_nhieu": ti_le.astype(np.float16),
        "p_tho": ti_le.astype(np.float16),
        "nuoc": rng.integers(0, 1858, tong).astype(np.uint16),
        "parent": np.full(so_node, -1, np.int32),
        "chi_so": np.zeros(so_node, np.int16),   # chỉ số nước dẫn tới node trong danh sách của cha
        "depth": np.zeros(so_node, np.int16),
        "ket_thuc": np.zeros(so_node, bool),
        "ket_qua": np.zeros(so_node, np.float16),  # kết quả ván ở node kết thúc
        "best_q": rng.uniform(-0.3, 0.3, so_node).astype(np.float16),
        "orig_q": rng.uniform(-0.3, 0.3, so_node).astype(np.float16),
        "G": np.zeros(so_node, np.float32),
        "E": np.zeros(so_node, np.float32),
        "m": np.zeros(so_node, np.float32),
    }
    del w, s, ti_le

    parent, chi_so, depth = cay["parent"], cay["chi_so"], cay["depth"]
    ket_thuc = cay["ket_thuc"]
    da_dung = {}
    cur = 1

    def choi(tu, idx, dai):
        nonlocal cur
        p, i = tu, idx
        for _ in range(dai):
            if cur >= so_node:
                break
            parent[cur] = p
            chi_so[cur] = i
            depth[cur] = depth[p] + 1
            p, i = cur, 0
            cur += 1
        ket_thuc[p] = True

    choi(0, 0, 100)
    so_van = 1
    while cur < so_node:
        p = int(rng.integers(0, cur))
        if ket_thuc[p] or k[p] < 2:
            continue
        dung = da_dung.setdefault(p, set())
        if len(dung) >= k[p] - 1:
            continue
        i = int(rng.integers(1, k[p]))
        if i in dung:
            continue
        dai = min(int(rng.geometric(1 / 60)), 449 - int(depth[p]))
        if dai < 1:
            continue
        dung.add(i)
        choi(p, i, dai)
        so_van += 1
    ket_thuc[cur - 1] = True
    cay["ket_qua"][ket_thuc] = rng.choice([-1.0, 0.0, 1.0], int(ket_thuc.sum()))
    return cay, so_van


def dung_lop_do_sau(cay):
    """Nhóm node theo độ sâu, làm một lần, dùng lại cho mọi lượt tính từ dưới lên."""
    depth = cay["depth"]
    thu_tu = np.argsort(depth, kind="stable")
    ranh = np.searchsorted(depth[thu_tu], np.arange(int(depth.max()) + 2))
    return [thu_tu[ranh[d]:ranh[d + 1]] for d in range(len(ranh) - 1)]


def tinh_pi(cay):
    off, n, k = cay["off"], cay["n"], cay["k"]
    N = np.add.reduceat(n.astype(np.float32), off[:-1])
    pi = n / np.repeat(N, k)
    tong_pi2 = np.add.reduceat(pi * pi, off[:-1])
    return pi.astype(np.float32), tong_pi2


def tinh_m(cay, lop):
    m = cay["m"]
    m[:] = cay["ket_thuc"]
    parent = cay["parent"]
    for d in range(len(lop) - 1, 0, -1):
        ch = lop[d]
        np.add.at(m, parent[ch], m[ch])


def tinh_rho_G_E(cay, lop, pi, tong_pi2):
    """Tính từ dưới lên theo 4.5: rho, G, E. Node kết thúc: G = kết quả, E = 0."""
    parent, off, chi_so = cay["parent"], cay["off"], cay["chi_so"]
    G, E = cay["G"], cay["E"]
    kt = cay["ket_thuc"]
    G[kt] = cay["ket_qua"][kt]
    E[kt] = 0.0
    for d in range(len(lop) - 1, 0, -1):
        ch = lop[d]
        par = parent[ch]
        cha, inv = np.unique(par, return_inverse=True)
        pi_ch = pi[off[par] + chi_so[ch]]
        f = OMEGA2 / (OMEGA2 + E[ch])
        A = np.bincount(inv, pi_ch * f)
        B = np.bincount(inv, f)
        nu = (1.0 - A) / B
        rho = (pi_ch + nu[inv]) * f
        U = tong_pi2[cha] - np.bincount(inv, pi_ch * pi_ch) + np.bincount(inv, (rho - pi_ch) ** 2)
        G[cha] = np.bincount(inv, rho * G[ch])
        E[cha] = np.bincount(inv, rho * rho * E[ch]) + OMEGA2 * U


def uoc_luong_omega2(cay):
    """Cách thứ nhất ở 4.4: độ chênh G giữa các nhánh của cùng node, trừ phần do sai số E."""
    parent = cay["parent"][1:]
    G, E = cay["G"][1:].astype(np.float64), cay["E"][1:].astype(np.float64)
    dem = np.bincount(parent, minlength=len(cay["G"]))
    tong = np.bincount(parent, G, minlength=len(cay["G"]))
    tong2 = np.bincount(parent, G * G, minlength=len(cay["G"]))
    tongE = np.bincount(parent, E, minlength=len(cay["G"]))
    ok = dem >= 2
    phuong_sai = (tong2[ok] - tong[ok] ** 2 / dem[ok]) / (dem[ok] - 1)
    return float(np.mean(phuong_sai - tongE[ok] / dem[ok]))


def quet(cay, rng):
    """Bước quét 6.1: mỗi node lấy một nước theo n^2 (T = 0.5); rẽ nếu nước đó chưa chơi."""
    off, n, k = cay["off"], cay["n"], cay["k"]
    w = n.astype(np.float64) ** 2
    C = np.cumsum(w)
    dau = np.concatenate(([0.0], C[off[1:-1] - 1]))
    muc_tieu = dau + rng.random(len(k)) * (C[off[1:] - 1] - dau)
    chon = np.searchsorted(C, muc_tieu, side="right")
    da_choi = np.zeros(len(n), bool)
    da_choi[off[cay["parent"][1:]] + cay["chi_so"][1:]] = True
    re = ~da_choi[chon] & ~cay["ket_thuc"]
    return int(re.sum())


def cat_la(cay, so_can_cat):
    """8.3: lặp lại cắt lá có m nhỏ nhất; node mất hết con thì thành lá."""
    parent, m = cay["parent"], cay["m"]
    so_con = np.bincount(parent[1:], minlength=len(m))
    la = np.flatnonzero(so_con == 0)
    heap = list(zip(m[la].tolist(), la.tolist()))
    heapq.heapify(heap)
    da_cat = 0
    while da_cat < so_can_cat and heap:
        _, x = heapq.heappop(heap)
        da_cat += 1
        p = int(parent[x])
        so_con[p] -= 1
        if so_con[p] == 0 and p != 0:
            heapq.heappush(heap, (float(m[p]), p))
    return da_cat


def gop_van_moi(cay, so_node_moi, k_tb, rng):
    """Mô phỏng chi phí gộp ván mới: nối thêm so_node_moi node và các nước đã thăm của chúng."""
    k = rng.integers(max(1, k_tb // 2), k_tb * 3 // 2 + 1, so_node_moi).astype(np.int32)
    tong = int(k.sum())
    moi = {}
    for ten in ("n", "q", "p_nhieu", "p_tho", "nuoc"):
        moi[ten] = np.concatenate((cay[ten], np.zeros(tong, cay[ten].dtype)))
    for ten in ("k", "parent", "chi_so", "depth", "ket_thuc", "ket_qua", "best_q", "orig_q", "G", "E", "m"):
        moi[ten] = np.concatenate((cay[ten], np.zeros(so_node_moi, cay[ten].dtype)))
    moi["off"] = np.concatenate((cay["off"], cay["off"][-1] + np.cumsum(k)))
    return moi


def ghi_du_lieu_huan_luyen(cay, pi, duong_dan):
    """12.6: cấu trúc cây (cha, nước), nhãn policy thưa, nhãn value, trọng số m."""
    np.savez(duong_dan, parent=cay["parent"], chi_so=cay["chi_so"], off=cay["off"],
             nuoc=cay["nuoc"], pi=pi.astype(np.float16), G=cay["G"].astype(np.float16),
             m=cay["m"])


def main():
    so_node = int(sys.argv[1]) if len(sys.argv) > 1 else 1_000_000
    k_tb = int(sys.argv[2]) if len(sys.argv) > 2 else 25
    rng = np.random.default_rng(12345)
    print(f"Cây giả {so_node} node, trung bình {k_tb} nước đã thăm mỗi node. RAM lúc đầu {rss_mb():.0f} MB")
    dh = DongHo()
    cay, so_van = dh.do("sinh cây giả (không tính vào thao tác)", tao_cay, so_node, k_tb, rng)
    byte = sum(a.nbytes for a in cay.values())
    print(f"  {so_van} ván; {len(cay['n'])} nước đã thăm; độ sâu lớn nhất {int(cay['depth'].max())}")
    print(f"  Dung lượng mảng của cây: {byte / 2**20:.0f} MB, tức {byte / so_node:.0f} byte mỗi node")

    lop = dh.do("nhóm node theo độ sâu", dung_lop_do_sau, cay)
    pi, tong_pi2 = dh.do("tính pi từ số lượt thăm", tinh_pi, cay)
    dh.do("tính m (số ván qua mỗi node)", tinh_m, cay, lop)
    dh.do("tính rho, G, E từ dưới lên (4.5)", tinh_rho_G_E, cay, lop, pi, tong_pi2)
    om2 = dh.do("ước lượng omega^2 (4.4, cách thứ nhất)", uoc_luong_omega2, cay)
    so_re = dh.do("quét toàn cây (6.1)", quet, cay, rng)
    print(f"  omega^2 ước lượng (vô nghĩa với số giả): {om2:.4f}; số điểm rẽ quét được: {so_re}")
    duong_dan = "du_lieu_huan_luyen_gia.npz"
    dh.do("ghi tệp dữ liệu huấn luyện", ghi_du_lieu_huan_luyen, cay, pi, duong_dan)
    import os
    print(f"  Tệp dữ liệu huấn luyện: {os.path.getsize(duong_dan) / 2**20:.0f} MB (chưa nén)")
    os.remove(duong_dan)
    so_cat = so_node // 8
    dh.do(f"cắt {so_cat} lá có m nhỏ nhất (8.3)", cat_la, cay, so_cat)
    dh.do(f"gộp {so_cat} node mới vào cây", gop_van_moi, cay, so_cat, k_tb, rng)
    tong = sum(t for ten, t in dh.ket_qua[1:])
    print(f"Tổng thời gian thao tác (không tính sinh cây giả): {tong:.1f} giây. RAM cuối {rss_mb():.0f} MB")


if __name__ == "__main__":
    main()
