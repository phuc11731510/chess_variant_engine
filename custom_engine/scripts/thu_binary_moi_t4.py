# -*- coding: utf-8 -*-
"""thu_binary_moi_t4.py -- thu binary Linux MOI tren T4 truoc khi thay binary tren Release (chay bang ~/chay_t4_thu.py).

Tai binary qua dung duong cua vong lap (colab_quickstart.sh, BIN_URL), kiem sha256, chay: cac bai thu CPU, tu dau ngan bang
mang that (cuda, co o 04), arena ngan (nhiet do 0, co o 08), doc lai van tu dau bang xem_du_lieu --kiem.
Doi ASSET va SHA khi thu binary khac.
"""
import glob
import hashlib
import os
import re
import subprocess
import sys
import time

ASSET = "custom_engine_thu"
SHA = "d0437008f196537033cb4dfbf67b88f5027fb85584d0e308cd957073e7feba9d"
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


log("1. ma (clone thua) + binary + ONNX Runtime gon qua colab_quickstart.sh")
sh(f"cd {C} && rm -rf chess_variant_engine && timeout 120 git clone -q --depth 1 --filter=blob:none --sparse -b main {REPO}.git "
   f"chess_variant_engine && cd chess_variant_engine && git sparse-checkout set custom_engine", timeout=200)
rc, out = sh(f"BIN_URL={REL}/{ASSET} bash {E}/scripts/colab_quickstart.sh 2>&1 | tail -n 6", timeout=700)
print(out, flush=True)
b = f"{E}/build-linux/custom_engine"
got = hashlib.sha256(open(b, "rb").read()).hexdigest() if os.path.exists(b) else ""
ket("binary tai ve khop sha256", got == SHA, got[:16])
ket("quickstart OK", "[quick] OK" in out)

log("2. bai thu CPU (khong can mang)")
for flag in ("--test-uci", "--test-adapter", "--test-cli", "--test-search-logic", "--test-neural", "--test-board", "--test-rules"):
    rc, out = sh(f"bash {E}/run.sh {flag} 2>&1 | tail -n 3", timeout=600)
    # --test-board in "ALL CHESSBOARD BRIDGE TESTS PASSED!" (khong co nhan [PASS]); cac bai khac in "[PASS] ..."
    ok = "[PASS]" in out or "TESTS PASSED" in out
    ket(f"{flag}", ok, "" if ok else out[-200:])

log("3. mang gen16, gen17 (FP16) cho tu dau va arena")
for g in (16, 17):
    sh(f"python3 {E}/python/lay_mang.py onnx {C}/gen{g}.onnx --rel {REL_NN} --fp16 2>&1 | tail -n 1", timeout=900)
ok_net = all(os.path.exists(f"{C}/gen{g}.onnx") for g in (16, 17))
ket("mang gen16 + gen17", ok_net)

log("4. tu dau 90 s (16 van song song, cuda, cờ như ô 04)")
sh(f"python3 {E}/python/sinh_the_khoi_dau.py --n 48 --out {C}/book.txt", timeout=60)
cmd = (f"cd {C} && rm -rf sp_out && bash {E}/run.sh --selfplay --games 48 --max-seconds 90 --visits 800 --max-moves 400 --fast-visits 200 "
       f"--fast-prob 0.5 --fast-cpuct 1.25 --fast-noise-eps 0.125 --temperature 0.5 --start-fen {C}/book.txt --parallel 16 --provider cuda "
       f"--fixed-batch 64 --batch-aggregate --noise-alpha 0.15 --show-nps --search-opt max-prefetch=0 --search-opt minibatch-size=32 "
       f"--search-opt nn-cache-size=2000000 --weights {C}/gen17.onnx --out {C}/sp_out --extra-batches 16,32,48")
rc, out = sh(cmd, timeout=420)
nh = re.findall(r"\[nhip\] t=(\d+)s\s+(\d+) van dang chay\s+(\d+) nps\s+(\d+) eval/s", out)
nps = [int(x[2]) for x in nh if int(x[0]) >= 60]
games = glob.glob(f"{C}/sp_out/**/*.xz", recursive=True)
ev = re.search(r"NN eval/playout\s*:\s*([\d.]+)", out)
ket("tu dau chay xong, khong Abort", rc == 0 and "terminate called" not in out and "Exception" not in out,
    f"ma thoat {rc}; nhip={len(nh)}; nps (t>=60s) {nps}; ven choi xong {len(games)}; eval/playout {ev.group(1) if ev else '?'}")
if rc != 0 or not nh:
    print(out[-1500:], flush=True)
ket("nps tu dau >= 5500 (ban cu o cung dieu kien ~6400)", bool(nps) and sum(nps) / len(nps) >= 5500,
    f"{sum(nps) / len(nps):.0f}" if nps else "khong co so")

log("5. doc lai van tu dau (xem_du_lieu --kiem)")
if games:
    rc, out = sh(f"cd {C} && python3 {E}/python/xem_du_lieu.py {C}/sp_out --liet-ke --kiem 2>&1 | tail -n 6", timeout=300)
    print(out, flush=True)
    ket("xem_du_lieu --kiem giai ma dung van moi (ma thoat 0)", rc == 0)

log("6. arena ngan (8 van, 100 luot, nhiet do 0)")
rc, out = sh(f"cd {C} && bash {E}/run.sh --arena --model-a {C}/gen17.onnx --model-b {C}/gen16.onnx --games 8 --visits 100 --temperature 0 "
             f"--cpuct 1.25 --start-fen {C}/book.txt --provider cuda --fixed-batch 32 --max-moves 400 --show-nps "
             f"--search-opt max-prefetch=0 --parallel 4 --batch-aggregate --search-opt minibatch-size=32 --search-opt task-workers=0 2>&1 | "
             f"grep -E 'FZ_ARENA|arena\\] search|rror|terminate' | tail -n 5", timeout=600)
print(out, flush=True)
ket("arena chay xong, in FZ_ARENA, nhiet do 0", "FZ_ARENA" in out and "temperature 0" in out and "terminate" not in out)

log("=== TOM TAT ===")
for ten, ok, note in KQ:
    print(f"  {'PASS' if ok else 'FAIL'}  {ten}  {note}")
print("KET LUAN:", "TAT CA PASS" if all(k[1] for k in KQ) else "CO FAIL -- KHONG thay binary")
log("xong")
