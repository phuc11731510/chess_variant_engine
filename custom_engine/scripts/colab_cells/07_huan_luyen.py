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
# 2026-11-27 (chủ dự án): tốc độ học 5e-4 -> 1e-4 (khởi động 50 bước từ 2e-6). Mỗi đời mạng dịch ít hơn ~5 lần; weight decay 1e-2 của AdamW nhân
# với lr nên cũng nhỏ đi 5 lần (~0,08% mỗi đời thay vì ~0,4%).
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
# Máy Colab sống nhiều đời liền và chỉ lấy mã mới khi chạy lại ô 02: train.py chưa phải bản mới nhất (dấu hiệu: hàm grad_origin, 2026-11-28)
# -> lấy thư mục python/ của main MỘT lần ngay tại đây (chỉ python/, vài trăm KB; binary / run.sh không đụng). Lỗi mạng -> học bằng bản
# đang có, các cờ chưa có tự tắt bên dưới.
try:
    _cu = "def grad_origin" not in open(f"{E}/python/train.py", encoding="utf-8").read()
except OSError:
    _cu = False
if _cu:
    import subprocess as _sp
    _r = _sp.run(f"cd {E}/.. && timeout 90 git fetch -q --depth 1 origin main && git checkout -q FETCH_HEAD -- custom_engine/python",
                 shell=True)
    print("[07] train.py trên máy là bản cũ: đã lấy python/ của main" if _r.returncode == 0 else
          "[07] train.py trên máy là bản cũ, lấy python/ của main lỗi -- học bằng bản đang có")
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
# --value-per-game 21 (chủ dự án chọn 2026-11-26): mỗi lượt học, ở MỖI ván chỉ bốc ngẫu nhiên 21 thế để học giá trị (ván ít hơn 21 thế: mọi
# thế), bốc lại mỗi đời; phần giá trị của loss = trung bình trên các thế được bốc (chia cho số thế được bốc, nên cán cân giá trị / chính sách
# giữ như cũ). Chính sách (PCR, mặt nạ nước không hợp lệ) và số nước còn lại không đổi. Lý do: đầu giá trị học thuộc kết quả từng ván (thế khởi
# đầu ngẫu nhiên là "dấu vân tay" của ván): gen139 đoán đúng 100% ở nửa nước 1 của ván đã học, ~51% ván mới; thử T4 (scripts/thu_hoc_thuoc_t4.py,
# 16 thế/ván): CE giá trị ván mới 0,6946 -> 0,6499. Dòng "[val]" vẫn chấm mọi thế. train.py cũ (chưa có cờ) -> học như trước, in cảnh báo.
# --weight-decay 1e-2 (chủ dự án chọn 2026-11-26, mức mặc định của AdamW / thường dùng cho transformer; trước đây 1e-4 = hệ số L2 của lc0 dùng
# với SGD, sang AdamW gần như không tác dụng: lr 5e-4 x 1e-4 x ~780 bước ≈ 0,004% mỗi đời; nay ≈ 0,4% mỗi đời). Thử T4 1 đời: không đổi CE
# giá trị / chính sách, không hại.
try:
    _vpg ="--value-per-game 21" if "--value-per-game" in open(f"{E}/python/train.py", encoding="utf-8").read() else ""
except OSError:
    _vpg = ""
if not _vpg:
    print("[!] train.py trên máy này chưa có --value-per-game: lượt học này đầu giá trị học mọi thế như cũ.")
# --td-lambda 0.8 --td-z-weight 0.5 --mirror (chủ dự án chọn 2026-11-27):
#   * nhãn giá trị của thế học = 0,5 x kết quả ván + 0,5 x TD(0,8) trên điểm tìm kiếm của các thế phía sau (chủ yếu ~5 nửa nước tới), thay
#     qMix 0,2 (80% kết quả ván): phần kết quả ván ~50% ở mọi giai đoạn (~60% ở giai đoạn cuối), bớt phần may rủi mà dấu vết khởi đầu khai thác
#     để học thuộc ván. --q-ratio 0.2 vẫn ghi để dòng "[val]" chấm CE như các đời trước (so được);
#   * --mirror: mỗi thế học lật trái-phải (cột a<->j, chính sách sang nước đối xứng) xác suất 1/2 mỗi lần bốc (luật không nhập thành nên đối
#     xứng; kiểm bằng engine trên 3000 thế thật).
#   Thử T4 1 đời từ gen184 trên đúng cửa sổ gen185 (scratchpad thu_td_t4.py), 562 ván n185 chưa học: CE giá trị so với kết quả 0,6597 (như cũ)
#   -> 0,5866 (TD) -> 0,5740 (TD + lật); đoán đúng 66,9 -> 68,6%; |q - q lật| 0,449 -> 0,230; học thuộc ván học 1 lượt 94,5 -> 79,1%;
#   CE chính sách 3,0046 -> 3,0130 (lật làm kém một chút ở đời đầu). train.py cũ (chưa có cờ) -> học như trước, in cảnh báo.
try:
    _td = "--td-lambda 0.8 --td-z-weight 0.5 --mirror" if "--td-lambda" in open(f"{E}/python/train.py", encoding="utf-8").read() else ""
except OSError:
    _td = ""
if not _td:
    print("[!] train.py trên máy này chưa có --td-lambda / --mirror: lượt học này dùng nhãn qMix, không lật.")
# --surprise-policy-beta 0.5 --surprise-value-beta 0.25 (chủ dự án chọn 2026-11-28): hai trọng số RIÊNG nhân vào loss của mỗi thế học,
#   w = (1 - beta) + beta x min(S / S trung bình, 10), chia lại cho trung bình 1; trung bình và chuẩn hoá tính riêng cho TỪNG mạng đã chơi ván:
#   * loss chính sách (chỉ thế tìm đầy đủ): S = policy_kld (KL phân bố lượt thăm so với prior thô), beta 0,5 (như KataGo);
#   * loss giá trị (21 thế / ván): S = KL(lợi nhuận TD(0,8) || Thắng/Hoà/Thua thô của mạng đã chơi), beta 0,25.
#   Khảo sát cửa sổ n241-n245 (630.599 thế): dữ liệu hiệu dụng chính sách 81,4% (w lớn nhất 5,5), giá trị 84,8% (3,37). Dòng "[val]" vẫn
#   chấm KHÔNG trọng số (so được với các đời trước); loss in lúc học là loss có trọng số. Cần --td-lambda (nên đi cùng _td).
try:
    _sw = ("--surprise-policy-beta 0.5 --surprise-value-beta 0.25"
           if _td and "--surprise-value-beta" in open(f"{E}/python/train.py", encoding="utf-8").read() else "")
except OSError:
    _sw = ""
if not _sw:
    print("[!] train.py trên máy này chưa có --surprise-*-beta: lượt học này không dùng trọng số theo độ bất ngờ.")
cmd = f"""python {E}/python/train.py \
    --data "{DATA}" --init-from {CURRENT_PT} \
    --epochs 1 --swa-tail 10 --swa-tail-every 20 --val-frac 0 --stats-newest-gen {_val} --batch 512 --accum-steps 2 \
    --lr 1e-4 --warmup-steps 50 \
    --q-ratio 0.2 --weight-decay 1e-2 {_vpg} {_td} {_sw} --report-every 20 --amp --grad-clip 10 {_onnx_opt} \
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
