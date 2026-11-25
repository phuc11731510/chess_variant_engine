"""kiem.py -- kiem ket qua cua chay_thu.sh (bo thu vong lap lien tuc bang may Colab gia).
Doi chieu SO CAI cua engine gia (/tmp/fc/ledger: moi van xong mot dong) voi cac GOI tren "dien thoai": moi van phai ve dung MOT lan
(khong mat, khong trung) -- tru kich ban mat_may, noi van chua gui luc mat may duoc phep mat."""
import collections
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
elif kb == "tu_canh":
    # cua so tu canh nho (vai chuc nghin the): `don_goi` xoa goi cu hon 1,5 lan cua so -> mot phan van (da vao huan luyen) khong con tren dien thoai; khong coi la mat
    check(len(mat) < len(mong), f"tu_canh: con {len(co)}/{len(mong)} van tren dien thoai (cac goi cu bi don theo cua so 1,5 lan)")
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
if kb == "tu_canh":
    tong = "\n".join(logs)
    td = f"{H}/.fz_tk/.tu_dong"
    moi = [int(x) for x in open(f"{td}/.lt_the_moi").read().split()] if os.path.exists(f"{td}/.lt_the_moi") else []
    ls = [l.split() for l in open(f"{td}/.lt_lich_su_hl")] if os.path.exists(f"{td}/.lt_lich_su_hl") else []
    check(len(moi) >= 3, f"lich su the moi co {len(moi)} dong (moi lan huan luyen thanh cong ghi mot so)")
    check(len(ls) >= 1 and all(len(x) == 3 and all(v.isdigit() for v in x) for x in ls), f"lich su thoi gian co {len(ls)} dong dung dang 'gom huan_luyen the_cua_so'")
    cs = {}                                     # doi -> so the cua so ghi trong dong '07: huan luyen doi N (cua so X the)'
    for m in re.finditer(r"07: huấn luyện đời (\d+) \(cửa sổ (\d+) thế\)", tong):
        cs[int(m.group(1))] = int(m.group(2))
    gens_hl = sorted(cs)
    check(len(gens_hl) >= 4, f"co {len(gens_hl)} lan huan luyen: {[ (g, cs[g]) for g in gens_hl ]}")
    if len(gens_hl) >= 4 and len(moi) >= 3:
        # lan thu 4: cua so = 2 (muc tieu) x TB 3 lan truoc (da co du 3 lan lich su)
        mong = (sum(moi[:3]) // 3) * 2
        check(cs[gens_hl[3]] == mong, f"cua so lan huan luyen thu 4 = {cs[gens_hl[3]]} = 2 x TB the moi 3 lan truoc ({mong})")
    check(all(1000 <= x <= 100000000 for x in cs.values()) and 625447 not in cs.values(), "cua so la so tu canh (khong phai mac dinh 625447 / khong ngoai kep)")
    check(not any(t[1] == "acc1" for t in bd), "acc1 (T4 con 35 phut < nguong huan luyen 40 phut) KHONG huan luyen")
    check(any(t[1] == "acc2" for t in bd), "acc2 huan luyen")
if kb == "doc_429":
    tong = "\n".join(logs)
    check("Colab từ chối ssh mới (429: phiên ssh trước chưa được giải phóng)" in tong, "co gap 429 khi doc log o 07 (mo phong) va nhan ra")
    check("KHÔNG huấn luyện lại" in tong, "het luot thu trong tai_theo_o thi vong lap con doc lai (khong coi la huan luyen hong)")
    check("huấn luyện chưa ra mạng" not in tong and "bỏ lượt huấn luyện" not in tong, "KHONG huan luyen lai / bo luot vi loi doc log")
    dem = collections.Counter((t[1], t[2]) for t in bd)
    check(all(v == 1 for v in dem.values()) and len(dem) >= 1, f"moi doi chi huan luyen MOT lan: {dict(dem)}")
if kb in ("len_colab", "len_colab_loi"):
    tong = "\n".join(logs)
    TOKEN = "TOKEN_GIA_abc123XYZ"
    cmds = open(f"{W}/ssh_cmds.log", errors="replace").read() if os.path.exists(f"{W}/ssh_cmds.log") else ""
    gtok = open(f"{W}/gh_token.log").read().split() if os.path.exists(f"{W}/gh_token.log") else []
    check(TOKEN not in cmds, "token KHONG nam tren dong lenh ssh (chi di qua dau vao)")
    check(TOKEN not in tong and TOKEN not in (open(f"{H}/.fz_tk/.tu_dong/nhat_ky.txt", errors="replace").read() if os.path.exists(f"{H}/.fz_tk/.tu_dong/nhat_ky.txt") else ""), "token KHONG xuat hien trong log cua so / nhat ky vong lap")
    check(len(gtok) >= 1 and all(t == "TOKEN:" + TOKEN for t in gtok), f"gh phia Colab nhan dung token qua GH_TOKEN ({len(gtok)} lan)")
    tren_dt = [os.path.basename(p) for p in glob.glob(f"{TAI}/gen*.pt")]
    if kb == "len_colab":
        check("từ máy Colab" in tong and "đã lên Release" in tong, "log noi mang len GitHub tu may Colab")
        check("Colab từ chối ssh mới (429)" in tong, "gap 429 o lan ssh tai len dau tien va cho roi thu lai")
        check(len(gtok) >= 2, f"it nhat 2 mang len bang duong Colab ({len(gtok)})")
        check(not tren_dt, f"dien thoai KHONG tai mang nao ve (con {tren_dt})")
        check("tải gen" not in tong, "khong con dong 'tai genN.pt len GitHub' cua duong cu")
    else:
        check("GitHub từ chối token" in tong and "dùng đường cũ" in tong, "gap loi token o Colab va noi ro chuyen ve duong cu")
        check("tải gen" in tong and "lên GitHub (" in tong, "mang van len GitHub bang duong cu (tai ve dien thoai roi tai len)")
        check(len(gtok) == 1, f"luot sau khong thu lai duong Colab trong thoi gian nghi ({len(gtok)} lan thu)")
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
