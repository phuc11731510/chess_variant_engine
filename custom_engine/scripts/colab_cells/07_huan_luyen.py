# Huấn luyện đời sau (mục 5)
# Mục 5 của sổ tay: huấn luyện đời sau, warm-start từ .pt đời hiện tại. Sửa tham số dưới đây.
# Cửa sổ trượt nhiều đời: DATA = "/content/games_gen0.zip,/content/games_gen1.zip"
# (các zip cũ phải có trên máy: colab upload ... từ Termux).
DATA = ZIP_GAMES

cmd = f"""python {E}/python/train.py \
    --data "{DATA}" --init-from {CURRENT_PT} \
    --epochs 2 --batch 1024 --lr 1e-3 --amp \
    --q-ratio 0.2 --weight-decay 1e-4 --report-every 20 \
    --channels 144 --blocks 12 \
    --out {NEXT_ONNX}"""

print(cmd)
!{cmd}
import os
if _exit_code == 0 and os.path.exists(NEXT_ONNX) and os.path.exists(NEXT_PT):
    !ls -la {NEXT_ONNX} {NEXT_PT}
    # Menu fz đọc các dòng FZ_TAI_VE=: tải mạng đời mới về Download/FairyZero khi ô xong
    # (đã có tệp cùng tên -> "gen1 (2).onnx", không ghi đè).
    print(f"FZ_TAI_VE={NEXT_ONNX}")
    print(f"FZ_TAI_VE={NEXT_PT}")
else:
    print("[!] Huấn luyện lỗi -- không tải về")
