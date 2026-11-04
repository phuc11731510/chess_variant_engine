"""Arena trên Colab cho ô 08 của `cv`: mạng A đấu mạng B bằng việc "A" của `lc0 treeplay`, dừng mềm như arena của fz.

Mỗi ván là "A <id> <temp_plies> <a_trang>": id chẵn thì A cầm Trắng, id lẻ thì B cầm Trắng, nên hai bên đổi màu đều
(như arena của engine biến thể). Không có nhiễu Dirichlet (engine tắt cho việc A); temperature 1 trong --temp-plies
nửa nước đầu để các ván khác nhau. Ba cách dừng MỀM (thôi nạp ván, ván dở chơi nốt): tệp --tep-dung, hết --max-giay,
hoặc đã nạp đủ --giao ván (như --games: máy không bao giờ chơi quá số ván được giao).

In ra màn hình (vòng lặp của `cv` đọc qua log của ô):
  === ARENA: A=<mạng A>  vs  B=<mạng B>
  [arena] <xong>/<giao> van, dang choi <d>: A thang <w>, hoa <h>, thua <l>   (mỗi 15 giây)
  FZ_ARENA W=<w> D=<h> L=<l> N=<n>    (cuối cùng; W = A thắng)
Thư mục (--thu-muc): arena.bin (bản ghi treeplay của mọi ván, giữ làm minh chứng), arena.bin.gz khi kết thúc,
engine_ra.log, engine_loi.log, arena.log, ket_qua.json.
"""
import argparse
import gzip
import json
import os
import shutil
import subprocess
import threading
import time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lc0", default="/content/cv/lc0")
    ap.add_argument("--a", required=True, help="mạng A (.pb.gz)")
    ap.add_argument("--b", required=True, help="mạng B (.pb.gz)")
    ap.add_argument("--thu-muc", required=True)
    ap.add_argument("--song-song", type=int, default=128)
    ap.add_argument("--visits", type=int, default=400)
    ap.add_argument("--temp-plies", type=int, default=30)
    ap.add_argument("--max-ply", type=int, default=450)
    ap.add_argument("--giao", type=int, required=True, help="số ván được giao")
    ap.add_argument("--max-giay", type=int, default=0)
    ap.add_argument("--tep-dung", default="")
    ap.add_argument("--backend", default="multiplexing", help="(thử trên máy tính: random)")
    ap.add_argument("--backend-opts", default="backend=onnx-cuda,threads=1,max_batch=1024")
    a = ap.parse_args()
    os.makedirs(a.thu_muc, exist_ok=True)
    tm = lambda t: os.path.join(a.thu_muc, t)
    if a.tep_dung and os.path.exists(a.tep_dung):
        os.remove(a.tep_dung)
    nhat_ky = open(tm("arena.log"), "a", buffering=1)

    def log(s):
        nhat_ky.write(time.strftime("%Y-%m-%d %H:%M:%S ") + s + "\n")
        print("[arena] " + s, flush=True)

    print(f"=== ARENA: A={a.a}  vs  B={a.b}", flush=True)
    log("bat dau: " + json.dumps(vars(a), ensure_ascii=False))
    # Như sinh.py: cùng tham số search (cpuct 1,3, FPU 0, không prefetch); mỗi mạng một backend + cache riêng.
    lenh = [a.lc0, "treeplay", f"--weights={a.a}", f"--weights2={a.b}", f"--backend={a.backend}",
            f"--backend-opts={a.backend_opts}", f"--parallelism={a.song_song}",
            f"--visits={a.visits}", f"--max-ply={a.max_ply}", "--report-seconds=60", f"--output={tm('arena.bin')}"]
    log("lenh: " + " ".join(lenh))
    p = subprocess.Popen(lenh, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=open(tm("engine_loi.log"), "a"),
                         text=True, bufsize=1)
    ra = open(tm("engine_ra.log"), "a", buffering=1)
    t = {"nap": 0, "xong": 0, "loi": 0, "w": 0, "d": 0, "l": 0, "evals": 0, "dang_dung": False, "ly_do": ""}
    khoa = threading.Lock()
    het = threading.Event()

    def doc_ra():
        for dong in p.stdout:
            ra.write(dong)
            phan = dong.split()
            with khoa:
                if len(phan) >= 4 and phan[0] == "XONG":
                    kq = int(phan[3]) * (1 if int(phan[1]) % 2 == 0 else -1)   # góc nhìn của A
                    t["w" if kq > 0 else "l" if kq < 0 else "d"] += 1
                    t["xong"] += 1
                    t["evals"] = int(phan[2])
                elif phan and phan[0] == "LOI":
                    t["loi"] += 1
                elif phan and phan[0] == "HET":
                    t["evals"] = int(phan[1])
        het.set()

    threading.Thread(target=doc_ra, daemon=True).start()
    bat_dau, lan_in = time.time(), 0.0
    while not het.is_set():
        with khoa:
            dang = t["nap"] - t["xong"] - t["loi"]
            if not t["dang_dung"]:
                ly_do = ("tep dung" if a.tep_dung and os.path.exists(a.tep_dung) else
                         "het --max-giay" if a.max_giay and time.time() - bat_dau >= a.max_giay else
                         "du so van giao" if t["nap"] >= a.giao else "")
                if ly_do:
                    t["dang_dung"], t["ly_do"] = True, ly_do
        if t["dang_dung"] and not p.stdin.closed:
            log(f"dung mem: {t['ly_do']}; {dang} van dang do se choi not")
            p.stdin.close()
        if not t["dang_dung"]:
            for _ in range(max(0, min(a.song_song + 4 - dang, a.giao - t["nap"]))):
                p.stdin.write(f"A {t['nap']} {a.temp_plies} {1 if t['nap'] % 2 == 0 else 0}\n")
                t["nap"] += 1
            p.stdin.flush()
        if time.time() - lan_in >= 15:
            with khoa:
                print(f"[arena] {t['xong']}/{a.giao} van, dang choi {t['nap'] - t['xong'] - t['loi']}: "
                      f"A thang {t['w']}, hoa {t['d']}, thua {t['l']}", flush=True)
            lan_in = time.time()
        time.sleep(1)
    p.wait()
    with open(tm("arena.bin"), "rb") as f_vao, gzip.open(tm("arena.bin.gz.tam"), "wb") as f_ra:
        shutil.copyfileobj(f_vao, f_ra)
    os.replace(tm("arena.bin.gz.tam"), tm("arena.bin.gz"))
    os.remove(tm("arena.bin"))
    kq = dict(t, giay=round(time.time() - bat_dau, 1), ma_thoat_engine=p.returncode, cau_hinh=vars(a))
    with open(tm("ket_qua.json"), "w") as f:
        json.dump(kq, f, ensure_ascii=False)
    log("ket thuc: " + json.dumps(kq, ensure_ascii=False))
    print(f"FZ_ARENA W={t['w']} D={t['d']} L={t['l']} N={t['xong']}", flush=True)


if __name__ == "__main__":
    main()
