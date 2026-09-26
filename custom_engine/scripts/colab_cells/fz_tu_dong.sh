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
#      khoan dang mo o cua so khac; khong xin duoc thi 10 phut sau thu lai.
#   2. 02 (neu may moi) -> 04 (SECS = han muc T4 - so phut chua, GAMES = so van con thieu) -> 06 ->
#      tai ve. Tong = so lon nhat trong ten goi + van DA XONG tren cac may dang chay; du muc tieu thi
#      moi cua so tao tep dung mem tren may minh (engine choi not van do roi thoat nhu het SECS).
#   3. Du muc tieu va moi may da tai ve: cua so co may nhieu han muc nhat huan luyen (cua so kia tra
#      may, cho). Gop du lieu (fz_tu_dong.py gop), can >= 20 phut T4 LUC SAP TAI LEN, tai len, 07,
#      tai mang moi ve. May mat giua chung -> xin may moi ngay, roi cu 10 phut mot lan, lam lai.
#   4. gh release upload -> GitHub Release (REL cua o 00), GEN_CURRENT + 1.
TD=$TKG/.tu_dong
TD_W=$TD/w_$$
TD_MUC_F=$TD/.muc_tieu
TD_DUNG=$TD/dung_tay
TD_PHUT_HL=20      # phut T4 toi thieu luc sap tai du lieu len de huan luyen
TD_PHUT_SINH=20    # sau khi tru so phut chua, con it hon chung nay phut choi thi khong chay 04, tra may
TD_CHO_XIN=600     # giay giua hai vong xin may
TD_SO_DOI=3        # so doi du lieu moi lan huan luyen: doi hien tai + 2 doi truoc
TD_CO_MAY=0        # cua so nay dang giu may (tai khoan $TK, ten $S)
TD_THOAT=0         # q: thoat vong lap o cua so nay, may van chay
TD_LOI=0           # loi khong tu sua duoc -> dung vong lap
TD_VAI=            # huan_luyen: cua so nay dang lo giai doan 3-4
TD_NHAN_LAI=0      # vua nhan lai may cua vong lap truoc -> xem may dang lam gi truoc
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
# Tong van doi $1: so lon nhat trong ten goi da tai + van da xong tren may cac cua so dang sinh / tai.
td_tong() {
  local f t=0 v co=1
  td_khoa && co=0
  for f in $(td_cac_cua_so); do
    [ "$(td_doc "$f" gen)" = "$1" ] || continue
    case $(td_doc "$f" buoc) in
      sinh|tai) v=$(td_doc "$f" van); t=$((t + ${v:-0})) ;;
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
td_xin_mot_vong() {
  local ds=() muc=() tk ten loai mo_ta rc
  mkdir -p "$TD"
  td_khoa_chon
  mapfile -t ds < <(echo; for tk in "$TKG"/*/; do [ -d "$tk" ] && basename "$tk"; done)
  for tk in "${ds[@]}"; do
    ten=$(ten_tk "$tk")
    [ -f "$TD/may_$ten" ] && tk_dang_nhap "$tk" && [ -z "$(cua_so_khac "$tk")" ] || continue
    dat_tk "$tk"
    py_colab ~/fz_nhan_may.py kiem "$S" >/dev/null 2>&1; rc=$?
    if [ $rc = 0 ]; then
      ghi_cua_so; TD_CO_MAY=1; TD_NHAN_LAI=1
      td_in "nhận lại máy của vòng lặp trước: $ten"
      td_mo_khoa_chon; return 0
    fi
    [ $rc = 1 ] && rm -f "$TD/may_$ten"
  done
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
  td_mo_khoa_chon
  return 1
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
    exec {fd}<"$fifo"
    ly_do=het
    while :; do
      if IFS= read -r -t 15 -u "$fd" dong; then
        printf '%s\n' "$dong"; lan=0
        [ "$o" = 04 ] && [[ "$dong" =~ ^\[selfplay\]\ ([0-9]+)/ ]] && td_ghi van="${BASH_REMATCH[1]}"
      else
        rc=$?
        [ -n "$dong" ] && printf '%s' "$dong"
        [ $NGAT = 1 ] && { ly_do=ngat; break; }
        [ $rc -gt 128 ] || break                      # het du lieu: ssh da thoat
      fi
      if [ "$o" = 04 ] && [ $da_dung = 0 ] && [ $((SECONDS - t)) -ge 15 ]; then
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
  tong=$(td_tong "$TD_G"); muc=$(td_muc)
  if [ "$tong" != "${TD_TONG_IN:-}" ] && [ $((SECONDS - ${TD_LUC_IN:-0})) -ge 60 ]; then
    td_in "đời $TD_G: ${M_DAM}$tong/$muc${M_HET} ván (đã tải $(tong_tich_luy "$TD_G"))"
    TD_TONG_IN=$tong; TD_LUC_IN=$SECONDS
  fi
  [ "$tong" -ge "$muc" ]
}
# Tao tep dung mem ma engine dang xem (doc tu dong lenh cua engine, nhu o 09b). 0 = da gui.
td_gui_dung() {
  local i out
  for i in 1 2 3; do
    out=$(ssh_colab "p=\$(pgrep -af '[c]ustom_engine.* --selfplay' | sed -n 's/.* --stop-file \([^ ]*\).*/\1/p' | head -1); if [ -n \"\$p\" ]; then touch \"\$p\" && echo FZ_DA_DUNG; else echo FZ_KHONG_CHAY; fi" 2>/dev/null)
    if grep -q FZ_DA_DUNG <<<"$out"; then
      td_in "${M_VANG}dừng mềm máy $(ten_tk "$TK")${M_HET}: $([ -f "$TD_DUNG" ] && echo "dừng tay" || echo "đủ $(td_muc) ván") -- ván dở chơi nốt"
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
  ssh_colab "b=$E_CL/build-linux/custom_engine; test -s \$b && echo BIN_\$(grep -c -a -- --stop-file \$b); test -s /content/gen$1.onnx && echo CO_ONNX; test -s /content/gen$1.pt && echo CO_PT" 2>/dev/null
}
td_chuan_bi() {
  local g=$1 can_pt=${2:-} out rc
  out=$(td_kiem_may_cl "$g")
  if ! grep -q '^BIN_[1-9]' <<<"$out" || ! grep -q CO_ONNX <<<"$out" || { [ -n "$can_pt" ] && ! grep -q CO_PT <<<"$out"; }; then
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
  if ! grep -q CO_ONNX <<<"$out"; then td_in "${M_DO}[!] Release không có gen$g.onnx${M_HET}"; return 2; fi
  if [ -n "$can_pt" ] && ! grep -q CO_PT <<<"$out"; then td_in "${M_DO}[!] Release không có gen$g.pt (cần để huấn luyện)${M_HET}"; return 2; fi
  return 0
}

# Giai doan 2 tren may cua cua so nay: 04 (tran theo han muc) -> 06 -> tai ve.
td_sinh() {
  local g=$1 rc secs muc tong so f
  td_chuan_bi "$g"; rc=$?
  case $rc in 0) ;; 2) TD_LOI=1; return ;; 3) td_mat_may; return ;; 4) return ;; *) td_ngu 30; return ;; esac
  [ -f "$TD_DUNG" ] && return
  secs=$(td_giay_t4)
  if [ -z "$secs" ]; then td_in "không đọc được hạn mức -- thử lại sau 1 phút"; td_ngu 60; return; fi
  secs=$((secs - $(chua_phut) * 60))
  if [ $secs -lt $((TD_PHUT_SINH * 60)) ]; then
    td_in "$(ten_tk "$TK"): hạn mức còn $((secs / 60 + $(chua_phut))) phút T4 -> trả máy"
    td_tra; return
  fi
  muc=$(td_muc); tong=$(td_tong "$g"); so=$((muc - tong))
  [ $so -ge 1 ] || return
  f=$TD/o_$$/$(basename "$(ls "$D"/04_*.py | head -1)")
  mkdir -p "$TD/o_$$"
  sed -E "0,/^SECS[[:space:]]*=[[:space:]]*[0-9]+/s//SECS = $secs/; 0,/^GAMES[[:space:]]*=[[:space:]]*[0-9]+/s//GAMES = $so/" \
    "$(ls "$D"/04_*.py | head -1)" > "$f"
  TD_G=$g; TD_TONG_IN=
  td_ghi gen="$g" buoc=sinh van=0
  td_in "04 trên $(ten_tk "$TK"): tối đa $so ván, SECS=$secs (≈ $((secs / 60)) phút) · đời $g: $tong/$muc"
  td_chay 04 "$f"; rc=$?
  case $rc in 3) td_mat_may; return ;; 4) return ;; esac
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

# May vua nhan lai (vong lap truoc bi dong giua chung): may dang lam gi thi lam tiep viec do.
td_tiep_tuc() {
  local g=$1 o pid tt rc
  read -r o pid <<<"$(ssh_colab "cat $LOGD/dang_chay 2>/dev/null" 2>/dev/null)"
  [ -n "$o" ] || return 0
  tt=$(ssh_colab "python3 $LOGD/fz_may.py trang_thai $o $pid" 2>/dev/null)
  td_in "máy đang có ô $o ($tt)"
  case "$o:$tt" in
    04:chay)
      TD_G=$g; TD_TONG_IN=; td_ghi gen="$g" buoc=sinh van=0
      td_xem 04 "$pid" 50; rc=$?
      case $rc in 3) td_mat_may; return ;; 4) return ;; esac
      td_gom_tai "$g" ;;
    04:*) td_ghi gen="$g" buoc=tai van=0; td_gom_tai "$g" ;;
    06:chay) td_ghi gen="$g" buoc=tai
             td_xem 06 "$pid" 20; rc=$?; [ $rc = 0 ] || { [ $rc = 3 ] && td_mat_may; return; }
             TAI_VE_MOC=td_van_0 tai_theo_o 06 ;;
    06:*) td_ghi gen="$g" buoc=tai; TAI_VE_MOC=td_van_0 tai_theo_o 06 ;;
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
        if [ $lan -gt 0 ]; then td_in "$((TD_CHO_XIN / 60)) phút nữa xin lại"; td_ngu $TD_CHO_XIN || return; fi
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

# Chua xin duoc may: cho TD_CHO_XIN giay (thoi som khi den luot huan luyen / du van / dung / doi doi).
td_cho_xin() {
  local g=$1 i
  td_in "chưa xin được máy -- $((TD_CHO_XIN / 60)) phút nữa thử lại"
  for ((i = 0; i < TD_CHO_XIN; i += 10)); do
    td_ngu 10 || return
    [ -f "$TD_DUNG" ] && return
    [ "$(td_gen)" = "$g" ] || return
    td_toi_luot_hl "$g" && return
    [ "$(td_tong "$g")" -ge "$(td_muc)" ] && return
  done
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
  [ ${#khac[@]} -eq 0 ] && rm -f "$TD_DUNG"
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
      td_tra; break
    fi
    if td_toi_luot_hl "$g" || [ "$(td_tong "$g")" -ge "$(td_muc)" ]; then td_giai_doan_3 "$g"; continue; fi
    if [ $TD_CO_MAY = 0 ]; then
      td_ghi gen="$g" buoc=xin van=0
      td_xin_mot_vong || { td_cho_xin "$g"; continue; }
    fi
    if [ $TD_NHAN_LAI = 1 ]; then TD_NHAN_LAI=0; td_tiep_tuc "$g"; continue; fi
    td_sinh "$g"
  done
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
