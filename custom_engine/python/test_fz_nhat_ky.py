"""Test of scripts/colab_cells/fz_nhat_ky.py: the per-window log of the Termux windows (everything the window shows).

Needs a Unix pty (Linux, WSL, Termux). Run:  python3 test_fz_nhat_ky.py

  A. The screen model: colors, \\r progress bars, \\b, tabs, ESC sequences and UTF-8 cut between two reads, OSC titles.
  B. The file: a line over --max-dong cuts the head down to --giu-dong lines; every line has a time.
  C. The clean-up: only cua_so_*.log files NOT MODIFIED for more than the number of days are removed.
  D. A real child in a real pty: it runs as normal (interactive prompt, exit code, window size, colors on the screen)
     while its text is logged; every run makes its own file; no tty / FZ_KHONG_NHAT_KY: the program just runs.
"""

import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import time

if os.name != "posix":
    print("[skip] needs a Unix pty (run it under Linux / WSL / Termux)")
    sys.exit(0)

import fcntl
import pty
import select
import struct
import termios

HERE = os.path.dirname(os.path.abspath(__file__))
WRAPPER = os.path.join(HERE, "..", "scripts", "colab_cells", "fz_nhat_ky.py")
spec = importlib.util.spec_from_file_location("fz_nhat_ky", WRAPPER)
NK = importlib.util.module_from_spec(spec)
spec.loader.exec_module(NK)

PASS = FAIL = 0


def check(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [ok] {msg}")
    else:
        FAIL += 1
        print(f"  [FAIL] {msg}")


def lines_of(*chunks):
    out = []
    m = NK.ManHinh(out.append)
    for c in chunks:
        m.them(c)
    return out, m


def test_screen_model():
    print("\n[A] the screen model")
    out, _ = lines_of(b"hello   \nsecond\n")
    check(out == ["hello", "second"], "plain lines, trailing spaces dropped")
    out, _ = lines_of(b"\x1b[31mred\x1b[0m and \x1b[1;32mgreen\x1b[m ok\n")
    check(out == ["red and green ok"], "color codes are dropped")
    out, _ = lines_of(b"10%\r50%\r100%\n")
    check(out == ["100%"], "a \\r progress bar leaves only its last state")
    out, _ = lines_of(b"abc\rX\n")
    check(out == ["Xbc"], "\\r then text overwrites from column 0")
    out, _ = lines_of(b"abc\b\bX\n")
    check(out == ["aXc"], "\\b moves back and the next character overwrites")
    out, _ = lines_of(b"\x1b[3", b"1mhi\n")
    check(out == ["hi"], "an ESC sequence cut between two reads")
    texte = "Enter = b\u1eaft \u0111\u1ea7u"                 # Vietnamese text
    raw = texte.encode("utf-8") + b"\n"
    out, _ = lines_of(raw[:12], raw[12:])
    check(out == [texte], "UTF-8 (Vietnamese) cut in the middle of a character")
    out, _ = lines_of(b"\x1b]0;window title\x07text\n")
    check(out == ["text"], "an OSC title (BEL end) is dropped")
    out, _ = lines_of(b"\x1b]0;title\x1b\\text2\n")
    check(out == ["text2"], "an OSC title (ESC \\ end) is dropped")
    out, _ = lines_of(b"old line\r\x1b[Knew\n")
    check(out == ["new"], "CSI K erases the rest of the line")
    out, _ = lines_of(b"a\tb\n")
    check(out == ["a       b"], "a tab pads to a multiple of 8")
    out, _ = lines_of(b"\x1b(B\x1b[?25lx\x1b[?25h\x07y\n")
    check(out == ["xy"], "charset, cursor show/hide and BEL codes are dropped")
    out, m = lines_of(b"name? ")
    check(out == [], "a prompt waiting for input is not a line yet")
    m.ket_thuc()
    check(out == ["name?"], "...and is written out when the window closes")
    out, _ = lines_of(b"\n\nx\n")
    check(out == ["", "", "x"], "blank lines are kept")


def test_file_and_cleanup(tmp):
    print("\n[B] the file: time on every line, cut when too long")
    p = os.path.join(tmp, "t.log")
    f = NK.TepNhatKy(p, 50, 20)
    for i in range(1, 121):
        f.dong_moi(f"dong {i}")
    f.dong_tep()
    got = open(p, encoding="utf-8").read().splitlines()
    check(len(got) <= 50 and got[-1].endswith("dong 120"), f"{len(got)} lines (max 50) and the last line is 'dong 120'")
    check(all(re.match(r"^\[\d\d:\d\d:\d\d\] ", g) for g in got), "every line starts with [HH:MM:SS]")
    check("da cat bo" in got[0], "the first line says how many lines were cut")
    nums = [int(g.rsplit("dong ", 1)[1]) for g in got[1:]]
    check(nums == list(range(nums[0], nums[0] + len(nums))) and nums[-1] == 120,
          "the kept lines are consecutive and end at the last one")

    print("\n[C] the clean-up of old logs")
    d = os.path.join(tmp, "cu")
    os.makedirs(d)
    now = time.time()

    def mk(name, days_old):
        q = os.path.join(d, name)
        open(q, "w").write("x\n")
        os.utime(q, (now - days_old * 86400, now - days_old * 86400))
        return q

    cu, moi, tam_cu, la, sai_duoi = (mk("cua_so_20260101_000000_1.log", 8), mk("cua_so_20260102_000000_2.log", 6),
                                      mk("cua_so_20260101_000000_3.log.tmp", 9), mk("ghi_chu.txt", 30),
                                      mk("cua_so_20260101_000000_4.txt", 30))
    n = NK.don_cu(d, 7, now)
    check(n == 2 and not os.path.exists(cu) and not os.path.exists(tam_cu), "a log 8 days old and a stale .tmp are removed")
    check(os.path.exists(moi), "a log 6 days old is kept (not modified for LESS than a week)")
    check(os.path.exists(la) and os.path.exists(sai_duoi), "files that are not cua_so_*.log are never touched")


def chay_trong_pty(args, cho=None, gui=None, rows=30, cols=100, timeout=60, env=None):
    """Run the wrapper under a real pty as if it were a terminal window. Returns (screen bytes, exit code)."""
    e = dict(os.environ)
    e.update(env or {})
    e.pop("FZ_NK_ACTIVE", None)
    pid, fd = pty.fork()
    if pid == 0:
        os.environ.clear()
        os.environ.update(e)
        os.execv(sys.executable, [sys.executable, WRAPPER] + args)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
    man, t0, da_gui = b"", time.time(), False
    while time.time() - t0 < timeout:
        r, _, _ = select.select([fd], [], [], 0.2)
        if r:
            try:
                d = os.read(fd, 65536)
            except OSError:
                break
            if not d:
                break
            man += d
        if cho and gui and not da_gui and cho in man:
            os.write(fd, gui)
            da_gui = True
    _, st = os.waitpid(pid, 0)
    return man, (os.WEXITSTATUS(st) if os.WIFEXITED(st) else 128 + os.WTERMSIG(st))


def doc_nhat_ky(thu_muc):
    ds = sorted(n for n in os.listdir(thu_muc) if n.startswith("cua_so_") and n.endswith(".log"))
    return ds, [open(os.path.join(thu_muc, n), encoding="utf-8").read().splitlines() for n in ds]


def test_real_pty(tmp):
    print("\n[D] a real program in a real pty")
    d = os.path.join(tmp, "nk")
    os.makedirs(d)
    cu = os.path.join(d, "cua_so_20200101_000000_9.log")       # an old log: removed when a window starts
    open(cu, "w").write("x\n")
    os.utime(cu, (time.time() - 8 * 86400,) * 2)
    moi = os.path.join(d, "cua_so_20200102_000000_9.log")      # a recent one: kept
    open(moi, "w").write("x\n")
    child = ("echo hello; printf '\\033[31mred\\033[0m\\n'; sleep 0.8; stty size; "
             "read -p 'name? ' x; echo got:$x; exit 3")
    man, code = chay_trong_pty(["--dir", d, "--", "bash", "-c", child], cho=b"name? ", gui=b"bob\r")
    check(code == 3, f"the exit code of the program is the exit code of the window (got {code})")
    check(b"got:bob" in man and b"\x1b[31mred" in man, "the screen still shows the program's output, colors included")
    check(b"30 100" in man, "the window size reaches the program (stty size = 30 100)")
    ds, logs = doc_nhat_ky(d)
    check(os.path.basename(cu) not in ds and os.path.basename(moi) in ds, "the old log was removed, the recent one kept")
    nuevo = [n for n in ds if n != os.path.basename(moi)]
    check(len(nuevo) == 1, "this window made exactly one new log file")
    lg = logs[ds.index(nuevo[0])]
    texto = [re.sub(r"^\[\d\d:\d\d:\d\d\] ", "", x) for x in lg]
    check(texto[0].startswith("=== cua so pid=") and "bat dau" in texto[0], "the log starts with a header line")
    check("hello" in texto and "red" in texto, "the program's lines are in the log (colors dropped)")
    check("30 100" in texto, "...and the stty output")
    check("name? bob" in texto and "got:bob" in texto, "the interactive prompt is logged with what was typed")
    check(texto[-1].startswith("=== cua so pid=") and "ket thuc" in texto[-1] and "ma thoat 3" in texto[-1],
          "the log ends with the exit code")

    man2, code2 = chay_trong_pty(["--dir", d, "--", "bash", "-c", "echo second window"])
    ds2, _ = doc_nhat_ky(d)
    check(code2 == 0 and len(ds2) == len(ds) + 1, "a second window makes its OWN file (the first one is untouched)")

    print("\n[D2] too many lines: cut while the window runs")
    d2 = os.path.join(tmp, "nk2")
    man3, code3 = chay_trong_pty(["--dir", d2, "--max-dong", "30", "--giu-dong", "10", "--", "bash", "-c",
                                  "for i in $(seq 1 100); do echo line $i; done"])
    ds3, logs3 = doc_nhat_ky(d2)
    lg3 = logs3[0]
    check(code3 == 0 and len(lg3) <= 31 and lg3[-1].find("ket thuc") >= 0 and any("line 100" in x for x in lg3),
          f"{len(lg3)} lines in the file (max 30 + the closing line), line 100 is there")
    check(any("da cat bo" in x for x in lg3) and not any(x.endswith("line 1") for x in lg3), "the head was cut")
    check(b"line 1\r\n" in man3 and b"line 100" in man3, "the SCREEN still showed every line (only the file is cut)")

    print("\n[D3] no log when it must not log")
    d3 = os.path.join(tmp, "nk3")
    man4, code4 = chay_trong_pty(["--dir", d3, "--", "bash", "-c", "echo quiet"], env={"FZ_KHONG_NHAT_KY": "1"})
    check(code4 == 0 and b"quiet" in man4 and not os.path.exists(d3), "FZ_KHONG_NHAT_KY=1: the program runs, nothing is written")
    p = subprocess.run([sys.executable, WRAPPER, "--dir", d3, "--", "bash", "-c", "echo plain; exit 5"],
                       capture_output=True, text=True)
    check(p.returncode == 5 and p.stdout == "plain\n" and not os.path.exists(d3),
          "stdin/stdout not a terminal (a pipe): the program just runs, same output, same exit code, no log")
    man5, code5 = chay_trong_pty(["--dir", d3, "--", "bash", "-c", "echo $FZ_NK_ACTIVE; ls \"$FZ_NK_TEP\" >/dev/null && echo tep-ok"])
    check(b"1" in man5 and b"tep-ok" in man5, "the program sees FZ_NK_ACTIVE=1 (no double wrapping) and FZ_NK_TEP")
    man6, code6 = chay_trong_pty(["--dir", d3, "--", "bash", "-c", "exec python3 %s --dir %s -- bash -c 'echo inner'" % (WRAPPER, d3)])
    ds6, _ = doc_nhat_ky(d3)
    check(code6 == 0 and b"inner" in man6 and len(ds6) == 2, "a wrapped program that calls the wrapper again does not wrap twice (2 files from 2 windows, not 3)")
    man7, code7 = chay_trong_pty(["--dir", d3, "--", "no_such_program_xyz"])
    check(code7 == 127, "a program that does not exist: exit code 127")


def test_menu_hook(tmp):
    """The exact hook block of scripts/colab_cells/menu.sh, extracted from the real file and run as the top of a tiny script."""
    print("\n[E] the hook at the top of menu.sh")
    menu = open(os.path.join(HERE, "..", "scripts", "colab_cells", "menu.sh"), encoding="utf-8").read()
    m = re.search(r"(if \[ -z \"\$\{FZ_NK_ACTIVE:-\}\" \].*?\nfi\n)", menu, re.S)
    check(m is not None, "the hook block is found in menu.sh")
    if not m:
        return
    script = os.path.join(tmp, "mini_menu.sh")
    open(script, "w").write("#!/bin/bash\n" + m[1] + 'echo "RAN active=${FZ_NK_ACTIVE:-no} args=$*"\nexit 4\n')
    home = os.path.join(tmp, "home")
    os.makedirs(home)
    open(os.path.join(home, "fz_nhat_ky.py"), "w").write(open(WRAPPER, encoding="utf-8").read())
    man, code = chay_trong_pty(["--dir", os.path.join(tmp, "unused"), "--", "bash", script, "04", "05"],
                               env={"HOME": home, "FZ_NK_ACTIVE": ""})
    # The outer wrapper (run by the harness) logs under tmp/unused and sets FZ_NK_ACTIVE, so the hook must NOT wrap again.
    check(b"RAN active=1 args=04 05" in man and code == 4, "under a wrapper already: the script just runs (no double wrapping), args kept")
    # Directly, as a window would start it: bash script under a pty with no FZ_NK_ACTIVE.
    pid, fd = pty.fork()
    if pid == 0:
        e = {k: v for k, v in os.environ.items() if k not in ("FZ_NK_ACTIVE", "FZ_KHONG_NHAT_KY")}
        e["HOME"] = home
        os.execve("/bin/bash", ["bash", script, "04", "05"], e)
    salida = b""
    while True:
        try:
            d = os.read(fd, 65536)
        except OSError:
            break
        if not d:
            break
        salida += d
    _, st = os.waitpid(pid, 0)
    logs = sorted(os.listdir(os.path.join(home, "fz_nhat_ky"))) if os.path.isdir(os.path.join(home, "fz_nhat_ky")) else []
    check(b"RAN active=1 args=04 05" in salida and os.WEXITSTATUS(st) == 4, "started like a window: the script runs inside the wrapper, exit code kept")
    check(len(logs) == 1, "...and ~/fz_nhat_ky has this window's log file")
    if logs:
        txt = open(os.path.join(home, "fz_nhat_ky", logs[0]), encoding="utf-8").read()
        check("RAN active=1 args=04 05" in txt and "ma thoat 4" in txt, "the log has the script's output and its exit code")

    # A broken fz_nhat_ky.py (bad download) must not stop the window: the hook sees --kiem-tra fail and runs the script directly.
    open(os.path.join(home, "fz_nhat_ky.py"), "w").write("def (:\n")
    for ten in os.listdir(os.path.join(home, "fz_nhat_ky")):
        os.remove(os.path.join(home, "fz_nhat_ky", ten))
    pid, fd = pty.fork()
    if pid == 0:
        e = {k: v for k, v in os.environ.items() if k not in ("FZ_NK_ACTIVE", "FZ_KHONG_NHAT_KY")}
        e["HOME"] = home
        os.execve("/bin/bash", ["bash", script, "04"], e)
    salida = b""
    while True:
        try:
            d = os.read(fd, 65536)
        except OSError:
            break
        if not d:
            break
        salida += d
    _, st = os.waitpid(pid, 0)
    check(b"RAN active=no args=04" in salida and os.WEXITSTATUS(st) == 4 and not os.listdir(os.path.join(home, "fz_nhat_ky")),
          "a broken fz_nhat_ky.py: the script still runs, unwrapped, nothing logged")
    os.remove(os.path.join(home, "fz_nhat_ky.py"))
    pid, fd = pty.fork()
    if pid == 0:
        e = {k: v for k, v in os.environ.items() if k not in ("FZ_NK_ACTIVE", "FZ_KHONG_NHAT_KY")}
        e["HOME"] = home
        os.execve("/bin/bash", ["bash", script], e)
    salida = b""
    while True:
        try:
            d = os.read(fd, 65536)
        except OSError:
            break
        if not d:
            break
        salida += d
    _, st = os.waitpid(pid, 0)
    check(b"RAN active=no" in salida and os.WEXITSTATUS(st) == 4, "no fz_nhat_ky.py at all (phone not updated yet): the script runs as before")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        test_screen_model()
        test_file_and_cleanup(tmp)
        test_real_pty(tmp)
        test_menu_hook(tmp)
    print("\n" + "=" * 60)
    print(f"RESULT: {PASS} passed, {FAIL} failed")
    print("=" * 60)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
