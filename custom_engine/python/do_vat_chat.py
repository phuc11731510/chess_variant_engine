"""Do mang hieu gia tri quan den dau: bo 1 quan cua ben di, xem dau gia tri (value head) doi bao nhieu.

Moi the co duoc dua cho engine UCI (--uci-nn) duoi dang `position fen <the cach 8 nua nuoc> moves <8 nuoc>`,
roi `go nodes 1` = chi danh gia goc bang mang, khong tim kiem; diem cua nuoc chua tham = gia tri mang cho
ben di (q = Thang - Thua, trong [-1,1]).

Vi sao phai co 8 nuoc lich su: mang nhan 8 ban co gan nhat. Dua the co bang FEN tron thi 6 ban lich su bi
trong -- kieu dau vao chi gap o nuoc dau van khi huan luyen (o the xuat phat mang tra ve gia tri xuat phat
bat ke quan nao bi bo). Bo quan o the cach 8 nua nuoc roi di lai 8 nuoc do -> ca 8 ban deu thieu quan do.

Chi bo quan cua BEN DI (bo quan doi phuong co the de vua doi phuong bi chieu khi khong toi luot = the sai luat),
khong dung toi Hoang gia. Neu 8 nuoc khong con hop le sau khi bo quan (vd. quan do da di/bi an/dang chan chieu)
thi bo qua lan do; kiem tra bang cach so ban co cuoi voi ban co goc tru dung quan do.

Vi du (WSL):  python3 do_vat_chat.py --engine /mnt/d/.../custom_engine.exe --model 'D:\\...\\gen79.onnx'
"""
import argparse
import math
import sys
from collections import defaultdict

TEN = {"p": "Tot", "s": "Sergeant", "n": "Ma", "b": "Tuong", "r": "Xe", "q": "Hau", "y": "Alibaba",
       "m": "Centaur", "h": "Archbishop", "e": "Chancellor", "v": "Wildebeest", "a": "Amazon"}
START = "vrhbqkberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHBQKBERV w BIbi - 8+8 0 1"
HIST = 8


class Uci:
    def __init__(self, exe, model, provider):
        import subprocess
        self.p = subprocess.Popen([exe, "--uci-nn"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True, bufsize=1)
        self.send("uci"); self.wait("uciok")
        self.send(f"setoption name WeightsFile value {model}")
        self.send(f"setoption name Provider value {provider}")
        self.send("isready"); self.wait("readyok")

    def send(self, s):
        self.p.stdin.write(s + "\n"); self.p.stdin.flush()

    def wait(self, prefix):
        lines = []
        while True:
            l = self.p.stdout.readline()
            if not l:
                raise RuntimeError("engine dong")
            l = l.strip(); lines.append(l)
            if l.startswith(prefix):
                return lines

    def setpos(self, fen, moves):
        self.send(f"position fen {fen}" + (" moves " + " ".join(moves) if moves else ""))

    def fen(self):
        self.send("fen")
        return self.wait("fen ")[-1][4:].strip()

    def value(self):
        """q (Thang-Thua) cua mang cho ben di o the hien tai, khong tim kiem."""
        self.send("go nodes 1")
        q = None
        for l in self.wait("bestmove"):
            t = l.split()
            if t[:1] == ["info"] and "multipv" in t and t[t.index("multipv") + 1] == "1" and "wdl" in t:
                i = t.index("wdl"); w, _, lo = (int(x) for x in t[i + 1:i + 4])
                q = (w - lo) / 1000.0
        return q

    def play_game(self, max_ply, nodes, cutoff):
        """Mang tu choi (Temperature 1.0 trong `cutoff` nua nuoc dau, 0 = ca van), tra ve danh sach nuoc."""
        self.send("setoption name Temperature value 1000")
        self.send(f"setoption name TempCutoffPly value {cutoff}")
        moves = []
        for _ in range(max_ply):
            self.setpos(START, moves); self.send(f"go nodes {nodes}")
            bm = self.wait("bestmove")[-1].split()[1]
            if bm == "0000":
                break
            moves.append(bm)
            self.setpos(START, moves); self.send("result")
            if self.wait("result ")[-1].split()[1] in ("white", "black", "draw"):
                moves.pop()   # khong lay the da het van
                break
        self.send("setoption name Temperature value 0")
        return moves

    def close(self):
        self.send("quit"); self.p.wait(timeout=10)


def parse(fen):
    f = fen.split()
    rows = []
    for row in f[0].split("/"):
        cells, k = [], 0
        while k < len(row):
            if row[k].isdigit():
                j = k
                while j < len(row) and row[j].isdigit():
                    j += 1
                cells += [None] * int(row[k:j]); k = j
            else:
                cells.append(row[k]); k += 1
        rows.append(cells)
    return rows, f


def build(rows, f):
    out = []
    for cells in rows:
        s, n = "", 0
        for c in cells:
            if c is None:
                n += 1
            else:
                s += (str(n) if n else "") + c; n = 0
        out.append(s + (str(n) if n else ""))
    g = list(f); g[0] = "/".join(out); g[2] = "-"; g[3] = "-"
    return " ".join(g)


def cp(q):
    q = max(-0.9999, min(0.9999, q))
    return 111.714640912 * math.tan(1.5620688421 * q)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--provider", default="dml")
    ap.add_argument("--games", type=int, default=8)
    ap.add_argument("--plies", default="20,36,52,70")
    ap.add_argument("--nodes", type=int, default=100)
    ap.add_argument("--temp-cutoff", type=int, default=0, help="nhiet do 1.0 chi trong N nua nuoc dau (0 = ca van)")
    ap.add_argument("--max-abs-q", type=float, default=1.0, help="chi do the co |q goc| <= nguong nay (the con can bang)")
    a = ap.parse_args()
    targets = [int(x) for x in a.plies.split(",")]

    u = Uci(a.engine, a.model, a.provider)
    snaps = []   # (fen cach HIST nua nuoc, HIST nuoc cuoi)
    for g in range(a.games):
        moves = u.play_game(max(targets), a.nodes, a.temp_cutoff)
        for t in targets:
            if t <= len(moves) and t >= HIST:
                u.setpos(START, moves[:t - HIST])
                snaps.append((u.fen(), moves[t - HIST:t]))
        print(f"  van {g + 1}: {len(moves)} nua nuoc", flush=True)
    print(f"So the co: {len(snaps)}", flush=True)

    dq = defaultdict(list); dcp = defaultdict(list); skipped = 0
    for idx, (fen0, last) in enumerate(snaps):
        rows0, f0 = parse(fen0)
        base0 = build(rows0, f0)
        u.setpos(base0, last); fin = u.fen()
        rowsF, fF = parse(fin)
        white = fF[1] == "w"
        q0 = u.value()
        if q0 is None or abs(q0) > a.max_abs_q:
            continue
        for r in range(10):
            for c in range(10):
                pc = rowsF[r][c]
                if pc is None or pc.lower() == "k" or pc.isupper() != white:
                    continue
                if rows0[r][c] != pc:   # quan da di trong 8 nua nuoc: khong bo duoc cho dong deu
                    skipped += 1; continue
                rows0[r][c] = None
                u.setpos(build(rows0, f0), last)
                rows0[r][c] = pc
                got = parse(u.fen())[0]
                rowsF[r][c] = None
                ok = got == rowsF
                rowsF[r][c] = pc
                if not ok:              # 8 nuoc khong con hop le sau khi bo quan
                    skipped += 1; continue
                q1 = u.value()
                t = pc.lower()
                dq[t].append(q0 - q1); dcp[t].append(cp(q0) - cp(q1))
        print(f"  the {idx}: q goc {q0:+.3f}", flush=True)
    u.close()

    print(f"\nBo qua {skipped} lan (quan da di trong 8 nua nuoc, hoac nuoc khong con hop le)")
    print("Mat 1 quan cua ben di -> gia tri mang (Thang - Thua, thang 2.0) giam bao nhieu")
    print(f"{'quan':<12}{'so lan':>7}{'giam q TB':>11}{'trung vi':>10}{'giam cp TB':>12}{'tang(q<0)':>10}")
    for t in sorted(dq, key=lambda t: -sum(dq[t]) / len(dq[t])):
        v = sorted(dq[t]); n = len(v)
        print(f"{TEN.get(t, t):<12}{n:>7}{sum(v) / n:>+11.3f}{v[n // 2]:>+10.3f}{sum(dcp[t]) / n:>+12.0f}"
              f"{sum(1 for x in v if x < 0):>10}")


if __name__ == "__main__":
    sys.exit(main())
