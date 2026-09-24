#!/data/data/com.termux/files/usr/bin/bash
# lay_ve.sh -- tai cac o lenh FairyZero ve ~/fz tren Termux va them lenh `o` vao ~/.bashrc.
#   bash lay_ve.sh        # chi tai o nao CHUA co (khong ghi de o ban da sua)
#   bash lay_ve.sh -f     # tai lai TAT CA, GHI DE o ban da sua
set -euo pipefail

URL=https://raw.githubusercontent.com/phuc11731510/chess_variant_engine/main/custom_engine/scripts/colab_cells
CELLS="00_cau_hinh 01_kiem_gpu 02_khoi_dong 02b_bien_dich 03_tao_gen0 04_sinh_du_lieu
05_xem_log 06_dong_goi 07_huan_luyen 08_arena 09_dung_viec_nen"

mkdir -p ~/fz
for c in $CELLS; do
  f=~/fz/$c.py
  if [ -f "$f" ] && [ "${1:-}" != "-f" ]; then
    echo "[giu nguyen] $f"
  else
    curl -fsSL -o "$f" "$URL/$c.py" && echo "[tai]        $f"
  fi
done

# o <so>: chay o ~/fz/<so>_*.py tren may Colab, sau khi ghep o cau hinh 00 vao dau.
if ! grep -q '^o() ' ~/.bashrc 2>/dev/null; then
  cat >> ~/.bashrc <<'EOF'
o() { cat ~/fz/00_cau_hinh.py ~/fz/"$1"_*.py | colab exec -s "${S:-fz}"; }
EOF
  echo "[them] lenh o vao ~/.bashrc -- chay: source ~/.bashrc (hoac mo lai Termux)"
fi
