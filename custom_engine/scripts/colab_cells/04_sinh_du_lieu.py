# Sinh dữ liệu (mục 3)
# Mục 3 của sổ tay: sinh dữ liệu huấn luyện. Sửa tham số ngay dưới đây.
# Cấu hình mặc định đã đo là tốt nhất trên T4 (2026-09-28, gen9, 300 s mỗi cấu hình, so trên CÙNG máy):
# gom batch mạng của NHIỀU ván (--batch-aggregate), PARALLEL = 16 ván cùng lúc, --fixed-batch 64, mỗi
# ván gom 32 lá mỗi lượt (--search-opt minibatch-size=32, như lc0 self-play). Engine từ c1217ef dùng
# thông số self-play kiểu lc0 (cpuct cố định, fpu 0, không tính lặp 2 lần là hoà, task-workers 0).
#
# Luật mới (2026-11-20, chủ dự án chọn): tìm kiếm PUCT với PLAYOUT CAP RANDOMIZATION (PCR). Trước MỖI nước
# tung đồng xu 50/50: tìm đủ 800 lượt (c_puct 1,5, nhiễu Dirichlet eps 0,25) hoặc tìm nông 200 lượt
# (c_puct 1,25, eps 0,125); alpha 0,15 chung. Nước tìm nông ghi fast_search = 1: huấn luyện value + mlh,
# KHÔNG huấn luyện policy. Mỗi nước tạo cây mới (không tái dùng cây). Nước đi được chọn cho CẢ ván theo
# trọng số N^(1/T), T = 0,5 (--temperature; nhãn policy vẫn là tỷ lệ lượt thăm). Số lượt thăm là mức
# SÀN: một lượt tìm kiếm dừng sau lô lá cuối (tối đa +31 với minibatch-size=32), như lc0.
# Thế khởi đầu: MỖI VÁN một thế ngẫu nhiên (python/sinh_the_khoi_dau.py: Tốt và Sergeant cố định, 18 quân
# còn lại xếp ngẫu nhiên, an toàn hai nước), sinh mới ở mỗi lần chạy ô (hạt giống ngẫu nhiên nên các máy
# Colab khác nhau không trùng thế).
# Đo: cấu hình cũ (4 ván, batch 16) 2.766 nps -> 4.049 nps. 24/32 ván không hơn mà phần đuôi dừng mềm
# dài ra; va chạm 1/1 và tắt out-of-order-eval (như lc0) thì chậm hơn trên máy này -> giữ mặc định.
# Cache NN 2.000.000 mục (--search-opt nn-cache-size=2000000, như mặc định self-play của lc0; mặc định
# engine 65.536): đo T4 gen23 2026-10-03, ABAB 360 s: gửi NN 66% -> 61% lượt tìm, 3.944 -> 4.225 nps
# (+7%); RAM tiến trình ~4,2 GB / 12,9 GB của máy.
# Phiên phụ cỡ mẻ 16/32/48 (--extra-batches 16,32,48, engine từ fbaaffc 2026-10-04): mẻ ít thế chạy trên
# phiên nhỏ nhất vừa đủ thay vì điền 0 cho đủ 64. Đo T4 gen23 ABAB 360 s (cache 2M): 4.372 -> 4.634 nps
# khi 16 ván chạy (+6%), cả lần chạy 4.162 -> 4.522 (+8,6%), phí pad 10% -> 5%; kết quả NN lệch 0,000005.
# --max-seconds dừng MỀM: ván đang chạy vẫn chơi nốt (16 ván: vượt giờ ~3-4 phút). Menu fz tự trừ phần
# này khỏi SECS theo số đo các lần trước (đuôi ván, ~/.fz_tk/.duoi_van_luat_moi; từ 2026-11-20 tệp mới, số đo của
# mạng CNN cũ không dùng được cho transformer FP32 -- đuôi ván dài hơn ~2 lần, mặc định 16 ván = 20 phút).
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
    _bin = open(f"{E}/build-linux/custom_engine", "rb").read()
except OSError:          # chưa có binary (ô 02 lỗi?) -- lệnh dưới sẽ báo
    _bin = b""
co_dung_mem = b"--stop-file" in _bin
co_phien_phu = b"--extra-batches" in _bin   # binary cũ không có: chạy như trước (chỉ phiên 64)
del _bin
print("FZ_PHIEN_PHU=" + ("co" if co_phien_phu else "khong"))
print("FZ_DUNG_MEM=" + ("co" if co_dung_mem else "khong"))
if not co_dung_mem:
    print("[!] Binary chưa có --stop-file (bản cũ): không dừng mềm được. Chạy ô 02b, đưa binary mới lên Release.")

# Tệp thế khởi đầu: một dòng FEN mỗi ván (engine lấy dòng g % số dòng; GAMES dòng nên không lặp thế).
BOOK = f"/content/the_khoi_dau_gen{GEN_CURRENT}.txt"
!python {E}/python/sinh_the_khoi_dau.py --n {GAMES} --out {BOOK}
if not os.path.exists(BOOK) or os.path.getsize(BOOK) == 0:
    raise SystemExit(f"[!] Không sinh được {BOOK} (python/sinh_the_khoi_dau.py lỗi) -- dừng, không sinh ván.")

cmd = f"""bash {E}/run.sh --selfplay \
    --games {GAMES} --max-seconds {SECS} \
    --visits 800 --max-moves 400 --fast-visits 200 --fast-prob 0.5 --fast-cpuct 1.25 --fast-noise-eps 0.125 \
    --temperature 0.5 --start-fen {BOOK} \
    --parallel {PARALLEL} --provider cuda --fixed-batch 64 --batch-aggregate \
    --noise-alpha 0.15 --show-nps --search-opt max-prefetch=0 --search-opt minibatch-size=32 \
    --search-opt nn-cache-size=2000000 \
    --weights {CURRENT_ONNX} --out {OUT_GAMES_DIR}""" + (f" --stop-file {DUNG_MEM}" if co_dung_mem else "") \
    + (" --extra-batches 16,32,48" if co_phien_phu else "")

print(cmd)
!{cmd}
