"""Tệp mẫu huấn luyện của cách cây trò chơi cho ô 07: mặt phẳng đầu vào lấy lại từ các mau.npz (đã mã hoá sẵn trên
máy sinh, colab/sinh.py), nhãn và trọng số lấy từ nhan_doi<G>.npz (cay.py trên điện thoại, phần 4, 5, 10 của thiết kế).
Ghi một .npz KHÔNG nén cùng định dạng với du_lieu.py, thêm mảng "w" (trọng số bốc mẫu = số ván đi qua node).

Chạy:  python gop_mau_cay.py <tệp ra .npz> <nhan_doi<G>.npz> <nhan_doi<G>.tep.txt> <thư mục chứa các mau.npz>
Trong tệp .tep.txt mỗi dòng là "<chỉ số tệp>\\t<đường dẫn tương đối>"; đường dẫn tính từ thư mục ở tham số cuối.
"""
import os
import sys
import time

import numpy as np

from du_lieu import chi_so_tu_raw


def main():
    ra, f_nhan, f_tep, goc = sys.argv[1:5]
    t = time.time()
    nh = dict(np.load(f_nhan))
    tep = {}
    for dong in open(f_tep, encoding="utf-8"):
        if dong.strip():
            i, duong = dong.rstrip("\n").split("\t")
            tep[int(i)] = os.path.join(goc, duong)
    n = len(nh["tep"])
    bit = np.zeros((n, 104), np.uint64)
    phu = np.zeros(n, np.uint8)
    r50 = np.zeros(n, np.uint8)
    hl_tung = [None] * n
    for i, duong in tep.items():
        chon = np.where(nh["tep"] == i)[0]
        m = np.load(duong)
        h = nh["hang"][chon]
        bit[chon], phu[chon], r50[chon] = m["bit"][h], m["phu"][h], m["r50"][h]
        off, hl = m["hl_off"], m["hl"]
        for k, hh in zip(chon.tolist(), h.tolist()):
            hl_tung[k] = hl[off[hh]:off[hh + 1]]
    thieu = [k for k in range(n) if hl_tung[k] is None]
    if thieu:
        sys.exit(f"[gop_mau_cay] thiếu mặt phẳng của {len(thieu)} mẫu (thiếu tệp mau.npz?)")
    hl_dai = np.array([len(x) for x in hl_tung])
    po = nh["pol_off"]
    pt_i = np.empty(len(nh["pol_mv"]), np.int16)
    for k in range(n):
        den = bool(nh["den_di"][k])
        for j in range(po[k], po[k + 1]):
            pt_i[j] = chi_so_tu_raw(int(nh["pol_mv"][j]), den)
    off = lambda dai: np.concatenate(([0], np.cumsum(dai))).astype(np.int64)
    mau = {"bit": bit, "phu": phu, "r50": r50, "hl_off": off(hl_dai), "hl": np.concatenate(hl_tung).astype(np.int16),
           "pt_off": po.astype(np.int64), "pt_i": pt_i, "pt_p": nh["pol_p"].astype(np.float32),
           "wdl": nh["wdl"].astype(np.float32), "w": nh["w"].astype(np.float32)}
    np.savez(ra, **mau)
    print(f"[gop_mau_cay] {n} mẫu từ {len(tep)} tệp mau.npz, tổng trọng số {float(nh['w'].sum()):.1f}, "
          f"số bước {int(nh['so_buoc'])}, {time.time() - t:.1f} giây", flush=True)


if __name__ == "__main__":
    main()
