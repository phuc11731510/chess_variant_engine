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
import cay_gm as gm

NODE2 = dict(C.NODE)
NODE2.update({
    "zs": (np.float32, 0), "ws": (np.float32, 0), "ws2": (np.float32, 0),      # ván thuần: sum w z (góc Trắng), sum w, sum w^2
    "q_ch": (np.float32, 0), "d_ch": (np.float32, 0),                         # search lúc chơi của ván thuần mới nhất (góc bên đi)
    "chia_ch": (np.float32, 0), "doi_q": (np.int16, -1),                      # tỉ lệ lượt thăm nước nhiều nhất; đời của search đó
    "re": (np.int8, 0),                                                       # 1 = con sinh ra từ ván rẽ có nước ép
    "ds": (np.float32, 0),                                                    # ván thuần: sum w 1[hoà]
    # đo B trong đời (12.9): số ván thuần đi qua node TRONG ĐỜI NÀY, tổng z và tổng z^2 (góc Trắng; phương sai không đổi theo
    # dấu), và cờ "ván lặp bắt đầu tại node này trong đời này". Xoá về 0 khi sang đời mới (xem _bat_dau_doi).
    "ng": (np.float32, 0), "zg": (np.float32, 0), "z2g": (np.float32, 0), "lapg": (np.int8, 0),
})
POOL2 = dict(C.POOL)
POOL2["qp"] = (np.float32, np.nan)                                            # Q lúc chơi của nước (ván thuần mới nhất tại node)
POOL2["dp"] = (np.float32, np.nan)                                            # xác suất hoà lúc chơi của nước (như qp)


class CayMoi(C.Cay):
    NODE = NODE2
    POOL = POOL2
    NHAN_TU_TINH = True        # nhan() tự gọi tinh(): cap_nhat không gọi tinh() riêng

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

    def _bat_dau_doi(self, doi):
        """Sang đời mới thì xoá các tổng đo B của đời trước (ng, zg, z2g, lapg) và bảng nước đầu của ván lặp."""
        if self.meta.get("doi_gom") == int(doi):
            return
        for k in ("ng", "zg", "z2g", "lapg"):
            self.a[k][:self.n] = 0
        self.meta["doi_gom"] = int(doi)
        self.meta["lap_nuoc"] = {}
        self.meta["lap_dem"] = [0, 0, 0]          # số ván lặp; số ván lặp không phải ván đầu của node; số ván trong đó khác nước đầu

    def nap_lan(self, thu_muc_lan, doi):
        """Gộp một lần sinh (thư mục chứa van.bin.gz và mau.npz) vào cây, theo mảng. Trả về (số node mới, số search, số ván)."""
        with gzip.open(os.path.join(thu_muc_lan, "van.bin.gz"), "rb") as f:
            ds = C.doc_ban_ghi(f.read())
        tep = len(self.meta["tep_mau"])
        self.meta["tep_mau"].append(os.path.relpath(os.path.join(thu_muc_lan, "mau.npz"), self.meta.get("goc_cach", ".")).replace(os.sep, "/"))
        a, con = self.a, self.con
        self._bat_dau_doi(doi)
        n0 = self.n
        goc = self.goc()
        lap_nut, lap_mv = [], []  # ván lặp: node bắt đầu và nước đầu (12.9)
        # ---- 1. đi đường, tạo node (tuần tự: số hiệu node phải theo thứ tự gặp như bản cũ)
        s_nut, s_van, s_N, s_bq, s_bd, s_p0, s_tham, s_con = [], [], [], [], [], [], [], []
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
                s_nut.append(s); s_van.append(-1); s_N.append(N); s_bq.append(bq); s_bd.append(bd); s_p0.append(p0); s_tham.append(tham); s_con.append(0)
                continue
            so_van += 1
            van = len(van_z)
            van_z.append(kq if kt == 0 else 0)
            van_re.append(moi_cuoi and len(dd) > 0)
            nut_dau = s
            lg = len(lan)
            # Ván lặp (12.9) = ván có đường đi tới một node ĐÃ CÓ TỪ ĐỜI TRƯỚC và không nước ép. Ván rẽ có node con đã tồn tại
            # từ đời trước cũng giống hệt, nhưng việc rẽ chỉ lập cho nước chưa có node con nên không xảy ra.
            if tao and len(dd) > 0 and not moi_cuoi and lg > 0 and a["doi_tao"][s] < doi:
                a["lapg"][s] = 1
                lap_nut.append(s)
                lap_mv.append(int(lan[0][0]))
            for j, (nuoc, N, bq, bd, p0, tham) in enumerate(lan):
                s_nut.append(s); s_van.append(van); s_N.append(N); s_bq.append(bq); s_bd.append(bd); s_p0.append(p0); s_tham.append(tham)
                s_con.append(lg - j)                # số nửa nước còn lại của ván tính từ node này (ước chi phí ván rẽ)
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
        bang_nuoc, dem_lap = self.meta["lap_nuoc"], self.meta["lap_dem"]
        for s, m in zip(lap_nut, lap_mv):
            dem_lap[0] += 1
            k = str(s)
            if k in bang_nuoc:
                dem_lap[1] += 1
                dem_lap[2] += int(bang_nuoc[k] != m)
            else:
                bang_nuoc[k] = m
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
            np.add.at(a["ds"], nut_gv, (z_gv == 0).astype(np.float32))
            np.add.at(a["ng"], nut_gv, np.float32(1))
            np.add.at(a["zg"], nut_gv, z_gv)
            np.add.at(a["z2g"], nut_gv, z_gv * z_gv)
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
            a["cach"][nc] = np.asarray(s_con, dtype=np.int32)[cuoi]
            # Q lúc chơi từng nước: xoá đoạn cũ của node rồi ghi Q của search mới nhất
            kc, oc = self._o_cua(nc)
            p["qp"][oc] = np.nan
            p["dp"][oc] = np.nan
            la_cuoi = np.zeros(so_search, bool)
            la_cuoi[cuoi] = True
            m_t = la_cuoi[t_ls]
            p["qp"][o_cua_t[m_t]] = t_q[m_t]
            p["dp"][o_cua_t[m_t]] = t_d[m_t]
        return self.n - n0, so_search, so_van

    # ------------------------------------------------------------ giảm (mục 8.1: trọng số làm cũ gamma^tuổi)
    def giam(self):
        """Như Cay.giam, thêm: các tổng ván thuần giảm theo gamma (tổng trọng số kết quả, tổng trọng số, số ván hoà) và
        gamma^2 (tổng bình phương trọng số), nên ván tuổi t có trọng số gamma^t và N hiệu dụng = ws^2 / ws2."""
        super().giam()
        a, n = self.a, self.n
        for k in ("zs", "ws", "ds"):
            a[k][:n] *= C.GAMMA
        a["ws2"][:n] *= C.GAMMA * C.GAMMA

    # ------------------------------------------------------------ nhóm và tham số (12.3, 12.7 bước 5)
    def nhom_cac_node(self):
        a, n = self.a, self.n
        return gm.nhom_cua(a["q_ch"][:n].astype(np.float64), a["d_ch"][:n].astype(np.float64),
                           a["chia_ch"][:n].astype(np.float64), a["doi_q"][:n])

    def _sai_dung(self):
        """(dung, sai): dung = node sống có đúng một ván thuần (N hiệu dụng bằng 1) và q lúc chơi; sai = (z - q)^2 của node đó."""
        a, n = self.a, self.n
        ws = a["ws"][:n].astype(np.float64)
        ws2 = a["ws2"][:n].astype(np.float64)
        dung = (a["trang"][:n] == 0) & (a["het"][:n] == 0) & (ws > 1e-9) & (a["doi_q"][:n] >= 0)
        neff = np.where(ws2 > 0, ws * ws / np.maximum(ws2, 1e-30), 0.0)
        dung &= neff < 1.0 + 1e-3
        sg = np.where(a["sau"][:n] % 2 == 1, -1.0, 1.0)
        x = sg * a["zs"][:n] / np.maximum(ws, 1e-30)
        return dung, (x - a["q_ch"][:n]) ** 2

    def do_S(self, so_toi_thieu=200):
        """S(g) = trung bình (z - q)^2 theo nhóm g, trên node có đúng một ván thuần (N hiệu dụng bằng 1), q là search lúc
        chơi của chính ván đó (công cụ 2, 12.3). Nhóm có dưới so_toi_thieu node lấy S chung. Trả về (S (SO_NHOM,), số node)."""
        dung, sai = self._sai_dung()
        g = self.nhom_cac_node()
        dem = np.bincount(g[dung], minlength=gm.SO_NHOM).astype(np.float64)
        tong = np.bincount(g[dung], sai[dung], minlength=gm.SO_NHOM)
        chung = float(sai[dung].mean()) if dung.any() else 0.3
        return np.where(dem >= so_toi_thieu, tong / np.maximum(dem, 1), chung), dem

    def _canh_re(self, co_p):
        """Các nhánh rẽ (con, cha) mà cha thuộc `co_p` (mảng bool theo node) và có Q, xác suất hoà lúc chơi của nước đó.
        Trả về (con, cha, Q lúc chơi, hoà lúc chơi), cả bốn cùng độ dài."""
        a, p, n = self.a, self.p, self.n
        cha, nuoc = a["cha"][:n], a["nuoc"][:n]
        con = np.flatnonzero((a["re"][:n] == 1) & (a["trang"][:n] < 2) & (cha >= 0))
        par = cha[con]
        ok = co_p[par]
        con, par = con[ok], par[ok]
        u = np.unique(par)
        khoa_o, o_o = self._o_cua(u)
        so = np.argsort(khoa_o)
        k_e = par.astype(np.int64) * 65536 + nuoc[con]
        vi = np.minimum(np.searchsorted(khoa_o[so], k_e), max(len(khoa_o) - 1, 0))
        co_o = (khoa_o[so][vi] == k_e) if len(khoa_o) else np.zeros(len(k_e), bool)
        slot = o_o[so][vi] if len(khoa_o) else np.zeros(len(k_e), np.int64)
        Qh, Dh = p["qp"][slot].astype(np.float64), p["dp"][slot].astype(np.float64)
        ok = co_o & np.isfinite(Qh) & np.isfinite(Dh)
        return con[ok], par[ok], Qh[ok], Dh[ok]

    # Tham số chỉnh được mà không cần cài lại mã: ghi JSON vào tệp <thư mục cách>/phuong_phap_moi, vd {"DOI_DUNG_DO": 2}.
    # cay.py đọc tệp này mỗi lần cap_nhat / sau_hl và gọi ap_cau_hinh. Tệp rỗng = mọi giá trị mặc định.
    CAU_HINH_CHO_PHEP = ("DOI_DUNG_DO", "W_B", "SE_MUC", "DF_B_TOI_THIEU", "N_RE_TOI_THIEU", "S_BO_QUA",
                         "TY_LE_CAP_DUY_TRI", "TY_LE_LAP_DON")

    def ap_cau_hinh(self, d):
        """Đặt các tham số trong d (chỉ những tên có trong CAU_HINH_CHO_PHEP, giữ kiểu của giá trị mặc định). Trả về dict đã đặt."""
        da = {}
        for k in self.CAU_HINH_CHO_PHEP:
            if k in d:
                setattr(self, k, type(getattr(type(self), k))(d[k]))
                da[k] = getattr(self, k)
        self._cau_hinh = da
        return da

    # ------------------------------------------------------------ đo tham số (12.7 bước 5, 12.9)
    W_B = 6                  # số đời gần nhất dùng để đo B
    DOI_DUNG_DO = 10         # từ đời này nhãn dùng B đo được (chủ dự án chốt 23/11); trước đó dùng giá trị khởi đầu
    DF_B_TOI_THIEU = 30      # nhóm / lớp có ít bậc tự do hơn thì không dùng B đo được
    N_RE_TOI_THIEU = 100     # nhóm có ít nhánh rẽ hơn thì gộp theo lớp p, rồi mới về giá trị mặc định
    GIOI_BS = (0.02, 0.98)   # B/S đo được bị chặn trong khoảng này

    def chot_B(self):
        """Gom số liệu đo B của đời hiện tại theo nhóm (sau khi gộp xong mọi lần sinh của đời), ghi vào meta["tk_B"].
        Một node có n >= 2 ván thuần đi qua trong đời cho n - 1 bậc tự do và B_node = tổng bình phương lệch / (n - 1), không lệch
        cho B. "lap" = node có ván lặp bắt đầu tại đó (do bốc ngẫu nhiên đều, không lệch theo mức đi qua của node);
        "da" = các node nhiều ván còn lại (do ván thường đi chung đường; lệch về node nông, chỉ dùng để tham khảo).
        Mỗi nhóm lưu 6 dòng: tổng w, w*B_node, w^2*B_node^2, w^2*B_node, w^2 (w = bậc tự do) và số node."""
        a, n = self.a, self.n
        doi = int(self.meta.get("doi_gom", self.meta.get("doi", -1)))
        ng = a["ng"][:n].astype(np.float64)
        zg = a["zg"][:n].astype(np.float64)
        z2g = a["z2g"][:n].astype(np.float64)
        ok = (ng >= 2) & (a["trang"][:n] == 0) & (a["doi_q"][:n] >= 0)
        ssw = np.maximum(z2g - zg * zg / np.maximum(ng, 1.0), 0.0)
        df = ng - 1.0
        bn = ssw / np.maximum(df, 1.0)
        g = self.nhom_cac_node()
        lap = a["lapg"][:n] == 1
        tk = {}
        for ten, mk in (("lap", ok & lap), ("da", ok & ~lap)):
            w, x, gg = df[mk], bn[mk], g[mk]
            tk[ten] = [np.bincount(gg, v, gm.SO_NHOM).tolist() for v in (w, w * x, w * w * x * x, w * w * x, w * w)]
            tk[ten].append(np.bincount(gg, minlength=gm.SO_NHOM).tolist())
        tk["van_lap"] = list(self.meta.get("lap_dem", [0, 0, 0]))
        bang = self.meta.setdefault("tk_B", {})
        bang[str(doi)] = tk
        for d in [k for k in bang if int(k) <= doi - 2 * self.W_B]:        # giữ gấp đôi cửa sổ cho nhật ký
            del bang[d]
        return tk

    def tong_B(self, doi=None):
        """Cộng số liệu đo B của W_B đời gần nhất tới `doi` (gồm doi). Trả về {"lap": (6, SO_NHOM), "da": (6, SO_NHOM)}."""
        doi = int(self.meta.get("doi", 0)) if doi is None else int(doi)
        bang = self.meta.get("tk_B", {})
        ra = {}
        for ten in ("lap", "da"):
            t = np.zeros((6, gm.SO_NHOM))
            for d in range(doi - self.W_B + 1, doi + 1):
                if str(d) in bang:
                    t += np.asarray(bang[str(d)][ten], dtype=np.float64)
            ra[ten] = t
        return ra

    @staticmethod
    def _gop_lop(t):
        """(k, SO_NHOM) -> (k, 8): cộng ba nhóm cùng khoảng p (cột 0-6), cột 7 = nhóm q từ mạng đời 0."""
        ra = np.zeros((t.shape[0], 8))
        ra[:, :7] = t[:, :gm.SO_NHOM_PS].reshape(t.shape[0], 7, 3).sum(2)
        ra[:, 7] = t[:, gm.NHOM_DOI0]
        return ra

    @staticmethod
    def _B_tu_tong(t):
        """Từ các tổng của chot_B ra (B, sai số chuẩn của B, bậc tự do), theo cột."""
        s0, s1, s2, t1, t2 = t[0], t[1], t[2], t[3], t[4]
        B = np.where(s0 > 0, s1 / np.maximum(s0, 1e-30), np.nan)
        var = (s2 - 2 * B * t1 + B * B * t2) / np.maximum(s0 * s0, 1e-30)
        return B, np.sqrt(np.maximum(var, 0.0)), s0

    def tham_B(self, S, dem):
        """B/S của từng nhóm: giá trị khởi đầu (BS_KHOI_DAU); từ đời DOI_DUNG_DO, nhóm nào có B đo được từ cặp ván lặp với sai
        số chuẩn của B/S không quá SE_MUC thì dùng nó, không thì dùng B/S của lớp p của nó (ba nhóm cùng khoảng p gộp lại, giả
        định B/S như nhau giữa ba mức tỉ lệ lượt thăm), không thì giá trị khởi đầu. Trả về (bs (SO_NHOM,), nguồn (SO_NHOM,),
        thông tin): nguồn 0 = khởi đầu, 1 = nhóm, 2 = lớp p."""
        bs = np.full(gm.SO_NHOM, gm.BS_KHOI_DAU)
        nguon = np.zeros(gm.SO_NHOM, np.int64)
        doi = int(self.meta.get("doi", 0))
        tong = self.tong_B(doi)
        B_g, se_g, df_g = self._B_tu_tong(tong["lap"])
        t_lop = self._gop_lop(tong["lap"])
        B_l, se_l, df_l = self._B_tu_tong(t_lop)
        dem_l = self._gop_lop(np.stack([dem * S, dem]))                 # tổng dem*S và dem theo lớp
        S_lop = dem_l[0] / np.maximum(dem_l[1], 1e-9)
        w_g = B_g / np.maximum(S, 1e-9)
        sew_g = se_g / np.maximum(S, 1e-9)
        w_l = B_l / np.maximum(S_lop, 1e-9)
        sew_l = se_l / np.maximum(S_lop, 1e-9)
        lop_cua = np.where(np.arange(gm.SO_NHOM) < gm.NHOM_DOI0, np.arange(gm.SO_NHOM) // 3, 7)
        if doi >= self.DOI_DUNG_DO:
            for g in range(gm.SO_NHOM):
                l = lop_cua[g]
                if df_g[g] >= self.DF_B_TOI_THIEU and sew_g[g] <= self.SE_MUC:
                    bs[g], nguon[g] = w_g[g], 1
                elif df_l[l] >= self.DF_B_TOI_THIEU and sew_l[l] <= self.SE_MUC:
                    bs[g], nguon[g] = w_l[l], 2
            bs = np.clip(bs, *self.GIOI_BS)
        info = {"df_nhom": df_g.round(1).tolist(), "w_nhom": np.round(w_g, 3).tolist(), "se_w_nhom": np.round(sew_g, 3).tolist(),
                "df_lop": df_l.round(1).tolist(), "w_lop": np.round(w_l, 3).tolist(), "se_w_lop": np.round(sew_l, 3).tolist(),
                "S_lop": np.round(S_lop, 4).tolist(), "nguon_B": nguon.tolist(), "bs": np.round(bs, 3).tolist(),
                "ty_le_khac_nuoc_dau": (self.meta.get("lap_dem", [0, 0, 0])[2] / max(self.meta.get("lap_dem", [0, 0, 0])[1], 1))}
        da = self._gop_lop(self.tong_B(doi)["da"])
        Bd, sed, dfd = self._B_tu_tong(da)
        info["tham_khao_B_node_nhieu_van"] = {"df_lop": dfd.round(0).tolist(), "w_lop": np.round(Bd / np.maximum(S_lop, 1e-9), 3).tolist()}
        return bs, nguon, info

    def do_re(self, B_nhom):
        """Tổng thống kê nhánh rẽ theo nhóm của node cha, trên các node cha có đúng một ván thuần và nhánh rẽ một ván (con có
        đúng một ván thuần và không có nhánh rẽ bên dưới), cả hai sống. Với mỗi nhánh: Y1 = z_beta - q, Y2 = z_a - Q lúc chơi
        (góc bên đi của cha), D = Y2 - Y1; kênh hoà: Dd tương tự. Trả về mảng (10, SO_NHOM):
        n, sum Y1, sum Y2, sum Y1*Y2, sum D, sum D^2, sum Dd, sum B(con), n_eta, sum Da*Db (hai nhánh đầu của một cha)."""
        a, n = self.a, self.n
        trang, het = a["trang"][:n], a["het"][:n]
        ws = a["ws"][:n].astype(np.float64)
        ws2 = a["ws2"][:n].astype(np.float64)
        neff = np.where(ws2 > 0, ws * ws / np.maximum(ws2, 1e-30), 0.0)
        co1 = (trang == 0) & (het == 0) & (ws > 1e-9) & (neff < 1.001)
        con, par, Qh, Dh = self._canh_re(co1)
        cha = a["cha"][:n]
        la_cha_re = np.zeros(n, bool)
        la_cha_re[cha[(a["re"][:n] == 1) & (trang < 2) & (cha >= 0)]] = True
        ok = co1[con] & ~la_cha_re[con]
        con, par, Qh, Dh = con[ok], par[ok], Qh[ok], Dh[ok]
        t = np.zeros((10, gm.SO_NHOM))
        if len(con) == 0:
            return t
        sg = np.where(a["sau"][:n] % 2 == 1, -1.0, 1.0)
        g = self.nhom_cac_node()
        zw = a["zs"][:n].astype(np.float64) / np.maximum(ws, 1e-30)             # góc Trắng
        dw = a["ds"][:n].astype(np.float64) / np.maximum(ws, 1e-30)
        q_ch, d_ch = a["q_ch"][:n].astype(np.float64), a["d_ch"][:n].astype(np.float64)
        Y1 = sg[par] * zw[par] - q_ch[par]
        Y2 = sg[par] * zw[con] - Qh
        D = Y2 - Y1
        Dd = (dw[con] - Dh) - (dw[par] - d_ch[par])
        gp = g[par]
        for i, v in enumerate((np.ones(len(con)), Y1, Y2, Y1 * Y2, D, D * D, Dd, B_nhom[g[con]])):
            t[i] = np.bincount(gp, v, gm.SO_NHOM)
        # hai nhánh đầu của cha có từ hai nhánh trở lên (cho eta)
        o = np.argsort(par, kind="stable")
        par_s, D_s = par[o], D[o]
        dau = np.flatnonzero(np.r_[True, par_s[1:] != par_s[:-1]])
        dem = np.diff(np.r_[dau, len(par_s)])
        hai = dau[dem >= 2]
        if len(hai):
            gh = g[par_s[hai]]
            t[8] = np.bincount(gh, minlength=gm.SO_NHOM)
            t[9] = np.bincount(gh, D_s[hai] * D_s[hai + 1], gm.SO_NHOM)
        return t

    def tham_so(self):
        """Bảng tham số theo nhóm (cay_gm.tham_so_tu_S) từ S đo được, B/S (tham_B), rồi kappa, o, o_d, Gamma, eta đo trên nhánh rẽ
        của cây hiện tại (12.7 bước 5). Nhóm có ít hơn N_RE_TOI_THIEU nhánh rẽ đo được thì gộp theo lớp p, ít hơn nữa thì dùng
        giá trị mặc định (kappa = KR_KHOI_DAU * S, o = 0, Gamma = 2A - 2 kappa, eta = max(A - 2 kappa, 0)). Phương sai ước ra
        âm thì đặt 0 và đếm lại. Lưu thông tin kiểm vào self._tham_log."""
        S, dem = self.do_S()
        bs, nguon_B, info = self.tham_B(S, dem)
        tham = gm.tham_so_tu_S(S, bs)
        B = tham["B"]
        t = self.do_re(B)
        t_l = self._gop_lop(t)
        nhom_lop = np.where(np.arange(gm.SO_NHOM) < gm.NHOM_DOI0, np.arange(gm.SO_NHOM) // 3, 7)
        nguon_re = np.zeros(gm.SO_NHOM, np.int64)
        so_am = {"kappa": 0, "Gam": 0, "eta": 0}
        var_D, Ec_g, var_Y1 = np.zeros(gm.SO_NHOM), np.zeros(gm.SO_NHOM), np.zeros(gm.SO_NHOM)
        for g in range(gm.SO_NHOM):
            cot = None
            if t[0, g] >= self.N_RE_TOI_THIEU:
                cot, nguon_re[g] = t[:, g], 1
            elif t_l[0, nhom_lop[g]] >= self.N_RE_TOI_THIEU:
                cot, nguon_re[g] = t_l[:, nhom_lop[g]], 2
            if cot is None:
                continue
            nn = cot[0]
            m1, m2 = cot[1] / nn, cot[2] / nn
            o_g = cot[4] / nn
            kap = cot[3] / nn - m1 * m2
            var_d = cot[5] / nn - o_g * o_g
            Ec = cot[7] / nn
            # kappa tính trên lớp thì đổi về nhóm theo tỉ lệ kappa / S của lớp (kappa tỉ lệ với S như ở giá trị khởi đầu)
            if nguon_re[g] == 2:
                S_l = info["S_lop"][nhom_lop[g]]
                kap = kap / max(S_l, 1e-9) * S[g]
                var_d = var_d / max(S_l, 1e-9) * S[g]
                Ec = Ec / max(S_l, 1e-9) * S[g]
            var_D[g], Ec_g[g] = var_d, Ec
            if kap < 0:
                so_am["kappa"] += 1
            kap = float(np.clip(kap, 0.0, 0.9 * tham["A"][g]))
            Gam = var_d - Ec - B[g]
            if Gam < 0:
                so_am["Gam"] += 1
            Gam = max(float(Gam), 1e-4)
            eta = max(tham["A"][g] - 2 * kap, 0.0)
            if cot[8] >= self.N_RE_TOI_THIEU and nguon_re[g] == 1:
                e = cot[9] / cot[8] - o_g * o_g - B[g]
                if e < 0:
                    so_am["eta"] += 1
                eta = max(float(e), 0.0)
            tham["kap"][g], tham["Gam"][g], tham["eta"][g] = kap, Gam, eta
            tham["o"][g] = o_g                       # độ lệch cộng thêm, không tỉ lệ với S
            tham["od"][g] = cot[6] / nn
        info.update({"nguon_re": nguon_re.tolist(), "n_re_nhom": t[0].astype(int).tolist(),
                     "kappa": np.round(tham["kap"], 4).tolist(), "o": np.round(tham["o"], 4).tolist(),
                     "od": np.round(tham["od"], 4).tolist(), "Gam": np.round(tham["Gam"], 4).tolist(),
                     "eta": np.round(tham["eta"], 4).tolist(), "am": so_am,
                     "var_D": np.round(var_D, 4).tolist(), "E_con": np.round(Ec_g, 4).tolist(),
                     "B": np.round(tham["B"], 4).tolist(), "A": np.round(tham["A"], 4).tolist(),
                     "S": np.round(S, 4).tolist(), "so_node_nhom": dem.astype(int).tolist()})
        self._tham_log = info
        return tham

    # ------------------------------------------------------------ G, E và nhãn (12.7)
    def tinh(self, tham=None):
        """Tính G (giá trị tổng hợp không có q, gửi lên node cha), E (sai số bình phương của G) cho mọi node sống, và nhãn value
        có q cho node có mẫu, bằng tổ hợp Gauss-Markov (cay_gm.gm_mang). Mọi phép tính theo mảng cấp node và cấp nhánh rẽ;
        không có bước nào chạy qua toàn bộ ô pool (khác Cay.tinh). Cần pool gọn (gọi nen trước)."""
        a, p, n = self.a, self.p, self.n
        if not self.la_gon():
            raise RuntimeError("tinh cần pool gọn: gọi nen() trước")
        if tham is None:
            self.chot_B()                                  # số liệu đo B của đời này (đã gộp xong các lần sinh) vào meta
            tham = self.tham_so()
        sau, trang, het = a["sau"][:n], a["trang"][:n], a["het"][:n]
        sg = np.where(sau % 2 == 1, -1.0, 1.0)
        ws = a["ws"][:n].astype(np.float64)
        ws2 = a["ws2"][:n].astype(np.float64)
        co_p = (ws > 1e-9) & (trang == 0) & (het == 0)
        neff = np.where(ws2 > 0, ws * ws / np.maximum(ws2, 1e-30), 0.0)
        g = self.nhom_cac_node()
        A, B, kap, Gam, eta = (tham[k][g] for k in ("A", "B", "kap", "Gam", "eta"))
        o, od = tham["o"][g], tham["od"][g]
        nb = np.where(neff > 0, neff / np.maximum(B, 1e-12), 0.0)
        xP_w = a["zs"][:n] / np.maximum(ws, 1e-30)                      # góc Trắng
        dP = a["ds"][:n] / np.maximum(ws, 1e-30)
        q_ch, d_ch = a["q_ch"][:n].astype(np.float64), a["d_ch"][:n].astype(np.float64)
        Gv = a["Gw"][:n].astype(np.float64) - a["Gl"][:n]                # góc Trắng
        Gd = a["Gd"][:n].astype(np.float64)
        E = a["E"][:n].astype(np.float64)
        Gv[co_p], Gd[co_p], E[co_p] = xP_w[co_p], dP[co_p], (B / np.maximum(neff, 1e-12))[co_p]
        la = (trang == 0) & (het > 0)                                     # node kết thúc: kết quả theo luật
        z = a["z"][:n].astype(np.float64)
        Gv[la], Gd[la], E[la] = z[la], (z[la] == 0).astype(np.float64), 0.0
        # nhánh rẽ: con có re = 1, cha có ván thuần và Q lúc chơi của nước đó
        con, par, Qh, Dh = self._canh_re(co_p)
        so_canh = len(con)

        def bang_cung(sel, ps, idx):
            """bằng chứng của các nhánh rẽ `sel` của các node cha `ps` (idx: chỉ số của cha trong ps), theo G con hiện có."""
            c, pa = con[sel], par[sel]
            xv = sg[pa] * Gv[c] + (q_ch[pa] - Qh[sel]) - o[pa]
            xd = Gd[c] + (d_ch[pa] - Dh[sel]) - od[pa]
            return E[c], np.stack([xv, xd], 1)

        dep = sau[par]
        for L in (np.unique(dep)[::-1] if so_canh else []):             # từ sâu lên nông: G của con phải xong trước cha
            sel = np.flatnonzero(dep == L)
            ps, idx = np.unique(par[sel], return_inverse=True)
            e_E, e_x = bang_cung(sel, ps, idx)
            x_P = np.stack([sg[ps] * xP_w[ps], dP[ps]], 1)
            r = gm.gm_mang(len(ps), A[ps], kap[ps], nb[ps], eta[ps], Gam[ps], idx, e_E, e_x, x_P, x_P)
            Gv[ps], Gd[ps], E[ps] = sg[ps] * r["G"][:, 0], r["G"][:, 1], r["E_G"]
        # nhãn của node có mẫu
        chon = np.flatnonzero(co_p & (a["mau_tep"][:n] >= 0) & (a["k"][:n] > 0))
        pos = np.full(n, -1, np.int64)
        pos[chon] = np.arange(len(chon))
        sel = np.flatnonzero(pos[par] >= 0) if so_canh else np.zeros(0, np.int64)
        idx = pos[par[sel]]
        e_E, e_x = bang_cung(sel, None, idx) if len(sel) else (np.zeros(0), np.zeros((0, 2)))
        q_arr = np.stack([q_ch[chon], d_ch[chon]], 1)
        x_P = np.stack([sg[chon] * xP_w[chon], dP[chon]], 1)
        r = gm.gm_mang(len(chon), A[chon], kap[chon], nb[chon], eta[chon], Gam[chon], idx, e_E, e_x, q_arr, x_P)
        v = np.clip(r["nhan"][:, 0], -1, 1)
        d = np.clip(r["nhan"][:, 1], 0, 1)
        wdl = np.stack([(1 + v - d) / 2, d, (1 - v - d) / 2], 1).clip(0, 1)
        wdl /= wdl.sum(1, keepdims=True)
        # ghi G, E (góc Trắng) về node sống
        song = trang == 0
        a["Gw"][:n] = np.where(song, ((1 + Gv - Gd) / 2).clip(0, 1), a["Gw"][:n])
        a["Gd"][:n] = np.where(song, Gd, a["Gd"][:n])
        a["Gl"][:n] = np.where(song, ((1 - Gv - Gd) / 2).clip(0, 1), a["Gl"][:n])
        a["E"][:n] = np.where(song, E, a["E"][:n])
        self._tam = {"chon": chon, "wdl": wdl, "r": r, "nhom": g, "tham": tham, "so_canh": so_canh}
        return self._tam

    def nhan(self, so_buoc, tham=None):
        """Nhãn huấn luyện của mọi node sống đã search, chưa kết thúc và có mặt phẳng (mau.npz): cùng định dạng với Cay.nhan.
        Value: tổ hợp Gauss-Markov (tinh). Policy: trung bình pi của các lần search (như bản cũ, 12.8)."""
        t = self.tinh(tham)
        a, p, n = self.a, self.p, self.n
        chon, wdl, r = t["chon"], t["wdl"], t["r"]
        # policy: pi = ns / tổng ns của node, chỉ các ô ns > 0 của node được chọn (pool gọn: đoạn của node i nằm theo thứ tự node)
        ms, ml = a["ms"][:n].astype(np.int64), a["ml"][:n].astype(np.int64)
        so_o = self.np_
        ns = p["ns"][:so_o]
        tong_n = np.zeros(n)
        co_ml = ml > 0
        if so_o:
            tong_n[co_ml] = np.add.reduceat(ns, ms[co_ml], dtype=np.float64)
        co_pol = tong_n[chon] > 0
        chon, wdl = chon[co_pol], wdl[co_pol]
        la_chon = np.zeros(n, bool)
        la_chon[chon] = True
        owner = np.repeat(np.arange(n, dtype=np.int32), ml)
        dem_moi = np.zeros(n, np.int64)
        pi2, mv2 = [], []
        for d0 in range(0, so_o, 1 << 23):
            sl = slice(d0, min(d0 + (1 << 23), so_o))
            ow = owner[sl]
            co = la_chon[ow] & (ns[sl] > 0)
            pi2.append((ns[sl][co] / np.maximum(tong_n[ow[co]], 1e-12)).astype(np.float32))
            mv2.append(p["mv"][sl][co])
            dem_moi += np.bincount(ow[co], minlength=n)
        del owner
        pi2 = np.concatenate(pi2) if pi2 else np.zeros(0, np.float32)
        mv2 = np.concatenate(mv2) if mv2 else np.zeros(0, np.uint16)
        dem = dem_moi[chon]
        pol_q = C._pi_uint16(pi2, dem)
        den = (a["sau"][:n] % 2 == 1)
        w_hoc = np.ones(len(chon), np.float32)
        so_buoc = max(int(so_buoc), -(-len(chon) // 1024))
        ra = {"tep": a["mau_tep"][chon], "hang": a["mau_hang"][chon], "den_di": den[chon].astype(np.uint8),
              "wdl": wdl.astype(np.float32), "w": w_hoc,
              "pol_dem": dem.astype(np.uint8 if dem.max(initial=0) < 256 else np.uint16),
              "pol_mv": mv2.astype(np.uint16), "pol_q": pol_q, "so_buoc": np.int64(so_buoc)}
        gg = t["nhom"][chon]
        tk = {"so_mau": int(len(chon)), "so_canh_re": int(t["so_canh"]), "node_hong": int(r["hong"].sum()),
              "doi": int(self.meta.get("doi", -1)),
              "lam_q_tb": float(r["lam_q"][co_pol].mean()) if len(chon) else 0.0,
              "lam_P_tb": float(r["lam_P"][co_pol].mean()) if len(chon) else 0.0,
              "lam_re_tb": float(r["lam_R"][co_pol].mean()) if len(chon) else 0.0,
              "E_nhan_tb": float(r["E_nhan"][co_pol].mean()) if len(chon) else 0.0,
              "S_nhom": [round(float(x), 4) for x in t["tham"]["S"]],
              "so_node_nhom": np.bincount(gg, minlength=gm.SO_NHOM).tolist(),
              "tham": getattr(self, "_tham_log", {}), "cau_hinh": getattr(self, "_cau_hinh", {}),
              "van_lap": list(self.meta.get("lap_dem", [0, 0, 0]))}
        return ra, tk

    # ------------------------------------------------------------ lập việc cho đời sau (8, 12.9)
    SE_MUC = 0.2             # sai số chuẩn muốn đạt của w = B/S ở mỗi nhóm (12.9)
    S_BO_QUA = 0.03          # nhóm có S nhỏ hơn: nhãn sai ít nên không dành cặp ván lặp cho nhóm đó
    TY_LE_CAP_DUY_TRI = 0.25 # phần trần 20% dành cho cặp ván lặp khi mọi nhóm đã đủ cặp (5% ngân sách)
    TY_LE_LAP_DON = 0.5      # phần trần còn lại dành cho ván lặp đơn (phần kia cho search lại đơn)

    def lap_viec(self, doi_moi, ngan_sach, rng, tham=None):
        """Danh sách việc cho đời `doi_moi`: [(loai, node, nuoc ép hoặc None, chi phí ước (lần chạy mạng))] đã xáo.
        loai "S" = search lại đơn; "G" với nước ép = ván rẽ; "G" không nước ép = ván lặp (cặp hoặc đơn, 12.9).
        Trần 20% ngân sách chia: cặp ván lặp (tới khi mọi nhóm có đủ cặp cho SE_MUC, rồi TY_LE_CAP_DUY_TRI của trần), phần
        còn lại chia TY_LE_LAP_DON cho ván lặp đơn (theo mức giảm sai số bình phương của nhãn trên mỗi chi phí) và phần kia cho
        search lại đơn (thứ tự ưu tiên như mục 8.5). Phần ngân sách còn lại cho ván rẽ (quét như cũ, 6.1 và 6.3)."""
        a, p, n = self.a, self.p, self.n
        if tham is None:
            tham = self.tham_so()
        e = float(self.meta.get("evals_moi_search", C.EVALS_MOI_SEARCH))
        trang, het = a["trang"][:n], a["het"][:n]
        cha, nuoc = a["cha"][:n], a["nuoc"][:n]
        song = (trang == 0) & (het == 0) & (a["k"][:n] > 0) & (a["ws"][:n] > 1e-9)
        cp_van = (a["cach"][:n].astype(np.float64) + 1) * e
        g = self.nhom_cac_node()
        song_lap = song & (a["sau"][:n] > 0)         # ván lặp không bắt đầu ở gốc (đó là ván thường, không có đường đi)
        tran = C.TRAN_SEARCH_LAI * ngan_sach
        tat = []
        da_dung = np.zeros(n, bool)
        # ---- 1. cặp ván lặp, lập theo LỚP p (ba nhóm cùng khoảng p gộp lại). Đo từng nhóm riêng cần ~390 triệu lần chạy mạng
        # (9,7 đời dùng cả trần) vì nhóm S nhỏ cần rất nhiều cặp; gộp theo lớp còn ~150 triệu (xem tham_B).
        # lớp dự kiến của node: node nhóm "q từ mạng đời 0" cũng được xếp theo p và tỉ lệ lượt thăm của q cũ (cặp rơi vào lớp nào
        # là do lần search mới của chính cặp quyết định, và đó là cái được đếm ở da_co). S của lớp tính trên cùng cách xếp này,
        # để đời 1 (mọi node đều có q từ mạng đời 0) vẫn lập được cặp.
        g_kd = gm.nhom_cua(a["q_ch"][:n].astype(np.float64), a["d_ch"][:n].astype(np.float64),
                           a["chia_ch"][:n].astype(np.float64), np.ones(n, np.int16))
        lop_node = g_kd // 3
        dung, sai = self._sai_dung()
        cnt_l = np.bincount(lop_node[dung], minlength=7).astype(np.float64)
        tot_l = np.bincount(lop_node[dung], sai[dung], 7)
        chung = float(sai[dung].mean()) if dung.any() else 0.3
        S_l = np.where(cnt_l >= 200, tot_l / np.maximum(cnt_l, 1.0), chung)
        t_l = self._gop_lop(self.tong_B(doi_moi - 1)["lap"])
        da_co = t_l[5]                                                  # số node có cặp đo được, theo lớp, trong cửa sổ
        # Số cặp cần có trong cửa sổ để sai số chuẩn của B/S không quá SE_MUC. Cận xấu nhất 2 / (SE^2 S) (từ Var(X) <= 2B,
        # 12.9) dùng khi lớp chưa đủ bậc tự do để ước sai số chuẩn thật; lớp đã đủ thì dùng sai số chuẩn THẬT đã đo, vì sai số
        # chuẩn tỉ lệ 1 / sqrt(n): cần n_hiện_có * (SE_thật / SE_MUC)^2 cặp (ít hơn nhiều so với cận: đời 3 lớp 3 cần 1 231
        # theo cận, trong khi 619 node đã cho SE_thật 0,111, tức đã đủ, mà kế hoạch cũ vẫn dành 13,7 triệu mỗi đời cho nó).
        S_g, dem_g = self.do_S()
        S_lop_nhom = self._gop_lop(np.stack([dem_g * S_g, dem_g]))
        S_lop_nhom = (S_lop_nhom[0] / np.maximum(S_lop_nhom[1], 1e-9))[:7]
        _, se_l, df_l = self._B_tu_tong(t_l)
        with np.errstate(invalid="ignore", divide="ignore"):
            sew = se_l[:7] / np.maximum(S_lop_nhom, 1e-9)
            do_duoc = (df_l[:7] >= self.DF_B_TOI_THIEU) & np.isfinite(sew)
            can_xau = np.ceil(2.0 / (self.SE_MUC ** 2 * np.maximum(S_l, 1e-3)))
            can_do = np.ceil(da_co[:7] * np.where(do_duoc, sew, 0.0) ** 2 / self.SE_MUC ** 2)
        can = np.where(do_duoc, can_do, can_xau)
        can = np.where(S_l >= self.S_BO_QUA, can, 0.0)
        con_thieu = np.maximum(can - da_co[:7], 0.0)
        ngan_cap = tran if con_thieu.sum() > 0 else self.TY_LE_CAP_DUY_TRI * tran
        da_cap = 0.0
        so_cap = 0
        cap_theo_lop = np.zeros(7, np.int64)
        for li in np.argsort(-S_l):
            if da_cap >= ngan_cap:
                break
            ung = np.flatnonzero(song_lap & (lop_node == li))
            if len(ung) == 0:
                continue
            # còn thiếu cặp thì chỉ lớp thiếu được thêm; đủ cả rồi thì mỗi lớp thêm can / W_B cặp để đo lại B mỗi đời (duy trì)
            muon = int(con_thieu[li]) if con_thieu.sum() > 0 else int(np.ceil(can[li] / self.W_B))
            rng.shuffle(ung)
            for s in ung[:max(muon, 0)]:
                cp = 2 * cp_van[s]
                if da_cap + cp > ngan_cap:
                    break
                tat += [("G", int(s), None, cp_van[s]), ("G", int(s), None, cp_van[s])]
                da_dung[s] = True
                da_cap += cp
                so_cap += 1
                cap_theo_lop[li] += 1
        # ---- 2. ván lặp đơn (theo mức giảm sai số bình phương của nhãn trên mỗi chi phí)
        con_tran = max(tran - da_cap, 0.0)
        ngan_don = self.TY_LE_LAP_DON * con_tran
        ws = a["ws"][:n].astype(np.float64)
        ws2 = a["ws2"][:n].astype(np.float64)
        neff = np.where(ws2 > 0, ws * ws / np.maximum(ws2, 1e-30), 0.0)
        A, B = tham["A"][g], tham["B"][g]
        loi = A * A * B / np.maximum((neff * A + B) * ((neff + 1) * A + B), 1e-30)
        diem = np.where(song_lap & ~da_dung, loi / cp_van, -1.0)
        da_don = 0.0
        so_don = 0
        if ngan_don > 0 and (diem > 0).any():
            top = np.flatnonzero(diem > 0)
            top = top[np.argsort(-diem[top])[:int(2 * ngan_don / max(e, 1.0)) + 10]]
            cum = np.cumsum(cp_van[top])
            tat += [("G", int(s), None, cp_van[s]) for s in top[cum <= ngan_don]]
            so_don = int((cum <= ngan_don).sum())
            da_don = float(cum[so_don - 1]) if so_don else 0.0
            da_dung[top[:so_don]] = True
        # ---- 3. search lại đơn (ưu tiên như 8.5: m * dhat / (k + 1))
        viec_s = []
        if C.CONG_TAC["search_lai"]:
            k = np.maximum(a["k"][:n].astype(np.float64), 1e-9)
            tuoi = doi_moi - a["gsum"][:n] / k
            dl = self._delta_bang()
            idx = np.flatnonzero(song & ~da_dung)
            dhat = np.array([dl(tu, kk) for tu, kk in zip(tuoi[idx], k[idx])])
            ut = a["m"][:n][idx] * dhat / (k[idx] + 1)
            gioi = int(max(tran - da_cap - da_don, 0.0) / e)
            for j in np.argsort(-ut)[:gioi]:
                s = int(idx[j])
                if k[s] >= a["m"][s] and tuoi[s] < 1:
                    continue
                viec_s.append(s)
        da_s = len(viec_s) * e
        # ---- 4. ván rẽ: quét một nước mỗi node theo ns^(1/T), thứ tự theo m (như Cay.lap_viec)
        ms, ml = a["ms"][:n].astype(np.int64), a["ml"][:n].astype(np.int64)
        so_o = self.np_
        owner = np.repeat(np.arange(n, dtype=np.int32), ml)
        w = np.power(p["ns"][:so_o].astype(np.float64), 1.0 / C.T_QUET)
        w[~song[owner]] = 0.0
        del owner
        co_ml = ml > 0
        tong = np.zeros(n)
        tong[co_ml] = np.add.reduceat(w, ms[co_ml])
        cum_w = np.cumsum(w)
        dau = np.zeros(n)
        dau[co_ml] = cum_w[ms[co_ml]] - w[ms[co_ml]]
        nut = np.flatnonzero(song & (tong > 0))
        u = dau[nut] + rng.random(len(nut)) * tong[nut]
        chon = np.minimum(np.searchsorted(cum_w, u, side="right"), len(cum_w) - 1)
        mv = p["mv"][:so_o][chon].astype(np.int64)
        del w, cum_w
        ok_c = (cha >= 0) & (trang < 2)
        co_con = np.sort(cha[ok_c].astype(np.int64) * 65536 + nuoc[ok_c])
        khoa = nut.astype(np.int64) * 65536 + mv
        vi = np.minimum(np.searchsorted(co_con, khoa), max(len(co_con) - 1, 0))
        da_choi = (co_con[vi] == khoa) if len(co_con) else np.zeros(len(khoa), bool)
        nd, mvd = nut[~da_choi], mv[~da_choi]
        if C.CONG_TAC["re_theo_m"] and len(nd):
            kh = -np.log(1.0 - rng.random(len(nd))) / np.maximum(a["m"][:n][nd].astype(np.float64), 1e-9) ** C.MU_M
            thu = np.argsort(kh, kind="stable")
            nd, mvd = nd[thu], mvd[thu]
        else:
            thu = rng.permutation(len(nd))
            nd, mvd = nd[thu], mvd[thu]
        con_lai = ngan_sach * C.DU_VIEC - da_cap - da_don - da_s
        cum_cp = np.cumsum(cp_van[nd]) if len(nd) else np.zeros(0)
        so_re = int(np.searchsorted(cum_cp, con_lai, side="left")) + 1 if len(nd) else 0   # lập tới khi đủ ngân sách (như bản cũ)
        so_re = min(so_re, len(nd))
        tat += [("G", int(s), int(m), cp_van[s]) for s, m in zip(nd[:so_re].tolist(), mvd[:so_re].tolist())]
        tat += [("S", s, None, e) for s in viec_s]
        # Xáo theo KHỐI: hai ván của một cặp (nằm đầu danh sách, từng đôi một) luôn đi liền nhau. Vòng lặp nhận việc từ đầu danh
        # sách tới khi đủ ngân sách rồi bỏ phần đuôi (danh sách lập dư DU_VIEC lần), nên xáo từng việc thì chỉ khoảng
        # (2/3)^2 = 44% số cặp có CẢ HAI ván được chơi, phần còn lại thành ván lẻ không đo được B (đời 1 lần chạy 6: 649 cặp lập,
        # 857 ván lặp được chơi, chỉ 282 node có đủ hai ván). Xáo theo khối thì cặp được chơi cả đôi hoặc bỏ cả đôi.
        khoi = [(tat[2 * i], tat[2 * i + 1]) for i in range(so_cap)] + [(e,) for e in tat[2 * so_cap:]]
        order = rng.permutation(len(khoi))
        tat = [e for i in order for e in khoi[i]]
        return tat, {"so_diem_re": int(len(nd)), "so_viec_s": len(viec_s), "so_viec_g": int(so_re), "so_cap_lap": so_cap,
                     "so_lap_don": so_don, "cap_theo_lop": cap_theo_lop.tolist(), "can_cap_lop": can.astype(int).tolist(),
                     "da_co_cap_lop": da_co[:7].astype(int).tolist(), "con_thieu_cap": int(con_thieu.sum()),
                     "se_w_lop": np.round(np.nan_to_num(sew, nan=-1.0), 3).tolist(), "can_theo_so_do": do_duoc.tolist(),
                     "chi_phi_cap": int(da_cap), "chi_phi_lap_don": int(da_don), "chi_phi_s": int(da_s)}
