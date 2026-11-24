"""Kiem thu fz_may.py (phan chay tren may Colab): o sinh du lieu lien tuc 04_<run> chay SONG SONG, cac o khac van chi mot o moi may.

Chay tren Linux (WSL / Colab) co IPython; Windows thi bo qua. Dung thu muc tam (FZ_LOG_DIR / FZ_CWD) thay /content.
  A. hai o 04_a, 04_b cung chay -> ca hai FZ_PID (khong FZ_BAN); khoi dong lai 04_a khi no con chay -> FZ_BAN=04_a
  B. o khac (07) chay -> o khac nua (06) bi FZ_BAN=07 (quy tac cu), nhung 04_c van khoi dong duoc; dang_chay chi ghi 07
  C. sinh_dang_chay liet ke dung cac o 04_* con chay (khong 07); xong het thi rong; trang_thai tung o dung (xong + ma thoat)
Chay:  python3 test_fz_may_sinh.py
"""
import base64
import json
import os
import subprocess
import sys
import tempfile
import time

PASS = FAIL = 0
HERE = os.path.dirname(os.path.abspath(__file__))
MAY = os.path.join(HERE, "..", "scripts", "colab_cells", "fz_may.py")


def check(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [ok] {msg}")
    else:
        FAIL += 1
        print(f"  [FAIL] {msg}")


def main():
    if not sys.platform.startswith("linux"):
        print("(bo qua: fz_may.py chay tren Linux)")
        return
    try:
        import IPython  # noqa: F401
    except ImportError:
        print("(bo qua: khong co IPython)")
        return
    with tempfile.TemporaryDirectory() as tmp:
        d = os.path.join(tmp, "fz_log")
        os.makedirs(d)
        json.dump(dict(os.environ), open(os.path.join(d, "env.json"), "w"))
        env = dict(os.environ, FZ_LOG_DIR=d, FZ_CWD=tmp)

        def chay(*args, ma=""):
            return subprocess.run([sys.executable, MAY, *args], input=base64.b64encode(ma.encode()).decode(),
                                  capture_output=True, text=True, env=env).stdout

        def o_ngu(giay, loi=False):
            # IPython: o ket thuc binh thuong -> ma 0; bat ky ngoai le (ke ca SystemExit) -> ma 1
            return f"import time\ntime.sleep({giay})\nprint('xong')\n" + ("raise RuntimeError('loi thu')\n" if loi else "")

        print("A. hai o sinh cung luc")
        a = chay("khoi_dong", "04_a", ma=o_ngu(6))
        b = chay("khoi_dong", "04_b", ma=o_ngu(6))
        check("FZ_PID=" in a and "FZ_PID=" in b, f"04_a, 04_b deu khoi dong ({a.strip()} / {b.strip()})")
        check(chay("khoi_dong", "04_a", ma=o_ngu(1)).strip() == "FZ_BAN=04_a", "04_a con chay -> khoi dong lai bi FZ_BAN=04_a")
        print("B. o khac van mot o moi may")
        c7 = chay("khoi_dong", "07", ma=o_ngu(6))
        check("FZ_PID=" in c7, "07 khoi dong")
        check(chay("khoi_dong", "06", ma=o_ngu(1)).strip() == "FZ_BAN=07", "06 bi FZ_BAN=07 (quy tac cu)")
        cc = chay("khoi_dong", "04_c", ma=o_ngu(6))
        check("FZ_PID=" in cc, "04_c van khoi dong duoc khi 07 dang chay")
        check(open(os.path.join(d, "dang_chay")).read().split()[0] == "07", "dang_chay chi ghi o khong phai sinh (07)")
        print("C. sinh_dang_chay, trang_thai")
        ds = [l.split()[1] for l in chay("sinh_dang_chay").splitlines() if l.startswith("FZ_SINH ")]
        check(sorted(ds) == ["04_a", "04_b", "04_c"], f"dang chay: {sorted(ds)}")
        pid_a = open(os.path.join(d, "04_a.pid")).read().strip()
        check(chay("trang_thai", "04_a", pid_a).strip() == "chay", "trang_thai 04_a = chay")
        time.sleep(9)
        check(chay("sinh_dang_chay").strip() == "FZ_SINH_XONG", "het ca: sinh_dang_chay rong")
        check(chay("trang_thai", "04_a", pid_a).strip() == "xong", "trang_thai 04_a = xong")
        check(open(os.path.join(d, "04_a.rc")).read().strip() == "0", "ma thoat 0 (rc=" + open(os.path.join(d, "04_a.rc")).read().strip() + ")")
        check("xong" in open(os.path.join(d, "04_a.log")).read(), "log 04_a co 'xong'")
        # o loi: ma thoat khac 0
        chay("khoi_dong", "04_d", ma=o_ngu(0, True))
        time.sleep(4)
        check(open(os.path.join(d, "04_d.rc")).read().strip() == "1", "o gap ngoai le -> .rc = 1")
        # chay_nhanh (o nhanh) van chay dung voi lenh IPY moi
        out = subprocess.run([sys.executable, MAY, "chay_nhanh", "nhanh"], input=base64.b64encode(b"print('nhanh ok')").decode(),
                             capture_output=True, text=True, env=env).stdout
        check("nhanh ok" in out, f"chay_nhanh: {out.strip()[-20:]}")
    print("\n" + "=" * 60)
    print(f"RESULT: {PASS} passed, {FAIL} failed")
    print("=" * 60)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
