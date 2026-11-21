# -*- coding: utf-8 -*-
"""bench_tai_xuong_t4.py -- do dung luong TAI XUONG cua o 02 moi (clone thua, giu ORT + binary giua cac doi) va
bang thoi gian theo loai phep toan cua mang (ORT --ort-profile) de dinh huong tu viet toi uu.

  P2  o 02 lan dau tren may moi (gen16)            -> RX (MB) va thoi gian
  P3  o 02 lan hai, sang doi ke tiep (gen17)       -> RX (MB): ky vong ~ gen17.pt (20,3 MB) + vai tram KB
  P4  bench-nn --ort-profile tren gen17.onnx      -> tong thoi gian moi lo theo op_name (MatMul, Transpose, ...)
Nhanh git thu: BR (xoa sau khi thu xong); o 02 that chay tu `main`.
"""
import glob
import json
import os
import re
import subprocess
import sys
import time
from collections import defaultdict

BR = "thu-tai-xuong"
REPO_RAW = "https://raw.githubusercontent.com/phuc11731510/chess_variant_engine"
C = "/content"
T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:6.0f}s]", *a, flush=True)


def rx_mb():
    tot = 0
    for ln in open("/proc/net/dev").read().splitlines()[2:]:
        name, rest = ln.split(":", 1)
        if name.strip() == "lo":
            continue
        tot += int(rest.split()[0])
    return tot / 1048576


def sh(cmd, timeout=900):
    p = subprocess.run(["bash", "-c", f"timeout -k 5 {timeout} bash -c {shq(cmd)}"], capture_output=True, text=True, errors="replace")
    return p.returncode, p.stdout + p.stderr


def shq(s):
    return "'" + s.replace("'", "'\"'\"'") + "'"


def translate(src):
    out = []
    for line in src.splitlines():
        s = line.lstrip()
        ind = line[:len(line) - len(s)]
        if s.startswith("%cd "):
            out.append(f"{ind}os.chdir({s[4:].strip()!r})")
        elif s.startswith("!"):
            out.append(f"{ind}os.system(f{s[1:]!r})")
        else:
            out.append(line)
    return "import os\n" + "\n".join(out) + "\n"


def fetch(path):
    rc, out = sh(f"curl -fsSL {REPO_RAW}/{BR}/custom_engine/scripts/colab_cells/{path}")
    assert rc == 0, f"khong lay duoc {path}: {out[:200]}"
    return out


CELL00 = fetch("00_cau_hinh.py")
CELL02 = fetch("02_khoi_dong.py").replace("-b main", f"-b {BR}").replace("origin main", f"origin {BR}")
G = {}


def run_cell02(gen):
    exec(translate(CELL00.replace("GEN_CURRENT = 0", f"GEN_CURRENT = {gen}")), G)
    r0, t0 = rx_mb(), time.time()
    exec(translate(CELL02), G)
    return rx_mb() - r0, time.time() - t0


log("P2 o 02 lan dau (may moi), gen16")
d2, t2 = run_cell02(16)
log(f"== P2: tai {d2:.1f} MB, {t2:.0f}s")
sh_out = sh("cd /content/chess_variant_engine && du -sh . .git custom_engine 2>/dev/null; git sparse-checkout list; ls custom_engine | head -n 12; "
            "ls -la custom_engine/build-linux/custom_engine custom_engine/build-linux/custom_engine.id; cat custom_engine/build-linux/custom_engine.id; "
            "ls custom_engine/third_party")[1]
print(sh_out, flush=True)

log("P3 o 02 lan hai tren CUNG may, gen17 (sang doi ke tiep)")
d3, t3 = run_cell02(17)
log(f"== P3: tai {d3:.1f} MB, {t3:.0f}s")
print(sh("ls -la /content/gen1*.onnx /content/gen1*.pt")[1], flush=True)

log("P4 ORT profile gen17.onnx (cuda, lo 64)")
rc, out = sh(f"cd {C} && bash {C}/chess_variant_engine/custom_engine/run.sh --bench-nn --weights {C}/gen17.onnx --provider cuda "
             f"--fixed-batch 64 --ort-profile {C}/ortprof", timeout=900)
m = re.search(r"^FZ_PROFILE (\S+)", out, re.M)
ms = re.search(r"ORT profile \(fixed_batch=64, ([\d.]+) ms/Run\)", out)
if m and os.path.exists(m.group(1)):
    ev = json.load(open(m.group(1)))
    per_op = defaultdict(lambda: [0.0, 0])
    nruns = 0
    for e in ev:
        if e.get("cat") == "Node" and e.get("name", "").endswith("_kernel_time"):
            op = e.get("args", {}).get("op_name", "?")
            per_op[op][0] += e["dur"]
            per_op[op][1] += 1
        if e.get("cat") == "Session" and e.get("name") == "model_run":
            nruns += 1
    tot = sum(v[0] for v in per_op.values()) or 1
    print(f"ORT profile: {nruns} lan chay, {ms.group(1) if ms else '?'} ms/Run do ngoai; tong thoi gian nut {tot / max(nruns, 1) / 1000:.2f} ms/lo", flush=True)
    print(f"{'op':28s} {'ms/lo':>8s} {'%':>6s} {'so nut/lo':>9s}", flush=True)
    for op, (us, n) in sorted(per_op.items(), key=lambda kv: -kv[1][0]):
        print(f"{op:28s} {us / max(nruns, 1) / 1000:8.3f} {100 * us / tot:6.1f} {n / max(nruns, 1):9.1f}", flush=True)
else:
    print("khong co FZ_PROFILE; dau ra cuoi:\n" + out[-1500:], flush=True)

log("=== TOM TAT ===")
print(f"o 02 lan dau (may moi, gen16): {d2:.1f} MB, {t2:.0f}s")
print(f"o 02 sang doi ke (cung may, gen17): {d3:.1f} MB, {t3:.0f}s")
log("xong")
