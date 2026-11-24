"""Engine GIA cho bo thu vong lap lien tuc: choi "van" bang cach chep van mau that (mau_van/*.xz) vao --out voi toc do FAKE_RATE van/giay,
giong engine that o cac diem vong lap dung: ghi .xz.tmp roi doi ten (nguyen tu), in dong "[selfplay] d/N", dung nhan van moi khi co tep
--stop-file hoac het --max-seconds (chia FAKE_SCALE de thu nhanh), roi choi not van do (~2 giay) va thoat 0. Moi van xong ghi mot dong vao
so cai /tmp/fc/ledger: "<tai khoan> <thu muc van> <ten van> <gio>" -- de bo thu doi chieu: moi van sinh ra phai ve dien thoai DUNG MOT LAN."""
import argparse
import glob
import os
import shutil
import sys
import time

ap = argparse.ArgumentParser()
ap.add_argument("--selfplay", action="store_true")
ap.add_argument("--games", type=int, default=1000)
ap.add_argument("--max-seconds", type=float, default=0)
ap.add_argument("--start-fen", default="")
ap.add_argument("--out", required=True)
ap.add_argument("--stop-file", default="")
ap.add_argument("--weights", default="")
ap.add_argument("--parallel", type=int, default=16)
a, _ = ap.parse_known_args()

if not (os.path.exists(a.weights) and os.path.getsize(a.weights) > 0):
    print(f"[!] khong co mang {a.weights}", flush=True)
    sys.exit(3)
if a.start_fen and not os.path.exists(a.start_fen):
    print(f"[!] khong co tep the khoi dau {a.start_fen}", flush=True)
    sys.exit(4)
scale = float(os.environ.get("FAKE_SCALE", "1"))
rate = float(os.environ.get("FAKE_RATE", "4"))
acc = os.path.basename(os.environ.get("HOME", "?").rstrip("/"))
mau = sorted(glob.glob(os.path.join(os.environ["FAKE_SRC"], "python", "mau_van", "*.xz")))
os.makedirs(a.out, exist_ok=True)
print(f"[selfplay] Generating {a.games} games into '{a.out}' (fake: {rate}/s, scale {scale})", flush=True)
t0 = time.time()
done = 0
i = 0
stop = False


def ghi_van(i):
    p = os.path.join(a.out, f"game_{i}.xz")
    shutil.copy(mau[i % len(mau)], p + ".tmp")
    os.rename(p + ".tmp", p)
    with open("/tmp/fc/ledger", "a") as f:
        f.write(f"{acc} {os.path.basename(a.out)} game_{i}.xz {time.time():.2f}\n")


while True:
    if not stop and a.stop_file and os.path.exists(a.stop_file):
        print(f"[selfplay] Co tep dung {a.stop_file} -> ngung nhan van moi (da xong {done} van, cac van dang chay se hoan tat).", flush=True)
        stop = True
    if not stop and a.max_seconds and time.time() - t0 >= a.max_seconds / scale:
        print(f"[selfplay] Finished {done}/{a.games} games in {time.time() - t0:.0f}s (dung som do dat nguong --max-seconds)", flush=True)
        stop = True
    if stop:
        break
    time.sleep(1.0 / rate)
    ghi_van(i)
    i += 1
    done += 1
    print(f"[selfplay] {done}/{a.games}  (game {i - 1} -> result=1, pieces=30)  | 1000 nps (tong)", flush=True)
# Duoi van: choi not mot so van dang do (nhu engine that).
for _ in range(min(3, a.parallel)):
    time.sleep(0.6)
    ghi_van(i)
    i += 1
    done += 1
    print(f"[selfplay] {done}/{a.games}  (game {i - 1} -> result=1, pieces=30)  | 1000 nps (tong)", flush=True)
print(f"[selfplay] Finished {done}/{a.games} games", flush=True)
