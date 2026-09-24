# Dừng NGAY ô đang chạy nền
# fz: nhanh
# Dừng ô chạy nền gần nhất (vd lỡ sai tham số) cùng mọi tiến trình con của nó (engine, train.py):
# dung_o() trong /content/fz_log/fz_may.py -- chỉ giết khi chắc chắn đúng tiến trình của ô đó.
# Selfplay dừng giữa chừng: các ván ĐÃ XONG vẫn còn trong thư mục ván; ván đang dở bị mất.
import os, subprocess

M = "/content/fz_log/fz_may.py"
if os.path.exists(M):
    g = {"__name__": "fz_may"}
    exec(open(M).read(), g)
    g["dung_o"]()
else:
    print("(chưa có ô nào chạy nền)")
# Phòng khi có engine / train.py chạy ngoài menu (vd colab_termux.sh).
_ = subprocess.run("pkill -f '[c]ustom_engine.* --(selfplay|arena)' ; pkill -f '[t]rain\\.py '", shell=True)
