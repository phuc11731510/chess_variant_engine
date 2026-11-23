#!/usr/bin/env python3
"""fz_nhat_ky.py -- ghi LAI TOAN BO chu hien tren man hinh cua mot cua so Termux (menu, vong lap tu dong, va ca log
kéo tu Colab ve) vao MOT tep rieng cua cua so do, ma chuong trinh ben trong van chay NHU BINH THUONG (nhu lenh `script`).

  python3 ~/fz_nhat_ky.py -- bash ~/fz_menu.sh [doi so ...]

  - Moi lan chay (moi cua so, moi lan mo lai) tao MOT tep moi:  ~/fz_nhat_ky/cua_so_<YYYYmmdd_HHMMSS>_<pid>.log
    (pid cua so cung la so dau moi dong cua ~/.fz_tk/.tu_dong/nhat_ky.txt, de doi chieu).
  - Moi dong co tien to gio [HH:MM:SS]. Ma mau, ma di chuyen con tro duoc bo; ky tu \\r (thanh tien do cua pip, wget, ...) va
    \\b ghi de len dong dang viet nen moi thanh tien do chi con dong cuoi cung.
  - Tep qua --max-dong dong (mac dinh 20000) thi cat bo phan dau, chi giu --giu-dong dong cuoi (mac dinh 10000).
  - Luc bat dau xoa cac tep cua so_*.log trong thu muc ma KHONG THAY DOI da hon --ngay ngay (mac dinh 7): nhat ky cu cua
    cua so da dong. Chi dung dung mau ten cua_so_*.log do chinh tep nay tao.
  - Chi bao khi stdin VA stdout deu la terminal. Khong phai terminal (ssh khong -t, cron, ong dan), hoac bat ky loi nao luc
    khoi tao: chay thang chuong trinh, khong ghi gi -- nhat ky khong bao gio duoc phep lam hong cua so.
  - FZ_KHONG_NHAT_KY=1: khong ghi. Chuong trinh ben trong thay FZ_NK_ACTIVE=1 (de khong boc hai lan) va FZ_NK_TEP=<duong dan tep>.

Doc nhat ky tu may tinh:  ssh dt 'tail -n 80 ~/fz_nhat_ky/cua_so_*.log'  (tep moi nhat: ls -t).
"""

import codecs
import errno
import fcntl
import os
import pty
import select
import signal
import struct
import sys
import termios
import time
import tty

MAU_TEN = "cua_so_"
DUOI_TEN = ".log"


# ---------------------------------------------------------------------------------------------------------------
# Dung lai chu hien tren man hinh tu luong byte cua terminal
# ---------------------------------------------------------------------------------------------------------------
class ManHinh:
    """May trang thai nho: nhan chuoi chu (co ma dieu khien) cua terminal, dua ra TUNG DONG chu thuan khi gap \\n.
    Xu ly: ma ANSI (CSI, OSC, chon bo ky tu) bi bo; \\r dua con tro ve dau dong va chu sau do GHI DE; \\b lui con tro;
    \\t chen dau cach toi cot boi cua 8; CSI K (xoa dong), C/D/G (di chuyen ngang) duoc hieu; ma dieu khien con lai bi bo."""

    def __init__(self, ra):
        self.ra = ra                  # ra(dong: str) -- nhan moi dong hoan chinh
        self.dong = []                # cac ky tu cua dong dang viet
        self.cot = 0                  # vi tri con tro trong dong
        self.tt = 0                   # 0 thuong, 1 sau ESC, 2 trong CSI, 3 trong OSC, 4 OSC thay ESC, 5 chon bo ky tu
        self.tham_so = ""             # tham so cua CSI dang doc
        self.giai_ma = codecs.getincrementaldecoder("utf-8")(errors="replace")

    def them(self, byte):
        """Nhan mot doan byte (co the cat giua ky tu UTF-8 hoac giua mot ma ANSI)."""
        for ch in self.giai_ma.decode(byte):
            self._ky_tu(ch)

    def _ghi(self, ch):
        if self.cot < len(self.dong):
            self.dong[self.cot] = ch
        else:
            self.dong.append(ch)
        self.cot += 1

    def _xuong_dong(self):
        self.ra("".join(self.dong).rstrip())
        self.dong, self.cot = [], 0

    def _ky_tu(self, ch):
        if self.tt == 0:
            if ch == "\x1b":
                self.tt = 1
            elif ch == "\n":
                self._xuong_dong()
            elif ch == "\r":
                self.cot = 0
            elif ch == "\b":
                self.cot = max(0, self.cot - 1)
            elif ch == "\t":
                for _ in range(8 - self.cot % 8):
                    self._ghi(" ")
            elif ch >= " " and ch != "\x7f":
                self._ghi(ch)
            return
        if self.tt == 1:
            if ch == "[":
                self.tt, self.tham_so = 2, ""
            elif ch == "]":
                self.tt = 3
            elif ch in "()":
                self.tt = 5
            else:
                self.tt = 0          # ma ESC mot ky tu (ESC 7, ESC 8, ESC =, ESC c, ...): bo
            return
        if self.tt == 2:
            if "\x40" <= ch <= "\x7e":           # ky tu cuoi cua CSI
                self._csi(ch, self.tham_so)
                self.tt = 0
            else:
                self.tham_so += ch
            return
        if self.tt == 3:                          # OSC: den BEL hoac ESC \
            if ch == "\x07":
                self.tt = 0
            elif ch == "\x1b":
                self.tt = 4
            return
        if self.tt == 4:
            self.tt = 0                           # ESC \ (hoac ESC bat ky) ket thuc OSC
            return
        if self.tt == 5:
            self.tt = 0
            return

    def _csi(self, cuoi, tham_so):
        so = tham_so.lstrip("?>=!")
        try:
            n = int(so.split(";")[0]) if so.split(";")[0] else None
        except ValueError:
            n = None
        if cuoi == "K":                            # xoa dong: 0/mac dinh tu con tro, 1 den con tro, 2 ca dong
            if n in (None, 0):
                del self.dong[self.cot:]
            elif n == 1:
                for i in range(min(self.cot, len(self.dong))):
                    self.dong[i] = " "
            elif n == 2:
                self.dong = []
        elif cuoi == "C":                          # con tro sang phai n o (lap khoang trang neu qua cuoi dong)
            for _ in range(n or 1):
                if self.cot >= len(self.dong):
                    self.dong.append(" ")
                self.cot += 1
        elif cuoi == "D":
            self.cot = max(0, self.cot - (n or 1))
        elif cuoi == "G":
            self.cot = max(0, (n or 1) - 1)
            while len(self.dong) < self.cot:
                self.dong.append(" ")
        # cac ma khac (di chuyen len/xuong, mau 'm', ...): bo

    def ket_thuc(self):
        """Dong dang viet do dang (vi du cau hoi cho nguoi go) -- dua ra khi cua so dong."""
        if self.dong:
            self.ra("".join(self.dong).rstrip())
            self.dong, self.cot = [], 0


# ---------------------------------------------------------------------------------------------------------------
# Tep nhat ky: moi dong co gio, tu cat khi qua dai, tu don tep cu
# ---------------------------------------------------------------------------------------------------------------
class TepNhatKy:
    def __init__(self, duong_dan, max_dong, giu_dong):
        self.duong_dan, self.max_dong, self.giu_dong = duong_dan, max_dong, giu_dong
        self.f = open(duong_dan, "a", encoding="utf-8")
        self.n = 0

    def dong_moi(self, chu):
        self.f.write(f"[{time.strftime('%H:%M:%S')}] {chu}\n")
        self.f.flush()
        self.n += 1
        if self.n > self.max_dong:
            self.cat()

    def cat(self):
        """Giu giu_dong dong cuoi; dong dau ghi lai da cat bao nhieu dong (tinh vao so dong)."""
        self.f.close()
        with open(self.duong_dan, encoding="utf-8", errors="replace") as f:
            tat_ca = f.read().splitlines()
        bo = len(tat_ca) - self.giu_dong
        giu = tat_ca[-self.giu_dong:] if self.giu_dong > 0 else []
        tam = self.duong_dan + ".tmp"
        with open(tam, "w", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] === da cat bo {max(bo, 0)} dong dau (qua {self.max_dong} dong, giu {self.giu_dong} dong cuoi) ===\n")
            f.write("".join(d + "\n" for d in giu))
        os.replace(tam, self.duong_dan)
        self.f = open(self.duong_dan, "a", encoding="utf-8")
        self.n = len(giu) + 1

    def dong_tep(self):
        try:
            self.f.close()
        except OSError:
            pass


def don_cu(thu_muc, so_ngay, bay_gio=None):
    """Xoa cac tep cua_so_*.log (va .tmp cat dang) KHONG THAY DOI hon so_ngay ngay. Tra ve so tep da xoa."""
    bay_gio = time.time() if bay_gio is None else bay_gio
    da_xoa = 0
    for ten in os.listdir(thu_muc):
        if not (ten.startswith(MAU_TEN) and (ten.endswith(DUOI_TEN) or ten.endswith(DUOI_TEN + ".tmp"))):
            continue
        p = os.path.join(thu_muc, ten)
        try:
            if os.path.isfile(p) and bay_gio - os.path.getmtime(p) > so_ngay * 86400:
                os.remove(p)
                da_xoa += 1
        except OSError:
            pass
    return da_xoa


# ---------------------------------------------------------------------------------------------------------------
def _kich_thuoc_cua_so(tu_fd, den_fd):
    try:
        fcntl.ioctl(den_fd, termios.TIOCSWINSZ, fcntl.ioctl(tu_fd, termios.TIOCGWINSZ, struct.pack("HHHH", 0, 0, 0, 0)))
    except OSError:
        pass


def _ghi_het(fd, data):
    while data:
        try:
            n = os.write(fd, data)
        except InterruptedError:
            continue
        except BlockingIOError:
            select.select([], [fd], [], 1.0)
            continue
        data = data[n:]


def _ma_thoat(status):
    if os.WIFEXITED(status):
        return os.WEXITSTATUS(status)
    if os.WIFSIGNALED(status):
        return 128 + os.WTERMSIG(status)
    return 1


def chay(lenh, thu_muc, max_dong=20000, giu_dong=10000, so_ngay=7):
    """Chay `lenh` trong mot pty, sao chep ra man hinh that va ghi nhat ky. Tra ve ma thoat cua `lenh`."""
    os.environ["FZ_NK_ACTIVE"] = "1"
    try:
        os.makedirs(thu_muc, exist_ok=True)
        don_cu(thu_muc, so_ngay)
        ten = f"{MAU_TEN}{time.strftime('%Y%m%d_%H%M%S')}_{os.getpid()}{DUOI_TEN}"
        tep = TepNhatKy(os.path.join(thu_muc, ten), max_dong, giu_dong)
        os.environ["FZ_NK_TEP"] = tep.duong_dan
    except Exception:
        os.execvp(lenh[0], lenh)        # loi luc khoi tao: chay thang, khong ghi

    man = ManHinh(tep.dong_moi)
    tep.dong_moi(f"=== cua so pid={os.getpid()} bat dau {time.strftime('%d/%m/%Y %H:%M:%S')}: {' '.join(lenh)} ===")
    try:
        pid, fd = pty.fork()
    except OSError:
        tep.dong_moi("=== khong tao duoc pty: chay thang, khong ghi ===")
        tep.dong_tep()
        os.execvp(lenh[0], lenh)
    if pid == 0:                        # con: chay chuong trinh that tren pty
        try:
            os.execvp(lenh[0], lenh)
        except OSError as e:
            sys.stderr.write(f"fz_nhat_ky: khong chay duoc {lenh[0]}: {e}\n")
            os._exit(127)

    _kich_thuoc_cua_so(0, fd)
    cu = termios.tcgetattr(0)
    ma_thoat = None
    bi_dung = []                        # tin hieu nhan duoc (de ghi vao nhat ky)

    def doi_kich_thuoc(_s, _f):
        _kich_thuoc_cua_so(0, fd)

    def chuyen_tin_hieu(so, _f):
        bi_dung.append(so)
        try:
            os.kill(pid, so)
        except OSError:
            pass

    signal.signal(signal.SIGWINCH, doi_kich_thuoc)
    for s in (signal.SIGHUP, signal.SIGTERM):
        signal.signal(s, chuyen_tin_hieu)
    tty.setraw(0)
    try:
        stdin_mo = True
        while True:
            doc = [fd] + ([0] if stdin_mo else [])
            try:
                san, _, _ = select.select(doc, [], [], 0.5)
            except InterruptedError:
                continue
            if 0 in san:
                try:
                    du_lieu = os.read(0, 4096)
                except OSError:
                    du_lieu = b""
                if du_lieu:
                    _ghi_het(fd, du_lieu)
                else:
                    stdin_mo = False
                    _ghi_het(fd, b"\x04")
            het = False
            if fd in san:
                try:
                    du_lieu = os.read(fd, 65536)
                except OSError as e:
                    du_lieu = b""
                    if e.errno not in (errno.EIO, errno.EBADF):
                        raise
                if du_lieu:
                    _ghi_het(1, du_lieu)
                    man.them(du_lieu)
                else:
                    het = True
            if ma_thoat is None:
                got, st = os.waitpid(pid, os.WNOHANG)
                if got:
                    ma_thoat = _ma_thoat(st)
                    # con da thoat nhung tien trinh nen co the giu pty: rut not phan con lai trong chốc lát
                    han = time.time() + 0.5
                    while time.time() < han:
                        s2, _, _ = select.select([fd], [], [], 0.1)
                        if not s2:
                            continue
                        try:
                            du_lieu = os.read(fd, 65536)
                        except OSError:
                            break
                        if not du_lieu:
                            break
                        _ghi_het(1, du_lieu)
                        man.them(du_lieu)
                    het = True
            if het:
                break
    finally:
        termios.tcsetattr(0, termios.TCSAFLUSH, cu)
        for s in (signal.SIGHUP, signal.SIGTERM):
            signal.signal(s, signal.SIG_DFL)
        if ma_thoat is None:
            try:
                _, st = os.waitpid(pid, 0)
                ma_thoat = _ma_thoat(st)
            except ChildProcessError:
                ma_thoat = 1
        man.ket_thuc()
        ghi_chu = f", nhan tin hieu {','.join(str(s) for s in bi_dung)}" if bi_dung else ""
        tep.dong_moi(f"=== cua so pid={os.getpid()} ket thuc {time.strftime('%d/%m/%Y %H:%M:%S')}, ma thoat {ma_thoat}{ghi_chu} ===")
        tep.dong_tep()
    return ma_thoat


def main(argv):
    if argv[1:2] == ["--kiem-tra"]:     # menu.sh goi de biet tep nay chay duoc truoc khi boc cua so (tep tai hong -> khong boc)
        return 0
    thu_muc = os.environ.get("FZ_NK_THU_MUC") or os.path.join(os.path.expanduser("~"), "fz_nhat_ky")
    max_dong, giu_dong, so_ngay = 20000, 10000, 7
    i = 1
    while i < len(argv) and argv[i] != "--":
        a = argv[i]
        if a in ("--dir", "--max-dong", "--giu-dong", "--ngay") and i + 1 < len(argv):
            v = argv[i + 1]
            if a == "--dir":
                thu_muc = v
            elif a == "--max-dong":
                max_dong = int(v)
            elif a == "--giu-dong":
                giu_dong = int(v)
            else:
                so_ngay = float(v)
            i += 2
        else:
            sys.stderr.write(f"fz_nhat_ky: tham so la: {a}\n")
            return 2
        continue
    lenh = argv[i + 1:] if i < len(argv) else []
    if not lenh:
        sys.stderr.write("dung: fz_nhat_ky.py [--dir D] [--max-dong N] [--giu-dong N] [--ngay N] -- lenh [doi so ...]\n")
        return 2
    if giu_dong >= max_dong:
        giu_dong = max_dong // 2
    # Khong phai terminal, hoac nguoi dung tat: chay thang (khong boc).
    if os.environ.get("FZ_KHONG_NHAT_KY") or os.environ.get("FZ_NK_ACTIVE") or not (os.isatty(0) and os.isatty(1)):
        os.execvp(lenh[0], lenh)
    return chay(lenh, thu_muc, max_dong, giu_dong, so_ngay)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
