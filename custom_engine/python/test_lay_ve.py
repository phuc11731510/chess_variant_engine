"""Test of scripts/colab_cells/fz_lay_ve.py and the new cell logic of lay_ve.sh: `bash ~/lay_ve.sh` updates exactly what changed.

Needs bash and curl (Linux, WSL, Termux). Run:  python3 test_lay_ve.py

  A. The three-way merge (diff3 by lines).
  B. The decision for every cell, with a local HTTP server standing in for GitHub: new cell, unchanged, new version while
     the user did not edit, user edit while upstream did not change, both changed elsewhere (merged), both changed the same
     line (nothing overwritten, the new version goes to <cell>.py.moi), first use without a saved base, --xem, -f / cell number,
     a download that fails, Windows line ends.
  C. lay_ve.sh itself against the same server (FZ_LAY_VE_URL): first run installs everything, second run changes nothing,
     an upstream change reaches exactly that cell, --xem writes nothing.
"""

import functools
import hashlib
import http.server
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import threading

if os.name != "posix":
    print("[skip] needs bash and curl (run it under Linux / WSL / Termux)")
    sys.exit(0)

HERE = os.path.dirname(os.path.abspath(__file__))
CELLS_DIR = os.path.join(HERE, "..", "scripts", "colab_cells")
HELPER = os.path.join(CELLS_DIR, "fz_lay_ve.py")
spec = importlib.util.spec_from_file_location("fz_lay_ve", HELPER)
LV = importlib.util.module_from_spec(spec)
spec.loader.exec_module(LV)

PASS = FAIL = 0


def check(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [ok] {msg}")
    else:
        FAIL += 1
        print(f"  [FAIL] {msg}")


def test_merge():
    print("\n[A] the three-way merge")
    base = ["a", "b", "c", "d", "e"]
    r, x = LV.tron_ba_ben(base, base, ["a", "b", "C", "d", "e"])
    check(x == 0 and r == ["a", "b", "C", "d", "e"], "only upstream changed: upstream's version")
    r, x = LV.tron_ba_ben(base, ["a", "B", "c", "d", "e"], base)
    check(x == 0 and r == ["a", "B", "c", "d", "e"], "only the user changed: the user's version")
    r, x = LV.tron_ba_ben(base, ["a", "B", "c", "d", "e"], ["a", "b", "c", "d", "E"])
    check(x == 0 and r == ["a", "B", "c", "d", "E"], "changes in different places: both kept")
    r, x = LV.tron_ba_ben(base, ["a", "X", "c", "d", "e"], ["a", "Y", "c", "d", "e"])
    check(x == 1, "the same line changed differently: one conflict")
    r, x = LV.tron_ba_ben(base, ["a", "X", "c", "d", "e"], ["a", "X", "c", "d", "e"])
    check(x == 0 and r == ["a", "X", "c", "d", "e"], "the same change on both sides: no conflict")
    r, x = LV.tron_ba_ben(base, ["new0", "a", "b", "c", "d", "e"], ["a", "b", "c", "d", "e", "new9"])
    check(x == 0 and r == ["new0", "a", "b", "c", "d", "e", "new9"], "a line added at the top by one side and at the end by the other")
    r, x = LV.tron_ba_ben(base, ["a", "b", "ins", "c", "d", "e"], ["a", "b", "c", "d", "E"])
    check(x == 0 and r == ["a", "b", "ins", "c", "d", "E"], "an insertion on one side next to a change on the other")
    r, x = LV.tron_ba_ben(base, ["a", "c", "d", "e"], ["a", "b", "c", "d", "E"])
    check(x == 0 and r == ["a", "c", "d", "E"], "a deletion by the user and a change elsewhere upstream")
    r, x = LV.tron_ba_ben([], ["u"], ["n"])
    check(x == 1, "no base lines and two different contents: conflict")
    r, x = LV.tron_ba_ben(base, base, base)
    check(x == 0 and r == base, "nothing changed")


class Servidor:
    """A tiny HTTP server over a directory (stands in for raw.githubusercontent.com)."""

    def __init__(self, raiz):
        class Q(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *a, **k):
                pass
        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Q, directory=raiz))
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def parar(self):
        self.srv.shutdown()


def ghi(p, s, newline=None):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline=newline) as f:
        f.write(s)


def doc(p):
    with open(p, encoding="utf-8", newline="") as f:
        return f.read()


def chay_helper(url, o_lenh, state, cells, *extra):
    p = subprocess.run([sys.executable, HELPER, "--url", url, "--dir", o_lenh, "--state", state, "--cells", cells, *extra],
                       capture_output=True, text=True, timeout=120)
    return p.returncode, p.stdout + p.stderr


def dau_van_tay(thu_muc):
    h = hashlib.sha256()
    for r, _, fs in sorted(os.walk(thu_muc)):
        for n in sorted(fs):
            h.update(n.encode())
            h.update(open(os.path.join(r, n), "rb").read())
    return h.hexdigest()


CELLS = "00_cau_hinh 04_sinh 08_arena"
CAU_HINH = "# cau hinh\nGEN_CURRENT = 0\nREL = \"v1\"\nOUT = \"/content/games\"\n"
SINH = "# sinh du lieu\nSECS = 15480\nGAMES = 1000\nPARALLEL = 16\ncmd = \"engine --visits 800\"\n"
ARENA = "# arena\nGAMES = 100\nA = \"new\"\ncmd = \"arena --visits 400\"\nprint(cmd)\n"


def test_cells(tmp):
    print("\n[B] the decision for every cell")
    repo, o, st = os.path.join(tmp, "repo"), os.path.join(tmp, "o_lenh"), os.path.join(tmp, "state")
    ghi(os.path.join(repo, "00_cau_hinh.py"), CAU_HINH)
    ghi(os.path.join(repo, "04_sinh.py"), SINH)
    ghi(os.path.join(repo, "08_arena.py"), ARENA)
    sv = Servidor(repo)
    try:
        rc, out = chay_helper(sv.url, o, st, CELLS)
        check(rc == 0 and out.count("[tai]") == 3 and all(os.path.exists(os.path.join(o, c + ".py")) for c in CELLS.split()),
              "first run: the three cells that were missing are downloaded")
        check(os.path.exists(os.path.join(st, "co_so", "08_arena.py")), "...and their base version is remembered")
        rc, out = chay_helper(sv.url, o, st, CELLS)
        check(rc == 0 and "[o lenh] 3 =" in out and "[tai]" not in out and "[moi]" not in out, "second run: nothing changes, nothing is printed but the summary")

        # upstream changes 08 only; the user did not touch it
        ghi(os.path.join(repo, "08_arena.py"), ARENA + "extra = 1\n")
        rc, out = chay_helper(sv.url, o, st, CELLS)
        check("[moi]" in out and "08_arena.py" in out and doc(os.path.join(o, "08_arena.py")).endswith("extra = 1\n"),
              "a new upstream version of a cell the user did not edit: replaced")
        check("04_sinh" not in out and "00_cau_hinh" not in out, "...and only that cell is mentioned (exactly what changed)")

        # the user (or the menu) edits 04: GAMES; upstream unchanged
        ghi(os.path.join(o, "04_sinh.py"), SINH.replace("GAMES = 1000", "GAMES = 200"))
        rc, out = chay_helper(sv.url, o, st, CELLS)
        check("[giu]" in out and "GAMES = 200" in doc(os.path.join(o, "04_sinh.py")), "the user edited, upstream did not change: the user's version is kept")

        # upstream changes 04 elsewhere; the user's GAMES edit must survive (the menu writes SECS/GAMES into the cell)
        ghi(os.path.join(repo, "04_sinh.py"), SINH.replace("--visits 800", "--visits 800 --fast-prob 0.5"))
        rc, out = chay_helper(sv.url, o, st, CELLS)
        t = doc(os.path.join(o, "04_sinh.py"))
        check("[tron]" in out and "GAMES = 200" in t and "--fast-prob 0.5" in t, "both changed in different places: merged (GAMES = 200 AND the new flag)")
        rc, out = chay_helper(sv.url, o, st, CELLS)
        check("[o lenh] 3 =" in out or ("[giu]" in out and "[tron]" not in out), "after a merge the next run does not merge again")

        # the loop writes GEN_CURRENT into 00; upstream adds lines
        ghi(os.path.join(o, "00_cau_hinh.py"), CAU_HINH.replace("GEN_CURRENT = 0", "GEN_CURRENT = 7"))
        ghi(os.path.join(repo, "00_cau_hinh.py"), CAU_HINH + "NEW_VAR = 1\n")
        rc, out = chay_helper(sv.url, o, st, CELLS)
        t = doc(os.path.join(o, "00_cau_hinh.py"))
        check("[tron]" in out and "GEN_CURRENT = 7" in t and "NEW_VAR = 1" in t, "00: GEN_CURRENT = 7 (written by the loop) survives a new upstream line")

        # conflict: both changed the same line of 08
        ghi(os.path.join(o, "08_arena.py"), doc(os.path.join(o, "08_arena.py")).replace("GAMES = 100", "GAMES = 40"))
        ghi(os.path.join(repo, "08_arena.py"), ARENA.replace("GAMES = 100", "GAMES = 64") + "extra = 1\n")
        antes = doc(os.path.join(o, "08_arena.py"))
        rc, out = chay_helper(sv.url, o, st, CELLS)
        check("[xung dot]" in out and doc(os.path.join(o, "08_arena.py")) == antes, "the same line changed on both sides: the user's file is NOT touched")
        check(os.path.exists(os.path.join(o, "08_arena.py.moi")) and "GAMES = 64" in doc(os.path.join(o, "08_arena.py.moi")),
              "...and the new version is saved next to it as 08_arena.py.moi")
        check("bash ~/lay_ve.sh 08" in out, "...with the command that replaces the cell for good")
        rc, out = chay_helper(sv.url, o, st, CELLS, "08")
        check("[thay]" in out and "GAMES = 64" in doc(os.path.join(o, "08_arena.py")) and not os.path.exists(os.path.join(o, "08_arena.py.moi")),
              "'lay_ve.sh 08' replaces that cell and removes the .moi")

        # --xem changes nothing
        ghi(os.path.join(repo, "08_arena.py"), ARENA.replace("GAMES = 100", "GAMES = 64") + "extra = 2\n")
        antes = dau_van_tay(tmp + "/o_lenh"), dau_van_tay(st)
        rc, out = chay_helper(sv.url, o, st, CELLS, "--xem")
        check("[moi]" in out and "chi xem" in out and (dau_van_tay(o), dau_van_tay(st)) == antes, "--xem says what would change and writes nothing")

        # -f replaces everything, including an edit
        ghi(os.path.join(o, "04_sinh.py"), "# my own file\n")
        rc, out = chay_helper(sv.url, o, st, CELLS, "-f")
        check(doc(os.path.join(o, "04_sinh.py")) == doc(os.path.join(repo, "04_sinh.py")) and out.count("[thay]") >= 1,
              "-f replaces every cell, edits included")

        # a download that fails: that cell is left alone
        os.remove(os.path.join(repo, "04_sinh.py"))
        antes = doc(os.path.join(o, "04_sinh.py"))
        rc, out = chay_helper(sv.url, o, st, CELLS)
        check(rc == 0 and "[loi]" in out and doc(os.path.join(o, "04_sinh.py")) == antes, "a download that fails: the cell is left as it is, the run goes on")
        ghi(os.path.join(repo, "04_sinh.py"), SINH)

        # first use without a base (the phone today): never overwrite what may be edited
        shutil.rmtree(st)
        ghi(os.path.join(repo, "08_arena.py"), ARENA + "extra = 3\n")
        ghi(os.path.join(o, "00_cau_hinh.py"), doc(os.path.join(repo, "00_cau_hinh.py")))     # this one equals upstream
        antes = doc(os.path.join(o, "08_arena.py"))
        rc, out = chay_helper(sv.url, o, st, CELLS)
        check("[chua ro]" in out and doc(os.path.join(o, "08_arena.py")) == antes and os.path.exists(os.path.join(o, "08_arena.py.moi")),
              "no saved base and the file differs: not overwritten, the new version goes to .moi")
        check("00_cau_hinh" not in out and os.path.exists(os.path.join(st, "co_so", "00_cau_hinh.py")),
              "a cell that equals upstream is not mentioned, and its base is saved now")
        rc, out = chay_helper(sv.url, o, st, CELLS, "08")
        check("extra = 3" in doc(os.path.join(o, "08_arena.py")), "'lay_ve.sh 08' then gives the new cell and starts remembering its base")

        # Windows line ends in a file the user never changed: not taken for an edit
        ghi(os.path.join(o, "04_sinh.py"), doc(os.path.join(repo, "04_sinh.py")).replace("\n", "\r\n"), newline="")
        rc, out = chay_helper(sv.url, o, st, CELLS)
        ghi(os.path.join(repo, "04_sinh.py"), SINH + "# upstream\n")
        rc, out = chay_helper(sv.url, o, st, CELLS)
        check("[moi]" in out and "04_sinh" in out and doc(os.path.join(o, "04_sinh.py")).endswith("# upstream\n"),
              "a CRLF copy of an unedited cell is still 'not edited': replaced when upstream changes")
    finally:
        sv.parar()


def test_lay_ve_sh(tmp):
    print("\n[C] lay_ve.sh against a stand-in for GitHub")
    repo = os.path.join(tmp, "repo2")
    shutil.copytree(CELLS_DIR, repo, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    home = os.path.join(tmp, "home")
    os.makedirs(os.path.join(home, "storage", "downloads"))
    os.makedirs(os.path.join(home, ".ssh"))                  # a Termux home always has it (lay_ve.sh makes a key there)
    shutil.copy(os.path.join(repo, "lay_ve.sh"), os.path.join(home, "lay_ve.sh"))
    sv = Servidor(repo)
    env = {k: v for k, v in os.environ.items() if k not in ("FZ_LAY_VE_MOI",)}
    env.update({"HOME": home, "FZ_LAY_VE_URL": sv.url, "PATH": os.environ["PATH"]})
    o = os.path.join(home, "storage", "downloads", "FairyZero", "o_lenh")

    def lay(*args):
        p = subprocess.run(["bash", os.path.join(home, "lay_ve.sh"), *args], capture_output=True, text=True, timeout=300, env=env, cwd=home)
        return p.returncode, p.stdout + p.stderr

    try:
        rc, out = lay()
        n_cells = len("00_cau_hinh 01_kiem_gpu 02_khoi_dong 02b_bien_dich 02c_chuan_bi_huan_luyen 03_tao_gen0 04_sinh_du_lieu 04l_sinh_lien_tuc "
                      "05_xem_log 06_dong_goi 07_huan_luyen 08_arena 09_dung_viec_nen 09b_dung_mem".split())
        check(rc == 0 and out.count("[tai]") >= n_cells, f"first run: exit {rc}, the cells and helper files are downloaded")
        check(all(os.path.exists(os.path.join(home, n)) for n in ("fz_menu.sh", "fz_nhat_ky.py", "fz_lay_ve.py", "fz_tu_dong.sh", "fz_lien_tuc.sh", "fz_may.py")),
              "...menu, window logger, updater and the loop scripts are in the home directory")
        check(len(os.listdir(os.path.join(home, ".fz_lay_ve", "co_so"))) == n_cells, f"...the base of all {n_cells} cells is remembered")
        rc, out = lay()
        check(rc == 0 and f"[o lenh] {n_cells} =" in out, "second run: no cell changes")

        # the arena cell changes upstream (this is the case that went wrong by hand); the user edited 04's GAMES
        ghi(os.path.join(o, "04_sinh_du_lieu.py"), doc(os.path.join(o, "04_sinh_du_lieu.py")).replace("GAMES = 1000", "GAMES = 123"))
        ghi(os.path.join(repo, "08_arena.py"), doc(os.path.join(repo, "08_arena.py")) + "\n# nuevo\n")
        ghi(os.path.join(repo, "04_sinh_du_lieu.py"), doc(os.path.join(repo, "04_sinh_du_lieu.py")) + "\n# upstream 04\n")
        rc, out = lay()
        check(rc == 0 and "[moi]" in out and "08_arena.py" in out and doc(os.path.join(o, "08_arena.py")).rstrip().endswith("# nuevo"),
              "08 changed upstream: 'lay_ve.sh' alone brings it")
        t = doc(os.path.join(o, "04_sinh_du_lieu.py"))
        check("[tron]" in out and "GAMES = 123" in t and t.rstrip().endswith("# upstream 04"), "04: the user's GAMES = 123 is kept and the upstream change arrives")
        check("[o lenh] 12 =, 1 moi, 1 tron" in out or ("1 moi" in out and "1 tron" in out), "the summary counts exactly those two cells")

        # --xem writes nothing and does not run the rest of the script
        ghi(os.path.join(repo, "08_arena.py"), doc(os.path.join(repo, "08_arena.py")) + "# one more\n")
        antes = dau_van_tay(home)
        rc, out = lay("--xem")
        check(rc == 0 and "chi xem" in out and "08_arena.py" in out and dau_van_tay(home) == antes, "--xem: says what would change, changes nothing")
        rc, out = lay("08")
        check(rc == 0 and doc(os.path.join(o, "08_arena.py")).rstrip().endswith("# one more"), "'lay_ve.sh 08' still forces one cell")

        # the updater cannot be downloaded: lay_ve.sh falls back to the old behaviour instead of failing
        os.remove(os.path.join(repo, "fz_lay_ve.py"))
        rc, out = lay()
        check(rc == 0 and "dung cach cu" in out and "[giu nguyen]" in out and "[tai]" in out,
              "no updater on the server: the old behaviour (keep the cells that exist), the run does not fail")
    finally:
        sv.parar()


def main():
    with tempfile.TemporaryDirectory() as tmp:
        test_merge()
        test_cells(tmp)
        test_lay_ve_sh(tmp)
    print("\n" + "=" * 60)
    print(f"RESULT: {PASS} passed, {FAIL} failed")
    print("=" * 60)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
