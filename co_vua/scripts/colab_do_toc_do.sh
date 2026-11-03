#!/usr/bin/env bash
# Do toc do tu choi tren Colab: chay lc0 treeplay voi van tu the khoi dau (cau hinh moc truyen thong:
# 800 luot tham, temperature 1 trong 30 nua nuoc dau) trong mot khoang thoi gian co dinh, in so lan
# chay mang moi giay.
#   bash colab_do_toc_do.sh <mang .pb.gz> <so van song song> <so luong gom lo> <so giay>
set -uo pipefail
CV=/content/cv
MANG=$1; SONG_SONG=$2; LUONG=$3; GIAY=$4
source "$CV/moi_truong.sh"
TEN="do_p${SONG_SONG}_t${LUONG}"
seq 0 99999 | sed 's/^/G /; s/$/ 30/' > "$CV/viec_do.txt"
timeout "$GIAY" "$CV/lc0" treeplay --weights="$MANG" \
  --backend=multiplexing --backend-opts="backend=onnx-cuda,threads=$LUONG,max_batch=1024" \
  --parallelism="$SONG_SONG" --visits=800 --report-seconds=15 \
  --output="$CV/$TEN.bin" < "$CV/viec_do.txt" > "$CV/$TEN.ra" 2> "$CV/$TEN.loi"
echo "== song song $SONG_SONG, luong gom lo $LUONG, $GIAY giay"
grep -v "^\s*$" "$CV/$TEN.loi" | grep -v "^.\[\|^|" | tail -4
echo "van xong: $(grep -c XONG "$CV/$TEN.ra")"
