# -*- coding: utf-8 -*-
"""thu_fzcuda_t4.py -- thu bo chay mang CUDA rieng (fzcuda) tren T4 that: dung hay khong, nhanh hay cham (chay bang ~/chay_t4_thu.py).

Binary dich bang bien_dich_linux_cuda.bat (ban_linux/custom_engine_fzcuda) duoc dua len may T4 thang bang `colab upload`
(~/chay_t4_thu.py --tep <local>:/content/custom_engine_fzcuda), KHONG qua Release. Ma + python lay tu nhanh BRANCH (clone thua). Cac buoc:
  1. clone thua, binary + ONNX Runtime gon qua colab_quickstart.sh, gen<GEN>.pt tu Release NN_Model;
  2. python/fzw.py convert gen.pt -> gen.fzw;  3. `--fzcuda-dump`: cac the co that (bo ma hoa that cua engine) + tham chieu PyTorch FP32;
  4. `--test-fzcuda`: nhan tung cai vs CPU, ca mang vs PyTorch (lo 1..64), backend, tat dinh, 4 luong, toc do tung lo / tung buoc;
  5. python/fzw.py taps: neu lech thi chi ra buoc dau tien lech;
  6. tu dau 90 s bang fzcuda (cung co nhu o 04), mot lan graph=1 va mot lan graph=0, de so nps voi ORT (6.588 nps o cung dieu kien),
     kem CPU dung va thong ke lo; giai ma van.
"""
import glob
import hashlib
import os
import re
import resource
import subprocess
import sys
import time

BRANCH = "luat-moi"
UPLOADED = "/content/custom_engine_fzcuda"   # binary do ~/chay_t4_thu.py --tep dua len
SHA = ""            # sha256 cua binary (de trong = chi in ra)
GEN = 17
REPO = "https://github.com/phuc11731510/chess_variant_engine"
REL = REPO + "/releases/download/v3.0.0"
REL_NN = REPO + "/releases/download/NN_Model"
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


log("1. may:", sh("nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader")[1].strip())
log("   thu vien cublas cu12:", sh("ls $(python3 -c 'import site;print(site.getsitepackages()[0])')/nvidia/cublas/lib 2>&1 | head -4")[1].strip().replace("\n", " "))
sh(f"cd {C} && rm -rf chess_variant_engine && timeout 120 git clone -q --depth 1 --filter=blob:none --sparse -b {BRANCH} {REPO}.git "
   f"chess_variant_engine && cd chess_variant_engine && git sparse-checkout set custom_engine", timeout=200)
sh(f"mkdir -p {E}/build-linux && cp {UPLOADED} {E}/build-linux/custom_engine && chmod +x {E}/build-linux/custom_engine")
rc, out = sh(f"bash {E}/scripts/colab_quickstart.sh 2>&1 | tail -n 4", timeout=700)
print(out, flush=True)
b = f"{E}/build-linux/custom_engine"
got = hashlib.sha256(open(b, "rb").read()).hexdigest() if os.path.exists(b) else ""
log("   sha256 binary:", got)
ket("binary da len may (khop sha256 neu da dien)", bool(got) and (not SHA or got == SHA))
ket("quickstart OK", "[quick] OK" in out)

rc, out = sh(f"python3 {E}/python/lay_mang.py pt {C}/gen{GEN}.pt --rel {REL_NN} 2>&1 | tail -n 1", timeout=300)
ket(f"gen{GEN}.pt", os.path.exists(f"{C}/gen{GEN}.pt"), out.strip()[-80:])
rc, out = sh(f"cd {E}/python && python3 fzw.py convert {C}/gen{GEN}.pt {C}/gen{GEN}.fzw 2>&1 | tail -n 2", timeout=300)
print(out, flush=True)
ket("gen.fzw (chi can torch, khong onnx / onnxruntime)", os.path.exists(f"{C}/gen{GEN}.fzw"))

log("2. the co that + tham chieu FP32")
sh(f"python3 {E}/python/sinh_the_khoi_dau.py --n 64 --out {C}/book.txt", timeout=60)
P = f"{C}/pos.bin"
rc, out = sh(f"bash {E}/run.sh --fzcuda-dump {P} --games 512 --start-fen {C}/book.txt 2>&1 | tail -n 2", timeout=300)
print(out, flush=True)
rc, out = sh(f"cd {E}/python && python3 fzw.py ref {C}/gen{GEN}.pt {P} {P}.ref 2>&1 | tail -n 1", timeout=600)
print(out, flush=True)
ket("tep the + tham chieu", os.path.exists(P + ".ref"))

log("3. --test-fzcuda (nhan, mang, backend, toc do)")
rc, out = sh(f"bash {E}/run.sh --test-fzcuda --weights {C}/gen{GEN}.fzw --fz-positions {P} 2>&1", timeout=900)
print(out, flush=True)
ket("--test-fzcuda", rc == 0 and "[PASS] --test-fzcuda" in out, f"ma thoat {rc}")
m = re.search(r"batch 64: ([\d.]+) ms per batch", out)
ket("toc do lo 64 (ORT: 12,85 ms)", bool(m), f"{m.group(1)} ms" if m else "khong co so")

log("4. taps (buoc dau tien lech CPU)")
rc, out = sh(f"cd {E}/python && python3 fzw.py taps {C}/gen{GEN}.pt {P} 2>&1", timeout=600)
print(out, flush=True)
ket("taps khop mo hinh CPU", "all stages agree" in out)

def tu_dau(tag, extra=""):
    log(f"5. tu dau 90 s bang fzcuda ({tag})")
    cmd = (f"cd {C} && rm -rf sp_fz && bash {E}/run.sh --selfplay --games 48 --max-seconds 90 --visits 800 --max-moves 400 --fast-visits 200 "
           f"--fast-prob 0.5 --fast-cpuct 1.25 --fast-noise-eps 0.125 --temperature 0.5 --start-fen {C}/book.txt --parallel 16 --provider fzcuda "
           f"--fixed-batch 64 --batch-aggregate --noise-alpha 0.15 --show-nps --search-opt max-prefetch=0 --search-opt minibatch-size=32 "
           f"--search-opt nn-cache-size=2000000 --weights {C}/gen{GEN}.fzw --out {C}/sp_fz {extra}")
    ru0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    t_sp = time.time()
    rc, out = sh(cmd, timeout=420)
    ru1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = (ru1.ru_utime - ru0.ru_utime) + (ru1.ru_stime - ru0.ru_stime)
    log(f"   CPU del engine: {cpu:.0f} s (user {ru1.ru_utime - ru0.ru_utime:.0f} + sys {ru1.ru_stime - ru0.ru_stime:.0f}) trong {time.time() - t_sp:.0f} s thuc = "
        f"{cpu / (time.time() - t_sp):.2f} nhan CPU (may co {os.cpu_count()})")
    print(chr(10).join(out.splitlines()[-28:]), flush=True)
    nh = re.findall(r"\[nhip\] t=(\d+)s\s+(\d+) van dang chay\s+(\d+) nps\s+(\d+) eval/s", out)
    nps = [int(x[2]) for x in nh if int(x[0]) >= 60]
    games = glob.glob(f"{C}/sp_fz/**/*.xz", recursive=True)
    ev = re.search(r"NN eval/playout\s*:\s*([\d.]+)", out)
    ket(f"tu dau {tag}: chay xong, khong Abort", rc == 0 and "terminate called" not in out and "Exception" not in out,
        f"ma thoat {rc}; nhip={len(nh)}; nps (t>=60s) {nps}; van xong {len(games)}; eval/playout {ev.group(1) if ev else '?'}")
    if rc != 0 or not nh:
        print(out[-2000:], flush=True)
    if nps:
        ket(f"nps tu dau {tag} (ORT cung dieu kien: 6.588)", True, f"{sum(nps) / len(nps):.0f}")
    if games and tag == "graph=1":
        rc, out = sh(f"cd {C} && python3 {E}/python/xem_du_lieu.py {C}/sp_fz --liet-ke --kiem 2>&1 | tail -n 3", timeout=300)
        print(out, flush=True)
        ket("xem_du_lieu --kiem giai ma van fzcuda", rc == 0)


tu_dau("graph=1")
tu_dau("graph=0", "--fz-opt graph=0")

# 6. ONNX Runtime nap luc can (-Donnxruntime_dlopen=true): binary khong lien ket libonnxruntime. Phai (a) chay khi KHONG co no tren duong
#    dan, (b) van dung duoc ONNX Runtime (CPU va CUDA EP) khi co: nhu vay binary nay thay duoc binary cu cho cac o lenh cu.
log("6. ONNX Runtime nap luc can")
rc, out = sh(f"ldd {E}/build-linux/custom_engine | grep -c libonnxruntime", timeout=30)
ket("binary khong lien ket dong voi libonnxruntime", out.strip().splitlines()[-1] == "0", out.strip()[-40:])
rc, out = sh(f"env -u LD_LIBRARY_PATH {E}/build-linux/custom_engine --test-uci 2>&1 | grep -c PASS", timeout=60)
ket("--test-uci khi KHONG co ONNX Runtime tren duong dan", out.strip().splitlines()[-1] == "1", out.strip()[-40:])
if os.path.exists(f"{C}/seed.onnx"):
    rc, out = sh(f"env -u LD_LIBRARY_PATH {E}/build-linux/custom_engine --test-neural --weights {C}/seed.onnx 2>&1 | tail -n 3", timeout=300)
    print(out, flush=True)
    ket("--test-neural --weights seed.onnx khi thieu ONNX Runtime: bao loi ro rang, khong sap", "ONNX Runtime" in out or "PASS" in out, out.strip()[-120:])
    rc, out = sh(f"bash {E}/run.sh --test-neural --weights {C}/seed.onnx 2>&1 | tail -n 3", timeout=600)
    print(out, flush=True)
    ket("--test-neural --weights seed.onnx (ONNX Runtime nap luc can, CPU)", rc == 0 and "[PASS] --test-neural" in out)
    cmd = (f"cd {C} && rm -rf sp_ort && bash {E}/run.sh --selfplay --games 8 --max-seconds 40 --visits 100 --max-moves 100 --temperature 0.5 "
           f"--parallel 4 --provider cuda --fixed-batch 16 --batch-aggregate --weights {C}/seed.onnx --out {C}/sp_ort 2>&1 | tail -n 6")
    rc, out = sh(cmd, timeout=300)
    print(out, flush=True)
    ket("tu dau --provider cuda (ONNX Runtime nap luc can, CUDA EP)", rc == 0 and glob.glob(f"{C}/sp_ort/**/*.xz", recursive=True) != [])
else:
    log("   (khong co /content/seed.onnx: bo qua kiem ONNX Runtime nap luc can; dua len bang --tep)")

log("=== TOM TAT ===")
for ten, ok, note in KQ:
    print(f"  {'PASS' if ok else 'FAIL'}  {ten}  {note}")
print("KET LUAN:", "TAT CA PASS" if all(k[1] for k in KQ) else "CO FAIL")
log("xong")
