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
!cd {CV} && tar -xzf goi.tar.gz colab/chuan_bi.sh && timeout 600 bash colab/chuan_bi.sh
!cat {CV}/goi_thong_tin.txt 2>/dev/null

# Mạng đời hiện tại (.pb.gz) từ Release REL_NN. Release chỉ giữ .pb.gz của đời mới nhất mỗi cách: đời cũ hơn thì
# py/lay_mang.py tự tải .pt rồi chuyển ngay trên máy. Đặt False nếu bạn tự tải lên từ điện thoại hoặc tự tạo
# (ô 03, đời 0). .pt + thư viện huấn luyện: ô 02c (chỉ máy huấn luyện).
TAI_MANG = True
if TAI_MANG:
    name = CURRENT_PB.split("/")[-1]
    !python3 {CV}/py/lay_mang.py pb {CURRENT_PB} --rel {REL_NN} || echo "[!] Khong lay duoc {name} tu Release co_vua_mang"
!ls -la /content/*_gen*.pb.gz /content/*_gen*.pt 2>/dev/null
