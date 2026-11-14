import json, re, sys
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import lil_matrix

pool = [x for x in json.load(open('pool_eg.json', encoding='utf-8')) if max(x['r']) <= 1.10 and not x['add'].startswith('WF') and not (x['core'] == 't[FWW]' and 'F' in x['add'])]
ban = set(sys.argv[1:])
pool = [x for x in pool if x['p'] not in ban]
ROYAL = {'W', 'F', 'D', 'A', 'N', 'm', 'n'}
RULE = {'W': [6], 'F': [6], 'H': [2], 'G': [2], 'C': [2], 'Z': [2], 'rider': [4, 6], 'p': [2], 'g': [2], 'i': [0], 't': [2], 'cj': [2],
        'N': [2, 4], 'A': [2, 4], 'D': [2, 4]}
for k in ['num', 'm', 'c', 'f', 'b', 's', 'v', 'l', 'r', 'n']:
    RULE[k] = [2, 4, 6]
famMax = {'t': 2, 'p': 2, 'g': 2, 'cj': 2, 'chiral': 2, 'sv': 2, 'fb': 2, 'leap': 2}
M = 12
target = [1.08 - j * (1.08 - 0.22) / (M - 1) for j in range(M)]
P = len(pool)
# biến: x_i (P), z_ij (P*M), y_ko
feats = list(RULE)
yv = []
for k in feats:
    for o in RULE[k]:
        yv.append((k, o))
nx, nz, ny = P, P * M, len(yv)
N = nx + nz + ny
xi = lambda i: i
zi = lambda i, j: nx + i * M + j
yi = lambda t: nx + nz + t
rows, lb, ub = [], [], []
A = lil_matrix((20000, N))
r = 0
def add(coefs, lo, hi):
    global r
    for c, v in coefs:
        A[r, c] = v
    lb.append(lo); ub.append(hi); r += 1
add([(xi(i), 1) for i in range(P)], M, M)
for t_idx, k in enumerate(feats):
    pass
for k in feats:
    base = 1 if k in ROYAL else 0
    ts = [t for t, (kk, o) in enumerate(yv) if kk == k]
    coefs = [(xi(i), 1) for i in range(P) if k in pool[i]['feat']] + [(yi(t), -yv[t][1]) for t in ts]
    add(coefs, -base, -base)  # sum x - sum o*y = -base  => count+base = chosen o
    add([(yi(t), 1) for t in ts], 1, 1)
for f, mx in famMax.items():
    add([(xi(i), 1) for i in range(P) if pool[i]['fam'] == f], 0, mx)
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
        add([(xi(i), 1) for i in idx], 0, 1)
for i in range(P):
    add([(zi(i, j), 1) for j in range(M)] + [(xi(i), -1)], 0, 0)
for j in range(M):
    add([(zi(i, j), 1) for i in range(P)], 1, 1)
A = A[:r].tocsr()
c = np.zeros(N)
for i in range(P):
    c[xi(i)] = 0.01 * len(pool[i]['p']) / 200 + (0.004 if len(re.sub('n', '', pool[i]['add'])) >= 3 else 0)
    for j in range(M):
        c[zi(i, j)] = (pool[i]['avg'] - target[j]) ** 2
res = milp(c, constraints=LinearConstraint(A, lb, ub), integrality=np.ones(N), bounds=Bounds(0, 1), options={'time_limit': 600, 'disp': False})
print(res.status, res.message, 'obj', res.fun)
if res.x is not None:
    sel = [i for i in range(P) if res.x[xi(i)] > 0.5]
    for i in sorted(sel, key=lambda i: -pool[i]['avg']):
        x = pool[i]
        print(f"  {x['p']:<24} {' '.join(f'{v:.2f}' for v in x['r'])} avg {x['avg']:.2f} {x['fam']} {','.join(x['feat'])}")
