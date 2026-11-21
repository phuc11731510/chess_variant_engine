# -*- coding: utf-8 -*-
"""profile_gpu_t4.py -- thoi gian GPU THAT cua mang vong lap (ORT CUDA EP, FP16 gop), theo nhan (kernel), lo 64, tren T4.

`--ort-profile` cua engine chi do thoi gian phat lenh phia CPU (CUDA khong dong bo), khong phai thoi gian GPU, nen dung
torch.profiler (CUPTI) bao quanh phien ORT-GPU cua pip: CUPTI ghi MOI nhan CUDA cua tien trinh, ke ca cua ORT.
Chay bang ~/chay_t4_thu.py.
"""
import os
import re
import subprocess
import sys
import time

GEN = 17
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


log("chuan bi: clone thua + mang")
sh(f"cd {C} && rm -rf chess_variant_engine && timeout 120 git clone -q --depth 1 --filter=blob:none --sparse -b main {REPO}.git "
   f"chess_variant_engine && cd chess_variant_engine && git sparse-checkout set custom_engine", timeout=200)
rc, out = sh(f"python3 {E}/python/lay_mang.py onnx {C}/gen{GEN}.onnx --rel {REL_NN} --fp16 2>&1 | tail -n 3", timeout=900)
print(out, flush=True)

PROF = r'''
import sys, time, collections
import numpy as np
sys.path.insert(0, "%(E)s/python")
import torch
import onnxruntime as ort
import train as T
from torch.profiler import profile, ProfilerActivity
x = T.check_inputs(64, seed=1)
s = ort.InferenceSession("%(C)s/gen%(GEN)d.onnx", providers=["CUDAExecutionProvider"])
name = s.get_inputs()[0].name
for _ in range(15):
    s.run(None, {name: x})
t = time.time()
for _ in range(20):
    s.run(None, {name: x})
wall = (time.time() - t) / 20 * 1000
print("ORT pip %%s: %%.2f ms/lo (do ngoai, gom chep numpy)" %% (ort.__version__, wall), flush=True)
N = 10
with profile(activities=[ProfilerActivity.CUDA, ProfilerActivity.CPU]) as prof:
    for _ in range(N):
        s.run(None, {name: x})
    torch.cuda.synchronize()
ev = prof.key_averages()
rows = [(e.key, e.count, getattr(e, "self_device_time_total", None) or getattr(e, "self_cuda_time_total", 0) or 0) for e in ev]
rows = [r for r in rows if r[2] > 0]
tot = sum(r[2] for r in rows) / N / 1000.0
print("tong thoi gian nhan GPU + memcpy: %%.2f ms/lo" %% tot, flush=True)
cat = collections.defaultdict(float)
def cls(k):
    kl = k.lower()
    if "memcpy" in kl or "memset" in kl: return "memcpy/memset"
    if any(w in kl for w in ("gemm", "cutlass", "xmma", "cublas", "sgemm", "hgemm", "gemv", "wmma")): return "GEMM (cuBLAS/cutlass)"
    if "softmax" in kl: return "softmax"
    if "layernorm" in kl or "layer_norm" in kl or "skiplayer" in kl: return "layernorm"
    if "transpose" in kl or "permute" in kl: return "transpose"
    if "gelu" in kl: return "gelu"
    if any(w in kl for w in ("elementwise", "vectorized", "cast", "add", "mul", "bias", "split", "concat", "copy", "gather")): return "elementwise/copy"
    return "khac"
for k, n, us in rows:
    cat[cls(k)] += us / N / 1000.0
print("--- theo nhom (ms/lo, %%) ---", flush=True)
for k, v in sorted(cat.items(), key=lambda kv: -kv[1]):
    print("%%-24s %%8.3f ms %%6.1f%%%%" %% (k, v, 100 * v / tot), flush=True)
print("--- 28 nhan nhieu thoi gian nhat (ms/lo, so lan/lo) ---", flush=True)
for k, n, us in sorted(rows, key=lambda r: -r[2])[:28]:
    print("%%8.3f  %%6.1f  %%s" %% (us / N / 1000.0, n / N, k[:110]), flush=True)
''' % {"E": E, "C": C, "GEN": GEN}
with open(f"{C}/prof.py", "w") as f:
    f.write(PROF)
log("profile GPU")
rc, out = sh(f"python3 {C}/prof.py 2>&1 | grep -v -E 'Warning|warn' ", timeout=900)
print(out, flush=True)
log("xong")
