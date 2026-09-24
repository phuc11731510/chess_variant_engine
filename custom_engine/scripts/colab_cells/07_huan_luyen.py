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

CHAY_NEN = True   # False = chờ đến khi xong như ô sổ tay (10-40 phút)

print(cmd)
if CHAY_NEN:
    !nohup {cmd} > /content/train.log 2>&1 &
    print('[da chay nen] xem: menu fz -> l (log truc tiep) hoac o 05')
else:
    !{cmd}
    !ls -la {NEXT_ONNX} {NEXT_PT}
print("Xong thi tai ve dien thoai (chay trong Termux):")
print(f"  colab download -s fz {NEXT_ONNX} ~/storage/downloads/FairyZero/gen{GEN_NEXT}.onnx")
print(f"  colab download -s fz {NEXT_PT} ~/storage/downloads/FairyZero/gen{GEN_NEXT}.pt")
