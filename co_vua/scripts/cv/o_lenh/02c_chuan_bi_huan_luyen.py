# Chuẩn bị huấn luyện: <cách>_gen.pt (trước ô 07)
# Chép theo ô 02c của fz. Chỉ máy sắp HUẤN LUYỆN mới cần: <cách>_gen{GEN_CURRENT}.pt từ Release co_vua_mang
# (warm-start của ô 07), nếu /content chưa có. Thư viện (onnx để xuất mạng) đã cài ở ô 02 (colab/chuan_bi.sh).
# Vòng lặp tự động (menu v) tự chạy ô này trên máy được chọn huấn luyện.
import os

if os.path.exists(CURRENT_PT) and os.path.getsize(CURRENT_PT) > 0:
    print(f"(đã có {CURRENT_PT})")
else:
    name = CURRENT_PT.split("/")[-1]
    !python3 {CV}/py/lay_mang.py pt {CURRENT_PT} --rel {REL_NN} || echo "[!] Khong lay duoc {name} tu Release co_vua_mang"
!python3 -c "import onnx, chess" && echo "[thu vien] onnx, chess: co"
!ls -la {CURRENT_PT} 2>/dev/null
