"""fz_colab.py -- Colab CLI "an toan" cho menu fz (chay tren DIEN THOAI).

Chay nhu `colab` (cung doi so), nhung sua hai loi cua Colab CLI 0.7.x ma menu va vong lap v gap:

1. LAM MOI TOKEN BAO LOI "invalid_scope" (2026-10-26, do tren hai tai khoan bi doi dang nhap lai):
   token.json ghi 6 scope CLI da xin, nhung mot so tai khoan chi duoc Google cap 3 scope (openid, email,
   profile -- khong co cloud-platform / colaboratory / drive.file). Khi access token het han (moi gio),
   CLI xin lam moi KEM danh sach 6 scope -> Google tra 400 invalid_scope -> CLI coi la token hong va doi
   dang nhap lai, du refresh_token van con hieu luc. Lam moi KHONG gui scope thi Google tra access token
   dung voi nhung gi da cap, va API Colab (tun/m/...) chap nhan token do (do 2026-10-26: HTTP 200).
   Tep nay doi cach CLI nap token: bo danh sach scope khi lam moi.
2. CLI HOI MA DANG NHAP (input()) NGAY TRONG LENH CHAY NEN -> cua so "dung hinh": dau ra cua lenh bi menu
   bat (out=$(colab new ...)) nen khong thay loi nhac, ma lenh cho ban go ma. Voi FZ_KHONG_HOI=1 (vong
   lap v, cac lenh chay nen) CLI KHONG hoi: in "FZ_CAN_DANG_NHAP" ra stderr va thoat ma 75.

  python ~/fz_colab.py <lenh colab ...>   # nhu `colab <lenh ...>`
  python ~/fz_colab.py --token            # kiem tra / lam moi token.json (luu nguyen tu), in FZ_TOKEN=...
      0 = ok (con han hoac da lam moi), 2 = phai dang nhap lai (khong co tep / refresh_token bi tu choi),
      3 = loi mang (thu lai sau, KHONG can dang nhap lai)
Tep: <HOME>/.config/colab-cli/token.json, token.json.bak (ban tot gan nhat, dung khi token.json bi hong).
HOME la cua tai khoan (menu dat HOME rieng cho moi tai khoan).
"""
import datetime
import json
import os
import shutil
import sys
import time

MA_CAN_DANG_NHAP = 75
CON_LAI_TOI_THIEU = 600    # token con it hon nhieu giay -> lam moi truoc (de lenh sau khoi tu lam moi)


def va(khong_hoi):
    """Vao Colab CLI (trong tien trinh nay): bo scope khi lam moi token; khong_hoi -> khong bao gio hoi ma."""
    from colab_cli import auth
    goc = auth.Credentials.from_authorized_user_file

    def tu_tep(path, scopes=None):
        c = goc(path, None)
        c._scopes = None          # lam moi khong gui scope (xem dau tep)
        return c

    auth.Credentials.from_authorized_user_file = staticmethod(tu_tep)
    if khong_hoi:
        def khong_hoi_(*_a, **_k):
            sys.stderr.write("FZ_CAN_DANG_NHAP\n")
            raise SystemExit(MA_CAN_DANG_NHAP)
        auth._run_remote_flow = khong_hoi_


def _nap(path):
    from google.oauth2.credentials import Credentials
    c = Credentials.from_authorized_user_file(path, None)
    c._scopes = None
    return c


def _ghi_nguyen_tu(path, noi_dung):
    tam = f"{path}.{os.getpid()}.tmp"
    with open(tam, "w") as f:
        f.write(noi_dung)
    os.chmod(tam, 0o600)
    os.replace(tam, path)


def kiem_token():
    from colab_cli import auth
    from google.auth import exceptions as ge
    from google.auth.transport.requests import Request
    va(True)
    p = auth.TOKEN_CONFIG_PATH
    bak = p + ".bak"
    try:
        import fcntl
        khoa = open(p + ".lock", "w")
        fcntl.flock(khoa, fcntl.LOCK_EX)      # hai tien trinh khong cung lam moi / ghi token.json
    except (ImportError, OSError):
        khoa = None
    creds = None
    for nguon in (p, bak):
        try:
            creds = _nap(nguon)
        except Exception:
            continue
        if nguon == bak:
            print("[fz] token.json hong -> khoi phuc tu token.json.bak")
            _ghi_nguyen_tu(p, creds.to_json())
        break
    if creds is None or not creds.refresh_token:
        print("FZ_TOKEN=thieu")
        return 2
    # creds.expiry la gio UTC khong mui gio; so voi UTC hien tai cung kieu.
    bay_gio = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    con_lai = (creds.expiry - bay_gio).total_seconds() if creds.expiry else 0
    if creds.valid and con_lai > CON_LAI_TOI_THIEU:
        if not os.path.exists(bak):
            shutil.copyfile(p, bak)
        print("FZ_TOKEN=ok")
        return 0

    class Yeu(Request):
        def __call__(self, *a, **k):
            k.setdefault("timeout", 20)
            return super().__call__(*a, **k)

    for lan in range(1, 4):
        try:
            creds.refresh(Yeu())
            break
        except ge.TransportError:
            if lan == 3:
                print("FZ_TOKEN=mang")
                return 3
            time.sleep(2 * lan)
        except ge.RefreshError as e:
            print(f"FZ_TOKEN=hong ({str(e)[:80]})")
            return 2
    # to_json() cua credentials khong co scope (da bo) -- CLI doc duoc.
    _ghi_nguyen_tu(p, creds.to_json())
    shutil.copyfile(p, bak)
    print("FZ_TOKEN=ok (da lam moi)")
    return 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--token":
        return kiem_token()
    va(bool(os.environ.get("FZ_KHONG_HOI")))
    from colab_cli.cli import main as cli
    sys.argv[0] = "colab"
    return cli()


if __name__ == "__main__":
    sys.exit(main())
