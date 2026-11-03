"""Kiểm mẫu huấn luyện (du_lieu.py) trên một tệp kết quả của `lc0 treeplay`.

Với mọi mẫu: 112 mặt phẳng giải nén (TrenGPU.lo, chạy trên CPU) phải trùng ma_hoa.ma_hoa của cùng thế cờ
(bộ mã hoá đã kiểm khớp với lc0); nhãn policy phải có đúng số nước hợp lệ, nước đã thăm phải hợp lệ, tổng
xác suất bằng 1; nhãn WDL tổng bằng 1.

Chạy:  python kiem_mau.py <tệp .bin>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python"))

import chess  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402

from ban_ghi import doc, sang_uci  # noqa: E402
from du_lieu import TrenGPU, tu_ban_ghi  # noqa: E402
from ma_hoa import ma_hoa  # noqa: E402


def main():
    ban_ghi = doc(sys.argv[1])
    mau = tu_ban_ghi(ban_ghi)
    du = TrenGPU(mau, "cpu")
    x, pol, wdl = du.lo(torch.arange(du.n))
    k, loi = 0, 0
    for r in ban_ghi:
        if r.search_lai:
            continue
        b = chess.Board()
        for m in r.duong_di:
            b.push_uci(sang_uci(m))
        for lan in r.lan:
            mong = ma_hoa(b)
            if not np.array_equal(mong, x[k].numpy()):
                lech = np.argwhere(mong != x[k].numpy())
                print(f"LỖI mặt phẳng: ván {r.id} mẫu {k}, mặt phẳng lệch {sorted(set(lech[:, 0].tolist()))}")
                loi += 1
            p = pol[k]
            if int((p >= 0).sum()) != b.legal_moves.count():
                print(f"LỖI số nước hợp lệ: mẫu {k}"); loi += 1
            if abs(float(p.clamp(min=0).sum()) - 1) > 1e-5 or abs(float(wdl[k].sum()) - 1) > 1e-5:
                print(f"LỖI tổng xác suất: mẫu {k}"); loi += 1
            if int((p > 0).sum()) != len(lan.tham):
                print(f"LỖI nước đã thăm không nằm trong nước hợp lệ: mẫu {k}"); loi += 1
            b.push_uci(sang_uci(lan.nuoc_di))
            k += 1
    assert k == du.n
    print(f"{du.n} mẫu từ {len(ban_ghi)} bản ghi: {'đạt hết' if loi == 0 else f'{loi} lỗi'}")
    sys.exit(1 if loi else 0)


if __name__ == "__main__":
    main()
