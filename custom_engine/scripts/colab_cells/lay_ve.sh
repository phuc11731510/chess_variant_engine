#!/data/data/com.termux/files/usr/bin/bash
# lay_ve.sh -- tai cac o lenh FairyZero ve thu muc CHUNG cua dien thoai
# (Download/FairyZero/o_lenh, mo/sua duoc bang MT Manager), tai menu ve ~/fz_menu.sh,
# va them hai lenh vao ~/.bashrc:  fz (mo menu)  va  o <so> [<so> ...] (chay o thang).
#   bash lay_ve.sh        # chi tai o nao CHUA co (khong ghi de o ban da sua)
#   bash lay_ve.sh -f     # tai lai TAT CA o, GHI DE o ban da sua
#   bash lay_ve.sh 05 07  # tai lai RIENG o 05 va 07 (ghi de hai o do), giu nguyen cac o khac
set -euo pipefail

# raw.githubusercontent.com luu dem tep theo ten nhanh (main) ~5 phut: vua day ban moi len ma tai
# ngay thi van nhan ban CU. Tai theo ma commit moi nhat cua main (hoi GitHub API) thi luon moi;
# API loi (gioi han 60 lan/gio) thi dung main.
REPO=phuc11731510/chess_variant_engine
SHA=$(curl -fsSL -H 'Accept: application/vnd.github.sha' "https://api.github.com/repos/$REPO/commits/main" 2>/dev/null) || SHA=
[[ "$SHA" =~ ^[0-9a-f]{40}$ ]] || SHA=main
URL=https://raw.githubusercontent.com/$REPO/$SHA/custom_engine/scripts/colab_cells
CELLS="00_cau_hinh 01_kiem_gpu 02_khoi_dong 02b_bien_dich 03_tao_gen0 04_sinh_du_lieu
05_xem_log 06_dong_goi 07_huan_luyen 08_arena 09_dung_viec_nen 09b_dung_mem"
DIR=$HOME/storage/downloads/FairyZero/o_lenh

# Tu cap nhat: lay ban moi nhat cua CHINH tep nay truoc, roi chay lai bang ban moi -- ban cu
# khong biet cac tep moi them sau no (vd fz_may.py).
if [ -z "${FZ_LAY_VE_MOI:-}" ]; then
  moi=$(mktemp)
  if curl -fsSL -o "$moi" "$URL/lay_ve.sh" && ! cmp -s "$moi" "$0"; then
    cp "$moi" "$0" && rm -f "$moi"
    echo "[cap nhat]   $0 -> ban moi, chay lai"
    FZ_LAY_VE_MOI=1 exec bash "$0" "$@"
  fi
  rm -f "$moi"
fi

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
curl -fsSL -o ~/fz_han_muc.py "$URL/fz_han_muc.py" && echo "[tai]        ~/fz_han_muc.py"
curl -fsSL -o ~/fz_nhan_may.py "$URL/fz_nhan_may.py" && echo "[tai]        ~/fz_nhan_may.py"
curl -fsSL -o ~/fz_giu_may.py "$URL/fz_giu_may.py" && echo "[tai]        ~/fz_giu_may.py"
curl -fsSL -o ~/fz_tu_dong.sh "$URL/fz_tu_dong.sh" && echo "[tai]        ~/fz_tu_dong.sh"
curl -fsSL -o ~/fz_tu_dong.py "$URL/fz_tu_dong.py" && echo "[tai]        ~/fz_tu_dong.py"

# Thay hai dong cu (neu co) trong ~/.bashrc.
#   fz            : mo menu.
#   o 04 [05 ...] : chay o 04 (roi 05 ...) nhu khi chon trong menu, khong hien menu.
touch ~/.bashrc
sed -i '/^o() /d; /^fz() /d' ~/.bashrc
cat >> ~/.bashrc <<'EOF'
fz() { bash ~/fz_menu.sh "$@"; }
o() { bash ~/fz_menu.sh "$@"; }
EOF

# Xem log truc tiep can ssh + khoa ca nhan (colab ssh dua khoa len may Colab).
command -v ssh >/dev/null || pkg install -y openssh
# Thanh tien do (%, toc do, con bao lau) khi tai len / tai ve qua menu.
command -v pv >/dev/null || pkg install -y pv
[ -f ~/.ssh/id_ed25519 ] || ssh-keygen -t ed25519 -N "" -q -f ~/.ssh/id_ed25519

# Chia se tep tu ung dung khac (MT Manager, Files) -> Termux -> "Edit": Termux chep tep vao
# ~/downloads roi goi ~/bin/termux-file-editor <tep>. Moc nay tai tep do len /content (giu ten).
# Khong ghi de neu ban da co termux-file-editor cua rieng minh.
mkdir -p ~/bin
if [ ! -f ~/bin/termux-file-editor ] || grep -q 'fz: tai len Colab' ~/bin/termux-file-editor; then
  cat > ~/bin/termux-file-editor <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
# fz: tai len Colab -- tep chia se vao Termux ("Edit") duoc tai len /content cua phien Colab.
# Tai qua menu (ssh, chiu duoc tep lon), dung tai khoan ban chon.
f=$1; n=$(basename "$f")
echo "Tải '$n' lên Colab: /content/$n"
read -rp "Tài khoản (Enter = chính, hoặc tên tài khoản phụ; n = không tải): " x
if [ "$x" != n ]; then bash ~/fz_menu.sh ${x:+"@$x"} --tai-len "$f"; fi
read -rp "--- Enter để đóng ---" _
EOF
  chmod +x ~/bin/termux-file-editor
  echo "[them] chia se tep -> Termux -> Edit = tai len Colab (~/bin/termux-file-editor)"
else
  echo "[giu nguyen] ~/bin/termux-file-editor cua ban (khong them moc tai len Colab)"
fi
echo "[xong] ban ${SHA:0:7}. Chay: source ~/.bashrc   roi go:  fz"
