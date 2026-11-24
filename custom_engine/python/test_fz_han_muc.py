"""Kiem thu phan HIEN THI / GHI NHAN "bi tu choi" cua scripts/colab_cells/fz_han_muc.py (chay tren dien thoai, khong hoi mang):
  A. T4 bi tu choi khi han muc con NHIEU (>= 2 gio T4): in "Colab tam het T4 ... KHONG phai het han muc", KHONG in "HET" (2026-11-24: tranlongn28 bi 412 luc con
     3 gio 31 phut, `h` in HET, bam m van muon duoc).
  B. T4 bi tu choi khi han muc con IT (< 2 gio): van in HET.
  C. `--het-xoa` (xin_may goi khi T4 vua DUOC cap) xoa dau bi tu choi: sau do in "con ...", khong con ghi nhan bi tu choi.
  D. Khong co lan chup / khong bi tu choi: in nhu cu.
Chay:  python test_fz_han_muc.py
"""
import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "colab_cells", "fz_han_muc.py")
PASS = FAIL = 0


def check(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [ok] {msg}")
    else:
        FAIL += 1
        print(f"  [FAIL] {msg}")


def chay(home, *args):
    env = dict(os.environ, HOME=home, USERPROFILE=home, NO_COLOR="1", PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, SCRIPT, *args], env=env, capture_output=True, text=True, encoding="utf-8")
    return p.stdout.strip()


def ghi(home, d):
    f = os.path.join(home, ".config", "colab-cli", "fz_han_muc.json")
    os.makedirs(os.path.dirname(f), exist_ok=True)
    json.dump(d, open(f, "w"))
    return f


def main():
    now = int(time.time())
    with tempfile.TemporaryDirectory() as home:
        print("A. bi tu choi khi con nhieu han muc")
        ghi(home, {"luc": now - 10, "con": 3765, "nap_lai": now + 80000, "het_luc": now - 200, "con_khi_tu_choi": 3765})
        out = chay(home, "--dong")
        check("tạm hết T4" in out and "KHÔNG phải hết hạn mức" in out and "HẾT" not in out, f"--dong: {out[:130]}...")
        out = chay(home, "--khoi")
        check("HẾT" not in out and "Colab tạm hết T4" in out, f"--khoi: {out.splitlines()[0]!r}")
        print("B. bi tu choi khi con it")
        ghi(home, {"luc": now - 10, "con": 800, "nap_lai": now + 80000, "het_luc": now - 200, "con_khi_tu_choi": 800})
        out = chay(home, "--dong")
        check(out.startswith("HẾT") and "tạm hết T4" not in out, f"--dong: {out[:80]}")
        check("HẾT" in chay(home, "--khoi"), "--khoi in HẾT")
        print("C. --het-xoa khi T4 vua duoc cap")
        ghi(home, {"luc": now - 10, "con": 3765, "nap_lai": now + 80000, "het_luc": now - 200, "con_khi_tu_choi": 3765})
        chay(home, "--het-xoa")
        d = json.load(open(os.path.join(home, ".config", "colab-cli", "fz_han_muc.json")))
        check("het_luc" not in d and "con_khi_tu_choi" not in d, f"da xoa dau bi tu choi, giu {sorted(d)}")
        out = chay(home, "--dong")
        check(out.startswith("còn 3.77 đơn vị") and "HẾT" not in out and "tạm hết" not in out, f"--dong: {out[:100]}")
        print("D. khong co dau bi tu choi / khong co lan chup")
        out2 = chay(home, "--het-xoa")
        check(out2 == "", "--het-xoa khi khong co dau: im lang")
        with tempfile.TemporaryDirectory() as home2:
            out = chay(home2, "--dong")
            check("chưa chụp" in out, f"chua chup: {out}")
            chay(home2, "--het-xoa")
            check(not os.path.exists(os.path.join(home2, ".config", "colab-cli", "fz_han_muc.json")), "--het-xoa khong tao tep khi chua chup")
    print("\n" + "=" * 60)
    print(f"RESULT: {PASS} passed, {FAIL} failed")
    print("=" * 60)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
