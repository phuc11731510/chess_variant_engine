"""Chuyển các tệp kết quả của `lc0 treeplay` thành một tệp mẫu .npz của cách truyền thống.

Chạy:  python tao_mau.py <tệp ra .npz> <tệp .bin> [<tệp .bin> ...] [--q-ratio 0.2] [--nen] [--chi-mat-phang]
--nen: ghi .npz nén (np.savez_compressed, khoảng 110 byte mỗi thế cờ, đo 2026-11-04) -- dạng lưu và chuyển đi;
không có --nen thì ghi không nén (nạp nhanh nhất, dùng ngay trên máy huấn luyện).
"""
import sys
import time

import numpy as np

from ban_ghi import doc
from du_lieu import tu_ban_ghi

# --chi-mat-phang (cách cây, 8/11): chỉ mặt phẳng đầu vào + nước hợp lệ -- nhãn của cách cây lấy từ cây (cay.py),
# không dùng policy / giá trị của search (pt_*, wdl). Đúng các khoá gop_mau_cay.py đọc.
MAT_PHANG = ("bit", "phu", "r50", "hl_off", "hl")


def main():
    args = sys.argv[1:]
    q_ratio = 0.2
    if "--q-ratio" in args:
        i = args.index("--q-ratio")
        q_ratio = float(args[i + 1])
        del args[i:i + 2]
    nen = "--nen" in args
    if nen:
        args.remove("--nen")
    chi_mp = "--chi-mat-phang" in args
    if chi_mp:
        args.remove("--chi-mat-phang")
    ra, vao = args[0], args[1:]
    t = time.time()
    ban_ghi = [r for f in vao for r in doc(f)]
    mau = tu_ban_ghi(ban_ghi, q_ratio)
    if chi_mp:
        mau = {k: mau[k] for k in MAT_PHANG}
    (np.savez_compressed if nen else np.savez)(ra, **mau)
    print(f"{len(ban_ghi)} bản ghi -> {len(mau['phu'])} mẫu, {time.time() - t:.1f} giây")


if __name__ == "__main__":
    main()
