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
# Goi chay tren Colab (lc0 + ma Python + script Colab), dang bang co_vua/scripts/dong_goi.py --dang.
curl -fsSL "https://github.com/phuc11731510/chess_variant_engine/releases/download/co_vua/goi.tar.gz" -o "$GOC/goi.tar.gz.moi"
mv "$GOC/goi.tar.gz.moi" "$GOC/goi.tar.gz"
echo "Da cai cvt vao $BIN (scripts o $CV_DIR/dieu_phoi)."
echo "Da tai goi chay tren Colab: $(tar -xzOf "$GOC/goi.tar.gz" goi_thong_tin.txt | tr '\n' ' ')"
echo "Du lieu va log: Download/CoVua/truyen_thong"
echo "Chay:  cvt @<tai khoan>    Dung mem:  cvt dung    Xem:  cvt xem"
