# Xem tiến độ việc chạy nền
# Tự nhận việc nào đang chạy (selfplay / train / arena) và hiện log của việc đó.
# Không còn việc nào chạy -> hiện log mới sửa gần nhất. Menu fz, mục "l", chạy ô này mỗi vài giây.
LOG = "tu_dong"   # hoặc "selfplay" / "train" / "arena" để xem cố định một log
SO_DONG = 15

import glob, os, subprocess, time

def sh(c):
    return subprocess.run(c, shell=True, capture_output=True, text=True).stdout.strip()

# Tiến trình đang chạy ([c]/[t] để pgrep không tự bắt chính dòng lệnh này).
ps = sh("pgrep -af '[c]ustom_engine|[t]rain\\.py'")
if "--selfplay" in ps:
    dang_chay = "selfplay"
elif "--arena" in ps:
    dang_chay = "arena"
elif "train.py" in ps:
    dang_chay = "train"
else:
    dang_chay = None

if LOG != "tu_dong":
    ten = LOG
elif dang_chay:
    ten = dang_chay
else:
    logs = glob.glob("/content/selfplay.log") + glob.glob("/content/train.log") + glob.glob("/content/arena.log")
    ten = os.path.basename(max(logs, key=os.path.getmtime))[:-4] if logs else None

if dang_chay:
    print(f"[DANG CHAY: {dang_chay}]  {time.strftime('%H:%M:%S')}")
else:
    print(f"[KHONG con tien trinh -- xong hoac loi]  {time.strftime('%H:%M:%S')}")

if ten is None:
    print("(chưa có log nào trong /content)")
else:
    f = f"/content/{ten}.log"
    phut = (time.time() - os.path.getmtime(f)) / 60 if os.path.exists(f) else 0
    print(f"--- {f}  (ghi lần cuối {phut:.0f} phút trước) ---")
    print(sh(f"tail -n {SO_DONG} {f}"))
    if ten == "selfplay":
        print(f"[so tep van] {len(glob.glob(OUT_GAMES_DIR + '/*'))}")
print("[GPU] " + sh("nvidia-smi --query-gpu=name,utilization.gpu,memory.used --format=csv,noheader"))
