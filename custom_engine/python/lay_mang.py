"""lay_mang.py -- lấy mạng NN về máy Colab từ GitHub Release "NN_Model" (ô 02, 02c, 08 và vòng lặp tự động).

Release NN_Model giữ .pt của MỌI đời nhưng chỉ .onnx của đời MỚI NHẤT (vòng lặp tải .onnx đời mới
lên và xoá .onnx đời trước, vì một Release chứa tối đa 1000 tệp). Muốn có .onnx của đời cũ (arena)
thì tải .pt của đời đó rồi chuyển sang .onnx ngay trên máy, bằng đúng hàm xuất của train.py
(export_onnx + verify_onnx): .onnx ra có cùng trọng số với .onnx lúc huấn luyện xuất ra.

    python lay_mang.py pt   /content/gen90.pt   --rel <URL thư mục Release>
    python lay_mang.py onnx /content/gen90.onnx --rel <URL thư mục Release> [--tu-pt]

  pt    tệp đã có (khác rỗng) thì thôi; chưa có thì tải gen<N>.pt từ Release.
  onnx  tệp đã có thì thôi; chưa có: tải gen<N>.onnx từ Release; Release không có .onnx đó thì lấy
        gen<N>.pt (đã có trên máy, hoặc tải từ Release) rồi chuyển sang .onnx. --tu-pt: bỏ qua
        .onnx trên Release, luôn chuyển từ .pt (để kiểm).
  Kiến trúc mạng (số kênh, số khối, tỉ lệ SE) suy ra từ chính tệp .pt, nên mạng đời nào cũng chuyển được.

Mã thoát: 0 = có tệp (in "FZ_MANG_CO <tệp>"); 10 = Release không có (HTTP 404) và máy cũng không có
.pt để chuyển; 1 = lỗi khác (mạng, chuyển lỗi) -- thử lại được.
Tải bằng thư viện chuẩn (không cần pip): thử lại 4 lần, cách nhau 15 giây, với HTTP 429/5xx và lỗi
mạng; HTTP 404 báo ngay.
"""
import argparse
import http.client
import importlib.util
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


def doi_so(p):
    m = re.fullmatch(r"gen(\d+)\.(onnx|pt)", os.path.basename(p))
    return int(m.group(1)) if m else None


def suy_kien_truc(sd):
    """(kênh, số khối, tỉ lệ SE) của FairyNet từ state_dict."""
    kenh = sd["stem_conv.weight"].shape[0]
    khoi = 1 + max(int(k.split(".")[1]) for k in sd if k.startswith("tower."))
    return kenh, khoi, kenh // sd["tower.0.se.fc1.weight"].shape[0]


def chuyen(pt, onnx):
    """Chuyển pt (state_dict của FairyNet) sang onnx cho engine; kiểm onnx tính ra đúng như torch."""
    thieu = [m for m in ("onnx", "onnxscript", "onnxruntime") if importlib.util.find_spec(m) is None]
    if thieu:
        print(f"[lay_mang] pip install {' '.join(thieu)}")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", *thieu], check=True)
    import torch
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from model import FairyNet
    from train import export_onnx, verify_onnx
    sd = torch.load(pt, map_location="cpu")
    kenh, khoi, se = suy_kien_truc(sd)
    print(f"[lay_mang] {os.path.basename(pt)}: {kenh} kênh x {khoi} khối, SE 1/{se}")
    net = FairyNet(channels=kenh, blocks=khoi, se_ratio=se)
    net.load_state_dict(sd)
    net.eval()
    tam = onnx + ".dang_chuyen"
    try:
        export_onnx(net, tam)
        verify_onnx(tam, net)
        os.replace(tam, onnx)
    finally:
        if os.path.exists(tam):
            os.remove(tam)


def lay_pt(dich, rel):
    if co_tep(dich):
        return 0
    g = doi_so(dich)
    if g is None or not rel:
        print(f"[lay_mang] không có {dich} và không biết tải từ đâu")
        return 1
    return tai(f"{rel}/gen{g}.pt", dich)


def lay_onnx(dich, rel, tu_pt):
    if co_tep(dich) and not tu_pt:
        return 0
    g = doi_so(dich)
    if g is None or not rel:
        print(f"[lay_mang] không có {dich} và không biết tải từ đâu")
        return 1
    if not tu_pt:
        rc = tai(f"{rel}/gen{g}.onnx", dich)
        if rc != KHONG_CO:
            return rc
        print(f"[lay_mang] gen{g}.onnx không còn trên Release -> chuyển từ gen{g}.pt")
    pt = dich[:-len(".onnx")] + ".pt"
    rc = lay_pt(pt, rel)
    if rc != 0:
        return rc
    try:
        chuyen(pt, dich)
    except Exception as e:   # noqa: BLE001 -- mọi lỗi chuyển đều là "thử lại / xem log"
        print(f"[lay_mang] chuyển {os.path.basename(pt)} -> onnx lỗi: {type(e).__name__}: {e}")
        return 1
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("loai", choices=("pt", "onnx"))
    ap.add_argument("tep", help="đường dẫn đích, dạng .../gen<N>.pt | .../gen<N>.onnx")
    ap.add_argument("--rel", default="", help="URL thư mục Release (…/releases/download/NN_Model)")
    ap.add_argument("--tu-pt", action="store_true", help="onnx: bỏ qua .onnx trên Release, luôn chuyển từ .pt")
    a = ap.parse_args()
    rc = lay_pt(a.tep, a.rel) if a.loai == "pt" else lay_onnx(a.tep, a.rel.rstrip("/"), a.tu_pt)
    if rc == 0:
        print(f"FZ_MANG_CO {a.tep}")
    sys.exit(rc)


if __name__ == "__main__":
    main()
