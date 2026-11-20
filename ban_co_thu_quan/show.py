import sys
sys.path.insert(0, '.')
from pieces_rules import PIECES, Pos, all_moves, name
from examples import EXAMPLES, sq, L
keys = sys.argv[1:] or list(PIECES)
for k in keys:
    print('=====', k, PIECES[k]['betza'])
    for i, (desc, Z, T, D) in enumerate(EXAMPLES[k], 1):
        pos = Pos(sq(Z), L(T), L(D))
        rules, normal, cj = all_moves(k, pos)
        print(f' Ex{i}: {desc} | Z={Z} T=[{T}] D=[{D}]  -> {len(normal)+len(cj)} nước')
        for rn, (mv, notes) in rules:
            print('   ', rn, ':', ' '.join(name(b) + ('(xóa ' + name(h) + ')' if h else '') for b, kk, h in mv))
            for n in notes: print('       -', n)
        multi = [name(b) for b, r in normal.items() if len(r) > 1]
        if multi: print('    nhiều quy tắc cùng chọn:', multi)
