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

print(f"[Cấu hình] CÁCH {BEN} · ĐỜI {GEN_CURRENT} -> ĐỜI {GEN_NEXT}")
