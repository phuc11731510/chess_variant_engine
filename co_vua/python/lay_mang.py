"""lay_mang.py -- lấy mạng cờ vua về máy Colab từ GitHub Release (ô 02, 02c, 08 và vòng lặp tự động của `cv`).

Chép theo python/lay_mang.py của engine cờ biến thể. Release giữ .pt của MỌI đời của mỗi cách nhưng chỉ .pb.gz
(mạng lc0 dùng) của đời MỚI NHẤT, vì một Release chứa tối đa 1000 tệp. Muốn .pb.gz của đời cũ (arena) thì tải .pt
của đời đó rồi chuyển ngay trên máy, bằng đúng đường xuất của huấn luyện (mang.xuat_onnx rồi `lc0 onnx2leela`):
.pb.gz ra có cùng trọng số với .pb.gz lúc huấn luyện xuất ra.

Tên tệp: <cách>_gen<N>.pt | <cách>_gen<N>.pb.gz, với <cách> = tt (truyền thống) hoặc cay (cây trò chơi).

    python lay_mang.py pt /content/tt_gen9.pt    --rel <URL thư mục Release>
    python lay_mang.py pb /content/tt_gen9.pb.gz --rel <URL thư mục Release> [--tu-pt]

  pt    tệp đã có (khác rỗng) thì thôi; chưa có thì tải từ Release.
  pb    tệp đã có thì thôi; chưa có: tải từ Release; Release không có thì lấy .pt (đã có trên máy, hoặc tải từ
        Release) rồi chuyển. --tu-pt: bỏ qua .pb.gz trên Release, luôn chuyển từ .pt (để kiểm).

Mã thoát: 0 = có tệp (in "FZ_MANG_CO <tệp>"); 10 = Release không có (HTTP 404) và máy cũng không có .pt để
chuyển; 1 = lỗi khác (mạng, chuyển lỗi) -- thử lại được.
Tải bằng thư viện chuẩn: thử lại 4 lần, cách nhau 15 giây, với HTTP 429/5xx và lỗi mạng; HTTP 404 báo ngay.
"""
import argparse
import http.client
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

KHONG_CO = 10
THU_LAI = (429, 500, 502, 503, 504)
LAN_THU, CHO_GIAY = 4, 15
LC0 = os.environ.get("CV_LC0", "/content/cv/lc0")


def co_tep(p):
    return os.path.isfile(p) and os.path.getsize(p) > 0


def tai(url, dich):
    """Tải url về dich (ghi tệp tạm rồi đổi tên: tải dở không để lại tệp hỏng). 0 / KHONG_CO / 1."""
    tam = dich + ".dang_tai"
    for lan in range(1, LAN_THU + 1):
        try:
            with urllib.request.urlopen(url, timeout=60) as r, open(tam, "wb") as f:
                shutil.copyfileobj(r, f, 1 << 20)
            if os.path.getsize(tam) == 0:
                raise OSError("tệp rỗng")
            os.replace(tam, dich)
            return 0
        except urllib.error.HTTPError as e:
            if e.code == 404:
                ket = KHONG_CO
                print(f"[lay_mang] Release không có {url.rsplit('/', 1)[-1]} (HTTP 404)")
                break
            loi, ket = f"HTTP {e.code}", (None if e.code in THU_LAI else 1)
        except (urllib.error.URLError, http.client.HTTPException, OSError) as e:
            loi, ket = str(e), None
        print(f"[lay_mang] {url.rsplit('/', 1)[-1]}: {loi} (lần {lan}/{LAN_THU})")
        if ket == 1:
            break
        if lan < LAN_THU:
            time.sleep(CHO_GIAY)
    else:
        ket = 1
    if os.path.exists(tam):
        os.remove(tam)
    return ket if ket is not None else 1


def ten_mang(p):
    """(cách, đời) từ tên tệp <cách>_gen<N>.pt|.pb.gz, hoặc None."""
    m = re.fullmatch(r"([a-z]+)_gen(\d+)\.(pb\.gz|pt)", os.path.basename(p))
    return (m.group(1), int(m.group(2))) if m else None


def chuyen(pt, pb):
    """pt (state_dict của MangCoVua) -> .onnx (fp32) -> .pb.gz cho lc0, đúng như huấn luyện xuất ra."""
    import torch
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from mang import MangCoVua, xuat_onnx
    mang = MangCoVua()
    mang.load_state_dict(torch.load(pt, map_location="cpu"))
    mang.eval()
    onnx = pb + ".dang_chuyen.onnx"
    tam = pb + ".dang_chuyen"
    try:
        xuat_onnx(mang, onnx)
        subprocess.run([LC0, "onnx2leela", f"--input={onnx}", f"--output={tam}", "--onnx-input=input_planes",
                        "--onnx-output-policy=policy", "--onnx-output-wdl=wdl",
                        "--moves-left-format=MOVES_LEFT_NONE"], check=True)
        os.replace(tam, pb)
    finally:
        for f in (onnx, tam):
            if os.path.exists(f):
                os.remove(f)


def lay_pt(dich, rel):
    if co_tep(dich):
        return 0
    if ten_mang(dich) is None or not rel:
        print(f"[lay_mang] không có {dich} và không biết tải từ đâu")
        return 1
    return tai(f"{rel}/{os.path.basename(dich)}", dich)


def lay_pb(dich, rel, tu_pt):
    if co_tep(dich) and not tu_pt:
        return 0
    if ten_mang(dich) is None or not rel:
        print(f"[lay_mang] không có {dich} và không biết tải từ đâu")
        return 1
    if not tu_pt:
        rc = tai(f"{rel}/{os.path.basename(dich)}", dich)
        if rc != KHONG_CO:
            return rc
        print(f"[lay_mang] {os.path.basename(dich)} không còn trên Release -> chuyển từ .pt")
    pt = dich[:-len(".pb.gz")] + ".pt"
    rc = lay_pt(pt, rel)
    if rc != 0:
        return rc
    try:
        chuyen(pt, dich)
    except Exception as e:   # noqa: BLE001 -- mọi lỗi chuyển đều là "thử lại / xem log"
        print(f"[lay_mang] chuyển {os.path.basename(pt)} -> .pb.gz lỗi: {type(e).__name__}: {e}")
        return 1
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("loai", choices=("pt", "pb"))
    ap.add_argument("tep", help="đường dẫn đích, dạng .../<cách>_gen<N>.pt | .../<cách>_gen<N>.pb.gz")
    ap.add_argument("--rel", default="", help="URL thư mục Release (…/releases/download/<tag>)")
    ap.add_argument("--tu-pt", action="store_true", help="pb: luôn chuyển từ .pt, bỏ qua .pb.gz trên Release")
    a = ap.parse_args()
    rel = a.rel.rstrip("/")
    os.makedirs(os.path.dirname(os.path.abspath(a.tep)), exist_ok=True)
    rc = lay_pt(a.tep, rel) if a.loai == "pt" else lay_pb(a.tep, rel, a.tu_pt)
    if rc == 0:
        print(f"FZ_MANG_CO {a.tep}")
    sys.exit(rc)


if __name__ == "__main__":
    main()
