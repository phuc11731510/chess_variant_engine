#!/usr/bin/env bash
# =============================================================================
# FairyZero — build & run on Google Colab (Linux + CUDA GPU)   [T6.5 / T8.5]
# =============================================================================
# Works with BOTH layouts (auto-detected):
#   * repo:    custom_engine/{meson.build, src/, python/, scripts/colab_setup.sh}
#              -> !bash custom_engine/scripts/colab_setup.sh
#   * bundle:  FairyZero/{engine_src/{meson.build,src/}, python/, scripts/colab_setup.sh}
#              -> !bash FairyZero/scripts/colab_setup.sh
#
# Stages: (1) build tools  (2) download ONNX Runtime GPU  (3) meson+ninja build
#         (4) run the test suite  (5) gen-0 seed + a tiny GPU self-play smoke.
#
# IMPORTANT — match ONNX Runtime to Colab's CUDA:
#   ORT 1.18.0 GPU = CUDA 11.8 / cuDNN 8.  Default below is 1.20.1 (CUDA 12).
#   Override:  ORT_VER=1.18.0 bash <script>     (for a CUDA-11.8 runtime)
#
# TIP: building on Google Drive (/content/drive/...) is SLOW + can be flaky (FUSE).
#      For speed, copy the folder to local disk first, e.g.:
#        !cp -r /content/drive/MyDrive/FairyZero /content/FairyZero
#        !bash /content/FairyZero/scripts/colab_setup.sh
# =============================================================================
set -e

ORT_VER="${ORT_VER:-1.20.1}"
ORT_PKG="${ORT_PKG:-onnxruntime-linux-x64-gpu-${ORT_VER}}"
ORT_URL="${ORT_URL:-https://github.com/microsoft/onnxruntime/releases/download/v${ORT_VER}/${ORT_PKG}.tgz}"

# --- locate the source tree (where meson.build is) and the python/ dir -------
# This script lives in <ROOT>/scripts/. The engine source may be at <ROOT> (repo)
# or <ROOT>/engine_src (portable bundle); python/ may sit next to either.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

if   [ -f "$ROOT_DIR/meson.build" ];            then ENGINE_DIR="$ROOT_DIR"
elif [ -f "$ROOT_DIR/engine_src/meson.build" ]; then ENGINE_DIR="$ROOT_DIR/engine_src"
else echo "[colab] FATAL: meson.build not found under $ROOT_DIR or $ROOT_DIR/engine_src"; exit 1; fi

if   [ -f "$ENGINE_DIR/python/make_seed.py" ]; then PY_DIR="$ENGINE_DIR/python"
elif [ -f "$ROOT_DIR/python/make_seed.py" ];   then PY_DIR="$ROOT_DIR/python"
else echo "[colab] FATAL: python/make_seed.py not found"; exit 1; fi

echo "[colab] engine dir: $ENGINE_DIR"
echo "[colab] python dir: $PY_DIR"
nvidia-smi -L || echo "[colab] WARNING: no GPU visible (Runtime > Change runtime type > GPU)"

# --- (1) build tools + python deps -------------------------------------------
echo "[colab] installing meson + ninja + onnx + onnxruntime ..."
pip install -q meson ninja onnx onnxruntime
apt-get -qq install -y ninja-build >/dev/null 2>&1 || true

# --- (2) ONNX Runtime GPU ----------------------------------------------------
mkdir -p "$ENGINE_DIR/third_party"
cd "$ENGINE_DIR/third_party"
if [ ! -d "$ORT_PKG" ]; then
  echo "[colab] downloading $ORT_PKG ..."
  wget -q "$ORT_URL" -O "${ORT_PKG}.tgz"
  tar xzf "${ORT_PKG}.tgz"
fi
cd "$ENGINE_DIR"
echo "[colab] ONNX Runtime: $ENGINE_DIR/third_party/$ORT_PKG"

# --- (3) configure + build ---------------------------------------------------
# Copying from Google Drive (FUSE) can leave source files with mtimes in the FUTURE
# relative to the Colab VM clock, which makes meson abort with "Clock skew detected".
# Normalize every timestamp in the engine tree to "now" before configuring.
echo "[colab] normalizing source timestamps (avoid meson clock-skew) ..."
find "$ENGINE_DIR" -exec touch {} + 2>/dev/null || true

echo "[colab] meson setup (use_cuda=true) ..."
if [ -d build-linux ]; then
  meson setup build-linux --reconfigure --buildtype=release \
      -Duse_cuda=true -Donnxruntime_dir="third_party/$ORT_PKG"
else
  meson setup build-linux --buildtype=release \
      -Duse_cuda=true -Donnxruntime_dir="third_party/$ORT_PKG"
fi
ninja -C build-linux
BIN="$ENGINE_DIR/build-linux/custom_engine"
echo "[colab] built: $BIN"

# The binary has the ORT lib dir baked in as rpath; LD_LIBRARY_PATH is a backup.
export LD_LIBRARY_PATH="$ENGINE_DIR/third_party/$ORT_PKG/lib:${LD_LIBRARY_PATH:-}"
# Make the CUDA 12 runtime libs (libcublasLt.so.12, libcudnn.so.9, ...) visible
# to the ORT CUDA EP (they ship inside torch's nvidia-* pip packages + /usr/local/cuda).
PYSITE="$(python -c 'import site;print(site.getsitepackages()[0])' 2>/dev/null || echo '')"
if [ -n "$PYSITE" ]; then
  for d in "$PYSITE"/nvidia/*/lib; do
    [ -d "$d" ] && export LD_LIBRARY_PATH="$d:$LD_LIBRARY_PATH"
  done
fi
[ -d /usr/local/cuda/lib64 ] && export LD_LIBRARY_PATH="/usr/local/cuda/lib64:$LD_LIBRARY_PATH"

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
$BIN --test-uci
$BIN --test-encoder

# --- (5) gen-0 seed + GPU self-play smoke ------------------------------------
echo "[colab] === gen-0 seed (Python) ==="
python "$PY_DIR/make_seed.py" --out "$PY_DIR/model_gen0.onnx"

echo "[colab] === GPU self-play smoke (provider=cuda) ==="
echo "[colab] Colab CUDA: $(nvcc --version 2>/dev/null | grep -o 'release [0-9.]*' || echo 'nvcc not found')"
set +e
$BIN --selfplay --games 2 --parallel 1 --visits 32 --max-moves 20 \
     --provider cuda --fixed-batch 16 \
     --weights "$PY_DIR/model_gen0.onnx" --out "$PY_DIR/selfplay_data"
if [ $? -ne 0 ]; then
  echo "[colab] !! GPU self-play failed. Likely an ORT CUDA/cuDNN <-> Colab CUDA mismatch."
  echo "[colab] !! Current ORT pkg = $ORT_PKG. If Colab is CUDA 11.x, re-run with:"
  echo "[colab] !!     ORT_VER=1.18.0 bash $SCRIPT_DIR/colab_setup.sh"
  echo "[colab] !! (CPU fallback: $BIN --selfplay --games 2 --provider cpu --weights $PY_DIR/model_gen0.onnx --out /tmp/sp)"
fi
set -e

echo ""
echo "[colab] DONE. Engine: $BIN"
echo "[colab] Two separate steps (see HUONG_DAN.md muc C):"
echo "[colab] 1) Generate self-play data on GPU:"
echo "  $BIN --selfplay --games 1000 --visits 200 --parallel 2 \\"
echo "      --provider cuda --fixed-batch 32 --weights $PY_DIR/seed.onnx --out $PY_DIR/games_gen0"
echo "[colab] 2) Train next generation (warm-start from the gen-0 .pt):"
echo "  python $PY_DIR/train.py --data $PY_DIR/games_gen0 --epochs 20 --batch 1024 \\"
echo "      --amp --init-from $PY_DIR/seed.pt --out $PY_DIR/model_gen1.onnx"
