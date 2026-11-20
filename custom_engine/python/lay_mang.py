"""lay_mang.py -- lấy mạng NN về máy Colab từ GitHub Release "NN_Model" (ô 02, 02c, 08 và vòng lặp tự động).

Release NN_Model CHỈ giữ .pt của mọi đời, không giữ .onnx (từ 2026-11-20, để bớt tải lên và tải xuống: mỗi
đời chỉ ~19 MB lên Release thay vì ~40 MB). Muốn có .onnx của một đời (sinh dữ liệu, arena) thì tải .pt của
đời đó rồi chuyển sang .onnx ngay trên máy, bằng đúng hàm xuất của train.py (export_onnx + verify_onnx):
.onnx ra có cùng trọng số với .onnx lúc huấn luyện xuất ra.

    python lay_mang.py pt   /content/gen90.pt   --rel <URL thư mục Release>
    python lay_mang.py onnx /content/gen90.onnx --rel <URL thư mục Release> [--tu-pt] [--thu-release]

  pt    tệp đã có (khác rỗng) thì thôi; chưa có thì tải gen<N>.pt từ Release.
  onnx  tệp đã có thì thôi; chưa có: lấy gen<N>.pt (đã có trên máy, hoặc tải từ Release) rồi chuyển sang
        .onnx (~10 giây xuất + kiểm, chưa kể nạp torch). --tu-pt: chuyển lại dù .onnx đã có (để kiểm).
        --thu-release: thử tải gen<N>.onnx từ Release trước (Release không còn giữ .onnx, nên mặc định bỏ
        qua, đỡ một lần gọi mạng vô ích).
  Kiến trúc mạng (d_model, số tầng, số đầu chú ý) suy ra từ chính tệp .pt, nên mạng đời nào cũng chuyển được.

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
    """(độ rộng d_model, số tầng, số đầu chú ý) của FairyNet (transformer) từ state_dict."""
    d_model = sd["embed.weight"].shape[0]
    tang = 1 + max(int(k.split(".")[1]) for k in sd if k.startswith("blocks."))
    return d_model, tang, sd["blocks.0.attn.rel_bias"].shape[0]


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
    d_model, tang, dau = suy_kien_truc(sd)
    print(f"[lay_mang] {os.path.basename(pt)}: d_model {d_model}, {tang} tầng, {dau} đầu chú ý")
    net = FairyNet(d_model=d_model, layers=tang, heads=dau)
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


def lay_onnx(dich, rel, tu_pt, thu_release=False):
    if co_tep(dich) and not tu_pt:
        return 0
    g = doi_so(dich)
    if g is None or not rel:
        print(f"[lay_mang] không có {dich} và không biết tải từ đâu")
        return 1
    if thu_release and not tu_pt:
        rc = tai(f"{rel}/gen{g}.onnx", dich)
        if rc != KHONG_CO:
            return rc
        print(f"[lay_mang] gen{g}.onnx không có trên Release -> chuyển từ gen{g}.pt")
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
    ap.add_argument("--tu-pt", action="store_true", help="onnx: chuyển lại từ .pt dù .onnx đã có")
    ap.add_argument("--thu-release", action="store_true",
                    help="onnx: thử tải gen<N>.onnx từ Release trước (Release không còn giữ .onnx)")
    a = ap.parse_args()
    rc = (lay_pt(a.tep, a.rel) if a.loai == "pt"
          else lay_onnx(a.tep, a.rel.rstrip("/"), a.tu_pt, a.thu_release))
    if rc == 0:
        print(f"FZ_MANG_CO {a.tep}")
    sys.exit(rc)


if __name__ == "__main__":
    main()
