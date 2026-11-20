# Tạo mạng đời 0 MỚI, ghi đè gen0 (mục 2)
# Mục 2 của sổ tay: mạng đời 0, trọng số ngẫu nhiên. Seed tự rút mỗi lần chạy và in ra log
# ([make_seed] seed ...); muốn tạo lại y hệt thì thêm --seed <số đó>.
# CHỈ chạy nếu muốn mạng đời 0 MỚI -- nó GHI ĐÈ /content/gen0.onnx và gen0.pt.
# Kiến trúc transformer (d_model 192, 10 tầng, 6 đầu: mặc định của make_seed.py và train.py) phải giữ nguyên suốt
# chuỗi warm-start.
!cd {E}/python && python make_seed.py \
    --out /content/gen0.onnx
!ls -la /content/gen0.*
print("Tai ve dien thoai: menu fz -> d -> /content/gen0.pt (CHI .pt; Release NN_Model khong giu .onnx, moi may "
      "chuyen .pt -> .onnx tai cho). Roi tu tai gen0.pt len Release NN_Model.")
