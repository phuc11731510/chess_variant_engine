# Mục 4 của sổ tay: gom hàng nghìn tệp .gz thành một .zip (train.py đọc .zip trực tiếp).
# Đợi ô 05 báo "KHONG con tien trinh" rồi mới chạy, nếu không sẽ thiếu các ván cuối.
!python {E}/python/archive.py pack {OUT_GAMES_DIR} --out {ZIP_GAMES}
!ls -la {ZIP_GAMES}
print("Tai ve dien thoai (chay trong Termux):")
print(f"  colab download -s fz {ZIP_GAMES} ~/storage/downloads/FairyZero/games_gen{GEN_CURRENT}.zip")
