# Huấn luyện đời sau (mục 5)
# Mục 5 của sổ tay: huấn luyện đời sau, warm-start từ .pt đời hiện tại. Sửa tham số dưới đây.
# Cửa sổ trượt nhiều đời: DATA = "/content/games_gen0.zip,/content/games_gen1.zip"
# (các zip cũ phải có trên máy: colab upload ... từ Termux).
DATA = ZIP_GAMES
import os
if not os.path.exists(CURRENT_PT):
    print(f"[!] Chưa có {CURRENT_PT} -- chạy ô 02c trước (tải .pt + thư viện huấn luyện)")

# Cửa sổ 4 đời (vòng lặp v gộp đời hiện tại + 3 đời trước), 1 epoch, tốc độ học không đổi.
# SWA "đuôi" (chủ dự án chọn, 2026-11-20): chụp trọng số ở BƯỚC HỌC CUỐI CÙNG rồi lùi mỗi 20 bước, tối
# đa 10 lần (cửa sổ 4 đời ~586 bước: các bước 406, 426, ..., 586), lấy trung bình với trọng số bằng
# nhau. Không chụp trước bước 1: lần học quá ngắn để đủ 10 lần thì chụp ít hơn (đời 0, 146 bước: 8 lần).
# --val-frac 0: không giữ ván nào ra ngoài. Không còn chấm mạng cũ trên đời mới nhất (bỏ --val-newest-gen
# 2026-11-20 để bớt ~1,5 phút mỗi đời; cờ vẫn còn trong train.py). Mạnh/yếu của mạng: arena.
cmd = f"""python {E}/python/train.py \
    --data "{DATA}" --init-from {CURRENT_PT} \
    --epochs 1 --swa-tail 10 --swa-tail-every 20 --val-frac 0 --batch 512 --accum-steps 2 --lr 1e-3 \
    --q-ratio 0.25 --weight-decay 1e-4 --report-every 20 \
    --out {NEXT_ONNX}"""

print(cmd)
!{cmd}
import os
if _exit_code == 0 and os.path.exists(NEXT_ONNX) and os.path.exists(NEXT_PT):
    !ls -la {NEXT_ONNX} {NEXT_PT}
    # Menu fz đọc các dòng FZ_TAI_VE=: tải mạng đời mới về Download/FairyZero khi ô xong
    # (đã có tệp cùng tên -> "gen1 (2).pt", không ghi đè). CHỈ .pt (2026-11-20): Release không giữ .onnx, mỗi
    # máy Colab chuyển .pt -> .onnx tại chỗ (python/lay_mang.py); nên điện thoại chỉ tải về và tải lên ~19 MB.
    print(f"FZ_TAI_VE={NEXT_PT}")
else:
    print("[!] Huấn luyện lỗi -- không tải về")
