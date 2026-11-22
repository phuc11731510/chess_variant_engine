# -*- coding: utf-8 -*-
"""thu_elo_cat_t4.py -- thu tren T4 that --temp-elo-cutoff 70.44 (chay bang ~/chay_t4_thu.py --tep <binary moi>:/content/cu_moi).

Tu dau 90 s xen ke A (khong co) / B (--temp-elo-cutoff 70.44) / A / B, cung co nhu o 04, mang gen<GEN> that. Voi moi lan:
  - nps (khong duoc cham di: bo loc chi chay mot lan moi nuoc);
  - doc lai cac van (.xz): ti le nuoc da di KHAC nuoc nhieu luot nhat, ti le nuoc kem nuoc nhieu luot nhat QUA 70,44 Elo
    (theo best_q / played_q cua ban ghi), do kem lon nhat. Voi B phai la KHONG nuoc nao qua 70,44.
"""
import glob
import hashlib
import math
import os
import re
import subprocess
import sys
import time

BRANCH = "luat-moi"
GEN = 17
CUT = 70.44
REPO = "https://github.com/phuc11731510/chess_variant_engine"
REL_NN = REPO + "/releases/download/NN_Model"
C = "/content"
E = f"{C}/chess_variant_engine/custom_engine"
B_MOI = f"{C}/cu_moi"
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


log("1. may:", sh("nvidia-smi --query-gpu=name,driver_version --format=csv,noheader")[1].strip())
sh(f"cd {C} && rm -rf chess_variant_engine && timeout 120 git clone -q --depth 1 --filter=blob:none --sparse -b {BRANCH} {REPO}.git "
   f"chess_variant_engine && cd chess_variant_engine && git sparse-checkout set custom_engine", timeout=200)
log("   sha256 binary", hashlib.sha256(open(B_MOI, "rb").read()).hexdigest()[:16])
sh(f"mkdir -p {E}/build-linux && cp {B_MOI} {E}/build-linux/custom_engine && chmod +x {E}/build-linux/custom_engine")
rc, out = sh(f"SKIP_ORT=1 bash {E}/scripts/colab_quickstart.sh 2>&1 | tail -n 2", timeout=700)
ket("quickstart OK", "[quick] OK" in out)
sh(f"python3 {E}/python/lay_mang.py pt {C}/gen{GEN}.pt --rel {REL_NN} 2>&1 | tail -n 1", timeout=300)
rc, out = sh(f"python3 {E}/python/lay_mang.py fzw {C}/gen{GEN}.fzw --rel {REL_NN} 2>&1 | tail -n 2", timeout=600)
ket("gen.fzw", os.path.exists(f"{C}/gen{GEN}.fzw") and rc == 0)
W = f"{C}/gen{GEN}.fzw"
sh(f"python3 {E}/python/sinh_the_khoi_dau.py --n 64 --out {C}/book.txt", timeout=60)
rc, out = sh(f"bash {E}/run.sh --help 2>&1 | grep -c -- --temp-elo-cutoff", timeout=60)
log("   binary biet --temp-elo-cutoff (--help):", out.strip().splitlines()[-1] if out.strip() else "?")

sys.path.insert(0, f"{E}/python")
import trainingdata_v6 as v6  # noqa: E402


def elo(q):
    s = min(max((1.0 + q) / 2.0, 1e-3), 1 - 1e-3)
    return 400.0 * math.log10(s / (1.0 - s))


def doc(thu_muc):
    """(so nuoc, ti le nuoc khac nuoc nhieu luot nhat, so nuoc qua CUT Elo, do kem lon nhat) cua cac van trong thu muc."""
    n = moved = big = 0
    worst = 0.0
    for f in glob.glob(f"{thu_muc}/**/*.xz", recursive=True):
        for r in v6.decode_game(open(f, "rb").read(), f, dense=False):
            n += 1
            if r["played_idx"] != r["best_idx"]:
                moved += 1
                d = elo(r["best_q"]) - elo(r["played_q"])
                worst = max(worst, d)
                big += d > CUT + 1e-3
    return n, (moved / n if n else 0.0), big, worst


def tu_dau(extra, tag):
    cmd = (f"cd {C} && rm -rf sp_x && bash {E}/run.sh --selfplay --games 48 --max-seconds 90 --visits 800 --max-moves 400 --fast-visits 200 "
           f"--fast-prob 0.5 --fast-cpuct 1.25 --fast-noise-eps 0.125 --temperature 0.5 --start-fen {C}/book.txt --parallel 16 --provider fzcuda "
           f"--fixed-batch 64 --batch-aggregate --noise-alpha 0.15 --show-nps --search-opt max-prefetch=0 --search-opt minibatch-size=32 "
           f"--search-opt nn-cache-size=2000000 --weights {W} --out {C}/sp_x {extra}")
    rc, out = sh(cmd, timeout=420)
    nh = re.findall(r"\[nhip\] t=(\d+)s\s+(\d+) van dang chay\s+(\d+) nps", out)
    nps = [int(x[2]) for x in nh if int(x[0]) >= 45]
    mean = sum(nps) / len(nps) if nps else 0.0
    n, moved, big, worst = doc(f"{C}/sp_x")
    dong = [l for l in out.splitlines() if "[selfplay] search" in l]
    log(f"   {tag}: ma thoat {rc}; nps {mean:.0f}; {n} nuoc: khac nuoc nhieu luot nhat {100 * moved:.1f}%, qua {CUT} Elo: {big} nuoc, kem nhat {worst:.0f} Elo")
    if rc != 0:
        print(out[-1500:], flush=True)
    return mean, n, moved, big, worst, "\n".join(dong)


log("2. tu dau 90 s xen ke A (khong loc) / B (--temp-elo-cutoff 70.44)")
res = {"A": [], "B": []}
dong_b = ""
for tag in ("A", "B", "A", "B"):
    r = tu_dau("" if tag == "A" else f"--temp-elo-cutoff {CUT}", tag)
    res[tag].append(r)
    if tag == "B":
        dong_b = r[5]
print(dong_b, flush=True)
mA = sum(r[0] for r in res["A"]) / 2
mB = sum(r[0] for r in res["B"]) / 2
ket("B: khong nuoc nao qua 70,44 Elo kem nuoc nhieu luot nhat", all(r[3] == 0 for r in res["B"]) and all(r[1] > 0 for r in res["B"]),
    f"{[r[3] for r in res['B']]} nuoc qua; kem nhat {[round(r[4], 1) for r in res['B']]}")
ket("A (khong loc) co nuoc qua 70,44 Elo (bo loc co viec de lam)", sum(r[3] for r in res["A"]) > 0, f"{[r[3] for r in res['A']]} nuoc")
ket("banner self-play ghi bo loc", "struck out" in dong_b, dong_b[-120:])
log(f"   ti le nuoc khac nuoc nhieu luot nhat: A {[round(100 * r[2], 1) for r in res['A']]}%  B {[round(100 * r[2], 1) for r in res['B']]}%")
log(f"   nps: A {[round(r[0]) for r in res['A']]} (tb {mA:.0f})  B {[round(r[0]) for r in res['B']]} (tb {mB:.0f})  B/A = {mB / mA:.3f}" if mA else "   khong do duoc nps")
ket("nps khong cham di vi bo loc (B >= 0,97 A)", mA > 0 and mB >= 0.97 * mA, f"{mB:.0f} so voi {mA:.0f}")

log("=== TOM TAT ===")
for ten, ok, note in KQ:
    print(f"  {'PASS' if ok else 'FAIL'}  {ten}  {note}")
print("KET LUAN:", "TAT CA PASS" if all(k[1] for k in KQ) else "CO FAIL")
log("xong")
