# -*- coding: utf-8 -*-
"""thu_van1323_nhieu_t4.py -- van 1323.47, nua nuoc thu 26 (Den di, the A): tim kiem THAT cua van cho a5b5 ~290 luot (Q +0,585) va a5c3 ~240 luot, con khi tai dung lai
bang cay moi (tu dau dung cay moi cho moi nuoc) thi a5b5 chi 16-32 luot, Q +0,40, a5c3 400 luot. Gia thuyet: nhieu Dirichlet o goc (epsilon 0,25, alpha 0,15; phan bo
rat nhon) tinh co day mot nuoc len. Lap tim kiem 800 luot (cai dat tu dau 04l, mang 117) nhieu lan, ghi cho moi lan: luot, Q, prior sau nhieu (P) va prior tho (Pnet)
cua a5b5 / a5c3 / nuoc nhieu luot nhat. Moi lan toi da 800 luot (khong vuot gioi han 8000).

Chay: python3 ~/chay_t4_thu.py thu_van1323_nhieu_t4.py --can-phut 10 --timeout 900 --tep <custom_engine_fzcuda>:/content/custom_engine_fzcuda"""
import json
import os
import queue
import re
import subprocess
import threading
import time

BRANCH = "luat-moi"
REPO = "https://github.com/phuc11731510/chess_variant_engine"
REL_NN = REPO + "/releases/download/NN_Model"
C = "/content"
E = f"{C}/chess_variant_engine/custom_engine"
UPLOADED = f"{C}/custom_engine_fzcuda"
T0 = time.time()
FEN0 = "gcbmnvkbcq/nsrsqsmsrs/pppppppppp/10/10/10/10/PPPPPPPPPP/RSNSRSMSMS/QBVGKBCCNQ w - - 8+8 0 1"
NUOC = ("f3f5 i8i6 f2f4 i9i7 e2f2 i10i9 f1e2 a9b7 g1f1 i7d7 d3d5 h9j7 d2d4 g9h9 h3h5 j9i8 i1h3 d7g7 e1d2 d8d6 h1i1 i8h7 f1h1 e9a5 h3g5").split()
NET = 117
LAN_NHIEU, LAN_SACH = 80, 20


def log(*a):
    print(f"[{time.time() - T0:6.0f}s]", *a, flush=True)


def shq(s):
    return "'" + s.replace("'", "'\"'\"'") + "'"


def sh(cmd, timeout=900):
    p = subprocess.run(["bash", "-c", f"timeout -k 5 {timeout} bash -c {shq(cmd)}"], capture_output=True, text=True, errors="replace")
    return p.returncode, p.stdout + p.stderr


class Engine:
    def __init__(self, fzw):
        self.p = subprocess.Popen(["bash", f"{E}/run.sh", "--uci-nn", "--weights", fzw, "--provider", "fzcuda", "--fixed-batch", "32"],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, errors="replace")
        self.q = queue.Queue()
        threading.Thread(target=self._doc, daemon=True).start()

    def _doc(self):
        for l in self.p.stdout:
            self.q.put(l.rstrip("\n"))
        self.q.put(None)

    def gui(self, s):
        self.p.stdin.write(s + "\n")
        self.p.stdin.flush()

    def cho(self, dk, timeout):
        out, t0 = [], time.time()
        while time.time() - t0 < timeout:
            try:
                l = self.q.get(timeout=1)
            except queue.Empty:
                continue
            if l is None:
                raise RuntimeError("engine chet: " + " | ".join(out[-5:]))
            out.append(l)
            if dk(l):
                return out
        raise TimeoutError("engine khong tra loi: " + " | ".join(out[-5:]))

    def khoi_dong(self, tuy_chon):
        self.gui("uci")
        self.cho(lambda l: l.startswith("uciok"), 120)
        for k, v in tuy_chon.items():
            self.gui(f"setoption name {k} value {v}")
        self.gui("isready")
        self.cho(lambda l: l.startswith("readyok"), 180)

    def dong(self):
        try:
            self.gui("quit")
            self.p.wait(timeout=10)
        except Exception:
            self.p.kill()


# cai dat tim kiem DAY DU cua tu dau (04l): cpuct 1,5, FPU 0, nhieu goc 0,25 / 0,15, minibatch 32, khong prefetch, policy-temp 1,0
BASE = {"ReuseTree": "false", "Threads": "1", "MultiPV": "64", "RootStats": "true", "PolicySoftmaxTemp": "1.0", "cpuct-factor": "0", "fpu-value": "0",
        "two-fold-draws": "false", "sticky-endgames": "false", "task-workers": "0", "max-prefetch": "0", "minibatch-size": "32",
        "nn-cache-size": "2000000", "noise-alpha": "0.15", "cpuct": "1.5"}


def tim(eng, nhieu):
    eng.gui(f"setoption name noise-epsilon value {0.25 if nhieu else 0.0}")
    eng.gui("ucinewgame")
    eng.gui(f"position fen {FEN0} moves {' '.join(NUOC)}")
    eng.gui("go nodes 800")
    out = eng.cho(lambda l: l.startswith("bestmove"), 120)
    st = {}
    for l in out:
        m = re.match(r"info string stat (\S+) N (\d+) P ([\d.]+) Q (-?[\d.]+)(?: Pnet ([\d.]+))?", l)
        if m:
            st[m.group(1)] = (int(m.group(2)), float(m.group(3)), float(m.group(4)), float(m.group(5)) if m.group(5) else -1.0)
    return st


log("may:", sh("nvidia-smi --query-gpu=name --format=csv,noheader")[1].strip())
sh(f"cd {C} && rm -rf chess_variant_engine && timeout 150 git clone -q --depth 1 --filter=blob:none --sparse -b {BRANCH} {REPO}.git "
   f"chess_variant_engine && cd chess_variant_engine && git sparse-checkout set custom_engine", timeout=250)
sh(f"mkdir -p {E}/build-linux && cp {UPLOADED} {E}/build-linux/custom_engine && chmod +x {E}/build-linux/custom_engine")
rc, out = sh(f"SKIP_ORT=1 bash {E}/scripts/colab_quickstart.sh 2>&1 | tail -n 2", timeout=700)
assert "[quick] OK" in out, out
rc, out = sh(f"python3 {E}/python/lay_mang.py pt {C}/gen{NET}.pt --rel {REL_NN} 2>&1 | tail -n 1", timeout=300)
assert os.path.exists(f"{C}/gen{NET}.pt"), out
sh(f"cd {E}/python && python3 fzw.py convert {C}/gen{NET}.pt {C}/gen{NET}.fzw 2>&1 | tail -n 1", timeout=300)
assert os.path.exists(f"{C}/gen{NET}.fzw")
log("da co mang", NET)

eng = Engine(f"{C}/gen{NET}.fzw")
eng.khoi_dong(BASE)
for nhieu, so in ((True, LAN_NHIEU), (False, LAN_SACH)):
    for i in range(so):
        st = tim(eng, nhieu)
        top = sorted(st.items(), key=lambda kv: -kv[1][0])[:3]
        r = {"nhieu": nhieu, "i": i, "top": [(m, *v) for m, v in top]}
        for m in ("a5b5", "a5c3"):
            r[m] = st.get(m)
        print("R " + json.dumps(r), flush=True)
eng.dong()
log("XONG")
