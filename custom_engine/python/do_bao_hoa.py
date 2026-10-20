"""do_bao_hoa.py -- đo "bão hoà giá trị" trên một gói dữ liệu tự chơi games_gen<G>.zip.

Thế mà tìm kiếm cho |Q| gần 1 (một bên thắng chắc theo mạng) thì mọi nước đi có Q gần như bằng nhau,
nên PUCT chia lượt thăm theo prior P của mạng (N ~ P) và nhãn policy (tỉ lệ lượt thăm) ≈ chính prior.
Script chia các thế theo |Q| gốc và in cho từng nhóm:
  - tỉ lệ số thế trong dữ liệu;
  - độ nhọn của nhãn policy: % lượt thăm của nước nhiều nhất, entropy (nat), số nước có >= 5% lượt thăm;
  - KL(nhãn || prior của mạng) lưu sẵn trong dữ liệu (policy_kld): nhỏ = nhãn không dạy thêm gì;
  - hiệu chỉnh: kết quả ván thật (thắng / hoà / thua của bên đi) khi mạng nói thắng và khi nói thua;
  - tỉ lệ thế |Q| >= 0.95 theo từng đoạn ply.

    python do_bao_hoa.py games_gen91.zip
"""
import os
import sys
import zipfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trainingdata_reader as tr  # noqa: E402

EDGES = [0, .5, .8, .9, .95, .98, 1.0001]


def main():
    zp = sys.argv[1]
    rows = []   # q, z, top, ent, n5, kld, ply
    with zipfile.ZipFile(zp) as zf:
        members = [m for m in zf.namelist() if tr.is_game_member(m)]
    for m in members:
        for ply, rec in enumerate(tr.iter_games([(zp, m)], sparse=True)):
            p = rec["legal_pi"].astype(np.float64)
            s = p.sum()
            if s <= 0:
                continue
            p /= s
            q = rec["root_q"] if rec.get("version", 2) >= 2 else -rec["root_q"]
            ent = -(p[p > 0] * np.log(p[p > 0])).sum()
            rows.append((q, rec["result_q"], p.max(), ent, int((p >= .05).sum()), rec["policy_kld"], ply))
    a = np.array(rows)
    q, z, top, ent, n5, kld, ply = a.T
    print(f"{len(a)} thế, {len(members)} ván")
    r = float(np.corrcoef(q, z)[0, 1])
    print(f"tương quan root_q (bên đi) với kết quả ván result_q: {r:.3f}")
    if r < 0:
        z = -z
        print("(đảo dấu result_q)")
    aq = np.abs(q)

    def dist(mask, sign):
        zz = z[mask] * sign
        return (f"bên đi thắng {np.mean(zz > .5) * 100:4.1f}% hoà {np.mean(np.abs(zz) <= .5) * 100:4.1f}% "
                f"thua {np.mean(zz < -.5) * 100:4.1f}% (n={mask.sum()})")

    print(f"\n{'|Q| gốc':>10} {'số thế':>8} {'tỉ lệ':>6} | {'top%':>5} {'entropy':>7} {'n>=5%':>6} {'KL(nhãn||prior)':>15}")
    for lo, hi in zip(EDGES[:-1], EDGES[1:]):
        s = (aq >= lo) & (aq < hi)
        if not s.any():
            continue
        print(f"{lo:4.2f}-{min(hi, 1):4.2f} {s.sum():8d} {s.mean() * 100:5.1f}% | {top[s].mean() * 100:5.1f} "
              f"{ent[s].mean():7.2f} {n5[s].mean():6.1f} {kld[s].mean():15.3f}")
        if (s & (q > 0)).any():
            print(f"{'':>10}   mạng nói bên đi THẮNG (Q>0): {dist(s & (q > 0), 1)}")
        if (s & (q < 0)).any():
            print(f"{'':>10}   mạng nói bên đi THUA  (Q<0): {dist(s & (q < 0), 1)}")
    print("\nTỉ lệ thế |Q| >= 0.95 theo đoạn ply:")
    for lo, hi in [(0, 32), (32, 100), (100, 200), (200, 10 ** 9)]:
        s = (ply >= lo) & (ply < hi)
        print(f"  ply {lo}-{min(hi, 999)}: {np.mean(aq[s] >= .95) * 100:5.1f}%")


if __name__ == "__main__":
    main()
