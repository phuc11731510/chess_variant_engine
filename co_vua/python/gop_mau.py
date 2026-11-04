"""Gộp mẫu của một đời cho ô 07: mỗi lần sinh (thư mục lan_*) đã có mau.npz (mã hoá sẵn trên máy sinh, colab/sinh.py)
thì nạp thẳng; lần nào thiếu thì mã hoá lại từ van.bin.gz bằng đúng bộ mã hoá đó. Ghi một .npz KHÔNG nén (nạp nhanh).

Chạy:  python gop_mau.py <tệp ra .npz> <thư mục lan_*> [<thư mục lan_*> ...]
"""
import gzip
import os
import sys
import time

import numpy as np

from ban_ghi import doc
from du_lieu import noi, tu_ban_ghi


def main():
    ra, cac_lan = sys.argv[1], sys.argv[2:]
    t = time.time()
    cac_mau, nap, tai_tao = [], 0, 0
    for d in cac_lan:
        f = os.path.join(d, "mau.npz")
        if os.path.exists(f):
            cac_mau.append(dict(np.load(f)))
            nap += 1
            continue
        b = os.path.join(d, "van.bin")
        with gzip.open(b + ".gz", "rb") as v, open(b, "wb") as o:
            o.write(v.read())
        cac_mau.append(tu_ban_ghi(list(doc(b)), 0.2))
        os.remove(b)
        tai_tao += 1
    mau = noi(cac_mau)
    np.savez(ra, **mau)
    print(f"[gop_mau] {os.path.basename(ra)}: {len(cac_lan)} lần sinh ({nap} nạp mau.npz, {tai_tao} mã hoá lại) "
          f"-> {len(mau['phu'])} mẫu, {time.time() - t:.1f} giây", flush=True)


if __name__ == "__main__":
    main()
