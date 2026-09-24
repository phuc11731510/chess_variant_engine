# Tình trạng ô chạy nền gần nhất
# fz: nhanh
# In ô chạy nền gần nhất đang CHẠY, đã XONG (kèm mã thoát) hay bị DỪNG giữa chừng, và SO_DONG
# dòng cuối log của nó. Trạng thái lấy từ trang_thai() trong /content/fz_log/fz_may.py
# (tệp .rc mã thoát + PID + dòng lệnh -- xem đầu tệp fz_may.py). Log TRỰC TIẾP: menu fz, mục "l".
SO_DONG = 15

import glob, os, subprocess, time

M = "/content/fz_log/fz_may.py"
if not os.path.exists(M):
    print("(chưa có ô nào chạy nền trên máy này)")
else:
    g = {"__name__": "fz_may"}
    exec(open(M).read(), g)
    o, pid = g["o_gan_nhat"]()
    if o is None:
        print("(chưa có ô nào chạy nền trên máy này)")
    else:
        tt, rc = g["trang_thai"](o, pid)
        nhan = {"chay": "DANG CHAY", "xong": f"DA XONG, ma thoat {rc}", "dung": "BI DUNG giua chung"}[tt]
        log = f"/content/fz_log/{o}.log"
        phut = (time.time() - os.path.getmtime(log)) / 60 if os.path.exists(log) else 0
        print(f"[{nhan}: ô {o}]  {time.strftime('%H:%M:%S')}  (log ghi lần cuối {phut:.0f} phút trước)")
        print(subprocess.run(f"tail -n {SO_DONG} {log}", shell=True, capture_output=True, text=True).stdout)
if os.path.isdir(OUT_GAMES_DIR):
    print(f"[so tep van gen{GEN_CURRENT}] {len(glob.glob(OUT_GAMES_DIR + '/*'))}")
print("[GPU] " + subprocess.run("nvidia-smi --query-gpu=name,utilization.gpu,memory.used --format=csv,noheader",
                                shell=True, capture_output=True, text=True).stdout.strip())
