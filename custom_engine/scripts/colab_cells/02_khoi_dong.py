# Mục 1 của sổ tay: tải mã nguồn, binary dựng sẵn từ Release + ONNX Runtime, sinh run.sh.
# Phải thấy "[quick] OK". Báo lỗi -> chạy ô 02b (biên dịch lại).
%cd /content
!rm -rf chess_variant_engine
!git clone -q --depth 1 -b main https://github.com/phuc11731510/chess_variant_engine.git
!BIN_URL={REL}/custom_engine bash {E}/scripts/colab_quickstart.sh

# Thư viện cho huấn luyện (mục 5a của sổ tay). Cảnh báo "protobuf ... incompatible" là của
# các gói khác của Colab, không ảnh hưởng FairyZero.
!pip install -q onnx onnxscript onnxruntime

# Tải mạng đời hiện tại từ GitHub Release. Đặt False cho tệp nào bạn tự tải lên từ
# điện thoại (colab upload) hoặc tự tạo (ô 03, đời 0).
TAI_ONNX = True
TAI_PT = True
for tai, f in [(TAI_ONNX, CURRENT_ONNX), (TAI_PT, CURRENT_PT)]:
    if tai:
        name = f.split("/")[-1]
        # wget hỏng vẫn để lại tệp rỗng -> xoá để không nhầm là đã có
        !wget -nv -O {f} {REL}/{name} || (echo "[!] Release KHONG co {name}"; rm -f {f})
!ls -la /content/gen*.onnx /content/gen*.pt 2>/dev/null
