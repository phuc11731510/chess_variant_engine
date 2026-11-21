# -*- coding: utf-8 -*-
"""bench_trt_dungsan_t4.py -- TensorRT: engine DUNG SAN va dung luong thu vien (chay bang ~/chay_t4_thu.py).

Tra loi hai cau hoi cua chu du an (2026-11-21):
  (1) Co dung san engine TensorRT roi dung lai cho cac doi khac duoc khong?
      T1: engine day du (co trong so) dung cho gen16, roi DOI tep ONNX sang trong so gen14 va chay lai CUNG bo nho dem:
          bo nho dem co bi dung nham khong (FZ_TRT_DIFF so voi CUDA FP32 cung tep: lech lon = dung nham trong so)?
      T2: engine BO TRONG SO (trt_weight_stripped_engine_enable): dung 1 lan voi gen16, doi sang gen14, nap lai + vá trong so
          (refit): ket qua dung (FZ_TRT_DIFF), toc do (FZ_TRT_SPEED), thoi gian nap, kich thuoc tep engine.
      T3: nhu T2 nhung da BO tep libnvinfer_builder_resource khoi may (chi chay, khong dung): co chay duoc khong.
  (2) Thu vien TensorRT can bao nhieu dung luong (that, va sau khi nen xz -9e nhu goi ORT "gon")?
Dung binary Release (bench-nn khong can ban sua WDL).
"""
import os
import re
import subprocess
import sys
import time

GEN_A, GEN_B = 16, 14
REPO = "https://github.com/phuc11731510/chess_variant_engine"
REL = REPO + "/releases/download/v3.0.0"
REL_NN = REPO + "/releases/download/NN_Model"
C = "/content"
E = f"{C}/chess_variant_engine/custom_engine"
ORT = f"{E}/third_party/onnxruntime-linux-x64-gpu-1.20.1"
TRT_DIR = f"{C}/trt"
NET = f"{C}/net.onnx"                       # DUONG DAN CO DINH cua mang dang dung
T0 = time.time()
R = {}


def log(*a):
    print(f"[{time.time() - T0:6.0f}s]", *a, flush=True)


def shq(s):
    return "'" + s.replace("'", "'\"'\"'") + "'"


def sh(cmd, timeout=900, show=True, tail=None):
    p = subprocess.Popen(["bash", "-c", f"timeout -k 5 {timeout} bash -c {shq(cmd)}"],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
    out = []
    for line in p.stdout:
        out.append(line)
        if show:
            print(line, end="", flush=True)
    p.wait()
    txt = "".join(out)
    if tail and not show:
        print("".join(txt.splitlines(True)[-tail:]), end="", flush=True)
    return p.returncode, txt


def ld(extra=""):
    return f"{extra}{TRT_DIR}/tensorrt_libs:$LD_LIBRARY_PATH"


# ---------------------------------------------------------------- setup
log("S1 ma + ORT (NuGet) + binary Release")
sh(f"cd {C} && rm -rf chess_variant_engine && timeout 120 git clone -q --depth 1 -b main {REPO}.git && echo clone_ok", timeout=200)
NUPKG = ("https://api.nuget.org/v3-flatcontainer/microsoft.ml.onnxruntime.gpu.linux/1.20.1/"
         "microsoft.ml.onnxruntime.gpu.linux.1.20.1.nupkg")
sh(f"set -e; mkdir -p {ORT}/lib; cd {C}; wget -q --tries=3 --waitretry=10 -O ort.nupkg {NUPKG}; rm -rf ort_nupkg; "
   f"unzip -q -o ort.nupkg 'runtimes/linux-x64/native/*' -d ort_nupkg; cp -a ort_nupkg/runtimes/linux-x64/native/*.so* {ORT}/lib/; "
   f"cd {ORT}/lib; [ -e libonnxruntime.so.1 ] || ln -s \"$(ls libonnxruntime.so* | head -n 1)\" libonnxruntime.so.1; ls", timeout=400)
rc, out = sh(f"BIN_URL={REL}/custom_engine bash {E}/scripts/colab_quickstart.sh", timeout=700, show=False, tail=3)
ok1 = "[quick] OK" in out

log("S2 mang gen%d / gen%d (do thi chuan FP32)" % (GEN_A, GEN_B))
PLAIN_PY = '''
import sys, os, torch
sys.path.insert(0, "%(E)s/python")
import lay_mang as L
from model import FairyNet
from train import export_onnx
gen = int(sys.argv[1]); out = sys.argv[2]
pt = "%(C)s/gen%%d.pt" %% gen
if not (os.path.isfile(pt) and os.path.getsize(pt) > 0):
    assert L.lay_pt(pt, "%(REL_NN)s") == 0, "khong lay duoc .pt"
sd = torch.load(pt, map_location="cpu")
d, t, h = L.suy_kien_truc(sd)
net = FairyNet(d_model=d, layers=t, heads=h); net.load_state_dict(sd); net.eval()
export_onnx(net, out, fuse=False, fp16=False)
print("PLAIN", out, os.path.getsize(out))
''' % {"E": E, "C": C, "REL_NN": REL_NN}
with open(f"{C}/plain.py", "w") as f:
    f.write(PLAIN_PY)
sh(f"python3 -m pip install -q onnx onnxscript 2>&1 | tail -n 1", timeout=300)
for g in (GEN_A, GEN_B):
    sh(f"cd {C} && python3 {C}/plain.py {g} {C}/gen{g}_plain.onnx 2>&1 | grep -E '^PLAIN|rror' | tail -n 3", timeout=600)
ok2 = all(os.path.exists(f"{C}/gen{g}_plain.onnx") for g in (GEN_A, GEN_B))
log("== S2", "PASS" if ok2 else "FAIL")

log("S3 TensorRT 10.4.0 (pip) + kich thuoc")
t0 = time.time()
sh(f"rm -rf {TRT_DIR}; pip install -q --no-deps --target {TRT_DIR} --extra-index-url https://pypi.nvidia.com "
   f"tensorrt-cu12-libs==10.4.0 2>&1 | tail -n 2", timeout=400)
R["pip_s"] = time.time() - t0
sh(f"ls -la {TRT_DIR}/tensorrt_libs | awk '{{print $5, $9}}'; du -sh {TRT_DIR}; "
   f"ls {TRT_DIR} | head -n 6; du -sh {TRT_DIR}/tensorrt_cu12_libs* 2>/dev/null | head", timeout=60)
ok3 = os.path.exists(f"{TRT_DIR}/tensorrt_libs/libnvinfer.so.10")
log("== S3", "PASS" if ok3 else "FAIL", f"pip {R['pip_s']:.0f}s")

# ---------------------------------------------------------------- (2) kich thuoc sau nen xz -9e
log("S4 nen xz -9e cac tep chay (nvinfer, plugin, onnxparser) -- do kich thuoc goi toi thieu")
if ok3:
    sh(f"mkdir -p {C}/xzt && cd {TRT_DIR}/tensorrt_libs && for f in libnvinfer.so.10 libnvinfer_plugin.so.10 libnvonnxparser.so.10; do "
       f"[ -e $f ] || continue; s=$(date +%s); cp -L $f {C}/xzt/$f; xz -9e -T2 -k -f {C}/xzt/$f; "
       f"echo \"$f: $(stat -c %s {C}/xzt/$f) -> $(stat -c %s {C}/xzt/$f.xz) byte, $(( $(date +%s) - s )) s\"; done; "
       f"echo '--- builder resource (chi can khi dung engine):'; ls -la {TRT_DIR}/tensorrt_libs/*builder_resource* | awk '{{print $5, $9}}'", timeout=1500)

# ---------------------------------------------------------------- bench helper
def bench(cache, extra="", label=""):
    t0 = time.time()
    rc, out = sh(f"export LD_LIBRARY_PATH={ld()}; cd {C} && timeout -k 5 900 bash {E}/run.sh --bench-nn --weights {NET} "
                 f"--provider tensorrt --fixed-batch 64 --trt-opt trt_fp16_enable=1 --trt-opt trt_engine_cache_path={cache} "
                 f"--trt-opt trt_timing_cache_path={cache} {extra}", timeout=1000, show=False)
    dt = time.time() - t0
    r = {"s": dt, "no_graph": "No graph will run on TensorRT" in out}
    m = re.search(r"^FZ_TRT_DIFF ([\d.]+) ([\d.]+)", out, re.M)
    r["diff"] = (float(m.group(1)), float(m.group(2))) if m else None
    m = re.search(r"^FZ_TRT_SPEED ([\d.]+) ([\d.]+)", out, re.M)
    r["speed"] = (float(m.group(1)), float(m.group(2))) if m else None
    keep = [l.strip()[:230] for l in out.splitlines() if re.search(r"refit|Refit|cache|Cache|stripped|rror|ERROR|nvinfer|Failed|failed", l)]
    r["lines"] = keep[:10]
    print(f"[{label}] {dt:.0f}s  diff={r['diff']}  speed(CUDA FP32, TRT)={r['speed']}  no_graph={r['no_graph']}", flush=True)
    for l in r["lines"]:
        print("     ", l, flush=True)
    if r["diff"] is None:
        print("".join(out.splitlines(True)[-14:]), flush=True)
    return r


def cache_info(path):
    rc, out = sh(f"ls -la {path} 2>/dev/null | awk 'NR>3{{print $5, $9}}'", timeout=30, show=False)
    return out.strip()


# ---------------------------------------------------------------- T1: engine day du, doi trong so, cung bo nho dem
if ok1 and ok2 and ok3:
    log("T1 engine DAY DU: dung voi gen%d, doi ONNX sang gen%d, chay lai cung bo nho dem" % (GEN_A, GEN_B))
    sh(f"cp {C}/gen{GEN_A}_plain.onnx {NET}; rm -rf {C}/c_full", timeout=60)
    t1a = bench(f"{C}/c_full", label="T1a gen%d (dung engine)" % GEN_A)
    print("   bo nho dem:", cache_info(f"{C}/c_full").replace("\n", " | "), flush=True)
    sh(f"cp {C}/gen{GEN_B}_plain.onnx {NET}", timeout=60)
    t1b = bench(f"{C}/c_full", label="T1b gen%d (cung bo nho dem)" % GEN_B)
    R["T1"] = (t1a, t1b)

    # ---------------------------------------------------------------- T2: bo trong so + refit
    log("T2 engine BO TRONG SO: dung voi gen%d, doi sang gen%d, nap + refit" % (GEN_A, GEN_B))
    sh(f"cp {C}/gen{GEN_A}_plain.onnx {NET}; rm -rf {C}/c_strip", timeout=60)
    strip = f"--trt-opt trt_weight_stripped_engine_enable=1 --trt-opt trt_onnx_model_folder_path={C}"
    t2a = bench(f"{C}/c_strip", strip, label="T2a gen%d (dung engine bo trong so)" % GEN_A)
    print("   bo nho dem:", cache_info(f"{C}/c_strip").replace("\n", " | "), flush=True)
    sh(f"cp {C}/gen{GEN_B}_plain.onnx {NET}", timeout=60)
    t2b = bench(f"{C}/c_strip", strip, label="T2b gen%d (nap + refit)" % GEN_B)
    R["T2"] = (t2a, t2b)
    sh(f"cd {C}/c_strip && for f in *.engine; do [ -e \"$f\" ] && echo \"$f: $(stat -c %s \"$f\") byte -> xz $(xz -9e -T2 -c \"$f\" | wc -c)\"; done", timeout=300)

    # ---------------------------------------------------------------- T3: bo builder_resource
    log("T3 nhu T2b nhung BO tep libnvinfer_builder_resource khoi may")
    sh(f"mkdir -p {C}/trt_aside && mv {TRT_DIR}/tensorrt_libs/*builder_resource* {C}/trt_aside/ && ls {TRT_DIR}/tensorrt_libs", timeout=60)
    sh(f"cp {C}/gen{GEN_B}_plain.onnx {NET}", timeout=60)
    t3 = bench(f"{C}/c_strip", strip, label="T3 gen%d (khong co builder_resource)" % GEN_B)
    R["T3"] = t3
    sh(f"mv {C}/trt_aside/* {TRT_DIR}/tensorrt_libs/", timeout=60)

log("=== TOM TAT ===")
print(f"pip tensorrt-cu12-libs 10.4.0: {R.get('pip_s', 0):.0f}s")
for k in ("T1", "T2"):
    if k in R:
        a, b = R[k]
        print(f"{k}: lan 1 {a['s']:.0f}s diff {a['diff']} speed {a['speed']} | lan 2 (doi trong so) {b['s']:.0f}s diff {b['diff']} speed {b['speed']}")
if "T3" in R:
    t = R["T3"]
    print(f"T3 (khong builder_resource): {t['s']:.0f}s diff {t['diff']} speed {t['speed']}")
log("xong")
