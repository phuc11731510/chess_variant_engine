"""lay_mang.py GIA: lay_mang.py <fzw|onnx> <duong dan> --rel <url>. Mang doi N co khi: doi N <= FAKE_GEN0 (mang co san luc dau) hoac
$FAKE_RELEASE/gen<N>.pt da len "Release". Khong co -> thoat 10 (nhu ban that: Release khong co .pt cua doi do)."""
import os
import re
import sys

a = sys.argv[1:]
path = a[1]
m = re.search(r"gen(\d+)\.", os.path.basename(path))
n = int(m.group(1))
rel = os.path.join(os.environ.get("FAKE_RELEASE", "/tmp/fc/release"), f"gen{n}.pt")
if not (n <= int(os.environ.get("FAKE_GEN0", "0")) or os.path.exists(rel)):
    print(f"[lay_mang] Release khong co gen{n}.pt", file=sys.stderr)
    sys.exit(10)
os.makedirs(os.path.dirname(path), exist_ok=True)
open(path, "wb").write(os.urandom(64))
base = path.rsplit(".", 1)[0]
if not os.path.exists(base + ".pt"):
    open(base + ".pt", "wb").write(os.urandom(64))
print(f"[lay_mang] gen{n} -> {path}")
