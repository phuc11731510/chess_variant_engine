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
  python ~/fz_han_muc.py --may T4 --giay-t4   # chỉ in số GIÂY T4 còn chạy được (menu dùng cho ô 04)
  python ~/fz_han_muc.py --chup   # chỉ chụp (lưu) hạn mức nếu đọc được, không in gì; 0 = đã chụp
  python ~/fz_han_muc.py --dong   # KHÔNG hỏi mạng: một dòng tóm tắt từ lần chụp gần nhất (mục a)
  python ~/fz_han_muc.py --het    # ghi nhận: vừa xin T4 bị từ chối (hết hạn mức?) -- mục m

freeCcuQuotaInfo CHỈ có khi tài khoản đang giữ máy (đo 2026-09-26: không giữ máy -> ccu-info không
có trường đó, dù còn hạn mức). Nên mỗi lần đọc được, nó được CHỤP vào
~/.config/colab-cli/fz_han_muc.json (HOME của tài khoản -- menu đặt HOME riêng cho mỗi tài khoản),
và lúc không giữ máy thì in lần chụp gần nhất. Thời điểm nạp lại là giây epoch (UTC, mốc tuyệt đối,
không phụ thuộc múi giờ); in ra theo múi giờ của điện thoại, kèm nhãn múi giờ để thấy nếu đặt sai.
"""
import json
import os
import sys
import time
from urllib.parse import urljoin

CHUP = os.path.expanduser("~/.config/colab-cli/fz_han_muc.json")
T4_UOC_TINH = 1.07  # CCU/giờ của một máy T4, đo trên tài khoản này (colab usage) 2026-09-24
TRU_HAO = 15 * 60   # giây chừa lại cho ô 06 (gom zip) + tải về, trước khi hết hạn mức



def gio_phut(h):
    m = int(round(h * 60))
    return f"{m // 60} giờ {m % 60:02d} phút"


def luc(ts):
    """Giờ điện thoại của mốc epoch `ts`."""
    return time.strftime("%H:%M %d/%m", time.localtime(int(ts)))


def mui_gio():
    z = time.strftime("%z")                    # vd +0700
    return f"UTC{z[:3]}:{z[3:]}" if len(z) == 5 else (z or "?")


def doc_chup():
    try:
        with open(CHUP) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def ghi_chup(d):
    os.makedirs(os.path.dirname(CHUP), exist_ok=True)
    tam = CHUP + ".tam"
    with open(tam, "w") as f:
        json.dump(d, f)
    os.replace(tam, CHUP)


def tom_tat(ch, bay_gio=None):
    """Một dòng: hạn mức lúc chụp + giờ nạp lại (hoặc 'đã tới giờ nạp lại')."""
    if not ch:
        return "chưa chụp hạn mức (h / t / a khi đang giữ máy)"
    now = time.time() if bay_gio is None else bay_gio
    nap = ch.get("nap_lai")
    qua_nap = bool(nap) and now >= nap and ch.get("luc", 0) < nap
    if qua_nap:
        dau = "ĐÃ TỚI giờ nạp lại -- có lẽ đã có hạn mức mới"
    elif ch.get("het_luc") and ch["het_luc"] >= ch.get("luc", 0):
        dau = f"HẾT (xin T4 bị từ chối lúc {luc(ch['het_luc'])})"
    elif ch.get("con") is not None:
        ccu = ch["con"] / 1000
        dau = f"còn {ccu:.2f} đơn vị ≈ {gio_phut(ccu / T4_UOC_TINH)} T4 (lúc {luc(ch['luc'])})"
    else:
        dau = f"không rõ còn bao nhiêu (lúc {luc(ch['luc'])})"
    if nap and not qua_nap:
        con = nap - now
        dau += f" · nạp lại {luc(nap)}" + (f" (sau {gio_phut(con / 3600)})" if con > 0 else "")
    elif nap:
        dau += f" ({luc(nap)})"
    return dau


if "--dong" in sys.argv:        # không hỏi mạng
    print(tom_tat(doc_chup()))
    sys.exit(0)

# --giay-t4 / --chup: không in gì ra stdout thật (--giay-t4 in đúng một số ở cuối).
CHI_GIAY = "--giay-t4" in sys.argv
IM = CHI_GIAY or "--chup" in sys.argv
if IM:
    sys.stdout = open(os.devnull, "w")

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

if "--het" in sys.argv:         # mục m: xin T4 bị từ chối -> ghi nhận, giữ giờ nạp lại đã biết
    ch = doc_chup() or {"luc": 0}
    ch["het_luc"] = int(time.time())
    ghi_chup(ch)
    sys.exit(0)

co_han_muc = [(t, d) for t, d, _ in ket_qua if d is not None and d.get("freeCcuQuotaInfo")]
if not co_han_muc:
    ccu = next((d for t, d, _ in ket_qua if d is not None), None)
    if ccu is not None and not int(ccu.get("assignmentsCount") or 0):
        # Bình thường: máy chủ chỉ trả hạn mức khi đang giữ máy.
        print("Tài khoản không giữ máy nào -> máy chủ Colab không trả hạn mức (chỉ trả khi đang giữ máy).")
        print(f"Lần chụp gần nhất: {tom_tat(doc_chup())}")
        print(f"(giờ theo điện thoại, {mui_gio()})")
        if ccu.get("eligibleGpus") is not None:
            print(f"GPU được dùng: {', '.join(ccu.get('eligibleGpus') or []) or '(không)'}")
        sys.exit(3)
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
if may.upper() == "TAM":        # menu h -> d: máy CPU xin tạm chỉ để đọc hạn mức (trả ngay sau đó)
    may, so_may = "", max(0, so_may - 1)
    print("(đọc bằng một máy CPU tạm -- menu trả nó ngay sau đây)")
q = info["freeCcuQuotaInfo"]
tok = q.get("remainingTokens")
nap = q.get("nextRefillTimestampSec")
ghi_chup({"luc": int(time.time()), "con": None if tok is None else int(tok),
          "nap_lai": int(nap) if nap else None, "tieu": rate, "so_may": so_may})
if "--chup" in sys.argv:
    sys.exit(0)
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
if nap:
    con = int(nap) - time.time()
    print(f"Nạp lại lúc:   {luc(nap)} (giờ điện thoại, {mui_gio()})"
          + (f" -- sau {gio_phut(con / 3600)}" if con > 0 else ""))
if h is not None:
    print(f"Gợi ý SECS ô 04 (trên T4): {max(0, int(h * 3600) - TRU_HAO)}"
          f" (= thời gian GPU còn lại - {TRU_HAO // 60} phút để gom zip + tải về)")
if CHI_GIAY:
    if h is None:
        sys.exit(1)
    print(int(h * 3600), file=sys.__stdout__)
