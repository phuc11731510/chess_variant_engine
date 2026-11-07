#!/data/data/com.termux/files/usr/bin/bash
# cv_lay_ve.sh -- (chep tu lay_ve.sh cua engine bien the) tai cac o lenh co vua ve thu muc CHUNG cua dien thoai
# (Download/CoVua/o_lenh, mo/sua duoc bang MT Manager), tai menu + vong lap + tro ly Python ve ~/cv,
# va them lenh `cv` vao ~/.bashrc (mo menu; `cv 04 05` = chay thang o 04 roi 05).
#   bash cv_lay_ve.sh        # chi tai o nao CHUA co (khong ghi de o ban da sua)
#   bash cv_lay_ve.sh -f     # tai lai TAT CA o, GHI DE o ban da sua
#   bash cv_lay_ve.sh 05 07  # tai lai RIENG o 05 va 07 (ghi de hai o do), giu nguyen cac o khac
# Lan dau:  curl -fLO https://raw.githubusercontent.com/phuc11731510/chess_variant_engine/main/co_vua/scripts/cv/cv_lay_ve.sh && bash cv_lay_ve.sh
# Khong dung toi ~/fz_* va lenh fz / o cua engine bien the; tai khoan Colab (~/.fz_tk) thi dung chung.
set -euo pipefail

# raw.githubusercontent.com luu dem tep theo ten nhanh (main) ~5 phut: tai theo ma commit moi nhat cua main
# (hoi GitHub API) thi luon moi; API loi (gioi han 60 lan/gio) thi dung main.
REPO=phuc11731510/chess_variant_engine
SHA=$(curl -fsSL -H 'Accept: application/vnd.github.sha' "https://api.github.com/repos/$REPO/commits/main" 2>/dev/null) || SHA=
[[ "$SHA" =~ ^[0-9a-f]{40}$ ]] || SHA=main
URL=https://raw.githubusercontent.com/$REPO/$SHA/co_vua/scripts/cv
CELLS="00_cau_hinh 01_kiem_gpu 02_khoi_dong 02c_chuan_bi_huan_luyen 03_tao_gen0 04_sinh_du_lieu 05_xem_log
06_dong_goi 07_huan_luyen 08_arena 09_dung_viec_nen 09b_dung_mem"
DIR=$HOME/storage/downloads/CoVua/o_lenh
CVD=$HOME/cv

# Tu cap nhat: lay ban moi nhat cua CHINH tep nay truoc, roi chay lai bang ban moi.
if [ -z "${CV_LAY_VE_MOI:-}" ]; then
  moi=$(mktemp)
  if curl -fsSL -o "$moi" "$URL/cv_lay_ve.sh" && ! cmp -s "$moi" "$0"; then
    cp "$moi" "$0" && rm -f "$moi"
    echo "[cap nhat]   $0 -> ban moi, chay lai"
    CV_LAY_VE_MOI=1 exec bash "$0" "$@"
  fi
  rm -f "$moi"
fi

if [ ! -d "$HOME/storage/downloads" ]; then
  echo "[loi] Termux chua co quyen bo nho: chay termux-setup-storage, chon Cho phep, roi chay lai." >&2
  exit 1
fi
mkdir -p "$DIR" "$CVD"
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
    curl -fsSL -o "$f" "$URL/o_lenh/$c.py" && echo "[tai]        $f"
  fi
done
# Menu, vong lap, tro ly Python khong phai thu ban sua -> luon lay ban moi.
for t in cv_menu.sh cv_tu_dong.sh cv_tu_dong.py cay.py fz_may.py fz_han_muc.py fz_nhan_may.py fz_trung_tk.py fz_giu_may.py fz_colab.py fz_chuyen.py; do
  curl -fsSL -o "$CVD/$t" "$URL/$t" && echo "[tai]        ~/cv/$t"
done

# Lenh cv (thay dong cu neu co).
touch ~/.bashrc
sed -i '/^cv() /d' ~/.bashrc
cat >> ~/.bashrc <<'EOF'
cv() { bash ~/cv/cv_menu.sh "$@"; }
EOF

# Cay tro choi (cay.py) chay tren may nay, can numpy cho python3.
python3 -c "import numpy" 2>/dev/null || { command -v pkg >/dev/null && pkg install -y python-numpy; } ||
  echo "[!] thieu numpy cho python3: Termux pkg install python-numpy / WSL apt install python3-numpy"
# Xem log truc tiep can ssh + khoa ca nhan (colab ssh dua khoa len may Colab).
command -v ssh >/dev/null || { command -v pkg >/dev/null && pkg install -y openssh; } || echo "[!] thieu ssh: cai bang trinh quan ly goi cua may (WSL: apt install openssh)"
# Thanh tien do (%, toc do, con bao lau) khi tai len / tai ve qua menu.
command -v pv >/dev/null || { command -v pkg >/dev/null && pkg install -y pv; } || echo "[!] thieu pv: cai bang trinh quan ly goi cua may (WSL: apt install pv)"
[ -f ~/.ssh/id_ed25519 ] || ssh-keygen -t ed25519 -N "" -q -f ~/.ssh/id_ed25519
echo "[xong] ban ${SHA:0:7}. Chay: source ~/.bashrc   roi go:  cv"
