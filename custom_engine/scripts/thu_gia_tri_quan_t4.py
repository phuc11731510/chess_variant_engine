# -*- coding: utf-8 -*-
"""thu_gia_tri_quan_t4.py -- mang gen100 danh gia tung LOAI QUAN bao nhieu? (hoi quy binh phuong nho nhat tren the co thuc chien)

Du lieu: 4000 van GAN NHAT trong du lieu huan luyen (dgl/*.zip trong gtq_dl.tar), moi the cua chung (~680 nghin the).
Voi moi the (goc nhin BEN DI = "ta"):
    d_i = (so quan loai i cua ta) - (so quan loai i cua dich), 11 loai (khong Hoang gia)
    e   = c_dich^0,8 - c_ta^0,8      (c = so lan chieu moi ben CON PHAI thuc hien de thang; ta can it hon dich -> e > 0 -> tot cho ta)
    y   = atanh(q), q = P(thang) - P(thua) cua mang gen100 (kep |q| <= 0,999)
Mo hinh:   y = b0 + sum_i b_i d_i + g * e + sai so,    binh phuong nho nhat dong thoi (g cung duoc uoc luong).
In: gia tri moi quan quy ra Tot (b_i / b_Tot) + sai so chuan (bootstrap 500 lan theo 200 khoi lien tiep ~ 20 van) + R^2, cho bon ban:
    V1 mang gen100, co b0 + chieu (DUNG NHU YEU CAU);  V2 nhu V1 nhung KHONG b0;  V3 nhu V1 nhung KHONG phan chieu;
    V4 nhu V1 nhung y = atanh(q tim kiem ghi trong du lieu) thay cho q cua mang.
Chay: python3 ~/chay_t4_thu.py thu_gia_tri_quan_t4.py --can-phut 30 --timeout 2400 --tep <gtq_dl.tar>:/content/gtq_dl.tar"""
import os
import subprocess
import sys
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
sh(f"cd {C} && rm -rf dgl && tar xf gtq_dl.tar && ls dgl | wc -l")
sh(f"python3 {E}/python/lay_mang.py pt {C}/gen100.pt --rel {REL_NN} 2>&1 | tail -n 1", timeout=300)
assert os.path.exists(f"{C}/gen100.pt"), "khong co gen100.pt"

sys.path.insert(0, f"{E}/python")
import numpy as np
import torch
from torch.utils.data import DataLoader
from dataset import FairyDataset, collate_packed, unpack_batch
from model import FairyNet
from nn_layout import AUX_BASE, AUX_CHECKS_THEM, AUX_CHECKS_US

LETTERS = "pnrqkbmvyscg"
LOAI = [c for c in LETTERS if c != "k"]
TEN = {"p": "Tot", "n": "Ma", "r": "Xe", "q": "Hau", "b": "Tuong(BmW)", "m": "Centaur", "v": "wildebeest", "y": "Alibaba", "s": "Sergeant",
       "c": "Phao", "g": "Grasshopper"}
dev = "cuda"
net = FairyNet(); net.load_state_dict(torch.load(f"{C}/gen100.pt", map_location="cpu")); net.to(dev).eval()
ds = FairyDataset(f"{C}/dgl", q_ratio=1.0, cache=True, sparse=True, packed=True, label="4000 van gan nhat")
log(f"{ds.num_games} van, {len(ds)} the")
dl = DataLoader(ds, batch_size=1024, shuffle=False, num_workers=2, collate_fn=collate_packed)
CNT, CHK, QN, QD = [], [], [], []
with torch.no_grad():
    for batch in dl:
        x, _, val = unpack_batch(batch, dev)
        v = torch.softmax(net(x)[1].float(), 1)
        QN.append((v[:, 0] - v[:, 2]).cpu().numpy())
        QD.append((val[:, 0] - val[:, 2]).cpu().numpy())                # q_ratio = 1: muc tieu gia tri = gia tri tim kiem (best_q) cua van
        CNT.append(x[:, :24].sum((2, 3)).round().to(torch.int16).cpu().numpy())
        CHK.append(torch.stack([x[:, AUX_BASE + AUX_CHECKS_US, 0, 0], x[:, AUX_BASE + AUX_CHECKS_THEM, 0, 0]], 1).mul(10).round().to(torch.int16).cpu().numpy())
CNT = np.concatenate(CNT); CHK = np.concatenate(CHK); QN = np.concatenate(QN).astype(np.float64); QD = np.concatenate(QD).astype(np.float64)
N = len(QN)
log(f"da chay mang tren {N} the; q mang: tb {QN.mean():+.3f}, |q| tb {np.abs(QN).mean():.3f}; q tim kiem: tb {QD.mean():+.3f}, |q| tb {np.abs(QD).mean():.3f}; "
    f"chieu con lai: ta {CHK[:, 0].mean():.2f}, dich {CHK[:, 1].mean():.2f}")
np.savez_compressed(f"{C}/gtq.npz", CNT=CNT, CHK=CHK, QN=QN, QD=QD)

idx = [LETTERS.index(c) for c in LOAI]
D = (CNT[:, idx] - CNT[:, [12 + i for i in idx]]).astype(np.float64)             # [N,11]
Ech = (CHK[:, 1].astype(np.float64) ** 0.8 - CHK[:, 0].astype(np.float64) ** 0.8)
atanh = lambda q: np.arctanh(np.clip(q, -0.999, 0.999))
YN, YD = atanh(QN), atanh(QD)
KHOI = 200
bien = np.linspace(0, N, KHOI + 1).astype(int)                                  # khoi lien tiep ~ 20 van: cac the cua mot van tuong quan
rng = np.random.RandomState(0)


def thu(ten, X, y, ten_cot):
    k = X.shape[1]
    A = np.zeros((KHOI, k, k)); B = np.zeros((KHOI, k)); S = np.zeros(KHOI)
    for b in range(KHOI):
        Xb, yb = X[bien[b]:bien[b + 1]], y[bien[b]:bien[b + 1]]
        A[b] = Xb.T @ Xb; B[b] = Xb.T @ yb; S[b] = yb @ yb
    beta = np.linalg.solve(A.sum(0), B.sum(0))
    sst = S.sum() - y.sum() ** 2 / N
    r2 = 1 - (S.sum() - 2 * beta @ B.sum(0) + beta @ A.sum(0) @ beta) / sst
    bs = []
    for _ in range(500):
        s = rng.randint(0, KHOI, KHOI)
        bs.append(np.linalg.solve(A[s].sum(0), B[s].sum(0)))
    bs = np.array(bs)
    ip = ten_cot.index("Tot")
    print(f"\n=== {ten}   (R^2 = {r2:.4f}, N = {N}) ===")
    print(f"{'he so':<14}{'gia tri (atanh)':>16}{'sai so':>9}{'quy ra Tot':>13}{'sai so':>9}")
    for j, c in enumerate(ten_cot):
        quy = beta[j] / beta[ip] if c in TEN.values() else float('nan')
        qs = (bs[:, j] / bs[:, ip]).std() if c in TEN.values() else float('nan')
        print(f"{c:<14}{beta[j]:>16.4f}{bs[:, j].std():>9.4f}{quy:>13.2f}{qs:>9.2f}", flush=True)


tot = [TEN[c] for c in LOAI]
X1 = np.column_stack([np.ones(N), D, Ech]); c1 = ["b0 (chan)"] + tot + ["g (chieu^0,8)"]
thu("V1 mang gen100: y = b0 + sum b_i d_i + g e", X1, YN, c1)
thu("V2 mang gen100: KHONG b0", X1[:, 1:], YN, c1[1:])
thu("V3 mang gen100: KHONG phan chieu", X1[:, :-1], YN, c1[:-1])
thu("V4 q TIM KIEM trong du lieu (best_q): co b0 + chieu", X1, YD, c1)
log("xong")
