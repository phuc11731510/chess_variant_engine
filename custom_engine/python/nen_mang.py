"""Nén / giải nén mạng NN (gen*.onnx, gen*.pt) để lưu trữ lâu dài -- KHÔNG MẤT MÁT, giải ra đúng
từng byte tệp gốc (kiểm sha256 khi nén và khi giải).

Cách nén: trọng số là số thực 32 bit; ba byte thấp của mỗi số gần như ngẫu nhiên, chỉ byte cao
(dấu + số mũ) lặp lại nhiều. Nên trong mỗi vùng trọng số của tệp, byte thứ 0 của mọi số được xếp
liền nhau, rồi byte thứ 1, ... (byte-shuffle), sau đó nén cả tệp bằng xz mức cao nhất (9e, từ điển
64 MiB, tham số lc/lp/pb cho dữ liệu 4 byte). Đo trên gen10.onnx (12x144): 22,05 MB -> ~18,5 MB
(xz thường: 20,2 MB). Đây gần như là mức tối thiểu khi không mất mát: ba byte thấp không nén được.

Nén cần thư viện `onnx` (tệp .onnx) hoặc `torch` (tệp .pt) để biết vùng nào là trọng số.
Giải nén chỉ cần Python chuẩn (không cần numpy/onnx/torch), chạy được cả trên Termux.

    python nen_mang.py nen  gen10.onnx gen10.pt ...   -> gen10.onnx.nen, gen10.pt.nen
    python nen_mang.py nen  <thư mục>                 -> nén mọi gen*.onnx / gen*.pt trong đó
    python nen_mang.py giai gen10.onnx.nen ...        -> gen10.onnx (không ghi đè tệp đã có)
    python nen_mang.py kiem gen10.onnx.nen ...        -> chỉ kiểm tra giải ra đúng sha256

Tệp .nen: b"FZN1" + 4 byte độ dài header + header JSON (tên, kích thước, sha256, danh sách vùng
[vị trí, độ dài]) + luồng xz của tệp đã xáo byte trong các vùng đó.
"""
import hashlib
import json
import lzma
import os
import struct
import sys

MAGIC = b"FZN1"
FILTERS = [{"id": lzma.FILTER_LZMA2, "preset": 9 | lzma.PRESET_EXTREME,
            "dict_size": 64 << 20, "lc": 0, "lp": 2, "pb": 2}]


def _float_blobs(path):
    """Các khối byte float32 (trọng số) của tệp, theo thư viện đọc được định dạng đó."""
    if path.endswith(".onnx"):
        import onnx
        from onnx import numpy_helper
        m = onnx.load(path)
        for t in m.graph.initializer:
            a = numpy_helper.to_array(t)
            if a.dtype.name == "float32" and a.size:
                yield a.tobytes()
    elif path.endswith(".pt"):
        import torch
        sd = torch.load(path, map_location="cpu", weights_only=False)
        if not isinstance(sd, dict):
            sd = getattr(sd, "state_dict", lambda: {})()
        for v in sd.values():
            if torch.is_tensor(v) and v.dtype == torch.float32 and v.numel():
                yield v.contiguous().numpy().tobytes()


def _regions(data, path):
    """Vị trí các khối trọng số trong tệp, không chồng lên nhau. Chỉ là gợi ý cho việc nén:
    vùng nào cũng giải ra đúng (xáo rồi xáo ngược), vùng sai chỉ làm nén kém đi."""
    found = []
    for blob in _float_blobs(path):
        if len(blob) < 64:
            continue
        i = data.find(blob)
        if i >= 0:
            found.append((i, len(blob) - len(blob) % 4))
    found.sort()
    out, end = [], 0
    for i, n in found:
        if i >= end:
            out.append((i, n))
            end = i + n
    return out


def _shuffle(data, regions, forward):
    b = bytearray(data)
    for off, n in regions:
        seg = bytes(b[off:off + n])
        if forward:   # a0 b0 c0 d0 a1 b1 ... -> a0 a1 ... b0 b1 ... c.. d..
            b[off:off + n] = b"".join(seg[k::4] for k in range(4))
        else:
            q = n // 4
            out = bytearray(n)
            for k in range(4):
                out[k::4] = seg[k * q:(k + 1) * q]
            b[off:off + n] = out
    return bytes(b)


def nen(path):
    dst = path + ".nen"
    if os.path.exists(dst):
        print(f"  bỏ qua {path}: đã có {dst}")
        return
    data = open(path, "rb").read()
    regions = _regions(data, path)
    header = json.dumps({"ten": os.path.basename(path), "kich_thuoc": len(data),
                         "sha256": hashlib.sha256(data).hexdigest(),
                         "vung": regions}).encode()
    body = lzma.compress(_shuffle(data, regions, True), format=lzma.FORMAT_XZ,
                         check=lzma.CHECK_CRC64, filters=FILTERS)
    blob = MAGIC + struct.pack("<I", len(header)) + header + body
    if _giai_bytes(blob)[1] != data:    # kiểm giải ra đúng từng byte TRƯỚC khi ghi
        raise SystemExit(f"[!] {path}: giải thử không khớp -- không ghi")
    with open(dst + ".tmp", "wb") as f:
        f.write(blob)
    os.replace(dst + ".tmp", dst)
    print(f"  {path}: {len(data) / 1e6:.2f} MB -> {len(blob) / 1e6:.2f} MB "
          f"({100 * len(blob) / len(data):.1f}%, {len(regions)} vùng trọng số)")


def _giai_bytes(blob):
    if blob[:4] != MAGIC:
        raise SystemExit("[!] không phải tệp .nen")
    (hl,) = struct.unpack("<I", blob[4:8])
    h = json.loads(blob[8:8 + hl])
    data = _shuffle(lzma.decompress(blob[8 + hl:]), [tuple(r) for r in h["vung"]], False)
    if len(data) != h["kich_thuoc"] or hashlib.sha256(data).hexdigest() != h["sha256"]:
        raise SystemExit(f"[!] {h['ten']}: sha256 KHÔNG khớp -- tệp .nen hỏng")
    return h, data


def giai(path, chi_kiem=False):
    h, data = _giai_bytes(open(path, "rb").read())
    if chi_kiem:
        print(f"  {path}: OK ({h['ten']}, {len(data) / 1e6:.2f} MB, sha256 khớp)")
        return
    dst = os.path.join(os.path.dirname(path), h["ten"])
    if os.path.exists(dst):
        print(f"  bỏ qua: đã có {dst}")
        return
    with open(dst + ".tmp", "wb") as f:
        f.write(data)
    os.replace(dst + ".tmp", dst)
    print(f"  {path} -> {dst} (sha256 khớp)")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows console: cp1252
    except AttributeError:
        pass
    if len(sys.argv) < 3 or sys.argv[1] not in ("nen", "giai", "kiem"):
        print(__doc__)
        sys.exit(1)
    lenh, tep = sys.argv[1], []
    for p in sys.argv[2:]:
        if os.path.isdir(p):
            tep += sorted(os.path.join(p, f) for f in os.listdir(p)
                          if f.startswith("gen") and f.endswith((".onnx", ".pt")))
        else:
            tep.append(p)
    for p in tep:
        if lenh == "nen":
            nen(p)
        else:
            giai(p, chi_kiem=(lenh == "kiem"))


if __name__ == "__main__":
    main()
