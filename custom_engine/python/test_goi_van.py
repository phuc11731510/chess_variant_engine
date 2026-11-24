"""Kiem thu goi_van.py (goi van cua vong lap lien tuc) tren VAN THAT (mau_van/*.xz) -- khong can engine.

  A. dem_the = so ban ghi that (doi chieu voi trainingdata_v6.decode_arrays) tren moi van mau; van hong / sai magic bi tu choi.
  B. pack: dung cau truc thu muc `games_gen<MANG>_<RUN>/`; tep .xz.tmp (van dang ghi) KHONG vao goi; ten thanh vien
     `games_gen<MANG>/<tk>_<RUN>_<tep>`; so van / so the dung; moi thu muc mot goi; van hong bi bo (FZ_GOI_BO).
  C. commit: lan pack sau KHONG gui lai van da commit, nhung gui van moi sinh them; pack roi KHONG commit thi gui lai du (dien thoai tai loi).
  D. --toi-thieu: thu muc it van hon nguong khong tao goi.
  E. train.py doc duoc goi (list_games / newest_generation) va thong_ke dung mang moi nhat.

Chay:  python test_goi_van.py
"""
import glob
import os
import re
import shutil
import sys
import tempfile
import zipfile
import io
import contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import goi_van as G  # noqa: E402

PASS = FAIL = 0


def check(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [ok] {msg}")
    else:
        FAIL += 1
        print(f"  [FAIL] {msg}")


def chay(*args):
    """goi_van.main(args), tra ve cac dong in ra."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        G.main(list(args))
    return buf.getvalue().splitlines()


MAU = sorted(glob.glob(os.path.join(HERE, "mau_van", "*.xz")))


def dem_that(p):
    import trainingdata_v6 as V
    with open(p, "rb") as f:
        return int(V.decode_arrays(f.read(), p)["n"])


def test_dem_the():
    print("A. dem_the")
    check(len(MAU) >= 2, f"co {len(MAU)} van mau")
    for p in MAU:
        data = open(p, "rb").read()
        check(G.dem_the(data) == dem_that(p), f"{os.path.basename(p)}: {G.dem_the(data)} the = so ban ghi that")
    for ten, data in (("xz hong", MAU and open(MAU[0], "rb").read()[:50]), ("khong phai xz", b"khong phai xz" * 10)):
        try:
            G.dem_the(data)
            check(False, f"{ten} phai bi tu choi")
        except ValueError:
            check(True, f"{ten} bi tu choi (ValueError)")


def tao(goc, mang, run, so_van, bat_dau=0):
    d = os.path.join(goc, f"games_gen{mang}_{run}")
    os.makedirs(d, exist_ok=True)
    for i in range(so_van):
        shutil.copy(MAU[(bat_dau + i) % len(MAU)], os.path.join(d, f"game_{bat_dau + i}.xz"))
    return d


def test_pack_commit():
    print("B/C/D. pack, commit, toi-thieu")
    with tempfile.TemporaryDirectory() as tmp:
        goc, ra = os.path.join(tmp, "content"), os.path.join(tmp, "ra")
        d1 = tao(goc, 57, "1124120000", 5)
        d2 = tao(goc, 58, "1124120500", 2)
        open(os.path.join(d1, "game_99.xz.tmp"), "wb").write(b"dang ghi do")        # van dang ghi: khong duoc vao goi
        open(os.path.join(d1, "game_98.xz"), "wb").write(b"xz hong")                  # van hong
        out = chay("pack", goc, "--tk", "tk-a", "--ra", ra)
        goi = [l.split() for l in out if l.startswith("FZ_GOI ")]
        check(len(goi) == 2, f"hai thu muc -> hai goi ({len(goi)})")
        check(any(l.startswith("FZ_GOI_BO") and "game_98.xz" in l for l in out), "van hong bi bo (FZ_GOI_BO)")
        by_net = {int(g[2]): g for g in goi}
        check(by_net[57][3] == "5" and by_net[58][3] == "2", f"so van moi goi {by_net[57][3]}, {by_net[58][3]}")
        mong = sum(dem_that(MAU[i % len(MAU)]) for i in range(5))
        check(int(by_net[57][4]) == mong, f"so the goi 57 = {by_net[57][4]} (mong {mong})")
        with zipfile.ZipFile(by_net[57][1]) as z:
            ten = sorted(z.namelist())
        check(all(re.fullmatch(r"games_gen57/tk_a_1124120000_game_\d\.xz", n) for n in ten), f"ten thanh vien dung: {ten[0]}")
        check(not any(n.endswith(".tmp") for n in ten), "tep .tmp khong vao goi")
        check(os.path.exists(by_net[57][1] + ".ds"), "co tep .ds")
        # train.py doc duoc goi: list_games + newest_generation
        import dataset as D
        games = D.list_games(by_net[57][1] + "," + by_net[58][1])
        top, newest = D.newest_generation(games)
        check(len(games) == 7 and top == 58 and len(newest) == 2, f"list_games doc 7 van, mang moi nhat {top} ({len(newest)} van)")
        # Khong commit -> pack lai gui lai du
        out2 = chay("pack", goc, "--tk", "tk-a", "--ra", ra)
        check(sum(l.startswith("FZ_GOI ") for l in out2) == 2, "chua commit -> gui lai ca hai goi")
        for p in glob.glob(os.path.join(ra, "*.zip")) + glob.glob(os.path.join(ra, "*.ds")):
            if p not in {g[1] for g in goi} | {g[1] + ".ds" for g in goi}:
                os.remove(p)
        # commit goi cua 57 -> lan sau chi gui van moi
        out3 = chay("commit", by_net[57][1] + ".ds")
        check(any(l.startswith("FZ_COMMIT 5 ") for l in out3), f"commit 5 van: {out3}")
        check(not os.path.exists(by_net[57][1]) and not os.path.exists(by_net[57][1] + ".ds"), "commit xoa zip va .ds")
        tao(goc, 57, "1124120000", 3, bat_dau=5)
        for p in glob.glob(os.path.join(ra, "*")):
            os.remove(p)
        out4 = chay("pack", goc, "--tk", "tk-a", "--ra", ra)
        g4 = {int(l.split()[2]): l.split() for l in out4 if l.startswith("FZ_GOI ")}
        check(g4[57][3] == "3", f"sau commit chi con 3 van moi cua mang 57 ({g4[57][3]})")
        check(g4[58][3] == "2", "mang 58 chua commit -> van du 2 van")
        check(chay("chua", goc) == ["FZ_CHUA 5"], f"chua = 5: {chay('chua', goc)}")
        # --toi-thieu
        for p in glob.glob(os.path.join(ra, "*")):
            os.remove(p)
        out5 = chay("pack", goc, "--tk", "tk-a", "--ra", ra, "--toi-thieu", "3")
        g5 = [l for l in out5 if l.startswith("FZ_GOI ")]
        check(len(g5) == 1 and g5[0].split()[2] == "57", f"--toi-thieu 3: chi thu muc 57 ({len(g5)} goi)")


def main():
    test_dem_the()
    test_pack_commit()
    print("\n" + "=" * 60)
    print(f"RESULT: {PASS} passed, {FAIL} failed")
    print("=" * 60)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
