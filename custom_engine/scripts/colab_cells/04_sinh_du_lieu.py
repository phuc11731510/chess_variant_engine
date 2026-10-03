# Sinh dữ liệu (mục 3)
# Mục 3 của sổ tay: sinh dữ liệu huấn luyện. Sửa tham số ngay dưới đây.
# Cấu hình mặc định đã đo là tốt nhất trên T4 (2026-09-28, gen9, 300 s mỗi cấu hình, so trên CÙNG máy):
# gom batch mạng của NHIỀU ván (--batch-aggregate), PARALLEL = 16 ván cùng lúc, --fixed-batch 64, mỗi
# ván gom 32 lá mỗi lượt (--search-opt minibatch-size=32, như lc0 self-play). Engine từ c1217ef dùng
# thông số self-play kiểu lc0 (cpuct 1,3 cố định, fpu 0, không tính lặp 2 lần là hoà, task-workers 0).
# Đo: cấu hình cũ (4 ván, batch 16) 2.766 nps -> 4.049 nps. 24/32 ván không hơn mà phần đuôi dừng mềm
# dài ra; va chạm 1/1 và tắt out-of-order-eval (như lc0) thì chậm hơn trên máy này -> giữ mặc định.
# Cache NN 2.000.000 mục (--search-opt nn-cache-size=2000000, như mặc định self-play của lc0; mặc định
# engine 65.536): đo T4 gen23 2026-10-03, ABAB 360 s: gửi NN 66% -> 61% lượt tìm, 3.944 -> 4.225 nps
# (+7%); RAM tiến trình ~4,2 GB / 12,9 GB của máy.
# --max-seconds dừng MỀM: ván đang chạy vẫn chơi nốt (16 ván: vượt giờ ~3-4 phút). Menu fz tự trừ phần
# này khỏi SECS theo số đo các lần trước (đuôi ván, ~/.fz_tk/.duoi_van).
# fz: che_do_sinh
# (dòng trên: menu fz hỏi chế độ khi chạy ô -- tối đa theo hạn mức T4 / tự chọn số ván / tự đặt cả
#  hai -- rồi GHI số đã chọn vào SECS, GAMES dưới đây; Enter = dùng số đang ghi.)
SECS = 15480
GAMES = 1000
PARALLEL = 16       # số ván chơi cùng lúc (menu fz đọc số này để tính đuôi ván và ván đang dở)

# Dừng MỀM theo lệnh: có tệp DUNG_MEM thì engine không nhận ván mới, ván đang chơi chơi nốt rồi
# thoát như hết SECS (06 chạy tiếp bình thường). Tệp do ô 09b hoặc vòng lặp tự động (menu v) tạo.
# Cần binary có --stop-file (từ 2026-09-26); binary cũ vẫn chạy như trước, chỉ không dừng mềm được.
DUNG_MEM = "/content/fz_log/dung_mem"
import os
if os.path.exists(DUNG_MEM):
    os.remove(DUNG_MEM)   # tệp của lần dừng trước: để lại thì engine dừng ngay từ ván đầu
try:
    co_dung_mem = b"--stop-file" in open(f"{E}/build-linux/custom_engine", "rb").read()
except OSError:          # chưa có binary (ô 02 lỗi?) -- lệnh dưới sẽ báo
    co_dung_mem = False
print("FZ_DUNG_MEM=" + ("co" if co_dung_mem else "khong"))
if not co_dung_mem:
    print("[!] Binary chưa có --stop-file (bản cũ): không dừng mềm được. Chạy ô 02b, đưa binary mới lên Release.")

cmd = f"""bash {E}/run.sh --selfplay \
    --games {GAMES} --max-seconds {SECS} \
    --visits 800 --max-moves 400 --temp-cutoff 32 \
    --parallel {PARALLEL} --provider cuda --fixed-batch 64 --batch-aggregate \
    --noise-alpha 0.15 --show-nps --search-opt max-prefetch=0 --search-opt minibatch-size=32 \
    --search-opt nn-cache-size=2000000 \
    --weights {CURRENT_ONNX} --out {OUT_GAMES_DIR}""" + (f" --stop-file {DUNG_MEM}" if co_dung_mem else "")

print(cmd)
!{cmd}
