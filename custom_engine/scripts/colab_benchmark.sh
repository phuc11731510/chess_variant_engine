#!/usr/bin/env bash
# =============================================================================
# FairyZero — quét cấu hình self-play và in MỘT bảng so sánh.
#
# Mục đích: trả lời bằng ĐO ĐẠC, không phải suy đoán, ba câu hỏi:
#   1. GPU đã bão hoà chưa?            -> sm% + NN eval/giay
#   2. Gom batch có hiệu quả không?    -> batch TB moi Run() + % phí do pad
#   3. Tăng --parallel có giúp không?  -> van/gio giữa các cấu hình
#
# Mọi cấu hình chạy CÙNG một khoảng thời gian tường (SECS) nên "van/gio" so sánh
# được trực tiếp. Đây là thước đo mục tiêu; nps chỉ là thông tin phụ.
#
# Dùng:
#   WEIGHTS=/content/net.onnx bash colab_benchmark.sh
#   WEIGHTS=... SECS=120 bash colab_benchmark.sh      # quét nhanh hơn
#
# Biến môi trường:
#   WEIGHTS  (bắt buộc) đường dẫn tệp .onnx
#   ENGINE   đường dẫn run.sh hoặc binary (mặc định: dò tự động)
#   SECS     giây mỗi cấu hình (mặc định 240)
#   VISITS   playout mỗi nước (mặc định 800 — giữ giống lúc sinh dữ liệu thật)
#   OUTROOT  thư mục tạm cho .gz (mặc định /content/bench, xoá sau mỗi lượt)
# =============================================================================
set -u

SECS="${SECS:-240}"
VISITS="${VISITS:-800}"
OUTROOT="${OUTROOT:-/content/bench}"
MAXMOVES="${MAXMOVES:-400}"

if [ -z "${WEIGHTS:-}" ]; then
  echo "FATAL: chua dat WEIGHTS=/duong/dan/net.onnx" >&2; exit 1
fi
[ -f "$WEIGHTS" ] || { echo "FATAL: khong thay $WEIGHTS" >&2; exit 1; }

# --- dò engine -------------------------------------------------------------
if [ -z "${ENGINE:-}" ]; then
  for c in ./run.sh ./custom_engine/run.sh \
           /content/chess_variant_engine/custom_engine/run.sh \
           ./build-linux/custom_engine \
           /content/chess_variant_engine/custom_engine/build-linux/custom_engine; do
    [ -x "$c" ] && ENGINE="$c" && break
  done
fi
[ -n "${ENGINE:-}" ] && [ -x "$ENGINE" ] || {
  echo "FATAL: khong tim thay engine. Dat ENGINE=/duong/dan/run.sh" >&2; exit 1; }
case "$ENGINE" in *.sh) RUN="bash $ENGINE";; *) RUN="$ENGINE";; esac

echo "engine : $ENGINE"
echo "weights: $WEIGHTS"
echo "moi cau hinh: ${SECS}s, visits=$VISITS, max-moves=$MAXMOVES"
echo

# --- các cấu hình cần quét --------------------------------------------------
# ten|parallel|fixed_batch|aggregate(0/1)|timeout_us
CONFIGS="
A_hientai|4|16|0|0
B_1van|1|16|0|0
C_agg_p4|4|64|1|500
D_agg_p8|8|64|1|500
E_agg_p16|16|64|1|200
F_agg_p32|32|64|1|200
"

RESULTS=""

for cfg in $CONFIGS; do
  [ -z "$cfg" ] && continue
  NAME=$(echo "$cfg" | cut -d'|' -f1)
  PAR=$(echo  "$cfg" | cut -d'|' -f2)
  FB=$(echo   "$cfg" | cut -d'|' -f3)
  AGG=$(echo  "$cfg" | cut -d'|' -f4)
  TMO=$(echo  "$cfg" | cut -d'|' -f5)

  EXTRA=""
  [ "$AGG" = "1" ] && EXTRA="--batch-aggregate --batch-timeout-us $TMO"

  OUT="$OUTROOT/$NAME"
  rm -rf "$OUT"; mkdir -p "$OUT"
  LOG="$OUTROOT/$NAME.log"

  echo "=============================================================="
  echo ">>> $NAME : parallel=$PAR fixed-batch=$FB aggregate=$AGG timeout=$TMO"
  echo "=============================================================="

  # Lấy mẫu sm% song song (1 mẫu/giây). Bỏ qua nếu khong co nvidia-smi.
  SMLOG="$OUTROOT/$NAME.sm"
  rm -f "$SMLOG"
  if command -v nvidia-smi >/dev/null 2>&1; then
    ( nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits \
        -l 1 > "$SMLOG" 2>/dev/null ) &
    SMPID=$!
  else
    SMPID=""
  fi

  $RUN --selfplay \
      --games 100000 --max-seconds "$SECS" \
      --visits "$VISITS" --max-moves "$MAXMOVES" --temp-cutoff 32 \
      --parallel "$PAR" --provider cuda --fixed-batch "$FB" $EXTRA \
      --noise-alpha 0.15 --show-nps \
      --weights "$WEIGHTS" --out "$OUT" > "$LOG" 2>&1

  [ -n "$SMPID" ] && kill "$SMPID" 2>/dev/null

  tail -14 "$LOG"

  # --- rút số liệu ---------------------------------------------------------
  pick() { grep -m1 "$1" "$LOG" | sed 's/.*: *//' | tr -d ' ' ; }
  GAMES=$(grep -m1 "Finished" "$LOG" | sed 's/.*Finished \([0-9]*\)\/.*/\1/')
  VANGIO=$(pick "Van/gio")
  EVALS=$(pick "NN eval/giay")
  EVPP=$(pick "NN eval/playout")
  BATCH=$(grep -m1 "Batch TB moi Run()" "$LOG" | sed 's/.*: *//; s/ .*//')
  PAD=$(grep -m1 "Phi do pad" "$LOG" | sed 's/.*: *//; s/%.*/%/')
  if [ -s "$SMLOG" ]; then
    SM=$(awk '{s+=$1; n++} END{if(n>0) printf "%.0f%%", s/n; else print "-"}' "$SMLOG")
  else
    SM="-"
  fi

  RESULTS="${RESULTS}${NAME}|${PAR}|${FB}|${AGG}|${GAMES:-0}|${VANGIO:--}|${EVALS:--}|${EVPP:--}|${BATCH:--}|${PAD:--}|${SM}\n"

  rm -rf "$OUT"          # .gz cua benchmark khong dung de huan luyen
done

echo
echo "================================ KET QUA ================================"
printf "%-11s %4s %4s %4s %6s %9s %11s %8s %8s %8s %6s\n" \
  "cau_hinh" "par" "fb" "agg" "van" "van/gio" "eval/giay" "ev/play" "batchTB" "pad%" "sm%"
printf -- "-------------------------------------------------------------------------------------\n"
printf "$RESULTS" | while IFS='|' read -r n p f a g vg ev ep bt pd sm; do
  [ -z "$n" ] && continue
  printf "%-11s %4s %4s %4s %6s %9s %11s %8s %8s %8s %6s\n" \
    "$n" "$p" "$f" "$a" "$g" "$vg" "$ev" "$ep" "$bt" "$pd" "$sm"
done
echo "========================================================================="
echo
echo "Cach doc:"
echo "  van/gio   : MUC TIEU. Cao hon = tot hon. Moi thu khac chi de giai thich."
echo "  sm%       : GPU ban bao nhieu. <50% = GPU DANG CHO, nut that o CPU/dieu phoi."
echo "  eval/giay : cong viec GPU that su. Nhan ~1.0 GFLOP de ra TFLOP/s"
echo "              (T4 dinh fp32 = 8.1 TFLOPS)."
echo "  ev/play   : >1 nghia la nhieu eval cho mot playout (collision, cache miss)."
echo "  batchTB   : batch trung binh moi lan Run(). Thap hon fixed-batch nhieu"
echo "              = gom batch KHONG hieu qua, nang MaxBatchSize se vo ich."
echo "  pad%      : phan tram thoi gian GPU tinh o batch rong do fixed-batch pad."
