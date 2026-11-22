# Cấu hình: GEN_CURRENT và đường dẫn
# ==================== CẤU HÌNH ĐỜI MẠNG HIỆN TẠI ====================
# Ô này được GHÉP VÀO ĐẦU mọi ô khi chạy (menu fz hoặc lệnh o, xem HUONG_DAN_TERMUX.md),
# nên chỉ cần sửa GEN_CURRENT ở đây mỗi khi chuyển đời.
GEN_CURRENT = 0  # <--- Thay đổi số này (0, 1, 2,...) khi chuyển đời
# ====================================================================

E = "/content/chess_variant_engine/custom_engine"
# Release v3.0.0: binary custom_engine + ONNX Runtime (colab_quickstart.sh).
REL = "https://github.com/phuc11731510/chess_variant_engine/releases/download/v3.0.0"
# Release NN_Model (tên "NN Models"): mạng. CHỈ .pt của MỌI đời, không giữ .onnx / .fzw (2026-11-20: bớt tải lên và
# tải xuống; một Release chứa tối đa 1000 tệp nên vòng lặp dừng ở đời 990). Cần mạng dạng engine đọc được của một
# đời (sinh dữ liệu, arena): python/lay_mang.py tải .pt đời đó rồi chuyển ngay trên máy (~10-30 giây).
REL_NN = "https://github.com/phuc11731510/chess_variant_engine/releases/download/NN_Model"

GEN_NEXT = GEN_CURRENT + 1

# Kiểu mạng engine chạy (2026-11-22, chủ dự án chọn dùng bộ chạy CUDA riêng):
#   "fzw"  = bộ chạy CUDA riêng của engine (--provider fzcuda; tệp .fzw ~10 MB làm từ .pt). Đo T4: tự đấu 12.600 nps so với
#            6.590 của ONNX Runtime; máy không cần pip onnx / onnxscript / onnxruntime-gpu và ONNX Runtime 79 MB.
#   "onnx" = ONNX Runtime như trước (--provider cuda; tệp .onnx).
#   "auto" = "fzw" nếu bộ chạy CUDA chạy được trên máy đó, không thì "onnx" (ô 02 thử từng máy rồi GHI kiểu thật vào NET_FILE;
#            các ô khác và vòng lặp tự động đọc lại từ đó). Máy mới thuê nào bộ chạy CUDA hỏng sẽ tự rơi về ONNX.
NET_KIND = "auto"   # <--- "auto" | "fzw" | "onnx"
NET_FILE = "/content/fz_log/net_kind"
if NET_KIND in ("fzw", "onnx"):
    NET_EXT = NET_KIND
else:
    try:
        NET_EXT = open(NET_FILE).read().strip()
    except OSError:
        NET_EXT = ""
    if NET_EXT not in ("fzw", "onnx"):
        NET_EXT = "fzw"   # máy chưa qua ô 02: sẽ chạy 02 rồi mới biết; "fzw" là kiểu ưu tiên

# Sinh dữ liệu
CURRENT_NET = f"/content/gen{GEN_CURRENT}.{NET_EXT}"
CURRENT_PT = f"/content/gen{GEN_CURRENT}.pt"
OUT_GAMES_DIR = f"/content/games_gen{GEN_CURRENT}"

# Đóng gói
ZIP_GAMES = f"/content/games_gen{GEN_CURRENT}.zip"

# Huấn luyện đời sau
NEXT_NET = f"/content/gen{GEN_NEXT}.{NET_EXT}"
NEXT_PT = f"/content/gen{GEN_NEXT}.pt"

print(f"[Cấu hình] ĐỜI {GEN_CURRENT} -> ĐỜI {GEN_NEXT} (mạng .{NET_EXT}, NET_KIND = {NET_KIND})")
