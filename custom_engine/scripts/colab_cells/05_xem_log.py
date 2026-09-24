# Tình trạng ô chạy nền gần nhất
# fz: nhanh
# In ô chạy nền gần nhất (menu ghi ở /content/fz_log/dang_chay) còn chạy hay đã xong, và
# SO_DONG dòng cuối log của nó. Xem log TRỰC TIẾP thì dùng menu fz, mục "l".
SO_DONG = 15

import glob, os, subprocess, time

D = "/content/fz_log"
try:
    o, pid = open(f"{D}/dang_chay").read().split()
except (FileNotFoundError, ValueError):
    o = pid = None

if o is None:
    print("(chưa có ô nào chạy nền trên máy này)")
else:
    log = f"{D}/{o}.log"
    trang_thai = "DANG CHAY" if os.path.exists(f"/proc/{pid}") else "DA XONG"
    phut = (time.time() - os.path.getmtime(log)) / 60 if os.path.exists(log) else 0
    print(f"[{trang_thai}: ô {o}]  {time.strftime('%H:%M:%S')}  (log ghi lần cuối {phut:.0f} phút trước)")
    print(subprocess.run(f"tail -n {SO_DONG} {log}", shell=True, capture_output=True, text=True).stdout)
if os.path.isdir(OUT_GAMES_DIR):
    print(f"[so tep van gen{GEN_CURRENT}] {len(glob.glob(OUT_GAMES_DIR + '/*'))}")
print("[GPU] " + subprocess.run("nvidia-smi --query-gpu=name,utilization.gpu,memory.used --format=csv,noheader",
                                shell=True, capture_output=True, text=True).stdout.strip())
