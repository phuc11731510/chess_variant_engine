#!/usr/bin/env python3
"""fz_lay_ve.py -- phan "o lenh" cua lay_ve.sh: cap nhat tung o trong Download/FairyZero/o_lenh tu ban moi nhat tren GitHub
va CHI doi dung cai da doi, ma khong ghi de cho ban da sua.

Moi o co ba phien ban: BAN GOC (ban moi nhat lay ve lan truoc, luu o <state>/co_so/<o>.py), BAN CUA BAN (tep trong o_lenh,
co the da sua tay hoac menu da ghi SECS/GAMES/GEN_CURRENT vao) va BAN MOI (tren GitHub). Quyet dinh cho tung o:

  chua co o do                          -> tai ve                                           [tai]
  ban cua ban == ban moi                -> khong lam gi (chi ghi nho ban goc)               [=]
  ban cua ban == ban goc, ban moi khac  -> ban khong sua gi: thay bang ban moi              [moi]
  ban cua ban != ban goc, ban moi == ban goc -> giu ban cua ban (ban moi khong doi gi)      [giu]
  ca hai cung doi                       -> TRON ba ben (diff3 theo dong): tron duoc thi ghi ket qua    [tron]
                                           cung sua mot cho: KHONG ghi de, ban moi luu o <o>.py.moi   [XUNG DOT]
  chua co ban goc (lan dau dung cach nay) va ban cua ban khac ban moi -> khong biet ban da sua chua:
                                           KHONG ghi de, ban moi luu o <o>.py.moi                      [chua ro]

  -f           : ep thay TAT CA cac o bang ban moi (ghi de ca phan ban da sua)
  <so> [<so>]  : ep thay RIENG cac o do (vd 08)
  --xem        : chi cho biet se lam gi, khong ghi gi

Ghi chu: xuong dong kieu Windows (\\r\\n) duoc coi nhu nhau khi so sanh. Ban goc o  <state>/co_so/. Mang loi o mot o thi bo qua o do.
"""

import argparse
import difflib
import os
import sys
import time
import urllib.error
import urllib.request


def chuan(s):
    return s.replace("\r\n", "\n")


def doc(path):
    try:
        with open(path, "r", encoding="utf-8", newline="") as f:
            return f.read()
    except FileNotFoundError:
        return None


def ghi(path, noi_dung):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tam = f"{path}.tmp{os.getpid()}"
    with open(tam, "w", encoding="utf-8", newline="") as f:
        f.write(noi_dung)
    os.replace(tam, path)


def tai(url, thu=3):
    """Noi dung (str) cua url, hoac None khi loi mang / 404 sau `thu` lan."""
    loi = None
    for lan in range(thu):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            loi = e
            if e.code in (404, 401, 403):
                break
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            loi = e
        time.sleep(1.0 + lan)
    sys.stderr.write(f"   (khong tai duoc {url}: {loi})\n")
    return None


def _khop(x, y):
    """Voi moi chi so i cua x: chi so tuong ung trong y theo cac khoi khop cua SequenceMatcher, hoac None."""
    m = [None] * len(x)
    for blk in difflib.SequenceMatcher(None, x, y, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            m[blk.a + k] = blk.b + k
    return m


def tron_ba_ben(co_so, a, b):
    """diff3 theo dong. co_so, a (ban cua ban), b (ban moi): danh sach dong. Tra ve (ket qua, so cho xung dot).
    Giua hai dong ma ca ba ban cung co (dong 'dong bo') la mot khuc: ben nao khong doi so voi ban goc thi lay ben kia;
    hai ben giong nhau thi lay mot; hai ben khac nhau va khac ban goc = xung dot (ket qua tam lay ban cua ban)."""
    ma, mb = _khop(co_so, a), _khop(co_so, b)
    dong_bo = [i for i in range(len(co_so)) if ma[i] is not None and mb[i] is not None]
    ra, xung_dot = [], 0
    pi, pa, pb = -1, -1, -1
    for i in dong_bo + [len(co_so)]:
        ai = ma[i] if i < len(co_so) else len(a)
        bi = mb[i] if i < len(co_so) else len(b)
        k_co, k_a, k_b = co_so[pi + 1:i], a[pa + 1:ai], b[pb + 1:bi]
        if k_a == k_co:
            ra += k_b
        elif k_b == k_co or k_a == k_b:
            ra += k_a
        else:
            xung_dot += 1
            ra += k_a
        if i < len(co_so):
            ra.append(co_so[i])
        pi, pa, pb = i, ai, bi
    return ra, xung_dot


def _dong(s):
    return s.split("\n")


def doi_dong(truoc, sau):
    """(so dong them, so dong bo) giua hai noi dung, de bao cho ngan gon."""
    them = bo = 0
    for d in difflib.unified_diff(_dong(truoc), _dong(sau), lineterm="", n=0):
        if d.startswith("+") and not d.startswith("+++"):
            them += 1
        elif d.startswith("-") and not d.startswith("---"):
            bo += 1
    return them, bo


def xu_ly_mot_o(ten, url, thu_muc, co_so_dir, ep, xem):
    """Tra ve (nhan, thong bao). nhan: tai | moi | = | giu | tron | xung dot | chua ro | thay | loi."""
    f = os.path.join(thu_muc, ten + ".py")
    p_co_so = os.path.join(co_so_dir, ten + ".py")
    p_moi = f + ".moi"
    moi = tai(f"{url}/{ten}.py")
    if moi is None:
        return "loi", f"{ten}.py: khong tai duoc ban moi -- giu nguyen"
    cua_ban, co_so = doc(f), doc(p_co_so)

    def ghi_nho(noi_dung):
        if not xem:
            ghi(p_co_so, noi_dung)
            if os.path.exists(p_moi):
                os.remove(p_moi)

    if ep:
        if cua_ban is not None and chuan(cua_ban) == chuan(moi):
            ghi_nho(moi)
            return "=", f"{ten}.py: da giong ban moi"
        if not xem:
            ghi(f, moi)
        ghi_nho(moi)
        return ("tai" if cua_ban is None else "thay"), f"{ten}.py: {'tai ve' if cua_ban is None else 'thay bang ban moi (ep)'}"
    if cua_ban is None:
        if not xem:
            ghi(f, moi)
        ghi_nho(moi)
        return "tai", f"{ten}.py: chua co -> tai ve"
    if chuan(cua_ban) == chuan(moi):
        if co_so is None or chuan(co_so) != chuan(moi):
            ghi_nho(moi)
        elif os.path.exists(p_moi) and not xem:
            os.remove(p_moi)
        return "=", f"{ten}.py: giong ban moi"
    if co_so is None:
        if not xem:
            ghi(p_moi, moi)
        them, bo = doi_dong(cua_ban, moi)
        return "chua ro", (f"{ten}.py: khac ban moi (+{them} -{bo} dong) nhung may chua luu ban goc (lan dau dung cach nay) -- "
                           f"KHONG ghi de. Ban moi o {ten}.py.moi. Neu ban chua sua o nay:  bash ~/lay_ve.sh {ten.split('_')[0]}")
    if chuan(cua_ban) == chuan(co_so):                     # ban khong sua gi
        them, bo = doi_dong(cua_ban, moi)
        if not xem:
            ghi(f, moi)
        ghi_nho(moi)
        return "moi", f"{ten}.py: co ban moi (+{them} -{bo} dong), ban khong sua o nay -> da thay"
    if chuan(moi) == chuan(co_so):                         # ban sua, ban moi khong doi
        return "giu", f"{ten}.py: ban da sua, ban moi khong doi gi -> giu ban cua ban"
    ket_qua, xd = tron_ba_ben(_dong(chuan(co_so)), _dong(chuan(cua_ban)), _dong(chuan(moi)))
    if xd == 0:
        them, bo = doi_dong(cua_ban, "\n".join(ket_qua))
        if not xem:
            ghi(f, "\n".join(ket_qua))
        ghi_nho(moi)
        return "tron", f"{ten}.py: ban sua + ban moi doi o cho khac -> da TRON (giu phan ban sua, them phan moi: +{them} -{bo} dong)"
    if not xem:
        ghi(p_moi, moi)
    return "xung dot", (f"{ten}.py: ban va ban moi cung sua {xd} cho -- KHONG ghi de. Ban moi o {ten}.py.moi "
                        f"(so sanh: diff {ten}.py {ten}.py.moi). Thay hoan toan:  bash ~/lay_ve.sh {ten.split('_')[0]}")


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--url", required=False)
    ap.add_argument("--dir", help="thu muc o lenh (Download/FairyZero/o_lenh)")
    ap.add_argument("--state", default=os.path.join(os.path.expanduser("~"), ".fz_lay_ve"))
    ap.add_argument("--cells", help="danh sach o, cach nhau bang dau cach")
    ap.add_argument("--xem", action="store_true")
    ap.add_argument("-f", dest="ep_het", action="store_true")
    ap.add_argument("--kiem-tra", action="store_true")
    ap.add_argument("ids", nargs="*", help="so o can ep thay (vd 08)")
    a = ap.parse_args(argv[1:])
    if a.kiem_tra:
        return 0
    if not (a.url and a.dir and a.cells):
        ap.error("can --url, --dir va --cells")
    ten_o = a.cells.split()
    co_so_dir = os.path.join(a.state, "co_so")
    dem, thong_bao = {}, []
    for ten in ten_o:
        ep = a.ep_het or ten.split("_")[0] in a.ids
        nhan, msg = xu_ly_mot_o(ten, a.url, a.dir, co_so_dir, ep, a.xem)
        dem[nhan] = dem.get(nhan, 0) + 1
        if nhan != "=":
            print(f"[{nhan}]".ljust(11) + msg)
    prefix = "(chi xem, khong ghi gi) " if a.xem else ""
    tom_tat = ", ".join(f"{v} {k}" for k, v in sorted(dem.items()))
    print(f"{prefix}[o lenh] {tom_tat}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
