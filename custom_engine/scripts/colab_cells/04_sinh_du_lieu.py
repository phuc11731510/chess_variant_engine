# Sinh dữ liệu (mục 3)
# Mục 3 của sổ tay: sinh dữ liệu huấn luyện. Sửa tham số ngay dưới đây.
# Cấu hình mặc định đã đo là tốt nhất trên T4: --fixed-batch 16, --parallel 4, không --batch-aggregate.
# --max-seconds dừng MỀM: ván đang chạy vẫn chơi nốt (vượt giờ ~2-3 phút).
# fz: che_do_sinh
# (dòng trên: menu fz hỏi chế độ khi chạy ô -- tối đa theo hạn mức T4 / tự chọn số ván / tự đặt cả
#  hai -- rồi GHI số đã chọn vào SECS, GAMES dưới đây; Enter = dùng số đang ghi.)
SECS = 15480
GAMES = 1000

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
    --parallel 4 --provider cuda --fixed-batch 16 \
    --noise-alpha 0.15 --show-nps --search-opt max-prefetch=0 \
    --weights {CURRENT_ONNX} --out {OUT_GAMES_DIR}""" + (f" --stop-file {DUNG_MEM}" if co_dung_mem else "")

print(cmd)
!{cmd}
