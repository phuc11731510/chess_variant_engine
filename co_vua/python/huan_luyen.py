"""Huấn luyện một đời: AdamW, tốc độ học cố định, SWA kiểu lc0, fp32 (THIET_KE_CO_VUA.md 2.5).

Giữ đúng cách của engine cờ biến thể (custom_engine/python/train.py với cấu hình ô 07): batch 1024,
tốc độ học 1e-3, weight decay 1e-4, 1 lượt qua dữ liệu của cửa sổ, cứ 25 bước tối ưu thì gộp trọng số
vào bản trung bình SWA (tối đa 10 bản), cập nhật lại BatchNorm cho bản SWA rồi xuất. Đời sau khởi động
từ bản SWA của đời trước. Khác engine biến thể ở một điểm: không dùng --amp, mọi phép tính là fp32.

Chạy:  python huan_luyen.py --mau d1.npz,d2.npz,... --khoi-tao doi3.pt --ra doi4
Ra:    doi4.pt, doi4.onnx, và một dòng JSON tóm tắt in ra cuối cùng.
"""
import argparse
import json
import time

import numpy as np
import torch
import torch.nn.functional as F

from du_lieu import TrenGPU, noi
from mang import MangCoVua, so_tham_so, xuat_onnx


def mat_policy(logit, pi):
    """Cross-entropy chỉ trên nước hợp lệ (pi < 0 đánh dấu nước không hợp lệ), như lc0."""
    khong_hop_le = pi < 0
    logp = F.log_softmax(logit.masked_fill(khong_hop_le, float("-inf")), dim=1).masked_fill(khong_hop_le, 0.0)
    return -(pi.clamp(min=0.0) * logp).sum(1).mean()


def mat_value(logit, wdl):
    return -(wdl * F.log_softmax(logit, dim=1)).sum(1).mean()


@torch.no_grad()
def danh_gia(mang, du, so_mau, lo):
    """Mất mát trung bình theo thế cờ của mạng (chế độ eval) trên tối đa so_mau mẫu đầu."""
    mang.eval()
    tp = tv = n = 0.0
    for d in range(0, min(so_mau, du.n), lo):
        ci = torch.arange(d, min(d + lo, so_mau, du.n), device=du.bit.device)
        x, pi, wdl = du.lo(ci)
        p, v = mang(x)
        tp += mat_policy(p, pi).item() * len(ci); tv += mat_value(v, wdl).item() * len(ci); n += len(ci)
    return tp / n, tv / n


@torch.no_grad()
def cap_nhat_bn(mang, du, lo):
    """Tính lại thống kê BatchNorm cho trọng số SWA: một lượt qua dữ liệu ở chế độ train, trung bình cộng dồn."""
    bn = [m for m in mang.modules() if isinstance(m, torch.nn.modules.batchnorm._BatchNorm)]
    dong_luong = {m: m.momentum for m in bn}
    for m in bn:
        m.reset_running_stats()
        m.momentum = None
    mang.train()
    for d in range(0, du.n, lo):
        ci = torch.arange(d, min(d + lo, du.n), device=du.bit.device)
        mang(du.lo(ci)[0])
    for m in bn:
        m.momentum = dong_luong[m]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mau", required=True, help="các tệp mẫu .npz của cửa sổ, cách nhau bằng dấu phẩy")
    ap.add_argument("--khoi-tao", default="", help=".pt của đời trước (bỏ trống = khởi tạo mới)")
    ap.add_argument("--ra", required=True, help="tiền tố tệp ra (không có đuôi)")
    ap.add_argument("--batch", type=int, default=1024)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--weight-decay", type=float, default=1e-4)
    ap.add_argument("--so-luot", type=int, default=1, help="số lượt qua dữ liệu")
    ap.add_argument("--so-buoc", type=int, default=0, help="số bước tối ưu (0 = theo --so-luot)")
    ap.add_argument("--swa-moi", type=int, default=25, help="gộp vào SWA sau mỗi chừng ấy bước")
    ap.add_argument("--swa-toi-da", type=int, default=10, help="số bản tối đa trong trung bình SWA")
    ap.add_argument("--seed", type=int, default=0, help="0 = ngẫu nhiên")
    ap.add_argument("--thiet-bi", default="cuda" if torch.cuda.is_available() else "cpu")
    a = ap.parse_args()

    seed = a.seed or int(np.random.SeedSequence().entropy % 2**31)
    torch.manual_seed(seed)
    t0 = time.time()
    cac = [dict(np.load(f)) for f in a.mau.split(",")]
    # Cách cây trò chơi (gop_mau_cay.py): một tệp có thêm trọng số "w" (số ván đi qua node, phần 10 của thiết kế);
    # mỗi lô bốc mẫu theo w (có lặp lại) thay cho xáo trộn đều.
    trong_so = cac[0].get("w") if len(cac) == 1 else None
    du = TrenGPU(noi(cac), a.thiet_bi)
    if trong_so is not None:
        trong_so = torch.as_tensor(trong_so, dtype=torch.float64, device=a.thiet_bi)
    t_nap = time.time() - t0

    mang = MangCoVua().to(a.thiet_bi)
    if a.khoi_tao:
        mang.load_state_dict(torch.load(a.khoi_tao, map_location=a.thiet_bi))
    so_buoc = a.so_buoc or a.so_luot * ((du.n + a.batch - 1) // a.batch)
    # Mất mát của trọng số khởi đầu trên dữ liệu đời mới nhất (tệp cuối của --mau), trước khi học nó.
    moi_nhat = dict(np.load(a.mau.split(",")[-1]))
    du_moi = TrenGPU(moi_nhat, a.thiet_bi)
    dau_p, dau_v = danh_gia(mang, du_moi, du_moi.n, a.batch)
    del du_moi

    opt = torch.optim.AdamW(mang.parameters(), lr=a.lr, weight_decay=a.weight_decay)
    swa = MangCoVua().to(a.thiet_bi)
    swa.load_state_dict(mang.state_dict())
    so_ban = 0
    tp = tv = n = 0.0
    t1 = time.time()
    buoc = 0
    while buoc < so_buoc:
        hoan_vi = torch.randperm(du.n, device=a.thiet_bi)
        for d in range(0, du.n, a.batch):
            if buoc >= so_buoc:
                break
            mang.train()
            if trong_so is not None:
                ci = torch.multinomial(trong_so, a.batch, replacement=True)
            else:
                ci = hoan_vi[d:d + a.batch]
            x, pi, wdl = du.lo(ci)
            p, v = mang(x)
            lp, lv = mat_policy(p, pi), mat_value(v, wdl)
            opt.zero_grad(set_to_none=True)
            (lp + lv).backward()
            opt.step()
            buoc += 1
            tp += lp.item() * len(x); tv += lv.item() * len(x); n += len(x)
            if buoc % a.swa_moi == 0:
                # SWA kiểu lc0: bản đầu là bản sao, sau đó swa += (w - swa) / (min(số bản, tối đa) + 1).
                with torch.no_grad():
                    for ps, pm in zip(swa.parameters(), mang.parameters()):
                        if so_ban == 0:
                            ps.copy_(pm)
                        else:
                            ps.add_((pm - ps) / (min(so_ban, a.swa_toi_da) + 1))
                so_ban += 1
    t_hoc = time.time() - t1
    xuat = swa if so_ban > 0 else mang
    cap_nhat_bn(xuat, du, a.batch)
    torch.save(xuat.state_dict(), a.ra + ".pt")
    xuat_onnx(xuat.to("cpu").eval(), a.ra + ".onnx")
    print(json.dumps({"so_mau": du.n, "so_buoc": buoc, "theo_trong_so": trong_so is not None, "so_ban_swa": so_ban, "seed": seed,
                      "mat_policy_hoc": tp / max(n, 1), "mat_value_hoc": tv / max(n, 1),
                      "mat_policy_dau_tren_doi_moi": dau_p, "mat_value_dau_tren_doi_moi": dau_v,
                      "giay_nap": round(t_nap, 1), "giay_hoc": round(t_hoc, 1),
                      "so_tham_so": so_tham_so(mang)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
