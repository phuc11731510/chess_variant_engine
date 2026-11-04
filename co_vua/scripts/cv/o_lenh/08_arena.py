# Arena: mạng của hai cách học (cùng đời) đấu nhau
# Chép theo ô 08 của fz, nhưng hai bên là HAI CÁCH HỌC ở cùng một đời (cùng lượng tính toán), không phải hai đời của
# một cách: mặc định A = truyền thống (tt), B = cây trò chơi (cay), đời GEN_CURRENT. Kết quả "A thắng" = tt thắng.
# Chủ dự án chốt (2026-11-04): 1000 ván, 400 lượt thăm mỗi nước (như arena của fz). 1000 ván: sai số 95% của tỉ lệ
# điểm khoảng +-3,1 điểm phần trăm, tức khoảng +-22 Elo quanh mức ngang nhau.
# Hai bên đổi màu mỗi ván; không nhiễu Dirichlet; temperature 1 trong 30 nửa nước đầu (để các ván khác nhau); cùng
# tham số search như ô 04 (cpuct 1,3, FPU 0, không prefetch); ván dừng ở nửa nước 450 (hoà).
# Vòng lặp tự động (menu v) tự ghi A_PB, B_PB, GAMES, SECS dưới đây vào bản chép của ô này.
# cv: hoi GAMES Số ván arena (hai bên đổi màu mỗi ván)
GAMES = 1000
PARALLEL = 128      # số ván cùng lúc (menu v đọc số này để tính đuôi ván)
SECS = 0            # > 0: dừng MỀM sau chừng này giây (ván dở chơi nốt); 0 = không giới hạn
A_PB = f"/content/tt_gen{GEN_CURRENT}.pb.gz"    # mạng A (kết quả "A thắng" = A thắng)
B_PB = f"/content/cay_gen{GEN_CURRENT}.pb.gz"   # mạng B

# Mạng của hai bên: máy chưa có thì lấy từ Release co_vua_mang (đời cũ: py/lay_mang.py chuyển từ .pt ngay trên máy).
import os, time
for _f in (A_PB, B_PB):
    if not (os.path.exists(_f) and os.path.getsize(_f) > 0):
        !python3 {CV}/py/lay_mang.py pb {_f} --rel {REL_NN}
_thieu = [_f for _f in (A_PB, B_PB) if not (os.path.exists(_f) and os.path.getsize(_f) > 0)]

# Dừng MỀM theo lệnh (như ô 04): có tệp DUNG_MEM thì không nhận ván mới, ván đang chơi chơi nốt.
DUNG_MEM = "/content/fz_log/dung_mem"
if os.path.exists(DUNG_MEM):
    os.remove(DUNG_MEM)
_ten = os.path.basename(A_PB).split(".")[0] + "_vs_" + os.path.basename(B_PB).split(".")[0]
LAN = f"/content/arena/{_ten}/" + time.strftime("lan_%Y%m%d_%H%M%S")
cmd = f"""python3 {CV}/colab/arena.py --lc0 {CV}/lc0 --a {A_PB} --b {B_PB} --thu-muc {LAN} \
    --song-song {PARALLEL} --visits 400 --temp-plies 30 --max-ply 450 \
    --giao {GAMES} --max-giay {SECS} --tep-dung {DUNG_MEM}"""

if _thieu:
    print(f"[!] Thiếu mạng {_thieu} (không tải / chuyển được từ Release co_vua_mang) -- không chạy arena")
else:
    print(cmd)
    !{cmd}
    # Bản ghi mọi ván arena: về điện thoại làm minh chứng (Download/CoVua/arena/).
    _gz = f"/content/arena_{_ten}_{os.path.basename(LAN)}.bin.gz"
    if os.path.exists(f"{LAN}/arena.bin.gz"):
        !cp {LAN}/arena.bin.gz {_gz} && cp {LAN}/ket_qua.json {_gz[:-len('.bin.gz')]}.json
        print(f"FZ_TAI_VE={_gz}")
        print(f"FZ_TAI_VE={_gz[:-len('.bin.gz')]}.json")
