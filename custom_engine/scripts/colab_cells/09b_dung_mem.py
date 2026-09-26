# Dừng MỀM ô 04 (chơi nốt ván đang dở)
# fz: nhanh
# Ô 04 đang sinh dữ liệu thôi nhận ván mới; các ván đang chơi chơi nốt (vài phút) rồi ô 04 kết thúc
# như hết SECS -> chuỗi "04 06" chạy tiếp 06 (gom zip, tải về) như bình thường.
# Khác ô 09: 09 dừng NGAY, mất các ván đang dở. Cần ô 04 chạy bằng binary có --stop-file (từ 2026-09-26).
import subprocess

ps = subprocess.run("pgrep -af '[c]ustom_engine.* --selfplay'", shell=True,
                    capture_output=True, text=True).stdout
if not ps.strip():
    print("(không có ô 04 nào đang sinh dữ liệu trên máy này)")
elif "--stop-file" not in ps:
    print("[!] Ô 04 đang chạy KHÔNG có --stop-file (binary hoặc ô 04 bản cũ) -> không dừng mềm được.")
    print("    Dừng ngay: ô 09 (mất các ván đang dở).")
else:
    tep = ps.split("--stop-file", 1)[1].split()[0]   # đúng tệp mà engine đang xem
    open(tep, "w").close()
    print(f"[đã yêu cầu dừng mềm] ({tep}) ô 04 không nhận ván mới; ván đang chơi chơi nốt rồi ô 04 kết thúc.")
    print("Xem: l (log trực tiếp)")
