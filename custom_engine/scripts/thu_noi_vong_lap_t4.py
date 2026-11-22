# -*- coding: utf-8 -*-
"""thu_noi_vong_lap_t4.py -- thu tren T4 that cac O LENH CUA VONG LAP o kieu mang fzw (bo chay CUDA rieng) va duong roi ve ONNX
(chay bang ~/chay_t4_thu.py --tep <cells.tgz>:/content/cells.tgz).

Chay DUNG cac o nhu vong lap (`00_cau_hinh.py` + o, IPython, GEN_CURRENT = GEN) tren mot may moi:
  A. 02 (kieu auto): mang ve + .fzw + chay thu fzcuda; phai ra FZ_NET=fzw, KHONG tai ONNX Runtime, khong pip onnx.
  B. 04: tu dau fzcuda (--provider fzcuda), ra van.
  C. 06 gom zip, 02c (khong pip), 07: train.py --out gen<N+1>.pt roi lay_mang fzw -> gen<N+1>.fzw (kiem an toan).
  D. 08 arena gen<GEN> vs gen<GEN-1> bang fzw: phai ra dong FZ_ARENA.
  E. 02 lan hai tren cung may (doi sau): giu ket luan, khong chay thu lai.
  F. Roi ve ONNX: bo net_kind, lam hong gen<GEN>.fzw -> 02 phai bao fzcuda khong chay duoc, roi ve onnx (ORT + .onnx), ra FZ_NET=onnx;
     sau do 04 chay duoc voi --provider cuda.
Ma lay tu nhanh BRANCH (02 duoc sua -b main -> -b BRANCH trong ban thu); binary lay that tu Release v3.0.0.
"""
import glob
import os
import re
import subprocess
import tarfile
import time

BRANCH = "luat-moi"
GEN = 17
C = "/content"
E = f"{C}/chess_variant_engine/custom_engine"
T0 = time.time()
KQ = []


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
with tarfile.open(f"{C}/cells.tgz") as t:
    t.extractall(f"{C}/cells")
CELLS = {os.path.basename(p)[:2] + ("c" if "02c" in p else "b" if "02b" in p else ""): p for p in glob.glob(f"{C}/cells/*.py")}


def cell(name, edits=(), net_kind=None, timeout=1500):
    """Chay o `name` (00 + o, IPython) y nhu may chay vong lap. edits = [(regex, thay)] ap dung cho CA tep ghep. Tra (rc, log)."""
    src = open(CELLS["00"], encoding="utf-8").read()
    src = re.sub(r"^GEN_CURRENT = .*$", f"GEN_CURRENT = {GEN}", src, flags=re.M)
    if net_kind:
        src = re.sub(r'^NET_KIND = "[a-z]*"', f'NET_KIND = "{net_kind}"', src, flags=re.M)
    body = open(CELLS[name], encoding="utf-8").read()
    if name == "02":     # ban thu lay ma tu nhanh BRANCH thay vi main
        body = body.replace("-b main", f"-b {BRANCH}").replace("origin main", f"origin {BRANCH}")
    for pat, rep in edits:
        body = re.sub(pat, rep, body, flags=re.M)
    f = f"{C}/t_{name}.ipy"
    open(f, "w", encoding="utf-8").write(src + "\n" + body)
    t = time.time()
    rc, out = sh(f"cd {C} && python3 -m IPython --no-banner --colors=NoColor {f} 2>&1", timeout=timeout)
    open(f"{C}/t_{name}.log", "w").write(out)
    log(f"   o {name}: {time.time() - t:.0f} s, rc {rc}")
    return rc, out


def tail(out, n=6):
    return "\n".join(out.strip().splitlines()[-n:])


log("may:", sh("nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader")[1].strip())
log("   pip onnx co san tren may moi?", sh("python3 -c 'import onnx' 2>&1 | tail -1")[1].strip() or "co")

# ------------------------------------------------------------------------------------------------------------------- A. o 02, kieu auto
print("\n##### A. o 02 tren may moi (NET_KIND auto)", flush=True)
rc, out = cell("02")
print(tail(out, 14), flush=True)
ket("A1 02 xong, FZ_NET=fzw", rc == 0 and "FZ_NET=fzw" in out)
ket("A2 net_kind = fzw", sh(f"cat {C}/fz_log/net_kind")[1].strip() == "fzw")
ket("A3 co gen%d.fzw, KHONG co .onnx" % GEN, os.path.exists(f"{C}/gen{GEN}.fzw") and not os.path.exists(f"{C}/gen{GEN}.onnx"))
ket("A4 KHONG tai ONNX Runtime (third_party trong)", not glob.glob(f"{E}/third_party/onnxruntime*") and "bo qua ONNX Runtime" in out)
ket("A5 02 khong pip install", "pip" not in out.lower().replace("pip package", ""), "")
log("   dung luong may sau 02:", sh(f"du -sh {E} {C}/gen{GEN}.pt {C}/gen{GEN}.fzw 2>&1")[1].replace("\n", " | "))
rc, out = sh(f"python3 -c 'import onnx' 2>&1 | tail -1")
log("   import onnx sau 02:", out.strip())

# ------------------------------------------------------------------------------------------------------------------- B. o 04
print("\n##### B. o 04 (tu dau, fzcuda)", flush=True)
rc, out = cell("04", edits=[(r"^SECS = .*$", "SECS = 75"), (r"^GAMES = .*$", "GAMES = 32")], timeout=900)
print(tail(out, 14), flush=True)
nps = re.findall(r"nps[ =:]+([0-9.,]+)", out)
ket("B1 04 chay bang --provider fzcuda", rc == 0 and "--provider fzcuda" in out and "FZ_NET=fzw" in out and "--extra-batches" not in out)
games = glob.glob(f"{C}/games_gen{GEN}/**/*.xz", recursive=True) + glob.glob(f"{C}/games_gen{GEN}/**/*.gz", recursive=True)
ket("B2 co van ghi ra", len(games) > 0, f"{len(games)} tep")
log("   nps in ra:", nps[-5:])

# ------------------------------------------------------------------------------------------------------------------- C. 06 + 02c + 07
print("\n##### C. 06 -> 02c -> 07 (train.py --out .pt, roi lay_mang fzw)", flush=True)
rc, out = cell("06")
ket("C1 06 gom zip", rc == 0 and os.path.exists(f"{C}/games_gen{GEN}.zip"))
rc, out = cell("02c")
print(tail(out, 5), flush=True)
ket("C2 02c khong pip (kieu fzw)", rc == 0 and "kiểu mạng fzw" in out and os.path.exists(f"{C}/gen{GEN}.pt"))
rc, out = cell("07", edits=[(r"--epochs 1 --swa-tail 10", "--epochs 1 --max-steps 4 --swa-tail 2"), (r"--batch 512 --accum-steps 2", "--batch 64 --accum-steps 1")], timeout=1200)
print(tail(out, 14), flush=True)
nxt = GEN + 1
ket("C3 07 khong xuat ONNX, ra gen%d.pt" % nxt, rc == 0 and os.path.exists(f"{C}/gen{nxt}.pt") and not os.path.exists(f"{C}/gen{nxt}.onnx"))
ket("C4 07 chuyen ra gen%d.fzw (lay_mang co kiem)" % nxt, os.path.exists(f"{C}/gen{nxt}.fzw") and "FZ_TAI_VE=" in out)

# ------------------------------------------------------------------------------------------------------------------- D. arena
print("\n##### D. o 08 arena (fzw): gen%d moi vs gen%d" % (nxt, GEN), flush=True)
rc, out = cell("08", edits=[(r"^GAMES = .*$", "GAMES = 8"), (r"^A_GEN = .*$", f"A_GEN = {nxt}"), (r"^B_GEN = .*$", f"B_GEN = {GEN}")], timeout=900)
print(tail(out, 12), flush=True)
m = re.search(r"^FZ_ARENA W=(\d+) D=(\d+) L=(\d+) N=(\d+)", out, re.M)
ket("D1 arena fzw xong", rc == 0 and m is not None and int(m.group(4)) >= 1 and "--provider fzcuda" in out, m.group(0) if m else "khong co dong FZ_ARENA")
ket("D2 dong ARENA co duoi .fzw", re.search(rf"A={C}/gen{nxt}\.fzw\s+vs\s+B={C}/gen{GEN}\.fzw", out) is not None)
# mang doi cu: 08 tu tai .pt doi truoc va chuyen
rc, out = cell("08", edits=[(r"^GAMES = .*$", "GAMES = 4"), (r"^A_GEN = .*$", f"A_GEN = {GEN}"), (r"^B_GEN = .*$", f"B_GEN = {GEN - 1}")], timeout=900)
print(tail(out, 8), flush=True)
m = re.search(r"^FZ_ARENA W=(\d+) D=(\d+) L=(\d+) N=(\d+)", out, re.M)
ket("D3 arena doi cu hon (08 tu tai gen%d.pt + chuyen fzw)" % (GEN - 1), m is not None and os.path.exists(f"{C}/gen{GEN - 1}.fzw"))

# ------------------------------------------------------------------------------------------------------------------- E. 02 lan hai
print("\n##### E. o 02 lan hai tren cung may (doi sau)", flush=True)
rc, out = cell("02")
print(tail(out, 6), flush=True)
ket("E1 giu ket luan fzw, khong chay thu lai", rc == 0 and "FZ_NET=fzw" in out and "chạy thử" not in out)

# ------------------------------------------------------------------------------------------------------------------- F. roi ve ONNX
print("\n##### F. bo chay CUDA hong -> auto roi ve ONNX", flush=True)
os.remove(f"{C}/fz_log/net_kind")
size = os.path.getsize(f"{C}/gen{GEN}.fzw")
with open(f"{C}/gen{GEN}.fzw", "r+b") as fh:     # lam hong: cat doi tep (CRC / do dai sai -> bo chay CUDA phai tu choi)
    fh.truncate(size // 2)
rc, out = cell("02", timeout=1500)
print(tail(out, 16), flush=True)
ket("F1 02 bao fzcuda khong chay duoc roi ve onnx", rc == 0 and "KHÔNG chạy được" in out and "FZ_NET=onnx" in out)
ket("F2 net_kind = onnx, co gen%d.onnx va ONNX Runtime" % GEN,
    sh(f"cat {C}/fz_log/net_kind")[1].strip() == "onnx" and os.path.exists(f"{C}/gen{GEN}.onnx") and bool(glob.glob(f"{E}/third_party/onnxruntime*")))
rc, out = cell("04", edits=[(r"^SECS = .*$", "SECS = 40"), (r"^GAMES = .*$", "GAMES = 8")], timeout=900)
print(tail(out, 8), flush=True)
ket("F3 04 kieu onnx chay bang --provider cuda", rc == 0 and "--provider cuda" in out and "FZ_NET=onnx" in out)
# NET_KIND = "fzw" tuong minh ma may khong chay duoc: phai DUNG va noi ly do
os.remove(f"{C}/fz_log/net_kind")
rc, out = cell("02", net_kind="fzw", timeout=600)
print(tail(out, 6), flush=True)
ket("F4 NET_KIND = fzw ma fzcuda hong: dung, khong tu roi ve onnx", rc != 0 and "FZ_NET=onnx" not in out)

print("\n" + "=" * 70)
for ten, ok, note in KQ:
    print(f"  {'PASS' if ok else 'FAIL'}  {ten} {note}")
print("=" * 70)
print(f"TONG: {sum(1 for _, ok, _ in KQ if ok)} dat, {sum(1 for _, ok, _ in KQ if not ok)} hong, {time.time() - T0:.0f} s")
