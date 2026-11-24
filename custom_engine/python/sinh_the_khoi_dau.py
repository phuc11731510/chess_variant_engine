"""Bộ sinh thế cờ khởi đầu ngẫu nhiên (luật 2026-11-24, nhánh luat-moi).

Thế khởi đầu của MỖI bên có 30 quân (Đen đối xứng theo hàng: hàng 3 -> 8, hàng 2 -> 9, hàng 1 -> 10):
  * hàng 3: 10 Tốt `p`, cố định;
  * hàng 2: 5 Sergeant `s` theo một trong 6 cấu hình, bốc đều (S1S1S1S1S1, 1SS1S1S1S1, 1S1SS1S1S1, 1S1S1SS1S1,
    1S1S1S1SS1, 1S1S1S1S1S; chữ 1 là ô dành cho quân khác); Đen bốc cấu hình của mình độc lập với Trắng;
  * 15 quân còn lại xếp vào 15 ô quân (10 ô hàng 1 và 5 ô hàng 2): Hoàng gia, 2 Mã, 2 Xe, Hậu, 2 Tượng, 2 Centaur
    (10 quân cố định) + 4 quân bốc từ 8 quân nhảy (2 wildebeest, 2 Alibaba, 2 Pháo, 2 Grasshopper; bốc 4 quân
    trong 8 quân, KHÔNG xét loại) + 1 quân thêm, bốc đều một trong Hậu, Tượng, Xe, Centaur. Bộ quân (4 quân nhảy
    được giữ + quân thêm) bốc MỘT lần cho cả thế: Trắng và Đen có cùng bộ quân, chỉ khác cách xếp (hằng
    CUNG_BO_QUAN = False cho mỗi bên bốc bộ quân riêng).

Tiêu chí an toàn (của chủ dự án): nếu một bên đi hai nước liên tiếp bất kỳ mà bên kia đứng yên thì không có cách nào
ăn được quân nào (kể cả nước đầu). Ta kiểm cho cả Trắng và Đen. Thêm một ràng buộc vị trí: Hoàng gia chỉ đứng ở
hàng 1 (Đen: hàng 10).

Vì sao có thể đếm và lấy mẫu chính xác (không thử đi thử lại): hàng 3 kín Tốt, nên hàng 1 và hàng 2 của một bên
chỉ có thể đi nước đầu bằng quân nhảy; ba hàng của đối phương kín quân, bốn hàng giữa trống, nên khả năng ăn trong
hai nước của một bên chỉ phụ thuộc vào cách xếp của chính bên đó. Một chuỗi hai nước như vậy chỉ dùng tối đa
hai quân không phải Tốt/Sergeant, nên cách xếp hợp lệ khi và chỉ khi mọi quân đứng ở ô cho phép và không có cặp
(quân, ô) nào nằm trong danh sách cặp vi phạm. Suy ra (và `--kiem-lai-bang` kiểm lại bằng bộ kiểm hai nước, mọi
cấu hình Sergeant):
  1. Ở 5 ô quân của hàng 2 không được đứng Pháo (ăn ngay qua ngòi là Tốt hàng 3), Grasshopper (nhảy lên hàng 4 rồi
     nhảy qua Tốt hàng 8), wildebeest (nhảy lên hàng 5 rồi ăn Tốt hàng 8); Tượng và Hậu chỉ đứng được ở cột e, f vì
     ở các cột khác một Tốt hàng 3 tiến lên mở ra đường chéo tới Tốt hàng 8 của Đen. Mỗi cấu hình Sergeant có đúng
     một ô quân ở cột e hoặc f.
  2. Pháo ở hàng 1 không được đứng ngay dưới một Mã hoặc Alibaba của hàng 2 (quân nhảy rời đi ở nước đầu, Tốt hàng 3
     thành ngòi duy nhất, nước hai Pháo ăn Tốt hàng 8).
  3. Hoàng gia chỉ ở hàng 1 (ràng buộc vị trí, không phải an toàn).
Mọi chỗ còn lại của hàng 1 đều tự do. Cách xếp của một bên được bốc đều trên mọi cách xếp hợp lệ (số cách đếm
chính xác): bốc dãy 5 quân hàng 2 theo trọng số = số cách xếp hàng 1 đi kèm, rồi xếp hàng 1 ngẫu nhiên.

Cách dùng:
    python sinh_the_khoi_dau.py --n 20000 --seed 1 --out book.txt
    custom_engine --selfplay ... --start-fen book.txt      (mỗi ván lấy một dòng theo thứ tự vòng tròn)
Engine lấy dòng thứ g % (số dòng) cho ván g; các dòng do bộ sinh ghi là độc lập nên không cần xáo trộn.

Nếu luật quân đổi (luat_py.py là bản dịch Python của `src/tests/test_rules_oracle.cc`) thì chạy `--kiem-lai-bang`.
"""
import argparse
import bisect
import itertools
import math
import random
import sys
from collections import Counter, namedtuple

import luat_py as orc

# ----------------------------------------------------------------------------------------------------------
# Quân, cấu hình, hình học
# ----------------------------------------------------------------------------------------------------------
K_, N_, R_, Q_, B_, M_, V_, Y_, C_, G_ = orc.K_, orc.N_, orc.R_, orc.Q_, orc.B_, orc.M_, orc.V_, orc.Y_, orc.C_, orc.G_
P_, S_ = orc.P_, orc.S_
TYPES = (K_, N_, R_, Q_, B_, M_, V_, Y_, C_, G_)          # thứ tự của "bộ quân" (bộ đếm 10 số)
LETTER = {K_: "K", N_: "N", R_: "R", Q_: "Q", B_: "B", M_: "M", V_: "V", Y_: "Y", C_: "C", G_: "G", S_: "S", P_: "P"}
TYPE_OF = {v: k for k, v in LETTER.items()}

# 6 cấu hình Sergeant của hàng 2 (chữ S = Sergeant, chữ 1 = ô dành cho quân khác), cột a..j.
CAU_HINH = ("S1S1S1S1S1", "1SS1S1S1S1", "1S1SS1S1S1", "1S1S1SS1S1", "1S1S1S1SS1", "1S1S1S1S1S")
CUNG_BO_QUAN = True                       # True: Trắng và Đen cùng bộ quân (xem docstring); False: mỗi bên bốc riêng

BO_CO_DINH = (K_, N_, N_, R_, R_, Q_, B_, B_, M_, M_)     # 10 quân luôn có
NHAY = (V_, V_, Y_, Y_, C_, C_, G_, G_)                   # 8 quân nhảy, bốc 4 quân giữ lại
THEM = (Q_, B_, R_, M_)                                   # quân thêm: một trong bốn loại
COT_RONG = (4, 5)                                         # cột e, f: ô hàng 2 cho Tượng và Hậu đứng
NHAY_NEU_DUOI_PHAO = (N_, Y_)                             # quân hàng 2 rời đi được, mở ngòi cho Pháo hàng 1 ngay dưới nó
HANG2_HEP = (N_, R_, M_, Y_)                              # loại được đứng ở ô quân hàng 2 (cột khác e, f)
HANG2_RONG = (N_, R_, M_, Y_, Q_, B_)                     # ... ở cột e, f


def _kiem_cau_hinh():
    for s in CAU_HINH:
        assert len(s) == 10 and s.count("S") == 5 and set(s) <= {"S", "1"}, s


_kiem_cau_hinh()
SERG_COT = [tuple(i for i, ch in enumerate(s) if ch == "S") for s in CAU_HINH]
O_QUAN_COT = [tuple(i for i, ch in enumerate(s) if ch == "1") for s in CAU_HINH]      # 5 cột có ô quân ở hàng 2
RONG_COT = [tuple(c for c in cols if c in COT_RONG) for cols in O_QUAN_COT]           # trong đó cột e, f
HEP_COT = [tuple(c for c in cols if c not in COT_RONG) for cols in O_QUAN_COT]

# Ben: cấu hình Sergeant (chỉ số trong CAU_HINH), hàng 1 (10 loại quân, cột a..j), hàng 2 (10 phần tử: loại quân hoặc
# S_ ở ô Sergeant). Hàng 3 luôn là 10 Tốt nên không lưu.
Ben = namedtuple("Ben", "mau hang1 hang2")


def mirror_sq(s):
    return (9 - s // 10) * 10 + s % 10


def make_board(w, b):
    """Bàn cờ (100 ô, ô = hàng*10 + cột) của thế khởi đầu: Trắng w, Đen b (Đen nhìn từ phía Đen rồi lật hàng)."""
    bd = [0] * 100
    for f in range(10):
        bd[f], bd[10 + f], bd[20 + f] = w.hang1[f], w.hang2[f], P_
        bd[90 + f], bd[80 + f], bd[70 + f] = -b.hang1[f], -b.hang2[f], -P_
    return bd


def to_fen(w, b):
    return orc.to_fen(make_board(w, b), "w")


def mo_ta(side):
    """Chuỗi dễ đọc của một bên: 'hàng 2 / hàng 1' (chữ hoa là quân, S Sergeant)."""
    return "".join(LETTER[t] for t in side.hang2) + " / " + "".join(LETTER[t] for t in side.hang1)


# ----------------------------------------------------------------------------------------------------------
# Luật xếp hợp lệ của MỘT bên (đã suy luận, kiểm bằng bộ kiểm hai nước ở `tinh_bang` / `--kiem-lai-bang`)
# ----------------------------------------------------------------------------------------------------------
def hang2_cho_phep(cot):
    """Loại quân được đứng ở ô quân hàng 2 cột `cot` (an toàn hai nước; Hoàng gia bị loại bởi ràng buộc vị trí)."""
    return HANG2_RONG if cot in COT_RONG else HANG2_HEP


def an_toan_ben(side):
    """Luật an toàn hai nước cho cách xếp của một bên (không tính ràng buộc Hoàng gia)."""
    for c in range(10):
        t2 = side.hang2[c]
        # Hoàng gia ở hàng 2 thì bộ kiểm hai nước cho phép (ràng buộc vị trí mới cấm, xem hop_le_ben)
        if t2 != S_ and t2 != K_ and t2 not in hang2_cho_phep(c):
            return False
        if side.hang1[c] == C_ and t2 in NHAY_NEU_DUOI_PHAO:
            return False
    return True


def hop_le_ben(side):
    """An toàn hai nước + Hoàng gia chỉ ở hàng 1 + đủ quân ở đúng ô."""
    return K_ not in side.hang2 and an_toan_ben(side)


# ----------------------------------------------------------------------------------------------------------
# Bộ kiểm hai nước (đúng tiêu chí) và cách tính các bảng từ nó
# ----------------------------------------------------------------------------------------------------------
INERT = 13   # quân không đi được, không ăn được: chỉ để chiếm ô khi tính bảng


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


def kiem_the(w, b, hop_le=False):
    """Kiểm trực tiếp bằng bộ kiểm hai nước, cho cả hai bên. True nếu thế đạt tiêu chí an toàn."""
    bd = make_board(w, b)
    return not vi_pham(bd, orc.W, hop_le) and not vi_pham(bd, orc.BL, hop_le)


def _ban_trong(mau, white_map):
    """Thế mà các ô quân của Trắng không có trong white_map thì là quân INERT; Đen toàn quân INERT."""
    hang1 = [white_map.get(f, INERT) for f in range(10)]
    hang2 = [S_] * 10
    for c in O_QUAN_COT[mau]:
        hang2[c] = white_map.get(10 + c, INERT)
    w = Ben(mau, tuple(hang1), tuple(hang2))
    ink = Ben(mau, (INERT,) * 10, tuple(INERT if x != S_ else S_ for x in hang2))
    return make_board(w, ink)


def tinh_bang(mau):
    """Cho cấu hình Sergeant `mau`: (cấm_đơn, cặp). cấm_đơn[ô] = tập loại quân không được đứng ở ô quân;
    cặp = tập các ((ô1, loại1), (ô2, loại2)) (ô1 < ô2) không được cùng xuất hiện. Ô = hàng*10 + cột."""
    o_quan = list(range(10)) + [10 + c for c in O_QUAN_COT[mau]]
    cam = {s: set() for s in o_quan}
    for s in o_quan:
        for t in TYPES:
            if vi_pham(_ban_trong(mau, {s: t}), orc.W):
                cam[s].add(t)
    ok = [(s, t) for s in o_quan for t in TYPES if t not in cam[s]]
    cap = set()
    for (s1, t1), (s2, t2) in itertools.combinations(ok, 2):
        if s1 != s2 and vi_pham(_ban_trong(mau, {s1: t1, s2: t2}), orc.W):
            cap.add(tuple(sorted(((s1, t1), (s2, t2)))))
    return cam, cap


def bang_theo_luat(mau):
    """Hai bảng mà luật `an_toan_ben` ngụ ý (so với `tinh_bang`)."""
    o_quan = list(range(10)) + [10 + c for c in O_QUAN_COT[mau]]
    cam = {s: set() for s in o_quan}
    for c in O_QUAN_COT[mau]:
        cam[10 + c] = {t for t in TYPES if t not in hang2_cho_phep(c) and t != K_}
    cap = set()
    for c in O_QUAN_COT[mau]:
        for t in NHAY_NEU_DUOI_PHAO:
            cap.add(tuple(sorted(((c, C_), (10 + c, t)))))
    return cam, cap


# ----------------------------------------------------------------------------------------------------------
# Đếm và lấy mẫu chính xác một bên
# ----------------------------------------------------------------------------------------------------------
_BANG = {}


class _Bang:
    """Mọi dãy 5 quân hàng 2 hợp lệ cho một bộ quân và số ô cột e, f (xếp ô cột e, f trước), kèm trọng số = số cách
    xếp 10 quân còn lại ở hàng 1 (Pháo không đứng dưới Mã / Alibaba của hàng 2, tức đúng `10 - b` cột cho Pháo)."""
    __slots__ = ("day", "con", "cum", "tong")

    def __init__(self, bo, n_rong):
        dem = dict(zip(TYPES, bo))
        n_pha = dem[C_]
        khe = [HANG2_RONG] * n_rong + [HANG2_HEP] * (5 - n_rong)
        day, con, trong_so = [], [], []
        cur = []

        def rec(i, b_nhay):
            if i == 5:
                ngoai_pha = [t for t in TYPES if t != C_]
                mau = 1
                for t in ngoai_pha:
                    mau *= math.factorial(dem[t])
                trong_so.append(math.comb(10 - b_nhay, n_pha) * (math.factorial(10 - n_pha) // mau))
                day.append(tuple(cur))
                con.append(tuple(itertools.chain.from_iterable([t] * dem[t] for t in ngoai_pha)))
                return
            for t in khe[i]:
                if dem[t] <= 0:
                    continue
                dem[t] -= 1
                cur.append(t)
                rec(i + 1, b_nhay + (t in NHAY_NEU_DUOI_PHAO))
                cur.pop()
                dem[t] += 1

        rec(0, 0)
        self.day, self.con = day, con
        self.cum = list(itertools.accumulate(trong_so))
        self.tong = self.cum[-1]


def _bang(bo, n_rong):
    key = (bo, n_rong)
    t = _BANG.get(key)
    if t is None:
        t = _BANG[key] = _Bang(bo, n_rong)
    return t


def so_cach_xep(bo, mau=0):
    """Số cách xếp hợp lệ của MỘT bên (với một cấu hình Sergeant `mau`) cho bộ quân `bo` (bộ đếm 10 số theo TYPES)."""
    return _bang(bo, len(RONG_COT[mau])).tong


def lay_ben(bo, rng=random, mau=None):
    """Một cách xếp hợp lệ của một bên: cấu hình Sergeant bốc đều (hoặc `mau` cho trước), rồi cách xếp đồng đều trên
    mọi cách xếp hợp lệ của bộ quân `bo`. Trả về `Ben`."""
    if mau is None:
        mau = rng.randrange(len(CAU_HINH))
    rong, hep = RONG_COT[mau], HEP_COT[mau]
    bg = _bang(bo, len(rong))
    i = bisect.bisect_right(bg.cum, rng.randrange(bg.tong))
    cols = rong + hep
    hang2 = [S_] * 10
    cam_pha = set()
    for c, t in zip(cols, bg.day[i]):
        hang2[c] = t
        if t in NHAY_NEU_DUOI_PHAO:
            cam_pha.add(c)
    hang1 = [0] * 10
    n_pha = bo[TYPES.index(C_)]
    if n_pha:
        cho = [c for c in range(10) if c not in cam_pha]
        for c in rng.sample(cho, n_pha):
            hang1[c] = C_
    con = list(bg.con[i])
    rng.shuffle(con)
    it = iter(con)
    for c in range(10):
        if not hang1[c]:
            hang1[c] = next(it)
    return Ben(mau, tuple(hang1), tuple(hang2))


# ----------------------------------------------------------------------------------------------------------
# Bộ quân
# ----------------------------------------------------------------------------------------------------------
def dem_bo(*loai):
    c = Counter(loai)
    return tuple(c.get(t, 0) for t in TYPES)


def lay_bo_quan(rng=random):
    """Bộ quân của một bên (bộ đếm 10 số theo TYPES): 10 quân cố định + 4 quân bốc từ 8 quân nhảy (bốc 4 quân trong
    8 quân, không xét loại) + 1 quân thêm (một trong Hậu, Tượng, Xe, Centaur)."""
    giu = [NHAY[i] for i in rng.sample(range(8), 4)]
    return dem_bo(*BO_CO_DINH, *giu, rng.choice(THEM))


def phan_bo_bo_quan():
    """{bộ quân: xác suất} chính xác của `lay_bo_quan`."""
    kq = Counter()
    for giu in itertools.combinations(range(8), 4):
        for them in THEM:
            kq[dem_bo(*BO_CO_DINH, *(NHAY[i] for i in giu), them)] += 1
    tong = sum(kq.values())
    return {bo: n / tong for bo, n in kq.items()}


def lay_the(rng=random):
    """(FEN, Trắng, Đen): hai bên xếp độc lập, cùng bộ quân (CUNG_BO_QUAN)."""
    bo = lay_bo_quan(rng)
    w = lay_ben(bo, rng)
    b = lay_ben(bo if CUNG_BO_QUAN else lay_bo_quan(rng), rng)
    return to_fen(w, b), w, b


# ----------------------------------------------------------------------------------------------------------
def thong_ke():
    pb = phan_bo_bo_quan()
    h_bo = -sum(p * math.log2(p) for p in pb.values())
    cnt = {bo: so_cach_xep(bo) for bo in pb}
    e_log = sum(p * math.log2(6 * cnt[bo]) for bo, p in pb.items())
    lo, hi = min(cnt.values()), max(cnt.values())
    print(f"{len(pb)} bộ quân khác nhau, entropy bộ quân {h_bo:.2f} bit")
    print(f"số cách xếp hợp lệ mỗi bên (một cấu hình Sergeant): từ {lo:,} đến {hi:,}")
    if CUNG_BO_QUAN:
        print(f"entropy thế khởi đầu ~ {h_bo + 2 * e_log:.1f} bit (bộ quân + 2 x (6 cấu hình x cách xếp))")
    else:
        print(f"entropy thế khởi đầu ~ {2 * h_bo + 2 * e_log:.1f} bit (mỗi bên bốc bộ quân riêng)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--n", type=int, default=10, help="số thế cần sinh")
    ap.add_argument("--seed", type=int, default=None, help="hạt giống (bỏ trống = ngẫu nhiên mỗi lần chạy)")
    ap.add_argument("--out", default="", help="tệp ra (mỗi dòng một FEN); bỏ trống = in ra màn hình")
    ap.add_argument("--kiem-lai-bang", action="store_true", help="tính lại các bảng bằng bộ kiểm hai nước (mọi cấu hình Sergeant) và so với luật")
    ap.add_argument("--thong-ke", action="store_true", help="in số bộ quân, số cách xếp và entropy")
    args = ap.parse_args()
    if args.kiem_lai_bang:
        for mau in range(len(CAU_HINH)):
            cam, cap = tinh_bang(mau)
            cam_l, cap_l = bang_theo_luat(mau)
            ok = cam == cam_l and cap == cap_l
            print(f"{CAU_HINH[mau]}: luật {'KHỚP' if ok else 'LỆCH'} với bộ kiểm hai nước ({len(cap)} cặp vi phạm)")
            if not ok:
                print("  cấm đơn tính lại:", {orc.sqname(s): "".join(sorted(LETTER[t] for t in v)) for s, v in cam.items() if v})
                print("  cặp tính lại:", sorted(f"{LETTER[a[1]]}@{orc.sqname(a[0])}+{LETTER[b[1]]}@{orc.sqname(b[0])}" for a, b in cap))
                return 1
    if args.thong_ke:
        thong_ke()
    rng = random.Random(args.seed) if args.seed is not None else random.SystemRandom()
    out = open(args.out, "w", encoding="utf-8", newline="\n") if args.out else sys.stdout
    for _ in range(args.n):
        out.write(lay_the(rng)[0] + "\n")
    if args.out:
        out.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
