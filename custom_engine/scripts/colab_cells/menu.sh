#!/data/data/com.termux/files/usr/bin/bash
# menu.sh -- menu FairyZero tren Termux: chon o lenh bang so, chay tren may Colab.
# Mo bang lenh `fz` (lay_ve.sh them vao ~/.bashrc). O lenh: Download/FairyZero/o_lenh.
# `bash menu.sh 04 05` (lenh `o 04 05`): chay thang cac o do theo cung cach, khong hien menu.
# `fz @B` / `o @B 04`: dung tai khoan Colab B. Nhieu tai khoan CUNG LUC = moi cua so Termux mot
# tai khoan (xem tai_khoan() -- muc a).
# `fz :may2` / `fz @B :may2` / `o :may2 04`: dung may ten may2 (mac dinh fz). Nhieu MAY cung luc (ca
# cung tai khoan) = moi cua so mot ten may (xem chon_may() -- muc p).
#
# Cach chay mot o -- MOI o (ke ca o ban them sau nay) chay QUA SSH, khong dung kernel Jupyter
# cua may Colab (kernel chet / khoi dong lai khong anh huong; colab exec vao kernel cu con lam
# Colab CLI xoa phien + tat keep-alive, xem fz_nhan_may.py):
#   - O co dong "# fz: nhanh" (01, 05, 09): IPython chay ngay tren may, ket qua hien ngay.
#   - O con lai: chay nen tren may (IPython rieng, log /content/fz_log/<o>.log), menu xem log truc
#     tiep (fz_may.py theo_doi). Ctrl+C chi dong phan xem, o van chay tiep.
#   - Moi may, lan dau: colab exec MOT lan de chup moi truong kernel (env.json) -- ssh co moi
#     truong khac (thieu duong dan toi driver GPU...). ssh hong thi quay ve colab exec.
D=$HOME/storage/downloads/FairyZero/o_lenh
TAI=$HOME/storage/downloads/FairyZero
S=${S:-fz}
LOGD=/content/fz_log

# Tai khoan Colab. Colab CLI lay moi thu (token.json, sessions.json, ~/.ssh) tu ~ = $HOME, nen
# moi tai khoan phu co mot HOME rieng cho CLI: ~/.fz_tk/<ten>/ (.config/colab-cli rieng, .ssh
# tro ve ~/.ssh). Tai khoan chinh (TK rong) = ~ nhu cu. Chi lenh colab (va python dung
# colab_cli) chay voi HOME do -- con lai cua menu van dung ~ that.
TKG=$HOME/.fz_tk
dat_tk() {
  TK=$1
  if [ -z "$TK" ]; then TKH=$HOME; return; fi
  TKH=$TKG/$TK
  mkdir -p "$TKH/.config/colab-cli"
  [ -e "$TKH/.ssh" ] || ln -s "$HOME/.ssh" "$TKH/.ssh"
  [ -e "$HOME/.colab-cli-oauth-config.json" ] && [ ! -e "$TKH/.colab-cli-oauth-config.json" ] &&
    ln -s "$HOME/.colab-cli-oauth-config.json" "$TKH/.colab-cli-oauth-config.json"
  return 0
}
# Ten tai khoan = ten thu muc ~/.fz_tk/<ten> (doi ten = doi ten thu muc). Tai khoan chinh
# khong co thu muc: ten cua no nam trong ~/.fz_tk/.ten_chinh (mac dinh "chinh").
ten_chinh() { local t; t=$(cat "$TKG/.ten_chinh" 2>/dev/null); echo "${t:-chinh}"; }
ten_tk() { if [ -n "$1" ]; then echo "$1"; else ten_chinh; fi; }
# Ten dung cho tai khoan moi / doi ten: chu, so, _ -, khong trung tai khoan nao.
tk_hop_le() { [[ "$1" =~ ^[A-Za-z0-9_-]{1,20}$ ]]; }
tk_trung() { [ "$1" = chinh ] || [ "$1" = "$(ten_chinh)" ] || [ -e "$TKG/$1" ]; }
# `fz @<ten>`: ten -> TK ("" = tai khoan chinh). In ra TK, sai thi tra 1.
tim_tk() {
  if [ "$1" = chinh ] || [ "$1" = "$(ten_chinh)" ]; then echo ""; return; fi
  tk_hop_le "$1" && [ -d "$TKG/$1" ] && echo "$1"
}

# Cua so nao dung may nao: moi menu dang mo ghi ~/.fz_tk/.cua_so/<pid> = "@<TK>:<ten may>".
# Hai cua so cung tai khoan VA cung ten may = dung chung mot may -> canh bao truoc khi chon.
CS=$TKG/.cua_so
ghi_cua_so() { mkdir -p "$CS" && echo "@$TK:$S" > "$CS/$$"; }
trap 'rm -f "$CS/$$"' EXIT
# In pid cac cua so KHAC dang dung tai khoan $1 -- ten may $2 (bo trong = may bat ky cua tai
# khoan do). Don tep cua cua so da dong.
cua_so_khac() {
  local f pid g
  for f in "$CS"/*; do
    [ -f "$f" ] || continue
    pid=${f##*/}
    [ "$pid" = $$ ] && continue
    if ! tr '\0' ' ' 2>/dev/null < "/proc/$pid/cmdline" | grep -q 'menu\.sh'; then
      rm -f "$f"; continue          # cua so da dong (pid co the da cap cho tien trinh khac)
    fi
    g=$(cat "$f" 2>/dev/null)
    if [ -n "${2:-}" ]; then [ "$g" = "@$1:$2" ] && echo "$pid"
    else [ "${g%%:*}" = "@$1" ] && echo "$pid"; fi
  done
}
# Hoi truoc khi dung may $2 cua tai khoan $1 neu cua so khac dang dung dung may do. 0 = dung duoc.
hoi_trung() {
  local x
  [ -z "$(cua_so_khac "$1" "$2")" ] && return 0
  echo "[!] Máy '$2' của tài khoản $(ten_tk "$1") đang mở ở cửa sổ Termux khác -- hai cửa sổ sẽ dùng"
  echo "    CHUNG một máy (ô chạy nền cửa sổ này có thể chồng lên cửa sổ kia). Máy khác: đặt tên khác (p)."
  read -rp "    Vẫn dùng? Gõ 'co' (Enter = không): " x
  [ "$x" = co ]
}
# Cua so nay chuyen sang tai khoan $1 (giu ten may; co hoi neu trung). 0 = da chuyen.
chon_tk() { hoi_trung "$1" "$S" || return 1; dat_tk "$1"; ghi_cua_so; }

TK=
ten_may_hop_le() { [[ "$1" =~ ^[A-Za-z0-9_-]{1,20}$ ]]; }
while [[ "${1:-}" == @* || "${1:-}" == :* ]]; do
  if [[ "$1" == @* ]]; then
    TK=$(tim_tk "${1#@}") || { echo "[!] Không có tài khoản '${1#@}' -- xem/thêm: fz -> a"; exit 1; }
  else
    ten_may_hop_le "${1#:}" || { echo "[!] Tên máy chỉ gồm chữ, số, _ và - (vd: fz :may2)"; exit 1; }
    S=${1#:}
  fi
  shift
done
LE=                                   # `fz_menu.sh [@tk] --tai-len <tep>`: moc chia se tep
[ "${1:-}" = --tai-len ] && LE=1
[ -n "$LE" ] || hoi_trung "$TK" "$S" || exit 1
dat_tk "$TK"
[ -n "$LE" ] || ghi_cua_so
colab() { HOME=$TKH command colab "$@"; }
py_colab() { HOME=$TKH python "$@"; }

# Ctrl+C: dung lenh dang chay (ssh xem log), KHONG thoat menu. Handler (khong phai bo qua)
# de tien trinh con van nhan Ctrl+C binh thuong. NGAT=1: nguoi dung vua bam Ctrl+C (ssh tra 255
# ca khi bi Ctrl+C lan khi rot mang -- xem() dua vao co nay de phan biet).
NGAT=0
trap 'NGAT=1' INT

# Doc tep o: bo BOM va \r ma trinh sua tep tren dien thoai co the them vao.
doc() { sed 's/^\xEF\xBB\xBF//; s/\r$//' "$@"; }

# Mot o = o cau hinh 00 + o do (de moi o biet GEN_CURRENT va duong dan).
ghep() { doc "$D/00_cau_hinh.py" "$1"; }

tieu_de() { doc "$1" | sed -n '1s/^# *//p'; }

dung() { echo; read -rp "--- Enter để về menu ---" _; }

# ssh toi may Colab cua phien $S (khong can ~/.ssh/config).
ssh_colab() {
  ssh -o ProxyCommand="env HOME=$TKH $(type -P colab) ssh --proxy-mode -s $S" \
      -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR \
      -o ServerAliveInterval=15 -o ServerAliveCountMax=4 \
      "root@colab-$S" "$@"
}

# Phan chay tren may Colab (khoi dong o, trang thai, theo doi log): ~/fz_may.py, gui len
# /content/fz_log/fz_may.py moi lan khoi dong o. Doc tep do de biet chinh xac no lam gi.
MAY=$HOME/fz_may.py

# Khoi dong o $1 (so o) tu tep $2 chay nen tren Colab. In "FZ_PID=<pid>", hoac "FZ_BAN=<o>" neu
# dang co o khac chay nen (khi do khong khoi dong, tru khi $3 = ep).
khoi_dong() {
  local b m
  [ -f "$MAY" ] || { echo "[!] Thiếu $MAY -- cập nhật: bash ~/lay_ve.sh (lay_ve.sh cũ thì tải lại nó trước, xem HUONG_DAN_TERMUX.md mục 5)"; return 1; }
  b=$(ghep "$2" | base64 -w0)
  m=$(base64 -w0 "$MAY")
  colab exec -s "$S" <<EOF
import base64, os
os.makedirs("$LOGD", exist_ok=True)
open("$LOGD/fz_may.py", "w").write(base64.b64decode("$m").decode())
g = {"__name__": "fz_may"}
exec(open("$LOGD/fz_may.py").read(), g)
g["khoi_dong"]("$1", "$b", ep=("${3:-}" == "ep"))
EOF
}

# Gui ~/fz_may.py (dong 1 cua stdin, base64) + ma o $3 (dong 2) roi chay "fz_may.py $1 $2 [$4]"
# tren may qua ssh. $1 = khoi_dong (o chay nen, in FZ_PID=/FZ_BAN=) | chay_nhanh (o nhanh, in thang).
# Ma thoat 97 = may chua co env.json (FZ_THIEU_ENV), 255 = ssh loi.
ssh_fz() {
  { base64 -w0 "$MAY"; echo; ghep "$3" | base64 -w0; echo; } |
    ssh_colab "mkdir -p $LOGD && read -r m && echo \"\$m\" | base64 -d > $LOGD/fz_may.py && python3 $LOGD/fz_may.py $1 $2 ${4:-}"
}

# Chup moi truong cua kernel Colab vao $LOGD/env.json (mot lan moi may) -- duy nhat cho con dung
# colab exec. Phien bi CLI xoa (kernel cu 404) -> nhan lai may roi thu lai.
luu_env() {
  local ma out
  ma="import json, os
os.makedirs('$LOGD', exist_ok=True)
json.dump(dict(os.environ), open('$LOGD/env.json.tmp', 'w'))
os.replace('$LOGD/env.json.tmp', '$LOGD/env.json')
print('FZ_ENV_OK')"
  echo "[máy mới] Chụp môi trường kernel Colab (một lần mỗi máy)..."
  out=$(colab exec -s "$S" <<<"$ma" 2>&1)
  grep -q FZ_ENV_OK <<<"$out" && return 0
  cuu_phien && out=$(colab exec -s "$S" <<<"$ma" 2>&1)
  grep -q FZ_ENV_OK <<<"$out" && return 0
  echo "$out" | tail -3
  echo "[!] Không chụp được môi trường kernel (colab exec lỗi)"
  return 1
}

# Khoi dong o $1 (tep $2, $3 = ep) chay nen qua ssh. In FZ_PID=/FZ_BAN=; 1 = ssh khong dung duoc.
khoi_dong_ssh() {
  local out rc
  out=$(ssh_fz khoi_dong "$1" "$2" "${3:-}" 2>&1); rc=$?
  if [ $rc = 97 ]; then
    luu_env >&2 || return 1
    out=$(ssh_fz khoi_dong "$1" "$2" "${3:-}" 2>&1)
  fi
  grep -q '^FZ_\(PID\|BAN\)=' <<<"$out" || { echo "$out" | tail -2 >&2; return 1; }
  echo "$out"
}

# Xem log o $1 (pid $2) tu dau va theo tiep den khi o ket thuc (fz_may.py theo_doi).
# Tra ve 0 = o da ket thuc, khac 0 = Ctrl+C (o van chay tiep).
# Rot mang: ssh tra 255 (khac Ctrl+C = 130, o xong = 0) -> tu noi lai moi 5 giay, in tiep 20
# dong cuoi roi theo doi tiep; o tren Colab khong bi anh huong. Chuoi "04 06" vi vay khong bi dut.
# Colab chi cho MOT phien ssh moi may: ket noi cu chet ma phia Colab chua biet -> tu choi ket noi
# moi (HTTP 429) toi khi no tu don -> cho gian dan 5, 10, ... 30 giay; bo sau 10 phut KE TU LUC
# BAT DAU mat ket noi. "Da noi duoc" = nhan duoc it nhat mot byte log (khong dua vao thoi gian:
# mang co wifi ma khong ra internet thi mot lan noi THAT BAI cung co the keo dai > 1 phut).
co_du_lieu() {  # chep stdin -> stdout, byte dau tien thi tao tep $1
  local c
  IFS= read -r -N 1 c || return 0
  : > "$1"; printf '%s' "$c"; exec cat
}
xem() {
  local rc lan=0 them="" cho bd ok
  ok=$(mktemp)
  echo "== Log trực tiếp ô $1 · Ctrl+C để về menu (ô vẫn chạy tiếp) =="
  while true; do
    NGAT=0; rm -f "$ok"
    ssh_colab "python3 $LOGD/fz_may.py theo_doi $1 $2 $them" | co_du_lieu "$ok"
    rc=${PIPESTATUS[0]}
    [ $NGAT = 1 ] && { rm -f "$ok"; return 130; }
    [ $rc = 255 ] || { rm -f "$ok"; return $rc; }
    [ -f "$ok" ] && lan=0                          # vua xem duoc roi moi dut -> dem lai
    [ $lan = 0 ] && bd=$SECONDS
    lan=$((lan + 1))
    if [ $((SECONDS - bd)) -gt 600 ]; then rm -f "$ok"; echo "[!] Mất kết nối hơn 10 phút -- về menu (ô vẫn chạy; xem lại: l)"; return $rc; fi
    cho=$((lan * 5)); [ $cho -gt 30 ] && cho=30
    echo
    echo "[mất kết nối tới máy Colab -- nối lại sau $cho giây (lần $lan) · ô trên Colab VẪN CHẠY, chỉ phần xem bị gián đoạn · Ctrl+C = về menu]"
    sleep $cho || { rm -f "$ok"; return 130; }
    [ $NGAT = 1 ] && { rm -f "$ok"; return 130; }
    # Ban fz_may.py tren may co the cu (khong biet doi so thu 3): gui ban moi truoc. O dang chay
    # khong dung tep nay nen ghi de an toan.
    [ -f "$MAY" ] && ssh_colab "mkdir -p $LOGD && cat > $LOGD/fz_may.py" < "$MAY" 2>/dev/null
    them=20
  done
}

# Chay o tep $1: nhanh thi chay thang; con lai thi chay nen + xem log.
# Tra ve 0 = o ket thuc; 1 = Ctrl+C khi dang xem (o VAN chay nen); 2 = khong khoi dong / huy.
# Gia tri "TEN = ..." dang ghi trong tep o $1.
gia_tri() { doc "$1" | sed -n "s/^$2[[:space:]]*=[[:space:]]*\([^ #]*\).*/\1/p" | head -1; }
so_nguyen() { [[ "$1" =~ ^[0-9]+$ ]] && [ "$((10#$1))" -gt 0 ]; }
# Ghi "TEN = so" vao dong "TEN = <so>" DAU TIEN cua tep $1 (giu chu thich va \r cuoi dong neu co):
# lan sau mo fz van la so nay. 0 = ghi duoc.
ghi_bien() {
  sed -i -E "0,/^$2[[:space:]]*=[[:space:]]*[0-9]+/s//$2 = $3/" "$1" 2>/dev/null
  [ "$(gia_tri "$1" "$2")" = "$3" ] && return 0
  local o=${1##*/}; o=${o%%_*}
  echo "[!] Không ghi được $2 = $3 vào ${1##*/} -- tệp thiếu dòng '$2 = <số>' (ô bản cũ? cập nhật: bash ~/lay_ve.sh $o)" >&2
  return 1
}

# Hoi tham so cua o $1 (tep) TRUOC khi chay chuoi va GHI NGAY vao tep o (lan sau mo fz van giu).
# Dong trong o:
#   # fz: che_do_sinh          -> 3 che do SECS / GAMES (o 04)
#   # fz: hoi TEN cau hoi      -> hoi mot so nguyen cho bien TEN (vd GAMES o 08)
# In "SECS=@T4" neu chon "het han muc T4 - 15 phut": so giay tinh LUC o bat dau chay (chay_o),
# khong phai luc hoi, roi moi ghi vao tep.
hoi_tham_so() {
  local f=$1 id x g sc ra=() dong ten cau cu kv
  id=$(basename "$f"); id=${id%%_*}
  if doc "$f" | grep -q '^# fz: che_do_sinh'; then
    g=$(gia_tri "$f" GAMES); sc=$(gia_tri "$f" SECS)
    {
      echo
      echo "== Ô $id: $(tieu_de "$f") -- chọn chế độ (trong tệp: GAMES=${g:-?}, SECS=${sc:-?}) =="
      echo " 1  Tối đa theo hạn mức T4: GAMES=1000, SECS = lúc hết hạn mức T4 - 15 phút"
      echo " 2  Tự chọn số ván, SECS=10000"
      echo " 3  Tự đặt cả số ván và SECS"
      echo " Enter = dùng số trong tệp"
    } >&2
    read -rp "Chọn: " x
    case "$x" in
      1) ra+=(GAMES=1000 SECS=@T4) ;;
      2) read -rp "Số ván (GAMES): " g; so_nguyen "$g" || { echo "[!] Không phải số" >&2; return 1; }
         ra+=(GAMES=$((10#$g)) SECS=10000) ;;
      3) read -rp "Số ván (GAMES): " g; so_nguyen "$g" || { echo "[!] Không phải số" >&2; return 1; }
         read -rp "Giây (SECS): " sc; so_nguyen "$sc" || { echo "[!] Không phải số" >&2; return 1; }
         ra+=(GAMES=$((10#$g)) SECS=$((10#$sc))) ;;
      "") ;;
      *) echo "[!] Chọn 1, 2, 3 hoặc Enter" >&2; return 1 ;;
    esac
  fi
  # fd 3: read ben trong doc tu ban phim (stdin), khong tu danh sach cau hoi.
  while IFS= read -r dong <&3; do
    ten=${dong%% *}; cau=${dong#* }
    cu=$(gia_tri "$f" "$ten")
    read -rp "Ô $id -- $cau (Enter = $cu): " x
    [ -z "$x" ] && continue
    so_nguyen "$x" || { echo "[!] Không phải số" >&2; return 1; }
    ra+=("$ten=$((10#$x))")
  done 3< <(doc "$f" | sed -n 's/^# fz: hoi \([A-Z_][A-Z0-9_]*\) \(.*\)$/\1 \2/p')
  for kv in "${ra[@]}"; do
    [ "$kv" = SECS=@T4 ] && { echo SECS=@T4; continue; }
    ghi_bien "$f" "${kv%%=*}" "${kv#*=}" || return 1
    echo "[đã lưu] ô $id: ${kv%%=*} = ${kv#*=}" >&2
  done
}

# SECS=@T4 -> so giay: thoi gian T4 con chay duoc (h) - 15 phut. Loi -> tra 1.
giay_t4() {
  local may g
  may=$(colab status -s "$S" 2>/dev/null | sed -n 's/.*Hardware: *\([^ |]*\).*/\1/p' | head -1)
  g=$(py_colab ~/fz_han_muc.py --may "$may" --giay-t4 2>/dev/null) || return 1
  [[ "$g" =~ ^[0-9]+$ ]] || return 1
  g=$((g - 15 * 60))
  [ $g -gt 0 ] || { echo "[!] Hạn mức T4 còn dưới 15 phút" >&2; return 1; }
  echo $g
}

# Muc g: doi GEN_CURRENT trong 00_cau_hinh.py (ghi thang vao tep -- moi o sau doc dung so do).
doi_doi() {
  local f=$D/00_cau_hinh.py gen x moi
  gen=$(gia_tri "$f" GEN_CURRENT)
  [[ "$gen" =~ ^[0-9]+$ ]] || { echo "[!] Không thấy dòng 'GEN_CURRENT = <số>' trong 00_cau_hinh.py"; return; }
  echo "== Đời mạng hiện tại: GEN_CURRENT = $gen (00_cau_hinh.py) =="
  echo " +      = tăng lên $((gen + 1))"
  echo " -      = giảm xuống $((gen - 1))"
  echo " <số>   = đặt đúng số đó"
  echo " Enter  = giữ nguyên"
  read -rp "Chọn: " x
  case "$x" in
    "") return ;;
    +) moi=$((gen + 1)) ;;
    -) moi=$((gen - 1)) ;;
    *) [[ "$x" =~ ^[0-9]+$ ]] || { echo "[!] Gõ +, - hoặc một số"; return; }; moi=$((10#$x)) ;;
  esac
  [ $moi -ge 0 ] || { echo "[!] Đời không âm"; return; }
  # Chi thay so (giu chu thich, \r cuoi dong neu tep sua tren dien thoai co).
  sed -i -E "0,/^GEN_CURRENT[[:space:]]*=[[:space:]]*[0-9]+/s//GEN_CURRENT = $moi/" "$f"
  gen=$(gia_tri "$f" GEN_CURRENT)
  if [ "$gen" = "$moi" ]; then
    echo "[xong] GEN_CURRENT = $moi -> ô chạy sau dùng gen$moi.onnx / gen$moi.pt, sinh vào games_gen$moi, huấn luyện ra gen$((moi + 1))"
  else
    echo "[!] Ghi không được (đang là '$gen') -- sửa tay 00_cau_hinh.py"
  fi
}

# Giu may cua phien $S (~/fz_nhan_may.py, xem dau tep do): Colab CLI XOA phien va TAT keep-alive
# khi colab exec gap loi 404/401 -- ca khi may van song (vd kernel cu chet). kiem_may: phien con
# thi bat lai keep-alive neu no chet + ghi endpoint; cuu_phien: phien vua bi xoa ma may con -> nhan
# lai. 0 = phien dung duoc.
kiem_may() { [ -f ~/fz_nhan_may.py ] && py_colab ~/fz_nhan_may.py kiem "$S"; }
cuu_phien() { [ -f ~/fz_nhan_may.py ] && py_colab ~/fz_nhan_may.py cuu "$S"; }

chay_o() {
  local f=$1 id out pid ban x lan qua g
  if [ "${2:-}" = SECS=@T4 ]; then
    echo "[hạn mức] Tính SECS theo hạn mức T4 còn lại..."
    g=$(giay_t4) || { echo "[!] Không tính được thời gian T4 còn lại -- không chạy ô"; return 2; }
    ghi_bien "$f" SECS "$g" || return 2
    echo "[hạn mức] SECS = $g (≈ $((g / 60)) phút, đã trừ 15 phút cho gom zip + tải về) -- đã lưu vào ô"
  fi
  id=$(basename "$f"); id=${id%%_*}
  echo
  echo "====== Ô $id: $(tieu_de "$f") ======"
  if doc "$f" | grep -q '^# fz: nhanh'; then
    ssh_fz chay_nhanh "$id" "$f"; x=$?
    if [ $x = 97 ]; then luu_env && { ssh_fz chay_nhanh "$id" "$f"; x=$?; }; fi
    [ $x = 255 ] || return 0
    [ $NGAT = 1 ] && return 0
    echo "[ssh lỗi -- chạy ô $id qua colab exec]"
    if ! ghep "$f" | colab exec -s "$S"; then
      if cuu_phien; then ghep "$f" | colab exec -s "$S"
      else echo "[!] colab exec lỗi. 'Connection was lost' = mất kết nối tới kernel (mạng chập chờn) -- chạy lại ô $id."; fi
    fi
    return 0
  fi
  kiem_may >/dev/null
  [ "${2:-}" = SECS=@T4 ] || kiem_secs "$f" || return 2
  lan=1; qua=ssh
  if ! out=$(khoi_dong_ssh "$id" "$f"); then
    qua=exec
    echo "[ssh không khởi động được ô $id -- dùng colab exec]"
  fi
  # colab exec mo websocket toi kernel truoc khi chay ma; mang chap chon -> "Connection was lost"
  # NGAY buoc do (ma khoi dong o chua chay) -> thu lai. Ma khoi dong luon in FZ_PID= / FZ_BAN=,
  # khong co dong nao = chua chay duoc.
  [ $qua = exec ] && for lan in 1 2 3; do
    out=$(khoi_dong "$id" "$f" 2>&1)
    grep -q '^FZ_\(PID\|BAN\)=' <<<"$out" && break
    [ -f "$MAY" ] && [ $lan -lt 3 ] || break
    # CLI co the vua xoa phien (kernel cu 404) du may con -> nhan lai truoc khi thu lai.
    grep -q 'appears to be lost\|not found' <<<"$out" && cuu_phien
    echo "[!] Không kết nối được kernel Colab ($(grep -o 'Connection was lost\|[A-Za-z]*Error: [^│]*' <<<"$out" | tail -1 | sed 's/ *$//'))"
    echo "    thử lại lần $((lan + 1))/3 sau 5 giây... (Ctrl+C = thôi)"
    sleep 5 || return 2
  done
  ban=$(sed -n 's/^FZ_BAN=//p' <<<"$out")
  if [ -n "$ban" ] && [ $lan -gt 1 ] && [ "$ban" = "$id" ]; then
    # Lan truoc mat ket noi SAU khi da khoi dong o -> o dang chay chinh la o nay: xem tiep no.
    out="FZ_PID=$(ssh_colab "cat $LOGD/dang_chay" | awk '{print $2}')"
    ban=
  fi
  if [ -n "$ban" ]; then
    read -rp "Ô $ban vẫn đang chạy nền. Vẫn chạy thêm ô $id song song? (co = chạy): " x
    [ "$x" = co ] || return 2
    if [ $qua = ssh ]; then out=$(khoi_dong_ssh "$id" "$f" ep); else out=$(khoi_dong "$id" "$f" ep); fi
  fi
  pid=$(sed -n 's/^FZ_PID=//p' <<<"$out")
  if [ -z "$pid" ]; then echo "$out"; echo "[!] Không khởi động được ô $id"; return 2; fi
  FZ_O_PID=$pid
  xem "$id" "$pid" || return 1
  tai_theo_o "$id"
  return 0
}

# Muc l: xem tiep log o chay nen gan nhat.
log_truc_tiep() {
  local dc id pid cho con x
  dc=$(ssh_colab "cat $LOGD/dang_chay 2>/dev/null")
  read -r id pid <<<"$dc"
  if [ -z "$id" ]; then echo "(chưa có ô nào chạy nền trên máy này)"; dung; return; fi
  { read -r cho; read -r con; } < "$(CHUOI)" 2>/dev/null
  if [ -n "$con" ] && [ "$cho" != "$id $pid" ]; then
    rm -f "$(CHUOI)"; con=                       # chuoi cu cua o khac -- bo
  fi
  [ -n "$con" ] && echo "(chuỗi đang chờ: ô $id xong thì chạy $con)"
  if xem "$id" "$pid"; then
    tai_theo_o "$id"
    if [ -n "$con" ]; then
      rm -f "$(CHUOI)"
      echo
      read -rp "Ô $id xong. Chạy tiếp chuỗi: $con? (Enter = chạy, n = bỏ): " x
      if [ "$x" != n ]; then chay_cac_o $con; fi
    fi
  fi
  dung
}

# Truoc khi chay o co "SECS = N" (o 04): SECS lon hon thoi gian han muc con lai -> Colab ngat
# giua chung (het quota), khong kip 06. Chi CANH BAO (khong tu doi SECS). 0 = chay tiep.
kiem_secs() {
  local secs may goi x
  secs=$(gia_tri "$1" SECS)
  [ -n "$secs" ] && [ -f ~/fz_han_muc.py ] || return 0
  may=$(colab status -s "$S" 2>/dev/null | sed -n 's/.*Hardware: *\([^ |]*\).*/\1/p' | head -1)
  goi=$(py_colab ~/fz_han_muc.py --may "$may" 2>/dev/null | sed -n 's/^Gợi ý SECS[^:]*: *\([0-9][0-9]*\).*/\1/p')
  [ -n "$goi" ] || return 0
  [ "$secs" -le "$goi" ] && return 0
  echo "[!] SECS = $secs (≈ $((secs / 60)) phút) nhưng hạn mức chỉ còn đủ cho SECS ≈ $goi (≈ $((goi / 60)) phút,"
  echo "    đã trừ 15 phút gom zip + tải về). Colab sẽ ngắt máy khi hết hạn mức -> 06 không kịp chạy."
  echo "    Sửa SECS ở ô 04, hoặc chạy tiếp."
  read -rp "    Vẫn chạy với SECS = $secs? Gõ 'co' (Enter = huỷ): " x
  [ "$x" = co ]
}

# Muc a: cac tai khoan Colab. Tai khoan chinh = ~/.config/colab-cli, tai khoan phu <ten> =
# ~/.fz_tk/<ten>/.config/colab-cli (dang nhap rieng, may rieng, han muc rieng). Chon so = cua so
# nay dung tai khoan do; cac cua so Termux khac khong bi anh huong.
tk_dang_nhap() { [ -f "$([ -n "$1" ] && echo "$TKG/$1" || echo "$HOME")/.config/colab-cli/token.json" ]; }
tai_khoan() {
  local ds i x ten cu
  # Tai khoan da "cat" theo cach cu (~/.config/colab-cli/luu/<ten>) -> tai khoan phu cung ten.
  for x in "$HOME/.config/colab-cli/luu"/*/; do
    [ -f "$x/token.json" ] || continue
    ten=$(basename "$x")
    tk_hop_le "$ten" && ! tk_trung "$ten" || continue
    mkdir -p "$TKG/$ten/.config/colab-cli" && cp "$x"/*.json "$TKG/$ten/.config/colab-cli/"
  done
  while true; do
    ds=("")
    for x in "$TKG"/*/; do [ -d "$x" ] && ds+=("$(basename "$x")"); done
    clear
    echo "== Tài khoản Colab =="
    for i in "${!ds[@]}"; do
      ten=${ds[$i]}; x=""
      [ "$ten" = "$TK" ] && x="<- cửa sổ này"
      [ -n "$(cua_so_khac "$ten")" ] && x="${x:+$x, }đang mở ở cửa sổ khác"
      printf " %2d  %-20s %-15s %s\n" $((i + 1)) "$(ten_tk "$ten")$([ -z "$ten" ] && echo " (chính)")" \
        "$(tk_dang_nhap "$ten" && echo "đã đăng nhập" || echo "CHƯA đăng nhập")" "$x"
    done
    echo "---"
    echo " Số = cửa sổ này dùng tài khoản đó (cửa sổ khác không đổi)"
    echo " n  = thêm tài khoản · r = đổi tên · x = đăng xuất / xoá · Enter = về menu"
    echo " Dùng CÙNG LÚC: mở thêm cửa sổ Termux (vuốt từ mép trái -> NEW SESSION), gõ: fz @<tên>"
    read -rp "Chọn: " x || return
    case "$x" in
    "") return ;;
    n|N)
      read -rp "Tên tài khoản mới (chữ/số/_/-, tối đa 20, vd B hoac phuc2): " ten
      tk_hop_le "$ten" || { echo "[!] Tên không hợp lệ"; dung; continue; }
      tk_trung "$ten" && { echo "[!] Đã có tài khoản $ten"; dung; continue; }
      dat_tk "$ten"; ghi_cua_so
      echo "[cửa sổ này dùng tài khoản $ten] Mở link dưới đây, chọn ĐÚNG tài khoản Google muốn thêm:"
      colab sessions      # chua co token -> CLI in link dang nhap o day
      dung; return ;;
    r|R)
      read -rp "Số tài khoản cần đổi tên: " i
      [[ "$i" =~ ^[0-9]+$ ]] && [ "$i" -ge 1 ] && [ "$i" -le ${#ds[@]} ] || continue
      ten=${ds[$((i - 1))]}
      if [ -n "$(cua_so_khac "$ten")" ]; then
        echo "[!] Tài khoản $(ten_tk "$ten") đang mở ở cửa sổ khác -- thoát menu bên đó (q) rồi đổi tên."
        dung; continue
      fi
      read -rp "Tên mới cho $(ten_tk "$ten") (chữ/số/_/-, tối đa 20): " x
      tk_hop_le "$x" || { echo "[!] Tên không hợp lệ"; dung; continue; }
      cu=$(ten_tk "$ten"); [ "$x" = "$cu" ] && continue
      tk_trung "$x" && { echo "[!] Đã có tài khoản $x"; dung; continue; }
      if [ -z "$ten" ]; then
        mkdir -p "$TKG" && echo "$x" > "$TKG/.ten_chinh"
      else
        mv "$TKG/$ten" "$TKG/$x" || { dung; continue; }
        [ "$TK" = "$ten" ] && { dat_tk "$x"; ghi_cua_so; }
      fi
      echo "[đã đổi tên] $cu -> $x   (mở song song: fz @$x)"
      dung ;;
    x|X)
      read -rp "Số tài khoản cần đăng xuất: " i
      [[ "$i" =~ ^[0-9]+$ ]] && [ "$i" -ge 1 ] && [ "$i" -le ${#ds[@]} ] || continue
      ten=${ds[$((i - 1))]}; cu=$TK
      if [ -n "$(cua_so_khac "$ten")" ]; then
        echo "[!] Tài khoản $(ten_tk "$ten") đang mở ở cửa sổ khác -- thoát menu bên đó (q) trước."
        dung; continue
      fi
      dat_tk "$ten"
      if tk_dang_nhap "$ten"; then
        echo "Máy tài khoản $(ten_tk "$ten") đang giữ (đăng xuất rồi vẫn tính hạn mức tới khi Colab thu hồi):"
        colab sessions
        read -rp "Trả máy '$S' của tài khoản này trước? (co = trả, Enter = không): " x
        [ "$x" = co ] && colab stop -s "$S"
      fi
      read -rp "Đăng xuất $(ten_tk "$ten")$([ -n "$ten" ] && echo " và xoá khỏi danh sách")? Gõ 'co': " x
      if [ "$x" = co ]; then
        if [ -n "$ten" ]; then rm -rf "${TKG:?}/$ten"; [ "$cu" = "$ten" ] && cu=
        else rm -f "$HOME/.config/colab-cli/token.json" "$HOME/.config/colab-cli/sessions.json"; fi
        echo "[đã đăng xuất] $(ten_tk "$ten")"
      fi
      dat_tk "$cu"; ghi_cua_so; dung ;;
    *)
      [[ "$x" =~ ^[0-9]+$ ]] && [ "$x" -ge 1 ] && [ "$x" -le ${#ds[@]} ] || continue
      [ "${ds[$((x - 1))]}" = "$TK" ] && return
      chon_tk "${ds[$((x - 1))]}" || continue
      echo "[cửa sổ này dùng tài khoản $(ten_tk "$TK")]"
      tk_dang_nhap "$TK" || echo "Chưa đăng nhập -- mở link dưới đây:"
      colab sessions
      dung; return ;;
    esac
  done
}

# Muc p: cac may cua tai khoan nay; chon may cho cua so nay, hoac dat ten cho may sap xin (m / c).
# Moi may mot ten; hai may cung ten thi `colab new` GHI DE phien cu (may cu thanh "?", keep-alive
# cua no tu dung -> Colab thu hoi) -- nen m / c tu choi ten dang la mot may con chay.
chon_may() {
  local ds i x ten hw ghi an=0
  mapfile -t ds < <(colab sessions 2>/dev/null | grep '^\[')
  clear
  echo "== Máy của tài khoản $(ten_tk "$TK") · cửa sổ này: '$S' =="
  local co=()
  for i in "${!ds[@]}"; do
    ten=${ds[$i]%%]*}; ten=${ten#[}
    [ "$ten" = "?" ] && { an=$((an + 1)); continue; }
    co+=("$ten")
    hw=$(sed -n 's/.*Hardware: *\([^ |]*\).*/\1/p' <<<"${ds[$i]}")
    ghi=""
    [ "$ten" = "$S" ] && ghi="<- cửa sổ này"
    [ -n "$(cua_so_khac "$TK" "$ten")" ] && ghi="${ghi:+$ghi, }đang mở ở cửa sổ khác"
    printf " %2d  %-20s %-5s %s\n" ${#co[@]} "$ten" "$hw" "$ghi"
  done
  [ ${#co[@]} -eq 0 ] && echo "  (chưa giữ máy nào có tên)"
  [ $an -gt 0 ] && echo "  (+ $an máy không tên '?': nhận lại ở mục t -> n <số>)"
  echo "---"
  echo " Số = cửa sổ này dùng máy đó · gõ TÊN MỚI (vd may2) = cửa sổ này sẽ xin máy tên đó (rồi m / c)"
  echo " Nhiều máy cùng lúc: mỗi cửa sổ Termux một tên -- mở thẳng: fz ${TK:+@$(ten_tk "$TK") }:<tên>"
  echo " Mỗi máy đang giữ đều tiêu hạn mức (h). Enter = về menu"
  read -rp "Chọn: " x || return
  [ -z "$x" ] && return
  if [[ "$x" =~ ^[0-9]+$ ]] && [ "$x" -ge 1 ] && [ "$x" -le ${#co[@]} ]; then ten=${co[$((x - 1))]}
  else
    ten_may_hop_le "$x" || { echo "[!] Tên máy chỉ gồm chữ, số, _ và - (tối đa 20)"; dung; return; }
    ten=$x
  fi
  [ "$ten" = "$S" ] && return
  hoi_trung "$TK" "$ten" || return
  S=$ten; ghi_cua_so
  if printf '%s\n' "${co[@]}" | grep -qx -- "$ten"; then echo "[cửa sổ này dùng máy '$S']"
  else echo "[cửa sổ này dùng tên '$S' -- chưa có máy: m = xin T4, c = xin CPU]"; fi
  dung
}

# m / c: xin may ten $S. Ten dang la mot may CON CHAY -> tu choi (colab new se ghi de phien, may cu
# bi thu hoi). 0 = xin duoc.
duoc_xin() {
  local rc
  [ -f ~/fz_nhan_may.py ] || return 0
  py_colab ~/fz_nhan_may.py con "$S" >/dev/null 2>&1; rc=$?
  [ $rc = 1 ] && return 0
  if [ $rc = 0 ]; then
    echo "[!] Tên '$S' đang là một máy CÒN CHẠY. Xin nữa thì Colab CLI ghi đè phiên và máy đó bị thu hồi."
    echo "    Máy thứ hai: p -> gõ tên mới (vd may2), rồi m / c. Đổi hẳn máy: t (trả) rồi m / c."
    return 1
  fi
  read -rp "[!] Không kiểm được máy '$S' còn chạy không (mạng?). Vẫn xin? Gõ 'co': " rc
  [ "$rc" = co ]
}

# Muc h: han muc mien phi con lai + so du, may dang giu, GPU duoc dung (~/fz_han_muc.py).
han_muc() {
  local may
  # Loai may cua phien $S, tu dong "... | Hardware: T4 | ..." cua colab status (CPU / T4 / ...).
  may=$(colab status -s "$S" 2>/dev/null | sed -n 's/.*Hardware: *\([^ |]*\).*/\1/p' | head -1)
  if [ -f ~/fz_han_muc.py ]; then py_colab ~/fz_han_muc.py --may "$may"; else echo "[!] Thiếu ~/fz_han_muc.py -- chạy: bash ~/lay_ve.sh"; colab usage; fi
}

# Kich thuoc de doc (1.2M, 340K).
kich_thuoc() { numfmt --to=iec --suffix=B "$1" 2>/dev/null || echo "${1}B"; }

# Ten chua co trong Download/FairyZero cho tep $1, kieu Windows Explorer ("Giu ca hai"):
# gen0.onnx -> "gen0 (2).onnx" -> "gen0 (3).onnx" ...; khong duoi / tep an: "ten (2)".
ten_trong() {
  local ten=$1 goc duoi n=2
  [ -e "$TAI/$ten" ] || { echo "$ten"; return; }
  if [[ "$ten" == [!.]*.* ]]; then goc=${ten%.*}; duoi=.${ten##*.}; else goc=$ten; duoi=; fi
  while [ -e "$TAI/$goc ($n)$duoi" ]; do n=$((n + 1)); done
  echo "$goc ($n)$duoi"
}

# Tai tep Colab $1 ve Download/FairyZero. Truyen qua ssh (cat, khong base64, khong giu ca tep
# trong RAM -- hop zip lon); ssh loi thi dung colab download. Tai vao tep tam an, kiem du kich
# thuoc, roi moi dat ten: tep dich luon la ban day du; trung ten -> ten_trong. Chon ten + mv
# nam trong khoa (mkdir la nguyen tu) nen hai cua so tai cung ten cung luc khong de len nhau.
tai_ve() {
  local nguon=$1 ten kt tam dich i q
  ten=${nguon##*/}
  q=$(printf %q "$nguon")
  mkdir -p "$TAI"
  tam=$TAI/.dang_tai_${BASHPID}_${RANDOM}_$ten
  kt=$(ssh_colab "stat -c %s $q" 2>/dev/null)
  if [[ "$kt" =~ ^[0-9]+$ ]]; then
    for i in 1 2 3; do
      echo "Tải về: $nguon ($(kich_thuoc "$kt")) ..."
      if command -v pv >/dev/null; then ssh_colab "cat $q" | pv -s "$kt" > "$tam"
      else ssh_colab "cat $q" > "$tam"; fi
      [ "$(stat -c %s "$tam" 2>/dev/null)" = "$kt" ] && break
      rm -f "$tam"
      if [ $i = 3 ]; then echo "[!] Tải dở / lỗi: $nguon (không lưu gì)"; return 1; fi
      echo "[!] Tải dở (mất kết nối?) -- thử lại lần $((i + 1))/3 sau 5 giây... (Ctrl+C = thôi)"
      sleep 5 || return 1
    done
  else
    echo "Tải về: $nguon (qua colab download) ..."
    colab download -s "$S" "$nguon" "$tam" >/dev/null 2>&1 && [ -f "$tam" ] ||
      { rm -f "$tam"; echo "[!] Không tải được: $nguon (không có trên Colab?)"; return 1; }
  fi
  for i in $(seq 50); do mkdir "$TAI/.khoa_dat_ten" 2>/dev/null && break; sleep 0.2; done
  dich=$(ten_trong "$ten")
  mv "$tam" "$TAI/$dich"
  rmdir "$TAI/.khoa_dat_ten" 2>/dev/null
  if [ "$dich" = "$ten" ]; then echo "[xong] Download/FairyZero/$dich"
  else echo "[xong] Download/FairyZero/$dich  (đã có '$ten' -> lưu tên mới, không ghi đè)"; fi
  # Bao cho Android: tep hien ngay trong Files / trinh chon tep.
  command -v termux-media-scan >/dev/null && termux-media-scan "$TAI/$dich" >/dev/null 2>&1
  return 0
}

# Tai tep dien thoai $1 len Colab $2 (mac dinh /content/<ten>). Qua ssh (cat): colab upload gui CA
# tep base64 trong MOT yeu cau HTTP -> tep lon (~100 MB) bi proxy Colab cat ngang (SSL
# UNEXPECTED_EOF). Ghi tep tam .dang_tai, du kich thuoc moi doi ten; dut giua chung -> thu lai 3 lan.
tai_len() {
  local nguon=$1 dich=${2:-/content/${1##*/}} kt q i
  kt=$(stat -c %s "$nguon" 2>/dev/null) || { echo "[!] Không đọc được $nguon"; return 1; }
  q=$(printf %q "$dich")
  for i in 1 2 3; do
    echo "Tải lên: ${nguon##*/} ($(kich_thuoc "$kt"))  ->  $dich"
    NGAT=0
    if command -v pv >/dev/null; then pv "$nguon"; else cat "$nguon"; fi |
      ssh_colab "mkdir -p \"\$(dirname $q)\" && cat > $q.dang_tai && [ \"\$(stat -c %s $q.dang_tai)\" = $kt ] && mv $q.dang_tai $q"
    [ "${PIPESTATUS[1]}" = 0 ] && { echo "[xong] $dich"; return 0; }
    ssh_colab "rm -f $q.dang_tai" 2>/dev/null
    [ $NGAT = 1 ] && { echo "[huỷ tải lên]"; return 1; }
    [ $i = 3 ] && break
    echo "[!] Tải lên dở (mất kết nối?) -- thử lại lần $((i + 1))/3 sau 5 giây... (Ctrl+C = thôi)"
    sleep 5 || return 1
  done
  echo "[!] Tải lên lỗi: $dich"
  return 1
}

# Sau khi o $1 chay nen xong: tai ve moi tep o do yeu cau bang dong "FZ_TAI_VE=<duong dan>"
# trong log (vd o 06 -> zip van). Nho vay "04 06" = sinh du lieu, gom zip, tai ve dien thoai.
# Moi lan chay o chi tai mot lan: tai xong ghi dong dau log (co gio bat dau) vao <o>.da_tai;
# xem lai bang `l` thi khong tai lai, nhung lan chay truoc chua tai (Ctrl+C, loi ssh) thi tai bu.
tai_theo_o() {
  local ra ds f dau da loi=0 tep
  # Chi hoi Colab khi o tren dien thoai co FZ_TAI_VE (khoi mot lan ssh cho moi o khac).
  tep=$(ls "$D/$1"_*.py 2>/dev/null | head -1)
  if [ -z "$tep" ] || ! doc "$tep" | grep -q FZ_TAI_VE; then
    if [ "$1" = 06 ]; then
      echo; echo "[!] Ô 06 trên điện thoại là bản CŨ (không tự tải zip). Cập nhật: bash ~/lay_ve.sh 06"
      echo "    Zip vẫn nằm trên Colab -- tải tay: fz -> d"
    fi
    return 0
  fi
  ra=$(ssh_colab "printf '%s\n' \"\$(head -1 $LOGD/$1.log 2>/dev/null)\" \"\$(cat $LOGD/$1.da_tai 2>/dev/null)\"; sed -n 's/^FZ_TAI_VE=//p' $LOGD/$1.log 2>/dev/null") ||
    { echo "[!] Không đọc được log ô $1 qua ssh -- không tải về được. Thử lại: fz -> l"; return 1; }
  mapfile -t ds <<<"$ra"
  dau=${ds[0]:-}; da=${ds[1]:-}; ds=("${ds[@]:2}")   # $(..) bo dong trong cuoi -> co the thieu
  [ -z "${ds[*]}" ] && ds=()
  if [ ${#ds[@]} -eq 0 ]; then
    echo; echo "[!] Ô $1 không yêu cầu tải gì (không có dòng FZ_TAI_VE trong log -- ô lỗi?)."
    return 0
  fi
  if [ -n "$dau" ] && [ "$da" = "$dau" ]; then
    echo; echo "(ô $1 lần chạy này đã tải về rồi -- tải lại: fz -> d)"; return 0
  fi
  echo
  echo "== Ô $1 yêu cầu tải về điện thoại: ${#ds[@]} tệp =="
  for f in "${ds[@]}"; do tai_ve "$f" || loi=1; done
  if [ $loi = 0 ]; then
    ssh_colab "cat > $LOGD/$1.da_tai" <<<"$dau"
    echo "Tệp ở: bộ nhớ trong -> Download -> FairyZero (Files / MT Manager: /sdcard/Download/FairyZero)"
  fi
}

# Muc d: duyet thu muc tren may Colab (liet ke qua ssh), chon so de vao thu muc / tai tep ve
# Download/FairyZero (colab download).
duyet_colab() {
  local dir=/content x i loai kt ten muc
  while true; do
    clear
    echo "== Tệp trên Colab: $dir =="
    echo "   (đang đọc thư mục...)"
    mapfile -t muc < <(ssh_colab "cd $(printf %q "$dir") 2>/dev/null && find . -mindepth 1 -maxdepth 1 -printf '%y\t%s\t%f\n' | LC_ALL=C sort -t\$'\t' -k1,1 -k3,3")
    clear
    echo "== Tệp trên Colab: $dir =="
    echo "  0   .. (thư mục cha)"
    for i in "${!muc[@]}"; do
      IFS=$'\t' read -r loai kt ten <<<"${muc[$i]}"
      if [ "$loai" = d ]; then printf " %2d   [%s/]\n" $((i + 1)) "$ten"
      else printf " %2d   %s  (%s)\n" $((i + 1)) "$ten" "$(kich_thuoc "$kt")"; fi
    done
    [ ${#muc[@]} -eq 0 ] && echo "      (trống, hoặc không đọc được)"
    echo "---"
    echo " Số = vào thư mục / tải tệp về · /đường/dẫn = nhảy tới · q = về menu"
    read -rp "Chọn: " x || return
    case "$x" in
      q|Q|"") return ;;
      /*) dir=$x ;;
      0) [ "$dir" != / ] && dir=$(dirname "$dir") ;;
      *)
        [[ "$x" =~ ^[0-9]+$ ]] && [ "$x" -le ${#muc[@]} ] || continue
        IFS=$'\t' read -r loai kt ten <<<"${muc[$((x - 1))]}"
        if [ "$loai" = d ]; then
          dir=${dir%/}/$ten
        else
          tai_ve "${dir%/}/$ten"
          dung
        fi ;;
    esac
  done
}

# Muc u: tai tep tu dien thoai len /content. Duyet thang thu muc tren dien thoai (find, nhu MT
# Manager -- thay moi tep, giu ten), bat dau o Download/FairyZero; hoac c = trinh chon tep cua
# Android (termux-storage-get: chi tra noi dung, khong tra ten -> phai hoi ten).
duyet_dt() {
  local dir=$TAI x loai kt ten muc an=1 loc
  while true; do
    # an=1: giau ten bat dau bang dau cham (.thumbnails, .nomedia ...); phim "." bat/tat.
    loc=(); [ $an = 1 ] && loc=(-not -name '.*')
    mapfile -t muc < <(cd "$dir" 2>/dev/null && find -L . -mindepth 1 -maxdepth 1 "${loc[@]}" \
                         -printf '%y\t%s\t%f\n' 2>/dev/null | LC_ALL=C sort -t$'\t' -k1,1 -k3,3)
    clear
    echo "== Tải lên Colab (/content) · điện thoại: ${dir/#$HOME/\~} =="
    echo "  0   .. (thư mục cha)"
    for i in "${!muc[@]}"; do
      IFS=$'\t' read -r loai kt ten <<<"${muc[$i]}"
      if [ "$loai" = d ]; then printf " %2d   [%s/]\n" $((i + 1)) "$ten"
      else printf " %2d   %s  (%s)\n" $((i + 1)) "$ten" "$(kich_thuoc "$kt")"; fi
    done
    [ ${#muc[@]} -eq 0 ] && echo "      (trống, hoặc không đọc được)"
    echo "---"
    echo " Số = vào thư mục / tải tệp lên · 0 = lên · . = $([ $an = 1 ] && echo hiện || echo ẩn) tệp ẩn · c = trình chọn tệp Android · q = về menu"
    echo " (~/storage/shared = bộ nhớ trong. Thiếu tệp so với MT Manager: cấp cho Termux quyền"
    echo "  \"Quản lý tất cả các tệp\" -- xem HUONG_DAN_TERMUX.md mục 13)"
    read -rp "Chọn: " x || return
    case "$x" in
      q|Q|"") return ;;
      c|C) chon_android; dung ;;
      .) an=$((1 - an)) ;;
      0) dir=$(dirname "$dir") ;;
      *)
        [[ "$x" =~ ^[0-9]+$ ]] && [ "$x" -ge 1 ] && [ "$x" -le ${#muc[@]} ] || continue
        IFS=$'\t' read -r loai kt ten <<<"${muc[$((x - 1))]}"
        if [ "$loai" = d ]; then
          dir=${dir%/}/$ten
        else
          tai_len "${dir%/}/$ten"
          dung
        fi ;;
    esac
  done
}

chon_android() {
  local tam ten i
  if ! command -v termux-storage-get >/dev/null; then
    echo "[!] Cần app Termux:API (cùng nguồn cài với Termux: F-Droid/GitHub) và: pkg install termux-api"
    return
  fi
  tam=$TAI/.dang_chon_$$
  rm -f "$tam"
  # Trinh chon tep cua Android (Files by Google) doc danh muc tep cua Android (MediaStore);
  # tep Termux tu ghi ra co the chua co trong do -> an. Bao cho Android truoc.
  command -v termux-media-scan >/dev/null && termux-media-scan -r "$HOME/storage/downloads" >/dev/null 2>&1
  echo "Chọn tệp trong cửa sổ vừa mở... (không thấy tệp: ☰ -> bộ nhớ trong để duyệt thẳng thư mục)"
  termux-storage-get "$tam"
  for i in $(seq 120); do [ -s "$tam" ] && break; sleep 1; done   # cho toi 2 phut
  [ -s "$tam" ] || { echo "[!] Không nhận được tệp (huỷ chọn, hoặc tệp rỗng)"; rm -f "$tam"; return; }
  sleep 1   # cho ghi xong
  echo "Đã nhận tệp ($(kich_thuoc "$(stat -c %s "$tam")")). termux-storage-get không trả về tên gốc."
  read -rp "Tên tệp trên Colab (vd gen1.onnx): " ten
  [ -n "$ten" ] && tai_len "$tam" "/content/$ten"
  rm -f "$tam"
}

# Muc t: liet ke MOI may dang giu tren tai khoan (colab sessions), chon may de tra. May co ten
# -> colab stop -s <ten>; may "?" (khong co ten tren dien thoai nay: tao tu web / thiet bi khac)
# -> goi thang client.unassign(endpoint) -- dung ham colab stop goi ben trong.
tra_may() {
  local ds dong i x chon ten ep hw
  while true; do
    mapfile -t ds < <(colab sessions 2>/dev/null | grep '^\[')
    clear
    echo "== Trả máy (tài khoản $(ten_tk "$TK")) =="
    if [ ${#ds[@]} -eq 0 ]; then echo "  (không giữ máy nào)"; return; fi
    for i in "${!ds[@]}"; do
      dong=${ds[$i]}
      ten=${dong%%]*}; ten=${ten#[}
      ep=${dong#*] }; ep=${ep%% *}
      hw=$(sed -n 's/.*Hardware: *\([^ |]*\).*/\1/p' <<<"$dong")
      if [ "$ten" = "?" ]; then printf " %2d   %-4s  %-5s %s   (không có tên ở máy này)\n" $((i + 1)) "?" "$hw" "$ep"
      else printf " %2d   %-4s  %-5s %s\n" $((i + 1)) "$ten" "$hw" "$ep"; fi
    done
    echo "---"
    echo " Số (nhiều số cách nhau) = trả các máy đó · a = trả TẤT CẢ · Enter = về menu"
    echo " n <số> = NHẬN LẠI máy '?' làm phiên '$S' (máy vẫn chạy nhưng mất tên -- vd CLI xoá phiên khi kernel chết)"
    read -rp "Chọn: " -a chon || return
    [ ${#chon[@]} -eq 0 ] && return
    if [ "${chon[0]}" = n ] || [ "${chon[0]}" = N ]; then
      x=${chon[1]:-}
      [[ "$x" =~ ^[0-9]+$ ]] && [ "$x" -ge 1 ] && [ "$x" -le ${#ds[@]} ] || continue
      dong=${ds[$((x - 1))]}
      ten=${dong%%]*}; ten=${ten#[}
      ep=${dong#*] }; ep=${ep%% *}
      [ "$ten" = "?" ] || { echo "[!] Máy $x đã có tên '$ten'"; dung; continue; }
      if grep -q "^\[$S\]" <<<"$(printf '%s\n' "${ds[@]}")"; then
        read -rp "Phiên '$S' đang là máy khác -- TRẢ máy đó (mất /content của nó) rồi nhận máy $x? Gõ 'co': " x
        [ "$x" = co ] || continue
        colab stop -s "$S"
      elif colab status -s "$S" >/dev/null 2>&1; then
        colab stop -s "$S" >/dev/null 2>&1    # ten con trong sessions.json nhung may da mat
      fi
      [ -f ~/fz_nhan_may.py ] && py_colab ~/fz_nhan_may.py nhan "$S" "$ep" || echo "[!] Thiếu ~/fz_nhan_may.py -- chạy: bash ~/lay_ve.sh"
      dung; continue
    fi
    if [ "${chon[0]}" = a ] || [ "${chon[0]}" = A ]; then chon=($(seq ${#ds[@]})); fi
    local hop=()
    for x in "${chon[@]}"; do
      [[ "$x" =~ ^[0-9]+$ ]] && [ "$x" -ge 1 ] && [ "$x" -le ${#ds[@]} ] && hop+=("$x")
    done
    [ ${#hop[@]} -eq 0 ] && continue
    read -rp "Trả ${#hop[@]} máy (${hop[*]})? Mọi tệp /content trên đó sẽ MẤT. Gõ 'co' để trả: " x
    [ "$x" = co ] || continue
    for x in "${hop[@]}"; do
      dong=${ds[$((x - 1))]}
      ten=${dong%%]*}; ten=${ten#[}
      ep=${dong#*] }; ep=${ep%% *}
      if [ "$ten" != "?" ]; then
        colab stop -s "$ten"
      else
        echo "[colab] Trả máy không tên $ep..."
        py_colab - "$ep" <<'EOF'
import sys
from colab_cli.common import state
state.client.unassign(sys.argv[1])
print("[colab] Session terminated.")
EOF
      fi
    done
    dung
  done
}

# Chay lan luot cac o $@; dung chuoi khi nguoi dung Ctrl+C / huy.
# Chuoi o dang cho (vd "04 06 07" ma ve menu giua 04 -- Ctrl+C hay mat ket noi lau): ~/.fz_tk/
# .chuoi_<tai khoan>_<phien> = dong 1 "<o> <pid>" o dang chay nen, dong 2 cac o con lai. Menu l
# xem o do toi khi xong roi hoi chay tiep phan con lai.
CHUOI() { echo "$TKG/.chuoi_$(ten_tk "$TK")_$S"; }
chay_cac_o() {
  local id f i=0 con
  local -A gd=()
  rm -f "$(CHUOI)"
  # Hoi het tham so TRUOC (chuoi dai khong phai dung giua chung cho nguoi tra loi).
  for id in "$@"; do
    f=$(ls "$D"/"$id"_*.py 2>/dev/null | head -1)
    [ -n "$f" ] || continue
    gd[$id]=$(hoi_tham_so "$f") || { echo "[dừng -- không chạy ô nào]"; return 1; }
  done
  for id in "$@"; do
    i=$((i + 1))
    f=$(ls "$D"/"$id"_*.py 2>/dev/null | head -1)
    if [ -z "$f" ]; then echo "[!] Không có ô $id"; continue; fi
    chay_o "$f" "${gd[$id]:-}"
    case $? in
      0) ;;
      1) con="${*:i+1}"
         echo
         if [ -n "$con" ]; then
           mkdir -p "$TKG" && printf '%s %s\n%s\n' "$id" "$FZ_O_PID" "$con" > "$(CHUOI)"
           echo "[về -- ô $id vẫn chạy nền. Chuỗi còn: $con -- fz -> l: xem $id tới khi xong rồi chạy tiếp]"
         else
           echo "[về -- ô $id vẫn chạy nền; xem lại: fz -> l]"
         fi
         return 1 ;;
      *) echo; echo "[dừng -- các ô sau không chạy]"; return 1 ;;
    esac
  done
}

if [ -n "$LE" ]; then tai_len "$2" "${3:-}"; exit; fi
if [ $# -gt 0 ]; then chay_cac_o "$@"; exit; fi

while true; do
  clear
  gen=$(doc "$D/00_cau_hinh.py" 2>/dev/null | sed -n 's/^GEN_CURRENT *= *\([0-9]*\).*/\1/p')
  echo "======== FairyZero trên Colab ========"
  echo " Tài khoản: $(ten_tk "$TK")   ·   Máy: $S   ·   Đời: ${gen:-?}"
  if [ -f "$(CHUOI)" ]; then
    { read -r x; read -r y; } < "$(CHUOI)"
    echo " Chuỗi đang chờ: ô ${x%% *} xong thì chạy $y  (l = xem rồi chạy tiếp)"
  fi
  echo " Ô lệnh: Download/FairyZero/o_lenh"
  echo "--------------------------------------"
  files=()
  for f in "$D"/[0-9]*_*.py; do
    [ -f "$f" ] || continue
    id=$(basename "$f"); id=${id%%_*}
    [ "$id" = 00 ] && continue
    files+=("$f")
    printf " %-4s %s\n" "$id" "$(tieu_de "$f")"
  done
  [ ${#files[@]} -eq 0 ] && echo " (chưa có ô nào -- chạy: bash ~/lay_ve.sh)"
  echo "--------------------------------------"
  echo " m    Xin máy T4 (tên '$S')"
  echo " p    Chọn máy / đặt tên máy mới (chạy nhiều máy cùng lúc)"
  echo " g    Đổi đời mạng GEN_CURRENT (hiện ${gen:-?}): + / - / số"
  echo " c    Xin máy CPU (thử nghiệm, không tốn hạn mức T4)"
  echo " l    Log trực tiếp ô đang chạy nền"
  echo " k    Xem máy đang giữ"
  echo " h    Hạn mức còn lại (máy đang giữ + T4)"
  echo " d    Duyệt tệp Colab, tải về điện thoại"
  echo " u    Duyệt tệp điện thoại, tải lên Colab"
  echo " t    Trả máy -- chọn trong mọi máy đang giữ (XOÁ /content)"
  echo " a    Tài khoản Colab (thêm / đổi / đăng xuất; nhiều tài khoản cùng lúc)"
  echo " q    Thoát"
  echo "--------------------------------------"
  echo " Nhiều ô liền nhau: gõ cách nhau, vd: 01 02"
  read -rp "Chọn: " -a chon || continue
  [ ${#chon[@]} -eq 0 ] && continue

  case "${chon[0]}" in
  q|Q) exit 0 ;;
  m|M) duoc_xin && { colab new -s "$S" --gpu T4; colab status -s "$S"; kiem_may >/dev/null; }; dung; continue ;;
  c|C)
    # Khong --gpu = may CPU. O dung GPU (04, 07, 08: --provider cuda / --amp) se loi tren may nay.
    duoc_xin || { dung; continue; }
    colab new -s "$S"; colab status -s "$S"; kiem_may >/dev/null
    echo; echo "[máy CPU] Hợp để thử menu, ô 01/02/03/05/06, tải lên/về. Ô 04/07/08 cần T4."
    echo "          Đổi sang T4: t (trả máy) rồi m."
    dung; continue ;;
  k|K) colab sessions; colab status -s "$S"; dung; continue ;;
  l|L) log_truc_tiep; continue ;;
  h|H) han_muc; dung; continue ;;
  a|A) tai_khoan; continue ;;
  t|T) tra_may; continue ;;
  p|P) chon_may; continue ;;
  g|G) doi_doi; dung; continue ;;
  d|D) duyet_colab; continue ;;
  u|U) duyet_dt; continue ;;
  esac

  chay_cac_o "${chon[@]}"
  dung
done
