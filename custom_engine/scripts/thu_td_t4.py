# -*- coding: utf-8 -*-
"""Thu tren T4 (chu du an 27/11): nhan gia tri 0,5 ket qua van + 0,5 TD(0,8) (--td-lambda 0.8 --td-z-weight 0.5) va lat trai-phai
(--mirror) so voi cach hien tai. Cung mang xuat phat gen184, cung du lieu = dung cua so gen185 da hoc (goi 2714-2795: 82 goi, 4108 van,
628932 the), cung thu tu (--seed 12345), cai dat o 07 (lr 5e-4, khoi dong 50, wd 1e-2, --value-per-game 21, SWA duoi 10 x 20, lo 512 x 2,
AMP, cat 10). Bon ban: goc = --q-ratio 0.2 (nhu o 07) | TD = --td-lambda 0.8 --td-z-weight 0.5 | q05 = --q-ratio 0.5 | TDlat = TD + --mirror.
Cham moi mang (gen184 xuat phat, gen185 that, 4 ban): CE chinh sach / gia tri (so voi KET QUA VAN va so voi qMix 0,2) / mlh tren moi/ = 12 goi
n185 (khong mang nao hoc); ti le doan dung ben thang 6 giai doan tren moi/ va hoc1/ (5 goi moi nhat cua cua so: hoc thuoc sau 1 luot);
|q - q lat trai-phai| tren moi/.
Chay: python3 ~/chay_t4_thu.py thu_td_t4.py --can-phut 75 --timeout 4500 --tep p_hoc_aa.tar:/content/p_hoc_aa.tar --tep p_hoc_ab.tar:/content/p_hoc_ab.tar
      --tep p_hoc_ac.tar:/content/p_hoc_ac.tar --tep p_kiem.tar:/content/p_kiem.tar
"""
import os
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
assert "--td-lambda" in open(f"{E}/python/train.py", encoding="utf-8").read(), "train.py chua co --td-lambda"
rc, out = sh(f"cd {C} && rm -rf hoc moi hoc1 && cat p_hoc_aa.tar p_hoc_ab.tar p_hoc_ac.tar | tar xf - && tar xf p_kiem.tar "
             f"&& echo hoc $(ls hoc | wc -l) moi $(ls moi | wc -l) hoc1 $(ls hoc1 | wc -l)")
log("du lieu:", out.strip())
for g in (184, 185):
    sh(f"python3 {E}/python/lay_mang.py pt {C}/gen{g}.pt --rel {REL_NN} 2>&1 | tail -n 1", timeout=300)
    assert os.path.exists(f"{C}/gen{g}.pt"), f"khong co gen{g}.pt"

EVAL = f"""
import os, sys, numpy as np, torch
sys.path.insert(0, "{E}/python")
LITE = bool(os.environ.get("LITE"))
from torch.utils.data import DataLoader
from train import evaluate
from model import FairyNet
from dataset import FairyDataset, collate_packed, list_games
import trainingdata_reader as tdr
dev = "cuda"
NETS = [("gen184 xuat phat", "{C}/gen184.pt"), ("gen185 that", "{C}/gen185.pt")] + [(t, "{C}/r_" + t + ".pt") for t in ("goc", "TD", "q05", "TDlat")]
NETS = [(t, p) for t, p in NETS if os.path.exists(p)]
if LITE: NETS = NETS[:2]
MOI, HOC1 = ("{C}/moi_lite", "{C}/hoc1_lite") if LITE else ("{C}/moi", "{C}/hoc1")
nets = []
for ten, pt in NETS:
    n = FairyNet(); n.load_state_dict(torch.load(pt, map_location="cpu")); n.to(dev).eval(); nets.append((ten, n))
dls = [DataLoader(FairyDataset(MOI, q_ratio=qr, cache=True, sparse=True, packed=True, label=f"moi n185 q_ratio {{qr}}"),
                 batch_size=512, shuffle=False, num_workers=2, collate_fn=collate_packed) for qr in (0.0, 0.2)]
for ten, n in nets:
    p, v0, m = evaluate(n, dls[0], dev, True, False)
    _, v2, _ = evaluate(n, dls[1], dev, True, False)
    print(f"CE {{ten:<17}} chinh sach {{p:.4f}}  gia tri/ket qua {{v0:.4f}}  gia tri/qMix0.2 {{v2:.4f}}  mlh {{m:.4f}}", flush=True)
def dau(thu_muc, nhan):
    k_, L_, kq, Q, QM = [], [], [], [[] for _ in nets], [[] for _ in nets]
    buf = []
    def xa():
        if not buf: return
        X = torch.from_numpy(np.stack(buf).astype(np.float32)).to(dev)
        with torch.no_grad(), torch.autocast(device_type=dev):
            for i, (_, n) in enumerate(nets):
                s = torch.softmax(n(X)[1].float(), 1); Q[i] += (s[:, 0] - s[:, 2]).cpu().tolist()
                s = torch.softmax(n(X.flip(-1))[1].float(), 1); QM[i] += (s[:, 0] - s[:, 2]).cpu().tolist()
        buf.clear()
    for g in list_games(thu_muc):
        recs = list(tdr.iter_games([g], sparse=True))
        if recs[0]["result_d"] > 0.5: continue
        for k, r in enumerate(recs):
            buf.append(tdr.reconstruct_planes(r)); k_.append(k); L_.append(len(recs)); kq.append(r["result_q"])
            if len(buf) >= 2048: xa()
    xa()
    k_, L_, kq = np.array(k_), np.array(L_), np.array(kq)
    gd = np.minimum(6 * k_ // L_, 5)
    for i, (ten, _) in enumerate(nets):
        d = np.sign(np.array(Q[i])) == np.sign(kq)
        print(f"DUNG {{nhan}} {{ten:<17}} " + " | ".join(f"{{j+1}}: {{d[gd == j].mean()*100:5.1f}}%" for j in range(6))
              + f" | nua nuoc 1: {{d[k_ == 0].mean()*100:5.1f}}% | tong {{d.mean()*100:5.1f}}%"
              + f" | |q - q lat| tb {{np.abs(np.array(Q[i]) - np.array(QM[i])).mean():.3f}}", flush=True)
dau(MOI, "n185 chua hoc")
dau(HOC1, "hoc 1 luot     ")
"""


def cham(lite):
    rc, out = sh(f"{'LITE=1 ' if lite else ''}python3 {C}/eval_k.py 2>&1", timeout=1800)
    print("\n".join(l for l in out.splitlines() if l.startswith(("CE ", "DUNG", "[dataset]")) or "Error" in l or "Traceback" in l
                    or "line " in l), flush=True)
    return rc


open(f"{C}/eval_k.py", "w").write(EVAL)
sh(f"mkdir -p {C}/moi_lite {C}/hoc1_lite && cp $(ls {C}/moi/*.zip | head -n 1) {C}/moi_lite/ && cp $(ls {C}/hoc1/*.zip | head -n 1) {C}/hoc1_lite/")
log("chay thu phan cham (1 goi, 2 mang) truoc khi huan luyen")
assert cham(True) == 0, "phan cham loi -- dung truoc khi ton thoi gian huan luyen"
COMMON = (f"--data {C}/hoc --init-from {C}/gen184.pt --epochs 1 --swa-tail 10 --swa-tail-every 20 --val-frac 0 --batch 512 --accum-steps 2 "
          f"--lr 5e-4 --warmup-steps 50 --weight-decay 1e-2 --value-per-game 21 --report-every 100 --amp --grad-clip 10 --seed 12345")
CFG = [("goc", "--q-ratio 0.2"), ("TD", "--q-ratio 0.2 --td-lambda 0.8 --td-z-weight 0.5"), ("q05", "--q-ratio 0.5"),
       ("TDlat", "--q-ratio 0.2 --td-lambda 0.8 --td-z-weight 0.5 --mirror")]
for k, opt in CFG:
    t = time.time()
    rc, out = sh(f"python3 {E}/python/train.py {COMMON} {opt} --out {C}/r_{k}.pt 2>&1", timeout=1500)
    buoc = [l.strip() for l in out.splitlines() if "step" in l and "policy_loss" in l]
    log(f"huan luyen {k} ({opt}): rc={rc}, {time.time() - t:.0f}s;", (buoc[:1] + buoc[-1:]) if buoc else out[-600:],
        [l.strip() for l in out.splitlines() if l.startswith("[dataset]")][:1])
log("cham day du")
cham(False)
log("XONG")
