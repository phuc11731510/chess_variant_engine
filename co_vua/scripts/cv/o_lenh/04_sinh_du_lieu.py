# Sinh dữ liệu
# Chép theo ô 04 của fz: sinh dữ liệu huấn luyện. Sửa tham số ngay dưới đây.
# Cấu hình đã đo nhanh nhất trên T4 (2026-11-03, THIET_KE_CO_VUA.md 12.8): 128 ván cùng lúc, 1 luồng gom lô,
# khoảng 16 900 lần chạy mạng mỗi giây. Tham số tự chơi kiểu lc0 của engine biến thể: 800 lượt thăm, cpuct 1,3 cố
# định, FPU 0, không prefetch, nhiễu Dirichlet 0,25 / alpha 0,3 (cờ vua), temperature 1 trong 30 nửa nước đầu,
# ván dừng ở nửa nước 450 (như lc0).
# Khác ô 04 của fz ở một chỗ: một đời đủ khi đủ LƯỢNG TÍNH TOÁN (số lần chạy mạng), không phải đủ số ván, để hai
# cách học được so ở cùng lượng tính toán. Vì vậy EVALS thay cho GAMES: máy dừng mềm khi số lần chạy mạng đã xong
# cộng phần ước lượng của các ván đang dở đạt EVALS (ván dở chơi nốt thì vừa đủ). SECS: dừng MỀM sau chừng ấy giây
# (ván dở chơi nốt), như --max-seconds của fz.
# cv: che_do_sinh
# (dòng trên: menu cv hỏi chế độ khi chạy ô -- tối đa theo hạn mức T4 / tự chọn số lần chạy mạng / tự đặt cả
#  hai -- rồi GHI số đã chọn vào SECS, EVALS dưới đây; Enter = dùng số đang ghi.)
SECS = 10000
HAN = 0             # dừng CỨNG sau chừng ấy giây (0 = tắt): vòng lặp ghi SECS + phần chừa đuôi ván, tức lúc phải
                    # gom và tải về; gần hạn thì máy tự thôi nạp theo độ dài ván đo được, tới hạn thì bỏ ván dở
EVALS = 200000000   # số lần chạy mạng giao cho máy này (một đời = 250 000 thế cờ x 800 lượt thăm)
PARALLEL = 128      # số ván chơi cùng lúc (menu cv đọc số này để tính đuôi ván)

# Dừng MỀM theo lệnh: có tệp DUNG_MEM thì không nhận ván mới, ván đang chơi chơi nốt rồi thoát như hết SECS (06 chạy
# tiếp bình thường). Tệp do ô 09b hoặc vòng lặp tự động (menu v) tạo.
DUNG_MEM = "/content/fz_log/dung_mem"
import os, time
if os.path.exists(DUNG_MEM):
    os.remove(DUNG_MEM)   # tệp của lần dừng trước: để lại thì dừng ngay từ ván đầu
LAN = time.strftime("lan_%Y%m%d_%H%M%S")

# Cách cây trò chơi (THIET_KE_CO_VUA.md 6.2, 12.6): ván luôn đi nước nhiều lượt thăm nhất (temperature 0, nhiễu
# Dirichlet giữ nguyên); việc (ván rẽ, search lại) do điện thoại giao trong /content/cay_viec.txt (vòng lặp tải lên);
# hết việc mà còn phần giao thì máy tự quét các ván nó vừa chơi rồi rẽ tiếp. Đời 0 (cây còn trống): bắt đầu bằng
# PARALLEL ván từ thế khởi đầu rồi tự quét.
TEMP_PLIES, THEM = 30, ""
if BEN == "cay":
    VIEC = "/content/cay_viec.txt"
    TEMP_PLIES = 0
    THEM = (f"--tu-quet --viec {VIEC}" if os.path.exists(VIEC) and os.path.getsize(VIEC) > 0
            else f"--tu-quet --van-goc {PARALLEL}")

# Máy đã dựng bằng gói cũ (trước 7/11) chưa có --han-cung: bỏ qua thay vì để sinh.py báo sai tham số.
HC = f"--han-cung {HAN}" if HAN and "--han-cung" in open(f"{CV}/colab/sinh.py", encoding="utf-8").read() else ""

cmd = f"""python3 {CV}/colab/sinh.py --lc0 {CV}/lc0 --mang {CURRENT_PB} \
    --thu-muc {OUT_GAMES_DIR}/{LAN} --song-song {PARALLEL} --luong-gom-lo 1 \
    --visits 800 --temp-plies {TEMP_PLIES} --max-ply 450 \
    --giao {EVALS} --max-giay {SECS} {HC} --tep-dung {DUNG_MEM} {THEM}"""

if not (os.path.exists(CURRENT_PB) and os.path.getsize(CURRENT_PB) > 0):
    print(f"[!] Thiếu mạng {CURRENT_PB} -- chạy ô 02 (hoặc ô 03 cho đời 0) trước")
else:
    print(cmd)
    !{cmd}
