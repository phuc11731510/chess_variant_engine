# Dừng NGAY ô đang chạy nền
# fz: nhanh
# Dừng ô chạy nền gần nhất (vd lỡ sai tham số) cùng mọi tiến trình con của nó (engine, train.py).
# Selfplay dừng giữa chừng: các ván ĐÃ XONG vẫn còn trong thư mục ván; ván đang dở bị mất.
import os, signal, subprocess, time

try:
    o, pid = open("/content/fz_log/dang_chay").read().split()
    # Menu khởi động mỗi ô trong một nhóm tiến trình riêng: giết cả nhóm.
    os.killpg(int(pid), signal.SIGTERM)
    time.sleep(2)
    if os.path.exists(f"/proc/{pid}"):
        os.killpg(int(pid), signal.SIGKILL)
    print(f"[da dung o {o}]")
except (FileNotFoundError, ValueError):
    print("(chưa có ô nào chạy nền)")
except ProcessLookupError:
    print(f"[o {o} da xong tu truoc]")
# Phòng khi có tiến trình chạy ngoài menu (vd colab_termux.sh).
subprocess.run("pkill -f '[c]ustom_engine.* --(selfplay|arena)' ; pkill -f '[t]rain\\.py '", shell=True)
