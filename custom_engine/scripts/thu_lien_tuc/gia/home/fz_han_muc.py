"""fz_han_muc.py GIA: --giay-t4 in so giay T4 con lai (tep $FAKE_QUOTA_DIR/<tai khoan>, mac dinh 20000); lenh khac chi thoat 0."""
import os
import sys

a = sys.argv[1:]
if "--giay-t4" in a:
    acc = os.path.basename(os.environ["HOME"].rstrip("/"))
    try:
        print(int(open(os.path.join(os.environ.get("FAKE_QUOTA_DIR", "/tmp/fc/quota"), acc)).read().strip()))
    except (OSError, ValueError):
        print(20000)
elif "--dong" in a or "--khoi" in a:
    print("han muc gia")
sys.exit(0)
