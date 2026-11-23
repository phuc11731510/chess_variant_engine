"""cay_gm.py -- phần toán thuần của nhãn value mới (SUY_RA_CONG_THUC.md 12.7), không đụng tới cây.

Tại một node s có bằng chứng y = (q, x_P, x_a1, ..., x_ak) về giá trị thật V của s, với ma trận hiệp phương sai sai số
        | A        0     (A-kap) 1^T          |
  Sigma = | 0       B/N    0                  |
        | (A-kap)1  0     D + eta (11^T - I)  |,     D = diag(E_a + Gam).
Nhãn là lam^T y, lam = Sigma^-1 1 / (1^T Sigma^-1 1), sai số bình phương của nhãn là 1 / (1^T Sigma^-1 1).

Khối nhánh rẽ R = diag(d_a) + eta 11^T, d_a = E_a + Gam - eta, nên theo Sherman-Morrison
  u = 1/d, s = sum u, R^-1 1 = u / (1 + eta s), t = 1^T R^-1 1 = s / (1 + eta s),
và theo khối (Schur) với c = A - kap:
  x_q = (1 - c t) / (A - c^2 t),  x_R = (1 - c x_q) R^-1 1,  1^T Sigma^-1 1 = x_q + (1 - c x_q) t + N/B.
Mọi thứ tính bằng bincount theo node, không giải hệ phương trình từng node.
"""
import numpy as np

EPS = 1e-12


def gm_mang(n, A, kap, nb, eta, Gam, e_par, e_E, e_x, q=None, x_P=None):
    """Tổ hợp Gauss-Markov cho n node cùng lúc.

    A, kap, nb, eta, Gam : mảng (n,) -- phương sai của q, hiệp phương sai kappa, độ chính xác của bằng chứng ván thuần
                           nb = N_hieu_dung / B, eta, Gam của nhóm node.
    e_par, e_E, e_x      : các nhánh rẽ: node cha (int, 0..n-1), E của node con, bằng chứng x_a (E, C) với C kênh.
    q, x_P               : (n, C), bằng chứng của q và của các ván thuần.
    Trả về dict:
      nhan (n, C)  nhãn = lam^T y có q;  E_nhan (n,) sai số bình phương của nhãn;
      G (n, C)     tổ hợp không có q (giá trị gửi lên node cha);  E_G (n,) sai số bình phương của G;
      lam_q, lam_P, lam_R (n,)  trọng số của q, của ván thuần, của tất cả nhánh rẽ cộng lại;
      hong (n,) bool  node có Sigma không xác định dương (đã bỏ nhánh rẽ khỏi tổ hợp của node đó).
    """
    C = x_P.shape[1]
    e_par = np.asarray(e_par, dtype=np.int64)
    d = e_E + Gam[e_par] - eta[e_par]
    hong_canh = d <= EPS
    u = np.where(hong_canh, 0.0, 1.0 / np.maximum(d, EPS))
    s = np.bincount(e_par, u, n)
    Suy = np.stack([np.bincount(e_par, u * e_x[:, j], n) for j in range(C)], 1)
    hong = np.bincount(e_par, hong_canh.astype(float), n) > 0

    def tinh(s, Suy):
        t = s / (1 + eta * s)
        R = Suy / (1 + eta * s)[:, None]                       # sum_a (R^-1 1)_a x_a
        c = A - kap
        mau = A - c * c * t
        x_q = np.where(mau > EPS, (1 - c * t) / np.maximum(mau, EPS), np.nan)
        f = 1 - c * x_q
        tong = x_q + f * t + nb
        tong0 = nb + t
        return t, R, x_q, f, tong, tong0

    t, R, x_q, f, tong, tong0 = tinh(s, Suy)
    hong |= ~np.isfinite(x_q) | ~(tong > EPS) | ~(tong0 > EPS)
    if hong.any():                                             # bỏ nhánh rẽ của node hỏng, tính lại
        s = np.where(hong, 0.0, s)
        Suy = np.where(hong[:, None], 0.0, Suy)
        t, R, x_q, f, tong, tong0 = tinh(s, Suy)
    nhan = (x_q[:, None] * q + f[:, None] * R + nb[:, None] * x_P) / tong[:, None]
    G = (nb[:, None] * x_P + R) / tong0[:, None]
    lam_q = x_q / tong
    lam_P = nb / tong
    lam_R = f * t / tong
    return {"nhan": nhan, "E_nhan": 1.0 / tong, "G": G, "E_G": 1.0 / tong0,
            "lam_q": lam_q, "lam_P": lam_P, "lam_R": lam_R, "hong": hong}


def gm_truc_tiep(A, kap, B_chia_N, eta, Gam, E_a, q, x_P, x_a, co_q=True):
    """Lời giải trực tiếp (giải hệ phương trình bằng numpy.linalg) cho MỘT node, để kiểm gm_mang.
    E_a, x_a: danh sách của các nhánh rẽ. Trả về (nhan, sai số bình phương, lam)."""
    k = len(E_a)
    ten = ([0] if co_q else []) + [1] + [2 + j for j in range(k)]
    m = 2 + k
    S = np.zeros((m, m))
    S[0, 0] = A
    S[1, 1] = B_chia_N
    for j in range(k):
        S[0, 2 + j] = S[2 + j, 0] = A - kap
        for l in range(k):
            S[2 + j, 2 + l] = (E_a[j] + Gam) if j == l else eta
    y = np.concatenate([[q, x_P], x_a])
    S, y = S[np.ix_(ten, ten)], y[ten]
    w = np.linalg.solve(S, np.ones(len(ten)))
    tong = w.sum()
    lam = w / tong
    return float(lam @ y), 1.0 / tong, lam


# ---------------------------------------------------------------- nhóm tham số (12.3, 12.12)
P_BIEN = np.array([0.002, 0.01, 0.05, 0.15, 0.4, 0.6])        # bảy khoảng của p = 1 - d - q^2 của search lúc chơi
S_BIEN = np.array([0.4, 0.7])                                  # ba khoảng của tỉ lệ lượt thăm của nước nhiều nhất
SO_NHOM_PS = (len(P_BIEN) + 1) * (len(S_BIEN) + 1)
NHOM_DOI0 = SO_NHOM_PS                                        # q đến từ mạng đời 0 (chưa học gì): nhóm riêng
SO_NHOM = SO_NHOM_PS + 1


def nhom_cua(q, d, chia, doi_q):
    """Nhóm của node từ thông tin biết ngay tại node: p = 1 - d - q^2, tỉ lệ lượt thăm, và đời của mạng cho q."""
    p = np.clip(1.0 - d - q * q, 0.0, 1.0)
    g = np.searchsorted(P_BIEN, p) * (len(S_BIEN) + 1) + np.searchsorted(S_BIEN, chia)
    return np.where(doi_q == 0, NHOM_DOI0, g)


# Giá trị khởi đầu (chủ dự án chốt 23/11): phần may rủi B = 0,25 S; kappa = 0,13 S (đo trên cây đời 20 của lần chạy 5,
# SUY_RA_CONG_THUC.md 12.14); o = 0. Gam và eta lấy theo giả định của 12.7 bước 5 (sai số của search trên nước rẽ có phương
# sai bằng A, không tương quan giữa hai nước): Gam = A + A - 2 kappa, eta = A - 2 kappa.
BS_KHOI_DAU = 0.25
KR_KHOI_DAU = 0.13


def tham_so_tu_S(S, bs=None, kr=None, o=None, od=None):
    """Từ S của từng nhóm (S = A + B) và các tỉ lệ (mặc định: giá trị khởi đầu) dựng bảng tham số: A, B, kap, Gam, eta, o, od."""
    S = np.asarray(S, dtype=np.float64)
    bs = np.full_like(S, BS_KHOI_DAU) if bs is None else np.asarray(bs, dtype=np.float64)
    kr = np.full_like(S, KR_KHOI_DAU) if kr is None else np.asarray(kr, dtype=np.float64)
    B = bs * S
    A = S - B
    kap = kr * S
    Gam = 2 * A - 2 * kap
    eta = np.maximum(A - 2 * kap, 0.0)
    return {"S": S, "A": A, "B": B, "kap": kap, "Gam": Gam, "eta": eta,
            "o": np.zeros_like(S) if o is None else np.asarray(o, dtype=np.float64),
            "od": np.zeros_like(S) if od is None else np.asarray(od, dtype=np.float64)}
