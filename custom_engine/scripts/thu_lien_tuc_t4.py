# -*- coding: utf-8 -*-
"""thu_lien_tuc_t4.py -- THU TREN T4 THAT cac thanh phan phia may cua vong lap lien tuc (chay bang ~/chay_t4_thu.py trong WSL):

  python3 ~/chay_t4_thu.py custom_engine/scripts/thu_lien_tuc_t4.py --can-phut 40 --timeout 3000 --tep /tmp/lt_t4.tgz:/content/lt_t4.tgz

tgz = custom_engine/scripts/colab_cells/*.py + custom_engine/python/goi_van.py + python/mau_van (khong can) + g55.zip (168 van that, 20.906 the).
Ma engine / lay_mang lay that tu nhanh BRANCH (o 02 that); goi_van.py, fz_may.py, o 04l lay tu tgz (chua nam tren GitHub).

  A. o 02 that: may moi co mang gen<GEN> (.fzw) va chay thu fzcuda.
  B. o 04l that qua fz_may.py: MOT engine (mang GEN) -> nps mot minh.
  C. HAI engine cung luc (04_a dang chay, khoi dong 04_b): nps tung engine, RAM (MemAvailable, RSS), bo nho GPU, thoi gian khoi dong cua B.
  D. dung mem 04_a (tep dung_a): thoi gian choi not van do (duoi), B van chay: nps cua B sau do.
  E. goi_van.py pack KHI engine B dang chay: zip hop le, so van = so tep .xz da xong, commit roi pack lai khong gui trung.
  F. HUAN LUYEN CHONG engine: cua so ~625.000 the (30 ban sao g55.zip), o 07 that voi engine B dang chay: RAM dinh, thoi gian, nps cua engine luc do.
     (so voi cung viec KHONG co engine: de quyet LT_CHO_DUOI = cho engine choi not roi moi huan luyen, hay huan luyen chong luon)
Ket qua in bang tom tat cuoi cung.
"""
import base64
import glob
import json
import os
import re
import shutil
import subprocess
import tarfile
import threading
import time
import zipfile

BRANCH = "luat-moi"
GEN = 17
C = "/content"
E = f"{C}/chess_variant_engine/custom_engine"
LOGD = f"{C}/fz_log"
T0 = time.time()
KQ = []
MAU = []


def log(*a):
    print(f"[{time.time() - T0:6.0f}s]", *a, flush=True)


def shq(s):
    return "'" + s.replace("'", "'\"'\"'") + "'"


def sh(cmd, timeout=900):
    p = subprocess.run(["bash", "-c", f"timeout -k 5 {timeout} bash -c {shq(cmd)}"], capture_output=True, text=True, errors="replace")
    return p.returncode, p.stdout + p.stderr


def ket(ten, ok, note=""):
    KQ.append((ten, ok, note))
    log(f"== {ten}: {'PASS' if ok else 'FAIL'} {note}")


os.makedirs(f"{C}/cells", exist_ok=True)
with tarfile.open(f"{C}/lt_t4.tgz") as t:
    t.extractall(f"{C}/cells")
CELLS = {}
for p in glob.glob(f"{C}/cells/**/*.py", recursive=True):
    b = os.path.basename(p)
    k = b[:2]
    if b.startswith(("02b", "02c", "04l")):
        k = b[:3]
    CELLS[k] = p


def ghep(ten_o, edits=()):
    src = open(CELLS["00"], encoding="utf-8").read()
    src = re.sub(r"^GEN_CURRENT = .*$", f"GEN_CURRENT = {GEN}", src, flags=re.M)
    body = open(CELLS[ten_o], encoding="utf-8").read()
    if ten_o == "02":
        body = body.replace("-b main", f"-b {BRANCH}").replace("origin main", f"origin {BRANCH}")
    for pat, rep in edits:
        body = re.sub(pat, rep, body, flags=re.M)
    return src + "\n" + body


def cell_sync(ten_o, edits=(), timeout=1500):
    f = f"{C}/t_{ten_o}.ipy"
    open(f, "w", encoding="utf-8").write(ghep(ten_o, edits))
    t = time.time()
    rc, out = sh(f"cd {C} && python3 -m IPython --no-banner --colors=NoColor {f} 2>&1", timeout=timeout)
    open(f"{C}/t_{ten_o}.log", "w").write(out)
    log(f"   o {ten_o}: {time.time() - t:.0f} s, rc {rc}")
    return rc, out


# ---- phia may: dung dung fz_may.py cua vong lap ----
def chuan_bi_fz_may():
    os.makedirs(LOGD, exist_ok=True)
    shutil.copy(glob.glob(f"{C}/cells/**/fz_may.py", recursive=True)[0], f"{LOGD}/fz_may.py")
    json.dump(dict(os.environ), open(f"{LOGD}/env.json", "w"))


def khoi_dong(o, ma):
    r = subprocess.run(["python3", f"{LOGD}/fz_may.py", "khoi_dong", o], input=base64.b64encode(ma.encode()).decode(),
                       capture_output=True, text=True)
    m = re.search(r"FZ_PID=(\d+)", r.stdout)
    return int(m.group(1)) if m else None, r.stdout.strip()


def trang_thai(o):
    try:
        pid = open(f"{LOGD}/{o}.pid").read().strip()
    except OSError:
        return "?"
    return subprocess.run(["python3", f"{LOGD}/fz_may.py", "trang_thai", o, pid], capture_output=True, text=True).stdout.strip()


def sinh_dang_chay():
    out = subprocess.run(["python3", f"{LOGD}/fz_may.py", "sinh_dang_chay"], capture_output=True, text=True).stdout
    return re.findall(r"^FZ_SINH (\S+)", out, re.M)


def nps_log(o):
    """nps cua dong [nhip] cuoi cung trong log cua o, hoac None."""
    try:
        t = open(f"{LOGD}/{o}.log", errors="replace").read()
    except OSError:
        return None
    m = re.findall(r"\[nhip\] t=(\d+)s\s+(\d+) van dang chay\s+(\d+) nps", t)
    return (int(m[-1][2]), int(m[-1][1])) if m else None


def so_van(run):
    return len(glob.glob(f"{C}/games_gen{GEN}_{run}/*.xz"))


# ---- lay mau RAM / GPU lien tuc ----
MAU_RUN = True


def lay_mau():
    while MAU_RUN:
        try:
            mem = {k: int(v.split()[0]) for k, v in (l.split(":") for l in open("/proc/meminfo"))}
            used = (mem["MemTotal"] - mem["MemAvailable"]) / 1024
            rss = {}
            for l in subprocess.run("ps -eo rss,args", shell=True, capture_output=True, text=True).stdout.splitlines()[1:]:
                p = l.split(None, 1)
                if len(p) == 2 and "custom_engine" in p[1] and "--selfplay" in p[1]:
                    m = re.search(r"--out (\S+)", p[1])
                    rss[os.path.basename(m.group(1)) if m else "?"] = int(p[0]) / 1024
                elif len(p) == 2 and "train.py" in p[1]:
                    rss["train"] = max(rss.get("train", 0), int(p[0]) / 1024)
            g = subprocess.run("nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits",
                               shell=True, capture_output=True, text=True).stdout.strip().split(",")
            MAU.append((time.time(), used, rss, int(g[0]), int(g[1])))
        except Exception:
            pass
        time.sleep(2)


def tom_tat(t0, t1):
    m = [x for x in MAU if t0 <= x[0] <= t1]
    if not m:
        return "khong co mau"
    rss_max = {}
    for x in m:
        for k, v in x[2].items():
            rss_max[k] = max(rss_max.get(k, 0), v)
    return (f"RAM dung toi da {max(x[1] for x in m):.0f} MB (may {int(open('/proc/meminfo').read().split()[1]) / 1024:.0f} MB), "
            f"GPU nho {max(x[3] for x in m)} MiB, GPU ban {sum(x[4] for x in m) / len(m):.0f}% (tb), RSS toi da: "
            + ", ".join(f"{k} {v:.0f} MB" for k, v in rss_max.items()))


log("may:", sh("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader; free -m | sed -n 2p; nproc")[1].strip().replace("\n", " | "))

# ------------------------------------------------------------------------------------------------------------------- A. o 02
print("\n##### A. o 02 that (nhanh %s)" % BRANCH, flush=True)
rc, out = cell_sync("02")
print("\n".join(out.strip().splitlines()[-8:]), flush=True)
ket("A1 02 xong, FZ_NET=fzw", rc == 0 and "FZ_NET=fzw" in out)
shutil.copy(glob.glob(f"{C}/cells/**/goi_van.py", recursive=True)[0], f"{E}/python/goi_van.py")
chuan_bi_fz_may()
threading.Thread(target=lay_mau, daemon=True).start()
O4 = ghep("04l")


def o04(secs, run):
    t = re.sub(r"^SECS = .*$", f"SECS = {secs}", O4, flags=re.M)
    t = re.sub(r"^RUN = .*$", f'RUN = "{run}"', t, flags=re.M)
    return re.sub(r"^NET_N = .*$", f"NET_N = {GEN}", t, flags=re.M)


# ------------------------------------------------------------------------------------------------------------------- B. mot engine
print("\n##### B. MOT engine (04l qua fz_may.py)", flush=True)
tb0 = time.time()
pid_a, out = khoi_dong("04_a", o04(1800, "a"))
ket("B1 04_a khoi dong", pid_a is not None, out)
time.sleep(75)
nA1 = nps_log("04_a")
log("   04_a nps:", nA1, " so van xong:", so_van("a"))
ket("B2 04_a dang chay va co nps", trang_thai("04_a") == "chay" and nA1 is not None and nA1[0] > 3000, str(nA1))
tb1 = time.time()
print("   ", tom_tat(tb0, tb1), flush=True)

# ------------------------------------------------------------------------------------------------------------------- C. hai engine
print("\n##### C. HAI engine cung luc", flush=True)
tc0 = time.time()
pid_b, out = khoi_dong("04_b", o04(1800, "b"))
ket("C1 04_b khoi dong trong khi 04_a dang chay (khong FZ_BAN)", pid_b is not None and "FZ_BAN" not in out, out)
t_ra_van = None
for _ in range(90):
    time.sleep(2)
    if so_van("b") >= 1 or nps_log("04_b"):
        t_ra_van = time.time() - tc0
        break
log("   04_b co nhip dau tien sau", f"{t_ra_van:.0f} s" if t_ra_van else "(chua)")
time.sleep(60)
nA2, nB2 = nps_log("04_a"), nps_log("04_b")
log("   luc chay chong: nps 04_a", nA2, " 04_b", nB2, " tong", (nA2[0] + nB2[0]) if nA2 and nB2 else None)
ket("C2 ca hai engine cung chay", trang_thai("04_a") == "chay" and trang_thai("04_b") == "chay" and sorted(sinh_dang_chay()) == ["04_a", "04_b"], str(sinh_dang_chay()))
tc1 = time.time()
print("   ", tom_tat(tc0, tc1), flush=True)

# ------------------------------------------------------------------------------------------------------------------- D. dung mem 04_a
print("\n##### D. dung mem engine cu (04_a), 04_b van chay", flush=True)
td0 = time.time()
open(f"{LOGD}/dung_a", "w").close()
while trang_thai("04_a") == "chay" and time.time() - td0 < 600:
    time.sleep(2)
duoi = time.time() - td0
log(f"   duoi cua 04_a (tu luc dung mem toi luc thoat): {duoi:.0f} s; 04_b trang thai {trang_thai('04_b')}")
ket("D1 04_a thoat sau dung mem (duoi < 400 s)", trang_thai("04_a") == "xong" and duoi < 400, f"{duoi:.0f} s")
time.sleep(30)
nB3 = nps_log("04_b")
log("   04_b sau khi 04_a thoat: nps", nB3)
ket("D2 04_b van chay sau khi 04_a thoat", trang_thai("04_b") == "chay")
td1 = time.time()
print("   ", tom_tat(td0, td1), flush=True)

# ------------------------------------------------------------------------------------------------------------------- E. pack khi engine chay
print("\n##### E. goi_van.py pack KHI engine 04_b dang chay", flush=True)
r1 = subprocess.run(["python3", f"{E}/python/goi_van.py", "pack", C, "--tk", "t4", "--ra", f"{C}/goi_ra"], capture_output=True, text=True)
goi = re.findall(r"^FZ_GOI (\S+) (\d+) (\d+) (\d+)", r1.stdout, re.M)
log("   pack:", r1.stdout.strip().replace("\n", " | ")[:300])
ket("E1 pack ra goi cho thu muc 04_a va 04_b", len(goi) >= 2 and "FZ_GOI_XONG" in r1.stdout, f"{len(goi)} goi")
tong = 0
hop_le = True
for z, mang, van, the in goi:
    with zipfile.ZipFile(z) as zf:
        hop_le &= (zf.testzip() is None and len(zf.namelist()) == int(van))
        tong += len(zf.namelist())
ket("E2 zip hop le va so van trong zip = so van bao", hop_le, f"{tong} van")
for z, *_ in goi:
    subprocess.run(["python3", f"{E}/python/goi_van.py", "commit", z + ".ds"], capture_output=True)
r2 = subprocess.run(["python3", f"{E}/python/goi_van.py", "pack", C, "--tk", "t4", "--ra", f"{C}/goi_ra"], capture_output=True, text=True)
moi = sum(int(x[2]) for x in re.findall(r"^FZ_GOI (\S+) (\d+) (\d+) (\d+)", r2.stdout, re.M))
ket("E3 sau commit, pack lai chi gui van MOI (khong trung)", moi < tong, f"{moi} van moi so voi {tong} da gui")

# ------------------------------------------------------------------------------------------------------------------- F. huan luyen chong
print("\n##### F. huan luyen CHONG engine (cua so ~625.000 the)", flush=True)
rc, out = cell_sync("02c")
ket("F0 02c (gen%d.pt + thu vien huan luyen)" % GEN, rc == 0 and os.path.exists(f"{C}/gen{GEN}.pt"))
os.makedirs(f"{C}/goi", exist_ok=True)
g55 = glob.glob(f"{C}/cells/**/g55.zip", recursive=True)[0]
ten = []
for i in range(30):
    d = f"{C}/goi/goi_{i:05d}_n55_168_20906.zip"
    shutil.copy(g55, d)
    ten.append(d)
DATA = ",".join(ten)
the_tong = 30 * 20906
log(f"   cua so gia: 30 ban sao g55.zip = {30 * 168} van, {the_tong} the")


def chay_07(ten_o):
    t_bd = time.time()
    # rm mang cu de kiem tra ra mang moi
    for ext in ("pt", "fzw"):
        p = f"{C}/gen{GEN + 1}.{ext}"
        if os.path.exists(p):
            os.remove(p)
    ma = ghep("07", edits=[(r"^DATA = .*$", f'DATA = "{DATA}"')])
    pid, o = khoi_dong("07", ma)
    log("   07 khoi dong:", o)
    while trang_thai("07") == "chay" and time.time() - t_bd < 1500:
        time.sleep(5)
    tail = open(f"{LOGD}/07.log", errors="replace").read()
    return time.time() - t_bd, tail


nBf0 = nps_log("04_b")
tf0 = time.time()
nps_truoc = nps_log("04_b")
dt_chong, tail = chay_07("07")
tf1 = time.time()
ra = os.path.exists(f"{C}/gen{GEN + 1}.pt")
log(f"   huan luyen CHONG engine: {dt_chong:.0f} s, ra mang: {ra}")
print("\n".join(tail.strip().splitlines()[-6:]), flush=True)
print("   ", tom_tat(tf0, tf1), flush=True)
nps_trong = nps_log("04_b")
log("   engine 04_b: nps truoc huan luyen", nps_truoc, "-> sau", nps_trong, "; trang thai", trang_thai("04_b"))
ket("F1 huan luyen chong engine ra gen%d.pt (khong het RAM)" % (GEN + 1), ra and "Killed" not in tail and "out of memory" not in tail.lower(), f"{dt_chong:.0f} s")
ket("F2 engine 04_b van song sau huan luyen", trang_thai("04_b") == "chay")
dem_rss = max((x[1] for x in MAU if tf0 <= x[0] <= tf1), default=0)
log(f"   RAM dinh luc huan luyen chong engine: {dem_rss:.0f} MB")

# khong co engine: dung 04_b, doi ngung
open(f"{LOGD}/dung_b", "w").close()
tw = time.time()
while trang_thai("04_b") == "chay" and time.time() - tw < 600:
    time.sleep(3)
log("   04_b thoat sau", f"{time.time() - tw:.0f} s")
tg0 = time.time()
dt_mot, tail = chay_07("07")
tg1 = time.time()
log(f"   huan luyen MOT MINH (khong engine): {dt_mot:.0f} s, ra mang: {os.path.exists(f'{C}/gen{GEN + 1}.pt')}")
print("   ", tom_tat(tg0, tg1), flush=True)
ket("F3 huan luyen mot minh ra mang", os.path.exists(f"{C}/gen{GEN + 1}.pt"), f"{dt_mot:.0f} s")
log(f"   => chong engine {dt_chong:.0f} s, mot minh {dt_mot:.0f} s (chenh {dt_chong - dt_mot:+.0f} s); RAM dinh chong engine {dem_rss:.0f} MB")

MAU_RUN = False
print("\n" + "=" * 70)
for ten_, ok, note in KQ:
    print(f"  {'PASS' if ok else 'FAIL'}  {ten_} {note}")
print("=" * 70)
print(f"TONG: {sum(1 for _, ok, _ in KQ if ok)} dat, {sum(1 for _, ok, _ in KQ if not ok)} hong, {time.time() - T0:.0f} s")
