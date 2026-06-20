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

ORT_VER="${ORT_VER:-1.18.0}"
ORT_PKG="${ORT_PKG:-onnxruntime-linux-x64-gpu-${ORT_VER}}"
ORT_URL="${ORT_URL:-https://github.com/microsoft/onnxruntime/releases/download/v${ORT_VER}/${ORT_PKG}.tgz}"

# cd to the custom_engine directory (this script lives in custom_engine/scripts/).
cd "$(dirname "$0")/.."
ENGINE_DIR="$(pwd)"
echo "[colab] engine dir: $ENGINE_DIR"
nvidia-smi -L || echo "[colab] WARNING: no GPU visible (Runtime > Change runtime type > GPU)"

# --- (1) build tools ---------------------------------------------------------
echo "[colab] installing meson + ninja ..."
pip install -q meson ninja
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
$BIN --selfplay --games 2 --parallel 1 --visits 32 --max-moves 20 \
     --provider cuda --fixed-batch 16 \
     --weights python/model_gen0.onnx --out python/selfplay_data

echo ""
echo "[colab] DONE. To generate data on GPU and train:"
echo "  $BIN --selfplay --games 1000 --parallel 2 --visits 200 --provider cuda --fixed-batch 32 --weights python/model_gen0.onnx --out python/selfplay_data"
echo "  python python/train.py --data python/selfplay_data --epochs 20 --batch 256 --init-from python/model_gen0.pt --out python/model_gen1.onnx --pin-memory --workers 2"
