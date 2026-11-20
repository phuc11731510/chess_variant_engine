# Arena đời mới đấu đời cũ (mục 6)
# Mục 6 của sổ tay: arena mạng A (mặc định đời mới NEXT) đấu mạng B (mặc định đời cũ CURRENT).
# 48 ván vẫn sai số lớn (hàng trăm Elo); phát hiện chênh ~50 Elo cần 400-1000 ván.
# --search-opt max-prefetch=0: như ô 04 -- bỏ đánh giá mạng "đoán trước" (đo trên T4: +37% nps).
# Gom batch như ô 04 (engine từ 4501740, 2026-09-29): 16 ván cùng lúc, mỗi mạng gom lá của mọi ván
# đang đến lượt nó vào một lần chạy GPU (--batch-aggregate, minibatch 32,
# task-workers 0). Đo T4 gen11 vs gen10: 2.164 -> 2.400 nps (+11%), ván/giờ +19%. Từ 2026-10-01 mẻ
# 32 thay 64: arena gom ít lá mỗi lần (cây mới mỗi nước, 400 lượt), mẻ 64 bỏ phí 40-45% chỗ trống;
# đo T4 gen20 vs gen19: 64 -> 2.165-2.364 nps, 32 -> 2.599 nps (phí còn 27%). Binary cũ không có
# arena gom batch: log thiếu dòng "[arena] batch-aggregate ON" -> lấy binary mới (ô 02).
# Vòng lặp tự động (menu v) tự ghi A_ONNX, B_ONNX, GAMES, SECS dưới đây vào bản chép của ô này.
# fz: hoi GAMES Số ván arena (hai bên đổi màu mỗi ván)
GAMES = 100
PARALLEL = 16       # số ván cùng lúc (menu v đọc số này để tính ván đang dở)
SECS = 0            # > 0: dừng MỀM sau chừng này giây (ván dở chơi nốt); 0 = không giới hạn
A_ONNX = NEXT_ONNX      # mạng A (kết quả "A wins" = A thắng)
B_ONNX = CURRENT_ONNX   # mạng B

# Mạng .onnx của hai bên: máy chưa có thì lấy từ Release NN_Model. Release chỉ giữ .pt (không giữ .onnx)
# (từ 2026-10-20, vì một Release chứa tối đa 1000 tệp); đời cũ hơn thì python/lay_mang.py tải .pt đời đó rồi
# chuyển sang .onnx ngay trên máy (~1-3 phút, CPU), nên đấu hai đời bất kỳ đều được. Đã có sẵn thì bỏ qua.
import os
for _f in (A_ONNX, B_ONNX):
    if not (os.path.exists(_f) and os.path.getsize(_f) > 0):
        !python {E}/python/lay_mang.py onnx {_f} --rel {REL_NN} --fp16
_thieu = [_f for _f in (A_ONNX, B_ONNX) if not (os.path.exists(_f) and os.path.getsize(_f) > 0)]

# Dừng MỀM theo lệnh (như ô 04): có tệp DUNG_MEM thì không nhận ván mới, ván đang chơi chơi nốt, in
# kết quả của các ván đã xong. Cần binary có arena dừng mềm (dòng FZ_ARENA, từ 2026-09-30).
DUNG_MEM = "/content/fz_log/dung_mem"
if os.path.exists(DUNG_MEM):
    os.remove(DUNG_MEM)   # tệp của lần dừng trước: để lại thì engine dừng ngay từ ván đầu
try:
    _bin = open(f"{E}/build-linux/custom_engine", "rb").read()
except OSError:
    _bin = b""
co_dung_mem = b"FZ_ARENA" in _bin
# Arena --start-fen (2026-11-20): một binary cũ vẫn nhận cờ nhưng BỎ QUA nó trong arena (chơi từ thế cố định) mà
# không báo gì, nên phải kiểm trước khi chạy, không đợi lỗi.
co_the_arena = b"each played by a PAIR" in _bin
# Arena tìm kiếm HẰNG (2026-11-20, chủ dự án chọn): 400 lượt thăm mỗi nước, c_puct 1,25, KHÔNG nhiễu, nhiệt độ 0,5 cho CẢ ván
# (trọng số (N/Nmax)^(1/T), như tự đấu). Binary cũ vẫn nhận --temperature/--cpuct nhưng chọn nước theo kiểu cũ (lấy mẫu
# 32 nước đầu rồi chọn nước nhiều lượt nhất, đọc --temp-cutoff), nên phải kiểm trước: binary mới in dòng "[arena] search: PUCT".
co_arena_hang = b"[arena] search: PUCT" in _bin
del _bin
print("FZ_ARENA_DUNG_MEM=" + ("co" if co_dung_mem else "khong"))
print("FZ_ARENA_THE_NGAU_NHIEN=" + ("co" if co_the_arena else "khong"))
print("FZ_ARENA_TIM_KIEM_HANG=" + ("co" if co_arena_hang else "khong"))

# Thế khởi đầu NGẪU NHIÊN như ô 04 (2026-11-20, chủ dự án chọn): mỗi CẶP ván (ván chẵn A cầm Trắng, ván lẻ A cầm
# Đen) chơi cùng một thế, nên mỗi thế được chơi với cả hai màu -- hai bên của một thế ngẫu nhiên không đối xứng.
# Cần (GAMES + 1) // 2 thế; hạt giống ngẫu nhiên mỗi lần chạy (mỗi máy một tệp khác nhau). Binary cũ không có
# --start-fen cho arena: ô sẽ báo lỗi "unknown flag" -> lấy binary mới (ô 02).
BOOK = f"/content/the_khoi_dau_arena_gen{GEN_CURRENT}.txt"
N_THE = (GAMES + 1) // 2
if not _thieu and co_the_arena:
    !python {E}/python/sinh_the_khoi_dau.py --n {N_THE} --out {BOOK}
    if not os.path.exists(BOOK) or os.path.getsize(BOOK) == 0:
        raise SystemExit(f"[!] Không sinh được {BOOK} (python/sinh_the_khoi_dau.py lỗi) -- dừng, không chạy arena.")

cmd = f"""bash {E}/run.sh --arena \
    --model-a {A_ONNX} \
    --model-b {B_ONNX} \
    --games {GAMES} --visits 400 --temperature 0.5 --cpuct 1.25 --start-fen {BOOK} \
    --provider cuda --fixed-batch 32 --max-moves 400 --show-nps \
    --search-opt max-prefetch=0 --parallel {PARALLEL} --batch-aggregate \
    --search-opt minibatch-size=32 --search-opt task-workers=0"""
if co_dung_mem:
    cmd += f" --stop-file {DUNG_MEM}" + (f" --max-seconds {SECS}" if SECS > 0 else "")

if not co_the_arena:
    print("[!] Binary chưa hỗ trợ --start-fen cho arena (bản cũ, sẽ chơi từ thế cố định mà không báo) -- "
          "lấy binary mới ở ô 02 / Release v3.0.0 -- không chạy arena")
elif not co_arena_hang:
    print("[!] Binary chưa có arena tìm kiếm hằng (nhiệt độ 0,5 cả ván, c_puct 1,25: bản cũ chỉ lấy mẫu 32 nước đầu rồi chọn "
          "nước nhiều lượt nhất) -- lấy binary mới ở ô 02 / Release v3.0.0 -- không chạy arena")
elif _thieu:
    print(f"[!] Thiếu mạng {_thieu} (không tải / chuyển được từ Release NN_Model) -- không chạy arena")
else:
    print(cmd)
    !{cmd}
