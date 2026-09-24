# Mục 3 của sổ tay: sinh dữ liệu huấn luyện. Sửa tham số ngay dưới đây.
# Cấu hình mặc định đã đo là tốt nhất trên T4: --fixed-batch 16, --parallel 4, không --batch-aggregate.
# --max-seconds dừng MỀM: ván đang chạy vẫn chơi nốt (vượt giờ ~2-3 phút).
SECS = 15480

cmd = f"""bash {E}/run.sh --selfplay \
    --games 1000 --max-seconds {SECS} \
    --visits 800 --max-moves 400 --temp-cutoff 32 \
    --parallel 4 --provider cuda --fixed-batch 16 \
    --noise-alpha 0.15 --show-nps --search-opt max-prefetch=0 \
    --weights {CURRENT_ONNX} --out {OUT_GAMES_DIR}"""

# CHAY_NEN = True: chạy nền trên máy Colab, lệnh trả về ngay, log ở /content/selfplay.log
#   (xem bằng ô 05). Mất sóng / đóng Termux thì engine VẪN chạy.
# CHAY_NEN = False: chạy như ô sổ tay, Termux chờ đến khi xong (~4,3 giờ) -- Termux mà bị
#   Android tắt giữa chừng thì không biết kết quả.
CHAY_NEN = True

print(cmd)
if CHAY_NEN:
    !nohup {cmd} > /content/selfplay.log 2>&1 &
    print("[da chay nen] xem: o 05")
else:
    !{cmd}
