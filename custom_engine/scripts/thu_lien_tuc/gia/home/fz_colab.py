"""fz_colab.py GIA (bo thu vong lap lien tuc): thay Colab CLI. HOME = thu muc tai khoan (~/.fz_tk/<ten>); moi tai khoan mot "may" = /content cua cua so."""
import json
import os
import subprocess
import sys

a = sys.argv[1:]
home = os.environ["HOME"]
reg_f = home + "/.config/colab-cli/fake_sessions.json"
acc = os.path.basename(home.rstrip("/"))


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
        sys.exit(1)
    print(f"[{name}] {r[name]['ep']} | Hardware: {r[name]['hw']} | Status: ok")
elif cmd == "sessions":
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
