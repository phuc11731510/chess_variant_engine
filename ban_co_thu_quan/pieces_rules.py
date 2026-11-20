# -*- coding: utf-8 -*-
"""Cài đặt độc lập (bám sát từng câu quy tắc) cho 13 quân, bàn 10x10.
Tọa độ (x, y), x = 1..10 (cột a..j), y = 1..10; y tăng theo hướng tiến của quân Z.
Mỗi quy tắc trả về danh sách nước đi (B, loại, H) và các ghi chú lý do loại."""

N = 10
FILES = 'abcdefghij'


def name(sq):
    return f"{FILES[sq[0]-1]}{sq[1]}"


def inside(sq):
    return 1 <= sq[0] <= N and 1 <= sq[1] <= N


def add(a, v, k=1):
    return (a[0] + k * v[0], a[1] + k * v[1])


class Pos:
    def __init__(self, Z, T=(), D=()):
        self.Z = Z
        self.T = set(T)
        self.D = set(D)
        assert Z not in self.T and Z not in self.D and not (self.T & self.D)

    def occ(self, sq):
        if sq in self.T:
            return 'T'
        if sq in self.D:
            return 'D'
        if sq == self.Z:
            return 'Z'
        return None


SGN = lambda t: (t > 0) - (t < 0)
ORTH = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIAG = [(1, 1), (-1, 1), (1, -1), (-1, -1)]
KNIGHT = [(1, 2), (-1, 2), (1, -2), (-1, -2), (2, 1), (-2, 1), (2, -1), (-2, -1)]
CAMEL = [(1, 3), (-1, 3), (1, -3), (-1, -3), (3, 1), (-3, 1), (3, -1), (-3, -1)]
ZEBRA = [(2, 3), (-2, 3), (2, -3), (-2, -3), (3, 2), (-3, 2), (3, -2), (-3, -2)]


def vec(v):
    return f"$({v[0]},{v[1]})$"


# ---------------- các loại quy tắc ----------------
def leap(pos, vecs, block=None, mode='mc'):
    """Nhảy: B = A + v. block(v) -> danh sách vector (so với A) của các ô phải trống."""
    A = pos.Z
    moves, notes = [], []
    for v in vecs:
        B = add(A, v)
        if not inside(B):
            continue
        o = pos.occ(B)
        if o == 'T':
            notes.append(f"{name(B)} (vector {vec(v)}) bị loại vì có quân cùng phe T")
            continue
        if block:
            bad = [add(A, w) for w in block(v) if pos.occ(add(A, w))]
            if bad:
                notes.append(f"{name(B)} (vector {vec(v)}) bị loại vì ô cản {', '.join(name(s) for s in bad)} có quân")
                continue
        if mode == 'm' and o == 'D':
            notes.append(f"{name(B)} (vector {vec(v)}) bị loại vì quy tắc này chỉ cho ô B trống mà {name(B)} có quân D")
            continue
        moves.append((B, 'n', None))
    return moves, notes


def slide(pos, dirs, limit=99, mode='mc', start=None):
    A = start or pos.Z
    moves, notes = [], []
    for d in dirs:
        k = 0
        cur = A
        while k < limit:
            k += 1
            cur = add(cur, d)
            if not inside(cur):
                break
            o = pos.occ(cur)
            if o == 'T':
                notes.append(f"theo vector {vec(d)}: dãy dừng trước {name(cur)} vì có quân cùng phe T")
                break
            if o == 'D':
                if mode == 'm':
                    notes.append(f"theo vector {vec(d)}: {name(cur)} có quân D nên không được chọn (quy tắc này chỉ cho ô trống) và dãy dừng ở đó")
                else:
                    moves.append((cur, 'n', None))
                    notes.append(f"theo vector {vec(d)}: {name(cur)} có quân D, được chọn và dãy dừng sau ô đó")
                break
            moves.append((cur, 'n', None))
    return moves, notes


def cannon(pos, dirs, limit=99):
    """Phần bắt kiểu nhảy qua đúng một quân (quân bị nhảy qua không bị xóa)."""
    A = pos.Z
    moves, notes = [], []
    for d in dirs:
        cur, k, hurdle = A, 0, None
        while k < limit:
            k += 1
            cur = add(cur, d)
            if not inside(cur):
                break
            if pos.occ(cur):
                hurdle = cur
                break
        if not hurdle:
            far = first_piece(pos, A, d)
            if far and limit < 99:
                notes.append(f"theo vector {vec(d)}: quân đầu tiên là {name(far[0])}, cách ô A {far[1]} bước, vượt quá {limit} bước nên không dùng làm quân bị nhảy qua được")
            continue
        cur, k, done = hurdle, 0, False
        while k < limit:
            k += 1
            cur = add(cur, d)
            if not inside(cur):
                done = True
                break
            o = pos.occ(cur)
            if o == 'D':
                moves.append((cur, 'n', None))
                notes.append(f"theo vector {vec(d)}: nhảy qua {name(hurdle)}, chọn {name(cur)} (quân D)")
                done = True
                break
            if o == 'T':
                notes.append(f"theo vector {vec(d)}: nhảy qua {name(hurdle)}, quân đầu tiên sau đó là T ở {name(cur)} nên không có nước bắt")
                done = True
                break
        if not done and limit < 99:
            far = first_piece(pos, hurdle, d)
            if far:
                notes.append(f"theo vector {vec(d)}: nhảy qua {name(hurdle)}, quân tiếp theo là {name(far[0])}, cách {name(hurdle)} {far[1]} bước, vượt quá {limit} bước nên không bắt được")
    return moves, notes


def first_piece(pos, start, d):
    cur, k = start, 0
    while True:
        k += 1
        cur = add(cur, d)
        if not inside(cur):
            return None
        if pos.occ(cur):
            return cur, k


def grass(pos, dirs):
    A = pos.Z
    moves, notes = [], []
    for d in dirs:
        cur, hurdle = A, None
        while True:
            cur = add(cur, d)
            if not inside(cur):
                break
            if pos.occ(cur):
                hurdle = cur
                break
        if not hurdle:
            continue
        B = add(hurdle, d)
        if not inside(B):
            notes.append(f"theo vector {vec(d)}: quân đầu tiên ở {name(hurdle)} nhưng ô ngay sau nó nằm ngoài bàn cờ")
            continue
        if pos.occ(B) == 'T':
            notes.append(f"theo vector {vec(d)}: quân đầu tiên ở {name(hurdle)}, ô ngay sau {name(B)} có quân T")
            continue
        moves.append((B, 'n', None))
        notes.append(f"theo vector {vec(d)}: quân đầu tiên ở {name(hurdle)}, chọn ô ngay sau là {name(B)}")
    return moves, notes


def checker(pos, vecs):
    A = pos.Z
    moves, notes = [], []
    for v in vecs:
        H = add(A, v)
        B = add(A, v, 2)
        if not inside(H) or pos.occ(H) != 'D':
            continue
        if not inside(B):
            notes.append(f"{name(H)} có quân D nhưng ô B tương ứng nằm ngoài bàn cờ")
            continue
        if pos.occ(B):
            notes.append(f"{name(H)} có quân D nhưng ô {name(B)} không trống nên không có nước bắt nhảy")
            continue
        moves.append((B, 'cj', H))
        notes.append(f"{name(H)} có quân D và {name(B)} trống: chọn {name(B)}, xóa quân ở {name(H)}")
    return moves, notes


def bend(pos, first_vecs, second):
    """t[...]: chặng 1 một bước u; nếu ô P trống thì chặng 2 theo second(u, P)."""
    A = pos.Z
    moves, notes = [], []
    for u in first_vecs:
        P = add(A, u)
        if not inside(P):
            continue
        o = pos.occ(P)
        if o == 'T':
            notes.append(f"chặng đầu {vec(u)}: {name(P)} có quân T nên không chọn được {name(P)} và không có chặng hai qua {name(P)}")
            continue
        moves.append((P, 'n', None))
        if o == 'D':
            notes.append(f"chặng đầu {vec(u)}: {name(P)} có quân D, được chọn nhưng không có chặng hai qua {name(P)}")
            continue
        m2, n2 = second(u, P)
        moves += m2
        notes += [f"từ {name(P)}: " + s for s in n2]
    return moves, notes


def leap_from(pos, P, vecs):
    moves, notes = [], []
    for v in vecs:
        B = add(P, v)
        if not inside(B):
            continue
        if pos.occ(B) == 'T':
            notes.append(f"{name(B)} có quân T")
            continue
        moves.append((B, 'n', None))
    return moves, notes


# ô cản của n (đường đi trong dải, ưu tiên nước thẳng) cho Mã và Lạc đà
def knight_block(v):
    a, b = v
    return [(SGN(a), 0)] if abs(a) == 2 else [(0, SGN(b))]


def camel_block(v):
    a, b = v
    if abs(a) == 3:
        return [(SGN(a), 0), (2 * SGN(a), SGN(b))]
    return [(0, SGN(b)), (SGN(a), 2 * SGN(b))]


def tripper_block(v):
    return [(SGN(v[0]), SGN(v[1])), (2 * SGN(v[0]), 2 * SGN(v[1]))]


# ---------------- 13 quân ----------------
PIECES = {}


def piece(key, betza, label):
    def deco(f):
        PIECES[key] = dict(betza=betza, label=label, rules=f)
        return f
    return deco


@piece('K', 'nGsWWvW', 'Quân hoàng gia')
def rules_K(p):
    return [
        ('Quy tắc 1 (trượt theo $(\\pm1,0)$)', slide(p, [(1, 0), (-1, 0)])),
        ('Quy tắc 2 (bước $(0,\\pm1)$)', leap(p, [(0, 1), (0, -1)])),
        ('Quy tắc 3 (nhảy $(\\pm3,\\pm3)$, cần hai ô chéo giữa trống)', leap(p, [(3, 3), (-3, 3), (3, -3), (-3, -3)], tripper_block)),
    ]


@piece('P1', 'Wt[FWW]', 'Quân 1')
def rules_P1(p):
    def second(u, P):
        return slide(p, [(u[0], 0), (0, u[1])], start=P)
    return [
        ('Quy tắc 1 (bước $(\\pm1,0),(0,\\pm1)$)', leap(p, ORTH)),
        ('Quy tắc 2 (bước chéo rồi trượt thẳng ra xa)', bend(p, DIAG, second)),
    ]


@piece('P2', 'FFmWWcpWW', 'Quân 2')
def rules_P2(p):
    return [
        ('Quy tắc 1 (trượt chéo)', slide(p, DIAG)),
        ('Quy tắc 2 (trượt thẳng, chỉ ô trống)', slide(p, ORTH, mode='m')),
        ('Quy tắc 3 (bắt thẳng bằng cách nhảy qua đúng một quân)', cannon(p, ORTH)),
    ]


@piece('P3', 'NGmF4cpF4', 'Quân 3')
def rules_P3(p):
    return [
        ('Quy tắc 1 (nhảy $(\\pm1,\\pm2),(\\pm2,\\pm1)$)', leap(p, KNIGHT)),
        ('Quy tắc 2 (nhảy $(\\pm3,\\pm3)$)', leap(p, [(3, 3), (-3, 3), (3, -3), (-3, -3)])),
        ('Quy tắc 3 (trượt chéo tối đa 4 ô, chỉ ô trống)', slide(p, DIAG, limit=4, mode='m')),
        ('Quy tắc 4 (bắt chéo nhảy qua một quân, mỗi đoạn tối đa 4 ô)', cannon(p, DIAG, limit=4)),
    ]


@piece('P4', 'nNZfrClfCblCrbC', 'Quân 4')
def rules_P4(p):
    return [
        ('Quy tắc 1 (nhảy kiểu Mã có ô cản)', leap(p, KNIGHT, knight_block)),
        ('Quy tắc 2 (nhảy $(\\pm2,\\pm3),(\\pm3,\\pm2)$)', leap(p, ZEBRA)),
        ('Quy tắc 3 (nhảy $(3,1),(-1,3),(-3,-1),(1,-3)$)', leap(p, [(3, 1), (-1, 3), (-3, -1), (1, -3)])),
    ]


@piece('P5', 'WAvWWsD', 'Quân 5')
def rules_P5(p):
    return [
        ('Quy tắc 1 (bước $(\\pm1,0),(0,\\pm1)$)', leap(p, ORTH)),
        ('Quy tắc 2 (nhảy $(\\pm2,\\pm2)$)', leap(p, [(2, 2), (-2, 2), (2, -2), (-2, -2)])),
        ('Quy tắc 3 (trượt theo $(0,\\pm1)$)', slide(p, [(0, 1), (0, -1)])),
        ('Quy tắc 4 (nhảy $(\\pm2,0)$)', leap(p, [(2, 0), (-2, 0)])),
    ]


@piece('P6', 'Ht[FD]', 'Quân 6')
def rules_P6(p):
    def second(u, P):
        return leap_from(p, P, [(2 * u[0], 0), (0, 2 * u[1])])
    return [
        ('Quy tắc 1 (nhảy $(\\pm3,0),(0,\\pm3)$)', leap(p, [(3, 0), (-3, 0), (0, 3), (0, -3)])),
        ('Quy tắc 2 (bước chéo rồi nhảy 2 ô thẳng ra xa)', bend(p, DIAG, second)),
    ]


@piece('P7', 'NmF[cj]F', 'Quân 7')
def rules_P7(p):
    return [
        ('Quy tắc 1 (nhảy kiểu Mã)', leap(p, KNIGHT)),
        ('Quy tắc 2 (bước chéo, chỉ ô trống)', leap(p, DIAG, mode='m')),
        ('Quy tắc 3 (bắt nhảy chéo)', checker(p, DIAG)),
    ]


@piece('P8', 'W2gWW', 'Quân 8')
def rules_P8(p):
    return [
        ('Quy tắc 1 (trượt thẳng tối đa 2 ô)', slide(p, ORTH, limit=2)),
        ('Quy tắc 2 (nhảy qua quân đầu tiên trên hàng/cột, đáp ngay sau)', grass(p, ORTH)),
    ]


@piece('P9', 'nNA', 'Quân 9')
def rules_P9(p):
    return [
        ('Quy tắc 1 (nhảy kiểu Mã có ô cản)', leap(p, KNIGHT, knight_block)),
        ('Quy tắc 2 (nhảy $(\\pm2,\\pm2)$)', leap(p, [(2, 2), (-2, 2), (2, -2), (-2, -2)])),
    ]


@piece('P10', 'HgFF', 'Quân 10')
def rules_P10(p):
    return [
        ('Quy tắc 1 (nhảy $(\\pm3,0),(0,\\pm3)$)', leap(p, [(3, 0), (-3, 0), (0, 3), (0, -3)])),
        ('Quy tắc 2 (nhảy qua quân đầu tiên trên đường chéo, đáp ngay sau)', grass(p, DIAG)),
    ]


@piece('P11', 'nCfrZlfZblZrbZ', 'Quân 11')
def rules_P11(p):
    return [
        ('Quy tắc 1 (nhảy $(\\pm1,\\pm3),(\\pm3,\\pm1)$ có hai ô cản)', leap(p, CAMEL, camel_block)),
        ('Quy tắc 2 (nhảy $(3,2),(-2,3),(-3,-2),(2,-3)$)', leap(p, [(3, 2), (-2, 3), (-3, -2), (2, -3)])),
    ]


@piece('P12', 'mW[cj]W', 'Quân 12')
def rules_P12(p):
    return [
        ('Quy tắc 1 (bước thẳng, chỉ ô trống)', leap(p, ORTH, mode='m')),
        ('Quy tắc 2 (bắt nhảy thẳng)', checker(p, ORTH)),
    ]


def all_moves(key, pos):
    rules = PIECES[key]['rules'](pos)
    normal, cj = {}, {}
    for rname, (moves, notes) in rules:
        for B, kind, H in moves:
            if kind == 'n':
                normal.setdefault(B, []).append(rname)
            else:
                cj.setdefault(B, []).append((rname, H))
    return rules, normal, cj
