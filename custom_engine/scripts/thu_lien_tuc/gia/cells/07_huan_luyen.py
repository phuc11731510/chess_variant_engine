# Huấn luyện GIẢ: đọc DATA (danh sách gói do vòng lặp ghi), đếm ván, ghi mạng đời sau
import os, time, zipfile
DATA = ZIP_GAMES
t0 = time.time()
n = 0
thieu = [p for p in DATA.split(",") if not os.path.exists(p)]
if thieu:
    raise SystemExit(f"[!] thiếu gói: {thieu}")
for p in DATA.split(","):
    n += len(zipfile.ZipFile(p).namelist())
print(f"[07 giả] {len(DATA.split(','))} gói, {n} ván; đời {GEN_CURRENT} -> {GEN_NEXT}")
with open("/tmp/fc/train.log", "a") as f:
    f.write(f"bat_dau {os.path.basename(os.environ.get('HOME', '?'))} {GEN_NEXT} {time.time():.2f} {len(DATA.split(','))} {n}\n")
time.sleep(float(os.environ.get("FAKE_TRAIN_S", "4")))
open(NEXT_PT, "wb").write(os.urandom(64))
open(NEXT_NET, "wb").write(os.urandom(64))
with open("/tmp/fc/train.log", "a") as f:
    f.write(f"xong {os.path.basename(os.environ.get('HOME', '?'))} {GEN_NEXT} {time.time():.2f}\n")
print(f"FZ_TAI_VE={NEXT_PT}")
