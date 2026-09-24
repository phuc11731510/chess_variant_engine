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
  python ~/fz_han_muc.py [--may T4|CPU]   # in tóm tắt (--may: loại máy đang giữ, menu tự truyền)
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
so_may = int(info.get("assignmentsCount") or 0)
# Loai may cua phien (menu truyen vao tu `colab status`: T4 / CPU / ...); rong = khong biet.
may = sys.argv[sys.argv.index("--may") + 1] if "--may" in sys.argv[:-1] else ""
q = info["freeCcuQuotaInfo"]
tok = q.get("remainingTokens")
print("== Hạn mức Colab của tài khoản ==")
# Một hạn mức chung cho cả tài khoản (đơn vị tính toán). Mọi máy đang giữ đều tiêu vào nó theo
# consumptionRateHourly: T4 ~1,07/giờ, CPU rất ít -- nên máy CPU chạy được rất lâu (trang web Colab
# hiện "tối đa X giờ" = hạn mức còn lại / mức tiêu hiện tại).
ten_may = may or "?"
if so_may == 0:
    print("Máy đang giữ:  không có")
else:
    print(f"Máy đang giữ:  {ten_may} ({so_may} máy) -- đang tiêu {rate:.3f} đơn vị/giờ")
h = None      # giờ T4 còn lại (cho gợi ý SECS)
if tok is None:
    print("Có freeCcuQuotaInfo nhưng không có remainingTokens (tài khoản còn đơn vị mua?).")
else:
    ccu = int(tok) / 1000
    print(f"Còn lại:       {ccu:.3f} đơn vị")
    if so_may and rate > 0:
        print(f"=> Máy {ten_may} đang giữ chạy được thêm ≈ {gio_phut(ccu / rate)} (theo mức tiêu hiện tại)")
    elif so_may:
        print(f"=> Máy {ten_may} đang tiêu 0 đơn vị/giờ -- không tính được thời gian (không trừ hạn mức)")
    la_t4 = so_may and rate > 0 and may.upper() not in ("", "CPU") and "T4" in may.upper()
    h = ccu / rate if la_t4 else ccu / T4_UOC_TINH
    if not la_t4:
        print(f"   Nếu dùng T4 (~{T4_UOC_TINH}/giờ): ≈ {gio_phut(h)}")
print(f"Đơn vị mua:    {float(info.get('currentBalance') or info.get('paidComputeUnitsBalance') or 0):.2f}")
if info.get("eligibleGpus") is not None:
    print(f"GPU được dùng: {', '.join(info.get('eligibleGpus') or []) or '(không)'}"
          f" · không được: {', '.join(info.get('ineligibleGpus') or []) or '(không)'}")
nap = q.get("nextRefillTimestampSec")
if nap:
    con = int(nap) - time.time()
    print(f"Nạp lại lúc:   {time.strftime('%H:%M %d/%m', time.localtime(int(nap)))}"
          + (f" (sau {gio_phut(con / 3600)})" if con > 0 else ""))
if h is not None:
    print(f"Gợi ý SECS ô 04 (trên T4): {max(0, int(h * 3600) - 20 * 60)}"
          f" (= thời gian GPU còn lại - 20 phút để gom zip + tải về)")
