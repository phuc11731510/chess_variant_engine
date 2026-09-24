# Gom ván thành zip (mục 4)
# Mục 4 của sổ tay: gom hàng nghìn tệp .gz thành một .zip (train.py đọc .zip trực tiếp).
# Đợi ô 04 chạy xong (log in "[fz] o 04 xong") rồi mới chạy, nếu không sẽ thiếu các ván cuối.
!python {E}/python/archive.py pack {OUT_GAMES_DIR} --out {ZIP_GAMES}
!ls -la {ZIP_GAMES}
print(f"Tai ve dien thoai: menu fz -> d -> {ZIP_GAMES}")
