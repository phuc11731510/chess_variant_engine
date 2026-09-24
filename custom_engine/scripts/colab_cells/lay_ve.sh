#!/data/data/com.termux/files/usr/bin/bash
# lay_ve.sh -- tai cac o lenh FairyZero ve thu muc CHUNG cua dien thoai
# (Download/FairyZero/o_lenh, mo/sua duoc bang MT Manager), tai menu ve ~/fz_menu.sh,
# va them hai lenh vao ~/.bashrc:  fz (mo menu)  va  o <so> [<so> ...] (chay o thang).
#   bash lay_ve.sh        # chi tai o nao CHUA co (khong ghi de o ban da sua)
#   bash lay_ve.sh -f     # tai lai TAT CA o, GHI DE o ban da sua
#   bash lay_ve.sh 05 07  # tai lai RIENG o 05 va 07 (ghi de hai o do), giu nguyen cac o khac
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
# Co tai lai o $c khong: -f = moi o; danh sach so = chi cac o do.
ghi_de() {
  local a
  for a in "$@"; do [ "$a" = -f ] || [ "$a" = "${c%%_*}" ] && return 0; done
  return 1
}
for c in $CELLS; do
  f=$DIR/$c.py
  if [ -f "$f" ] && ! ghi_de "$@"; then
    echo "[giu nguyen] $f"
  else
    curl -fsSL -o "$f" "$URL/$c.py" && echo "[tai]        $f"
  fi
done
# Menu + phan chay tren may Colab khong phai thu ban sua -> luon lay ban moi.
curl -fsSL -o ~/fz_menu.sh "$URL/menu.sh" && echo "[tai]        ~/fz_menu.sh"
curl -fsSL -o ~/fz_may.py "$URL/fz_may.py" && echo "[tai]        ~/fz_may.py"

# Thay hai dong cu (neu co) trong ~/.bashrc.
#   fz            : mo menu.
#   o 04 [05 ...] : chay o 04 (roi 05 ...) nhu khi chon trong menu, khong hien menu.
touch ~/.bashrc
sed -i '/^o() /d; /^fz() /d' ~/.bashrc
cat >> ~/.bashrc <<'EOF'
fz() { bash ~/fz_menu.sh; }
o() { bash ~/fz_menu.sh "$@"; }
EOF

# Xem log truc tiep can ssh + khoa ca nhan (colab ssh dua khoa len may Colab).
command -v ssh >/dev/null || pkg install -y openssh
[ -f ~/.ssh/id_ed25519 ] || ssh-keygen -t ed25519 -N "" -q -f ~/.ssh/id_ed25519
echo "[xong] chay: source ~/.bashrc   roi go:  fz"
