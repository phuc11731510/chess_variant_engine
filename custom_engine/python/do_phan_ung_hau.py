"""do_phan_ung_hau.py -- đầu giá trị PHẢN ỨNG thế nào khi một bên mất một Hậu (theo từng đời mạng).

Lấy ngẫu nhiên các thế trong dữ liệu tự chơi mà bên đi và đối phương có cùng số Hậu (1-1 hoặc 2-2) và các quân khác gần cân bằng
(tổng chênh lệch số quân mỗi loại, trừ Hậu và Hoàng gia, không quá 2). Với mỗi thế, xoá MỘT Hậu (của bên đi, rồi một Hậu của đối
phương) khỏi bàn hiện tại VÀ khỏi các bàn lịch sử nếu quân đó còn đứng đúng ô, cho mạng chấm lại, và in độ đổi của atanh(q), q = Thắng - Thua
của value head từ góc nhìn BÊN ĐI:

    xoá Hậu của bên đi:      phải ÂM  (bên đi yếu đi);   xoá Hậu của đối phương: phải DƯƠNG, độ lớn gần bằng.
    nhóm 1-1: mất Hậu duy nhất;   nhóm 2-2: mất một trong hai Hậu (tình huống ván 1323.47 ở nửa nước 26).

Dùng cho: (1) theo dõi qua các đời xem mạng có học dần giá trị của Hậu không (số đo 26/11/2026, mỗi nhóm 700 thế, sai số chuẩn ~0,02:
nhóm 2-2 xoá Hậu của ta: gen10 -0,07, gen30 -0,14, gen64 -0,13, gen100 -0,24, gen110 -0,31, gen117 -0,28, gen122 -0,23; nhóm 1-1: -0,07, -0,23,
-0,42, -0,62, -0,67, -0,59, -0,58); (2) kiểm lỗi ngầm của đường giá trị: hướng đúng (ta âm / địch dương, độ lớn gần bằng) và không lệch theo màu
bên đi (Trắng/Đen). Chỉ DÙNG để đo: không đưa quy tắc nào vào huấn luyện.

    python do_phan_ung_hau.py --data "D:\\chess_variant\\Dữ liệu huấn luyện" --nets 100,110,117,122 --net-dir D:\\chess_variant\\models
    python do_phan_ung_hau.py --data goi --nets 130,135 --net-dir mang --ghi lich_su_phan_ung_hau.csv   # nối thêm mỗi lần đo vào CSV

Mạng genN.pt lấy trong --net-dir; thiếu thì tải từ --rel (mặc định Release NN_Model). Chạy CPU, khoảng 5 giây mỗi mạng (1.400 thế).
"""
import argparse
import csv
import datetime
import os
import random
import sys
import urllib.request
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trainingdata_reader as tdr  # noqa: E402
from dataset import list_games  # noqa: E402
from nn_layout import MOVE_HISTORY, PIECE_KINDS, PLANES_PER_BOARD  # noqa: E402

LETTERS = "pnrqkbmvyscg"                     # kPieceKindOrder (encoder.cc)
IQ, IK = LETTERS.index("q"), LETTERS.index("k")
REL = "https://github.com/phuc11731510/chess_variant_engine/releases/download/NN_Model"
NHOM = ((1, 1), (2, 2))                      # (số Hậu của bên đi, số Hậu của đối phương)


def dem(pp, j):
    """Số quân trên mặt phẳng j (mặt nạ 128 bit gồm hai từ uint64)."""
    return int(pp[j, 0]).bit_count() + int(pp[j, 1]).bit_count()


def lay_mau(args):
    """Các thế đủ điều kiện của một nhóm ván: dict(pp, ep, rule50, cu, ct, nus, nth, stm)."""
    games, per_game, seed = args
    rng = random.Random(seed)
    out = []
    for g in games:
        recs = list(tdr.iter_games([g], sparse=True))
        for k in rng.sample(range(len(recs)), min(per_game, len(recs))):
            r = recs[k]
            pp = np.asarray(r["piece_planes"], dtype=np.uint64).reshape(PLANES_PER_BOARD * MOVE_HISTORY, 2)
            nus, nth = dem(pp, IQ), dem(pp, PIECE_KINDS + IQ)
            if (nus, nth) not in NHOM:
                continue
            d = np.array([dem(pp, j) - dem(pp, PIECE_KINDS + j) for j in range(PIECE_KINDS)])
            if int(np.abs(np.delete(d, [IQ, IK])).sum()) > 2:
                continue
            out.append(dict(pp=pp.copy(), ep=np.asarray(r["ep_mask"], dtype=np.uint64).copy(), rule50=r["rule50_count"],
                            cu=r["checks_remaining_us"], ct=r["checks_remaining_them"], nus=nus, nth=nth, stm=int(r["side_to_move"])))
    return out


def rec_of(d, pp):
    return dict(piece_planes=pp.reshape(-1), ep_mask=d["ep"], rule50_count=d["rule50"],
                checks_remaining_us=d["cu"], checks_remaining_them=d["ct"])


def bo_hau(d, chu, rng):
    """Xoá một Hậu của chủ `chu` (0 = bên đi, 1 = đối phương) khỏi bàn hiện tại và các bàn lịch sử còn Hậu đúng ô đó."""
    pp = d["pp"].copy()
    off = IQ + chu * PIECE_KINDS
    bits = [(w, b) for w in range(2) for b in range(64) if (int(pp[off, w]) >> b) & 1]
    w, b = rng.choice(bits)
    mask = ~np.uint64(1 << b)
    for blk in range(MOVE_HISTORY):
        if (int(pp[blk * PLANES_PER_BOARD + off, w]) >> b) & 1:
            pp[blk * PLANES_PER_BOARD + off, w] &= mask
    return pp


def tai_mang(gen, net_dir, rel):
    path = os.path.join(net_dir, f"gen{gen}.pt")
    if not os.path.exists(path):
        os.makedirs(net_dir, exist_ok=True)
        print(f"[tải] gen{gen}.pt từ {rel}", flush=True)
        urllib.request.urlretrieve(f"{rel}/gen{gen}.pt", path)
    return path


def q_cua(net, X, torch):
    qs = []
    with torch.no_grad():
        for i in range(0, len(X), 256):
            _, v, _ = net(torch.from_numpy(X[i:i + 256]))
            s = torch.softmax(v, 1)
            qs.append((s[:, 0] - s[:, 2]).numpy().astype(np.float64))
    return np.concatenate(qs)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", required=True, help="thư mục / .zip / .xz dữ liệu tự chơi (như train.py --data)")
    ap.add_argument("--nets", required=True, help="các đời mạng, vd 100,110,117,122")
    ap.add_argument("--net-dir", default="mang", help="thư mục chứa genN.pt (thiếu thì tải về đây)")
    ap.add_argument("--rel", default=REL, help="URL thư mục Release chứa genN.pt")
    ap.add_argument("--so-the", type=int, default=700, help="số thế mỗi nhóm (1-1, 2-2)")
    ap.add_argument("--moi-van", type=int, default=4, help="số thế lấy tối đa mỗi ván")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--ghi", default="", help="nối thêm kết quả vào tệp CSV (ngày, đời, nhóm, ...) để theo dõi theo thời gian")
    a = ap.parse_args()
    import torch
    from model import FairyNet

    games = list_games(a.data)
    random.Random(a.seed).shuffle(games)
    lo = [(games[i::a.workers * 8], a.moi_van, a.seed + i) for i in range(a.workers * 8)]
    with Pool(a.workers) as p:
        mau = [d for part in p.map(lay_mau, lo) for d in part]
    random.Random(a.seed).shuffle(mau)
    chon = []
    for nhom in NHOM:
        ds = [d for d in mau if (d["nus"], d["nth"]) == nhom][:a.so_the]
        if len(ds) < 100:
            sys.exit(f"[!] nhóm {nhom} chỉ có {len(ds)} thế (cần ít nhất 100): dữ liệu quá ít ván, tăng --moi-van hoặc dùng thêm dữ liệu")
        chon += ds
    nh = np.array([0 if (d["nus"], d["nth"]) == NHOM[0] else 1 for d in chon])
    stm = np.array([d["stm"] for d in chon])
    print(f"{len(games)} ván, {len(chon)} thế: nhóm 1-1 {int((nh == 0).sum())}, nhóm 2-2 {int((nh == 1).sum())}; bên đi Trắng {int((stm == 0).sum())} / Đen {int((stm == 1).sum())}")
    rng = random.Random(a.seed + 1)
    st = lambda X: np.stack([tdr.reconstruct_planes(x) for x in X]).astype(np.float32)
    X0 = st([rec_of(d, d["pp"]) for d in chon])
    Xta = st([rec_of(d, bo_hau(d, 0, rng)) for d in chon])
    Xdich = st([rec_of(d, bo_hau(d, 1, rng)) for d in chon])
    at = lambda q: np.arctanh(np.clip(q, -0.999, 0.999))
    print("độ đổi atanh(q) của BÊN ĐI: xoá Hậu CỦA TA (phải âm) | xoá Hậu CỦA ĐỊCH (phải dương, cùng độ lớn)")
    print(f"{'mạng':<8}{'1-1 ta':>8}{'1-1 địch':>10}{'2-2 ta':>8}{'2-2 địch':>10}   2-2 ta theo bên đi: Trắng / Đen   sai số chuẩn 1-1 / 2-2")
    ghi = []
    for gen in [int(x) for x in a.nets.split(",")]:
        net = FairyNet()
        net.load_state_dict(torch.load(tai_mang(gen, a.net_dir, a.rel), map_location="cpu"))
        net.eval()
        q0, q1, q2 = q_cua(net, X0, torch), q_cua(net, Xta, torch), q_cua(net, Xdich, torch)
        dta, ddich = at(q1) - at(q0), at(q2) - at(q0)
        m = lambda v, k: v[nh == k].mean()
        se = lambda v, k: v[nh == k].std() / np.sqrt((nh == k).sum())
        w, b = ((nh == 1) & (stm == 0)), ((nh == 1) & (stm == 1))
        print(f"gen{gen:<5}{m(dta, 0):>+8.2f}{m(ddich, 0):>+10.2f}{m(dta, 1):>+8.2f}{m(ddich, 1):>+10.2f}   "
              f"{dta[w].mean():+.2f} / {dta[b].mean():+.2f}                    {se(dta, 0):.3f} / {se(dta, 1):.3f}", flush=True)
        for k, ten in ((0, "1-1"), (1, "2-2")):
            ghi.append([datetime.date.today().isoformat(), gen, ten, int((nh == k).sum()), f"{m(dta, k):.4f}", f"{m(ddich, k):.4f}", f"{se(dta, k):.4f}"])
    if a.ghi:
        moi = not os.path.exists(a.ghi)
        with open(a.ghi, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if moi:
                w.writerow(["ngay", "doi", "nhom", "so_the", "doi_atanh_xoa_hau_ta", "doi_atanh_xoa_hau_dich", "sai_so_chuan"])
            w.writerows(ghi)
        print(f"[ghi] {len(ghi)} dòng vào {a.ghi}")


if __name__ == "__main__":
    main()
