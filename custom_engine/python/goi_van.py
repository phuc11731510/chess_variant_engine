"""goi_van.py -- GOI VAN cua vong lap lien tuc, chay TREN MAY COLAB (chi dung thu vien chuan: struct, lzma, zipfile).

Vong lap lien tuc (fz_lien_tuc.sh, menu fz -> w) khong doi het mot "doi" moi gom van: engine cu choi mai, cu moi ~50 van
cua mot may thi cua so Termux gom cac van MOI (chua gui) thanh mot goi .zip nho va tai ve dien thoai, trong luc engine van chay.

  python3 goi_van.py pack  <goc> --tk <ten tai khoan> --ra <thu muc> [--toi-thieu N]
      Tim moi thu muc van `<goc>/games_gen<MANG>_<RUN>/` (engine choi bang mang <MANG>, lan chay <RUN>; thu muc nay do o 04l dat
      ten), lay cac van da XONG (tep .xz; engine ghi tep .xz.tmp roi doi ten nen khong bao gio doc phai van do) chua gui
      (khong nam trong `<thu muc>/.da_goi`), dem so the cua tung van (doc phan dau tep nen, khong giai nen het), gom thanh MOT
      goi .zip (ZIP_STORED) cho moi thu muc co tu --toi-thieu van moi (mac dinh 1). Ten thanh vien trong zip:
      `games_gen<MANG>/<tk>_<RUN>_game_<g>.xz` -- tien to <tk>_<RUN> la duy nhat tren moi may / moi lan chay (engine danh so lai
      tu game_0 moi lan chay), thu muc `games_gen<MANG>` la cho train.py --stats-newest-gen biet mang nao da choi van do.
      In moi goi mot dong:  FZ_GOI <zip> <mang> <so van> <so the> <so byte cua zip>
      va ghi `<zip>.ds` (cac ten tep van da bo vao zip) de `commit` danh dau. Cuoi cung in FZ_GOI_XONG <so goi>.
      Van loi (khong giai nen duoc) KHONG gui, in canh bao FZ_GOI_BO <tep> MOT lan (ghi vao .da_goi nen lan sau khong bao lai).
  python3 goi_van.py commit <zip>.ds ...
      Goi da ve toi dien thoai: ghi cac ten tep trong <zip>.ds vao `<thu muc van>/.da_goi` (de lan pack sau khong gui lai) roi xoa <zip> va <zip>.ds.
      Thu muc van = dong dau cua tep .ds.
  python3 goi_van.py chua <goc>
      In FZ_CHUA <so van chua gui tren moi thu muc> (dung de kiem).

Tai sao `commit` tach rieng khoi `pack`: dien thoai tai ve LOI giua chung thi van van con chua danh dau, lan pack sau gui lai;
tai ve xong ma `commit` loi (mat mang ngay luc do) thi van gui hai lan -- hiem, va van trung chi la them vai van vao cua so huan luyen.
"""
import argparse
import glob
import os
import re
import struct
import sys
import zipfile
import lzma

_HEADER = struct.Struct("<4s7I")        # magic, revision, version, input_format, n (so the), l_total, lf, f  (xem trainingdata_v6.py)
_MAGIC = b"FZD6"
RE_DIR = re.compile(r"games_gen(\d+)_([A-Za-z0-9]+)$")
DA_GOI = ".da_goi"
_dem_goi = 0        # moi goi mot so rieng trong cung tien trinh (ten goi = pid + so nay)


def dem_the(data):
    """So the (ban ghi) trong mot van .xz (dau tep da giai nen). ValueError neu khong phai van hop le."""
    try:
        d = lzma.LZMADecompressor(format=lzma.FORMAT_XZ)
        head = d.decompress(data, max_length=_HEADER.size)
    except lzma.LZMAError as e:
        raise ValueError(f"xz hong: {e}") from None
    if len(head) < _HEADER.size:
        raise ValueError("tep van qua ngan")
    magic, rev, ver, fmt, n, _lt, _lf, _f = _HEADER.unpack_from(head, 0)
    if magic != _MAGIC:
        raise ValueError(f"khong phai van v6 (magic {magic!r})")
    return n


def _da_goi(thu_muc):
    try:
        with open(os.path.join(thu_muc, DA_GOI), encoding="utf-8") as f:
            return {d.strip() for d in f if d.strip()}
    except OSError:
        return set()


def _thu_muc_van(goc):
    out = []
    for d in sorted(glob.glob(os.path.join(goc, "games_gen*_*"))):
        m = RE_DIR.search(d.replace("\\", "/"))
        if m and os.path.isdir(d):
            out.append((d, int(m.group(1)), m.group(2)))
    return out


def _van_moi(thu_muc):
    da = _da_goi(thu_muc)
    return sorted(f for f in os.listdir(thu_muc) if f.endswith(".xz") and f not in da)


def pack(goc, tk, ra, toi_thieu=1, tai_lieu=None):
    os.makedirs(ra, exist_ok=True)
    so_goi = 0
    for d, mang, run in _thu_muc_van(goc):
        ten_tep = _van_moi(d)
        if len(ten_tep) < toi_thieu or not ten_tep:
            continue
        tien_to = f"{tk}_{run}"
        tam = os.path.join(ra, f".dang_goi_{tien_to}_{os.getpid()}.zip")
        ds, tong_the = [], 0
        with zipfile.ZipFile(tam, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as z:
            for t in ten_tep:
                p = os.path.join(d, t)
                try:
                    with open(p, "rb") as f:
                        data = f.read()
                    n = dem_the(data)
                except (OSError, ValueError) as e:
                    print(f"FZ_GOI_BO {p} ({e})", flush=True)
                    with open(os.path.join(d, DA_GOI), "a", encoding="utf-8") as f:     # chi canh bao mot lan
                        f.write(t + "\n")
                    continue
                zi = zipfile.ZipInfo(f"games_gen{mang}/{tien_to}_{t}", date_time=_gio(os.path.getmtime(p)))
                zi.compress_type = zipfile.ZIP_STORED
                z.writestr(zi, data)
                ds.append(t)
                tong_the += n
        if not ds:
            os.remove(tam)
            continue
        _dem_goi_tang()
        ten = f"g_{tien_to}_{mang}_{len(ds)}_{tong_the}_{os.getpid()}_{_dem_goi}.zip"
        dich = os.path.join(ra, ten)
        os.replace(tam, dich)
        with open(dich + ".ds", "w", encoding="utf-8") as f:
            f.write(d + "\n" + "\n".join(ds) + "\n")
        print(f"FZ_GOI {dich} {mang} {len(ds)} {tong_the} {os.path.getsize(dich)}", flush=True)
        so_goi += 1
    print(f"FZ_GOI_XONG {so_goi}", flush=True)
    return so_goi


def _dem_goi_tang():
    global _dem_goi
    _dem_goi += 1


def _gio(t):
    """date_time cua zip (gio dia phuong, 2 giay; nam >= 1980) -- train.py lay 4% van MOI NHAT (theo gio nay) lam tap kiem dinh neu bat."""
    import time
    g = time.localtime(max(t, 315532800))
    return (g.tm_year, g.tm_mon, g.tm_mday, g.tm_hour, g.tm_min, g.tm_sec)


def commit(ds_files):
    for ds in ds_files:
        try:
            with open(ds, encoding="utf-8") as f:
                dong = [d.rstrip("\n") for d in f if d.strip()]
        except OSError as e:
            print(f"FZ_COMMIT_LOI {ds} ({e})")
            continue
        thu_muc, ten_tep = dong[0], dong[1:]
        with open(os.path.join(thu_muc, DA_GOI), "a", encoding="utf-8") as f:
            f.write("\n".join(ten_tep) + "\n")
        for p in (ds, ds[:-3] if ds.endswith(".ds") else None):
            if p and os.path.exists(p):
                os.remove(p)
        print(f"FZ_COMMIT {len(ten_tep)} van tu {thu_muc}")


def chua(goc):
    tong = 0
    for d, mang, run in _thu_muc_van(goc):
        tong += len(_van_moi(d))
    print(f"FZ_CHUA {tong}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="lenh", required=True)
    p = sub.add_parser("pack")
    p.add_argument("goc")
    p.add_argument("--tk", required=True)
    p.add_argument("--ra", required=True)
    p.add_argument("--toi-thieu", type=int, default=1)
    p = sub.add_parser("commit")
    p.add_argument("ds", nargs="+")
    p = sub.add_parser("chua")
    p.add_argument("goc")
    a = ap.parse_args(argv)
    if a.lenh == "pack":
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,20}", a.tk):
            sys.exit("--tk phai la chu / so / _ / -, toi da 20 ky tu")
        pack(a.goc, a.tk.replace("-", "_"), a.ra, a.toi_thieu)
    elif a.lenh == "commit":
        commit(a.ds)
    else:
        chua(a.goc)


if __name__ == "__main__":
    main()
