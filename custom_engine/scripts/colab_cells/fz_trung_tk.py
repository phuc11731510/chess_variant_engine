"""fz_trung_tk.py -- dò các tài khoản Colab của menu fz bị TRÙNG (chạy trên ĐIỆN THOẠI).

    python ~/fz_trung_tk.py <ten>|<HOME> ...      (menu a -> d tự truyền mọi tài khoản)
    python ~/fz_trung_tk.py --khong-mang <ten>|<HOME> ...   (chỉ so tệp, không hỏi Google)

Mỗi tài khoản = một tệp <HOME>/.config/colab-cli/token.json. Hai mức trùng:
  1. CHÉP TRÙNG: hai tài khoản cùng refresh_token -- cùng MỘT tệp đăng nhập bị chép sang hai tên
     (vd chép nhầm tệp lúc chuyển giữa các điện thoại).
  2. CÙNG TÀI KHOẢN GOOGLE: token khác nhau nhưng cùng email (đăng nhập cùng một Google hai lần).
     Email lấy bằng chính token đó: đổi refresh_token lấy access token (token_uri của tệp) rồi hỏi
     openidconnect.googleapis.com/v1/userinfo (token có quyền userinfo.email). Chỉ ĐỌC: không ghi
     gì vào tệp token, không đổi đăng nhập nào.
Không in token. Email in ra để biết tên nào là tài khoản Google nào (chỉ hiện trên điện thoại).
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def doc_token(home):
    try:
        with open(os.path.join(home, ".config/colab-cli/token.json")) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def email_cua(tk):
    """Email Google của token (None + lý do nếu không hỏi được)."""
    try:
        body = urllib.parse.urlencode({
            "client_id": tk["client_id"], "client_secret": tk["client_secret"],
            "refresh_token": tk["refresh_token"], "grant_type": "refresh_token"}).encode()
        uri = tk.get("token_uri") or "https://oauth2.googleapis.com/token"
        with urllib.request.urlopen(urllib.request.Request(uri, data=body), timeout=20) as r:
            access = json.load(r)["access_token"]
        req = urllib.request.Request("https://openidconnect.googleapis.com/v1/userinfo",
                                     headers={"Authorization": f"Bearer {access}"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r).get("email"), None
    except urllib.error.HTTPError as e:
        return None, f"Google trả {e.code}" + (" (token hết hạn / bị thu hồi -> đăng nhập lại)"
                                               if e.code in (400, 401) else "")
    except (OSError, KeyError, ValueError) as e:
        return None, f"không hỏi được ({type(e).__name__})"


def main():
    a = sys.argv[1:]
    mang = True
    if a and a[0] == "--khong-mang":
        mang, a = False, a[1:]
    if not a:
        sys.exit(__doc__)
    ds = []
    for muc in a:
        ten, home = (muc.split("|", 1) + [""])[:2]
        tk = doc_token(home)
        if tk is None:
            print(f"  {ten}: chưa đăng nhập (không có token.json) -- bỏ qua")
            continue
        ds.append((ten, tk))
    print(f"[dò trùng] {len(ds)} tài khoản có token")

    # 1. Chép trùng: cùng refresh_token.
    nhom = {}
    for ten, tk in ds:
        nhom.setdefault(tk.get("refresh_token"), []).append(ten)
    chep = [v for v in nhom.values() if len(v) > 1]

    # 2. Cùng email (mỗi refresh_token hỏi một lần).
    email, loi = {}, {}
    if mang:
        for rt, tens in nhom.items():
            e, l = email_cua(next(tk for ten, tk in ds if tk.get("refresh_token") == rt))
            for t in tens:
                email[t], loi[t] = e, l
    theo_email = {}
    for ten, _ in ds:
        if email.get(ten):
            theo_email.setdefault(email[ten], []).append(ten)

    for ten, _ in ds:
        if mang:
            print(f"  {ten:<20} {email[ten] or '? ' + (loi[ten] or '')}")
        else:
            print(f"  {ten}")
    print()
    trung = 0
    for v in chep:
        trung += 1
        print(f"[CHÉP TRÙNG] {', '.join(v)}: cùng MỘT tệp token"
              + (f" ({email.get(v[0])})" if email.get(v[0]) else ""))
    chep_set = {frozenset(v) for v in chep}
    for e, v in theo_email.items():
        if len(v) > 1 and frozenset(v) not in chep_set:
            trung += 1
            print(f"[CÙNG GOOGLE] {', '.join(v)}: cùng tài khoản {e} (đăng nhập riêng nhiều lần)")
    if trung == 0:
        print("[dò trùng] không có tài khoản nào trùng" + ("" if mang else " (chỉ so tệp)"))
    else:
        print()
        print("Sửa: giữ MỘT tên cho mỗi tài khoản Google; tên còn lại xoá (a -> x) rồi thêm lại")
        print("bằng tệp token ĐÚNG của tài khoản kia (chép từ điện thoại khác) hoặc đăng nhập lại (a -> n).")
    hong = [t for t in loi if loi[t]]
    if hong:
        print(f"[!] Không biết email của: {', '.join(hong)} -- so được tệp, chưa so được tài khoản Google")
    print(f"FZ_TRUNG {trung}")


if __name__ == "__main__":
    main()
