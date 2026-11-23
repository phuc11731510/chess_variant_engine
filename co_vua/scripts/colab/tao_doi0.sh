#!/usr/bin/env bash
# Tao mang doi 0 (khoi tao ngau nhien, fp32) tren Colab va boc cho lc0.
#   bash tao_doi0.sh <seed>
# Ra: /content/cv/mang/doi0.pt, doi0.onnx, doi0.pb.gz; log: /content/cv/log/tao_doi0.log
set -euo pipefail
CV=/content/cv
SEED=$1
cd "$CV/py"
{
  echo "$(date '+%F %T') tao doi 0, seed $SEED"
  python3 tao_mang_doi0.py "$CV/mang" "$SEED"
  "$CV/lc0" onnx2leela --input="$CV/mang/doi0.onnx" --output="$CV/mang/doi0.pb.gz" \
    --onnx-input=input_planes --onnx-output-policy=policy --onnx-output-wdl=wdl --moves-left-format=MOVES_LEFT_NONE
  sha256sum "$CV/mang/doi0.pt" "$CV/mang/doi0.pb.gz"
  echo "$(date '+%F %T') XONG_DOI0"
} >> "$CV/log/tao_doi0.log" 2>&1
