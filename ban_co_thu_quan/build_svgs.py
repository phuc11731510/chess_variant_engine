# -*- coding: utf-8 -*-
"""Sinh biểu tượng SVG cho 13 quân theo một bộ kí hiệu thống nhất.
Toạ độ lưới: quân ở (0,0), y tăng theo hướng tiến. 1 ô = U đơn vị SVG, tâm (50,50).

Bộ kí hiệu:
  đường liền              = đi và ăn (trượt / bước)
  đường đứt               = chỉ đi, không ăn
  mũi tên ở cuối          = trượt không giới hạn
  vạch chặn ở cuối (+ số) = trượt có giới hạn số ô
  chấm đặc đứng riêng     = ô nhảy tới, nhảy qua mọi quân (đi và ăn)
  đường thẳng tới chấm    = nhảy bị cản: các ô trên đường phải trống (n)
  chấm rỗng               = ô chỉ đi được, không ăn
  hình thoi vàng          = quân làm bàn đạp, KHÔNG bị ăn (p, g)
  chấm đỏ                 = ô chỉ ăn được (bắt sau khi nhảy qua bàn đạp, kiểu Pháo)
  dấu × đỏ                = quân đối phương bị nhảy qua và BỊ ĂN ([cj]); vòng tròn rỗng sau nó = ô hạ cánh
"""
import math, os

U = 10.0
GOLD, RED = '#e39b00', '#e0352b'
OUT = 'svg'
os.makedirs(OUT, exist_ok=True)


def P(x, y):
    return 50 + x * U, 50 - y * U


class G:
    def __init__(self):
        self.el = []

    def line(self, pts, dashed=False, w=3.0, color='currentColor'):
        d = ' '.join(f'{"M" if i == 0 else "L"}{P(*p)[0]:.1f},{P(*p)[1]:.1f}' for i, p in enumerate(pts))
        da = ' stroke-dasharray="4 3.2"' if dashed else ''
        self.el.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"{da}/>')

    def arrow(self, a, b, dashed=False, color='currentColor'):
        self.line([a, b], dashed, color=color)
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy); ux, uy = dx / L, dy / L
        px, py = -uy, ux
        s = 0.55
        p1 = (b[0] - s * ux + s * 0.75 * px, b[1] - s * uy + s * 0.75 * py)
        p2 = (b[0] - s * ux - s * 0.75 * px, b[1] - s * uy - s * 0.75 * py)
        self.line([p1, b, p2], False, color=color)

    def bar(self, a, b, dashed=False, label=None):
        self.line([a, b], dashed)
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy); px, py = -dy / L, dx / L
        s = 0.45
        self.line([(b[0] + s * px, b[1] + s * py), (b[0] - s * px, b[1] - s * py)], False)
        if label:
            ux, uy = dx / L, dy / L
            tx, ty = P(b[0] + 0.55 * ux + 0.55 * px, b[1] + 0.55 * uy + 0.55 * py)
            self.el.append(f'<text x="{tx:.1f}" y="{ty:.1f}" font-size="8.5" font-weight="700" font-family="system-ui,sans-serif" fill="currentColor" text-anchor="middle" dominant-baseline="central">{label}</text>')

    def dot(self, p, filled=True, r=3.1, color='currentColor'):
        x, y = P(*p)
        if filled:
            self.el.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}"/>')
        else:
            self.el.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="none" stroke="{color}" stroke-width="1.8"/>')

    def diamond(self, p, s=3.6):
        x, y = P(*p)
        self.el.append(f'<path d="M{x:.1f},{y - s:.1f} L{x + s:.1f},{y:.1f} L{x:.1f},{y + s:.1f} L{x - s:.1f},{y:.1f} Z" fill="{GOLD}" stroke="currentColor" stroke-width="0.9"/>')

    def cross(self, p, s=3.0):
        x, y = P(*p)
        self.el.append(f'<path d="M{x - s:.1f},{y - s:.1f} L{x + s:.1f},{y + s:.1f} M{x - s:.1f},{y + s:.1f} L{x + s:.1f},{y - s:.1f}" stroke="{RED}" stroke-width="2.6" stroke-linecap="round"/>')


ORTH = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIAG = [(1, 1), (-1, 1), (1, -1), (-1, -1)]
KNIGHT = [(1, 2), (-1, 2), (1, -2), (-1, -2), (2, 1), (-2, 1), (2, -1), (-2, -1)]
CAMEL = [(1, 3), (-1, 3), (1, -3), (-1, -3), (3, 1), (-3, 1), (3, -1), (-3, -1)]
ZEBRA = [(2, 3), (-2, 3), (2, -3), (-2, -3), (3, 2), (-3, 2), (3, -2), (-3, -2)]
sgn = lambda t: (t > 0) - (t < 0)
SLIDE_R = 3.9  # độ dài vẽ cho quân trượt không giới hạn


def far(d, r=SLIDE_R):
    L = math.hypot(*d)
    return (d[0] / L * r, d[1] / L * r)


def knight_path(v):  # đường đi của nN (n[o]): ô cản rồi ô đích
    a, b = v
    blk = (sgn(a), 0) if abs(a) == 2 else (0, sgn(b))
    return [(0, 0), blk, v]


def piece_K(g):
    g.line([(-1, -1), (1, -1), (1, 1), (-1, 1), (-1, -1)])
    for x in range(-1, 2):
        for y in range(-1, 2):
            if x or y: g.dot((x, y))
    g.line([(-2, -2), (2, -2), (2, 2), (-2, 2), (-2, -2)], dashed=True, w=2)
    for x in range(-2, 3):
        for y in range(-2, 3):
            if max(abs(x), abs(y)) == 2: g.dot((x, y), filled=False, r=2.4)


def piece_A(g):  # F2t[WFF]
    for d in DIAG:
        g.bar((0, 0), (2 * d[0], 2 * d[1]))
    for u in ORTH:
        g.line([(0, 0), u])
        for d in DIAG:
            if u[0] * d[0] + u[1] * d[1] > 0:
                end = (u[0] + d[0] * 1.9, u[1] + d[1] * 1.9)
                g.arrow(u, end)
        g.dot(u, r=2.6)


def piece_B(g):  # vWFFmWWcpWW
    for d in DIAG:
        g.arrow((0, 0), far(d))
    for u in ORTH:
        g.arrow((0, 0), far(u, 1.6), dashed=True)
        g.diamond((u[0] * 2, u[1] * 2))
        g.line([(u[0] * 2.45, u[1] * 2.45), (u[0] * 3.55, u[1] * 3.55)], w=2, color=RED)
        g.dot((u[0] * 3.75, u[1] * 3.75), color=RED)
    for u in [(0, 1), (0, -1)]:
        g.line([(0, 0), u]); g.dot(u)


def piece_C(g):  # CHmFF[cj1]FF
    for v in CAMEL: g.dot(v)
    for u in ORTH: g.dot((3 * u[0], 3 * u[1]))
    for d in DIAG:
        g.line([(0, 0), (1.55 * d[0], 1.55 * d[1])], dashed=True)
        g.cross((2 * d[0], 2 * d[1]))
        g.dot((3 * d[0], 3 * d[1]), filled=False, r=2.8)


def piece_D(g):  # NmF4cpF4
    for v in KNIGHT: g.dot(v)
    for d in DIAG:
        g.bar((0, 0), (2.75 * d[0], 2.75 * d[1]), dashed=True, label='4')
        g.diamond((1.35 * d[0], 1.35 * d[1]), s=3.0)
        g.line([(1.75 * d[0], 1.75 * d[1]), (2.35 * d[0], 2.35 * d[1])], w=2, color=RED)
        g.dot((2.55 * d[0], 2.55 * d[1]), color=RED, r=2.6)


def piece_E(g):  # FZgF3
    for d in DIAG:
        g.line([(0, 0), d]); g.dot(d)
        g.line([d, (2 * d[0], 2 * d[1])], w=1.6)
        g.diamond((2 * d[0], 2 * d[1]))
        g.dot((3 * d[0], 3 * d[1]))
    for v in ZEBRA: g.dot(v)


def piece_F(g):  # DHfrClfCblCrbC
    for u in ORTH:
        g.dot((2 * u[0], 2 * u[1])); g.dot((3 * u[0], 3 * u[1]))
    for v in [(3, 1), (-1, 3), (-3, -1), (1, -3)]:
        x0, y0 = P(0, 0); x1, y1 = P(*v)
        # cung mảnh xoáy theo chiều chong chóng, chỉ để nhìn thấy tính bất đối xứng
        cx, cy = P(v[0] * 0.5 - v[1] * 0.35, v[1] * 0.5 + v[0] * 0.35)
        g.el.append(f'<path d="M{x0:.1f},{y0:.1f} Q{cx:.1f},{cy:.1f} {x1:.1f},{y1:.1f}" fill="none" stroke="currentColor" stroke-width="1.3" stroke-dasharray="1.5 2.2" opacity="0.8"/>')
        g.dot(v, r=3.4)


def piece_G(g):  # WGgW3
    for u in ORTH:
        g.line([(0, 0), u]); g.dot(u)
        g.line([u, (2 * u[0], 2 * u[1])], w=1.6)
        g.diamond((2 * u[0], 2 * u[1]))
        g.dot((3 * u[0], 3 * u[1]))
    for d in DIAG: g.dot((3 * d[0], 3 * d[1]))


def piece_H(g):  # sDt[WnA]
    for s in [(2, 0), (-2, 0)]: g.dot(s)
    for u in ORTH:
        g.line([(0, 0), u]); g.dot(u, r=2.6)
        for d in [(2, 2), (-2, 2), (2, -2), (-2, -2)]:
            if u[0] * d[0] + u[1] * d[1] > 0:
                t = (u[0] + d[0], u[1] + d[1])
                g.line([u, t]); g.dot(t)


def piece_J(g):  # ZnD
    for v in ZEBRA: g.dot(v)
    for u in ORTH:
        t = (2 * u[0], 2 * u[1]); g.line([(0, 0), t]); g.dot(t)


def piece_L(g):  # nGsWWvW
    for s in [(1, 0), (-1, 0)]: g.arrow((0, 0), far(s))
    for u in [(0, 1), (0, -1)]: g.line([(0, 0), u]); g.dot(u)
    for d in DIAG:
        t = (3 * d[0], 3 * d[1]); g.line([(0, 0), t]); g.dot(t)


def piece_M(g):  # nNfrNlfNblNrbN
    for v in [(2, 1), (-1, 2), (-2, -1), (1, -2)]: g.dot(v, r=3.4)
    for v in [(1, 2), (-2, 1), (-1, -2), (2, -1)]:
        g.line(knight_path(v)); g.dot(v)


def piece_N(g):  # nN[cj]nN
    for v in KNIGHT:
        g.line(knight_path(v))
        g.line([v, (2 * v[0], 2 * v[1])], w=1.2, dashed=True)
        g.dot(v)
        g.cross(v, s=2.2)
        g.dot((2 * v[0] * 0.92, 2 * v[1] * 0.92), filled=False, r=2.4)


PIECES = [('K', 'Quân hoàng gia', 'WFmnDmnAmnN', piece_K), ('A', 'Quân 1', 'F2t[WFF]', piece_A), ('B', 'Quân 2', 'vWFFmWWcpWW', piece_B),
          ('C', 'Quân 3', 'CHmFF[cj1]FF', piece_C), ('D', 'Quân 4', 'NmF4cpF4', piece_D), ('E', 'Quân 5', 'FZgF3', piece_E),
          ('F', 'Quân 6', 'DHfrClfCblCrbC', piece_F), ('G', 'Quân 7', 'WGgW3', piece_G), ('H', 'Quân 8', 'sDt[WnA]', piece_H),
          ('J', 'Quân 9', 'ZnD', piece_J), ('L', 'Quân 10', 'nGsWWvW', piece_L), ('M', 'Quân 11', 'nNfrNlfNblNrbN', piece_M),
          ('N', 'Quân 12', 'nN[cj]nN', piece_N)]
STYLE = {'w': ('#f7f5ef', '#1d1d1d'), 'b': ('#262626', '#f3f3f3')}


def svg(code, side, fn):
    g = G(); fn(g)
    fill, ink = STYLE[side]
    body = '\n  '.join(g.el)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100" color="{ink}">\n'
            f'  <circle cx="50" cy="50" r="48" fill="{fill}" stroke="{ink}" stroke-width="2.5"/>\n'
            f'  <circle cx="50" cy="50" r="2.4" fill="{ink}"/>\n  {body}\n</svg>\n')


if __name__ == '__main__':
    for code, name, betza, fn in PIECES:
        for side in 'wb':
            with open(os.path.join(OUT, f'{code}_{side}.svg'), 'w', encoding='utf-8') as f:
                f.write(svg(code, side, fn))
    print('ok', len(PIECES) * 2, 'files')
