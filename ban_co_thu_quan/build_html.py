# -*- coding: utf-8 -*-
import base64, os, sys, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pieces_rules import PIECES, Pos, all_moves, name
from examples import EXAMPLES, sq, L
from texts import DESC, REMARK, NAMES

HERE = os.path.dirname(os.path.abspath(__file__))

def img(key, i):
    with open(os.path.join(HERE, 'images', f'{key}_{i}.png'), 'rb') as f:
        return 'data:image/png;base64,' + base64.b64encode(f.read()).decode()

def lst(xs):
    return ', '.join(xs) if xs else 'không có'

parts = []
toc = []
for key in PIECES:
    betza = PIECES[key]['betza']
    title = f"{NAMES[key]}: <code>{betza}</code>"
    toc.append(f'<a href="#{key}">{NAMES[key]} <code>{betza}</code></a>')
    sec = [f'<section id="{key}"><h2>{title}</h2>', '<h3>Khả năng của quân</h3>', DESC[key]]
    for i, (desc, Z, T, D) in enumerate(EXAMPLES[key], 1):
        pos = Pos(sq(Z), L(T), L(D))
        rules, normal, cj = all_moves(key, pos)
        n = len(normal) + len(cj)
        sec.append(f'<div class="ex"><h3>Ví dụ {i}: {desc}</h3>')
        sec.append(f'<img src="{img(key, i)}" alt="{NAMES[key]} {betza} ví dụ {i}">')
        sec.append(f'<p><b>Vị trí:</b> Z ở {Z} (ô $A$); T ở {lst(T.split())}; D ở {lst(D.split())}. <b>Số nước đi hợp lệ: {n}.</b></p><ul>')
        for rname, (moves, notes) in rules:
            g = [name(b) for b, k, h in moves if k == 'n']
            o = [f"{name(b)} (xóa D ở {name(h)})" for b, k, h in moves if k == 'cj']
            chosen = g + o
            line = f'<li><b>{rname}:</b> ' + (f"chọn {', '.join(chosen)}." if chosen else 'không chọn ô nào.')
            if notes:
                line += '<ul>' + ''.join(f'<li>{html.escape(x).replace("&#x27;", "\'")}</li>' for x in notes) + '</ul>'
            sec.append(line + '</li>')
        sec.append('</ul>')
        multi = [name(b) for b, r in normal.items() if len(r) > 1]
        if multi:
            sec.append(f'<p>Ô được nhiều quy tắc cùng chọn (mỗi ô vẫn chỉ là một nước đi): {", ".join(multi)}.</p>')
        removed = set(normal) | {h for v in cj.values() for _, h in v}
        untouched = [name(d) for d in sorted(pos.D) if d not in removed]
        if pos.D:
            sec.append(f'<p>Quân D không bị nước nào xóa: {lst(untouched)}.</p>')
        sec.append(f'<p class="note"><b>Điều cần chú ý:</b> {REMARK[key][i-1]}</p></div>')
    sec.append('</section>')
    parts.append('\n'.join(sec))

page = f'''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nước đi 13 quân</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.css">
<script defer src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.js"></script>
<script defer src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/contrib/auto-render.min.js"
 onload="renderMathInElement(document.body,{{delimiters:[{{left:'$$',right:'$$',display:true}},{{left:'$',right:'$',display:false}}]}})"></script>
<style>
:root{{--bg:#fbfaf7;--fg:#1d1d1f;--muted:#5b5b62;--card:#ffffff;--line:#e3e0d8;--accent:#0b5d1e;--note:#fff6e0}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--bg:#17171a;--fg:#ececf0;--muted:#a3a3ad;--card:#202024;--line:#33333a;--accent:#7fd18f;--note:#2e2716}}}}
:root[data-theme="dark"]{{--bg:#17171a;--fg:#ececf0;--muted:#a3a3ad;--card:#202024;--line:#33333a;--accent:#7fd18f;--note:#2e2716}}
body{{background:var(--bg);color:var(--fg);font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif;margin:0}}
main{{max-width:920px;margin:0 auto;padding:24px 16px 80px}}
h1{{font-size:1.7rem;margin:.2em 0}} h2{{border-top:2px solid var(--line);padding-top:1em;margin-top:2.2em;color:var(--accent)}}
code{{background:var(--card);border:1px solid var(--line);border-radius:4px;padding:0 .3em;font-size:.95em}}
.ex{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin:18px 0}}
.ex img{{max-width:100%;height:auto;display:block;margin:8px auto;border-radius:6px;background:#fff}}
.note{{background:var(--note);padding:8px 12px;border-radius:6px}}
nav{{columns:2;column-gap:24px;font-size:.95rem}} nav a{{display:block;color:var(--fg);text-decoration:none;padding:2px 0}}
@media (max-width:600px){{nav{{columns:1}}}}
</style></head><body><main>
<h1>Nước đi của 13 quân</h1>
<p>Bàn cờ $10\times10$ được coi là các điểm nguyên $(x,y)$ với $1\le x\le 10$ (cột a đến j) và $1\le y\le 10$ (hàng 1 đến 10). Chiều tăng của $y$ là hướng tiến của quân $Z$. Mọi quân trong bộ này có tập nước đi không đổi khi xoay bàn cờ $180^\circ$, nên quân của phe bên kia dùng đúng các vector như dưới đây.</p>
<p><b>Kí hiệu trên ảnh.</b> Z (vàng) là quân đang được xét, và ô chứa nó là ô $A$. T (xanh dương) là quân cùng phe với Z. D (đỏ) là quân đối phương của Z.
Với mỗi ô xanh lá, có một nước đi hợp lệ chọn ô xanh lá đó làm ô $B$; thực hiện nước đi này nghĩa là: xóa quân đối phương ở ô $B$ nếu có; xóa quân Z khỏi ô $A$; đặt quân Z vừa xóa vào ô $B$.
Với mỗi ô cam (chỉ có ở quân 7 và quân 12), có một nước đi hợp lệ chọn ô cam đó làm ô $B$; gọi $H=\frac{{A+B}}{{2}}$ là ô nằm chính giữa (đánh dấu bằng chữ X màu cam); thực hiện nước đi này nghĩa là: xóa quân đối phương ở ô $H$; xóa quân Z khỏi ô $A$; đặt quân Z vừa xóa vào ô $B$.</p>
<p>Tập ô $B$ của mọi ví dụ được tính bằng hai chương trình độc lập (một chương trình bám theo từng câu quy tắc dưới đây, một chương trình đọc trực tiếp ký hiệu Betza theo quy ước của bạn); hai chương trình khớp nhau trên 39 000 thế cờ ngẫu nhiên.</p>
<nav>{"".join(toc)}</nav>
{"".join(parts)}
</main></body></html>'''
page = page.replace(chr(9) + 'imes', chr(92) + 'times').replace(chr(12) + 'rac', chr(92) + 'frac')
open(os.path.join(HERE, 'nuoc_di_13_quan.html'), 'w', encoding='utf-8').write(page)
print(len(page) // 1024, 'KB')
