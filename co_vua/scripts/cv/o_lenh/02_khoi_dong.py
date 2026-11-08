# Khởi động: gói lc0 + mã, ONNX Runtime, mạng đời hiện tại
# Chép theo ô 02 của fz: tải gói chạy dựng sẵn từ Release REL (goi.tar.gz: lc0, py/, colab/), chuẩn bị máy
# (colab/chuan_bi.sh: ONNX Runtime GPU, python-chess, onnx, moi_truong.sh), rồi tải mạng đời hiện tại.
# Phải thấy dòng "MAY {...}" (tóm tắt máy) và mạng <cách>_gen<N>.pb.gz ở cuối.
import os, subprocess, time

os.makedirs(CV, exist_ok=True)
# Tải gói có giới hạn 2 phút mỗi lần, tối đa 3 lần (fz: mạng chập chờn thì treo im lặng, không log).
for lan in (1, 2, 3):
    r = subprocess.run(f"timeout 120 wget -q -O {CV}/goi.tar.gz.dang_tai {REL}/goi.tar.gz && "
                       f"mv {CV}/goi.tar.gz.dang_tai {CV}/goi.tar.gz", shell=True)
    if r.returncode == 0:
        break
    print(f"[02] tải goi.tar.gz lần {lan} thất bại hoặc treo -- thử lại", flush=True)
    time.sleep(5)
else:
    tai_qua_api(REL, "goi.tar.gz", f"{CV}/goi.tar.gz")      # ô 00: đường dự phòng qua api.github.com
# ONNX Runtime GPU 1.20.1 (colab/chuan_bi.sh tải từ Release của Microsoft, bỏ qua nếu lib/ đã có): tải trước ở đây.
# Gói GỌN của fz (Release v3.0.0, 79 MB .tar.xz thay cho 258 MB .tgz, 9/11): chỉ libonnxruntime.so.1.20.1 +
# providers_cuda + providers_shared, giống từng byte bản của Microsoft (bỏ TensorRT và tệp biên dịch, lc0 không
# dùng). Lỗi thì lấy bản của Microsoft; mỗi đường đều có dự phòng qua api.github.com (8/11).
ORT = "onnxruntime-linux-x64-gpu-1.20.1"
REL_V3 = REL.rsplit("/", 1)[0] + "/v3.0.0"
ORT_MS = "https://github.com/microsoft/onnxruntime/releases/download/v1.20.1"


def _co(p):
    return os.path.exists(p) and os.path.getsize(p) > 0


if not os.path.exists(f"{CV}/lib/libonnxruntime_providers_cuda.so"):
    for rel, ten, giai in ((REL_V3, f"{ORT}-gon.tar.xz", "xJf"), (ORT_MS, f"{ORT}.tgz", "xzf")):
        r = subprocess.run(f"rm -f /tmp/{ten}; timeout 300 wget -q -O /tmp/{ten} {rel}/{ten}", shell=True)
        if r.returncode != 0 or not _co(f"/tmp/{ten}"):
            tai_qua_api(rel, ten, f"/tmp/{ten}")
        if _co(f"/tmp/{ten}") and subprocess.run(
                f"rm -rf /tmp/{ORT} && tar -{giai} /tmp/{ten} -C /tmp && mkdir -p {CV}/lib && "
                f"cp -a /tmp/{ORT}/lib/libonnxruntime* {CV}/lib/ && test -s {CV}/lib/libonnxruntime_providers_cuda.so",
                shell=True).returncode == 0:
            print(f"[02] ONNX Runtime: {ten}", flush=True)
            break
!cd {CV} && tar -xzf goi.tar.gz colab/chuan_bi.sh && timeout 600 bash colab/chuan_bi.sh
!cat {CV}/goi_thong_tin.txt 2>/dev/null

# Mạng đời hiện tại (.pb.gz) từ Release REL_NN. Release chỉ giữ .pb.gz của đời mới nhất mỗi cách: đời cũ hơn thì
# py/lay_mang.py tự tải .pt rồi chuyển ngay trên máy. Đặt False nếu bạn tự tải lên từ điện thoại hoặc tự tạo
# (ô 03, đời 0). .pt + thư viện huấn luyện: ô 02c (chỉ máy huấn luyện).
TAI_MANG = True
if TAI_MANG:
    name = CURRENT_PB.split("/")[-1]
    !python3 {CV}/py/lay_mang.py pb {CURRENT_PB} --rel {REL_NN} || echo "[!] Khong lay duoc {name} tu Release co_vua_mang"
    if not (os.path.exists(CURRENT_PB) and os.path.getsize(CURRENT_PB) > 0):
        tai_qua_api(REL_NN, name, CURRENT_PB)
!ls -la /content/*_gen*.pb.gz /content/*_gen*.pt 2>/dev/null
