"""Kiem thu phan GOI VAN cua scripts/colab_cells/fz_tu_dong.py (vong lap lien tuc, chay tren dien thoai):
goi_nhan (dat ten, so thu tu khong trung ke ca khi nhieu tien trinh cung luc), goi_tong, cua_so, nhap_cu (tu thu muc doi cu), don_goi.
Dung VAN THAT (mau_van/*.xz), khong can engine.   Chay:  python test_fz_tu_dong_goi.py
"""
import contextlib
import glob
import io
import multiprocessing
import os
import shutil
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts", "colab_cells"))
sys.path.insert(0, HERE)

import fz_tu_dong as T  # noqa: E402
import goi_van as G  # noqa: E402

PASS = FAIL = 0
MAU = sorted(glob.glob(os.path.join(HERE, "mau_van", "*.xz")))


def check(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [ok] {msg}")
    else:
        FAIL += 1
        print(f"  [FAIL] {msg}")


def chay(f, *a):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        f(*a)
    return buf.getvalue().splitlines()


def zip_tam(thu_muc, mang, so_van):
    """Zip tam gom so_van van mau (de dua cho goi_nhan)."""
    p = os.path.join(thu_muc, f"tam_{mang}_{so_van}_{os.getpid()}.zip")
    with zipfile.ZipFile(p, "w", zipfile.ZIP_STORED) as z:
        for i in range(so_van):
            z.write(MAU[i % len(MAU)], f"games_gen{mang}/x_game_{i}.xz")
    return p


def _nhan(args):
    tai, mang = args
    tam = zip_tam(tai, mang, 1)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        T.goi_nhan(tai, tam, mang, 1, 57)
    return int(buf.getvalue().split()[2])


def test_dem_the():
    print("A. dem_the (ban sao khong can numpy) = goi_van.dem_the")
    for p in MAU:
        d = open(p, "rb").read()
        check(T.dem_the(d) == G.dem_the(d), f"{os.path.basename(p)}: {T.dem_the(d)} the")
    try:
        T.dem_the(b"khong phai xz")
        check(False, "van hong phai bi tu choi")
    except ValueError:
        check(True, "van hong bi tu choi")


def test_goi_nhan_tong_cua_so():
    print("B. goi_nhan / goi_tong / cua_so / don_goi")
    with tempfile.TemporaryDirectory() as tai:
        # 5 goi lien tiep: so van 2, the 100 (gia lap qua ten)
        ten = []
        for i, (mang, van, the) in enumerate([(54, 10, 1000), (55, 10, 1200), (55, 10, 900), (56, 10, 1100), (57, 10, 800)]):
            tam = zip_tam(tai, mang, 1)
            out = chay(T.goi_nhan, tai, tam, mang, van, the)
            ten.append(out[0].split()[1])
        check(ten[0] == "goi_00001_n54_10_1000.zip" and ten[4] == "goi_00005_n57_10_800.zip", f"ten goi: {ten[0]} ... {ten[4]}")
        check(all(os.path.exists(os.path.join(tai, "goi", t)) for t in ten), "tep goi nam trong goi/")
        check(chay(T.goi_tong, tai, 0)[0] == "FZ_GOI_TONG 50 5000 5 5000 50", f"goi_tong moc 0: {chay(T.goi_tong, tai, 0)[0]}")
        check(chay(T.goi_tong, tai, 3)[0] == "FZ_GOI_TONG 20 1900 5 5000 50", f"goi_tong moc 3 (seq > 3): {chay(T.goi_tong, tai, 3)[0]}")
        check(chay(T.goi_tong, tai, 5)[0].startswith("FZ_GOI_TONG 0 0 5 "), "goi_tong moc 5: khong con van moi")
        # cua so 2500 the: moi nhat truoc: 800 (57) + 1100 (56) + 900 (55) = 2800 >= 2500 -> 3 goi, goi 4 la goi cuoi vua du
        out = chay(T.cua_so, tai, 2500)
        check(out[:3] == [f"GOI {ten[4]}", f"GOI {ten[3]}", f"GOI {ten[2]}"] and out[3] == "FZ_CUA_SO 3 30 2800 55-57", f"cua_so 2500: {out}")
        out = chay(T.cua_so, tai, 800)
        check(out == [f"GOI {ten[4]}", "FZ_CUA_SO 1 10 800 57-57"], f"cua_so 800 (goi moi nhat vua du): {out}")
        out = chay(T.cua_so, tai, 99999)
        check(out[-1] == "FZ_CUA_SO 5 50 5000 54-57", f"cua_so lon hon tat ca: lay het: {out[-1]}")
        # don_goi 2000 the, he so 1: giu 800 + 1100 + 900 (cong 2800 >= 2000 sau goi thu 3) -> xoa 2 goi cu
        out = chay(T.don_goi, tai, 2000, 1)
        check(out[-1].startswith("FZ_DON_GOI_XONG 2 "), f"don_goi xoa 2 goi cu: {out}")
        check(not os.path.exists(os.path.join(tai, "goi", ten[0])) and os.path.exists(os.path.join(tai, "goi", ten[2])), "goi cu mat, goi trong cua so con")


def _goi_gia(tai, cac):
    """Tao goi gia (tep rong, so van / the nam trong ten) theo thu tu: cac = [(mang, van, the), ...] -> seq 1, 2, ..."""
    d = os.path.join(tai, "goi")
    os.makedirs(d, exist_ok=True)
    for i, (mang, van, the) in enumerate(cac, 1):
        open(os.path.join(d, f"goi_{i:05d}_n{mang}_{van}_{the}.zip"), "wb").close()


def _cs(tai, r10, moc_ls, the_ls, lo=0, hi=10**9, muc=1000, them=0, dem=False, tren="-"):
    out = chay(lambda: T.cua_so_luot(tai, r10, lo, hi, muc, them, moc_ls, the_ls, tren, chi_dem=dem))
    seqs = sorted(int(l.split()[1][4:9]) for l in out if l.startswith("GOI "))
    return seqs, out


def test_cua_so_luot():
    print("E. cua_so_luot: cua so = goi cua R luot gan nhat (moi the hoc dung R lan)")
    with tempfile.TemporaryDirectory() as tai:
        # 4 luot: A = goi 1-3, B = 4-6, C = 7-9 (da xong; moc 3, 6, 9); D = luot dang chay = goi 10-14 (so cua so tang dot ngot: 5 goi thay vi 3)
        _goi_gia(tai, [(60, 10, 1700)] * 3 + [(61, 10, 1750)] * 3 + [(62, 10, 1800)] * 3 + [(63, 10, 1800)] * 5)
        seqs, out = _cs(tai, 40, "9,6,3", "5400,5250,5100")
        check(seqs == list(range(1, 15)) and out[-1] == "FZ_CUA_SO_CACH luot 4 0",
              f"R=4, moc 9,6,3 + moc 0 uoc tu the moi cua luot A: goi 1-14 ({seqs}, {out[-1]})")
        check(out[-2] == f"FZ_CUA_SO 14 140 {3 * 1700 + 3 * 1750 + 8 * 1800} 60-63", f"dong tong: {out[-2]}")
        seqs, _ = _cs(tai, 30, "9,6,3", "-")
        check(seqs == list(range(4, 15)), f"R=3: goi 4-14 = luot B, C, D ({seqs})")
        seqs, _ = _cs(tai, 35, "9,6,3,0", "-")
        check(seqs == list(range(2, 15)), f"R=3,5: luot B, C, D + NUA luot A (moi nhat truoc: goi 3, 2 >= 1/2 x 5100) ({seqs})")
        seqs, _ = _cs(tai, 20, "9,6,3", "-")
        check(seqs == list(range(7, 15)), f"R=2: goi 7-14 ({seqs})")
        seqs, _ = _cs(tai, 40, "9,6,3", "-")
        check(seqs == list(range(1, 15)), f"R=4 khong co the moi de uoc moc thu 4: van dung (cach uoc, lay het) ({seqs})")
        # moc chi co moc hien tai (vua chuyen sang): uoc moc 6, 3 tu so the moi 5400 (C), 5250 (B)
        seqs, out = _cs(tai, 30, "9", "5400,5250,5100")
        check(seqs == list(range(4, 15)) and out[-1] == "FZ_CUA_SO_CACH luot 3 3", f"chi co moc 9: uoc 6, 3 tu the moi -> goi 4-14 ({seqs}, {out[-1]})")
        seqs, out = _cs(tai, 30, "-", "5400,5250,5100")
        check(out[-1] == "FZ_CUA_SO_CACH uoc" and seqs == list(range(6, 15)),
              f"khong co moc: cach cu 3 x TB the moi (5250 x 3 = 15750) -> goi moi nhat toi khi du ({seqs})")
        seqs, _ = _cs(tai, 30, "9,6,3", "-", hi=12000)
        check(seqs == list(range(9, 15)), f"tran 12000 the: bo goi cu nhat cho toi khi <= tran ({seqs})")
        seqs, _ = _cs(tai, 20, "9,6,3", "-", lo=20000)
        check(seqs == list(range(3, 15)), f"san 20000 the: them goi cu hon (moi nhat truoc) ({seqs})")
        _, out = _cs(tai, 30, "9,6,3", "-", them=20, dem=True)
        per_van = sum([1700] * 3 + [1750] * 3 + [1800] * 8) / 140
        check(out == [f"FZ_CUA_SO_UOC {3 * 1750 + 8 * 1800 + int(20 * per_van)}"], f"--dem: cua so + 20 van cho gui ({out})")
        seqs, _ = _cs(tai, 30, "9,6,3", "-", tren="12")
        check(seqs == list(range(4, 13)), f"moc tren 12 (goi 13, 14 den SAU luc gom = luot sau): khong lay ({seqs})")
        # so cua so GIAM dot ngot: luot D chi 1 goi
        with tempfile.TemporaryDirectory() as tai2:
            _goi_gia(tai2, [(60, 10, 1700)] * 3 + [(61, 10, 1750)] * 3 + [(62, 10, 1800)] * 3 + [(63, 10, 1800)])
            seqs, _ = _cs(tai2, 40, "9,6,3,0", "-")
            check(seqs == list(range(1, 11)), f"luot D nho (1 goi): cua so van dung 4 luot, goi 1-10 ({seqs})")


def test_dong_thoi():
    print("C. nhieu tien trinh nhan goi cung luc: so thu tu khong trung")
    with tempfile.TemporaryDirectory() as tai:
        with multiprocessing.Pool(6) as pool:
            seqs = pool.map(_nhan, [(tai, 57)] * 24)
        check(sorted(seqs) == list(range(1, 25)), f"24 lan nhan -> so 1..24 khong trung ({sorted(seqs)[:5]}...)")
        check(len(T.ds_goi(tai)) == 24, "24 tep goi")


def test_nhap_cu():
    print("D. nhap_cu: thu muc games_gen<k>/ cua vong lap cu -> goi")
    with tempfile.TemporaryDirectory() as tai:
        for k, so in ((55, 3), (56, 4), (57, 2)):
            d = os.path.join(tai, f"games_gen{k}")
            os.makedirs(d)
            for i in range(so):
                shutil.copy(MAU[i % len(MAU)], os.path.join(d, f"1{k}_game_{i}.xz"))
        open(os.path.join(tai, "games_gen57", "hong.xz"), "wb").write(b"xz hong")
        out = chay(T.nhap_cu, tai, 57, 4)           # k = 54..57; 54 khong co thu muc
        check(out[-1] == "FZ_NHAP_XONG 3 3", f"nhap 3 goi, so thu tu lon nhat 3: {out}")
        ds = T.ds_goi(tai)
        check([(g[1], g[2]) for g in ds] == [(55, 3), (56, 4), (57, 2)], f"mang/van: {[(g[1], g[2]) for g in ds]} (van hong bi bo)")
        with zipfile.ZipFile(os.path.join(tai, "goi", ds[1][4])) as z:
            check(sorted(z.namelist())[0] == "games_gen56/156_game_0.xz", f"ten thanh vien giu mang: {sorted(z.namelist())[0]}")
        the_mong = sum(G.dem_the(open(MAU[i % len(MAU)], "rb").read()) for i in range(4))
        check(ds[1][3] == the_mong, f"so the goi 56 = {ds[1][3]} (mong {the_mong})")
        out2 = chay(T.nhap_cu, tai, 57, 4)
        check(out2[-1].startswith("FZ_NHAP_XONG 0 "), f"nhap lai: khong nhap hai lan ({out2})")


def main():
    test_dem_the()
    test_goi_nhan_tong_cua_so()
    test_cua_so_luot()
    test_dong_thoi()
    test_nhap_cu()
    print("\n" + "=" * 60)
    print(f"RESULT: {PASS} passed, {FAIL} failed")
    print("=" * 60)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
