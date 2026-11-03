"""Sinh ván trên Colab (chạy nền): nạp việc liên tục cho `lc0 treeplay`, ghi tiến độ ra tệp, dừng mềm khi được báo.

Cách truyền thống: mọi việc là "G <id> <temp_plies>" (ván từ thế khởi đầu). Bộ điều phối trên điện thoại đọc
tien_do.json qua SSH để cộng ngân sách, và tạo tệp `dung` khi tổng số lần chạy mạng đã đủ. Khi đó script
thôi nạp việc, đóng đầu vào của engine; engine chơi nốt các ván đang dở rồi thoát (không mất ván nào).

Thư mục của một lần chạy (--thu-muc): van.bin (bản ghi treeplay), engine_ra.log (stdout: XONG/LOI/HET),
engine_loi.log (stderr: dòng tiến độ), sinh.log (log của script này), gpu.log (nvidia-smi mỗi 5 phút),
tien_do.json (cập nhật mỗi 10 giây), xong.json (khi kết thúc), van.bin.gz (nén khi kết thúc).
"""
import argparse
import gzip
import json
import os
import shutil
import subprocess
import threading
import time


def ghi_json(duong_dan, du_lieu):
    tam = duong_dan + ".tam"
    with open(tam, "w") as f:
        json.dump(du_lieu, f, ensure_ascii=False)
    os.replace(tam, duong_dan)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lc0", default="/content/cv/lc0")
    ap.add_argument("--mang", required=True)
    ap.add_argument("--thu-muc", required=True)
    ap.add_argument("--song-song", type=int, default=128)
    ap.add_argument("--luong-gom-lo", type=int, default=1)
    ap.add_argument("--visits", type=int, default=800)
    ap.add_argument("--temp-plies", type=int, default=30)
    ap.add_argument("--max-ply", type=int, default=450)
    ap.add_argument("--gioi-han-evals", type=int, default=0, help="tự dừng khi đạt (0 = chỉ dừng theo tệp dung)")
    a = ap.parse_args()
    os.makedirs(a.thu_muc, exist_ok=True)
    tm = lambda t: os.path.join(a.thu_muc, t)
    nhat_ky = open(tm("sinh.log"), "a", buffering=1)
    log = lambda s: nhat_ky.write(time.strftime("%Y-%m-%d %H:%M:%S ") + s + "\n")
    cau_hinh = vars(a)
    log("bat dau: " + json.dumps(cau_hinh, ensure_ascii=False))

    lenh = [a.lc0, "treeplay", f"--weights={a.mang}", "--backend=multiplexing",
            f"--backend-opts=backend=onnx-cuda,threads={a.luong_gom_lo},max_batch=1024",
            f"--parallelism={a.song_song}", f"--visits={a.visits}", f"--max-ply={a.max_ply}",
            "--report-seconds=60", f"--output={tm('van.bin')}"]
    log("lenh: " + " ".join(lenh))
    loi = open(tm("engine_loi.log"), "a")
    p = subprocess.Popen(lenh, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=loi, text=True, bufsize=1)
    ra = open(tm("engine_ra.log"), "a", buffering=1)

    trang = {"evals": 0, "van_xong": 0, "van_da_nap": 0, "loi": 0, "dang_dung": False, "bat_dau": time.time()}
    khoa = threading.Lock()
    het = threading.Event()

    def doc_ra():
        for dong in p.stdout:
            ra.write(dong)
            phan = dong.split()
            with khoa:
                if phan and phan[0] == "XONG":
                    trang["van_xong"] += 1
                    trang["evals"] = int(phan[2])
                elif phan and phan[0] == "LOI":
                    trang["loi"] += 1
                elif phan and phan[0] == "HET":
                    trang["evals"] = int(phan[1])
        het.set()

    def ghi_gpu():
        while not het.wait(300):
            try:
                g = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,temperature.gpu",
                                    "--format=csv,noheader"], capture_output=True, text=True, timeout=30).stdout.strip()
                with open(tm("gpu.log"), "a") as f:
                    f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + g + "\n")
            except Exception as e:  # noqa: BLE001 -- chỉ là log
                log(f"nvidia-smi loi: {e}")

    threading.Thread(target=doc_ra, daemon=True).start()
    threading.Thread(target=ghi_gpu, daemon=True).start()

    id_tiep = 0
    lan_ghi = 0.0
    while not het.is_set():
        with khoa:
            dung = os.path.exists(tm("dung")) or (a.gioi_han_evals and trang["evals"] >= a.gioi_han_evals)
            con_dang = trang["van_da_nap"] - trang["van_xong"] - trang["loi"]
        if dung and not trang["dang_dung"]:
            trang["dang_dung"] = True
            log(f"dung mem: thoi nap viec; {con_dang} van dang do se choi not")
            p.stdin.close()
        if not trang["dang_dung"]:
            # Giữ hàng đợi của engine luôn có việc: tối đa 2 lần số ván song song đang chờ hoặc đang chơi.
            them = 2 * a.song_song - con_dang
            for _ in range(max(0, them)):
                p.stdin.write(f"G {id_tiep} {a.temp_plies}\n")
                id_tiep += 1
            p.stdin.flush()
            with khoa:
                trang["van_da_nap"] = id_tiep
        if time.time() - lan_ghi >= 10:
            with khoa:
                t = dict(trang)
            t["giay"] = round(time.time() - t["bat_dau"], 1)
            ghi_json(tm("tien_do.json"), t)
            lan_ghi = time.time()
        time.sleep(1)
    p.wait()
    with khoa:
        t = dict(trang)
    t["giay"] = round(time.time() - t["bat_dau"], 1)
    t["ma_thoat_engine"] = p.returncode
    t["cau_hinh"] = cau_hinh
    with open(tm("van.bin"), "rb") as f_vao, gzip.open(tm("van.bin.gz"), "wb", compresslevel=6) as f_ra:
        shutil.copyfileobj(f_vao, f_ra)
    t["byte_van_bin"] = os.path.getsize(tm("van.bin"))
    t["byte_van_bin_gz"] = os.path.getsize(tm("van.bin.gz"))
    ghi_json(tm("tien_do.json"), t)
    ghi_json(tm("xong.json"), t)
    log("ket thuc: " + json.dumps(t, ensure_ascii=False))


if __name__ == "__main__":
    main()
