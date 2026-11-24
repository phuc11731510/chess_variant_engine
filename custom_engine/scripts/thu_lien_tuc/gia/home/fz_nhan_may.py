"""fz_nhan_may.py GIA: con <ten> = 0 neu may con (co /content/.maychu va khong co /content/.mat), 1 neu mat; cac lenh khac thoat 0."""
import os
import sys

a = sys.argv[1:]
if a[:1] == ["con"]:
    sys.exit(0 if os.path.exists("/content/.maychu") and not os.path.exists("/content/.mat") else 1)
sys.exit(0)
