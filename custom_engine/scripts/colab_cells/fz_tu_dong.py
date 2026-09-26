"""fz_tu_dong.py -- phần tính toán của vòng lặp tự động (menu fz -> v), chạy trên ĐIỆN THOẠI.

  python ~/fz_tu_dong.py xep <ten>|<HOME>|<lan thu cuoi> ...
      Thứ tự thử xin T4 của các tài khoản (theo lần chụp hạn mức gần nhất, ~/.config/colab-cli/
      fz_han_muc.json trong HOME của từng tài khoản -- xem fz_han_muc.py). In mỗi dòng
      "<ten>\t<loai>\t<mo ta>" theo thứ tự thử; tài khoản bỏ qua in "<ten>\tbo\t<lý do>".
        nap_lai    đã tới giờ nạp lại từ lần chụp          -> thử trước
        xanh       còn >= 1 giờ T4 (nhiều trước)           -> thử (bị từ chối thì 10 phút sau thử lại)
        chua_chup  chưa chụp lần nào / không rõ còn bao nhiêu -> thử sau cùng
        het        HẾT, không rõ giờ nạp lại               -> mỗi giờ thử một lần
        bo         còn < 1 giờ (vàng) / HẾT chờ giờ nạp lại  -> bỏ qua
  python ~/fz_tu_dong.py gop <thu muc FairyZero> <doi G> <so doi>
      Cuối giai đoạn 2: bung mọi gói games_gen<G>_<N>.zip vào thư mục games_gen<G>/ (tên tệp thêm
      tiền tố <N>_ vì engine đánh số lại từ game_0 mỗi lần chạy; ván trùng nội dung -- cùng CRC và
      kích thước -- bỏ; GIỮ ngày sửa gốc của từng ván: train.py lấy 4% ván MỚI NHẤT làm tập kiểm
      định), rồi gói games_gen<G>/, games_gen<G-1>/ ... (<so doi> đời, đời nào có) thành
      games_gen<G>.zip (ZIP_STORED, bên trong giữ thư mục games_gen<k>/). Ghi qua tệp tạm rồi mới
      đổi tên: gộp dở (mất điện, bị giết) không để lại gói hỏng. In "FZ_GOP_XONG <so van>".
"""
import json
import os
import shutil
import sys
import time
import zipfile

T4_UOC_TINH = 1.07        # CCU/giờ của một máy T4 (như fz_han_muc.py)
MOT_GIO = 3600


def doc_chup(home):
    try:
        with open(os.path.join(home, ".config/colab-cli/fz_han_muc.json")) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def xep(ds, now=None):
    now = time.time() if now is None else now
    thu, bo = [], []
    for muc in ds:
        ten, home, lan = (muc.split("|") + ["", ""])[:3]
        lan = float(lan or 0)
        ch = doc_chup(home)
        if not ch:
            thu.append((3, 0, ten, "chua_chup", "chưa chụp hạn mức"))
            continue
        nap, luc = ch.get("nap_lai"), ch.get("luc", 0)
        if nap and now >= nap and luc < nap:
            thu.append((0, 0, ten, "nap_lai", "đã tới giờ nạp lại"))
            continue
        het = bool(ch.get("het_luc")) and ch["het_luc"] >= luc
        if ch.get("con") is not None:
            gio = ch["con"] / 1000 / T4_UOC_TINH
            if gio >= 1:
                thu.append((1, -gio, ten, "xanh", f"còn ≈ {gio:.1f} giờ T4"))
            else:
                bo.append((ten, f"còn ≈ {int(gio * 60)} phút T4 (< 1 giờ)"))
            continue
        if het and nap and now < nap:
            bo.append((ten, "HẾT, chờ giờ nạp lại"))
        elif het:
            if now - lan >= MOT_GIO:
                thu.append((2, 0, ten, "het", "HẾT, không rõ giờ nạp lại -- thử lại mỗi giờ"))
            else:
                bo.append((ten, "HẾT, không rõ giờ nạp lại -- đã thử trong giờ này"))
        else:
            thu.append((3, 0, ten, "chua_chup", "không rõ còn bao nhiêu"))
    for _, _, ten, loai, mo_ta in sorted(thu):
        print(f"{ten}\t{loai}\t{mo_ta}")
    for ten, ly_do in bo:
        print(f"{ten}\tbo\t{ly_do}")


def la_van(ten):
    return ten.endswith((".gz", ".bin"))


def ten_moi(thu_muc, ten):
    """Tên chưa có trong thu_muc, kiểu Windows Explorer: 'x.zip' -> 'x (2).zip' -> 'x (3).zip'..."""
    if not os.path.exists(os.path.join(thu_muc, ten)):
        return ten
    goc, duoi = os.path.splitext(ten)
    n = 2
    while os.path.exists(os.path.join(thu_muc, f"{goc} ({n}){duoi}")):
        n += 1
    return f"{goc} ({n}){duoi}"


def gop(tai, g, so_doi):
    g, so_doi = int(g), int(so_doi)
    goi = []
    for f in os.listdir(tai):
        dau, duoi = f"games_gen{g}_", ".zip"
        if f.startswith(dau) and f.endswith(duoi) and f[len(dau):-len(duoi)].isdigit():
            goi.append((int(f[len(dau):-len(duoi)]), f))
    if not goi:
        sys.exit(f"[!] Không có gói games_gen{g}_<số>.zip nào trong {tai}")
    goi.sort()
    # 1. Bung các gói vào thư mục tạm, rồi mới thay thư mục games_gen<g>/.
    dich = os.path.join(tai, f"games_gen{g}")
    tam = os.path.join(tai, f".games_gen{g}.dang_gom")
    shutil.rmtree(tam, ignore_errors=True)
    os.makedirs(tam)
    da_co, so, trung = set(), 0, 0
    for n, f in goi:
        with zipfile.ZipFile(os.path.join(tai, f)) as z:
            for i in z.infolist():
                if i.is_dir() or not la_van(i.filename):
                    continue
                khoa = (i.CRC, i.file_size)
                if khoa in da_co:
                    trung += 1
                    continue
                da_co.add(khoa)
                ra = os.path.join(tam, f"{n}_{os.path.basename(i.filename)}")
                with z.open(i) as vao, open(ra, "wb") as o:
                    shutil.copyfileobj(vao, o)
                t = time.mktime(i.date_time + (0, 0, -1))   # giữ ngày sửa gốc (tập kiểm định)
                os.utime(ra, (t, t))
                so += 1
        print(f"  {f}: xong (tổng {so} ván)", flush=True)
    if os.path.exists(dich):
        cu = ten_moi(tai, f"games_gen{g}")
        os.rename(dich, os.path.join(tai, cu))
        print(f"  (đã có thư mục games_gen{g}/ -> đổi tên thành {cu}/, không xoá)")
    os.rename(tam, dich)
    print(f"[gộp] {len(goi)} gói -> games_gen{g}/: {so} ván" + (f" (bỏ {trung} ván trùng)" if trung else ""))
    # 2. Gói gộp nhiều đời.
    zip_ra = os.path.join(tai, f"games_gen{g}.zip")
    zip_tam = os.path.join(tai, f".games_gen{g}.zip.dang_goi")
    tong, dem = 0, []
    with zipfile.ZipFile(zip_tam, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as z:
        for k in range(g, max(-1, g - so_doi), -1):
            d = os.path.join(tai, f"games_gen{k}")
            if not os.path.isdir(d):
                continue
            n = 0
            for goc, _, tep in os.walk(d):
                for t in sorted(tep):
                    if la_van(t):
                        p = os.path.join(goc, t)
                        z.write(p, os.path.join(f"games_gen{k}", os.path.relpath(p, d)))
                        n += 1
            dem.append(f"games_gen{k}: {n}")
            tong += n
    if os.path.exists(zip_ra):
        cu = ten_moi(tai, f"games_gen{g}.zip")
        os.rename(zip_ra, os.path.join(tai, cu))
        print(f"  (đã có games_gen{g}.zip -> đổi tên thành {cu}, không xoá)")
    os.replace(zip_tam, zip_ra)
    mb = os.path.getsize(zip_ra) / 1e6
    print(f"[gộp] games_gen{g}.zip ({mb:.1f} MB): {' · '.join(dem)}")
    print(f"FZ_GOP_XONG {tong}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "xep":
        xep(a[1:])
    elif len(a) == 4 and a[0] == "gop":
        gop(a[1], a[2], a[3])
    else:
        sys.exit(__doc__)
