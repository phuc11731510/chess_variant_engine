#!/bin/bash
# chay_thu.sh -- THU VONG LAP LIEN TUC bang may Colab GIA (chay trong WSL / Linux, quyen root: dung unshare -m).
#
# Chay DUNG ma that: menu.sh (muc w), fz_tu_dong.sh, fz_lien_tuc.sh, fz_tu_dong.py, fz_may.py (phia may), python/goi_van.py, o 04l that
# (sinh_the_khoi_dau.py that). Chi thay: Colab CLI (fz_colab.py gia), ssh (chay lenh tai cho trong khong gian ten cua cua so = "may" voi
# /content rieng), gh (Release = thu muc), engine (chep van mau that, toc do FAKE_RATE), o 02 / 02c / 07 / 08 (gia, nhanh).
# Hai cua so (hai tai khoan acc1, acc2) cung chay nhu hai cua so Termux that (chung HOME, chung ~/.fz_tk).
#
#   bash chay_thu.sh [co ban]      co ban: co_ban (mac dinh) | arena | mat_may | xin_treo | nap_lai | len_loi | dung_cu | xin_muon
#     nap_lai: giua luc chay, ~/fz_lien_tuc.sh tren "dien thoai" bi THAY (nguyen tu, nhu lay_ve / Claude cai): cua so phai tu nap lai ham moi
#     (khong dong den engine / may dang chay, khong mat van), roi mot ban moi co LOI CU PHAP phai bi tu choi ma van chay tiep.
#     xin_treo: lenh xin may cua acc1 BI TREO (het gio) roi may chu cap may muon cho phien khong ten -- tai hien loi 2026-11-24 do tren dien thoai
#     (`colab status` thoat ma 0 khi khong co phien -> vong lap tuong da co may -> bao "may da mat"; may mo coi an han muc).
#     len_loi: tai goi len may huan luyen bi Colab tu choi 429 "Already-active SSH session" (hong khi hoi danh sach goi, va hong giua luong tar):
#     phai cho roi thu lai, KHONG bo luot huan luyen (loi that 14:42 24/11 tren dien thoai).
#     dung_cu: con TEP DUNG CU (`fz dung` luc truoc, tao 10 phut truoc) trong luc mot cua so cu con song: cua so MOI mo phai bo qua no va chay binh thuong
#     (loi that 15:10 24/11: cua so moi tu dung ngay sau "Enter = bat dau").
#     xin_muon: nhu xin_treo nhung may chu cap may CHAM hon khoang cho cua xin_may (cap sau 16 giay, khoang cho 4 + 6 giay): quet muon chay nen (menu.sh
#     xin_quet_muon) phai tra no, khong de tai khoan giu mot T4 "[?]" (loi that 15:13 24/11: nguoi dung mo fz thay tai khoan van con T4).
#   MENU_SRC=<tep menu.sh khac>  thu voi ban menu.sh khac (vd ban cu lay tu git de THAY loi tai hien)
# Ket qua: in PASS / FAIL tung kiem tra; log tung cua so o /tmp/fc/log_w<k>.txt.
set -u
REPO=$(cd "$(dirname "$0")/../.." && pwd)            # .../custom_engine
SC=$REPO/scripts/colab_cells
GIA=$REPO/scripts/thu_lien_tuc/gia
W=/tmp/fc
H=/tmp/fakehome
KB=${1:-co_ban}
GEN0=5
export FAKE_SRC=$REPO FAKE_GIA=$GIA FAKE_RELEASE=$W/release FAKE_QUOTA_DIR=$W/quota FAKE_GEN0=$GEN0
export FAKE_SCALE=${FAKE_SCALE:-200} FAKE_RATE=${FAKE_RATE:-5} FAKE_TRAIN_S=${FAKE_TRAIN_S:-5}
export LT_PACK_VAN=${LT_PACK_VAN:-8}

chmod +x "$GIA"/bin/* "$GIA"/may/run.sh 2>/dev/null     # git tren Windows khong giu quyen chay
pkill -f "fz_menu.sh lien_tuc" 2>/dev/null
sleep 1
rm -rf "$W" "$H"
mkdir -p "$W/w1" "$W/w2" "$W/release" "$W/quota" "$H/storage/downloads/FairyZero/o_lenh" "$H/.fz_tk"
: > "$W/ledger"
# Release NN_Model gia: da co .pt cua cac doi tu 0 toi GEN0 (Release that luon co tep; danh sach rong se bi coi la loi mang)
for i in $(seq 0 $GEN0); do head -c 64 /dev/urandom > "$W/release/gen$i.pt"; done
TAI=$H/storage/downloads/FairyZero
O=$TAI/o_lenh
# --- "dien thoai": menu + tep phia dien thoai that, tep gia, o lenh ---
cp "${MENU_SRC:-$SC/menu.sh}" "$H/fz_menu.sh"
for f in fz_tu_dong.sh fz_lien_tuc.sh fz_tu_dong.py fz_may.py; do cp "$SC/$f" "$H/$f"; done
[ -n "${LT_SRC:-}" ] && cp "$LT_SRC" "$H/fz_lien_tuc.sh"        # thu voi ban fz_lien_tuc.sh khac (vd ban cu lay tu git de THAY loi tai hien)
cp "$GIA"/home/*.py "$H/"
cp "$SC/00_cau_hinh.py" "$O/"
sed -i "s/^GEN_CURRENT = .*/GEN_CURRENT = $GEN0/" "$O/00_cau_hinh.py"
cp "$SC"/04l_*.py "$O/"
cp "$GIA"/cells/*.py "$O/"
NOW=$(date +%s)
for a in acc1 acc2; do
  mkdir -p "$H/.fz_tk/$a/.config/colab-cli"
  echo '{}' > "$H/.fz_tk/$a/.config/colab-cli/token.json"
  echo "{\"luc\": $NOW, \"con\": 4500}" > "$H/.fz_tk/$a/.config/colab-cli/fz_han_muc.json"
  echo 20000 > "$W/quota/$a"
done
[ "$KB" = mat_may ] && echo 20000 > "$W/quota/acc1"
[ "$KB" = len_loi ] && { echo 2 > "$W/loi429"; echo 1 > "$W/loi429_tar"; }
[ "$KB" = xin_muon ] && echo 1 > "$W/hang_acc1"
[ "$KB" = xin_treo ] && echo 1 > "$W/hang_acc1"          # lan xin dau tien cua acc1 bi treo (cua so chuyen sang tai khoan khac ngay trong cung luot)

if [ "$KB" = dung_cu ]; then
  # Mot "cua so cu" con song (tien trinh co chu menu.sh trong dong lenh + tep trang thai lt=1) va tep dung_tay tao tu 10 phut truoc.
  mkdir -p "$H/.fz_tk/.tu_dong"
  bash -c 'sleep 700; :' fz_menu.sh &      # dau ':' de bash khong thay the chinh no bang sleep (se mat chu menu.sh trong dong lenh)
  CU=$!
  echo "lt=1 gen=$GEN0 buoc=sinh van=0" > "$H/.fz_tk/.tu_dong/w_$CU"
  : > "$H/.fz_tk/.tu_dong/dung_tay"
  touch -d '10 minutes ago' "$H/.fz_tk/.tu_dong/dung_tay"
fi
TRA_LOI=$'30\n200000\n\n-\n\n'          # so van moi / luot, so the cua so, chua phut (Enter), arena tat, Enter = bat dau
[ "$KB" = arena ] && TRA_LOI=$'30\n200000\n\n5 7 9\n100\n\n'   # arena: day doi 5 7 9 (doi 7 dau doi 5, doi 9 dau doi 7), 100 van
mk_cua_so() {   # $1 = k (1, 2)
  local k=$1
  unshare -m bash -c "
    mount --bind $W/w$k /content
    export HOME=$H PATH=$GIA/bin:\$PATH TERM=dumb NO_COLOR=1 FZ_KHONG_NHAT_KY=1 PYTHONPATH=$GIA/pylib FAKE_DIR=$W
    [ "$KB" = xin_treo ] && export FZ_XIN_TO=4 FZ_XIN_CHO=8 FAKE_GRANT_LATE=3
    [ "$KB" = xin_muon ] && export FZ_XIN_TO=4 FZ_XIN_CHO=6 FZ_XIN_CHO2=10 FAKE_GRANT_LATE=16
    [ "$KB" = nap_lai ] && export LT_NAP_GIAY=8
    [ "$KB" = len_loi ] && export LT_CHO_429=2
    cd $H
    exec bash $H/fz_menu.sh lien_tuc
  " <<<"$TRA_LOI" > "$W/log_w$k.txt" 2>&1 &
  echo $! > "$W/pid_w$k"
}
echo "== kich ban: $KB =="
mk_cua_so 1
sleep 3
mk_cua_so 2
if [ "$KB" = nap_lai ]; then
  # Thay ~/fz_lien_tuc.sh NGUYEN TU (ghi tep moi roi mv: nhu lay_ve / cai qua ssh) khi cac cua so dang chay.
  thay() { local f=$H/fz_lien_tuc.sh; "$@" < "$f" > "$f.moi" && mv "$f.moi" "$f"; }
  (
    sleep 25
    thay sed 's/td_in "gửi $n gói (/td_in "gửi $n gói [v2] (/'
    sleep 45
    thay sed '$a\
lt_hong() {\
  echo "ham dang do, khong dong"'
  ) &
fi

# ---- cho cac moc ----
doc_gen() { sed -n 's/^GEN_CURRENT = \([0-9]*\).*/\1/p' "$O/00_cau_hinh.py" | head -1; }
dem_goi() { ls "$TAI"/goi/goi_*.zip 2>/dev/null | wc -l; }
T0=$(date +%s)
muc_tieu_gen=$((GEN0 + 2))
[ "$KB" = arena ] && muc_tieu_gen=$((GEN0 + 4))
[ "$KB" = nap_lai ] && muc_tieu_gen=$((GEN0 + 4))
while :; do
  g=$(doc_gen)
  [ "${g:-0}" -ge "$muc_tieu_gen" ] && break
  [ $(( $(date +%s) - T0 )) -gt ${TIMEOUT:-420} ] && { echo "[!] het gio cho GEN_CURRENT >= $muc_tieu_gen (hien $g)"; break; }
  if [ "$KB" = mat_may ] && [ -d "$W/w1" ] && [ ! -e "$W/da_mat" ] && [ "$(dem_goi)" -ge 3 ]; then
    touch "$W/w1/.mat"; touch "$W/da_mat"; echo "(da danh dau MAT may cua cua so 1 luc $(( $(date +%s) - T0 )) giay)"
  fi
  sleep 3
done
echo "GEN_CURRENT = $(doc_gen) sau $(( $(date +%s) - T0 )) giay; $(dem_goi) goi"
# ---- dung mem ca vong lap ----
: > "$H/.fz_tk/.tu_dong/dung_tay"
for _ in $(seq 120); do
  p1=$(cat "$W/pid_w1" 2>/dev/null); p2=$(cat "$W/pid_w2" 2>/dev/null)
  { [ -d /proc/$p1 ] || [ -d /proc/$p2 ]; } || break
  sleep 2
done
sleep 1
[ -n "${CU:-}" ] && kill "$CU" 2>/dev/null
echo "== log cuoi cua so 1 =="; tail -n 25 "$W/log_w1.txt"
echo "== log cuoi cua so 2 =="; tail -n 25 "$W/log_w2.txt"
python3 "$(dirname "$0")/kiem.py" "$KB" "$W" "$TAI" "$H" "$GEN0"
