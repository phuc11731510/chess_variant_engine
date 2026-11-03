#!/usr/bin/env bash
# Chuan bi may Colab cho du an co vua (chay tren Colab sau khi bo dieu phoi tai goi.tar.gz len /content/cv).
# - Giai goi: lc0, py/ (ma Python), colab/ (cac script nay).
# - Tai ONNX Runtime 1.20.1 ban GPU (cung ban dung khi bien dich) tu GitHub cua Microsoft vao /content/cv/lib
#   (lc0 co RUNPATH $ORIGIN/lib).
# - Cai python-chess (ma hoa the co khi tao mau) va onnx (torch can de xuat mang).
# - Ghi /content/cv/moi_truong.sh: LD_LIBRARY_PATH toi thu vien CUDA/cuDNN cua cac goi pip nvidia-* co san.
# In mot dong JSON tom tat may (GPU, CPU, RAM, phien ban) de bo dieu phoi luu vao log.
set -euo pipefail
CV=/content/cv
ORT=onnxruntime-linux-x64-gpu-1.20.1
cd "$CV"
tar -xzf goi.tar.gz
chmod +x lc0
mkdir -p lib mang log
if [ ! -f lib/libonnxruntime_providers_cuda.so ]; then
  wget -q "https://github.com/microsoft/onnxruntime/releases/download/v1.20.1/$ORT.tgz" -O /tmp/ort.tgz
  tar xzf /tmp/ort.tgz -C /tmp
  cp -a /tmp/$ORT/lib/libonnxruntime* lib/
fi
python3 -c "import chess, onnx" 2>/dev/null || pip install -q chess onnx
LD="$CV/lib"
PYSITE=$(python3 -c "import site; print(site.getsitepackages()[0])")
for d in "$PYSITE"/nvidia/*/lib; do
  [ -d "$d" ] && LD="$LD:$d"
done
[ -d /usr/local/cuda/lib64 ] && LD="$LD:/usr/local/cuda/lib64"
echo "export LD_LIBRARY_PATH=$LD:\${LD_LIBRARY_PATH:-}" > moi_truong.sh
python3 - <<'EOF'
import json, os, platform, subprocess
g = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
                   capture_output=True, text=True).stdout.strip()
import torch, chess, numpy
print("MAY " + json.dumps({"gpu": g, "so_cpu": os.cpu_count(),
      "ram_gb": round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30, 1),
      "python": platform.python_version(), "torch": torch.__version__, "cuda_torch": torch.version.cuda,
      "numpy": numpy.__version__, "python_chess": chess.__version__,
      "goi": open("/content/cv/goi_thong_tin.txt").read().strip()}, ensure_ascii=False))
EOF
