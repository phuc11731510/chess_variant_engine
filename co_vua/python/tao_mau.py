"""Chuyển các tệp kết quả của `lc0 treeplay` thành một tệp mẫu .npz của cách truyền thống.

Chạy:  python tao_mau.py <tệp ra .npz> <tệp .bin> [<tệp .bin> ...] [--q-ratio 0.2]
"""
import sys
import time

import numpy as np

from ban_ghi import doc
from du_lieu import tu_ban_ghi


def main():
    args = sys.argv[1:]
    q_ratio = 0.2
    if "--q-ratio" in args:
        i = args.index("--q-ratio")
        q_ratio = float(args[i + 1])
        del args[i:i + 2]
    ra, vao = args[0], args[1:]
    t = time.time()
    ban_ghi = [r for f in vao for r in doc(f)]
    mau = tu_ban_ghi(ban_ghi, q_ratio)
    np.savez(ra, **mau)
    print(f"{len(ban_ghi)} bản ghi -> {len(mau['phu'])} mẫu, {time.time() - t:.1f} giây")


if __name__ == "__main__":
    main()
