#!/usr/bin/env bash
# =============================================================================
# FairyZero — khoi dong Colab KHONG bien dich.
#
# colab_setup.sh mat 8-12 phut vi phai bien dich ~278 don vi. Nhung binary Linux
# hau nhu khong doi giua cac phien. Script nay:
#   1. tai ONNX Runtime GPU (neu chua co)  -- nhanh, vai chuc giay
#   2. nhan mot binary DUNG SAN (tu GitHub Release, hoac da co san trong cay)
#   3. sinh run.sh dat LD_LIBRARY_PATH roi exec engine
#   4. tu kiem tra
#
# Vi sao van can run.sh: moi cell Colab la mot shell moi, nen `export` o cell
# truoc KHONG song sot. Binary can libonnxruntime*.so va cac thu vien CUDA nam
# trong cac goi pip nvidia-* cua torch.
#
# Dung:
#   bash colab_quickstart.sh                       # binary da co trong build-linux/
#   BIN_URL=https://.../custom_engine bash colab_quickstart.sh
#
# Bien moi truong:
#   BIN_URL  URL tai binary (bo qua neu build-linux/custom_engine da co)
#   ORT_VER  phien ban ONNX Runtime (mac dinh 1.20.1 -- PHAI khop luc build)
#   SKIP_ORT=1  khong tai ONNX Runtime (may chay bo chay CUDA rieng, --provider fzcuda); binary cu can no thi tu tai o cuoi
# =============================================================================
set -e

ORT_VER="${ORT_VER:-1.20.1}"
ORT_PKG="${ORT_PKG:-onnxruntime-linux-x64-gpu-${ORT_VER}}"
ORT_URL="${ORT_URL:-https://github.com/microsoft/onnxruntime/releases/download/v${ORT_VER}/${ORT_PKG}.tgz}"
# Goi gon (chi 3 thu vien can, xz) tren Release cua repo -- chi co cho ban 1.20.1. ORT_GON_URL= (rong)
# de tat, luon tai goi chinh thuc.
if [ "$ORT_VER" = 1.20.1 ]; then
  ORT_GON_URL="${ORT_GON_URL-https://github.com/phuc11731510/chess_variant_engine/releases/download/v3.0.0/${ORT_PKG}-gon.tar.xz}"
  ORT_GON_SHA="${ORT_GON_SHA-d5005438ce9a12fffe8d72228bb508263e67939479a68b27314703058a66f34a}"
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENGINE_DIR="$(dirname "$SCRIPT_DIR")"
[ -f "$ENGINE_DIR/meson.build" ] || { echo "[quick] FATAL: khong thay meson.build o $ENGINE_DIR" >&2; exit 1; }
cd "$ENGINE_DIR"

BIN="$ENGINE_DIR/build-linux/custom_engine"

# --- 1. binary ---------------------------------------------------------------
# Tai binary CHI KHI CAN (2026-11-21, tiet kiem tai xuong): chua co, hoac Release da doi (kich thuoc / ETag cua
# tep tren Release khac dau da luu canh binary). Khong hoi duoc Release (mang loi) ma da co binary thi dung binary dang co.
if [ -n "${BIN_URL:-}" ]; then
  mkdir -p "$ENGINE_DIR/build-linux"
  remote=$(curl -sIL --max-time 30 "$BIN_URL" 2>/dev/null | tr -d '\r' |
           awk 'tolower($1)=="content-length:"{l=$2} tolower($1)=="etag:"{e=$2} END{print l, e}' || true)
  remote="${remote## }"
  if [ -f "$BIN" ] && { [ -z "${remote// }" ] || [ "$remote" = "$(cat "$BIN.id" 2>/dev/null || true)" ]; }; then
    echo "[quick] binary da co, khop Release (${remote:-khong hoi duoc Release}): khong tai lai"
  else
    echo "[quick] tai binary: $BIN_URL"
    wget -q --timeout=30 --tries=4 --waitretry=15 --retry-on-http-error=429,500,502,503,504 "$BIN_URL" -O "$BIN.tmp" \
      && mv -f "$BIN.tmp" "$BIN" || { rm -f "$BIN.tmp"; echo "[quick] FATAL: tai binary that bai" >&2; exit 1; }
    [ -n "${remote// }" ] && echo "$remote" > "$BIN.id" || true
  fi
fi
[ -f "$BIN" ] || {
  echo "[quick] FATAL: khong co binary o $BIN" >&2
  echo "[quick] Dat BIN_URL=... , hoac chay colab_setup.sh mot lan de bien dich." >&2
  exit 1; }
chmod +x "$BIN"

# --- 2. ONNX Runtime ---------------------------------------------------------
# SKIP_ORT=1 (2026-11-22): may chi chay bo chay CUDA rieng cua engine (--provider fzcuda, o 02) khong can ONNX Runtime (79 MB).
# Binary tu Release v3.0.0 (dung -Donnxruntime_dlopen=true) khong lien ket libonnxruntime, nen chay duoc khi thieu no; neu
# binary la ban cu (can libonnxruntime ngay luc nap) thi buoc kiem tra o cuoi se tai ONNX Runtime roi kiem lai.
lay_ort() {
mkdir -p third_party && cd third_party
if [ ! -d "$ORT_PKG" ]; then
  # Uu tien goi GON tren Release cua repo (ORT_GON_URL): chi 3 thu vien engine can (libonnxruntime,
  # providers_shared, providers_cuda -- bo TensorRT, header, cmake), nen xz -9e: ~81 MB thay vi goi
  # chinh thuc 258 MB. Loi (chua co tren Release / sai sha256) thi tai goi chinh thuc nhu cu.
  ok=
  if [ -n "${ORT_GON_URL:-}" ]; then
    echo "[quick] tai $ORT_PKG (goi gon) ..."
    if wget -q --timeout=30 --tries=4 --waitretry=15 --retry-on-http-error=429,500,502,503,504 "$ORT_GON_URL" -O "${ORT_PKG}.tar.xz" &&
       { [ -z "${ORT_GON_SHA:-}" ] || echo "$ORT_GON_SHA  ${ORT_PKG}.tar.xz" | sha256sum -c --quiet; } &&
       tar xJf "${ORT_PKG}.tar.xz"; then ok=1
    else echo "[quick] goi gon loi -- tai goi chinh thuc"; rm -rf "$ORT_PKG"; fi
    rm -f "${ORT_PKG}.tar.xz"
  fi
  if [ -z "$ok" ]; then
    echo "[quick] tai $ORT_PKG ..."
    wget -q --timeout=30 --tries=4 --waitretry=15 --retry-on-http-error=429,500,502,503,504 "$ORT_URL" -O "${ORT_PKG}.tgz"
    tar xzf "${ORT_PKG}.tgz"
    rm -f "${ORT_PKG}.tgz"
  fi
fi
cd "$ENGINE_DIR"
echo "[quick] ONNX Runtime: $ENGINE_DIR/third_party/$ORT_PKG"
}
if [ "${SKIP_ORT:-0}" = 1 ]; then
  echo "[quick] bo qua ONNX Runtime (SKIP_ORT=1: bo chay CUDA rieng khong can no)"
else
  lay_ort
fi

# --- 3. run.sh ---------------------------------------------------------------
cat > "$ENGINE_DIR/run.sh" <<EOF
#!/usr/bin/env bash
# Auto-generated by colab_quickstart.sh
ED="$ENGINE_DIR"
export LD_LIBRARY_PATH="\$ED/third_party/$ORT_PKG/lib:\${LD_LIBRARY_PATH:-}"
# CUDA EP can libcublasLt/libcudnn... -- tren Colab chung nam trong cac goi pip
# nvidia-* cua torch, khong o duong dan mac dinh.
PYSITE="\$(python -c 'import site;print(site.getsitepackages()[0])' 2>/dev/null || echo '')"
if [ -n "\$PYSITE" ]; then
  for d in "\$PYSITE"/nvidia/*/lib; do [ -d "\$d" ] && export LD_LIBRARY_PATH="\$d:\$LD_LIBRARY_PATH"; done
fi
[ -d /usr/local/cuda/lib64 ] && export LD_LIBRARY_PATH="/usr/local/cuda/lib64:\$LD_LIBRARY_PATH"
exec "\$ED/build-linux/custom_engine" "\$@"
EOF
chmod +x "$ENGINE_DIR/run.sh"
echo "[quick] wrote $ENGINE_DIR/run.sh"

# --- 4. kiem tra -------------------------------------------------------------
kiem_tra() { bash "$ENGINE_DIR/run.sh" --test-uci 2>/tmp/fz_quick | grep -q '\[PASS\]'; }
if ! kiem_tra && [ "${SKIP_ORT:-0}" = 1 ]; then
  echo "[quick] engine can ONNX Runtime ngay luc nap (binary ban cu?) -- tai no roi kiem lai"
  lay_ort
fi
if kiem_tra; then
  echo "[quick] OK -- engine chay duoc tren Colab image nay."
  echo "[quick] Dung qua:  bash $ENGINE_DIR/run.sh <args>"
else
  echo "[quick] !! engine KHONG chay duoc (xem /tmp/fz_quick)."
  echo "[quick] !! Thuong la Colab doi base image -> chay colab_setup.sh de bien dich lai."
  exit 1
fi
