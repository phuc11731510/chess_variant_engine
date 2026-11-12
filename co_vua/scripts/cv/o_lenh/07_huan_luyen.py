# Huấn luyện đời sau
# Chép theo ô 07 của fz: huấn luyện đời sau, warm-start từ <cách>_gen{GEN_CURRENT}.pt (ô 02c). Dữ liệu: gói gộp
# ZIP_GAMES (vòng lặp gộp trên điện thoại: đời hiện tại + 3 đời trước, mỗi đời một thư mục <cách>_games_gen<k>/,
# rồi tải lên). Chạy tay: tự tải gói gộp lên /content (menu u) trước.
# Tham số theo ô 07 của fz (từ đời 12 của fz, 2026-09-29): cửa sổ 4 đời, 1 epoch, SWA kiểu lc0 (cứ 25 bước lấy trung
# bình trọng số một lần, tối đa 10 bản), tốc độ học không đổi 1e-3, batch 1024, weight decay 1e-4, q-ratio 0.2. Khác
# fz một chỗ: không --amp, mọi phép tính fp32 (chủ dự án chốt).
# Như --val-newest-gen của fz: trước khi học, py/huan_luyen.py chấm mạng đời hiện tại MỘT LẦN trên toàn bộ mẫu của
# đời mới nhất (ván nó vừa chơi, chưa học) -- hai số mat_*_dau_tren_doi_moi trong dòng JSON tóm tắt; so giữa các đời.
import glob, os, re, shutil, subprocess

HL = "/content/hl"
shutil.rmtree(HL, ignore_errors=True)
os.makedirs(HL)
SO_BUOC = 0
if BEN == "cay":
    # Cách cây trò chơi (THIET_KE_CO_VUA.md 10, 12.6): điện thoại gửi một tệp tar gồm nhãn (nhan_doi<G>.npz, cay.py)
    # và các mau.npz chứa mặt phẳng đầu vào của các node; py/gop_mau_cay.py ghép thành một tệp mẫu có trọng số w (số
    # ván đi qua node). Số bước = số bước của cách truyền thống ở cùng đời (12.6), ghi sẵn trong nhãn.
    import numpy as _np
    TAR = f"/content/cay_hl_gen{GEN_CURRENT}.tar"
    !tar -xf {TAR} -C {HL}
    # Kho đệm (8/11): mau.npz đã có trên Release co_vua_du_lieu thì điện thoại không gửi lại; tải theo .kho.txt rồi
    # ghép lại .tep.txt đầy đủ cho gop_mau_cay.py (dòng "-1" chỉ là chỗ chỉ tới .kho.txt).
    _f_tep, _f_kho = f"{HL}/nhan_doi{GEN_CURRENT}.tep.txt", f"{HL}/nhan_doi{GEN_CURRENT}.kho.txt"
    if os.path.exists(_f_kho):
        _kho = [d.rstrip("\n").split("\t") for d in open(_f_kho, encoding="utf-8") if d.strip()]
        THIEU_KHO = lay_kho([(p, t, int(kt)) for _, p, t, kt in _kho], HL)
        _dong = [d for d in open(_f_tep, encoding="utf-8") if d.strip() and not d.startswith("-1\t")]
        with open(_f_tep, "w", encoding="utf-8") as _f:
            _f.write("".join(_dong) + "".join(f"{i}\t{p}\n" for i, p, _, _ in _kho))
    NHAN = f"{HL}/nhan_doi{GEN_CURRENT}.npz"
    # Nhãn gọn (8/11): pi lưu uint16 (pol_q) + độ dài đoạn mỗi node (pol_dem) -> pol_p (chia lại cho tổng mỗi node),
    # pol_off như gop_mau_cay.py trong gói vẫn đọc.
    if os.path.exists(NHAN):
        _z = dict(_np.load(NHAN))
        if "pol_q" in _z:
            _dem = _z.pop("pol_dem").astype(_np.int64)
            _own = _np.repeat(_np.arange(len(_dem)), _dem)
            _p = _z.pop("pol_q").astype(_np.float64)
            _p /= _np.maximum(_np.bincount(_own, _p, len(_dem)), 1e-12)[_own]
            _z["pol_p"] = _p.astype(_np.float32)
            _z["pol_off"] = _np.concatenate(([0], _np.cumsum(_dem))).astype(_np.int64)
            del _own, _p
            _np.savez(NHAN, **_z)
        del _z
    !cd {CV}/py && python3 gop_mau_cay.py {HL}/mau_cay.npz {NHAN} {HL}/nhan_doi{GEN_CURRENT}.tep.txt {HL}
    MAU = [f"{HL}/mau_cay.npz"] if os.path.exists(f"{HL}/mau_cay.npz") else []
    # Mọi trọng số bằng nhau (12/11: mỗi node được học như nhau): bỏ "w" để huan_luyen.py xáo trộn rồi đi lần lượt như
    # cách truyền thống (mỗi node tối đa một lần), kể cả trên máy còn gói cũ (huan_luyen.py cũ bốc có lặp khi có "w").
    if MAU:
        _m = dict(_np.load(MAU[0]))
        if "w" in _m and len(_m["w"]) and float(_m["w"].min()) == float(_m["w"].max()):
            del _m["w"]
            _np.savez(MAU[0], **_m)
            print("[07] trọng số đều -> xáo trộn, mỗi node tối đa một lần mỗi lượt")
        del _m
    SO_BUOC = int(_np.load(NHAN)["so_buoc"]) if os.path.exists(NHAN) else 0
    cac_doi = []
else:
    !cd {HL} && python3 -c "import zipfile, sys; zipfile.ZipFile(sys.argv[1]).extractall('.')" {ZIP_GAMES}
    # Kho đệm (8/11): mau.npz đã có trên Release co_vua_du_lieu thì điện thoại không gửi lại (kho_ds.txt trong gói).
    if os.path.exists(f"{HL}/kho_ds.txt"):
        _kho = [d.rstrip("\n").split("\t") for d in open(f"{HL}/kho_ds.txt", encoding="utf-8") if d.strip()]
        THIEU_KHO = lay_kho([(p, t, int(kt)) for p, t, kt in _kho], HL)
cac_doi = cac_doi if BEN == "cay" else sorted((int(re.search(r"_games_gen(\d+)$", d).group(1)), d)
                 for d in glob.glob(f"{HL}/{BEN}_games_gen*") if os.path.isdir(d))
# Mỗi lần sinh là một thư mục con (trên điện thoại gộp đặt tên <N>_lan_<giờ>) có mau.npz (từ 8/11 điện thoại không
# gửi van.bin.gz khi đã có mau.npz) hoặc van.bin.gz (gop_mau.py mã hoá lại).
def _la_lan(x):
    return os.path.exists(x + "/mau.npz") or os.path.exists(x + "/van.bin.gz")
print("[07] cửa sổ dữ liệu: " + ", ".join(f"đời {k} ({sum(map(_la_lan, glob.glob(d + '/*')))} lần sinh)" for k, d in cac_doi))
# Mỗi lần sinh đã được mã hoá sẵn trên máy sinh (mau.npz trong thư mục lan_*): chỉ việc nạp và nối theo đời. Lần nào
# thiếu mau.npz thì py/gop_mau.py mã hoá lại từ van.bin.gz (cùng bộ mã hoá).
MAU = MAU if BEN == "cay" else []
for k, d in cac_doi:
    lan_ = " ".join(x for x in sorted(glob.glob(d + "/*")) if _la_lan(x))
    if not lan_:
        continue
    !cd {CV}/py && python3 gop_mau.py {HL}/mau_doi{k}.npz {lan_}
    MAU.append(f"{HL}/mau_doi{k}.npz")
# Đời mới nhất phải là tệp CUỐI của --mau (huan_luyen.py chấm mạng đầu trên tệp cuối).
ok = bool(MAU) and (BEN == "cay" or MAU[-1].endswith(f"mau_doi{GEN_CURRENT}.npz")) and os.path.exists(CURRENT_PT)
if globals().get("THIEU_KHO"):                   # thiếu tệp của kho đệm: không huấn luyện trên cửa sổ dữ liệu thiếu
    print(f"[!] Không tải được {len(THIEU_KHO)} tệp từ kho đệm (Release co_vua_du_lieu), vd {THIEU_KHO[0]} -- không huấn luyện")
    ok = False
if not ok:
    print(f"[!] Thiếu dữ liệu đời {GEN_CURRENT} trong {ZIP_GAMES} hoặc thiếu {CURRENT_PT} (ô 02c) -- không huấn luyện")
else:
    RA = NEXT_PT[:-len(".pt")]
    cmd = f"""cd {CV}/py && python3 huan_luyen.py --mau {",".join(MAU)} --khoi-tao {CURRENT_PT} --ra {RA} \
        --batch 1024 --lr 1e-3 --weight-decay 1e-4 --so-luot 1 --swa-moi 25 --swa-toi-da 10 --so-buoc {SO_BUOC}"""
    print(cmd)
    !{cmd} | tee {RA}.hl.json
    !{CV}/lc0 onnx2leela --input={RA}.onnx --output={NEXT_PB} \
        --onnx-input=input_planes --onnx-output-policy=policy --onnx-output-wdl=wdl --moves-left-format=MOVES_LEFT_NONE
    if os.path.exists(NEXT_PB) and os.path.exists(NEXT_PT):
        !ls -la {NEXT_PB} {NEXT_PT} && sha256sum {NEXT_PB} {NEXT_PT}
        # Menu cv đọc các dòng FZ_TAI_VE=: tải mạng đời mới (và tóm tắt huấn luyện) về Download/CoVua khi ô xong.
        print(f"FZ_TAI_VE={NEXT_PB}")
        print(f"FZ_TAI_VE={NEXT_PT}")
        print(f"FZ_TAI_VE={RA}.hl.json")
    else:
        print("[!] Huấn luyện lỗi -- không tải về")
