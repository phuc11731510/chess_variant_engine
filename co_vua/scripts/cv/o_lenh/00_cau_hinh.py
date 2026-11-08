# Cấu hình: cách học, đời mạng hiện tại và đường dẫn
# ==================== CẤU HÌNH (chép theo ô 00 của fz) ====================
# Ô này được GHÉP VÀO ĐẦU mọi ô khi chạy (menu cv), nên mọi ô đều biết BEN, GEN_CURRENT và đường dẫn.
# Chạy tay từ menu: sửa BEN và GEN_CURRENT ở đây. Vòng lặp tự động (menu v) tự ghi hai số này vào bản chép
# của ô 00 cho từng việc (cách nào, đời nào), không đụng tệp này.
BEN = "tt"         # <--- cách học: "tt" = truyền thống, "cay" = cây trò chơi
GEN_CURRENT = 0    # <--- đời mạng hiện tại của cách BEN
# ==========================================================================

CV = "/content/cv"       # gói chạy: lc0 + mã Python (py/) + script Colab (colab/), từ Release REL
# Release `co_vua`: goi.tar.gz (lc0 + mã + script; co_vua/scripts/dong_goi.py --dang tạo).
REL = "https://github.com/phuc11731510/chess_variant_engine/releases/download/co_vua"
# Release `co_vua_mang`: .pt của MỌI đời mỗi cách + .pb.gz của đời mới nhất mỗi cách (vòng lặp tải mạng mới lên,
# xoá .pb.gz đời trước; .pb.gz đời cũ tạo lại từ .pt khi cần: py/lay_mang.py). Một Release chứa tối đa 1000 tệp.
REL_NN = "https://github.com/phuc11731510/chess_variant_engine/releases/download/co_vua_mang"
# Release `co_vua_du_lieu`: kho đệm dữ liệu huấn luyện (scripts/cv/kho.py trên điện thoại); ô 07 tải ở đây các tệp mà
# điện thoại không gửi lại (kho_ds.txt / nhan_doi<G>.kho.txt).
REL_DL = REL_NN.rsplit("/", 1)[0] + "/co_vua_du_lieu"

GEN_NEXT = GEN_CURRENT + 1

# Mạng: <cách>_gen<N>.pb.gz (lc0 chạy) và .pt (huấn luyện warm-start). Đời 0 của hai cách là CÙNG một mạng (ô 03).
CURRENT_PB = f"/content/{BEN}_gen{GEN_CURRENT}.pb.gz"
CURRENT_PT = f"/content/{BEN}_gen{GEN_CURRENT}.pt"
NEXT_PB = f"/content/{BEN}_gen{GEN_NEXT}.pb.gz"
NEXT_PT = f"/content/{BEN}_gen{GEN_NEXT}.pt"

# Sinh dữ liệu: mỗi lần chạy ô 04 là một thư mục lan_<giờ> trong thư mục ván của đời.
OUT_GAMES_DIR = f"/content/{BEN}_games_gen{GEN_CURRENT}"
# Đóng gói (ô 06) / gói gộp 4 đời để huấn luyện (vòng lặp gộp trên điện thoại, tải lên trước ô 07).
ZIP_GAMES = f"/content/{BEN}_games_gen{GEN_CURRENT}.zip"

# Thư viện CUDA / ONNX Runtime cho lc0 (colab/chuan_bi.sh ghi moi_truong.sh lúc ô 02).
import os
if os.path.exists(f"{CV}/moi_truong.sh"):
    _ld = open(f"{CV}/moi_truong.sh").read().split("LD_LIBRARY_PATH=", 1)[1].split(":${", 1)[0]
    if _ld not in os.environ.get("LD_LIBRARY_PATH", ""):
        os.environ["LD_LIBRARY_PATH"] = _ld + ":" + os.environ.get("LD_LIBRARY_PATH", "")


def tai_qua_api(rel, ten, dich):
    """Đường dự phòng khi github.com/.../releases/download/... lỗi (8/11: HTTP 504 với mọi tệp, trong lúc API vẫn
    chạy): tìm tệp trong Release qua api.github.com rồi tải bằng Accept: application/octet-stream (không cần token,
    tối đa 60 lần gọi API mỗi giờ mỗi IP). True = đã có dich."""
    import json, re, shutil, time, urllib.request
    m = re.match(r"https://github\.com/([^/]+/[^/]+)/releases/download/([^/]+)$", rel)
    if not m:
        return False
    api = f"https://api.github.com/repos/{m.group(1)}"
    for lan in (1, 2, 3):
        try:
            with urllib.request.urlopen(f"{api}/releases/tags/{m.group(2)}", timeout=60) as r:
                tep = [a for a in json.load(r)["assets"] if a["name"] == ten]
            if not tep:
                print(f"[api] Release {m.group(2)} không có {ten}")
                return False
            yc = urllib.request.Request(f"{api}/releases/assets/{tep[0]['id']}", headers={"Accept": "application/octet-stream"})
            with urllib.request.urlopen(yc, timeout=300) as r, open(dich + ".dang_tai", "wb") as f:
                shutil.copyfileobj(r, f, 1 << 20)
            if os.path.getsize(dich + ".dang_tai") != tep[0]["size"]:
                raise OSError("thiếu byte")
            os.replace(dich + ".dang_tai", dich)
            print(f"[api] đã tải {ten} qua api.github.com ({tep[0]['size']} byte)")
            return True
        except Exception as e:
            print(f"[api] {ten}: {e} (lần {lan}/3)")
            time.sleep(10)
    return False


def lay_kho(ds, goc):
    """Tải các tệp của kho đệm về goc/<đường dẫn>. ds = [(đường dẫn, tên trên Release REL_DL, cỡ)]. Thử thẳng (song song
    8 luồng), tệp nào lỗi thì qua api.github.com (một lần gọi liệt kê). Trả về danh sách đường dẫn KHÔNG tải được."""
    import json, re, shutil, time, urllib.request
    from concurrent.futures import ThreadPoolExecutor

    def mot(x, url, dau=None):
        p, ten, kt = x
        dich = os.path.join(goc, p)
        os.makedirs(os.path.dirname(dich), exist_ok=True)
        for lan in (1, 2):
            try:
                yc = urllib.request.Request(url, headers=dau or {})
                with urllib.request.urlopen(yc, timeout=120) as r, open(dich + ".dang_tai", "wb") as f:
                    shutil.copyfileobj(r, f, 1 << 20)
                if os.path.getsize(dich + ".dang_tai") == kt:
                    os.replace(dich + ".dang_tai", dich)
                    return True
            except Exception:
                time.sleep(3)
        return False

    t0 = time.time()
    with ThreadPoolExecutor(8) as ex:
        ok = list(ex.map(lambda x: mot(x, f"{REL_DL}/{x[1]}"), ds))
    loi = [x for x, o in zip(ds, ok) if not o]
    if loi:
        m = re.match(r"https://github\.com/([^/]+/[^/]+)/releases/download/([^/]+)$", REL_DL)
        api = f"https://api.github.com/repos/{m.group(1)}"
        try:
            with urllib.request.urlopen(f"{api}/releases/tags/{m.group(2)}", timeout=60) as r:
                rid = json.load(r)["id"]
            tep, trang = {}, 1
            while True:
                with urllib.request.urlopen(f"{api}/releases/{rid}/assets?per_page=100&page={trang}", timeout=60) as r:
                    lo = json.load(r)
                tep.update({a["name"]: a["id"] for a in lo})
                if len(lo) < 100:
                    break
                trang += 1
            with ThreadPoolExecutor(4) as ex:
                ok2 = list(ex.map(lambda x: x[1] in tep and mot(x, f"{api}/releases/assets/{tep[x[1]]}",
                                                                 {"Accept": "application/octet-stream"}), loi))
            loi = [x for x, o in zip(loi, ok2) if not o]
        except Exception as e:
            print(f"[kho] api.github.com: {e}")
    mb = sum(x[2] for x in ds if x not in loi) / 1e6
    print(f"[kho] tải {len(ds) - len(loi)}/{len(ds)} tệp ({mb:.0f} MB) từ kho đệm, {time.time() - t0:.0f} giây"
          + (f" -- THIẾU {len(loi)} tệp" if loi else ""), flush=True)
    return [x[0] for x in loi]


print(f"[Cấu hình] CÁCH {BEN} · ĐỜI {GEN_CURRENT} -> ĐỜI {GEN_NEXT}")
