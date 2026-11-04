"""fz_trung_tk.py -- dò các tài khoản Colab của menu fz bị TRÙNG tệp token (chạy trên ĐIỆN THOẠI).

    python ~/fz_trung_tk.py <ten>|<HOME> ...      (menu a -> d tự truyền mọi tài khoản)

Mỗi tài khoản = một tệp <HOME>/.config/colab-cli/token.json. Hai tên có cùng refresh_token = cùng
MỘT tệp đăng nhập bị chép sang hai tên (vd chép nhầm tệp lúc chuyển giữa các điện thoại). Chỉ so các
tệp trên điện thoại với nhau: không hỏi mạng, không ghi gì, không in token.
"""
import json
import os
import sys


def doc_token(home):
    try:
        with open(os.path.join(home, ".config/colab-cli/token.json")) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    nhom, co = {}, 0
    for muc in a:
        ten, home = (muc.split("|", 1) + [""])[:2]
        tk = doc_token(home)
        if tk is None:
            print(f"  {ten}: chưa đăng nhập (không có token.json) -- bỏ qua")
            continue
        co += 1
        nhom.setdefault(tk.get("refresh_token"), []).append(ten)
    print(f"[dò trùng] {co} tài khoản có token")
    trung = [v for v in nhom.values() if len(v) > 1]
    for v in trung:
        print(f"[TRÙNG] {', '.join(v)}: cùng MỘT tệp token")
    if not trung:
        print("[dò trùng] không có tài khoản nào trùng")
    else:
        print()
        print("Sửa: giữ MỘT tên; tên còn lại xoá (a -> x) rồi thêm lại bằng tệp token ĐÚNG của")
        print("tài khoản kia (chép từ điện thoại khác) hoặc đăng nhập lại (a -> n).")
    print(f"FZ_TRUNG {len(trung)}")


if __name__ == "__main__":
    main()
