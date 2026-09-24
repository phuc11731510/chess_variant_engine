#!/data/data/com.termux/files/usr/bin/bash
# lay_ve.sh -- tai cac o lenh FairyZero ve thu muc CHUNG cua dien thoai
# (Download/FairyZero/o_lenh, mo/sua duoc bang MT Manager), tai menu ve ~/fz_menu.sh,
# va them hai lenh vao ~/.bashrc:  fz (mo menu)  va  o <so> [<so> ...] (chay o thang).
#   bash lay_ve.sh        # chi tai o nao CHUA co (khong ghi de o ban da sua)
#   bash lay_ve.sh -f     # tai lai TAT CA o, GHI DE o ban da sua
set -euo pipefail

URL=https://raw.githubusercontent.com/phuc11731510/chess_variant_engine/main/custom_engine/scripts/colab_cells
CELLS="00_cau_hinh 01_kiem_gpu 02_khoi_dong 02b_bien_dich 03_tao_gen0 04_sinh_du_lieu
05_xem_log 06_dong_goi 07_huan_luyen 08_arena 09_dung_viec_nen"
DIR=$HOME/storage/downloads/FairyZero/o_lenh

if [ ! -d "$HOME/storage/downloads" ]; then
  echo "[loi] Termux chua co quyen bo nho: chay termux-setup-storage, chon Cho phep, roi chay lai." >&2
  exit 1
fi
mkdir -p "$DIR"
for c in $CELLS; do
  f=$DIR/$c.py
  if [ -f "$f" ] && [ "${1:-}" != "-f" ]; then
    echo "[giu nguyen] $f"
  else
    curl -fsSL -o "$f" "$URL/$c.py" && echo "[tai]        $f"
  fi
done
# Menu khong phai thu ban sua -> luon lay ban moi.
curl -fsSL -o ~/fz_menu.sh "$URL/menu.sh" && echo "[tai]        ~/fz_menu.sh"

# Thay hai dong cu (neu co) trong ~/.bashrc.
#   fz            : mo menu.
#   o 04 [05 ...] : chay o 04 (roi 05 ...) tren may Colab, sau khi ghep o cau hinh 00 vao dau;
#                   sed bo BOM va \r ma trinh sua tep tren dien thoai co the them.
touch ~/.bashrc
sed -i '/^o() /d; /^fz() /d' ~/.bashrc
cat >> ~/.bashrc <<'EOF'
fz() { bash ~/fz_menu.sh; }
o() { local d=~/storage/downloads/FairyZero/o_lenh i; for i in "$@"; do echo "====== o $i ======"; cat "$d"/00_cau_hinh.py "$d"/"$i"_*.py | sed 's/^\xEF\xBB\xBF//; s/\r$//' | colab exec -s "${S:-fz}"; done; }
EOF
echo "[xong] chay: source ~/.bashrc   roi go:  fz"
