# Chuẩn bị huấn luyện GIẢ: chỉ bảo đảm có gen<GEN_CURRENT>.pt (lay_mang)
import os
p = f"/content/gen{GEN_CURRENT}.pt"
if not os.path.exists(p):
    open(p, "wb").write(os.urandom(64))
print("[02c giả] xong")
