"""Kiểm mạng xuất ONNX cho ra cùng kết quả trong Python và trong lc0, trên một số thế cờ chọn sẵn.

Cùng lúc kiểm ba thứ: bộ mã hoá 112 mặt phẳng (ma_hoa.py), bảng chỉ số nước đi, và việc xuất mạng.
Lc0 chạy lệnh UCI "go nodes 1" với --verbose-move-stats: in chỉ số policy của từng nước hợp lệ, xác suất
P (đã softmax trên các nước hợp lệ, phần trăm 2 chữ số) và V của thế cờ (4 chữ số).

Bước 1:  py -I kiem_khop_lc0.py lenh <tệp lệnh UCI ra>
Bước 2:  chạy lc0 với tệp lệnh đó, lưu toàn bộ đầu ra; dòng "__cho" nghĩa là chờ lc0 search xong
         (lc0 nhận "go" không chờ, nên lệnh sau sẽ đè lệnh trước)
Bước 3:  py -I kiem_khop_lc0.py so <tệp đầu ra của lc0> <mạng .onnx>
"""
import re
import sys

import chess
import numpy as np

from ma_hoa import chi_so_policy, ma_hoa

THE_CO = [
    ("thế khởi đầu", ""),
    ("Đen đi", "e2e4"),
    ("Trắng đã nhập thành, Đen đi", "e2e4 e7e5 g1f3 b8c6 f1c4 g8f6 e1g1"),
    ("có bắt tốt qua đường", "e2e4 a7a6 e4e5 d7d5"),
    ("thế lặp lại, luật 50 nước khác 0", "g1f3 g8f6 f3g1 f6g8 g1f3 g8f6"),
    ("phong cấp", "a2a4 b7b5 a4b5 a7a6 b5a6 c8b7 a6b7 b8c6"),
    ("Đen mất quyền nhập thành một cánh", "e2e4 h7h5 d2d4 h8h7 b1c3 h7h8 g1f3"),
]


def lenh(duong_dan):
    with open(duong_dan, "w", newline="\n") as f:
        f.write("uci\nisready\n")
        for _, nuoc in THE_CO:
            f.write(f"ucinewgame\nposition startpos moves {nuoc}\ngo nodes 1\n__cho\n")


def doc_lc0(duong_dan):
    """Tách đầu ra của lc0 thành từng thế cờ: {uci: (chỉ số policy, P%)} và V của thế cờ."""
    kq, cur = [], {}
    for dong in open(duong_dan, encoding="utf-8", errors="replace"):
        m = re.match(r"info string (\S+)\s+\(\s*(\d+)\s*\).*?\(P:\s*([\d.]+)%\)", dong)
        if not m:
            continue
        if m.group(1) == "node":
            # Sau đúng 1 lượt thăm, WL và D của gốc là đầu ra của mạng tại thế cờ đó.
            g = re.search(r"\(WL:\s*([-\d.]+)\)\s*\(D:\s*([-\d.]+)\)", dong)
            kq.append((cur, (float(g.group(1)), float(g.group(2)))))
            cur = {}
        else:
            cur[m.group(1)] = (int(m.group(2)), float(m.group(3)))
    return kq


def so(duong_dan_lc0, duong_dan_onnx):
    import onnxruntime as ort
    phien = ort.InferenceSession(duong_dan_onnx, providers=["CPUExecutionProvider"])
    lc0 = doc_lc0(duong_dan_lc0)
    assert len(lc0) == len(THE_CO), f"lc0 có {len(lc0)} thế cờ, cần {len(THE_CO)}"
    loi = 0
    for (ten, nuoc), (nuoc_lc0, v_lc0) in zip(THE_CO, lc0):
        b = chess.Board()
        for u in nuoc.split():
            b.push_uci(u)
        x = ma_hoa(b)[None]
        if phien.get_inputs()[0].type == "tensor(float16)":
            x = x.astype(np.float16)
        pol, wdl = phien.run(None, {"input_planes": x})
        pol, wdl = pol[0].astype(np.float64), wdl[0].astype(np.float64)
        hop_le = list(b.legal_moves)
        ci = [chi_so_policy(b, m) for m in hop_le]
        p = np.exp(pol[ci] - pol[ci].max())
        p /= p.sum()
        lech_ci = [m.uci() for m, c in zip(hop_le, ci) if nuoc_lc0.get(_ten_lc0(b, m), (None,))[0] != c]
        lech_p = max(abs(100 * pi - nuoc_lc0[_ten_lc0(b, m)][1]) for m, pi in zip(hop_le, p))
        wl, d = wdl[0] - wdl[2], wdl[1]
        wl_lc0, d_lc0 = v_lc0
        dat = (not lech_ci and len(nuoc_lc0) == len(hop_le) and lech_p < 0.011
               and abs(wl - wl_lc0) < 0.00051 and abs(d - d_lc0) < 0.0011)
        loi += not dat
        print(f"[{'ĐẠT' if dat else 'LỖI'}] {ten}: {len(hop_le)} nước hợp lệ (lc0: {len(nuoc_lc0)}), "
              f"chỉ số lệch: {lech_ci or 'không'}, P lệch tối đa {lech_p:.3f} điểm %, "
              f"WL Python {wl:+.5f} / lc0 {wl_lc0:+.5f}, D Python {d:.3f} / lc0 {d_lc0:.3f}")
    print("KẾT QUẢ:", "khớp hết" if loi == 0 else f"{loi} thế cờ không khớp")
    return loi


def viec(duong_dan):
    """Danh sách việc S (search lại) cho lc0 treeplay, mỗi thế cờ một việc, id = thứ tự."""
    with open(duong_dan, "w", newline="\n") as f:
        for i, (_, nuoc) in enumerate(THE_CO):
            f.write(f"S {i} {nuoc}\n")


def so_treeplay(duong_dan_bin, duong_dan_onnx):
    """So đầu ra thô của mạng mà treeplay ghi lại (raw_q, raw_d, prior thô của các nước đã thăm)."""
    import onnxruntime as ort

    from ban_ghi import doc
    phien = ort.InferenceSession(duong_dan_onnx, providers=["CPUExecutionProvider"])
    ghi = {r.id: r for r in doc(duong_dan_bin)}
    loi = 0
    for i, (ten, nuoc) in enumerate(THE_CO):
        b = chess.Board()
        for u in nuoc.split():
            b.push_uci(u)
        pol, wdl = phien.run(None, {"input_planes": ma_hoa(b)[None]})
        pol, wdl = pol[0].astype(np.float64), wdl[0].astype(np.float64)
        hop_le = list(b.legal_moves)
        ci = [chi_so_policy(b, m) for m in hop_le]
        p = np.exp(pol[ci] - pol[ci].max())
        p /= p.sum()
        p_theo_nuoc = {m.uci(): pi for m, pi in zip(hop_le, p)}
        lan = ghi[i].lan[0]
        from ban_ghi import sang_uci
        lech_p = max(abs(float(t["p_tho"]) - p_theo_nuoc[sang_uci(int(t["nuoc"]))]) / p_theo_nuoc[sang_uci(int(t["nuoc"]))]
                     for t in lan.tham)
        wl = wdl[0] - wdl[2]
        # Lc0 lưu prior ở độ chính xác thấp hơn (nén 16 bit), nên prior thô chỉ khớp tới cỡ 0.3%.
        dat = abs(wl - lan.raw_q) < 1e-4 and abs(wdl[1] - lan.raw_d) < 1e-4 and lech_p < 5e-3
        loi += not dat
        print(f"[{'ĐẠT' if dat else 'LỖI'}] {ten}: WL Python {wl:+.6f} / treeplay {lan.raw_q:+.6f}, "
              f"D {wdl[1]:.6f} / {lan.raw_d:.6f}, prior thô lệch tương đối tối đa {lech_p:.2e} "
              f"trên {len(lan.tham)} nước đã thăm")
    print("KẾT QUẢ:", "khớp hết" if loi == 0 else f"{loi} thế cờ không khớp")
    return loi


def _ten_lc0(b, m):
    """Lc0 in nước nhập thành theo kiểu vua đi hai ô như UCI thường, giống m.uci()."""
    return m.uci()


if __name__ == "__main__":
    if sys.argv[1] == "lenh":
        lenh(sys.argv[2])
    elif sys.argv[1] == "viec":
        viec(sys.argv[2])
    elif sys.argv[1] == "so_treeplay":
        sys.exit(1 if so_treeplay(sys.argv[2], sys.argv[3]) else 0)
    else:
        sys.exit(1 if so(sys.argv[2], sys.argv[3]) else 0)
