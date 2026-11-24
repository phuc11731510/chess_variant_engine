"""kiem.py -- kiem ket qua cua chay_thu.sh (bo thu vong lap lien tuc bang may Colab gia).
Doi chieu SO CAI cua engine gia (/tmp/fc/ledger: moi van xong mot dong) voi cac GOI tren "dien thoai": moi van phai ve dung MOT lan
(khong mat, khong trung) -- tru kich ban mat_may, noi van chua gui luc mat may duoc phep mat."""
import glob
import json
import os
import re
import sys
import zipfile

kb, W, TAI, H, GEN0 = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])
PASS = FAIL = 0


def check(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [ok] {msg}")
    else:
        FAIL += 1
        print(f"  [FAIL] {msg}")


led = []
for l in open(f"{W}/ledger"):
    p = l.split()
    if len(p) == 4:
        led.append((p[0], p[1], p[2], float(p[3])))
print(f"\n== KIEM ({kb}) ==")
check(len(led) > 0, f"engine gia da choi {len(led)} van")
mong = {}
for acc, d, g, t in led:
    m = re.fullmatch(r"games_gen(\d+)_(\d+)", d)
    mong.setdefault(f"games_gen{m.group(1)}/{acc}_{m.group(2)}_{g}", 0)
    mong[f"games_gen{m.group(1)}/{acc}_{m.group(2)}_{g}"] += 1
check(all(v == 1 for v in mong.values()), "so cai: moi van mot lan (khong trung ten)")

goi = sorted(glob.glob(f"{TAI}/goi/goi_*.zip"))
co = {}
tong_van = tong_the = 0
for p in goi:
    m = re.fullmatch(r"goi_(\d+)_n(\d+)_(\d+)_(\d+)\.zip", os.path.basename(p))
    with zipfile.ZipFile(p) as z:
        ten = z.namelist()
    check_ok = len(ten) == int(m.group(3))
    if not check_ok:
        check(False, f"{os.path.basename(p)}: ten goi bao {m.group(3)} van nhung zip co {len(ten)}")
    tong_van += int(m.group(3))
    tong_the += int(m.group(4))
    for n in ten:
        co[n] = co.get(n, 0) + 1
print(f"  ({len(goi)} goi, {tong_van} van, {tong_the} the; so cai {len(led)} van)")
check(all(v == 1 for v in co.values()), f"goi: khong van nao nam hai lan ({sum(v - 1 for v in co.values())} trung)")
check(set(co) <= set(mong), f"goi: moi van trong goi deu co trong so cai ({len(set(co) - set(mong))} la)")
mat = set(mong) - set(co)
if kb == "mat_may":
    check(len(mat) > 0, f"mat may: {len(mat)} van chua gui bi mat (dung nhu du kien)")
    check(len(mat) < 0.5 * len(mong), f"mat may: chi mat {len(mat)}/{len(mong)} van")
else:
    check(not mat, f"khong mat van nao ({len(mat)} van tren may chua ve dien thoai)")

# cac lan huan luyen
tl = [l.split() for l in open(f"{W}/train.log")] if os.path.exists(f"{W}/train.log") else []
bd = [t for t in tl if t[0] == "bat_dau"]
xg = {(t[1], t[2]): float(t[3]) for t in tl if t[0] == "xong"}
check(len(bd) >= 2, f"co {len(bd)} lan huan luyen")
for t in bd:
    acc, gen, t0 = t[1], t[2], float(t[3])
    t1 = xg.get((acc, gen), t0 + 5)
    khac = [x for x in led if x[0] != acc and t0 < x[3] < t1]
    check(len(khac) >= 1, f"{acc} huan luyen doi {gen} trong {t1 - t0:.0f}s: cua so khac van sinh {len(khac)} van")
    check(int(t[5]) >= 1, f"  cua so huan luyen doi {gen} co {t[4]} goi / {t[5]} van")

gens = sorted(int(re.fullmatch(r"gen(\d+)\.pt", os.path.basename(p)).group(1)) for p in glob.glob(f"{W}/release/gen*.pt"))
check(len(gens) >= 2 and gens == list(range(gens[0], gens[0] + len(gens))), f"Release co mang {gens}")
cfg = open(f"{TAI}/o_lenh/00_cau_hinh.py").read()
g_cuoi = int(re.search(r"^GEN_CURRENT = (\d+)", cfg, re.M).group(1))
check(g_cuoi == (gens[-1] if gens else -1), f"GEN_CURRENT = {g_cuoi} = mang moi nhat tren Release")

# may da tra het
for acc in ("acc1", "acc2"):
    f = f"{H}/.fz_tk/{acc}/.config/colab-cli/fake_sessions.json"
    ss = json.load(open(f)) if os.path.exists(f) else {}
    check(not ss, f"{acc}: da tra may ({list(ss)})")

# loi bash / python trong log
bad = 0
logs = []
for k in (1, 2):
    log = open(f"{W}/log_w{k}.txt", errors="replace").read()
    for pat in (r"command not found", r"syntax error", r"Traceback", r"unbound variable", r"bad substitution", r"integer expression expected"):
        for m in re.finditer(pat, log):
            bad += 1
            print(f"  log cua so {k}: '{pat}' ... {log[max(0, m.start() - 120):m.end() + 60]!r}")
    check("vòng lặp liên tục đã dừng" in log or "thoát" in log, f"cua so {k} thoat sach")
    logs.append(log)
check(bad == 0, "log khong co loi bash / python")
if kb == "xin_muon":
    nk = open(f"{H}/.fz_tk/.tu_dong/nhat_ky.txt", encoding="utf-8", errors="replace").read() if os.path.exists(f"{H}/.fz_tk/.tu_dong/nhat_ky.txt") else ""
    check("Xin máy quá giờ" in "\n".join(logs), "xin het gio duoc nhan ra")
    check("muộn (sau khi ta bỏ yêu cầu) -> trả máy đó" in nk, "quet muon chay nen da tra may cap cham (ghi trong nhat ky vong lap)")
if kb == "dung_cu":
    for i, l in enumerate(logs, 1):
        a, b = l.find("04l trên"), l.find("dừng mềm")
        check(a != -1 and (b == -1 or a < b), f"cua so {i}: van chay engine (04l) truoc khi co lenh dung that, KHONG tu dung vi tep dung cu")
if kb == "len_loi":
    tong = "\n".join(logs)
    check("Colab từ chối ssh mới (429" in tong, "co gap loi 429 (mo phong) va nhan ra")
    check("bỏ lượt huấn luyện" not in tong, "KHONG bo luot huan luyen vi loi tai goi")
    check(tong.count("gói) lên máy bằng một luồng") + tong.count("lên máy bằng một luồng") >= 2, "tai goi bang luong tar, thu lai sau khi bi dut")
if kb == "nap_lai":
    tong = "\n".join(logs)
    check("đã nạp lại mã mới" in tong, "cua so bao da nap lai ma moi (khong mo lai cua so)")
    sau = tong.split("đã nạp lại mã mới", 1)[1] if "đã nạp lại mã mới" in tong else ""
    check("[v2]" in sau, "sau khi nap, ham gui goi dung ban moi ('[v2]' trong thong bao gui goi)")
    check("có lỗi cú pháp" in tong, "ban co loi cu phap bi tu choi, vong lap giu ban dang chay")
    check("[v2]" in tong.split("có lỗi cú pháp", 1)[-1] if "có lỗi cú pháp" in tong else False, "...va van chay tiep sau ban hong (con gui goi ban '[v2]')")
if kb == "xin_treo":
    check(any("Xin máy quá giờ" in l for l in logs), "lenh xin het gio duoc bao la het gio (khong phai 'may da duoc cap')")
    check(not any("máy của acc" in l and "đã mất" in l for l in logs), "KHONG bao 'may da mat' sai khi chua tung co may")
    check(any("trả máy đó" in l for l in logs), "may cap muon (phien khong ten) da duoc tra")
    check(not any("dùng máy này" in l for l in logs), "khong coi lenh xin loi la 'da co may'")
if kb == "arena":
    check(any("arena gen" in l for l in logs), "it nhat mot cua so da danh arena")
    arena_files = glob.glob(f"{TAI}/arena/gen*_vs_gen*.txt")
    check(len(arena_files) >= 2 and all(any(x.startswith("XONG") for x in open(f)) for f in arena_files), f"arena ghi ket qua XONG: {[os.path.basename(f) for f in arena_files]}")
print(f"\nKET QUA: {PASS} pass, {FAIL} fail")
sys.exit(1 if FAIL else 0)
