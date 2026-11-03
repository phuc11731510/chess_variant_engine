#!/usr/bin/env bash
# Huan luyen mot doi tren Colab (chay nen; bo dieu phoi doc log va tep XONG qua SSH).
#   bash huan_luyen_doi.sh <G> <seed>
# Vao: /content/cv/hl/van/doi<k>/*.bin.gz voi k trong cua so (bo dieu phoi tai len), /content/cv/mang/doi<G>.pt
# Ra:  /content/cv/mang/doi<G+1>.pt, .onnx, .pb.gz; /content/cv/hl/tom_tat_doi<G>.json; log /content/cv/log/hl_doi<G>.log
set -euo pipefail
CV=/content/cv
G=$1; SEED=$2; G1=$((G + 1))
LOG="$CV/log/hl_doi$G.log"
cd "$CV/py"
{
  echo "$(date '+%F %T') huan luyen doi $G -> doi $G1, seed $SEED"
  MAU=""
  for d in $(ls -d "$CV"/hl/van/doi* | sort -V); do
    k=${d##*/doi}
    ls "$d"/*.bin.gz > /dev/null
    rm -f "$d"/*.bin
    for f in "$d"/*.bin.gz; do gunzip -k "$f"; done
    python3 tao_mau.py "$CV/hl/mau_doi$k.npz" "$d"/*.bin
    MAU="$MAU,$CV/hl/mau_doi$k.npz"
  done
  MAU=${MAU#,}
  echo "$(date '+%F %T') mau: $MAU"
  python3 huan_luyen.py --mau "$MAU" --khoi-tao "$CV/mang/doi$G.pt" --ra "$CV/mang/doi$G1" --seed "$SEED" \
    | tee "$CV/hl/tom_tat_doi$G.json"
  "$CV/lc0" onnx2leela --input="$CV/mang/doi$G1.onnx" --output="$CV/mang/doi$G1.pb.gz" \
    --onnx-input=input_planes --onnx-output-policy=policy --onnx-output-wdl=wdl --moves-left-format=MOVES_LEFT_NONE
  sha256sum "$CV/mang/doi$G1.pt" "$CV/mang/doi$G1.pb.gz"
  echo "$(date '+%F %T') XONG_HUAN_LUYEN"
} >> "$LOG" 2>&1
