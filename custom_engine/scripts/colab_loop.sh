#!/usr/bin/env bash
# =============================================================================
# FairyZero — run the full AlphaZero loop on Colab GPU with ONE command [T8.5].
# Build first with scripts/colab_setup.sh, then:
#     !bash /content/FairyZero/scripts/colab_loop.sh
#
# Tunables via env vars (all optional; sensible GPU defaults):
#   GENS=10 GAMES=1000 VISITS=200 WINDOW=4 EPOCHS=20 BATCH=1024
#   PARALLEL=2 FIXED_BATCH=32 EVAL=40 WORKDIR=<py>/loop_run
#   SAVE_DIR=/content/drive/MyDrive/FairyZero/models   # copy *.onnx here after each run
#   EXTRA="--diff-focus --resign-threshold -0.9"       # passed straight to loop.py
# Example:  !GENS=4 GAMES=400 VISITS=128 bash .../colab_loop.sh
# =============================================================================
set -e

# --- locate source + python (same auto-detect as colab_setup.sh) -------------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
if   [ -f "$ROOT_DIR/meson.build" ];            then ENGINE_DIR="$ROOT_DIR"
elif [ -f "$ROOT_DIR/engine_src/meson.build" ]; then ENGINE_DIR="$ROOT_DIR/engine_src"
else echo "[colab-loop] FATAL: meson.build not found"; exit 1; fi
if   [ -f "$ENGINE_DIR/python/loop.py" ]; then PY_DIR="$ENGINE_DIR/python"
elif [ -f "$ROOT_DIR/python/loop.py" ];   then PY_DIR="$ROOT_DIR/python"
else echo "[colab-loop] FATAL: python/loop.py not found"; exit 1; fi

BIN="$ENGINE_DIR/build-linux/custom_engine"
if [ ! -x "$BIN" ]; then
  echo "[colab-loop] FATAL: engine not built ($BIN). Run scripts/colab_setup.sh first."
  exit 1
fi

# --- make ORT + CUDA libs visible to the CUDA EP -----------------------------
ORT_DIR="$(ls -d "$ENGINE_DIR"/third_party/onnxruntime-linux-x64-gpu-* 2>/dev/null | head -1)"
[ -n "$ORT_DIR" ] && export LD_LIBRARY_PATH="$ORT_DIR/lib:${LD_LIBRARY_PATH:-}"
PYSITE="$(python -c 'import site;print(site.getsitepackages()[0])' 2>/dev/null || echo '')"
if [ -n "$PYSITE" ]; then
  for d in "$PYSITE"/nvidia/*/lib; do [ -d "$d" ] && export LD_LIBRARY_PATH="$d:$LD_LIBRARY_PATH"; done
fi
[ -d /usr/local/cuda/lib64 ] && export LD_LIBRARY_PATH="/usr/local/cuda/lib64:$LD_LIBRARY_PATH"

# --- defaults (override via env) ---------------------------------------------
GENS="${GENS:-10}"; GAMES="${GAMES:-1000}"; VISITS="${VISITS:-200}"
WINDOW="${WINDOW:-4}"; EPOCHS="${EPOCHS:-20}"; BATCH="${BATCH:-1024}"
PARALLEL="${PARALLEL:-2}"; FIXED_BATCH="${FIXED_BATCH:-32}"; EVAL="${EVAL:-40}"
WORKDIR="${WORKDIR:-$PY_DIR/loop_run}"

echo "[colab-loop] engine=$BIN"
echo "[colab-loop] gens=$GENS games/gen=$GAMES visits=$VISITS window=$WINDOW epochs=$EPOCHS batch=$BATCH"
nvidia-smi -L || true

python "$PY_DIR/loop.py" --engine "$BIN" --workdir "$WORKDIR" \
    --gens "$GENS" --games-per-gen "$GAMES" --visits "$VISITS" --window-gens "$WINDOW" \
    --epochs "$EPOCHS" --batch "$BATCH" --provider cuda --fixed-batch "$FIXED_BATCH" \
    --parallel "$PARALLEL" --eval-games "$EVAL" ${EXTRA:-}

# --- copy resulting models to Drive (optional) -------------------------------
if [ -n "${SAVE_DIR:-}" ]; then
  mkdir -p "$SAVE_DIR"
  cp -v "$WORKDIR"/models/*.onnx "$SAVE_DIR"/ 2>/dev/null || true
  echo "[colab-loop] models copied to $SAVE_DIR"
fi
echo "[colab-loop] DONE. Models in $WORKDIR/models/"
