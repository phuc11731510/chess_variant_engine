# Cấu hình: cách học, đời mạng hiện tại và đường dẫn
# ==================== CẤU HÌNH (chép theo ô 00 của fz) ====================
# Ô này được GHÉP VÀO ĐẦU mọi ô khi chạy (menu cv), nên mọi ô đều biết BEN, GEN_CURRENT và đường dẫn.
# Chạy tay từ menu: sửa BEN và GEN_CURRENT ở đây. Vòng lặp tự động (menu v) tự ghi hai số này vào bản chép
# của ô 00 cho từng việc (cách nào, đời nào), không đụng tệp này.
BEN = "tt"         # <--- cách học: "tt" = truyền thống, "cay" = cây trò chơi
GEN_CURRENT = 0    # <--- đời mạng hiện tại của cách BEN
# ==========================================================================

CV = "/content/cv"       # gói chạy: lc0 + mã Python (py/) + script Colab (colab/), từ Release REL
# Release `co_vua`: goi.tar.gz (lc0 + mã + script; co_vua/scripts/dong_goi.py --dang tạo).
REL = "https://github.com/phuc11731510/chess_variant_engine/releases/download/co_vua"
# Release `co_vua_mang`: .pt của MỌI đời mỗi cách + .pb.gz của đời mới nhất mỗi cách (vòng lặp tải mạng mới lên,
# xoá .pb.gz đời trước; .pb.gz đời cũ tạo lại từ .pt khi cần: py/lay_mang.py). Một Release chứa tối đa 1000 tệp.
REL_NN = "https://github.com/phuc11731510/chess_variant_engine/releases/download/co_vua_mang"

GEN_NEXT = GEN_CURRENT + 1

# Mạng: <cách>_gen<N>.pb.gz (lc0 chạy) và .pt (huấn luyện warm-start). Đời 0 của hai cách là CÙNG một mạng (ô 03).
CURRENT_PB = f"/content/{BEN}_gen{GEN_CURRENT}.pb.gz"
CURRENT_PT = f"/content/{BEN}_gen{GEN_CURRENT}.pt"
NEXT_PB = f"/content/{BEN}_gen{GEN_NEXT}.pb.gz"
NEXT_PT = f"/content/{BEN}_gen{GEN_NEXT}.pt"

# Sinh dữ liệu: mỗi lần chạy ô 04 là một thư mục lan_<giờ> trong thư mục ván của đời.
OUT_GAMES_DIR = f"/content/{BEN}_games_gen{GEN_CURRENT}"
# Đóng gói (ô 06) / gói gộp 4 đời để huấn luyện (vòng lặp gộp trên điện thoại, tải lên trước ô 07).
ZIP_GAMES = f"/content/{BEN}_games_gen{GEN_CURRENT}.zip"

# Thư viện CUDA / ONNX Runtime cho lc0 (colab/chuan_bi.sh ghi moi_truong.sh lúc ô 02).
import os
if os.path.exists(f"{CV}/moi_truong.sh"):
    _ld = open(f"{CV}/moi_truong.sh").read().split("LD_LIBRARY_PATH=", 1)[1].split(":${", 1)[0]
    if _ld not in os.environ.get("LD_LIBRARY_PATH", ""):
        os.environ["LD_LIBRARY_PATH"] = _ld + ":" + os.environ.get("LD_LIBRARY_PATH", "")


def tai_qua_api(rel, ten, dich):
    """Đường dự phòng khi github.com/.../releases/download/... lỗi (8/11: HTTP 504 với mọi tệp, trong lúc API vẫn
    chạy): tìm tệp trong Release qua api.github.com rồi tải bằng Accept: application/octet-stream (không cần token,
    tối đa 60 lần gọi API mỗi giờ mỗi IP). True = đã có dich."""
    import json, re, shutil, time, urllib.request
    m = re.match(r"https://github\.com/([^/]+/[^/]+)/releases/download/([^/]+)$", rel)
    if not m:
        return False
    api = f"https://api.github.com/repos/{m.group(1)}"
    for lan in (1, 2, 3):
        try:
            with urllib.request.urlopen(f"{api}/releases/tags/{m.group(2)}", timeout=60) as r:
                tep = [a for a in json.load(r)["assets"] if a["name"] == ten]
            if not tep:
                print(f"[api] Release {m.group(2)} không có {ten}")
                return False
            yc = urllib.request.Request(f"{api}/releases/assets/{tep[0]['id']}", headers={"Accept": "application/octet-stream"})
            with urllib.request.urlopen(yc, timeout=300) as r, open(dich + ".dang_tai", "wb") as f:
                shutil.copyfileobj(r, f, 1 << 20)
            if os.path.getsize(dich + ".dang_tai") != tep[0]["size"]:
                raise OSError("thiếu byte")
            os.replace(dich + ".dang_tai", dich)
            print(f"[api] đã tải {ten} qua api.github.com ({tep[0]['size']} byte)")
            return True
        except Exception as e:
            print(f"[api] {ten}: {e} (lần {lan}/3)")
            time.sleep(10)
    return False


print(f"[Cấu hình] CÁCH {BEN} · ĐỜI {GEN_CURRENT} -> ĐỜI {GEN_NEXT}")
