"""do_nhiet_do.py -- đo hai thứ trên dữ liệu tự chơi (một gói games_gen<G>.zip) và mạng đã sinh ra nó:

  (1) NHIỆT ĐỘ: chọn nước theo nhiệt độ T (xác suất ~ số lượt thăm ^ (1/T), như ô xem tự chơi / SelectMoveEdge)
      làm mất bao nhiêu. Dữ liệu chỉ có giá trị Q của nước TỐT NHẤT (nhiều lượt thăm nhất) và nước ĐÃ CHƠI,
      và chỉ ở các ply < --cutoff (nơi tự chơi lấy mẫu với T = 1), nên:
        - mất mát quan sát được = best_q - played_q của các nước đã chơi (Q của bên đi, -1..1);
        - mất mát khi dùng T khác: ước lượng bằng trọng số quan trọng w = P_T(nước đã chơi) / P_1(nước đã chơi)
          (nước đã chơi được rút theo P_1 nên ước lượng này không chệch); kiểm lại bằng công thức đúng
          của xác suất chọn nước khác nước tốt nhất, tính được ở MỌI ply từ phân bố lượt thăm đã lưu;
        - số nước "không phải tốt nhất" kỳ vọng mỗi ván theo T.
  (2) POLICY THÔ (một lần chạy mạng, không tìm kiếm) so với phân bố lượt thăm của tìm kiếm (nhãn huấn luyện):
      trùng top-1, hạng của nước nhiều lượt thăm nhất trong policy thô, tương quan hạng (Spearman), độ phân
      tán (entropy), và "nhiệt độ hiệu dụng" T* làm softmax(logits / T*) giống phân bố lượt thăm nhất
      (T* < 1: policy thô phẳng hơn kết quả tìm kiếm). Kiểm đường ống: q thô tính lại == orig_q đã lưu.

    python do_nhiet_do.py --data games_gen91.zip --onnx gen91.onnx [--mau 3000] [--cutoff 32] [--max-games N]

--onnx PHẢI là mạng đã sinh dữ liệu đó (gen91 sinh games_gen91). Cần numpy + onnxruntime (không cần torch).
"""
import argparse
import math
import os
import random
import sys
import time
import zipfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trainingdata_reader as tr  # noqa: E402

BUCKETS = [(0, 32, "ply 0-31"), (32, 100, "ply 32-99"), (100, 200, "ply 100-199"), (200, 10 ** 9, "ply >= 200")]
TEMPS = [1.0, 0.5, 0.25, 0.1]
KEEP = ("piece_planes", "ep_mask", "rule50_count", "checks_remaining_us", "checks_remaining_them",
        "castling_us_ooo_sq", "castling_us_oo_sq", "castling_them_ooo_sq", "castling_them_oo_sq")


def bucket_of(ply):
    for i, (lo, hi, _) in enumerate(BUCKETS):
        if lo <= ply < hi:
            return i
    return len(BUCKETS) - 1


def p_temp(p, t):
    """Phân bố chọn nước ~ p^(1/t) (p = tỉ lệ lượt thăm, 0 giữ 0)."""
    w = np.power(p.astype(np.float64), 1.0 / t)
    return w / w.sum()


def q_stm(rec, key):
    q = rec[key]
    return -q if rec.get("version", 2) < 2 else q


def avg_rank(x):
    order = np.argsort(x, kind="stable")
    r = np.empty(len(x))
    r[order] = np.arange(len(x), dtype=np.float64)
    xs = x[order]
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and xs[j + 1] == xs[i]:
            j += 1
        if j > i:
            r[order[i:j + 1]] = (i + j) / 2.0
        i = j + 1
    return r


def spearman(a, b):
    ra, rb = avg_rank(a), avg_rank(b)
    ra -= ra.mean()
    rb -= rb.mean()
    d = math.sqrt(float((ra * ra).sum() * (rb * rb).sum()))
    return float((ra * rb).sum() / d) if d > 0 else float("nan")


def pct(x, q):
    return float(np.percentile(x, q)) if len(x) else float("nan")


# ---------------------------------------------------------------- (1) nhiệt độ + lấy mẫu cho (2)
def duyet(zip_path, cutoff, mau, rng, max_games):
    st = {
        "pnb": [[0.0] * len(BUCKETS) for _ in TEMPS], "n": [0] * len(BUCKETS),
        "nonbest_obs": [0] * len(BUCKETS),
        "per_game": [[] for _ in TEMPS], "len": [],
        "reg": [], "is_best": [], "w": {t: [] for t in TEMPS},
        "sampled_after_cut": 0,
    }
    reservoir, seen = [], 0
    with zipfile.ZipFile(zip_path) as zf:
        members = [m for m in zf.namelist() if tr.is_game_member(m)]
    if max_games:
        members = members[:max_games]
    t0 = time.time()
    for gi, m in enumerate(members):
        tot = [0.0] * len(TEMPS)
        n_ply = 0
        for ply, rec in enumerate(tr.iter_games([(zip_path, m)], sparse=True)):
            li, pi = rec["legal_idx"], rec["legal_pi"].astype(np.float64)
            s = pi.sum()
            if s <= 0:
                continue
            p1 = pi / s
            jb = np.nonzero(li == rec["best_idx"])[0]
            jp = np.nonzero(li == rec["played_idx"])[0]
            if len(jb) == 0 or len(jp) == 0:
                continue
            jb, jp = int(jb[0]), int(jp[0])
            b = bucket_of(ply)
            st["n"][b] += 1
            n_ply += 1
            nonbest = rec["played_idx"] != rec["best_idx"]
            st["nonbest_obs"][b] += int(nonbest)
            if nonbest and ply >= cutoff:
                st["sampled_after_cut"] += 1
            pts = []
            for ti, t in enumerate(TEMPS):
                pt = p1 if t == 1.0 else p_temp(p1, t)
                pts.append(pt)
                v = 1.0 - float(pt[jb])
                st["pnb"][ti][b] += v
                tot[ti] += v
            if ply < cutoff:
                r = q_stm(rec, "best_q") - q_stm(rec, "played_q")
                st["reg"].append(r)
                st["is_best"].append(not nonbest)
                for ti, t in enumerate(TEMPS):
                    st["w"][t].append(float(pts[ti][jp] / p1[jp]))
            # lấy mẫu ngẫu nhiên (reservoir) cho phần (2)
            seen += 1
            item = None
            if len(reservoir) < mau:
                item = len(reservoir)
                reservoir.append(None)
            else:
                j = rng.randrange(seen)
                if j < mau:
                    item = j
            if item is not None:
                reservoir[item] = {"ply": ply, "legal_idx": li.copy(), "legal_pi": rec["legal_pi"].copy(),
                                   "best_idx": rec["best_idx"], "orig_q": rec["orig_q"], "orig_d": rec["orig_d"],
                                   "policy_kld": rec["policy_kld"], "version": rec["version"],
                                   **{k: (np.array(rec[k]) if k == "piece_planes" else rec[k]) for k in KEEP}}
        for ti in range(len(TEMPS)):
            st["per_game"][ti].append(tot[ti])
        st["len"].append(n_ply)
        if (gi + 1) % 200 == 0:
            print(f"  ... {gi + 1}/{len(members)} ván ({time.time() - t0:.0f} s)", flush=True)
    return st, reservoir, len(members), seen


def in_nhiet_do(st, cutoff, n_games, n_rec):
    print(f"\n=== (1) NHIỆT ĐỘ -- {n_games} ván, {n_rec} thế, trung bình {np.mean(st['len']):.1f} ply/ván ===")
    print(f"Nước đã chơi KHÁC nước nhiều lượt thăm nhất ở ply >= {cutoff}: {st['sampled_after_cut']} "
          f"(0 = đúng như hiểu: chỉ lấy mẫu trước ply {cutoff})")
    print("\nXác suất chọn nước KHÁC nước nhiều lượt thăm nhất, tính đúng từ phân bố lượt thăm đã lưu (trung bình các thế):")
    print("  khoảng ply    số thế   " + "   ".join(f"T={t:<5}" for t in TEMPS))
    for b, (_, _, name) in enumerate(BUCKETS):
        n = st["n"][b]
        if n:
            print(f"  {name:<12} {n:>8}   " + "   ".join(f"{100 * st['pnb'][ti][b] / n:6.1f}%" for ti in range(len(TEMPS))))
    print("\nSố nước kỳ vọng KHÁC nước tốt nhất mỗi ván (cả hai bên, cả ván) nếu dùng nhiệt độ T ở MỌI ply:")
    for ti, t in enumerate(TEMPS):
        print(f"  T={t:<5} {np.mean(st['per_game'][ti]):6.1f} nước / ván ({np.mean(st['len']):.0f} ply)")
    reg = np.array(st["reg"])
    isb = np.array(st["is_best"])
    print(f"\nMất mát Q (Q nước nhiều lượt thăm nhất - Q nước đã chơi, bên đi, thang -1..1), ply < {cutoff}, {len(reg)} thế:")
    nb = reg[~isb]
    print(f"  Quan sát (T=1 thật): chơi khác nước tốt nhất ở {100 * (~isb).mean():.1f}% thế; "
          f"mất mát trung bình mỗi ply {reg.mean():+.4f}")
    if len(nb):
        print(f"    riêng các nước khác: trung bình {nb.mean():+.3f}, trung vị {np.median(nb):+.3f}, "
              f"p90 {pct(nb, 90):+.3f}, lớn nhất {nb.max():+.3f}; mất > 0,1: {100 * (nb > 0.1).mean():.0f}%, "
              f"> 0,3: {100 * (nb > 0.3).mean():.0f}%, > 0,6: {100 * (nb > 0.6).mean():.0f}%; "
              f"có lợi hơn nước tốt nhất (< 0): {100 * (nb < 0).mean():.0f}%")
    print("  Ước lượng cho nhiệt độ khác (trọng số quan trọng; ESS = cỡ mẫu hiệu dụng):")
    print("    xác suất MỖI PLY chơi nước mất > 0,1 / > 0,3 / > 0,6 Q, và số nước như vậy kỳ vọng mỗi ván (nhân ply/ván, giả định cùng tỉ lệ ở cả ván):")
    for t in TEMPS:
        w = np.array(st["w"][t])
        ps = [float((w * (reg > th)).mean()) for th in (0.1, 0.3, 0.6)]
        print(f"      T={t:<5} " + "   ".join(f"> {th}: {100 * p:5.2f}% (~{p * np.mean(st['len']):4.1f}/ván)"
                                             for th, p in zip((0.1, 0.3, 0.6), ps)))
    print("    T      P(nước khác)   [đối chiếu công thức đúng]   mất mát TB mỗi ply   ESS")
    pn_exact_open = [st["pnb"][ti][0] / max(1, st["n"][0]) for ti in range(len(TEMPS))]
    for ti, t in enumerate(TEMPS):
        w = np.array(st["w"][t])
        ess = float(w.sum() ** 2 / (w * w).sum()) if len(w) else float("nan")
        pnb = float((w * (~isb)).mean())
        print(f"    {t:<5} {100 * pnb:9.1f}%      {100 * pn_exact_open[ti]:8.1f}%                 "
              f"{float((w * reg).mean()):+.4f}            {ess:6.0f}")
    print("  Tổng mất mát Q kỳ vọng mỗi ván (ước lượng quan trọng mỗi ply x số ply/ván; GIẢ ĐỊNH tỉ lệ ở cả ván như ở khai cuộc, "
          "và chỉ tính theo Q của chính mạng này):")
    for t in TEMPS:
        w = np.array(st["w"][t])
        print(f"    T={t:<5} ≈ {float((w * reg).mean()) * np.mean(st['len']):5.2f} Q mỗi ván")


# ---------------------------------------------------------------- (2) policy thô
def chay_mang(onnx_path, reservoir, bs=32):
    import onnxruntime as ort
    so = ort.SessionOptions()
    so.intra_op_num_threads = os.cpu_count() or 4
    sess = ort.InferenceSession(onnx_path, so, providers=["CPUExecutionProvider"])
    out = []
    t0 = time.time()
    for i in range(0, len(reservoir), bs):
        chunk = reservoir[i:i + bs]
        x = np.stack([tr.reconstruct_planes(r) for r in chunk]).astype(np.float32)
        pol, val = sess.run(["policy", "value"], {"input": x})
        for r, lg, v in zip(chunk, pol, val):
            r["logits"] = lg[r["legal_idx"].astype(np.int64)].astype(np.float64)
            r["q_raw"] = float(v[0] - v[2])
        if (i // bs) % 20 == 19:
            print(f"  ... mạng {i + len(chunk)}/{len(reservoir)} ({time.time() - t0:.0f} s)", flush=True)
    return out


def phan_tich_policy(reservoir):
    Ts = np.round(np.arange(0.25, 2.01, 0.05), 3)
    rows = []
    dq = []
    for r in reservoir:
        lg, pi = r["logits"], r["legal_pi"].astype(np.float64)
        s = pi.sum()
        if s <= 0 or len(lg) < 2:
            continue
        t = pi / s
        jb = np.nonzero(r["legal_idx"] == r["best_idx"])[0]
        if len(jb) == 0:
            continue
        jb = int(jb[0])
        z = lg - lg.max()
        p_raw = np.exp(z) / np.exp(z).sum()
        order = np.argsort(-lg, kind="stable")
        rank_best = int(np.nonzero(order == jb)[0][0]) + 1
        top1 = int(order[0] == int(np.argmax(t)))
        ent = lambda p: float(-(p[p > 0] * np.log(p[p > 0])).sum())
        vis = t > 0
        sp = spearman(lg[vis], t[vis]) if vis.sum() >= 3 else float("nan")
        # nhiệt độ hiệu dụng: min_T KL(t || softmax(lg/T))
        zz = lg[None, :] / Ts[:, None]
        zz = zz - zz.max(axis=1, keepdims=True)
        lsm = zz - np.log(np.exp(zz).sum(axis=1, keepdims=True))
        kl = (t[vis][None, :] * (np.log(t[vis])[None, :] - lsm[:, vis])).sum(axis=1)
        k1 = int(np.argmin(np.abs(Ts - 1.0)))
        ks = int(np.argmin(kl))
        # chọn nước theo policy thô với nhiệt độ T: xác suất khác nước tìm kiếm cho là tốt nhất
        def pnb(T):
            w = np.exp((lg - lg.max()) / T)
            return 1.0 - float(w[jb] / w.sum())
        sl = np.sort(lg)[::-1]
        st2 = np.sort(t)[::-1]
        rows.append({
            "ply": r["ply"], "top1": top1, "rank_best": rank_best, "top3": int(rank_best <= 3),
            "h_raw": ent(p_raw), "h_vis": ent(t), "ptop_raw": float(p_raw.max()), "ptop_vis": float(t.max()),
            "sp": sp, "kl1": float(kl[k1]), "kls": float(kl[ks]), "Ts": float(Ts[ks]),
            "gap_raw": float(sl[0] - sl[1]), "gap_vis": float(math.log(st2[0] / st2[1])) if st2[1] > 0 else float("nan"),
            "pnb1": pnb(1.0), "pnb05": pnb(0.5), "kld_saved": r["policy_kld"],
            "nlegal": len(lg),
        })
        if r["version"] >= 4 and r["orig_d"] is not None:
            dq.append((r["q_raw"], r["orig_q"]))
    return rows, dq


def in_policy(rows, dq):
    def col(k, sel=None):
        v = np.array([x[k] for x in rows if sel is None or sel(x)], dtype=np.float64)
        return v[~np.isnan(v)]
    print(f"\n=== (2) POLICY THÔ so với lượt thăm (800 lượt) -- {len(rows)} thế ngẫu nhiên ===")
    if dq:
        a = np.array(dq)
        d = np.abs(a[:, 0] - a[:, 1])
        print(f"Kiểm đường ống: q thô tính lại vs orig_q đã lưu ({len(a)} thế): |chênh| trung vị {np.median(d):.5f}, "
              f"p95 {pct(d, 95):.4f}, lớn nhất {d.max():.3f}; > 0,05: {100 * (d > 0.05).mean():.1f}% thế "
              "(chênh lớn do bộ nhớ đệm NN dùng khoá thế cờ không có lịch sử)")
    print("  khoảng ply    số thế  top1=nhiều thăm  nước nhiều thăm nằm top3  hạng TB  Spearman  số nước hợp lệ TB")
    for lo, hi, name in BUCKETS + [(0, 10 ** 9, "TẤT CẢ")]:
        sel = lambda x, lo=lo, hi=hi: lo <= x["ply"] < hi
        n = len([1 for x in rows if sel(x)])
        if not n:
            continue
        print(f"  {name:<12} {n:>6}   {100 * col('top1', sel).mean():12.1f}%   {100 * col('top3', sel).mean():18.1f}%   "
              f"{col('rank_best', sel).mean():6.2f}   {np.nanmean(col('sp', sel)):7.3f}   {col('nlegal', sel).mean():8.1f}")
    print("\nChỉ các thế tìm kiếm CHẮC một nước (nước nhiều lượt thăm nhất có >= 60% / >= 80% lượt thăm) -- ít bị nhiễu gốc Dirichlet làm lệch:")
    for th in (0.6, 0.8):
        sel = lambda x, th=th: x["ptop_vis"] >= th
        n = len([1 for x in rows if sel(x)])
        if n:
            print(f"  >= {int(th * 100)}%: {n:>5} thế ({100 * n / len(rows):.0f}%)  top1 trùng {100 * col('top1', sel).mean():.1f}%  "
                  f"nằm top3 {100 * col('top3', sel).mean():.1f}%  hạng TB {col('rank_best', sel).mean():.2f}")
    print("\nĐộ nhọn (TB theo thế)         policy thô     phân bố lượt thăm")
    print(f"  xác suất nước đứng đầu       {100 * col('ptop_raw').mean():6.1f}%         {100 * col('ptop_vis').mean():6.1f}%")
    print(f"  entropy (nat)                {col('h_raw').mean():6.2f}          {col('h_vis').mean():6.2f}")
    print(f"  số nước 'hiệu dụng' e^H      {np.exp(col('h_raw')).mean():6.1f}          {np.exp(col('h_vis')).mean():6.1f}")
    print(f"  logit nước 1 - nước 2        {col('gap_raw').mean():6.2f}          {np.nanmean(col('gap_vis')):6.2f}  (phải: ln(lượt thăm1/lượt thăm2))")
    ts = col("Ts")
    print(f"\nNhiệt độ hiệu dụng T* (softmax(logits/T*) giống lượt thăm nhất): trung vị {np.median(ts):.2f}, "
          f"p25 {pct(ts, 25):.2f}, p75 {pct(ts, 75):.2f}; KL(lượt thăm || policy) tại T=1: {col('kl1').mean():.3f}, tại T*: {col('kls').mean():.3f}"
          f"  [policy_kld đã lưu trong dữ liệu: {col('kld_saved').mean():.3f}]")
    print(f"Nếu CHỌN NƯỚC THEO POLICY THÔ (không tìm kiếm): xác suất ra nước khác nước tìm kiếm cho là tốt nhất: "
          f"T=1 {100 * col('pnb1').mean():.1f}%, T=0,5 {100 * col('pnb05').mean():.1f}%")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--data", required=True, help="games_gen<G>.zip (ván .xz v6)")
    ap.add_argument("--onnx", required=True, help="mạng đã sinh dữ liệu đó (gen<G>.onnx)")
    ap.add_argument("--mau", type=int, default=3000, help="số thế ngẫu nhiên chạy mạng cho phần (2)")
    ap.add_argument("--cutoff", type=int, default=32, help="ply: trước đó tự chơi lấy mẫu với T=1 (--temp-cutoff)")
    ap.add_argument("--max-games", type=int, default=0)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    print(f"[do_nhiet_do] đọc {a.data} ...")
    st, reservoir, n_games, n_rec = duyet(a.data, a.cutoff, a.mau, rng, a.max_games)
    in_nhiet_do(st, a.cutoff, n_games, n_rec)
    print(f"\n[do_nhiet_do] chạy mạng {a.onnx} trên {len(reservoir)} thế ...")
    chay_mang(a.onnx, reservoir)
    rows, dq = phan_tich_policy(reservoir)
    in_policy(rows, dq)


if __name__ == "__main__":
    main()
