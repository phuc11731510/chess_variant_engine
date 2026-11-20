# -*- coding: utf-8 -*-
import os
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pieces_rules import PIECES, Pos, all_moves, name, N
from examples import EXAMPLES, sq, L

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images')
os.makedirs(OUT, exist_ok=True)

GREEN_TXT = [
    "Ô xanh lá: với mỗi ô xanh lá, có một nước đi hợp lệ chọn ô xanh lá đó làm ô B. Thực hiện nước đi",
    "này nghĩa là: xóa quân đối phương ở ô B nếu có; xóa quân Z khỏi ô A (ô A là ô chứa quân Z trước",
    "khi thực hiện nước đi); đặt quân Z vừa xóa vào ô B.",
]
ORANGE_TXT = [
    "Ô cam: với mỗi ô cam, có một nước đi hợp lệ chọn ô cam đó làm ô B. Gọi H là ô nằm chính giữa ô A",
    "và ô B (tọa độ của H bằng trung bình cộng tọa độ của A và B; H được đánh dấu bằng chữ X màu cam).",
    "Thực hiện nước đi này nghĩa là: xóa quân đối phương ở ô H; xóa quân Z khỏi ô A; đặt quân Z vừa xóa",
    "vào ô B. Ô B của nước đi này luôn là ô trống.",
]
DIR_TXT = "Hướng tiến của quân Z là chiều tăng của số hàng (từ hàng 1 lên hàng 10), tức chiều tăng của y."


def draw(key, idx, desc, Z, T, D):
    pos = Pos(sq(Z), L(T), L(D))
    rules, normal, cj = all_moves(key, pos)
    has_cj = PIECES[key]['betza'].find('[cj]') >= 0
    lines = GREEN_TXT + ([""] + ORANGE_TXT if has_cj else []) + ["", DIR_TXT]
    extra = 0.36 * len(lines)
    fig_h = 9.4 + extra * 0.78
    fig, ax = plt.subplots(figsize=(8.6, fig_h))
    ax.set_xlim(-0.7, N + 0.4)
    ax.set_ylim(-1.15 - extra, N + 1.35)
    ax.set_aspect('equal')
    ax.axis('off')
    for x in range(1, N + 1):
        for y in range(1, N + 1):
            light = (x + y) % 2 == 1
            ax.add_patch(Rectangle((x - 1, y - 1), 1, 1, color='#f0d9b5' if light else '#b58863', zorder=0))
    for x in range(1, N + 1):
        ax.text(x - 0.5, -0.28, 'abcdefghij'[x - 1], ha='center', va='center', fontsize=10)
    for y in range(1, N + 1):
        ax.text(-0.35, y - 0.5, str(y), ha='center', va='center', fontsize=10)
    for B in normal:
        ax.add_patch(Rectangle((B[0] - 1 + 0.04, B[1] - 1 + 0.04), 0.92, 0.92, facecolor=(0.1, 0.75, 0.2, 0.45),
                               edgecolor='#0b5d1e', linewidth=2.2, zorder=1))
    for B, lst in cj.items():
        ax.add_patch(Rectangle((B[0] - 1 + 0.04, B[1] - 1 + 0.04), 0.92, 0.92, facecolor=(1.0, 0.55, 0.0, 0.5),
                               edgecolor='#a34700', linewidth=2.2, zorder=1))
        for _, H in lst:
            ax.text(H[0] - 0.84, H[1] - 0.16, 'X', color='#e06800', fontsize=13, fontweight='bold', ha='center',
                    va='center', zorder=4)

    def piece(s, col, ch):
        ax.add_patch(Circle((s[0] - 0.5, s[1] - 0.5), 0.33, facecolor=col, edgecolor='black', linewidth=1.2, zorder=2))
        ax.text(s[0] - 0.5, s[1] - 0.5, ch, ha='center', va='center', fontsize=12, fontweight='bold',
                color='black' if ch == 'Z' else 'white', zorder=3)

    piece(pos.Z, '#f2c200', 'Z')
    for s in pos.T:
        piece(s, '#1f5fd1', 'T')
    for s in pos.D:
        piece(s, '#d12a1f', 'D')
    nmoves = len(normal) + len(cj)
    ax.text(N / 2 - 0.15, N + 0.95, f"{PIECES[key]['label']}  {PIECES[key]['betza']}  -  Ví dụ {idx}",
            ha='center', va='center', fontsize=13, fontweight='bold')
    ax.text(N / 2 - 0.15, N + 0.42, f"{desc}. Số nước đi hợp lệ: {nmoves}.", ha='center', va='center', fontsize=10.5)
    # chú thích quân
    yl = -0.78
    items = [('#f2c200', 'Z', 'Z: quân đang được xét'), ('#1f5fd1', 'T', 'T: quân cùng phe với Z'),
             ('#d12a1f', 'D', 'D: quân đối phương của Z')]
    for i, (col, ch, txt) in enumerate(items):
        cx = 0.0 + i * 3.5
        ax.add_patch(Circle((cx, yl), 0.2, facecolor=col, edgecolor='black', linewidth=1, zorder=2))
        ax.text(cx, yl, ch, ha='center', va='center', fontsize=8, fontweight='bold',
                color='black' if ch == 'Z' else 'white', zorder=3)
        ax.text(cx + 0.32, yl, txt, ha='left', va='center', fontsize=10)
    y = yl - 0.5
    for ln in lines:
        ax.text(-0.6, y, ln, ha='left', va='center', fontsize=9.3)
        y -= 0.36
    fn = os.path.join(OUT, f"{key}_{idx}.png")
    fig.savefig(fn, dpi=110, bbox_inches='tight')
    plt.close(fig)
    return fn


if __name__ == '__main__':
    keys = sys.argv[1:] or list(PIECES)
    for k in keys:
        for i, ex in enumerate(EXAMPLES[k], 1):
            print(draw(k, i, *ex))
