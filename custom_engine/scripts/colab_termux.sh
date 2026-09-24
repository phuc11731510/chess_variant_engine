#!/data/data/com.termux/files/usr/bin/bash
# colab_termux.sh -- chay vong FairyZero tren Colab GPU tu Termux (google-colab-cli), khong can trinh duyet.
# Tuong duong so tay FairyZero_1.ipynb. Huong dan day du: HUONG_DAN_TERMUX.md. Dung:
#   export GEN=0                      # doi hien tai (giong GEN_CURRENT trong so tay)
#   bash colab_termux.sh start        # muc 0-2: xin VM GPU (T4), KIEM GPU, tai binary + ORT, nap/tao mang doi GEN
#   bash colab_termux.sh gpu          # kiem lai VM dang co GPU gi
#   bash colab_termux.sh selfplay     # muc 3: sinh du lieu CHAY NEN tren VM (SECS=15480 mac dinh)
#   bash colab_termux.sh status       # xem log selfplay (status train / status arena)
#   bash colab_termux.sh fetch        # muc 4: gom zip + tai ve dien thoai
#   bash colab_termux.sh train        # muc 5: huan luyen CHAY NEN (DATA="a.zip,b.zip" de cua so truot)
#   bash colab_termux.sh getnet       # tai gen{GEN+1}.onnx/.pt ve dien thoai
#   bash colab_termux.sh arena        # muc 6: arena CHAY NEN
#   bash colab_termux.sh stop         # tra VM (MAT het /content -- fetch/getnet truoc!)
set -euo pipefail

S=${S:-fz}                 # ten phien Colab
GPU=${GPU:-T4}             # T4 (mien phi) | L4 | A100 | H100 | G4 (can Colab Pro / don vi tinh toan)
GEN=${GEN:-0}
NEXT=$((GEN + 1))
E=/content/chess_variant_engine/custom_engine
REL=https://github.com/phuc11731510/chess_variant_engine/releases/download/v3.0.0
LOCAL=${LOCAL:-$HOME/storage/downloads/FairyZero}
mkdir -p "$LOCAL"

rx() { colab exec -s "$S"; }   # chay ma (cu phap o Colab: !lenh, %cd) doc tu stdin tren VM

# In ten GPU cua VM; tra ve 1 neu VM chi co CPU.
check_gpu() {
  local out
  out=$(echo '!nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo FZ_NO_GPU' | rx)
  echo "[fz] GPU cua VM: $out"
  case "$out" in
    *FZ_NO_GPU*|"") return 1 ;;
    *) return 0 ;;
  esac
}

case "${1:-}" in
start)
  if colab sessions 2>/dev/null | grep -qw -- "$S"; then
    echo "[fz] phien '$S' DA TON TAI (co the la VM CPU cu). Kiem: bash $0 gpu"
    echo "[fz] muon xin lai tu dau: bash $0 stop  roi  bash $0 start"
    exit 1
  fi
  colab new -s "$S" --gpu "$GPU"
  colab status -s "$S" || true
  if ! check_gpu; then
    echo "[fz] LOI: VM KHONG co GPU (chi CPU). Tra VM de khoi ton quota."
    echo "[fz] Nguyen nhan hay gap: het quota GPU mien phi hom nay, hoac lenh 'colab new' thieu --gpu."
    colab stop -s "$S" || true
    exit 1
  fi
  rx <<EOF
%cd /content
!rm -rf chess_variant_engine
!git clone -q --depth 1 -b main https://github.com/phuc11731510/chess_variant_engine.git
!BIN_URL=$REL/custom_engine bash $E/scripts/colab_quickstart.sh
!pip install -q onnx onnxscript onnxruntime
EOF
  for x in onnx pt; do
    if [ -f "$LOCAL/gen$GEN.$x" ]; then
      colab upload -s "$S" "$LOCAL/gen$GEN.$x" "/content/gen$GEN.$x"
    elif [ "$GEN" -eq 0 ]; then
      [ "$x" = onnx ] && echo "!cd $E/python && python make_seed.py --channels 144 --blocks 12 --se-ratio 8 --out /content/gen0.onnx" | rx
      colab download -s "$S" "/content/gen0.$x" "$LOCAL/gen0.$x"
    else
      echo "!wget -q -O /content/gen$GEN.$x $REL/gen$GEN.$x" | rx
    fi
  done
  echo "!ls -la /content/gen$GEN.*" | rx
  ;;
gpu)
  colab sessions || true
  colab status -s "$S" || true
  check_gpu || echo "[fz] VM nay CHI CO CPU -- selfplay --provider cuda se khong chay."
  ;;
selfplay)
  check_gpu || { echo "[fz] VM khong co GPU -- dung lai."; exit 1; }
  echo "!nohup bash $E/run.sh --selfplay --games 1000 --max-seconds ${SECS:-15480} \
--visits 800 --max-moves 400 --temp-cutoff 32 --parallel 4 --provider cuda --fixed-batch 16 \
--noise-alpha 0.15 --show-nps --search-opt max-prefetch=0 \
--weights /content/gen$GEN.onnx --out /content/games_gen$GEN > /content/selfplay.log 2>&1 &" | rx
  echo "[fz] da chay nen tren VM; xem: bash $0 status"
  ;;
status)
  echo "!tail -n ${N:-15} /content/${2:-selfplay}.log; ls /content/games_gen$GEN 2>/dev/null | wc -l | sed 's/^/[fz] so tep van: /'; \
nvidia-smi --query-gpu=name,utilization.gpu,memory.used --format=csv,noheader 2>/dev/null | sed 's/^/[fz] GPU: /'; \
pgrep -af '[c]ustom_engine|[t]rain\.py' >/dev/null && echo '[fz] DANG CHAY' || echo '[fz] KHONG con tien trinh (xong hoac loi)'" | rx
  ;;
fetch)
  echo "!python $E/python/archive.py pack /content/games_gen$GEN --out /content/games_gen$GEN.zip && ls -la /content/games_gen$GEN.zip" | rx
  colab download -s "$S" "/content/games_gen$GEN.zip" "$LOCAL/games_gen$GEN.zip"
  ;;
train)
  check_gpu || { echo "[fz] VM khong co GPU -- dung lai."; exit 1; }
  echo "!nohup python $E/python/train.py --data \"${DATA:-/content/games_gen$GEN.zip}\" --init-from /content/gen$GEN.pt \
--epochs 2 --batch 1024 --lr 1e-3 --amp --q-ratio 0.2 --weight-decay 1e-4 --report-every 20 \
--channels 144 --blocks 12 --out /content/gen$NEXT.onnx > /content/train.log 2>&1 &" | rx
  echo "[fz] da chay nen tren VM; xem: bash $0 status train"
  ;;
getnet)
  for x in onnx pt; do colab download -s "$S" "/content/gen$NEXT.$x" "$LOCAL/gen$NEXT.$x"; done
  ;;
arena)
  echo "!nohup bash $E/run.sh --arena --model-a /content/gen$NEXT.onnx --model-b /content/gen$GEN.onnx \
--games 48 --visits 400 --temp-cutoff 32 --provider cuda --fixed-batch 16 --max-moves 400 --show-nps \
> /content/arena.log 2>&1 &" | rx
  echo "[fz] da chay nen tren VM; xem: bash $0 status arena"
  ;;
stop)
  colab stop -s "$S"
  ;;
*)
  sed -n '2,15p' "$0"; exit 1
  ;;
esac
