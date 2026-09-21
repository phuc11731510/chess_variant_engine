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
  if ! $PY -m pip -q install "onnxruntime-gpu==$ORT_VER" onnx >/dev/null 2>&1; then
    PYVER="$($PY -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo '?')"
    echo "[bench] khong cai duoc ORT $ORT_VER -- Colab dang chay Python $PYVER"
    echo "[bench] va ORT $ORT_VER khong co wheel cho ban Python do. Dung ban moi nhat."
    echo "[bench] LUU Y: ban do se KHAC ban engine dung -> chi so tuyet doi khong"
    echo "[bench] so thang duoc voi self-play; ti so TensorRT/CUDA thi van co nghia."
    $PY -m pip -q install onnxruntime-gpu onnx >/dev/null 2>&1
  fi

  # ORT >= 1.23 duoc build cho CUDA 13 (loi dien hinh: "libcublasLt.so.13: cannot
  # open shared object file"), trong khi torch cua Colab chi mang CUDA 12. Cai
  # them bo thu vien cu13 -- driver Colab (nvidia-smi bao CUDA 13.0) ho tro.
  ORT_NOW="$($PY -c 'import onnxruntime;print(onnxruntime.__version__)' 2>/dev/null || echo 0.0)"
  NEEDS_CU13=0
  $PY -c "import sys; v=sys.argv[1].split('.'); sys.exit(0 if (int(v[0]),int(v[1]))>=(1,23) else 1)" \
      "$ORT_NOW" 2>/dev/null && NEEDS_CU13=1
  if [ "${FORCE_CU13:-0}" = "1" ] || [ "$NEEDS_CU13" = "1" ]; then
    echo "[bench] ORT $ORT_NOW can CUDA 13 -> cai bo thu vien nvidia-*-cu13 ..."
    $PY -m pip -q install nvidia-cublas-cu13 nvidia-cudnn-cu13 \
        nvidia-cuda-runtime-cu13 nvidia-cufft-cu13 nvidia-curand-cu13 \
        nvidia-cusolver-cu13 nvidia-cusparse-cu13 nvidia-nvjitlink-cu13 \
        >/dev/null 2>&1 || echo "[bench] mot so goi cu13 khong cai duoc (bo qua)"
  fi
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
