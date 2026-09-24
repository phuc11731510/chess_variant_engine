"""fz_han_muc.py -- hạn mức GPU miễn phí còn lại của tài khoản Colab (chạy trên ĐIỆN THOẠI).

`colab usage` chỉ in số dư đơn vị tính toán mua được (tài khoản miễn phí: 0). Hạn mức miễn phí nằm
ở một API khác: GET https://colab.pa.googleapis.com/v1/user-info?get_ccu_consumption_info=true --
đúng API mà tiện ích Colab cho VS Code của Google gọi (googlecolab/colab-vscode,
src/colab/client/v1). Trường freeCcuQuotaInfo trong đó:
  remainingTokens         hạn mức miễn phí còn lại, đơn vị milli-CCU (1000 = 1 đơn vị tính toán)
  nextRefillTimestampSec  lúc hạn mức được nạp lại (giây, epoch)
consumptionRateHourly: tốc độ tiêu (CCU/giờ) của các máy đang giữ -- T4 khoảng 1,07.
Thời gian còn lại ~= remainingTokens / 1000 / consumptionRateHourly.

Dùng thông tin đăng nhập sẵn có của Colab CLI (~/.config/colab-cli/token.json).
  python ~/fz_han_muc.py          # in tóm tắt
  python ~/fz_han_muc.py --raw    # in nguyên JSON trả về (để kiểm)
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
api = getattr(c, "colab_api_domain", None) or "https://colab.pa.googleapis.com"
try:
    info = c._issue_request(urljoin(api, "v1/user-info"),
                            params={"get_ccu_consumption_info": "true"}, schema=dict)
except Exception as e:  # noqa: BLE001 -- in lỗi gốc cho người dùng
    sys.exit(f"[!] Không đọc được hạn mức: {e}")

if "--raw" in sys.argv:
    print(json.dumps(info, indent=2, ensure_ascii=False))
    sys.exit(0)


def gio_phut(h):
    m = int(round(h * 60))
    return f"{m // 60} giờ {m % 60:02d} phút"


rate = float(info.get("consumptionRateHourly") or 0)
print(f"Gói: {info.get('subscriptionTier', '?')} · đơn vị tính toán mua: "
      f"{float(info.get('paidComputeUnitsBalance') or 0):.2f} · đang tiêu: {rate:.2f}/giờ")

q = info.get("freeCcuQuotaInfo") or {}
tok = q.get("remainingTokens")
if tok is None:
    print("Không có trường hạn mức miễn phí (tài khoản có đơn vị mua, hoặc API không trả về).")
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
