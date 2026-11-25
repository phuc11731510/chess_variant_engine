# -*- coding: utf-8 -*-
"""thu_lr_t4.py -- thu tren T4: tốc độ học của mỗi lần huấn luyện (ô 07) có làm CHÍNH SÁCH tệ đi không?

Nhật ký 10 lần huấn luyện thật (đời 62 đến 105): CE chính sách KHÔNG giảm trong một vòng (tăng 0,004 đến 0,023 từ 20 bước đầu tới
20 bước cuối) trong khi CE giá trị giảm 0,40 -> 0,30; CE chính sách 3,3 so với entropy mục tiêu 2,35 (KL ~1 nat): mạng còn xa mục tiêu.
Thử: cùng mạng xuất phát (gen103), cùng dữ liệu, cùng thứ tự (--seed 1), chỉ đổi tốc độ học; chấm mạng xuất ra (SWA) trên ván
ĐỜI 104 (mạng chưa thấy, ngoài cửa sổ huấn luyện).
  A  = ô 07 như thật: lr 1e-3 hằng số;  B = lr 3e-4;  C = lr 1e-3 giảm từng bậc (5 bậc);  D = lr 1e-4.
Chạy: python3 ~/chay_t4_thu.py thu_lr_t4.py --can-phut 55 --timeout 3300 --tep /tmp/lr_data.tar:/content/lr_data.tar
(lr_data.tar: dtrain/*.zip = cửa sổ huấn luyện ~400k thế của mạng 101-103; dval/*.zip = ván đời 104)
"""
import os
import re
import subprocess
import time

REPO = "https://github.com/phuc11731510/chess_variant_engine"
REL_NN = REPO + "/releases/download/NN_Model"
C = "/content"
E = f"{C}/chess_variant_engine/custom_engine"
T0 = time.time()
START = 103


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
rc, out = sh(f"cd {C} && rm -rf dtrain dval && tar xf lr_data.tar && ls dtrain | wc -l && ls dval | wc -l")
log("du lieu:", out.replace("\n", " "))
sh(f"python3 {E}/python/lay_mang.py pt {C}/gen{START}.pt --rel {REL_NN} 2>&1 | tail -n 1", timeout=300)
assert os.path.exists(f"{C}/gen{START}.pt"), "khong co mang xuat phat"

CFG = [
    ("A", "--lr 1e-3"),
    ("B", "--lr 3e-4"),
    ("C", "--lr 1e-3 --lr-values 1e-3,5e-4,2.5e-4,1.25e-4,6e-5 --lr-boundaries 79,158,237,316"),
    ("D", "--lr 1e-4"),
]
COMMON = (f"--data {C}/dtrain --init-from {C}/gen{START}.pt --epochs 1 --swa-tail 10 --swa-tail-every 20 --val-frac 0 "
          f"--batch 512 --accum-steps 2 --q-ratio 0.25 --weight-decay 1e-4 --report-every 20 --amp --grad-clip 10 --seed 1")
DRIFT = {}
for ten, lr in CFG:
    t = time.time()
    rc, out = sh(f"python3 {E}/python/train.py {COMMON} {lr} --out {C}/lr_{ten}.pt 2>&1", timeout=1500)
    open(f"{C}/lr_{ten}.log", "w").write(out)
    p, prev = [], None
    for l in out.splitlines():
        m = re.search(r"step\s+(\d+): policy_loss=([\d.]+)\s+value_loss=([\d.]+)", l)
        if m:
            k = int(m.group(1)) // 20
            M = float(m.group(2))
            p.append(M if prev is None else k * M - (k - 1) * prev)
            prev = M
    if len(p) >= 8:
        DRIFT[ten] = (sum(p[:3]) / 3, sum(p[-3:]) / 3)
    log(f"huan luyen {ten} ({lr}): rc={rc}, {time.time() - t:.0f}s, buoc cuoi:",
        [l for l in out.splitlines() if "step" in l and "policy_loss" in l][-1:] or out[-300:])

EVAL = f"""
import sys, torch
sys.path.insert(0, "{E}/python")
from torch.utils.data import DataLoader
from train import evaluate
from model import FairyNet
from dataset import FairyDataset, collate_packed
dev = "cuda"
ds = FairyDataset("{C}/dval", q_ratio=0.25, cache=True, sparse=True, packed=True, label="dval")
dl = DataLoader(ds, batch_size=512, shuffle=False, num_workers=2, collate_fn=collate_packed)
for ten, pt in [("xuat phat gen{START}", "{C}/gen{START}.pt")] + [(t, "{C}/lr_" + t + ".pt") for t in "ABCD"]:
    net = FairyNet(); net.load_state_dict(torch.load(pt, map_location="cpu")); net.to(dev)
    p, v, m = evaluate(net, dl, dev, True, False)
    print(f"EVAL {{ten:<18}} chinh sach {{p:.4f}}  gia tri {{v:.4f}}  mlh {{m:.4f}}", flush=True)
"""
open(f"{C}/eval_lr.py", "w").write(EVAL)
rc, out = sh(f"python3 {C}/eval_lr.py 2>&1", timeout=1200)
print("\n".join(l for l in out.splitlines() if l.startswith("EVAL") or "dataset" in l or "Error" in l or "Traceback" in l), flush=True)
log("troi CE chinh sach trong vong (3 cua so dau -> 3 cua so cuoi):",
    {k: f"{a:.4f}->{b:.4f}" for k, (a, b) in DRIFT.items()})
