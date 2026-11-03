#!/usr/bin/env bash
# Chuan bi may Colab cho engine co vua (chay tren Colab, sau khi da tai lc0 len /content/cv/lc0).
# - Tai ONNX Runtime 1.20.1 ban GPU (cung ban dung khi bien dich, co_vua/scripts/bien_dich_linux.sh)
#   tu GitHub cua Microsoft, chep thu vien vao /content/cv/lib (lc0 co RUNPATH $ORIGIN/lib).
# - Ghi /content/cv/moi_truong.sh: LD_LIBRARY_PATH tro toi thu vien CUDA/cuDNN cua cac goi pip nvidia-*
#   co san tren Colab, can cho provider CUDA cua ONNX Runtime.
set -euo pipefail
CV=/content/cv
ORT=onnxruntime-linux-x64-gpu-1.20.1
mkdir -p "$CV/lib"
if [ ! -f "$CV/lib/libonnxruntime_providers_cuda.so" ]; then
  echo "[chuan bi] tai $ORT ..."
  wget -q "https://github.com/microsoft/onnxruntime/releases/download/v1.20.1/$ORT.tgz" -O /tmp/ort.tgz
  tar xzf /tmp/ort.tgz -C /tmp
  cp -a /tmp/$ORT/lib/libonnxruntime* "$CV/lib/"
fi
LD="$CV/lib"
PYSITE=$(python3 -c "import site; print(site.getsitepackages()[0])")
for d in "$PYSITE"/nvidia/*/lib; do
  [ -d "$d" ] && LD="$LD:$d"
done
[ -d /usr/local/cuda/lib64 ] && LD="$LD:/usr/local/cuda/lib64"
echo "export LD_LIBRARY_PATH=$LD:\${LD_LIBRARY_PATH:-}" > "$CV/moi_truong.sh"
chmod +x "$CV/lc0"
nvidia-smi -L
echo "[chuan bi] xong"
