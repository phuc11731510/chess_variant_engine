"""cay_moi.py -- cách cây theo phương pháp mới của mục 12 (SUY_RA_CONG_THUC.md), viết theo mảng. Lớp CayMoi kế thừa Cay
(cay.py) và thêm:

  - mỗi node nhớ các ván thuần đi qua nó: tổng trọng số kết quả (zs), tổng trọng số (ws), tổng bình phương trọng số (ws2),
    cùng giá trị search LÚC CHƠI của ván thuần mới nhất tại node (q_ch, d_ch, chia_ch = tỉ lệ lượt thăm của nước nhiều
    nhất, doi_q = đời của lần search đó) và Q lúc chơi của từng nước (qp, theo ô pool);
  - re = 1 ở node con sinh ra từ ván rẽ có nước ép (nhánh rẽ), khác node con của chính ván thuần.

Giai đoạn A (file này): nap_lan viết theo mảng. Khi dữ liệu không có ván lặp, cây ra giống cây của Cay.nap_lan (cay.py) từng
node: cùng số node, cùng số lượt thăm từng nước (cộng float32 theo đúng thứ tự gặp), cùng m, k, gsum, Nsum, p0sum, z, het,
mau_tep, mau_hang.
"""
import gzip
import os

import numpy as np

import cay as C

NODE2 = dict(C.NODE)
NODE2.update({
    "zs": (np.float32, 0), "ws": (np.float32, 0), "ws2": (np.float32, 0),      # ván thuần: sum w z (góc Trắng), sum w, sum w^2
    "q_ch": (np.float32, 0), "d_ch": (np.float32, 0),                         # search lúc chơi của ván thuần mới nhất (góc bên đi)
    "chia_ch": (np.float32, 0), "doi_q": (np.int16, -1),                      # tỉ lệ lượt thăm nước nhiều nhất; đời của search đó
    "re": (np.int8, 0),                                                       # 1 = con sinh ra từ ván rẽ có nước ép
})
POOL2 = dict(C.POOL)
POOL2["qp"] = (np.float32, np.nan)                                            # Q lúc chơi của nước (ván thuần mới nhất tại node)


class CayMoi(C.Cay):
    NODE = NODE2
    POOL = POOL2

    def _tao_con(self, s, m, doi):
        """Tạo node con (s, m); gọi khi chắc chắn chưa có."""
        a = self.a
        c = self._them_node()
        a["cha"][c], a["nuoc"][c], a["sau"][c], a["doi_tao"][c] = s, m, a["sau"][s] + 1, doi
        self.con[s * 65536 + m] = c
        return c

    def _o_cua(self, nut):
        """(khoá node*65536+nước, chỉ số ô) của mọi ô thuộc các node trong `nut` (mảng node duy nhất)."""
        a, p = self.a, self.p
        ml = a["ml"][nut].astype(np.int64)
        tong = int(ml.sum())
        dau_o = np.cumsum(ml) - ml
        trong = np.arange(tong, dtype=np.int64) - np.repeat(dau_o, ml)
        o = np.repeat(a["ms"][nut].astype(np.int64), ml) + trong
        khoa = np.repeat(nut.astype(np.int64), ml) * 65536 + p["mv"][o]
        return khoa, o

    def nap_lan(self, thu_muc_lan, doi):
        """Gộp một lần sinh (thư mục chứa van.bin.gz và mau.npz) vào cây, theo mảng. Trả về (số node mới, số search, số ván)."""
        with gzip.open(os.path.join(thu_muc_lan, "van.bin.gz"), "rb") as f:
            ds = C.doc_ban_ghi(f.read())
        tep = len(self.meta["tep_mau"])
        self.meta["tep_mau"].append(os.path.relpath(os.path.join(thu_muc_lan, "mau.npz"), self.meta.get("goc_cach", ".")).replace(os.sep, "/"))
        a, con = self.a, self.con
        n0 = self.n
        goc = self.goc()
        # ---- 1. đi đường, tạo node (tuần tự: số hiệu node phải theo thứ tự gặp như bản cũ)
        s_nut, s_van, s_N, s_bq, s_bd, s_p0, s_tham = [], [], [], [], [], [], []
        duong_m = []              # node của mọi đường đi (đầu + nước đã chơi) của các ván, để cộng m
        van_z, van_re = [], []    # kết quả (góc Trắng) và "node đầu chơi được tạo mới" của từng ván
        delta = []
        so_van = 0
        for loai, kq, kt, dd, lan in ds:
            if loai == 2:
                continue
            s = goc
            duong = [goc]
            ok = True
            moi_cuoi = False
            tao = (loai == 0)
            for m in dd:
                s2 = con.get(s * 65536 + m)
                moi_cuoi = False
                if s2 is None:
                    if not tao:
                        ok = False
                        break
                    s2 = self._tao_con(s, m, doi)
                    moi_cuoi = True
                s = s2
                duong.append(s)
            if not ok:
                continue
            if loai == 1:
                nuoc, N, bq, bd, p0, tham = lan[0]
                if a["k"][s] > 0:
                    mv_cu, pi_cu = self.pi_cua(s)
                    pi_moi = tham["n"].astype(np.float64) / max(tham["n"].sum(), 1)
                    tat = dict(zip(mv_cu.tolist(), pi_cu.tolist()))
                    for x, y in zip(tham["nuoc"].tolist(), pi_moi.tolist()):
                        tat[x] = tat.get(x, 0.0) - y
                    tuoi = doi - a["gsum"][s] / a["k"][s]
                    delta.append((float(tuoi), float(a["k"][s]), 0.5 * sum(abs(v) for v in tat.values())))
                s_nut.append(s); s_van.append(-1); s_N.append(N); s_bq.append(bq); s_bd.append(bd); s_p0.append(p0); s_tham.append(tham)
                continue
            so_van += 1
            van = len(van_z)
            van_z.append(kq if kt == 0 else 0)
            van_re.append(moi_cuoi and len(dd) > 0)
            nut_dau = s
            for nuoc, N, bq, bd, p0, tham in lan:
                s_nut.append(s); s_van.append(van); s_N.append(N); s_bq.append(bq); s_bd.append(bd); s_p0.append(p0); s_tham.append(tham)
                s2 = con.get(s * 65536 + nuoc)
                if s2 is None:
                    s2 = self._tao_con(s, nuoc, doi)
                s = s2
                duong.append(s)
            a["het"][s] = 1 if kt == 0 else 2
            a["z"][s] = kq if kt == 0 else 0
            duong_m.extend(duong)
            if van_re[-1]:
                a["re"][nut_dau] = 1
        for tuoi, k, d in delta:
            khoa = f"{min(int(tuoi), 9)}_{min(int(k), 9)}"
            t = self.meta["delta"].setdefault(khoa, [0.0, 0])
            t[0] += d
            t[1] += 1
        so_search = len(s_nut)
        if so_search == 0:
            return self.n - n0, 0, so_van
        # ---- 2. mảng cho cả lô
        nut = np.asarray(s_nut, dtype=np.int64)
        van = np.asarray(s_van, dtype=np.int64)
        la_van = van >= 0
        dai = np.fromiter((len(t) for t in s_tham), dtype=np.int64, count=so_search)
        # mỗi phần tử tham có 12 byte = 6 số 16 bit (nuoc, n, q, d, p_nhieu, p_tho; q, d là float16): nối các bản xem
        # uint16 rồi tách cột, nhanh hơn nhiều so với np.concatenate trên mảng có trường (mỗi mảng một lần xét kiểu)
        th = np.concatenate([t.view(np.uint16) for t in s_tham]).reshape(-1, 6)
        t_mv = th[:, 0].astype(np.int64)
        t_n = th[:, 1].astype(np.float32)
        qd = np.ascontiguousarray(th[:, 2:4]).view(np.float16)
        t_q = qd[:, 0].astype(np.float32)
        t_d = qd[:, 1].astype(np.float32)
        t_ls = np.repeat(np.arange(so_search), dai)         # search chứa mỗi phần tử tham
        t_nut = nut[t_ls]
        khoa = t_nut * 65536 + t_mv
        # ---- 3. nới đoạn của các node có nước mới (nước mới xếp theo lần gặp đầu tiên, như bản cũ)
        u = np.unique(nut)
        e_khoa, _ = self._o_cua(u)
        uk, dau = np.unique(khoa, return_index=True)
        moi = ~np.isin(uk, e_khoa)
        k_moi, d_moi = uk[moi], dau[moi]
        if len(k_moi):
            o = np.lexsort((d_moi, k_moi >> 16))             # theo node, rồi theo lần gặp đầu
            k_moi = k_moi[o]
            nd_moi = k_moi >> 16
            ext, cnt = np.unique(nd_moi, return_counts=True)
            ml_cu = a["ml"][ext].astype(np.int64)
            ml_moi = ml_cu + cnt
            goc_pool = self._them_pool(int(ml_moi.sum()))
            ms_moi = goc_pool + np.cumsum(ml_moi) - ml_moi
            p = self.p
            # chép đoạn cũ sang đoạn mới
            tong_cu = int(ml_cu.sum())
            if tong_cu:
                dau_cu = np.cumsum(ml_cu) - ml_cu
                trong = np.arange(tong_cu, dtype=np.int64) - np.repeat(dau_cu, ml_cu)
                nguon = np.repeat(a["ms"][ext].astype(np.int64), ml_cu) + trong
                dich = np.repeat(ms_moi, ml_cu) + trong
                for k in self.POOL:
                    p[k][dich] = p[k][nguon]
            # nước mới nối vào cuối đoạn
            dau_nd = np.cumsum(cnt) - cnt
            thu_tu = np.arange(len(k_moi), dtype=np.int64) - np.repeat(dau_nd, cnt)
            vt = np.repeat(ms_moi + ml_cu, cnt) + thu_tu
            p["mv"][vt] = (k_moi & 65535).astype(np.uint16)
            a["ms"][ext], a["ml"][ext] = ms_moi, ml_moi
        p = self.p
        # ---- 4. cộng lượt thăm, tổng Q, tổng xác suất hoà vào các ô
        e_khoa, e_o = self._o_cua(u)
        so = np.argsort(e_khoa)
        vi = np.searchsorted(e_khoa[so], khoa)
        o_cua_t = e_o[so][vi]
        assert (e_khoa[so][vi] == khoa).all()
        np.add.at(p["ns"], o_cua_t, t_n)
        np.add.at(p["nq"], o_cua_t, t_n * t_q)
        np.add.at(p["nd"], o_cua_t, t_n * t_d)
        # ---- 5. số liệu mỗi node theo search
        np.add.at(a["k"], nut, np.float32(1))
        np.add.at(a["gsum"], nut, np.float32(doi))
        np.add.at(a["Nsum"], nut, np.asarray(s_N, dtype=np.float32))
        np.add.at(a["p0sum"], nut, np.asarray(s_p0, dtype=np.float32))
        if duong_m:
            np.add.at(a["m"], np.asarray(duong_m, dtype=np.int64), np.float32(1))
        # ---- 6. mặt phẳng: lần search đầu tiên của ván tại node chưa có mẫu
        gv = np.flatnonzero(la_van)
        hang = np.arange(len(gv), dtype=np.int64)            # thứ tự search của ván trong lô (như biến hang của bản cũ)
        nut_gv = nut[gv]
        _, dau_gv = np.unique(nut_gv, return_index=True)
        dau_gv = dau_gv[a["mau_tep"][nut_gv[dau_gv]] < 0]
        a["mau_tep"][nut_gv[dau_gv]] = tep
        a["mau_hang"][nut_gv[dau_gv]] = hang[dau_gv]
        # ---- 7. ván thuần: tổng trọng số kết quả, search lúc chơi mới nhất
        if len(gv):
            z_gv = np.asarray(van_z, dtype=np.float32)[van[gv]]
            np.add.at(a["zs"], nut_gv, z_gv)
            np.add.at(a["ws"], nut_gv, np.float32(1))
            np.add.at(a["ws2"], nut_gv, np.float32(1))
            # search mới nhất của mỗi node (lần cuối trong lô)
            _, d_cuoi = np.unique(nut_gv[::-1], return_index=True)
            cuoi = gv[len(gv) - 1 - d_cuoi]                  # chỉ số search (trong lô) của search mới nhất mỗi node
            nc = nut[cuoi]
            dau_s = np.cumsum(dai) - dai
            tong_n = np.add.reduceat(t_n, dau_s)
            max_n = np.maximum.reduceat(t_n, dau_s)
            a["q_ch"][nc] = np.asarray(s_bq, dtype=np.float32)[cuoi]
            a["d_ch"][nc] = np.asarray(s_bd, dtype=np.float32)[cuoi]
            a["chia_ch"][nc] = (max_n[cuoi] / np.maximum(tong_n[cuoi], 1)).astype(np.float32)
            a["doi_q"][nc] = doi
            # Q lúc chơi từng nước: xoá đoạn cũ của node rồi ghi Q của search mới nhất
            kc, oc = self._o_cua(nc)
            p["qp"][oc] = np.nan
            la_cuoi = np.zeros(so_search, bool)
            la_cuoi[cuoi] = True
            m_t = la_cuoi[t_ls]
            p["qp"][o_cua_t[m_t]] = t_q[m_t]
        return self.n - n0, so_search, so_van
