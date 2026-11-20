"""Bộ sinh thế cờ khởi đầu ngẫu nhiên cho luật mới (nhánh luat-moi).

Thế khởi đầu: Tốt `p` (8 quân, hàng 3, cột b..i) và Sergeant `s` (4 quân, hàng 2, cột b d g i) đứng cố định như
luật cũ, cho cả hai bên (Đen đối xứng theo hàng). 18 quân còn lại của mỗi bên (Hoàng gia 1, Mã 2, Xe 2, Hậu 1,
Tượng 2, Centaur 2, wildebeest 2, Alibaba 2, Pháo 2, Grasshopper 2) được xếp ngẫu nhiên vào 18 ô còn lại của ba
hàng dưới (hàng 1: 10 ô; hàng 2: cột a c e f h j; hàng 3: cột a và j). Hai bên xếp độc lập, không cần đối xứng.

Tiêu chí (của chủ dự án): nếu một bên đi hai nước liên tiếp bất kỳ mà bên kia đứng yên thì không có cách nào ăn được
quân nào (kể cả nước đầu). Ta kiểm cho cả Trắng và Đen.

Vì sao có thể đếm và lấy mẫu chính xác (không thử đi thử lại): ba hàng của đối phương kín quân, bốn hàng giữa trống,
nên khả năng ăn trong hai nước của một bên chỉ phụ thuộc vào cách xếp của chính bên đó. Một chuỗi hai nước như vậy
chỉ dùng tối đa hai quân không phải Tốt/Sergeant, nên cách xếp hợp lệ khi và chỉ khi (1) mỗi quân đứng ở ô cho phép
và (2) không có cặp (quân, ô) nào nằm trong danh sách cặp vi phạm. Hai danh sách này được tính bằng chính bộ kiểm
hai nước (`tinh_bang`) và chép sẵn bên dưới; `--kiem-lai-bang` tính lại và so sánh.

Cách dùng:
    python sinh_the_khoi_dau.py --n 20000 --seed 1 --out book.txt
    custom_engine --selfplay ... --start-fen book.txt      (mỗi ván lấy một dòng theo thứ tự vòng tròn)
Engine lấy dòng thứ g % (số dòng) cho ván g; các dòng do bộ sinh ghi là độc lập nên không cần xáo trộn.

Nếu luật quân đổi (luat_py.py là bản dịch Python của `src/tests/test_rules_oracle.cc`) thì chạy `--kiem-lai-bang`
và chép lại hai bảng.
"""
import argparse
import bisect
import itertools
import math
import random
import sys
from collections import Counter

import luat_py as orc

# ----------------------------------------------------------------------------------------------------------
# Hình học
# ----------------------------------------------------------------------------------------------------------
# Ô = hàng * 10 + cột (hàng 0..9 là hàng 1..10, cột 0..9 là a..j).
FREE_SQ = [f for f in range(10)] + [10 + f for f in (0, 2, 4, 5, 7, 9)] + [20 + 0, 20 + 9]
PAWN_SQ = [20 + f for f in range(1, 9)]          # b3..i3
SERG_SQ = [10 + f for f in (1, 3, 6, 8)]         # b2 d2 g2 i2
TYPE_OF = {"K": orc.K_, "N": orc.N_, "R": orc.R_, "Q": orc.Q_, "B": orc.B_, "M": orc.M_, "V": orc.V_, "Y": orc.Y_,
           "C": orc.C_, "G": orc.G_}
LETTER = {v: k for k, v in TYPE_OF.items()}
TYPES = list(TYPE_OF.values())
POOL = [orc.K_] + [orc.N_] * 2 + [orc.R_] * 2 + [orc.Q_] + [orc.B_] * 2 + [orc.M_] * 2 + [orc.V_] * 2 + \
       [orc.Y_] * 2 + [orc.C_] * 2 + [orc.G_] * 2
assert len(POOL) == len(FREE_SQ) == 18
INERT = 13   # quân không đi được, không ăn được: chỉ để chiếm ô khi tính bảng


def sq(name):
    return (int(name[1:]) - 1) * 10 + ord(name[0]) - 97


def sqn(s):
    return orc.sqname(s)


def mirror_sq(s):
    return (9 - s // 10) * 10 + s % 10


def make_board(arr_white, arr_black):
    """arr_*: 18 loại quân theo thứ tự FREE_SQ (Đen nhìn từ phía Đen, rồi lật hàng)."""
    b = [0] * 100
    for s in PAWN_SQ:
        b[s] = orc.P_
        b[mirror_sq(s)] = -orc.P_
    for s in SERG_SQ:
        b[s] = orc.S_
        b[mirror_sq(s)] = -orc.S_
    for s, t in zip(FREE_SQ, arr_white):
        b[s] = t
    for s, t in zip(FREE_SQ, arr_black):
        b[mirror_sq(s)] = -t
    return b


def to_fen(arr_white, arr_black):
    return orc.to_fen(make_board(arr_white, arr_black), "w")


# ----------------------------------------------------------------------------------------------------------
# Bộ kiểm hai nước (đúng tiêu chí) và cách tính hai bảng
# ----------------------------------------------------------------------------------------------------------
def vi_pham(b, ben, hop_le=False):
    """True nếu `ben` đi hai nước liên tiếp (bên kia đứng yên) có thể ăn một quân, kể cả ở nước đầu.
    hop_le=False: nước giả-hợp-lệ (không xét Hoàng gia bị chiếu); True: nước hợp lệ thật."""
    gen = orc.gen_legal if hop_le else orc.gen_pseudo
    m1 = gen(b, ben)
    for m in m1:
        if b[m[1]]:
            return True
    for m in m1:
        nb = orc.apply(b, m)
        for m2 in gen(nb, ben):
            if nb[m2[1]]:
                return True
    return False


def _ban_trong(white_map):
    """Thế mà các ô tự do không có trong white_map và toàn bộ phía Đen là quân INERT."""
    b = [0] * 100
    for s in PAWN_SQ:
        b[s] = orc.P_
        b[mirror_sq(s)] = -orc.P_
    for s in SERG_SQ:
        b[s] = orc.S_
        b[mirror_sq(s)] = -orc.S_
    for s in FREE_SQ:
        b[s] = white_map.get(s, INERT)
        b[mirror_sq(s)] = -INERT
    return b


def tinh_bang():
    """Trả về (cấm_đơn, cặp): cấm_đơn[ô] = tập loại quân không được đứng ở ô; cặp = tập các
    ((ô1, loại1), (ô2, loại2)) (ô1 < ô2) không được cùng xuất hiện."""
    cam = {s: set() for s in FREE_SQ}
    for s in FREE_SQ:
        for t in TYPES:
            if vi_pham(_ban_trong({s: t}), orc.W):
                cam[s].add(t)
    ok = [(s, t) for s in FREE_SQ for t in TYPES if t not in cam[s]]
    cap = set()
    for (s1, t1), (s2, t2) in itertools.combinations(ok, 2):
        if s1 != s2 and vi_pham(_ban_trong({s1: t1, s2: t2}), orc.W):
            cap.add(tuple(sorted(((s1, t1), (s2, t2)))))
    return cam, cap


# ----------------------------------------------------------------------------------------------------------
# Hai bảng đã tính (chép từ `tinh_bang()` ngày 2026-11-20, luật quân của luat-moi)
# ----------------------------------------------------------------------------------------------------------
_CAM_DON_TEXT = {
    "a2": "BCGQV",
    "c2": "BCGQV",
    "e2": "CGV",
    "f2": "CGV",
    "h2": "BCGQV",
    "j2": "BCGQV",
    "a3": "BCGQRV",
    "j3": "BCGQRV",
}
_CAP_TEXT = [
    "C@a1+N@a2",
    "C@a1+Y@a2",
    "C@a1+N@a3",
    "C@a1+K@a3",
    "C@a1+M@a3",
    "C@a1+Y@a3",
    "C@c1+N@c2",
    "C@c1+Y@c2",
    "C@e1+N@e2",
    "C@e1+Y@e2",
    "C@f1+N@f2",
    "C@f1+Y@f2",
    "C@h1+N@h2",
    "C@h1+Y@h2",
    "C@j1+N@j2",
    "C@j1+Y@j2",
    "C@j1+N@j3",
    "C@j1+K@j3",
    "C@j1+M@j3",
    "C@j1+Y@j3",
    "R@a2+N@a3",
    "R@a2+K@a3",
    "R@a2+M@a3",
    "R@a2+Y@a3",
    "R@j2+N@j3",
    "R@j2+K@j3",
    "R@j2+M@j3",
    "R@j2+Y@j3",
]


def _doc_bang():
    cam = {sq(k): {TYPE_OF[c] for c in v} for k, v in _CAM_DON_TEXT.items()}
    for s in FREE_SQ:
        cam.setdefault(s, set())
    cap = set()
    for text in _CAP_TEXT:
        a, b = text.split("+")
        x = (sq(a[2:]), TYPE_OF[a[0]])
        y = (sq(b[2:]), TYPE_OF[b[0]])
        cap.add(tuple(sorted((x, y))))
    return cam, cap


CAM_DON, CAP_VI_PHAM = _doc_bang()


def hop_le_theo_bang(arr):
    """Cách xếp (18 loại theo thứ tự FREE_SQ) có thoả hai bảng không."""
    items = list(zip(FREE_SQ, arr))
    for s, t in items:
        if t in CAM_DON[s]:
            return False
    for x, y in itertools.combinations(items, 2):
        if tuple(sorted((x, y))) in CAP_VI_PHAM:
            return False
    return True


# ----------------------------------------------------------------------------------------------------------
# Đếm và lấy mẫu chính xác
# ----------------------------------------------------------------------------------------------------------
_HANG1 = [s for s in FREE_SQ if s // 10 == 0]
_TREN = [s for s in FREE_SQ if s // 10 != 0]        # 8 ô hàng 2-3
_MIEN = {s: [t for t in TYPES if t not in CAM_DON[s]] for s in FREE_SQ}


def _dung_cau_truc():
    """Mọi cặp vi phạm hoặc là (Pháo ở hàng 1, quân ở hàng 2-3) hoặc nằm hết ở hàng 2-3; quân V, C, G chỉ đứng
    được ở hàng 1. Hai điều này làm cho bộ đếm bên dưới đúng; kiểm lại mỗi khi bảng đổi."""
    phao_cam, tren_tren = {}, set()
    for x, y in CAP_VI_PHAM:
        hx, hy = x[0] // 10, y[0] // 10
        if hx == 0 or hy == 0:
            c, o = (x, y) if hx == 0 else (y, x)
            if not (c[1] == orc.C_ and o[0] // 10 != 0):
                raise AssertionError("cặp vi phạm không phải (Pháo hàng 1, quân hàng trên): đổi bộ đếm")
            phao_cam.setdefault(c[0], set()).add(o)
        else:
            tren_tren.add((x, y))
    for t in (orc.V_, orc.G_, orc.C_):
        if any(t in _MIEN[s] for s in _TREN):
            raise AssertionError("V, C, G phải chỉ đứng được ở hàng 1: đổi bộ đếm")
    return phao_cam, tren_tren


_PHAO_CAM, _TREN_TREN = _dung_cau_truc()
_DA_XAY = None


def _xay():
    """Liệt kê mọi cách xếp 8 ô hàng 2-3 hợp lệ và trọng số = số cách xếp hàng 1 đi kèm."""
    con = Counter(POOL)
    for t in (orc.V_, orc.C_, orc.G_):
        con[t] = 0
    cfgs = []

    def rec(i, cur, cnt):
        if i == len(_TREN):
            cfgs.append(tuple(cur))
            return
        s = _TREN[i]
        for t in _MIEN[s]:
            if cnt.get(t, 0) <= 0:
                continue
            if any(tuple(sorted(((_TREN[j], cur[j]), (s, t)))) in _TREN_TREN for j in range(i)):
                continue
            cnt[t] -= 1
            cur.append(t)
            rec(i + 1, cur, cnt)
            cur.pop()
            cnt[t] += 1

    rec(0, [], dict(con))
    bang, trong_so = [], []
    for cur in cfgs:
        con_lai = Counter(POOL)
        for t in cur:
            con_lai[t] -= 1
        here = set(zip(_TREN, cur))
        phep = [s for s in _HANG1 if not (_PHAO_CAM.get(s, set()) & here)]
        k = len(phep)
        khac = Counter(con_lai)
        khac[orc.C_] = 0
        khac = +khac
        mau = 1
        for v in khac.values():
            mau *= math.factorial(v)
        trong_so.append(k * (k - 1) // 2 * (math.factorial(8) // mau))
        bang.append((cur, phep, sorted(khac.elements())))
    return bang, trong_so


def _dam_bao():
    global _DA_XAY
    if _DA_XAY is None:
        bang, ts = _xay()
        _DA_XAY = (bang, ts, list(itertools.accumulate(ts)))
    return _DA_XAY


def so_cach_xep():
    """Số cách xếp hợp lệ cho MỘT bên (chính xác)."""
    return _dam_bao()[2][-1]


def lay_mau(rng=random):
    """Một cách xếp hợp lệ của một bên, đồng đều trên mọi cách xếp hợp lệ. Trả về 18 loại theo thứ tự FREE_SQ."""
    bang, _, cum = _dam_bao()
    i = bisect.bisect_right(cum, rng.randrange(cum[-1]))
    cur, phep, con = bang[i]
    c1, c2 = rng.sample(phep, 2)
    o_con_lai = [s for s in _HANG1 if s != c1 and s != c2]
    con = list(con)
    rng.shuffle(con)
    asg = dict(zip(_TREN, cur))
    asg[c1] = asg[c2] = orc.C_
    asg.update(zip(o_con_lai, con))
    return [asg[s] for s in FREE_SQ]


def lay_the(rng=random):
    """(FEN, cách xếp Trắng, cách xếp Đen). Hai bên độc lập."""
    aw, ab = lay_mau(rng), lay_mau(rng)
    return to_fen(aw, ab), aw, ab


def kiem_the(aw, ab, hop_le=False):
    """Kiểm trực tiếp bằng bộ kiểm hai nước, cho cả hai bên. True nếu thế đạt tiêu chí."""
    b = make_board(aw, ab)
    return not vi_pham(b, orc.W, hop_le) and not vi_pham(b, orc.BL, hop_le)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--n", type=int, default=10, help="số thế cần sinh")
    ap.add_argument("--seed", type=int, default=None, help="hạt giống (bỏ trống = ngẫu nhiên mỗi lần chạy)")
    ap.add_argument("--out", default="", help="tệp ra (mỗi dòng một FEN); bỏ trống = in ra màn hình")
    ap.add_argument("--kiem-lai-bang", action="store_true", help="tính lại hai bảng bằng bộ kiểm hai nước và so với bảng chép sẵn")
    ap.add_argument("--thong-ke", action="store_true", help="in số cách xếp và entropy")
    args = ap.parse_args()
    if args.kiem_lai_bang:
        cam, cap = tinh_bang()
        same = cam == {s: set(CAM_DON[s]) for s in FREE_SQ} and cap == CAP_VI_PHAM
        print("bảng chép sẵn", "KHỚP" if same else "LỆCH", "với bộ kiểm hai nước:", len(cap), "cặp vi phạm")
        if not same:
            print("cấm đơn tính lại:", {sqn(s): "".join(sorted(LETTER[t] for t in v)) for s, v in cam.items() if v})
            print("cặp tính lại:", sorted(f"{LETTER[a[1]]}@{sqn(a[0])}+{LETTER[b[1]]}@{sqn(b[0])}" for a, b in cap))
            return 1
    if args.thong_ke:
        v = so_cach_xep()
        print(f"số cách xếp hợp lệ mỗi bên = {v} (~{v:.3e}); mỗi bên {math.log2(v):.2f} bit; số thế khởi đầu = {v * v:.3e}")
    rng = random.Random(args.seed) if args.seed is not None else random.SystemRandom()
    out = open(args.out, "w", encoding="utf-8", newline="\n") if args.out else sys.stdout
    for _ in range(args.n):
        out.write(lay_the(rng)[0] + "\n")
    if args.out:
        out.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
