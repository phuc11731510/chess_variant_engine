# -*- coding: utf-8 -*-
"""Thu chay_t4_thu.py bang dien thoai + Colab GIA (khong mang, khong thue may): chon tai khoan, khoa dat cho, may MO COI (xin het gio ma may chu van cap),
ghi nho ben khi tien trinh bi giet.   python test_chay_t4_thu.py   (thoat 0 = dung het)"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("chay_t4_thu", os.path.join(AQUI, "chay_t4_thu.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
LOI = 0


def check(c, msg):
    global LOI
    print(("  [ok] " if c else "  [FAIL] ") + msg)
    LOI += (not c)


class Gia:
    """Dien thoai gia (tep trong ~/.fz_tk/.tu_dong) + Colab gia (phien cua tung tai khoan) + unassign gia."""

    def __init__(self, tk, quota=None):
        self.tk = tk
        self.tep = {}                       # 'khoa_ngoai_a1' -> epoch ...
        self.may = {}                       # tai khoan -> {ten: endpoint}  ("" = khong ten)
        self.new_rc = {}                    # tai khoan -> ma thoat cua `colab new` (mac dinh 0)
        self.cap_muon = {}                  # tai khoan -> endpoint se xuat hien sau `colab new` that bai (may chu cap muon)
        self.nhat = []                      # (lenh, tai khoan)
        self.tra = []
        self.quota = quota or {n: {"luc": time.time(), "con": 4500} for n in tk}
        self.thu_muc = tempfile.mkdtemp()

    # --- dien thoai ---
    def dt(self, cmd, inp=None, timeout=40):
        class R:
            returncode = 0
            stdout = ""
            stderr = ""
        r = R()
        if 'printf "S' in cmd:
            out = []
            for n in self.tk:
                out.append(f"S\t{n}\t{json.dumps(self.quota[n])}")
            for k, v in self.tep.items():
                mm = re.fullmatch(r"(xin_hong|xin_dang|thu|khoa_ngoai)_(.+)", k)
                if mm:
                    out.append(f"M\t{mm.group(1)}\t{mm.group(2)}\t{v}")
                elif k.startswith("may_"):
                    out.append(f"B\t{k[4:]}")
            r.stdout = "\n".join(out) + "\n"
            return r
        for mm in re.finditer(r"date \+%s > ~/.fz_tk/\.tu_dong/(xin_hong|khoa_ngoai)_(\S+?)(\.tam)?( &&|;|$)", cmd):
            if mm.group(3):
                self.tep.setdefault("__tam_" + mm.group(1) + "_" + mm.group(2), int(time.time()))
            else:
                self.tep[f"{mm.group(1)}_{mm.group(2)}"] = int(time.time())
        for mm in re.finditer(r"mv -f ~/.fz_tk/\.tu_dong/xin_hong_(\S+)\.tam", cmd):
            self.tep[f"xin_hong_{mm.group(1)}"] = int(time.time())
        for mm in re.finditer(r"rm -f ~/.fz_tk/\.tu_dong/khoa_ngoai_(\S+)", cmd):
            self.tep.pop(f"khoa_ngoai_{mm.group(1)}", None)
        return r

    # --- Colab ---
    def colab(self, name, *a, timeout=None, stream=False):
        class R:
            returncode = 0
            stdout = ""
            stderr = ""
        r = R()
        cmd = a[0]
        self.nhat.append((cmd, name))
        if cmd == "sessions":
            ds = self.may.get(name, {})
            if not ds:
                r.stdout = "[colab] No active sessions found on server.\n"
            else:
                r.stdout = "".join(f"[{t or '?'}] {ep} | Hardware: T4 | Status: ok\n" for t, ep in ds.items())
        elif cmd == "new":
            rc = self.new_rc.get(name, 0)
            if rc:
                if name in self.cap_muon:
                    self.may.setdefault(name, {})[""] = self.cap_muon[name]       # may chu cap may sau khi lenh cua ta bo
                r.returncode = rc
                r.stdout = "ReadTimeout"
            else:
                self.may.setdefault(name, {})[a[a.index("-s") + 1]] = f"ep-{name}"
        elif cmd == "stop":
            self.may.get(name, {}).pop(a[a.index("-s") + 1], None)
        return r

    def unassign(self, name, ep):
        d = self.may.get(name, {})
        for t in list(d):
            if d[t] == ep:
                del d[t]
                self.tra.append((name, ep))


def lap(g):
    """Gan ban gia vao module."""
    m.tai_khoan = lambda: list(g.tk)
    m.chi_so = lambda n: g.tk.index(n) + 1
    m.dt = g.dt
    m.colab = g.colab
    m.GHI_NHO = os.path.join(g.thu_muc, "dang_xin.json")
    m.chup = lambda name: False
    m.doc_chup_wsl = lambda name: None
    m.chup_va_ghi = lambda name, da_tra_may: True
    m.time.sleep = lambda s: None
    real_run = subprocess.run

    def run(argv, **kw):
        if argv and argv[0] == m.PY:                    # unassign: [PY, "-", endpoint], HOME = tai khoan
            name = os.path.basename(kw["env"]["HOME"].rstrip("/"))
            g.unassign(name, argv[2])

            class R:
                returncode = 0
                stdout = ""
                stderr = ""
            return R()
        return real_run(argv, **kw)
    m.subprocess.run = run


print("== 1. chon tai khoan: tranh dau hieu mem con han ==")
g = Gia(["a1", "a2", "a3", "a4", "a5"])
now = int(time.time())
g.tep.update({"xin_hong_a2": now - 60, "khoa_ngoai_a3": now - 600, "thu_a4": now - 5000, "xin_dang_a5": now - 30})
lap(g)
snaps, ban = m.trang_thai_dien_thoai()
check(ban == {"a2", "a3", "a5"}, f"tranh a2 (xin_hong), a3 (khoa_ngoai), a5 (xin_dang); a4 (thu cu 5000 s) thu duoc: {sorted(ban)}")
check(m.trang_thai_dien_thoai(mem=False)[1] == set(), "mem=False: khong tai khoan nao 'dang ban' (chi may_*)")
g.tep["may_a1"] = now
check("a1" in m.trang_thai_dien_thoai(mem=False)[1], "may_a1 (vong lap dang giu) luon la ban")

print("== 2. xin het gio + may chu cap muon: tra, tha khoa, giao cho dien thoai ==")
g = Gia(["a1"]); g.new_rc["a1"] = 124; g.cap_muon["a1"] = "gpu-muon-1"
lap(g)
rc = m.chay("ks.py", 15, 100)
check(rc == 2, f"khong chay duoc (tra 2): {rc}")
check(("a1", "gpu-muon-1") in g.tra and not g.may["a1"], f"may mo coi da duoc tra: {g.tra}")
check("khoa_ngoai_a1" not in g.tep, "khoa_ngoai da tha")
check("xin_hong_a1" in g.tep, "da ghi xin_hong_a1 cho vong lap tren dien thoai quet them 30 phut")
check(m.doc_ghi_nho() == [], "ghi nho ben da xoa")

print("== 3. tien trinh bi giet: ghi nho con sot -> lan sau (hoac --don) tra may, tha khoa ==")
g = Gia(["a1"]); g.may["a1"] = {"": "gpu-mo-coi-2"}
lap(g)
m.luu_ghi_nho([{"name": "a1", "ten": "a1", "t": time.time(), "pid": 999999}])
g.tep["khoa_ngoai_a1"] = int(time.time())
check(m.don_ghi_nho() == 1, "don_ghi_nho dung 1 tai khoan")
check(("a1", "gpu-mo-coi-2") in g.tra and "khoa_ngoai_a1" not in g.tep and m.doc_ghi_nho() == [], "tra may mo coi + tha khoa + xoa ghi nho")

print("== 4. lan chay khac cua ta con song: khong dung toi ==")
g = Gia(["a1"]); g.may["a1"] = {"": "gpu-cua-lan-chay-khac"}
lap(g)
m.luu_ghi_nho([{"name": "a1", "ten": "a1", "t": time.time(), "pid": os.getppid()}])
check(m.don_ghi_nho() == 0 and not g.tra, "pid con song -> bo qua, khong tra may")

print("== 5. khong bao gio dong may cua vong lap (may_*) ==")
g = Gia(["a1"]); g.may["a1"] = {"": "gpu-cua-vong-lap"}; g.tep["may_a1"] = int(time.time())
lap(g)
check(m.don_mo_coi("a1") == 0 and not g.tra, "tai khoan co may_a1: khong tra gi")

print("== 6. xin duoc may: chay, tra, tha khoa, khong ghi xin_hong ==")
g = Gia(["a1"])
lap(g)
rc = m.chay("ks.py", 15, 100)
check(rc == 0, f"chay xong (tra 0): {rc}")
check(("stop", "a1") in g.nhat and "khoa_ngoai_a1" not in g.tep and "xin_hong_a1" not in g.tep, "da tra may, tha khoa, khong ghi xin_hong")

print("== 7. lenh sessions het gio: bo qua tai khoan, van tha khoa ==")
g = Gia(["a1"])
lap(g)
orig = g.colab


def treo(name, *a, **kw):
    if a[0] == "sessions":
        raise subprocess.TimeoutExpired("colab", 60)
    return orig(name, *a, **kw)


m.colab = treo
check(m.chay("ks.py", 15, 100) == 2 and "khoa_ngoai_a1" not in g.tep and not any(c == "new" for c, _ in g.nhat), "khong xin may khi khong doc duoc phien; khoa da tha")

print(f"\nKET QUA: {'DUNG HET' if not LOI else str(LOI) + ' LOI'}")
sys.exit(1 if LOI else 0)
