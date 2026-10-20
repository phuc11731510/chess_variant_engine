# Cấu hình: GEN_CURRENT và đường dẫn
# ==================== CẤU HÌNH ĐỜI MẠNG HIỆN TẠI ====================
# Ô này được GHÉP VÀO ĐẦU mọi ô khi chạy (menu fz hoặc lệnh o, xem HUONG_DAN_TERMUX.md),
# nên chỉ cần sửa GEN_CURRENT ở đây mỗi khi chuyển đời.
GEN_CURRENT = 0  # <--- Thay đổi số này (0, 1, 2,...) khi chuyển đời
# ====================================================================

E = "/content/chess_variant_engine/custom_engine"
# Release v3.0.0: binary custom_engine + ONNX Runtime (colab_quickstart.sh).
REL = "https://github.com/phuc11731510/chess_variant_engine/releases/download/v3.0.0"
# Release NN_Model (tên "NN Models"): mạng. .pt của MỌI đời; .onnx chỉ của đời MỚI NHẤT (vòng lặp tự
# động tải .onnx đời mới lên, xoá .onnx đời trước; một Release chứa tối đa 1000 tệp nên vòng lặp dừng ở
# đời 990). Cần .onnx đời cũ (arena): python/lay_mang.py tải .pt đời đó rồi chuyển sang .onnx trên máy.
REL_NN = "https://github.com/phuc11731510/chess_variant_engine/releases/download/NN_Model"

GEN_NEXT = GEN_CURRENT + 1

# Sinh dữ liệu
CURRENT_ONNX = f"/content/gen{GEN_CURRENT}.onnx"
CURRENT_PT = f"/content/gen{GEN_CURRENT}.pt"
OUT_GAMES_DIR = f"/content/games_gen{GEN_CURRENT}"

# Đóng gói
ZIP_GAMES = f"/content/games_gen{GEN_CURRENT}.zip"

# Huấn luyện đời sau
NEXT_ONNX = f"/content/gen{GEN_NEXT}.onnx"
NEXT_PT = f"/content/gen{GEN_NEXT}.pt"

print(f"[Cấu hình] ĐỜI {GEN_CURRENT} -> ĐỜI {GEN_NEXT}")
