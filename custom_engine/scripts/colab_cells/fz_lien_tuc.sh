# fz_lien_tuc.sh -- VONG LAP LIEN TUC cua menu fz (muc w): engine choi MAI, huan luyen chay chong len tu dau, khong doi "het doi".
# menu.sh SOURCE ~/fz_tu_dong.sh truoc roi tep nay, va dung lai ham cua chung (xin_may, td_xin_mot_vong, td_tra, td_arena, td_len_github,
# tai_len, ...). Tep cu fz_tu_dong.sh (vong lap THEO DOI, muc v) KHONG doi: chon v hoac w, dung mo ca hai cung luc.
#
# MO HINH (chu du an chot 2026-11-24):
#   * Moi cua so Termux = mot may Colab (mot tai khoan) nhu cu. Moi may chay engine LIEN TUC (o 04l, mang hien tai = GEN_CURRENT cua o 00);
#     ngoai quota het / dung tay, may KHONG bi tra de cho nhau nua (truoc day 24,6% thoi gian la cho).
#   * DU LIEU di theo GOI NHO: cu moi LT_PACK_VAN van moi cua mot may, cua so gom cac van da xong (python/goi_van.py tren may, engine van chay)
#     thanh mot goi .zip, tai ve Download/FairyZero/goi/goi_<so thu tu>_n<mang>_<van>_<the>.zip (fz_tu_dong.py goi_nhan).
#   * HUAN LUYEN khi: khong co luot nao dang chay VA so van MOI >= td_muc (mac dinh 1000; bo dem KHONG tinh lai khi doi mang -- "cach Y"):
#     van moi = van trong cac goi co so thu tu > moc (moc = goi cuoi cung luc luot huan luyen truoc BAT DAU) + van dang cho gui o cac may.
#     Cua so nao thay du dieu kien va giu duoc khoa (mkdir) thi: yeu cau moi may gui goi NGAY (rao), dung engine cua chinh no (van do choi
#     not), lay CUA SO = cac goi moi nhat cho toi khi du LT_THE_F the (mac dinh 625.447), tai len may (chi goi may do chua co), chay o 07
#     (DATA = danh sach goi), tai mang moi ve, len GitHub, GEN_CURRENT + 1. Cac may khac van sinh du lieu SUOT thoi gian do.
#   * DOI MANG: cua so thay GEN_CURRENT doi -> tai mang moi len may (python/lay_mang.py tu Release, ~20 giay, engine cu van chay),
#     khoi dong engine MOI (04_<run moi>) ngay, roi dung mem engine cu (04_<run cu> choi not van do, 1,5-3,5 phut) -- hai tien trinh cung luc.
#     Van cua engine cu duoc gom o lan gui goi ke tiep (goi_van.py quet moi thu muc van tren may).
#   * ARENA: nhu cu (td_arena) nhung KHONG con la mot giai doan cua "doi": dung engine, gui goi, arena, roi sinh tiep bang mang moi.
# Tep trang thai tren dien thoai (~/.fz_tk/.tu_dong/):
#   .lt_moc  .lt_cua_so_the (>= 100000: cua so CO DINH; khong co = TU CANH)  .lt_dung_lai (4)  .lt_the_moi  .lt_lich_su_hl  .lt_yeu_cau_goi ("<so> <epoch>": yeu cau gui goi NGAY)  lt_hl/ (khoa huan luyen, pid)  .lt_hl_nghi (epoch)
#   w_<pid> co them: lt=1 van= da_goi= phuc_vu= (so yeu cau da phuc vu)

LT_GOI=$TAI/goi
LT_MOC_F=$TD/.lt_moc
LT_THE_F=$TD/.lt_cua_so_the
LT_YC_F=$TD/.lt_yeu_cau_goi
LT_HL=$TD/lt_hl
LT_NGHI_F=$TD/.lt_hl_nghi
LT_PACK_VAN=${LT_PACK_VAN:-50}     # moi may gui goi sau moi chung nay van moi
LT_THE_MAC_DINH=625447             # so the cua cua so huan luyen (chu du an chon 2026-11-24; tham so, chinh luc bat dau)
LT_CHO_DUOI=${LT_CHO_DUOI:-1}      # 1 = huan luyen chi bat dau sau khi engine cua may huan luyen choi not van do (RAM: engine ~4,2 GB + huan luyen)
LT_O=; LT_RUN=; LT_PID=; LT_NET=; LT_VAN=0; LT_DA_GOI=0; LT_SK=; LT_CRASH=0
LT_THE_HL=; LT_LEN_VONG=1          # cua so huan luyen da chot cho lan huan luyen dang chay (so the); so vong cua lan lt_len_goi gan nhat
LT_T_BD=0                          # luc (giay epoch) cua so nay BAT DAU chay vong lap (sau khi tra loi het cau hoi); 0 = chua biet

# LENH DUNG CHUNG (tep $TD_DUNG, do `fz dung` / Ctrl+C -> s tao) CHI co hieu luc voi cua so da chay TRUOC luc tao tep. Truoc day cua so MOI mo
# trong luc cua so cu con dang tat (vd cua so cu dang huan luyen, `fz dung` doi no xong) thay tep dung cu -> tu dung ngay sau khi tra loi
# "Enter = bat dau" (2026-11-24 15:10, cua so 17945). Tep cu hon luc cua so bat dau bi bo qua. Ghi de ham cung ten cua fz_tu_dong.sh (vong lap cu
# khong doi): menu.sh nap fz_tu_dong.sh roi moi nap tep nay.
lt_dung_hieu_luc() { [ -f "$TD_DUNG" ] && [ "$(stat -c %Y "$TD_DUNG" 2>/dev/null || echo 0)" -ge "${LT_T_BD:-0}" ]; }
td_dung_ca() { lt_dung_hieu_luc || [ -f "$TD_DUNG_RIENG" ]; }
lt_moc() { local n; n=$(cat "$LT_MOC_F" 2>/dev/null); [[ "$n" =~ ^[0-9]+$ ]] && echo $((10#$n)) || echo 0; }
# ---------------- Cua so huan luyen TU CANH + nguong T4 theo so the ----------------
# Moi the duoc dung lai bao nhieu lan = so the cua cua so / so the MOI cua mot lan huan luyen. Truoc day cua so la mot so co dinh (625.447), nen so lan dung
# lai troi theo do dai van va so cua so dang chay (do 24/11: 3,36 lan thay vi 4: van dai 174,5 the thay vi ~156, va moi luot nhan ~1.091 van thay vi 1000
# vi them cac van lot vao luc gom goi -- phan nay tang theo so cua so; it cua so thi so lan dung lai lai vuot 4). Nay: cua so = LT_DUNG_LAI (mac dinh 4)
# x TRUNG BINH so the moi cua LT_NHO lan huan luyen gan nhat (ghi o .lt_the_moi), kep trong [LT_THE_MIN, LT_THE_MAX]. Mot so >= 100000 trong .lt_cua_so_the
# (nhap tay o menu w) = cua so CO DINH, bo qua tu canh.
LT_DUNG_LAI_F=$TD/.lt_dung_lai          # muc tieu so lan dung lai moi the (mac dinh 4; cho phep le 3.5)
LT_THE_MOI_F=$TD/.lt_the_moi            # so the MOI cua cac lan huan luyen thanh cong gan nhat (moi dong mot so; giu 10 dong)
LT_LS_F=$TD/.lt_lich_su_hl              # "<giay gom+tai goi> <giay huan luyen+ve dien thoai> <so the cua so>" cua cac lan huan luyen SACH gan nhat (giu 10 dong)
LT_THE_MIN=${LT_THE_MIN:-300000}
LT_THE_MAX=${LT_THE_MAX:-1500000}
LT_NHO=${LT_NHO:-5}                     # so lan huan luyen gan nhat de lay trung binh the moi
LT_DU_PHUT=${LT_DU_PHUT:-6}             # nguong T4: phan vi 90% thoi gian cac lan gan nhat + so phut nay
LT_HL_PHUT_MIN=${LT_HL_PHUT_MIN:-15}    # ...nhung khong bao gio thap hon
LT_GOM_MAC_DINH=${LT_GOM_MAC_DINH:-240} # giay gom + tai goi khi chua co lich su (do 24/11: 3,4 den 3,8 phut)
LT_HL_GIAY_NGHIN_THE=${LT_HL_GIAY_NGHIN_THE:-9}   # giay huan luyen + ve dien thoai tren 10.000 the khi chua co lich su (do 24/11: ~570 giay / 632.000 the)
LT_GIA_TRI_DUNG_LAI=4
# So lan dung lai muc tieu, nhan 10 (4 -> 40; 3.5 -> 35).
lt_dung_lai10() {
  local r; r=$(cat "$LT_DUNG_LAI_F" 2>/dev/null)
  if [[ "$r" =~ ^([0-9]+)(\.([0-9]))?$ ]]; then echo $(( 10#${BASH_REMATCH[1]} * 10 + 10#${BASH_REMATCH[3]:-0} )); else echo $((LT_GIA_TRI_DUNG_LAI * 10)); fi
}
# Uoc tinh so the MOI cua lan huan luyen sap toi: trung binh LT_NHO lan gan nhat; chua du 3 lan thi lay so the TB moi van (tu ten cac goi gan nhat) x so van moi / luot.
lt_the_moi_uoc() {
  local -a his; local x s=0 v=0 t=0 f b
  mapfile -t his < <(tail -n "$LT_NHO" "$LT_THE_MOI_F" 2>/dev/null | grep -E '^[0-9]+$')
  if [ ${#his[@]} -ge 3 ]; then
    for x in "${his[@]}"; do s=$((s + 10#$x)); done
    echo $((s / ${#his[@]})); return
  fi
  for f in $(ls -r "$LT_GOI"/goi_*.zip 2>/dev/null | head -60); do
    b=${f##*/}
    [[ $b =~ ^goi_[0-9]+_n[0-9]+_([0-9]+)_([0-9]+)\.zip$ ]] || continue
    v=$((v + 10#${BASH_REMATCH[1]})); t=$((t + 10#${BASH_REMATCH[2]}))
  done
  if [ $v -gt 0 ]; then echo $((t * $(td_muc) / v)); else echo $((LT_THE_MAC_DINH / 4)); fi
}
# So the cua cua so huan luyen: co dinh (tep .lt_cua_so_the >= 100000) hoac tu canh.
lt_the() {
  local n the
  n=$(cat "$LT_THE_F" 2>/dev/null)
  if [[ "$n" =~ ^[0-9]+$ ]] && [ $((10#$n)) -ge 100000 ]; then echo $((10#$n)); return; fi
  the=$(( $(lt_the_moi_uoc) * $(lt_dung_lai10) / 10 ))
  [ $the -lt "$LT_THE_MIN" ] && the=$LT_THE_MIN
  [ $the -gt "$LT_THE_MAX" ] && the=$LT_THE_MAX
  echo $the
}
# Giay T4 can con khi lay khoa huan luyen voi cua so $1 the: phan vi 90% (hang gan nhat) cua [giay gom + giay huan luyen quy theo $1 the] qua cac lan sach gan nhat
# (huan luyen ti le voi so the), cong LT_DU_PHUT phut; chua du 3 lan thi dung gia tri do duoc (LT_GOM_MAC_DINH, LT_HL_GIAY_NGHIN_THE). Khong thap hon LT_HL_PHUT_MIN.
lt_can_giay() {
  local the=$1 g h t i n idx need
  local -a du=() lsu
  mapfile -t lsu < <(tail -n 10 "$LT_LS_F" 2>/dev/null | grep -E '^[0-9]+ [0-9]+ [0-9]+$')
  for i in "${!lsu[@]}"; do
    read -r g h t <<<"${lsu[$i]}"
    [ $((10#$t)) -gt 0 ] && du+=($((10#$g + 10#$h * the / 10#$t)))
  done
  n=${#du[@]}
  if [ $n -ge 3 ]; then
    mapfile -t du < <(printf '%s\n' "${du[@]}" | sort -n)
    idx=$(( (9 * n + 9) / 10 - 1 ))                  # hang gan nhat cua phan vi 90%
    need=$((du[idx] + LT_DU_PHUT * 60))
  else
    need=$((LT_GOM_MAC_DINH + the * LT_HL_GIAY_NGHIN_THE / 10000 + LT_DU_PHUT * 60))
  fi
  [ $need -lt $((LT_HL_PHUT_MIN * 60)) ] && need=$((LT_HL_PHUT_MIN * 60))
  echo $need
}
# Ghi mot lan huan luyen THANH CONG: $1 giay gom, $2 giay huan luyen, $3 so the cua so, $4 so the moi, $5 = 1 neu lan sach (khong phai thu lai / cho 429).
lt_ghi_lich_su() {
  { tail -n 9 "$LT_THE_MOI_F" 2>/dev/null; echo "$4"; } > "$LT_THE_MOI_F.t" && mv "$LT_THE_MOI_F.t" "$LT_THE_MOI_F"
  [ "${5:-0}" = 1 ] || return 0
  { tail -n 9 "$LT_LS_F" 2>/dev/null; echo "$1 $2 $3"; } > "$LT_LS_F.t" && mv "$LT_LS_F.t" "$LT_LS_F"
}
lt_yc() { local n; n=$(cut -d' ' -f1 "$LT_YC_F" 2>/dev/null); [[ "$n" =~ ^[0-9]+$ ]] && echo $((10#$n)) || echo 0; }
lt_ghi_tep() { printf '%s\n' "$2" > "$1.t" && mv "$1.t" "$1"; }    # ghi nguyen tu
# "<so van> <so the> <so thu tu lon nhat>" cua cac goi co so thu tu > $1 (thuan bash: goi_<seq>_n<mang>_<van>_<the>.zip).
lt_goi_moi() {
  local f b v=0 t=0 m=0 s
  for f in "$LT_GOI"/goi_*.zip; do
    b=${f##*/}
    [[ $b =~ ^goi_([0-9]+)_n[0-9]+_([0-9]+)_([0-9]+)\.zip$ ]] || continue
    s=$((10#${BASH_REMATCH[1]})); [ $s -gt $m ] && m=$s
    [ $s -gt "$1" ] && { v=$((v + ${BASH_REMATCH[2]})); t=$((t + ${BASH_REMATCH[3]})); }
  done
  echo "$v $t $m"
}
# Van da xong ma cac cua so chua gui (uoc tinh: van cua lan chay hien tai tru van luc gui goi cuoi).
lt_van_cho_gui() {
  local w v d tong=0
  for w in $(td_cac_cua_so); do
    [ "$(td_doc "$w" buoc)" = sinh ] || continue
    v=$(td_doc "$w" van); d=$(td_doc "$w" da_goi)
    [ $((${v:-0} - ${d:-0})) -gt 0 ] && tong=$((tong + ${v:-0} - ${d:-0}))
  done
  echo $tong
}

# ---------------- Khoa huan luyen ----------------
lt_hl_chu() {
  local p
  p=$(cat "$LT_HL/pid" 2>/dev/null)
  if [ -n "$p" ] && td_song "$p"; then echo "$p"; return; fi
  [ -d "$LT_HL" ] && rm -rf "$LT_HL"
}
lt_hl_lay() {
  [ "$(lt_hl_chu)" = $$ ] && return 0
  [ -n "$(lt_hl_chu)" ] && return 1
  mkdir "$LT_HL" 2>/dev/null || return 1
  echo $$ > "$LT_HL/pid"
}
lt_hl_tra() { [ "$(cat "$LT_HL/pid" 2>/dev/null)" = $$ ] && rm -rf "$LT_HL"; return 0; }
# Co nen huan luyen luot moi (khong dung toi may; chi doc tep tren dien thoai)? 0 = co.
lt_hl_den_luot() {
  local moc van the seq nghi
  [ -n "$(lt_hl_chu)" ] && return 1
  nghi=$(cat "$LT_NGHI_F" 2>/dev/null)
  [[ "$nghi" =~ ^[0-9]+$ ]] && [ $(( $(date +%s) - nghi )) -lt 600 ] && return 1
  moc=$(lt_moc)
  read -r van the seq <<<"$(lt_goi_moi "$moc")"
  [ $((van + $(lt_van_cho_gui))) -ge "$(td_muc)" ]
}

# ---------------- Gom + tai goi van ve dien thoai ----------------
# Tai mot goi $1 (tren may, $5 byte) ve dien thoai. $2 mang $3 so van $4 so the. 0 = da dat ten (FZ_GOI_NHAN). Mot ssh moi lan thu.
lt_tai_goi() {
  local nguon=$1 mang=$2 van=$3 the=$4 kt=$5 q tam i
  q=$(printf %q "$nguon")
  mkdir -p "$LT_GOI"
  tam=$LT_GOI/.dang_tai_${BASHPID}_$RANDOM.zip
  for i in 1 2 3; do
    ssh_colab "cat $q" > "$tam" 2>/dev/null
    [ "$(stat -c %s "$tam" 2>/dev/null)" = "$kt" ] && break
    rm -f "$tam"
    sleep 3
  done
  [ -f "$tam" ] || return 1
  python ~/fz_tu_dong.py goi_nhan "$TAI" "$tam" "$mang" "$van" "$the" 2>&1 | sed -n 's/^FZ_GOI_NHAN \(.*\)/    [goi] \1/p'
  [ "${PIPESTATUS[0]}" = 0 ] || { rm -f "$tam"; return 1; }
  return 0
}
# Gom cac van MOI tren may (moi thu muc games_gen<mang>_<run>) thanh goi, tai ve, danh dau da gui. 0 = xong (ke ca khong co gi), 1 = loi.
# Dat da_goi = van da xong luc bat dau gui; phuc_vu = yeu cau da phuc vu (doc TRUOC khi gom: yeu cau moi den giua chung se duoc phuc vu lan sau).
# So lan ssh: 1 (gom) + 1 moi goi (tai) + 1 (danh dau da gui tat ca cac goi da ve).
lt_gui_goi() {
  local yc van_luc out l zip mang van the kt loi=0 n=0 tong_van=0 tong_the=0 ds=()
  LT_GOI_T=$SECONDS
  yc=$(lt_yc); van_luc=$LT_VAN
  out=$(ssh_colab "python3 $E_CL/python/goi_van.py pack /content --tk $(ten_tk "$TK") --ra /content/goi_ra" 2>&1)
  if ! grep -q '^FZ_GOI_XONG' <<<"$out"; then
    td_in "${M_VANG}[!] gom goi van lỗi${M_HET}: $(tail -2 <<<"$out" | tr '\n' ' ')"
    return 1
  fi
  while IFS= read -r l; do
    if [[ "$l" =~ ^FZ_GOI_BO\ (.*) ]]; then td_in "${M_VANG}bỏ ván hỏng${M_HET} ${BASH_REMATCH[1]}"; continue; fi
    [[ "$l" =~ ^FZ_GOI\ ([^\ ]+)\ ([0-9]+)\ ([0-9]+)\ ([0-9]+)\ ([0-9]+)$ ]] || continue
    zip=${BASH_REMATCH[1]}; mang=${BASH_REMATCH[2]}; van=${BASH_REMATCH[3]}; the=${BASH_REMATCH[4]}; kt=${BASH_REMATCH[5]}
    if lt_tai_goi "$zip" "$mang" "$van" "$the" "$kt"; then
      n=$((n + 1)); tong_van=$((tong_van + van)); tong_the=$((tong_the + the)); ds+=("$(printf %q "$zip.ds")")
    else
      loi=1
    fi
  done <<<"$out"
  if [ $n -gt 0 ]; then
    if ! ssh_colab "python3 $E_CL/python/goi_van.py commit ${ds[*]}" >/dev/null 2>&1; then
      td_in "${M_VANG}[!] chưa đánh dấu được $n gói đã gửi${M_HET} -- lần sau gửi lại (trùng vài ván, vô hại)"
    fi
    td_in "gửi $n gói ($tong_van ván, $tong_the thế) về điện thoại · tổng ván mới: $(lt_goi_moi "$(lt_moc)" | cut -d' ' -f1) + $(lt_van_cho_gui) chờ gửi"
  fi
  [ $loi = 0 ] && { LT_DA_GOI=$van_luc; td_ghi da_goi="$LT_DA_GOI" phuc_vu="$yc"; return 0; }
  td_in "${M_VANG}[!] chưa gửi hết gói -- thử lại lần sau${M_HET}"
  return 1
}

# ---------------- Engine: khoi dong / dung / cho het ----------------
# Dung mem MOI tien trinh sinh 04_* tren may (tep dung_<run>); in so tien trinh con chay. 0 = da gui lenh.
lt_dung_het_run() {
  ssh_colab "for o in \$(python3 $LOGD/fz_may.py sinh_dang_chay | sed -n 's/^FZ_SINH 04_\\([^ ]*\\) .*/\\1/p'); do touch $LOGD/dung_\$o; done; echo FZ_DUNG_XONG" 2>/dev/null | grep -q FZ_DUNG_XONG
}
lt_con_chay() {   # in so tien trinh sinh con chay tren may; rong = khong doc duoc
  local out
  out=$(ssh_colab "python3 $LOGD/fz_may.py sinh_dang_chay" 2>&1)
  grep -q FZ_SINH_XONG <<<"$out" || { td_in "${M_VANG}[!] không đọc được danh sách engine trên máy${M_HET}: $(tail -2 <<<"$out" | tr '
' ' ')" >&2; return 1; }
  grep -c '^FZ_SINH ' <<<"$out" || true      # grep -c in 0 va thoat 1 khi khong co dong nao: khong duoc coi la loi
}
# Dung mem moi engine sinh va cho toi da $1 giay (mac dinh 480) cho choi not van do; qua gio thi giet. 0 = het, 3 = mat may, 4 = q.
lt_dung_cho_het() {
  local gioi=${1:-480} t=$SECONDS n bao=$SECONDS
  lt_dung_het_run
  while :; do
    n=$(lt_con_chay) || { td_con_may || return 3; n=1; }
    [ "$n" = 0 ] && break
    if [ $((SECONDS - t)) -ge "$gioi" ]; then
      td_in "${M_VANG}[!] engine còn chạy sau $((gioi / 60)) phút -- dừng hẳn${M_HET}"
      ssh_colab "pkill -f 'custom_engine.*--selfplay' ; sleep 2; echo FZ_GIET" >/dev/null 2>&1
      break
    fi
    if [ $((SECONDS - bao)) -ge 60 ]; then bao=$SECONDS; td_in "chờ $n engine chơi nốt ván dở ($((SECONDS - t)) giây)..."; fi
    td_ngu 8 || return 4
  done
  LT_O=; LT_RUN=; LT_PID=; LT_NET=
  return 0
}
# Mang $1 co tren may (dung kieu .fzw / .onnx cua may)? Chua thi lay tu Release NN_Model (python/lay_mang.py). 0 = co.
lt_lay_mang() {
  local m=$1 k url out rc
  k=$(td_net_may); url=$(td_rel_nn_url)
  out=$(ssh_colab "[ -s /content/gen$m.$k ] && echo FZ_RC=0 || { python3 $E_CL/python/lay_mang.py $k /content/gen$m.$k --rel '$url'; echo FZ_RC=\$?; }" 2>&1)
  rc=$(sed -n 's/^FZ_RC=//p' <<<"$out" | tail -1)
  [ "$rc" = 0 ] && return 0
  td_in "${M_VANG}[!] chưa có mạng gen$m trên máy (rc ${rc:-?})${M_HET}: $(tail -2 <<<"$out" | tr '\n' ' ')"
  return 1
}
# Khoi dong mot lan chay engine (o 04l, ma RUN moi) bang mang $1. Tien trinh dang chay truoc do (neu co) duoc dung mem.
# 0 = dang chay (LT_O, LT_PID, LT_NET, LT_RUN), 1 = loi tam (thu lai), 2 = het han muc (da tra may), 3 = mat may, 4 = q.
lt_bat_run() {
  local g=$1 secs par duoi o04l f out pid run cu=$LT_RUN
  secs=$(td_giay_t4)
  if [ -z "$secs" ]; then td_in "không đọc được hạn mức -- thử lại sau 1 phút"; td_ngu 60 || return 4; return 1; fi
  o04l=$(ls "$D"/04l_*.py 2>/dev/null | head -1)
  [ -n "$o04l" ] || { td_in "${M_DO}[!] thiếu ô 04l trên điện thoại (bash ~/lay_ve.sh)${M_HET}"; TD_LOI=1; return 1; }
  par=$(song_song_o04 "$o04l"); duoi=$(duoi_giay "$par")
  secs=$((secs - $(chua_phut) * 60 - duoi))
  if [ $secs -lt $((TD_PHUT_SINH * 60)) ]; then
    td_in "$(ten_tk "$TK"): hạn mức còn $(( (secs + duoi) / 60 + $(chua_phut) )) phút T4 -> gom nốt, trả máy"
    lt_ket_may; return 2
  fi
  lt_lay_mang "$g" || { td_con_may || return 3; td_ngu 30 || return 4; return 1; }
  run=$(date +%m%d%H%M%S)
  f=$TD/o_$$/$(basename "$o04l")
  mkdir -p "$TD/o_$$"
  sed -E "0,/^SECS = [0-9]+.*/s//SECS = $secs/; 0,/^RUN = .*/s//RUN = \"$run\"/; 0,/^NET_N = .*/s//NET_N = $g/" "$o04l" > "$f"
  td_in "04l trên $(ten_tk "$TK"): mạng gen$g, mã $run, chạy tối đa $((secs / 60)) phút (đã trừ $(chua_phut) phút gom + $(( (duoi + 59) / 60 )) phút đuôi ván)"
  out=$(khoi_dong_ssh "04_$run" "$f") || { td_con_may || return 3; return 1; }
  pid=$(sed -n 's/^FZ_PID=//p' <<<"$out")
  [ -n "$pid" ] || { echo "$out" | tail -3; return 1; }
  LT_O="04_$run"; LT_RUN=$run; LT_PID=$pid; LT_NET=$g; LT_VAN=0; LT_DA_GOI=0
  td_ghi lt=1 gen="$g" buoc=sinh van=0 da_goi=0 par="$par" run="$run"
  # Tien trinh cu (mang cu) chi choi not van do roi thoat: van cua no duoc gom o lan gui goi ke tiep.
  if [ -n "$cu" ]; then
    ssh_colab "touch $LOGD/dung_$cu" 2>/dev/null && td_in "đã dừng mềm engine cũ (mã $cu): chơi nốt ván dở rồi thoát"
  fi
  return 0
}
# Ghi so giay vuot SECS cua lan chay vua xong (de lan sau tru dung duoi van, nhu ghi_duoi_log cua ô 04).
lt_ghi_duoi() {
  local r p secs x
  r=$(ssh_colab "f=$LOGD/04_$1.log; grep -o -- '--parallel [0-9]*' \$f | head -1; grep -o -- '--max-seconds [0-9]*' \$f | head -1; sed -n 's/^\\[selfplay\\] Finished [0-9]*\\/[0-9]* games in \\([0-9]*\\)[.0-9]*s (dung som do dat nguong --max-seconds).*/\\1/p' \$f | tail -1" 2>/dev/null) || return 0
  p=$(sed -n 's/^--parallel //p' <<<"$r"); secs=$(sed -n 's/^--max-seconds //p' <<<"$r")
  x=$(grep -E '^[0-9]+$' <<<"$r" | tail -1)
  so_nguyen "$p" && so_nguyen "$secs" && so_nguyen "$x" && [ "$x" -gt "$secs" ] || return 0
  echo "$p $((x - secs))" >> "$DUOI_F"
  tail -n 50 "$DUOI_F" > "$DUOI_F.t" 2>/dev/null && mv "$DUOI_F.t" "$DUOI_F"
  td_in "[đuôi ván] $p ván song song: vượt SECS $((x - secs)) giây -- đã ghi"
}
# Ket thuc viec cua may nay: dung engine, gui not goi, tra may.
lt_ket_may() {
  lt_dung_cho_het 480
  lt_gui_goi || lt_gui_goi
  td_tra
  LT_O=; LT_RUN=; LT_PID=; LT_NET=
}

# ---------------- Tu nap lai ma moi (2026-11-24) ----------------
# Cua so chay hang gio, nen cap nhat ~/fz_menu.sh, ~/fz_tu_dong.sh, ~/fz_lien_tuc.sh (lay_ve.sh, hoac Claude cai qua ssh) KHONG bat buoc phai mo
# lai cua so: moi LT_NAP_GIAY giay (mac dinh 60) cua so xem ngay sua tep; doi thi nap lai CAC HAM va cac bien moi CHUA co -- khong dong vao bien
# trang thai dang chay (may dang giu, engine dang chay, ...). Ma moi co loi cu phap thi giu ban dang chay (bao mot lan). Ham dang chay do chay
# not ban cu (bash sao than ham truoc khi chay), lan goi sau dung ban moi. Cac o (04l, 07, 08...) va python/*.py von doc lai moi lan chay.
# KHONG nap lai duoc: doi y nghia mot bien dang dung / doi cau truc tep trang thai -- khi do mo lai cua so.
declare -gA LT_NAP_M=()
LT_NAP_F=("$HOME/fz_menu.sh" "$HOME/fz_tu_dong.sh" "$HOME/fz_lien_tuc.sh")
LT_NAP_T=$SECONDS
for _f in "${LT_NAP_F[@]}"; do LT_NAP_M[$_f]=$(stat -c %Y "$_f" 2>/dev/null); done; unset _f
# In ra cac ham cap cao nhat (cot 0: `ten() {` ... `}` o cot 0, hoac mot dong) cua tep $1.
lt_trich_ham() {
  awk '
    /^[A-Za-z_][A-Za-z0-9_]*\(\)[ \t]*\{/ {
      print; l = $0; sub(/[ \t]+#.*$/, "", l)
      dang = (l ~ /\}[ \t]*$/) ? 0 : 1
      next }
    dang { print; if ($0 ~ /^\}[ \t]*$/) dang = 0 }
  ' "$1"
}
lt_nap_lai() {
  local f m ham l n moi=()
  for f in "${LT_NAP_F[@]}"; do
    m=$(stat -c %Y "$f" 2>/dev/null) || continue
    [ "$m" = "${LT_NAP_M[$f]:-}" ] || moi+=("$f")
  done
  [ ${#moi[@]} -gt 0 ] || return 0
  sleep 3                                  # tep co the dang duoc ghi (curl -o): doi no on dinh roi moi doc
  for f in "${moi[@]}"; do
    m=$(stat -c %Y "$f" 2>/dev/null) || continue
    ham=$(lt_trich_ham "$f")
    if [ -n "$ham" ] && bash -n <<<"$ham" 2>/dev/null; then
      while IFS= read -r l; do                # bien cap cao viet hoa MOI (chua co): dat gia tri mac dinh cua ban moi
        n=${l%%=*}
        [ -z "${!n+x}" ] && eval "$l"
      done < <(grep -E '^[A-Z][A-Z0-9_]*=' "$f")
      eval "$ham"
      td_in "${M_XANH}đã nạp lại mã mới${M_HET} từ ${f##*/} (không cần mở lại cửa sổ)"
    else
      td_in "${M_DO}[!] mã mới trong ${f##*/} có lỗi cú pháp -- giữ bản đang chạy${M_HET} (sửa tệp là tự nạp lại)"
    fi
    LT_NAP_M[$f]=$m
  done
  # fz_lien_tuc.sh nap sau cung: ham no GHI DE ham cung ten cua fz_tu_dong.sh (td_dung_ca) phai thang du tep nao vua doi.
  ham=$(lt_trich_ham "$HOME/fz_lien_tuc.sh")
  [ -n "$ham" ] && bash -n <<<"$ham" 2>/dev/null && eval "$ham"
  return 0
}

# ---------------- Su kien (chi doc tep tren dien thoai, khong ssh) ----------------
LT_GOI_T=-999; LT_HL_T=-999; LT_NGHI_RIENG=-9999
lt_su_kien() {
  local yc dv
  LT_SK=
  if [ $((SECONDS - LT_NAP_T)) -ge "${LT_NAP_GIAY:-60}" ]; then LT_NAP_T=$SECONDS; lt_nap_lai; fi
  if td_dung_ca; then LT_SK=dung; return 0; fi
  if [ "$(td_gen)" != "$LT_NET" ]; then LT_SK=mang; return 0; fi
  yc=$(lt_yc); dv=$(td_doc "$TD_W" phuc_vu)
  if [ "$yc" -gt "${dv:-0}" ] && [ $((SECONDS - LT_GOI_T)) -ge 20 ]; then LT_SK=goi; return 0; fi
  # Gui goi theo so van (it nhat 60 giay giua hai lan thu: gui loi khong duoc lap lien tuc).
  if [ $((LT_VAN - LT_DA_GOI)) -ge "$LT_PACK_VAN" ] && [ $((SECONDS - LT_GOI_T)) -ge 60 ]; then LT_SK=goi; return 0; fi
  # Dieu kien huan luyen quet cac tep trang thai cua moi cua so: chi kiem moi 15 giay; sau lan tu choi (thieu han muc) nghi 10 phut.
  if [ $((SECONDS - LT_HL_T)) -ge 15 ] && [ $((SECONDS - LT_NGHI_RIENG)) -ge 600 ]; then
    LT_HL_T=$SECONDS
    if lt_hl_den_luot; then LT_SK=hl; return 0; fi
  fi
  return 1
}
# Xem log engine $1 (pid $2) den khi no ket thuc HOAC co su kien (lt_su_kien). 0 = o ket thuc, 3 = mat may, 4 = q, 5 = su kien (LT_SK).
# Luong log qua MOT ssh (Colab chi cho mot ssh moi may): co su kien thi ngat luong, lam viec, roi noi lai (xem td_xem).
lt_xem() {
  local o=$1 pid=$2 them=${3:-} fifo=$TD/.luong_$$ sp fd dong rc lan=0 bd=0 ly_do cho
  local sil=$SECONDS nhac=$SECONDS ctl=$SECONDS chk=$SECONDS
  LT_SK=
  while :; do
    rm -f "$fifo"; mkfifo "$fifo" || return 1
    NGAT=0
    ssh_colab "python3 $LOGD/fz_may.py theo_doi $o $pid $them" > "$fifo" 2>/dev/null &
    sp=$!
    command exec {fd}<"$fifo" || { td_giet "$sp"; td_ngu 5 || return 4; continue; }
    ly_do=het
    while :; do
      if IFS= read -r -t 5 -u "$fd" dong; then
        printf '%s\n' "$dong"; lan=0; sil=$SECONDS; nhac=$SECONDS
        if [[ "$dong" =~ ^\[selfplay\]\ ([0-9]+)/ ]]; then LT_VAN=${BASH_REMATCH[1]}; td_ghi van="$LT_VAN"; fi
      else
        rc=$?
        [ -n "$dong" ] && printf '%s' "$dong"
        [ $NGAT = 1 ] && { ly_do=ngat; break; }
        [ $rc -gt 128 ] || break
        if [ $((SECONDS - sil)) -ge 600 ]; then
          td_in "${M_VANG}10 phút không có dòng log mới${M_HET} -- nối lại luồng log (engine trên máy vẫn chạy)"
          ly_do=tre; break
        elif [ $((SECONDS - sil)) -ge 180 ] && [ $((SECONDS - nhac)) -ge 180 ]; then
          ly_do=soi; break
        fi
      fi
      if [ $((SECONDS - ctl)) -ge 1 ]; then ctl=$SECONDS; td_ctrl_d; fi
      [ $NGAT = 1 ] && { ly_do=ngat; break; }
      if [ $((SECONDS - chk)) -ge 4 ]; then
        chk=$SECONDS
        lt_su_kien && { ly_do=su_kien; break; }
      fi
    done
    exec {fd}<&-
    if [ $ly_do = het ]; then
      wait "$sp"; rc=$?
      rm -f "$fifo"
      [ $rc = 0 ] && return 0
      [ $NGAT = 1 ] && ly_do=ngat
    else
      td_giet "$sp"; wait "$sp" 2>/dev/null
      rm -f "$fifo"
    fi
    them=3
    case $ly_do in
      ngat) td_hoi_ngat; [ $TD_THOAT = 1 ] && return 4 ;;
      su_kien) return 5 ;;
      soi)
        nhac=$SECONDS
        td_in "${M_VANG}chưa có dòng log mới sau $((SECONDS - sil)) giây${M_HET} -- các tiến trình đang chạy trên máy:"
        ssh_colab "ps -eo etime,args | grep -E 'git |wget|curl|pip |lay_mang|custom_engine|train.py|IPython' | grep -v grep | tail -4 | cut -c1-140" 2>&1 | sed 's/^/    /'
        td_con_may || return 3 ;;
      tre)
        them=20
        td_con_may || return 3
        td_ngu 5 || return 4 ;;
      het)
        them=20
        td_con_may || return 3
        [ $lan = 0 ] && bd=$SECONDS
        lan=$((lan + 1)); cho=$((lan * 5)); [ $cho -gt 30 ] && cho=30
        echo "[mất kết nối tới máy -- nối lại sau $cho giây (lần $lan) · engine trên Colab VẪN CHẠY]"
        td_ngu $cho || return 4 ;;
    esac
  done
}

# ---------------- Huan luyen (chay chong len sinh du lieu cua cac may khac) ----------------
# Cac goi ($@ = ten tep trong $LT_GOI) ma may CHUA co du: khac ten hoac khac kich thuoc (tar bi dut giua chung de lai tep cut). In ten, moi dong
# mot goi. Ma 2 = khong hoi duoc may (ssh loi / Colab tu choi 429).
lt_goi_thieu() {
  local out x s
  out=$(ssh_colab "mkdir -p /content/goi; cd /content/goi && { stat -c '%n %s' *.zip 2>/dev/null; echo FZ_LIET_XONG; }" 2>"$TD/.loi_ssh_$$")
  grep -q FZ_LIET_XONG <<<"$out" || return 2
  for x in "$@"; do
    s=$(stat -c %s "$LT_GOI/$x" 2>/dev/null)
    grep -qxF "$x $s" <<<"$out" || echo "$x"
  done
  return 0
}
# Dua cac goi len may bang MOT luong tar qua MOT ssh. Truoc day moi goi mot ssh rieng: 25 goi mat ~3 phut (moi lan bat tay ssh ~5 giay), va mot lan
# dut giua chung (2026-11-24 14:41, tai khoan luubi: toc do roi xuong ~1 KB/s) khien Colab tu choi MOI ssh moi voi 429 "Already-active SSH session"
# vai phut (phien cu chua duoc giai phong) -> ba lan thu cach nhau 5 giay deu hong -> bo ca luot huan luyen. Nay: toi 7 vong; moi vong hoi may con
# thieu goi nao roi chi gui phan do; 429 thi cho LT_CHO_429 (mac dinh 30) giay x so vong, loi khac cho 10 giay. 0 = may da co du.
lt_len_goi() {
  local err=$TD/.loi_ssh_$$ i thieu out rc tong x cho
  for i in 1 2 3 4 5 6 7; do
    out=$(lt_goi_thieu "$@"); rc=$?
    if [ $rc = 0 ]; then
      mapfile -t thieu <<<"$out"
      [ -z "${thieu[0]:-}" ] && { rm -f "$err"; LT_LEN_VONG=$i; return 0; }      # i = 1: may da co du; 2: mot lan gui roi du (binh thuong); > 2: phai thu lai
      [ $i = 7 ] && break
      tong=0
      for x in "${thieu[@]}"; do tong=$((tong + $(stat -c %s "$LT_GOI/$x"))); done
      td_in "tải ${#thieu[@]} gói ($((tong / 1024)) KB) lên máy bằng một luồng (vòng $i)"
      if command -v pv >/dev/null; then
        ( cd "$LT_GOI" && tar cf - "${thieu[@]}" ) | pv -s "$tong" | ssh_colab "mkdir -p /content/goi && tar xf - -C /content/goi" 2>"$err"
      else
        ( cd "$LT_GOI" && tar cf - "${thieu[@]}" ) | ssh_colab "mkdir -p /content/goi && tar xf - -C /content/goi" 2>"$err"
      fi
      continue                       # vong sau hoi lai may de kiem tra (khong tin ma thoat cua duong ong)
    fi
    [ $i = 7 ] && break
    if grep -q -E 'Already-active SSH session|HTTP 429' "$err" "$TD/.loi_ssh_$$" 2>/dev/null; then
      cho=$(( ${LT_CHO_429:-30} * i ))
      td_in "${M_VANG}Colab từ chối ssh mới (429: phiên ssh cũ chưa được giải phóng)${M_HET} -- chờ $cho giây rồi thử lại (vòng $i/6)"
    else
      cho=10
      td_in "${M_VANG}chưa hỏi được máy qua ssh${M_HET} -- chờ $cho giây rồi thử lại (vòng $i/6)"
    fi
    td_ngu "$cho" || return 1
  done
  rm -f "$err"
  return 1
}
# Tai len may cac goi cua cua so huan luyen ma may chua co; xoa goi thua. In danh sach (cach nhau dau phay) ra bien LT_DATA.
lt_len_cua_so() {
  local the ds ten tong
  the=${LT_THE_HL:-$(lt_the)}                  # cua so da chot luc lay khoa huan luyen (tu canh doi theo lich su, khong de doi giua chung)
  ds=$(python ~/fz_tu_dong.py cua_so "$TAI" "$the")
  tong=$(grep '^FZ_CUA_SO' <<<"$ds")
  mapfile -t ten < <(sed -n 's/^GOI //p' <<<"$ds")
  if [ ${#ten[@]} -eq 0 ]; then td_in "${M_DO}[!] chưa có gói ván nào cho cửa sổ huấn luyện${M_HET}"; return 1; fi
  td_in "cửa sổ huấn luyện: ${tong#FZ_CUA_SO } (gói, ván, thế, mạng nhỏ nhất-lớn nhất)"
  lt_len_goi "${ten[@]}" || { td_in "${M_VANG}[!] chưa tải đủ gói lên máy${M_HET}"; return 1; }
  ssh_colab "cd /content/goi && for f in *.zip; do case ' ${ten[*]} ' in *\" \$f \"*) ;; *) rm -f \"\$f\" ;; esac; done" >/dev/null 2>&1
  LT_DATA=$(printf '/content/goi/%s,' "${ten[@]}"); LT_DATA=${LT_DATA%,}
  return 0
}
# ---------------- Dua mang len GitHub TU MAY COLAB (khong qua dien thoai) ----------------
# Neu co tep token ($LT_NETS_TOKEN_F, mac dinh ~/.fz_nets_token, do nguoi dung tu dat) thi sau khi o 07 xong, MAY HUAN LUYEN tu tai /content/gen<N>.pt len Release NN_Model bang
# `gh release upload --clobber` (gh co san tren anh Colab; do 2026-11-25: gh 2.102, gui 20 MB ra ngoai ~0,3-0,7 giay) thay cho duong cu: dien thoai tai .pt ve (20,3 MB) roi tai len
# (20,3 MB), mat 39-83 giay moi lan. Token di tu dien thoai qua DAU VAO cua mot lenh ssh (khong nam tren dong lenh, khong ghi tep tren may, khong vao nhat ky). Dien thoai chi doc danh
# sach tep cua Release de kiem kich thuoc + sha256 do may Colab tinh. Loi gi cung tra 1 -> vong lap dung duong cu (tai ve dien thoai roi tai len); sau loi thi nghi LT_NETS_NGHI_GIAY.
LT_NETS_TOKEN_F=${LT_NETS_TOKEN_F:-$HOME/.fz_nets_token}
LT_NETS_NGHI_F=$TD/.lt_nets_loi
LT_NETS_NGHI_GIAY=${LT_NETS_NGHI_GIAY:-1800}
lt_nets_bat() {      # 0 = co tep token va khong dang nghi sau loi
  local t
  [ -s "$LT_NETS_TOKEN_F" ] || return 1
  t=$(cat "$LT_NETS_NGHI_F" 2>/dev/null)
  [[ "$t" =~ ^[0-9]+$ ]] && [ $(( $(date +%s) - t )) -lt "$LT_NETS_NGHI_GIAY" ] && return 1
  return 0
}
lt_nets_loi() { lt_ghi_tep "$LT_NETS_NGHI_F" "$(date +%s)"; td_in "${M_VANG}$1${M_HET} -- dùng đường cũ (tải về điện thoại rồi tải lên); thử lại đường mới sau $((LT_NETS_NGHI_GIAY / 60)) phút"; }
lt_len_github_colab() {
  local n=$1 repo tag tsv so them out err=$TD/.loi_nets_$$ i rc cho sz sha ten tsz dg cmd
  read -r repo tag <<<"$(td_rel_nn)"
  [ -n "$tag" ] || { lt_nets_loi "không đọc được REL_NN"; return 1; }
  [ "$n" -le "$TD_GEN_CUOI" ] || { td_in "${M_DO}[!] đời $n vượt giới hạn $TD_GEN_CUOI${M_HET}"; return 1; }
  tsv=$(td_tep_release "$repo" "$tag") || { lt_nets_loi "không đọc được danh sách tệp Release $tag"; return 1; }
  so=$(grep -c . <<<"$tsv"); them=0; grep -q "^gen$n\.pt"$'\t' <<<"$tsv" || them=1
  [ $((so + them)) -le "$TD_REL_TOI_DA" ] || { td_in "${M_DO}[!] Release $tag có $so tệp, thêm $them tệp sẽ vượt giới hạn $TD_REL_TOI_DA${M_HET}"; return 1; }
  td_in "đưa gen$n.pt lên GitHub ${M_DAM}từ máy Colab${M_HET} ($tag, đang có $so/$TD_REL_TOI_DA tệp)"
  cmd="read -r GH_TOKEN || exit 90; export GH_TOKEN; command -v gh >/dev/null || exit 91; cd /content && [ -s gen$n.pt ] || exit 92; gh release upload $tag gen$n.pt --clobber -R $repo >/dev/null 2>/content/fz_gh_err || { tail -c 300 /content/fz_gh_err >&2; exit 93; }; echo FZ_NETS \$(stat -c %s gen$n.pt) \$(sha256sum gen$n.pt | cut -d' ' -f1)"
  for i in 1 2 3; do
    out=$(cat "$LT_NETS_TOKEN_F" | ssh_colab "$cmd" 2>"$err"); rc=$?
    [ $rc = 0 ] && grep -q '^FZ_NETS ' <<<"$out" && break
    if [ $i -lt 3 ] && grep -q -E 'Already-active SSH session|HTTP 429' "$err"; then
      cho=$(( ${LT_CHO_NETS:-15} * i ))
      td_in "${M_VANG}Colab từ chối ssh mới (429)${M_HET} -- chờ $cho giây rồi tải lên lại (lần $i/3)"
      td_ngu "$cho" || { rm -f "$err"; return 1; }
      continue
    fi
    break
  done
  if [ $rc != 0 ] || ! grep -q '^FZ_NETS ' <<<"$out"; then
    case $rc in
      91) lt_nets_loi "máy Colab không có gh" ;;
      92) lt_nets_loi "không thấy /content/gen$n.pt trên máy Colab" ;;
      93) if grep -q -E '401|403|Bad credentials|Forbidden|not accessible|Not Found' "$err"; then lt_nets_loi "GitHub từ chối token ($(tr -d '\n' < "$err" | cut -c1-120)) -- kiểm tra $LT_NETS_TOKEN_F"; else lt_nets_loi "gh tải lên lỗi: $(tr -d '\n' < "$err" | cut -c1-120)"; fi ;;
      *) lt_nets_loi "không chạy được lệnh tải lên trên máy Colab (mã $rc)" ;;
    esac
    rm -f "$err"; return 1
  fi
  rm -f "$err"
  read -r _ sz sha <<<"$(grep '^FZ_NETS ' <<<"$out" | tail -1)"
  for i in 1 2 3; do tsv=$(td_tep_release "$repo" "$tag") && break; td_ngu 10 || return 1; done
  IFS=$'\t' read -r ten tsz dg < <(grep "^gen$n\.pt"$'\t' <<<"$tsv" | head -1) || :
  if [ -z "$tsz" ] || [ "$tsz" != "$sz" ] || { [ -n "$dg" ] && [ "$dg" != "sha256:$sha" ]; }; then
    lt_nets_loi "gen$n.pt trên Release không khớp máy Colab (kích thước $tsz/$sz)"; return 1
  fi
  td_in "${M_XANH}đã lên Release $tag${M_HET} (từ máy Colab; kích thước + sha256 trên GitHub khớp tệp trên máy huấn luyện, điện thoại không phải tải $((sz / 1000000)) MB về rồi lên)"
  return 0
}
# Cua so nay huan luyen luot moi. Goi khi lt_hl_den_luot dung. Tra 0 = xong (ke ca loi, da tra khoa); 3 = mat may; 4 = q.
lt_huan_luyen() {
  local g n yc t0 w cho moc_cu seq van the h rc loi=0 f hl loi_len=0 bu_nghi=0 need t_khoa t_07 t_xong mv mt ms the_moi=0 sach=1 mang_len=0
  g=$(td_gen); n=$((g + 1))
  lt_hl_lay || return 0
  moc_cu=$(lt_moc)
  # Du dieu kien that khong (cua so khac vua lay khoa roi tra)? May nay con du T4 cho cua so huan luyen nay khong (lt_can_giay: phan vi 90% thoi gian cac lan
  # gan nhat quy theo so the cua so + LT_DU_PHUT phut)?
  if ! lt_hl_den_luot_khoa; then lt_hl_tra; return 0; fi
  LT_THE_HL=$(lt_the)
  need=$(lt_can_giay "$LT_THE_HL")
  h=$(td_giay_t4)
  if [ -z "$h" ] || [ "$h" -lt "$need" ]; then
    td_in "máy còn $(( ${h:-0} / 60 )) phút T4 (< $(( (need + 59) / 60 )) phút cần cho cửa sổ $LT_THE_HL thế) -- để cửa sổ khác huấn luyện"
    LT_NGHI_RIENG=$SECONDS
    lt_hl_tra; return 0
  fi
  t_khoa=$SECONDS
  TD_VAI=huan_luyen
  td_in "${M_DAM}huấn luyện đời $n${M_HET}: đủ ván mới -- yêu cầu các máy gửi gói ngay"
  yc=$(( $(lt_yc) + 1 ))
  lt_ghi_tep "$LT_YC_F" "$yc $(date +%s)"
  lt_gui_goi
  td_ghi phuc_vu="$yc"
  t0=$SECONDS
  while [ $((SECONDS - t0)) -lt 120 ]; do
    cho=0
    for w in $(td_cac_cua_so); do
      [ "$w" = "$TD_W" ] && continue
      [ "$(td_doc "$w" buoc)" = sinh ] || continue
      [ "$(td_doc "$w" phuc_vu | sed 's/^$/0/')" -ge "$yc" ] || cho=1
    done
    [ $cho = 0 ] && break
    td_ngu 3 || { lt_hl_tra; TD_VAI=; return 4; }
  done
  # Dung engine cua may nay (choi not van do) roi gom not.
  if [ "$LT_CHO_DUOI" = 1 ]; then
    lt_dung_cho_het 480; rc=$?
    case $rc in 3) lt_hl_tra; TD_VAI=; td_mat_may; return 3 ;; 4) lt_hl_tra; TD_VAI=; return 4 ;; esac
    lt_gui_goi || lt_gui_goi
  else
    lt_dung_het_run; LT_O=; LT_RUN=; LT_PID=; LT_NET=
  fi
  read -r mv mt ms <<<"$(lt_goi_moi "$moc_cu")"; the_moi=${mt:-0}          # so the MOI cua lan huan luyen nay (de canh cua so cho cac lan sau)
  read -r van the seq <<<"$(lt_goi_moi 0)"
  lt_ghi_tep "$LT_MOC_F" "$seq"
  td_ghi buoc=huan_luyen gen="$g" van=0
  while :; do
    td_chuan_bi "$g" pt; rc=$?
    case $rc in 0) ;; 2) loi=1; break ;; 3) lt_hl_tra; TD_VAI=; td_mat_may; lt_ghi_tep "$LT_MOC_F" "$moc_cu"; return 3 ;; 4) lt_hl_tra; TD_VAI=; return 4 ;; *) td_ngu 30 || { lt_hl_tra; TD_VAI=; return 4; }; continue ;; esac
    if ! lt_len_cua_so; then
      loi_len=$((loi_len + 1)); sach=0
      if [ $loi_len -ge 3 ]; then loi=1; bu_nghi=420; break; fi
      td_in "${M_VANG}tải gói lên máy lỗi${M_HET} -- thử lại sau 60 giây ($loi_len/3)"
      td_ngu 60 || { lt_hl_tra; TD_VAI=; return 4; }
      continue
    fi
    [ "${LT_LEN_VONG:-1}" -gt 2 ] && sach=0         # tai goi phai thu lai nhieu vong (429...): thoi gian lan nay khong dai dien
    f=$TD/o_$$/07_hl.py
    mkdir -p "$TD/o_$$"
    sed -E "s#^DATA = .*#DATA = \"$LT_DATA\"#" "$(ls "$D"/07_*.py | head -1)" > "$f"
    grep -q '^DATA = "/content/goi/' "$f" || { td_in "${M_DO}[!] ô 07 không có dòng DATA = ... để thay${M_HET}"; loi=1; break; }
    td_in "07: huấn luyện đời $n (cửa sổ $LT_THE_HL thế)"
    t_07=$SECONDS
    td_chay 07 "$f"; rc=$?
    case $rc in 3) lt_hl_tra; TD_VAI=; td_mat_may; lt_ghi_tep "$LT_MOC_F" "$moc_cu"; return 3 ;; 4) lt_hl_tra; TD_VAI=; return 4 ;; esac
    td_don_mang_cu "$n"
    # Co tep token: may Colab tu tai mang len GitHub (nhanh, khong qua dien thoai); loi thi xuong duong cu ben duoi.
    if lt_nets_bat && lt_len_github_colab "$n"; then mang_len=1; break; fi
    tai_theo_o 07
    [ "${TAI_DOC_CHO:-0}" = 1 ] && sach=0           # doc log bi 429 phai cho: khong dai dien
    # KHONG doc duoc log o 07 (ssh loi / Colab tu choi 429) khac voi "huan luyen khong ra mang": mang co the DA xong tren may (2026-11-24 17:23: gen65 xong, doc log
    # bi 429, vong lap huan luyen lai tu dau, mat 11 phut). Doc lai (toi 3 lan cach 60 giay) truoc khi nghi la huan luyen hong.
    for k in 1 2 3; do
      td_co_mang "$n" && break
      [ "${TAI_DOC_LOI:-0}" = 1 ] && td_con_may || break
      sach=0
      td_in "${M_VANG}chưa đọc được log ô 07${M_HET} (ssh) -- mạng có thể đã xong, đọc lại sau ${LT_CHO_DOC:-60} giây ($k/3), KHÔNG huấn luyện lại"
      td_ngu "${LT_CHO_DOC:-60}" || { lt_hl_tra; TD_VAI=; return 4; }
      tai_theo_o 07
    done
    td_co_mang "$n" && break
    td_con_may || { lt_hl_tra; TD_VAI=; td_mat_may; lt_ghi_tep "$LT_MOC_F" "$moc_cu"; return 3; }
    loi=$((loi + 1)); sach=0
    if [ $loi -ge 2 ]; then td_in "${M_DO}[!] huấn luyện lỗi 2 lần -- xem log ô 07${M_HET}"; loi=1; break; fi
    td_in "huấn luyện chưa ra mạng -- thử lại"; loi=0
  done
  if [ $loi = 1 ] || { [ $mang_len = 0 ] && ! td_co_mang "$n"; }; then
    td_in "${M_DO}[!] bỏ lượt huấn luyện đời $n${M_HET} -- ván vẫn giữ, thử lại sau $(( (600 - bu_nghi) / 60 )) phút"
    lt_ghi_tep "$LT_MOC_F" "$moc_cu"; lt_ghi_tep "$LT_NGHI_F" "$(( $(date +%s) - bu_nghi ))"
    lt_hl_tra; TD_VAI=; return 0
  fi
  # Mang da ve dien thoai: ghi lan huan luyen THANH CONG (the moi de canh cua so, thoi gian de tinh nguong T4 cho cac lan sau).
  t_xong=$SECONDS
  lt_ghi_lich_su "$((t_07 - t_khoa))" "$((t_xong - t_07))" "$LT_THE_HL" "$the_moi" "$sach"
  [ $mang_len = 1 ] || td_len_github "$n" || { lt_hl_tra; TD_VAI=; return 0; }      # mang_len = 1: may Colab da dua len Release roi
  td_len_doi "$g" "$n"
  [ "$(td_gen)" = "$n" ] && td_don_dep "$n"
  python ~/fz_tu_dong.py don_goi "$TAI" "$LT_THE_HL" 1.5 | sed -n 's/^FZ_DON_GOI_XONG \([0-9]*\) \(.*\)/dọn gói cũ: xoá \1 gói (\2 MB)/p' | while IFS= read -r hl; do td_in "$hl"; done
  lt_hl_tra; TD_VAI=
  return 0
}
# Nhu lt_hl_den_luot nhung KHONG xet khoa (cua so nay vua giu khoa).
lt_hl_den_luot_khoa() {
  local moc van the seq
  moc=$(lt_moc)
  read -r van the seq <<<"$(lt_goi_moi "$moc")"
  [ $((van + $(lt_van_cho_gui))) -ge "$(td_muc)" ]
}

# ---------------- Sinh du lieu tren may cua cua so nay ----------------
# Tra: 0 = quay lai vong chinh (may con hay da tra), 10 = can arena cho mang moi.
lt_sinh() {
  local rc them="" g
  while :; do
    lt_nap_lai
    [ $TD_THOAT = 1 ] && return 0
    if td_dung_ca && [ "$TD_VAI" != huan_luyen ]; then lt_ket_may; return 0; fi
    g=$(td_gen)
    if [ -z "$LT_O" ] || [ "$LT_NET" != "$g" ]; then
      if td_ar_viec "$g"; then return 10; fi
      lt_bat_run "$g"; rc=$?
      case $rc in
        0) them="" ;;
        1) [ $TD_LOI = 1 ] && return 0; td_ngu 20 || return 0; continue ;;
        2) return 0 ;;
        3) td_mat_may; LT_O=; LT_RUN=; LT_PID=; LT_NET=; return 0 ;;
        *) return 0 ;;
      esac
    fi
    lt_xem "$LT_O" "$LT_PID" "$them"; rc=$?
    them=3
    case $rc in
      0)
        # Engine ket thuc (het SECS / dung mem / loi): gom not; vong tiep theo xin han muc -> chay tiep hoac tra may.
        local ma t_chay
        ma=$(ssh_colab "cat $LOGD/$LT_O.rc 2>/dev/null" 2>/dev/null)
        lt_ghi_duoi "$LT_RUN"
        td_in "engine $LT_O kết thúc (mã ${ma:-?})"
        if [ "${ma:-0}" != 0 ]; then
          LT_CRASH=$((LT_CRASH + 1))
          if [ $LT_CRASH -ge 3 ]; then td_in "${M_DO}[!] engine thoát lỗi $LT_CRASH lần liền -- dừng vòng lặp (xem log: ô 04_$LT_RUN trên máy)${M_HET}"; TD_LOI=1; fi
        else
          LT_CRASH=0
        fi
        lt_dung_cho_het 480
        lt_gui_goi || lt_gui_goi
        [ $TD_LOI = 1 ] && return 0 ;;
      3) td_mat_may; LT_O=; LT_RUN=; LT_PID=; LT_NET=; return 0 ;;
      4) return 0 ;;
      5)
        case $LT_SK in
          dung) lt_ket_may; return 0 ;;
          mang) : ;;                      # vong sau: khoi dong engine moi bang mang moi (lt_bat_run)
          goi) lt_gui_goi ;;
          hl)
            lt_huan_luyen; rc=$?
            case $rc in 3|4) return 0 ;; esac
            # Huan luyen dung engine cua may nay: LT_O da bi xoa (lt_dung_cho_het) -> vong sau khoi dong engine moi
            [ -z "$LT_O" ] && them="" ;;
        esac ;;
    esac
  done
}

# May vua duoc cua so nay nhan lai (vong lap lien tuc truoc do bi dong giua chung): dung mem moi engine con chay, gom van, sinh tiep.
lt_nhan_may() {
  local o pid
  td_in "nhận lại máy: dừng mềm engine còn chạy, gom ván rồi sinh tiếp"
  td_ghi lt=1 gen="$(td_gen)" buoc=sinh van=0 da_goi=0 phuc_vu="$(lt_yc)"
  lt_dung_cho_het 480
  read -r o pid <<<"$(td_dang_chay)"
  if [ -n "$o" ] && [ "$(ssh_colab "python3 $LOGD/fz_may.py trang_thai $o $pid" 2>/dev/null)" = chay ]; then
    case $o in 04|08) td_cho_o_la "$o" "$pid" ;; *) td_xem "$o" "$pid" 20 ;; esac
  fi
  lt_gui_goi || lt_gui_goi
}

# Cho toi lich xin may chung (thoi som khi dung tay).
lt_cho_xin() { td_cho_lich td_dung_ca; }

# ---------------- Bat dau / vong chinh ----------------
lt_bat_dau() {
  local g x k f n_cs khac=() hoi_cu=()
  mkdir -p "$TD"
  clear
  echo "${M_DAM}== Vòng lặp LIÊN TỤC ==${M_HET}"
  g=$(td_gen)
  [[ "$g" =~ ^[0-9]+$ ]] || { echo "[!] Không đọc được GEN_CURRENT trong 00_cau_hinh.py"; return 1; }
  if [ "$g" -ge "$TD_GEN_CUOI" ]; then
    echo "${M_DO}[!] Đời hiện tại $g >= $TD_GEN_CUOI.${M_HET} Release NN_Model chứa tối đa $TD_REL_TOI_DA tệp: không chạy tiếp."
    return 1
  fi
  if [ -z "$(td_rel_nn)" ]; then echo "[!] 00_cau_hinh.py chưa có dòng REL_NN"; return 1; fi
  for f in 02_*.py 02c_*.py 04l_*.py 07_*.py 08_*.py; do
    [ -n "$(ls "$D"/$f 2>/dev/null)" ] || { echo "[!] Thiếu ô $f trên điện thoại -- chạy: bash ~/lay_ve.sh"; return 1; }
  done
  for f in ~/fz_tu_dong.py ~/fz_han_muc.py ~/fz_nhan_may.py ~/fz_giu_may.py ~/fz_colab.py ~/fz_may.py; do
    [ -f "$f" ] || { echo "[!] Thiếu $f -- chạy: bash ~/lay_ve.sh"; return 1; }
  done
  grep -q 'goi_nhan' ~/fz_tu_dong.py && grep -q 'sinh_dang_chay' ~/fz_may.py || { echo "[!] ~/fz_tu_dong.py / ~/fz_may.py là bản cũ -- chạy: bash ~/lay_ve.sh"; return 1; }
  # Hai vong lap (cu theo doi / moi lien tuc) khong chay cung luc: tranh nhau tai khoan, GEN_CURRENT, khoa.
  for f in $(td_cac_cua_so); do
    [ "$f" = "$TD_W" ] && continue
    khac+=("${f##*/w_}")
    grep -q '^lt=1' "$f" || hoi_cu+=("${f##*/w_}")
  done
  if [ ${#hoi_cu[@]} -gt 0 ]; then
    echo "${M_DO}[!] Đang có cửa sổ của vòng lặp CŨ (theo đời, mục v): pid ${hoi_cu[*]}${M_HET}"
    echo "    Dừng mềm chúng trước (Ctrl+C -> s), đợi trả máy hết, rồi mở lại w."
    return 1
  fi
  echo "Đời mạng hiện tại (ô 00): ${M_DAM}$g${M_HET}   ${M_MO}(đổi: menu g)${M_HET}"
  [ ${#khac[@]} -gt 0 ] && echo "${M_VANG}Đang có ${#khac[@]} cửa sổ khác chạy vòng lặp liên tục${M_HET}"
  if ! command -v gh >/dev/null || ! gh auth status >/dev/null 2>&1; then
    echo "${M_VANG}[!] Chưa đăng nhập GitHub (gh): bước đưa mạng lên GitHub sẽ đứng chờ.${M_HET}"
  fi
  read -rp "Số ván MỚI mỗi lượt huấn luyện (Enter = $(td_muc)): " x
  if [ -n "$x" ]; then so_nguyen "$x" || { echo "[!] Không phải số"; return 1; }; echo $((10#$x)) > "$TD_MUC_F"; fi
  n_cs=$(cat "$LT_THE_F" 2>/dev/null)
  if [[ "$n_cs" =~ ^[0-9]+$ ]] && [ $((10#$n_cs)) -ge 100000 ]; then
    echo "Cửa sổ huấn luyện hiện: ${M_DAM}CỐ ĐỊNH $((10#$n_cs)) thế${M_HET}"
  else
    echo "Cửa sổ huấn luyện hiện: ${M_DAM}TỰ CANH${M_HET} = $(( $(lt_dung_lai10) / 10 )),$(( $(lt_dung_lai10) % 10 )) lần số thế mới của mỗi lượt ≈ $(lt_the) thế"
  fi
  echo "  Enter = giữ nguyên · số nhỏ hơn 100 (vd 4 hoặc 3.5) = tự canh sao cho mỗi thế được dùng lại chừng đó lần · số từ 100000 = cửa sổ cố định (số thế)"
  read -rp "Cửa sổ huấn luyện: " x
  if [ -n "$x" ]; then
    if [[ "$x" =~ ^[0-9]+$ ]] && [ $((10#$x)) -ge 100000 ]; then lt_ghi_tep "$LT_THE_F" $((10#$x))
    elif [[ "$x" =~ ^([0-9]+)(\.[0-9])?$ ]] && [ $((10#${BASH_REMATCH[1]})) -ge 1 ] && [ $((10#${BASH_REMATCH[1]})) -lt 100 ]; then lt_ghi_tep "$LT_DUNG_LAI_F" "$x"; rm -f "$LT_THE_F"
    else echo "[!] Nhập số lần dùng lại (1 đến 99, vd 4) hoặc số thế từ 100000"; return 1; fi
  fi
  hoi_chua_phut || return 1
  td_hoi_arena || return 1
  # Nhap du lieu cua vong lap cu (thu muc games_gen<k>/ cua 4 doi gan nhat) thanh goi, mot lan.
  if [ -z "$(ls "$LT_GOI"/goi_*.zip 2>/dev/null)" ]; then
    echo "${M_MO}Chưa có gói nào: nhập dữ liệu vòng lặp cũ (games_gen<đời>/ của $TD_SO_DOI đời gần nhất) làm cửa sổ ban đầu${M_HET}"
    python ~/fz_tu_dong.py nhap_cu "$TAI" "$g" "$TD_SO_DOI" | sed 's/^/    /'
  fi
  if [ ! -f "$LT_MOC_F" ]; then
    lt_ghi_tep "$LT_MOC_F" "$(cut -d' ' -f3 <<<"$(lt_goi_moi 0)")"
    echo "Mốc huấn luyện đặt ở gói cuối cùng hiện có (dữ liệu đã nhập tính là cũ, cần $(td_muc) ván mới)."
  fi
  read -r k x f <<<"$(lt_goi_moi "$(lt_moc)")"
  echo "---"
  echo "Gói trên điện thoại: $(ls "$LT_GOI"/goi_*.zip 2>/dev/null | wc -l) · ván mới từ lượt huấn luyện trước: ${M_DAM}$k${M_HET}/$(td_muc)"
  read -rp "Enter = bắt đầu, n = thôi: " x || { echo; return 1; }
  [ -z "$x" ] || return 1
  td_don_dep "$g"
  [ ${#khac[@]} -eq 0 ] && rm -f "$TD_DUNG" "$TD_XIN_SAU" "$LT_YC_F"
  LT_T_BD=$(date +%s)
  return 0
}
lt_vong() {
  local rc
  KHONG_HOI=1; bat_ctrl_c
  lt_vong_chinh "$@"; rc=$?
  KHONG_HOI=; bat_ctrl_c
  return $rc
}
lt_vong_chinh() {
  local g rc
  TD_THOAT=0; TD_LOI=0; TD_VAI=; TD_NHAN_LAI=0
  LT_O=; LT_RUN=; LT_PID=; LT_NET=; LT_VAN=0; LT_DA_GOI=0; LT_CRASH=0
  rm -f "$TD_DUNG_RIENG"
  [ -s "$TD/nhat_ky.txt" ] && [ "$(wc -l < "$TD/nhat_ky.txt")" -gt 4000 ] &&
    { tail -n 2000 "$TD/nhat_ky.txt" > "$TD/nhat_ky.tmp" && mv "$TD/nhat_ky.tmp" "$TD/nhat_ky.txt"; }
  trap 'lt_hl_tra; rm -f "$CS/$$" "$TD_W" "$TD/.w_$$.tmp" "$TD/.luong_$$" "$TD_DUNG_RIENG"; rm -rf "$TD/o_$$"' EXIT
  lt_bat_dau || return
  NGAT=0
  td_ranh
  td_ghi lt=1 gen="$(td_gen)" buoc=xin van=0 da_goi=0 phuc_vu="$(lt_yc)"
  while [ $TD_THOAT = 0 ] && [ $TD_LOI = 0 ]; do
    lt_nap_lai
    declare -F quet_mo_coi_tat_ca >/dev/null && quet_mo_coi_tat_ca   # may mo coi con sot tu cac lan xin hong (ghi nho o $TD/xin_hong_*, het han sau FZ_MO_COI_TTL); khong co thi khong ton gi
    if [ $NGAT = 1 ]; then td_hoi_ngat; [ $TD_THOAT = 1 ] && break; fi
    g=$(td_gen)
    if [ "${g:-0}" -ge "$TD_GEN_CUOI" ] && ! lt_dung_hieu_luc; then
      td_in "${M_VANG}đã tới đời $g (giới hạn $TD_GEN_CUOI)${M_HET}: Release GitHub chứa tối đa $TD_REL_TOI_DA tệp -> dừng vòng lặp"
      : > "$TD_DUNG"
    fi
    if td_dung_ca && [ "$TD_VAI" != huan_luyen ]; then
      if lt_dung_hieu_luc; then td_in "dừng mềm: trả máy, thoát vòng lặp"
      else td_in "dừng mềm RIÊNG cửa sổ này: trả máy, thoát (cửa sổ khác vẫn chạy)"; fi
      if [ $TD_CO_MAY = 1 ]; then lt_ket_may; fi
      local ds=()
      while lt_dung_hieu_luc; do
        td_khoa_chon; td_ds_tk
        if ! td_nhan_lai; then td_mo_khoa_chon; break; fi
        td_mo_khoa_chon
        TD_NHAN_LAI=0; lt_nhan_may
        td_tra
      done
      break
    fi
    if [ $TD_CO_MAY = 0 ]; then
      td_ghi lt=1 gen="$g" buoc=xin van=0 da_goi=0
      td_xin_mot_vong || { lt_cho_xin; continue; }
      LT_O=; LT_RUN=; LT_PID=; LT_NET=; LT_CRASH=0
    fi
    if [ $TD_NHAN_LAI = 1 ]; then TD_NHAN_LAI=0; lt_nhan_may; continue; fi
    # May san sang cho mang g (02: ma nguon, binary, mang), roi arena (neu den luot) hoac sinh du lieu lien tuc.
    td_chuan_bi "$g"; rc=$?
    case $rc in 0) TD_CB_LOI=0 ;; 2) TD_LOI=1; continue ;; 3) td_mat_may; continue ;; 4) break ;; *) td_chuan_bi_loi; continue ;; esac
    td_dung_ca && continue
    lt_sinh; rc=$?
    if [ $rc = 10 ]; then
      # Mang moi co arena: dung engine, gui goi, danh arena roi sinh tiep.
      g=$(td_gen)
      td_in "arena cho mạng gen$g: dừng sinh dữ liệu, gửi gói rồi đấu"
      lt_dung_cho_het 480; lt_gui_goi || lt_gui_goi
      td_arena "$g"
    fi
  done
  # Dung vi loi ma con giu may: gom nốt van roi tra (loi gom -> giu may de lay tay).
  if [ $TD_LOI = 1 ] && [ $TD_CO_MAY = 1 ]; then
    if lt_dung_cho_het 480 && lt_gui_goi; then td_tra
    else td_in "${M_DO}[!] chưa gom được ván -- GIỮ máy (lấy tay: fz -> d, rồi t để trả)${M_HET}"; fi
  fi
  rm -f "$TD_W"
  echo
  if [ $TD_THOAT = 1 ] && [ $TD_CO_MAY = 1 ]; then
    td_in "${M_VANG}thoát -- máy của $(ten_tk "$TK") VẪN CHẠY (engine tiếp tục, ván chưa gửi sẽ mất nếu Colab thu hồi)${M_HET}"
    td_in "(mở lại w để nhận lại, hoặc t để trả)"
  elif [ $TD_LOI = 1 ]; then
    td_in "${M_DO}vòng lặp dừng vì lỗi ở trên${M_HET}"
    [ $TD_CO_MAY = 1 ] && td_in "máy của $(ten_tk "$TK") vẫn giữ (t để trả)"
  else
    td_in "vòng lặp liên tục đã dừng"
  fi
}
