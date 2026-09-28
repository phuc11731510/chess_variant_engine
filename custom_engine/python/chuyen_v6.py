"""Chuyển gói ván cũ (.gz / .bin, data v1-5) sang dạng gọn v6 (.xz) -- nhỏ hơn ~4,7 lần.

    python chuyen_v6.py games_gen5.zip [games_gen6.zip ...]   -> games_gen5_v6.zip ...
    python chuyen_v6.py games_gen5.zip --out gon.zip

Mỗi ván: đọc bản ghi cũ -> mã hoá v6 -> GIẢI MÃ LẠI và so TỪNG BIT mọi trường với bản
cũ; lệch một bit là dừng, không ghi gói. Ván đã là .xz thì chép nguyên. Giữ tên
(đổi đuôi thành .xz), thứ tự và NGÀY SỬA của từng ván (train.py lấy 4% ván mới nhất
làm tập kiểm định theo ngày sửa). Ghi ra tệp tạm rồi mới đổi tên; KHÔNG bao giờ
xoá hay ghi đè gói gốc. In "FZ_CHUYEN_XONG <số ván> <MB cũ> <MB mới>".
"""

import argparse
import gzip
import os
import sys
import time
import zipfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trainingdata_reader as tr  # noqa: E402
import trainingdata_v6 as v6  # noqa: E402


def _records(zf, name):
    raw = zf.read(name)
    if name.endswith(".gz"):
        raw = gzip.decompress(raw)
    if len(raw) % tr.RECORD_SIZE:
        raise ValueError(f"{name}: kích thước {len(raw)} không chia hết cho {tr.RECORD_SIZE}")
    return [tr.unpack_record(raw[i:i + tr.RECORD_SIZE]) for i in range(0, len(raw), tr.RECORD_SIZE)]


def _same(a, b):
    """Two record dicts hold the same bits in every field of the 45940-byte form."""
    for k, v in a.items():
        w = b[k]
        if isinstance(v, np.ndarray):
            if v.shape != np.shape(w) or v.tobytes() != np.asarray(w, v.dtype).tobytes():
                return False
        elif isinstance(v, float):
            if np.float32(v).tobytes() != np.float32(w).tobytes():
                return False
        elif v != w:
            return False
    return True


def convert(src, out):
    t0 = time.time()
    tam = out + ".dang_chuyen"
    n_game = n_rec = 0
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(
            tam, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as zout:
        for info in zin.infolist():
            name = info.filename
            if info.is_dir() or not tr.is_game_member(name):
                continue
            if name.endswith(tr.V6_EXT):
                data, new = zin.read(name), name
            else:
                recs = _records(zin, name)
                if not recs:
                    continue
                data = v6.encode_game(recs)
                back = v6.decode_game(data, name)
                if len(back) != len(recs) or not all(_same(a, b) for a, b in zip(recs, back)):
                    raise SystemExit(f"[!] {name}: đọc lại KHÔNG khớp -- dừng, không ghi gói")
                new = name.rsplit(".", 1)[0] + tr.V6_EXT
                n_rec += len(recs)
            zi = zipfile.ZipInfo(new, date_time=info.date_time)   # giữ ngày sửa
            zi.compress_type = zipfile.ZIP_STORED
            zout.writestr(zi, data)
            n_game += 1
            if n_game % 200 == 0:
                print(f"  {n_game} ván ...", flush=True)
    os.replace(tam, out)
    mb_in, mb_out = os.path.getsize(src) / 1e6, os.path.getsize(out) / 1e6
    print(f"[chuyển] {src} -> {out}: {n_game} ván ({n_rec} thế cờ đã chuyển), "
          f"{mb_in:.1f} MB -> {mb_out:.1f} MB ({mb_in / max(mb_out, 1e-9):.1f} lần), "
          f"{time.time() - t0:.0f} s; đọc lại khớp từng bit")
    print(f"FZ_CHUYEN_XONG {n_game} {mb_in:.1f} {mb_out:.1f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("zips", nargs="+")
    ap.add_argument("--out", help="tên gói ra (chỉ khi chuyển một gói)")
    a = ap.parse_args()
    if a.out and len(a.zips) != 1:
        raise SystemExit("--out chỉ dùng khi chuyển một gói")
    for z in a.zips:
        out = a.out or z[:-4] + "_v6.zip"
        if os.path.abspath(out) == os.path.abspath(z) or os.path.exists(out):
            raise SystemExit(f"[!] {out} đã có (hoặc trùng gói gốc) -- không ghi đè")
        convert(z, out)


if __name__ == "__main__":
    main()
