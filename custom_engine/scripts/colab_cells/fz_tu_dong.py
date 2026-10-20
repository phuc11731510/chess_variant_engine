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
  python ~/fz_tu_dong.py hen <ten>|<HOME>|<lan thu cuoi> ...
      Sau một vòng xin không được: in "<giây epoch>\t<lý do>" = lúc nên xin lại (giờ nạp lại sớm
      nhất đã biết; HẾT không rõ giờ nạp: lần thử cuối + 1 giờ; còn tài khoản thử được: 10 phút).
  python ~/fz_tu_dong.py gop <thu muc FairyZero> <doi G> <so doi>
      Cuối giai đoạn 2: bung mọi gói games_gen<G>_<N>.zip vào thư mục games_gen<G>/ (tên tệp thêm
      tiền tố <N>_ vì engine đánh số lại từ game_0 mỗi lần chạy; ván trùng nội dung -- cùng CRC và
      kích thước -- bỏ; GIỮ ngày sửa gốc của từng ván: train.py lấy 4% ván MỚI NHẤT làm tập kiểm
      định), rồi gói games_gen<G>/, games_gen<G-1>/ ... (<so doi> đời, đời nào có) thành
      games_gen<G>.zip (ZIP_STORED, bên trong giữ thư mục games_gen<k>/). Ghi qua tệp tạm rồi mới
      đổi tên: gộp dở (mất điện, bị giết) không để lại gói hỏng. In "FZ_GOP_XONG <so van>".
  python ~/fz_tu_dong.py don_dep <thu muc FairyZero> <doi G> <so doi> [<tep mang tren GitHub>] [--thu]
      Dọn điện thoại lúc CHUẨN BỊ SINH DỮ LIỆU đời G (đầu vòng lặp, và sau khi huấn luyện xong đời G-1
      rồi lên đời G): xoá những gì đời G trở đi không còn dùng.
        - gói ván của các đời < G: games_gen<k>_<N>.zip và games_gen<k>.zip (kể cả bản "(2)").
          Ván của chúng đã nằm trong thư mục games_gen<k>/. Đời k còn trong cửa sổ huấn luyện mà
          KHÔNG có thư mục games_gen<k>/ thì GIỮ gói (xoá là mất ván).
        - thư mục ván games_gen<k>/ của các đời k < G - (<so doi> - 1) (ra khỏi cửa sổ huấn luyện:
          đời 91, 4 đời -> giữ 88..91, xoá <= 87) và thư mục gộp dở .games_gen<k>.dang_gom.
        - mạng gen<k>.onnx / gen<k>.pt (kể cả "gen<k> (2).pt") đã LÊN GITHUB: <tep mang tren GitHub> là
          các dòng "ten<TAB>kich thuoc<TAB>sha256:..." của Release; chỉ xoá khi sha256 của tệp trên
          điện thoại KHỚP sha256 trên GitHub (không có sha256 hoặc lệch -> giữ). Không đưa tệp đó
          vào thì không động tới mạng.
      In "XOA <loai> <ten> <MB>" / "GIU <ly do>" và cuối cùng "FZ_DON_XONG <so muc> <MB>". --thu: chỉ in,
      không xoá.
"""
import hashlib
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


def la_van(ten):
    return ten.endswith((".xz", ".gz", ".bin"))


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


RE_GOI = re.compile(r"games_gen(\d+)(?:_(\d+))?(?: \(\d+\))?\.zip")
RE_THU_MUC = re.compile(r"games_gen(\d+)(?: \(\d+\))?")
RE_TAM = re.compile(r"\.games_gen(\d+)\.(?:dang_gom|zip\.dang_goi)")
RE_MANG = re.compile(r"gen(\d+)(?: \(\d+\))?\.(onnx|pt)")


def kich_thuoc(p):
    if os.path.isdir(p):
        return sum(os.path.getsize(os.path.join(g, t)) for g, _, ts in os.walk(p) for t in ts)
    return os.path.getsize(p)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for khoi in iter(lambda: f.read(1 << 20), b""):
            h.update(khoi)
    return h.hexdigest()


def doc_github(tep):
    """{ten: (kich thuoc, sha256 hex hoặc '')} từ các dòng 'ten<TAB>kich thuoc<TAB>sha256:...'."""
    gh = {}
    with open(tep, encoding="utf-8") as f:
        for dong in f:
            p = dong.rstrip("\r\n").split("\t")
            if len(p) >= 2 and p[1].isdigit():
                gh[p[0]] = (int(p[1]), p[2].removeprefix("sha256:") if len(p) > 2 else "")
    return gh


def don_dep(tai, g, so_doi, tep_github=None, thu=False):
    g, so_doi = int(g), int(so_doi)
    dau_cua_so = g - (so_doi - 1)          # đời nhỏ nhất còn trong cửa sổ huấn luyện của đời g
    xoa, giu = [], []                      # (loai, ten, byte)
    gh = doc_github(tep_github) if tep_github else None
    ten_tep = sorted(os.listdir(tai))
    co_thu_muc = {int(m.group(1)) for t in ten_tep
                  if (m := RE_THU_MUC.fullmatch(t)) and os.path.isdir(os.path.join(tai, t))}
    for t in ten_tep:
        p = os.path.join(tai, t)
        if m := RE_GOI.fullmatch(t):
            k = int(m.group(1))
            if k >= g or not os.path.isfile(p):
                continue
            if k >= dau_cua_so and k not in co_thu_muc:
                giu.append(f"gói {t}: đời {k} còn trong cửa sổ huấn luyện mà chưa có thư mục games_gen{k}/")
                continue
            xoa.append(("goi", t, kich_thuoc(p)))
        elif m := RE_TAM.fullmatch(t):          # gộp / gói dở của đời trước (đời g có thể đang gộp: giữ)
            if int(m.group(1)) < g:
                xoa.append(("tam", t, kich_thuoc(p)))
        elif (m := RE_THU_MUC.fullmatch(t)) and os.path.isdir(p):
            if int(m.group(1)) < dau_cua_so:
                xoa.append(("thu_muc", t, kich_thuoc(p)))
        elif gh is not None and (m := RE_MANG.fullmatch(t)) and os.path.isfile(p):
            tren = gh.get(f"gen{m.group(1)}.{m.group(2)}")
            if tren is None:
                giu.append(f"mạng {t}: chưa có trên GitHub")
            elif not tren[1]:
                giu.append(f"mạng {t}: GitHub không ghi sha256 -> không chắc giống, giữ")
            elif os.path.getsize(p) != tren[0] or sha256(p) != tren[1]:
                giu.append(f"mạng {t}: khác bản trên GitHub, giữ")
            else:
                xoa.append(("mang", t, kich_thuoc(p)))
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
    elif len(a) == 4 and a[0] == "gop":
        gop(a[1], a[2], a[3])
    elif a and a[0] == "don_dep" and 4 <= len(a) <= 6:
        don_dep(a[1], a[2], a[3], next((x for x in a[4:] if x != "--thu"), None), "--thu" in a[4:])
    else:
        sys.exit(__doc__)
