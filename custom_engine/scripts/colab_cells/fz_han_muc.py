"""fz_han_muc.py -- hạn mức GPU miễn phí còn lại của tài khoản Colab (chạy trên ĐIỆN THOẠI).

Hạn mức miễn phí là trường freeCcuQuotaInfo (theo tiện ích Colab cho VS Code của Google,
googlecolab/colab-vscode, src/colab/client/v1/api.ts):
  remainingTokens         hạn mức miễn phí còn lại, đơn vị milli-CCU (1000 = 1 đơn vị tính toán)
  nextRefillTimestampSec  lúc hạn mức được nạp lại (giây, epoch)
consumptionRateHourly: tốc độ tiêu (CCU/giờ) của các máy đang giữ -- T4 khoảng 1,07.
Thời gian còn lại ~= remainingTokens / 1000 / consumptionRateHourly.

Hỏi hai nơi, bằng thông tin đăng nhập sẵn có của Colab CLI (~/.config/colab-cli/token.json):
  1. GET colab.research.google.com/tun/m/ccu-info -- nơi `colab usage` hỏi (được phép); Colab CLI
     chỉ đọc 3 trường rồi bỏ phần còn lại, ở đây đọc NGUYÊN câu trả lời.
  2. GET colab.pa.googleapis.com/v1/user-info?get_ccu_consumption_info=true -- nơi tiện ích VS Code
     hỏi; có thể trả 403 vì token Colab CLI cấp cho ứng dụng đăng nhập khác (của gcloud).
  python ~/fz_han_muc.py          # in tóm tắt
  python ~/fz_han_muc.py --raw    # in nguyên câu trả lời của cả hai nơi (để kiểm)
"""
import json
import sys
import time
from urllib.parse import urljoin

T4_UOC_TINH = 1.07  # CCU/giờ của một máy T4, đo trên tài khoản này (colab usage) 2026-09-24

try:
    from colab_cli.common import state
except ImportError:
    sys.exit("[!] Không tìm thấy Colab CLI (colab_cli) trong Python này.")

c = state.client
web = getattr(c, "colab_domain", None) or "https://colab.research.google.com"
api = getattr(c, "colab_api_domain", None) or "https://colab.pa.googleapis.com"
NOI = [
    ("tun/m/ccu-info", urljoin(web, "/tun/m/ccu-info"), None),
    ("v1/user-info", urljoin(api, "v1/user-info"), {"get_ccu_consumption_info": "true"}),
]


def hoi(url, params):
    """(dữ liệu, None) hoặc (None, lỗi kèm nội dung máy chủ trả về)."""
    try:
        return c._issue_request(url, params=params, schema=dict), None
    except Exception as e:  # noqa: BLE001 -- in lỗi gốc cho người dùng
        than = getattr(e, "response_body", "") or ""
        return None, f"{e}" + (f"\n      máy chủ trả: {than[:300]}" if than else "")


ket_qua = []
for ten, url, params in NOI:
    d, loi = hoi(url, params)
    ket_qua.append((ten, d, loi))
    if "--raw" in sys.argv:
        print(f"===== {ten}")
        print(json.dumps(d, indent=2, ensure_ascii=False) if d is not None else f"[lỗi] {loi}")
    elif d is not None and d.get("freeCcuQuotaInfo"):
        break  # đã có hạn mức, khỏi hỏi nơi sau
if "--raw" in sys.argv:
    sys.exit(0)


def gio_phut(h):
    m = int(round(h * 60))
    return f"{m // 60} giờ {m % 60:02d} phút"


co_han_muc = [(t, d) for t, d, _ in ket_qua if d is not None and d.get("freeCcuQuotaInfo")]
if not co_han_muc:
    print("Không nơi nào trả về hạn mức miễn phí (freeCcuQuotaInfo):")
    for ten, d, loi in ket_qua:
        print(f"  {ten}: " + (f"trả về các trường {sorted(d)}" if d is not None else f"lỗi -- {loi}"))
    print("Xem nguyên câu trả lời: python ~/fz_han_muc.py --raw")
    sys.exit(1)

ten, info = co_han_muc[0]
rate = float(info.get("consumptionRateHourly") or 0)
q = info["freeCcuQuotaInfo"]
tok = q.get("remainingTokens")
print(f"(nguồn: {ten}) đang tiêu: {rate:.2f} đơn vị/giờ")
if tok is None:
    print("Có freeCcuQuotaInfo nhưng không có remainingTokens (tài khoản còn đơn vị mua?).")
else:
    ccu = int(tok) / 1000
    print(f"Hạn mức miễn phí còn: {ccu:.2f} đơn vị tính toán")
    if rate > 0:
        h = ccu / rate
        print(f"=> Với mức tiêu hiện tại: còn khoảng {gio_phut(h)}")
    else:
        h = ccu / T4_UOC_TINH
        print(f"=> Chưa giữ máy nào; nếu xin T4 (~{T4_UOC_TINH}/giờ): khoảng {gio_phut(h)}")
    goi_y = max(0, int(h * 3600) - 20 * 60)
    print(f"   Gợi ý SECS cho ô 04 (trừ 20 phút để gom zip + tải về): {goi_y}")
nap = q.get("nextRefillTimestampSec")
if nap:
    print(f"Nạp lại hạn mức lúc: {time.strftime('%H:%M %d/%m', time.localtime(int(nap)))}")
