# Gom ván thành zip, tải về điện thoại (mục 4)
# Mục 4 của sổ tay: gom hàng nghìn tệp .gz thành một .zip (train.py đọc .zip trực tiếp).
# Đợi ô 04 chạy xong (log in "[fz] o 04 xong") rồi mới chạy, nếu không sẽ thiếu các ván cuối.
# Chạy "04 06" trong menu fz = 06 tự chạy khi 04 xong, gom zip rồi TỰ TẢI zip về
# Download/FairyZero (đã có tệp cùng tên -> lưu "games_gen0 (2).zip", không ghi đè).
import os

TAM = ZIP_GAMES + ".dang_goi"   # gom vào tệp tạm: gom lỗi giữa chừng thì zip cũ vẫn nguyên
!python {E}/python/archive.py pack {OUT_GAMES_DIR} --out {TAM}
if _exit_code == 0 and os.path.exists(TAM):
    os.replace(TAM, ZIP_GAMES)
    !ls -la {ZIP_GAMES}
    # Menu fz đọc dòng FZ_TAI_VE= trong log, tải tệp đó về điện thoại khi ô chạy xong.
    print(f"FZ_TAI_VE={ZIP_GAMES}")
else:
    if os.path.exists(TAM):
        os.remove(TAM)
    print("[!] Gom zip lỗi -- không tải về")
