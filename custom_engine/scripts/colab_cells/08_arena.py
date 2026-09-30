# Arena đời mới đấu đời cũ (mục 6)
# Mục 6 của sổ tay: arena mạng A (mặc định đời mới NEXT) đấu mạng B (mặc định đời cũ CURRENT).
# 48 ván vẫn sai số lớn (hàng trăm Elo); phát hiện chênh ~50 Elo cần 400-1000 ván.
# --search-opt max-prefetch=0: như ô 04 -- bỏ đánh giá mạng "đoán trước" (đo trên T4: +37% nps).
# Gom batch như ô 04 (engine từ 4501740, 2026-09-29): 16 ván cùng lúc, mỗi mạng gom lá của mọi ván
# đang đến lượt nó vào một lần chạy GPU (--batch-aggregate, --fixed-batch 64, minibatch 32,
# task-workers 0). Đo T4 gen11 vs gen10: 2.164 -> 2.400 nps (+11%), ván/giờ +19%. Binary cũ không có
# arena gom batch: log thiếu dòng "[arena] batch-aggregate ON" -> lấy binary mới (ô 02).
# Vòng lặp tự động (menu v) tự ghi A_ONNX, B_ONNX, GAMES, SECS dưới đây vào bản chép của ô này.
# fz: hoi GAMES Số ván arena (hai bên đổi màu mỗi ván)
GAMES = 100
PARALLEL = 16       # số ván cùng lúc (menu v đọc số này để tính ván đang dở)
SECS = 0            # > 0: dừng MỀM sau chừng này giây (ván dở chơi nốt); 0 = không giới hạn
A_ONNX = NEXT_ONNX      # mạng A (kết quả "A wins" = A thắng)
B_ONNX = CURRENT_ONNX   # mạng B

# Dừng MỀM theo lệnh (như ô 04): có tệp DUNG_MEM thì không nhận ván mới, ván đang chơi chơi nốt, in
# kết quả của các ván đã xong. Cần binary có arena dừng mềm (dòng FZ_ARENA, từ 2026-09-30).
DUNG_MEM = "/content/fz_log/dung_mem"
import os
if os.path.exists(DUNG_MEM):
    os.remove(DUNG_MEM)   # tệp của lần dừng trước: để lại thì engine dừng ngay từ ván đầu
try:
    co_dung_mem = b"FZ_ARENA" in open(f"{E}/build-linux/custom_engine", "rb").read()
except OSError:
    co_dung_mem = False
print("FZ_ARENA_DUNG_MEM=" + ("co" if co_dung_mem else "khong"))

cmd = f"""bash {E}/run.sh --arena \
    --model-a {A_ONNX} \
    --model-b {B_ONNX} \
    --games {GAMES} --visits 400 --temp-cutoff 32 \
    --provider cuda --fixed-batch 64 --max-moves 400 --show-nps \
    --search-opt max-prefetch=0 --parallel {PARALLEL} --batch-aggregate \
    --search-opt minibatch-size=32 --search-opt task-workers=0"""
if co_dung_mem:
    cmd += f" --stop-file {DUNG_MEM}" + (f" --max-seconds {SECS}" if SECS > 0 else "")

print(cmd)
!{cmd}
