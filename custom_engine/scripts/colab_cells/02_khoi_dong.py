# Khởi động: mã, binary, ONNX Runtime, mạng (mục 1)
# Mục 1 của sổ tay: tải mã nguồn, binary dựng sẵn từ Release + ONNX Runtime, sinh run.sh.
# Phải thấy "[quick] OK". Báo lỗi -> chạy ô 02b (biên dịch lại).
#
# TIẾT KIỆM TẢI XUỐNG (2026-11-21, chủ dự án chọn): máy Colab sống nhiều đời liền, nên
#   - thư mục repo KHÔNG bị xoá mỗi đời nữa: lần đầu clone THƯA chỉ custom_engine (~1 MB thay vì ~22 MB của cả repo, phần lớn
#     là thư mục nghiên cứu), các lần sau chỉ `git fetch` + `reset` (vài trăm KB). ONNX Runtime (79 MB) và binary (3,6 MB) nằm
#     trong thư mục đó nên cũng CÒN NGUYÊN: colab_quickstart.sh chỉ tải lại binary khi Release đổi (kích thước / ETag khác).
#   - Máy MỚI thuê vẫn tải đủ một lần.
%cd /content
# git bị giới hạn 2 phút mỗi lần, tối đa 3 lần (trước đây mạng chập chờn thì treo im lặng, không log).
import os, subprocess, time
_URL = "https://github.com/phuc11731510/chess_variant_engine.git"
for lan in (1, 2, 3):
    r = None
    if os.path.isdir("chess_variant_engine/.git"):
        # Cập nhật tại chỗ: giữ third_party/ (ONNX Runtime), build-linux/ (binary), run.sh (không nằm trong git).
        r = subprocess.run("cd chess_variant_engine && timeout 120 git fetch -q --depth 1 origin main "
                           "&& git reset -q --hard FETCH_HEAD", shell=True)
        if r.returncode != 0:
            print(f"[02] git fetch lan {lan} that bai -- dung lai thu muc ma (giu third_party va build-linux)", flush=True)
            subprocess.run("rm -rf /content/.fz_giu && mkdir -p /content/.fz_giu && cd chess_variant_engine/custom_engine "
                           "&& for d in third_party build-linux; do [ -e $d ] && mv $d /content/.fz_giu/; done; "
                           "cd /content && rm -rf chess_variant_engine", shell=True)
    if not os.path.isdir("chess_variant_engine/.git"):
        # Clone thưa: chỉ custom_engine (GitHub hỗ trợ --filter); lỗi thì clone nông thường như trước đây.
        r = subprocess.run(f"timeout 120 git clone -q --depth 1 --filter=blob:none --sparse -b main {_URL} chess_variant_engine "
                           "&& cd chess_variant_engine && git sparse-checkout set custom_engine", shell=True)
        if r.returncode != 0 or not os.path.isfile("chess_variant_engine/custom_engine/meson.build"):
            print(f"[02] clone thua lan {lan} that bai -- thu clone thuong", flush=True)
            r = subprocess.run(f"rm -rf chess_variant_engine; timeout 120 git clone -q --depth 1 -b main {_URL}", shell=True)
        # Trả lại third_party / build-linux cất lúc nãy (nếu có)
        subprocess.run("[ -d /content/.fz_giu ] && for d in third_party build-linux; do [ -e /content/.fz_giu/$d ] && "
                       "mv /content/.fz_giu/$d chess_variant_engine/custom_engine/; done; rm -rf /content/.fz_giu", shell=True)
    if r is not None and r.returncode == 0:
        break
    print(f"[02] git lan {lan} that bai hoac treo -- thu lai", flush=True)
    time.sleep(5)
# ONNX Runtime (79 MB) CHỈ tải khi máy cần nó (NET_KIND = "onnx", hoặc "auto" mà bộ chạy CUDA riêng hỏng: xem dưới).
SKIP_ORT = 0 if NET_KIND == "onnx" else 1
!SKIP_ORT={SKIP_ORT} BIN_URL={REL}/custom_engine bash {E}/scripts/colab_quickstart.sh

# ---- Mạng đời hiện tại và KIỂU MẠNG của máy này (xem NET_KIND ở ô 00) ----------------------------------------------------
# Release NN_Model (REL_NN) chỉ giữ .pt, nên python/lay_mang.py tải gen<N>.pt rồi chuyển ngay trên máy:
#   .fzw  (--provider fzcuda): chỉ cần torch + numpy (Colab có sẵn), ~10-20 giây, KIỂM an toàn trước khi ghi (mô hình CPU của
#         bộ chạy phải ra gần như số FP32 của mạng; lệch / NaN thì không ghi tệp).
#   .onnx (--provider cuda):   cần pip onnx, onnxscript, onnxruntime-gpu (tự pip install nếu thiếu, ~250 MB) + ONNX Runtime 79 MB.
# "fzw" / "auto": chuyển .fzw rồi CHẠY THỬ thật một ván hai nước bằng bộ chạy CUDA (nạp libcublasLt, GPU, trọng số, một lượt chạy
# mạng). Chạy được -> kiểu "fzw". Không chạy được: "auto" rơi về "onnx" (tải ONNX Runtime + chuyển .onnx), "fzw" dừng và báo lý do.
# Kiểu thật được GHI vào NET_FILE (/content/fz_log/net_kind) và in ra dòng FZ_NET=...; ô 00 đọc lại để mọi ô dùng cùng kiểu.
# Đặt TAI_MANG = False nếu bạn tự tải mạng lên từ điện thoại (colab upload) hoặc tự tạo (ô 03, đời 0): ô này không đụng tới mạng.
# .pt + thư viện huấn luyện: ô 02c (chỉ máy huấn luyện).
TAI_MANG = True


def _lay_mang(ext):
    """python/lay_mang.py <ext>: gen<GEN_CURRENT>.<ext> có trên máy (không để lại tệp rỗng / dở khi lỗi; thử lại 4 lần với HTTP 429/5xx)."""
    f = f"/content/gen{GEN_CURRENT}.{ext}"
    sub = subprocess.run(f"python3 {E}/python/lay_mang.py {ext} {f} --rel {REL_NN}" + (" --fp16" if ext == "onnx" else ""), shell=True)
    return sub.returncode == 0 and os.path.exists(f) and os.path.getsize(f) > 0


def _thu_fzcuda(fzw):
    """Chạy THẬT bộ chạy CUDA riêng: một ván hai nước --provider fzcuda trên mạng fzw (như ô 04, chỉ nhỏ hơn). In lỗi của engine nếu hỏng."""
    cmd = (f"rm -rf /content/fz_thu && bash {E}/run.sh --selfplay --games 1 --max-moves 2 --visits 16 --fast-visits 8 --parallel 2 "
           f"--provider fzcuda --fixed-batch 16 --fz-opt contexts=1 --fz-opt autotune=0 --fz-opt graph=0 --weights {fzw} --out /content/fz_thu")
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        print("[02] chạy thử bộ chạy CUDA quá 300 giây (treo?)", flush=True)
        return False
    if r.returncode != 0:
        print(f"[02] chạy thử bộ chạy CUDA lỗi (mã {r.returncode}):\n" + "\n".join((r.stdout + r.stderr).strip().splitlines()[-12:]), flush=True)
    subprocess.run("rm -rf /content/fz_thu", shell=True)
    return r.returncode == 0


if TAI_MANG:
    os.makedirs(os.path.dirname(NET_FILE), exist_ok=True)
    try:
        _truoc = open(NET_FILE).read().strip()      # kết luận của lần chạy 02 trước trên CHÍNH máy này (máy mới thuê: không có)
    except OSError:
        _truoc = ""
    kind = None
    if NET_KIND == "auto" and _truoc in ("fzw", "onnx"):
        # Máy này đã được thử rồi (mỗi đời mới máy chạy lại 02 để lấy mạng mới): giữ kết luận, không chạy thử lại mỗi đời.
        kind = _truoc
        if not _lay_mang(kind):
            raise SystemExit(f"[!] Khong lay duoc gen{GEN_CURRENT}.{kind} tu Release NN_Model")
    else:
        if NET_KIND in ("fzw", "auto"):
            if _lay_mang("fzw") and _thu_fzcuda(f"/content/gen{GEN_CURRENT}.fzw"):
                kind = "fzw"
            elif NET_KIND == "fzw":
                raise SystemExit("[!] NET_KIND = \"fzw\" nhưng không có / không chạy được mạng .fzw trên máy này (lý do ở trên) -- "
                                 "đổi NET_KIND ở ô 00 thành \"auto\" hoặc \"onnx\" để dùng ONNX Runtime")
            else:
                print("[02] bộ chạy CUDA riêng KHÔNG chạy được trên máy này (lý do ở trên) -> rơi về ONNX Runtime", flush=True)
        if kind is None:
            !bash {E}/scripts/colab_quickstart.sh
            if not _lay_mang("onnx"):
                raise SystemExit(f"[!] Khong lay duoc gen{GEN_CURRENT}.onnx tu Release NN_Model")
            kind = "onnx"
        with open(NET_FILE, "w") as _f:
            _f.write(kind)
    print(f"FZ_NET={kind}")
else:
    print("(TAI_MANG = False: ô này không tải / chuyển mạng và không ghi kiểu mạng)")
!ls -la /content/gen*.fzw /content/gen*.onnx /content/gen*.pt 2>/dev/null
