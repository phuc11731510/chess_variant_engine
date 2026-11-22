# Chuẩn bị huấn luyện: gen.pt + thư viện (trước ô 07)
# Chỉ máy sắp HUẤN LUYỆN mới cần (ô 02 không tải để máy chỉ sinh dữ liệu đỡ ~55 MB):
#   - gen{GEN_CURRENT}.pt từ GitHub Release NN_Model (warm-start của ô 07), nếu /content chưa có;
#   - CHỈ khi máy chạy kiểu mạng "onnx" (NET_EXT, ô 00 / 02): onnx, onnxscript, onnxruntime-gpu (bản GPU: train.py xuất + kiểm
#     mạng ONNX FP16 trên GPU). Cảnh báo "protobuf ... incompatible" là của các gói khác của Colab, không ảnh hưởng FairyZero.
#     Kiểu "fzw" (bộ chạy CUDA riêng): train.py chỉ ghi .pt, không cần gói nào ngoài torch của Colab (đỡ ~250 MB tải xuống mỗi máy).
# Vòng lặp tự động (menu v) tự chạy ô này trên máy được chọn huấn luyện.
import os

if NET_EXT == "onnx":
    !pip install -q onnx onnxscript onnxruntime-gpu
else:
    print("(kiểu mạng fzw: không cần pip onnx / onnxscript / onnxruntime-gpu)")
if os.path.exists(CURRENT_PT) and os.path.getsize(CURRENT_PT) > 0:
    print(f"(đã có {CURRENT_PT})")
else:
    # .pt của mọi đời nằm trên Release NN_Model (REL_NN); lay_mang.py không để lại tệp rỗng/dở khi lỗi
    name = CURRENT_PT.split("/")[-1]
    !python {E}/python/lay_mang.py pt {CURRENT_PT} --rel {REL_NN} || echo "[!] Khong lay duoc {name} tu Release NN_Model"
!ls -la {CURRENT_PT} 2>/dev/null
