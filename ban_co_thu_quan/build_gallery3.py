# -*- coding: utf-8 -*-
import base64, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pieces_rules3 import PIECES
from examples3 import EXAMPLES
import build_svgs as SV
from build_svg_gallery import LEG, legend_icon
KEY2CODE = {'R': 'K', 'Q1': 'A', 'Q2': 'B', 'Q3': 'C', 'Q4': 'D', 'Q5': 'E', 'Q6': 'F', 'Q7': 'G', 'Q8': 'H', 'Q9': 'J', 'Q10': 'L', 'Q11': 'M', 'Q12': 'N'}
ICON = {c: {s: SV.svg(c, s, fn) for s in 'wb'} for c, _, _, fn in SV.PIECES}
NAMES = {k: v['label'] for k, v in __import__('pieces_rules3').PIECES.items()}
HERE = os.path.dirname(os.path.abspath(__file__))
secs, toc = [], []
for key in PIECES:
    b = PIECES[key]['betza']
    toc.append(f'<a href="#{key}">{NAMES[key]} <code>{b}</code></a>')
    imgs = []
    for i in range(1, len(EXAMPLES[key]) + 1):
        data = base64.b64encode(open(os.path.join(HERE, 'images3', f'{key}_{i}.png'), 'rb').read()).decode()
        imgs.append(f'<img src="data:image/png;base64,{data}" alt="{NAMES[key]} {b} ví dụ {i}">')
    c = KEY2CODE[key]
    secs.append(f'<section id="{key}"><h2><span class="icons">{ICON[c]["w"]}{ICON[c]["b"]}</span><span>{NAMES[key]} <span class="ltr">{c}</span>: <code>{b}</code></span></h2><div class="grid">{"".join(imgs)}</div></section>')
LEGEND = ''.join(f'<div class="lg">{legend_icon(f)}<span>{t}</span></div>' for t, f in LEG)
page = f'''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ảnh ví dụ bộ quân thứ ba</title><style>
:root{{--bg:#fbfaf7;--fg:#1d1d1f;--line:#e3e0d8;--accent:#0b5d1e;--card:#fff}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--bg:#17171a;--fg:#ececf0;--line:#33333a;--accent:#7fd18f;--card:#202024}}}}
:root[data-theme="dark"]{{--bg:#17171a;--fg:#ececf0;--line:#33333a;--accent:#7fd18f;--card:#202024}}
body{{background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;margin:0}}
main{{max-width:1200px;margin:0 auto;padding:24px 16px 60px}}
h2{{color:var(--accent);border-top:2px solid var(--line);padding-top:.8em;margin-top:1.8em}}
code{{background:var(--card);border:1px solid var(--line);border-radius:4px;padding:0 .3em}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,520px),1fr));gap:14px}}
.grid img{{width:100%;height:auto;border-radius:8px;background:#fff;border:1px solid var(--line)}}
nav{{columns:3;column-gap:20px}} nav a{{display:block;color:var(--fg);text-decoration:none;padding:2px 0}}
@media (max-width:700px){{nav{{columns:1}}}}
h2{{display:flex;align-items:center;gap:14px;flex-wrap:wrap}}
.icons{{display:flex;gap:8px}} .icons svg{{width:84px;height:84px}}
.ltr{{display:inline-block;border:1px solid var(--line);border-radius:5px;padding:0 7px;font-size:.9em}}
.legend{{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,330px),1fr));gap:4px 18px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 14px}}
.lg{{display:flex;align-items:center;gap:8px;font-size:.92rem}} .lg svg{{flex:none;color:var(--fg)}}
</style></head><body><main><h1>Ảnh ví dụ bộ quân thứ ba</h1><h2 style="border:0;margin-top:.6em">Chú giải biểu tượng quân</h2><div class="legend">{LEGEND}</div><p style="opacity:.75;font-size:.9rem">Biểu tượng vẽ quân ở tâm, hướng tiến ở phía trên; chỉ gợi ý hình dạng nước đi, không đúng tỉ lệ khoảng cách. Chữ trong khung là chữ cái quân trên trang bàn cờ.</p><nav>{"".join(toc)}</nav>{"".join(secs)}</main></body></html>'''
open(os.path.join(HERE, 'anh_vi_du_bo_3.html'), 'w', encoding='utf-8').write(page)
print(len(page)//1024, 'KB')
