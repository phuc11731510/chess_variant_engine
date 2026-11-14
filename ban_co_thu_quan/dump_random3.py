import json, random, sys
sys.path.insert(0, '.')
from pieces_rules3 import PIECES, Pos, all_moves
random.seed(3)
out = []
for key in PIECES:
    for t in range(3000):
        dens = random.choice([0.05, 0.15, 0.3, 0.45, 0.6])
        sq = [(x, y) for x in range(1, 11) for y in range(1, 11)]
        random.shuffle(sq)
        k = int(dens * 100)
        Z = sq[0]; rest = sq[1:k]
        T = rest[:len(rest)//2]; D = rest[len(rest)//2:]
        pos = Pos(Z, T, D)
        _, normal, cj = all_moves(key, pos)
        out.append(dict(key=key, betza=PIECES[key]['betza'], Z=Z, T=T, D=D,
                        normal=sorted(normal), cj=sorted([[B[0], B[1], v[0][1][0], v[0][1][1]] for B, v in cj.items()])))
json.dump(out, open('rand_cases.json', 'w'))
print(len(out))
