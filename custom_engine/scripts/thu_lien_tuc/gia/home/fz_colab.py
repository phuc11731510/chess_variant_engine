"""fz_colab.py GIA (bo thu vong lap lien tuc): thay Colab CLI. HOME = thu muc tai khoan (~/.fz_tk/<ten>); moi tai khoan mot "may" = /content cua cua so.

Bat chuoc dung nhung diem THAT cua Colab CLI da lam hong vong lap (2026-11-24, do tren dien thoai):
  - `status` khi KHONG co phien: in "[colab] Session 'fz' not found." roi THOAT MA 0.
  - `new` bi treo (tep $FAKE_DIR/hang_<tai khoan> chua so lan treo con lai): lenh khong tra loi cho toi khi bi `timeout` giet; may chu
    van CAP MAY SAU do ($FAKE_GRANT_LATE giay sau khi bat dau, mac dinh 3) cho mot phien KHONG TEN ("?") ma khong ai giu.
"""
import json
import os
import subprocess
import sys
import time

a = sys.argv[1:]
home = os.environ["HOME"]
reg_f = home + "/.config/colab-cli/fake_sessions.json"
acc = os.path.basename(home.rstrip("/"))
FAKE_DIR = os.environ.get("FAKE_DIR", "/tmp/fc")


def load():
    try:
        return json.load(open(reg_f))
    except (OSError, ValueError):
        return {}


def save(r):
    os.makedirs(os.path.dirname(reg_f), exist_ok=True)
    json.dump(r, open(reg_f, "w"))


if a[:1] == ["--token"]:
    print("FZ_TOKEN=ok")
    sys.exit(0)
if not a:
    sys.exit(2)
cmd = a[0]
name = a[a.index("-s") + 1] if "-s" in a else "fz"
r = load()
if os.path.exists("/content/.mat") and name in r and cmd in ("status", "sessions", "new"):
    del r[name]                      # may da mat (Colab thu hoi): CLI khong con thay phien nay
    save(r)
if cmd == "new":
    hang_f = f"{FAKE_DIR}/hang_{acc}"
    try:
        con_lai = int(open(hang_f).read().strip())
    except (OSError, ValueError):
        con_lai = 0
    if con_lai > 0:
        open(hang_f, "w").write(str(con_lai - 1))
        print("[colab] Creating session 'fz'...", flush=True)
        if os.fork() == 0:                    # may chu cap may muon, sau khi lenh cua ta da bi giet
            os.setsid()
            _fd = os.open(os.devnull, os.O_RDWR)      # khong giu ong dau ra cua `$(...)` cua nguoi goi (neu giu, nguoi goi phai doi het thoi gian cho)
            os.dup2(_fd, 0)
            os.dup2(_fd, 1)
            os.dup2(_fd, 2)
            time.sleep(float(os.environ.get("FAKE_GRANT_LATE", "3")))
            rr = load()
            rr["?"] = {"ep": f"gpu-orphan-{acc}", "hw": "T4"}
            save(rr)
            os._exit(0)
        time.sleep(600)
        sys.exit(0)
    subprocess.run("rm -rf /content/* /content/.maychu /content/.mat", shell=True)   # may moi = /content trong
    gpu = a[a.index("--gpu") + 1] if "--gpu" in a else "CPU"
    r[name] = {"ep": f"gpu-fake-{acc}", "hw": gpu}
    save(r)
    os.makedirs("/content", exist_ok=True)
    open("/content/.maychu", "w").write(acc)
    if os.path.exists("/content/.mat"):
        os.remove("/content/.mat")
    print(f"[colab] Session '{name}' created ({gpu})")
elif cmd == "status":
    if name not in r:
        print(f"[colab] Session '{name}' not found.")      # that: van thoat ma 0
        sys.exit(0)
    print(f"[{name}] {r[name]['ep']} | Hardware: {r[name]['hw']} | Status: ok")
elif cmd == "sessions":
    if not r:
        print("[colab] No active sessions found on server.")
    for n, v in r.items():
        print(f"[{n}] {v['ep']} | Hardware: {v['hw']} | Status: ok")
elif cmd == "stop":
    if name in r:
        del r[name]
        save(r)
    subprocess.run("rm -rf /content/* /content/.maychu /content/.mat", shell=True)   # may tra di = mat /content
    print("[colab] Session terminated.")
elif cmd == "exec":
    code = sys.stdin.read()
    sys.exit(subprocess.run(["python3", "-c", code]).returncode)
else:
    sys.exit(0)
