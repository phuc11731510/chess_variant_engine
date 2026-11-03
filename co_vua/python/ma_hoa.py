"""Mã hoá thế cờ thành 112 mặt phẳng và nước đi thành chỉ số policy, giống hệt lc0.

Theo co_vua/engine/src/neural/encoder.cc, định dạng INPUT_CLASSICAL_112_PLANE, history fill "no"
(đúng cấu hình của chế độ treeplay). Mọi mặt phẳng nhìn từ phía bên đang đi: "ta" là quân của bên
đang đi, và nếu bên đang đi là Đen thì lật hàng (ô sq thành sq ^ 56). Mặt phẳng là mảng 8 x 8 với
hàng = hàng của bàn cờ (0 là hàng 1), cột = cột (0 là cột a).

- 8 thế cờ gần nhất (thế hiện tại trước), mỗi thế 13 mặt phẳng: 6 loại quân của ta (tốt, mã, tượng,
  xe, hậu, vua), 6 loại quân của đối phương, và một mặt phẳng toàn 1 nếu thế đó đã xuất hiện trước.
  Thiếu lịch sử (đầu ván) thì để 0.
- 104-107: ta còn quyền nhập thành cánh hậu, cánh vua; đối phương cánh hậu, cánh vua (toàn 1 nếu có).
- 108: toàn 1 nếu bên đang đi là Đen. 109: số nửa nước của luật 50 nước (số thô). 110: 0. 111: toàn 1.
"""
from pathlib import Path

import chess
import numpy as np

_B = np.load(Path(__file__).resolve().parent / "bang_lc0.npz")
NUOC_LC0 = [str(x) for x in _B["nuoc"]]
CHI_SO_NUOC = {m: i for i, m in enumerate(NUOC_LC0)}
GOM_POLICY = _B["gom_policy"]

_LOAI = (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN, chess.KING)


def _mat(bb, lat):
    """Bitboard của python-chess (bit = ô) sang mảng 8 x 8; lat = lật hàng."""
    if lat:
        bb = chess.flip_vertical(bb)
    return np.unpackbits(np.array([bb], dtype="<u8").view(np.uint8), bitorder="little").reshape(8, 8)


def ma_hoa(board):
    """board: chess.Board có đủ move_stack từ thế khởi đầu. Trả về mảng float32 (112, 8, 8)."""
    ra = np.zeros((112, 8, 8), np.float32)
    ta = board.turn
    lat = ta == chess.BLACK
    da_qua = {}
    # Số lần mỗi thế đã xuất hiện, để biết thế ở mỗi bước lùi có lặp lại thế trước nó không.
    lich_su = [board.copy(stack=False)]
    tam = board.copy()
    while tam.move_stack:
        tam.pop()
        lich_su.append(tam.copy(stack=False))
    lich_su.reverse()                                   # từ thế khởi đầu tới thế hiện tại
    lap = []
    for t in lich_su:
        k = t._transposition_key()
        lap.append(da_qua.get(k, 0) > 0)
        da_qua[k] = da_qua.get(k, 0) + 1
    for i in range(8):
        k = len(lich_su) - 1 - i
        if k < 0:
            break
        t = lich_su[k]
        co = 13 * i
        for j, loai in enumerate(_LOAI):
            ra[co + j] = _mat(t.pieces_mask(loai, ta), lat)
            ra[co + 6 + j] = _mat(t.pieces_mask(loai, not ta), lat)
        if lap[k]:
            ra[co + 12] = 1.0
    if board.has_queenside_castling_rights(ta):
        ra[104] = 1.0
    if board.has_kingside_castling_rights(ta):
        ra[105] = 1.0
    if board.has_queenside_castling_rights(not ta):
        ra[106] = 1.0
    if board.has_kingside_castling_rights(not ta):
        ra[107] = 1.0
    if lat:
        ra[108] = 1.0
    ra[109] = board.halfmove_clock
    ra[111] = 1.0
    return ra


def chi_so_policy(board, nuoc):
    """Chỉ số (0..1857) của nước nuoc (chess.Move, toạ độ tuyệt đối) tại thế board, theo lc0.

    Lc0 viết nước theo góc nhìn bên đang đi, nhập thành là "vua ăn xe", phong mã không có hậu tố.
    """
    tu, den = nuoc.from_square, nuoc.to_square
    if board.is_castling(nuoc):
        den = chess.square(7 if chess.square_file(den) > chess.square_file(tu) else 0, chess.square_rank(tu))
    if board.turn == chess.BLACK:
        tu, den = chess.square_mirror(tu), chess.square_mirror(den)
    s = chess.square_name(tu) + chess.square_name(den)
    if nuoc.promotion and nuoc.promotion != chess.KNIGHT:
        s += chess.piece_symbol(nuoc.promotion)
    return CHI_SO_NUOC[s]
