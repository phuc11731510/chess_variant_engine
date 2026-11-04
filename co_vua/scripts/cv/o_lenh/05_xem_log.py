# Tình trạng ô chạy nền gần nhất
# cv: nhanh
# Chép theo ô 05 của fz: ô chạy nền gần nhất đang CHẠY, đã XONG (kèm mã thoát) hay bị DỪNG giữa chừng, và SO_DONG
# dòng cuối log của nó. Trạng thái lấy từ trang_thai() trong /content/fz_log/fz_may.py. Log TRỰC TIẾP: menu cv, mục "l".
SO_DONG = 15

import glob, json, os, subprocess, time

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
# Các lần sinh của đời này trên máy: số ván, số lần chạy mạng (đang chạy: tien_do.json; xong: xong.json).
for d in sorted(glob.glob(OUT_GAMES_DIR + "/lan_*")):
    for t in ("xong.json", "tien_do.json"):
        if os.path.exists(f"{d}/{t}"):
            j = json.load(open(f"{d}/{t}"))
            print(f"[{BEN} gen{GEN_CURRENT} {os.path.basename(d)}] {'xong' if t == 'xong.json' else 'đang chạy'}: "
                  f"{j.get('van_xong', 0)} ván, {j.get('evals', 0):,} lần chạy mạng")
            break
print("[GPU] " + subprocess.run("nvidia-smi --query-gpu=name,utilization.gpu,memory.used --format=csv,noheader",
                                shell=True, capture_output=True, text=True).stdout.strip())
