# -*- coding: utf-8 -*-
"""thu_do_sau_t4.py -- 800 luot tham tren moi the cua mot mau 1000 the (lay deu qua toan bo cac the cua 4000 van gan nhat): tim kiem di xuong sau bao nhieu?

Moi the duoc tim lai tu dau (cay moi, KHONG dung lai cay nhu trong van tu dau) bang chinh mang da sinh van do (n107..n111, tu Release NN_Model), voi cung
cai dat tim kiem cua tu dau (04l): 800 luot, cpuct 1,5 co dinh, cpuct-factor 0, uu tien o chua tham 0, nhieu Dirichlet goc 0,25 / 0,15, minibatch 32,
khong prefetch, policy-temp 1,0, khong hoa lap hai lan; lich su that cua van (FEN dau van + cac nuoc da di) nen mang thay du 8 the truoc.
Dung binary co tuy chon `DepthStats` (UCI `setoption name DepthStats value true`): doc tren cay da tim xong xem moi luot ket thuc o do sau nao
(xem uci_nn_engine.cc, EmitBestMove). Luot thu hai: 200 luot kieu tim kiem NHANH cua tu dau (cpuct 1,25, nhieu goc 0,125), cung cac the.

Chay: python3 ~/chay_t4_thu.py thu_do_sau_t4.py --can-phut 25 --timeout 1800 --tep <custom_engine_fzcuda>:/content/custom_engine_fzcuda --tep <the_do_sau.tsv>:/content/the_do_sau.tsv
Ket qua: moi the mot dong `R <json>` tren stdout (phan tich o may nay)."""
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

BRANCH = "luat-moi"
REPO = "https://github.com/phuc11731510/chess_variant_engine"
REL_NN = REPO + "/releases/download/NN_Model"
C = "/content"
E = f"{C}/chess_variant_engine/custom_engine"
UPLOADED = f"{C}/custom_engine_fzcuda"
TSV = f"{C}/the_do_sau.tsv"
T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:6.0f}s]", *a, flush=True)


def shq(s):
    return "'" + s.replace("'", "'\"'\"'") + "'"


def sh(cmd, timeout=900):
    p = subprocess.run(["bash", "-c", f"timeout -k 5 {timeout} bash -c {shq(cmd)}"], capture_output=True, text=True, errors="replace")
    return p.returncode, p.stdout + p.stderr


class Engine:
    def __init__(self, fzw, mo_ta):
        self.p = subprocess.Popen(["bash", f"{E}/run.sh", "--uci-nn", "--weights", fzw, "--provider", "fzcuda", "--fixed-batch", "32"],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, errors="replace")
        self.q = queue.Queue()
        threading.Thread(target=self._doc, daemon=True).start()
        self.mo_ta = mo_ta

    def _doc(self):
        for l in self.p.stdout:
            self.q.put(l.rstrip("\n"))
        self.q.put(None)

    def gui(self, s):
        self.p.stdin.write(s + "\n")
        self.p.stdin.flush()

    def cho(self, dk, timeout):
        out = []
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                l = self.q.get(timeout=1)
            except queue.Empty:
                continue
            if l is None:
                raise RuntimeError(f"engine {self.mo_ta} chet: " + " | ".join(out[-5:]))
            out.append(l)
            if dk(l):
                return out
        raise TimeoutError(f"engine {self.mo_ta} khong tra loi trong {timeout}s: " + " | ".join(out[-5:]))

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


BASE = {"ReuseTree": "false", "Threads": "1", "DepthStats": "true", "MultiPV": "1", "PolicySoftmaxTemp": "1.0",
        "cpuct-factor": "0", "fpu-value": "0", "two-fold-draws": "false", "sticky-endgames": "false", "task-workers": "0",
        "max-prefetch": "0", "minibatch-size": "32", "nn-cache-size": "2000000", "noise-alpha": "0.15"}
CAI = {
    "800": dict(BASE, **{"cpuct": "1.5", "noise-epsilon": "0.25"}),                  # tim kiem day du cua tu dau
    "200": dict(BASE, **{"cpuct": "1.25", "noise-epsilon": "0.125"}),                # tim kiem nhanh (PCR) cua tu dau
}


def tim(eng, the, nodes, in_ra=False):
    t0 = time.time()
    eng.gui("ucinewgame")
    eng.gui(f"position fen {the['fen']}" + (f" moves {the['nuoc']}" if the["nuoc"] else ""))
    eng.gui(f"go nodes {nodes}")
    out = eng.cho(lambda l: l.startswith("bestmove"), 120)
    if in_ra:
        for l in out[-12:]:
            print("    ", l[:300], flush=True)
    kq = {"id": the["id"], "mang": the["mang"], "nodes_yc": nodes, "giay": round(time.time() - t0, 3)}
    ds = None
    for l in out:
        if l.startswith("info string depthstats"):
            ds = l.split()[3:]
        elif l.startswith("info depth") and " seldepth " in l:
            m = re.match(r"info depth (\d+) seldepth (\d+)", l)
            kq["d_info"], kq["s_info"] = int(m.group(1)), int(m.group(2))
            m = re.search(r" nodes (\d+)", l)
            if m:
                kq["n_info"] = int(m.group(1))
        elif l.startswith("info depth") and " multipv 1 " in l:
            m = re.match(r"info depth (\d+) multipv 1 score cp (-?\d+) wdl (\d+) (\d+) (\d+) nodes (\d+)", l)
            if m:
                kq["pv24"], kq["cp"], kq["wdl"], kq["nodes_root"] = int(m.group(1)), int(m.group(2)), [int(m.group(i)) for i in (3, 4, 5)], int(m.group(6))
        elif l.startswith("bestmove"):
            kq["bestmove"] = l.split()[1]
    if ds is None:
        raise RuntimeError("khong co dong depthstats: " + " | ".join(out[-6:]))
    for i in range(0, len(ds) - 1, 2):
        k, v = ds[i], ds[i + 1]
        if k == "leaf":
            kq["leaf"] = [int(x) for x in v.split(",")]
        else:
            kq[k] = float(v) if k == "mean" else int(v)
    return kq


def cong_viec(args):
    mang, ds_the, mo_ta = args
    fzw = f"{C}/gen{mang}.fzw"
    ket_qua = []
    for ten, nodes in (("800", 800), ("200", 200)):
        eng = Engine(fzw, f"{mo_ta}/{ten}")
        try:
            eng.khoi_dong(CAI[ten])
            for the in ds_the:
                r = tim(eng, the, nodes)
                ket_qua.append((ten, r))
                print("R " + json.dumps(dict(r, luot=ten)), flush=True)
        finally:
            eng.dong()
    return mo_ta, ket_qua


log("may:", sh("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader")[1].strip(), "| CPU:", os.cpu_count())
sh(f"cd {C} && rm -rf chess_variant_engine && timeout 150 git clone -q --depth 1 --filter=blob:none --sparse -b {BRANCH} {REPO}.git "
   f"chess_variant_engine && cd chess_variant_engine && git sparse-checkout set custom_engine", timeout=250)
sh(f"mkdir -p {E}/build-linux && cp {UPLOADED} {E}/build-linux/custom_engine && chmod +x {E}/build-linux/custom_engine")
rc, out = sh(f"SKIP_ORT=1 bash {E}/scripts/colab_quickstart.sh 2>&1 | tail -n 4", timeout=700)
print(out, flush=True)
assert "[quick] OK" in out, "quickstart khong OK"

the = []
with open(TSV, encoding="utf-8") as f:
    cot = f.readline().rstrip("\n").split("\t")
    for l in f:
        v = l.rstrip("\n").split("\t")
        d = dict(zip(cot, v))
        d["id"], d["mang"] = int(d["id"]), int(d["mang"])
        the.append(d)
log(f"{len(the)} the; mang: " + ", ".join(f"n{m}={sum(1 for t in the if t['mang'] == m)}" for m in sorted({t['mang'] for t in the})))

mangs = sorted({t["mang"] for t in the})
for m in mangs:
    rc, out = sh(f"python3 {E}/python/lay_mang.py pt {C}/gen{m}.pt --rel {REL_NN} 2>&1 | tail -n 1", timeout=300)
    assert os.path.exists(f"{C}/gen{m}.pt"), f"khong co gen{m}.pt: {out}"
    rc, out = sh(f"cd {E}/python && python3 fzw.py convert {C}/gen{m}.pt {C}/gen{m}.fzw 2>&1 | tail -n 1", timeout=300)
    assert os.path.exists(f"{C}/gen{m}.fzw"), f"khong co gen{m}.fzw: {out}"
log(f"da co {len(mangs)} mang .fzw: {mangs}")

log("thu mot the (in ca dong tho cua engine)")
e = Engine(f"{C}/gen{the[0]['mang']}.fzw", "thu")
e.khoi_dong(CAI["800"])
tim(e, the[0], 800, in_ra=True)
tim(e, the[0], 800, in_ra=False)
e.dong()

# hai tien trinh engine song song (T4 co 2 vCPU: mot luong tim kiem chi dung ~mot nhan, GPU con ranh)
viec = []
for m in mangs:
    ds = [t for t in the if t["mang"] == m]
    for s in (0, 1):
        viec.append((m, ds[s::2], f"n{m}{'ab'[s]}"))
log(f"chay {len(viec)} viec tren 2 luong")
tong = 0
with ThreadPoolExecutor(2) as ex:
    for mo_ta, kq in ex.map(cong_viec, viec):
        tong += len(kq)
        log(f"xong {mo_ta}: {len(kq)} ket qua (tong {tong})")
log("XONG")
