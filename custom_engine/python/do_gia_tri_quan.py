"""do_gia_tri_quan.py -- mạng hiểu GIÁ TRỊ TỪNG LOẠI QUÂN thế nào: xoá một quân khỏi thế cờ rồi xem value đổi bao nhiêu.

Với mỗi thế trong dữ liệu tự chơi (games_gen*/ *.xz), lấy ngẫu nhiên một phần các thế; trong mỗi thế, lần lượt
XOÁ TỪNG QUÂN (cả của bên đi lẫn bên kia) rồi cho mạng chấm lại. "Độ lệch" của một lần xoá, tính theo phía
CHỦ quân đó:

    lệch = q_chủ(trước) - q_chủ(sau)        q = Thắng - Thua của value head (WDL softmax), từ góc nhìn bên đi;
                                            q_chủ = q nếu quân thuộc bên đi, = -q nếu thuộc bên kia.

Lệch DƯƠNG = mất quân đó làm chủ quân thiệt đi (mạng coi quân đó có giá trị). Với mỗi loại quân in p40 (bách phân
vị 40), cùng trung bình, trung vị, p25, p75, số lần.

Cách xoá giữ đầu vào nhất quán với lúc huấn luyện: mạng nhận 8 bàn cờ liên tiếp (27 mặt phẳng mỗi bàn, mọi bàn
đều theo góc nhìn bên đi hiện tại). Quân bị xoá khỏi bàn hiện tại VÀ khỏi cả 7 bàn lịch sử, lần theo đường đi của chính
quân đó (mỗi nước chỉ đổi một quân nên ô quân đứng trước là duy nhất). Quân vừa phong cấp trong 7 nước gần nhất
không lần ngược được -> bỏ qua. Quân Hoàng gia (k) xoá đi là thế không thể có trong ván: in riêng, chỉ để tham khảo.
Quyền nhập thành gắn với xe bị xoá cũng được xoá.

    python do_gia_tri_quan.py --model D:\\chess_variant\\models\\gen109.onnx --data "D:\\chess_variant\\Dữ liệu huấn luyện" --keep 0.04
"""
import argparse
import glob
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trainingdata_reader as tr  # noqa: E402

PPB = 27                       # mặt phẳng mỗi bàn lịch sử: 0-12 quân bên đi, 13-25 quân bên kia, 26 lặp thế
NHIST = 8
# chỉ số mặt phẳng -> (ký hiệu, tên). Thứ tự theo encoder.cc.
LOAI = ["p", "n", "b", "r", "q", "k", "a", "e", "h", "m", "v", "y", "s"]
TEN = {"p": "Tốt", "n": "Mã", "b": "Tượng", "r": "Xe", "q": "Hậu", "k": "Hoàng gia (tham khảo)", "a": "Amazon",
       "e": "Chancellor", "h": "Archbishop", "m": "Centaur", "v": "Wildebeest", "y": "Alibaba", "s": "Sergeant"}


def lan_nguoc(P, o, t, r, c):
    """Xoá quân (chủ o: 0 = bên đi, 1 = bên kia; loại t) đứng ô (r,c) khỏi P (đã là bản sao): bàn hiện tại rồi 7 bàn
    lịch sử. Trả về 'ok' hoặc 'phongcap' (không lần ngược được)."""
    off = o * 13 + t
    P[off, r, c] = 0.0
    # quyền nhập thành gắn với ô này
    for k in range(4):
        if P[tr.AUX_BASE + k, r, c] > 0 and ((o == 0 and k < 2) or (o == 1 and k >= 2)) and t == 3:
            P[tr.AUX_BASE + k, r, c] = 0.0
    cur = (r, c)
    for d in range(1, NHIST):
        nd = d * PPB + off
        if not P[d * PPB: d * PPB + 26].any():      # bàn lịch sử trống: hết lịch sử
            return "ok"
        if P[nd, cur[0], cur[1]] > 0:               # quân đứng yên ở nước này
            P[nd, cur[0], cur[1]] = 0.0
            continue
        # quân vừa đến ô cur ở nước này: ô nó rời đi = ô có trong bàn d mà không có trong bàn d-1 (gốc, chưa sửa)
        prev = G_GOC[(d - 1) * PPB + off]
        dep = (G_GOC[nd] > 0) & ~(prev > 0)
        sq = np.argwhere(dep)
        if len(sq) != 1:
            return "phongcap"
        cur = (int(sq[0][0]), int(sq[0][1]))
        P[nd, cur[0], cur[1]] = 0.0
    return "ok"


G_GOC = None   # các mặt phẳng gốc của thế đang xử lý (lan_nguoc đọc)


def chay(sess, X, bs):
    out = np.empty((len(X), 3), dtype=np.float32)
    for i in range(0, len(X), bs):
        out[i:i + bs] = sess.run(["value"], {"input": X[i:i + bs]})[0]
    return out


def pct(v, p):
    return float(np.percentile(v, p)) if len(v) else float("nan")


def main():
    global G_GOC
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--data", required=True, help="thư mục chứa games_gen*/ (các tệp .xz)")
    ap.add_argument("--keep", type=float, default=0.04, help="xác suất giữ mỗi thế")
    ap.add_argument("--max-positions", type=int, default=0, help="giới hạn số thế (0 = không)")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--threads", type=int, default=0)
    ap.add_argument("--batch", type=int, default=256)
    ap.add_argument("--raw", default="", help="ghi mọi lần xoá ra tệp .npz để phân tích thêm")
    a = ap.parse_args()

    import onnxruntime as ort
    so = ort.SessionOptions()
    so.intra_op_num_threads = a.threads or os.cpu_count()
    sess = ort.InferenceSession(a.model, so, providers=["CPUExecutionProvider"])

    files = sorted(glob.glob(os.path.join(a.data, "games_gen*", "*.xz")))
    rng = np.random.default_rng(a.seed)
    print(f"{len(files)} ván; giữ mỗi thế với xác suất {a.keep}", flush=True)

    # --- chọn thế ---
    chosen = []    # (tệp, chỉ số thế)
    tong = 0
    for f in files:
        n = sum(1 for _ in tr.iter_games([(f, None)], sparse=True))
        tong += n
        for i in np.nonzero(rng.random(n) < a.keep)[0]:
            chosen.append((f, int(i)))
    if a.max_positions and len(chosen) > a.max_positions:
        pick = np.sort(rng.choice(len(chosen), a.max_positions, replace=False))
        chosen = [chosen[i] for i in pick]
    print(f"tổng {tong} thế trong dữ liệu; lấy {len(chosen)} thế", flush=True)

    by_file = {}
    for f, i in chosen:
        by_file.setdefault(f, set()).add(i)

    rows = []       # (loại t, chủ o, q_trước, lệch, ply, w0,d0,l0, w1,d1,l1)
    bo_qua = {"phongcap": 0}
    t0 = time.time()
    done = 0
    pend_X, pend_meta = [], []

    def xu_ly_lo():
        nonlocal pend_X, pend_meta
        if not pend_X:
            return
        v = chay(sess, np.stack(pend_X), a.batch)
        for (o, t, q0, ply, wdl0), w in zip(pend_meta, v):
            q1 = float(w[0] - w[2])
            qa, qb = (q0, q1) if o == 0 else (-q0, -q1)
            rows.append((t, o, q0, qa - qb, ply, wdl0[0], wdl0[1], wdl0[2], w[0], w[1], w[2]))
        pend_X, pend_meta = [], []

    for f, want in by_file.items():
        for i, rec in enumerate(tr.iter_games([(f, None)], sparse=True)):
            if i not in want:
                continue
            P0 = tr.reconstruct_planes(rec)
            G_GOC = P0
            w0 = chay(sess, P0[None], 1)[0]
            q0 = float(w0[0] - w0[2])
            for o in (0, 1):
                for t in range(13):
                    pl = P0[o * 13 + t]
                    for r, c in np.argwhere(pl > 0):
                        P = P0.copy()
                        if lan_nguoc(P, o, t, int(r), int(c)) != "ok":
                            bo_qua["phongcap"] += 1
                            continue
                        pend_X.append(P)
                        pend_meta.append((o, t, q0, i, w0))
                        if len(pend_X) >= a.batch * 8:
                            xu_ly_lo()
            done += 1
            if done % 500 == 0:
                print(f"  {done}/{len(chosen)} thế, {len(rows)} lần xoá, {time.time() - t0:.0f}s", flush=True)
    xu_ly_lo()
    print(f"xong: {len(rows)} lần xoá, bỏ qua {bo_qua['phongcap']} (quân vừa phong cấp), {time.time() - t0:.0f}s\n")

    R = np.array(rows, dtype=np.float64)
    if a.raw:
        np.savez_compressed(a.raw, rows=R)
    t_, o_, q0_, dl_, ply_ = R[:, 0].astype(int), R[:, 1].astype(int), R[:, 2], R[:, 3], R[:, 4]

    def bang(mask, tieu_de):
        print(tieu_de)
        print(f"{'quân':<24}{'số lần':>9}{'p40':>8}{'p25':>8}{'trung vị':>9}{'p75':>8}{'TB':>8}{'tỉ lệ lệch>0':>14}")
        ds = []
        for t in range(13):
            m = mask & (t_ == t)
            if m.sum() == 0:
                continue
            v = dl_[m]
            ds.append((pct(v, 40), t, len(v), pct(v, 25), pct(v, 50), pct(v, 75), float(v.mean()), float((v > 0).mean())))
        for p40, t, n, p25, p50, p75, mean, pos in sorted(ds, key=lambda x: -x[0]):
            print(f"{TEN[LOAI[t]]:<24}{n:>9}{p40:>+8.3f}{p25:>+8.3f}{p50:>+9.3f}{p75:>+8.3f}{mean:>+8.3f}{pos * 100:>13.1f}%")
        pawn = [x for x in ds if x[1] == 0]
        if pawn and pawn[0][0] > 1e-6:
            print("  (p40 so với p40 của Tốt: " +
                  ", ".join(f"{TEN[LOAI[t]].split()[0]} {p40 / pawn[0][0]:.1f}" for p40, t, *_ in
                            sorted(ds, key=lambda x: -x[0]) if t not in (0, 5)) + ")")
        print()

    tat = np.ones(len(R), dtype=bool)
    bang(tat, "TẤT CẢ thế (kể cả thế đã nghiêng hẳn |q|~1: xoá quân không đổi gì vì mạng đã chắc kết quả)")
    cb = np.abs(q0_) < 0.5
    bang(cb, f"Thế CÒN CÂN BẰNG theo mạng (|q trước| < 0.5): {cb.sum()} lần xoá")
    bang((np.abs(q0_) < 0.9), f"Thế chưa quá nghiêng (|q trước| < 0.9): {(np.abs(q0_) < 0.9).sum()} lần xoá")

    print("Tách theo chủ quân, thế còn cân bằng (|q trước| < 0.5), p40 của độ lệch:")
    print(f"{'quân':<24}{'quân của bên ĐI':>18}{'quân của bên KIA':>18}")
    for t in range(13):
        m0 = cb & (t_ == t) & (o_ == 0)
        m1 = cb & (t_ == t) & (o_ == 1)
        if m0.sum() + m1.sum() == 0:
            continue
        print(f"{TEN[LOAI[t]]:<24}{pct(dl_[m0], 40):>+13.3f} ({m0.sum():>4}){pct(dl_[m1], 40):>+12.3f} ({m1.sum():>4})")


if __name__ == "__main__":
    main()
