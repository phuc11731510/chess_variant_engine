"""cv_tu_dong.py -- phần tính toán của vòng lặp tự động (menu cv -> v), chạy trên ĐIỆN THOẠI.

Chép từ fz_tu_dong.py của engine cờ biến thể. `xep`, `hen` giữ nguyên. `gop`, `don_dep` viết lại cho dữ liệu cờ vua
(mỗi lần sinh là một thư mục lan_* gồm van.bin.gz, mau.npz, xong.json và log), thêm `can`: lượng tính toán đời G
còn cần.

  python cv_tu_dong.py xep <ten>|<HOME>|<lan thu cuoi> ...
      Thứ tự thử xin T4 của các tài khoản (theo lần chụp hạn mức gần nhất, ~/.config/colab-cli/
      fz_han_muc.json trong HOME của từng tài khoản -- xem fz_han_muc.py). In mỗi dòng
      "<ten>\t<loai>\t<mo ta>" theo thứ tự thử; tài khoản bỏ qua in "<ten>\tbo\t<lý do>".
        nap_lai    đã tới giờ nạp lại từ lần chụp          -> thử trước
        xanh       còn >= 1 giờ T4 (nhiều trước)           -> thử (bị từ chối thì 10 phút sau thử lại)
        chua_chup  chưa chụp lần nào / không rõ còn bao nhiêu -> thử sau cùng
        het        HẾT, không rõ giờ nạp lại               -> mỗi giờ thử một lần
        bo         còn < 1 giờ (vàng) / HẾT chờ giờ nạp lại  -> bỏ qua
  python cv_tu_dong.py hen <ten>|<HOME>|<lan thu cuoi> ...
      Sau một vòng xin không được: in "<giây epoch>\t<lý do>" = lúc nên xin lại (giờ nạp lại sớm
      nhất đã biết; HẾT không rõ giờ nạp: lần thử cuối + 1 giờ; còn tài khoản thử được: 10 phút).
  python cv_tu_dong.py can <thu muc cach> <doi G> <ngan sach moi doi>
      Lượng tính toán (số lần chạy mạng) đời G còn cần, tính CỘNG DỒN: mục tiêu khi xong đời G là
      ngân_sách x (G + 1); phần đời trước vượt thì đời G bớt đúng chừng ấy, nhưng đời nào cũng tự sinh ít nhất
      nửa ngân sách. In "<cần cho đời G> <đã dùng ở các đời trước>". Số đã dùng của một đời k = tổng xong.json
      trong thư mục games_gen<k>/ (đã gộp), hoặc số tích luỹ lớn nhất trong tên gói games_gen<k>_<N>.zip.
  python cv_tu_dong.py gop <thu muc cach> <cach> <doi G> <so doi>
      Cuối giai đoạn 2: bung mọi gói games_gen<G>_<N>.zip vào thư mục games_gen<G>/ (mỗi lần sinh một thư mục
      <N>_lan_<giờ>/, giữ MỌI tệp: ván, mẫu, log -- minh chứng), rồi gói van.bin.gz + mau.npz + xong.json của
      games_gen<G>/, games_gen<G-1>/ ... (<so doi> đời, đời nào có) thành games_gen<G>.zip (ZIP_STORED, bên trong
      giữ thư mục <cach>_games_gen<k>/ như trên máy Colab). Ghi qua tệp tạm rồi mới đổi tên: gộp dở (mất điện,
      bị giết) không để lại gói hỏng. In "FZ_GOP_XONG <so lan sinh>".
  python cv_tu_dong.py don_dep <thu muc cach> <doi G> [--thu]
      Dọn điện thoại lúc CHUẨN BỊ SINH DỮ LIỆU đời G. Khác fz: dự án giữ MỌI dấu vết, nên chỉ xoá thứ trùng lặp:
      gói ván games_gen<k>_<N>.zip và gói gộp games_gen<k>.zip của các đời k < G mà thư mục games_gen<k>/ đã có
      (nội dung của chúng đã nằm trong thư mục đó), và thư mục / gói gộp dở. Thư mục ván và mạng KHÔNG BAO GIỜ
      bị xoá. In "XOA <loai> <ten> <MB>" / "GIU <ly do>" và cuối cùng "FZ_DON_XONG <so muc> <MB>". --thu: chỉ in.
"""
import json
import os
import re
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
        het = bool(ch.get("het_luc")) and ch["het_luc"] >= luc
        # Bi tu choi SAU gio nap lai: lan nap do khong con gi -> HET, gio nap moi chua biet.
        het_sau_nap = het and bool(nap) and ch["het_luc"] >= nap
        if nap and now >= nap and luc < nap and not het_sau_nap:
            thu.append((0, 0, ten, "nap_lai", "đã tới giờ nạp lại"))
            continue
        if het_sau_nap:
            nap = None                 # gio nap cu da qua va da dung -> "khong ro gio nap lai"
        elif ch.get("con") is not None:
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


def hen(ds, now=None):
    """Lúc nên xin máy lại sau một vòng xin không được: sớm nhất trong các mốc
      - tài khoản HẾT / vàng đã biết giờ nạp lại  -> giờ nạp lại đó;
      - HẾT không rõ giờ nạp lại (hoặc vàng không rõ) -> lần thử cuối + 1 giờ (thử để biết);
      - còn tài khoản được thử ngay (nạp lại / xanh / chưa chụp) -> 10 phút nữa (Colab từ chối
        dù còn hạn mức: hết T4 tạm thời).
    In "<giây epoch>\t<lý do>". Ít nhất 1 phút, nhiều nhất 3 giờ (lần chụp có thể đã cũ)."""
    now = time.time() if now is None else now
    moc = []
    for muc in ds:
        ten, home, lan = (muc.split("|") + ["", ""])[:3]
        lan = float(lan or 0)
        ch = doc_chup(home)
        if not ch:
            moc.append((now + 600, f"{ten}: chưa chụp hạn mức"))
            continue
        nap, luc = ch.get("nap_lai"), ch.get("luc", 0)
        het = bool(ch.get("het_luc")) and ch["het_luc"] >= luc
        het_sau_nap = het and bool(nap) and ch["het_luc"] >= nap
        if nap and now >= nap and luc < nap and not het_sau_nap:
            moc.append((now + 600, f"{ten}: đã tới giờ nạp lại"))
            continue
        if het_sau_nap:
            nap = None
        con = ch.get("con")
        if not het and con is not None and con / 1000 / T4_UOC_TINH >= 1:
            moc.append((now + 600, f"{ten}: còn hạn mức (Colab hết T4 tạm thời?)"))
        elif nap and nap > now:
            moc.append((nap, f"{ten}: nạp lại lúc {time.strftime('%H:%M', time.localtime(nap))}"))
        elif het:
            # Như xep: HẾT không rõ giờ nạp lại -> mỗi giờ thử một lần (xin được thì biết giờ nạp).
            moc.append((max(lan, now - MOT_GIO) + MOT_GIO, f"{ten}: HẾT, không rõ giờ nạp lại -- thử để biết"))
        elif con is None:
            moc.append((now + 600, f"{ten}: không rõ còn bao nhiêu"))
        # vàng (< 1 giờ) không rõ giờ nạp lại: xep luôn bỏ qua -> không phải mốc
    if not moc:
        moc.append((now + 600, "không tài khoản nào thử được -- xem lại sau 10 phút"))
    t, ly_do = min(moc)
    t = min(max(t, now + 60), now + 3 * MOT_GIO)
    print(f"{int(t)}\t{ly_do}")


def ten_moi(thu_muc, ten):
    """Tên chưa có trong thu_muc, kiểu Windows Explorer: 'x.zip' -> 'x (2).zip' -> 'x (3).zip'..."""
    if not os.path.exists(os.path.join(thu_muc, ten)):
        return ten
    goc, duoi = os.path.splitext(ten)
    n = 2
    while os.path.exists(os.path.join(thu_muc, f"{goc} ({n}){duoi}")):
        n += 1
    return f"{goc} ({n}){duoi}"


RE_GOI = re.compile(r"games_gen(\d+)_(\d+)(?: \(\d+\))?\.zip")
RE_GOP = re.compile(r"games_gen(\d+)(?: \(\d+\))?\.zip")
RE_THU_MUC = re.compile(r"games_gen(\d+)")
RE_TAM = re.compile(r"\.games_gen(\d+)\.(?:dang_gom|zip\.dang_goi)")
CHO_HUAN_LUYEN = ("van.bin.gz", "mau.npz", "xong.json")


def goi_doi(tai, g):
    """[(N, tên)] các gói lẻ games_gen<g>_<N>.zip, N tăng dần."""
    ra = []
    for f in os.listdir(tai):
        m = RE_GOI.fullmatch(f)
        if m and int(m.group(1)) == g and os.path.isfile(os.path.join(tai, f)):
            ra.append((int(m.group(2)), f))
    return sorted(ra)


def evals_doi(tai, k):
    """Số lần chạy mạng đã dùng ở đời k: thư mục đã gộp (tổng xong.json) hoặc số tích luỹ lớn nhất trong tên gói."""
    d = os.path.join(tai, f"games_gen{k}")
    if os.path.isdir(d):
        tong = 0
        for lan in os.listdir(d):
            try:
                with open(os.path.join(d, lan, "xong.json")) as f:
                    tong += json.load(f)["evals"]
            except (OSError, ValueError, KeyError):
                pass
        return tong
    g = goi_doi(tai, k)
    return g[-1][0] if g else 0


def can(tai, g, ngan_sach):
    g, ns = int(g), int(ngan_sach)
    truoc = sum(evals_doi(tai, k) for k in range(g))
    print(f"{max(ns * (g + 1) - truoc, ns // 2)} {truoc}")


def gop(tai, cach, g, so_doi):
    g, so_doi = int(g), int(so_doi)
    goi = goi_doi(tai, g)
    if not goi:
        sys.exit(f"[!] Không có gói games_gen{g}_<số>.zip nào trong {tai}")
    # 1. Bung các gói vào thư mục tạm, rồi mới thay thư mục games_gen<g>/.
    dich = os.path.join(tai, f"games_gen{g}")
    tam = os.path.join(tai, f".games_gen{g}.dang_gom")
    shutil.rmtree(tam, ignore_errors=True)
    os.makedirs(tam)
    so_lan, trung, da_co = 0, 0, set()
    for n, f in goi:
        with zipfile.ZipFile(os.path.join(tai, f)) as z:
            for i in z.infolist():
                phan = i.filename.split("/")
                if i.is_dir() or len(phan) != 3 or not phan[1].startswith("lan_"):
                    continue                     # tong.json của gói: tính lại từ xong.json
                lan, ten = phan[1], phan[2]
                if ten == "van.bin.gz":
                    khoa = (i.CRC, i.file_size)
                    if khoa in da_co:            # cùng một lần sinh tải về hai lần (gói trùng)
                        trung += 1
                        continue
                    da_co.add(khoa)
                    so_lan += 1
                ra = os.path.join(tam, f"{n}_{lan}", ten)
                os.makedirs(os.path.dirname(ra), exist_ok=True)
                with z.open(i) as vao, open(ra, "wb") as o:
                    shutil.copyfileobj(vao, o)
                t = time.mktime(i.date_time + (0, 0, -1))   # giữ ngày sửa gốc
                os.utime(ra, (t, t))
        print(f"  {f}: xong (tổng {so_lan} lần sinh)", flush=True)
    for lan in os.listdir(tam):                  # lần sinh trùng: chỉ còn log, bỏ
        if not os.path.exists(os.path.join(tam, lan, "van.bin.gz")):
            shutil.rmtree(os.path.join(tam, lan))
    if os.path.exists(dich):
        cu = ten_moi(tai, f"games_gen{g}")
        os.rename(dich, os.path.join(tai, cu))
        print(f"  (đã có thư mục games_gen{g}/ -> đổi tên thành {cu}/, không xoá)")
    os.rename(tam, dich)
    print(f"[gộp] {len(goi)} gói -> games_gen{g}/: {so_lan} lần sinh, {evals_doi(tai, g):,} lần chạy mạng"
          + (f" (bỏ {trung} lần sinh trùng)" if trung else ""))
    # 2. Gói gộp nhiều đời: chỉ những gì ô 07 cần (ván, mẫu, tóm tắt của từng lần sinh).
    zip_ra = os.path.join(tai, f"games_gen{g}.zip")
    zip_tam = os.path.join(tai, f".games_gen{g}.zip.dang_goi")
    tong, dem = 0, []
    with zipfile.ZipFile(zip_tam, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as z:
        for k in range(g, max(-1, g - so_doi), -1):
            d = os.path.join(tai, f"games_gen{k}")
            if not os.path.isdir(d):
                continue
            n = 0
            for lan in sorted(os.listdir(d)):
                if not os.path.exists(os.path.join(d, lan, "van.bin.gz")):
                    continue
                for t in CHO_HUAN_LUYEN:
                    p = os.path.join(d, lan, t)
                    if os.path.exists(p):
                        z.write(p, f"{cach}_games_gen{k}/{lan}/{t}")
                n += 1
            dem.append(f"games_gen{k}: {n} lần sinh")
            tong += n
    if os.path.exists(zip_ra):
        cu = ten_moi(tai, f"games_gen{g}.zip")
        os.rename(zip_ra, os.path.join(tai, cu))
        print(f"  (đã có games_gen{g}.zip -> đổi tên thành {cu}, không xoá)")
    os.replace(zip_tam, zip_ra)
    mb = os.path.getsize(zip_ra) / 1e6
    print(f"[gộp] games_gen{g}.zip ({mb:.1f} MB): {' · '.join(dem)}")
    print(f"FZ_GOP_XONG {tong}")


def kich_thuoc(p):
    if os.path.isdir(p):
        return sum(os.path.getsize(os.path.join(g, t)) for g, _, ts in os.walk(p) for t in ts)
    return os.path.getsize(p)


def don_dep(tai, g, thu=False):
    g = int(g)
    xoa, giu = [], []                      # (loai, ten, byte)
    ten_tep = sorted(os.listdir(tai))
    co_thu_muc = {int(m.group(1)) for t in ten_tep
                  if (m := RE_THU_MUC.fullmatch(t)) and os.path.isdir(os.path.join(tai, t))}
    for t in ten_tep:
        p = os.path.join(tai, t)
        m = RE_GOI.fullmatch(t) or RE_GOP.fullmatch(t)
        if m and os.path.isfile(p):
            k = int(m.group(1))
            if k >= g:
                continue
            if k not in co_thu_muc:
                giu.append(f"gói {t}: đời {k} chưa có thư mục games_gen{k}/ (xoá là mất ván)")
                continue
            xoa.append(("goi", t, kich_thuoc(p)))
        elif m := RE_TAM.fullmatch(t):          # gộp / gói dở của đời trước (đời g có thể đang gộp: giữ)
            if int(m.group(1)) < g:
                xoa.append(("tam", t, kich_thuoc(p)))
    tong = 0
    for loai, t, byte in xoa:
        p = os.path.join(tai, t)
        print(f"XOA {loai} {t} {byte / 1e6:.1f}", flush=True)
        if not thu:
            shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
        tong += byte
    for ly_do in giu:
        print(f"GIU {ly_do}")
    print(f"FZ_DON_XONG {len(xoa)} {tong / 1e6:.1f}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "xep":
        xep(a[1:])
    elif a and a[0] == "hen":
        hen(a[1:])
    elif len(a) == 4 and a[0] == "can":
        can(a[1], a[2], a[3])
    elif len(a) == 5 and a[0] == "gop":
        gop(a[1], a[2], a[3], a[4])
    elif a and a[0] == "don_dep" and 3 <= len(a) <= 4:
        don_dep(a[1], a[2], "--thu" in a[3:])
    else:
        sys.exit(__doc__)
