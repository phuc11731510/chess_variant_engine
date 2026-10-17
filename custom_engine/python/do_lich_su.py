"""Do anh huong cua lich su: cung mot the co, danh gia cua mang khi dua kem 8 nua nuoc truoc do (nhu luc
tu choi that) so voi khi chi dua FEN (6/8 ban lich su trong), `go nodes 1` va tim kiem `go nodes N`.

Vi du (WSL): python3 do_lich_su.py --engine /mnt/d/.../custom_engine.exe --model 'D:\\...\\gen79.onnx'
"""
import argparse
import sys

from do_vat_chat import HIST, START, Uci


def bestmove_q(u, nodes):
    u.send(f"go nodes {nodes}")
    q = bm = None
    for l in u.wait("bestmove"):
        t = l.split()
        if t[:1] == ["info"] and "multipv" in t and t[t.index("multipv") + 1] == "1" and "wdl" in t:
            i = t.index("wdl"); w, _, lo = (int(x) for x in t[i + 1:i + 4]); q = (w - lo) / 1000.0
        if t[:1] == ["bestmove"]:
            bm = t[1]
    return q, bm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--provider", default="dml")
    ap.add_argument("--games", type=int, default=8)
    ap.add_argument("--plies", default="20,36,52,70")
    ap.add_argument("--nodes", type=int, default=100, help="lượt tìm mỗi nước khi tự chơi tạo thế cờ")
    ap.add_argument("--search", type=int, default=800, help="lượt tìm khi so nước đi chọn được")
    ap.add_argument("--goc-ca-hai", action="store_true",
                    help="đối chứng: cả hai lần đều có lịch sử (đo độ dao động tự nhiên của tìm kiếm)")
    a = ap.parse_args()
    targets = [int(x) for x in a.plies.split(",")]

    u = Uci(a.engine, a.model, a.provider)
    rows = []
    for g in range(a.games):
        moves = u.play_game(max(targets), a.nodes, 16)
        for t in targets:
            if t > len(moves):
                continue
            u.setpos(START, moves[:t - HIST]); f8 = u.fen()
            u.setpos(f8, moves[t - HIST:t]); fin = u.fen()
            qh = u.value(); qhs, bmh = bestmove_q(u, a.search)
            u.send("ucinewgame")
            if a.goc_ca_hai:
                u.setpos(f8, moves[t - HIST:t])
            else:
                u.setpos(fin, [])
            qf = u.value(); qfs, bmf = bestmove_q(u, a.search)
            u.send("ucinewgame")
            rows.append((qh, qf, qhs, qfs, bmh == bmf))
            print(f"  van {g + 1} ply {t}: mang co LS {qh:+.3f} chi FEN {qf:+.3f} | "
                  f"tim {a.search}: co LS {qhs:+.3f} chi FEN {qfs:+.3f} cung nuoc={bmh == bmf}", flush=True)
    u.close()
    n = len(rows)
    d1 = sorted(abs(r[0] - r[1]) for r in rows); d2 = sorted(abs(r[2] - r[3]) for r in rows)
    print(f"\n{n} the co. |q co lich su - q chi FEN|:")
    print(f"  mang, khong tim: TB {sum(d1) / n:.3f}  trung vi {d1[n // 2]:.3f}  lon nhat {d1[-1]:.3f}  "
          f"> 0.2: {sum(1 for x in d1 if x > 0.2)}")
    print(f"  tim {a.search} luot : TB {sum(d2) / n:.3f}  trung vi {d2[n // 2]:.3f}  lon nhat {d2[-1]:.3f}  "
          f"> 0.2: {sum(1 for x in d2 if x > 0.2)}")
    print(f"  cung nuoc di chon duoc: {sum(1 for r in rows if r[4])}/{n}")


if __name__ == "__main__":
    sys.exit(main())
