# Tạo mạng đời 0 MỚI cho CẢ HAI cách (ghi đè tt_gen0, cay_gen0)
# Chép theo ô 03 của fz: mạng đời 0, trọng số ngẫu nhiên, fp32. Hai cách bắt đầu từ CÙNG một mạng đời 0 (so sánh
# công bằng), nên ô này ghi một mạng ra hai tên tt_gen0.* và cay_gen0.* (cùng nội dung, sha256 in ở cuối).
# CHỈ chạy nếu muốn mạng đời 0 MỚI. Kiến trúc 11 x 64 SE-8 (py/mang.py) phải giữ nguyên suốt chuỗi warm-start.
# Seed NGẪU NHIÊN mỗi lần tạo (chủ dự án chốt 2026-11-04), in ra và ghi vào <cách>_gen0.seed.txt (tải về điện thoại)
# để tạo lại y hệt được. Muốn tạo lại một mạng cũ: thay dòng dưới bằng SEED = <số đã ghi>.
import random as _r
SEED = _r.SystemRandom().randrange(1, 2**31)
print(f"[gen0] SEED = {SEED}")
!mkdir -p /content/doi0_moi && cd {CV}/py && python3 tao_mang_doi0.py /content/doi0_moi {SEED}
!{CV}/lc0 onnx2leela --input=/content/doi0_moi/doi0.onnx --output=/content/doi0_moi/doi0.pb.gz \
    --onnx-input=input_planes --onnx-output-policy=policy --onnx-output-wdl=wdl --moves-left-format=MOVES_LEFT_NONE
for _ben in ("tt", "cay"):
    !cp /content/doi0_moi/doi0.pt /content/{_ben}_gen0.pt && cp /content/doi0_moi/doi0.pb.gz /content/{_ben}_gen0.pb.gz
for _ben in ("tt", "cay"):
    with open(f"/content/{_ben}_gen0.seed.txt", "w") as _f:
        _f.write(str(SEED) + chr(10))
!sha256sum /content/tt_gen0.* /content/cay_gen0.*
# Menu cv đọc các dòng FZ_TAI_VE= trong log, tải các tệp đó về điện thoại khi ô xong.
for _ben in ("tt", "cay"):
    for _duoi in ("pb.gz", "pt", "seed.txt"):
        print(f"FZ_TAI_VE=/content/{_ben}_gen0.{_duoi}")
