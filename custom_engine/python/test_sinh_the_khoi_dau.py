"""Bộ sinh thế cờ khởi đầu (sinh_the_khoi_dau.py), luật 2026-11-24: luật xếp khớp bộ kiểm hai nước, số cách xếp đúng
(đếm lại độc lập bằng quy hoạch động theo cột), mẫu đồng đều, thế sinh ra đạt tiêu chí cho cả hai bên.
Chạy: py -3 test_sinh_the_khoi_dau.py  (khoảng một phút, phần lớn là bộ kiểm hai nước)."""
import math
import random
from collections import Counter
from functools import lru_cache

import luat_py as orc
import sinh_the_khoi_dau as g


def dem_dp(bo, mau, ep=None):
    """Đếm độc lập số cách xếp hợp lệ của MỘT bên: quy hoạch động theo cột (mỗi cột chọn quân hàng 1 và quân hàng 2),
    chỉ dùng luật theo ô (ô quân hàng 2 cho loại nào; Pháo không đứng trên Mã / Alibaba). `ep` = {(0 hàng 1 / 1 hàng 2,
    cột): loại} ép một số ô."""
    ep = ep or {}
    serg = set(g.SERG_COT[mau])

    def lay(con, t):
        i = g.TYPES.index(t)
        if con[i] == 0:
            return None
        return con[:i] + (con[i] - 1,) + con[i + 1:]

    @lru_cache(maxsize=None)
    def f(c, con):
        if c == 10:
            return 1 if not any(con) else 0
        tong = 0
        opts2 = [g.S_] if c in serg else list(g.hang2_cho_phep(c))
        if (1, c) in ep:
            opts2 = [x for x in opts2 if x == ep[(1, c)]]
        for t2 in opts2:
            con2 = con if t2 == g.S_ else lay(con, t2)
            if con2 is None:
                continue
            for t1 in g.TYPES:
                if (0, c) in ep and ep[(0, c)] != t1:
                    continue
                if t1 == g.C_ and t2 in g.NHAY_NEU_DUOI_PHAO:
                    continue
                con3 = lay(con2, t1)
                if con3 is not None:
                    tong += f(c + 1, con3)
        return tong

    return f(0, tuple(bo))


def mot_bo(*giu, them=g.Q_):
    return g.dem_bo(*g.BO_CO_DINH, *giu, them)


def test_luat_khop_bo_kiem_hai_nuoc():
    # hai cấu hình đại diện (một không có hai Sergeant liền nhau, một có); `--kiem-lai-bang` kiểm cả sáu
    for mau in (0, 3):
        cam, cap = g.tinh_bang(mau)
        cam_l, cap_l = g.bang_theo_luat(mau)
        assert cam == cam_l, (mau, cam, cam_l)
        assert cap == cap_l, (mau, cap, cap_l)


def _xep_tuy_y(rng, mau, bo):
    """Xếp tuỳ ý (mọi quân vào ô bất kỳ trong 15 ô quân): phần lớn vi phạm."""
    qs = [t for t, n in zip(g.TYPES, bo) for _ in range(n)]
    rng.shuffle(qs)
    hang1 = tuple(qs[:10])
    it = iter(qs[10:])
    hang2 = tuple(g.S_ if c in g.SERG_COT[mau] else next(it) for c in range(10))
    return g.Ben(mau, hang1, hang2)


def _doi_cho(rng, side):
    """Đổi chỗ hai quân của một cách xếp hợp lệ: gần hợp lệ, nên vi phạm và không vi phạm đều gặp nhiều."""
    ps = [(0, c) for c in range(10)] + [(1, c) for c in g.O_QUAN_COT[side.mau]]
    h = [list(side.hang1), list(side.hang2)]
    (r1, c1), (r2, c2) = rng.sample(ps, 2)
    h[r1][c1], h[r2][c2] = h[r2][c2], h[r1][c1]
    return g.Ben(side.mau, tuple(h[0]), tuple(h[1]))


def test_luat_dung_voi_bo_kiem_tren_mau_tuy_y():
    rng = random.Random(3)
    n_bad = n_ok = 0
    for it in range(240):
        bo = g.lay_bo_quan(rng)
        mau = rng.randrange(len(g.CAU_HINH))
        if it % 4 == 0:
            side = _xep_tuy_y(rng, mau, bo)
        else:
            side = g.lay_ben(bo, rng, mau)
            for _ in range(1 + it % 3):
                side = _doi_cho(rng, side)
        if g.K_ in side.hang2:                       # bộ kiểm hai nước cho Hoàng gia ở hàng 2; ràng buộc vị trí thì không
            assert not g.hop_le_ben(side)
        bd = g.make_board(side, side)
        truc_tiep_trang = g.vi_pham(bd, orc.W)
        truc_tiep_den = g.vi_pham(bd, orc.BL)
        assert truc_tiep_trang == (not g.an_toan_ben(side)), (g.mo_ta(side), mau)
        assert truc_tiep_den == truc_tiep_trang      # Đen là ảnh lật của Trắng
        n_bad += truc_tiep_trang
        n_ok += not truc_tiep_trang
    assert n_bad > 20 and n_ok > 20     # cả hai loại đều được thử nhiều


def test_dem_bang_quy_hoach_dong():
    # số cách xếp của bộ đếm = đếm lại độc lập bằng quy hoạch động, với bộ quân có Pháo và không có Pháo, cấu hình khác nhau
    for giu, them, mau in [((g.V_, g.Y_, g.C_, g.G_), g.Q_, 0), ((g.C_, g.C_, g.Y_, g.Y_), g.R_, 3),
                           ((g.V_, g.V_, g.G_, g.G_), g.B_, 5), ((g.C_, g.Y_, g.Y_, g.G_), g.M_, 2)]:
        bo = mot_bo(*giu, them=them)
        assert g.so_cach_xep(bo, mau) == dem_dp(bo, mau), (giu, them, mau)
    # mọi bộ quân có thể bốc: cùng số cách xếp với mọi cấu hình Sergeant (mỗi cấu hình có đúng một ô quân ở cột e hoặc f)
    for bo in g.phan_bo_bo_quan():
        assert len({g.so_cach_xep(bo, m) for m in range(len(g.CAU_HINH))}) == 1


def _gan_bang(emp, p, n, what):
    sd = math.sqrt(max(p * (1 - p), 1e-12) / n)
    assert abs(emp - p) <= 5 * sd + 1e-9, (what, emp, p)


def test_mau_dong_deu():
    # tần số của một số ô (loại quân ở ô quân cột e hoặc f hàng 2, ở a1, ở c1) = tỉ lệ đếm chính xác bằng quy hoạch động
    rng = random.Random(7)
    bo, mau = mot_bo(g.C_, g.Y_, g.G_, g.V_, them=g.R_), 4      # 1S1S1S1SS1: ô cột e (e2) là ô quân, cột f là Sergeant
    cot_rong = g.RONG_COT[mau][0]
    n = 6000
    mau_ = [g.lay_ben(bo, rng, mau) for _ in range(n)]
    tong = dem_dp(bo, mau)
    assert tong == g.so_cach_xep(bo, mau)
    for t in g.HANG2_RONG:
        p = dem_dp(bo, mau, {(1, cot_rong): t}) / tong
        _gan_bang(sum(1 for s in mau_ if s.hang2[cot_rong] == t) / n, p, n, ("hàng 2", g.LETTER[t]))
    for t in (g.K_, g.C_, g.R_):
        p = dem_dp(bo, mau, {(0, 0): t}) / tong
        _gan_bang(sum(1 for s in mau_ if s.hang1[0] == t) / n, p, n, ("a1", g.LETTER[t]))
    for t in (g.C_, g.N_):
        p = dem_dp(bo, mau, {(0, 2): t}) / tong
        _gan_bang(sum(1 for s in mau_ if s.hang1[2] == t) / n, p, n, ("c1", g.LETTER[t]))
    assert all(g.hop_le_ben(s) for s in mau_)


def test_phan_bo_bo_quan():
    pb = g.phan_bo_bo_quan()
    assert len(pb) == 76 and abs(sum(pb.values()) - 1) < 1e-12
    # bốc 4 trong 8 quân nhảy (không xét loại): loại quân giữ lại có dạng (2,2,0,0) 6/70, (2,1,1,0) 48/70, (1,1,1,1) 16/70
    dang = Counter()
    for bo, p in pb.items():
        nh = sorted((bo[g.TYPES.index(t)] for t in (g.V_, g.Y_, g.C_, g.G_)), reverse=True)
        dang[tuple(nh)] += p
    for k, v in {(2, 2, 0, 0): 6 / 70, (2, 1, 1, 0): 48 / 70, (1, 1, 1, 1): 16 / 70}.items():
        assert abs(dang[k] - v) < 1e-12, (k, dang[k], v)
    rng = random.Random(11)
    n = 20000
    emp = Counter(g.lay_bo_quan(rng) for _ in range(n))
    for bo, p in sorted(pb.items(), key=lambda x: -x[1])[:6]:
        _gan_bang(emp[bo] / n, p, n, bo)
    for bo in pb:
        assert sum(bo) == 15 and bo[g.TYPES.index(g.K_)] == 1


def test_the_dung_bo_quan_va_dat_tieu_chi():
    rng = random.Random(5)
    cau_hinh = Counter()
    for k in range(2000):
        fen, w, b = g.lay_the(rng)
        bd = g.make_board(w, b)
        for hang, dau in ((0, 1), (9, -1)):                      # hàng 1 và 10: đủ 10 quân, Hoàng gia ở đó
            assert all(bd[hang * 10 + f] * dau > 0 for f in range(10))
        assert [bd[20 + f] for f in range(10)] == [g.P_] * 10 and [bd[70 + f] for f in range(10)] == [-g.P_] * 10
        for sd, h2, dau in ((w, 10, 1), (b, 80, -1)):
            assert sorted(c for c in range(10) if bd[h2 + c] == dau * g.S_) == sorted(g.SERG_COT[sd.mau])
            assert g.hop_le_ben(sd)
            assert sum(1 for s in range(100) if bd[s] * dau > 0) == 30
            assert g.K_ not in sd.hang2 and g.K_ in sd.hang1
            assert not {g.V_, g.C_, g.G_} & set(sd.hang2)
        cw = Counter(abs(x) for x in bd[:30] if x)
        cb = Counter(abs(x) for x in bd[70:] if x)
        assert cw == cb                                          # CUNG_BO_QUAN: cùng bộ quân
        assert sum(cw[t] for t in (g.V_, g.Y_, g.C_, g.G_)) == 4 and cw[g.P_] == 10 and cw[g.S_] == 5
        assert sum(cw[t] for t in (g.Q_, g.B_, g.R_, g.M_)) == 8     # Hậu 1 + Tượng 2 + Xe 2 + Centaur 2 + 1 quân thêm
        assert orc.from_fen(fen) == bd
        assert fen.split()[-3:] == [f"{orc.N_CHECKS}+{orc.N_CHECKS}", "0", "1"]
        cau_hinh[w.mau] += 1
        cau_hinh[len(g.CAU_HINH) + b.mau] += 1
    for k, v in cau_hinh.items():                                # 6 cấu hình đều, Trắng và Đen độc lập
        _gan_bang(v / 2000, 1 / 6, 2000, ("cấu hình", k))
    # bộ kiểm hai nước trực tiếp, cả hai bên
    for _ in range(150):
        _, w, b = g.lay_the(rng)
        assert g.kiem_the(w, b)
    for _ in range(8):                                            # nước hợp lệ thật (Hoàng gia không đứng ở ô bị tấn công)
        _, w, b = g.lay_the(rng)
        assert g.kiem_the(w, b, hop_le=True)


def test_hai_ben_doc_lap():
    rng = random.Random(9)
    khac = sum(1 for _ in range(400) if (lambda r: r[1].hang1 != r[2].hang1 or r[1].hang2 != r[2].hang2)(g.lay_the(rng)))
    assert khac > 395          # hai bên hầu như luôn xếp khác nhau (không đối xứng)



def test_cap_doi_mau():
    """--cap-doi-mau: dòng 2k + 1 là dòng 2k đổi màu (Trắng lấy cách xếp của Đen và ngược lại), vẫn đạt tiêu chí; số dòng lẻ bị từ chối."""
    rng = random.Random(21)
    dong = g.sinh_dong(40, rng, cap_doi_mau=True)
    assert len(dong) == 40
    for a, b in zip(dong[0::2], dong[1::2]):
        ba, bb = orc.from_fen(a), orc.from_fen(b)
        # (B, A) = (A, B) lật hàng và đổi màu quân: ô hàng r cột c của thế sau = ô hàng 9 - r cùng cột của thế trước, đổi dấu
        assert all(bb[s] == -ba[g.mirror_sq(s)] for s in range(100))
        w = g.Ben(0, tuple(bb[f] for f in range(10)), tuple(bb[10 + f] for f in range(10)))
        k = g.Ben(0, tuple(-bb[90 + f] for f in range(10)), tuple(-bb[80 + f] for f in range(10)))
        assert g.hop_le_ben(w) and g.hop_le_ben(k)
    assert len(set(dong[0::2])) == 20                            # các cặp khác nhau
    assert g.sinh_dong(5, random.Random(1)) and len(g.sinh_dong(5, random.Random(1))) == 5
    try:
        g.sinh_dong(5, rng, cap_doi_mau=True)
        assert False, "số dòng lẻ phải bị từ chối"
    except ValueError:
        pass


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
