"""Hai số thống kê trên các ván của một đời tự đấu, tính TỪ BẢN GHI (không cần engine).

Trước đây hai số này do engine tính ở từng máy Colab lúc sinh dữ liệu (selfplay_game.cc / selfplay_driver.cc) rồi in
ở dòng tổng kết cuối lần chạy, nên mỗi máy một con số. Ở đây chúng được tính trên TẤT CẢ ván của đời mới nhất (thư mục
games_gen<g> số lớn nhất, gồm ván của mọi máy), ngay trước khi huấn luyện (train.py --stats-newest-gen).

  1. Số quân còn lại trung bình lúc kết thúc ván (cả hai bên, kể cả Hoàng gia).
  2. Tỉ lệ ván phân thắng bại mà bên "công nhiều hơn" thắng. Điểm công TÍCH LUỸ của một bên: ở mỗi thế cờ trước khi đi,
     cộng số quân của bên đó đang đứng ở NỬA BÀN đối phương (Trắng: hạng 6-10, Đen: hạng 1-5). Bên có tổng lớn hơn là bên
     công nhiều hơn; chỉ đếm ván có kết quả thắng thua và hai tổng khác nhau.

Cách tính từ một bản ghi (thế TRƯỚC nước đi đó, khung của bên đi: quân mình ở dưới, hạng 0-4 là nửa mình, 5-9 nửa đối thủ):
  - mặt phẳng 0-11 của thế hiện tại là quân của bên đi, 12-23 là quân đối thủ (nn_layout.py); mỗi ô tối đa một quân.
  - điểm công: quân mình ở hạng 5-9 tính cho bên đi; quân đối thủ ở hạng 0-4 tính cho bên kia. (Bản ghi đã lật cho Đen
    nên khung là khung của bên đi; bên đi ở bản ghi là Trắng nếu side_to_move = 0.)
  - số quân lúc kết thúc: bản ghi cuối ván là thế TRƯỚC nước đi cuối, nên trừ 1 nếu nước đi cuối là nước ăn quân. Nước đi cuối
    giải mã từ played_idx (loại * 100 + ô xuất phát, encoder.cc MoveToNNIndex); nó ăn quân nếu ô đến có quân đối thủ, hoặc ô đến
    là ô bắt tốt qua đường mà quân đi là Sergeant (luôn ăn) hoặc Tốt đi chéo (Tốt đi thẳng vào ô ep là nước thường).
    Kết quả khớp với số engine in (pieces=, cong W=/B=) trên từng ván (test_thong_ke_doi.py). Ván Trắng/Đen xin thua sớm
    (resign) không có nước cuối được đi; tự đấu thật tắt resign nên không xét.

Dùng:  python thong_ke_doi.py --data "games_gen3.zip,games_gen2.zip"   (in thống kê của đời mới nhất trong gói)
       python thong_ke_doi.py --data games_gen3 --all                   (mọi ván của --data, không chọn đời)
"""

import argparse
import sys

import numpy as np

import trainingdata_reader as R
from dataset import list_games, newest_generation
from nn_layout import BOARD, MOVE_TYPES, PIECE_KINDS, PROMOTION_BASE, SLIDE_TYPES, KNIGHT_BASE, CAMEL_BASE

PAWN, SERGEANT = 0, 9          # chỉ số loại quân theo kPieceKindOrder (encoder.cc): Tốt đầu tiên, Sergeant thứ mười
OWN_HALF = BOARD // 2          # hạng 0..4 là nửa mình, 5..9 nửa đối thủ (khung của bên đi)

# Hướng và bước nhảy theo ĐÚNG thứ tự trong encoder.cc (MoveToNNIndex): Bắc, ĐB, Đông, ĐN, Nam, TN, Tây, TB.
_SLIDE_DIRS = [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]
_KNIGHT = [(1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2)]
_CAMEL = [(1, 3), (3, 1), (3, -1), (1, -3), (-1, -3), (-3, -1), (-3, 1), (-1, 3)]


def decode_move(idx):
    """played_idx -> (file, rank, dx, dy): ô xuất phát (cột, hạng) và độ dời, trong khung của bên đi (đi lên = dy > 0).
    Nước phong cấp chỉ ghi hướng (ăn trái, thẳng, ăn phải), độ dời luôn là một hạng lên."""
    kind, frm = divmod(int(idx), BOARD * BOARD)
    if not 0 <= kind < MOVE_TYPES:
        raise ValueError(f"played_idx {idx}: loại nước {kind} ngoài khoảng 0..{MOVE_TYPES - 1}")
    rank, file = divmod(frm, BOARD)
    if kind < SLIDE_TYPES:
        d, dist = divmod(kind, 9)
        dx, dy = _SLIDE_DIRS[d][0] * (dist + 1), _SLIDE_DIRS[d][1] * (dist + 1)
    elif kind < CAMEL_BASE:
        dx, dy = _KNIGHT[kind - KNIGHT_BASE]
    elif kind < PROMOTION_BASE:
        dx, dy = _CAMEL[kind - CAMEL_BASE]
    else:
        dx, dy = (kind - PROMOTION_BASE) % 3 - 1, 1
    return file, rank, dx, dy


def _board_bits(planes):
    """uint64 [..., 2] (lo, hi) -> bool [..., 10, 10]."""
    return R._unpack_block(np.asarray(planes, dtype=np.uint64)) > 0.5


def game_stats(recs):
    """Thống kê của MỘT ván từ danh sách bản ghi của nó (theo thứ tự). Trả về dict:
    plies, pieces (còn lại lúc kết thúc), white_attack, black_attack, result ('W' Trắng thắng, 'B' Đen thắng, 'D' hoà)."""
    n = len(recs)
    if n == 0:
        raise ValueError("ván không có bản ghi")
    pp = np.stack([np.asarray(r["piece_planes"], dtype=np.uint64).reshape(-1, 2)[:2 * PIECE_KINDS] for r in recs])
    bits = _board_bits(pp)                                   # [n, 24, 10, 10]
    ours, theirs = bits[:, :PIECE_KINDS], bits[:, PIECE_KINDS:]
    ours_any, theirs_any = ours.any(axis=1), theirs.any(axis=1)          # [n, 10, 10]
    stm = np.array([int(r["side_to_move"]) for r in recs])
    us_att = ours_any[:, OWN_HALF:, :].sum(axis=(1, 2))      # quân của bên đi ở nửa đối thủ
    them_att = theirs_any[:, :OWN_HALF, :].sum(axis=(1, 2))  # quân đối thủ ở nửa của bên đi
    white_attack = int(us_att[stm == 0].sum() + them_att[stm == 1].sum())
    black_attack = int(them_att[stm == 0].sum() + us_att[stm == 1].sum())

    last = recs[-1]
    pieces = int(ours[-1].sum() + theirs[-1].sum())
    file, rank, dx, dy = decode_move(last["played_idx"])
    to_f, to_r = file + dx, rank + dy
    if not (0 <= to_f < BOARD and 0 <= to_r < BOARD):
        raise ValueError(f"nước đi cuối ra ngoài bàn: ô đến ({to_f}, {to_r})")
    captured = bool(theirs_any[-1][to_r, to_f])
    if not captured and _board_bits(np.asarray(last["ep_mask"], dtype=np.uint64))[to_r, to_f]:
        mover = np.nonzero(ours[-1][:, rank, file])[0]
        kind = int(mover[0]) if len(mover) else -1
        captured = kind == SERGEANT or (kind == PAWN and dx != 0)
    pieces -= int(captured)

    q, white_to_move = float(recs[0]["result_q"]), int(recs[0]["side_to_move"]) == 0
    if recs[0]["result_d"] > 0.5 or q == 0.0:
        result = "D"
    else:
        result = "W" if (q > 0) == white_to_move else "B"
    return {"plies": n, "pieces": pieces, "white_attack": white_attack, "black_attack": black_attack,
            "result": result}


def iter_game_records(games):
    """Từng ván (danh sách bản ghi, đọc dạng thưa) của `games` (dataset.list_games), theo thứ tự."""
    import zipfile
    zf, zpath = None, None
    try:
        for path, member in games:
            if member is None:
                yield list(R.iter_records(path, sparse=True))
                continue
            if path != zpath:
                if zf is not None:
                    zf.close()
                zf, zpath = zipfile.ZipFile(path), path
            yield list(R._iter_member(zf, member, path, sparse=True))
    finally:
        if zf is not None:
            zf.close()


def summarize(per_game):
    """Gộp thống kê của nhiều ván thành các số của báo cáo."""
    n = len(per_game)
    if n == 0:
        return None
    decisive = [g for g in per_game if g["result"] != "D" and g["white_attack"] != g["black_attack"]]
    won = sum(1 for g in decisive if (g["white_attack"] > g["black_attack"]) == (g["result"] == "W"))
    return {
        "games": n,
        "positions": sum(g["plies"] for g in per_game),
        "white_wins": sum(1 for g in per_game if g["result"] == "W"),
        "black_wins": sum(1 for g in per_game if g["result"] == "B"),
        "draws": sum(1 for g in per_game if g["result"] == "D"),
        "avg_pieces": sum(g["pieces"] for g in per_game) / n,
        "avg_white_attack": sum(g["white_attack"] for g in per_game) / n,
        "avg_black_attack": sum(g["black_attack"] for g in per_game) / n,
        "white_more": sum(1 for g in per_game if g["white_attack"] > g["black_attack"]),
        "black_more": sum(1 for g in per_game if g["black_attack"] > g["white_attack"]),
        "decisive_clear": len(decisive),
        "more_attacker_won": won,
    }


def format_report(label, s):
    pct = 100.0 * s["more_attacker_won"] / s["decisive_clear"] if s["decisive_clear"] else 0.0
    return "\n".join([
        f"[stats] {label}: {s['games']} games, {s['positions']} positions "
        f"(avg {s['positions'] / s['games']:.1f} plies per game)",
        f"  results: White wins {s['white_wins']} | Black wins {s['black_wins']} | draws {s['draws']}",
        f"  pieces left on the board when the game ended (both sides): avg {s['avg_pieces']:.2f}",
        f"  cumulative attack score per game: White {s['avg_white_attack']:.1f}  Black {s['avg_black_attack']:.1f}; "
        f"games where each side attacked more: White {s['white_more']} | Black {s['black_more']}",
        f"  the side that attacked more WON: {s['more_attacker_won']}/{s['decisive_clear']} decisive games ({pct:.1f}%)",
    ])


def newest_generation_report(data, newest=True):
    """Đọc ván của đời mới nhất trong `data` (hoặc tất cả nếu newest=False), in và trả về thống kê (None nếu không có)."""
    games = list_games(data)
    label = "all games"
    if newest:
        gen, sel = newest_generation(games)
        if not sel:
            print("[stats] --stats-newest-gen: no games_gen<g> folder in the data paths -- no statistics", flush=True)
            return None
        games, label = sel, f"newest generation {gen}"
    per_game = [game_stats(recs) for recs in iter_game_records(games) if recs]
    s = summarize(per_game)
    if s is None:
        print(f"[stats] {label}: no games", flush=True)
        return None
    print(format_report(label, s), flush=True)
    return s


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--data", required=True, help="như train.py --data: thư mục, glob, .zip, nối bằng dấu phẩy")
    ap.add_argument("--all", action="store_true", help="tính trên mọi ván của --data, không chọn đời mới nhất")
    a = ap.parse_args()
    return 0 if newest_generation_report(a.data, newest=not a.all) is not None else 1


if __name__ == "__main__":
    sys.exit(main())
