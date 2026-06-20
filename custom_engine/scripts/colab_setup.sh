#!/usr/bin/env bash
# =============================================================================
# FairyZero — build & run on Google Colab (Linux + CUDA GPU)   [Milestone T6.5]
# =============================================================================
# Usage on Colab (after cloning the repo):
#     !bash custom_engine/scripts/colab_setup.sh
#
# Stages: (1) build tools  (2) download ONNX Runtime GPU  (3) meson+ninja build
#         (4) run the test suite  (5) gen-0 seed + a tiny GPU self-play smoke.
#
# IMPORTANT — match ONNX Runtime to Colab's CUDA:
#   ORT 1.18.0 GPU = CUDA 11.8 / cuDNN 8.  If Colab uses CUDA 12, set a CUDA-12
#   ORT build below (e.g. ORT_VER=1.20.1 which ships cuda12 .so) — the Linux
#   build uses THIS package's own headers, independent of the Windows 1.18.0.
# =============================================================================
set -e

# Default to a CUDA-12 ORT build (current Colab GPU runtimes are CUDA 12.x).
# Override for a different CUDA: ORT_VER=1.18.0 (=CUDA 11.8) bash colab_setup.sh
ORT_VER="${ORT_VER:-1.20.1}"
ORT_PKG="${ORT_PKG:-onnxruntime-linux-x64-gpu-${ORT_VER}}"
ORT_URL="${ORT_URL:-https://github.com/microsoft/onnxruntime/releases/download/v${ORT_VER}/${ORT_PKG}.tgz}"

# cd to the custom_engine directory (this script lives in custom_engine/scripts/).
cd "$(dirname "$0")/.."
ENGINE_DIR="$(pwd)"
echo "[colab] engine dir: $ENGINE_DIR"
nvidia-smi -L || echo "[colab] WARNING: no GPU visible (Runtime > Change runtime type > GPU)"

# --- (1) build tools + python deps -------------------------------------------
# meson/ninja for the C++ build; onnx (export) + onnxruntime (verify) for the
# Python side. torch + numpy are pre-installed on Colab.
echo "[colab] installing meson + ninja + onnx + onnxruntime ..."
pip install -q meson ninja onnx onnxruntime
apt-get -qq install -y ninja-build >/dev/null 2>&1 || true

# --- (2) ONNX Runtime GPU ----------------------------------------------------
mkdir -p third_party && cd third_party
if [ ! -d "$ORT_PKG" ]; then
  echo "[colab] downloading $ORT_PKG ..."
  wget -q "$ORT_URL" -O "${ORT_PKG}.tgz"
  tar xzf "${ORT_PKG}.tgz"
fi
cd "$ENGINE_DIR"
echo "[colab] ONNX Runtime: third_party/$ORT_PKG"

# --- (3) configure + build ---------------------------------------------------
echo "[colab] meson setup (use_cuda=true) ..."
if [ -d build-linux ]; then
  meson setup build-linux --reconfigure --buildtype=release \
      -Duse_cuda=true -Donnxruntime_dir="third_party/$ORT_PKG"
else
  meson setup build-linux --buildtype=release \
      -Duse_cuda=true -Donnxruntime_dir="third_party/$ORT_PKG"
fi
ninja -C build-linux
echo "[colab] built: build-linux/custom_engine"

# The binary has the ORT lib dir baked in as rpath; LD_LIBRARY_PATH is a backup.
export LD_LIBRARY_PATH="$ENGINE_DIR/third_party/$ORT_PKG/lib:${LD_LIBRARY_PATH:-}"
# Make the CUDA 12 runtime libs (libcublasLt.so.12, libcudnn.so.9, ...) visible
# to the ORT CUDA EP. On Colab these ship inside torch's nvidia-* pip packages
# and under /usr/local/cuda; add them all so providers_cuda.so resolves.
PYSITE="$(python -c 'import site;print(site.getsitepackages()[0])' 2>/dev/null || echo '')"
if [ -n "$PYSITE" ]; then
  for d in "$PYSITE"/nvidia/*/lib; do
    [ -d "$d" ] && export LD_LIBRARY_PATH="$d:$LD_LIBRARY_PATH"
  done
fi
[ -d /usr/local/cuda/lib64 ] && export LD_LIBRARY_PATH="/usr/local/cuda/lib64:$LD_LIBRARY_PATH"
BIN=./build-linux/custom_engine

# --- (4) correctness test suite (CPU-side logic; must be 100% green) ---------
echo "[colab] === test suite ==="
$BIN --test-board
$BIN --test-policy
$BIN --test-perft
$BIN --test-bits
$BIN --test-rules
$BIN --test-adapter
$BIN --test-nn
$BIN --test-trainingdata

# --- (5) gen-0 seed + GPU self-play smoke ------------------------------------
echo "[colab] === gen-0 seed (Python) ==="
python python/make_seed.py --out python/model_gen0.onnx

echo "[colab] === GPU self-play smoke (provider=cuda) ==="
echo "[colab] Colab CUDA: $(nvcc --version 2>/dev/null | grep -o 'release [0-9.]*' || echo 'nvcc not found')"
# Non-fatal: the build + test suite above are the DoD-critical parts. If the
# CUDA EP fails to load (ORT CUDA/cuDNN version != Colab's), this prints a hint
# instead of aborting; fix by setting ORT_VER to a matching CUDA build.
set +e
$BIN --selfplay --games 2 --parallel 1 --visits 32 --max-moves 20 \
     --provider cuda --fixed-batch 16 \
     --weights python/model_gen0.onnx --out python/selfplay_data
if [ $? -ne 0 ]; then
  echo "[colab] !! GPU self-play failed. Likely an ORT CUDA/cuDNN <-> Colab CUDA mismatch."
  echo "[colab] !! Colab's CUDA is shown above; current ORT pkg = $ORT_PKG (1.18.0 = CUDA 11.8)."
  echo "[colab] !! If Colab is CUDA 12.x, re-run with a CUDA-12 ORT, e.g.:"
  echo "[colab] !!     ORT_VER=1.20.1 bash custom_engine/scripts/colab_setup.sh"
  echo "[colab] !! (You can also test on CPU first: $BIN --selfplay --games 2 --provider cpu --weights python/model_gen0.onnx --out /tmp/sp)"
fi
set -e

echo ""
echo "[colab] DONE. Manual gen-data + train:"
echo "  $BIN --selfplay --games 1000 --parallel 2 --visits 200 --provider cuda --fixed-batch 32 --weights python/model_gen0.onnx --out python/selfplay_data"
echo "  python python/train.py --data python/selfplay_data --epochs 20 --batch 256 --init-from python/model_gen0.pt --out python/model_gen1.onnx --pin-memory --workers 2"
echo ""
echo "[colab] Or run the FULL AlphaZero loop (T7) on GPU:"
echo "  python python/loop.py --engine $BIN --gens 10 --games-per-gen 1000 --visits 200 \\"
echo "      --window-gens 4 --epochs 20 --batch 256 --provider cuda --fixed-batch 32 \\"
echo "      --parallel 2 --eval-games 40 --diff-focus --workdir python/loop_run"
