
# ----------------------------------------------------------------------------------------------------------
# One-shot benchmark of the FairyZero transformer on a Colab GPU (FP32). Runs on the VM via `colab run`.
# Measures: (A) the dynamo ONNX export on THIS torch, (B) .pt -> .onnx conversion time (lay_mang.py),
# (C) training step speed and memory by batch size (FP32; FP16 only as a reference),
# (D) inference speed with ONNX Runtime CUDA by batch size (FP32; FP16 only as a reference).
# ----------------------------------------------------------------------------------------------------------
import base64
import io
import os
import subprocess
import sys
import time
import zipfile

os.makedirs("/content/fzpy", exist_ok=True)
zipfile.ZipFile(io.BytesIO(base64.b64decode(ZIP_B64))).extractall("/content/fzpy")
sys.path.insert(0, "/content/fzpy")
os.chdir("/content/fzpy")


def sh(cmd, quiet=False):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if not quiet:
        print(r.stdout.strip()[-1500:], r.stderr.strip()[-600:], flush=True)
    return r


print("=== machine", flush=True)
sh("nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader")
t0 = time.time()
sh("pip install -q onnx onnxscript onnxruntime-gpu 2>&1 | tail -3")
print(f"pip install onnx onnxscript onnxruntime-gpu: {time.time() - t0:.0f} s", flush=True)

import numpy as np  # noqa: E402
import torch  # noqa: E402

print("torch", torch.__version__, "cuda", torch.version.cuda, "| device", torch.cuda.get_device_name(0), flush=True)
import onnxruntime as ort  # noqa: E402

print("onnxruntime", ort.__version__, ort.get_available_providers(), flush=True)

from model import FairyNet, ExportNet, NUM_PLANES, POLICY_SIZE  # noqa: E402
import train as T  # noqa: E402

net = FairyNet().eval()
print("params %.2fM" % (sum(p.numel() for p in net.parameters()) / 1e6), flush=True)

print("\n=== (A) dynamo ONNX export on this torch", flush=True)
t = time.time()
try:
    T.export_onnx(net, "/content/g0.onnx")
    print(f"export_onnx: {time.time() - t:.1f} s; file {os.path.getsize('/content/g0.onnx') / 2**20:.1f} MB; "
          f".data exists: {os.path.exists('/content/g0.onnx.data')}", flush=True)
    T.verify_onnx("/content/g0.onnx", net)
except Exception as e:  # noqa: BLE001
    print("EXPORT FAILED:", type(e).__name__, str(e)[:400], flush=True)

print("\n=== (B) .pt -> .onnx conversion in a fresh process (what lay_mang.py does on every machine, every generation)", flush=True)
torch.save(net.state_dict(), "/content/gen5.pt")
t = time.time()
r = sh("python /content/fzpy/lay_mang.py onnx /content/gen5.onnx --rel http://127.0.0.1:1 2>&1 | tail -4", quiet=True)
print(f"lay_mang.py onnx (pt already local): {time.time() - t:.1f} s total, exit {r.returncode}", flush=True)
print(r.stdout.strip()[-500:], flush=True)

print("\n=== (C) training step, FP32 (batch: ms/step, positions/s, peak GPU memory)", flush=True)


def bench_train(batch, amp, steps=15, warm=4):
    torch.manual_seed(0)
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    m = FairyNet().cuda().train()
    opt = torch.optim.AdamW(m.parameters(), lr=1e-3, weight_decay=1e-4)
    scaler = torch.amp.GradScaler("cuda", enabled=amp)
    x = (torch.rand(batch, NUM_PLANES, 10, 10, device="cuda") < 0.08).float()
    pi = torch.full((batch, POLICY_SIZE), -1.0, device="cuda")
    pi.scatter_(1, torch.randint(0, POLICY_SIZE, (batch, 30), device="cuda"), 1.0 / 30)
    val = torch.cat([torch.softmax(torch.randn(batch, 3, device="cuda"), 1),
                     torch.randint(1, 200, (batch, 1), device="cuda").float(),
                     (torch.rand(batch, 1, device="cuda") < 0.5).float()], 1)

    def step():
        with torch.autocast("cuda", enabled=amp):
            lp, lv, lm = T.compute_losses(m(x), pi, val)
            loss = lp + lv + lm
        scaler.scale(loss).backward()
        scaler.step(opt)
        scaler.update()
        opt.zero_grad(set_to_none=True)

    for _ in range(warm):
        step()
    torch.cuda.synchronize()
    t = time.time()
    for _ in range(steps):
        step()
    torch.cuda.synchronize()
    dt = (time.time() - t) / steps
    return dt, torch.cuda.max_memory_allocated() / 2**30


for amp in (False, True):
    for batch in (128, 256, 512, 1024):
        try:
            dt, mem = bench_train(batch, amp)
            print(f"  {'FP16 AMP (reference)' if amp else 'FP32'} batch {batch:5d}: {dt * 1000:7.0f} ms/step, "
                  f"{batch / dt:7.0f} positions/s, peak {mem:5.1f} GB", flush=True)
        except torch.cuda.OutOfMemoryError:
            print(f"  {'FP16 AMP (reference)' if amp else 'FP32'} batch {batch:5d}: OUT OF GPU MEMORY", flush=True)
            torch.cuda.empty_cache()
        except Exception as e:  # noqa: BLE001
            print(f"  batch {batch}: {type(e).__name__}: {str(e)[:200]}", flush=True)

print("\n=== (D) inference with ONNX Runtime CUDA (what the engine's self-play does): batch -> ms/batch, positions/s", flush=True)


def bench_ort(path, label, batches=(16, 32, 48, 64), n=40):
    try:
        sess = ort.InferenceSession(path, providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
    except Exception as e:  # noqa: BLE001
        print(f"  {label}: cannot load: {type(e).__name__}: {str(e)[:200]}", flush=True)
        return
    print(f"  {label}: providers in use {sess.get_providers()}", flush=True)
    for b in batches:
        x = (np.random.default_rng(0).random((b, NUM_PLANES, 10, 10)) < 0.08).astype(np.float32)
        for _ in range(6):
            sess.run(None, {"input": x})
        t = time.time()
        for _ in range(n):
            sess.run(None, {"input": x})
        dt = (time.time() - t) / n
        print(f"    batch {b:3d}: {dt * 1000:7.2f} ms/batch  {b / dt:8.0f} positions/s", flush=True)


bench_ort("/content/g0.onnx", "FP32 (the decision)")
try:
    import onnx
    from onnxruntime.transformers.float16 import convert_float_to_float16
    m16 = convert_float_to_float16(onnx.load("/content/g0.onnx"), keep_io_types=True,
                                   op_block_list=["Softmax", "LayerNormalization"])
    onnx.save(m16, "/content/g0_fp16.onnx")
    bench_ort("/content/g0_fp16.onnx", "FP16 (reference only)")
except Exception as e:  # noqa: BLE001
    print("  FP16 reference skipped:", type(e).__name__, str(e)[:200], flush=True)
print("\n=== done", flush=True)
