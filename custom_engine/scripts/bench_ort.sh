#!/usr/bin/env bash
# =============================================================================
# Chay bench_ort.py voi LD_LIBRARY_PATH dung, va voi onnxruntime-gpu KHOP
# PHIEN BAN ma engine dang dung.
#
# Vi sao can wrapper nay (hai cai bay, ca hai deu da cam bay that):
#
#  1. CUDAExecutionProvider dlopen cuDNN/cuBLAS LUC NAP. Tren Colab cac thu vien
#     do nam trong cac goi pip nvidia-* cua torch, khong nam trong duong dan mac
#     dinh. Python KHONG the tu sua LD_LIBRARY_PATH cho chinh tien trinh no dang
#     chay -> phai dat TRUOC khi khoi dong. Day chinh xac la ly do
#     colab_prebuilt.sh phai sinh ra run.sh cho engine.
#
#  2. Colab cai san onnxruntime (CPU) va pip co the cai onnxruntime-gpu ban moi
#     nhat, vd 1.30, duoc build cho mot phien ban CUDA khac. Do ban do thi khong
#     noi len dieu gi ve ban engine dung. ORT_VER duoi day PHAI khop
#     ORT_VER trong colab_setup.sh.
#
# Dung:
#   bash bench_ort.sh /content/net.onnx
#   ORT_VER=1.20.1 SKIP_INSTALL=1 bash bench_ort.sh /content/net.onnx
# =============================================================================
set -u

MODEL="${1:-}"
[ -n "$MODEL" ] || { echo "dung: bash bench_ort.sh <model.onnx> [--board N]" >&2; exit 1; }
[ -f "$MODEL" ] || { echo "FATAL: khong thay $MODEL" >&2; exit 1; }
shift

ORT_VER="${ORT_VER:-1.20.1}"   # PHAI khop colab_setup.sh
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PY="${PY:-python3}"

if [ "${SKIP_INSTALL:-0}" != "1" ]; then
  echo "[bench] go onnxruntime cu va cai onnxruntime-gpu==$ORT_VER (khop engine) ..."
  $PY -m pip -q uninstall -y onnxruntime onnxruntime-gpu >/dev/null 2>&1 || true
  $PY -m pip -q install "onnxruntime-gpu==$ORT_VER" onnx >/dev/null 2>&1 \
    || { echo "[bench] pip that bai, thu khong ghim phien ban ..."; \
         $PY -m pip -q install onnxruntime-gpu onnx >/dev/null 2>&1; }
fi

# --- gom moi thu muc thu vien CUDA co the co -------------------------------
LIBS=""
for sp in $($PY -c 'import site,sys; [print(p) for p in (site.getsitepackages() or [])]' 2>/dev/null); do
  for d in "$sp"/nvidia/*/lib; do [ -d "$d" ] && LIBS="$d:$LIBS"; done
done
for d in /usr/local/cuda/lib64 /usr/lib/x86_64-linux-gnu; do
  [ -d "$d" ] && LIBS="$d:$LIBS"
done
export LD_LIBRARY_PATH="${LIBS}${LD_LIBRARY_PATH:-}"

echo "[bench] ORT_VER=$ORT_VER"
echo "[bench] LD_LIBRARY_PATH co $(echo "$LD_LIBRARY_PATH" | tr ':' '\n' | grep -c .) muc"
echo

exec $PY "$SCRIPT_DIR/bench_ort.py" "$MODEL" "$@"
