# -*- coding: utf-8 -*-
"""thu_hoc_thuoc_t4.py -- thu tren T4: dau gia tri HOC THUOC van (2026-11-26: gen139 doan dung ket qua 100% ngay o nua nuoc 1 cua van da hoc,
51,7% tren van moi; moi van mot the khoi dau ngau nhien). Weight decay lon hon (E) hay chi hoc gia tri tren 16 the moi van (B) co bot hoc thuoc
ma khong lam gia tri / chinh sach ngoai mau te di khong?

Cung mang xuat phat gen138, cung du lieu (hoc/ = goi n135..n138 ~636k the, cua so gen139 da hoc), cung thu tu (--seed 12345), cai dat o 07
(lr 5e-4, khoi dong 50, q_ratio 0,2, SWA duoi 10 x 20, lo 512 x 2, AMP, cat 10), chi doi:
  goc    = nhu o 07 (weight decay 1e-4)      E1 = weight decay 1e-2      E2 = weight decay 5e-2      B16 = --value-per-game 16
Cham (moi mang, ca gen138 xuat phat va gen139 that): (1) CE chinh sach / gia tri / mlh tren kiem/ = 19 goi van n139 (KHONG mang nao hoc);
(2) ti le doan dung ben thang theo giai doan van tren kiem/ (ngoai mau) va tren 6 goi n138 trong hoc/ (da hoc: do hoc thuoc).
Chay: python3 ~/chay_t4_thu.py thu_hoc_thuoc_t4.py --can-phut 70 --timeout 3900 --tep p_ds_aa.tar:/content/p_ds_aa.tar
      --tep p_ds_ab.tar:/content/p_ds_ab.tar --tep p_ds_ac.tar:/content/p_ds_ac.tar --tep p_kiem.tar:/content/p_kiem.tar
"""
import os
import re
import subprocess
import time

BRANCH = "luat-moi"
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
sh(f"cd {C} && rm -rf chess_variant_engine && timeout 150 git clone -q --depth 1 --filter=blob:none --sparse -b {BRANCH} {REPO}.git "
   f"chess_variant_engine && cd chess_variant_engine && git sparse-checkout set custom_engine", timeout=250)
assert "--value-per-game" in open(f"{E}/python/train.py", encoding="utf-8").read(), "train.py chua co --value-per-game"
rc, out = sh(f"cd {C} && rm -rf hoc kiem && for t in p_ds_aa p_ds_ab p_ds_ac p_kiem; do tar xf $t.tar; done && ls hoc | wc -l && ls kiem | wc -l")
log("du lieu (goi hoc / goi kiem):", out.replace("\n", " "))
for g in (138, 139):
    sh(f"python3 {E}/python/lay_mang.py pt {C}/gen{g}.pt --rel {REL_NN} 2>&1 | tail -n 1", timeout=300)
    assert os.path.exists(f"{C}/gen{g}.pt"), f"khong co gen{g}.pt"
# 6 goi n138 moi nhat trong hoc/ = tap "da hoc" de do hoc thuoc
sh(f"mkdir -p {C}/dahoc && cd {C}/hoc && ls | grep _n138_ | sort | tail -n 6 | xargs -I{{}} cp {{}} {C}/dahoc/")
sh(f"mkdir -p {C}/kiem_lite {C}/dahoc_lite && cp $(ls {C}/kiem/*.zip | head -n 1) {C}/kiem_lite/ && cp $(ls {C}/dahoc/*.zip | head -n 1) {C}/dahoc_lite/")

def cham(lite):
    rc, out = sh(f"{'LITE=1 ' if lite else ''}python3 {C}/eval_ht.py 2>&1", timeout=1800)
    print("\n".join(l for l in out.splitlines() if l.startswith(("CE ", "DUNG", "[dataset]")) or "Error" in l or "Traceback" in l
                    or "line " in l), flush=True)
    return rc


EVAL = f"""
import os, sys, glob, numpy as np, torch
sys.path.insert(0, "{E}/python")
LITE = bool(os.environ.get("LITE"))
from torch.utils.data import DataLoader
from train import evaluate
from model import FairyNet
from dataset import FairyDataset, collate_packed, list_games
import trainingdata_reader as tdr
dev = "cuda"
NETS = [("gen138 xuat phat", "{C}/gen138.pt"), ("gen139 that", "{C}/gen139.pt")] + [(t, "{C}/r_" + t + ".pt") for t in ("goc", "E1", "E2", "B16")]
if LITE:
    NETS = NETS[:2]
K, DH = ("{C}/kiem_lite", "{C}/dahoc_lite") if LITE else ("{C}/kiem", "{C}/dahoc")
nets = []
for ten, pt in NETS:
    n = FairyNet(); n.load_state_dict(torch.load(pt, map_location="cpu")); n.to(dev).eval(); nets.append((ten, n))
ds = FairyDataset(K, q_ratio=0.2, cache=True, sparse=True, packed=True, label="kiem n139")
dl = DataLoader(ds, batch_size=512, shuffle=False, num_workers=2, collate_fn=collate_packed)
for ten, n in nets:
    p, v, m = evaluate(n, dl, dev, True, False)
    print(f"CE {{ten:<17}} chinh sach {{p:.4f}}  gia tri {{v:.4f}}  mlh {{m:.4f}}", flush=True)
PHA = ((1, 1), (2, 40), (41, 80), (81, 160), (161, 9999))
def dau(thu_muc, nhan):
    ply, kq, Q = [], [], [[] for _ in nets]
    buf = []
    def xa():
        if not buf: return
        X = torch.from_numpy(np.stack(buf).astype(np.float32)).to(dev)
        with torch.no_grad(), torch.autocast(device_type=dev):
            for i, (_, n) in enumerate(nets):
                s = torch.softmax(n(X)[1].float(), 1); Q[i] += (s[:, 0] - s[:, 2]).cpu().tolist()
        buf.clear()
    for g in list_games(thu_muc):
        recs = list(tdr.iter_games([g], sparse=True))
        if recs[0]["result_d"] > 0.5: continue
        for k, r in enumerate(recs):
            buf.append(tdr.reconstruct_planes(r)); ply.append(k + 1); kq.append(r["result_q"])
            if len(buf) >= 2048: xa()
    xa()
    ply, kq = np.array(ply), np.array(kq)
    for i, (ten, _) in enumerate(nets):
        d = np.sign(np.array(Q[i])) == np.sign(kq)
        print(f"DUNG {{nhan}} {{ten:<17}} tong {{d.mean()*100:5.1f}}% | " + " | ".join(f"nua nuoc {{a}}-{{b}}: {{d[(ply>=a)&(ply<=b)].mean()*100:5.1f}}%" for a, b in PHA), flush=True)
dau(K, "kiem n139 (chua hoc)")
dau(DH, "n138 da hoc       ")
"""

CFG = [("goc", "--weight-decay 1e-4"), ("E1", "--weight-decay 1e-2"), ("E2", "--weight-decay 5e-2"),
       ("B16", "--weight-decay 1e-4 --value-per-game 16")]
COMMON = (f"--data {C}/hoc --init-from {C}/gen138.pt --epochs 1 --swa-tail 10 --swa-tail-every 20 --val-frac 0 --batch 512 --accum-steps 2 "
          f"--lr 5e-4 --warmup-steps 50 --q-ratio 0.2 --report-every 100 --amp --grad-clip 10 --seed 12345")
open(f"{C}/eval_ht.py", "w").write(EVAL)
log("chay thu phan cham (1 goi, 2 mang) truoc khi huan luyen")
assert cham(True) == 0, "phan cham loi -- dung truoc khi ton thoi gian huan luyen"
for ten, opt in CFG:
    t = time.time()
    rc, out = sh(f"python3 {E}/python/train.py {COMMON} {opt} --out {C}/r_{ten}.pt 2>&1", timeout=1500)
    open(f"{C}/r_{ten}.log", "w").write(out)
    buoc = [l.strip() for l in out.splitlines() if "step" in l and "policy_loss" in l]
    log(f"huan luyen {ten} ({opt}): rc={rc}, {time.time() - t:.0f}s;", (buoc[:1] + buoc[-1:]) if buoc else out[-400:],
        [l.strip() for l in out.splitlines() if l.startswith("[dataset]")][:1])
log("cham day du")
cham(False)
log("XONG")
