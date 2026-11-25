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
# --val-frac 0: không giữ ván nào ra ngoài. --val-newest-games 1000 (chủ dự án chọn 2026-11-26, thay cho --val-newest-gen đã bỏ
# 2026-11-20 vì tốn ~1,5 phút mỗi đời): chấm mạng KHỞI ĐẦU một lần trên 1000 ván mới nhất (theo giờ tệp trong gói zip, cỡ các ván chơi từ
# lúc mạng đó bắt đầu học lần trước), in CE chính sách / giá trị / số nước còn lại và số giây đã tốn (dòng "[val] start weights ..."), rồi
# vẫn học trên TẤT CẢ ván như thường: KHÔNG ván nào bị giữ ra khỏi bước học. train.py cũ trên máy (chưa có cờ) -> bỏ qua việc chấm.
# 2026-11-26 (chủ dự án): tốc độ học 1e-3 -> 5e-4 hằng số, khởi động tuyến tính 50 bước tối ưu (từ lr/50 = 1e-5 tới 5e-4; dòng
# "[train] lr warmup ..." in lịch thật), q_ratio 0,25 -> 0,2. Chuỗi CE giá trị đổi cách tính từ đời đổi (nhãn khác), không so thẳng trước/sau.
# (Trước đó:) Không còn chấm mạng cũ trên đời mới nhất (bỏ --val-newest-gen
# 2026-11-20 để bớt ~1,5 phút mỗi đời; cờ vẫn còn trong train.py). Mạnh/yếu của mạng: arena.
# --stats-newest-gen: trước khi học, in hai số thống kê của đời mới nhất (thư mục games_gen<g> số lớn nhất, ván của
# mọi máy): số quân còn lại trung bình lúc ván kết thúc, và tỉ lệ bên công nhiều hơn thắng (dòng "[stats] ...").
# Tính từ bản ghi, chỉ đọc; lỗi chỉ in cảnh báo, không dừng việc học.
# FP16 (chủ dự án quyết định 2026-11-20, theo cách truyền thống): --amp = huấn luyện hỗn hợp: trọng số gốc + optimizer FP32,
# nhân ma trận FP16 (autocast), softmax / layer norm / ba hàm mất mát FP32, nhân tỉ lệ loss động (GradScaler), --grad-clip 10 cắt
# gradient SAU khi bỏ tỉ lệ, bước có gradient vô cực/NaN bị bỏ và đếm (dòng "[amp] ..."; 16 bước liền như vậy thì dừng, không xuất mạng).
# --onnx-fp16 = .onnx cho engine ở FP16, chỉ dùng sau khi kiểm trên GPU là ra gần như số FP32 (lệch thì giữ FP32 và nói lý do).
# Kiểu mạng "fzw" (2026-11-22, bộ chạy CUDA riêng của engine; NET_EXT ở ô 00 / 02): train.py ghi CHỈ .pt (--out gen<N>.pt, không xuất ONNX, nên
# máy huấn luyện không cần pip onnx / onnxscript / onnxruntime-gpu), rồi python/lay_mang.py fzw chuyển .pt -> .fzw ngay ở dưới (kiểm an toàn
# với mạng FP32 như đã nói; lệch / NaN thì KHÔNG ghi .fzw và ô báo lỗi, không tải mạng về). Kiểu "onnx": như trước.
if NET_EXT == "fzw":
    _out, _onnx_opt = NEXT_PT, ""
else:
    _out, _onnx_opt = NEXT_NET, "--onnx-fp16"
# Cờ chấm CE ngoài mẫu chỉ có từ train.py mới (2026-11-26): máy Colab giữ bản mã cũ thì bỏ cờ, không để cả lượt học lỗi vì "unrecognized arguments".
try:
    _val = "--val-newest-games 1000" if "--val-newest-games" in open(f"{E}/python/train.py", encoding="utf-8").read() else ""
except OSError:
    _val = ""
if not _val:
    print("[!] train.py trên máy này chưa có --val-newest-games: lượt học này không chấm CE ngoài mẫu.")
cmd = f"""python {E}/python/train.py \
    --data "{DATA}" --init-from {CURRENT_PT} \
    --epochs 1 --swa-tail 10 --swa-tail-every 20 --val-frac 0 --stats-newest-gen {_val} --batch 512 --accum-steps 2 \
    --lr 5e-4 --warmup-steps 50 \
    --q-ratio 0.2 --weight-decay 1e-4 --report-every 20 --amp --grad-clip 10 {_onnx_opt} \
    --out {_out}"""

print(cmd)
!{cmd}
import os
_train_ok = _exit_code == 0 and os.path.exists(NEXT_PT)
if _train_ok and NET_EXT == "fzw":
    !python {E}/python/lay_mang.py fzw {NEXT_NET} --rel {REL_NN}
    _train_ok = _exit_code == 0 and os.path.exists(NEXT_NET)
elif _train_ok:
    _train_ok = os.path.exists(NEXT_NET)
if _train_ok:
    !ls -la {NEXT_NET} {NEXT_PT}
    # Menu fz đọc các dòng FZ_TAI_VE=: tải mạng đời mới về Download/FairyZero khi ô xong
    # (đã có tệp cùng tên -> "gen1 (2).pt", không ghi đè). CHỈ .pt (2026-11-20): Release không giữ .onnx / .fzw, mỗi
    # máy Colab chuyển .pt -> .fzw / .onnx tại chỗ (python/lay_mang.py); nên điện thoại chỉ tải về và tải lên ~19 MB.
    print(f"FZ_TAI_VE={NEXT_PT}")
else:
    print("[!] Huấn luyện lỗi -- không tải về")
