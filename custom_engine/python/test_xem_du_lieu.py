# -*- coding: utf-8 -*-
"""Test xem_du_lieu.py: đổi ván trong dữ liệu huấn luyện thành nhật ký xem lại (GUI --replay / --replay-dir).

  py -3 test_xem_du_lieu.py                      # không cần engine
  FZ_ENGINE=...\\custom_engine.exe py -3 test_xem_du_lieu.py   # thêm: so thế cuối và kết quả với chính engine

Ba ván thật làm mẫu trong mau_van/ (đã kiểm bằng engine): một có ăn qua đường, một có phong cấp, một thắng bằng 7 lần
chiếu; mau_van/mong_doi.json giữ thế đầu, dãy nước, bàn cờ cuối và lý do kết thúc đã kiểm. Hai ván lấy từ dữ liệu đời 1;
van_phong_cap.xz lấy từ dữ liệu đời 54 (2026-11-24, thay ván cũ có phong cấp Tượng ở hàng 3 mà luật mới không cho: hàng 8/3
chỉ còn Mã, Centaur, Alibaba, Grasshopper), thắng bằng 8 lần chiếu, có phong cấp Grasshopper ở hàng 8.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xem_du_lieu as x  # noqa: E402

MAU = os.path.join(HERE, "mau_van")
FAILS = []


def check(cond, msg):
    print(("[OK]   " if cond else "[FAIL] ") + msg)
    if not cond:
        FAILS.append(msg)


# --- encode ngược chỉ số nước (nguyên văn MoveToNNIndex của encoder.cc) để thử decode ---------------------------------
def ma_hoa(from_rk, from_fl, dx, dy, promo=None):
    frm = from_rk * 10 + from_fl
    if promo is not None:
        return (x.PROMOTION_BASE + x.PROMO.index(promo) * 3 + dx + 1) * 100 + frm
    if (abs(dx), abs(dy)) in ((1, 2), (2, 1)):
        return (x.KNIGHT_BASE + x.KNIGHT.index((dx, dy))) * 100 + frm
    if (abs(dx), abs(dy)) in ((1, 3), (3, 1)):
        return (x.CAMEL_BASE + x.CAMEL.index((dx, dy))) * 100 + frm
    k = max(abs(dx), abs(dy))
    return (x.SLIDE_DIRS.index((dx // k, dy // k)) * 9 + k - 1) * 100 + frm


def test_bang_chi_so():
    """Mọi (loại, ô đi) hợp lệ giải mã ra nước rồi mã hoá lại đúng chỉ số cũ; Đen lật hàng."""
    n = 0
    for t in range(x.PROMOTION_BASE + 27):
        for frm in range(100):
            idx = t * 100 + frm
            rk, fl = divmod(frm, 10)
            try:
                uci = x.nuoc_tu_chi_so(idx, False)
            except ValueError:
                continue          # đích ra ngoài bàn
            f2, r2, promo = x.tach_nuoc(uci)[1] % 10, x.tach_nuoc(uci)[1] // 10, x.tach_nuoc(uci)[2]
            back = ma_hoa(rk, fl, f2 - fl, r2 - rk, promo or None)
            if back != idx:
                check(False, f"chỉ số {idx} -> {uci} -> {back}")
                return
            # Đen: hàng lật, cột giữ
            ud = x.nuoc_tu_chi_so(idx, True)
            fr_d, to_d, pr_d = x.tach_nuoc(ud)
            if (fr_d // 10, to_d // 10) != (9 - rk, 9 - r2) or (fr_d % 10, to_d % 10) != (fl, f2) or pr_d != promo:
                check(False, f"Đen: chỉ số {idx} -> {ud}")
                return
            n += 1
    check(n > 5000, f"bảng chỉ số nước: {n} (loại, ô đi) hợp lệ giải mã và mã hoá lại đúng, Đen lật hàng")
    # vài giá trị biết trước (ô j3 = hàng 2 chỉ số 9, loại 63 = hướng Tây Bắc 1 ô): j3 -> i4
    check(x.nuoc_tu_chi_so(6329, False) == "j3i4", "6329 -> j3i4 (Trắng)")
    check(x.nuoc_tu_chi_so(6329, True) == "j8i7", "6329 -> j8i7 (Đen, hàng lật)")
    # phong cấp: loại = PROMOTION_BASE + quân*3 + (dx+1); d8 = ô 73
    check(x.nuoc_tu_chi_so((x.PROMOTION_BASE + x.PROMO.index("g") * 3 + 1) * 100 + 73, False) == "d8d9g",
          "phong Grasshopper đi thẳng: d8d9g")
    check(x.nuoc_tu_chi_so((x.PROMOTION_BASE + x.PROMO.index("c") * 3 + 0) * 100 + 73, False) == "d8c9c",
          "phong Pháo ăn chéo trái: d8c9c")


def test_van_mau():
    mong = json.load(open(os.path.join(MAU, "mong_doi.json"), encoding="utf-8"))
    for ten, m in mong.items():
        v = x.doc_van((os.path.join(MAU, ten), None))
        check(v.fen == m["fen_dau"], f"{ten}: thế đầu")
        check(v.nuoc == m["nuoc"], f"{ten}: dãy {len(v.nuoc)} nước")
        check(x.dat_quan(v.ban_cuoi()) == m["ban_cuoi"], f"{ten}: bàn cờ cuối (ván này {'có ăn qua đường' if 'qua_duong' in ten else 'thường'})")
        check(x.MA_KET_QUA[v.ket_qua()] == m["ket_qua"], f"{ten}: kết quả {m['ket_qua']}")
        check(v.kiem() == [], f"{ten}: mọi nước khớp bàn cờ bản ghi kế tiếp")
        # lý do suy ra từ thế cuối engine đã ghi (không cần engine)
        fen = m["fen_cuoi_engine"]
        kq = {"W": "white", "B": "black", "D": "draw"}[m["ket_qua"]]
        so_hl = 0 if m["ly_do"] == "no_moves" else 1
        check(x.ly_do(fen, kq, so_hl, len(v.nuoc), m["ket_qua"]) == m["ly_do"], f"{ten}: lý do {m['ly_do']}")
    pc = x.doc_van((os.path.join(MAU, "van_phong_cap.xz"), None))
    check(any(not mv[-1].isdigit() for mv in pc.nuoc), "van_phong_cap: có nước phong cấp (hậu tố chữ)")


def test_nhat_ky():
    v = x.doc_van((os.path.join(MAU, "van_thang_chieu.xz"), None))
    t = x.nhat_ky(v, 3, 10)
    dong = t.split("\n")
    check(dong[0].startswith("# dữ liệu huấn luyện"), "dòng đầu là chú thích #")
    dau = [l for l in dong if l.startswith("--- nửa nước")]
    check(len(dau) == len(v.nuoc), f"{len(dau)} mục, mỗi nửa nước một mục")
    check(all(re.match(r"^--- nửa nước \d+ \((trắng|đen) đi\) → \S+$", l) for l in dau), "tiêu đề mỗi mục đúng định dạng GUI")
    check(dau[0].endswith("→ " + v.nuoc[0]) and dau[-1].endswith("→ " + v.nuoc[-1]), "nước ở tiêu đề = nước đã đi")
    pos = [l for l in dong if l.startswith("position fen ")]
    check(pos[0] == f"position fen {v.fen}" and pos[-1] == f"position fen {v.fen} moves " + " ".join(v.nuoc[:-1]),
          "lệnh position: mục đầu không có moves, mục cuối đủ mọi nước trừ nước của chính mục đó")
    stat = [l for l in dong if re.match(r"^    \S+ N \d+( Q -?[\d.]+)?$", l)]
    check(len(stat) > len(v.nuoc), "có dòng 'N' của các nước ứng viên")
    khoi = t.split("--- nửa nước")[1:]
    check(all(len(re.findall(r"^    \S+ N \d+", k, flags=re.M)) <= x.TOP_UNG_VIEN + 1 for k in khoi),
          f"mỗi mục tối đa {x.TOP_UNG_VIEN} nước ứng viên (+ nước đã đi)")
    check(any(" Q " in l for l in stat), "nước đã đi / nước tốt nhất có Q")
    info = [l for l in dong if l.startswith("  depth ")]
    check(all(re.search(r" wdl \d+ \d+ \d+ nodes \d+ .* pv \S+$", l) for l in info), "dòng info có wdl, nodes và pv")


def test_xuat_va_cli():
    tmp = tempfile.mkdtemp(prefix="fz_xem_")
    out = os.path.join(tmp, "xem")
    r = subprocess.run([sys.executable, os.path.join(HERE, "xem_du_lieu.py"), MAU, "--xuat", out],
                       capture_output=True, text=True, encoding="utf-8")
    check(r.returncode == 0, f"--xuat không engine: mã thoát {r.returncode}")
    tsv = open(os.path.join(out, "chi_muc.tsv"), encoding="utf-8").read().splitlines()
    check(tsv[0].split("\t") == list(x.CAC_COT) and len(tsv) == 4, "chi_muc.tsv: tiêu đề + 3 ván")
    cot = [l.split("\t") for l in tsv[1:]]
    check(all(len(c) == len(x.CAC_COT) for c in cot), "mỗi dòng đủ cột")
    check(sorted(c[3] for c in cot) == sorted(["B", "B", "W"]), "cột kết quả: 1 Trắng thắng, 2 Đen thắng")
    check(all(os.path.exists(os.path.join(out, c[1])) for c in cot), "mỗi ván có tệp nhật ký")
    r2 = subprocess.run([sys.executable, os.path.join(HERE, "xem_du_lieu.py"), MAU, "--xuat", out],
                        capture_output=True, text=True, encoding="utf-8")
    check("đã có" in r2.stdout, "chạy lại khi dữ liệu không đổi thì bỏ qua")
    r3 = subprocess.run([sys.executable, os.path.join(HERE, "xem_du_lieu.py"), MAU, "--liet-ke", "--kiem"],
                        capture_output=True, text=True, encoding="utf-8")
    check(r3.returncode == 0 and "3 ván" in r3.stdout, "--liet-ke --kiem: 3 ván, đều giải mã đúng")
    r4 = subprocess.run([sys.executable, os.path.join(HERE, "xem_du_lieu.py"), MAU, "--van", "99"],
                        capture_output=True, text=True, encoding="utf-8")
    check(r4.returncode == 1 and "chỉ có 3 ván" in r4.stdout, "--van ngoài khoảng bị từ chối")
    one = os.path.join(tmp, "mot.txt")
    r5 = subprocess.run([sys.executable, os.path.join(HERE, "xem_du_lieu.py"), os.path.join(MAU, "van_phong_cap.xz"), "--out", one],
                        capture_output=True, text=True, encoding="utf-8")
    check(r5.returncode == 0 and os.path.getsize(one) > 1000, "một tệp ván: ghi nhật ký")


def test_engine():
    exe = os.environ.get("FZ_ENGINE")
    if not exe:
        print("[skip] đặt FZ_ENGINE để so thế cuối / kết quả với engine thật")
        return
    mong = json.load(open(os.path.join(MAU, "mong_doi.json"), encoding="utf-8"))
    may = x.May(exe)
    try:
        for ten, m in mong.items():
            v = x.doc_van((os.path.join(MAU, ten), None))
            fen, hl, kq = may.the_cuoi(v.fen, v.nuoc)
            check(fen == m["fen_cuoi_engine"], f"engine: {ten}: thế cuối trùng")
            check(x.ly_do(fen, kq, hl, len(v.nuoc), m["ket_qua"]) == m["ly_do"], f"engine: {ten}: lý do {m['ly_do']}")
            # hậu tố phong cấp: engine nhận đúng quân (trước 2026-11-21 chữ cái phong cấp của engine sai)
        pc = x.doc_van((os.path.join(MAU, "van_phong_cap.xz"), None))
        k = next(i for i, mv in enumerate(pc.nuoc) if not mv[-1].isdigit())
        may.gui("ucinewgame")
        may.gui(f"position fen {pc.fen} moves " + " ".join(pc.nuoc[:k + 1]))
        may.gui("fen")
        fen = may.cho(lambda l: l.startswith("fen "))[4:]
        frm, to, promo = x.tach_nuoc(pc.nuoc[k])
        b = x.ban_co({"piece_planes": pc.recs[k + 1]["piece_planes"], "side_to_move": pc.recs[k + 1]["side_to_move"]})
        check(fen.split()[0] == x.dat_quan(b), f"engine nhận phong cấp {pc.nuoc[k]}: bàn cờ trùng bản ghi dữ liệu")
    finally:
        may.dong()


if __name__ == "__main__":
    test_bang_chi_so()
    test_van_mau()
    test_nhat_ky()
    test_xuat_va_cli()
    test_engine()
    print()
    print("ALL PASS" if not FAILS else f"{len(FAILS)} FAIL")
    sys.exit(1 if FAILS else 0)
