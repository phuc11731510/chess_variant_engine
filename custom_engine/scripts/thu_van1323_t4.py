# -*- coding: utf-8 -*-
"""thu_van1323_t4.py -- van 1323.47 (goi_01323_n117, van thu 47): o nua nuoc thu 26 (Den di, 829 luot) tim kiem van ra a5b5 (Hau den len b5, bi Tuong trang e2 an,
khong an lai duoc). Hoi dau chinh sach hay dau gia tri sai: gia tri tho + prior tho + tim kiem o ba the (truoc a5b5, sau a5b5, sau e2b5) cua mang 117
(mang sinh van) va vai doi cu (do hoc theo doi), voi 800 luot kieu tu dau (co nhieu) va nhieu luot hon (khong nhieu).

LUU Y (26/11): dong "GIA TRI THO" in tu `go nodes 1` KHONG phai gia tri tho khi the da nam trong bo nho dem cua engine (tim kiem chay hon 1 luot, in Q cua nuoc con): gia tri tho dung phai tinh bang PyTorch tu mat phang ban ghi (khop engine +-0,003). Dong prior (Pnet) va ket qua tim kiem la dung.

Chay: python3 ~/chay_t4_thu.py thu_van1323_t4.py --can-phut 15 --timeout 1200 --tep <custom_engine_fzcuda>:/content/custom_engine_fzcuda"""
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
NUOC = ("f3f5 i8i6 f2f4 i9i7 e2f2 i10i9 f1e2 a9b7 g1f1 i7d7 d3d5 h9j7 d2d4 g9h9 h3h5 j9i8 i1h3 d7g7 e1d2 d8d6 h1i1 i8h7 f1h1 e9a5 h3g5 "
        "a5b5 e2b5").split()
VI_TRI = [("truoc a5b5 (Den di, nua nuoc 26)", 25), ("sau a5b5 (Trang di)", 26), ("sau a5b5 e2b5 (Den di, mat Hau)", 27)]
NET = 117
CU = [30, 64, 100]


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


BASE = {"ReuseTree": "false", "Threads": "1", "DepthStats": "true", "MultiPV": "64", "RootStats": "true", "PolicySoftmaxTemp": "1.0",
        "cpuct-factor": "0", "fpu-value": "0", "two-fold-draws": "false", "sticky-endgames": "false", "task-workers": "0",
        "max-prefetch": "0", "minibatch-size": "32", "nn-cache-size": "2000000", "noise-alpha": "0.15", "cpuct": "1.5"}


def tim(eng, k, nodes, nhieu):
    eng.gui(f"setoption name noise-epsilon value {0.25 if nhieu else 0.0}")
    eng.gui("ucinewgame")
    eng.gui(f"position fen {FEN0} moves {' '.join(NUOC[:k])}")
    eng.gui(f"go nodes {nodes}")
    out = eng.cho(lambda l: l.startswith("bestmove"), 300)
    st, wdl, ds = {}, None, ""
    for l in out:
        m = re.match(r"info string stat (\S+) N (\d+) P ([\d.]+) Q (-?[\d.]+)(?: Pnet ([\d.]+))?", l)
        if m:
            st[m.group(1)] = (int(m.group(2)), float(m.group(3)), float(m.group(4)), float(m.group(5)) if m.group(5) else -1.0)
        m = re.match(r"info depth \d+ multipv 1 score cp (-?\d+) wdl (\d+) (\d+) (\d+) nodes (\d+)", l)
        if m:
            wdl = (int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)))
        if l.startswith("info string depthstats"):
            ds = l
    return st, wdl, ds


def mo_ta_the(st, uu_tien):
    """top 6 theo luot + cac nuoc ta quan tam (neu co)."""
    top = sorted(st.items(), key=lambda kv: -kv[1][0])
    hang = {m: i + 1 for i, (m, _) in enumerate(top)}
    s = "    top: " + "  ".join(f"{m}[N{v[0]} P{v[1]:.2f} Pnet{v[3]:.3f} Q{v[2]:+.2f}]" for m, v in top[:6])
    for m in uu_tien:
        if m in st:
            v = st[m]
            s += f"\n    {m}: hang {hang[m]} theo luot, N {v[0]}, Pnet {v[3]:.3f} (P sau nhieu {v[1]:.3f}), Q {v[2]:+.3f}"
    return s


log("may:", sh("nvidia-smi --query-gpu=name --format=csv,noheader")[1].strip())
sh(f"cd {C} && rm -rf chess_variant_engine && timeout 150 git clone -q --depth 1 --filter=blob:none --sparse -b {BRANCH} {REPO}.git "
   f"chess_variant_engine && cd chess_variant_engine && git sparse-checkout set custom_engine", timeout=250)
sh(f"mkdir -p {E}/build-linux && cp {UPLOADED} {E}/build-linux/custom_engine && chmod +x {E}/build-linux/custom_engine")
rc, out = sh(f"SKIP_ORT=1 bash {E}/scripts/colab_quickstart.sh 2>&1 | tail -n 2", timeout=700)
assert "[quick] OK" in out, out
for m in [NET] + CU:
    rc, out = sh(f"python3 {E}/python/lay_mang.py pt {C}/gen{m}.pt --rel {REL_NN} 2>&1 | tail -n 1", timeout=300)
    assert os.path.exists(f"{C}/gen{m}.pt"), f"khong co gen{m}.pt: {out}"
    sh(f"cd {E}/python && python3 fzw.py convert {C}/gen{m}.pt {C}/gen{m}.fzw 2>&1 | tail -n 1", timeout=300)
    assert os.path.exists(f"{C}/gen{m}.fzw"), f"khong co gen{m}.fzw"
log("da co cac mang:", [NET] + CU)

# ghi chu cho viec doc: gia tri tho tu `go nodes 1` (wdl o ngan phan, goc nhin ben di)
for m in [NET] + CU:
    eng = Engine(f"{C}/gen{m}.fzw")
    eng.khoi_dong(BASE)
    print(f"\n######## mang gen{m}" + ("  (mang sinh van; ban ghi orig_q luc sinh van o the 1 = +0.142, nuoc da di a5b5, e2b5)" if m == NET else ""), flush=True)
    for ten, k in VI_TRI:
        st, wdl, _ = tim(eng, k, 1, False)
        if wdl is None:
            print("  --- " + ten + ": khong co dong wdl", flush=True)
            continue
        w, d, l, _n = wdl
        print(f"  --- {ten}: GIA TRI THO cua mang (ben di): W {w/10:.1f}% D {d/10:.1f}% L {l/10:.1f}%  => q = {(w-l)/1000:+.3f}", flush=True)
        uu = {25: ["a5b5", "a5c3"], 26: ["e2b5"], 27: []}[k]
        # prior tho = Pnet cua cac nuoc (tu mot tim kiem rat ngan co RootStats day du): dung 800 luot khong nhieu
        cau_hinh = [(800, True, "800 luot, co nhieu (nhu luc sinh van)"), (800, False, "800 luot, khong nhieu")]
        if m == NET:
            cau_hinh += [(3200, False, "3200 luot, khong nhieu"), (12800, False, "12800 luot, khong nhieu"), (51200, False, "51200 luot, khong nhieu")]
        for nodes, nhieu, mo in cau_hinh:
            t = time.time()
            st, wdl, ds = tim(eng, k, nodes, nhieu)
            if wdl is None:
                print("  " + mo + ": khong co dong wdl", flush=True)
                continue
            w, d, l, n = wdl
            mean = re.search(r"mean ([\d.]+) max (\d+)", ds)
            print(f"  {mo}: gia tri goc sau tim kiem q = {(w-l)/1000:+.3f} | do sau tb {mean.group(1) if mean else '?'}, sau nhat {mean.group(2) if mean else '?'} | {time.time()-t:.1f}s\n{mo_ta_the(st, uu)}", flush=True)
    eng.dong()
log("XONG")
