"""Thao tác với một máy Colab của một tài khoản: xin, trả, tải lên, tải về, chạy lệnh qua SSH, giữ máy.

Kế thừa từ hệ thống của engine cờ biến thể (custom_engine/scripts/colab_cells, HUONG_DAN_TERMUX.md mục 3.1, 4.1, 10):
- Mỗi tài khoản có thư mục nhà riêng cho Colab CLI (biến HOME), nên nhiều tài khoản chạy song song được.
- Colab thu hồi máy sau khoảng 10 đến 15 phút nếu không có kết nối SSH; một phiên SSH ngắn (`true`) mỗi
  60 giây giữ được máy (đo 2026-09-26). Colab chỉ cho một phiên SSH mỗi máy, nên mọi lệnh SSH đi qua một khoá.
- `colab exec` mất kết nối với lệnh chạy lâu, nên việc dài chạy nền và được hỏi tiến độ qua SSH.
Mọi thao tác ghi vào log (hàm log do bộ điều phối truyền vào).
"""
import os
import shlex
import shutil
import subprocess
import threading
import time

THU_MUC = os.path.dirname(os.path.abspath(__file__))
_BO_QUA = ("new version", "colab update", "uv tool install", "silence this check")


def _loc(s):
    return "\n".join(d for d in s.splitlines() if d.strip() and not any(b in d for b in _BO_QUA))


def python_cua_cli():
    """Trình Python của Colab CLI (đọc dòng shebang của lệnh `colab`)."""
    colab = shutil.which("colab")
    if not colab:
        raise RuntimeError("khong tim thay lenh colab")
    dong = open(os.path.realpath(colab), "rb").readline().decode().strip()
    return dong[2:].split()[0] if dong.startswith("#!") else "python3"


class May:
    def __init__(self, ten, home, log):
        self.ten, self.home, self.log = ten, os.path.expanduser(home), log
        self.env = dict(os.environ, HOME=self.home)
        self.py_cli = python_cua_cli()
        self.khoa_ssh = threading.Lock()
        self.lan_ssh_cuoi = 0.0
        self._dung_giu = threading.Event()
        self._giu = None

    # --- lệnh colab ------------------------------------------------------------------------------
    def colab(self, *args, timeout=600):
        try:
            r = subprocess.run(["colab", *args], env=self.env, capture_output=True, text=True, timeout=timeout)
            return r.returncode, _loc(r.stdout + r.stderr)
        except subprocess.TimeoutExpired:
            return -1, f"het gio {timeout} giay"

    def con_song(self):
        rc, ra = self.colab("sessions", timeout=120)
        return rc == 0 and f"[{self.ten}]" in ra

    def xin(self, gpu="T4"):
        """Xin máy mới tên self.ten. Trả về True nếu được."""
        if self.con_song():
            self.log(f"may '{self.ten}' van con, dung lai")
            self.bat_giu_may()
            return True
        rc, ra = self.colab("new", "-s", self.ten, "--gpu", gpu, timeout=600)
        self.log(f"xin may {gpu} '{self.ten}': ma {rc}; {ra[-300:]}")
        if rc == 0 and "READY" in ra:
            self.bat_giu_may()
            return True
        return False

    def tra(self):
        self._dung_giu.set()
        rc, ra = self.colab("stop", "-s", self.ten, timeout=300)
        self.log(f"tra may '{self.ten}': ma {rc}; {ra[-200:]}")

    def tai_len(self, cuc_bo, tu_xa, so_lan=3):
        for k in range(so_lan):
            t = time.time()
            rc, ra = self.colab("upload", "-s", self.ten, cuc_bo, tu_xa, timeout=1800)
            if rc == 0:
                self.log(f"tai len {os.path.basename(cuc_bo)} ({os.path.getsize(cuc_bo)} byte) -> {tu_xa}: "
                         f"{time.time() - t:.0f} giay")
                return True
            self.log(f"tai len {cuc_bo} loi (lan {k + 1}): {ra[-200:]}")
            time.sleep(10)
        return False

    def tai_ve(self, tu_xa, cuc_bo, so_lan=3):
        os.makedirs(os.path.dirname(cuc_bo) or ".", exist_ok=True)
        tam = cuc_bo + ".dang_tai"
        for k in range(so_lan):
            t = time.time()
            rc, ra = self.colab("download", "-s", self.ten, tu_xa, tam, timeout=1800)
            if rc == 0 and os.path.exists(tam):
                os.replace(tam, cuc_bo)
                self.log(f"tai ve {tu_xa} ({os.path.getsize(cuc_bo)} byte): {time.time() - t:.0f} giay")
                return True
            self.log(f"tai ve {tu_xa} loi (lan {k + 1}): {ra[-200:]}")
            time.sleep(10)
        return False

    # --- SSH ---------------------------------------------------------------------------------------
    def ssh(self, lenh, timeout=300):
        """Chạy lệnh shell trên máy qua SSH. Trả về (mã thoát, đầu ra)."""
        proxy = f"{self.py_cli} {os.path.join(THU_MUC, 'proxy_ssh.py')} {self.ten}"
        args = ["ssh", "-o", f"ProxyCommand={proxy}", "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR", "-o", "ConnectTimeout=30",
                "-o", "BatchMode=yes", f"root@colab-{self.ten}", lenh]
        with self.khoa_ssh:
            try:
                r = subprocess.run(args, env=self.env, stdin=subprocess.DEVNULL, capture_output=True,
                                   text=True, timeout=timeout)
                rc, ra = r.returncode, r.stdout + r.stderr
            except subprocess.TimeoutExpired:
                rc, ra = -1, f"het gio {timeout} giay"
            self.lan_ssh_cuoi = time.time()
        return rc, ra

    def chay_nen(self, lenh):
        """Chạy lệnh nền trên máy (không gắn với phiên SSH).

        `setsid -f` tách tiến trình ra phiên mới rồi trả về ngay. Không dùng `cd ... && setsid ... &`: khi đó cả chuỗi
        chạy trong một shell con vẫn giữ kết nối SSH cho tới khi việc nền xong, nên lệnh SSH không trả về.
        """
        return self.ssh(f"cd /content/cv; setsid -f nohup bash -c {shlex.quote(lenh)} > /dev/null 2>&1 < /dev/null")

    def bat_giu_may(self):
        if self._giu and self._giu.is_alive():
            return
        self._dung_giu.clear()

        def vong():
            loi = 0
            while not self._dung_giu.wait(20):
                if time.time() - self.lan_ssh_cuoi < 55:
                    continue
                rc, ra = self.ssh("true", timeout=90)
                if rc == 0:
                    loi = 0
                else:
                    loi += 1
                    if loi in (1, 3) or loi % 10 == 0:
                        self.log(f"giu may: ssh loi (ma {rc}) lan {loi} lien tiep: {ra.strip()[-200:]}")
        self._giu = threading.Thread(target=vong, daemon=True)
        self._giu.start()
