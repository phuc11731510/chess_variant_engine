# -*- coding: utf-8 -*-
"""bench_repack_pip_t4.py -- goi pip `onnxruntime-gpu` (239,7 MB) nen xz -9e va luoc bot xuong con bao nhieu, va ban luoc con chay CUDA khong.

  1. pip download --no-deps onnxruntime-gpu==1.32.0 (dung ban gio dang dung o lay_mang)
  2. giai nen: liet ke tep lon nhat
  3. nen: (a) nguyen ban tho (tar + xz -9e), (b) da luoc: bo provider TensorRT, quantization, tools, tests, datasets... (giu transformers)
  4. kiem tra ban luoc: giai nen vao thu muc rieng, PYTHONPATH, import, CUDAExecutionProvider, chay gen17.onnx lo 64, so sanh dau ra voi ban pip thuong
Chay bang ~/chay_t4_thu.py.
"""
import glob
import os
import re
import shutil
import subprocess
import sys
import time

C = "/content"
VER = "1.32.0"
REPO = "https://github.com/phuc11731510/chess_variant_engine"
REL_NN = REPO + "/releases/download/NN_Model"
E = f"{C}/chess_variant_engine/custom_engine"
T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:6.0f}s]", *a, flush=True)


def shq(s):
    return "'" + s.replace("'", "'\"'\"'") + "'"


def sh(cmd, timeout=900):
    p = subprocess.run(["bash", "-c", f"timeout -k 5 {timeout} bash -c {shq(cmd)}"], capture_output=True, text=True, errors="replace")
    return p.returncode, p.stdout + p.stderr


def size(p):
    return os.path.getsize(p) / 1048576


log("1. tai goi")
sh(f"rm -rf {C}/whl {C}/tree {C}/tree_nho && mkdir -p {C}/whl")
rc, out = sh(f"pip download --no-deps -d {C}/whl onnxruntime-gpu=={VER} 2>&1 | tail -n 2", timeout=600)
print(out, flush=True)
whl = (glob.glob(f"{C}/whl/*.whl") or [None])[0]
assert whl, "khong tai duoc goi"
log(f"goi: {os.path.basename(whl)} = {size(whl):.1f} MiB")

log("2. giai nen, tep lon nhat")
sh(f"mkdir -p {C}/tree && cd {C}/tree && unzip -q -o {whl}")
rc, out = sh(f"cd {C}/tree && du -sh . && find . -type f -printf '%s %p\\n' | sort -rn | head -n 12 | awk '{{printf \"%8.1f MiB  %s\\n\", $1/1048576, $2}}'")
print(out, flush=True)

log("3a. nen xz -9e ban tho (tar)")
t = time.time()
sh(f"cd {C} && tar -cf tho.tar -C tree . && xz -9e -T2 -k -f tho.tar", timeout=1500)
tho = size(f"{C}/tho.tar.xz")
log(f"== tho: tar {size(f'{C}/tho.tar'):.1f} MiB -> xz {tho:.1f} MiB ({time.time() - t:.0f}s)")

log("3b. luoc bot")
sh(f"cp -a {C}/tree {C}/tree_nho && cd {C}/tree_nho && rm -rf onnxruntime/capi/libonnxruntime_providers_tensorrt.so "
   f"onnxruntime/quantization onnxruntime/datasets onnxruntime/transformers/models onnxruntime/backend "
   f"&& find . -name '__pycache__' -prune -exec rm -rf {{}} + ; find . -name 'tests' -type d -prune -exec rm -rf {{}} + ; true")
rc, out = sh(f"cd {C}/tree_nho && du -sh . && ls onnxruntime onnxruntime/capi | head -n 40")
print(out, flush=True)
t = time.time()
sh(f"cd {C} && tar -cf nho.tar -C tree_nho . && xz -9e -T2 -k -f nho.tar", timeout=1500)
nho = size(f"{C}/nho.tar.xz")
log(f"== luoc: tar {size(f'{C}/nho.tar'):.1f} MiB -> xz {nho:.1f} MiB ({time.time() - t:.0f}s)")

log("4. kiem tra ban luoc (giai nen tu xz, PYTHONPATH)")
sh(f"rm -rf {C}/site_nho && mkdir -p {C}/site_nho && tar -xJf {C}/nho.tar.xz -C {C}/site_nho")
sh(f"rm -rf {C}/chess_variant_engine && cd {C} && timeout 120 git clone -q --depth 1 --filter=blob:none --sparse -b main {REPO}.git chess_variant_engine "
   f"&& cd chess_variant_engine && git sparse-checkout set custom_engine", timeout=200)
sh(f"python3 {E}/python/lay_mang.py onnx {C}/gen17.onnx --rel {REL_NN} --fp16 2>&1 | tail -n 2", timeout=900)
TEST = r'''
import sys, numpy as np, importlib.metadata as md
sys.path.insert(0, "%(E)s/python")
import onnxruntime as ort
print("ORT", ort.__version__, "tu", ort.__file__)
print("providers", ort.get_available_providers())
try:
    print("metadata", md.version("onnxruntime-gpu"))
except Exception as e:
    print("metadata loi", e)
try:
    from onnxruntime.transformers.onnx_model import OnnxModel
    from onnxruntime.transformers import optimizer
    print("onnxruntime.transformers (OnnxModel, optimizer): import OK")
except Exception as e:
    print("onnxruntime.transformers LOI:", type(e).__name__, str(e)[:160])
import train as T
x = T.check_inputs(64, seed=3)
s = ort.InferenceSession("%(C)s/gen17.onnx", providers=["CUDAExecutionProvider"])
print("session dung", s.get_providers())
out = s.run(None, {s.get_inputs()[0].name: x})
np.save("%(C)s/%(tag)s.npy", np.concatenate([o.reshape(64, -1) for o in out], axis=1))
import time
for _ in range(10): s.run(None, {s.get_inputs()[0].name: x})
t = time.time()
for _ in range(20): s.run(None, {s.get_inputs()[0].name: x})
print("ms/lo %%.2f" %% ((time.time() - t) / 20 * 1000))
'''
for tag, pp in (("pip_thuong", ""), ("nho", f"{C}/site_nho")):
    with open(f"{C}/t_{tag}.py", "w") as f:
        f.write(TEST % {"E": E, "C": C, "tag": tag})
    # ban luoc phai DUNG TRUOC ban pip thuong: PYTHONPATH di truoc site-packages
    rc, out = sh(f"PYTHONPATH={pp} python3 {C}/t_{tag}.py 2>&1 | grep -v -i warn | tail -n 8", timeout=600)
    print(f"--- {tag}:\n{out}", flush=True)
import numpy as np
a, b = np.load(f"{C}/pip_thuong.npy"), np.load(f"{C}/nho.npy")
print("khac biet toi da giua hai ban:", float(np.abs(a - b).max()), flush=True)

log("=== TOM TAT ===")
print(f"goi pip: {size(whl):.1f} MiB (zip)")
print(f"nen xz -9e: nguyen ban {tho:.1f} MiB | da luoc {nho:.1f} MiB")
log("xong")
