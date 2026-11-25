# -*- coding: utf-8 -*-
"""thu_qua_khop_t4.py -- bai kiem tra CHUAN cua mot duong huan luyen: no co HOC THUOC duoc mot tap nho khong, va FP16 (--amp) co hut so voi FP32 khong?

Nhat ky 10 lan huan luyen that cho thay CE chinh sach KHONG giam ngay tren du lieu mang da thay 3 lan (3,25 -> 3,27 trong mot vong), trong khi
muc tieu cua chinh tim kiem con 1,08 nat (san nhieu 2,35 so voi mang 3,43). Mot mang 5,6M tham so, qua nhieu vong tren 20.000 the, phai keo CE huan luyen
xuong ro ret (hoc thuoc). Neu khong: loi o duong huan luyen (AMP, mat na, toc do...), khong phai o thiet ke.
  A: lr 1e-3 --amp (nhu o 07)   B: lr 1e-3 FP32 (khong --amp)   C: lr 3e-4 --amp
Cung 20.000 the dau cua cua so (tep dtrain trong lr_data.tar), khoi dau gen103, 24 vong, lo 256, khong SWA (--swa-start-frac 1) de CE moi vong la CE cua trong so dang hoc.
Chay: python3 ~/chay_t4_thu.py thu_qua_khop_t4.py --can-phut 45 --timeout 2700 --tep <lr_data.tar>:/content/lr_data.tar"""
import os
import re
import subprocess
import time

REPO = "https://github.com/phuc11731510/chess_variant_engine"
REL_NN = REPO + "/releases/download/NN_Model"
C = "/content"
E = f"{C}/chess_variant_engine/custom_engine"
T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:6.0f}s]", *a, flush=True)


def shq(s):
    return "'" + s.replace("'", "'\"'\"'") + "'"


def sh(cmd, timeout=900):
    p = subprocess.run(["bash", "-c", f"timeout -k 5 {timeout} bash -c {shq(cmd)}"], capture_output=True, text=True, errors="replace")
    return p.returncode, p.stdout + p.stderr


log("may:", sh("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader")[1].strip())
sh(f"cd {C} && rm -rf chess_variant_engine && timeout 150 git clone -q --depth 1 --filter=blob:none --sparse -b main {REPO}.git "
   f"chess_variant_engine && cd chess_variant_engine && git sparse-checkout set custom_engine", timeout=250)
sh(f"cd {C} && rm -rf dtrain dval && tar xf lr_data.tar")
sh(f"python3 {E}/python/lay_mang.py pt {C}/gen103.pt --rel {REL_NN} 2>&1 | tail -n 1", timeout=300)
assert os.path.exists(f"{C}/gen103.pt")

CFG = [("A", "--lr 1e-3 --amp"), ("B", "--lr 1e-3"), ("C", "--lr 3e-4 --amp")]
COMMON = (f"--data {C}/dtrain --init-from {C}/gen103.pt --max-records 20000 --epochs 24 --batch 256 --val-frac 0 "
          f"--q-ratio 0.25 --weight-decay 1e-4 --grad-clip 10 --swa-start-frac 1 --seed 1")
for ten, cf in CFG:
    t = time.time()
    rc, out = sh(f"python3 {E}/python/train.py {COMMON} {cf} --out {C}/qk_{ten}.pt 2>&1", timeout=1100)
    ep = re.findall(r"epoch\s+(\d+): policy_loss=([\d.]+)\s+value_loss=([\d.]+)", out)
    if not ep:
        log(f"{ten} {cf}: rc={rc}, khong co dong epoch; cuoi log:", out[-400:])
        continue
    tom = ", ".join(f"{int(e)}:{float(p):.3f}/{float(v):.3f}" for e, p, v in ep if int(e) in (1, 2, 4, 8, 12, 16, 20, 24))
    log(f"{ten} ({cf}) rc={rc} {time.time() - t:.0f}s | vong:chinh sach/gia tri -> {tom}")
    amp = re.findall(r"\[amp\].*", out)
    if amp:
        log("   ", amp[-1][:200])
