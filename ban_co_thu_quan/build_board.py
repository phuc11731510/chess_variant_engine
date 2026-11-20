import re
eng = open('betza_sim.js', encoding='utf-8').read()
eng = eng.replace("'use strict';", '')
eng = re.sub(r'\nmodule\.exports\s*=.*', '\n', eng)
tpl = open('board_template.html', encoding='utf-8').read()
assert '/*ENGINE*/' in tpl
import json, os
icons = {}
for f in os.listdir('svg'):
    code, side = f[:-4].split('_')
    icons.setdefault(code, {})[side] = open(os.path.join('svg', f), encoding='utf-8').read().strip()
tpl = tpl.replace('/*ICONS*/null', json.dumps(icons, ensure_ascii=False))
open('index.html', 'w', encoding='utf-8').write(tpl.replace('/*ENGINE*/', eng))
print('ok', len(tpl) + len(eng))
