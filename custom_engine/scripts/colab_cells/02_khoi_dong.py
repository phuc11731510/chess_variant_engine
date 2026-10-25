# Khởi động: mã, binary, ONNX Runtime, mạng (mục 1)
# Mục 1 của sổ tay: tải mã nguồn, binary dựng sẵn từ Release + ONNX Runtime, sinh run.sh.
# Phải thấy "[quick] OK". Báo lỗi -> chạy ô 02b (biên dịch lại).
%cd /content
# git clone co gioi han 2 phut moi lan, toi da 3 lan (truoc day mang chap chon thi treo im lang, khong log).
import subprocess, time
for lan in (1, 2, 3):
    r = subprocess.run("rm -rf chess_variant_engine; timeout 120 git clone -q --depth 1 -b main "
                       "https://github.com/phuc11731510/chess_variant_engine.git", shell=True)
    if r.returncode == 0:
        break
    print(f"[02] git clone lan {lan} that bai hoac treo -- thu lai", flush=True)
    time.sleep(5)
!BIN_URL={REL}/custom_engine bash {E}/scripts/colab_quickstart.sh

# Tải mạng đời hiện tại (.onnx) từ GitHub Release NN_Model (REL_NN). Release chỉ giữ .onnx của đời mới nhất:
# đời cũ hơn thì tự tải .pt rồi chuyển sang .onnx ngay trên máy (python/lay_mang.py). Đặt False nếu bạn tự
# tải lên từ điện thoại (colab upload) hoặc tự tạo (ô 03, đời 0). .pt + thư viện huấn luyện: ô 02c
# (chỉ máy huấn luyện).
TAI_ONNX = True
for tai, f in [(TAI_ONNX, CURRENT_ONNX)]:
    if tai:
        # lay_mang.py không để lại tệp rỗng/dở khi lỗi; thử lại 4 lần với HTTP 429/5xx
        name = f.split("/")[-1]
        !python {E}/python/lay_mang.py onnx {f} --rel {REL_NN} || echo "[!] Khong lay duoc {name} tu Release NN_Model"
!ls -la /content/gen*.onnx /content/gen*.pt 2>/dev/null
