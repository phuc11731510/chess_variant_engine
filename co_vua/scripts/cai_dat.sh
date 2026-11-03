#!/usr/bin/env bash
# Cai (hoac cap nhat) lenh cvt cua du an co vua tren Termux. Chay lai bat cu luc nao de lay ban moi nhat:
#   curl -fsSL https://raw.githubusercontent.com/phuc11731510/chess_variant_engine/main/co_vua/scripts/cai_dat.sh | bash
# Can san (giong engine co bien the): python, openssh, Colab CLI da dang nhap (tai khoan chinh va/hoac ~/.fz_tk/<ten>),
# termux-setup-storage da chay (de ghi vao Download/CoVua).
set -euo pipefail
RAW=https://raw.githubusercontent.com/phuc11731510/chess_variant_engine/main/co_vua/scripts
CV_DIR="$HOME/co_vua"
mkdir -p "$CV_DIR/dieu_phoi"
for f in colab_may.py proxy_ssh.py truyen_thong.py xem.py cvt; do
  curl -fsSL "$RAW/dieu_phoi/$f" -o "$CV_DIR/dieu_phoi/$f.moi"
  mv "$CV_DIR/dieu_phoi/$f.moi" "$CV_DIR/dieu_phoi/$f"
done
chmod +x "$CV_DIR/dieu_phoi/cvt"
BIN="${PREFIX:-$HOME/.local}/bin"
mkdir -p "$BIN"
ln -sf "$CV_DIR/dieu_phoi/cvt" "$BIN/cvt"
GOC="$HOME/storage/downloads/CoVua/truyen_thong"
mkdir -p "$GOC"
echo "Da cai cvt vao $BIN (scripts o $CV_DIR/dieu_phoi)."
echo "Du lieu va log: Download/CoVua/truyen_thong. Can co tep goi.tar.gz trong thu muc do truoc khi chay."
[ -f "$GOC/goi.tar.gz" ] || echo "  -> CHUA co goi.tar.gz trong $GOC"
echo "Chay:  cvt @<tai khoan>    Dung mem:  cvt dung    Xem:  cvt xem"
