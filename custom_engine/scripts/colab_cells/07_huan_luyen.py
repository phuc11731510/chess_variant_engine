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
# --stats-newest-gen: trước khi học, in hai số thống kê của đời mới nhất (thư mục games_gen<g> số lớn nhất, ván của
# mọi máy): số quân còn lại trung bình lúc ván kết thúc, và tỉ lệ bên công nhiều hơn thắng (dòng "[stats] ...").
# Tính từ bản ghi, chỉ đọc; lỗi chỉ in cảnh báo, không dừng việc học.
# FP16 (chủ dự án quyết định 2026-11-20, theo cách truyền thống): --amp = huấn luyện hỗn hợp: trọng số gốc + optimizer FP32,
# nhân ma trận FP16 (autocast), softmax / layer norm / ba hàm mất mát FP32, nhân tỉ lệ loss động (GradScaler), --grad-clip 10 cắt
# gradient SAU khi bỏ tỉ lệ, bước có gradient vô cực/NaN bị bỏ và đếm (dòng "[amp] ..."; 16 bước liền như vậy thì dừng, không xuất mạng).
# --onnx-fp16 = .onnx cho engine ở FP16, chỉ dùng sau khi kiểm trên GPU là ra gần như số FP32 (lệch thì giữ FP32 và nói lý do).
cmd = f"""python {E}/python/train.py \
    --data "{DATA}" --init-from {CURRENT_PT} \
    --epochs 1 --swa-tail 10 --swa-tail-every 20 --val-frac 0 --stats-newest-gen --batch 512 --accum-steps 2 --lr 1e-3 \
    --q-ratio 0.25 --weight-decay 1e-4 --report-every 20 --amp --grad-clip 10 --onnx-fp16 \
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
