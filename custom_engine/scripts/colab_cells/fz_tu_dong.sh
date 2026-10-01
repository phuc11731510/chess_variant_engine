# fz_tu_dong.sh -- VONG LAP TU DONG cua menu fz: sinh du lieu -> gop -> huan luyen -> len doi, lap lai.
# menu.sh SOURCE tep nay (muc v, hoac `fz tu_dong`) va dung lai ham cua menu (xin_may, khoi_dong_ssh,
# ssh_colab, tai_ve, tai_len, tai_theo_o, ...). Tinh toan (xep tai khoan, gop du lieu): ~/fz_tu_dong.py.
#
# Moi cua so Termux chay vong lap = lo tron MOT may (mot tai khoan -- Colab mien phi khong cho hai may
# mot tai khoan). Hai cua so = toi da hai may, phoi hop qua tep tren dien thoai:
#   ~/.fz_tk/.tu_dong/w_<pid>     trang thai tung cua so (doi, buoc, so van da xong tren may cua no)
#   ~/.fz_tk/.tu_dong/may_<tk>    may cua vong lap dang giu o tai khoan <tk> (mo lai vong lap -> nhan lai)
#   ~/.fz_tk/.tu_dong/hl_<G>/     khoa "cua so dang huan luyen doi G"
#   ~/.fz_tk/.tu_dong/dung_tay    dung mem ca vong lap (Ctrl+C -> s o bat ky cua so nao)
#   Download/FairyZero/games_gen<G>_<N>.zip   goi van, ten tich luy (o 06, xem tai_ve)
#
# Mot doi G (GEN_CURRENT cua o 00 luc bat dau; sau moi doi vong lap tu tang):
#   1. Chua co may: xin T4 theo thu tu fz_tu_dong.py xep (da nap lai / xanh / chua chup ...), bo tai
#      khoan dang mo o cua so khac; khong xin duoc thi theo LICH CHUNG (td_lich: gio nap lai som nhat,
#      HET khong ro gio nap: moi gio; con tai khoan thu duoc: 10 phut) -- chi mot cua so xin moi lan.
#   2. 02 (neu may moi) -> 04 (SECS = han muc T4 - so phut chua, GAMES = so van con thieu) -> 06 ->
#      tai ve. Tong = so lon nhat trong ten goi + van DA XONG tren cac may dang chay; du muc tieu thi
#      moi cua so tao tep dung mem tren may minh (engine choi not van do roi thoat nhu het SECS).
#   3. Du muc tieu va moi may da tai ve: cua so co may nhieu han muc nhat huan luyen (cua so kia tra
#      may, cho). Gop du lieu (fz_tu_dong.py gop), can >= 20 phut T4 LUC SAP TAI LEN, tai len, 07,
#      tai mang moi ve. May mat giua chung -> xin may moi ngay, roi cu 10 phut mot lan, lam lai.
#   4. gh release upload -> GitHub Release (REL cua o 00), GEN_CURRENT + 1.
#   0. ARENA (tuy chon, hoi luc bat dau: day doi a b c ...): khi doi hien tai G la mot so trong day
#      (khong phai so dau), truoc khi sinh du lieu doi G: o 08 cho genG dau voi doi dung truoc no
#      trong day, tong TD_AR_VAN van (mac dinh 100) chia cho cac may nhu o 04 (dem ca van dang do,
#      du thi dung mem, khong thua ca loat van song song). Ket qua tung may cong vao
#      Download/FairyZero/arena/gen<G>_vs_gen<a>.txt; du van -> dong XONG = arena do da xong, vong lap
#      khong lam lai (dung mem giua chung -> lan sau choi not phan con thieu).
TD=$TKG/.tu_dong
TD_W=$TD/w_$$
TD_MUC_F=$TD/.muc_tieu
TD_DUNG=$TD/dung_tay
TD_PHUT_HL=20      # phut T4 toi thieu luc sap tai du lieu len de huan luyen
TD_PHUT_SINH=20    # sau khi tru so phut chua, con it hon chung nay phut choi thi khong chay 04, tra may
TD_SO_DOI=4        # so doi du lieu moi lan huan luyen: doi hien tai + 3 doi truoc (tu doi 12, 2026-09-29; truoc la 3)
TD_CO_MAY=0        # cua so nay dang giu may (tai khoan $TK, ten $S)
TD_THOAT=0         # q: thoat vong lap o cua so nay, may van chay
TD_LOI=0           # loi khong tu sua duoc -> dung vong lap
TD_VAI=            # huan_luyen: cua so nay dang lo giai doan 3-4
TD_NHAN_LAI=0      # vua nhan lai may cua vong lap truoc -> xem may dang lam gi truoc
TD_AR_DAY_F=$TD/.arena_day   # day doi arena (vd "11 12 15"), hoi luc bat dau
TD_AR_VAN_F=$TD/.arena_van   # so van moi arena
TD_AR_DIR=$TAI/arena         # ket qua arena cua vong lap (tren dien thoai, xem duoc)
TD_KIEU=           # o dang xem la arena (td_xem / td_can_dung dem theo arena)
TD_AR_A=           # doi doi thu cua arena dang chay
# Tep dung mem va duong dan ma nguon tren may: PHAI khop o 04 (DUNG_MEM) va o 00 (E).
E_CL=$(doc "$D/00_cau_hinh.py" 2>/dev/null | sed -n 's/^E *= *"\([^"]*\)".*/\1/p')
E_CL=${E_CL:-/content/chess_variant_engine/custom_engine}

td_in() { echo "${M_LAM}[tự động $(date +%H:%M)]${M_HET} $*"; }
td_gen() { doc "$D/00_cau_hinh.py" 2>/dev/null | sed -n 's/^GEN_CURRENT *= *\([0-9]*\).*/\1/p' | head -1; }
td_muc() { local n; n=$(cat "$TD_MUC_F" 2>/dev/null); so_nguyen "$n" && echo $((10#$n)) || echo 1000; }
td_home() { if [ -n "$1" ]; then echo "$TKG/$1"; else echo "$HOME"; fi; }
td_song() { tr '\0' ' ' 2>/dev/null < "/proc/$1/cmdline" | grep -q 'menu\.sh'; }

# Trang thai cua so nay: dong "khoa=gia tri" trong $TD_W (ghi qua tep tam an + mv: doc khong do dang).
td_ghi() {
  local kv t=$TD/.w_$$.tmp
  cat "$TD_W" > "$t" 2>/dev/null || : > "$t"
  for kv in "$@"; do sed -i "/^${kv%%=*}=/d" "$t"; echo "$kv" >> "$t"; done
  mv "$t" "$TD_W"
}
td_doc() { sed -n "s/^$2=//p" "$1" 2>/dev/null | tail -1; }
# Tep trang thai cua cac cua so vong lap CON SONG (don tep cua cua so da dong).
td_cac_cua_so() {
  local f pid
  for f in "$TD"/w_*; do
    pid=${f##*/w_}
    [[ "$pid" =~ ^[0-9]+$ ]] || continue
    if td_song "$pid"; then echo "$f"; else rm -f "$f"; fi
  done
}
# Cua so nay khong giu tai khoan nao (cua so khac duoc xin may o moi tai khoan).
td_ranh() { TD_CO_MAY=0; mkdir -p "$CS" && echo "@/:$S" > "$CS/$$"; }

# Khoa dat ten goi van (chung voi tai_ve): tong + so van tung may doc cung mot luc.
td_khoa() {
  local i
  for i in 1 2; do
    for _ in $(seq 50); do mkdir "$TAI/.khoa_dat_ten" 2>/dev/null && return 0; sleep 0.2; done
    rmdir "$TAI/.khoa_dat_ten" 2>/dev/null    # 10 giay khong mo = sot lai (giu khoa chi vai phan giay)
  done
  return 1
}
td_van_0() { td_ghi van=0; }     # TAI_VE_MOC: goi vua co ten tich luy -> van cua may nay da nam trong ten
# Van dang do tren may cua cua so (tep $1) dang o buoc sinh: engine luon giu dung `par` van cung luc
# (xong van nao mo van moi ngay) cho toi khi het so van duoc giao (`giao`) -> min(par, giao - van).
# Sau khi da gui dung mem (dung_van, dung_dang ghi luc gui): khong mo van moi nua -> dung_dang tru di
# so van xong tu luc do. Khong biet cau hinh (may nhan lai tu vong lap cu, o 04 ban cu) -> 0.
td_dang_do() {
  local f=$1 v par giao dv dd d
  v=$(td_doc "$f" van); v=${v:-0}
  dd=$(td_doc "$f" dung_dang)
  if [ -n "$dd" ]; then
    dv=$(td_doc "$f" dung_van); d=$((dd - (v - ${dv:-0})))
  else
    par=$(td_doc "$f" par); giao=$(td_doc "$f" giao)
    [ -n "$par" ] && [ -n "$giao" ] || { echo 0; return; }
    d=$((giao - v)); [ $d -gt "$par" ] && d=$par
  fi
  [ $d -gt 0 ] && echo $d || echo 0
}
# Tong van doi $1: so lon nhat trong ten goi da tai + van da xong VA dang do tren may cac cua so dang
# sinh / tai. Tinh ca van dang do: du muc tieu thi dung mem LUC DO, van dang do choi not la vua du
# (khong thua ca loat van song song cua moi may), va cua so khac khong nhan lai phan van dang choi.
td_tong() {
  local f t=0 v co=1
  td_khoa && co=0
  for f in $(td_cac_cua_so); do
    [ "$(td_doc "$f" gen)" = "$1" ] || continue
    case $(td_doc "$f" buoc) in
      sinh) v=$(td_doc "$f" van); t=$((t + ${v:-0} + $(td_dang_do "$f"))) ;;
      tai) v=$(td_doc "$f" van); t=$((t + ${v:-0})) ;;
    esac
  done
  t=$((t + $(tong_tich_luy "$1")))
  [ $co = 0 ] && rmdir "$TAI/.khoa_dat_ten" 2>/dev/null
  echo $t
}
td_co_mang() { [ -s "$TAI/gen$1.onnx" ] && [ -s "$TAI/gen$1.pt" ]; }
# Den luot giai doan 3-4 cua doi $1: da co mang doi sau tren dien thoai (chi con tai len GitHub), da co
# goi gop, hoac so van DA TAI VE du muc tieu.
td_toi_luot_hl() {
  td_co_mang $(($1 + 1)) || [ -f "$TAI/games_gen$1.zip" ] || [ "$(tong_tich_luy "$1")" -ge "$(td_muc)" ]
}

# Ngu $1 giay, Ctrl+C -> hoi (s / q / Enter). 1 = nguoi dung chon q.
td_ngu() {
  local i
  for ((i = 0; i < $1; i++)); do
    sleep 1
    if [ $NGAT = 1 ]; then td_hoi_ngat; [ $TD_THOAT = 1 ] && return 1; fi
  done
  return 0
}
td_hoi_ngat() {
  local x
  NGAT=0
  echo
  echo "${M_DAM}== Vòng lặp tự động ==${M_HET}"
  echo " ${M_DAM}s${M_HET}      dừng mềm CẢ vòng lặp (mọi"
  echo "        cửa sổ): chơi nốt ván dở, gom,"
  echo "        tải về, trả máy"
  echo " ${M_DAM}q${M_HET}      thoát ở cửa sổ này -- máy"
  echo "        và ô trên Colab VẪN CHẠY (tiêu"
  echo "        hạn mức); mở lại v để nhận lại"
  echo " ${M_DAM}Enter${M_HET}  tiếp tục"
  read -rp "Chọn: " x
  case "$x" in
    s|S) : > "$TD_DUNG"; td_in "đã yêu cầu dừng mềm" ;;
    q|Q) TD_THOAT=1 ;;
  esac
  NGAT=0
}

# Giay T4 con chay duoc cua tai khoan dang giu may (chua tru so phut chua). Rong = khong doc duoc.
td_giay_t4() {
  local may g
  may=$(colab status -s "$S" 2>/dev/null | sed -n 's/.*Hardware: *\([^ |]*\).*/\1/p' | head -1)
  g=$(py_colab ~/fz_han_muc.py --may "$may" --giay-t4 2>/dev/null)
  [[ "$g" =~ ^[0-9]+$ ]] && echo "$g"
}
# 0 = may cua cua so nay con (hoac mat mang, khong biet), 1 = da mat.
td_con_may() { py_colab ~/fz_nhan_may.py con "$S" >/dev/null 2>&1; [ $? != 1 ]; }
td_mat_may() {
  td_in "${M_DO}máy của $(ten_tk "$TK") đã mất${M_HET}"
  td_in "(Colab thu hồi / hết hạn mức -- ván chưa tải về của máy đó mất)"
  td_ghi van=0 buoc=xin
  rm -f "$TD/may_$(ten_tk "$TK")"
  td_ranh
}
# Tra may cua cua so nay (chup han muc truoc: con giu may thi may chu con tra han muc).
td_tra() {
  local ds x ep
  [ $TD_CO_MAY = 1 ] || return 0
  chup_han_muc "$TK"
  mapfile -t ds < <(colab sessions 2>/dev/null | grep "^\[$S\]")
  if [ ${#ds[@]} -eq 0 ]; then       # phien bi CLI xoa ma may con: tra theo endpoint da ghi
    ep=$(cat "$TKH/.config/colab-cli/fz_may_$S.txt" 2>/dev/null)
    [ -n "$ep" ] && mapfile -t ds < <(colab sessions 2>/dev/null | grep "^\[?\] $ep ")
  fi
  for x in "${ds[@]}"; do tra_mot "$x"; done
  rm -f "$TD/may_$(ten_tk "$TK")"
  td_in "đã trả máy của $(ten_tk "$TK")"
  td_ranh
}

# Khoa chon tai khoan: hai cua so khong cung luc chon (khong xin trung mot tai khoan).
td_khoa_chon() {
  local p
  while ! mkdir "$TD/.khoa_chon" 2>/dev/null; do
    p=$(cat "$TD/.khoa_chon/pid" 2>/dev/null)
    if [ -n "$p" ] && ! td_song "$p"; then rm -rf "$TD/.khoa_chon"; continue; fi
    sleep 1
  done
  echo $$ > "$TD/.khoa_chon/pid"
}
td_mo_khoa_chon() { rm -rf "$TD/.khoa_chon"; }

# Mot vong xin may: nhan lai may cua vong lap truoc (neu co), roi thu tung tai khoan theo thu tu
# fz_tu_dong.py xep toi khi xin duoc. 0 = co may (cua so nay da chuyen sang tai khoan do).
# Nhan lai mot may cua vong lap ma khong cua so nao dang lo (cua so do bi dong / Termux bi giet).
# Goi khi da giu khoa chon. 0 = da nhan (cua so nay chuyen sang tai khoan do).
td_nhan_lai() {
  local tk ten rc
  for tk in "${ds[@]}"; do
    ten=$(ten_tk "$tk")
    [ -f "$TD/may_$ten" ] && tk_dang_nhap "$tk" && [ -z "$(cua_so_khac "$tk")" ] || continue
    dat_tk "$tk"
    py_colab ~/fz_nhan_may.py kiem "$S" >/dev/null 2>&1; rc=$?
    if [ $rc = 0 ]; then
      ghi_cua_so; TD_CO_MAY=1; TD_NHAN_LAI=1
      td_in "nhận lại máy của vòng lặp trước: $ten"
      return 0
    fi
    [ $rc = 1 ] && rm -f "$TD/may_$ten"
  done
  return 1
}
td_ds_tk() { mapfile -t ds < <(echo; for tk in "$TKG"/*/; do [ -d "$tk" ] && basename "$tk"; done); }
# LICH XIN MAY CHUNG cho moi cua so: $TD/.xin_sau = "<giay epoch>\t<ly do>" -- truoc luc do khong cua
# so nao xin. Mot vong xin khong duoc (cua so nao lam truoc, trong khoa chon) ghi luc nen xin lai
# (fz_tu_dong.py hen: gio nap lai som nhat da biet; HET khong ro gio nap: moi gio thu mot lan; con
# tai khoan thu duoc: 10 phut). Cac cua so khac cho dung luc do -> chi MOT cua so xin moi lan.
TD_XIN_SAU=$TD/.xin_sau
td_lich() { local t; t=$(cut -f1 "$TD_XIN_SAU" 2>/dev/null); [[ "$t" =~ ^[0-9]+$ ]] && echo "$t" || echo 0; }
td_xin_mot_vong() {
  local ds=() muc=() tk ten loai mo_ta rc
  mkdir -p "$TD"
  td_khoa_chon
  td_ds_tk
  if td_nhan_lai; then td_mo_khoa_chon; return 0; fi
  # Chua toi lich (cua so khac vua xin khong duoc): khong xin.
  if [ "$(date +%s)" -lt "$(td_lich)" ]; then td_mo_khoa_chon; return 1; fi
  for tk in "${ds[@]}"; do
    tk_dang_nhap "$tk" && muc+=("$(ten_tk "$tk")|$(td_home "$tk")|$(cat "$TD/thu_$(ten_tk "$tk")" 2>/dev/null)")
  done
  while IFS=$'\t' read -r -u 3 ten loai mo_ta; do
    if [ "$loai" = bo ]; then echo "   ${M_MO}bỏ qua $ten: $mo_ta${M_HET}"; continue; fi
    tk=$(tim_tk "$ten")
    if [ -n "$(cua_so_khac "$tk")" ]; then echo "   ${M_MO}bỏ qua $ten: đang mở ở cửa sổ khác${M_HET}"; continue; fi
    dat_tk "$tk"
    if [ -n "$(colab sessions 2>/dev/null | grep '^\[' | grep -v '^\[colab\]')" ]; then
      echo "   ${M_MO}bỏ qua $ten: đang giữ máy (không phải của vòng lặp)${M_HET}"; continue
    fi
    ghi_cua_so                                  # danh dau truoc: cua so khac bo qua tai khoan nay
    date +%s > "$TD/thu_$ten"
    td_in "xin T4: ${M_DAM}$ten${M_HET} ($mo_ta)"
    if xin_may T4; then
      TD_CO_MAY=1
      date +%s > "$TD/may_$ten"
      td_mo_khoa_chon; return 0
    fi
    td_ranh
  done 3< <(python ~/fz_tu_dong.py xep "${muc[@]}")
  # Ca vong khong xin duoc: dat lich chung (thu_<ten> vua ghi o tren -> moc "moi gio" dung).
  muc=()
  for tk in "${ds[@]}"; do
    tk_dang_nhap "$tk" && muc+=("$(ten_tk "$tk")|$(td_home "$tk")|$(cat "$TD/thu_$(ten_tk "$tk")" 2>/dev/null)")
  done
  if ! python ~/fz_tu_dong.py hen "${muc[@]}" > "$TD_XIN_SAU.t" 2>/dev/null || [ ! -s "$TD_XIN_SAU.t" ]; then
    printf '%s\t%s\n' $(( $(date +%s) + 600 )) "10 phút (không tính được lịch)" > "$TD_XIN_SAU.t"
  fi
  mv "$TD_XIN_SAU.t" "$TD_XIN_SAU"
  td_mo_khoa_chon
  return 1
}
# Cho toi lich xin may chung. $1 = ham "thoi cho som" (tuy chon, 0 = thoi). 1 = nguoi dung chon q.
td_cho_lich() {
  local t bao=0
  while :; do
    t=$(td_lich)
    [ "$(date +%s)" -ge "$t" ] && return 0
    if [ $bao = 0 ]; then
      td_in "chưa xin được máy -- xin lại lúc ${M_DAM}$(date -d "@$t" +%H:%M 2>/dev/null || echo "?")${M_HET} ($(cut -f2 "$TD_XIN_SAU" 2>/dev/null))"
      bao=1
    fi
    td_ngu 10 || return 1
    [ -n "${1:-}" ] && "$1" && return 0
  done
}

# Xem log o $1 (pid $2) den khi o ket thuc; $3 = chi in tu $3 dong cuoi. O 04: dem van ([selfplay]
# d/N), moi 15 giay xem tong -- du muc tieu (hoac dung tay) thi tao tep dung mem tren may. Luong log
# qua MOT ssh (Colab chi cho mot ssh moi may): gui lenh thi ngat luong, gui, roi noi lai.
# 0 = o ket thuc, 3 = mat may, 4 = nguoi dung chon q.
td_xem() {
  local o=$1 pid=$2 them=${3:-} fifo=$TD/.luong_$$ sp fd dong rc t=$SECONDS lan=0 bd=0 ly_do cho
  local da_dung=0
  while :; do
    rm -f "$fifo"; mkfifo "$fifo" || return 1
    NGAT=0
    ssh_colab "python3 $LOGD/fz_may.py theo_doi $o $pid $them" > "$fifo" 2>/dev/null &
    sp=$!
    command exec {fd}<"$fifo" || { td_giet "$sp"; td_ngu 5 || return 4; continue; }
    ly_do=het
    while :; do
      if IFS= read -r -t 15 -u "$fd" dong; then
        printf '%s\n' "$dong"; lan=0
        [ "$o" = 04 ] && [[ "$dong" =~ ^\[selfplay\]\ ([0-9]+)/ ]] && td_ghi van="${BASH_REMATCH[1]}"
        [ "$o" = 08 ] && [[ "$dong" =~ ^\ \ game\ ([0-9]+)/ ]] && td_ghi van="${BASH_REMATCH[1]}"
      else
        rc=$?
        [ -n "$dong" ] && printf '%s' "$dong"
        [ $NGAT = 1 ] && { ly_do=ngat; break; }
        [ $rc -gt 128 ] || break                      # het du lieu: ssh da thoat
      fi
      if { [ "$o" = 04 ] || [ "$o" = 08 ]; } && [ $da_dung = 0 ] && [ $((SECONDS - t)) -ge 15 ]; then
        t=$SECONDS
        td_can_dung && { ly_do=dung; break; }
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
    them=3                    # noi lai sau khi chu dong ngat: vai dong cuoi la du (khoi in lai log)
    case $ly_do in
      ngat) td_hoi_ngat; [ $TD_THOAT = 1 ] && return 4 ;;
      dung) td_gui_dung && da_dung=1 ;;
      het)
        them=20
        td_con_may || return 3
        [ $lan = 0 ] && bd=$SECONDS
        lan=$((lan + 1)); cho=$((lan * 5)); [ $cho -gt 30 ] && cho=30
        echo "[mất kết nối tới máy -- nối lại sau $cho giây (lần $lan) · ô trên Colab VẪN CHẠY]"
        td_ngu $cho || return 4 ;;
    esac
  done
}
# Giet tien trinh $1 (vo bash chay ssh_colab o nen) cung cac con truc tiep cua no (ssh). Doc /proc
# bang bash, khong can pkill (Termux co the khong co san).
td_giet() {
  local f s a
  for f in /proc/[0-9]*/stat; do
    read -r s < "$f" 2>/dev/null || continue
    s=${s##*) }; a=($s)                  # sau "(ten)": trang thai, ppid, ...
    [ "${a[1]}" = "$1" ] && { f=${f%/stat}; kill -TERM "${f#/proc/}" 2>/dev/null; }
  done
  kill -TERM "$1" 2>/dev/null
}
# Nen dung mem 04 chua (goi trong luc xem log): dung tay, hoac tong du muc tieu. In tong moi phut.
td_can_dung() {
  local tong muc
  [ -f "$TD_DUNG" ] && return 0
  if [ "$TD_KIEU" = arena ]; then
    tong=$(td_ar_tong "$TD_G" "$TD_AR_A"); muc=$(td_ar_van)
    if [ "$tong" != "${TD_TONG_IN:-}" ] && [ $((SECONDS - ${TD_LUC_IN:-0})) -ge 60 ]; then
      td_in "arena gen$TD_G vs gen$TD_AR_A: ${M_DAM}$tong/$muc${M_HET} ván (đã ghi $(td_ar_da "$TD_G" "$TD_AR_A"), tính cả ván đang chơi dở)"
      TD_TONG_IN=$tong; TD_LUC_IN=$SECONDS
    fi
    [ "$tong" -ge "$muc" ]; return
  fi
  tong=$(td_tong "$TD_G"); muc=$(td_muc)
  if [ "$tong" != "${TD_TONG_IN:-}" ] && [ $((SECONDS - ${TD_LUC_IN:-0})) -ge 60 ]; then
    td_in "đời $TD_G: ${M_DAM}$tong/$muc${M_HET} ván (đã tải $(tong_tich_luy "$TD_G"), tính cả ván đang chơi dở)"
    TD_TONG_IN=$tong; TD_LUC_IN=$SECONDS
  fi
  [ "$tong" -ge "$muc" ]
}
# Tao tep dung mem ma engine dang xem (doc tu dong lenh cua engine, nhu o 09b). 0 = da gui.
td_gui_dung() {
  local i out
  for i in 1 2 3; do
    out=$(ssh_colab "p=\$(pgrep -af '[c]ustom_engine.* --(selfplay|arena)' | sed -n 's/.* --stop-file \([^ ]*\).*/\1/p' | head -1); if [ -n \"\$p\" ]; then touch \"\$p\" && echo FZ_DA_DUNG; else echo FZ_KHONG_CHAY; fi" 2>/dev/null)
    if grep -q FZ_DA_DUNG <<<"$out"; then
      td_ghi dung_van="$(td_doc "$TD_W" van)" dung_dang="$(td_dang_do "$TD_W")"
      td_in "${M_VANG}dừng mềm máy $(ten_tk "$TK")${M_HET}: $([ -f "$TD_DUNG" ] && echo "dừng tay" || { [ "$TD_KIEU" = arena ] && echo "đủ $(td_ar_van) ván arena" || echo "đủ $(td_muc) ván"; }) -- ván dở chơi nốt"
      return 0
    fi
    grep -q FZ_KHONG_CHAY <<<"$out" && return 0         # engine vua xong
    sleep 5
  done
  td_in "[!] chưa gửi được lệnh dừng mềm -- thử lại sau"
  return 1
}

# Chay o $1 (tep $2) nen tren may cua cua so nay va xem den khi xong. 0 = xong, 1 = khong khoi dong
# duoc, 3 = mat may, 4 = q.
td_chay() {
  local out pid ban
  kiem_may >/dev/null 2>&1
  out=$(khoi_dong_ssh "$1" "$2" 2>&1) || { td_con_may || return 3; echo "$out" | tail -3; return 1; }
  ban=$(sed -n 's/^FZ_BAN=//p' <<<"$out")
  if [ -n "$ban" ]; then
    # O khac dang chay nen tren may nay (vd nhan lai may giua chung): xem no xong roi chay o nay.
    read -r ban pid <<<"$(ssh_colab "cat $LOGD/dang_chay" 2>/dev/null)"
    td_in "ô $ban đang chạy trên máy -- xem tới khi xong"
    td_xem "$ban" "$pid" 20 || return $?
    out=$(khoi_dong_ssh "$1" "$2" 2>&1) || return 1
  fi
  pid=$(sed -n 's/^FZ_PID=//p' <<<"$out")
  [ -n "$pid" ] || { echo "$out" | tail -3; return 1; }
  td_xem "$1" "$pid"
}

# May san sang cho doi $1: co ma nguon + binary co --stop-file + gen$1.onnx (+ gen$1.pt neu $2 = pt).
# Chua thi chay 02. 0 = san sang, 1 = loi (thu lai), 2 = loi khong tu sua duoc, 3 = mat may, 4 = q.
td_kiem_may_cl() {
  ssh_colab "b=$E_CL/build-linux/custom_engine; test -s \$b && echo BIN_\$(grep -c -a -- --stop-file \$b) && echo BINA_\$(grep -c -a FZ_ARENA \$b); test -s /content/gen$1.onnx && echo CO_ONNX; test -s /content/gen$1.pt && python3 -c 'import onnx, onnxscript, onnxruntime' 2>/dev/null && echo CO_PT" 2>/dev/null
}
td_chuan_bi() {
  local g=$1 can_pt=${2:-} out rc
  out=$(td_kiem_may_cl "$g")
  if ! grep -q '^BIN_[1-9]' <<<"$out" || ! grep -q CO_ONNX <<<"$out"; then
    td_ghi buoc=chuan_bi
    td_in "chạy 02 (mã, binary, gen$g từ Release)"
    td_chay 02 "$(ls "$D"/02_*.py 2>/dev/null | head -1)"; rc=$?
    [ $rc = 0 ] || return $rc
    out=$(td_kiem_may_cl "$g")
  fi
  if ! grep -q '^BIN_' <<<"$out"; then td_in "[!] 02 chưa dựng được engine -- thử lại"; return 1; fi
  if grep -q '^BIN_0' <<<"$out"; then
    td_in "${M_DO}[!] binary trên Release chưa có --stop-file${M_HET}"
    td_in "    (bản cũ): chạy tay 02 rồi 02b, đưa binary mới lên Release, rồi mở lại vòng lặp"
    return 2
  fi
  if ! grep -q CO_ONNX <<<"$out"; then
    # Thuong la loi tam thoi cua GitHub (vd HTTP 500) -- cua so khac van tai duoc. 5 phut sau chay lai
    # 02; 6 lan lien (30 phut) van khong co thi moi dung (va tra may, xem td_vong).
    TD_LOI_ONNX=$((${TD_LOI_ONNX:-0} + 1))
    if [ $TD_LOI_ONNX -ge 6 ]; then
      td_in "${M_DO}[!] $TD_LOI_ONNX lần liền không tải được gen$g.onnx từ Release${M_HET} -- dừng"
      TD_LOI_ONNX=0; return 2
    fi
    td_in "${M_VANG}[!] chưa tải được gen$g.onnx từ Release (lần $TD_LOI_ONNX/6)${M_HET} -- 5 phút nữa thử lại"
    ssh_colab "rm -f /content/gen$g.onnx" 2>/dev/null
    td_ngu 300 || return 4
    return 1
  fi
  TD_LOI_ONNX=0
  if [ -n "$can_pt" ] && ! grep -q CO_PT <<<"$out"; then
    # Chi may huan luyen moi tai .pt + thu vien (o 02c) -- may chi sinh du lieu khong can.
    td_in "02c: tải gen$g.pt + thư viện huấn luyện"
    td_chay 02c "$(ls "$D"/02c_*.py 2>/dev/null | head -1)"; rc=$?
    [ $rc = 0 ] || return $rc
    out=$(td_kiem_may_cl "$g")
    if ! grep -q CO_PT <<<"$out"; then
      TD_LOI_ONNX=$((${TD_LOI_ONNX:-0} + 1))       # cung bo dem: loi tai tam thoi nhu .onnx
      if [ $TD_LOI_ONNX -ge 6 ]; then
        td_in "${M_DO}[!] $TD_LOI_ONNX lần liền chưa có gen$g.pt / thư viện huấn luyện (Release thiếu gen$g.pt?)${M_HET} -- dừng"
        TD_LOI_ONNX=0; return 2
      fi
      td_in "${M_VANG}[!] chưa tải được gen$g.pt / thư viện huấn luyện (lần $TD_LOI_ONNX/6)${M_HET} -- 5 phút nữa thử lại"
      ssh_colab "rm -f /content/gen$g.pt" 2>/dev/null
      td_ngu 300 || return 4
      return 1
    fi
    TD_LOI_ONNX=0
  fi
  return 0
}

# Giai doan 2 tren may cua cua so nay: 04 (tran theo han muc) -> 06 -> tai ve.
td_sinh() {
  local g=$1 rc secs muc tong so f o04 par duoi
  td_chuan_bi "$g"; rc=$?
  case $rc in 0) ;; 2) TD_LOI=1; return ;; 3) td_mat_may; return ;; 4) return ;; *) td_ngu 30; return ;; esac
  [ -f "$TD_DUNG" ] && return
  secs=$(td_giay_t4)
  if [ -z "$secs" ]; then td_in "không đọc được hạn mức -- thử lại sau 1 phút"; td_ngu 60; return; fi
  o04=$(ls "$D"/04_*.py | head -1)
  par=$(song_song_o04 "$o04"); duoi=$(duoi_giay "$par")
  secs=$((secs - $(chua_phut) * 60 - duoi))
  if [ $secs -lt $((TD_PHUT_SINH * 60)) ]; then
    td_in "$(ten_tk "$TK"): hạn mức còn $(( (secs + duoi) / 60 + $(chua_phut) )) phút T4 -> trả máy"
    td_tra; return
  fi
  muc=$(td_muc); tong=$(td_tong "$g"); so=$((muc - tong))
  [ $so -ge 1 ] || return
  f=$TD/o_$$/$(basename "$o04")
  mkdir -p "$TD/o_$$"
  sed -E "0,/^SECS[[:space:]]*=[[:space:]]*[0-9]+/s//SECS = $secs/; 0,/^GAMES[[:space:]]*=[[:space:]]*[0-9]+/s//GAMES = $so/" \
    "$o04" > "$f"
  TD_G=$g; TD_TONG_IN=
  td_ghi gen="$g" buoc=sinh van=0 giao="$so" par="$par" dung_van= dung_dang=
  td_in "04 trên $(ten_tk "$TK"): tối đa $so ván ($par song song), SECS=$secs (≈ $((secs / 60)) phút, đã trừ $(chua_phut) phút gom zip + tải về và $(( (duoi + 59) / 60 )) phút đuôi ván) · đời $g: $tong/$muc"
  td_chay 04 "$f"; rc=$?
  case $rc in 3) td_mat_may; return ;; 4) return ;; esac
  ghi_duoi_log
  td_gom_tai "$g"
}
# 06 + tai goi van ve (ten tich luy; van cua may nay ve 0 ngay luc dat ten).
td_gom_tai() {
  local g=$1 rc lan v
  td_ghi buoc=tai
  td_in "06: gom ván, tải về"
  td_chay 06 "$(ls "$D"/06_*.py | head -1)"; rc=$?
  case $rc in 3) td_mat_may; return 1 ;; 4) return 1 ;; esac
  for lan in 1 2 3 4 5; do
    TAI_VE_MOC=td_van_0 tai_theo_o 06
    v=$(td_doc "$TD_W" van)
    if [ "${v:-0}" = 0 ]; then td_ghi buoc=xong; return 0; fi
    td_con_may || { td_mat_may; return 1; }
    td_in "chưa tải được gói ván -- thử lại sau 30 giây ($lan/5)"
    td_ngu 30 || return 1
  done
  td_ghi buoc=xong
  return 1
}

# ---------------- Giai doan 0: arena ----------------
td_ar_van() { local n; n=$(cat "$TD_AR_VAN_F" 2>/dev/null); so_nguyen "$n" && echo $((10#$n)) || echo 100; }
td_ar_day() { cat "$TD_AR_DAY_F" 2>/dev/null; }
td_ar_tep() { echo "$TD_AR_DIR/gen$1_vs_gen$2.txt"; }
# Doi thu cua doi $1: so dung ngay truoc $1 trong day. Rong = doi $1 khong co arena.
td_ar_doi_thu() {
  local d t=
  for d in $(td_ar_day); do
    [ "$d" = "$1" ] && [ -n "$t" ] && { echo "$t"; return; }
    t=$d
  done
}
# Cong W/D/L/N cac dong ket qua (moi may mot dong) cua arena $1 vs $2: in "W D L N".
td_ar_cong() {
  local f; f=$(td_ar_tep "$1" "$2")
  [ -f "$f" ] || { echo "0 0 0 0"; return; }
  awk '/^[0-9]/ { for (i = 1; i <= NF; i++) { split($i, k, "="); if (k[1] ~ /^[WDLN]$/) s[k[1]] += k[2] } }
       END { print s["W"] + 0, s["D"] + 0, s["L"] + 0, s["N"] + 0 }' "$f"
}
td_ar_da() { local w d l n; read -r w d l n <<<"$(td_ar_cong "$1" "$2")"; echo "$n"; }
td_ar_xong() { grep -q '^\(XONG\|BO_QUA\)' "$(td_ar_tep "$1" "$2")" 2>/dev/null; }
# Tong van arena $1 vs $2 = da ghi + van da xong VA dang do tren may cac cua so dang arena (nhu td_tong).
td_ar_tong() {
  local f t v co=1
  td_khoa && co=0
  t=$(td_ar_da "$1" "$2")
  for f in $(td_cac_cua_so); do
    [ "$(td_doc "$f" gen)" = "$1" ] && [ "$(td_doc "$f" buoc)" = arena ] || continue
    v=$(td_doc "$f" van); t=$((t + ${v:-0} + $(td_dang_do "$f")))
  done
  [ $co = 0 ] && rmdir "$TAI/.khoa_dat_ten" 2>/dev/null
  echo $t
}
# Doi $1 con viec arena: co doi thu trong day, chua XONG / BO_QUA, tong (ca van dang do) < so van.
td_ar_viec() {
  local a
  a=$(td_ar_doi_thu "$1"); [ -n "$a" ] || return 1
  td_ar_xong "$1" "$a" && return 1
  [ "$(td_ar_tong "$1" "$a")" -lt "$(td_ar_van)" ]
}
# Bo arena $1 vs $2 (ly do $3): ghi BO_QUA de vong lap khong thu lai.
td_ar_bo() {
  mkdir -p "$TD_AR_DIR"
  echo "BO_QUA $(date '+%Y-%m-%d %H:%M') $3" >> "$(td_ar_tep "$1" "$2")"
  td_in "${M_DO}[!] bỏ arena gen$1 vs gen$2: $3${M_HET}"
}
# Du van -> dong XONG (ty le thang cua doi moi, khoang tin cay 95%, Elo) va in ket qua.
td_ar_ket() {
  local g=$1 a=$2 w d l n kq
  td_ar_xong "$g" "$a" && return 0
  read -r w d l n <<<"$(td_ar_cong "$g" "$a")"
  [ "$n" -ge "$(td_ar_van)" ] || return 0
  kq=$(awk -v w="$w" -v d="$d" -v n="$n" 'BEGIN {
    p = (w + d / 2) / n; s = sqrt(p * (1 - p) / n)
    lo = p - 1.96 * s; hi = p + 1.96 * s
    e = (p > 0 && p < 1) ? sprintf("%+.0f Elo", -400 * log(1 / p - 1) / log(10)) : "Elo ?"
    printf "%.1f%% (95%%: %.0f-%.0f%%), %s", 100 * p, 100 * (lo < 0 ? 0 : lo), 100 * (hi > 1 ? 1 : hi), e }')
  echo "XONG $(date '+%Y-%m-%d %H:%M') W=$w D=$d L=$l N=$n -- gen$g: $kq" >> "$(td_ar_tep "$g" "$a")"
  td_in "${M_XANH}arena gen$g vs gen$a xong${M_HET}: gen$g thắng $w / hoà $d / thua $l ($n ván) = ${M_DAM}$kq${M_HET}"
  td_in "(Download/FairyZero/arena/gen${g}_vs_gen$a.txt)"
}
# Ghi ket qua lan chay o 08 tren may nay (dong FZ_ARENA cua log) vao tep arena $1 vs $2 -- mot lan
# moi lan chay (08.da_ghi tren may = dong dau log da ghi), chi khi log dung la arena gen$1 vs gen$2
# cua day. Cung khoa voi td_ar_tong: van cua may nay ve 0 dung luc dong ket qua duoc them.
td_ar_ghi() {
  local g=$1 a=$2 ds dau da kq co=1
  [ "$(td_ar_doi_thu "$g")" = "$a" ] || return 0
  mapfile -t ds < <(ssh_colab "printf '%s\n' \"\$(head -1 $LOGD/08.log 2>/dev/null)\" \"\$(cat $LOGD/08.da_ghi 2>/dev/null)\" \"\$(grep -c 'A=/content/gen$g.onnx  vs  B=/content/gen$a.onnx' $LOGD/08.log 2>/dev/null)\" \"\$(grep '^FZ_ARENA ' $LOGD/08.log 2>/dev/null | tail -1)\"" 2>/dev/null)
  [ ${#ds[@]} -ge 4 ] || { td_in "[!] không đọc được log ô 08 -- ghi kết quả sau"; return 1; }
  dau=${ds[0]}; da=${ds[1]}; kq=${ds[3]}
  if [ -z "$dau" ] || [ "$da" = "$dau" ] || [ "${ds[2]:-0}" = 0 ]; then td_ghi van=0; return 0; fi
  ssh_colab "cat > $LOGD/08.da_ghi" <<<"$dau" || { td_in "[!] chưa ghi được dấu đã ghi -- thử lại sau"; return 1; }
  mkdir -p "$TD_AR_DIR"
  td_khoa && co=0
  if [[ "$kq" =~ ^FZ_ARENA\ W=([0-9]+)\ D=([0-9]+)\ L=([0-9]+)\ N=([0-9]+) ]]; then
    [ -f "$(td_ar_tep "$g" "$a")" ] ||
      echo "# arena gen$g (moi) vs gen$a: W/D/L = gen$g thang/hoa/thua, moi may mot dong" > "$(td_ar_tep "$g" "$a")"
    [ "${BASH_REMATCH[4]}" -gt 0 ] && echo "$(date '+%Y-%m-%d %H:%M') $(ten_tk "$TK") W=${BASH_REMATCH[1]} D=${BASH_REMATCH[2]} L=${BASH_REMATCH[3]} N=${BASH_REMATCH[4]}" >> "$(td_ar_tep "$g" "$a")"
    td_in "arena máy $(ten_tk "$TK"): gen$g thắng ${BASH_REMATCH[1]} / hoà ${BASH_REMATCH[2]} / thua ${BASH_REMATCH[3]}"
  else
    td_in "${M_VANG}[!] log ô 08 không có dòng FZ_ARENA (ô lỗi / dừng ngang) -- các ván đó không tính${M_HET}"
  fi
  td_ghi van=0
  td_ar_ket "$g" "$a"                 # trong khoa: hai cua so xong cung luc khong ghi XONG hai lan
  [ $co = 0 ] && rmdir "$TAI/.khoa_dat_ten" 2>/dev/null
  return 0
}
# Mang gen$1.onnx (doi thu) len may: co san / tai tu Release (REL cua o 00) / tu dien thoai.
# 0 = co, 1 = loi mang (thu lai), 2 = khong co o dau ca.
td_ar_mang() {
  local a=$1 rel out
  rel=$(doc "$D/00_cau_hinh.py" | sed -n 's/^REL *= *"\([^"]*\)".*/\1/p' | head -1)
  out=$(ssh_colab "f=/content/gen$a.onnx; test -s \$f || { wget -q --tries=4 --waitretry=15 --retry-on-http-error=429,500,502,503,504 -O \$f.t $rel/gen$a.onnx && mv \$f.t \$f; rm -f \$f.t; }; test -s \$f && echo FZ_CO" 2>/dev/null)
  grep -q FZ_CO <<<"$out" && return 0
  [ -s "$TAI/gen$a.onnx" ] || return 2
  td_in "Release không có gen$a.onnx -> tải từ điện thoại lên"
  tai_len "$TAI/gen$a.onnx" "/content/gen$a.onnx" || return 1
}
# Giai doan 0 tren may cua cua so nay: o 08 (so van con thieu, tran theo han muc) -> ghi ket qua.
td_arena() {
  local g=$1 a rc secs par duoi so f o08 muc tong
  a=$(td_ar_doi_thu "$g")
  td_chuan_bi "$g"; rc=$?
  case $rc in 0) ;; 2) TD_LOI=1; return ;; 3) td_mat_may; return ;; 4) return ;; *) td_ngu 30; return ;; esac
  [ -f "$TD_DUNG" ] && return
  # Binary / o 08 cu: DUNG vong lap (khong ghi BO_QUA -- cap nhat xong mo lai thi arena van con).
  if ! grep -q '^BINA_[1-9]' <<<"$(td_kiem_may_cl "$g")"; then
    td_in "${M_DO}[!] binary trên Release chưa có arena dừng mềm (cần bản từ 2026-09-30)${M_HET}"
    td_in "    đưa binary mới lên Release rồi mở lại vòng lặp (hoặc tắt arena: dãy đời = -)"
    TD_LOI=1; return
  fi
  td_ar_mang "$a"; rc=$?
  case $rc in
    0) ;;
    2) td_ar_bo "$g" "$a" "không có gen$a.onnx trên Release lẫn Download/FairyZero"; return ;;
    *) td_con_may || td_mat_may; return ;;
  esac
  o08=$(ls "$D"/08_*.py 2>/dev/null | head -1)
  if [ -z "$o08" ] || ! grep -q '^A_ONNX' "$o08"; then
    td_in "${M_DO}[!] ô 08 trên điện thoại là bản cũ${M_HET}: bash ~/lay_ve.sh 08, rồi mở lại vòng lặp"
    TD_LOI=1; return
  fi
  secs=$(td_giay_t4)
  if [ -z "$secs" ]; then td_in "không đọc được hạn mức -- thử lại sau 1 phút"; td_ngu 60; return; fi
  par=$(song_song_o04 "$o08"); duoi=$(duoi_giay "$par")
  secs=$((secs - $(chua_phut) * 60 - duoi))
  if [ $secs -lt $((TD_PHUT_SINH * 60)) ]; then
    td_in "$(ten_tk "$TK"): hạn mức còn $(( (secs + duoi) / 60 + $(chua_phut) )) phút T4 -> trả máy"
    td_tra; return
  fi
  muc=$(td_ar_van); tong=$(td_ar_tong "$g" "$a"); so=$((muc - tong))
  [ $so -ge 1 ] || return
  f=$TD/o_$$/$(basename "$o08")
  mkdir -p "$TD/o_$$"
  sed -E "0,/^SECS[[:space:]]*=[[:space:]]*[0-9]+/s//SECS = $secs/; 0,/^GAMES[[:space:]]*=[[:space:]]*[0-9]+/s//GAMES = $so/; s#^A_ONNX[[:space:]]*=.*#A_ONNX = \"/content/gen$g.onnx\"#; s#^B_ONNX[[:space:]]*=.*#B_ONNX = \"/content/gen$a.onnx\"#" \
    "$o08" > "$f"
  TD_G=$g; TD_AR_A=$a; TD_KIEU=arena; TD_TONG_IN=
  td_ghi gen="$g" buoc=arena van=0 giao="$so" par="$par" dung_van= dung_dang=
  td_in "08 arena ${M_DAM}gen$g vs gen$a${M_HET} trên $(ten_tk "$TK"): $so ván ($par song song), SECS=$secs · arena: $tong/$muc"
  td_chay 08 "$f"; rc=$?
  TD_KIEU=
  case $rc in 3) td_mat_may; return ;; 4) return ;; 1) td_ngu 30; return ;; esac
  td_ar_ghi "$g" "$a"
  td_ghi buoc=xong
}

# May vua nhan lai (vong lap truoc bi dong giua chung): may dang lam gi thi lam tiep viec do.
td_tiep_tuc() {
  local g=$1 o pid tt rc
  read -r o pid <<<"$(ssh_colab "cat $LOGD/dang_chay 2>/dev/null" 2>/dev/null)"
  [ -n "$o" ] || return 0
  tt=$(ssh_colab "python3 $LOGD/fz_may.py trang_thai $o $pid" 2>/dev/null)
  td_in "máy đang có ô $o ($tt)"
  case "$o:$tt" in
    04:chay)
      # So van duoc giao + so van song song: doc tu dong lenh cua engine dang chay (tinh van dang do).
      local cfg giao par
      cfg=$(ssh_colab "pgrep -af '[c]ustom_engine.* --selfplay' | head -1" 2>/dev/null)
      giao=$(sed -n 's/.* --games \([0-9]*\).*/\1/p' <<<"$cfg"); par=$(sed -n 's/.* --parallel \([0-9]*\).*/\1/p' <<<"$cfg")
      TD_G=$g; TD_TONG_IN=; td_ghi gen="$g" buoc=sinh van=0 giao="$giao" par="$par" dung_van= dung_dang=
      td_xem 04 "$pid" 50; rc=$?
      case $rc in 3) td_mat_may; return ;; 4) return ;; esac
      ghi_duoi_log
      td_gom_tai "$g" ;;
    04:*) td_ghi gen="$g" buoc=tai van=0; td_gom_tai "$g" ;;
    06:chay) td_ghi gen="$g" buoc=tai
             td_xem 06 "$pid" 20; rc=$?; [ $rc = 0 ] || { [ $rc = 3 ] && td_mat_may; return; }
             TAI_VE_MOC=td_van_0 tai_theo_o 06 ;;
    06:*) td_ghi gen="$g" buoc=tai; TAI_VE_MOC=td_van_0 tai_theo_o 06 ;;
    08:*)
      # Arena cua vong lap: doi + doi thu doc tu dong "=== ARENA: A=... vs B=..." cua log.
      local ar g2 a2 cfg giao par
      ar=$(ssh_colab "grep -m1 '=== ARENA: A=' $LOGD/08.log" 2>/dev/null)
      [[ "$ar" =~ A=/content/gen([0-9]+)\.onnx\ +vs\ +B=/content/gen([0-9]+)\.onnx ]] || return 0
      g2=${BASH_REMATCH[1]}; a2=${BASH_REMATCH[2]}
      [ "$(td_ar_doi_thu "$g2")" = "$a2" ] || return 0      # arena chay tay, khong phai cua day
      if [ "$tt" = chay ]; then
        cfg=$(ssh_colab "pgrep -af '[c]ustom_engine.* --arena' | head -1" 2>/dev/null)
        giao=$(sed -n 's/.* --games \([0-9]*\).*/\1/p' <<<"$cfg"); par=$(sed -n 's/.* --parallel \([0-9]*\).*/\1/p' <<<"$cfg")
        TD_G=$g2; TD_AR_A=$a2; TD_KIEU=arena; TD_TONG_IN=
        td_ghi gen="$g2" buoc=arena van=0 giao="$giao" par="$par" dung_van= dung_dang=
        td_xem 08 "$pid" 50; rc=$?
        TD_KIEU=
        case $rc in 3) td_mat_may; return ;; 4) return ;; esac
      fi
      td_ar_ghi "$g2" "$a2"; td_ghi buoc=xong ;;
    07:chay)
      if td_lay_hl "$g"; then
        TD_VAI=huan_luyen; td_ghi gen="$g" buoc=huan_luyen
        td_xem 07 "$pid" 20; rc=$?; [ $rc = 0 ] || { [ $rc = 3 ] && td_mat_may; return; }
        td_don_mang_cu $((g + 1)); tai_theo_o 07
      fi ;;
  esac
}

# Khoa huan luyen doi $1: pid cua so dang giu (con song), hoac rong.
td_chu_hl() {
  local p
  p=$(cat "$TD/hl_$1/pid" 2>/dev/null)
  if [ -n "$p" ] && td_song "$p"; then echo "$p"; return; fi
  [ -d "$TD/hl_$1" ] && [ -n "$p" ] && rm -rf "$TD/hl_$1"
}
td_lay_hl() {
  [ "$(td_chu_hl "$1")" = $$ ] && return 0
  td_chu_hl "$1" >/dev/null
  mkdir "$TD/hl_$1" 2>/dev/null || return 1
  echo $$ > "$TD/hl_$1/pid"
}
# Cua so nao huan luyen: trong cac cua so doi $1 dang cho, may con nhieu han muc nhat (bang nhau: pid
# nho hon); khong ai giu may: pid nho nhat. In pid.
td_chon_hl() {
  local f p h b= bh=-1 bp=
  for f in $(td_cac_cua_so); do
    [ "$(td_doc "$f" gen)" = "$1" ] || continue
    p=${f##*/w_}
    case $(td_doc "$f" buoc) in
      cho_hl) h=$(td_doc "$f" han); h=${h:-0} ;;
      cho) h=-1 ;;
      *) continue ;;
    esac
    if [ "$h" -gt "$bh" ] || { [ "$h" = "$bh" ] && [ "$p" -lt "${b:-999999999}" ]; }; then b=$p; bh=$h; fi
  done
  echo "$b"
}
# Con cua so nao (khac cua so nay) cua doi $1 dang chuan bi / sinh / tai ve?
td_ai_ban() {
  local f
  for f in $(td_cac_cua_so); do
    [ "$f" = "$TD_W" ] && continue
    [ "$(td_doc "$f" gen)" = "$1" ] || continue
    case $(td_doc "$f" buoc) in chuan_bi|sinh|tai) return 0 ;; esac
  done
  return 1
}

# Giai doan 3 (cho / bau cua so huan luyen) cho doi $1.
td_giai_doan_3() {
  local g=$1 chu da_bao=0
  if [ $TD_CO_MAY = 1 ]; then td_ghi gen="$g" buoc=cho_hl han="$(td_giay_t4 || echo 0)" van=0
  else td_ghi gen="$g" buoc=cho han=0 van=0; fi
  while :; do
    [ "$(td_gen)" = "$g" ] || return 0
    chu=$(td_chu_hl "$g")
    if [ -n "$chu" ] && [ "$chu" != $$ ]; then
      if [ $TD_CO_MAY = 1 ]; then
        td_in "cửa sổ khác huấn luyện đời $g -> trả máy, chờ"
        td_tra; td_ghi buoc=cho han=0
      fi
      [ -f "$TD_DUNG" ] && return 0
      [ $da_bao = 0 ] && { td_in "chờ cửa sổ khác huấn luyện xong đời $g..."; da_bao=1; }
    elif [ -z "$chu" ]; then
      # So van tut duoi muc tieu (may cua so khac mat giua chung) -> quay lai sinh tiep.
      if ! td_toi_luot_hl "$g" && [ "$(td_tong "$g")" -lt "$(td_muc)" ]; then return 0; fi
      if td_toi_luot_hl "$g" && ! td_ai_ban "$g" && [ "$(td_chon_hl "$g")" = $$ ] && td_lay_hl "$g"; then
        td_huan_luyen "$g"; return
      fi
      [ $da_bao = 0 ] && { td_in "đủ ván đời $g -- chờ các máy khác tải về..."; da_bao=1; }
    fi
    td_ngu 10 || return
  done
}

# Mang doi $1 dang co san tren dien thoai (cu) -> doi ten sang ten trong ("gen4 (2).onnx"): mang vua
# huan luyen tai ve dung ten gen$1.*, giai doan 4 tai len dung tep do.
td_don_mang_cu() {
  local x
  for x in onnx pt; do
    [ -e "$TAI/gen$1.$x" ] && mv "$TAI/gen$1.$x" "$TAI/$(ten_trong "gen$1.$x")"
  done
}

# Giai doan 3-4 (cua so nay da giu khoa huan luyen doi $1).
td_huan_luyen() {
  local g=$1 n=$(($1 + 1)) lan=0 loi=0 h rc
  TD_VAI=huan_luyen; td_ghi gen="$g" buoc=huan_luyen van=0
  if ! td_co_mang "$n"; then
    if [ ! -f "$TAI/games_gen$g.zip" ]; then
      td_in "gộp dữ liệu đời $g ($TD_SO_DOI đời) ..."
      # Ctrl+C trong luc gop bi bo qua (gop do dang thi phai lam lai) -- bam lai sau khi gop xong.
      ( trap '' INT; python ~/fz_tu_dong.py gop "$TAI" "$g" "$TD_SO_DOI" | tee "$TD/.gop_$$" )
      grep -q '^FZ_GOP_XONG' "$TD/.gop_$$" || { td_in "${M_DO}[!] gộp lỗi${M_HET}"; rm -f "$TD/.gop_$$"; TD_LOI=1; return; }
      rm -f "$TD/.gop_$$"
      command -v termux-media-scan >/dev/null && termux-media-scan -r "$TAI" >/dev/null 2>&1
    fi
    while :; do
      [ $NGAT = 1 ] && td_hoi_ngat
      [ $TD_THOAT = 1 ] && return
      if [ $TD_CO_MAY = 0 ]; then
        if [ $lan -gt 0 ]; then td_cho_lich || return; fi
        lan=$((lan + 1))
        td_xin_mot_vong || continue
        td_ghi buoc=huan_luyen
      fi
      td_chuan_bi "$g" pt; rc=$?
      case $rc in 0) ;; 2) TD_LOI=1; return ;; 3) td_mat_may; continue ;; 4) return ;; *) td_ngu 30 || return; continue ;; esac
      h=$(td_giay_t4)
      if [ -z "$h" ]; then td_in "không đọc được hạn mức -- thử lại"; td_ngu 30 || return; continue; fi
      if [ "$h" -lt $((TD_PHUT_HL * 60)) ]; then
        td_in "máy còn $((h / 60)) phút T4 (< $TD_PHUT_HL) -> trả, xin máy khác"
        td_tra; lan=0; continue
      fi
      td_in "tải games_gen$g.zip lên (máy còn $((h / 60)) phút T4)"
      if ! tai_len "$TAI/games_gen$g.zip" "/content/games_gen$g.zip"; then
        td_con_may || td_mat_may; lan=0; continue
      fi
      td_in "07: huấn luyện đời $n"
      td_chay 07 "$(ls "$D"/07_*.py | head -1)"; rc=$?
      case $rc in 3) td_mat_may; lan=0; continue ;; 4) return ;; esac
      td_don_mang_cu "$n"
      tai_theo_o 07
      td_co_mang "$n" && break
      td_con_may || { td_mat_may; lan=0; continue; }
      loi=$((loi + 1))
      if [ $loi -ge 2 ]; then td_in "${M_DO}[!] huấn luyện lỗi 2 lần -- xem log ô 07${M_HET}"; TD_LOI=1; return; fi
      td_in "huấn luyện chưa ra mạng -- thử lại"
    done
  fi
  td_len_github "$n" || return
  td_len_doi "$g" "$n"
  rm -rf "$TD/hl_$g"
  TD_VAI=
}
# Giai doan 4: gen$1.onnx + .pt len GitHub Release (REL trong o 00). Loi mang -> thu lai.
td_len_github() {
  local n=$1 repo tag
  read -r repo tag <<<"$(doc "$D/00_cau_hinh.py" | sed -n 's#^REL *= *"https://github.com/\([^/]*/[^/]*\)/releases/download/\([^"]*\)".*#\1 \2#p')"
  if [ -z "$tag" ]; then td_in "${M_DO}[!] không đọc được REL trong 00_cau_hinh.py${M_HET}"; TD_LOI=1; return 1; fi
  while :; do
    if ! command -v gh >/dev/null || ! gh auth status >/dev/null 2>&1; then
      td_in "${M_DO}[!] chưa có gh / chưa đăng nhập GitHub${M_HET} (pkg install gh; gh auth login) -- 5 phút nữa thử lại"
      td_ngu 300 || return 1; continue
    fi
    td_in "tải gen$n.onnx + gen$n.pt lên GitHub ($tag)"
    if ( trap '' INT; gh release upload "$tag" "$TAI/gen$n.onnx" "$TAI/gen$n.pt" --clobber -R "$repo" ); then
      td_in "${M_XANH}đã lên Release $tag${M_HET}"; return 0
    fi
    td_in "tải lên GitHub lỗi (mạng?) -- 2 phút nữa thử lại"
    td_ngu 120 || return 1
  done
}
td_len_doi() {
  local f=$D/00_cau_hinh.py
  [ "$(td_gen)" = "$1" ] && sed -i -E "0,/^GEN_CURRENT[[:space:]]*=[[:space:]]*[0-9]+/s//GEN_CURRENT = $2/" "$f"
  if [ "$(td_gen)" = "$2" ]; then td_in "${M_XANH}xong đời $1 -> GEN_CURRENT = $2${M_HET}"
  else td_in "${M_DO}[!] không ghi được GEN_CURRENT = $2 vào 00_cau_hinh.py${M_HET}"; TD_LOI=1; fi
}

# Chua xin duoc may: cho toi lich xin chung (thoi som khi den luot huan luyen / du van / dung / doi doi).
td_cx_thoi() {
  [ -f "$TD_DUNG" ] || [ "$(td_gen)" != "$TD_CX_G" ] || td_toi_luot_hl "$TD_CX_G" ||
    [ "$(td_tong "$TD_CX_G")" -ge "$(td_muc)" ]
}
td_cho_xin() { TD_CX_G=$1; td_cho_lich td_cx_thoi; }

# Hoi day doi arena + so van moi arena (Enter = giu), in tinh trang tung cap. 1 = go sai.
td_hoi_arena() {
  local x d t= ds=() cap a n
  echo "${M_MO}Arena: dãy đời, vd 11 12 15 = đời 12 ra thì${M_HET}"
  echo "${M_MO}đấu đời 11, đời 15 ra thì đấu đời 12${M_HET}"
  read -rp "Dãy đời arena (Enter = $( [ -n "$(td_ar_day)" ] && td_ar_day || echo "không có"); - = tắt): " x
  if [ "$x" = - ]; then rm -f "$TD_AR_DAY_F"
  elif [ -n "$x" ]; then
    for d in ${x//,/ }; do
      [[ "$d" =~ ^[0-9]+$ ]] || { echo "[!] '$d' không phải số đời"; return 1; }
      d=$((10#$d))
      [ -n "$t" ] && [ "$d" -le "$t" ] && { echo "[!] Dãy phải tăng dần ($t rồi $d)"; return 1; }
      ds+=("$d"); t=$d
    done
    [ ${#ds[@]} -ge 2 ] || { echo "[!] Cần ít nhất 2 đời"; return 1; }
    echo "${ds[*]}" > "$TD_AR_DAY_F"
  fi
  [ -n "$(td_ar_day)" ] || return 0
  read -rp "Số ván mỗi arena (Enter = $(td_ar_van)): " x
  if [ -n "$x" ]; then
    so_nguyen "$x" || { echo "[!] Không phải số"; return 1; }
    echo $((10#$x)) > "$TD_AR_VAN_F"
  fi
  t=
  for d in $(td_ar_day); do
    if [ -n "$t" ]; then
      a=$t; cap="gen$d vs gen$a"
      if grep -q '^XONG' "$(td_ar_tep "$d" "$a")" 2>/dev/null; then
        echo "  $cap: ${M_XANH}xong${M_HET} -- $(grep '^XONG' "$(td_ar_tep "$d" "$a")" | tail -1 | sed 's/.* -- //')"
      elif grep -q '^BO_QUA' "$(td_ar_tep "$d" "$a")" 2>/dev/null; then echo "  $cap: ${M_VANG}đã bỏ${M_HET}"
      else n=$(td_ar_da "$d" "$a"); echo "  $cap: $n/$(td_ar_van) ván"; fi
    fi
    t=$d
  done
  return 0
}

# Bat dau: doi (o 00), muc tieu, so phut chua, thu muc cac doi truoc, giai doan hien tai.
td_bat_dau() {
  local g x k thieu=() khac=() f n o04
  mkdir -p "$TD"
  clear
  echo "${M_DAM}== Vòng lặp tự động ==${M_HET}"
  g=$(td_gen)
  [[ "$g" =~ ^[0-9]+$ ]] || { echo "[!] Không đọc được GEN_CURRENT trong 00_cau_hinh.py"; return 1; }
  o04=$(ls "$D"/04_*.py 2>/dev/null | head -1)
  if [ -z "$(ls "$D"/02c_*.py 2>/dev/null)" ]; then
    echo "[!] Thiếu ô 02c (tải .pt trước huấn luyện):"
    echo "    bash ~/lay_ve.sh"
    return 1
  fi
  if [ -z "$o04" ] || ! grep -q DUNG_MEM "$o04"; then
    echo "[!] Ô 04 trên điện thoại là bản cũ (chưa"
    echo "    dừng mềm được): bash ~/lay_ve.sh 04"
    return 1
  fi
  for f in ~/fz_tu_dong.py ~/fz_han_muc.py ~/fz_nhan_may.py ~/fz_giu_may.py; do
    [ -f "$f" ] || { echo "[!] Thiếu $f -- chạy: bash ~/lay_ve.sh"; return 1; }
  done
  for f in $(td_cac_cua_so); do [ "$f" = "$TD_W" ] || khac+=("${f##*/w_}"); done
  echo "Đời hiện tại (ô 00): ${M_DAM}$g${M_HET}"
  echo "${M_MO}(đổi đời trước khi chạy: menu g)${M_HET}"
  [ ${#khac[@]} -gt 0 ] && echo "${M_VANG}Đang có ${#khac[@]} cửa sổ khác chạy vòng lặp${M_HET}"
  if ! command -v gh >/dev/null || ! gh auth status >/dev/null 2>&1; then
    echo "${M_VANG}[!] Chưa đăng nhập GitHub (gh):${M_HET}"
    echo "    giai đoạn 4 sẽ đứng chờ. Cài:"
    echo "    pkg install gh && gh auth login"
  fi
  read -rp "Tổng số ván mỗi đời (Enter = $(td_muc)): " x
  if [ -n "$x" ]; then
    so_nguyen "$x" || { echo "[!] Không phải số"; return 1; }
    echo $((10#$x)) > "$TD_MUC_F"
  fi
  hoi_chua_phut || return 1
  td_hoi_arena || return 1
  for ((k = 1; k < TD_SO_DOI; k++)); do
    [ $((g - k)) -ge 0 ] && [ ! -d "$TAI/games_gen$((g - k))" ] && thieu+=("games_gen$((g - k))/")
  done
  if [ ${#thieu[@]} -gt 0 ] && ! td_co_mang $((g + 1)) && [ ! -f "$TAI/games_gen$g.zip" ]; then
    echo "${M_VANG}[!] Thiếu thư mục dữ liệu đời trước${M_HET}"
    echo "    trong Download/FairyZero:"
    printf '      %s\n' "${thieu[@]}"
    echo "    Huấn luyện sẽ chỉ dùng các đời có."
    read -rp "Chạy tiếp? (co = chạy, Enter = thôi): " x
    [ "$x" = co ] || return 1
  fi
  echo "---"
  if td_ar_viec "$g"; then
    echo "Arena gen$g vs gen$(td_ar_doi_thu "$g") chưa xong ($(td_ar_da "$g" "$(td_ar_doi_thu "$g")")/$(td_ar_van)) -> đấu trước"
  fi
  if td_co_mang $((g + 1)); then echo "Đã có gen$((g + 1)).onnx + .pt -> chỉ còn"; echo "tải lên GitHub (giai đoạn 4)"
  elif [ -f "$TAI/games_gen$g.zip" ]; then echo "Đã có games_gen$g.zip -> huấn luyện"
  else
    n=$(tong_tich_luy "$g")
    if [ "$n" -ge "$(td_muc)" ]; then echo "Đã đủ $n/$(td_muc) ván -> gộp, huấn luyện"
    else echo "Đã có $n/$(td_muc) ván đời $g -> sinh tiếp"; fi
  fi
  read -rp "Enter = bắt đầu, n = thôi: " x
  [ -z "$x" ] || return 1
  # Khong con cua so nao chay vong lap: lenh dung tay cu (lan truoc) het hieu luc.
  # (va lich xin may chung cua lan truoc: mo lai vong lap = xin ngay)
  [ ${#khac[@]} -eq 0 ] && rm -f "$TD_DUNG" "$TD_XIN_SAU"
  return 0
}

td_vong() {
  local g
  TD_THOAT=0; TD_LOI=0; TD_VAI=; TD_NHAN_LAI=0
  trap 'rm -f "$CS/$$" "$TD_W" "$TD/.w_$$.tmp" "$TD/.luong_$$"; rm -rf "$TD/o_$$"' EXIT
  td_bat_dau || return
  td_ranh
  td_ghi gen="$(td_gen)" buoc=xin van=0
  while [ $TD_THOAT = 0 ] && [ $TD_LOI = 0 ]; do
    # Ctrl+C luc dang lam viec khac (tai len / tai ve / ssh ngan): hoi ngay khi viec do dung.
    if [ $NGAT = 1 ]; then td_hoi_ngat; [ $TD_THOAT = 1 ] && break; fi
    g=$(td_gen)
    if [ -f "$TD_DUNG" ] && [ "$TD_VAI" != huan_luyen ]; then
      td_in "dừng mềm: trả máy, thoát vòng lặp"
      td_tra
      # May cua vong lap ma cua so lo no da chet (vd Termux bi giet): nhan lai, dung mem, tai ve, tra.
      local ds=()
      while :; do
        td_khoa_chon; td_ds_tk
        if ! td_nhan_lai; then td_mo_khoa_chon; break; fi
        td_mo_khoa_chon
        TD_NHAN_LAI=0; td_tiep_tuc "$g"
        [ $TD_THOAT = 1 ] && break 2
        td_tra
      done
      break
    fi
    # Giai doan 0: arena cua doi nay (neu co trong day va chua xong) truoc khi sinh du lieu.
    if td_ar_viec "$g"; then
      if [ $TD_CO_MAY = 0 ]; then
        td_ghi gen="$g" buoc=xin van=0
        td_xin_mot_vong || { td_cho_xin "$g"; continue; }
      fi
      if [ $TD_NHAN_LAI = 1 ]; then TD_NHAN_LAI=0; td_tiep_tuc "$g"; continue; fi
      td_arena "$g"; continue
    fi
    if td_toi_luot_hl "$g" || [ "$(td_tong "$g")" -ge "$(td_muc)" ]; then td_giai_doan_3 "$g"; continue; fi
    if [ $TD_CO_MAY = 0 ]; then
      td_ghi gen="$g" buoc=xin van=0
      td_xin_mot_vong || { td_cho_xin "$g"; continue; }
    fi
    if [ $TD_NHAN_LAI = 1 ]; then TD_NHAN_LAI=0; td_tiep_tuc "$g"; continue; fi
    td_sinh "$g"
  done
  # Dung vi loi ma con giu may: may van tieu han muc, het han muc thi Colab thu hoi -> mat van chua tai.
  # Con van chua tai (thu muc van cua doi) -> gom + tai ve truoc; roi tra may. Tai ve loi -> giu may
  # (lay tay: fz -> d) thay vi tra ma mat van.
  if [ $TD_LOI = 1 ] && [ $TD_CO_MAY = 1 ]; then
    local gv nv
    gv=$(td_doc "$TD_W" gen); gv=${gv:-$(td_gen)}
    nv=$(ssh_colab "ls /content/games_gen$gv 2>/dev/null | grep -c -E '\.(xz|gz|bin)\$'" 2>/dev/null)
    if [[ "$nv" =~ ^[0-9]+$ ]] && [ "$nv" -gt 0 ]; then
      td_in "máy còn $nv ván đời $gv chưa tải về -- gom, tải về trước khi trả máy"
      if td_gom_tai "$gv"; then td_tra
      else td_in "${M_DO}[!] chưa tải được ván về -- GIỮ máy (lấy tay: fz -> d, rồi t để trả)${M_HET}"; fi
    else
      td_tra
    fi
  fi
  rm -f "$TD_W"
  echo
  if [ $TD_THOAT = 1 ] && [ $TD_CO_MAY = 1 ]; then
    td_in "${M_VANG}thoát -- máy của $(ten_tk "$TK") VẪN CHẠY${M_HET}"
    td_in "(mở lại v để nhận lại, hoặc t để trả)"
  elif [ $TD_LOI = 1 ]; then
    td_in "${M_DO}vòng lặp dừng vì lỗi ở trên${M_HET}"
    [ $TD_CO_MAY = 1 ] && td_in "máy của $(ten_tk "$TK") vẫn giữ (t để trả)"
  else
    td_in "vòng lặp đã dừng"
  fi
}
