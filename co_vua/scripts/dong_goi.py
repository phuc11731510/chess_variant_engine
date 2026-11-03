"""Tạo gói chạy trên Colab: co_vua/ban_linux/goi.tar.gz.

Gói gồm: lc0 (co_vua/ban_linux/lc0, dịch bằng co_vua/bien_dich_linux.bat), py/ (mã Python của co_vua/python),
colab/ (co_vua/scripts/colab), goi_thong_tin.txt (commit, số tệp chưa commit, sha256 của lc0, thời điểm đóng gói).
Bộ điều phối tải gói này lên mỗi máy Colab mới; chép nó vào thư mục gốc (GOC) của cvt/cvc.

Chạy:  py dong_goi.py
"""
import hashlib
import io
import subprocess
import tarfile
import time
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]          # D:\chess_variant
CV = GOC / "co_vua"


def main():
    lc0 = CV / "ban_linux" / "lc0"
    git = lambda *a: subprocess.run(["git", "-C", str(GOC), *a], capture_output=True, text=True).stdout.strip()
    thong_tin = (f"commit={git('rev-parse', '--short', 'HEAD')}\n"
                 f"tep_chua_commit_co_vua={len(git('status', '--porcelain', '--', 'co_vua').splitlines())}\n"
                 f"lc0_sha256={hashlib.sha256(lc0.read_bytes()).hexdigest()}\n"
                 f"dong_goi={time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    ra = CV / "ban_linux" / "goi.tar.gz"
    with tarfile.open(ra, "w:gz") as t:
        t.add(lc0, "lc0")
        for f in sorted((CV / "python").glob("*.py")) + [CV / "python" / "bang_lc0.npz"]:
            t.add(f, f"py/{f.name}")
        for f in sorted((CV / "scripts" / "colab").iterdir()):
            if f.suffix == ".sh":       # script shell chạy trên Linux: bỏ CR nếu có
                du_lieu = f.read_bytes().replace(b"\r\n", b"\n")
                ti = tarfile.TarInfo(f"colab/{f.name}")
                ti.size, ti.mode, ti.mtime = len(du_lieu), 0o755, int(time.time())
                t.addfile(ti, io.BytesIO(du_lieu))
            elif f.suffix == ".py":
                t.add(f, f"colab/{f.name}")
        b = thong_tin.encode()
        ti = tarfile.TarInfo("goi_thong_tin.txt")
        ti.size, ti.mtime = len(b), int(time.time())
        t.addfile(ti, io.BytesIO(b))
    print(f"Đã ghi {ra} ({ra.stat().st_size} byte)\n{thong_tin}")


if __name__ == "__main__":
    main()
