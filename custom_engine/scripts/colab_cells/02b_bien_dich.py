# Biên dịch lại, chỉ khi cần (mục 1b)
# Mục 1b của sổ tay -- CHỈ KHI CẦN (~8-12 phút): Release chưa có binary, Colab đổi base image
# (ô 02 báo lỗi), hoặc bạn vừa sửa mã nguồn. Cần chạy ô 02 trước (để có mã nguồn).
!bash {E}/scripts/colab_setup.sh 2>&1
!bash {E}/scripts/colab_prebuilt.sh wrap
print()
import os
BIN = E + "/build-linux/custom_engine"
if os.path.exists(BIN):
    print("Binary moi o:", BIN)
    # Menu fz tu tai binary ve Download/FairyZero; dua no len GitHub Release (ten dung:
    # custom_engine, thay tep cu) de may Colab sau khoi bien dich (o 02 tai tu Release).
    print(f"FZ_TAI_VE={BIN}")
else:
    print("[!] Bien dich loi -- khong co binary")
