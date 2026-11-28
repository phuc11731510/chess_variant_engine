# fz_nap_som.sh -- NAP SOM han muc (menu fz -> n, `fz nap_som [phut]`): chay o MOT cua so Termux RIENG, song song vong lap (v / w).
# menu.sh SOURCE ~/fz_tu_dong.sh truoc roi tep nay, va dung lai ham cua chung (xin_may, chup_han_muc, tra_mot, cua_so_khac, td_in, ...).
#
# Ly do (chu du an 2026-11-28): tai khoan da toi GIO NAP LAI ma chua ai dung thi han muc moi chua bat dau tinh: gio nap lai KE TIEP chi chay tu
# lan dung dau tien. Luc moi cua so vong lap deu dang co may, khong ai xin may nen tai khoan do nam yen, gio nap lai bi "dong bang". Cu moi
# <phut> phut (mac dinh 30), cua so nay tim cac tai khoan fz_tu_dong.py xep xep loai "nap_lai" (da qua gio nap lai, lan chup han muc gan nhat
# co TRUOC gio do), xin T4 o tung tai khoan, chup han muc (gio nap lai moi + con lai) roi tra may ngay. Moi lan ghi vao nhat ky vong lap
# ($TD/nhat_ky.txt) gio nap lai truoc / sau, de thay gio nap lai co doi that khong.
#
# Khong gianh may voi vong lap:
#   * chon tai khoan trong KHOA CHON CHUNG ($TD/.khoa_chon, nhu td_xin_mot_vong): kiem + danh dau cua so (ghi_cua_so) roi moi nha khoa, nen
#     cua so vong lap chon sau do thay tai khoan "dang mo o cua so khac" va bo qua;
#   * bo qua tai khoan: dang mo o cua so khac, vong lap dang giu may o do ($TD/may_<tk>), may WSL dang muon (khoa ngoai), dang co lan xin may
#     (xin_dang_<tk>), dang giu phien may bat ky;
#   * co cua so vong lap dang CHO MAY (buoc=xin): luot nay khong lam gi -- cua so do se tu xin tai khoan "nap_lai" truoc (fz_tu_dong.py xep).
# Phien may ten rieng NS_S (khong trung ten may nao cua vong lap / menu). Ctrl+C: thoat (dang giu may thi tra truoc).

NS_S=fznap                # ten phien Colab cua lan xin tam
NS_CO_MAY=0               # dang giu may tam o tai khoan $TK
NS_PHUT_F=$TD/.nap_som_phut

ns_in() { td_in "[nạp sớm] $*"; }

# May tam cua tai khoan $TK (ten $NS_S): tra (tat giu may + colab stop), kiem lai; 0 = khong con.
ns_tra() {
  local x i
  for i in 1 2 3; do
    mapfile -t ds_ns < <(KHONG_HOI=1 COLAB_TO=60 colab sessions 2>/dev/null | grep "^\[$NS_S\]")
    [ ${#ds_ns[@]} -eq 0 ] && { NS_CO_MAY=0; return 0; }
    for x in "${ds_ns[@]}"; do tra_mot "$x" >/dev/null 2>&1; done
    sleep 3
  done
  ns_in "${M_DO}[!] chưa trả được máy tạm của $(ten_tk "$TK")${M_HET} -- trả ở menu t (tài khoản đó, máy $NS_S)"
  return 1
}
ns_thoat() {
  [ "$NS_CO_MAY" = 1 ] && ns_tra
  [ "$(cat "$TD/.khoa_chon/pid" 2>/dev/null)" = $$ ] && rm -rf "$TD/.khoa_chon"
  td_ranh
}

# Khoa chon chung (nhu td_khoa_chon, nhung Ctrl+C = bo luot, KHONG hien menu d / s / q cua vong lap: s o day se dung ca vong lap).
ns_khoa_chon() {
  local p t i=0
  while ! mkdir "$TD/.khoa_chon" 2>/dev/null; do
    p=$(cat "$TD/.khoa_chon/pid" 2>/dev/null)
    if [ -n "$p" ] && ! td_song "$p"; then rm -rf "$TD/.khoa_chon"; continue; fi
    t=$(stat -c %Y "$TD/.khoa_chon" 2>/dev/null || echo 0)
    if [ "$t" -gt 0 ] && [ $(( $(date +%s) - t )) -gt 1200 ]; then rm -rf "$TD/.khoa_chon"; continue; fi
    sleep 1; i=$((i + 1))
    [ $NGAT = 1 ] && return 1
    [ $((i % 60)) = 0 ] && echo "   chờ cửa sổ khác chọn tài khoản xong ($i giây)..."
  done
  echo $$ > "$TD/.khoa_chon/pid"
}

# Co cua so vong lap (con song) dang o buoc xin may?
ns_co_cua_so_cho_may() {
  local f pid
  for f in "$TD"/w_*; do
    [ -f "$f" ] || continue
    pid=${f##*/w_}; [[ "$pid" =~ ^[0-9]+$ ]] || continue
    td_song "$pid" && grep -qx 'buoc=xin' "$f" && return 0
  done
  return 1
}

# Mot tai khoan $1 (ten): kiem (trong khoa chon), xin T4, chup han muc, tra may. 0 = da nap som.
ns_nhan() {
  local ten=$1 tk truoc sau l ok=1
  tk=$(tim_tk "$ten") || return 1
  ns_khoa_chon || return 1
  if [ -n "$(cua_so_khac "$tk")" ]; then td_mo_khoa_chon; echo "   bỏ qua $ten: đang mở ở cửa sổ khác"; return 1; fi
  if [ -f "$TD/may_$ten" ]; then td_mo_khoa_chon; echo "   bỏ qua $ten: vòng lặp đang giữ máy ở đó"; return 1; fi
  if khoa_ngoai_con_han "$ten"; then td_mo_khoa_chon; echo "   bỏ qua $ten: máy khác (WSL) đang dùng"; return 1; fi
  l=$(cat "$TD/xin_dang_$ten" 2>/dev/null)
  if [[ "$l" =~ ^[0-9]+$ ]] && [ $(( $(date +%s) - l )) -lt 400 ]; then td_mo_khoa_chon; echo "   bỏ qua $ten: đang có lần xin máy"; return 1; fi
  S=$NS_S; dat_tk "$tk"
  if ! td_token_ok "$ten"; then td_ranh; td_mo_khoa_chon; return 1; fi
  if [ -n "$(KHONG_HOI=1 COLAB_TO=60 colab sessions 2>/dev/null | grep '^\[' | grep -v '^\[colab\]')" ]; then
    td_ranh; td_mo_khoa_chon; echo "   bỏ qua $ten: đang giữ máy"; return 1
  fi
  ghi_cua_so                      # tu day vong lap thay tai khoan nay "dang mo o cua so khac"
  td_mo_khoa_chon
  truoc=$(dong_han_muc "$tk")
  ns_in "xin T4 ở ${M_DAM}$ten${M_HET} (đã tới giờ nạp lại; trước: ${truoc:-?})"
  if xin_may T4 >/dev/null; then
    NS_CO_MAY=1
    wait $! 2>/dev/null            # lan chup nen cua xin_may (cung tep tam .tam: khong chup hai lan cung luc)
    chup_han_muc "$tk" 90          # dang giu may: may chu tra han muc + gio nap lai moi
    ns_tra && ok=0
    sau=$(dong_han_muc "$tk")
    ns_in "${M_XANH}đã nạp sớm $ten${M_HET} -- sau: ${sau:-?}"
  else
    ns_in "${M_VANG}không xin được T4 ở $ten${M_HET} (xin_may đã ghi nhận hạn mức nếu bị từ chối)"
  fi
  td_ranh
  return $ok
}

# Mot luot: moi tai khoan "nap_lai" theo fz_tu_dong.py xep.
ns_mot_luot() {
  local ds=() muc=() tk ten loai mo_ta n=0 cho=()
  declare -F quet_mo_coi_tat_ca >/dev/null && quet_mo_coi_tat_ca
  if ns_co_cua_so_cho_may; then
    echo "   có cửa sổ vòng lặp đang chờ máy: để nó tự xin tài khoản tới giờ nạp lại"; return 0
  fi
  td_ds_tk
  for tk in "${ds[@]}"; do
    tk_dang_nhap "$tk" && muc+=("$(ten_tk "$tk")|$(td_home "$tk")|$(cat "$TD/thu_$(ten_tk "$tk")" 2>/dev/null)")
  done
  while IFS=$'\t' read -r ten loai mo_ta; do
    [ "$loai" = nap_lai ] && cho+=("$ten")
  done < <(python ~/fz_tu_dong.py xep "${muc[@]}")
  if [ ${#cho[@]} -eq 0 ]; then echo "   không có tài khoản nào tới giờ nạp lại mà chưa dùng"; return 0; fi
  echo "   tới giờ nạp lại, chưa dùng: ${#cho[@]} tài khoản"
  for ten in "${cho[@]}"; do
    [ $NGAT = 1 ] && break
    ns_nhan "$ten" && n=$((n + 1))
  done
  [ $n -gt 0 ] && ns_in "lượt này nạp sớm $n / ${#cho[@]} tài khoản"
  return 0
}

ns_vong() {
  local phut=${1:-} x t
  [[ "$phut" =~ ^[0-9]+$ ]] && [ "$((10#$phut))" -gt 0 ] || phut=
  if [ -z "$phut" ]; then
    x=$(cat "$NS_PHUT_F" 2>/dev/null); [[ "$x" =~ ^[0-9]+$ ]] && [ "$((10#$x))" -gt 0 ] || x=30
    read -rp "Mấy phút xem một lần? (Enter = $((10#$x))): " phut || return
    [[ "$phut" =~ ^[0-9]+$ ]] && [ "$((10#$phut))" -gt 0 ] || phut=$x
  fi
  phut=$((10#$phut)); mkdir -p "$TD"; echo "$phut" > "$NS_PHUT_F"
  trap 'NGAT=1' INT
  trap 'ns_thoat' EXIT
  td_ranh
  ns_in "bắt đầu: mỗi $phut phút xem tài khoản tới giờ nạp lại (Ctrl+C = thoát)"
  NGAT=0
  while :; do
    echo "${M_LAM}[nạp sớm $(date +%H:%M)]${M_HET} xem tài khoản..."
    ns_mot_luot
    [ $NGAT = 1 ] && break
    echo "   lượt sau lúc $(date -d "@$(( $(date +%s) + phut * 60 ))" +%H:%M 2>/dev/null || echo "+$phut phút") (Ctrl+C = thoát)"
    for ((t = 0; t < phut * 60; t++)); do sleep 1; [ $NGAT = 1 ] && break; done
    [ $NGAT = 1 ] && break
  done
  ns_thoat
  trap - EXIT
  bat_ctrl_c
  ns_in "thoát"
}
