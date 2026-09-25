# Sinh dữ liệu (mục 3)
# Mục 3 của sổ tay: sinh dữ liệu huấn luyện. Sửa tham số ngay dưới đây.
# Cấu hình mặc định đã đo là tốt nhất trên T4: --fixed-batch 16, --parallel 4, không --batch-aggregate.
# --max-seconds dừng MỀM: ván đang chạy vẫn chơi nốt (vượt giờ ~2-3 phút).
# fz: che_do_sinh
# (dòng trên: menu fz hỏi chế độ khi chạy ô -- tối đa theo hạn mức T4 / tự chọn số ván / tự đặt cả
#  hai -- rồi GHI số đã chọn vào SECS, GAMES dưới đây; Enter = dùng số đang ghi.)
SECS = 15480
GAMES = 1000

cmd = f"""bash {E}/run.sh --selfplay \
    --games {GAMES} --max-seconds {SECS} \
    --visits 800 --max-moves 400 --temp-cutoff 32 \
    --parallel 4 --provider cuda --fixed-batch 16 \
    --noise-alpha 0.15 --show-nps --search-opt max-prefetch=0 \
    --weights {CURRENT_ONNX} --out {OUT_GAMES_DIR}"""

print(cmd)
!{cmd}
