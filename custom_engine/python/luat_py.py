"""Ban dich Python cua bo luat doc lap src/tests/test_rules_oracle.cc (chi phan sinh nuoc gia-hop-le + tan cong).
Ban co: 10x10, o = r*10 + f (r 0..9 la hang 1..10, f 0..9 la cot a..j), quan trang = +loai, den = -loai."""
E_, P_, N_, R_, Q_, K_, B_, M_, V_, Y_, S_, C_, G_ = range(13)
CH = ".pnrqkbmvyscg"
W, BL = 0, 1

# N of the N-checks rule: the "N+N" field of every FEN to_fen() writes, hence of every self-play and arena start
# position (the engine reads N from the FEN). 8 since 2026-11-22 (7 from 2026-11-16 to 2026-11-21, 8 before that).
N_CHECKS = 8

KNIGHT = [(1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2)]
CAMEL = [(1, 3), (3, 1), (3, -1), (1, -3), (-1, -3), (-3, -1), (-3, 1), (-1, 3)]
KSTEP = [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]
ALFIL = [(2, 2), (2, -2), (-2, -2), (-2, 2)]
DABBABA = [(0, 2), (2, 0), (0, -2), (-2, 0)]
ORTH = [(0, 1), (1, 0), (0, -1), (-1, 0)]
DIAG = [(1, 1), (1, -1), (-1, -1), (-1, 1)]


def sgn(v):
    return (v > 0) - (v < 0)


def on_board(f, r):
    return 0 <= f < 10 and 0 <= r < 10


def col(pc):
    return W if pc > 0 else BL


def typ(pc):
    return pc if pc > 0 else -pc


def piece_attacks(b, p, s):
    pc = b[p]
    if not pc or p == s:
        return False
    t = typ(pc)
    pf, pr = p % 10, p // 10
    sf, sr = s % 10, s // 10
    df, dr = sf - pf, sr - pr
    adf, adr = abs(df), abs(dr)
    fwd = 1 if col(pc) == W else -1
    kstep = max(adf, adr) == 1
    knight = (adf == 1 and adr == 2) or (adf == 2 and adr == 1)

    def empty_at(f, r):
        return on_board(f, r) and not b[r * 10 + f]

    horse_ok = knight and empty_at(pf + (sgn(df) if adf == 2 else 0), pr + (sgn(dr) if adr == 2 else 0))
    orth = (df == 0) != (dr == 0)
    diag = adf == adr and adf != 0

    def between():
        a, bb = sgn(df), sgn(dr)
        n = 0
        last = False
        f, r = pf + a, pr + bb
        while f != sf or r != sr:
            occ = b[r * 10 + f] != 0
            if occ:
                n += 1
            last = occ and f + a == sf and r + bb == sr
            f += a
            r += bb
        return n, last

    if t == P_:
        return dr == fwd and adf == 1
    if t == S_:
        return dr == fwd and adf <= 1
    if t == N_:
        return knight
    if t == K_:
        return kstep
    if t in (R_, Q_, B_):
        line = (t in (R_, Q_) and orth) or (t in (B_, Q_) and diag)
        if not line:
            return False
        n, _ = between()
        return n == 0
    if t == M_:
        return kstep or horse_ok
    if t == V_:
        return knight or (adf == 1 and adr == 3) or (adf == 3 and adr == 1)
    if t == Y_:
        return (adf == 2 and adr == 2) or (adf == 2 and adr == 0) or (adf == 0 and adr == 2)
    if t == C_:
        if adf + adr == 1:
            return True
        if not orth:
            return False
        n, _ = between()
        return n == 1
    if t == G_:
        if kstep:
            return True
        if not (orth or diag):
            return False
        n, last = between()
        return n == 1 and last
    return False


def attacked(b, s, c):
    for p in range(100):
        if b[p] and col(b[p]) == c and piece_attacks(b, p, s):
            return True
    return False


def find_king(b, c):
    k = K_ if c == W else -K_
    for s in range(100):
        if b[s] == k:
            return s
    return -1


def gen_pseudo(b, us, ep_mid=-1):
    """Nuoc gia-hop-le (khong phong cap: cac nuoc toi hang 8+ duoc ghi la den-o, kem co promo=False)."""
    them = us ^ 1
    fwd = 1 if us == W else -1
    out = []  # (from, to)

    def dbl_region(r):
        return r <= 2 if us == W else r >= 7

    def empty(f, r):
        return on_board(f, r) and not b[r * 10 + f]

    def enemy(f, r):
        return on_board(f, r) and b[r * 10 + f] != 0 and col(b[r * 10 + f]) == them

    for s in range(100):
        pc = b[s]
        if not pc or col(pc) != us:
            continue
        t = typ(pc)
        f, r = s % 10, s // 10
        if t == P_:
            if on_board(f, r + fwd) and not b[(r + fwd) * 10 + f]:
                out.append((s, (r + fwd) * 10 + f))
                if dbl_region(r) and on_board(f, r + 2 * fwd) and not b[(r + 2 * fwd) * 10 + f]:
                    out.append((s, (r + 2 * fwd) * 10 + f))
            for df in (-1, 1):
                if not on_board(f + df, r + fwd):
                    continue
                to = (r + fwd) * 10 + f + df
                if to == ep_mid or (b[to] and col(b[to]) == them):
                    out.append((s, to))
            continue
        if t == S_:
            for df in (-1, 0, 1):
                if not on_board(f + df, r + fwd):
                    continue
                to = (r + fwd) * 10 + f + df
                if to == ep_mid or not b[to] or col(b[to]) == them:
                    out.append((s, to))
            if dbl_region(r):
                for df in (0, -2, 2):
                    tf, tr = f + df, r + 2 * fwd
                    if not on_board(tf, tr):
                        continue
                    if b[(r + fwd) * 10 + f + df // 2] or b[tr * 10 + tf]:
                        continue
                    out.append((s, tr * 10 + tf))
            continue
        dest = set()

        def move_capture(ff, rr):
            if empty(ff, rr) or enemy(ff, rr):
                dest.add(rr * 10 + ff)

        def move_only(ff, rr):
            if empty(ff, rr):
                dest.add(rr * 10 + ff)

        def horse(capture):
            for d in KNIGHT:
                if empty(f + (sgn(d[0]) if abs(d[0]) == 2 else 0), r + (sgn(d[1]) if abs(d[1]) == 2 else 0)):
                    (move_capture if capture else move_only)(f + d[0], r + d[1])

        def slide(dirs):
            for d in dirs:
                k = 1
                while True:
                    ff, rr = f + d[0] * k, r + d[1] * k
                    if not on_board(ff, rr):
                        break
                    if b[rr * 10 + ff]:
                        if enemy(ff, rr):
                            dest.add(rr * 10 + ff)
                        break
                    dest.add(rr * 10 + ff)
                    k += 1

        def wazir(capture):
            for d in ORTH:
                (move_capture if capture else move_only)(f + d[0], r + d[1])

        if t == N_:
            for d in KNIGHT:
                move_capture(f + d[0], r + d[1])
        elif t == R_:
            slide(ORTH)
        elif t == Q_:
            slide(ORTH)
            slide(DIAG)
        elif t == K_:
            for d in KSTEP:
                move_capture(f + d[0], r + d[1])
            for d in DABBABA:
                if empty(f + d[0] // 2, r + d[1] // 2):
                    move_only(f + d[0], r + d[1])
            for d in ALFIL:
                if empty(f + (1 if d[0] > 0 else -1), r + (1 if d[1] > 0 else -1)):
                    move_only(f + d[0], r + d[1])
            horse(False)
        elif t == B_:
            slide(DIAG)
            wazir(False)
        elif t == M_:
            for d in KSTEP:
                move_capture(f + d[0], r + d[1])
            horse(True)
        elif t == V_:
            for d in KNIGHT:
                move_capture(f + d[0], r + d[1])
            for d in CAMEL:
                move_capture(f + d[0], r + d[1])
        elif t == Y_:
            for d in ALFIL:
                move_capture(f + d[0], r + d[1])
            for d in DABBABA:
                move_capture(f + d[0], r + d[1])
            wazir(False)
        elif t == C_:
            for d in ORTH:
                k = 1
                while True:   # nuoc im toi quan dau tien (ngoi)
                    ff, rr = f + d[0] * k, r + d[1] * k
                    if not on_board(ff, rr) or b[rr * 10 + ff]:
                        break
                    dest.add(rr * 10 + ff)
                    k += 1
                k += 1
                while True:   # sau ngoi: quan dau tien, neu la dich thi an
                    ff, rr = f + d[0] * k, r + d[1] * k
                    if not on_board(ff, rr):
                        break
                    if b[rr * 10 + ff]:
                        if enemy(ff, rr):
                            dest.add(rr * 10 + ff)
                        break
                    k += 1
            wazir(True)
        elif t == G_:
            for d in KSTEP:
                move_capture(f + d[0], r + d[1])
            for d in KSTEP:
                k = 1
                while empty(f + d[0] * k, r + d[1] * k):
                    k += 1
                if not on_board(f + d[0] * k, r + d[1] * k):
                    continue
                move_capture(f + d[0] * (k + 1), r + d[1] * (k + 1))
        for to in dest:
            out.append((s, to))
    return out


def apply(b, mv):
    nb = list(b)
    nb[mv[1]] = nb[mv[0]]
    nb[mv[0]] = 0
    return nb


def gen_legal(b, us, ep_mid=-1):
    ks = find_king(b, us)
    res = []
    for mv in gen_pseudo(b, us, ep_mid):
        nb = apply(b, mv)
        k = mv[1] if mv[0] == ks else ks
        if k >= 0 and attacked(nb, k, us ^ 1):
            continue
        res.append(mv)
    return res


def sqname(s):
    return chr(97 + s % 10) + str(s // 10 + 1)


def mvname(mv):
    return sqname(mv[0]) + sqname(mv[1])


def to_fen(b, stm="w"):
    rows = []
    for r in range(9, -1, -1):
        row = ""
        e = 0
        for f in range(10):
            pc = b[r * 10 + f]
            if not pc:
                e += 1
                continue
            if e:
                row += str(e)
                e = 0
            ch = CH[typ(pc)]
            row += ch.upper() if pc > 0 else ch
        if e:
            row += str(e)
        rows.append(row)
    return "/".join(rows) + f" {stm} - - {N_CHECKS}+{N_CHECKS} 0 1"


def from_fen(fen):
    b = [0] * 100
    rows = fen.split()[0].split("/")
    for i, row in enumerate(rows):
        r = 9 - i
        f = 0
        j = 0
        while j < len(row):
            ch = row[j]
            if ch.isdigit():
                n = int(ch)
                if j + 1 < len(row) and row[j + 1].isdigit():
                    n = int(row[j:j + 2])
                    j += 1
                f += n
            else:
                t = CH.index(ch.lower())
                b[r * 10 + f] = t if ch.isupper() else -t
                f += 1
            j += 1
    return b
