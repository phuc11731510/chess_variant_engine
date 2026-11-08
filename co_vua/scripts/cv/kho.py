"""kho.py -- kho đệm dữ liệu huấn luyện trên GitHub Release `co_vua_du_lieu` (8/11), chạy trên điện thoại.

Mỗi đời, máy huấn luyện (Colab, máy mới) cần cả cửa sổ dữ liệu: cách truyền thống mau.npz của 4 đời, cách cây các
mau.npz chứa mặt phẳng của mọi node còn sống (kể cả node tạo từ đời 0). Trước đây điện thoại gửi lại toàn bộ mỗi đời
(cây đời 6: 575 MB, truyền thống: 697 MB), dù phần lớn đã gửi ở đời trước. Nay:
  - lúc gộp, `chia` tách các tệp >= 1 MB đã có trên Release (cùng tên, cùng cỡ) ra khỏi gói gửi thẳng; danh sách
    các tệp đó đi kèm gói, ô 07 tự tải chúng từ Release (đường dự phòng qua api.github.com như ô 02);
  - `khoi_len` mở một tiến trình nền: đợi mạng đời sau có trên điện thoại (huấn luyện xong), rồi đưa các tệp còn
    thiếu lên Release và xoá các tệp của cách đó không còn trong cửa sổ.
Không đọc được Release (mạng, gh) thì coi như kho trống: gửi thẳng tất cả, như trước. Tệp nhỏ (< 1 MB) luôn gửi thẳng.

  python kho.py len <thư mục cách> <cách> <đời>     # tiến trình nền (khoi_len gọi), log: Download/CoVua/log/kho.log
"""
import json
import os
import re
import subprocess
import sys
import time

TAG = os.environ.get("CV_KHO_TAG", "co_vua_du_lieu")     # đổi được để thử trên một Release riêng
NGUONG = 1 << 20
REPO_MAC_DINH = "phuc11731510/chess_variant_engine"
TD = os.path.expanduser("~/.fz_tk/.cv_tu_dong")


def repo(cach_dir):
    f = os.path.join(os.path.dirname(os.path.abspath(cach_dir)), "o_lenh", "00_cau_hinh.py")
    try:
        m = re.search(r'^REL_NN *= *"https://github\.com/([^/]+/[^/]+)/releases/download/', open(f, encoding="utf-8-sig").read(), re.M)
        return m.group(1) if m else REPO_MAC_DINH
    except OSError:
        return REPO_MAC_DINH


def ten_asset(cach, arc):
    return f"{cach}__" + arc.replace("/", "__")


def gh(*a, timeout=600):
    return subprocess.run(["gh", *a], capture_output=True, text=True, timeout=timeout)


def ds_kho(rp):
    """{tên: cỡ} các tệp trên Release, hoặc None nếu không đọc được."""
    try:
        r = gh("release", "view", TAG, "-R", rp, "--json", "assets", timeout=120)
        return {x["name"]: x["size"] for x in json.loads(r.stdout)["assets"]} if r.returncode == 0 else None
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired):
        return None


def chia(cach_dir, cach, muc):
    """muc: [(arc, đường dẫn trên điện thoại)]. Trả về (gửi thẳng [(arc, đường dẫn)], lấy từ kho [(arc, tên, cỡ)])."""
    co = ds_kho(repo(cach_dir)) or {}
    gui, kho = [], []
    for arc, p in muc:
        kt = os.path.getsize(p)
        t = ten_asset(cach, arc)
        if kt >= NGUONG and co.get(t) == kt:
            kho.append((arc, t, kt))
        else:
            gui.append((arc, p))
    return gui, kho


def khoi_len(cach_dir, cach, g, muc):
    """Ghi danh sách cửa sổ của đời g rồi mở tiến trình nền đưa lên kho sau khi huấn luyện xong."""
    try:
        with open(os.path.join(cach_dir, f".kho_gen{g}.json"), "w", encoding="utf-8") as f:
            json.dump([[a, p, os.path.getsize(p)] for a, p in muc if os.path.getsize(p) >= NGUONG], f)
        log = open(os.path.join(os.path.dirname(os.path.abspath(cach_dir)), "log", "kho.log"), "a", encoding="utf-8")
        subprocess.Popen([sys.executable, os.path.abspath(__file__), "len", cach_dir, cach, str(g)], stdin=subprocess.DEVNULL,
                         stdout=log, stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
    except OSError as e:
        print(f"[kho] không mở được tiến trình đưa lên kho: {e}")


def ghi(*a):
    print(time.strftime("%Y-%m-%d %H:%M:%S"), *a, flush=True)


def len_kho(cach_dir, cach, g):
    g = int(g)
    khoa = os.path.join(TD, f"kho_len_{cach}")
    try:
        os.makedirs(khoa)
    except FileExistsError:
        try:
            pid = int(open(os.path.join(khoa, "pid")).read())
            if os.path.exists(f"/proc/{pid}"):
                ghi(f"[kho {cach} đời {g}] tiến trình {pid} đang đưa lên -- thôi")
                return
        except (OSError, ValueError):
            pass
    with open(os.path.join(khoa, "pid"), "w") as f:
        f.write(str(os.getpid()))
    try:
        mang = os.path.join(cach_dir, f"gen{g + 1}.pb.gz")
        han = time.time() + 12 * 3600
        while not os.path.exists(mang):
            if time.time() > han or os.path.exists(os.path.join(cach_dir, f".kho_gen{g + 1}.json")):
                ghi(f"[kho {cach} đời {g}] chưa thấy {os.path.basename(mang)} -- thôi")
                return
            time.sleep(60)
        muc = json.load(open(os.path.join(cach_dir, f".kho_gen{g}.json"), encoding="utf-8"))
        rp = repo(cach_dir)
        co = ds_kho(rp)
        if co is None:
            r = gh("release", "create", TAG, "-R", rp, "--title", TAG, "--notes",
                   "Kho đệm dữ liệu huấn luyện của dự án cờ vua (scripts/cv/kho.py): mau.npz của các lần sinh, "
                   "đưa lên một lần để máy huấn luyện tự tải thay vì điện thoại gửi lại mỗi đời.")
            co = ds_kho(rp)
            if co is None:
                ghi(f"[kho {cach} đời {g}] không đọc / tạo được Release {TAG}: {r.stderr.strip()[:200]}")
                return
        can = {ten_asset(cach, a): (p, kt) for a, p, kt in muc}
        ln = os.path.join(khoa, "ln")
        os.makedirs(ln, exist_ok=True)
        moi = [t for t, (p, kt) in can.items() if co.get(t) != kt and os.path.exists(p) and os.path.getsize(p) == kt]
        for t in moi:
            if t in co:
                gh("release", "delete-asset", TAG, t, "-R", rp, "-y")
            if os.path.lexists(os.path.join(ln, t)):
                os.remove(os.path.join(ln, t))
            os.symlink(can[t][0], os.path.join(ln, t))
        len_ok = loi = 0
        for i in range(0, len(moi), 4):
            lo = moi[i:i + 4]
            for lan in range(3):
                r = gh("release", "upload", TAG, *[os.path.join(ln, t) for t in lo], "-R", rp, "--clobber", timeout=3600)
                if r.returncode == 0:
                    len_ok += len(lo)
                    break
                time.sleep(30)
            else:
                loi += len(lo)
                ghi(f"[kho {cach} đời {g}] lỗi đưa lên {lo}: {r.stderr.strip()[:200]}")
        bo = [t for t in co if t.startswith(f"{cach}__") and t not in can]
        for t in bo:
            gh("release", "delete-asset", TAG, t, "-R", rp, "-y")
        mb = sum(can[t][1] for t in moi) / 1e6
        ghi(f"[kho {cach} đời {g}] đưa lên {len_ok}/{len(moi)} tệp ({mb:.0f} MB), xoá {len(bo)} tệp ngoài cửa sổ, "
            f"kho giữ {len(can)} tệp" + (f", {loi} tệp lỗi (đời sau gửi thẳng)" if loi else ""))
        for t in os.listdir(ln):
            os.remove(os.path.join(ln, t))
        for k in range(max(0, g - 3), g):
            try:
                os.remove(os.path.join(cach_dir, f".kho_gen{k}.json"))
            except OSError:
                pass
    finally:
        try:
            os.remove(os.path.join(khoa, "pid"))
        except OSError:
            pass


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "len":
        len_kho(*sys.argv[2:5])
    else:
        sys.exit(__doc__)
