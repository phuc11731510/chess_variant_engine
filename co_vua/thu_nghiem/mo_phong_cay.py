"""mo_phong_cay.py -- mô phỏng cây trò chơi trên một "thế giới giả" có giá trị thật biết trước.

Mục đích (THIET_KE_CO_VUA.md phần 14, chủ dự án cho bắt đầu 5/11): kiểm các công thức của phần 4, 5, 7 trước khi
viết mã thật, ở chỗ mà dữ liệu thật không cho biết đáp án:
  1. E (độ sai dự báo của G) có khớp với sai số thật (G - V)^2 không -- phương án A (omega^2 chung, 4.2) và
     phương án B (độ toả tại node, 4.4).
  2. Cách ước lượng tau_q^2 (chỉ từ node có E nhỏ, phần 5) so với tau_q^2 thật; cách gộp cả cây.
  3. Nhãn value mới (w_q q + (1-w_q) G) so với nhãn kiểu truyền thống (0.2 q + 0.8 z) -- sai số so với V thật.
  4. Nhãn policy mới pi' (7.2) so với pi -- giá trị thật kỳ vọng của nước theo nhãn, tỉ lệ trúng nước tốt nhất.

Thế giới giả (mọi giá trị theo góc Trắng, Trắng đi ở độ sâu chẵn):
  - Mỗi thế cờ có K nước. Giá trị thật V của các thế cờ con dao động quanh V của cha và trung bình theo chính sách
    thật p (softmax theo giá trị của bên đi) đúng bằng V của cha, nên V(s) = kết quả trung bình nếu chơi tiếp theo p.
    Độ toả nhỏ dần khi V gần ±1 (hệ số 1 - V^2) để V nằm trong [-1, 1].
  - Ván kết thúc ngẫu nhiên (mỗi nửa nước xác suất P_HET), kết quả +1/0/-1 rút một lần với trung bình V của node cuối.
  - "Search" tại một thế cờ: Q của mỗi nước = V thật + lệch cố định của mạng (một số node có một nước bị mạng
    đánh giá cao sai) + nhiễu mỗi lần search; tỉ lệ lượt thăm = softmax theo Q, trộn nhiễu Dirichlet, rồi rút 800
    lượt. Như search thật, nó ít nhiễu nhưng có thể lệch.
  - Cây trò chơi: đời 0 chơi R0 ván từ gốc (mỗi ván search lại mọi thế cờ nó đi qua); các đời sau quét cây với
    temperature 0.5 (6.1), xáo trộn điểm rẽ, chơi tới hết ngân sách (6.3); ván luôn đi nước nhiều lượt thăm nhất.
    Thế giới không đổi qua các đời (mạng không học), nên không có cắt lá, không giảm gamma.

Chạy:  py mo_phong_cay.py [--seed 1] [--doi 4] [--ngan-sach 40000] [--r0 300] [--lech 0.05]
"""
import argparse
import time

import numpy as np

K = 10            # số nước mỗi thế cờ
D_MAX = 3000      # gần như không giới hạn: giá trị thật của thế giới giả không biết luật hoà khi chạm giới hạn, nên giới hạn thấp làm hỏng phép đo (chẩn đoán 7/11)
OMEGA2 = 0.006    # độ toả giá trị thật giữa các nước ở thế cân bằng (tổng dọc ~100 nửa nước cỡ 0.6 như đo thật)
SAC = 1.5         # độ sắc của chính sách thật (gần đời 0: nước nhiều nhất ~25%)
P_HOA = 0.05      # mỗi nửa nước sau nửa nước 40, thế gần cân bằng (|V| < 0.05) có xác suất này kết thúc hoà
_u = np.random.default_rng(12345).normal(size=(20000, K))
_p = np.exp(SAC * _u); _p /= _p.sum(1, keepdims=True)
SIG0 = float(np.sqrt(OMEGA2 / ((_p * (_u - (_p * _u).sum(1, keepdims=True)) ** 2).sum(1)).mean()))
NHIEU_Q = 0.045   # nhiễu giá trị search mỗi lần (tau_d ~ sqrt(0.002) ở 7.2)
LECH = 0.30       # độ lệch cố định của nước bị mạng đánh giá sai
EPS, ALPHA, VISITS, C_PUCT = 0.25, 0.3, 800, 1.3


class The:
    """Cây + thế giới giả, lưu bằng mảng cấp sẵn."""

    def __init__(self, n_max, rng, ty_le_lech):
        self.rng, self.ty_le_lech, self.n = rng, ty_le_lech, 0
        self.cha = np.full(n_max, -1, np.int64)
        self.sau = np.zeros(n_max, np.int32)
        self.V = np.zeros(n_max)
        self.het = np.zeros(n_max, bool)
        self.z = np.zeros(n_max)
        self.z_van = np.full(n_max, np.nan)      # kết quả ván đầu tiên tạo ra node (nhãn kiểu truyền thống)
        self.m = np.zeros(n_max)
        self.co_con = np.zeros(n_max, bool)      # đã sinh giá trị con chưa
        self.Vc = np.zeros((n_max, K))           # giá trị thật của các con
        self.p = np.zeros((n_max, K))            # chính sách thật
        self.lech = np.zeros((n_max, K))         # lệch cố định của mạng (góc bên đi)
        self.n_sum = np.zeros((n_max, K))        # tổng lượt thăm qua các lần search (phần 3, nhóm 1)
        self.nq_sum = np.zeros((n_max, K))       # tổng lượt thăm x Q (góc Trắng)
        self.k = np.zeros(n_max)                 # số lần search
        self.con = [dict() for _ in range(n_max)]
        self.so_search = 0

    def dau(self, s):
        return 1.0 if self.sau[s] % 2 == 0 else -1.0

    def tao(self, cha, nuoc, V):
        s = self.n
        self.n += 1
        self.cha[s], self.V[s] = cha, V
        self.sau[s] = 0 if cha < 0 else self.sau[cha] + 1
        # Kết thúc theo "luật": thế đã gần như thắng/thua chắc (|V| >= 0.99) -> kết quả +1/-1 rút với trung bình đúng
        # bằng V (độ dao động ở lá <= 0.02); thế cân bằng (|V| < 0.02) sau nửa nước 40 thỉnh thoảng thành hoà.
        # Nhờ vậy V luôn đúng là kết quả trung bình khi chơi tiếp theo p, và kết quả ở lá gần như chắc chắn như cờ
        # thật (E = 0 ở lá). (Bản 5/11 dùng ngưỡng 0.95 -> luôn +1, làm V gần cuối ván không còn là kết quả trung bình.)
        if cha >= 0:
            if abs(V) >= 0.99:
                self.het[s], self.z[s] = True, (1.0 if self.rng.random() < (1 + V) / 2 else -1.0)
            elif self.sau[s] >= 40 and abs(V) < 0.02 and self.rng.random() < P_HOA:
                self.het[s], self.z[s] = True, 0.0
            elif self.sau[s] >= D_MAX:
                self.het[s], self.z[s] = True, 0.0
        if cha >= 0:
            self.con[cha][nuoc] = s
        return s

    def sinh_con(self, s):
        sg, V = self.dau(s), self.V[s]
        u = self.rng.normal(size=K)
        p = np.exp(SAC * u)
        p /= p.sum()
        sig = SIG0 * np.sqrt(max(1 - V * V, 0.0))
        Vc = V + sg * sig * (u - (p * u).sum())          # trung bình theo p đúng bằng V
        self.Vc[s], self.p[s] = np.clip(Vc, -0.999, 0.999), p
        if self.rng.random() < self.ty_le_lech:
            self.lech[s, self.rng.integers(K)] = LECH
        self.co_con[s] = True

    def search(self, s):
        """Một lần search: trả về lượt thăm của lần này; cộng vào trung bình của node."""
        if not self.co_con[s]:
            self.sinh_con(s)
        sg, V = self.dau(s), self.V[s]
        sig = max(SIG0 * np.sqrt(max(1 - V * V, 0.0)), 1e-6)
        q_ben = sg * self.Vc[s] + self.lech[s] + self.rng.normal(0, NHIEU_Q, K)
        x = SAC * (q_ben - q_ben.mean()) / sig
        pi = np.exp(x - x.max())
        pi /= pi.sum()
        pi = (1 - EPS) * pi + EPS * self.rng.dirichlet(np.full(K, ALPHA))
        n = self.rng.multinomial(VISITS, pi).astype(float)
        self.n_sum[s] += n
        self.nq_sum[s] += n * sg * q_ben               # lưu Q theo góc Trắng
        self.k[s] += 1
        self.so_search += 1
        return n

    def choi(self, s, search_lai_duong):
        """Chơi từ node s tới hết ván (nước nhiều lượt thăm nhất). Trả về danh sách node đã đi qua."""
        duong = [s]
        moi = []
        while not self.het[s]:
            if search_lai_duong or self.k[s] == 0:
                n = self.search(s)
            else:
                n = self.n_sum[s]
            a = int(np.argmax(n))
            c = self.con[s].get(a)
            if c is None:
                c = self.tao(s, a, self.Vc[s, a])
                moi.append(c)
            s = c
            duong.append(s)
        z = self.z[s]
        for x in moi:
            self.z_van[x] = z
        return duong

    def ghi_van(self, duong):
        goc = duong[0]
        while self.cha[goc] >= 0:                       # mọi node từ gốc tới điểm bắt đầu cũng có thêm một ván
            goc = self.cha[goc]
            self.m[goc] += 1
        self.m[np.array(duong)] += 1


def chay(a):
    rng = np.random.default_rng(a.seed)
    T = The(a.r0 * 1200 + a.doi * a.ngan_sach * 2 + 1000, rng, a.lech)
    goc = T.tao(-1, 0, 0.0)
    T.z_van[goc] = np.nan
    t0 = time.time()
    # Đời 0: các ván từ gốc, search lại mọi thế cờ đi qua (như các ván đầu đời 0 của thiết kế 6.2).
    tong_u, z_goc = [], []
    for _ in range(a.r0):
        d = T.choi(goc, True)
        T.ghi_van(d)
        z_goc.append(T.z[d[-1]])
    # Các đời sau: quét, xáo trộn, chơi tới hết ngân sách (tính bằng số lần search).
    for g in range(a.doi):
        diem = []
        for s in range(T.n):
            if T.het[s] or T.k[s] == 0:
                continue
            w = T.n_sum[s] ** 2
            x = int(rng.choice(K, p=w / w.sum()))
            if x not in T.con[s]:
                diem.append((s, x))
        rng.shuffle(diem)
        dau = T.so_search
        for s, x in diem:
            if T.so_search - dau >= a.ngan_sach:
                break
            if x in T.con[s]:
                continue
            c = T.tao(s, x, T.Vc[s, x])
            d = T.choi(c, False)
            T.ghi_van([s] + d)
    print(f"cây: {T.n} node, {T.so_search} lần search, {int(T.m[goc])} ván qua gốc, {time.time() - t0:.1f} giây")
    return T, np.array(z_goc)


def bang_hoa(T):
    """Tỉ lệ ván hoà theo |q| (10 nhóm), đếm trên chính các ván của cây: thay cho xác suất hoà mà search của lc0
    cho sẵn (best_d) -- search giả của mô phỏng chỉ cho Q."""
    n = T.n
    ns = T.n_sum[:n]
    Qw = np.where(ns > 0, T.nq_sum[:n] / np.maximum(ns, 1e-12), 0.0)
    q = Qw[np.arange(n), ns.argmax(1)]
    co = ~T.het[:n] & (T.k[:n] > 0) & ~np.isnan(T.z_van[:n])
    bien = np.quantile(np.abs(q[co]), np.linspace(0, 1, 11))
    nhom = np.clip(np.searchsorted(bien, np.abs(q), side="right") - 1, 0, 9)
    ty = np.array([np.mean(T.z_van[:n][co & (nhom == i)] == 0) if (co & (nhom == i)).any() else 0.3 for i in range(10)])
    return q, ty[nhom]


def tinh(T, omega2_A):
    """G, E theo phương án A (omega^2 chung), B (độ toả tại node), C (độ chênh đo thẳng), D (B có trần tự nhiên)."""
    n = T.n
    q_all, hoa_all = bang_hoa(T)
    G = {k: np.zeros(n) for k in "ABCD"}
    E = {k: np.zeros(n) for k in "ABCD"}
    rho_ = {k: [None] * n for k in "ABCD"}
    for s in np.argsort(-T.sau[:n], kind="stable"):
        if T.het[s]:
            for k in "ABCD":
                G[k][s], E[k][s] = T.z[s], 0.0
            continue
        ns = T.n_sum[s]
        pi = ns / ns.sum()
        Q = np.where(ns > 0, T.nq_sum[s] / np.maximum(ns, 1e-12), 0.0)
        C = np.array(sorted(T.con[s]))
        ch = np.array([T.con[s][a] for a in C])
        tham = ns > 0
        khong_choi = tham.copy()
        khong_choi[C] = False
        Qb = (pi * Q).sum()
        om = {"A": omega2_A, "B": max((pi * (Q - Qb) ** 2).sum(), 1e-6)}
        om["C"] = om["D"] = om["B"]
        tran = max(1.0 - hoa_all[s] - q_all[s] ** 2, 1e-4)   # độ dao động lớn nhất của kết quả một ván từ s
        for k in "ABCD":
            Ec = E[k][ch]
            f = om[k] / (om[k] + Ec)
            nu = (1 - (pi[C] * f).sum()) / f.sum()
            r = (pi[C] + nu) * f
            G[k][s] = (r * G[k][ch]).sum()
            if k == "C":
                # Phương án C (7/11): phần sai do chọn thiếu nước đo thẳng bằng độ chênh giữa cách gộp các nước đã
                # chơi (theo rho) và cách gộp mọi nước đã thăm (theo pi), dùng giá trị search Q thay cho giá trị thật.
                # Ván đi nước nhiều lượt thăm nhất nên nước đã chơi thường có Q cao hơn mức chung: độ chênh này bắt
                # được đúng phần "chọn nước tốt nhất" mà omega^2 x U (coi độ lệch là ngẫu nhiên) bỏ sót.
                # Trừ phần do nhiễu của chính Q (mỗi nước nhiễu phương sai NHIEU_Q^2 / số lần search): kỳ vọng của
                # độ chênh bình phương = độ chênh thật bình phương + nhiễu x U. (Mô phỏng dùng nhiễu biết trước; mã thật
                # ước nó từ các node được search nhiều lần.)
                U = ((r - pi[C]) ** 2).sum() + (pi[khong_choi] ** 2).sum()
                E[k][s] = (r * r * Ec).sum() + max(((r * Q[C]).sum() - Qb) ** 2 - NHIEU_Q ** 2 / T.k[s] * U, 0.0)
            else:
                U = ((r - pi[C]) ** 2).sum() + (pi[khong_choi] ** 2).sum()
                E[k][s] = (r * r * Ec).sum() + om[k] * U
                if k == "D":
                    E[k][s] = min(E[k][s], tran)
            rho_[k][s] = (C, ch, r)
    return G, E, rho_


def omega2_cach_hai(T, z_goc):
    """Cách thứ hai ở 4.4: phương sai kết quả ván / tổng U dọc một ván (rho = 1 cho nước đã chơi)."""
    # U tại mỗi node trên đường của các ván từ gốc: dùng pi trung bình của node, nước đã chơi = nước ván đi.
    u_node = np.zeros(T.n)
    for s in range(T.n):
        if T.het[s] or T.k[s] == 0:
            continue
        pi = T.n_sum[s] / T.n_sum[s].sum()
        a = int(np.argmax(T.n_sum[s]))
        u_node[s] = (1 - pi[a]) ** 2 + (np.delete(pi, a) ** 2).sum()
    # độ dài trung bình đường đi từ gốc tới lá x U trung bình
    la = np.where(T.het[:T.n])[0]
    tongu = []
    for x in rng_chon(la, 500):
        t, s = 0.0, T.cha[x]
        while s >= 0:
            t += u_node[s]
            s = T.cha[s]
        tongu.append(t)
    return z_goc.var() / np.mean(tongu)


def rng_chon(x, k):
    return x if len(x) <= k else np.random.default_rng(0).choice(x, k, replace=False)


def bang_hieu_chinh(du, thuc, ten):
    q = np.quantile(du, [0, .2, .4, .6, .8, 1])
    print(f"  {ten}: nhóm E dự báo -> sai số thật trung bình (tỉ số thật/dự báo)")
    for i in range(5):
        m = (du >= q[i]) & (du <= q[i + 1])
        print(f"    E {du[m].mean():.4f}  ->  thật {thuc[m].mean():.4f}   ({thuc[m].mean() / max(du[m].mean(), 1e-9):.2f})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--doi", type=int, default=4)
    ap.add_argument("--ngan-sach", type=int, default=40000)
    ap.add_argument("--r0", type=int, default=300)
    ap.add_argument("--lech", type=float, default=0.05)
    ap.add_argument("--kiem-dinh-nghia", action="store_true")
    ap.add_argument("--nhieu-q", type=float, default=NHIEU_Q, help="độ lệch chuẩn nhiễu Q mỗi lần search")
    a = ap.parse_args()
    globals()["NHIEU_Q"] = a.nhieu_q
    T, z_goc = chay(a)
    n = T.n
    trong = ~T.het[:n] & (T.k[:n] > 0)

    om_that = np.mean([(T.p[s] * (T.Vc[s] - T.V[s]) ** 2).sum() for s in np.where(trong)[0]])
    omA = omega2_cach_hai(T, z_goc)
    print(f"omega^2: thật (trung bình độ toả theo p) {om_that:.5f}, ước lượng cách thứ hai {omA:.5f}")
    G, E, rho_ = tinh(T, omA)
    V = T.V[:n]

    # 1. E dự báo so với sai số thật, trên node không phải lá
    print("\n1. E dự báo so với sai số thật (G - V)^2, node trong cây")
    for k in "AB":
        thuc = (G[k][trong] - V[trong]) ** 2
        print(f" Phương án {k}: E trung bình {E[k][trong].mean():.4f}, sai số thật trung bình {thuc.mean():.4f}")
        bang_hieu_chinh(E[k][trong], thuc, k)
    # theo số ván đi qua
    print(" Theo số ván đi qua node (m): sai số thật | E dự báo A | E dự báo B")
    for lo, hi in [(1, 2), (2, 4), (4, 16), (16, 10 ** 9)]:
        mm = trong & (T.m[:n] >= lo) & (T.m[:n] < hi)
        if mm.sum():
            print(f"   m {lo}-{hi - 1 if hi < 10**9 else 'nhiều'}: {mm.sum():6d} node, thật A {((G['A'][mm]-V[mm])**2).mean():.4f} "
                  f"dự báo A {E['A'][mm].mean():.4f} | thật B {((G['B'][mm]-V[mm])**2).mean():.4f} dự báo B {E['B'][mm].mean():.4f}")

    # 2. tau_q^2
    ns = T.n_sum[:n]
    Qw = np.where(ns > 0, T.nq_sum[:n] / np.maximum(ns, 1e-12), 0.0)
    a_sao = ns.argmax(1)
    q = Qw[np.arange(n), a_sao]
    tq_that = ((q[trong] - V[trong]) ** 2).mean()
    print(f"\n2. tau_q^2 thật {tq_that:.4f}")
    tq = {}
    for k in "AB":
        gop = ((G[k][trong] - q[trong]) ** 2).mean() - E[k][trong].mean()
        nho = trong & (E[k] < 0.05)
        uoc = ((G[k][nho] - q[nho]) ** 2).mean() - E[k][nho].mean() if nho.sum() else np.nan
        tq[k] = 0.01 if not np.isfinite(uoc) else max(uoc, 0.01)
        print(f"   phương án {k}: gộp cả cây {gop:.4f}; chỉ node E<0.05 ({nho.sum()} node) {uoc:.4f} -> dùng {tq[k]:.4f}")

    # 3. Nhãn value so với V thật (trọng số m như khi huấn luyện, phần 10)
    print("\n3. Nhãn value: sai số bình phương so với V thật (trọng số m)")
    w = T.m[:n] * trong
    tt = 0.2 * q + 0.8 * np.nan_to_num(T.z_van[:n])
    co_z = trong & ~np.isnan(T.z_van[:n])
    def mse(x, mask=None):
        mk = co_z if mask is None else mask
        return (w[mk] * (x[mk] - V[mk]) ** 2).sum() / w[mk].sum()
    print(f"   truyền thống 0.2q+0.8z: {mse(tt):.4f}   chỉ q: {mse(q):.4f}   chỉ z: {mse(np.nan_to_num(T.z_van[:n])):.4f}")
    for k in "AB":
        wq = E[k] / (E[k] + tq[k])
        moi = wq * q + (1 - wq) * G[k]
        print(f"   mới, phương án {k}: {mse(moi):.4f}   (chỉ G: {mse(G[k]):.4f}; w_q trung bình theo m {(w[co_z]*wq[co_z]).sum()/w[co_z].sum():.2f})")
    for lo, hi, ten in [(1, 2, "node 1 ván"), (2, 10 ** 9, "node nhiều ván")]:
        mk = co_z & (T.m[:n] >= lo) & (T.m[:n] < hi)
        dong = f"   {ten} ({mk.sum()} node): truyền thống {mse(tt, mk):.4f}"
        for k in "AB":
            wq = E[k] / (E[k] + tq[k])
            dong += f", mới {k} {mse(wq * q + (1 - wq) * G[k], mk):.4f}"
        print(dong)

    # 4. Nhãn policy pi' (7.2) ở node có >= 2 nước đã chơi
    print("\n4. Nhãn policy pi' (7.2), node có ít nhất 2 nước đã chơi")
    for k in "AB":
        nut = [s for s in np.where(trong)[0] if len(T.con[s]) >= 2]
        # tau_d^2: (delta - d)^2 - E(sa) trên các nước đã chơi có E nhỏ
        mau = []
        for s in nut:
            C, ch, r = rho_[k][s]
            sg = T.dau(s)
            Qs = sg * Qw[s]
            Qbar = (r * Qs[C]).sum()
            d = Qs[C] - Qbar
            de = sg * (G[k][ch] - G[k][s])
            for i in range(len(C)):
                if E[k][ch[i]] < 0.05:
                    mau.append((de[i] - d[i]) ** 2 - E[k][ch[i]])
        td = max(np.mean(mau) if mau else 0.0005, 0.0005)
        gt_pi, gt_pp, tr_pi, tr_pp, gt_p = [], [], [], [], []
        lam = C_PUCT / np.sqrt(VISITS)
        for s in nut:
            C, ch, r = rho_[k][s]
            sg = T.dau(s)
            ns_ = T.n_sum[s]
            pi = ns_ / ns_.sum()
            Qs = sg * Qw[s]
            Qbar = (r * Qs[C]).sum()
            d = Qs[C] - Qbar
            de = sg * (G[k][ch] - G[k][s])
            D = d + td / (td + E[k][ch]) * (de - d)
            Qp = Qs.copy()
            Qp[C] = Qbar + D
            beta = (pi * Qs).sum() + lam
            wa = np.maximum(pi * (beta - Qs), 1e-9)
            lo, hi = Qp.max() + 1e-12, Qp.max() + 10
            for _ in range(100):
                mid = (lo + hi) / 2
                if (wa / (mid - Qp)).sum() > 1:
                    lo = mid
                else:
                    hi = mid
            pp = wa / (hi - Qp)
            pp /= pp.sum()
            vben = sg * T.Vc[s]
            tot = int(np.argmax(vben))
            gt_pi.append((pi * vben).sum()); gt_pp.append((pp * vben).sum()); gt_p.append((T.p[s] * vben).sum())
            tr_pi.append(np.argmax(pi) == tot); tr_pp.append(np.argmax(pp) == tot)
        print(f"   phương án {k}: {len(nut)} node, tau_d^2 ước {td:.5f} (nhiễu thật {NHIEU_Q**2:.5f}); giá trị thật kỳ vọng "
              f"theo nhãn: pi {np.mean(gt_pi):+.4f}, pi' {np.mean(gt_pp):+.4f} (chính sách thật {np.mean(gt_p):+.4f}); "
              f"trúng nước tốt nhất: pi {np.mean(tr_pi):.3f}, pi' {np.mean(tr_pp):.3f}")
    if a.kiem_dinh_nghia:
        kiem_dinh_nghia(T, G, E)



def gia_tri_khi_choi_that(T, s, so_van, rng):
    """Kết quả trung bình khi chơi tiếp từ s đúng như ván thật của cây (nước nhiều lượt thăm nhất của một lần
    search mới mỗi nửa nước), ước bằng so_van ván độc lập. Nước đầu dùng các giá trị con cố định của s; từ đó trở
    đi thế giới được sinh mới (cùng quy luật), nên đây là trung bình theo cả độ ngẫu nhiên của thế giới bên dưới."""
    tong = 0.0
    for _ in range(so_van):
        V, sau = T.V[s], T.sau[s]
        Vc, lech = T.Vc[s].copy(), T.lech[s].copy()
        while True:
            sg = 1.0 if sau % 2 == 0 else -1.0
            sig = max(SIG0 * np.sqrt(max(1 - V * V, 0.0)), 1e-6)
            q_ben = sg * Vc + lech + rng.normal(0, NHIEU_Q, K)
            x = SAC * (q_ben - q_ben.mean()) / sig
            pi = np.exp(x - x.max()); pi /= pi.sum()
            pi = (1 - EPS) * pi + EPS * rng.dirichlet(np.full(K, ALPHA))
            a = int(np.argmax(rng.multinomial(VISITS, pi)))
            V, sau = Vc[a], sau + 1
            if abs(V) >= 0.99:
                tong += 1.0 if rng.random() < (1 + V) / 2 else -1.0; break
            if sau >= 40 and abs(V) < 0.02 and rng.random() < P_HOA:
                break
            if sau >= D_MAX:
                break
            u = rng.normal(size=K); p = np.exp(SAC * u); p /= p.sum()
            sg2 = 1.0 if sau % 2 == 0 else -1.0
            sig2 = SIG0 * np.sqrt(max(1 - V * V, 0.0))
            Vc = np.clip(V + sg2 * sig2 * (u - (p * u).sum()), -0.999, 0.999)
            lech = np.zeros(K)
            if rng.random() < T.ty_le_lech:
                lech[rng.integers(K)] = LECH
    return tong / so_van


def kiem_dinh_nghia(T, G, E, so_node=300, so_van=200, seed=7):
    rng = np.random.default_rng(seed)
    n = T.n
    trong = np.where(~T.het[:n] & (T.k[:n] > 0))[0]
    mau = rng.choice(trong, min(so_node, len(trong)), replace=False)
    Tp = np.array([gia_tri_khi_choi_that(T, s, so_van, rng) for s in mau])
    V = T.V[mau]
    sg = np.where(T.sau[mau] % 2 == 0, 1.0, -1.0)
    print(f"\n5. Giá trị thật theo hai định nghĩa, {len(mau)} node mẫu, mỗi node {so_van} ván chơi tiếp độc lập")
    print(f"   chênh (chơi thật - trung bình theo p), góc bên đi: trung bình {np.mean(sg * (Tp - V)):+.4f}, "
          f"bình phương trung bình {np.mean((Tp - V) ** 2):.4f} (sai số lấy mẫu ~{np.mean(1 - Tp**2) / so_van:.4f})")
    for k in "AB":
        print(f"   phương án {k}: E dự báo {E[k][mau].mean():.4f} | sai số thật so với V theo p {np.mean((G[k][mau] - V) ** 2):.4f}"
              f" | so với giá trị khi chơi thật {np.mean((G[k][mau] - Tp) ** 2) - np.mean(1 - Tp**2) / so_van:.4f}")


if __name__ == "__main__":
    main()
