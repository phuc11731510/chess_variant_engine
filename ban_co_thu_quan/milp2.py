# -*- coding: utf-8 -*-
"""Chọn 12 quân + thế khởi đầu (đủ 12 loại, mỗi loại 1 hoặc 2 quân) bằng MILP, kiểm tra thế đầu thật, lặp với lát cắt."""
import json, re, sys, subprocess
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import lil_matrix

safe = json.load(open('safe_all.json', encoding='utf-8'))
pool = [x for x in json.load(open('pool_eg.json', encoding='utf-8'))
        if max(x['r']) <= 1.10 and not x['add'].startswith('WF') and not (x['core'] == 't[FWW]' and 'F' in x['add'])]
seenp, pool2 = set(), []
for x in pool:
    if x['p'] in seenp or not safe.get(x['p']):
        continue
    seenp.add(x['p'])
    pool2.append(x)
pool = pool2
FREE = ['a3', 'j3', 'a2', 'c2', 'e2', 'f2', 'h2', 'j2', 'a1', 'b1', 'c1', 'd1', 'e1', 'f1', 'g1', 'h1', 'i1', 'j1']
KSQ = ['a1', 'b1', 'c1', 'd1', 'e1', 'f1', 'g1', 'h1', 'i1', 'j1']
ROYAL = {'W', 'F', 'D', 'A', 'N', 'm', 'n'}
RULE = {'W': [6], 'F': [6], 'H': [2], 'G': [2], 'C': [2], 'Z': [2], 'rider': [4, 6], 'p': [2], 'g': [2], 'i': [0], 't': [2], 'cj': [2],
        'N': [2, 4], 'A': [2, 4], 'D': [2, 4]}
for k in ['num', 'm', 'c', 'f', 'b', 's', 'v', 'l', 'r', 'n']:
    RULE[k] = [2, 4, 6]
famMax = {'t': 2, 'p': 2, 'g': 2, 'cj': 2, 'chiral': 2, 'sv': 2, 'fb': 2, 'leap': 2}
M = 12
target = [1.08 - j * (1.08 - 0.22) / (M - 1) for j in range(M)]
P = len(pool)
print('pool', P, file=sys.stderr, flush=True)
feats = list(RULE)
yv = [(k, o) for k in feats for o in RULE[k]]
var = {}


def v(name):
    if name not in var:
        var[name] = len(var)
    return var[name]


for i in range(P):
    v(('x', i)); v(('q', i))
for i in range(P):
    for s in safe[pool[i]['p']]:
        v(('a', i, s))
for i in range(P):
    for j in range(M):
        v(('z', i, j))
for t in range(len(yv)):
    v(('y', t))
for s in KSQ:
    v(('k', s))
NV = len(var)
rows = []


def add(coefs, lo, hi):
    rows.append((coefs, lo, hi))


add([(v(('x', i)), 1) for i in range(P)], M, M)
add([(v(('q', i)), 1) for i in range(P)], 5, 5)
for i in range(P):
    add([(v(('q', i)), 1), (v(('x', i)), -1)], -1, 0)
    add([(v(('a', i, s)), 1) for s in safe[pool[i]['p']]] + [(v(('x', i)), -1), (v(('q', i)), -1)], 0, 0)
for s in FREE:
    co = [(v(('a', i, s)), 1) for i in range(P) if s in safe[pool[i]['p']]]
    if s in KSQ:
        co.append((v(('k', s)), 1))
    add(co, 1, 1)
add([(v(('k', s)), 1) for s in KSQ], 1, 1)
for k in feats:
    base = 1 if k in ROYAL else 0
    ts = [t for t, (kk, o) in enumerate(yv) if kk == k]
    add([(v(('x', i)), 1) for i in range(P) if k in pool[i]['feat']] + [(v(('y', t)), -yv[t][1]) for t in ts], -base, -base)
    add([(v(('y', t)), 1) for t in ts], 1, 1)
for f, mx in famMax.items():
    add([(v(('x', i)), 1) for i in range(P) if pool[i]['fam'] == f], 0, mx)


def atoms(s):
    return ''.join(sorted(re.findall(r'n?[WFDAHGNCZ]', s)))


groups = {}
for i, x in enumerate(pool):
    if x['core']:
        groups.setdefault('core:' + x['core'], []).append(i)
    a = atoms(x['add']) if x['core'] else atoms(x['p'])
    if a:
        groups.setdefault('add:' + a, []).append(i)
for g, idx in groups.items():
    if len(idx) > 1:
        add([(v(('x', i)), 1) for i in idx], 0, 1)
for i in range(P):
    add([(v(('z', i, j)), 1) for j in range(M)] + [(v(('x', i)), -1)], 0, 0)
for j in range(M):
    add([(v(('z', i, j)), 1) for i in range(P)], 1, 1)
cuts = []


def solve():
    allrows = rows + cuts
    A = lil_matrix((len(allrows), NV))
    lb, ub = [], []
    for r, (co, lo, hi) in enumerate(allrows):
        for c, val in co:
            A[r, c] = val
        lb.append(lo); ub.append(hi)
    c = np.zeros(NV)
    for i in range(P):
        c[v(('x', i))] = 0.01 * len(pool[i]['p']) / 200
        for j in range(M):
            c[v(('z', i, j))] = (pool[i]['avg'] - target[j]) ** 2
    return milp(c, constraints=LinearConstraint(A.tocsr(), lb, ub), integrality=np.ones(NV), bounds=Bounds(0, 1),
                options={'time_limit': 900})


for it in range(300):
    res = solve()
    print('iter', it, res.status, res.message, res.fun, file=sys.stderr, flush=True)
    if res.x is None:
        break
    X = res.x
    sel = [i for i in range(P) if X[v(('x', i))] > 0.5]
    setup = {}
    for i in sel:
        for s in safe[pool[i]['p']]:
            if X[v(('a', i, s))] > 0.5:
                setup[s] = pool[i]['p']
    ks = [s for s in KSQ if X[v(('k', s))] > 0.5][0]
    setup[ks] = 'K'
    r = subprocess.run(['node', 'verify_setup.js'], input=json.dumps(setup), capture_output=True, text=True, encoding='utf-8')
    chk = json.loads(r.stdout)
    print('  verify', chk['ok'], chk['nbad'], chk['pairs'][:8], file=sys.stderr, flush=True)
    if chk['ok']:
        out = {'pieces': [pool[i] for i in sorted(sel, key=lambda i: -pool[i]['avg'])],
               'count': {pool[i]['p']: int(round(X[v(('x', i))] + X[v(('q', i))])) for i in sel}, 'setup': setup, 'obj': res.fun,
               'code': chk['code'], 'first': chk['first']}
        json.dump(out, open('design2.json', 'w', encoding='utf-8'), ensure_ascii=False)
        for x in out['pieces']:
            print(f"  {x['p']:<24} {' '.join(f'{t:.2f}' for t in x['r'])} avg {x['avg']:.2f} x{out['count'][x['p']]} {x['fam']}")
        print('  setup', setup, '\n  code', chk['code'])
        break
    where = {s: i for i in sel for s in safe[pool[i]['p']] if X[v(('a', i, s))] > 0.5}
    nc = 0
    for pr in chk['pairs']:
        sq = pr.split('+')
        if any(q not in where for q in sq):
            continue  # liên quan quân hoàng gia hoặc Tốt: bỏ qua
        co = [(v(('a', where[q], q)), 1) for q in sq]
        cuts.append((co, 0, len(co) - 1)); nc += 1
    if nc == 0:
        used = [(v(('a', i, s)), 1) for s, i in where.items()]
        cuts.append((used, 0, len(used) - 1))
    print('  cuts +', nc, 'total', len(cuts), file=sys.stderr, flush=True)
