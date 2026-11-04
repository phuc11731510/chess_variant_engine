# Dừng MỀM ô 04 hoặc 08 (chơi nốt ván đang dở)
# cv: nhanh
# Chép theo ô 09b của fz: ô 04 đang sinh dữ liệu thôi nhận ván mới; các ván đang chơi chơi nốt rồi ô 04 kết thúc như
# hết SECS -> chuỗi "04 06" chạy tiếp 06 (gom zip, tải về) như bình thường. Khác ô 09: 09 dừng NGAY, mất lần sinh dở.
import subprocess

ps = subprocess.run("pgrep -af '[s]inh\\.py |[a]rena\\.py '", shell=True, capture_output=True, text=True).stdout
if not ps.strip():
    print("(không có ô 04 / 08 nào đang chạy trên máy này)")
elif "--tep-dung" not in ps:
    print("[!] Tiến trình đang chạy KHÔNG có --tep-dung (ô bản cũ) -> không dừng mềm được. Dừng ngay: ô 09.")
else:
    tep = ps.split("--tep-dung", 1)[1].split()[0]   # đúng tệp mà tiến trình đang xem
    open(tep, "w").close()
    print(f"[đã yêu cầu dừng mềm] ({tep}) không nhận ván mới; ván đang chơi chơi nốt rồi ô kết thúc.")
    print("Xem: l (log trực tiếp)")
