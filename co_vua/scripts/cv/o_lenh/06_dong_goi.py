# Gom ván thành zip, tải về điện thoại
# Chép theo ô 06 của fz: gom các lần sinh ĐÃ XONG của đời này (thư mục lan_* có van.bin.gz + xong.json) thành một
# .zip, kèm mọi log của từng lần sinh (log là minh chứng, giữ vĩnh viễn trên điện thoại).
# Đợi ô 04 chạy xong (log in "[fz] o 04 xong") rồi mới chạy, nếu không lần sinh đang chạy chưa được gom.
# Chạy "04 06" trong menu cv = 06 tự chạy khi 04 xong, gom zip rồi TỰ TẢI zip về Download/CoVua với TÊN TÍCH LUỸ
# (menu đặt tên theo tổng số lần chạy mạng của đời), rồi chuyển các van.bin.gz đã tải trên Colab sang
# /content/da_tai/ (06 lần sau chỉ gom lần sinh mới).
# Trong zip, đường dẫn tính từ /content (vd tt_games_gen3/lan_20261104_101500/van.bin.gz) và có tệp tong.json:
# tổng số lần chạy mạng, số ván, số lần sinh của gói.
import glob, json, os, zipfile

TAM = ZIP_GAMES + ".dang_goi"   # gom vào tệp tạm: gom lỗi giữa chừng thì zip cũ vẫn nguyên
lan = [d for d in sorted(glob.glob(OUT_GAMES_DIR + "/lan_*"))
       if os.path.exists(f"{d}/xong.json") and os.path.exists(f"{d}/van.bin.gz")]
if not lan:
    print(f"[!] Không có lần sinh nào đã xong trong {OUT_GAMES_DIR} -- không có gì để gom")
else:
    tong = {"ben": BEN, "doi": GEN_CURRENT, "evals": 0, "van_xong": 0, "lan": []}
    try:
        with zipfile.ZipFile(TAM, "w", zipfile.ZIP_STORED) as z:
            for d in lan:
                x = json.load(open(f"{d}/xong.json"))
                tong["evals"] += x["evals"]; tong["van_xong"] += x["van_xong"]
                tong["lan"].append({"lan": os.path.basename(d), "evals": x["evals"], "van_xong": x["van_xong"],
                                    "giay": x.get("giay"), "ly_do_dung": x.get("ly_do_dung")})
                for f in sorted(glob.glob(f"{d}/*")):
                    if os.path.isfile(f) and not f.endswith(".tam"):
                        z.write(f, os.path.relpath(f, "/content"))
            z.writestr(os.path.relpath(f"{OUT_GAMES_DIR}/tong.json", "/content"), json.dumps(tong, ensure_ascii=False))
        os.replace(TAM, ZIP_GAMES)
        print(f"[06] {len(lan)} lần sinh, {tong['van_xong']} ván, {tong['evals']:,} lần chạy mạng")
        !ls -la {ZIP_GAMES}
        # Menu cv đọc dòng FZ_TAI_VE= trong log, tải tệp đó về điện thoại khi ô chạy xong.
        print(f"FZ_TAI_VE={ZIP_GAMES}")
    except Exception as e:  # noqa: BLE001
        if os.path.exists(TAM):
            os.remove(TAM)
        print(f"[!] Gom zip lỗi ({type(e).__name__}: {e}) -- không tải về")
