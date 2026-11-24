# Khởi động GIẢ (bộ thử vòng lặp liên tục): dựng "máy Colab" giả trong /content của cửa sổ
# (lay_mang.py giả có chữ lay_mang để các kiểm tra của vòng lặp nhận ra ô mới)
import os, shutil
G = os.environ["FAKE_GIA"]; R = os.environ["FAKE_SRC"]
os.makedirs(E + "/build-linux", exist_ok=True)
os.makedirs(E + "/python", exist_ok=True)
open(E + "/build-linux/custom_engine", "wb").write(b"fake binary --stop-file FZ_ARENA --temp-elo-cutoff each played by a PAIR [arena] search: PUCT\n")
for f in ("run.sh", "fake_engine.py"):
    shutil.copy(G + "/may/" + f, E + "/" + f)
os.chmod(E + "/run.sh", 0o755)
for f in os.listdir(R + "/python"):
    d = E + "/python/" + f
    if f == "lay_mang.py" or os.path.exists(d) or os.path.isdir(R + "/python/" + f):
        continue
    os.symlink(R + "/python/" + f, d)
shutil.copy(G + "/may/lay_mang.py", E + "/python/lay_mang.py")
os.makedirs("/content/fz_log", exist_ok=True)
open(NET_FILE, "w").write("fzw")
for ext in ("fzw", "pt"):
    p = f"/content/gen{GEN_CURRENT}.{ext}"
    if not os.path.exists(p):
        open(p, "wb").write(os.urandom(64))
print("[02 giả] máy dựng xong")
print("FZ_NET=fzw")
