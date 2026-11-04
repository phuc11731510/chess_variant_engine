# cv_tu_dong.sh -- VONG LAP TU DONG cua menu cv (chep tu fz_tu_dong.sh cua engine bien the): sinh du lieu -> gop -> huan luyen -> len doi, lap lai.
# menu.sh SOURCE tep nay (muc v, hoac `cv tu_dong`) va dung lai ham cua menu (xin_may, khoi_dong_ssh,
# ssh_colab, tai_ve, tai_len, tai_theo_o, ...). Tinh toan (xep tai khoan, gop du lieu): $CVD/cv_tu_dong.py.
#
# Moi cua so Termux chay vong lap = lo tron MOT may (mot tai khoan -- Colab mien phi khong cho hai may
# mot tai khoan). N cua so = toi da N may (da dung toi 4), phoi hop qua tep tren dien thoai:
#   ~/.fz_tk/.cv_tu_dong/w_<pid>     trang thai tung cua so (cach, doi, buoc, so lan chay mang tren may cua no)
#   ~/.fz_tk/.cv_tu_dong/may_<tk>    may cua vong lap dang giu o tai khoan <tk> (mo lai vong lap -> nhan lai)
#   ~/.fz_tk/.cv_tu_dong/hl_<cach>_<G>/  khoa "cua so dang huan luyen doi G cua cach do"
#   ~/.fz_tk/.cv_tu_dong/dung_tay    dung mem ca vong lap (Ctrl+C -> s o bat ky cua so nao)
#   Download/CoVua/<cach>/doi.txt              doi hien tai cua cach (tt = truyen thong, cay = cay tro choi)
#   Download/CoVua/<cach>/games_gen<G>_<N>.zip goi van, ten tich luy: N = tong SO LAN CHAY MANG da tai ve cua doi G
#   Download/CoVua/<cach>/games_gen<G>/        cac lan sinh da gop (giu vinh vien: van, mau, log)
#   Download/CoVua/<cach>/gen<G>.pb.gz, .pt    mang (Release co_vua_mang: <cach>_gen<G>.*)
#   Download/CoVua/log/nhat_ky_vong_lap.txt    nhat ky vong lap, giu vinh vien
#
# KHAC fz (bat buoc, de hai cach hoc so duoc o cung luong tinh toan): mot doi du khi du SO LAN CHAY MANG, khong phai
# du so van. Ngan sach moi doi (ngan_sach, mac dinh 250 000 x 800 = 200 trieu) tinh CONG DON: xong doi G thi tong cua
# cac doi 0..G phai dat ngan_sach x (G + 1); phan doi truoc vuot thi doi G bot dung chung ay, nhung doi nao cung tu
# sinh it nhat nua ngan sach (cv_tu_dong.py can). Moi may duoc giao phan con thieu (EVALS cua o 04) nhu fz giao GAMES,
# va van dang do tren moi may duoc tinh vao tong theo uoc luong cua chinh may do (sinh.py: "uoc con").
#
# Mot doi G cua mot cach (Download/CoVua/<cach>/doi.txt; sau moi doi vong lap tu tang):
#   1. Chua co may: xin T4 theo thu tu fz_tu_dong.py xep (da nap lai / xanh / chua chup ...), bo tai
#      khoan dang mo o cua so khac; khong xin duoc thi theo LICH CHUNG (td_lich: gio nap lai som nhat,
#      HET khong ro gio nap: moi gio; con tai khoan thu duoc: 10 phut) -- chi mot cua so xin moi lan.
#   2. 02 (neu may moi) -> 04 (SECS = han muc T4 - so phut chua, EVALS = so lan chay mang con thieu) -> 06 ->
#      tai ve. Tong = so lon nhat trong ten goi + van DA XONG tren cac may dang chay; du muc tieu thi
#      moi cua so tao tep dung mem tren may minh (engine choi not van do roi thoat nhu het SECS).
#   3. Du muc tieu va moi may da tai ve: cua so co may nhieu han muc nhat huan luyen (cua so kia tra
#      may, cho). Gop du lieu (fz_tu_dong.py gop), can >= 20 phut T4 LUC SAP TAI LEN, tai len, 07,
#      tai mang moi ve. May mat giua chung -> xin may moi ngay, roi cu 10 phut mot lan, lam lai.
#   4. gh release upload <cach>_gen<n>.pb.gz + .pt -> GitHub Release co_vua_mang (REL_NN cua o 00; ve kiem tra
#      sha256), xoa .pb.gz cac doi truoc tren Release (Release giu .pt MOI doi nhung chi .pb.gz doi moi nhat;
#      mot Release chua toi da 1000 tep nen vong lap DUNG khi ra doi TD_GEN_CUOI = 490), doi + 1 (doi.txt),
#      roi don dien thoai (td_don_dep): chi goi van da gop vao thu muc -- thu muc van, mang, log giu het.
#   0. ARENA (hoi luc bat dau: day doi so sanh, mac dinh 10 20 ... 100; so van, mac dinh 1000): doi k nao trong
#      day ma ca hai cach da co mang doi k thi, truoc khi sinh du lieu, moi cua so dau tt_gen<k> vs cay_gen<k>
#      (o 08, 400 luot tham), tong van chia cho cac may nhu o 04 (dem ca van dang do, du thi dung mem). Ket qua tung
#      may cong vao Download/CoVua/arena/tt_gen<k>_vs_cay_gen<k>.txt; du van -> dong XONG = arena do da xong,
#      vong lap khong lam lai (dung mem giua chung -> lan sau choi not phan con thieu).
TD=$TKG/.cv_tu_dong
TD_W=$TD/w_$$
TD_MUC_F=$TD/.muc_tieu
TD_DUNG=$TD/dung_tay
TD_DUNG_RIENG=$TD/dung_cs_$$   # dung mem RIENG cua so nay (d trong menu Ctrl+C); TD_DUNG = dung ca vong lap
TD_PHUT_HL=20      # phut T4 toi thieu luc sap tai du lieu len de huan luyen
TD_PHUT_SINH=20    # sau khi tru so phut chua, con it hon chung nay phut choi thi khong chay 04, tra may
TD_SO_DOI=4        # so doi du lieu moi lan huan luyen: doi hien tai + 3 doi truoc (tu doi 12, 2026-09-29; truoc la 3)
TD_GEN_CUOI=490    # doi mang cuoi cung duoc huan luyen + len GitHub: ra doi nay thi DUNG vong lap
TD_REL_TOI_DA=1000 # so tep toi da cua mot Release GitHub (co_vua_mang: .pt doi 0..490 cua 2 cach + 2 .pb.gz = 984 tep)
TD_CO_MAY=0        # cua so nay dang giu may (tai khoan $TK, ten $S)
TD_THOAT=0         # q: thoat vong lap o cua so nay, may van chay
TD_LOI=0           # loi khong tu sua duoc -> dung vong lap
TD_VAI=            # huan_luyen: cua so nay dang lo giai doan 3-4
TD_NHAN_LAI=0      # vua nhan lai may cua vong lap truoc -> xem may dang lam gi truoc
TD_AR_DAY_F=$TD/.arena_day   # day doi arena (vd "11 12 15"), hoi luc bat dau
TD_AR_VAN_F=$TD/.arena_van   # so van moi arena
TD_AR_DIR=$TAI/arena         # ket qua arena cua vong lap (tren dien thoai, xem duoc)
TD_KIEU=           # o dang xem la arena (td_xem / td_can_dung dem theo arena)
TD_AR_G=           # doi cua arena dang lam (td_ar_viec)
# Goi chay tren may (o 02 giai goi.tar.gz vao day): PHAI khop CV cua o 00.
CV_CL=/content/cv
# Cach hoc cua viec dang lam: TB = thu muc du lieu cua no tren dien thoai.
TD_BEN=tt; TB=$TAI/tt
td_dat_ben() { TD_BEN=$1; TB=$TAI/$1; mkdir -p "$TB"; }
# ---- DIEU PHOI HAI CACH (khong co trong fz: fz chi co mot cach hoc) ----
# Cac cach vong lap duoc lam ($TD/.cac_ben, mac dinh "tt"): cach cay tro choi chua viet, nen chua bat. Moi cua so,
# truoc moi viec, tu chon cach DANG TUT LAI (tong so lan chay mang cong don nho hon) ma con viec cho cua so nay
# (con thieu luong tinh toan, hoac du roi va chua ai huan luyen); ca hai deu khong con viec thi chon cach tut lai
# (cua so do cho, nhu fz). Hai cach so o CUNG DOI = cung luong tinh toan, nen quy tac nay chi quyet dinh cach nao toi
# doi do som hon, khong anh huong phep so sanh. TD_BEN_EP (hoi luc bat dau): ep cua so nay chi lam mot cach.
TD_CAC_BEN_F=$TD/.cac_ben
TD_BEN_EP=
td_cac_ben() { local x; x=$(cat "$TD_CAC_BEN_F" 2>/dev/null); echo "${x:-tt}"; }
# Tong so lan chay mang cong don cua cach dang dat (moi doi truoc + doi hien tai, tinh ca van dang do).
td_cong_don() {
  local g truoc
  g=$(td_gen)
  truoc=$(python $CVD/cv_tu_dong.py can "$TB" "$g" "$(ngan_sach)" 2>/dev/null | cut -d' ' -f2)
  echo $(( ${truoc:-0} + $(td_tong "$g") ))
}
# Cach dang dat con viec cho mot cua so khong: con thieu luong tinh toan (sinh), hoac du roi va chua ai huan luyen /
# chua may nao dang sinh, tai ve (huan luyen). 0 = con.
td_co_viec() {
  local g
  g=$(td_gen)
  [ "$g" -ge "$TD_GEN_CUOI" ] && return 1
  if ! td_toi_luot_hl "$g" && [ "$(td_tong "$g")" -lt "$(td_muc "$g")" ]; then return 0; fi
  [ -z "$(td_chu_hl "$g")" ] && ! td_ai_ban "$g"
}
# In cach cho viec ke tiep cua cua so nay (xem tren). Chay trong subshell: khong doi TD_BEN / TB cua cua so.
td_chon_ben() {
  local b ds=()
  if [ -n "$TD_BEN_EP" ]; then echo "$TD_BEN_EP"; return; fi
  mapfile -t ds < <(for b in $(td_cac_ben); do echo "$( (td_dat_ben "$b"; td_cong_don) ) $b"; done | sort -n | cut -d' ' -f2)
  for b in "${ds[@]}"; do ( td_dat_ben "$b"; td_co_viec ) && { echo "$b"; return; }; done
  echo "${ds[0]:-tt}"
}
# Tinh trang hai cach (menu b, va luc bat dau vong lap): doi, luong tinh toan cong don, doi hien tai da co bao nhieu.
td_hai_ben() {
  local b g
  echo "${M_DAM}== Hai cách học ==${M_HET}  (ngân sách mỗi đời: $(ngan_sach) lần chạy mạng)"
  for b in tt cay; do
    ( td_dat_ben "$b"; g=$(td_gen)
      printf ' %-4s đời %-3s · cộng dồn %s lần chạy mạng · đời %s: %s/%s%s\n' "$b" "$g" "$(td_cong_don)" "$g" \
        "$(td_tong "$g")" "$(td_muc "$g")" "$(grep -qw "$b" <<<"$(td_cac_ben)" || echo "  ${M_MO}(vòng lặp chưa làm cách này)${M_HET}")" )
  done
  echo "${M_MO} tt = truyền thống · cay = cây trò chơi (chưa viết)${M_HET}"
}
# Ban chep cua o 00 voi BEN / GEN_CURRENT cua viec dang lam (menu ghep() dung TD_O00): tep o 00 cua ban khong bi sua.
td_o00() {
  mkdir -p "$TD/o_$$"
  TD_O00=$TD/o_$$/00_cau_hinh.py
  doc "$D/00_cau_hinh.py" | sed -E "0,/^BEN[[:space:]]*=.*/s//BEN = \"$TD_BEN\"/; 0,/^GEN_CURRENT[[:space:]]*=[[:space:]]*[0-9]+/s//GEN_CURRENT = $(td_gen)/" > "$TD_O00"
}

# Moi dong thong bao cua vong lap cung duoc ghi vao $TD_NK (pid cua so, ngay gio, noi dung; bo mau): sau khi cua so
# treo / bi dong van xem lai duoc no da lam gi. Khac fz: nhat ky nam o Download/CoVua/log (mo duoc bang MT Manager)
# va KHONG BAO GIO bi cat bot -- log la minh chung cua du an, giu vinh vien (chu du an yeu cau 2026-11-03).
TD_NK=$TAI/log/nhat_ky_vong_lap.txt
td_in() {
  echo "${M_LAM}[tự động $(date +%H:%M)]${M_HET} $*"
  mkdir -p "${TD_NK%/*}" 2>/dev/null
  printf '%s %s %s\n' "$$" "$(date '+%Y-%m-%d %H:%M:%S')" "$*" 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g' >> "$TD_NK" 2>/dev/null
  return 0
}
td_gen() { local n; n=$(cat "$TB/doi.txt" 2>/dev/null); [[ "$n" =~ ^[0-9]+$ ]] && echo $((10#$n)) || echo 0; }
# So lan chay mang doi $1 (mac dinh doi hien tai) cua cach dang lam CAN (cong don, xem dau tep). Doi < G khong doi
# trong luc lam doi G, nen tinh mot lan moi doi (tep dem .can_doi<G>_<ngan sach>).
td_muc() {
  local g=${1:-$(td_gen)} f
  mkdir -p "$TB" 2>/dev/null; f=$TB/.can_doi${g}_$(ngan_sach)
  [ -s "$f" ] || python $CVD/cv_tu_dong.py can "$TB" "$g" "$(ngan_sach)" 2>/dev/null | cut -d' ' -f1 > "$f"
  cat "$f"
}
td_home() { if [ -n "$1" ]; then echo "$TKG/$1"; else echo "$HOME"; fi; }
td_song() { tr '\0' ' ' 2>/dev/null < "/proc/$1/cmdline" | grep -q 'menu\.sh'; }
# Release giu mang (REL_NN cua o 00): .pt MOI doi + .pb.gz doi moi nhat cua moi cach. td_rel_nn in "<chu>/<kho> <tag>",
# td_rel_nn_url in URL thu muc tai ve (REL_NN dung cho wget tren Colab). REL (v3.0.0) chi con binary + ONNX Runtime.
td_rel_nn() { doc "$D/00_cau_hinh.py" 2>/dev/null | sed -n 's#^REL_NN *= *"https://github.com/\([^/]*/[^/]*\)/releases/download/\([^"]*\)".*#\1 \2#p' | head -1; }
td_rel_nn_url() { doc "$D/00_cau_hinh.py" 2>/dev/null | sed -n 's/^REL_NN *= *"\([^"]*\)".*/\1/p' | head -1; }
# Tep cua Release $2 ($1 = chu/kho), moi dong "ten<TAB>kich thuoc<TAB>sha256:...". Loi mang / chua dang nhap -> ma 1.
td_tep_release() {
  local id
  id=$(gh api "repos/$1/releases/tags/$2" --jq .id 2>/dev/null) && [[ "$id" =~ ^[0-9]+$ ]] || return 1
  gh api --paginate "repos/$1/releases/$id/assets?per_page=100" --jq '.[] | [.name, .size, (.digest // "")] | @tsv' 2>/dev/null
}

# Trang thai cua so nay: dong "khoa=gia tri" trong $TD_W (ghi qua tep tam an + mv: doc khong do dang).
td_ghi() {
  local kv t=$TD/.w_$$.tmp
  cat "$TD_W" > "$t" 2>/dev/null || : > "$t"
  for kv in "$@"; do
    sed -i "/^${kv%%=*}=/d" "$t"; echo "$kv" >> "$t"
    [ "${kv%%=*}" = buoc ] && td_pha "${kv#*=}"
  done
  sed -i "/^ben=/d" "$t"; echo "ben=$TD_BEN" >> "$t"       # cach cua viec dang lam (cua so khac loc theo)
  mv "$t" "$TD_W"
}
# ---- Ke toan THOI GIAN GIU MAY: may dang giu (tieu han muc) thi moi buoc mat bao lau. In luc tra / mat may, de
# thay "thoi gian chet" (giu may ma khong chay 04 / 07 / 08) nam o dau thay vi doan.
declare -gA TD_PH_TONG=()
TD_PH=; TD_PH_T=$SECONDS; TD_MAY_T=
td_may_bat_dau() { TD_PH_TONG=(); TD_PH=; TD_PH_T=$SECONDS; TD_MAY_T=$SECONDS; }
td_pha() {
  local moi=$1
  [ -n "$TD_MAY_T" ] && [ -n "$TD_PH" ] && TD_PH_TONG[$TD_PH]=$(( ${TD_PH_TONG[$TD_PH]:-0} + SECONDS - TD_PH_T ))
  TD_PH=$moi; TD_PH_T=$SECONDS
}
# Tong ket (goi truoc khi tra / khi mat may). Doc: "sinh" va "huan luyen"/"arena" la thoi gian co ich; con lai la cho.
td_may_tong_ket() {
  local k v out= tong
  [ -n "$TD_MAY_T" ] || return 0
  td_pha "$TD_PH"
  tong=$((SECONDS - TD_MAY_T))
  for k in sinh huan_luyen arena chuan_bi tai xong cho_hl xin; do
    v=${TD_PH_TONG[$k]:-0}; [ "$v" -ge 60 ] || continue
    case $k in
      sinh) k="sinh dữ liệu (04)" ;; huan_luyen) k="huấn luyện (tải lên + 07 + tải mạng)" ;; arena) k="arena (08)" ;;
      chuan_bi) k="chuẩn bị (02)" ;; tai) k="gom + tải ván về (06)" ;; xong) k="rảnh giữa các bước" ;;
      cho_hl) k="chờ tới lượt huấn luyện" ;; xin) k="xin máy" ;;
    esac
    out+=" · $k $((v / 60)) phút"
  done
  [ -n "$out" ] && out=${out# · } || out="(dưới 1 phút mỗi bước)"
  td_in "giữ máy $(ten_tk "$TK") $((tong / 60)) phút: $out"
  TD_MAY_T=; TD_PH=; TD_PH_TONG=()
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
# Phan con lai (uoc luong) cua cac van dang do tren may cua cua so (tep $1): sinh.py tu uoc luong va in "uoc con" moi
# 15 giay (moi van do con nua van trung binh); td_xem ghi vao con=. Sau dung mem may van in, nen so nay giam dan ve 0.
td_dang_do() { local c; c=$(td_doc "$1" con); echo "${c:-0}"; }
# Tong so lan chay mang doi $1 cua cach dang lam: so lon nhat trong ten goi da tai + lan chay mang da xong VA uoc luong
# phan con lai cua van dang do tren may cac cua so dang sinh / tai. Tinh ca van dang do: du muc tieu thi dung mem LUC DO,
# van dang do choi not la vua du, va cua so khac khong nhan lai phan van dang choi.
td_tong() {
  local f t=0 v co=1
  td_khoa && co=0
  for f in $(td_cac_cua_so); do
    [ "$(td_doc "$f" gen)" = "$1" ] && [ "$(td_doc "$f" ben)" = "$TD_BEN" ] || continue
    case $(td_doc "$f" buoc) in
      sinh) v=$(td_doc "$f" van); t=$((t + ${v:-0} + $(td_dang_do "$f"))) ;;
      tai) v=$(td_doc "$f" van); t=$((t + ${v:-0})) ;;
    esac
  done
  t=$((t + $(tong_tich_luy "$1" "$TB")))
  [ $co = 0 ] && rmdir "$TAI/.khoa_dat_ten" 2>/dev/null
  echo $t
}
td_co_mang() { [ -s "$TB/gen$1.pb.gz" ] && [ -s "$TB/gen$1.pt" ]; }
# Den luot giai doan 3-4 cua doi $1: da co mang doi sau tren dien thoai (chi con tai len GitHub), da co
# goi gop, hoac so van DA TAI VE du muc tieu.
td_toi_luot_hl() {
  td_co_mang $(($1 + 1)) || [ -f "$TB/games_gen$1.zip" ] || [ "$(tong_tich_luy "$1" "$TB")" -ge "$(td_muc "$1")" ]
}

# Ctrl+D (EOF tren ban phim) trong luc vong lap dang chay = nhu Ctrl+C: mo menu thoat co hoi (d / s / q). Doc
# terminal khong chan (toi da 0.05 giay); chi tinh EOF (read tra 1), phim khac bi nuot + bo.
TD_HB=0
td_ctrl_d() {
  local k rc
  # Nhip tim: cua so con song thi tep trang thai $TD_W duoc "cham" moi 30 giay (07 chay nhieu phut khong ghi gi), de
  # cua so khac / menu a phan biet "dang chay tot" voi "da treo" (xem cua_so_ket).
  if [ $((SECONDS - TD_HB)) -ge 30 ]; then TD_HB=$SECONDS; [ -f "$TD_W" ] && touch "$TD_W" 2>/dev/null; fi
  [ -t 0 ] || return 0
  IFS= read -rs -t 0.05 -N 1 k 2>/dev/null; rc=$?
  if [ $rc = 1 ]; then NGAT=1
  elif [ $rc = 0 ]; then while IFS= read -rs -t 0.01 -N 1 k 2>/dev/null; do :; done
  fi
  return 0
}
# Ngu $1 giay, Ctrl+C / Ctrl+D -> hoi (d / s / q / Enter). 1 = nguoi dung chon q.
td_ngu() {
  local i
  for ((i = 0; i < $1; i++)); do
    sleep 1; td_ctrl_d
    if [ $NGAT = 1 ]; then td_hoi_ngat; [ $TD_THOAT = 1 ] && return 1; fi
  done
  return 0
}
# Dung mem (cua so nay HOAC ca vong lap)?
td_dung_ca() { [ -f "$TD_DUNG" ] || [ -f "$TD_DUNG_RIENG" ]; }
# Ctrl+C trong vong lap: bam MOT lan = menu thoat (hien o cho kiem tra ke tiep); bam HAI lan trong 3 giay = thoat
# ngay du cua so dang ket o dau (lenh treo khong kiem co NGAT). Co may thi may VAN CHAY, nhac cach tra.
TD_INT_LUC=-99
td_int() {
  NGAT=1
  if [ $((SECONDS - TD_INT_LUC)) -le 3 ]; then
    echo; echo "${M_DO}[thoát ngay]${M_HET}"
    [ "${TD_CO_MAY:-0}" = 1 ] && echo "${M_VANG}máy của $(ten_tk "$TK") VẪN CHẠY (tiêu hạn mức): mở lại v để nhận lại, hoặc menu t để trả${M_HET}"
    [ "$(cat "$TD/.khoa_chon/pid" 2>/dev/null)" = $$ ] && rm -rf "$TD/.khoa_chon"
    rm -f "$TD_DUNG_RIENG"
    exit 130
  fi
  TD_INT_LUC=$SECONDS
}
td_hoi_ngat() {
  local x
  NGAT=0
  echo
  echo "${M_DAM}== Vòng lặp tự động ==${M_HET}"
  echo " ${M_DAM}d${M_HET}      dừng mềm CỬA SỔ NÀY (cửa sổ"
  echo "        khác vẫn chạy): chơi nốt ván"
  echo "        dở, gom, tải về, trả máy, thoát."
  echo "        Chưa có máy -> thoát ngay"
  echo " ${M_DAM}s${M_HET}      dừng mềm CẢ vòng lặp (mọi cửa sổ)"
  echo " ${M_DAM}q${M_HET}      thoát NGAY -- máy và ô trên"
  echo "        Colab VẪN CHẠY (tiêu hạn mức);"
  echo "        mở lại v để nhận lại"
  echo " ${M_DAM}Enter${M_HET}  tiếp tục"
  echo "${M_MO}(Ctrl+C 2 lần liền = thoát ngay)${M_HET}"
  read -rp "Chọn: " x
  case "$x" in
    d|D)
      if [ $TD_CO_MAY = 1 ]; then : > "$TD_DUNG_RIENG"; td_in "đã yêu cầu dừng mềm RIÊNG cửa sổ này"
      else TD_THOAT=1; fi ;;
    s|S) : > "$TD_DUNG"; td_in "đã yêu cầu dừng mềm" ;;
    q|Q)
      if [ $TD_CO_MAY = 1 ]; then
        echo "${M_VANG}Máy của $(ten_tk "$TK") VẪN CHẠY và tiêu hạn mức tới khi bạn trả (menu t) hoặc Colab thu hồi.${M_HET}"
        read -rp "Thoát thật? Gõ 'co' (Enter = ở lại): " x || x=
        [ "$x" = co ] && TD_THOAT=1
      else
        TD_THOAT=1
      fi ;;
  esac
  NGAT=0
}

# Giay T4 con chay duoc cua tai khoan dang giu may (chua tru so phut chua). Rong = khong doc duoc.
td_giay_t4() {
  local may g
  may=$(colab status -s "$S" 2>/dev/null | sed -n 's/.*Hardware: *\([^ |]*\).*/\1/p' | head -1)
  g=$(py_colab $CVD/fz_han_muc.py --may "$may" --giay-t4 2>/dev/null)
  [[ "$g" =~ ^[0-9]+$ ]] && echo "$g"
}
# 0 = may cua cua so nay con (hoac mat mang, khong biet), 1 = da mat.
# rc 1 = may mat; 0 = con; khac (2 = loi mang / dang nhap, 75 = can dang nhap, 124 = treo) = khong biet. Truoc day
# "khong biet" tinh la CON mai mai: may da bi Colab thu hoi ma vong lap van "noi lai sau 30 giay" voi tai
# khoan hong token. Gio 6 lan "khong biet" lien (~vai phut) -> coi nhu MAT de cua so tiep tuc xin may khac.
TD_CON_KB=0
td_con_may() {
  local rc
  HOME=$TKH timeout 60 python $CVD/fz_nhan_may.py con "$S" >/dev/null 2>&1; rc=$?
  case $rc in
    0) TD_CON_KB=0; return 0 ;;
    1) TD_CON_KB=0; return 1 ;;
  esac
  TD_CON_KB=$((TD_CON_KB + 1))
  if [ $TD_CON_KB -ge 6 ]; then
    td_in "${M_DO}không xác minh được máy của $(ten_tk "$TK") $TD_CON_KB lần liền (mạng / đăng nhập)${M_HET} -> coi như đã mất"
    TD_CON_KB=0; return 1
  fi
  return 0
}
td_mat_may() {
  td_may_tong_ket
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
  td_may_tong_ket
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
# Cho khoa: Ctrl+C thoat duoc (return 1); nguoi giu khoa treo qua 20 phut (mot vong xin toi da ~10 phut: moi lenh
# colab co gioi han thoi gian) -> pha khoa. Truoc day vong cho `sleep 1` mai mai khong nhin Ctrl+C: mot cua so
# ket o lenh xin may giu khoa thi cua so kia (tai khoan lanh lan) dung hinh theo.
td_khoa_chon() {
  local p t i=0
  while ! mkdir "$TD/.khoa_chon" 2>/dev/null; do
    p=$(cat "$TD/.khoa_chon/pid" 2>/dev/null)
    if [ -n "$p" ] && ! td_song "$p"; then rm -rf "$TD/.khoa_chon"; continue; fi
    t=$(stat -c %Y "$TD/.khoa_chon" 2>/dev/null || echo 0)
    if [ "$t" -gt 0 ] && [ $(( $(date +%s) - t )) -gt 1200 ]; then
      td_in "${M_VANG}khoá chọn tài khoản treo > 20 phút (cửa sổ giữ khoá không phản hồi) -> phá khoá${M_HET}"
      rm -rf "$TD/.khoa_chon"; continue
    fi
    sleep 1; td_ctrl_d; i=$((i + 1))
    [ $((i % 30)) = 0 ] && td_in "chờ cửa sổ khác chọn tài khoản xong ($i giây)..."
    if [ $NGAT = 1 ]; then td_hoi_ngat; [ $TD_THOAT = 1 ] && return 1; fi
  done
  echo $$ > "$TD/.khoa_chon/pid"
  return 0
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
    py_colab $CVD/fz_nhan_may.py kiem "$S" >/dev/null 2>&1; rc=$?
    if [ $rc = 0 ]; then
      ghi_cua_so; TD_CO_MAY=1; TD_NHAN_LAI=1; td_may_bat_dau
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
# Token cua tai khoan dang dat (dat_tk) dung duoc khong? Lam moi truoc (nguyen tu, co thu lai) de lenh colab sau do
# khong phai tu lam moi. 0 = dung duoc. Tai khoan hong / mang chap chon -> bo qua tai khoan do, KHONG treo.
td_token_ok() {
  local kq rc
  [ -f $CVD/fz_colab.py ] || return 0
  kq=$(HOME=$TKH timeout 90 python $CVD/fz_colab.py --token 2>&1); rc=$?
  case $rc in
    0) return 0 ;;
    3|124) td_in "${M_VANG}bỏ qua $1: mạng chập chờn khi làm mới token${M_HET} (thử lại sau, KHÔNG cần đăng nhập lại)" ;;
    *) td_in "${M_DO}bỏ qua $1: token không dùng được${M_HET} (${kq##*FZ_TOKEN=}) -- đăng nhập lại: cv -> a -> x (xoá) -> n (thêm)" ;;
  esac
  return 1
}
td_xin_mot_vong() {
  local ds=() muc=() tk ten loai mo_ta rc
  mkdir -p "$TD"
  td_khoa_chon || return 1
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
    touch "$TD/.khoa_chon" 2>/dev/null          # con lam viec: khoa khong bi coi la treo (xem td_khoa_chon)
    if [ -n "$(cua_so_khac "$tk")" ]; then echo "   ${M_MO}bỏ qua $ten: đang mở ở cửa sổ khác${M_HET}"; continue; fi
    dat_tk "$tk"
    td_token_ok "$ten" || { td_ranh; continue; }
    if [ -n "$(COLAB_TO=60 colab sessions 2>/dev/null | grep '^\[' | grep -v '^\[colab\]')" ]; then
      echo "   ${M_MO}bỏ qua $ten: đang giữ máy (không phải của vòng lặp)${M_HET}"; continue
    fi
    ghi_cua_so                                  # danh dau truoc: cua so khac bo qua tai khoan nay
    date +%s > "$TD/thu_$ten"
    td_in "xin T4: ${M_DAM}$ten${M_HET} ($mo_ta)"
    if xin_may T4; then
      TD_CO_MAY=1; td_may_bat_dau
      date +%s > "$TD/may_$ten"
      td_mo_khoa_chon; return 0
    fi
    td_ranh
    if [ $NGAT = 1 ]; then
      # Nha khoa chon TRUOC khi hoi (nguoi dung co the roi di): cua so khac khong bi chan boi mot lua chon bo ngo.
      td_mo_khoa_chon; td_hoi_ngat
      [ $TD_THOAT = 1 ] && return 1
      td_khoa_chon || return 1
    fi
  done 3< <(python $CVD/cv_tu_dong.py xep "${muc[@]}")
  # Ca vong khong xin duoc: dat lich chung (thu_<ten> vua ghi o tren -> moc "moi gio" dung).
  muc=()
  for tk in "${ds[@]}"; do
    tk_dang_nhap "$tk" && muc+=("$(ten_tk "$tk")|$(td_home "$tk")|$(cat "$TD/thu_$(ten_tk "$tk")" 2>/dev/null)")
  done
  if ! python $CVD/cv_tu_dong.py hen "${muc[@]}" > "$TD_XIN_SAU.t" 2>/dev/null || [ ! -s "$TD_XIN_SAU.t" ]; then
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
    [ $TD_THOAT = 1 ] && return 1
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

# Xem log o $1 (pid $2) den khi o ket thuc; $3 = chi in tu $3 dong cuoi. O 04: dem lan chay mang (dong
# "[sinh] ..." cua sinh.py), moi 15 giay xem tong -- du muc tieu (hoac dung tay) thi tao tep dung mem tren may. Luong log
# qua MOT ssh (Colab chi cho mot ssh moi may): gui lenh thi ngat luong, gui, roi noi lai.
# 0 = o ket thuc, 3 = mat may, 4 = nguoi dung chon q.
td_xem() {
  local o=$1 pid=$2 them=${3:-} fifo=$TD/.luong_$$ sp fd dong rc t=$SECONDS lan=0 bd=0 ly_do cho
  local da_dung=0 sil=$SECONDS nhac=$SECONDS ctl=$SECONDS
  while :; do
    rm -f "$fifo"; mkfifo "$fifo" || return 1
    NGAT=0
    ssh_colab "python3 $LOGD/fz_may.py theo_doi $o $pid $them" > "$fifo" 2>/dev/null &
    sp=$!
    command exec {fd}<"$fifo" || { td_giet "$sp"; td_ngu 5 || return 4; continue; }
    ly_do=het
    while :; do
      if IFS= read -r -t 15 -u "$fd" dong; then
        printf '%s\n' "$dong"; lan=0; sil=$SECONDS; nhac=$SECONDS
        # sinh.py: "[sinh] <van> van, <evals> evals, dang choi <d>, uoc con <r>, giao <x>" moi 15 giay; ket thuc: con 0.
        [ "$o" = 04 ] && [[ "$dong" =~ ^\[sinh\]\ [0-9]+\ van,\ ([0-9]+)\ evals,\ dang\ choi\ [0-9]+,\ uoc\ con\ ([0-9]+) ]] &&
          td_ghi van="${BASH_REMATCH[1]}" con="${BASH_REMATCH[2]}"
        [ "$o" = 04 ] && [[ "$dong" =~ ^\[sinh\]\ Ket\ thuc:\ [0-9]+\ van,\ ([0-9]+)\ evals ]] && td_ghi van="${BASH_REMATCH[1]}" con=0
        [ "$o" = 08 ] && [[ "$dong" =~ ^\[arena\]\ ([0-9]+)/[0-9]+\ van,\ dang\ choi\ ([0-9]+) ]] &&
          td_ghi van="${BASH_REMATCH[1]}" con="${BASH_REMATCH[2]}"
      else
        rc=$?
        [ -n "$dong" ] && printf '%s' "$dong"
        [ $NGAT = 1 ] && { ly_do=ngat; break; }
        [ $rc -gt 128 ] || break                      # het du lieu: ssh da thoat
        # Im lang lau: ssh co the da treo (mang chet, proxy treo) -> bao, roi noi lai luong log (ô tren may van chay).
        if [ $((SECONDS - sil)) -ge 600 ]; then
          td_in "${M_VANG}10 phút không có dòng log mới${M_HET} -- nối lại luồng log (ô trên máy vẫn chạy)"
          ly_do=tre; break
        elif [ $((SECONDS - sil)) -ge 180 ] && [ $((SECONDS - nhac)) -ge 180 ]; then
          ly_do=soi; break
        fi
      fi
      if [ $((SECONDS - ctl)) -ge 1 ]; then ctl=$SECONDS; td_ctrl_d; fi     # Ctrl+D = nhu Ctrl+C
      [ $NGAT = 1 ] && { ly_do=ngat; break; }
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
      soi)
        # Colab chi cho MOT ssh moi may: luong log da bi ngat o tren, hoi nhanh may dang chay gi roi noi lai.
        them=3; nhac=$SECONDS
        td_in "${M_VANG}chưa có dòng log mới sau $((SECONDS - sil)) giây${M_HET} -- các tiến trình đang chạy trên máy (thời gian chạy · lệnh):"
        ssh_colab "ps -eo etime,args | grep -E 'wget|curl|pip |lay_mang|lc0 |sinh.py|tao_mau|gop_mau|huan_luyen|IPython' | grep -v grep | tail -4 | cut -c1-140" 2>&1 | sed 's/^/    /'
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
  td_dung_ca && return 0
  if [ "$TD_KIEU" = arena ]; then
    tong=$(td_ar_tong "$TD_G"); muc=$(td_ar_van)
    if [ "$tong" != "${TD_TONG_IN:-}" ] && [ $((SECONDS - ${TD_LUC_IN:-0})) -ge 60 ]; then
      td_in "arena đời $TD_G (tt vs cay): ${M_DAM}$tong/$muc${M_HET} ván (đã ghi $(td_ar_da "$TD_G"), tính cả ván đang chơi dở)"
      TD_TONG_IN=$tong; TD_LUC_IN=$SECONDS
    fi
    [ "$tong" -ge "$muc" ]; return
  fi
  tong=$(td_tong "$TD_G"); muc=$(td_muc "$TD_G")
  if [ "$tong" != "${TD_TONG_IN:-}" ] && [ $((SECONDS - ${TD_LUC_IN:-0})) -ge 60 ]; then
    td_in "$TD_BEN đời $TD_G: ${M_DAM}$tong/$muc${M_HET} lần chạy mạng (đã tải $(tong_tich_luy "$TD_G" "$TB"), tính cả ván đang chơi dở)"
    TD_TONG_IN=$tong; TD_LUC_IN=$SECONDS
  fi
  [ "$tong" -ge "$muc" ]
}
# Tao tep dung mem ma engine dang xem (doc tu dong lenh cua engine, nhu o 09b). 0 = da gui.
# Tao tep dung mem ma sinh.py dang xem (doc tu dong lenh, nhu o 09b). 0 = da gui.
td_gui_dung() {
  local i out
  for i in 1 2 3; do
    out=$(ssh_colab "p=\$(pgrep -af '[s]inh\.py |[a]rena\.py ' | sed -n 's/.* --tep-dung \([^ ]*\).*/\1/p' | head -1); if [ -n \"\$p\" ]; then touch \"\$p\" && echo FZ_DA_DUNG; else echo FZ_KHONG_CHAY; fi" 2>/dev/null)
    if grep -q FZ_DA_DUNG <<<"$out"; then
      td_in "${M_VANG}dừng mềm máy $(ten_tk "$TK")${M_HET}: $(td_dung_ca && echo "dừng tay" || { [ "$TD_KIEU" = arena ] && echo "đủ $(td_ar_van) ván arena" || echo "đủ $(td_muc "$TD_G") lần chạy mạng"; }) -- ván dở chơi nốt"
      return 0
    fi
    grep -q FZ_KHONG_CHAY <<<"$out" && return 0         # sinh.py vua xong
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
  # Thong bao tien trinh (stderr cua khoi_dong_ssh: "[máy mới] Chụp môi trường...", loi ssh) hien thang ra man hinh --
  # truoc day bi bat vao $out nen may moi mat vai phut im lang, khong phan biet duoc cham voi treo.
  td_in "nối ssh, khởi động ô $1 trên máy (máy mới còn chụp môi trường: có thể mất 1-3 phút)"
  out=$(khoi_dong_ssh "$1" "$2") || { td_con_may || return 3; return 1; }
  ban=$(sed -n 's/^FZ_BAN=//p' <<<"$out")
  if [ -n "$ban" ]; then
    # O khac dang chay nen tren may nay (vd nhan lai may giua chung): xem no xong roi chay o nay.
    read -r ban pid <<<"$(ssh_colab "cat $LOGD/dang_chay" 2>/dev/null)"
    td_in "ô $ban đang chạy trên máy -- xem tới khi xong"
    td_xem "$ban" "$pid" 20 || return $?
    out=$(khoi_dong_ssh "$1" "$2") || return 1
  fi
  pid=$(sed -n 's/^FZ_PID=//p' <<<"$out")
  [ -n "$pid" ] || { echo "$out" | tail -3; return 1; }
  td_in "ô $1 đã chạy nền trên máy (pid $pid) -- xem log"
  td_xem "$1" "$pid"
}

# May san sang cho doi $1 cua cach dang lam: goi chay (lc0, moi truong, py/lay_mang.py) + <cach>_gen$1.pb.gz
# (+ .pt va thu vien huan luyen neu $2 = pt).
td_kiem_may_cl() {
  ssh_colab "test -x $CV_CL/lc0 && test -s $CV_CL/moi_truong.sh && echo BIN_1 && echo BINA_\$(test -s $CV_CL/colab/arena.py && echo 1 || echo 0); test -s $CV_CL/py/lay_mang.py && echo CO_LM; test -s /content/${TD_BEN}_gen$1.pb.gz && echo CO_ONNX; test -s /content/${TD_BEN}_gen$1.pt && python3 -c 'import onnx, chess' 2>/dev/null && echo CO_PT" 2>/dev/null
}
# Chua thi chay 02. 0 = san sang, 1 = loi (thu lai), 2 = loi khong tu sua duoc, 3 = mat may, 4 = q.
td_chuan_bi() {
  local g=$1 can_pt=${2:-} out rc
  out=$(td_kiem_may_cl "$g")
  if ! grep -q '^BIN_1' <<<"$out" || ! grep -q CO_ONNX <<<"$out" || ! grep -q CO_LM <<<"$out"; then
    td_ghi buoc=chuan_bi
    td_in "chạy 02 (gói lc0 + mã từ Release co_vua, ${TD_BEN}_gen$g từ Release co_vua_mang)"
    td_chay 02 "$(ls "$D"/02_*.py 2>/dev/null | head -1)"; rc=$?
    [ $rc = 0 ] || return $rc
    out=$(td_kiem_may_cl "$g")
  fi
  if ! grep -q '^BIN_1' <<<"$out" || ! grep -q CO_LM <<<"$out"; then td_in "[!] 02 chưa dựng được gói chạy (lc0 / py) -- thử lại"; return 1; fi
  if ! grep -q CO_ONNX <<<"$out" && [ "$g" = 0 ]; then
    # Doi 0 chua co tren Release: tao (o 03, chung cho ca hai cach) hoac tai len tu dien thoai.
    td_gen0; rc=$?
    [ $rc = 0 ] || return $rc
    out=$(td_kiem_may_cl "$g")
  fi
  if ! grep -q CO_ONNX <<<"$out"; then
    # Thuong la loi tam thoi cua GitHub (vd HTTP 500) -- cua so khac van tai duoc. 5 phut sau chay lai
    # 02; 6 lan lien (30 phut) van khong co thi moi dung (va tra may, xem td_vong).
    TD_LOI_ONNX=$((${TD_LOI_ONNX:-0} + 1))
    if [ $TD_LOI_ONNX -ge 6 ]; then
      td_in "${M_DO}[!] $TD_LOI_ONNX lần liền không tải được ${TD_BEN}_gen$g.pb.gz từ Release${M_HET} -- dừng"
      TD_LOI_ONNX=0; return 2
    fi
    td_in "${M_VANG}[!] chưa tải được ${TD_BEN}_gen$g.pb.gz từ Release (lần $TD_LOI_ONNX/6)${M_HET} -- 5 phút nữa thử lại"
    ssh_colab "rm -f /content/${TD_BEN}_gen$g.pb.gz" 2>/dev/null
    td_ngu 300 || return 4
    return 1
  fi
  TD_LOI_ONNX=0
  if [ -n "$can_pt" ] && ! grep -q CO_PT <<<"$out"; then
    # Chi may huan luyen moi can .pt (o 02c) -- may chi sinh du lieu khong can.
    td_in "02c: tải ${TD_BEN}_gen$g.pt"
    td_chay 02c "$(ls "$D"/02c_*.py 2>/dev/null | head -1)"; rc=$?
    [ $rc = 0 ] || return $rc
    out=$(td_kiem_may_cl "$g")
    if ! grep -q CO_PT <<<"$out"; then
      TD_LOI_ONNX=$((${TD_LOI_ONNX:-0} + 1))       # cung bo dem: loi tai tam thoi nhu .pb.gz
      if [ $TD_LOI_ONNX -ge 6 ]; then
        td_in "${M_DO}[!] $TD_LOI_ONNX lần liền chưa có ${TD_BEN}_gen$g.pt / thư viện huấn luyện (Release thiếu?)${M_HET} -- dừng"
        TD_LOI_ONNX=0; return 2
      fi
      td_in "${M_VANG}[!] chưa tải được ${TD_BEN}_gen$g.pt (lần $TD_LOI_ONNX/6)${M_HET} -- 5 phút nữa thử lại"
      ssh_colab "rm -f /content/${TD_BEN}_gen$g.pt" 2>/dev/null
      td_ngu 300 || return 4
      return 1
    fi
    TD_LOI_ONNX=0
  fi
  return 0
}

# Mang doi 0 cho may nay (Release chua co): dien thoai co thi tai len; chua co thi o 03 tao (MOT mang chung cho ca hai
# cach -- so sanh cong bang), tai ve dien thoai roi dua len Release cho ca hai cach. Khoa tao_gen0: chi mot cua so tao.
# 0 = xong, 1 = thu lai sau, 2 = loi khong tu sua duoc, 3 = mat may, 4 = q.
td_gen0() {
  local b rc p ben_cu=$TD_BEN
  if td_co_mang 0; then
    td_in "Release chưa có ${TD_BEN}_gen0 -> tải lên máy từ điện thoại"
    tai_len "$TB/gen0.pb.gz" "/content/${TD_BEN}_gen0.pb.gz" && tai_len "$TB/gen0.pt" "/content/${TD_BEN}_gen0.pt" && return 0
    td_con_may || return 3; return 1
  fi
  p=$(cat "$TD/tao_gen0/pid" 2>/dev/null)
  [ -n "$p" ] && ! td_song "$p" && rm -rf "$TD/tao_gen0"
  if ! mkdir "$TD/tao_gen0" 2>/dev/null; then td_in "cửa sổ khác đang tạo mạng đời 0 -- chờ"; td_ngu 60 || return 4; return 1; fi
  echo $$ > "$TD/tao_gen0/pid"
  td_in "${M_DAM}tạo mạng đời 0${M_HET} (ô 03): một mạng chung cho cả hai cách"
  td_chay 03 "$(ls "$D"/03_*.py 2>/dev/null | head -1)"; rc=$?
  [ $rc = 0 ] && tai_theo_o 03
  if [ $rc = 0 ] && [ -s "$TAI/tt/gen0.pb.gz" ] && [ -s "$TAI/cay/gen0.pb.gz" ]; then
    for b in tt cay; do td_dat_ben "$b"; td_len_github 0 || { td_dat_ben "$ben_cu"; rm -rf "$TD/tao_gen0"; return 1; }; done
    td_dat_ben "$ben_cu"
  fi
  rm -rf "$TD/tao_gen0"
  [ $rc = 0 ] || return $rc
  td_co_mang 0 || { td_in "[!] chưa có mạng đời 0 trên điện thoại sau ô 03 -- thử lại"; return 1; }
  return 0
}

# Chuan bi may (02...) loi nhieu lan lien: TRA may thay vi giu may khong lam gi (vua tieu han muc tai khoan, vua
# khong ai thay -- cua so ghi "dang chay o" ma khong co log).
TD_CB_LOI=0
td_chuan_bi_loi() {
  TD_CB_LOI=$((TD_CB_LOI + 1))
  if [ $TD_CB_LOI -ge 10 ]; then
    td_in "${M_DO}[!] chuẩn bị máy lỗi $TD_CB_LOI lần liền -> trả máy, xin lại${M_HET}"
    TD_CB_LOI=0; td_tra; return
  fi
  td_ngu 30
}
# Giai doan 2 tren may cua cua so nay: 04 (tran theo han muc) -> 06 -> tai ve.
td_sinh() {
  local g=$1 rc secs muc tong so f o04 par duoi
  td_chuan_bi "$g"; rc=$?
  case $rc in 0) TD_CB_LOI=0 ;; 2) TD_LOI=1; return ;; 3) td_mat_may; return ;; 4) return ;; *) td_chuan_bi_loi; return ;; esac
  td_dung_ca && return
  secs=$(td_giay_t4)
  if [ -z "$secs" ]; then td_in "không đọc được hạn mức -- thử lại sau 1 phút"; td_ngu 60; return; fi
  o04=$(ls "$D"/04_*.py | head -1)
  par=$(song_song_o04 "$o04"); duoi=$(duoi_giay "$par")
  secs=$((secs - $(chua_phut) * 60 - duoi))
  if [ $secs -lt $((TD_PHUT_SINH * 60)) ]; then
    td_in "$(ten_tk "$TK"): hạn mức còn $(( (secs + duoi) / 60 + $(chua_phut) )) phút T4 -> trả máy"
    td_tra; return
  fi
  muc=$(td_muc "$g"); tong=$(td_tong "$g"); so=$((muc - tong))
  [ $so -ge 1 ] || return
  f=$TD/o_$$/$(basename "$o04")
  mkdir -p "$TD/o_$$"
  sed -E "0,/^SECS[[:space:]]*=[[:space:]]*[0-9]+/s//SECS = $secs/; 0,/^EVALS[[:space:]]*=[[:space:]]*[0-9]+/s//EVALS = $so/" \
    "$o04" > "$f"
  TD_G=$g; TD_TONG_IN=
  td_ghi gen="$g" buoc=sinh van=0 con=0 giao="$so" par="$par"
  td_in "04 trên $(ten_tk "$TK"): $TD_BEN đời $g, giao $so lần chạy mạng ($par ván song song), SECS=$secs (≈ $((secs / 60)) phút, đã trừ $(chua_phut) phút gom zip + tải về và $(( (duoi + 59) / 60 )) phút đuôi ván) · đời $g: $tong/$muc"
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
# KHAC fz: hai ben la HAI CACH HOC o cung mot doi k (cung luong tinh toan) -- tt_gen<k> (A) dau cay_gen<k> (B), khong
# phai doi moi dau doi cu. Day doi so sanh (mac dinh 10 20 ... 100, hoi luc bat dau): doi k nao trong day ma ca hai cach
# da co mang doi k thi moi cua so dau arena do truoc khi sinh du lieu (nhu fz). Ket qua: Download/CoVua/arena/
# tt_gen<k>_vs_cay_gen<k>.txt (moi may mot dong W= D= L= N=, W = tt thang); du van -> dong XONG kem ti le, Elo.
td_ar_van() { local n; n=$(cat "$TD_AR_VAN_F" 2>/dev/null); so_nguyen "$n" && echo $((10#$n)) || echo 1000; }
td_ar_day() { local x; x=$(cat "$TD_AR_DAY_F" 2>/dev/null); echo "${x:-10 20 30 40 50 60 70 80 90 100}"; }
td_ar_tep() { echo "$TD_AR_DIR/tt_gen$1_vs_cay_gen$1.txt"; }
# Doi k con viec arena: trong day, ca hai cach da co mang doi k tren dien thoai, chua XONG / BO_QUA, tong (ca van dang
# do) < so van. In doi nho nhat nhu vay; 1 = khong co.
td_ar_doi_thu() {
  local k
  for k in $(td_ar_day); do
    [ -s "$TAI/tt/gen$k.pb.gz" ] && [ -s "$TAI/cay/gen$k.pb.gz" ] || continue
    td_ar_xong "$k" && continue
    [ "$(td_ar_tong "$k")" -lt "$(td_ar_van)" ] && { echo "$k"; return 0; }
  done
  return 1
}
# Cong W/D/L/N cac dong ket qua (moi may mot dong) cua arena doi $1: in "W D L N".
td_ar_cong() {
  local f; f=$(td_ar_tep "$1")
  [ -f "$f" ] || { echo "0 0 0 0"; return; }
  awk '/^[0-9]/ { for (i = 1; i <= NF; i++) { split($i, k, "="); if (k[1] ~ /^[WDLN]$/) s[k[1]] += k[2] } }
       END { print s["W"] + 0, s["D"] + 0, s["L"] + 0, s["N"] + 0 }' "$f"
}
td_ar_da() { local w d l n; read -r w d l n <<<"$(td_ar_cong "$1")"; echo "$n"; }
td_ar_xong() { grep -q '^\(XONG\|BO_QUA\)' "$(td_ar_tep "$1")" 2>/dev/null; }
# Tong van arena doi $1 = da ghi + van da xong VA dang do tren may cac cua so dang arena doi do (nhu td_tong).
td_ar_tong() {
  local f t v co=1
  td_khoa && co=0
  t=$(td_ar_da "$1")
  for f in $(td_cac_cua_so); do
    [ "$(td_doc "$f" gen)" = "$1" ] && [ "$(td_doc "$f" buoc)" = arena ] || continue
    v=$(td_doc "$f" van); t=$((t + ${v:-0} + $(td_dang_do "$f")))
  done
  [ $co = 0 ] && rmdir "$TAI/.khoa_dat_ten" 2>/dev/null
  echo $t
}
# Con viec arena khong: 0 = co, TD_AR_G = doi do.
td_ar_viec() { TD_AR_G=$(td_ar_doi_thu) && [ -n "$TD_AR_G" ]; }
# Bo arena doi $1 (ly do $2): ghi BO_QUA de vong lap khong thu lai.
td_ar_bo() {
  mkdir -p "$TD_AR_DIR"
  echo "BO_QUA $(date '+%Y-%m-%d %H:%M') $2" >> "$(td_ar_tep "$1")"
  td_in "${M_DO}[!] bỏ arena tt_gen$1 vs cay_gen$1: $2${M_HET}"
}
# Du van -> dong XONG (ti le diem cua tt, khoang tin cay 95%, Elo) va in ket qua.
td_ar_ket() {
  local g=$1 w d l n kq
  td_ar_xong "$g" && return 0
  read -r w d l n <<<"$(td_ar_cong "$g")"
  [ "$n" -ge "$(td_ar_van)" ] || return 0
  kq=$(awk -v w="$w" -v d="$d" -v n="$n" 'BEGIN {
    p = (w + d / 2) / n; s = sqrt(p * (1 - p) / n)
    lo = p - 1.96 * s; hi = p + 1.96 * s
    e = (p > 0 && p < 1) ? sprintf("%+.0f Elo", -400 * log(1 / p - 1) / log(10)) : "Elo ?"
    printf "%.1f%% (95%%: %.0f-%.0f%%), %s", 100 * p, 100 * (lo < 0 ? 0 : lo), 100 * (hi > 1 ? 1 : hi), e }')
  echo "XONG $(date '+%Y-%m-%d %H:%M') W=$w D=$d L=$l N=$n -- tt_gen$g (so voi cay_gen$g): $kq" >> "$(td_ar_tep "$g")"
  td_in "${M_XANH}arena đời $g xong${M_HET}: truyền thống thắng $w / hoà $d / thua $l ($n ván) = ${M_DAM}$kq${M_HET} (dương = truyền thống mạnh hơn)"
  td_in "(Download/CoVua/arena/tt_gen${g}_vs_cay_gen$g.txt)"
}
# Ghi ket qua lan chay o 08 tren may nay (dong FZ_ARENA cua log) vao tep arena doi $1 -- mot lan moi lan chay
# (08.da_ghi tren may = dong dau log da ghi), chi khi log dung la arena tt_gen$1 vs cay_gen$1.
td_ar_ghi() {
  local g=$1 ds dau da kq co=1
  mapfile -t ds < <(ssh_colab "printf '%s\n' \"\$(head -1 $LOGD/08.log 2>/dev/null)\" \"\$(cat $LOGD/08.da_ghi 2>/dev/null)\" \"\$(grep -c 'A=/content/tt_gen$g.pb.gz  vs  B=/content/cay_gen$g.pb.gz' $LOGD/08.log 2>/dev/null)\" \"\$(grep '^FZ_ARENA ' $LOGD/08.log 2>/dev/null | tail -1)\"" 2>/dev/null)
  [ ${#ds[@]} -ge 4 ] || { td_in "[!] không đọc được log ô 08 -- ghi kết quả sau"; return 1; }
  dau=${ds[0]}; da=${ds[1]}; kq=${ds[3]}
  if [ -z "$dau" ] || [ "$da" = "$dau" ] || [ "${ds[2]:-0}" = 0 ]; then td_ghi van=0 con=0; return 0; fi
  ssh_colab "cat > $LOGD/08.da_ghi" <<<"$dau" || { td_in "[!] chưa ghi được dấu đã ghi -- thử lại sau"; return 1; }
  mkdir -p "$TD_AR_DIR"
  td_khoa && co=0
  if [[ "$kq" =~ ^FZ_ARENA\ W=([0-9]+)\ D=([0-9]+)\ L=([0-9]+)\ N=([0-9]+) ]]; then
    [ -f "$(td_ar_tep "$g")" ] ||
      echo "# arena doi $g: tt_gen$g (A) vs cay_gen$g (B), 400 luot tham; W/D/L = tt thang/hoa/thua, moi may mot dong" > "$(td_ar_tep "$g")"
    [ "${BASH_REMATCH[4]}" -gt 0 ] && echo "$(date '+%Y-%m-%d %H:%M') $(ten_tk "$TK") W=${BASH_REMATCH[1]} D=${BASH_REMATCH[2]} L=${BASH_REMATCH[3]} N=${BASH_REMATCH[4]}" >> "$(td_ar_tep "$g")"
    td_in "arena máy $(ten_tk "$TK"): truyền thống thắng ${BASH_REMATCH[1]} / hoà ${BASH_REMATCH[2]} / thua ${BASH_REMATCH[3]}"
  else
    td_in "${M_VANG}[!] log ô 08 không có dòng FZ_ARENA (ô lỗi / dừng ngang) -- các ván đó không tính${M_HET}"
  fi
  td_ghi van=0 con=0
  td_ar_ket "$g"                      # trong khoa: hai cua so xong cung luc khong ghi XONG hai lan
  [ $co = 0 ] && rmdir "$TAI/.khoa_dat_ten" 2>/dev/null
  return 0
}
# Mang cay_gen$1 len may (tt_gen$1 da co nho td_chuan_bi): Release co_vua_mang (doi cu: chuyen tu .pt tren may), hoac
# tu dien thoai. 0 = co, 1 = loi mang (thu lai), 2 = khong co o dau ca.
td_ar_mang() {
  local k=$1 url out rc
  url=$(td_rel_nn_url)
  out=$(ssh_colab "python3 $CV_CL/py/lay_mang.py pb /content/cay_gen$k.pb.gz --rel '$url'; echo FZ_RC=\$?" 2>&1)
  rc=$(sed -n 's/^FZ_RC=//p' <<<"$out" | tail -1)
  case "$rc" in
    0) return 0 ;;
    10) ;;
    *) tail -5 <<<"$out"; return 1 ;;
  esac
  if [ -s "$TAI/cay/gen$k.pb.gz" ]; then
    td_in "Release không có cay_gen$k -> tải từ điện thoại lên"
    tai_len "$TAI/cay/gen$k.pb.gz" "/content/cay_gen$k.pb.gz" && return 0
    return 1
  fi
  return 2
}
# Giai doan 0 tren may cua cua so nay: o 08 (so van con thieu, tran theo han muc) -> ghi ket qua.
td_arena() {
  local g=$1 rc secs par duoi so f o08 muc tong ben_cu=$TD_BEN
  td_dat_ben tt; td_o00                       # may can goi chay + tt_gen$g (td_chuan_bi), roi them cay_gen$g
  td_chuan_bi "$g"; rc=$?
  case $rc in 0) TD_CB_LOI=0 ;; 2) TD_LOI=1; return ;; 3) td_mat_may; return ;; 4) return ;; *) td_chuan_bi_loi; return ;; esac
  td_dung_ca && return
  if ! grep -q '^BINA_1' <<<"$(td_kiem_may_cl "$g")"; then
    td_in "${M_DO}[!] gói chạy trên Release co_vua chưa có colab/arena.py${M_HET} -- đưa gói mới lên (dong_goi.py --dang) rồi mở lại vòng lặp"
    TD_LOI=1; return
  fi
  td_ar_mang "$g"; rc=$?
  case $rc in
    0) ;;
    2) td_ar_bo "$g" "không có cay_gen$g trên Release co_vua_mang lẫn Download/CoVua/cay"; return ;;
    *) td_con_may || td_mat_may; return ;;
  esac
  o08=$(ls "$D"/08_*.py 2>/dev/null | head -1)
  if [ -z "$o08" ] || ! grep -q '^A_PB' "$o08"; then
    td_in "${M_DO}[!] ô 08 trên điện thoại là bản cũ${M_HET}: bash $CVD/cv_lay_ve.sh 08, rồi mở lại vòng lặp"
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
  muc=$(td_ar_van); tong=$(td_ar_tong "$g"); so=$((muc - tong))
  [ $so -ge 1 ] || return
  f=$TD/o_$$/$(basename "$o08")
  mkdir -p "$TD/o_$$"
  sed -E "0,/^SECS[[:space:]]*=[[:space:]]*[0-9]+/s//SECS = $secs/; 0,/^GAMES[[:space:]]*=[[:space:]]*[0-9]+/s//GAMES = $so/; s#^A_PB[[:space:]]*=.*#A_PB = \"/content/tt_gen$g.pb.gz\"#; s#^B_PB[[:space:]]*=.*#B_PB = \"/content/cay_gen$g.pb.gz\"#" \
    "$o08" > "$f"
  TD_G=$g; TD_KIEU=arena; TD_TONG_IN=
  td_ghi gen="$g" buoc=arena van=0 con=0 giao="$so" par="$par"
  td_in "08 arena ${M_DAM}tt_gen$g vs cay_gen$g${M_HET} trên $(ten_tk "$TK"): $so ván ($par song song, 400 lượt thăm), SECS=$secs · arena: $tong/$muc"
  td_chay 08 "$f"; rc=$?
  TD_KIEU=
  case $rc in 3) td_mat_may; td_dat_ben "$ben_cu"; return ;; 4) return ;; 1) td_ngu 30; return ;; esac
  td_ar_ghi "$g"
  tai_theo_o 08                               # ban ghi moi van arena + ket qua: minh chung
  td_ghi buoc=xong
  td_dat_ben "$ben_cu"
}

# May vua nhan lai (vong lap truoc bi dong giua chung): may dang lam gi thi lam tiep viec do.
td_tiep_tuc() {
  local g=$1 o pid tt rc
  read -r o pid <<<"$(ssh_colab "cat $LOGD/dang_chay 2>/dev/null" 2>/dev/null)"
  [ -n "$o" ] || return 0
  tt=$(ssh_colab "python3 $LOGD/fz_may.py trang_thai $o $pid" 2>/dev/null)
  # O tren may duoc ghep tu ban chep o 00 cua viec do: doc cach + doi tu chinh tep o (/content/fz_log/<o>.ipy).
  local bg
  bg=$(ssh_colab "sed -n 's/^BEN = \"\([a-z]*\)\".*/B=\1/p; s/^GEN_CURRENT = \([0-9]*\).*/G=\1/p' $LOGD/$o.ipy 2>/dev/null | head -2" 2>/dev/null)
  if [[ "$bg" =~ B=([a-z]+) ]]; then td_dat_ben "${BASH_REMATCH[1]}"; fi
  if [[ "$bg" =~ G=([0-9]+) ]]; then g=${BASH_REMATCH[1]}; fi
  td_o00
  td_in "máy đang có ô $o ($tt) -- cách $TD_BEN, đời $g"
  case "$o:$tt" in
    04:chay)
      # So van duoc giao + so van song song: doc tu dong lenh cua engine dang chay (tinh van dang do).
      local cfg giao par
      cfg=$(ssh_colab "pgrep -af '[s]inh\.py ' | head -1" 2>/dev/null)
      giao=$(sed -n 's/.* --giao \([0-9]*\).*/\1/p' <<<"$cfg"); par=$(sed -n 's/.* --song-song \([0-9]*\).*/\1/p' <<<"$cfg")
      TD_G=$g; TD_TONG_IN=; td_ghi gen="$g" buoc=sinh van=0 con=0 giao="$giao" par="$par"
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
      local ar g2 g3 cfg giao par
      ar=$(ssh_colab "grep -m1 '=== ARENA: A=' $LOGD/08.log" 2>/dev/null)
      [[ "$ar" =~ A=/content/tt_gen([0-9]+)\.pb\.gz\ +vs\ +B=/content/cay_gen([0-9]+)\.pb\.gz ]] || return 0
      g2=${BASH_REMATCH[1]}; g3=${BASH_REMATCH[2]}
      [ "$g2" = "$g3" ] || return 0                          # arena chay tay (khac doi), khong phai cua vong lap
      if [ "$tt" = chay ]; then
        cfg=$(ssh_colab "pgrep -af '[a]rena\.py ' | head -1" 2>/dev/null)
        giao=$(sed -n 's/.* --giao \([0-9]*\).*/\1/p' <<<"$cfg"); par=$(sed -n 's/.* --song-song \([0-9]*\).*/\1/p' <<<"$cfg")
        TD_G=$g2; TD_KIEU=arena; TD_TONG_IN=
        td_ghi gen="$g2" buoc=arena van=0 con=0 giao="$giao" par="$par"
        td_xem 08 "$pid" 50; rc=$?
        TD_KIEU=
        case $rc in 3) td_mat_may; return ;; 4) return ;; esac
      fi
      td_ar_ghi "$g2"; tai_theo_o 08; td_ghi buoc=xong ;;
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
  p=$(cat "$TD/hl_${TD_BEN}_$1/pid" 2>/dev/null)
  if [ -n "$p" ] && td_song "$p"; then echo "$p"; return; fi
  [ -d "$TD/hl_${TD_BEN}_$1" ] && [ -n "$p" ] && rm -rf "$TD/hl_${TD_BEN}_$1"
}
td_lay_hl() {
  [ "$(td_chu_hl "$1")" = $$ ] && return 0
  td_chu_hl "$1" >/dev/null
  mkdir "$TD/hl_${TD_BEN}_$1" 2>/dev/null || return 1
  echo $$ > "$TD/hl_${TD_BEN}_$1/pid"
}
# Cua so nao huan luyen: trong cac cua so doi $1 dang cho, may con nhieu han muc nhat (bang nhau: pid
# nho hon); khong ai giu may: pid nho nhat. In pid.
td_chon_hl() {
  local f p h b= bh=-1 bp=
  for f in $(td_cac_cua_so); do
    [ "$(td_doc "$f" gen)" = "$1" ] && [ "$(td_doc "$f" ben)" = "$TD_BEN" ] || continue
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
    [ "$(td_doc "$f" gen)" = "$1" ] && [ "$(td_doc "$f" ben)" = "$TD_BEN" ] || continue
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
      td_dung_ca && return 0
      [ $da_bao = 0 ] && { td_in "chờ cửa sổ khác huấn luyện xong đời $g..."; da_bao=1; }
    elif [ -z "$chu" ]; then
      # So van tut duoi muc tieu (may cua so khac mat giua chung) -> quay lai sinh tiep.
      if ! td_toi_luot_hl "$g" && [ "$(td_tong "$g")" -lt "$(td_muc "$g")" ]; then return 0; fi
      if td_toi_luot_hl "$g" && ! td_ai_ban "$g" && [ "$(td_chon_hl "$g")" = $$ ] && td_lay_hl "$g"; then
        td_huan_luyen "$g"; return
      fi
      [ $da_bao = 0 ] && { td_in "$TD_BEN đời $g đủ lượng tính toán -- chờ các máy khác tải về..."; da_bao=1; }
    fi
    td_ngu 10 || return
  done
}

# Mang doi $1 dang co san tren dien thoai (cu) -> doi ten sang ten trong ("gen4 (2).pb.gz"): mang vua huan luyen tai ve
# dung ten gen$1.*, giai doan 4 tai len dung tep do.
td_don_mang_cu() {
  local x
  for x in pb.gz pt; do
    [ -e "$TB/gen$1.$x" ] && mv "$TB/gen$1.$x" "$TB/$(ten_trong "gen$1.$x" "$TB")"
  done
}

# Giai doan 3-4 (cua so nay da giu khoa huan luyen doi $1).
td_huan_luyen() {
  local g=$1 n=$(($1 + 1)) lan=0 loi=0 h rc
  TD_VAI=huan_luyen; td_ghi gen="$g" buoc=huan_luyen van=0
  if ! td_co_mang "$n"; then
    if [ ! -f "$TB/games_gen$g.zip" ]; then
      td_in "gộp dữ liệu $TD_BEN đời $g ($TD_SO_DOI đời) ..."
      # Ctrl+C trong luc gop bi bo qua (gop do dang thi phai lam lai) -- bam lai sau khi gop xong.
      ( trap '' INT; python $CVD/cv_tu_dong.py gop "$TB" "$TD_BEN" "$g" "$TD_SO_DOI" | tee "$TD/.gop_$$" )
      grep -q '^FZ_GOP_XONG' "$TD/.gop_$$" || { td_in "${M_DO}[!] gộp lỗi${M_HET}"; rm -f "$TD/.gop_$$"; TD_LOI=1; return; }
      rm -f "$TD/.gop_$$"
      command -v termux-media-scan >/dev/null && termux-media-scan -r "$TB" >/dev/null 2>&1
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
      td_in "tải $TD_BEN games_gen$g.zip lên (máy còn $((h / 60)) phút T4)"
      if ! tai_len "$TB/games_gen$g.zip" "/content/${TD_BEN}_games_gen$g.zip"; then
        td_con_may || td_mat_may; lan=0; continue
      fi
      td_in "07: huấn luyện $TD_BEN đời $n"
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
  [ "$(td_gen)" = "$n" ] && td_don_dep "$n"     # mang vua len GitHub + goi van doi truoc: don dien thoai
  rm -rf "$TD/hl_${TD_BEN}_$g"
  TD_VAI=
}
# Giai doan 4: gen$1.pb.gz + .pt cua cach dang lam len GitHub Release co_vua_mang (REL_NN trong o 00) voi ten
# <cach>_gen$1.*, kiem sha256 tren Release, roi xoa .pb.gz cac doi truoc cua cach do. Loi mang -> thu lai.
td_len_github() {
  local n=$1 repo tag tsv so them x up=$TD/len_$$
  read -r repo tag <<<"$(td_rel_nn)"
  if [ -z "$tag" ]; then td_in "${M_DO}[!] không đọc được REL_NN trong 00_cau_hinh.py${M_HET}"; TD_LOI=1; return 1; fi
  if [ "$n" -gt "$TD_GEN_CUOI" ]; then
    td_in "${M_DO}[!] đời $n vượt giới hạn $TD_GEN_CUOI${M_HET}: Release chứa tối đa $TD_REL_TOI_DA tệp -- không tải lên"
    TD_LOI=1; return 1
  fi
  while :; do
    if ! command -v gh >/dev/null || ! gh auth status >/dev/null 2>&1; then
      td_in "${M_DO}[!] chưa có gh / chưa đăng nhập GitHub${M_HET} (pkg install gh; gh auth login) -- 5 phút nữa thử lại"
      td_ngu 300 || return 1; continue
    fi
    if ! tsv=$(td_tep_release "$repo" "$tag"); then
      td_in "không đọc được danh sách tệp của Release $tag (mạng? Release chưa tạo: gh release create $tag -R $repo) -- 2 phút nữa thử lại"
      td_ngu 120 || return 1; continue
    fi
    so=$(grep -c . <<<"$tsv"); them=0
    for x in pb.gz pt; do grep -q "^${TD_BEN}_gen$n\.$x"$'\t' <<<"$tsv" || them=$((them + 1)); done
    if [ $((so + them)) -gt "$TD_REL_TOI_DA" ]; then
      td_in "${M_DO}[!] Release $tag có $so tệp, thêm $them tệp sẽ vượt giới hạn $TD_REL_TOI_DA${M_HET} -- không tải lên"
      TD_LOI=1; return 1
    fi
    rm -rf "$up"; mkdir -p "$up"
    cp "$TB/gen$n.pb.gz" "$up/${TD_BEN}_gen$n.pb.gz" && cp "$TB/gen$n.pt" "$up/${TD_BEN}_gen$n.pt" ||
      { td_in "${M_DO}[!] thiếu $TB/gen$n.pb.gz / .pt${M_HET}"; rm -rf "$up"; TD_LOI=1; return 1; }
    td_in "tải ${TD_BEN}_gen$n.pb.gz + .pt lên GitHub ($tag, đang có $so/$TD_REL_TOI_DA tệp)"
    if ( trap '' INT; gh release upload "$tag" "$up/${TD_BEN}_gen$n.pb.gz" "$up/${TD_BEN}_gen$n.pt" --clobber -R "$repo" ) &&
       td_kiem_len "$repo" "$tag" "$n"; then
      rm -rf "$up"
      td_in "${M_XANH}đã lên Release $tag${M_HET} (sha256 trên GitHub khớp tệp trên điện thoại)"
      td_xoa_onnx_cu "$repo" "$tag" "$n"
      return 0
    fi
    rm -rf "$up"
    td_in "tải lên GitHub lỗi (mạng?) -- 2 phút nữa thử lại"
    td_ngu 120 || return 1
  done
}
# <cach>_gen$3.pb.gz + .pt tren Release $2 ($1 = chu/kho) co sha256 giong tep tren dien thoai. 0 = khop.
td_kiem_len() {
  local tsv x h s ten tsz dg
  tsv=$(td_tep_release "$1" "$2") || return 1
  for x in pb.gz pt; do
    h=$(sha256sum "$TB/gen$3.$x" 2>/dev/null | cut -d' ' -f1); s=$(stat -c %s "$TB/gen$3.$x" 2>/dev/null)
    [ -n "$h" ] && [ -n "$s" ] || return 1
    IFS=$'\t' read -r ten tsz dg < <(grep "^${TD_BEN}_gen$3\.$x"$'\t' <<<"$tsv" | head -1) || return 1
    [ "$tsz" = "$s" ] || return 1
    [ -z "$dg" ] || [ "$dg" = "sha256:$h" ] || return 1     # GitHub chua ghi sha256 -> chi so kich thuoc
  done
}
# Xoa <cach>_gen<k>.pb.gz (k < $3) cua cach dang lam tren Release: Release chi giu .pb.gz doi moi nhat (doi cu tao lai tu
# .pt khi can, xem py/lay_mang.py). Chi xoa khi <cach>_gen$3.pb.gz da len; loi xoa khong dung vong lap -- lan sau xoa tiep.
td_xoa_onnx_cu() {
  local repo=$1 tag=$2 n=$3 tsv k ten xoa=0 loi=0
  tsv=$(td_tep_release "$repo" "$tag") || { td_in "[!] chưa đọc được danh sách Release -- chưa xoá .pb.gz đời cũ (lần sau xoá tiếp)"; return 0; }
  grep -q "^${TD_BEN}_gen$n\.pb\.gz"$'\t' <<<"$tsv" || return 0
  while IFS=$'\t' read -r ten _; do
    [[ "$ten" =~ ^${TD_BEN}_gen([0-9]+)\.pb\.gz$ ]] || continue
    k=$((10#${BASH_REMATCH[1]}))
    [ "$k" -lt "$n" ] || continue
    if gh release delete-asset "$tag" "$ten" -y -R "$repo" >/dev/null 2>&1; then xoa=$((xoa + 1)); else loi=$((loi + 1)); fi
  done <<<"$tsv"
  [ $xoa -gt 0 ] && td_in "đã xoá $xoa tệp .pb.gz đời cũ của $TD_BEN trên Release (giữ ${TD_BEN}_gen$n.pb.gz)"
  [ $loi -gt 0 ] && td_in "${M_VANG}[!] chưa xoá được $loi tệp .pb.gz đời cũ trên Release -- lần sau xoá tiếp${M_HET}"
  return 0
}
# Dau vong lap: .pb.gz doi cu con sot tren Release (lan xoa truoc bi loi) thi xoa tiep. Chi khi <cach>_gen$1.pb.gz da o do.
td_xoa_onnx_thua() {
  local repo tag
  read -r repo tag <<<"$(td_rel_nn)"
  [ -n "$tag" ] && command -v gh >/dev/null && gh auth status >/dev/null 2>&1 || return 0
  td_xoa_onnx_cu "$repo" "$tag" "$1"
}
# Don dien thoai truoc khi sinh du lieu doi $1: goi van cac doi truoc, thu muc van ngoai cua so huan luyen, mang da
# len GitHub (sha256 khop) -- chi tiet o `fz_tu_dong.py don_dep`. Khong doc duoc Release -> bo qua phan mang.
# Don dien thoai truoc khi sinh du lieu doi $1 cua cach dang lam -- KHAC fz: giu MOI dau vet (thu muc van, mang), chi xoa
# goi da gop vao thu muc (trung lap) va tep gop do; chi tiet o `cv_tu_dong.py don_dep`.
td_don_dep() {
  local g=$1 out l mb n_goi n_tam
  out=$(python $CVD/cv_tu_dong.py don_dep "$TB" "$g" 2>&1) || { td_in "[!] dọn điện thoại lỗi: $(tail -1 <<<"$out")"; return 0; }
  n_goi=$(grep -c '^XOA goi ' <<<"$out"); n_tam=$(grep -c '^XOA tam ' <<<"$out")
  mb=$(sed -n 's/^FZ_DON_XONG [0-9]* //p' <<<"$out" | tail -1)
  if [ $((n_goi + n_tam)) -gt 0 ]; then
    td_in "dọn điện thoại ($TD_BEN, trước khi sinh đời $g): xoá $n_goi gói ván đã gộp vào thư mục, $n_tam tệp dở -- giải phóng ${mb:-0} MB (thư mục ván, mạng, log: giữ hết)"
    command -v termux-media-scan >/dev/null && termux-media-scan -r "$TB" >/dev/null 2>&1
  fi
  while IFS= read -r l; do td_in "${M_VANG}giữ ${l#GIU }${M_HET}"; done < <(grep '^GIU gói ' <<<"$out")
  return 0
}
td_len_doi() {
  [ "$(td_gen)" = "$1" ] && echo "$2" > "$TB/doi.txt.tam" && mv "$TB/doi.txt.tam" "$TB/doi.txt"
  if [ "$(td_gen)" = "$2" ]; then td_in "${M_XANH}xong $TD_BEN đời $1 -> đời $2${M_HET}"
  else td_in "${M_DO}[!] không ghi được đời $2 vào $TB/doi.txt${M_HET}"; TD_LOI=1; fi
}

# Chua xin duoc may: cho toi lich xin chung (thoi som khi den luot huan luyen / du van / dung / doi doi).
td_cx_thoi() {
  td_dung_ca || [ "$(td_gen)" != "$TD_CX_G" ] || td_toi_luot_hl "$TD_CX_G" ||
    [ "$(td_tong "$TD_CX_G")" -ge "$(td_muc "$TD_CX_G")" ]
}
td_cho_xin() { TD_CX_G=$1; td_cho_lich td_cx_thoi; }

# Hoi day doi so sanh + so van moi arena (Enter = giu), in tinh trang tung doi. 1 = go sai.
td_hoi_arena() {
  local x d t= ds=() n
  echo "${M_MO}Arena: các đời so sánh hai cách (cùng đời = cùng lượng tính toán)${M_HET}"
  read -rp "Dãy đời so sánh (Enter = $(td_ar_day); - = tắt): " x
  if [ "$x" = - ]; then echo "-1" > "$TD_AR_DAY_F"
  elif [ -n "$x" ]; then
    for d in ${x//,/ }; do
      [[ "$d" =~ ^[0-9]+$ ]] || { echo "[!] '$d' không phải số đời"; return 1; }
      d=$((10#$d))
      [ -n "$t" ] && [ "$d" -le "$t" ] && { echo "[!] Dãy phải tăng dần ($t rồi $d)"; return 1; }
      ds+=("$d"); t=$d
    done
    echo "${ds[*]}" > "$TD_AR_DAY_F"
  fi
  read -rp "Số ván mỗi arena (Enter = $(td_ar_van)): " x
  if [ -n "$x" ]; then
    so_nguyen "$x" || { echo "[!] Không phải số"; return 1; }
    echo $((10#$x)) > "$TD_AR_VAN_F"
  fi
  for d in $(td_ar_day); do
    [ "$d" -ge 0 ] 2>/dev/null || continue
    if grep -q '^XONG' "$(td_ar_tep "$d")" 2>/dev/null; then
      echo "  đời $d: ${M_XANH}xong${M_HET} -- $(grep '^XONG' "$(td_ar_tep "$d")" | tail -1 | sed 's/.* -- //')"
    elif grep -q '^BO_QUA' "$(td_ar_tep "$d")" 2>/dev/null; then echo "  đời $d: ${M_VANG}đã bỏ${M_HET}"
    else n=$(td_ar_da "$d"); [ "$n" -gt 0 ] && echo "  đời $d: $n/$(td_ar_van) ván"; fi
  done
  return 0
}

# Bat dau: doi (o 00), muc tieu, so phut chua, thu muc cac doi truoc, giai doan hien tai.
# Bat dau: doi cua tung cach, ngan sach, so phut chua, thu muc cac doi truoc, giai doan hien tai.
td_bat_dau() {
  local g x k thieu=() khac=() f n o04 b
  mkdir -p "$TD" "$TAI/tt" "$TAI/cay"
  clear
  echo "${M_DAM}== Vòng lặp tự động (cờ vua) ==${M_HET}"
  g=$(td_gen)
  if [ "$g" -ge "$TD_GEN_CUOI" ]; then
    echo "${M_DO}[!] Đời hiện tại $g >= $TD_GEN_CUOI.${M_HET} Release co_vua_mang chứa tối đa $TD_REL_TOI_DA tệp:"
    echo "    vòng lặp không chạy tiếp (cần Release mới)."
    return 1
  fi
  if [ -z "$(td_rel_nn)" ]; then
    echo "[!] 00_cau_hinh.py chưa có dòng REL_NN (Release co_vua_mang giữ mạng):"
    echo "    bash $CVD/cv_lay_ve.sh 00   (lấy lại ô 00)"
    return 1
  fi
  if [ -n "$(grep -L lay_mang "$D"/02_*.py "$D"/02c_*.py 2>/dev/null)" ]; then
    echo "[!] Ô 02 / 02c trên điện thoại là bản cũ: bash $CVD/cv_lay_ve.sh 02 02c"
    return 1
  fi
  o04=$(ls "$D"/04_*.py 2>/dev/null | head -1)
  if [ -z "$(ls "$D"/02c_*.py 2>/dev/null)" ] || [ -z "$(ls "$D"/03_*.py 2>/dev/null)" ]; then
    echo "[!] Thiếu ô 02c / 03: bash $CVD/cv_lay_ve.sh"
    return 1
  fi
  if [ -z "$o04" ] || ! grep -q DUNG_MEM "$o04" || ! grep -q '^EVALS' "$o04"; then
    echo "[!] Ô 04 trên điện thoại là bản cũ: bash $CVD/cv_lay_ve.sh 04"
    return 1
  fi
  for f in $CVD/cv_tu_dong.py $CVD/fz_han_muc.py $CVD/fz_nhan_may.py $CVD/fz_giu_may.py $CVD/fz_colab.py; do
    [ -f "$f" ] || { echo "[!] Thiếu $f -- chạy: bash $CVD/cv_lay_ve.sh"; return 1; }
  done
  for f in $(td_cac_cua_so); do [ "$f" = "$TD_W" ] || khac+=("${f##*/w_}"); done
  td_hai_ben
  echo "${M_MO}Vòng lặp làm các cách: $(td_cac_ben) (cách cây trò chơi bật khi đã viết xong)${M_HET}"
  read -rp "Cửa sổ này làm cách nào (Enter = tự chọn cách tụt lại; tt / cay = chỉ cách đó): " x
  case "$x" in
    "") TD_BEN_EP= ;;
    tt|cay) grep -qw "$x" <<<"$(td_cac_ben)" || { echo "[!] Vòng lặp chưa làm cách $x"; return 1; }; TD_BEN_EP=$x ;;
    *) echo "[!] Gõ tt, cay hoặc Enter"; return 1 ;;
  esac
  td_dat_ben "$(td_chon_ben)"; g=$(td_gen)
  [ ${#khac[@]} -gt 0 ] && echo "${M_VANG}Đang có ${#khac[@]} cửa sổ khác chạy vòng lặp${M_HET}"
  if ! command -v gh >/dev/null || ! gh auth status >/dev/null 2>&1; then
    echo "${M_VANG}[!] Chưa đăng nhập GitHub (gh):${M_HET}"
    echo "    giai đoạn 4 sẽ đứng chờ. Cài:"
    echo "    pkg install gh && gh auth login"
  fi
  read -rp "Ngân sách mỗi đời, số lần chạy mạng (Enter = $(ngan_sach)): " x
  if [ -n "$x" ]; then
    so_nguyen "$x" || { echo "[!] Không phải số"; return 1; }
    echo $((10#$x)) > "$NS_F"
  fi
  hoi_chua_phut || return 1
  td_hoi_arena || return 1
  for ((k = 1; k < TD_SO_DOI; k++)); do
    [ $((g - k)) -ge 0 ] && [ ! -d "$TB/games_gen$((g - k))" ] && thieu+=("$TD_BEN/games_gen$((g - k))/")
  done
  if [ ${#thieu[@]} -gt 0 ] && ! td_co_mang $((g + 1)) && [ ! -f "$TB/games_gen$g.zip" ]; then
    echo "${M_VANG}[!] Thiếu thư mục dữ liệu đời trước${M_HET}"
    echo "    trong Download/CoVua:"
    printf '      %s\n' "${thieu[@]}"
    echo "    Huấn luyện sẽ chỉ dùng các đời có."
    read -rp "Chạy tiếp? (co = chạy, Enter = thôi): " x
    [ "$x" = co ] || return 1
  fi
  echo "---"
  if td_co_mang $((g + 1)); then echo "$TD_BEN: đã có gen$((g + 1)).pb.gz + .pt -> chỉ còn"; echo "tải lên GitHub (giai đoạn 4)"
  elif [ -f "$TB/games_gen$g.zip" ]; then echo "$TD_BEN: đã có games_gen$g.zip -> huấn luyện"
  else
    n=$(tong_tich_luy "$g" "$TB")
    if [ "$n" -ge "$(td_muc "$g")" ]; then echo "$TD_BEN: đời $g đã đủ $n/$(td_muc "$g") lần chạy mạng -> gộp, huấn luyện"
    else echo "$TD_BEN: đời $g đã có $n/$(td_muc "$g") lần chạy mạng -> sinh tiếp"; fi
  fi
  read -rp "Enter = bắt đầu, n = thôi: " x || { echo; return 1; }      # Ctrl+D = thoi
  [ -z "$x" ] || return 1
  td_don_dep "$g"                 # don dien thoai (goi da gop) truoc khi sinh doi $g
  td_xoa_onnx_thua "$g"           # Release chi giu .pb.gz doi moi nhat: xoa phan con sot (lan xoa truoc bi loi)
  # Khong con cua so nao chay vong lap: lenh dung tay cu (lan truoc) het hieu luc.
  # (va lich xin may chung cua lan truoc: mo lai vong lap = xin ngay)
  [ ${#khac[@]} -eq 0 ] && rm -f "$TD_DUNG" "$TD_XIN_SAU"
  return 0
}

# Vong lap chay voi KHONG_HOI=1: moi lenh colab cua vong lap KHONG BAO GIO hoi ma dang nhap (loi nhac bi bat vao
# bien nen khong ai thay -> cua so "dung hinh"); Ctrl+C = td_int.
td_vong() {
  local rc
  KHONG_HOI=1; bat_ctrl_c
  td_vong_chinh "$@"; rc=$?
  KHONG_HOI=; bat_ctrl_c
  return $rc
}
td_vong_chinh() {
  local g b
  TD_THOAT=0; TD_LOI=0; TD_VAI=; TD_NHAN_LAI=0
  rm -f "$TD_DUNG_RIENG"
  # (fz cat nhat ky xuong 2000 dong khi qua 4000; cv giu nguyen toan bo -- xem TD_NK)
  trap 'rm -f "$CS/$$" "$TD_W" "$TD/.w_$$.tmp" "$TD/.luong_$$" "$TD_DUNG_RIENG"; rm -rf "$TD/o_$$"' EXIT
  td_bat_dau || return
  # Ctrl+C o mot cau hoi cua lan mo v TRUOC (bo do) da dat NGAT=1 -- khong de no bat menu ngat ngay khi bat dau.
  NGAT=0
  td_ranh
  td_ghi gen="$(td_gen)" buoc=xin van=0
  while [ $TD_THOAT = 0 ] && [ $TD_LOI = 0 ]; do
    # Ctrl+C luc dang lam viec khac (tai len / tai ve / ssh ngan): hoi ngay khi viec do dung.
    if [ $NGAT = 1 ]; then td_hoi_ngat; [ $TD_THOAT = 1 ] && break; fi
    # Cach cho viec nay (tut lai ma con viec); dang lo huan luyen thi giu cach do.
    [ "$TD_VAI" = huan_luyen ] || { b=$(td_chon_ben); [ "$b" = "$TD_BEN" ] || { td_dat_ben "$b"; td_in "việc kế tiếp: cách ${M_DAM}$b${M_HET}"; }; }
    g=$(td_gen)
    td_o00                         # ban chep o 00: BEN / GEN_CURRENT cua viec sap lam
    # Release GitHub chua toi da 1000 tep (.pt moi doi cua hai cach + 2 .pb.gz): ra doi TD_GEN_CUOI thi dung ca vong lap
    # (dung mem nhu `cv dung`: tra may, thoat moi cua so) -- khong sinh du lieu / huan luyen them.
    if [ "${g:-0}" -ge "$TD_GEN_CUOI" ] && [ ! -f "$TD_DUNG" ]; then
      td_in "${M_VANG}đã tới đời $g (giới hạn $TD_GEN_CUOI)${M_HET}: Release GitHub chứa tối đa $TD_REL_TOI_DA tệp -> dừng vòng lặp"
      : > "$TD_DUNG"
    fi
    if td_dung_ca && [ "$TD_VAI" != huan_luyen ]; then
      if [ -f "$TD_DUNG" ]; then td_in "dừng mềm: trả máy, thoát vòng lặp"
      else td_in "dừng mềm RIÊNG cửa sổ này: trả máy, thoát (cửa sổ khác vẫn chạy)"; fi
      td_tra
      # May cua vong lap ma cua so lo no da chet (vd Termux bi giet): nhan lai, dung mem, tai ve, tra.
      # Chi khi dung CA vong lap -- dung rieng cua so nay khong dong den may cua cua so khac.
      local ds=()
      while [ -f "$TD_DUNG" ]; do
        td_khoa_chon; td_ds_tk
        if ! td_nhan_lai; then td_mo_khoa_chon; break; fi
        td_mo_khoa_chon
        TD_NHAN_LAI=0; td_tiep_tuc "$g"
        [ $TD_THOAT = 1 ] && break 2
        td_tra
      done
      break
    fi
    # Giai doan 0: arena (doi nao trong day so sanh ma ca hai cach da co mang, chua xong) truoc khi sinh du lieu.
    if [ "$TD_VAI" != huan_luyen ] && td_ar_viec; then
      if [ $TD_CO_MAY = 0 ]; then
        td_ghi gen="$g" buoc=xin van=0
        td_xin_mot_vong || { td_cho_xin "$g"; continue; }
      fi
      if [ $TD_NHAN_LAI = 1 ]; then TD_NHAN_LAI=0; td_tiep_tuc "$g"; continue; fi
      td_arena "$TD_AR_G"; continue
    fi
    if td_toi_luot_hl "$g" || [ "$(td_tong "$g")" -ge "$(td_muc "$g")" ]; then td_giai_doan_3 "$g"; continue; fi
    if [ $TD_CO_MAY = 0 ]; then
      td_ghi gen="$g" buoc=xin van=0
      td_xin_mot_vong || { td_cho_xin "$g"; continue; }
    fi
    if [ $TD_NHAN_LAI = 1 ]; then TD_NHAN_LAI=0; td_tiep_tuc "$g"; continue; fi
    td_sinh "$g"
  done
  # Dung vi loi ma con giu may: may van tieu han muc, het han muc thi Colab thu hoi -> mat van chua tai.
  # Con van chua tai (thu muc van cua doi) -> gom + tai ve truoc; roi tra may. Tai ve loi -> giu may
  # (lay tay: cv -> d) thay vi tra ma mat van.
  if [ $TD_LOI = 1 ] && [ $TD_CO_MAY = 1 ]; then
    local gv nv
    gv=$(td_doc "$TD_W" gen); gv=${gv:-$(td_gen)}
    nv=$(ssh_colab "ls /content/${TD_BEN}_games_gen$gv/*/van.bin.gz 2>/dev/null | wc -l" 2>/dev/null)
    if [[ "$nv" =~ ^[0-9]+$ ]] && [ "$nv" -gt 0 ]; then
      td_in "máy còn $nv lần sinh $TD_BEN đời $gv chưa tải về -- gom, tải về trước khi trả máy"
      if td_gom_tai "$gv"; then td_tra
      else td_in "${M_DO}[!] chưa tải được ván về -- GIỮ máy (lấy tay: cv -> d, rồi t để trả)${M_HET}"; fi
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
