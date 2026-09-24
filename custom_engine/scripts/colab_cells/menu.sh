#!/data/data/com.termux/files/usr/bin/bash
# menu.sh -- menu FairyZero tren Termux: chon o lenh bang so, chay tren may Colab.
# Mo bang lenh `fz` (lay_ve.sh them vao ~/.bashrc). O lenh: Download/FairyZero/o_lenh.
D=$HOME/storage/downloads/FairyZero/o_lenh
TAI=$HOME/storage/downloads/FairyZero
S=${S:-fz}

# Doc tep o: bo BOM va \r ma trinh sua tep tren dien thoai co the them vao.
doc() { sed 's/^\xEF\xBB\xBF//; s/\r$//' "$@"; }

# Chay mot o tren may Colab: ghep o cau hinh 00 vao dau roi gui cho colab exec.
chay() { doc "$D/00_cau_hinh.py" "$1" | colab exec -s "$S"; }

tieu_de() { doc "$1" | sed -n '1s/^# *//p'; }

dung() { echo; read -rp "--- Enter để về menu ---" _; }

while true; do
  clear
  gen=$(doc "$D/00_cau_hinh.py" 2>/dev/null | sed -n 's/^GEN_CURRENT *= *\([0-9]*\).*/\1/p')
  echo "======== FairyZero trên Colab ========"
  echo " Phiên: $S   ·   Đời hiện tại: ${gen:-?}"
  echo " Ô lệnh: Download/FairyZero/o_lenh"
  echo "--------------------------------------"
  files=()
  for f in "$D"/[0-9]*_*.py; do
    [ -f "$f" ] || continue
    id=$(basename "$f"); id=${id%%_*}
    [ "$id" = 00 ] && continue
    files+=("$f")
    printf " %-4s %s\n" "$id" "$(tieu_de "$f")"
  done
  [ ${#files[@]} -eq 0 ] && echo " (chưa có ô nào -- chạy: bash ~/lay_ve.sh)"
  echo "--------------------------------------"
  echo " m    Xin máy T4"
  echo " k    Xem máy đang giữ"
  echo " d    Tải tệp Colab -> điện thoại"
  echo " u    Tải tệp điện thoại -> Colab"
  echo " t    Trả máy (XOÁ /content)"
  echo " q    Thoát"
  echo "--------------------------------------"
  echo " Nhiều ô liền nhau: gõ cách nhau, vd: 01 02"
  read -rp "Chọn: " -a chon
  [ ${#chon[@]} -eq 0 ] && continue

  case "${chon[0]}" in
  q|Q) exit 0 ;;
  m|M) colab new -s "$S" --gpu T4; colab status -s "$S"; dung; continue ;;
  k|K) colab sessions; colab status -s "$S"; dung; continue ;;
  t|T)
    read -rp "Trả máy '$S'? Mọi tệp trên Colab (/content) sẽ MẤT. Gõ 'co' để trả: " x
    [ "$x" = co ] && colab stop -s "$S"
    dung; continue ;;
  d|D)
    echo "Ví dụ: /content/games_gen${gen:-0}.zip   /content/gen$(( ${gen:-0} + 1 )).onnx"
    read -rp "Đường dẫn tệp trên Colab: " r
    [ -n "$r" ] && colab download -s "$S" "$r" "$TAI/$(basename "$r")" && echo "-> Download/FairyZero/$(basename "$r")"
    dung; continue ;;
  u|U)
    mapfile -t ds < <(find "$TAI" -maxdepth 1 -type f | sort)
    [ ${#ds[@]} -eq 0 ] && { echo "Download/FairyZero chưa có tệp nào."; dung; continue; }
    for i in "${!ds[@]}"; do printf " %2d  %s\n" $((i + 1)) "$(basename "${ds[$i]}")"; done
    read -rp "Số thứ tự tệp: " i
    if [[ "$i" =~ ^[0-9]+$ ]] && [ "$i" -ge 1 ] && [ "$i" -le ${#ds[@]} ]; then
      f=${ds[$((i - 1))]}
      colab upload -s "$S" "$f" "/content/$(basename "$f")"
    fi
    dung; continue ;;
  esac

  for id in "${chon[@]}"; do
    f=$(ls "$D"/"$id"_*.py 2>/dev/null | head -1)
    if [ -z "$f" ]; then echo "[!] Không có ô $id"; continue; fi
    echo
    echo "====== Ô $id: $(tieu_de "$f") ======"
    chay "$f"
  done
  dung
done
