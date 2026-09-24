# Mục 2 của sổ tay: mạng đời 0, trọng số ngẫu nhiên. Seed tự rút mỗi lần chạy và in ra log
# ([make_seed] seed ...); muốn tạo lại y hệt thì thêm --seed <số đó>.
# CHỈ chạy nếu muốn mạng đời 0 MỚI -- nó GHI ĐÈ /content/gen0.onnx và gen0.pt.
# Kiến trúc 144 x 12 SE-8 phải giữ nguyên suốt chuỗi warm-start.
!cd {E}/python && python make_seed.py --channels 144 --blocks 12 --se-ratio 8 \
    --out /content/gen0.onnx
!ls -la /content/gen0.*
print("Tai ve dien thoai (chay trong Termux):")
print("  colab download -s fz /content/gen0.onnx ~/storage/downloads/FairyZero/gen0.onnx")
print("  colab download -s fz /content/gen0.pt   ~/storage/downloads/FairyZero/gen0.pt")
