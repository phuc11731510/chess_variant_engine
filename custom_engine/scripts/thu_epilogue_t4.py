# -*- coding: utf-8 -*-
"""thu_epilogue_t4.py -- thu tren T4 that: cong du trong epilogue cuBLASLt (beta = 1) + LayerNorm rieng, va ff1 (chay bang ~/chay_t4_thu.py).

Hai binary do ~/chay_t4_thu.py --tep dua len: MOI = /content/cu_moi (ban co thay doi), CU = /content/cu_cu (binary dang tren Release v3.0.0).
  1. may, clone thua nhanh BRANCH, gen<GEN>.pt tu Release NN_Model, .fzw (python/fzw.py)
  2. binary MOI: --fzcuda-dump, --test-fzcuda (nhan, mang vs PyTorch FP32, backend), fzw.py taps (buoc dau tien lech mo hinh CPU)
  3. thoi gian tung buoc (--bench-fzcuda) cua CU, MOI, va cac bien the ff1 cua MOI (--fz-opt exp=1,2,3)
  4. tu dau 90 s xen ke CU / MOI / CU / MOI (cung co nhu o 04) de so nps THAT
"""
import glob
import hashlib
import os
import re
import resource
import subprocess
import time

BRANCH = "luat-moi"
GEN = 17
REPO = "https://github.com/phuc11731510/chess_variant_engine"
REL = REPO + "/releases/download/v3.0.0"
REL_NN = REPO + "/releases/download/NN_Model"
C = "/content"
E = f"{C}/chess_variant_engine/custom_engine"
B_MOI, B_CU = f"{C}/cu_moi", f"{C}/cu_cu"
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


def dung(binary):
    sh(f"mkdir -p {E}/build-linux && cp {binary} {E}/build-linux/custom_engine && chmod +x {E}/build-linux/custom_engine")


log("1. may:", sh("nvidia-smi --query-gpu=name,driver_version,memory.total,clocks.max.sm --format=csv,noheader")[1].strip())
sh(f"cd {C} && rm -rf chess_variant_engine && timeout 120 git clone -q --depth 1 --filter=blob:none --sparse -b {BRANCH} {REPO}.git "
   f"chess_variant_engine && cd chess_variant_engine && git sparse-checkout set custom_engine", timeout=200)
for b in (B_MOI, B_CU):
    log("   sha256", os.path.basename(b), hashlib.sha256(open(b, "rb").read()).hexdigest()[:16])
dung(B_MOI)
rc, out = sh(f"SKIP_ORT=1 bash {E}/scripts/colab_quickstart.sh 2>&1 | tail -n 3", timeout=700)
print(out, flush=True)
ket("quickstart OK", "[quick] OK" in out)
sh(f"python3 {E}/python/lay_mang.py pt {C}/gen{GEN}.pt --rel {REL_NN} 2>&1 | tail -n 1", timeout=300)
rc, out = sh(f"python3 {E}/python/lay_mang.py fzw {C}/gen{GEN}.fzw --rel {REL_NN} 2>&1 | tail -n 3", timeout=600)
print(out, flush=True)
ket("gen.fzw (lay_mang fzw, mo hinh CPU moi)", os.path.exists(f"{C}/gen{GEN}.fzw") and rc == 0)
W = f"{C}/gen{GEN}.fzw"

log("2. binary MOI: the that + tham chieu FP32, --test-fzcuda, taps")
sh(f"python3 {E}/python/sinh_the_khoi_dau.py --n 64 --out {C}/book.txt", timeout=60)
P = f"{C}/pos.bin"
rc, out = sh(f"bash {E}/run.sh --fzcuda-dump {P} --games 512 --start-fen {C}/book.txt 2>&1 | tail -n 2", timeout=300)
rc, out = sh(f"cd {E}/python && python3 fzw.py ref {C}/gen{GEN}.pt {P} {P}.ref 2>&1 | tail -n 1", timeout=600)
ket("tep the + tham chieu", os.path.exists(P + ".ref"))
rc, out = sh(f"bash {E}/run.sh --test-fzcuda --weights {W} --fz-positions {P} 2>&1", timeout=900)
print("\n".join(l for l in out.splitlines() if "[PASS]" in l or "[FAIL]" in l or "TV" in l or "worst" in l or "FAIL" in l)[-3500:], flush=True)
ket("--test-fzcuda (binary MOI)", rc == 0 and "[PASS] --test-fzcuda" in out, f"ma thoat {rc}")
rc, out = sh(f"cd {E}/python && python3 fzw.py taps {C}/gen{GEN}.pt {P} 2>&1", timeout=600)
print(out[-1800:], flush=True)
ket("taps khop mo hinh CPU moi", "all stages agree" in out)


def bench(binary, tag, extra=""):
    dung(binary)
    rc, out = sh(f"bash {E}/run.sh --bench-fzcuda --weights {W} {extra} 2>&1", timeout=600)
    stages = {}
    in_stages = False
    for line in out.splitlines():
        if "time per stage" in line:
            in_stages = True
            continue
        m = re.match(r"\s+(.+?): ([\d.]+) ms$", line)
        if in_stages and m:
            stages[m.group(1)] = float(m.group(2))
    m64 = re.search(r"batch 64: ([\d.]+) ms per batch", out[out.find("one CUDA graph launch"):]) if "one CUDA graph launch" in out else None
    log(f"   {tag}: lo 64 (graph) {m64.group(1) if m64 else '?'} ms ; cac buoc:")
    for k, v in stages.items():
        print(f"        {v:7.3f} ms  {k}", flush=True)
    return stages, float(m64.group(1)) if m64 else None


log("3. thoi gian tung buoc (lo 64)")
st_cu, t_cu = bench(B_CU, "CU (Release)")
st_moi, t_moi = bench(B_MOI, "MOI exp=0")
ket("MOI nhanh hon CU o lo 64 (--bench-fzcuda, graph)", t_cu is not None and t_moi is not None and t_moi < t_cu, f"{t_moi} ms so voi {t_cu} ms")
for n in (1, 2, 3):
    bench(B_MOI, f"MOI exp={n}", f"--fz-opt exp={n}")

log("4. tu dau 90 s xen ke CU / MOI / CU / MOI")


def tu_dau(binary, tag):
    dung(binary)
    cmd = (f"cd {C} && rm -rf sp_x && bash {E}/run.sh --selfplay --games 48 --max-seconds 90 --visits 800 --max-moves 400 --fast-visits 200 "
           f"--fast-prob 0.5 --fast-cpuct 1.25 --fast-noise-eps 0.125 --temperature 0.5 --start-fen {C}/book.txt --parallel 16 --provider fzcuda "
           f"--fixed-batch 64 --batch-aggregate --noise-alpha 0.15 --show-nps --search-opt max-prefetch=0 --search-opt minibatch-size=32 "
           f"--search-opt nn-cache-size=2000000 --weights {W} --out {C}/sp_x")
    rc, out = sh(cmd, timeout=420)
    nh = re.findall(r"\[nhip\] t=(\d+)s\s+(\d+) van dang chay\s+(\d+) nps\s+(\d+) eval/s", out)
    nps = [int(x[2]) for x in nh if int(x[0]) >= 45]
    games = glob.glob(f"{C}/sp_x/**/*.xz", recursive=True)
    mean = sum(nps) / len(nps) if nps else 0.0
    log(f"   {tag}: ma thoat {rc}; nps (t>=45s) trung binh {mean:.0f} ({len(nps)} nhip); van xong {len(games)}")
    if rc != 0 or not nh:
        print(out[-1500:], flush=True)
    return mean


res = {"CU": [], "MOI": []}
for tag, b in (("CU", B_CU), ("MOI", B_MOI), ("CU", B_CU), ("MOI", B_MOI)):
    res[tag].append(tu_dau(b, tag))
m_cu, m_moi = sum(res["CU"]) / len(res["CU"]), sum(res["MOI"]) / len(res["MOI"])
log(f"   nps tu dau: CU {res['CU']} (tb {m_cu:.0f}) ; MOI {res['MOI']} (tb {m_moi:.0f}) ; MOI/CU = {m_moi / m_cu:.3f}" if m_cu else "   khong do duoc nps")
ket("MOI nhanh hon CU o tu dau that (ABAB)", m_cu > 0 and m_moi > m_cu, f"{m_moi:.0f} so voi {m_cu:.0f} nps")

log("=== TOM TAT ===")
for ten, ok, note in KQ:
    print(f"  {'PASS' if ok else 'FAIL'}  {ten}  {note}")
print("KET LUAN:", "TAT CA PASS" if all(k[1] for k in KQ) else "CO FAIL")
log("xong")
