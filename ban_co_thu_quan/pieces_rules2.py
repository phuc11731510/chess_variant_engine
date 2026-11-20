# -*- coding: utf-8 -*-
"""Bộ quân mới (quân hoàng gia WFmnDmnAmnN + 12 quân). Cài đặt độc lập theo từng câu quy tắc."""
from pieces_rules import (Pos, name, inside, add, N, ORTH, DIAG, KNIGHT, CAMEL, ZEBRA, SGN, leap, slide, cannon,
                          bend, leap_from, knight_block, first_piece)

PIECES = {}
MID = 'mid'      # H là trung điểm của A và B
NEAR = 'near'    # H là ô kề B trên đoạn thẳng từ A tới B


def piece(key, betza, label, cj=None):
    def deco(f):
        PIECES[key] = dict(betza=betza, label=label, rules=f, cj=cj)
        return f
    return deco


D_V = [(2, 0), (-2, 0), (0, 2), (0, -2)]
A_V = [(2, 2), (-2, 2), (2, -2), (-2, -2)]
H_V = [(3, 0), (-3, 0), (0, 3), (0, -3)]
G_V = [(3, 3), (-3, 3), (3, -3), (-3, -3)]
mid_block = lambda v: [(v[0] // 2, v[1] // 2)]


def grass(pos, dirs, limit=99):
    A = pos.Z
    moves, notes = [], []
    for d in dirs:
        cur, hurdle, k = A, None, 0
        while k < limit:
            k += 1
            cur = add(cur, d)
            if not inside(cur):
                break
            if pos.occ(cur):
                hurdle = cur
                break
        if not hurdle:
            continue
        B = add(hurdle, d)
        if inside(B) and pos.occ(B) != 'T':
            moves.append((B, 'n', None))
    return moves, notes


def cj_slide(pos, dirs, bmax=1):
    A = pos.Z
    moves = []
    for d in dirs:
        cur = A
        while True:
            cur = add(cur, d)
            if not inside(cur) or pos.occ(cur):
                break
        if not inside(cur) or pos.occ(cur) != 'D':
            continue
        H = cur
        for b in range(1, bmax + 1):
            B = add(H, d, b)
            if not inside(B) or pos.occ(B):
                break
            moves.append((B, 'cj', H))
    return moves, []


def cj_mao(pos):
    A = pos.Z
    moves = []
    for v in KNIGHT:
        H = add(A, v)
        if not inside(H) or pos.occ(H) != 'D':
            continue
        if any(pos.occ(add(A, w)) for w in knight_block(v)):
            continue
        B = add(H, v)
        if not inside(B) or pos.occ(B):
            continue
        if any(pos.occ(add(H, w)) for w in knight_block(v)):
            continue
        moves.append((B, 'cj', H))
    return moves, []


@piece('R', 'WFmnDmnAmnN', 'Quân hoàng gia')
def r_R(p):
    return [('W, F', leap(p, ORTH + DIAG)), ('mnD', leap(p, D_V, mid_block, mode='m')),
            ('mnA', leap(p, A_V, mid_block, mode='m')), ('mnN', leap(p, KNIGHT, knight_block, mode='m'))]


@piece('Q1', 'F2t[WFF]', 'Quân 1')
def r_Q1(p):
    def second(u, P):
        return slide(p, [d for d in DIAG if u[0] * d[0] + u[1] * d[1] > 0], start=P)
    return [('F2', slide(p, DIAG, limit=2)), ('t[WFF]', bend(p, ORTH, second))]


@piece('Q2', 'sWFFmWWcpWW', 'Quân 2')
def r_Q2(p):
    return [('sW', leap(p, [(1, 0), (-1, 0)])), ('FF', slide(p, DIAG)), ('mWW', slide(p, ORTH, mode='m')),
            ('cpWW', cannon(p, ORTH))]


@piece('Q3', 'CHmFF[cj1]FF', 'Quân 3', cj=NEAR)
def r_Q3(p):
    return [('C', leap(p, CAMEL)), ('H', leap(p, H_V)), ('mFF', slide(p, DIAG, mode='m')), ('[cj1]FF', cj_slide(p, DIAG, 1))]


@piece('Q4', 'DHmFFcpFF', 'Quân 4')
def r_Q4(p):
    return [('D', leap(p, D_V)), ('H', leap(p, H_V)), ('mFF', slide(p, DIAG, mode='m')), ('cpFF', cannon(p, DIAG))]


@piece('Q5', 'NGfrClfCblCrbC', 'Quân 5')
def r_Q5(p):
    return [('N', leap(p, KNIGHT)), ('G', leap(p, G_V)), ('C chong chóng', leap(p, [(3, 1), (-1, 3), (-3, -1), (1, -3)]))]


@piece('Q6', 'FZgF3', 'Quân 6')
def r_Q6(p):
    return [('F', leap(p, DIAG)), ('Z', leap(p, ZEBRA)), ('gF3', grass(p, DIAG, 3))]


@piece('Q7', 'WGgWW', 'Quân 7')
def r_Q7(p):
    return [('W', leap(p, ORTH)), ('G', leap(p, G_V)), ('gWW', grass(p, ORTH))]


@piece('Q8', 'vDt[WA]', 'Quân 8')
def r_Q8(p):
    def second(u, P):
        return leap_from(p, P, [d for d in A_V if u[0] * d[0] + u[1] * d[1] > 0])
    return [('vD', leap(p, [(0, 2), (0, -2)])), ('t[WA]', bend(p, ORTH, second))]


@piece('Q9', 'ZnD', 'Quân 9')
def r_Q9(p):
    return [('Z', leap(p, ZEBRA)), ('nD', leap(p, D_V, mid_block))]


@piece('Q10', 'sWWvW', 'Quân 10')
def r_Q10(p):
    return [('sWW', slide(p, [(1, 0), (-1, 0)])), ('vW', leap(p, [(0, 1), (0, -1)]))]


@piece('Q11', 'nNfrNlfNblNrbN', 'Quân 11')
def r_Q11(p):
    return [('nN', leap(p, KNIGHT, knight_block)), ('N chong chóng', leap(p, [(2, 1), (-1, 2), (-2, -1), (1, -2)]))]


@piece('Q12', 'nN[cj]nN', 'Quân 12', cj=MID)
def r_Q12(p):
    return [('nN', leap(p, KNIGHT, knight_block)), ('[cj]nN', cj_mao(p))]


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
