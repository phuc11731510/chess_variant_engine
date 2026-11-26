#!/usr/bin/env python3
"""chay_t4_thu.py -- thue MOT may T4 ngan de thu nghiem, roi tra may VA ghi han muc moi len dien thoai.

  python3 ~/chay_t4_thu.py <kich_ban.py> [--can-phut 15] [--timeout 1500] [--tep LOCAL:REMOTE ...]   # thue T4, chay, tra, ghi han muc
                                                                             #  --tep: dua tep tu may nay len may T4 truoc khi chay (khong qua Release)
  python3 ~/chay_t4_thu.py --ghi-han-muc <chi_so>                           # chi doc lai han muc cua tai khoan thu <chi_so>
                                                                             #  (bang may CPU tam) va ghi len dien thoai
  python3 ~/chay_t4_thu.py --don                                            # tra may mo coi con sot tu lan chay truoc (bi giet giua chung), tha khoa
Quy tac (chu du an cho phep 2026-11-20): chi muon tai khoan KHONG ban (khong co trong ~/.fz_tk/.tu_dong/may_* hoac .cv_tu_dong/may_* (vong lap fz va vong lap cv) tren dien thoai
va `colab sessions` rong) va con du han muc (theo lan chup tren dien thoai, roi do lai khi da giu may). Chon tai khoan VUA DU
(con it nhat nhung van du, de lai tai khoan nhieu han muc cho vong lap). Dung xong: doc han muc luc con giu may (may chu chi tra
khi dang giu may), tra may, ghi lan chup moi vao dien thoai (~/.fz_tk/<tk>/.config/colab-cli/fz_han_muc.json, atomic; khong ghi
neu dien thoai da co lan chup moi hon). Chi in CHI SO tai khoan (thu tu trong ~/.fz_tk), khong in ten, khong dung token.

DONG BO VOI VONG LAP TREN DIEN THOAI (2026-11-25) -- may chu Colab la noi chung duy nhat, nen hai ben nhan nhau bang tep tren dien thoai
(~/.fz_tk/.tu_dong/, xem menu.sh "MAY MO COI"):
  * khoa_ngoai_<tk>  TA ghi truoc khi xin may (dong 1 = epoch), xoa khi xong: vong lap KHONG xin / KHONG quet tai khoan do (het han sau 2 gio neu ta chet).
  * ta TRANH tai khoan co: may_<tk> (vong lap dang giu), xin_dang_<tk> (vong lap dang xin), xin_hong_<tk> (vong lap con cho may cap muon),
    thu_<tk> moi (vong lap vua xin), khoa_ngoai_<tk> (mot lan chay khac cua ta).
  * MAY MO COI: `colab new` het gio cho ma may chu van cap may. Sau moi lan xin hong ta quet NGAY, roi +100 s, +300 s; xong thi ghi xin_hong_<tk>
    len dien thoai de vong lap tiep tuc quet them 30 phut. Ghi nho ben trong ~/.chay_t4_thu_dang_xin.json (song sot khi tien trinh bi giet):
    lan chay sau (hoac --don) tra may mo coi va tha khoa.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

FZ = os.path.expanduser("~/.fz_tk")
COLAB = "/root/.local/bin/colab"
PY = "/root/.local/share/uv/tools/google-colab-cli/bin/python"
HM_DIR = "/mnt/d/chess_variant/custom_engine/scripts/colab_cells"      # fz_han_muc.py + fz_colab.py ban moi nhat
T4 = 1.07           # CCU/gio cua mot T4 (nhu fz_han_muc.py)
VONG_LAP_TOI_THIEU = 1.25   # gio T4 toi thieu vong lap con xin (fz_tu_dong.py GIO_T4_TOI_THIEU)
MAY = "thu"
GHI_NHO = os.path.expanduser("~/.chay_t4_thu_dang_xin.json")
# Han cua cac dau hieu mem tren dien thoai (giay): thay mot dau con han thi KHONG thu tai khoan do.
HAN_DAU = {"xin_hong": 1800, "xin_dang": 400, "thu": 900, "khoa_ngoai": 7200}
QUET_SAU = (100, 200)       # cac moc quet may mo coi sau lan xin hong cuoi: +100 s, roi +200 s nua (= +300 s)


def norm(s):
    return re.sub(r"^_+|_+$", "", s).lower()


def tai_khoan():
    return sorted(d for d in os.listdir(FZ) if os.path.isdir(os.path.join(FZ, d)) and not d.startswith("."))


def chi_so(name):
    return tai_khoan().index(name) + 1


def tat_cap_nhat(home):
    """Tat kiem tra cap nhat cua Colab CLI cho mot HOME tai khoan ("enable_update_check": false trong ~/.config/colab-cli/settings.json, giu cac
    khoa khac). Chu du an 2026-11-26: khong muon thay loi nhac cap nhat (va KHONG BAO GIO nang cap CLI); goi truoc moi lenh colab nen tai khoan
    moi cung tu tat. Loi doc / ghi thi bo qua (khong chan lenh)."""
    p = os.path.join(home, ".config", "colab-cli", "settings.json")
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    if d.get("enable_update_check") is False:
        return
    d["enable_update_check"] = False
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p + ".fz", "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2)
        os.replace(p + ".fz", p)
    except OSError:
        pass


def colab(name, *args, timeout=None, stream=False):
    env = dict(os.environ, HOME=os.path.join(FZ, name))
    tat_cap_nhat(env["HOME"])
    if stream:
        return subprocess.run([COLAB, *args], env=env, timeout=timeout)
    return subprocess.run([COLAB, *args], env=env, capture_output=True, text=True, timeout=timeout)


def dt(cmd, inp=None, timeout=40):
    return subprocess.run(["ssh", "-o", "ConnectTimeout=8", "dt", cmd], input=inp, capture_output=True, text=True,
                          timeout=timeout)


def doc_chup_wsl(name):
    try:
        with open(os.path.join(FZ, name, ".config/colab-cli/fz_han_muc.json")) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def chup(name):
    """Doc han muc tu may chu (chi co khi dang giu may) va luu o ban sao WSL. True neu chup duoc."""
    env = dict(os.environ, HOME=os.path.join(FZ, name))
    r = subprocess.run([PY, os.path.join(HM_DIR, "fz_han_muc.py"), "--chup"], env=env, cwd=HM_DIR,
                       capture_output=True, text=True, timeout=120)
    return r.returncode == 0


def trang_thai_dien_thoai(mem=True):
    """({ten: lan chup}, {ten tai khoan KHONG nen thu, da chuan hoa}) doc tu dien thoai.
    mem=False: chi tai khoan vong lap DANG GIU may (may_*). mem=True: them tai khoan co dau hieu mem con han (HAN_DAU)."""
    r = dt('cd ~/.fz_tk && for d in */; do n=${d%/}; f="$d.config/colab-cli/fz_han_muc.json"; printf "S\\t%s\\t" "$n"; '
           'if [ -f "$f" ]; then tr -d "\\n" < "$f"; else printf "{}"; fi; echo; done; '
           'for f in .tu_dong/may_* .cv_tu_dong/may_*; do [ -e "$f" ] && printf "B\\t%s\\n" "${f##*/may_}"; done; '
           'for k in xin_hong xin_dang thu khoa_ngoai; do for f in .tu_dong/${k}_*; do [ -f "$f" ] || continue; '
           'case "$f" in *.tam|*.quet) continue;; esac; printf "M\\t%s\\t%s\\t%s\\n" "$k" "${f##*/${k}_}" "$(head -1 "$f" 2>/dev/null)"; done; done; true')
    if r.returncode != 0:
        raise RuntimeError("khong noi duoc dien thoai (ssh dt): " + r.stderr.strip()[-200:])
    snaps, ban, now = {}, set(), time.time()
    for ln in r.stdout.splitlines():
        p = ln.split("\t")
        if p[0] == "S" and len(p) >= 3:
            try:
                snaps[p[1]] = json.loads(p[2])
            except ValueError:
                snaps[p[1]] = {}
        elif p[0] == "B" and len(p) >= 2:
            ban.add(norm(p[1]))
        elif mem and p[0] == "M" and len(p) >= 4 and p[3].strip().isdigit():
            if now - int(p[3]) < HAN_DAU.get(p[1], 0):
                ban.add(norm(p[2]))
    return snaps, ban


def ten_dt(name, snaps):
    """Ten thu muc cua tai khoan nay tren dien thoai (co the khac dau gach duoi dau / cuoi), None neu dien thoai khong co."""
    return next((n for n in snaps if norm(n) == norm(name)), None)


def xep(snaps, ban, can_gio):
    now, out = time.time(), []
    for name, ch in snaps.items():
        if norm(name) in ban or name not in tai_khoan():
            continue
        nap, luc, het = ch.get("nap_lai"), ch.get("luc", 0), ch.get("het_luc", 0)
        bi_tu_choi = bool(het) and (het >= luc or "con_khi_tu_choi" in ch)
        da_nap = bool(nap) and now >= nap and luc < nap and not (bi_tu_choi and het >= nap)
        if da_nap:
            out.append((1, 0.0, name))
        elif bi_tu_choi:
            continue
        elif ch.get("con") is None:
            out.append((2, 0.0, name))
        else:
            gio = ch["con"] / 1000 / T4
            if gio >= can_gio + VONG_LAP_TOI_THIEU:
                out.append((0, gio, name))          # vua du nhat truoc
    return [n for _, _, n in sorted(out)]


def day_len_dien_thoai(name, snap):
    """Ghi lan chup moi len dien thoai (atomic), tru khi dien thoai da co lan chup moi hon."""
    snaps, _ = trang_thai_dien_thoai(mem=False)
    ten = ten_dt(name, snaps)
    if ten is None:
        print("[t4] dien thoai khong co thu muc tai khoan nay -- khong ghi")
        return False
    cu = snaps.get(ten) or {}
    if cu.get("luc", 0) >= snap.get("luc", 0):
        print("[t4] dien thoai da co lan chup moi hon -- giu nguyen")
        return False
    p = f"~/.fz_tk/{ten}/.config/colab-cli/fz_han_muc.json"
    r = dt(f"cat > {p}.tam && mv {p}.tam {p}", inp=json.dumps(snap))
    if r.returncode != 0:
        print("[t4] ghi len dien thoai LOI:", r.stderr.strip()[-200:])
        return False
    con = snap.get("con")
    print(f"[t4] da ghi han muc len dien thoai (tai khoan so {chi_so(name)}): "
          + (f"con {con / 1000:.2f} CCU ~ {con / 1000 / T4:.2f} gio T4" if con is not None else "khong ro con bao nhieu")
          + (f", nap lai luc {time.strftime('%H:%M %d/%m', time.localtime(snap['nap_lai']))}" if snap.get("nap_lai") else ""))
    return True


def chup_va_ghi(name, da_tra_may):
    if not chup(name):
        print("[t4] khong doc duoc han muc (may chu chi tra khi dang giu may)")
        return False
    snap = doc_chup_wsl(name)
    if not snap:
        return False
    if da_tra_may:
        snap = dict(snap, so_may=0)
    return day_len_dien_thoai(name, snap)


def tai_khoan_moi_nhat():
    """Tai khoan co colab.log ghi gan day nhat (= vua giu / tra may)."""
    def t(n):
        try:
            return os.path.getmtime(os.path.join(FZ, n, ".config/colab-cli/colab.log"))
        except OSError:
            return 0
    return max(tai_khoan(), key=t)


def ghi_han_muc_cpu(idx):
    name = tai_khoan_moi_nhat() if str(idx) == "moi" else tai_khoan()[int(idx) - 1]
    s = colab(name, "sessions", timeout=60)
    if "No active sessions" not in s.stdout + s.stderr:
        print("[t4] tai khoan dang giu may -- khong thue them")
        return 1
    n = colab(name, "new", "-s", "hm", timeout=300)
    if n.returncode != 0:
        print("[t4] khong tao duoc may CPU:", (n.stdout + n.stderr).strip()[-200:])
        return 1
    try:
        ok = chup_va_ghi(name, da_tra_may=True)
    finally:
        colab(name, "stop", "-s", "hm", timeout=120)
    return 0 if ok else 1


# ---------------------------------------------------------------------------------------------- khoa + may mo coi
def doc_ghi_nho():
    try:
        with open(GHI_NHO) as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def luu_ghi_nho(ds):
    tam = GHI_NHO + ".tam"
    with open(tam, "w") as f:
        json.dump(ds, f)
    os.replace(tam, GHI_NHO)


def khoa(name, ten):
    """Dat cho truoc tren dien thoai (khoa_ngoai_<tk>) va ghi nho ben. True neu da dat duoc (khong dat duoc -> khong dung tai khoan nay)."""
    try:
        r = dt(f"mkdir -p ~/.fz_tk/.tu_dong && date +%s > ~/.fz_tk/.tu_dong/khoa_ngoai_{ten}")
    except Exception:        # noqa: BLE001
        return False
    if r.returncode != 0:
        return False
    luu_ghi_nho([x for x in doc_ghi_nho() if x.get("name") != name]
                + [{"name": name, "ten": ten, "t": time.time(), "pid": os.getpid()}])
    return True


def nha_khoa(name, ten, giao_cho_dien_thoai=False):
    """Tha khoa. giao_cho_dien_thoai: ghi xin_hong_<tk> de vong lap tren dien thoai tiep tuc quet may mo coi them 30 phut."""
    cmd = f"rm -f ~/.fz_tk/.tu_dong/khoa_ngoai_{ten}"
    if giao_cho_dien_thoai:
        p = f"~/.fz_tk/.tu_dong/xin_hong_{ten}"
        cmd = f"date +%s > {p}.tam && mv -f {p}.tam {p}; " + cmd
    try:
        dt(cmd)
    except Exception:        # noqa: BLE001
        pass
    luu_ghi_nho([x for x in doc_ghi_nho() if x.get("name") != name])


def don_mo_coi(name):
    """Tra may T4 'mo coi': `colab new` het gio cho (120 s) ma may chu van cap may -> may do giu han muc va khong ai tra
    (dien thoai thay tai khoan 'dang giu may' va bo qua). Chi dong may khong ten ([?]) o tai khoan ta DA kiem la khong co phien
    nao truoc khi xin, va tai khoan khong co may_* (vong lap dang giu) tren dien thoai luc nay. Tra ve so may da tra."""
    try:
        _, ban = trang_thai_dien_thoai(mem=False)
    except Exception:       # noqa: BLE001 - khong chac dien thoai co dang dung tai khoan nay -> khong dong
        return 0
    if norm(name) in ban:
        return 0
    try:
        s = colab(name, "sessions", timeout=90)
    except subprocess.TimeoutExpired:
        return 0
    n = 0
    env = dict(os.environ, HOME=os.path.join(FZ, name))
    for ln in (s.stdout or "").splitlines():
        if not ln.startswith("[?]"):
            continue
        ep = ln.split("] ", 1)[1].split()[0]
        r = subprocess.run([PY, "-", ep], input="import sys\nfrom colab_cli.common import state\nstate.client.unassign(sys.argv[1])\n",
                           env=env, capture_output=True, text=True, timeout=120)
        n += r.returncode == 0
    if n:
        print(f"[t4] da tra {n} may mo coi cua tai khoan so {chi_so(name)}", flush=True)
    return n


def don_ghi_nho():
    """Lan chay truoc bi giet giua chung (ghi nho con sot, tien trinh do khong con): tra may mo coi, tha khoa. Tra ve so tai khoan da don."""
    n = 0
    for x in doc_ghi_nho():
        pid = x.get("pid")
        if pid and pid != os.getpid():
            try:
                os.kill(pid, 0)
                continue                    # lan chay khac cua ta van song: khong dung toi
            except OSError:
                pass
        name = x.get("name")
        if name in tai_khoan():
            don_mo_coi(name)
            nha_khoa(name, x.get("ten") or name, giao_cho_dien_thoai=True)
            n += 1
        else:
            luu_ghi_nho([y for y in doc_ghi_nho() if y is not x and y.get("name") != name])
    return n


def chay(kich_ban, can_phut, timeout, tep=()):
    can_gio = can_phut / 60
    don_ghi_nho()
    snaps, ban = trang_thai_dien_thoai()
    thu_tu = xep(snaps, ban, can_gio)
    print(f"[t4] {len(ban)} tai khoan dang ban / vua duoc vong lap dung (dien thoai); {len(thu_tu)} tai khoan co the thu")
    that_bai = []
    try:
        return _chay_vong(kich_ban, can_phut, timeout, tep, can_gio, thu_tu, snaps, that_bai)
    finally:
        if that_bai:
            for cho in QUET_SAU:           # may chu co the cap T4 MUON (sau khi ta bo yeu cau): quet lai cac tai khoan da thu hong
                time.sleep(cho)
                for name, _ in that_bai:
                    don_mo_coi(name)
            for name, ten in that_bai:     # het cach: giao cho vong lap tren dien thoai quet them 30 phut
                nha_khoa(name, ten, giao_cho_dien_thoai=True)


def _chay_vong(kich_ban, can_phut, timeout, tep, can_gio, thu_tu, snaps, that_bai):
    for name in thu_tu[:8]:
        ten = ten_dt(name, snaps)
        if ten is None or not khoa(name, ten):
            continue                       # dien thoai khong co tai khoan nay / khong dat duoc khoa -> khong lieu
        giu_khoa = False
        try:
            try:
                s = colab(name, "sessions", timeout=60)
            except subprocess.TimeoutExpired:
                continue
            if "No active sessions" not in s.stdout + s.stderr:
                continue
            print(f"[t4] thu tai khoan so {chi_so(name)}", flush=True)
            try:
                n = colab(name, "new", "--gpu", "T4", "-s", MAY, timeout=300)
            except subprocess.TimeoutExpired:
                n = None
            if n is None or n.returncode != 0:
                print("[t4] khong tao duoc may T4:", "(het gio)" if n is None else (n.stdout + n.stderr).strip()[-160:])
                that_bai.append((name, ten))
                giu_khoa = True            # giu khoa cho den khi quet muon xong (chay() quet roi giao cho dien thoai)
                don_mo_coi(name)
                continue
            da_chay = False
            try:
                if chup(name):
                    sn = doc_chup_wsl(name) or {}
                    if sn.get("con") is not None and sn["con"] / 1000 / T4 < can_gio + 0.1:
                        print("[t4] han muc that con it hon can -- bo tai khoan nay")
                        continue
                for cap in tep:
                    local, remote = cap.split(":", 1)
                    u = colab(name, "upload", local, remote, "-s", MAY, timeout=300)
                    print(f"[t4] dua {os.path.basename(local)} len may: " + ("xong" if u.returncode == 0 else "LOI " + (u.stdout + u.stderr).strip()[-160:]),
                          flush=True)
                colab(name, "exec", "-s", MAY, "-f", kich_ban, "--timeout", str(timeout), stream=True)
                da_chay = True
                chup_va_ghi(name, da_tra_may=True)      # con giu may -> may chu moi tra han muc
            finally:
                colab(name, "stop", "-s", MAY, timeout=120)
                print("[t4] da tra may;", colab(name, "sessions", timeout=60).stdout.strip()[-60:])
            if da_chay:
                return 0
        finally:
            if not giu_khoa:
                nha_khoa(name, ten)
    print("[t4] khong chay duoc tren tai khoan nao")
    return 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kich_ban", nargs="?")
    ap.add_argument("--can-phut", type=float, default=15)
    ap.add_argument("--timeout", type=int, default=1500)
    ap.add_argument("--tep", action="append", default=[], help="LOCAL:REMOTE (duong dan tren may nay : tren may T4), lap lai duoc")
    ap.add_argument("--ghi-han-muc", help="chi so tai khoan (1..N), hoac \"moi\" = tai khoan vua dung may gan day nhat")
    ap.add_argument("--don", action="store_true", help="tra may mo coi con sot tu lan chay truoc, tha khoa tren dien thoai, roi thoat")
    a = ap.parse_args()
    if a.don:
        print(f"[t4] da don {don_ghi_nho()} tai khoan")
        return 0
    if a.ghi_han_muc:
        return ghi_han_muc_cpu(a.ghi_han_muc)
    if not a.kich_ban:
        ap.error("can kich ban hoac --ghi-han-muc / --don")
    return chay(a.kich_ban, a.can_phut, a.timeout, a.tep)


if __name__ == "__main__":
    sys.exit(main())
