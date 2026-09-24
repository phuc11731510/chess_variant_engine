"""fz_may.py -- phan chay TREN MAY COLAB cua menu fz.

menu.sh gui tep nay len /content/fz_log/fz_may.py moi lan chay mot o, roi chay o QUA SSH -- khong
dung kernel Jupyter cua may (kernel chet / khoi dong lai khong anh huong; xem fz_nhan_may.py):
  - qua ssh:  python3 fz_may.py khoi_dong <o> [ep] < ma_b64  -> o chay nen; in "FZ_PID=<pid>" /
              "FZ_BAN=<o>" (dang co o khac chay nen)
  - qua ssh:  python3 fz_may.py chay_nhanh <o> < ma_b64      -> o nhanh, chay ngay, in thang ra ssh
  - duong cu (ssh hong): trong kernel colab exec: khoi_dong(o, ma_b64, ep)
Phien ssh co moi truong KHAC kernel (PATH, LD_LIBRARY_PATH toi driver GPU /usr/lib64-nvidia, cac
bien COLAB_*...). Nen moi may, menu chup moi truong kernel MOT lan (colab exec) vao env.json; o
chay qua ssh dung dung moi truong do. Chua co env.json: khoi_dong/chay_nhanh thoat 97, khong
chay gi.
  - qua ssh:  python3 /content/fz_log/fz_may.py theo_doi <o> <pid> [n]   -> log truc tiep
              (n: chi in n dong cuoi roi theo tiep -- dung khi noi lai sau rot mang)
O 05, 09 cung doc tep nay (trang_thai, dung_o).

Trang thai mot o chay nen (trang_thai) -- khong doan theo thoi gian hay noi dung log:
  xong  co tep <o>.rc: vo bash boc o ghi ma thoat vao do NGAY KHI IPython chay o ket thuc
        (ghi sau dong "[fz] o .. xong" cua log, ghi qua tep tam + mv nen khong bao gio doc do dang).
  chay  chua co .rc, PID con trong /proc, KHONG phai zombie (Z), VA dong lenh cua PID do chua
        "fz_log/<o>.ipy" (PID da bi cap lai cho tien trinh khac thi khong khop -> khong nham).
  dung  khong co .rc va tien trinh khong con: bi o 09 / bi may giet giua chung.
"""
import base64
import json
import os
import select
import signal
import subprocess
import sys
import threading
import time

D = "/content/fz_log"
ENV = f"{D}/env.json"


def moi_truong():
    """Moi truong cua kernel Colab (env.json) + PYTHONUNBUFFERED; chua co thi moi truong hien tai."""
    try:
        with open(ENV) as f:
            e = json.load(f)
    except (FileNotFoundError, ValueError):
        e = dict(os.environ)
    e["PYTHONUNBUFFERED"] = "1"
    return e


def trang_thai(o, pid):
    """("xong", ma_thoat) | ("chay", None) | ("dung", None)."""
    try:
        return "xong", int(open(f"{D}/{o}.rc").read())
    except (FileNotFoundError, ValueError):
        pass
    try:
        st = open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()[0]
        cmd = open(f"/proc/{pid}/cmdline", "rb").read()
        if st != "Z" and f"fz_log/{o}.ipy".encode() in cmd:
            return "chay", None
    except (FileNotFoundError, IndexError, ProcessLookupError):
        pass
    return "dung", None


def o_gan_nhat():
    """(o, pid) cua o chay nen gan nhat, hoac (None, None)."""
    try:
        o, pid = open(f"{D}/dang_chay").read().split()
        return o, pid
    except (FileNotFoundError, ValueError):
        return None, None


def khoi_dong(o, ma_b64, ep=False):
    """Chay o (ma IPython, base64) nen trong nhom tien trinh rieng, log vao <o>.log."""
    os.makedirs(D, exist_ok=True)
    cu, pid_cu = o_gan_nhat()
    if cu and not ep and trang_thai(cu, pid_cu)[0] == "chay":
        print(f"FZ_BAN={cu}")
        return
    p, log, rc = f"{D}/{o}.ipy", f"{D}/{o}.log", f"{D}/{o}.rc"
    if os.path.exists(rc):
        os.remove(rc)
    open(p, "w").write(base64.b64decode(ma_b64).decode())
    lenh = (f"cd /content && stdbuf -oL -eL python3 -m IPython --no-banner --colors=NoColor {p}; "
            f"rc=$?; echo \"[fz] o {o} xong $(date +%H:%M:%S), ma thoat $rc\"; "
            f"echo $rc > {rc}.tmp && mv {rc}.tmp {rc}")
    with open(log, "w") as f:
        f.write(f"[fz] o {o} bat dau {time.strftime('%H:%M:%S')}\n")
        f.flush()
        pr = subprocess.Popen(["bash", "-c", lenh], stdout=f, stderr=subprocess.STDOUT,
                              stdin=subprocess.DEVNULL, start_new_session=True,
                              env=moi_truong())
    # Khoi dong tu kernel (duong cu): kernel la cha cua o va song suot phien -> thu don (wait) o
    # ngay khi o thoat, de o khong thanh zombie. Qua ssh: tien trinh nay thoat ngay, o thanh con
    # cua init. trang_thai() khong dua vao viec nay -- day chi la don dep dung cach.
    threading.Thread(target=pr.wait, daemon=True).start()
    open(f"{D}/dang_chay", "w").write(f"{o} {pr.pid}\n")
    print(f"FZ_PID={pr.pid}")


def _n_dong_cuoi(f, n):
    """Dua con tro tep f toi dau n dong cuoi (doc toi da 256 KB cuoi tep)."""
    f.seek(0, 2)
    co = f.tell()
    f.seek(max(0, co - 256 * 1024))
    d = f.read()
    vt = len(d)
    for _ in range(n + 1):             # +1: bo qua dau xuong dong cuoi tep
        vt = d.rfind(b"\n", 0, vt)
        if vt < 0:
            break
    f.seek(co - len(d) + (vt + 1 if vt >= 0 else 0))


def theo_doi(o, pid, n=None):
    """In log o tu dau (n: chi n dong cuoi) va theo tiep den khi o het 'chay'. 0 = o da ket
    thuc, 1 = nguoi xem ngat ket noi (ssh bi Ctrl+C: dau ra dong -> POLLHUP/POLLERR, BrokenPipe)."""
    out = sys.stdout.buffer
    nghe = select.poll()
    nghe.register(out.fileno(), 0)  # 0: chi nhan HUP/ERR -- dau doc (ssh) da dong
    ket_thuc = False
    with open(f"{D}/{o}.log", "rb") as f:
        if n:
            _n_dong_cuoi(f, n)
        while True:
            d = f.read()
            if d:
                try:
                    out.write(d)
                    out.flush()
                except BrokenPipeError:
                    return 1
                continue
            if ket_thuc:           # da doc het sau khi o ket thuc
                break
            if any(ev & (select.POLLHUP | select.POLLERR) for _, ev in nghe.poll(0)):
                return 1
            ket_thuc = trang_thai(o, pid)[0] != "chay"
            if not ket_thuc:
                time.sleep(0.2)
    if trang_thai(o, pid)[0] == "dung":
        print(f"[fz] o {o} da bi dung giua chung (khong co ma thoat)", flush=True)
    return 0


def dung_o():
    """Dung o chay nen gan nhat (ca nhom tien trinh: IPython, engine, train.py)."""
    o, pid = o_gan_nhat()
    if o is None:
        print("(chưa có ô nào chạy nền)")
        return
    tt, rc = trang_thai(o, pid)
    if tt != "chay":
        print(f"[o {o} khong con chay: {tt}" + (f", ma thoat {rc}]" if tt == "xong" else "]"))
        return
    try:
        os.killpg(int(pid), signal.SIGTERM)
        for _ in range(20):
            time.sleep(0.25)
            if trang_thai(o, pid)[0] != "chay":
                break
        else:
            os.killpg(int(pid), signal.SIGKILL)
    except ProcessLookupError:  # vua ket thuc dung luc nay
        pass
    print(f"[da dung o {o}]")


def chay_nhanh(o, ma_b64):
    """O nhanh qua ssh: chay IPython ngay (thay tien trinh nay), dau ra di thang ve ssh."""
    p = f"{D}/{o}.nhanh.ipy"
    with open(p, "w") as f:
        f.write(base64.b64decode(ma_b64).decode())
    os.chdir("/content")
    sys.stdout.flush()
    os.execvpe("python3", ["python3", "-m", "IPython", "--no-banner", "--colors=NoColor", p],
               moi_truong())


def _lenh(a):
    if len(a) in (3, 4) and a[0] == "theo_doi":
        return theo_doi(a[1], a[2], int(a[3]) if len(a) == 4 else None)
    if len(a) == 3 and a[0] == "trang_thai":
        print(trang_thai(a[1], a[2])[0])
        return 0
    if (len(a) in (2, 3) and a[0] == "khoi_dong") or (len(a) == 2 and a[0] == "chay_nhanh"):
        if not os.path.exists(ENV):
            return 97          # menu chup env.json (luu_env) roi goi lai
        ma = sys.stdin.read().strip()
        if a[0] == "chay_nhanh":
            return chay_nhanh(a[1], ma)
        return khoi_dong(a[1], ma, ep=len(a) == 3 and a[2] == "ep")
    print(__doc__)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(_lenh(sys.argv[1:]))
    except KeyboardInterrupt:  # Ctrl+C toi duoc day (vd ssh -t): chi dung xem, o van chay
        sys.exit(130)
