"""fz_chuyen.py -- chuyển "ghế lái" giữa điện thoại (Termux) và máy tính (WSL), dùng chung cho cv và fz.

Ghế lái = mọi thứ menu và vòng lặp đọc: tài khoản Colab (token, hạn mức chụp gần nhất), trạng thái vòng lặp
(~/.fz_tk/.tu_dong của fz, ~/.fz_tk/.cv_tu_dong của cv, các tệp cấu hình ~/.fz_tk/.*), và dữ liệu cần để chạy
tiếp (Download/CoVua của cv, Download/FairyZero của fz). Nhận gói xong, máy bên kia chạy y như máy bên này.

  python fz_chuyen.py tinh_trang                         # máy này đang cầm lái hay đã giao; gói chuyển có sẵn
  python fz_chuyen.py xuat [--du-an cv,fz] [--menu-pid P] # tạo Download/chuyen_<dt|pc>_<lúc>.tar rồi KHOÁ máy này
  python fz_chuyen.py nhap <gói.tar> [--menu-pid P] [--ep] # nhận gói (mở khoá nếu là gói chiều về)
  python fz_chuyen.py khoa                               # mã thoát 0 = máy này đã giao ghế lái

Hai kiểu gói, tự chọn:
  ĐẦY ĐỦ (máy này chưa từng nhận gói, vd điện thoại gửi đi lần đầu): tài khoản + trạng thái + dữ liệu, TRỪ các tệp
    lớn (> 1 MB) của đời cũ hơn cửa sổ (đời < đời mới nhất - 4): chúng ở yên bên gửi, không ai cần tới (vòng lặp
    chỉ gộp 4 đời gần nhất; lượng tính toán cộng dồn đọc xong.json -- tệp nhỏ, luôn đi theo). Bên nhận cất mọi thứ
    cũ của nó sang chỗ lưu (không xoá), thay bằng gói, và ghi "gốc" = danh sách tệp vừa nhận.
  THAY ĐỔI (máy này đang chạy bằng gói đầy đủ nhận được, vd máy tính gửi về): tài khoản + trạng thái + MỌI tệp dữ
    liệu mới hoặc đổi so với gốc, kèm danh sách tệp đã bị xoá (gói ván vòng lặp đã gộp). Bên nhận chép đè/xoá đúng
    như vậy -- dấu vết đầy đủ như thể chưa từng rời máy.

An toàn (chép theo tinh thần fz: không để hai nơi cùng lái):
  - Chỉ xuất ở chỗ DỪNG SẠCH: không cửa sổ menu nào khác đang chạy, không tài khoản nào đang giữ máy Colab.
  - Xuất xong, máy gửi bị KHOÁ (~/.fz_tk/.chuyen/da_giao.json): menu cv/fz không xin máy, không chạy vòng lặp,
    cho tới khi nhập gói chiều về (hoặc nhập lại gói ĐẦY ĐỦ từ máy kia).
  - Gói chứa token = mật khẩu tài khoản: chỉ chép giữa máy của chủ dự án, không bao giờ vào git.
"""
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tarfile
import time
import uuid

HOME = os.path.expanduser("~")
TKG = os.path.join(HOME, ".fz_tk")
CHUYEN = os.path.join(TKG, ".chuyen")
DA_GIAO = os.path.join(CHUYEN, "da_giao.json")
GOC = os.path.join(CHUYEN, "goc.json")
CHINH = os.path.join(HOME, ".config", "colab-cli")
DL = os.path.join(HOME, "storage", "downloads")
DU_AN = {"cv": "CoVua", "fz": "FairyZero"}
TEP_TK = ("token.json", "settings.json", "fz_han_muc.json")   # mỗi tài khoản: đăng nhập, cài đặt CLI, hạn mức chụp
BO_THU_MUC_TKG = {".cua_so", ".chuyen"}                       # theo tiến trình / của chính công cụ này
# Tệp theo pid của một cửa sổ (w_<pid>, o_<pid>, .gop_<pid>, ...): chỉ có nghĩa với tiến trình đang chạy.
RE_PID = re.compile(r"^(\.?w|o|\.gop|\.luong|dung_cs|len|\.mang_gh|\.can|nhat_ky)_\d+(\.tmp)?$|^nhat_ky\.tmp$")
LON = 1 << 20          # tệp > 1 MB của đời cũ thì không mang theo
DU_DOI = 4             # mang theo các đời >= đời mới nhất - 4 (cửa sổ 4 đời + 1 đời dư)
RE_GEN = re.compile(r"gen(\d+)")


def may_nay():
    return "dt" if "com.termux" in os.environ.get("PREFIX", "") else "pc"


def doc_json(p, mac_dinh=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return mac_dinh


def ghi_json(p, x):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tam = p + ".tam"
    with open(tam, "w", encoding="utf-8") as f:
        json.dump(x, f, ensure_ascii=False, indent=1)
    os.replace(tam, p)


def ten_chinh():
    try:
        with open(os.path.join(TKG, ".ten_chinh"), encoding="utf-8") as f:
            return f.read().strip() or "chinh"
    except OSError:
        return "chinh"


def cac_tk():
    """[(tên, thư mục colab-cli)] mọi tài khoản đã đăng nhập; tài khoản chính trước."""
    ra = []
    if os.path.isfile(os.path.join(CHINH, "token.json")):
        ra.append((ten_chinh(), CHINH))
    if os.path.isdir(TKG):
        for t in sorted(os.listdir(TKG)):
            d = os.path.join(TKG, t, ".config", "colab-cli")
            if not t.startswith(".") and os.path.isfile(os.path.join(d, "token.json")):
                ra.append((t, d))
    return ra


def dang_giu_may():
    """[(tài khoản, [tên phiên])] các tài khoản còn phiên máy Colab (sessions.json của Colab CLI)."""
    ra = []
    for t, d in cac_tk():
        s = doc_json(os.path.join(d, "sessions.json"), {})
        ten = list(s) if isinstance(s, dict) else [str(x) for x in s] if isinstance(s, list) else []
        if ten:
            ra.append((t, ten))
    return ra


def to_tien(pid):
    """Các pid tổ tiên của pid (để không tính cửa sổ đang gọi công cụ này là 'cửa sổ khác')."""
    ra = set()
    while pid and pid not in ra and pid > 1:
        ra.add(pid)
        try:
            with open(f"/proc/{pid}/stat") as f:
                pid = int(f.read().rsplit(")", 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            break
    return ra


def cua_so_khac(menu_pid):
    """pid các cửa sổ menu cv/fz khác đang chạy (~/.fz_tk/.cua_so/<pid>, tiến trình còn sống)."""
    minh = to_tien(os.getpid()) | to_tien(menu_pid or 0)
    d = os.path.join(TKG, ".cua_so")
    ra = []
    for f in (os.listdir(d) if os.path.isdir(d) else []):
        if f.isdigit() and int(f) not in minh and os.path.exists(f"/proc/{f}"):
            ra.append(int(f))
    return ra


def tep_trang_thai():
    """[(đường dẫn tương đối trong ~/.fz_tk, tuyệt đối)] tệp cấu hình + trạng thái vòng lặp (không theo pid)."""
    ra = []
    if not os.path.isdir(TKG):
        return ra
    for f in sorted(os.listdir(TKG)):
        p = os.path.join(TKG, f)
        if os.path.isfile(p) and f.startswith("."):
            ra.append((f, p))
        elif os.path.isdir(p) and f.startswith(".") and f not in BO_THU_MUC_TKG:
            for g in sorted(os.listdir(p)):       # chỉ tệp cấp đầu: thư mục con là khoá mkdir / bản chép ô theo pid
                q = os.path.join(p, g)
                if os.path.isfile(q) and not RE_PID.match(g):
                    ra.append((f"{f}/{g}", q))
    return ra


def kiem_ke(goc):
    """{đường dẫn tương đối: [cỡ, mtime]} mọi tệp dưới thư mục dữ liệu goc."""
    ra = {}
    for d, ds, fs in os.walk(goc):
        ds[:] = [x for x in ds if not x.startswith(".tam")]
        for f in fs:
            if f.startswith(".tam_"):
                continue
            p = os.path.join(d, f)
            try:
                st = os.stat(p)
            except OSError:
                continue
            ra[os.path.relpath(p, goc).replace(os.sep, "/")] = [st.st_size, int(st.st_mtime)]
    return ra


def khoa_nhom(rel):
    """Nhóm đời của tệp = các thành phần đường dẫn trước thành phần đầu tiên có 'gen<số>' (cv: tt / cay / arena;
    fz: thư mục gốc). Đời của tệp = số gen lớn nhất trong đường dẫn."""
    phan = rel.split("/")
    for i, x in enumerate(phan):
        if RE_GEN.search(x):
            return "/".join(phan[:i]), max(int(n) for n in RE_GEN.findall(rel))
    return None, None


def chon_tep_day_du(ke):
    """Tách kiểm kê thành (mang theo, để lại): để lại tệp > 1 MB của đời < đời mới nhất trong nhóm - 4."""
    moi = {}
    for rel in ke:
        k, g = khoa_nhom(rel)
        if k is not None:
            moi[k] = max(moi.get(k, 0), g)
    theo, lai = {}, {}
    for rel, v in ke.items():
        k, g = khoa_nhom(rel)
        (lai if k is not None and v[0] > LON and g < moi[k] - DU_DOI else theo)[rel] = v
    return theo, lai


def bam_script():
    """sha256 ngắn của menu / vòng lặp đang cài (cảnh báo khi hai máy chạy hai phiên bản khác nhau)."""
    ra = {}
    for ten, p in (("cv", os.path.join(HOME, "cv", "cv_tu_dong.sh")), ("cv_menu", os.path.join(HOME, "cv", "cv_menu.sh")),
                   ("fz", os.path.join(HOME, "fz_tu_dong.sh")), ("fz_menu", os.path.join(HOME, "fz_menu.sh"))):
        try:
            with open(p, "rb") as f:
                ra[ten] = hashlib.sha256(f.read()).hexdigest()[:12]
        except OSError:
            pass
    return ra


def co(x):
    for d in ("B", "KB", "MB", "GB"):
        if x < 1024 or d == "GB":
            return f"{x:.0f} {d}" if d == "B" else f"{x:.1f} {d}"
        x /= 1024


def tinh_trang():
    g = doc_json(DA_GIAO)
    if g:
        print(f"ĐÃ GIAO ghế lái lúc {g.get('luc_doc', '?')} (gói {g.get('goi', '?')}, dữ liệu: {', '.join(g.get('du_an', [])) or 'không'})")
        print("  -> nhập gói chiều về (hoặc gói đầy đủ từ máy kia) để lái lại ở máy này")
    else:
        print("Máy này đang cầm lái.")
    goc = doc_json(GOC)
    if goc:
        print(f"Đang chạy bằng gói đầy đủ nhận lúc {goc.get('luc_doc', '?')} từ {goc.get('tu', '?')}: lần xuất tới là gói THAY ĐỔI (chiều về)")
    tk = cac_tk()
    print(f"Tài khoản: {', '.join(t for t, _ in tk) or 'chưa có'}")
    for t, s in dang_giu_may():
        print(f"  {t} đang giữ máy: {', '.join(s)}")
    goi = sorted((f for f in (os.listdir(DL) if os.path.isdir(DL) else []) if re.fullmatch(r"chuyen_\w+_\d{8}_\d{6}\.tar", f)),
                 reverse=True)
    for f in goi:
        print(f"  gói có sẵn: Download/{f} ({co(os.path.getsize(os.path.join(DL, f)))})")


def xuat(du_an, menu_pid):
    if os.path.exists(DA_GIAO):
        sys.exit("[!] Máy này đã giao ghế lái (đã xuất trước đó) -- không xuất lần nữa. Nhập gói của máy kia trước.")
    loi = []
    k = cua_so_khac(menu_pid)
    if k:
        loi.append(f"còn {len(k)} cửa sổ menu khác đang mở (pid {', '.join(map(str, k))}): thoát hết (q) trước")
    for t, s in dang_giu_may():
        loi.append(f"tài khoản {t} còn giữ máy {', '.join(s)}: dừng mềm vòng lặp rồi trả máy (menu t) trước")
    if loi:
        sys.exit("[!] Chưa ở chỗ dừng sạch:\n  " + "\n  ".join(loi))
    tk = cac_tk()
    if not tk:
        sys.exit("[!] Chưa có tài khoản Colab nào để chuyển")
    goc = doc_json(GOC)
    kieu = "thay_doi" if goc else "day_du"
    if goc:
        du_an = [d for d in goc["du_an"]]           # chiều về: đúng các dự án đã nhận
    du_an = [d for d in du_an if os.path.isdir(os.path.join(DL, DU_AN[d]))]
    phien = uuid.uuid4().hex[:12]
    luc = time.strftime("%Y%m%d_%H%M%S")
    ten = f"chuyen_{may_nay()}_{luc}.tar"
    meta = {"phien": phien, "kieu": kieu, "tu": may_nay(), "luc": int(time.time()), "luc_doc": time.strftime("%H:%M %d/%m/%Y"),
            "du_an": du_an, "chinh": ten_chinh(), "tk": [t for t, _ in tk], "script": bam_script(),
            "goc": goc["phien"] if goc else None, "xoa": {}, "de_lai": {}, "gui": {}}
    os.makedirs(DL, exist_ok=True)
    tam = os.path.join(DL, ".tam_" + ten)
    tong = 0
    with tarfile.open(tam, "w") as tar:
        for t, d in tk:
            for f in TEP_TK:
                p = os.path.join(d, f)
                if os.path.isfile(p):
                    tar.add(p, f"tk/{t}/{f}")
        for rel, p in tep_trang_thai():
            tar.add(p, f"tkg/{rel}")
        for da in du_an:
            goc_da = os.path.join(DL, DU_AN[da])
            ke = kiem_ke(goc_da)
            if kieu == "day_du":
                theo, lai = chon_tep_day_du(ke)
                meta["de_lai"][da] = len(lai)
            else:
                cu = goc["tep"].get(da, {})
                theo = {r: v for r, v in ke.items() if cu.get(r) != v}
                meta["xoa"][da] = sorted(r for r in cu if r not in ke)
            meta["gui"][da] = ke if kieu == "day_du" else theo   # bên nhận dò xung đột / ghi gốc
            for rel in sorted(theo):
                tar.add(os.path.join(goc_da, rel), f"du_lieu/{da}/{rel}")
                tong += theo[rel][0]
        b = json.dumps(meta, ensure_ascii=False).encode()
        ti = tarfile.TarInfo("meta.json")
        ti.size, ti.mtime = len(b), int(time.time())
        tar.addfile(ti, io.BytesIO(b))
    os.replace(tam, os.path.join(DL, ten))
    giao = {k: meta[k] for k in ("phien", "kieu", "luc", "luc_doc", "du_an", "tk")}
    giao["goi"] = ten
    giao["gui"] = meta["gui"]     # để khi nhận gói chiều về biết tệp nào ở đây đã bị sửa trong lúc giao
    ghi_json(DA_GIAO, giao)
    if goc:
        os.replace(GOC, GOC + ".da_tra")      # chiều về xong: máy này không còn chạy bằng gói đầy đủ đó
    print(f"[đã xuất] Download/{ten}  ({co(os.path.getsize(os.path.join(DL, ten)))}; gói {'ĐẦY ĐỦ' if kieu == 'day_du' else 'THAY ĐỔI (chiều về)'})")
    print(f"  tài khoản: {', '.join(meta['tk'])}")
    for da in du_an:
        n = len(meta["gui"][da]) if kieu == "thay_doi" else len(meta["gui"][da]) - meta["de_lai"][da]
        print(f"  {DU_AN[da]}: {n} tệp" + (f" (để lại {meta['de_lai'][da]} tệp lớn của đời cũ)" if kieu == "day_du" else
                                            f", {len(meta['xoa'][da])} tệp đã xoá"))
    print("[khoá] máy này đã GIAO ghế lái: không xin máy, không chạy vòng lặp tới khi nhập gói của máy kia.")


def cat_vao(p, noi_luu, goc_tuong_doi):
    """Chuyển p sang chỗ lưu (giữ cấu trúc), không xoá gì."""
    if os.path.lexists(p):
        dich = os.path.join(noi_luu, goc_tuong_doi)
        os.makedirs(os.path.dirname(dich), exist_ok=True)
        shutil.move(p, dich)


def nhap(goi, menu_pid, ep):
    if not os.path.isfile(goi):
        sys.exit(f"[!] Không có tệp {goi}")
    k = cua_so_khac(menu_pid)
    if k:
        sys.exit(f"[!] Còn {len(k)} cửa sổ menu khác đang mở (pid {', '.join(map(str, k))}): thoát hết (q) trước")
    may = dang_giu_may()
    if may:
        sys.exit("[!] Máy này còn giữ máy Colab: " + "; ".join(f"{t}: {', '.join(s)}" for t, s in may) + " -- trả máy (menu t) trước")
    with tarfile.open(goi) as tar:
        meta = json.load(tar.extractfile("meta.json"))
        giao = doc_json(DA_GIAO)
        if meta["kieu"] == "thay_doi":
            if not giao or giao.get("phien") != meta["goc"]:
                sys.exit("[!] Gói chiều về này không khớp lần giao của máy này (máy này không phải nơi đã gửi gói đầy đủ "
                         "tương ứng, hoặc đã nhận rồi). Không nhập.")
        elif not giao and not ep:
            co_du_lieu = [DU_AN[d] for d in meta["du_an"]
                          if os.path.isdir(os.path.join(DL, DU_AN[d])) and os.listdir(os.path.join(DL, DU_AN[d]))]
            if co_du_lieu or cac_tk():
                print("[!] Máy này đang cầm lái (chưa giao) mà gói là gói ĐẦY ĐỦ: nhận sẽ cất tài khoản và dữ liệu "
                      f"hiện có ({', '.join(co_du_lieu) or 'chỉ tài khoản'}) sang chỗ lưu (không xoá). Chắc chắn thì "
                      "chạy lại với --ep.")
                sys.exit(3)                        # menu hỏi lại người dùng rồi gọi với --ep
        luc = time.strftime("%Y%m%d_%H%M%S")
        ten_tep = [m for m in tar.getmembers() if m.isfile()]
        for m in ten_tep:                          # gói của mình nhưng vẫn chặn đường dẫn lạ
            if m.name.startswith("/") or ".." in m.name.split("/"):
                sys.exit(f"[!] Gói có đường dẫn lạ: {m.name}")
        canh_bao = []
        if meta["kieu"] == "day_du":
            luu = os.path.join(HOME, f"fz_chuyen_luu_{luc}")
            # Cất ghế lái cũ của máy này (tài khoản, trạng thái, dữ liệu) -- không xoá.
            if os.path.isdir(TKG):
                cat_vao(TKG, luu, ".fz_tk")
            for f in TEP_TK + ("sessions.json",):
                cat_vao(os.path.join(CHINH, f), luu, f"colab-cli_chinh/{f}")
            for d in meta["du_an"]:
                p = os.path.join(DL, DU_AN[d])
                if os.path.isdir(p):
                    os.replace(p, os.path.join(DL, f"{DU_AN[d]}_truoc_chuyen_{luc}"))
            print(f"[cất] ghế lái cũ của máy này: ~/fz_chuyen_luu_{luc}" +
                  "".join(f", Download/{DU_AN[d]}_truoc_chuyen_{luc}" for d in meta["du_an"]))
        else:
            # Chiều về: tệp ở đây mà đã khác lúc giao = có ai đó đã chạy ở máy này trong lúc giao.
            for d in meta["du_an"]:
                goc_da = os.path.join(DL, DU_AN[d])
                luc_giao = giao.get("gui", {}).get(d, {})
                for rel in list(meta["gui"].get(d, {})) + meta["xoa"].get(d, []):
                    p = os.path.join(goc_da, rel)
                    if rel in luc_giao and os.path.isfile(p):
                        st = os.stat(p)
                        if [st.st_size, int(st.st_mtime)] != luc_giao[rel]:
                            canh_bao.append(f"{DU_AN[d]}/{rel}")
        # Tài khoản: token / hạn mức mới nhất của bên kia.
        os.makedirs(TKG, exist_ok=True)
        for m in ten_tep:
            phan = m.name.split("/")
            if phan[0] == "tk" and len(phan) == 3:
                t, f = phan[1], phan[2]
                d = CHINH if t == meta["chinh"] else os.path.join(TKG, t, ".config", "colab-cli")
                os.makedirs(d, exist_ok=True)
                if d != CHINH:
                    s = os.path.join(TKG, t, ".ssh")
                    if not os.path.lexists(s):
                        os.symlink(os.path.join(HOME, ".ssh"), s)
                    o = os.path.join(HOME, ".colab-cli-oauth-config.json")
                    if os.path.exists(o) and not os.path.lexists(os.path.join(TKG, t, ".colab-cli-oauth-config.json")):
                        os.symlink(o, os.path.join(TKG, t, ".colab-cli-oauth-config.json"))
                ghi_tep(tar, m, os.path.join(d, f))
                if f == "token.json":
                    os.chmod(os.path.join(d, f), 0o600)
        # Trạng thái: thư mục trạng thái vòng lặp lấy y bên kia (bỏ tệp cũ không theo pid trước).
        thu_muc_tt = {m.name.split("/")[1] for m in ten_tep if m.name.startswith("tkg/") and m.name.count("/") == 2}
        for d in thu_muc_tt:
            p = os.path.join(TKG, d)
            for g in (os.listdir(p) if os.path.isdir(p) else []):
                q = os.path.join(p, g)
                if os.path.isfile(q) and not RE_PID.match(g):
                    os.remove(q)
        for m in ten_tep:
            if m.name.startswith("tkg/"):
                ghi_tep(tar, m, os.path.join(TKG, m.name[4:]))
        # Dữ liệu.
        so = {}
        for m in ten_tep:
            phan = m.name.split("/", 2)
            if phan[0] == "du_lieu":
                ghi_tep(tar, m, os.path.join(DL, DU_AN[phan[1]], phan[2]))
                so[phan[1]] = so.get(phan[1], 0) + 1
        da_xoa = {}
        for d, ds in meta.get("xoa", {}).items():
            for rel in ds:
                p = os.path.join(DL, DU_AN[d], rel)
                if os.path.isfile(p):
                    os.remove(p)
                    da_xoa[d] = da_xoa.get(d, 0) + 1
    if meta["kieu"] == "day_du":
        ghi_json(GOC, {"phien": meta["phien"], "tu": meta["tu"], "luc_doc": meta["luc_doc"], "du_an": meta["du_an"],
                       "tep": {d: kiem_ke(os.path.join(DL, DU_AN[d])) for d in meta["du_an"]}})
    if os.path.exists(DA_GIAO):
        os.replace(DA_GIAO, DA_GIAO + ".da_nhan")
    print(f"[đã nhập] gói {'ĐẦY ĐỦ' if meta['kieu'] == 'day_du' else 'THAY ĐỔI (chiều về)'} từ "
          f"{'điện thoại' if meta['tu'] == 'dt' else 'máy tính'}, xuất lúc {meta['luc_doc']}")
    print(f"  tài khoản: {', '.join(meta['tk'])} (chính: {meta['chinh']})")
    for d in meta["du_an"]:
        print(f"  {DU_AN[d]}: ghi {so.get(d, 0)} tệp" + (f", xoá {da_xoa.get(d, 0)} tệp (gói ván đã gộp ở bên kia)"
                                                        if meta["kieu"] == "thay_doi" else ""))
    if canh_bao:
        print(f"[!] {len(canh_bao)} tệp ở máy này đã bị sửa trong lúc giao, nay bị thay bằng bản của máy kia, vd: "
              + ", ".join(canh_bao[:5]))
    khac = [k for k, v in meta.get("script", {}).items() if bam_script().get(k) not in (None, v)]
    if khac:
        print(f"[!] Script hai máy khác phiên bản ({', '.join(khac)}): cập nhật cả hai (bash ~/cv/cv_lay_ve.sh, bash ~/lay_ve.sh)")
    print("[xong] máy này cầm lái. Thoát menu (q) rồi mở lại để menu đọc tài khoản mới.")


def ghi_tep(tar, m, dich):
    os.makedirs(os.path.dirname(dich), exist_ok=True)
    tam = os.path.join(os.path.dirname(dich), ".tam_chuyen_" + os.path.basename(dich))
    with tar.extractfile(m) as nguon, open(tam, "wb") as f:
        shutil.copyfileobj(nguon, f, 1 << 20)
    os.replace(tam, dich)
    try:
        os.utime(dich, (m.mtime, m.mtime))
    except OSError:
        pass


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    menu_pid = int(a[a.index("--menu-pid") + 1]) if "--menu-pid" in a[:-1] else 0
    if a[0] == "tinh_trang":
        tinh_trang()
    elif a[0] == "khoa":
        sys.exit(0 if os.path.exists(DA_GIAO) else 1)
    elif a[0] == "xuat":
        du_an = a[a.index("--du-an") + 1].split(",") if "--du-an" in a[:-1] else list(DU_AN)
        if any(d not in DU_AN for d in du_an):
            sys.exit(f"[!] --du-an chỉ nhận {', '.join(DU_AN)}")
        xuat(du_an, menu_pid)
    elif a[0] == "nhap" and len(a) >= 2:
        nhap(a[1], menu_pid, "--ep" in a)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
