"""Chuyển bản ghi của `lc0 treeplay` thành mẫu huấn luyện, và nạp mẫu lên GPU theo từng lô.

Một mẫu là một thế cờ đã được search trong một ván (bản ghi G). Mẫu lưu gọn:
- `bit`  (N, 104) uint64: 8 thế cờ gần nhất x 13 mặt phẳng, dạng bitboard đúng như lc0 (ma_hoa.py):
         bit i = ô i (hàng * 8 + cột), đã lật hàng nếu bên đang đi là Đen.
- `phu`  (N,) uint8: bit 0-3 quyền nhập thành (ta cánh hậu, ta cánh vua, đối phương cánh hậu,
         đối phương cánh vua), bit 4 = bên đang đi là Đen.
- `r50`  (N,) uint8: số nửa nước của luật 50 nước.
- `hl_off`, `hl` : chỉ số policy (0..1857) của các nước hợp lệ, dạng CSR (mẫu k chiếm hl[hl_off[k]:hl_off[k+1]]).
- `pt_off`, `pt_i`, `pt_p`: nhãn policy dạng thưa: chỉ số và xác suất của các nước đã thăm.
- `wdl`  (N, 3) float32: nhãn value (thắng, hòa, thua) theo góc nhìn bên đang đi.
Mặt phẳng 104..111 dựng lại từ `phu` và `r50` khi giải nén (giai_nen_lo).

Nhãn của cách truyền thống (THIET_KE_CO_VUA.md 2.5): policy = pi(a) = n(a) / N, value = q_ratio * WDL(best_q, best_d)
+ (1 - q_ratio) * z, với z là kết quả ván (ván dừng ở 450 nửa nước tính là hòa).
"""
import chess
import numpy as np
import torch

from ma_hoa import CHI_SO_NUOC, chi_so_policy

_LOAI = (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN, chess.KING)
_CHI_SO_RAW = {}


def chi_so_tu_raw(raw, den_di):
    """Chỉ số policy của nước lc0 16 bit (toạ độ tuyệt đối) khi bên đang đi là Đen (den_di) hay Trắng."""
    k = (raw, den_di)
    v = _CHI_SO_RAW.get(k)
    if v is None:
        tu, den = (raw >> 6) & 63, raw & 63          # nhập thành của lc0 vốn là "vua ăn xe", đúng như bảng
        if den_di:
            tu, den = tu ^ 56, den ^ 56
        s = chess.square_name(tu) + chess.square_name(den)
        if raw & 0x4000 and (raw >> 12) & 3:          # phong cấp; mã (0) không có hậu tố
            s += "nqrb"[(raw >> 12) & 3]
        v = _CHI_SO_RAW[k] = CHI_SO_NUOC[s]
    return v


def _bitboard_huong(board, ta):
    """12 bitboard (6 loại quân của ta, 6 của đối phương) nhìn từ bên `ta` (lật hàng nếu ta là Đen)."""
    ra = [board.pieces_mask(t, ta) for t in _LOAI] + [board.pieces_mask(t, not ta) for t in _LOAI]
    if ta == chess.BLACK:
        ra = [chess.flip_vertical(b) for b in ra]
    return ra


def _mot_mau(lich_su, lap, board):
    """Bitboard 104 + phụ + r50 của thế cờ hiện tại; lich_su là danh sách board (cũ -> mới), lap tương ứng."""
    ta = board.turn
    bit = np.zeros(104, np.uint64)
    for i in range(8):
        k = len(lich_su) - 1 - i
        if k < 0:
            break
        bit[13 * i:13 * i + 12] = _bitboard_huong(lich_su[k], ta)
        if lap[k]:
            bit[13 * i + 12] = 0xFFFFFFFFFFFFFFFF
    phu = (int(board.has_queenside_castling_rights(ta)) | int(board.has_kingside_castling_rights(ta)) << 1
           | int(board.has_queenside_castling_rights(not ta)) << 2 | int(board.has_kingside_castling_rights(not ta)) << 3
           | int(ta == chess.BLACK) << 4)
    return bit, phu, min(board.halfmove_clock, 255)


def tu_ban_ghi(ban_ghi, q_ratio=0.2):
    """Danh sách BanGhi (ban_ghi.py) -> dict các mảng mẫu của cách truyền thống (bỏ qua bản ghi S)."""
    from ban_ghi import sang_uci
    bit, phu, r50, hl, hl_dai, pt_i, pt_p, pt_dai, wdl = [], [], [], [], [], [], [], [], []
    for r in ban_ghi:
        if r.search_lai:
            continue
        b = chess.Board()
        lich_su, lap, da_qua = [], [], {}

        def ghi_the(bd):
            k = bd._transposition_key()
            lap.append(da_qua.get(k, 0) > 0)
            da_qua[k] = da_qua.get(k, 0) + 1
            lich_su.append(bd.copy(stack=False))

        ghi_the(b)
        for m in r.duong_di:
            b.push_uci(sang_uci(m))
            ghi_the(b)
        for lan in r.lan:
            den_di = b.turn == chess.BLACK
            x, p, c = _mot_mau(lich_su, lap, b)
            bit.append(x); phu.append(p); r50.append(c)
            hop_le = [chi_so_policy(b, m) for m in b.legal_moves]
            hl.extend(hop_le); hl_dai.append(len(hop_le))
            n = lan.tham["n"].astype(np.float64)
            tong = n.sum()
            for t, ni in zip(lan.tham["nuoc"], n):
                pt_i.append(chi_so_tu_raw(int(t), den_di)); pt_p.append(ni / tong)
            pt_dai.append(len(n))
            # Nhãn value: WDL của search (best_q, best_d) trộn với kết quả ván, góc nhìn bên đang đi.
            q, d = lan.best_q, lan.best_d
            w_s = np.clip([(1 + q - d) / 2, d, (1 - q - d) / 2], 0, 1)
            z = r.ket_qua if r.ket_thuc == 0 else 0
            z = z if not den_di else -z
            w_z = np.array([z == 1, z == 0, z == -1], np.float64)
            wdl.append(q_ratio * w_s + (1 - q_ratio) * w_z)
            b.push_uci(sang_uci(lan.nuoc_di))
            ghi_the(b)
    off = lambda dai: np.concatenate(([0], np.cumsum(dai))).astype(np.int64)
    return {"bit": np.array(bit, np.uint64).reshape(-1, 104), "phu": np.array(phu, np.uint8),
            "r50": np.array(r50, np.uint8), "hl_off": off(hl_dai), "hl": np.array(hl, np.int16),
            "pt_off": off(pt_dai), "pt_i": np.array(pt_i, np.int16), "pt_p": np.array(pt_p, np.float32),
            "wdl": np.array(wdl, np.float32).reshape(-1, 3)}


def noi(cac_mau):
    """Nối nhiều dict mẫu (ví dụ các đời trong cửa sổ) thành một."""
    ra = {k: np.concatenate([m[k] for m in cac_mau]) for k in ("bit", "phu", "r50", "hl", "pt_i", "pt_p", "wdl")}
    for k, v in (("hl_off", "hl"), ("pt_off", "pt_i")):
        dai = np.concatenate([np.diff(m[k]) for m in cac_mau])
        ra[k] = np.concatenate(([0], np.cumsum(dai))).astype(np.int64)
    return ra


class TrenGPU:
    """Toàn bộ mẫu nằm trên thiết bị (GPU); mỗi lô được giải nén tại chỗ, không qua CPU."""

    def __init__(self, mau, thiet_bi):
        t = lambda a, kieu: torch.as_tensor(np.ascontiguousarray(a)).to(thiet_bi).to(kieu)
        self.n = len(mau["phu"])
        self.bit = t(mau["bit"].view(np.int64), torch.int64)
        self.phu = t(mau["phu"], torch.int64)
        self.r50 = t(mau["r50"], torch.float32)
        self.hl_off, self.hl = t(mau["hl_off"], torch.int64), t(mau["hl"], torch.int64)
        self.pt_off, self.pt_i = t(mau["pt_off"], torch.int64), t(mau["pt_i"], torch.int64)
        self.pt_p = t(mau["pt_p"], torch.float32)
        self.wdl = t(mau["wdl"], torch.float32)
        self.dich = torch.arange(64, device=thiet_bi, dtype=torch.int64)

    def _csr(self, off, chi_so):
        """Với các mẫu chi_so: (hàng trong lô, vị trí trong mảng phẳng) của mọi phần tử CSR."""
        dau, cuoi = off[chi_so], off[chi_so + 1]
        dai = cuoi - dau
        hang = torch.repeat_interleave(torch.arange(len(chi_so), device=off.device), dai)
        lech = torch.arange(int(dai.sum()), device=off.device) - torch.repeat_interleave(torch.cumsum(dai, 0) - dai, dai)
        return hang, torch.repeat_interleave(dau, dai) + lech

    def lo(self, chi_so):
        """Trả về (x (B,112,8,8), nhãn policy (B,1858) với -1 ở nước không hợp lệ, nhãn WDL (B,3))."""
        B = len(chi_so)
        bit = self.bit[chi_so]                                         # (B, 104)
        x = torch.zeros(B, 112, 64, device=bit.device)
        x[:, :104] = ((bit[:, :, None] >> self.dich) & 1).float()
        phu = self.phu[chi_so]
        for j in range(5):                                              # 104-107 nhập thành, 108 Đen đi
            x[:, 104 + j] = ((phu >> j) & 1).float()[:, None]
        x[:, 109] = self.r50[chi_so][:, None]
        x[:, 111] = 1.0
        pol = torch.full((B, 1858), -1.0, device=bit.device)
        h, v = self._csr(self.hl_off, chi_so)
        pol[h, self.hl[v]] = 0.0
        h, v = self._csr(self.pt_off, chi_so)
        pol[h, self.pt_i[v]] = self.pt_p[v]
        return x.view(B, 112, 8, 8), pol, self.wdl[chi_so]
