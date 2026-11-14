# -*- coding: utf-8 -*-
"""Trang xem 13 biểu tượng SVG: chú giải, cỡ lớn cho hai màu, và bàn cờ Thế 1 ở cỡ thật."""
import os
from build_svgs import PIECES, svg, G, P, GOLD, RED

def legend_icon(draw):
    g = G(); draw(g)
    return f'<svg viewBox="-4 32 42 36" width="80" height="68" color="currentColor">{"".join(g.el)}</svg>'

def L_solid(g): g.line([(-4.4, 0), (-2.4, 0)]); g.arrow((-2.4, 0), (-1.0, 0)) if False else None
LEG = [
    ('đường liền: đi và ăn được', lambda g: g.line([(-5, 0), (-2, 0)])),
    ('đường đứt: chỉ đi, không ăn', lambda g: g.line([(-5, 0), (-2, 0)], dashed=True)),
    ('mũi tên: trượt không giới hạn', lambda g: g.arrow((-5, 0), (-2, 0))),
    ('vạch chặn: trượt tối đa tới đó (số = số ô)', lambda g: g.bar((-5, 0), (-2.4, 0), label='4')),
    ('chấm đứng riêng: nhảy tới, bỏ qua mọi quân ở giữa', lambda g: g.dot((-3.5, 0))),
    ('đường thẳng tới chấm: nhảy bị cản (n), các ô trên đường phải trống', lambda g: (g.line([(-5, 0), (-2.5, 0)]), g.dot((-2.5, 0)))),
    ('chấm rỗng: ô chỉ đi được', lambda g: g.dot((-3.5, 0), filled=False, r=2.6)),
    ('thoi vàng: quân bàn đạp (phe nào cũng được), không bị ăn', lambda g: g.diamond((-3.5, 0))),
    ('thoi vàng + chấm ngay sau: Châu chấu (g), đáp ngay sau bàn đạp', lambda g: (g.diamond((-4.5, 0)), g.dot((-3, 0)))),
    ('thoi vàng + chấm đỏ: Pháo (p), chỉ ăn quân sau bàn đạp', lambda g: (g.diamond((-5, 0)), g.line([(-4.4, 0), (-2.8, 0)], w=2, color=RED), g.dot((-2.4, 0), color=RED))),
    ('× đỏ + vòng rỗng: bắt nhảy [cj], quân bị nhảy qua bị ăn, hạ cánh ở ô trống phía sau', lambda g: (g.cross((-4.5, 0)), g.dot((-2.8, 0), filled=False, r=2.6))),
]
SETUP = 'cfbeggkjda/htntmhtntm/lppppppppl/10/10/10/10/LPPPPPPPPL/HTNTMHTNTM/CFBEGGKJDA'

def main():
    icons = {(c, s): svg(c, s, fn) for c, _, _, fn in PIECES for s in 'wb'}
    leg = ''.join(f'<div class="lg">{legend_icon(f)}<span>{t}</span></div>' for t, f in LEG)
    cards = ''.join(
        f'<div class="card"><div class="pair">{icons[(c, "w")]}{icons[(c, "b")]}</div><b>{name}</b> <span class="code">{c}</span><br><code>{betza}</code></div>'
        for c, name, betza, _ in PIECES)
    rows = []
    for k, r in enumerate(SETUP.split('/')):
        cells, y = [], 9 - k
        for tok in __import__('re').findall(r'\d+|[A-Za-z]', r):
            if tok.isdigit():
                cells += [''] * int(tok)
            else:
                cells.append(tok)
        rows.append(cells)
    sq = []
    for k, cells in enumerate(rows):
        for x, t in enumerate(cells):
            y = 9 - k
            cls = 'l' if (x + y) % 2 else 'd'
            inner = ''
            if t:
                up = t.upper(); side = 'w' if t == up else 'b'
                if up in 'PT':
                    inner = f'<div class="pawn {side}">{up}</div>'
                else:
                    inner = icons[(up, side)]
            sq.append(f'<div class="sq {cls}">{inner}</div>')
    html = f'''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Biểu tượng quân cờ</title><style>
:root{{--bg:#f6f4ef;--fg:#1d1d1f;--card:#fff;--line:#dedbd2;--muted:#62626a}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--bg:#16161a;--fg:#ececf0;--card:#202026;--line:#34343c;--muted:#a4a4ae}}}}
:root[data-theme="dark"]{{--bg:#16161a;--fg:#ececf0;--card:#202026;--line:#34343c;--muted:#a4a4ae}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}}
main{{max-width:1180px;margin:0 auto;padding:18px 16px 50px}}
h2{{margin:26px 0 10px}}
.legend{{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,330px),1fr));gap:6px 18px}}
.lg{{display:flex;align-items:center;gap:8px}} .lg svg{{flex:none;color:var(--fg)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,260px),1fr));gap:12px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}}
.pair{{display:flex;gap:10px;margin-bottom:6px}} .pair svg{{width:110px;height:110px}}
.code{{display:inline-block;border:1px solid var(--line);border-radius:5px;padding:0 6px;font-weight:700}}
code{{font-size:.85rem}}
.board{{display:grid;grid-template-columns:repeat(10,1fr);width:min(100%,640px);aspect-ratio:1/1;border:2px solid #6b5137}}
.sq{{display:flex;align-items:center;justify-content:center}} .sq.l{{background:#f0d9b5}} .sq.d{{background:#b58863}}
.sq svg{{width:88%;height:88%}}
.pawn{{width:62%;aspect-ratio:1/1;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:clamp(10px,2.2vw,18px);border:2px solid #1d1d1d}}
.pawn.w{{background:#f7f5ef;color:#1d1d1d}} .pawn.b{{background:#262626;color:#f3f3f3}}
.muted{{color:var(--muted);font-size:.88rem}}
</style></head><body><main>
<h1 style="margin:0">Biểu tượng 13 quân</h1>
<p class="muted">Mỗi biểu tượng vẽ quân ở tâm, hướng tiến là phía trên. Chữ ở góc thẻ là chữ cái quân dùng trên trang bàn cờ. Biểu tượng chỉ gợi ý hình dạng nước đi, không vẽ đúng tỉ lệ khoảng cách.</p>
<h2>Chú giải</h2><div class="legend">{leg}</div>
<h2>13 quân (trắng / đen)</h2><div class="grid">{cards}</div>
<h2>Cỡ thật trên bàn cờ (Thế 1)</h2><div class="board">{''.join(sq)}</div>
<p class="muted">Hai loại Tốt (P, T) tạm hiện bằng chữ, vì bạn đã có ảnh riêng cho chúng.</p>
</main></body></html>'''
    open('bieu_tuong_quan.html', 'w', encoding='utf-8').write(html)
    print('ok')

if __name__ == '__main__':
    main()
