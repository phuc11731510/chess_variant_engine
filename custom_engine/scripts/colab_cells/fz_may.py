"""fz_may.py -- phan chay TREN MAY COLAB cua menu fz.

menu.sh gui tep nay len /content/fz_log/fz_may.py moi lan khoi dong mot o, roi:
  - trong kernel colab exec:  khoi_dong(o, ma_b64, ep)   -> in "FZ_PID=<pid>" hoac "FZ_BAN=<o>"
  - qua ssh:  python3 /content/fz_log/fz_may.py theo_doi <o> <pid>   -> log truc tiep
O 05, 09 cung doc tep nay (trang_thai, dung_o).

Trang thai mot o chay nen (trang_thai) -- khong doan theo thoi gian hay noi dung log:
  xong  co tep <o>.rc: vo bash boc o ghi ma thoat vao do NGAY KHI IPython chay o ket thuc
        (ghi sau dong "[fz] o .. xong" cua log, ghi qua tep tam + mv nen khong bao gio doc do dang).
  chay  chua co .rc, PID con trong /proc, KHONG phai zombie (Z), VA dong lenh cua PID do chua
        "fz_log/<o>.ipy" (PID da bi cap lai cho tien trinh khac thi khong khop -> khong nham).
  dung  khong co .rc va tien trinh khong con: bi o 09 / bi may giet giua chung.
"""
import base64
import os
import select
import signal
import subprocess
import sys
import threading
import time

D = "/content/fz_log"


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
                              env=dict(os.environ, PYTHONUNBUFFERED="1"))
    # Kernel la cha cua o va song suot phien: thu don (wait) o ngay khi o thoat, de o khong
    # thanh zombie. trang_thai() khong dua vao viec nay -- day chi la don dep dung cach.
    threading.Thread(target=pr.wait, daemon=True).start()
    open(f"{D}/dang_chay", "w").write(f"{o} {pr.pid}\n")
    print(f"FZ_PID={pr.pid}")


def theo_doi(o, pid):
    """In log o tu dau va theo tiep den khi o het 'chay'. 0 = o da ket thuc, 1 = nguoi xem
    ngat ket noi (ssh bi Ctrl+C: dau ra dong -> POLLHUP/POLLERR hoac BrokenPipe)."""
    out = sys.stdout.buffer
    nghe = select.poll()
    nghe.register(out.fileno(), 0)  # 0: chi nhan HUP/ERR -- dau doc (ssh) da dong
    ket_thuc = False
    with open(f"{D}/{o}.log", "rb") as f:
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


if __name__ == "__main__" and len(sys.argv) == 4 and sys.argv[1] == "theo_doi":
    try:
        sys.exit(theo_doi(sys.argv[2], sys.argv[3]))
    except KeyboardInterrupt:  # Ctrl+C toi duoc day (vd ssh -t): chi dung xem, o van chay
        sys.exit(130)
