# Sinh dữ liệu LIÊN TỤC (vòng lặp liên tục: mỗi lần chạy engine là một RUN, chạy song song được)
# Ô của VÒNG LẶP LIÊN TỤC (fz_lien_tuc.sh, menu fz -> w). Khác ô 04 ở chỗ nào:
#   - Không có "số ván mục tiêu của một đời": engine chơi MÃI (GAMES rất lớn) cho tới khi hết SECS (hạn mức T4) hoặc có tệp dừng
#     của RIÊNG lần chạy này. Dữ liệu được gom thành gói nhỏ và gửi về điện thoại trong lúc engine vẫn chạy (python/goi_van.py).
#   - Mỗi lần chạy có mã RUN riêng: thư mục ván /content/games_gen<NET_N>_<RUN>, tệp dừng /content/fz_log/dung_<RUN>, tệp thế khởi
#     đầu /content/the_khoi_dau_<RUN>.txt, ô trên máy tên "04_<RUN>" (fz_may.py cho phép nhiều ô 04_* chạy cùng lúc). Nhờ vậy khi mạng mới ra,
#     tiến trình MỚI (mạng mới) khởi động ngay trong lúc tiến trình CŨ chỉ chơi nốt các ván dở rồi thoát.
#   - Tệp dừng chung /content/fz_log/dung_mem (ô 09b) KHÔNG còn tác dụng với ô này, và ô này không xoá nó.
# Tham số do vòng lặp ghi vào ba dòng dưới đây (sed): SECS, RUN, NET_N. Tự chạy tay: để nguyên (RUN theo giờ, mạng = GEN_CURRENT của ô 00).
# Mọi thiết lập tìm kiếm / PCR / loại nước sai Elo / bộ chạy mạng giống hệt ô 04 (xem ô 04: đo đạc và lý do).
import os, time
SECS = 15480          # dừng MỀM sau chừng này giây (ván dở chơi nốt: vượt giờ ~1,5-3,5 phút)
RUN = time.strftime("%m%d%H%M%S")     # mã lần chạy, duy nhất trên một máy
NET_N = GEN_CURRENT   # đời mạng engine dùng (mạng gen<NET_N>.fzw / .onnx đã có trên máy: ô 02 / python/lay_mang.py)
GAMES = 1000000       # "mãi mãi": engine dừng vì SECS hoặc tệp dừng, không phải vì đủ ván
N_THE = 6000          # số dòng thế khởi đầu trong tệp, CHẴN (engine lấy dòng g % N_THE; một lần chạy dài ~1 giờ chơi ~600 ván nên không lặp)
PARALLEL = 16         # số ván chơi cùng lúc
ELO_CAT = 70.44       # loại khỏi lần bốc nước những nước kém nước nhiều lượt thăm nhất quá chừng này Elo (0 = không loại)

CURRENT_NET = f"/content/gen{NET_N}.{NET_EXT}"
OUT_GAMES_DIR = f"/content/games_gen{NET_N}_{RUN}"
DUNG_MEM = f"/content/fz_log/dung_{RUN}"
BOOK = f"/content/the_khoi_dau_{RUN}.txt"
if os.path.exists(DUNG_MEM):
    os.remove(DUNG_MEM)   # tệp của lần dừng trước cùng mã: để lại thì engine dừng ngay từ ván đầu
try:
    _bin = open(f"{E}/build-linux/custom_engine", "rb").read()
except OSError:          # chưa có binary (ô 02 lỗi?) -- lệnh dưới sẽ báo
    _bin = b""
co_dung_mem = b"--stop-file" in _bin
co_elo_cat = b"--temp-elo-cutoff" in _bin
co_phien_phu = b"--extra-batches" in _bin and NET_EXT == "onnx"
del _bin
print("FZ_RUN=" + RUN)
print("FZ_NET_N=" + str(NET_N))
print("FZ_PHIEN_PHU=" + ("co" if co_phien_phu else "khong"))
print("FZ_NET=" + NET_EXT)
if not (os.path.exists(CURRENT_NET) and os.path.getsize(CURRENT_NET) > 0):
    raise SystemExit(f"[!] Không có {CURRENT_NET} -- chạy ô 02 trước (tải gen{NET_N}.pt từ Release NN_Model và chuyển)")
if not co_dung_mem:
    raise SystemExit("[!] Binary chưa có --stop-file (bản cũ): vòng lặp liên tục cần dừng mềm. Chạy ô 02b, đưa binary mới lên Release.")
_provider = "fzcuda" if NET_EXT == "fzw" else "cuda"
print("FZ_DUNG_MEM=co")
print("FZ_ELO_CAT=" + (f"{ELO_CAT}" if co_elo_cat and ELO_CAT > 0 else "khong"))
if ELO_CAT > 0 and not co_elo_cat:
    print("[!] Binary chưa có --temp-elo-cutoff: sinh dữ liệu KHÔNG loại nước sai. Chạy ô 02 / đưa binary mới lên Release.")

# Tệp thế khởi đầu: thế ngẫu nhiên (python/sinh_the_khoi_dau.py, luật 2026-11-24), hạt giống ngẫu nhiên mỗi lần chạy.
# Cặp đổi màu (chủ dự án 2026-11-27): mỗi thế khởi đầu dùng cho HAI ván liền nhau, ván sau Trắng lấy cách xếp của Đen và
# ngược lại (sinh_the_khoi_dau.py --cap-doi-mau): dấu vết khởi đầu của một ván không còn gắn với đúng một kết quả, nên đầu
# giá trị không học thuộc được kết quả từng ván qua thế khởi đầu. Mã trên máy chưa có cờ thì sinh như cũ (không dừng ván).
_cap = " --cap-doi-mau" if "--cap-doi-mau" in open(f"{E}/python/sinh_the_khoi_dau.py", encoding="utf-8").read() else ""
if not _cap:
    print("[!] python/sinh_the_khoi_dau.py chưa có --cap-doi-mau: mỗi ván một thế khởi đầu như cũ.")
!python {E}/python/sinh_the_khoi_dau.py --n {N_THE} --out {BOOK}{_cap}
if not os.path.exists(BOOK) or os.path.getsize(BOOK) == 0:
    raise SystemExit(f"[!] Không sinh được {BOOK} (python/sinh_the_khoi_dau.py lỗi) -- dừng, không sinh ván.")

cmd = f"""bash {E}/run.sh --selfplay \
    --games {GAMES} --max-seconds {SECS} \
    --visits 800 --max-moves 400 --fast-visits 200 --fast-prob 0.5 --fast-cpuct 1.5 --fast-noise-eps 0 \
    --temperature 0.5 --start-fen {BOOK} \
    --parallel {PARALLEL} --provider {_provider} --fixed-batch 64 --batch-aggregate \
    --noise-alpha 0.15 --show-nps --search-opt max-prefetch=0 --search-opt minibatch-size=32 \
    --search-opt nn-cache-size=2000000 \
    --weights {CURRENT_NET} --out {OUT_GAMES_DIR} --stop-file {DUNG_MEM}""" \
    + (" --extra-batches 16,32,48" if co_phien_phu else "") \
    + (f" --temp-elo-cutoff {ELO_CAT}" if co_elo_cat and ELO_CAT > 0 else "")

print(cmd)
!{cmd}
