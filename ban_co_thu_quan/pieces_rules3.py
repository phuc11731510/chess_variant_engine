# -*- coding: utf-8 -*-
"""Bộ quân thứ ba (thiết kế cùng thế khởi đầu). Cài đặt độc lập theo từng câu quy tắc."""
from pieces_rules import Pos, name, inside, add, N, ORTH, DIAG, KNIGHT, ZEBRA, SGN, leap, slide, cannon, bend, leap_from, knight_block
import pieces_rules2 as R2
from pieces_rules2 import MID, NEAR, grass, D_V, A_V, H_V, G_V, mid_block

PIECES = {}


def piece(key, betza, label, cj=None):
    def deco(f):
        PIECES[key] = dict(betza=betza, label=label, rules=f, cj=cj)
        return f
    return deco


tripper_block = lambda v: [(SGN(v[0]), SGN(v[1])), (2 * SGN(v[0]), 2 * SGN(v[1]))]

PIECES['R'] = dict(R2.PIECES['R'])
PIECES['Q1'] = dict(R2.PIECES['Q1'])


@piece('Q2', 'vWFFmWWcpWW', 'Quân 2')
def r_Q2(p):
    return [('vW', leap(p, [(0, 1), (0, -1)])), ('FF', slide(p, DIAG)), ('mWW', slide(p, ORTH, mode='m')), ('cpWW', cannon(p, ORTH))]


PIECES['Q3'] = dict(R2.PIECES['Q3'])


@piece('Q4', 'NmF4cpF4', 'Quân 4')
def r_Q4(p):
    return [('N', leap(p, KNIGHT)), ('mF4', slide(p, DIAG, limit=4, mode='m')), ('cpF4', cannon(p, DIAG, limit=4))]


PIECES['Q5'] = dict(R2.PIECES['Q6'], label='Quân 5')


@piece('Q6', 'DHfrClfCblCrbC', 'Quân 6')
def r_Q6(p):
    return [('D', leap(p, D_V)), ('H', leap(p, H_V)), ('C chong chóng', leap(p, [(3, 1), (-1, 3), (-3, -1), (1, -3)]))]


@piece('Q7', 'WGgW3', 'Quân 7')
def r_Q7(p):
    return [('W', leap(p, ORTH)), ('G', leap(p, G_V)), ('gW3', grass(p, ORTH, 3))]


@piece('Q8', 'sDt[WnA]', 'Quân 8')
def r_Q8(p):
    def second(u, P):
        out = []
        for d in A_V:
            if u[0] * d[0] + u[1] * d[1] <= 0:
                continue
            Bq = add(P, d)
            if not inside(Bq) or p.occ(Bq) == 'T':
                continue
            if p.occ(add(P, (d[0] // 2, d[1] // 2))):
                continue
            out.append((Bq, 'n', None))
        return out, []
    return [('sD', leap(p, [(2, 0), (-2, 0)])), ('t[WnA]', bend(p, ORTH, second))]


PIECES['Q9'] = dict(R2.PIECES['Q9'])


@piece('Q10', 'nGsWWvW', 'Quân 10')
def r_Q10(p):
    return [('nG', leap(p, G_V, tripper_block)), ('sWW', slide(p, [(1, 0), (-1, 0)])), ('vW', leap(p, [(0, 1), (0, -1)]))]


PIECES['Q11'] = dict(R2.PIECES['Q11'])
PIECES['Q12'] = dict(R2.PIECES['Q12'])


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
