# -*- coding: utf-8 -*-
"""Đổi ván cờ trong DỮ LIỆU HUẤN LUYỆN thành nhật ký xem lại cho GUI (xem_lai.bat).

Một ván tự đấu = một tệp .xz (hoặc .gz / .bin cũ); gói .zip của vòng lặp (games_genN_*.zip) chứa nhiều ván.
Mỗi bản ghi lưu thế cờ (các mặt phẳng quân, nhìn từ phía bên đi), chỉ số nước đã đi (played_idx = loại nước x 100
+ ô xuất phát, trong khung nhìn của bên đi: Đen thì lật hàng), số lượt thăm của mọi nước hợp lệ và các giá trị
Q. Từ đó dựng lại: thế xuất phát (FEN), dãy nước UCI, và với mỗi nước: số lượt thăm của các nước ứng viên, WDL ở gốc,
Q của nước đã đi / nước tốt nhất. Kết quả là tệp văn bản đúng định dạng của `tu_dau_log/tu_dau_*.txt` nên
`xem_lai.bat` / `fairyzero_gui.exe --replay` đọc được, kể cả bảng tìm kiếm (phím L).

Cách dùng (chạy từ thư mục gốc dự án):
  py -3 custom_engine/python/xem_du_lieu.py "Dữ liệu huấn luyện/games_gen1" --liet-ke        # bảng các ván
  py -3 custom_engine/python/xem_du_lieu.py "Dữ liệu huấn luyện/games_gen1" --van 12        # ván số 12
  py -3 custom_engine/python/xem_du_lieu.py "Dữ liệu huấn luyện/games_gen1/games_gen1_257.zip"  # một ván ngẫu nhiên
  py -3 custom_engine/python/xem_du_lieu.py <nguồn> --liet-ke --kiem                       # kiểm giải mã mọi ván

<nguồn>: tệp ván, gói .zip, hoặc thư mục (tìm cả trong thư mục con). Thứ tự ván = thứ tự tên tệp, trong gói
= thứ tự trong gói. `--kiem` so từng nước giải mã với bàn cờ của bản ghi kế tiếp (đúng ô đi, đúng quân phong,
chỉ thêm tối đa một quân bị ăn qua đường): giải mã sai thì báo ngay.

Mã thoát: 0 = xong; 1 = lỗi (không có ván, đọc lỗi, --kiem thấy ván giải mã sai).
"""
import argparse
import os
import random
import re
import sys
import zipfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trainingdata_reader as tdr  # noqa: E402
from nn_layout import BOARD, PIECE_KINDS, PLANES_PER_BOARD  # noqa: E402

LETTERS = "pnrqkbmvyscg"                      # thứ tự loại quân trong mặt phẳng (kPieceKindOrder, encoder.cc)
PROMO = "nbrqmvycg"                           # quân phong cấp theo thứ tự ô policy (nn_layout.h)
SLIDE_DIRS = [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]   # B, ĐB, Đ, ĐN, N, TN, T, TB
KNIGHT = [(1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2)]
CAMEL = [(1, 3), (3, 1), (3, -1), (1, -3), (-1, -3), (-3, -1), (-3, 1), (-1, 3)]
SLIDE_TYPES = 8 * 9
KNIGHT_BASE = SLIDE_TYPES
CAMEL_BASE = KNIGHT_BASE + 8
PROMOTION_BASE = CAMEL_BASE + 8
GAME_EXTS = tdr.GAME_EXTS


# --------------------------------------------------------------------------------------------------
# Giải mã
# --------------------------------------------------------------------------------------------------
def nuoc_tu_chi_so(idx, den):
    """Chỉ số policy -> nước UCI tuyệt đối. `den`: bên đi là Đen (khung nhìn lật hàng)."""
    t, frm = divmod(int(idx), BOARD * BOARD)
    rk, fl = divmod(frm, BOARD)
    promo = ""
    if t < SLIDE_TYPES:
        dx, dy = SLIDE_DIRS[t // 9]
        k = t % 9 + 1
        dx, dy = dx * k, dy * k
    elif t < CAMEL_BASE:
        dx, dy = KNIGHT[t - KNIGHT_BASE]
    elif t < PROMOTION_BASE:
        dx, dy = CAMEL[t - CAMEL_BASE]
    else:
        p = t - PROMOTION_BASE
        if p >= len(PROMO) * 3:
            raise ValueError(f"chỉ số nước {idx}: loại {t} không có")
        promo = PROMO[p // 3]
        dx, dy = p % 3 - 1, 1
    r2, f2 = rk + dy, fl + dx
    if not (0 <= r2 < BOARD and 0 <= f2 < BOARD):
        raise ValueError(f"chỉ số nước {idx}: đích ra ngoài bàn")
    if den:
        rk, r2 = BOARD - 1 - rk, BOARD - 1 - r2
    return f"{chr(97 + fl)}{rk + 1}{chr(97 + f2)}{r2 + 1}{promo}"


def ban_co(rec):
    """Bàn cờ tuyệt đối của bản ghi: list 100 số (ô = hàng*10 + cột, hàng 0 = hàng 1), dương = Trắng, âm = Đen,
    độ lớn = loại quân (1..12 theo LETTERS)."""
    pp = np.asarray(rec["piece_planes"], dtype=np.uint64)[:PLANES_PER_BOARD * 2].reshape(PLANES_PER_BOARD, 2)
    den = rec["side_to_move"] == 1
    b = [0] * (BOARD * BOARD)
    for j in range(2 * PIECE_KINDS):
        ta = j < PIECE_KINDS                      # quân của bên đi
        kind = j % PIECE_KINDS + 1
        bits = int(pp[j, 0]) | (int(pp[j, 1]) << 64)
        while bits:
            low = bits & -bits
            s = low.bit_length() - 1
            bits ^= low
            rk, fl = divmod(s, 12)                # khoảng cách giữa hai hàng trong mặt nạ là 12
            if rk >= BOARD or fl >= BOARD:
                continue
            trang = (ta != den)
            r_abs = BOARD - 1 - rk if den else rk
            b[r_abs * BOARD + fl] = kind if trang else -kind
    return b


def dat_quan(b):
    """Trường bố trí quân của FEN (hàng 10 -> hàng 1) từ bàn cờ tuyệt đối b."""
    rows = []
    for r in range(BOARD - 1, -1, -1):
        row, e = "", 0
        for f in range(BOARD):
            pc = b[r * BOARD + f]
            if not pc:
                e += 1
                continue
            if e:
                row += str(e)
                e = 0
            ch = LETTERS[abs(pc) - 1]
            row += ch.upper() if pc > 0 else ch
        rows.append(row + (str(e) if e else ""))
    return "/".join(rows)


def fen_vi_tri(b, rec):
    """FEN của bàn cờ b (xem ban_co) và bản ghi rec: lượt, ô bắt qua đường, số chiếu còn lại (Trắng+Đen), luật 50."""
    den = rec["side_to_move"] == 1
    cu, ct = rec["checks_remaining_us"], rec["checks_remaining_them"]
    trang_ck, den_ck = (ct, cu) if den else (cu, ct)      # "us" = bên đi
    ep = "-"
    mask = int(rec["ep_mask"][0]) | (int(rec["ep_mask"][1]) << 64)
    if mask:
        s = (mask & -mask).bit_length() - 1
        rk, fl = divmod(s, 12)
        if rk < BOARD and fl < BOARD:
            ep = f"{chr(97 + fl)}{(BOARD - rk if den else rk + 1)}"
    return f"{dat_quan(b)} {'b' if den else 'w'} - {ep} {trang_ck}+{den_ck} {rec['rule50_count']} 1"


def ep_o(rec):
    """Các ô bắt qua đường (tuyệt đối) của bản ghi: ep_mask nằm trong khung nhìn của bên đi."""
    mask = int(rec["ep_mask"][0]) | (int(rec["ep_mask"][1]) << 64)
    den = rec["side_to_move"] == 1
    out = set()
    while mask:
        low = mask & -mask
        rk, fl = divmod(low.bit_length() - 1, 12)
        mask ^= low
        if rk < BOARD and fl < BOARD:
            out.add((BOARD - 1 - rk if den else rk) * BOARD + fl)
    return out


def o_cua(uci):
    f = ord(uci[0]) - 97
    r = int(uci[1:uci.index(next(c for c in uci[1:] if c.isalpha()))]) - 1
    return r * BOARD + f


def tach_nuoc(uci):
    """'e2e4' / 'a9a10q' -> (ô đi, ô đến, chữ phong hoặc '')."""
    i = next(k for k in range(1, len(uci)) if uci[k].isalpha())
    j = next((k for k in range(i + 1, len(uci)) if uci[k].isalpha()), len(uci))
    frm = (int(uci[1:i]) - 1) * BOARD + ord(uci[0]) - 97
    to = (int(uci[i + 1:j]) - 1) * BOARD + ord(uci[i]) - 97
    return frm, to, uci[j:]


def kiem_nuoc(b0, b1, uci):
    """None nếu bàn cờ b1 đúng là b0 sau nước uci, ngược lại lời báo lỗi."""
    frm, to, promo = tach_nuoc(uci)
    pc = b0[frm]
    if not pc:
        return f"{uci}: ô đi trống"
    dau = 1 if pc > 0 else -1
    muon = dau * (LETTERS.index(promo) + 1) if promo else pc
    if promo and abs(pc) not in (LETTERS.index("p") + 1, LETTERS.index("s") + 1):
        return f"{uci}: phong cấp nhưng quân đi không phải Tốt / Sergeant"
    if b1[frm] != 0 and frm != to:
        return f"{uci}: ô đi còn quân sau nước"
    if b1[to] != muon:
        return f"{uci}: ô đến có {b1[to]}, đáng lẽ {muon}"
    khac = [s for s in range(BOARD * BOARD) if s not in (frm, to) and b0[s] != b1[s]]
    if len(khac) > 1 or (khac and not (b1[khac[0]] == 0 and b0[khac[0]] * dau < 0 and
                                       abs(b0[khac[0]]) in (LETTERS.index("p") + 1, LETTERS.index("s") + 1))):
        return f"{uci}: bàn cờ đổi thêm ở {khac}"
    return None


class Van:
    """Một ván đã giải mã: thế xuất phát, nước đã đi và dữ liệu từng nước."""

    def __init__(self, recs, ten):
        if not recs:
            raise ValueError(f"{ten}: ván rỗng")
        self.ten = ten
        self.recs = recs
        self.boards = [ban_co(r) for r in recs]
        self.den = [r["side_to_move"] == 1 for r in recs]
        self.fen = fen_vi_tri(self.boards[0], recs[0])
        self.nuoc = [nuoc_tu_chi_so(r["played_idx"], d) for r, d in zip(recs, self.den)]

    def kiem(self):
        """Danh sách lỗi giải mã (rỗng = đúng)."""
        loi = []
        for k in range(len(self.recs) - 1):
            if self.den[k] == self.den[k + 1]:
                loi.append(f"nước {k + 1}: hai bản ghi liền cùng một bên đi")
            e = kiem_nuoc(self.boards[k], self.boards[k + 1], self.nuoc[k])
            if e:
                loi.append(f"nước {k + 1}: {e}")
        return loi

    def ban_cuoi(self):
        """Bàn cờ sau nước đi cuối (không có bản ghi cho thế này): áp nước cuối lên bản ghi cuối.
        Ăn qua đường: nước cuối của Tốt / Sergeant đáp xuống một ô bắt qua đường (ep_mask của bản ghi cuối, ô trống)
        thì quân bị ăn là quân vừa bước đôi, đang đứng ở ô ĐẾN của nước ngay trước (có thể cách hai cột)."""
        b = list(self.boards[-1])
        frm, to, promo = tach_nuoc(self.nuoc[-1])
        pc = b[frm]
        dau = 1 if pc > 0 else -1
        tot = LETTERS.index("p") + 1, LETTERS.index("s") + 1
        if abs(pc) in tot and not b[to] and len(self.nuoc) > 1 and to in ep_o(self.recs[-1]):
            nan = tach_nuoc(self.nuoc[-2])[1]
            if b[nan] * dau < 0 and abs(b[nan]) in tot:
                b[nan] = 0
        b[to] = dau * (LETTERS.index(promo) + 1) if promo else pc
        b[frm] = 0
        return b

    def ket_qua(self):
        """'Trắng thắng' / 'Đen thắng' / 'Hoà' theo bản ghi cuối (giá trị kết quả tính từ bên đi của bản ghi đó)."""
        r = self.recs[-1]
        q, d = r["result_q"], r["result_d"]
        if d > 0.5 or abs(q) < 0.5:
            return "Hoà"
        thang_di = q > 0
        trang = thang_di != self.den[-1]
        return "Trắng thắng" if trang else "Đen thắng"


# --------------------------------------------------------------------------------------------------
# Nguồn ván
# --------------------------------------------------------------------------------------------------
def liet_ke_van(nguon):
    """[(đường dẫn, thành viên zip hoặc None)] theo thứ tự tên; nguồn là tệp, .zip hoặc thư mục (cả thư mục con)."""
    tep = []
    if os.path.isdir(nguon):
        for goc, _, ten in os.walk(nguon):
            tep += [os.path.join(goc, t) for t in ten if t.endswith(GAME_EXTS + (".zip",))]
    elif os.path.isfile(nguon):
        tep = [nguon]
    else:
        raise FileNotFoundError(f"không có {nguon}")
    van = []
    for f in sorted(tep):
        if f.endswith(".zip"):
            with zipfile.ZipFile(f) as zf:
                van += [(f, m) for m in zf.namelist() if tdr.is_game_member(m)]
        elif f.endswith(GAME_EXTS):
            van.append((f, None))
    return van


def nhan_goi(duong_dan, thu_tu):
    """Nhãn cố định của ván trong gói của vòng lặp liên tục (`goi_<số>_n<đời>_<ván>_<thế>.zip`): `<số gói>.<thứ tự trong gói, từ 1>`,
    cùng nhãn app Android hiện làm số ván (vd 992.8 = ván thứ 8 của gói goi_00992_...); nguồn khác: rỗng."""
    m = re.match(r"^goi_(\d+)_n\d+_\d+_\d+\.zip$", os.path.basename(duong_dan))
    return f"{int(m.group(1))}.{thu_tu}" if m else ""


def ten_van(entry):
    p, m = entry
    return f"{os.path.basename(p)}:{m}" if m else os.path.basename(p)


def doc_van(entry):
    recs = []
    for r in tdr.iter_games([entry], sparse=True):
        if "legal_idx" not in r:                          # định dạng cũ: chính mảng xác suất
            li = np.nonzero(r["probabilities"] >= 0)[0].astype(np.uint16)
            r["legal_idx"], r["legal_pi"] = li, r["probabilities"][li]
        recs.append(r)
    return Van(recs, ten_van(entry))


# --------------------------------------------------------------------------------------------------
# Nhật ký đúng định dạng tu_dau_log (GUI: --replay)
# --------------------------------------------------------------------------------------------------
def wdl_phan_nghin(q, d):
    w = (1.0 - d + q) / 2.0
    l = (1.0 - d - q) / 2.0
    w, d3, l = (max(0, round(x * 1000)) for x in (w, d, l))
    return w, d3, l


TOP_UNG_VIEN = 8      # như nhật ký tự đấu của GUI (MultiPV 8): chỉ ghi 8 nước nhiều lượt thăm nhất (+ nước đã đi)


def nhat_ky(van, so_van=None, tong=None):
    """Văn bản nhật ký của ván: tiêu đề, rồi mỗi nửa nước một mục (xem SelfPlayLog trong GUI)."""
    nhan = f" · ván {so_van}/{tong}" if so_van is not None else ""
    out = [f"# dữ liệu huấn luyện · {van.ten}{nhan} · {len(van.nuoc)} nửa nước · {van.ket_qua()} "
           f"(mỗi nước: số lượt thăm N của {TOP_UNG_VIEN} nước nhiều nhất; Q chỉ có cho nước đã đi và nước tốt nhất)"]
    ds = []
    for k, rec in enumerate(van.recs):
        den = van.den[k]
        out.append(f"--- nửa nước {k + 1} ({'đen' if den else 'trắng'} đi) → {van.nuoc[k]}")
        out.append(f"position fen {van.fen}" + (" moves " + " ".join(van.nuoc[:k]) if k else ""))
        visits = int(rec["visits"])
        w, dr, l = wdl_phan_nghin(rec["root_q"], rec["root_d"])
        best = nuoc_tu_chi_so(rec["best_idx"], den) if rec["best_idx"] != 65535 else van.nuoc[k]
        out.append(f"  depth 1 seldepth 1 multipv 1 wdl {w} {dr} {l} nodes {visits} nps 0 time 0 pv {best}")
        tot = max(visits - 1, 1)
        ung = []
        for i, p in zip(rec["legal_idx"], rec["legal_pi"]):
            ung.append((int(round(float(p) * tot)), nuoc_tu_chi_so(i, den), int(i)))
        ung.sort(key=lambda x: (-x[0], x[1]))
        da_di = int(rec["played_idx"])
        ung = [u for j, u in enumerate(ung) if j < TOP_UNG_VIEN or u[2] == da_di]
        for n, mv, i in ung:
            q = ""
            if i == int(rec["played_idx"]):
                q = f" Q {rec['played_q']:.4f}"
            elif i == int(rec["best_idx"]):
                q = f" Q {rec['best_q']:.4f}"
            out.append(f"    {mv} N {n}{q}")
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------
# Xuất cả nguồn: một nhật ký mỗi ván + bảng chỉ mục (GUI: --replay-dir)
# --------------------------------------------------------------------------------------------------
class May:
    """Engine UCI tối thiểu (--uci-nn, không cần mạng) để hỏi thế cuối của ván: FEN, số nước hợp lệ, kết quả."""

    def __init__(self, exe):
        import subprocess
        self.p = subprocess.Popen([exe, "--uci-nn"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True, encoding="utf-8", bufsize=1,
                                  cwd=os.path.dirname(os.path.abspath(exe)))
        self.gui("uci")
        self.cho(lambda l: l == "uciok")

    def gui(self, s):
        self.p.stdin.write(s + "\n")
        self.p.stdin.flush()

    def cho(self, dk):
        while True:
            l = self.p.stdout.readline()
            if not l:
                raise RuntimeError("engine đã đóng")
            l = l.strip()
            if dk(l):
                return l

    def the_cuoi(self, fen_dau, nuoc):
        """(FEN, số nước hợp lệ, kết quả 'white'/'black'/'draw'/'undecided') sau khi đi hết `nuoc` từ fen_dau."""
        self.gui("ucinewgame")
        self.gui(f"position fen {fen_dau}" + (" moves " + " ".join(nuoc) if nuoc else ""))
        self.gui("fen")
        fen = self.cho(lambda l: l.startswith("fen "))[4:]
        self.gui("legalmoves")
        hop_le = self.cho(lambda l: l.startswith("legalmoves")).split()[1:]
        self.gui("result")
        kq = self.cho(lambda l: l.startswith("result ")).split()[1]
        return fen, len(hop_le), kq

    def dong(self):
        try:
            self.gui("quit")
            self.p.wait(timeout=5)
        except Exception:      # noqa: BLE001
            self.p.kill()


def ly_do(fen, ket_qua, so_hop_le, so_nuoc, ket_qua_du_lieu):
    """Mã lý do kết thúc ván: checks | no_moves | rule50 | repetition | cut | adjudicated.
    Cùng thứ tự kiểm với PositionHistory::ComputeGameResult (position.cc) và `_endReason` của GUI."""
    p = fen.split()
    a, b = (int(x) for x in p[4].split("+"))
    ruoc50 = int(p[5])
    if ket_qua == "undecided":
        return "cut" if ket_qua_du_lieu == "D" else "adjudicated"
    if a <= 0 or b <= 0:
        return "checks"
    if ruoc50 >= 100:
        return "rule50" if ket_qua == "draw" else "no_moves"
    if ket_qua == "draw":
        return "repetition"
    return "no_moves" if so_hop_le == 0 else "unknown"


MA_KET_QUA = {"Trắng thắng": "W", "Đen thắng": "B", "Hoà": "D"}
CAC_COT = ("so", "tep", "nua_nuoc", "ket_qua", "quan_trang", "quan_den", "ly_do", "ghi_chu")


def dem_quan(placement):
    t = sum(c.isupper() for c in placement)
    d = sum(c.islower() for c in placement)
    return t, d


def xuat(ds, thu_muc, engine, lam_lai):
    """Ghi van_NNNN.txt cho mọi ván và chi_muc.tsv. 0 = xong, 1 = có ván giải mã sai / lệch engine."""
    os.makedirs(thu_muc, exist_ok=True)
    tsv = os.path.join(thu_muc, "chi_muc.tsv")
    moi_nhat = max(os.path.getmtime(p) for p, _ in ds)
    if os.path.exists(tsv) and not lam_lai and os.path.getmtime(tsv) >= moi_nhat:
        with open(tsv, encoding="utf-8") as f:
            n = sum(1 for _ in f) - 1
        if n == len(ds):
            print(f"[xem_du_lieu] {tsv} đã có cho {n} ván (dữ liệu không đổi; --lam-lai để làm lại)")
            return 0
    may = May(engine) if engine else None
    dong, xau = [], 0
    try:
        for i, e in enumerate(ds):
            ten_log = f"van_{i:04d}.txt"
            try:
                v = doc_van(e)
            except (ValueError, OSError, zipfile.BadZipFile) as ex:
                dong.append((i, ten_log, 0, "?", 0, 0, "unreadable", str(ex).replace("\t", " ")[:80]))
                xau += 1
                continue
            loi = v.kiem()
            with open(os.path.join(thu_muc, ten_log), "w", encoding="utf-8", newline="\n") as f:
                f.write(nhat_ky(v, i, len(ds)))
            cuoi = dat_quan(v.ban_cuoi())
            ma = MA_KET_QUA[v.ket_qua()]
            ghi_chu = ""
            ly = "unknown"
            if may:
                fen, so_hl, kq = may.the_cuoi(v.fen, v.nuoc)
                cuoi_engine = fen.split()[0]
                ly = ly_do(fen, kq, so_hl, len(v.nuoc), ma)
                if cuoi_engine != cuoi:
                    ghi_chu = "ban co cuoi lech engine"
                kq_ma = {"white": "W", "black": "B", "draw": "D"}.get(kq)
                if kq_ma and kq_ma != ma and not ghi_chu:
                    ghi_chu = f"engine bao {kq}, du lieu bao {ma}"
                cuoi = cuoi_engine
            if loi:
                ghi_chu = ("giai ma sai: " + loi[0]).replace("\t", " ")[:80]
            if ghi_chu:
                xau += 1
            t, d = dem_quan(cuoi)
            dong.append((i, ten_log, len(v.nuoc), ma, t, d, ly, ghi_chu))
            if (i + 1) % 100 == 0:
                print(f"[xem_du_lieu] {i + 1}/{len(ds)} ván…", flush=True)
    finally:
        if may:
            may.dong()
    tam = tsv + ".tmp"
    with open(tam, "w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(CAC_COT) + "\n")
        for r in dong:
            f.write("\t".join(str(x) for x in r) + "\n")
    os.replace(tam, tsv)
    print(f"[xem_du_lieu] ghi {len(dong)} nhật ký + {tsv}" + (f"; {xau} ván có ghi chú lỗi" if xau else ""))
    return 1 if xau else 0


def main():
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("nguon", help="tệp ván (.xz/.gz/.bin), gói .zip, hoặc thư mục")
    ap.add_argument("--van", type=int, help="số thứ tự ván (từ 0, theo thứ tự của --liet-ke)")
    ap.add_argument("--ngau-nhien", action="store_true", help="chọn một ván ngẫu nhiên (mặc định khi có nhiều ván)")
    ap.add_argument("--seed", type=int, help="hạt giống cho --ngau-nhien")
    ap.add_argument("--out", default=os.path.join("tu_dau_log", "du_lieu_xem.txt"), help="tệp nhật ký ghi ra")
    ap.add_argument("--liet-ke", action="store_true", help="in bảng mọi ván (số nước, kết quả) rồi thôi")
    ap.add_argument("--kiem", action="store_true", help="kiểm giải mã từng nước (với --liet-ke: mọi ván)")
    ap.add_argument("--xuat", metavar="THU_MUC", help="ghi nhật ký của MỌI ván + chi_muc.tsv vào thư mục này (GUI: --replay-dir)")
    ap.add_argument("--engine", help="custom_engine.exe để hỏi thế cuối của từng ván (lý do kết thúc, số quân còn lại)")
    ap.add_argument("--lam-lai", action="store_true", help="--xuat: làm lại dù chi_muc.tsv đã mới hơn dữ liệu")
    a = ap.parse_args()

    try:
        ds = liet_ke_van(a.nguon)
    except (OSError, zipfile.BadZipFile) as e:
        print(f"[xem_du_lieu] {e}")
        return 1
    if not ds:
        print(f"[xem_du_lieu] không thấy ván nào trong {a.nguon} (tìm {', '.join(GAME_EXTS)} và .zip)")
        return 1

    if a.xuat:
        try:
            return xuat(ds, a.xuat, a.engine, a.lam_lai)
        except (OSError, RuntimeError) as e:
            print(f"[xem_du_lieu] --xuat lỗi: {e}")
            return 1

    if a.liet_ke:
        dem = {"Trắng thắng": 0, "Đen thắng": 0, "Hoà": 0}
        hong = 0
        print(f"{'số':>5} {'nửa nước':>9}  {'kết quả':<12} tệp (nhãn <số gói>.<thứ tự trong gói> = số ván trong app Android)")
        dem_goi = {}
        for i, e in enumerate(ds):
            dem_goi[e[0]] = dem_goi.get(e[0], 0) + 1
            nhan = nhan_goi(e[0], dem_goi[e[0]])
            try:
                v = doc_van(e)
            except (ValueError, OSError, zipfile.BadZipFile) as ex:
                print(f"{i:>5} {'?':>9}  {'(đọc lỗi)':<12} {ten_van(e)}: {ex}")
                hong += 1
                continue
            kq = v.ket_qua()
            dem[kq] += 1
            loi = v.kiem() if a.kiem else []
            print(f"{i:>5} {len(v.nuoc):>9}  {kq:<12} {v.ten}" + (f"  <{nhan}>" if nhan else "")
                  + (f"   GIẢI MÃ SAI: {loi[0]}" if loi else ""))
            hong += bool(loi)
        print(f"-- {len(ds)} ván: Trắng thắng {dem['Trắng thắng']}, Đen thắng {dem['Đen thắng']}, Hoà {dem['Hoà']}"
              + (f"; {hong} ván lỗi" if hong else "") + (" (đã kiểm giải mã)" if a.kiem else ""))
        return 1 if hong else 0

    if a.van is not None:
        if not 0 <= a.van < len(ds):
            print(f"[xem_du_lieu] --van {a.van}: chỉ có {len(ds)} ván (0..{len(ds) - 1})")
            return 1
        i = a.van
    elif len(ds) == 1:
        i = 0
    else:
        i = random.Random(a.seed).randrange(len(ds))
    try:
        v = doc_van(ds[i])
    except (ValueError, OSError, zipfile.BadZipFile) as e:
        print(f"[xem_du_lieu] đọc {ten_van(ds[i])} lỗi: {e}")
        return 1
    if a.kiem:
        loi = v.kiem()
        if loi:
            print(f"[xem_du_lieu] ván {i} giải mã SAI: " + "; ".join(loi[:5]))
            return 1
    d = os.path.dirname(a.out)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(nhat_ky(v, i, len(ds)))
    print(f"[xem_du_lieu] ván {i}/{len(ds)}: {v.ten}, {len(v.nuoc)} nửa nước, {v.ket_qua()}")
    print(f"[xem_du_lieu] ghi {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
