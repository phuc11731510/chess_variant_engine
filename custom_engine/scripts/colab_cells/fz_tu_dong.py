"""fz_tu_dong.py -- phần tính toán của vòng lặp tự động (menu fz -> v), chạy trên ĐIỆN THOẠI.

  python ~/fz_tu_dong.py xep <ten>|<HOME>|<lan thu cuoi> ...
      Thứ tự thử xin T4 của các tài khoản (theo lần chụp hạn mức gần nhất, ~/.config/colab-cli/
      fz_han_muc.json trong HOME của từng tài khoản -- xem fz_han_muc.py). In mỗi dòng
      "<ten>\t<loai>\t<mo ta>" theo thứ tự thử; tài khoản bỏ qua in "<ten>\tbo\t<lý do>".
        nap_lai    đã tới giờ nạp lại từ lần chụp          -> thử trước
        xanh       còn >= 1 giờ 15 phút T4 (nhiều trước)           -> thử (bị từ chối thì 10 phút sau thử lại)
        chua_chup  chưa chụp lần nào / không rõ còn bao nhiêu -> thử sau cùng
        het        HẾT, không rõ giờ nạp lại               -> mỗi giờ thử một lần
        bo         còn < 1 giờ 15 phút (vàng) / HẾT chờ giờ nạp lại  -> bỏ qua
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

VONG LAP LIEN TUC (fz_lien_tuc.sh, menu fz -> w): du lieu di theo GOI nho thay vi theo doi.
  Goi tren dien thoai: Download/FairyZero/goi/goi_<so thu tu 5 chu so>_n<mang da choi>_<so van>_<so the>.zip
  (ben trong: games_gen<mang>/<tk>_<run>_game_<g>.xz -- xem python/goi_van.py, phan chay tren may Colab).
  python ~/fz_tu_dong.py goi_nhan <thu muc FairyZero> <zip tam> <mang> <so van> <so the>
      Dat ten cho mot goi vua tai ve: so thu tu = lon nhat + 1, GIU CHO nguyen tu (tep danh dau .seq_<n> tao bang O_EXCL) nen hai cua so
      tai cung luc khong bao gio ra cung so. In "FZ_GOI_NHAN <ten> <so thu tu>".
  python ~/fz_tu_dong.py goi_tong <thu muc FairyZero> <moc>
      Cac goi co so thu tu > <moc> (van MOI tu lan huan luyen truoc bat dau): in
      "FZ_GOI_TONG <so van> <so the> <so thu tu lon nhat> <tong the moi goi> <tong van moi goi>".
  python ~/fz_tu_dong.py cua_so <thu muc FairyZero> <so the>
      CUA SO HUAN LUYEN = cac goi MOI NHAT cho toi khi du <so the> (goi cuoi cung vua du thi dung; chua du thi lay het). In moi goi
      mot dong "GOI <ten>" (tu moi toi cu), cuoi cung "FZ_CUA_SO <so goi> <so van> <so the> <mang nho nhat>-<mang lon nhat>".
  python ~/fz_tu_dong.py nhap_cu <thu muc FairyZero> <doi G> <so doi>
      Mot lan khi chuyen tu vong lap cu (theo doi) sang vong lap lien tuc: moi thu muc games_gen<k>/ (k tu G-<so doi>+1 den G) thanh MOT goi
      (mang k) de lam cua so huan luyen ban dau; thu muc k nao da nhap roi (tep goi/.da_nhap_<k>) thi bo qua.
      In "FZ_NHAP_XONG <so goi> <so thu tu lon nhat>".
  python ~/fz_tu_dong.py don_goi <thu muc FairyZero> <so the> [<he so>]
      Xoa goi cu: giu cac goi moi nhat cho toi khi du <so the> * <he so> (mac dinh 1,5) the; xoa cac goi con lai va tep .seq_ cu.
"""
import hashlib
import json
import lzma
import os
import re
import shutil
import struct
import sys
import time
import zipfile

T4_UOC_TINH = 1.07        # CCU/giờ của một máy T4 (như fz_han_muc.py)
MOT_GIO = 3600
# Hạn mức T4 tối thiểu để xin (12/11): Colab từ chối T4 khi còn ≈ 1,07 giờ (25031006, 12/11), chủ dự án thấy còn
# 1 giờ 10 phút đã không xin được -- trước đây ngưỡng là 1 giờ.
GIO_T4_TOI_THIEU = 1.25
# T4 bị từ chối khi lần đọc ngay sau đó còn từ chừng này giờ trở lên: coi là Colab tạm hết T4 (vẫn thử lại sau
# 10 phút như trước), không phải tài khoản hết hạn mức.
GIO_TU_CHOI_TAM = 2.0


def bi_tu_choi(ch):
    """Như fz_han_muc.bi_tu_choi, nhưng lần bị từ chối khi còn nhiều hạn mức (Colab tạm hết T4) không tính."""
    h = ch.get("het_luc")
    if not h:
        return False
    if h >= ch.get("luc", 0):
        return True
    c = ch.get("con_khi_tu_choi", "khong")
    if c == "khong":
        return False
    return c is None or c / 1000 / T4_UOC_TINH < GIO_TU_CHOI_TAM


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
        het = bi_tu_choi(ch)
        # Bi tu choi SAU gio nap lai: lan nap do khong con gi -> HET, gio nap moi chua biet.
        het_sau_nap = het and bool(nap) and ch["het_luc"] >= nap
        if nap and now >= nap and luc < nap and not het_sau_nap:
            thu.append((0, 0, ten, "nap_lai", "đã tới giờ nạp lại"))
            continue
        if het_sau_nap:
            nap = None                 # gio nap cu da qua va da dung -> "khong ro gio nap lai"
        elif not het and ch.get("con") is not None:   # 12/11: tài khoản vừa bị từ chối không còn hiện "xanh"
            gio = ch["con"] / 1000 / T4_UOC_TINH
            if gio >= GIO_T4_TOI_THIEU:
                thu.append((1, -gio, ten, "xanh", f"còn ≈ {gio:.1f} giờ T4"))
            else:
                bo.append((ten, f"còn ≈ {int(gio * 60)} phút T4 (< {int(GIO_T4_TOI_THIEU * 60)} phút)"))
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
        het = bi_tu_choi(ch)
        het_sau_nap = het and bool(nap) and ch["het_luc"] >= nap
        if nap and now >= nap and luc < nap and not het_sau_nap:
            moc.append((now + 600, f"{ten}: đã tới giờ nạp lại"))
            continue
        if het_sau_nap:
            nap = None
        con = ch.get("con")
        if not het and con is not None and con / 1000 / T4_UOC_TINH >= GIO_T4_TOI_THIEU:
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


# ---------------- Vong lap lien tuc: goi van nho ----------------
RE_GOI_LT = re.compile(r"goi_(\d+)_n(\d+)_(\d+)_(\d+)\.zip")
RE_SEQ = re.compile(r"\.seq_(\d+)")
_HDR = struct.Struct("<4s7I")      # tieu de van v6: magic, ban, version, dinh dang, so the (n), ... (xem python/trainingdata_v6.py)


def dem_the(data):
    """So the cua mot van .xz (chi giai nen phan dau tep; khong can numpy). ValueError neu van hong."""
    try:
        head = lzma.LZMADecompressor(format=lzma.FORMAT_XZ).decompress(data, max_length=_HDR.size)
    except lzma.LZMAError as e:
        raise ValueError(f"xz hong: {e}") from None
    if len(head) < _HDR.size or head[:4] != b"FZD6":
        raise ValueError("khong phai van v6")
    return _HDR.unpack_from(head, 0)[4]


def thu_muc_goi(tai):
    return os.path.join(tai, "goi")


def ds_goi(tai):
    """[(so thu tu, mang, so van, so the, ten)] tang dan theo so thu tu."""
    d = thu_muc_goi(tai)
    out = []
    try:
        ten_tep = os.listdir(d)
    except OSError:
        return out
    for t in ten_tep:
        m = RE_GOI_LT.fullmatch(t)
        if m:
            out.append((int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)), t))
    return sorted(out)


def goi_nhan(tai, tam, mang, van, the):
    d = thu_muc_goi(tai)
    os.makedirs(d, exist_ok=True)
    for _ in range(1000):
        seq = 1 + max([g[0] for g in ds_goi(tai)] + [int(m.group(1)) for t in os.listdir(d) if (m := RE_SEQ.fullmatch(t))] + [0])
        try:
            os.close(os.open(os.path.join(d, f".seq_{seq}"), os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        except FileExistsError:
            continue                      # cua so khac vua lay so nay
        ten = f"goi_{seq:05d}_n{int(mang)}_{int(van)}_{int(the)}.zip"
        os.replace(tam, os.path.join(d, ten))
        print(f"FZ_GOI_NHAN {ten} {seq}")
        return ten
    sys.exit("[!] khong dat duoc so thu tu cho goi")


def goi_tong(tai, moc):
    van = the = 0
    ds = ds_goi(tai)
    for seq, _m, v, t, _n in ds:
        if seq > int(moc):
            van += v
            the += t
    print(f"FZ_GOI_TONG {van} {the} {max([g[0] for g in ds] + [0])} {sum(g[3] for g in ds)} {sum(g[2] for g in ds)}")


def cua_so(tai, so_the):
    so_the = int(so_the)
    chon, the, van = [], 0, 0
    for g in sorted(ds_goi(tai), reverse=True):
        if the >= so_the:
            break
        chon.append(g)
        the += g[3]
        van += g[2]
    for g in chon:
        print(f"GOI {g[4]}")
    mangs = [g[1] for g in chon]
    print(f"FZ_CUA_SO {len(chon)} {van} {the} {min(mangs, default=0)}-{max(mangs, default=0)}")


def nhap_cu(tai, g, so_doi):
    g, so_doi = int(g), int(so_doi)
    d = thu_muc_goi(tai)
    os.makedirs(d, exist_ok=True)
    so = 0
    for k in range(max(0, g - so_doi + 1), g + 1):
        nguon = os.path.join(tai, f"games_gen{k}")
        if not os.path.isdir(nguon) or os.path.exists(os.path.join(d, f".da_nhap_{k}")):
            continue
        tam = os.path.join(d, f".dang_nhap_{k}.zip")
        van = the = 0
        with zipfile.ZipFile(tam, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as z:
            for t in sorted(os.listdir(nguon)):
                p = os.path.join(nguon, t)
                if not (t.endswith(".xz") and os.path.isfile(p)):
                    continue
                with open(p, "rb") as f:
                    data = f.read()
                try:
                    n = dem_the(data)
                except ValueError:
                    continue
                g_t = time.localtime(max(os.path.getmtime(p), 315532800))
                zi = zipfile.ZipInfo(f"games_gen{k}/{t}", date_time=tuple(g_t)[:6])
                zi.compress_type = zipfile.ZIP_STORED
                z.writestr(zi, data)
                van += 1
                the += n
        if van == 0:
            os.remove(tam)
            continue
        ten = goi_nhan(tai, tam, k, van, the)
        with open(os.path.join(d, f".da_nhap_{k}"), "w") as f:
            f.write(ten + "\n")
        print(f"FZ_NHAP {k} {van} {the}")
        so += 1
    print(f"FZ_NHAP_XONG {so} {max([x[0] for x in ds_goi(tai)] + [0])}")


def don_goi(tai, so_the, he_so=1.5):
    gioi_han = float(so_the) * float(he_so)
    cong, xoa, mb = 0, 0, 0.0
    ds = sorted(ds_goi(tai), reverse=True)
    for g in ds:
        if cong >= gioi_han:
            p = os.path.join(thu_muc_goi(tai), g[4])
            byte = os.path.getsize(p)
            print(f"XOA goi {g[4]} {byte / 1e6:.1f}")
            os.remove(p)
            xoa += 1
            mb += byte / 1e6
        cong += g[3]
    d = thu_muc_goi(tai)
    if ds:
        cao = ds[0][0]
        for t in os.listdir(d):
            m = RE_SEQ.fullmatch(t)
            if m and int(m.group(1)) < cao - 200:
                os.remove(os.path.join(d, t))
    print(f"FZ_DON_GOI_XONG {xoa} {mb:.1f}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "xep":
        xep(a[1:])
    elif a and a[0] == "hen":
        hen(a[1:])
    elif len(a) == 4 and a[0] == "gop":
        gop(a[1], a[2], a[3])
    elif len(a) == 6 and a[0] == "goi_nhan":
        goi_nhan(a[1], a[2], a[3], a[4], a[5])
    elif len(a) == 3 and a[0] == "goi_tong":
        goi_tong(a[1], a[2])
    elif len(a) == 3 and a[0] == "cua_so":
        cua_so(a[1], a[2])
    elif len(a) == 4 and a[0] == "nhap_cu":
        nhap_cu(a[1], a[2], a[3])
    elif len(a) in (3, 4) and a[0] == "don_goi":
        don_goi(a[1], a[2], *a[3:])
    elif a and a[0] == "don_dep" and 4 <= len(a) <= 6:
        don_dep(a[1], a[2], a[3], next((x for x in a[4:] if x != "--thu"), None), "--thu" in a[4:])
    else:
        sys.exit(__doc__)
