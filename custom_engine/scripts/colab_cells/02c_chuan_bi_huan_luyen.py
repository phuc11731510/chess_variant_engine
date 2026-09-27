# Chuẩn bị huấn luyện: gen.pt + thư viện (trước ô 07)
# Chỉ máy sắp HUẤN LUYỆN mới cần (ô 02 không tải để máy chỉ sinh dữ liệu đỡ ~55 MB):
#   - gen{GEN_CURRENT}.pt từ GitHub Release (warm-start của ô 07), nếu /content chưa có;
#   - onnx, onnxscript, onnxruntime (train.py xuất + kiểm mạng ONNX). Cảnh báo "protobuf ...
#     incompatible" là của các gói khác của Colab, không ảnh hưởng FairyZero.
# Vòng lặp tự động (menu v) tự chạy ô này trên máy được chọn huấn luyện.
import os

!pip install -q onnx onnxscript onnxruntime
if os.path.exists(CURRENT_PT) and os.path.getsize(CURRENT_PT) > 0:
    print(f"(đã có {CURRENT_PT})")
else:
    name = CURRENT_PT.split("/")[-1]
    # wget hỏng vẫn để lại tệp rỗng -> xoá để không nhầm là đã có
    !wget -nv -O {CURRENT_PT} {REL}/{name} || (echo "[!] Release KHONG co {name}"; rm -f {CURRENT_PT})
!ls -la {CURRENT_PT} 2>/dev/null
