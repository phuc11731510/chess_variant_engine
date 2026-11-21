# Khởi động: mã, binary, ONNX Runtime, mạng (mục 1)
# Mục 1 của sổ tay: tải mã nguồn, binary dựng sẵn từ Release + ONNX Runtime, sinh run.sh.
# Phải thấy "[quick] OK". Báo lỗi -> chạy ô 02b (biên dịch lại).
#
# TIẾT KIỆM TẢI XUỐNG (2026-11-21, chủ dự án chọn): máy Colab sống nhiều đời liền, nên
#   - thư mục repo KHÔNG bị xoá mỗi đời nữa: lần đầu clone THƯA chỉ custom_engine (~1 MB thay vì ~22 MB của cả repo, phần lớn
#     là thư mục nghiên cứu), các lần sau chỉ `git fetch` + `reset` (vài trăm KB). ONNX Runtime (79 MB) và binary (3,6 MB) nằm
#     trong thư mục đó nên cũng CÒN NGUYÊN: colab_quickstart.sh chỉ tải lại binary khi Release đổi (kích thước / ETag khác).
#   - Máy MỚI thuê vẫn tải đủ một lần.
%cd /content
# git bị giới hạn 2 phút mỗi lần, tối đa 3 lần (trước đây mạng chập chờn thì treo im lặng, không log).
import os, subprocess, time
_URL = "https://github.com/phuc11731510/chess_variant_engine.git"
for lan in (1, 2, 3):
    r = None
    if os.path.isdir("chess_variant_engine/.git"):
        # Cập nhật tại chỗ: giữ third_party/ (ONNX Runtime), build-linux/ (binary), run.sh (không nằm trong git).
        r = subprocess.run("cd chess_variant_engine && timeout 120 git fetch -q --depth 1 origin main "
                           "&& git reset -q --hard FETCH_HEAD", shell=True)
        if r.returncode != 0:
            print(f"[02] git fetch lan {lan} that bai -- dung lai thu muc ma (giu third_party va build-linux)", flush=True)
            subprocess.run("rm -rf /content/.fz_giu && mkdir -p /content/.fz_giu && cd chess_variant_engine/custom_engine "
                           "&& for d in third_party build-linux; do [ -e $d ] && mv $d /content/.fz_giu/; done; "
                           "cd /content && rm -rf chess_variant_engine", shell=True)
    if not os.path.isdir("chess_variant_engine/.git"):
        # Clone thưa: chỉ custom_engine (GitHub hỗ trợ --filter); lỗi thì clone nông thường như trước đây.
        r = subprocess.run(f"timeout 120 git clone -q --depth 1 --filter=blob:none --sparse -b main {_URL} chess_variant_engine "
                           "&& cd chess_variant_engine && git sparse-checkout set custom_engine", shell=True)
        if r.returncode != 0 or not os.path.isfile("chess_variant_engine/custom_engine/meson.build"):
            print(f"[02] clone thua lan {lan} that bai -- thu clone thuong", flush=True)
            r = subprocess.run(f"rm -rf chess_variant_engine; timeout 120 git clone -q --depth 1 -b main {_URL}", shell=True)
        # Trả lại third_party / build-linux cất lúc nãy (nếu có)
        subprocess.run("[ -d /content/.fz_giu ] && for d in third_party build-linux; do [ -e /content/.fz_giu/$d ] && "
                       "mv /content/.fz_giu/$d chess_variant_engine/custom_engine/; done; rm -rf /content/.fz_giu", shell=True)
    if r is not None and r.returncode == 0:
        break
    print(f"[02] git lan {lan} that bai hoac treo -- thu lai", flush=True)
    time.sleep(5)
!BIN_URL={REL}/custom_engine bash {E}/scripts/colab_quickstart.sh

# Mạng đời hiện tại (.onnx): Release NN_Model (REL_NN) chỉ giữ .pt, nên lay_mang.py tải gen<N>.pt rồi chuyển
# sang .onnx FP16 (--fp16, kiểm trên GPU so với FP32; lệch thì giữ FP32) ngay trên máy (cần torch, onnx, onnxscript,
# onnxruntime-gpu: tự pip install nếu thiếu). Đặt False nếu bạn tự
# tải lên từ điện thoại (colab upload) hoặc tự tạo (ô 03, đời 0). .pt + thư viện huấn luyện: ô 02c
# (chỉ máy huấn luyện).
TAI_ONNX = True
for tai, f in [(TAI_ONNX, CURRENT_ONNX)]:
    if tai:
        # lay_mang.py không để lại tệp rỗng/dở khi lỗi; thử lại 4 lần với HTTP 429/5xx
        name = f.split("/")[-1]
        !python {E}/python/lay_mang.py onnx {f} --rel {REL_NN} --fp16 || echo "[!] Khong lay duoc {name} tu Release NN_Model"
!ls -la /content/gen*.onnx /content/gen*.pt 2>/dev/null
