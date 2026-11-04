# Dừng NGAY ô đang chạy nền
# cv: nhanh
# Chép theo ô 09 của fz: dừng ô chạy nền gần nhất (vd lỡ sai tham số) cùng mọi tiến trình con của nó (sinh.py, lc0,
# huấn luyện): dung_o() trong /content/fz_log/fz_may.py -- chỉ giết khi chắc chắn đúng tiến trình của ô đó.
# Sinh dữ liệu dừng giữa chừng: lần sinh đó không có xong.json nên ô 06 không gom; dùng dừng MỀM (09b) để giữ ván.
import os, subprocess

M = "/content/fz_log/fz_may.py"
if os.path.exists(M):
    g = {"__name__": "fz_may"}
    exec(open(M).read(), g)
    g["dung_o"]()
else:
    print("(chưa có ô nào chạy nền)")
# Phòng khi có tiến trình chạy ngoài menu.
_ = subprocess.run("pkill -f '[s]inh\\.py ' ; pkill -f '[l]c0 treeplay' ; pkill -f '[l]c0 selfplay' ; "
                   "pkill -f '[h]uan_luyen\\.py '", shell=True)
