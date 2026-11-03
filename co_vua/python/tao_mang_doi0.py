"""Tạo mạng đời 0 (khởi tạo ngẫu nhiên) và xuất ONNX.

Chạy:  py -I tao_mang_doi0.py <thư mục ra> [seed] [--fp16]
Ra:    doi0.pt (trọng số PyTorch) và doi0.onnx (hoặc doi0_fp16.onnx với --fp16).
"""
import sys
from pathlib import Path

import torch

from mang import MangCoVua, so_tham_so, xuat_onnx


def main():
    ra = Path(sys.argv[1])
    ra.mkdir(parents=True, exist_ok=True)
    seed = int(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else 1
    fp16 = "--fp16" in sys.argv
    torch.manual_seed(seed)
    mang = MangCoVua()
    print(f"Mạng: {so_tham_so(mang)} tham số, seed {seed}")
    torch.save(mang.state_dict(), ra / "doi0.pt")
    ten = "doi0_fp16.onnx" if fp16 else "doi0.onnx"
    xuat_onnx(mang, str(ra / ten), fp16=fp16)
    print("Đã ghi", ra / "doi0.pt", "và", ra / ten)


if __name__ == "__main__":
    main()
