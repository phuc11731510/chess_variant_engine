"""Sinh ván trên Colab cho ô 04 của `cv`: nạp việc liên tục cho `lc0 treeplay`, dừng mềm như ô 04 của fz.

Cách truyền thống: mọi việc là "G <id> <temp_plies>" (ván từ thế khởi đầu). Ba cách dừng MỀM (thôi nạp việc,
đóng đầu vào của engine; engine chơi nốt các ván đang dở rồi thoát, không mất ván nào):
  - có tệp --tep-dung (vòng lặp / ô 09b tạo; như --stop-file của engine biến thể);
  - hết --max-giay giây (như --max-seconds: chừa hạn mức T4 cho phần chơi nốt, gom và tải về);
  - đủ lượng tính toán được giao --giao (như --games: máy không bao giờ nhận quá phần được giao). Ván đang dở
    được tính vào: dừng khi số lần chạy mạng đã xong + ước lượng phần còn lại của các ván dở (mỗi ván dở còn
    nửa ván trung bình) đạt --giao, để sau khi chơi nốt thì vừa đủ.
  - gần --han-cung: còn ít hơn 1,1 lần độ dài ván dài (phân vị 90 của các ván đã xong, tính bằng giây) thì thôi nạp,
    để ván nạp cuối kịp xong trước hạn.
Một cách dừng CỨNG: tới --han-cung giây (lúc Colab sắp thu hồi máy vì hết hạn mức) mà engine chưa thoát thì tắt
engine, bỏ các việc còn dở, giữ mọi ván đã xong (cắt bản ghi dở ở cuối van.bin). Thà mất vài ván dở còn hơn mất
cả máy: 7/11 hai máy cách cây chỉ chừa 7 phút đuôi ván (đo một lần ở đời 2 cách truyền thống, ván ngắn), trong
khi ván đời 0 cách cây dài gần 23 phút; Colab thu hồi máy khi ván còn đang chơi nốt, mất hết hơn 110 triệu lần
chạy mạng chưa tải về.

In ra màn hình (vòng lặp của `cv` đọc các dòng này qua log của ô):
  [sinh] <ván xong> van, <lần chạy mạng> evals, dang choi <d>, uoc con <r>, giao <giao>   (mỗi 15 giây)
  [sinh] dung mem: <lý do>; <d> van dang do se choi not
  [sinh] Ket thuc: <ván> van, <evals> evals trong <giây>s (<lý do dừng>)
Cách cây trò chơi (THIET_KE_CO_VUA.md 6, 9, 12.6): --viec <tệp> = danh sách việc do điện thoại lập (cay.py lay_viec),
mỗi dòng "G <id> <temp> <nước...>" (ván rẽ) hoặc "S <id> <nước...>" (search lại); nạp lần lượt. --tu-quet: hết việc mà
còn ngân sách thì tự quét các ván máy vừa chơi rồi rẽ tiếp (colab/tu_quet.py); --van-goc K: khi không có tệp việc thì
bắt đầu bằng K ván từ thế khởi đầu (đời 0). Ước phần còn lại của việc dở tính theo loại việc: ván rẽ còn nửa ván
trung bình, search lại còn một lần search.

Thư mục của lần chạy (--thu-muc): van.bin (bản ghi treeplay), engine_ra.log (XONG/LOI/HET), engine_loi.log,
sinh.log, gpu.log, tien_do.json (mỗi 10 giây), xong.json (khi kết thúc), van.bin.gz (nén khi kết thúc), mau.npz
(mẫu huấn luyện đã mã hoá và nén, tạo một lần khi kết thúc; ô 07 nạp thẳng).
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


def cat_ban_ghi_do(duong_dan, log):
    """Sau khi tắt engine: cắt van.bin tới hết bản ghi trọn vẹn cuối cùng (mỗi bản ghi mở đầu bằng magic CVG1 và
    độ dài cả bản ghi, u32)."""
    import struct
    try:
        n = os.path.getsize(duong_dan)
    except OSError:
        return
    i = 0
    with open(duong_dan, "rb") as f:
        while i + 8 <= n:
            f.seek(i)
            dau = f.read(8)
            magic, co = dau[:4], struct.unpack("<I", dau[4:])[0]
            if magic != b"CVG1" or co < 8 or i + co > n:
                break
            i += co
    if i < n:
        with open(duong_dan, "r+b") as f:
            f.truncate(i)
        log(f"cat {n - i} byte ban ghi do o cuoi van.bin (giu {i} byte)", True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lc0", default="/content/cv/lc0")
    ap.add_argument("--py", default="/content/cv/py", help="thư mục mã Python (tao_mau.py)")
    ap.add_argument("--mang", required=True)
    ap.add_argument("--thu-muc", required=True)
    ap.add_argument("--song-song", type=int, default=128)
    ap.add_argument("--luong-gom-lo", type=int, default=1)
    ap.add_argument("--visits", type=int, default=800)
    ap.add_argument("--temp-plies", type=int, default=30)
    ap.add_argument("--max-ply", type=int, default=450)
    ap.add_argument("--giao", type=int, default=0, help="số lần chạy mạng được giao (0 = không giới hạn)")
    ap.add_argument("--max-giay", type=int, default=0, help="dừng mềm sau chừng này giây (0 = không giới hạn)")
    ap.add_argument("--tep-dung", default="", help="có tệp này thì dừng mềm")
    ap.add_argument("--han-cung", type=int, default=0,
                    help="dừng CỨNG sau chừng này giây (bỏ việc dở, giữ ván đã xong); gần hạn thì thôi nạp (0 = tắt)")
    ap.add_argument("--backend", default="multiplexing", help="chỉ để thử (vd random)")
    ap.add_argument("--backend-opts", default="", help="chỉ để thử; rỗng = onnx-cuda như ô 04")
    ap.add_argument("--viec", default="", help="cách cây: tệp danh sách việc (G/S) do điện thoại lập")
    ap.add_argument("--tu-quet", action="store_true", help="cách cây: hết việc thì tự quét ván của máy rồi rẽ tiếp")
    ap.add_argument("--van-goc", type=int, default=0, help="cách cây: số ván từ thế khởi đầu khi không có tệp việc")
    a = ap.parse_args()
    if not a.han_cung and a.max_giay:
        # Vòng lặp mở trước bản sửa 7/11 không ghi HAN: lấy hạn cứng = --max-giay + 400 giây, đúng phần chừa đuôi ván
        # đã đo cho 128 ván (408 giây) mà vòng lặp cũ trừ ra khi tính SECS -- tức lúc phải gom và tải về.
        a.han_cung = a.max_giay + 400
    che_do_cay = bool(a.viec) or a.tu_quet or a.van_goc > 0
    os.makedirs(a.thu_muc, exist_ok=True)
    tm = lambda t: os.path.join(a.thu_muc, t)
    if a.tep_dung and os.path.exists(a.tep_dung):
        os.remove(a.tep_dung)   # tệp của lần dừng trước: để lại thì dừng ngay từ ván đầu
    nhat_ky = open(tm("sinh.log"), "a", buffering=1)

    def log(s, man_hinh=False):
        nhat_ky.write(time.strftime("%Y-%m-%d %H:%M:%S ") + s + "\n")
        if man_hinh:
            print("[sinh] " + s, flush=True)

    cau_hinh = vars(a)
    log("bat dau: " + json.dumps(cau_hinh, ensure_ascii=False), True)

    opts = a.backend_opts or (f"backend=onnx-cuda,threads={a.luong_gom_lo},max_batch=1024" if a.backend == "multiplexing" else "")
    lenh = [a.lc0, "treeplay", f"--weights={a.mang}", f"--backend={a.backend}"] + ([f"--backend-opts={opts}"] if opts else []) + [
            f"--parallelism={a.song_song}", f"--visits={a.visits}", f"--max-ply={a.max_ply}",
            "--report-seconds=60", f"--output={tm('van.bin')}"]
    log("lenh: " + " ".join(lenh), True)
    loi = open(tm("engine_loi.log"), "a")
    p = subprocess.Popen(lenh, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=loi, text=True, bufsize=1)
    ra = open(tm("engine_ra.log"), "a", buffering=1)

    trang = {"evals": 0, "van_xong": 0, "van_da_nap": 0, "loi": 0, "dang_dung": False, "ly_do_dung": "",
             "bat_dau": time.time(), "giao": a.giao}
    khoa = threading.Lock()
    het = threading.Event()
    nap_luc = {}          # id -> lúc nạp (mọi việc)
    thoi_g = []           # số giây của từng ván (G) đã xong -- cho dừng mềm gần --han-cung

    def doc_ra():
        for dong in p.stdout:
            ra.write(dong)
            phan = dong.split()
            with khoa:
                if phan and phan[0] == "XONG":
                    trang["van_xong"] += 1
                    trang["evals"] = int(phan[2])
                    t0 = nap_luc.pop(int(phan[1]), None)
                    loai_xong = dang_chay.pop(int(phan[1]), None)
                    if t0 is not None and (not che_do_cay or loai_xong == "G"):
                        thoi_g.append(time.time() - t0)
                elif phan and phan[0] == "LOI":
                    trang["loi"] += 1
                    if len(phan) > 1 and phan[1].isdigit():
                        dang_chay.pop(int(phan[1]), None)
                        nap_luc.pop(int(phan[1]), None)
                elif phan and phan[0] == "HET":
                    trang["evals"] = int(phan[1])
        het.set()

    def ghi_gpu():
        # Mẫu đầu sau 30 giây (engine đã chạy đều), sau đó 5 phút một lần, để gpu.log luôn có.
        cho = 30
        while not het.wait(cho):
            cho = 300
            try:
                g = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,temperature.gpu",
                                    "--format=csv,noheader"], capture_output=True, text=True, timeout=30).stdout.strip()
                with open(tm("gpu.log"), "a") as f:
                    f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + g + "\n")
            except Exception as e:  # noqa: BLE001 -- chỉ là log
                log(f"nvidia-smi loi: {e}")

    # Cách cây: hàng đợi việc, loại của việc đang chạy, cây nhỏ để tự quét và để đếm số lần search đã xong.
    hang_doi = []
    e_viec, g_viec = 490.0, 0.0          # lần chạy mạng mỗi search, chi phí một ván rẽ (dòng "# e .. g .." của tệp việc)
    if a.viec:
        for dong in open(a.viec):
            phan = dong.split()
            if phan and phan[0] == "#":
                kv = dict(zip(phan[1::2], phan[2::2]))
                e_viec = float(kv.get("e", e_viec))
                g_viec = float(kv.get("g", g_viec))
            elif phan:
                hang_doi.append((phan[0], " ".join(phan[2:])))
    else:
        hang_doi = [("G", "0")] * a.van_goc
    dang_chay = {}
    cay_nho = None
    if che_do_cay:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from tu_quet import CayCucBo
        cay_nho = CayCucBo()

    def uoc_con(t):
        """Ước lượng số lần chạy mạng các việc đang dở còn tốn. Cách truyền thống: mỗi ván dở còn nửa ván trung bình
        (từ 8 ván xong). Cách cây: ván rẽ dở còn nửa ván rẽ trung bình, search lại dở còn nửa lần search.
        Cách cây KHÔNG chia bộ đếm của engine cho số search đã xong: bộ đếm gồm cả phần việc dở, còn số search đếm
        từ van.bin (đọc 10 giây một lần) chỉ gồm việc đã xong -- việc S xong rất nhanh nên tỉ số phồng hàng chục lần
        (thử 7/11: đời 1 dừng ở 100 nghìn / 1 triệu). Lần chạy mạng mỗi search lấy theo điện thoại đo (dòng # e);
        độ dài ván rẽ đo trên máy từ các ván rẽ đã xong (từ 4 ván), trước đó theo ước của điện thoại (# g)."""
        d = t["van_da_nap"] - t["van_xong"] - t["loi"]
        if not che_do_cay:
            return int(d * t["evals"] / t["van_xong"] / 2) if t["van_xong"] >= 8 else 0
        with khoa:
            loai = list(dang_chay.values())
        so_g = loai.count("G")
        return int(so_g * gia_g() / 2 + (len(loai) - so_g) * e_viec / 2)

    def gia_g():
        """Chi phí một ván rẽ: đo từ các ván rẽ đã xong trên máy (từ 4 ván), trước đó theo ước của điện thoại.
        Đời 0 (ván từ gốc, không có tệp việc): 0 tới khi xong 4 ván, như cách truyền thống chờ 8 ván."""
        if cay_nho.so_viec_g >= 4:
            return e_viec * cay_nho.so_lan_g / cay_nho.so_viec_g
        return g_viec

    threading.Thread(target=doc_ra, daemon=True).start()
    threading.Thread(target=ghi_gpu, daemon=True).start()

    def van_dai():
        """Số giây của một ván dài: phân vị 90 các ván đã xong (từ 8 ván), None nếu chưa đủ."""
        with khoa:
            d = sorted(thoi_g)
        return d[int(0.9 * (len(d) - 1))] if len(d) >= 8 else None

    id_tiep = 0
    lan_ghi = lan_in = 0.0
    da_cat = False
    while not het.is_set():
        with khoa:
            t = dict(trang)
        con = uoc_con(t)
        da_chay = time.time() - t["bat_dau"]
        if a.han_cung and da_chay >= a.han_cung and not da_cat:
            da_cat = True
            with khoa:
                trang["dang_dung"], trang["ly_do_dung"] = True, "het --han-cung"
            log(f"dung cung: het --han-cung ({a.han_cung}s); bo {t['van_da_nap'] - t['van_xong'] - t['loi']} viec dang do, "
                "giu van da xong", True)
            try:
                p.stdin.close()
            except OSError:
                pass
            p.terminate()
            try:
                p.wait(20)
            except subprocess.TimeoutExpired:
                p.kill()
            het.wait(30)              # luồng đọc kết quả hết dữ liệu -> thoát vòng
            continue
        if not t["dang_dung"]:
            ly_do = ""
            if a.tep_dung and os.path.exists(a.tep_dung):
                ly_do = "tep dung"
            elif os.path.exists(tm("dung")):
                ly_do = "tep dung"
            elif a.max_giay and da_chay >= a.max_giay:
                ly_do = "het --max-giay"
            elif a.han_cung and van_dai() is not None and da_chay >= a.han_cung - 1.1 * van_dai():
                ly_do = f"gan --han-cung (van dai {van_dai() / 60:.1f} phut)"
            elif a.giao and t["evals"] + con >= a.giao:
                ly_do = "du phan giao"
            if ly_do:
                with khoa:
                    trang["dang_dung"] = True
                    trang["ly_do_dung"] = ly_do
                log(f"dung mem: {ly_do}; {t['van_da_nap'] - t['van_xong'] - t['loi']} van dang do se choi not", True)
                p.stdin.close()
        if not trang["dang_dung"]:
            # Nạp vừa đủ: số ván song song cộng 4 việc chờ. Việc đã nạp vẫn được chơi sau khi dừng mềm, nên nạp
            # dư làm vượt phần giao (lần chạy thử 2026-11-03 nạp 2 lần số ván song song: vượt gấp đôi).
            them = a.song_song + 4 - (t["van_da_nap"] - t["van_xong"] - t["loi"])
            if che_do_cay and them > 0 and len(hang_doi) < them and a.tu_quet:
                cay_nho.doc_them(tm("van.bin"))
                moi = cay_nho.quet()
                hang_doi.extend(("G", "0 " + " ".join(d)) for d in moi)
                if moi:
                    log(f"tu quet: them {len(moi)} van re", True)
            het_viec = du_giao = False
            them_uoc = 0.0
            for _ in range(max(0, them)):
                if not che_do_cay:
                    p.stdin.write(f"G {id_tiep} {a.temp_plies}\n")
                elif hang_doi:
                    # Cách cây: chỉ nạp khi phần đã chạy + phần còn của việc dở + việc này còn trong phần giao
                    # (thử 7/11: hết danh sách, tự quét nạp một lúc 48 ván rẽ khi giao 300 nghìn -> chạy 2 triệu).
                    gia = gia_g() if hang_doi[0][0] == "G" else e_viec
                    if a.giao and t["evals"] + con + them_uoc + gia > a.giao and (dang_chay or them_uoc):
                        du_giao = True
                        break
                    loai, phan_con = hang_doi.pop(0)
                    p.stdin.write(f"{loai} {id_tiep} {phan_con}\n")
                    them_uoc += gia
                    with khoa:
                        dang_chay[id_tiep] = loai
                else:
                    het_viec = True
                    break
                with khoa:
                    nap_luc[id_tiep] = time.time()
                id_tiep += 1
            p.stdin.flush()
            with khoa:
                trang["van_da_nap"] = id_tiep
            if du_giao:
                with khoa:
                    trang["dang_dung"], trang["ly_do_dung"] = True, "du phan giao"
                log(f"dung mem: du phan giao (viec ke tiep khong con vua); {len(dang_chay)} viec dang do se chay not", True)
                p.stdin.close()
            elif het_viec and not dang_chay and not hang_doi:
                # Hết việc, không còn gì đang chạy, quét không ra điểm rẽ mới: dừng (engine tự thoát).
                with khoa:
                    trang["dang_dung"], trang["ly_do_dung"] = True, "het viec"
                log("het viec: khong con viec nao de nap", True)
                p.stdin.close()
        if che_do_cay and time.time() - lan_ghi >= 10:
            cay_nho.doc_them(tm("van.bin"))          # đếm số lần search đã xong (cho uoc_con)
        if time.time() - lan_ghi >= 10:
            with khoa:
                t = dict(trang)
            t["giay"] = round(time.time() - t["bat_dau"], 1)
            t["dang_choi"] = t["van_da_nap"] - t["van_xong"] - t["loi"]
            t["uoc_con"] = uoc_con(t)
            ghi_json(tm("tien_do.json"), t)
            lan_ghi = time.time()
        if time.time() - lan_in >= 15:
            with khoa:
                t = dict(trang)
            print(f"[sinh] {t['van_xong']} van, {t['evals']} evals, dang choi {t['van_da_nap'] - t['van_xong'] - t['loi']}, "
                  f"uoc con {uoc_con(t)}, giao {a.giao}", flush=True)
            lan_in = time.time()
        time.sleep(1)
    p.wait()
    if da_cat:
        cat_ban_ghi_do(tm("van.bin"), log)
    with khoa:
        t = dict(trang)
    t["giay"] = round(time.time() - t["bat_dau"], 1)
    t["ma_thoat_engine"] = p.returncode
    t["cau_hinh"] = cau_hinh
    with open(tm("van.bin"), "rb") as f_vao, gzip.open(tm("van.bin.gz.tam"), "wb", compresslevel=6) as f_ra:
        shutil.copyfileobj(f_vao, f_ra)
    os.replace(tm("van.bin.gz.tam"), tm("van.bin.gz"))
    t["byte_van_bin"] = os.path.getsize(tm("van.bin"))
    t["byte_van_bin_gz"] = os.path.getsize(tm("van.bin.gz"))
    # Mã hoá một lần ngay trên máy vừa sinh (như engine của fz ghi ván ở dạng sẵn sàng huấn luyện): mau.npz nén,
    # ô 07 chỉ việc nạp. Bộ mã hoá là py/ma_hoa.py đã kiểm khớp với lc0. Lỗi thì ô 07 tự mã hoá lại từ van.bin.gz.
    t0 = time.time()
    r = subprocess.run(["python3", os.path.join(a.py, "tao_mau.py"), tm("mau.npz.tam.npz"), tm("van.bin"),
                        "--q-ratio", "0.2", "--nen"], cwd=a.py, capture_output=True, text=True)
    if r.returncode == 0 and os.path.exists(tm("mau.npz.tam.npz")):
        os.replace(tm("mau.npz.tam.npz"), tm("mau.npz"))
        t["mau"] = {"giay": round(time.time() - t0, 1), "byte": os.path.getsize(tm("mau.npz")),
                    "ra": r.stdout.strip()[-300:]}
        log(f"tao mau: {r.stdout.strip()[-200:]}", True)
    else:
        t["mau"] = {"loi": (r.stdout + r.stderr).strip()[-500:]}
        log(f"tao mau LOI (o 07 se tu ma hoa lai tu van.bin.gz): {(r.stdout + r.stderr).strip()[-300:]}", True)
    os.remove(tm("van.bin"))   # đã có bản .gz
    ghi_json(tm("tien_do.json"), t)
    ghi_json(tm("xong.json"), t)
    log("ket thuc: " + json.dumps(t, ensure_ascii=False))
    print(f"[sinh] Ket thuc: {t['van_xong']} van, {t['evals']} evals trong {t['giay']:.0f}s "
          f"({t['ly_do_dung'] or 'engine tu thoat'}), ma thoat engine {p.returncode}", flush=True)


if __name__ == "__main__":
    main()
