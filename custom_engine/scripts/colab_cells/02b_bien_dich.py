# Biên dịch lại, chỉ khi cần (mục 1b)
# Mục 1b của sổ tay -- CHỈ KHI CẦN (~8-12 phút): Release chưa có binary, Colab đổi base image
# (ô 02 báo lỗi), hoặc bạn vừa sửa mã nguồn. Cần chạy ô 02 trước (để có mã nguồn).
!bash {E}/scripts/colab_setup.sh 2>&1 | tail -4
!bash {E}/scripts/colab_prebuilt.sh wrap
print()
print("Binary moi o:", E + "/build-linux/custom_engine")
print("Tai ve dien thoai (chay trong Termux, KHONG phai o day):")
print(f"  colab download -s fz {E}/build-linux/custom_engine ~/storage/downloads/FairyZero/custom_engine")
print("roi dua len GitHub Release (ten dung: custom_engine) de lan sau khoi bien dich.")
