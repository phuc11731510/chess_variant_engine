# -*- coding: utf-8 -*-
import base64, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pieces_rules2 import PIECES
from examples2 import EXAMPLES
NAMES = {k: v['label'] for k, v in __import__('pieces_rules2').PIECES.items()}
HERE = os.path.dirname(os.path.abspath(__file__))
secs, toc = [], []
for key in PIECES:
    b = PIECES[key]['betza']
    toc.append(f'<a href="#{key}">{NAMES[key]} <code>{b}</code></a>')
    imgs = []
    for i in range(1, len(EXAMPLES[key]) + 1):
        data = base64.b64encode(open(os.path.join(HERE, 'images2', f'{key}_{i}.png'), 'rb').read()).decode()
        imgs.append(f'<img src="data:image/png;base64,{data}" alt="{NAMES[key]} {b} ví dụ {i}">')
    secs.append(f'<section id="{key}"><h2>{NAMES[key]}: <code>{b}</code></h2><div class="grid">{"".join(imgs)}</div></section>')
page = f'''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ảnh ví dụ bộ quân mới</title><style>
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
</style></head><body><main><h1>Ảnh ví dụ bộ quân mới</h1><nav>{"".join(toc)}</nav>{"".join(secs)}</main></body></html>'''
open(os.path.join(HERE, 'anh_vi_du_bo_moi.html'), 'w', encoding='utf-8').write(page)
print(len(page)//1024, 'KB')
