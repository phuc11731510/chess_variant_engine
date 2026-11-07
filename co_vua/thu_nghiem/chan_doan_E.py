"""chan_doan_E.py -- chẩn đoán vì sao E (phần 4 của thiết kế) dự báo thấp hơn sai số thật của G trên cây giả.

Dựng cùng cây giả như mo_phong_cay.py, tính G, E (phương án A, B), rồi tách các node theo các đặc điểm:
khoảng cách tới cuối ván (theo đường ván đầu tiên đi qua node), số ván đi qua, số nước đã chơi, |V|, và xem
sai số thật (G - V)^2 so với E ở từng nhóm. Cũng tách sai số thật thành phần lệch có hệ thống (trung bình của
G - V theo góc bên đi) và phần dao động.

Chạy:  py chan_doan_E.py [--seed 1] [--nhieu-q 0.045] [--lech 0.05]
"""
import argparse
import types

import numpy as np

import mo_phong_cay as mp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--nhieu-q", type=float, default=mp.NHIEU_Q)
    ap.add_argument("--lech", type=float, default=0.05)
    a = ap.parse_args()
    mp.NHIEU_Q = a.nhieu_q
    cfg = types.SimpleNamespace(seed=a.seed, doi=4, ngan_sach=40000, r0=300, lech=a.lech)
    T, z_goc = mp.chay(cfg)
    n = T.n
    om = mp.omega2_cach_hai(T, z_goc)
    G, E, _ = mp.tinh(T, om)
    V = T.V[:n]
    trong = ~T.het[:n] & (T.k[:n] > 0)
    sg = np.where(T.sau[:n] % 2 == 0, 1.0, -1.0)

    # Khoảng cách tới cuối ván dọc đường đi nước nhiều lượt thăm nhất (đường của ván đầu tiên qua node).
    cach = np.zeros(n, int)
    for s in np.argsort(-T.sau[:n], kind="stable"):
        if T.het[s]:
            continue
        a_ = int(np.argmax(T.n_sum[s]))
        c = T.con[s].get(a_)
        if c is None:
            c = T.con[s][min(T.con[s])]
        cach[s] = cach[c] + 1
    so_choi = np.array([len(T.con[s]) for s in range(n)])

    print(f"omega^2 dùng {om:.5f}")
    for k in "ABCD":
        err = G[k] - V
        print(f"\n=== Phương án {k} ===")
        print(" Theo khoảng cách tới cuối ván (chỉ node có đúng 1 ván đi qua):")
        print("   cách cuối | số node | E dự báo | sai thật | lệch hệ thống (góc bên đi) | phần dao động")
        mot = trong & (T.m[:n] == 1)
        for lo, hi in [(1, 5), (5, 15), (15, 40), (40, 80), (80, 160), (160, 1000)]:
            mk = mot & (cach >= lo) & (cach < hi)
            if mk.sum() < 50:
                continue
            e = err[mk]
            lech = (sg[mk] * e).mean()
            print(f"   {lo:4d}-{hi - 1:<4d} | {mk.sum():7d} | {E[k][mk].mean():.4f}   | {(e ** 2).mean():.4f}   | "
                  f"{lech:+.4f} (bình phương {lech ** 2:.4f}) | {(e ** 2).mean() - lech ** 2:.4f}")
        q20 = np.quantile(E[k][trong], 0.2)
        thap = trong & (E[k] <= q20)
        print(f" Nhóm 20% node có E nhỏ nhất (E <= {q20:.4f}), {thap.sum()} node:")
        print(f"   E dự báo trung bình {E[k][thap].mean():.4f}, sai thật {(err[thap] ** 2).mean():.4f}")
        print(f"   cách cuối ván: trung vị {np.median(cach[thap]):.0f} (cả cây {np.median(cach[trong]):.0f}); "
              f"số ván đi qua: trung vị {np.median(T.m[:n][thap]):.0f}; có >= 2 nước đã chơi: {np.mean(so_choi[thap] >= 2):.0%}; "
              f"|V| trung bình {np.abs(V[thap]).mean():.2f} (cả cây {np.abs(V[trong]).mean():.2f})")
        for ten, mk in [("cách cuối < 15", thap & (cach < 15)), ("cách cuối >= 15", thap & (cach >= 15))]:
            if mk.sum():
                print(f"   {ten}: {mk.sum()} node, E {E[k][mk].mean():.4f}, sai thật {(err[mk] ** 2).mean():.4f}, "
                      f"lệch hệ thống {(sg[mk] * err[mk]).mean():+.4f}")
        # Kiểm định nghĩa: dọc một ván, mỗi nửa nước giá trị thật đổi bao nhiêu khi đi nước nhiều lượt thăm nhất
    buoc, buoc_p = [], []
    for s in np.where(trong)[0][:50000]:
        a_ = int(np.argmax(T.n_sum[s]))
        buoc.append(T.dau(s) * (T.Vc[s, a_] - T.V[s]))
        buoc_p.append((T.p[s] * (T.Vc[s] - T.V[s]) ** 2).sum())
    buoc = np.array(buoc)
    print(f"\nMỗi nửa nước theo nước nhiều lượt thăm nhất: giá trị thật đổi trung bình {buoc.mean():+.4f} cho bên đi, "
          f"bình phương {np.mean(buoc ** 2):.5f}; omega^2 thật theo p {np.mean(buoc_p):.5f}")


if __name__ == "__main__":
    main()
