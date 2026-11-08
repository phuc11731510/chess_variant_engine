"""cay.py -- cây trò chơi của cách "cay" (THIET_KE_CO_VUA.md phần 3 đến 11), chạy trên ĐIỆN THOẠI (cần numpy).

Cây lưu ở Download/CoVua/cay/cay/ (cay.npz + cay.json). Mỗi node là một thế cờ cùng lịch sử (đường đi từ gốc).
Không cần python-chess: nước đi là số 16 bit của lc0 (toạ độ tuyệt đối), đọc từ bản ghi treeplay.

  python3 cay.py cap_nhat <thư mục cách> <đời G>   # gộp các lần sinh đời G (games_gen<G>/*) vào cây, tính G, E,
                                                   # nhãn; ghi nhan_doi<G>.npz (+ danh sách mau.npz cần tải lên)
  python3 cay.py sau_hl <thư mục cách> <đời G> <ngân sách đời G+1>
                                                   # giảm gamma, cắt lá, quét điểm rẽ, ưu tiên search lại,
                                                   # lập danh sách việc của đời G+1 (viec_doi<G+1>.txt)
  python3 cay.py lay_viec <thư mục cách> <đời> <lần chạy mạng được giao> <tệp ra> [<số giây máy còn chạy>]
                                                   # nhận một phần danh sách việc (khoá thư mục), in số việc
  python3 cay.py tinh_trang <thư mục cách>
  python3 cay.py don_mau <thư mục cách> <đời G>         # dồn mặt phẳng còn dùng sang tệp gọn (sau_hl tự mở chạy nền)

Công tắc (mục 14, chủ dự án chốt 5/11 "mọi phần bật", nhãn policy mới tắt): CONG_TAC dưới đây.
"""
import gzip
import json
import os
import struct
import sys
import time

import numpy as np

CONG_TAC = {
    "nhan_value_moi": True,     # phần 4, 5: w_q q + (1 - w_q) G; tắt = 0.2 q + 0.8 G (G = kết quả ván ở node 1 ván)
    "search_lai": True,         # phần 9: tới 20% ngân sách
    "nhan_policy_moi": False,   # phần 7: pi' -- TẮT ở lần chạy chính (chủ dự án đồng ý 5/11)
}
W_DOI = 4                       # 8.1: mỗi đời làm mới 1/4 cây (chủ dự án chốt 4/11)
GAMMA = 1 - 1 / W_DOI           # 8.4
T_QUET = 0.5                    # 6.1
TRAN_SEARCH_LAI = 0.20          # 9.3 (chủ dự án chốt 5/11)
SAN_TAU_Q = 0.01                # phần 5
CACH_CUOI_TAU = 4               # 7/11: tau_q^2 ước từ node cách cuối ván <= 4 nửa nước
EVALS_MOI_SEARCH = 490          # mặc định trước khi đo (đo đời 0 cách truyền thống, 4/11)
DU_VIEC = 1.5                   # lập dư việc so với ngân sách (ước chi phí ván rẽ còn thô)

# ---------------------------------------------------------------- đọc bản ghi treeplay (giống python/ban_ghi.py)
MAGIC = b"CVG1"
_DAU = struct.Struct("<4sIQBbBBHH")
_LAN = struct.Struct("<HHIfffff")
KIEU_NUOC = np.dtype([("nuoc", "<u2"), ("n", "<u2"), ("q", "<f2"), ("d", "<f2"), ("p_nhieu", "<f2"), ("p_tho", "<f2")])


def doc_ban_ghi(b):
    """bytes -> list of (loai, ket_qua, ket_thuc, duong_di[list int], lan[list (nuoc, N, bq, bd, p0, tham)])."""
    ra, i = [], 0
    while i + _DAU.size <= len(b):
        magic, co, _id, loai, kq, kt, _, so_dd, so_lan = _DAU.unpack_from(b, i)
        if magic != MAGIC:
            raise ValueError(f"sai magic ở byte {i}")
        if i + co > len(b):
            break
        j = i + _DAU.size
        dd = list(struct.unpack_from(f"<{so_dd}H", b, j))
        j += 2 * so_dd
        lan = []
        for _ in range(so_lan):
            nuoc, so_tham, N, bq, bd, _rq, _rd, p0 = _LAN.unpack_from(b, j)
            j += _LAN.size
            tham = np.frombuffer(b, KIEU_NUOC, so_tham, j)
            j += KIEU_NUOC.itemsize * so_tham
            lan.append((nuoc, N, bq, bd, p0, tham))
        ra.append((loai, kq, kt, dd, lan))
        i += co
    return ra


def sang_uci(m):
    tu, den = (m >> 6) & 63, m & 63
    if (m >> 12) & 7 == 1:
        den = (tu & ~7) | (6 if (den & 7) > (tu & 7) else 2)
    s = "abcdefgh"[tu & 7] + str(tu // 8 + 1) + "abcdefgh"[den & 7] + str(den // 8 + 1)
    if m & 0x4000:
        s += "nqrb"[(m >> 12) & 3]
    return s


# ---------------------------------------------------------------- cây
NODE = {  # tên: (kiểu, giá trị đầu)
    "cha": (np.int32, -1), "nuoc": (np.uint16, 0), "sau": (np.int16, 0), "trang": (np.int8, 0),  # 0 sống 1 gốc-cắt 2 xoá
    "het": (np.int8, 0), "z": (np.int8, 0), "m": (np.float32, 0), "doi_tao": (np.int16, 0),
    "mau_tep": (np.int32, -1), "mau_hang": (np.int32, -1),
    "k": (np.float32, 0), "gsum": (np.float32, 0), "Nsum": (np.float32, 0), "p0sum": (np.float32, 0),
    "ms": (np.int64, 0), "ml": (np.int32, 0),
    "Gw": (np.float32, 0), "Gd": (np.float32, 0), "Gl": (np.float32, 0), "E": (np.float32, 0), "cach": (np.int32, 0),
}
POOL = {"mv": (np.uint16, 0), "ns": (np.float32, 0), "nq": (np.float32, 0), "nd": (np.float32, 0)}


def _pi_uint16(pi, dem, khuc=1 << 22):
    """pi (các node nối liền, node thứ i có dem[i] nước) -> uint16 với tổng mỗi node đúng 65535: làm tròn xuống, rồi
    cộng 1 cho các nước có phần lẻ lớn nhất (theo thứ tự phần lẻ giảm dần) tới khi đủ. Theo từng khúc node."""
    dem = np.asarray(dem, np.int64)
    off = np.concatenate(([0], np.cumsum(dem)))
    ra = np.empty(int(off[-1]), np.uint16)
    i, n = 0, len(dem)
    while i < n:
        j = min(max(int(np.searchsorted(off, off[i] + khuc, side="right")) - 1, i + 1), n)
        a, b = int(off[i]), int(off[j])
        x = pi[a:b].astype(np.float64) * 65535
        q = np.floor(x)
        own = np.repeat(np.arange(j - i), dem[i:j])
        thieu = np.clip(np.rint(65535 - np.bincount(own, q, j - i)), 0, dem[i:j]).astype(np.int64)
        thu_tu = np.argsort(own + (q - x + 1) * 0.999)  # theo node, trong node phần lẻ giảm dần (một khoá float64)
        hang = np.arange(b - a) - np.repeat(off[i:j] - a, dem[i:j])
        q[thu_tu[hang < thieu[own[thu_tu]]]] += 1
        ra[a:b] = q
        i = j
    return ra


class Cay:
    def __init__(self):
        self.n = 0
        self.a = {k: np.full(1024, v, t) for k, (t, v) in NODE.items()}
        self.np_ = 0
        self.p = {k: np.full(4096, v, t) for k, (t, v) in POOL.items()}
        self.meta = {"doi": -1, "moi_moi_doi": {}, "tep_mau": [], "da_nap": [], "delta": {}, "evals_moi_search": EVALS_MOI_SEARCH,
                     "nhat_ky": []}
        self.con = {}

    # -- dung lượng (nới 1.25 lần chứ không gấp đôi: pool đời 5 đã 47 triệu ô, gấp đôi lúc gộp tốn thêm 1.3 GB, 8/11)
    def _them_node(self, k=1):
        if self.n + k > len(self.a["cha"]):
            moi = max(len(self.a["cha"]) * 5 // 4 + 1024, self.n + k)
            for t, (kieu, v) in NODE.items():
                x = np.full(moi, v, kieu)
                x[:self.n] = self.a[t][:self.n]
                self.a[t] = x
        i = self.n
        self.n += k
        return i

    def _them_pool(self, k):
        if self.np_ + k > len(self.p["mv"]):
            moi = max(len(self.p["mv"]) * 5 // 4 + 4096, self.np_ + k)
            for t, (kieu, v) in POOL.items():
                x = np.full(moi, v, kieu)
                x[:self.np_] = self.p[t][:self.np_]
                self.p[t] = x
        i = self.np_
        self.np_ += k
        return i

    # -- lưu / nạp
    def luu(self, thu_muc):
        self.nen()
        os.makedirs(thu_muc, exist_ok=True)
        d = {f"n_{k}": v[:self.n] for k, v in self.a.items()}
        d.update({f"p_{k}": v[:self.np_] for k, v in self.p.items()})
        tam = os.path.join(thu_muc, "cay.tam.npz")
        np.savez(tam, **d)
        os.replace(tam, os.path.join(thu_muc, "cay.npz"))
        with open(os.path.join(thu_muc, "cay.json.tam"), "w", encoding="utf-8") as f:
            json.dump(self.meta, f, ensure_ascii=False)
        os.replace(os.path.join(thu_muc, "cay.json.tam"), os.path.join(thu_muc, "cay.json"))

    @classmethod
    def nap(cls, thu_muc):
        c = cls()
        f = os.path.join(thu_muc, "cay.npz")
        if not os.path.exists(f):
            return c
        z = np.load(f)
        c.n = len(z["n_cha"])
        c.a = {k: z[f"n_{k}"] for k in NODE}            # mỗi lần đọc z[...] đã là một mảng mới
        c.np_ = len(z["p_mv"])
        c.p = {k: z[f"p_{k}"] for k in POOL}
        with open(os.path.join(thu_muc, "cay.json"), encoding="utf-8") as fj:
            c.meta = json.load(fj)
        c.meta["tep_mau"] = [t.replace("\\", "/") for t in c.meta["tep_mau"]]   # cây tạo trên Windows (thử)
        c._dung_con()
        return c

    def _dung_con(self):
        a = self.a
        idx = np.where((a["cha"][:self.n] >= 0) & (a["trang"][:self.n] < 2))[0]
        khoa = a["cha"][idx].astype(np.int64) * 65536 + a["nuoc"][idx]
        self.con = None                                  # bỏ bảng cũ trước khi dựng bảng mới (khỏi giữ hai bảng)
        self.con = dict(zip(khoa.tolist(), idx.tolist()))

    def la_gon(self):
        """Pool gọn: đoạn của các node nằm liền nhau theo thứ tự node, không có ô bỏ lại (sau nen)."""
        ml = self.a["ml"][:self.n].astype(np.int64)
        dau = np.cumsum(ml) - ml
        return int(ml.sum()) == self.np_ and bool(np.array_equal(self.a["ms"][:self.n], dau))

    def nen(self):
        """Bỏ node đã xoá, dồn pool (đoạn cũ của node được search lại bị bỏ lại khi nới đoạn)."""
        a, n = self.a, self.n
        giu = np.where(a["trang"][:n] < 2)[0]
        if len(giu) == n and self.la_gon():              # không có gì để bỏ: khỏi chép lại cả cây
            return
        moi = np.full(n, -1, np.int64)
        moi[giu] = np.arange(len(giu))
        for k in NODE:
            a[k] = a[k][:n][giu]                         # chỉ số mảng đã là bản mới
        a["cha"] = np.where(a["cha"] >= 0, moi[np.maximum(a["cha"], 0)], -1).astype(np.int32)
        del moi
        self.n = len(giu)
        # pool: chép các đoạn đang dùng theo thứ tự node; ô thứ j của đoạn node i lấy từ ms_cu[i] + j
        ml = a["ml"][:self.n].astype(np.int64)
        tong = int(ml.sum())
        dau = np.cumsum(ml) - ml
        nguon = np.arange(tong, dtype=np.int64)
        nguon += np.repeat(a["ms"][:self.n].astype(np.int64) - dau, ml)
        for k in POOL:                                   # từng mảng một: lúc nào cũng chỉ thêm một mảng mới
            x = self.p[k][nguon] if tong else np.zeros(1, POOL[k][0])
            self.p[k] = x
        del nguon
        self.np_ = tong
        a["ms"] = dau
        self._dung_con()

    # -- node
    def goc(self):
        if self.n == 0:
            i = self._them_node()
            self.a["cha"][i] = -1
            self.a["doi_tao"][i] = self.meta["doi"]
        return 0

    def con_cua(self, s, m, tao, doi):
        k = s * 65536 + m
        c = self.con.get(k)
        if c is None and tao:
            c = self._them_node()
            a = self.a
            a["cha"][c], a["nuoc"][c], a["sau"][c], a["doi_tao"][c] = s, m, a["sau"][s] + 1, doi
            self.con[k] = c
        return c

    def them_search(self, s, tham, N, p0, doi):
        """Cộng một lần search vào trung bình của node s (phần 3, nhóm 1; đổi 4/11)."""
        a, p = self.a, self.p
        mv = tham["nuoc"].astype(np.uint16)
        n = tham["n"].astype(np.float32)
        q = tham["q"].astype(np.float32)
        d = tham["d"].astype(np.float32)
        ms, ml = int(a["ms"][s]), int(a["ml"][s])
        cu = p["mv"][ms:ms + ml]
        thieu = mv[~np.isin(mv, cu)]
        if len(thieu):                                   # nới đoạn: chép đoạn cũ + nước mới ra cuối pool
            moi = self._them_pool(ml + len(thieu))
            for k in POOL:
                self.p[k][moi:moi + ml] = self.p[k][ms:ms + ml]
            self.p["mv"][moi + ml:moi + ml + len(thieu)] = thieu
            for k in ("ns", "nq", "nd"):
                self.p[k][moi + ml:moi + ml + len(thieu)] = 0
            ms, ml = moi, ml + len(thieu)
            a["ms"][s], a["ml"][s] = ms, ml
            p = self.p
        seg = p["mv"][ms:ms + ml]
        order = np.argsort(seg)                          # đoạn có thể chưa sắp
        vi = ms + order[np.searchsorted(seg, mv, sorter=order)]
        p["ns"][vi] += n
        p["nq"][vi] += n * q
        p["nd"][vi] += n * d
        a["k"][s] += 1
        a["gsum"][s] += doi
        a["Nsum"][s] += N
        a["p0sum"][s] += p0

    def pi_cua(self, s):
        ms, ml = int(self.a["ms"][s]), int(self.a["ml"][s])
        ns = self.p["ns"][ms:ms + ml]
        return self.p["mv"][ms:ms + ml], ns / max(ns.sum(), 1e-12)

    # -- gộp bản ghi
    def nap_lan(self, thu_muc_lan, doi):
        """Gộp một lần sinh (thư mục chứa van.bin.gz và mau.npz) vào cây. Trả về (số node mới, số search, số ván)."""
        with gzip.open(os.path.join(thu_muc_lan, "van.bin.gz"), "rb") as f:
            ds = doc_ban_ghi(f.read())
        tep = len(self.meta["tep_mau"])
        self.meta["tep_mau"].append(os.path.relpath(os.path.join(thu_muc_lan, "mau.npz"), self.meta.get("goc_cach", ".")).replace(os.sep, "/"))
        a = self.a
        hang = 0
        n0, so_search, so_van, delta = self.n, 0, 0, []
        goc = self.goc()
        for loai, kq, kt, dd, lan in ds:
            if loai == 2:
                continue
            s = goc
            duong = [goc]
            ok = True
            for m in dd:
                s2 = self.con_cua(s, m, tao=(loai == 0), doi=doi)
                if s2 is None:
                    ok = False
                    break
                s = s2
                duong.append(s)
            if not ok:
                continue                                   # node của việc search lại đã bị cắt
            if loai == 1:                                  # search lại: đo độ chênh nhãn trước khi cộng (9.2)
                nuoc, N, bq, bd, p0, tham = lan[0]
                if a["k"][s] > 0:
                    mv_cu, pi_cu = self.pi_cua(s)
                    pi_moi = tham["n"].astype(np.float64) / max(tham["n"].sum(), 1)
                    tat = dict(zip(mv_cu.tolist(), pi_cu.tolist()))
                    for x, y in zip(tham["nuoc"].tolist(), pi_moi.tolist()):
                        tat[x] = tat.get(x, 0.0) - y
                    tuoi = doi - a["gsum"][s] / a["k"][s]
                    delta.append((float(tuoi), float(a["k"][s]), 0.5 * sum(abs(v) for v in tat.values())))
                self.them_search(s, tham, N, p0, doi)
                so_search += 1
                continue
            so_van += 1
            for nuoc, N, bq, bd, p0, tham in lan:
                self.them_search(s, tham, N, p0, doi)
                if a["mau_tep"][s] < 0:
                    a["mau_tep"][s], a["mau_hang"][s] = tep, hang
                hang += 1
                so_search += 1
                s = self.con_cua(s, nuoc, tao=True, doi=doi)
                duong.append(s)
            a["het"][s] = 1 if kt == 0 else 2
            a["z"][s] = kq if kt == 0 else 0
            a["m"][np.array(duong)] += 1
        for tuoi, k, d in delta:
            khoa = f"{min(int(tuoi), 9)}_{min(int(k), 9)}"
            t = self.meta["delta"].setdefault(khoa, [0.0, 0])
            t[0] += d
            t[1] += 1
        return self.n - n0, so_search, so_van

    # -- tính G, E, nhãn (phần 4, 5; phương án B, chủ dự án duyệt 7/11)
    def tinh(self):
        """Cần pool gọn (gọi nen trước). Mảng theo ô pool (47 triệu ô ở đời 5) là phần tốn bộ nhớ: mỗi mảng float64
        375 MB, nên chỉ giữ owner, pi, Qs và tạm một mảng; không dựng mảng chỉ số ô, không sắp khoá 64 bit (8/11:
        bản trước lên 5.8 GB). Kết quả giống hệt bản trước."""
        a, p, n = self.a, self.p, self.n
        if not self.la_gon():
            raise RuntimeError("tinh cần pool gọn: gọi nen() trước")
        song = a["trang"][:n] == 0
        ml = a["ml"][:n].astype(np.int64)
        ms = a["ms"][:n]
        so_o = self.np_
        slot = slice(0, so_o)                            # pool gọn: ô của node i là ms[i] .. ms[i] + ml[i] - 1
        # thống kê search mỗi node
        owner = np.repeat(np.arange(n, dtype=np.int64), ml)
        ns = p["ns"][:so_o]                              # float32; các phép dưới tự nâng lên float64 như bản trước
        co_ns = ns > 0
        tong = np.bincount(owner, ns, n)
        pi = np.maximum(tong, 1e-12)[owner]
        np.divide(ns, pi, out=pi)
        Qs = np.zeros(so_o)                              # góc bên đi
        np.divide(p["nq"][:so_o], np.maximum(ns, 1e-12), out=Qs, where=co_ns, dtype=np.float64)
        Qbar = np.bincount(owner, pi * Qs, n)
        x = Qbar[owner]
        np.subtract(Qs, x, out=x)
        x *= x
        x *= pi
        om2 = np.maximum(np.bincount(owner, x, n), 1e-6)
        np.multiply(pi, pi, out=x)
        pi2 = np.bincount(owner, x, n)
        del x
        # nước nhiều lượt thăm nhất mỗi node (hoà thì ô sau cùng, như lexsort bản trước) -> q, d của nhãn
        co_ml = ml > 0
        mx = np.zeros(n, np.float32)
        if so_o:
            mx[co_ml] = np.maximum.reduceat(ns, ms[co_ml])
        dinh = np.flatnonzero(ns == mx[owner])
        o = owner[dinh]
        cuoi = np.r_[o[1:] != o[:-1], True] if len(o) else np.zeros(0, bool)
        best = np.full(n, -1)
        best[o[cuoi]] = dinh[cuoi]
        del dinh, o, cuoi
        co_search = best >= 0
        b = np.maximum(best, 0)
        q_ben = np.where(co_search, Qs[b], 0.0) if so_o else np.zeros(n)
        d_ben = np.zeros(n)
        if so_o:
            np.divide(p["nd"][b], np.maximum(ns[b], 1e-12), out=d_ben, where=co_search & co_ns[b], dtype=np.float64)
        del Qs, co_ns
        # con đã chơi (sống hoặc gốc-cắt) của mỗi node, cùng pi của nước dẫn tới con: dò đoạn của cha từng ô một
        # (đoạn dài tối đa vài chục ô, mỗi nước một lần trong đoạn)
        con = np.where((a["cha"][:n] >= 0) & (a["trang"][:n] < 2))[0]
        cha = a["cha"][con]
        pi_con = np.zeros(len(con))
        dau_c, dai_c, nuoc_c = ms[cha], ml[cha], a["nuoc"][con]
        con_lai = np.flatnonzero(dai_c > 0)
        j = 0
        while con_lai.size:
            vt = dau_c[con_lai] + j
            trung = p["mv"][vt] == nuoc_c[con_lai]
            pi_con[con_lai[trung]] = pi[vt[trung]]
            j += 1
            con_lai = con_lai[~trung & (dai_c[con_lai] > j)]
        del dau_c, dai_c, nuoc_c, con_lai
        # kết quả ở lá (góc Trắng)
        G = np.zeros((n, 3))
        E = a["E"][:n].astype(np.float64).copy()
        G[:, 0], G[:, 1], G[:, 2] = a["Gw"][:n], a["Gd"][:n], a["Gl"][:n]
        cach = a["cach"][:n].astype(np.int64).copy()
        la = song & (a["het"][:n] > 0)
        z = a["z"][:n]
        G[la] = 0
        G[la & (z == 1), 0] = 1
        G[la & (z == 0), 1] = 1
        G[la & (z == -1), 2] = 1
        E[la], cach[la] = 0, 0
        rho = np.zeros(len(con))
        # từ dưới lên theo độ sâu: node sống, chưa hết ván, có con
        sau = a["sau"][:n]
        sau_cha = sau[cha]
        for muc in range(int(sau[:n].max(initial=0)), -1, -1):
            o = (sau_cha == muc) & song[cha] & (a["het"][cha] == 0)
            if not o.any():
                continue
            c, pc = con[o], cha[o]
            pi_c = pi_con[o]
            f = om2[pc] / (om2[pc] + E[c])
            A = np.bincount(pc, pi_c * f, n)
            B = np.bincount(pc, f, n)
            nu = (1 - A) / np.maximum(B, 1e-12)
            r = (pi_c + nu[pc]) * f
            rho[o] = r
            cha_muc = np.unique(pc)
            for j in range(3):
                G[cha_muc, j] = np.bincount(pc, r * G[c, j], n)[cha_muc]
            U = np.bincount(pc, (r - pi_c) ** 2, n) + pi2 - np.bincount(pc, pi_c ** 2, n)
            E[cha_muc] = (np.bincount(pc, r * r * E[c], n) + om2 * U)[cha_muc]
            # khoảng cách tới cuối ván dọc con có pi lớn nhất
            tt = np.lexsort((pi_c, pc))
            cu = np.r_[pc[tt][1:] != pc[tt][:-1], True]
            cach[pc[tt][cu]] = cach[c[tt][cu]] + 1
        for j, k in enumerate(("Gw", "Gd", "Gl")):
            a[k][:n] = np.where(song, G[:, j], a[k][:n])
        a["E"][:n] = np.where(song, E, a["E"][:n])
        a["cach"][:n] = np.where(song, cach, a["cach"][:n])
        self._tam = dict(owner=owner, slot=slot, pi=pi, om2=om2, q_ben=q_ben, d_ben=d_ben, co_search=co_search,
                         con=con, rho=rho, pi_con=pi_con)
        return self._tam

    def nhan(self, so_buoc):
        """Nhãn huấn luyện của mọi node sống đã search và có mặt phẳng (mau.npz). Trả về dict mảng + thống kê."""
        t, a, n = self._tam, self.a, self.n
        den = (a["sau"][:n] % 2 == 1)                       # bên đi là Đen ở độ sâu lẻ (từ thế khởi đầu)
        sg = np.where(den, -1.0, 1.0)
        G = np.stack([a["Gw"][:n], a["Gd"][:n], a["Gl"][:n]], 1).astype(np.float64)
        G_ben = np.where(den[:, None], G[:, ::-1], G)       # Đen đi: đổi thắng <-> thua
        q_wdl = np.stack([(1 + t["q_ben"] - t["d_ben"]) / 2, t["d_ben"], (1 - t["q_ben"] - t["d_ben"]) / 2], 1).clip(0, 1)
        song = (a["trang"][:n] == 0) & t["co_search"] & (a["het"][:n] == 0)
        # tau_q^2 từ node cách cuối ván <= 4 (7/11)
        gan = song & (a["cach"][:n] <= CACH_CUOI_TAU)
        G_s = (G[:, 0] - G[:, 2])
        q_trang = sg * t["q_ben"]
        tau = max(float(np.mean((G_s[gan] - q_trang[gan]) ** 2)) if gan.any() else 0.0, SAN_TAU_Q)
        E = a["E"][:n].astype(np.float64)
        if CONG_TAC["nhan_value_moi"]:
            wq = E / (E + tau)
        else:
            wq = np.full(n, 0.2)
        wdl = wq[:, None] * q_wdl + (1 - wq[:, None]) * G_ben
        chon = np.where(song & (a["mau_tep"][:n] >= 0))[0]
        # policy: trung bình pi các lần search (nhãn policy mới tắt)
        owner, slot, pi = t["owner"], t["slot"], t["pi"]
        # (pool gọn: owner đã tăng dần nên các ô được chọn tự xếp theo node, khỏi sắp lại; đếm bằng reduceat theo
        # đoạn, khỏi dựng mảng owner của ô được chọn -- mỗi mảng theo ô ~40 triệu phần tử, 8/11)
        la_chon = np.zeros(n, bool)
        la_chon[chon] = True
        co = la_chon[owner]
        co &= self.p["ns"][slot] > 0
        co_ml = a["ml"][:n] > 0
        dem_moi = np.zeros(n, np.int64)
        if co.size:
            dem_moi[co_ml] = np.add.reduceat(co.view(np.uint8), a["ms"][:n][co_ml], dtype=np.int64)
        dem = dem_moi[chon]
        mv2 = self.p["mv"][slot][co]
        # Gửi lên máy huấn luyện gọn hơn (8/11): pi lưu số nguyên 16 bit, tổng mỗi node đúng 65535 (làm tròn xuống rồi
        # cộng 1 cho các nước có phần lẻ lớn nhất), sai mỗi số < 1/65535 = 1.5e-5, nhỏ hơn độ mịn 1/800 của 800 lượt
        # thăm ~80 lần; độ dài đoạn mỗi node thay cho mảng chỉ số int64. Nén: 103 + 4.3 MB -> 74 + 1.7 MB ở đời 5.
        pi2 = np.empty(int(dem.sum()), np.float32)          # pi[co] theo từng khúc, khỏi tạo bản float64 cả mảng
        k = 0
        for dau in range(0, co.size, 1 << 23):
            x = pi[dau:dau + (1 << 23)][co[dau:dau + (1 << 23)]]
            pi2[k:k + len(x)] = x
            k += len(x)
        del co
        pol_q = _pi_uint16(pi2, dem)
        ra = {"tep": a["mau_tep"][chon], "hang": a["mau_hang"][chon], "den_di": den[chon].astype(np.uint8),
              "wdl": wdl[chon].astype(np.float32), "w": a["m"][chon].astype(np.float32),
              "pol_dem": dem.astype(np.uint8 if dem.max(initial=0) < 256 else np.uint16),
              "pol_mv": mv2.astype(np.uint16), "pol_q": pol_q,
              "so_buoc": np.int64(so_buoc)}
        tk = {"tau_q2": tau, "so_node_tau": int(gan.sum()), "so_mau": int(len(chon)),
              "wq_tb_theo_m": float((a["m"][chon] * wq[chon]).sum() / max(a["m"][chon].sum(), 1e-9)),
              "E_tb": float(E[chon].mean()) if len(chon) else 0.0,
              "omega2_tb": float(t["om2"][chon].mean()) if len(chon) else 0.0}
        return ra, tk

    # -- giảm, cắt (phần 8)
    def giam(self):
        a = self.a
        for k in ("m", "k", "gsum", "Nsum", "p0sum"):
            a[k][:self.n] *= GAMMA
        for k in ("ns", "nq", "nd"):
            self.p[k][:self.np_] *= GAMMA

    def cat_la(self, giu):
        """Cắt lá có m nhỏ nhất (8.3) cho tới khi còn `giu` node sống. Node bị cắt thành 'gốc-cắt' (giữ m, G, E
        của nó cho node cha, 8.2), con gốc-cắt của nó bị xoá. Trả về số node đã cắt."""
        import heapq
        a, n = self.a, self.n
        song = a["trang"][:n] == 0
        so_song = int(song.sum())
        can = so_song - giu
        if can <= 0:
            return 0
        so_con_song = np.bincount(a["cha"][:n][song & (a["cha"][:n] >= 0)], minlength=n)
        la = np.where(song & (so_con_song == 0) & (a["cha"][:n] >= 0))[0]
        h = list(zip(a["m"][la].tolist(), la.tolist()))
        heapq.heapify(h)
        con_cua = {}
        con = np.where(a["cha"][:n] >= 0)[0]
        for c, p_ in zip(con.tolist(), a["cha"][con].tolist()):
            con_cua.setdefault(p_, []).append(c)
        cat = 0
        while h and cat < can:
            _, s = heapq.heappop(h)
            if a["trang"][s] != 0 or so_con_song[s] != 0:
                continue
            a["trang"][s] = 1
            a["ml"][s] = 0
            a["mau_tep"][s] = -1
            for c in con_cua.get(s, []):
                a["trang"][c] = 2
            cat += 1
            p_ = int(a["cha"][s])
            so_con_song[p_] -= 1
            if p_ != 0 and so_con_song[p_] == 0:      # gốc không bao giờ bị cắt
                heapq.heappush(h, (float(a["m"][p_]), p_))
        return cat

    # -- quét, ưu tiên, việc (phần 6, 9)
    def lap_viec(self, doi_moi, ngan_sach, rng):
        t = self.tinh()
        a, n = self.a, self.n
        owner, slot = t["owner"], t["slot"]
        song = (a["trang"][:n] == 0) & (a["het"][:n] == 0) & t["co_search"]
        # quét: mỗi node bốc một nước theo ns^(1/T)
        w = self.p["ns"][slot].astype(np.float64)
        np.power(w, 1 / T_QUET, out=w)
        w[~song[owner]] = 0.0
        tong = np.bincount(owner, w, n)
        cum = np.cumsum(w)
        node_dau = np.full(n, -1.0)                  # đầu đoạn của mỗi node trong cum (pool gọn: ô đầu là ms)
        co_ml = a["ml"][:n] > 0
        d0 = a["ms"][:n][co_ml]
        node_dau[co_ml] = cum[d0] - w[d0]
        del w, d0
        nut = np.where(song & (tong > 0))[0]
        u = node_dau[nut] + rng.random(len(nut)) * tong[nut]
        chon = np.searchsorted(cum, u, side="right")
        chon = np.minimum(chon, len(cum) - 1)
        mv = self.p["mv"][slot][chon]
        da_choi = np.array([(int(s) * 65536 + int(m)) in self.con for s, m in zip(nut, mv)], bool)
        diem = list(zip(nut[~da_choi].tolist(), mv[~da_choi].tolist()))
        rng.shuffle(diem)
        e = float(self.meta.get("evals_moi_search", EVALS_MOI_SEARCH))
        # search lại theo ưu tiên (9.2, sửa 5/11)
        viec_s = []
        if CONG_TAC["search_lai"]:
            k = np.maximum(a["k"][:n].astype(np.float64), 1e-9)
            tuoi = doi_moi - a["gsum"][:n] / k
            dl = self._delta_bang()
            dhat = np.array([dl(tu, kk) for tu, kk in zip(tuoi[song], k[song])])
            ut = a["m"][:n][song] * dhat / (k[song] + 1)
            idx = np.where(song)[0]
            thu = np.argsort(-ut)
            gioi = int(TRAN_SEARCH_LAI * ngan_sach / e)
            for j in thu[:gioi]:
                s = idx[j]
                if k[s] >= a["m"][s] and tuoi[s] < 1:
                    continue
                viec_s.append(int(s))
        # ván rẽ: tới khi ước chi phí đủ ngân sách còn lại (lập dư DU_VIEC lần)
        con_lai = ngan_sach * DU_VIEC - len(viec_s) * e
        viec_g, chi_g = [], []
        for s, m in diem:
            if con_lai <= 0:
                break
            cp = (a["cach"][s] + 1) * e
            viec_g.append((s, m))
            chi_g.append(cp)
            con_lai -= cp
        # trộn đều S và G
        tat = [("S", s, None, e) for s in viec_s] + [("G", s, m, c) for (s, m), c in zip(viec_g, chi_g)]
        rng.shuffle(tat)
        return tat, {"so_diem_re": len(diem), "so_viec_s": len(viec_s), "so_viec_g": len(viec_g)}

    def _delta_bang(self):
        bang = {k: v[0] / v[1] for k, v in self.meta["delta"].items() if v[1] >= 30}
        tb_do = np.mean(list(bang.values())) if bang else None

        def f(tuoi, k):
            khoa = f"{min(int(max(tuoi, 0)), 9)}_{min(int(k), 9)}"
            if khoa in bang:
                return bang[khoa]
            mac_dinh = max(tuoi, 0) + 1
            return mac_dinh * (tb_do / 2.5 if tb_do else 1.0)
        return f

    def duong(self, s):
        ra = []
        while self.a["cha"][s] >= 0:
            ra.append(int(self.a["nuoc"][s]))
            s = int(self.a["cha"][s])
        return ra[::-1]


# ---------------------------------------------------------------- lệnh
def thu_muc_cay(cach):
    return os.path.join(cach, "cay")


def cap_nhat(cach, g):
    t0 = time.time()
    tm = thu_muc_cay(cach)
    _cho_don(tm)                                         # bước dồn mặt phẳng chạy nền (sau sau_hl) phải xong trước
    c = Cay.nap(tm)
    c.meta["goc_cach"] = cach
    c.meta["doi"] = g
    gd = os.path.join(cach, f"games_gen{g}")
    lan = sorted(d for d in os.listdir(gd) if os.path.isdir(os.path.join(gd, d))) if os.path.isdir(gd) else []
    moi = so_s = so_v = 0
    for d in lan:
        key = f"games_gen{g}/{d}"
        if key in c.meta["da_nap"]:
            continue
        a, b, v = c.nap_lan(os.path.join(gd, d), g)
        moi, so_s, so_v = moi + a, so_s + b, so_v + v
        c.meta["da_nap"].append(key)
    c.meta["moi_moi_doi"][str(g)] = c.meta["moi_moi_doi"].get(str(g), 0) + moi
    # lần chạy mạng trung bình mỗi lần search, đo trên các lần sinh của đời này (xong.json của sinh.py)
    ev = 0
    for d in lan:
        try:
            with open(os.path.join(gd, d, "xong.json"), encoding="utf-8") as fj:
                ev += int(json.load(fj)["evals"])
        except (OSError, ValueError, KeyError):
            pass
    if ev and so_s:
        c.meta["evals_moi_search"] = ev / so_s
    c.nen()                                              # tinh cần pool gọn (gộp xong thì đoạn mới nằm cuối pool)
    c.tinh()
    so_buoc = _so_buoc_tt(cach, g) or max(1, int((c.a["trang"][:c.n] == 0).sum()) // 1024)
    nh, tk = c.nhan(so_buoc)
    ra = os.path.join(cach, f"nhan_doi{g}.npz")
    np.savez_compressed(ra[:-4] + ".tam.npz", **nh)
    os.replace(ra[:-4] + ".tam.npz", ra)
    # Các tệp mau.npz cần tải lên máy huấn luyện: "<chỉ số>\t<đường dẫn tương đối trong thư mục cách>"
    can_tep = [(i, c.meta["tep_mau"][i]) for i in np.unique(nh["tep"]).tolist()]
    # Kho đệm (kho.py, 8/11): mau.npz đã có trên Release thì không gửi lại. .tep.txt (vòng lặp gói đúng các tệp ở cột
    # 2) chỉ còn tệp gửi thẳng, cộng dòng "-1 nhan_doi<G>.kho.txt": ô 07 tải các tệp trong đó rồi ghép lại .tep.txt.
    lay = []
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import kho
        muc = [(t, os.path.join(cach, t)) for _, t in can_tep]
        _, lay = kho.chia(cach, "cay", muc)
        kho.khoi_len(cach, "cay", g, muc)
    except Exception as e:                           # thiếu kho.py / lỗi bất kỳ: gửi thẳng tất cả như trước
        print(f"(kho đệm: {e} -- gửi thẳng tất cả)", file=sys.stderr)
    trong_kho = {a: (t, kt) for a, t, kt in lay}
    with open(os.path.join(cach, f"nhan_doi{g}.kho.txt"), "w", encoding="utf-8") as f:
        f.write("".join(f"{i}\t{p}\t{trong_kho[p][0]}\t{trong_kho[p][1]}\n" for i, p in can_tep if p in trong_kho))
    with open(os.path.join(cach, f"nhan_doi{g}.tep.txt"), "w", encoding="utf-8") as f:
        f.write("".join(f"{i}\t{t}\n" for i, t in can_tep if t not in trong_kho) + (f"-1\tnhan_doi{g}.kho.txt\n" if lay else ""))
    tk.update({"doi": g, "node_moi": moi, "search": so_s, "van": so_v, "so_node": int(c.n),
               "so_node_song": int((c.a["trang"][:c.n] == 0).sum()), "so_buoc": so_buoc, "giay": round(time.time() - t0, 1),
               "so_tep_mau": len(can_tep), "kho_lay": len(lay), "kho_lay_mb": round(sum(x[2] for x in lay) / 1e6)})
    c.meta["nhat_ky"].append(tk)
    c.luu(tm)
    print(json.dumps(tk, ensure_ascii=False))


def _so_buoc_tt(cach, g):
    """Số bước huấn luyện của cách truyền thống ở cùng đời (12.6: hai bên cùng số bước)."""
    f = os.path.join(os.path.dirname(os.path.abspath(cach)), "tt", f"gen{g + 1}.hl.json")
    try:
        with open(f, encoding="utf-8") as fj:
            return int(json.load(fj)["so_buoc"])
    except (OSError, ValueError, KeyError):
        return 0


def sau_hl(cach, g, ngan_sach):
    tm = thu_muc_cay(cach)
    _cho_don(tm)
    c = Cay.nap(tm)
    c.giam()
    moi = c.meta["moi_moi_doi"]
    giu = sum(moi.get(str(k), 0) for k in range(g - W_DOI + 1, g + 1))
    cat = c.cat_la(giu) if g >= W_DOI - 1 else 0
    c.nen()
    rng = np.random.default_rng()
    tat, tk = c.lap_viec(g + 1, ngan_sach, rng)
    with open(os.path.join(cach, f"viec_doi{g + 1}.txt.tam"), "w") as f, \
            open(os.path.join(cach, f"viec_doi{g + 1}.chi_phi.tam"), "w") as fc:
        for i, (loai, s, m, cp) in enumerate(tat):
            d = " ".join(sang_uci(x) for x in c.duong(s) + ([m] if m is not None else []))
            f.write(f"S {i} {d}\n" if loai == "S" else f"G {i} 0 {d}\n")
            fc.write(f"{int(cp)}\n")
    for duoi in ("txt", "chi_phi"):
        os.replace(os.path.join(cach, f"viec_doi{g + 1}.{duoi}.tam"), os.path.join(cach, f"viec_doi{g + 1}.{duoi}"))
    with open(os.path.join(cach, f"viec_doi{g + 1}.con_tro"), "w") as f:
        f.write("0\n")
    tk.update({"doi": g, "cat": cat, "giu": giu, "so_node": int(c.n)})
    c.meta["nhat_ky"].append({"sau_hl": tk})
    c.luu(tm)
    print(json.dumps(tk, ensure_ascii=False))
    del c
    _mo_nen(cach, ["don_mau", cach, str(g)])


# ---------------------------------------------------------------- dồn mặt phẳng (9/11)
# Mặt phẳng của một node nằm trong mau.npz của lần sinh đã tạo ra nó; tệp còn phải giữ (trên điện thoại và trong kho
# đệm trên Release) chừng nào còn một node của nó sống. Đời 8: 46 tệp 490 MB, tệp của đời 1-5 chỉ còn dùng 29-36%,
# và mỗi tệp cũ còn mang policy / giá trị của search mà cách cây không dùng (12.9 MB, phần cần 3.9 MB). Sau mỗi sau_hl,
# một tiến trình nền dồn các hàng còn dùng của tệp "đáng dồn" (còn mang pt_* hoặc dùng < DON_DUOI) sang tệp mới chỉ có
# MAT_PHANG (mỗi tệp tối đa DON_HANG hàng), cho node trỏ sang đó, đưa tệp mới lên kho; tệp cũ không còn node nào trỏ
# tới thì đời sau kho tự xoá. Tệp gốc trên điện thoại giữ nguyên. Khoá cay/.dang_don: cap_nhat / sau_hl đợi nó xong.
MAT_PHANG = ("bit", "phu", "r50", "hl_off", "hl")
DON_DUOI = 0.5
DON_HANG = 300_000


def _mo_nen(cach, lenh):
    import subprocess
    try:
        log = open(os.path.join(os.path.dirname(os.path.abspath(cach)), "log", "kho.log"), "a", encoding="utf-8")
        subprocess.Popen([sys.executable, os.path.abspath(__file__), *lenh], stdin=subprocess.DEVNULL, stdout=log,
                         stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
    except OSError as e:
        print(f"[!] không mở được {lenh[0]} chạy nền: {e}", file=sys.stderr)


def _cho_don(tm, toi_da=3600):
    f = os.path.join(tm, ".dang_don")
    han = time.time() + toi_da
    while os.path.exists(f) and time.time() < han:
        try:
            if not os.path.exists(f"/proc/{int(open(f).read())}"):
                break
        except (OSError, ValueError):
            break
        time.sleep(5)


def _ghi(*a):
    print(time.strftime("%Y-%m-%d %H:%M:%S"), "[dồn mặt phẳng]", *a, flush=True)


def don_mau(cach, g):
    tm = thu_muc_cay(cach)
    khoa = os.path.join(tm, ".dang_don")
    _cho_don(tm, 0)
    with open(khoa, "w") as f:
        f.write(str(os.getpid()))
    try:
        t0 = time.time()
        c = Cay.nap(tm)
        n, a = c.n, c.a
        tep, hang = a["mau_tep"][:n], a["mau_hang"][:n]
        co = np.flatnonzero(tep >= 0)
        dung = np.bincount(tep[co], minlength=len(c.meta["tep_mau"]))
        chon, tong_cu = [], 0
        for i in np.flatnonzero(dung).tolist():
            p = os.path.join(cach, c.meta["tep_mau"][i])
            try:
                with np.load(p) as z:
                    du = "pt_p" in z.files
                    so = len(z["phu"])
            except (OSError, ValueError, KeyError) as e:
                _ghi(f"đời {g}: không đọc được {c.meta['tep_mau'][i]} ({e}) -- bỏ qua tệp này")
                continue
            if du or dung[i] < DON_DUOI * so:
                chon.append(i)
                tong_cu += os.path.getsize(p)
        if not chon:
            _ghi(f"đời {g}: không có tệp nào đáng dồn ({len(np.flatnonzero(dung))} tệp)")
            return
        # node theo (tệp cũ, hàng cũ): mỗi tệp cũ nạp một lần, các hàng chép theo thứ tự
        node = co[np.isin(tep[co], chon)]
        node = node[np.lexsort((hang[node], tep[node]))]
        os.makedirs(os.path.join(cach, "nen_mau"), exist_ok=True)
        moi_tep, khuc, so_khuc = [], {k: [] for k in MAT_PHANG + ("hl_dai",)}, 0
        tep_moi = np.empty(len(node), np.int32)
        hang_moi = np.empty(len(node), np.int32)
        vi = 0

        def xa_khuc():
            nonlocal khuc, so_khuc
            if not so_khuc:
                return
            hl_dai = np.concatenate(khuc["hl_dai"])
            ra = {"bit": np.concatenate(khuc["bit"]), "phu": np.concatenate(khuc["phu"]),
                  "r50": np.concatenate(khuc["r50"]),
                  "hl_off": np.concatenate(([0], np.cumsum(hl_dai))).astype(np.int64), "hl": np.concatenate(khuc["hl"])}
            ten = f"nen_mau/doi{g}_{len(moi_tep)}.npz"
            while os.path.exists(os.path.join(cach, ten)) or ten in c.meta["tep_mau"]:
                ten = ten[:-4] + "b.npz"
            p = os.path.join(cach, ten)
            np.savez_compressed(p[:-4] + ".tam.npz", **ra)
            os.replace(p[:-4] + ".tam.npz", p)
            moi_tep.append(ten)
            khuc, so_khuc = {k: [] for k in MAT_PHANG + ("hl_dai",)}, 0

        dau = 0
        while dau < len(node):
            i = int(tep[node[dau]])
            cuoi = dau + int(np.searchsorted(tep[node[dau:]], i, side="right"))
            h = hang[node[dau:cuoi]].astype(np.int64)
            with np.load(os.path.join(cach, c.meta["tep_mau"][i])) as z:
                off, hl = z["hl_off"], z["hl"]
                bit, phu, r50 = z["bit"], z["phu"], z["r50"]
            vt0 = 0
            while vt0 < len(h):
                k = min(DON_HANG - so_khuc, len(h) - vt0)      # không vượt chỗ còn trống của khúc đang gom
                hh = h[vt0:vt0 + k]
                khuc["bit"].append(bit[hh])
                khuc["phu"].append(phu[hh])
                khuc["r50"].append(r50[hh])
                dai = (off[hh + 1] - off[hh]).astype(np.int64)
                khuc["hl_dai"].append(dai)
                khuc["hl"].append(hl[np.repeat(off[hh] - (np.cumsum(dai) - dai), dai) + np.arange(int(dai.sum()))])
                tep_moi[vi:vi + k] = len(c.meta["tep_mau"]) + len(moi_tep)
                hang_moi[vi:vi + k] = so_khuc + np.arange(k)
                vi += k
                so_khuc += k
                vt0 += k
                if so_khuc >= DON_HANG:
                    xa_khuc()
            del off, hl, bit, phu, r50
            dau = cuoi
        xa_khuc()
        assert vi == len(node)
        a["mau_tep"][node] = tep_moi
        a["mau_hang"][node] = hang_moi
        c.meta["tep_mau"].extend(moi_tep)
        c.meta["nhat_ky"].append({"don_mau": {"doi": g, "tep_cu": len(chon), "tep_moi": len(moi_tep), "hang": int(len(node))}})
        c.luu(tm)
        mb_moi = sum(os.path.getsize(os.path.join(cach, t)) for t in moi_tep) / 1e6
        _ghi(f"đời {g}: {len(chon)} tệp ({tong_cu / 1e6:.0f} MB) -> {len(moi_tep)} tệp ({mb_moi:.0f} MB), "
             f"{len(node)} hàng, {time.time() - t0:.0f} giây")
        del c
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import kho
            kho.dua_len(cach, "cay", [(t, os.path.join(cach, t)) for t in moi_tep], f"dồn mặt phẳng đời {g}")
        except Exception as e:
            _ghi(f"đời {g}: chưa đưa được lên kho ({e}) -- đời sau gửi thẳng")
    finally:
        try:
            os.remove(khoa)
        except OSError:
            pass


TOC_MAC_DINH = 16000      # lần chạy mạng mỗi giây của một T4 khi chưa đo được (cách truyền thống đo 15 400)


def toc_do_may(cach, g):
    """Lần chạy mạng mỗi giây của một máy cách này: lớn nhất trong các lần chạy đã tải về của đời g, không có thì
    đời g - 1 (xong.json: evals / giay)."""
    for d in (g, g - 1):
        toc = []
        thu = os.path.join(cach, f"games_gen{d}")
        for ten in (os.listdir(thu) if os.path.isdir(thu) else []):
            try:
                with open(os.path.join(thu, ten, "xong.json"), encoding="utf-8") as f:
                    t = json.load(f)
                if t.get("giay", 0) > 600:
                    toc.append(t["evals"] / t["giay"])
            except (OSError, ValueError, KeyError):
                pass
        if toc:
            return max(toc)
    return TOC_MAC_DINH


def giay_may_tu_o(thu_muc=os.path.expanduser("~/.fz_tk/.cv_tu_dong")):
    """Vòng lặp mở trước bản sửa 7/11 không truyền số giây: đọc SECS của ô 04 nó vừa ghi (trong 120 giây) + 400."""
    import glob
    import re
    moi = [(os.path.getmtime(f), f) for f in glob.glob(os.path.join(thu_muc, "o_*", "04_*.py"))]
    moi = [x for x in moi if time.time() - x[0] < 120]
    if not moi:
        return None
    m = re.search(r"^SECS\s*=\s*(\d+)", open(max(moi)[1], encoding="utf-8").read(), re.M)
    return int(m.group(1)) + 400 if m else None


def so_cua_so(thu_muc=os.path.expanduser("~/.fz_tk/.cv_tu_dong")):
    """Số cửa sổ vòng lặp đang chạy: mỗi cửa sổ giữ một tệp w_<pid> (cập nhật mỗi bước), tiến trình còn sống."""
    import glob
    n = 0
    for f in glob.glob(os.path.join(thu_muc, "w_*")):
        try:
            os.kill(int(f.rsplit("_", 1)[1]), 0)
            n += 1
        except (ValueError, OSError):
            pass
    return max(1, n)


def lay_viec(cach, g, giao, ra, giay=None):
    """Nhận phần việc kế tiếp (khoá thư mục), đủ ước chi phí >= giao. In số việc; 0 = hết việc.
    giay = số giây máy còn chạy được: phần nhận không quá 1,3 lần số máy chạy kịp (tốc độ đo được x giây). Việc nhận
    mà không nạp kịp thì mất, nên trước bản sửa 7/11 một máy còn 20 phút đã nhận 2/3 danh sách việc đời 1 (193 triệu
    trong khi chỉ chạy kịp cỡ 15 triệu). Nhận thiếu thì máy hết việc sớm và tự quét ván của nó -- vẫn là việc hợp lệ."""
    if giay is None:
        giay = giay_may_tu_o()
    if giay:
        giao = min(giao, int(1.3 * toc_do_may(cach, g) * giay))
    # Chờ danh sách việc của đời g (đời >= 1): cửa sổ huấn luyện chuyển đời rồi mới lập danh sách (sau_hl, gần 2 phút),
    # nên cửa sổ khác có thể tới nhận trước khi có tệp (8/11 đời 3: một máy nhận "hết việc" 10 giây trước khi danh sách
    # xong, rồi tự quét suốt 255 phút). Quá 8 phút vẫn chưa có (sau_hl hỏng) thì nhận 0 như cũ -- máy tự quét; chờ
    # lâu hơn thì máy đang giữ có thể bị Colab thu hồi, vì lúc này vòng lặp không nối ssh.
    f_viec = os.path.join(cach, f"viec_doi{g}.txt")
    if g >= 1:
        for _ in range(48):
            if os.path.exists(f_viec) and os.path.exists(os.path.join(cach, f"viec_doi{g}.con_tro")):
                break
            time.sleep(10)
    khoa = os.path.join(cach, f"viec_doi{g}.khoa")
    for _ in range(600):
        try:
            os.mkdir(khoa)
            break
        except FileExistsError:
            time.sleep(0.5)
    else:
        sys.exit("khoá việc treo")
    try:
        if not os.path.exists(f_viec):
            open(ra, "w").close()
            print(0)
            return
        dong = open(f_viec).read().splitlines()
        cp = [int(x) for x in open(os.path.join(cach, f"viec_doi{g}.chi_phi")).read().split()]
        f_ct = os.path.join(cach, f"viec_doi{g}.con_tro")
        dau = int(open(f_ct).read().strip() or 0)
        # Chia đều phần còn lại của danh sách cho các cửa sổ đang chạy: máy nhận trước không ôm hết, máy đến sau vẫn
        # còn việc (7/11 đời 1: ba máy đầu nhận theo sức chạy, hết danh sách khi máy thứ tư tới, máy đó phải chơi
        # ván từ gốc trong khi việc của ba máy kia thừa và sẽ mất khi đủ ngân sách).
        giao = min(giao, sum(cp[dau:]) // so_cua_so() + 1)
        cuoi, tong = dau, 0
        while cuoi < len(dong) and tong < giao:
            tong += cp[cuoi]
            cuoi += 1
        # Dòng đầu "# e <lần chạy mạng mỗi search> g <chi phí trung bình một ván rẽ của phần này>": sinh.py ước phần
        # còn lại của việc đang dở bằng hai số này (bộ đếm của engine gồm cả việc dở nên không chia ra được).
        e = EVALS_MOI_SEARCH
        try:
            with open(os.path.join(thu_muc_cay(cach), "cay.json"), encoding="utf-8") as fj:
                e = float(json.load(fj).get("evals_moi_search", e))
        except (OSError, ValueError):
            pass
        cp_g = [cp[i] for i in range(dau, cuoi) if dong[i].startswith("G ")]
        g_tb = sum(cp_g) / len(cp_g) if cp_g else 0
        with open(ra, "w") as f:
            if cuoi > dau:
                f.write(f"# e {e:.1f} g {g_tb:.0f}\n")
            f.write("\n".join(dong[dau:cuoi]) + ("\n" if cuoi > dau else ""))
        with open(f_ct + ".tam", "w") as f:
            f.write(f"{cuoi}\n")
        os.replace(f_ct + ".tam", f_ct)
        print(cuoi - dau)
    finally:
        os.rmdir(khoa)


def tinh_trang(cach):
    c = Cay.nap(thu_muc_cay(cach))
    song = int((c.a["trang"][:c.n] == 0).sum())
    print(json.dumps({"doi": c.meta["doi"], "so_node": c.n, "so_node_song": song,
                      "moi_moi_doi": c.meta["moi_moi_doi"], "cuoi": c.meta["nhat_ky"][-2:]}, ensure_ascii=False))


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == "cap_nhat":
        cap_nhat(a[1], int(a[2]))
    elif a[0] == "sau_hl":
        sau_hl(a[1], int(a[2]), int(a[3]))
    elif a[0] == "lay_viec":
        lay_viec(a[1], int(a[2]), int(a[3]), a[4], int(a[5]) if len(a) > 5 else None)
    elif a[0] == "tinh_trang":
        tinh_trang(a[1])
    elif a[0] == "don_mau":
        don_mau(a[1], int(a[2]))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
