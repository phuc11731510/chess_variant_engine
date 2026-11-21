# -*- coding: utf-8 -*-
"""bench_tensorrt_t4.py -- thi nghiem TensorRT tren T4 (chay bang `colab exec`, xem ~/chay_t4_thu.py).

Do bang DUNG engine va ONNX Runtime 1.20.1 cua vong lap (binary Release v3.0.0), mang doi GEN:
  S2  ma + binary + ONNX Runtime 1.20.1 (goi NuGet Microsoft.ML.OnnxRuntime.Gpu.Linux: co provider TensorRT; goi "gon"
      cua vong lap khong co; GitHub microsoft/onnxruntime tra 404 tu 2026-11-21)
  S3  mang gen<GEN>.onnx cua vong lap (FP16, da GOP toan tu contrib SkipLayerNormalization / BiasGelu) VA mot ban
      do thi CHUAN FP32 (khong gop: TensorRT khong hieu toan tu contrib, lan 1 bao "No graph will run on TensorRT")
  S4  thu vien TensorRT 10.x (pip --no-deps --target, khong dong den python cua may)
  S5  --bench-nn lo 64: CUDA EP (mang vong lap) so voi TensorRT EP FP16 tren do thi chuan; dong FZ_TRT_SPEED / FZ_TRT_DIFF
  S6  (neu TensorRT nhanh hon >= 15%) do khop bang python: TV policy, |WDL|, |mlh| theo ngưỡng cua lay_mang
  S7  tu dau 16 van song song (cung co o 04): CUDA EP (mang vong lap) so voi TensorRT, doc cac dong [nhip]
Moi buoc tu bao PASS / FAIL; "No graph will run on TensorRT" la FAIL (khong phai chay bang TensorRT).
"""
import os
import re
import subprocess
import sys
import time

GEN = 16
REPO = "https://github.com/phuc11731510/chess_variant_engine"
REL = REPO + "/releases/download/v3.0.0"
REL_NN = REPO + "/releases/download/NN_Model"
C = "/content"
E = f"{C}/chess_variant_engine/custom_engine"
ORT = f"{E}/third_party/onnxruntime-linux-x64-gpu-1.20.1"
TRT_DIR = f"{C}/trt"
NET = f"{C}/gen{GEN}.onnx"
PLAIN = f"{C}/gen{GEN}_plain.onnx"
SAVE = {}
T0 = time.time()
# True: chi dung engine TensorRT + tu dau (bo S5 / S6 / tu dau CUDA): lan 3 da do xong S5 (TensorRT 8,31 ms so voi CUDA 12,85 ms
# o lo 64) va S6 (khop), con tu dau TensorRT bi hong ngay khi khoi dong.
ONLY_SP = True


def log(*a):
    print(f"[{time.time() - T0:6.0f}s]", *a, flush=True)


def shq(s):
    return "'" + s.replace("'", "'\"'\"'") + "'"


def sh(cmd, timeout=900, show=True, tail=None):
    """Chay bash, in dong dang chay; tra (ma thoat, toan bo dau ra). timeout cung bang `timeout -k 5`."""
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


def stage(name, ok, note=""):
    SAVE.setdefault("stages", []).append((name, ok, note))
    log(f"== {name}: {'PASS' if ok else 'FAIL'} {note}")


def ld_extra():
    parts = []
    if os.path.isdir(f"{TRT_DIR}/tensorrt_libs"):
        parts.append(f"{TRT_DIR}/tensorrt_libs")
    return ":".join(parts + ["$LD_LIBRARY_PATH"])


def ld_full():
    """LD_LIBRARY_PATH cho python (ORT pip + TensorRT): giong run.sh cua engine (CUDA 12 truoc, goi nvidia sau)."""
    import glob
    import site
    parts = [f"{TRT_DIR}/tensorrt_libs", "/usr/local/cuda/lib64"]
    for sp in site.getsitepackages():
        parts += sorted(glob.glob(sp + "/nvidia/*/lib"))
    parts.append(f"{ORT}/lib")
    return ":".join([p for p in parts if os.path.isdir(p)] + [os.environ.get("LD_LIBRARY_PATH", "")])


# ---------------------------------------------------------------- S1
log("S1 moi truong")
sh("nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader; nproc", timeout=60)

# ---------------------------------------------------------------- S2
log("S2 ma + binary + ONNX Runtime")
sh(f"cd {C} && rm -rf chess_variant_engine && timeout 120 git clone -q --depth 1 -b main {REPO}.git && echo clone_ok", timeout=200)
NUPKG = ("https://api.nuget.org/v3-flatcontainer/microsoft.ml.onnxruntime.gpu.linux/1.20.1/"
         "microsoft.ml.onnxruntime.gpu.linux.1.20.1.nupkg")
sh(f"set -e; mkdir -p {ORT}/lib; cd {C}; wget -q --tries=3 --waitretry=10 -O ort.nupkg {NUPKG}; "
   f"rm -rf ort_nupkg; unzip -q -o ort.nupkg 'runtimes/linux-x64/native/*' -d ort_nupkg; "
   f"cp -a ort_nupkg/runtimes/linux-x64/native/*.so* {ORT}/lib/; cd {ORT}/lib; "
   f"[ -e libonnxruntime.so.1 ] || ln -s \"$(ls libonnxruntime.so* | head -n 1)\" libonnxruntime.so.1; ls", timeout=400)
rc, out = sh(f"BIN_URL={REL}/custom_engine bash {E}/scripts/colab_quickstart.sh", timeout=700, show=False, tail=4)
ok2 = "[quick] OK" in out and os.path.exists(f"{ORT}/lib/libonnxruntime_providers_tensorrt.so")
stage("S2 quickstart + provider TensorRT", ok2)

# ---------------------------------------------------------------- S3
log("S3 mang (vong lap + do thi chuan)")
rc, out = sh(f"python3 {E}/python/lay_mang.py onnx {NET} --rel {REL_NN} --fp16", timeout=900, show=False, tail=3)
ok3 = os.path.exists(NET) and os.path.getsize(NET) > 0
stage(f"S3a gen{GEN}.onnx (vong lap, FP16 gop)", ok3)
PLAIN_PY = f'''
import sys, os, torch
sys.path.insert(0, "{E}/python")
import lay_mang as L
from model import FairyNet
from train import export_onnx
pt = "{C}/gen{GEN}.pt"
if not (os.path.isfile(pt) and os.path.getsize(pt) > 0):
    assert L.lay_pt(pt, "{REL_NN}") == 0, "khong lay duoc .pt"
sd = torch.load(pt, map_location="cpu")
d, t, h = L.suy_kien_truc(sd)
net = FairyNet(d_model=d, layers=t, heads=h); net.load_state_dict(sd); net.eval()
export_onnx(net, "{PLAIN}", fuse=False, fp16=False)
import onnx
m = onnx.load("{PLAIN}")
ops = sorted({{n.op_type + ("(" + n.domain + ")" if n.domain else "") for n in m.graph.node}})
print("PLAIN ops:", ops, "nodes", len(m.graph.node))
'''
with open(f"{C}/plain.py", "w") as f:
    f.write(PLAIN_PY)
rc, out = sh(f"cd {C} && python3 {C}/plain.py 2>&1 | grep -v -E '^\\[torch.onnx\\]' | tail -n 8", timeout=600)
ok3b = os.path.exists(PLAIN) and os.path.getsize(PLAIN) > 0
stage(f"S3b gen{GEN}_plain.onnx (FP32, khong gop)", ok3b)

# ---------------------------------------------------------------- S4
log("S4 TensorRT 10.x")
ok4 = False
for ver in ("10.4.0", "10.5.0", "10.3.0"):
    rc, out = sh(f"rm -rf {TRT_DIR}; pip install -q --no-deps --target {TRT_DIR} --extra-index-url https://pypi.nvidia.com "
                 f"tensorrt-cu12-libs=={ver} 2>&1 | tail -n 3", timeout=300)
    if os.path.exists(f"{TRT_DIR}/tensorrt_libs/libnvinfer.so.10"):
        SAVE["trt_ver"] = ver
        ok4 = True
        break
stage("S4 libnvinfer.so.10", ok4, SAVE.get("trt_ver", ""))

RUN = f"bash {E}/run.sh"


def bench_nn(weights, provider, extra=""):
    ld = ld_extra()
    rc, out = sh(f"export LD_LIBRARY_PATH={ld}; cd {C} && {RUN} --bench-nn --weights {weights} --provider {provider} "
                 f"--fixed-batch 64 {extra}", timeout=1500, show=False, tail=14)
    r = {"no_graph": "No graph will run on TensorRT" in out}
    m = re.search(r"^FZ_B3 64 ([\d.]+)", out, re.M)
    r["ms64"] = float(m.group(1)) if m else None
    m = re.search(r"^FZ_TRT_SPEED ([\d.]+) ([\d.]+)", out, re.M)
    r["speed"] = (float(m.group(1)), float(m.group(2))) if m else None
    m = re.search(r"^FZ_TRT_DIFF ([\d.]+) ([\d.]+)", out, re.M)
    r["diff"] = (float(m.group(1)), float(m.group(2))) if m else None
    errs = [l.strip()[:200] for l in out.splitlines() if ("TensorRT EP" in l or "ERROR" in l or "rror" in l)][:6]
    r["errs"] = errs
    return r


def trt_opts(cache, level=None):
    s = (f"--trt-opt trt_fp16_enable=1 --trt-opt trt_engine_cache_path={cache} --trt-opt trt_timing_cache_path={cache}")
    if level:
        s += f" --trt-opt trt_builder_optimization_level={level}"
    return s


# ---------------------------------------------------------------- S5
log("S5 --bench-nn lo 64")
base = t1 = t5 = None
if ONLY_SP:
    log("S5 bo qua (ONLY_SP)")
if ok2 and ok3 and not ONLY_SP:
    base = bench_nn(NET, "cuda")
    stage("S5a CUDA EP, mang vong lap (FP16 gop)", base["ms64"] is not None,
          f"{base['ms64']:.2f} ms/lo = {64000 / base['ms64']:.0f} eval/s" if base["ms64"] else "")
if ok2 and ok3b and ok4 and not ONLY_SP:
    t0 = time.time()
    t1 = bench_nn(PLAIN, "tensorrt", trt_opts(f"{C}/trt_cache1"))
    good = t1["speed"] is not None and not t1["no_graph"]
    stage("S5b TensorRT FP16 tren do thi chuan", good,
          (f"CUDA FP32 {t1['speed'][0]:.2f} ms vs TensorRT {t1['speed'][1]:.2f} ms/lo = {64000 / t1['speed'][1]:.0f} eval/s; "
           f"max|diff| {t1['diff']}; tong {time.time() - t0:.0f}s") if t1["speed"] else f"loi: {t1['errs']}")
    if t1["no_graph"]:
        print("   -> TensorRT KHONG nhan phan nao cua do thi:", t1["errs"], flush=True)
    if good and t1["speed"][1] < 0.95 * (base["ms64"] if base and base["ms64"] else 1e9):
        t0 = time.time()
        t5 = bench_nn(PLAIN, "tensorrt", trt_opts(f"{C}/trt_cache5", level=5))
        stage("S5c TensorRT FP16, builder_optimization_level=5", t5["speed"] is not None and not t5["no_graph"],
              (f"{t5['speed'][1]:.2f} ms/lo = {64000 / t5['speed'][1]:.0f} eval/s; max|diff| {t5['diff']}; tong {time.time() - t0:.0f}s")
              if t5["speed"] else f"loi: {t5['errs']}")

best_ms = None
for t in (t1, t5):
    if t and t["speed"] and not t["no_graph"]:
        best_ms = t["speed"][1] if best_ms is None else min(best_ms, t["speed"][1])
SAVE["base"], SAVE["t1"], SAVE["t5"] = base, t1, t5
if ONLY_SP:
    best_ms = 1.0      # de S7 chay TensorRT

# ---------------------------------------------------------------- S6
PAR = r'''
import sys, time
import numpy as np
sys.path.insert(0, "%(E)s/python")
import train as T
import onnxruntime as ort
print("ORT", ort.__version__, ort.get_available_providers(), flush=True)
def run(path, prov, x):
    s = ort.InferenceSession(path, providers=prov)
    return s, s.run(None, {s.get_inputs()[0].name: x})
ok = True
for seed in (1, 7, 23):
    x = T.check_inputs(64, seed=seed)
    _, ref = run("%(NET)s", ["CUDAExecutionProvider"], x)
    s, out = run("%(PLAIN)s", [("TensorrtExecutionProvider", {"trt_fp16_enable": True, "trt_engine_cache_enable": True,
                 "trt_engine_cache_path": "%(C)s/trt_cache_py", "trt_timing_cache_enable": True,
                 "trt_timing_cache_path": "%(C)s/trt_cache_py"}), "CUDAExecutionProvider"], x)
    d = T.fp16_differences(ref, out)
    print("seed", seed, "providers", s.get_providers()[:2], "DIFF TV/WDL/mlh", d, "tol", T.FP16_TOLERANCE, flush=True)
    ok = ok and d is not None and all(a <= b for a, b in zip(d, T.FP16_TOLERANCE))
print("PAR_RESULT", "PASS" if ok else "FAIL")
''' % {"E": E, "NET": NET, "PLAIN": PLAIN, "C": C}

if best_ms is not None and base and base["ms64"] and best_ms <= base["ms64"] / 1.15:
    log("S6 do khop (TensorRT nhanh hon >= 15%)")
    with open(f"{C}/par.py", "w") as f:
        f.write(PAR)
    sh(f"pip install -q --no-deps --target {C}/ort120 onnxruntime-gpu==1.20.2 2>&1 | tail -n 3", timeout=300)
    rc, out = sh(f"export LD_LIBRARY_PATH={ld_full()}; PYTHONPATH={C}/ort120 python3 {C}/par.py 2>&1 | tail -n 14", timeout=900)
    stage("S6 khop TensorRT vs CUDA (TV policy / WDL / mlh)", "PAR_RESULT PASS" in out)
else:
    log("S6 bo qua (TensorRT khong nhanh hon >= 15% hoac khong chay duoc)")

# ---------------------------------------------------------------- S7
BOOK = f"{C}/book_bench.txt"
sh(f"python3 {E}/python/sinh_the_khoi_dau.py --n 64 --out {BOOK}", timeout=60)


def selfplay(weights, provider, extra=""):
    ld = ld_extra()
    cmd = (f"export LD_LIBRARY_PATH={ld}; cd {C} && rm -rf {C}/sp_out && {RUN} --selfplay --games 64 --max-seconds 190 "
           f"--visits 800 --max-moves 400 --fast-visits 200 --fast-prob 0.5 --fast-cpuct 1.25 --fast-noise-eps 0.125 "
           f"--temperature 0.5 --start-fen {BOOK} --parallel 16 --provider {provider} --fixed-batch 64 --batch-aggregate "
           f"--noise-alpha 0.15 --show-nps --search-opt max-prefetch=0 --search-opt minibatch-size=32 "
           f"--search-opt nn-cache-size=2000000 --weights {weights} --out {C}/sp_out {extra}")
    rc, out = sh(cmd, timeout=900, show=False)
    rows = []
    if not re.search(r"\[nhip\]", out):
        print(f"[selfplay {provider}] khong co dong [nhip]; ma thoat {rc}; 40 dong cuoi:", flush=True)
        print("".join(out.splitlines(True)[-40:]), flush=True)
    for line in out.splitlines():
        if "[nhip]" in line or "NN eval/playout" in line or "Finished" in line or "No graph will run" in line:
            print(line, flush=True)
        m = re.search(r"\[nhip\] t=(\d+)s\s+(\d+) van dang chay\s+(\d+) nps\s+(\d+) eval/s\s+batch TB ([\d.]+)\s+pad ([\d.]+)%"
                      r"\s+GPU ban ([\d.]+)%.*Run TB ([\d.]+) ms", line)
        if m:
            rows.append(tuple(float(v) for v in m.groups()))
    return rows, "No graph will run on TensorRT" in out


log("S7 tu dau so sanh")
res = {}
if ok2 and ok3 and not ONLY_SP:
    res["cuda (mang vong lap)"] = selfplay(NET, "cuda")
if ok2 and ok3b and ok4 and best_ms is not None:
    res["tensorrt (do thi chuan, FP16)"] = selfplay(PLAIN, "tensorrt", trt_opts(f"{C}/trt_cache1"))


def avg(rows):
    use = [r for r in rows if r[0] >= 120 and r[1] >= 12] or rows[-2:]
    if not use:
        return None
    n = len(use)
    return tuple(sum(r[i] for r in use) / n for i in range(2, 8))   # nps, eval/s, batch TB, pad, GPU ban, Run TB


log("=== TOM TAT ===")
print("TensorRT libs:", SAVE.get("trt_ver"))
if base and base["ms64"]:
    print(f"bench-nn lo 64, CUDA EP mang vong lap: {base['ms64']:.2f} ms = {64000 / base['ms64']:.0f} eval/s")
for nm, t in (("TensorRT FP16 (level mac dinh)", t1), ("TensorRT FP16 (level 5)", t5)):
    if t:
        print(f"bench-nn lo 64, {nm}:",
              "KHONG nhan do thi" if t["no_graph"] else
              ("khong co so do" if not t["speed"] else
               f"{t['speed'][1]:.2f} ms = {64000 / t['speed'][1]:.0f} eval/s (CUDA FP32 cung do thi: {t['speed'][0]:.2f} ms), max|diff| {t['diff']}"))
for k, (rows, ng) in res.items():
    a = avg(rows)
    print(f"tu dau {k}: nhip={len(rows)}", "[TensorRT khong nhan do thi]" if ng else "", "->",
          "khong co so do" if a is None else
          f"{a[0]:.0f} nps, {a[1]:.0f} eval/s, lo TB {a[2]:.1f}, pad {a[3]:.1f}%, GPU ban {a[4]:.1f}%, Run TB {a[5]:.2f} ms, eval/playout {a[1] / a[0]:.3f}")
for name, ok, note in SAVE.get("stages", []):
    print(f"  {'PASS' if ok else 'FAIL'}  {name} {note}")
log("xong")
