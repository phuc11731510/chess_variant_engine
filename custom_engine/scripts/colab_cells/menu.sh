#!/data/data/com.termux/files/usr/bin/bash
# menu.sh -- menu FairyZero tren Termux: chon o lenh bang so, chay tren may Colab.
# Mo bang lenh `fz` (lay_ve.sh them vao ~/.bashrc). O lenh: Download/FairyZero/o_lenh.
# `bash menu.sh 04 05` (lenh `o 04 05`): chay thang cac o do theo cung cach, khong hien menu.
#
# Cach chay mot o:
#   - O co dong "# fz: nhanh" (01, 05, 09): gui thang cho `colab exec`, ket qua hien ngay.
#   - O con lai: `colab exec` chi KHOI DONG o do chay nen tren may Colab (IPython rieng, log o
#     /content/fz_log/<o>.log) roi tra ve ngay; menu xem log truc tiep qua ssh (fz_may.py).
#     Ctrl+C chi dong phan xem (ssh), o van chay tiep. Kernel cua colab exec khong bi giu, nen
#     menu khong bao gio phai cho o chay nen.
D=$HOME/storage/downloads/FairyZero/o_lenh
TAI=$HOME/storage/downloads/FairyZero
S=${S:-fz}
LOGD=/content/fz_log

# Ctrl+C: dung lenh dang chay (ssh xem log), KHONG thoat menu. Handler (khong phai bo qua)
# de tien trinh con van nhan Ctrl+C binh thuong.
trap ':' INT

# Doc tep o: bo BOM va \r ma trinh sua tep tren dien thoai co the them vao.
doc() { sed 's/^\xEF\xBB\xBF//; s/\r$//' "$@"; }

# Mot o = o cau hinh 00 + o do (de moi o biet GEN_CURRENT va duong dan).
ghep() { doc "$D/00_cau_hinh.py" "$1"; }

tieu_de() { doc "$1" | sed -n '1s/^# *//p'; }

dung() { echo; read -rp "--- Enter để về menu ---" _; }

# ssh toi may Colab cua phien $S (khong can ~/.ssh/config).
ssh_colab() {
  ssh -o ProxyCommand="$(command -v colab) ssh --proxy-mode -s $S" \
      -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR \
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

# Xem log o $1 (pid $2) tu dau va theo tiep den khi o ket thuc (fz_may.py theo_doi).
# Tra ve 0 = o da ket thuc, khac 0 = Ctrl+C (o van chay tiep).
xem() {
  echo "== Log trực tiếp ô $1 · Ctrl+C để về menu (ô vẫn chạy tiếp) =="
  ssh_colab "python3 $LOGD/fz_may.py theo_doi $1 $2"
}

# Chay o tep $1: nhanh thi chay thang; con lai thi chay nen + xem log.
# Tra ve 0 = o ket thuc; 1 = Ctrl+C khi dang xem (o VAN chay nen); 2 = khong khoi dong / huy.
chay_o() {
  local f=$1 id out pid ban x
  id=$(basename "$f"); id=${id%%_*}
  echo
  echo "====== Ô $id: $(tieu_de "$f") ======"
  if doc "$f" | grep -q '^# fz: nhanh'; then
    ghep "$f" | colab exec -s "$S"
    return 0
  fi
  out=$(khoi_dong "$id" "$f")
  ban=$(sed -n 's/^FZ_BAN=//p' <<<"$out")
  if [ -n "$ban" ]; then
    read -rp "Ô $ban vẫn đang chạy nền. Vẫn chạy thêm ô $id song song? (co = chạy): " x
    [ "$x" = co ] || return 2
    out=$(khoi_dong "$id" "$f" ep)
  fi
  pid=$(sed -n 's/^FZ_PID=//p' <<<"$out")
  if [ -z "$pid" ]; then echo "$out"; echo "[!] Không khởi động được ô $id"; return 2; fi
  xem "$id" "$pid" || return 1
}

# Muc l: xem tiep log o chay nen gan nhat.
log_truc_tiep() {
  local dc id pid
  dc=$(ssh_colab "cat $LOGD/dang_chay 2>/dev/null")
  read -r id pid <<<"$dc"
  if [ -z "$id" ]; then echo "(chưa có ô nào chạy nền trên máy này)"; dung; return; fi
  xem "$id" "$pid"
  dung
}

# Doi tai khoan Colab. Dang nhap = ~/.config/colab-cli/token.json (+ sessions.json: cac phien
# cua tai khoan do). Cat moi tai khoan vao ~/.config/colab-cli/luu/<ten>/ de doi qua lai.
CFG=$HOME/.config/colab-cli
LUU=$CFG/luu
doi_tai_khoan() {
  local x ten i ds
  echo "== Đổi tài khoản Colab =="
  colab sessions
  read -rp "Trả máy '$S' của tài khoản hiện tại trước? (co = trả, Enter = không): " x
  [ "$x" = co ] && colab stop -s "$S"
  if [ -f "$CFG/token.json" ]; then
    read -rp "Cất tài khoản hiện tại để lần sau quay lại? Gõ tên (vd A), Enter = không cất: " ten
    if [ -n "$ten" ]; then
      mkdir -p "$LUU/$ten"
      cp "$CFG/token.json" "$LUU/$ten/"
      [ -f "$CFG/sessions.json" ] && cp "$CFG/sessions.json" "$LUU/$ten/"
      echo "[đã cất] $ten"
    fi
  fi
  mapfile -t ds < <(find "$LUU" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort)
  echo " 0   Đăng nhập tài khoản MỚI (mở link, chọn tài khoản trong trình duyệt)"
  for i in "${!ds[@]}"; do printf " %-3s Dùng lại tài khoản đã cất: %s\n" $((i + 1)) "$(basename "${ds[$i]}")"; done
  read -rp "Chọn (Enter = huỷ, giữ tài khoản hiện tại): " i
  [ -z "$i" ] && return
  rm -f "$CFG/token.json" "$CFG/sessions.json"
  if [[ "$i" =~ ^[0-9]+$ ]] && [ "$i" -ge 1 ] && [ "$i" -le ${#ds[@]} ]; then
    cp "${ds[$((i - 1))]}"/*.json "$CFG/"
    echo "[đã chuyển] $(basename "${ds[$((i - 1))]}")"
  fi
  colab sessions      # chua co token -> CLI in link dang nhap o day
}

# Muc h: han muc mien phi con lai + so du, may dang giu, GPU duoc dung (~/fz_han_muc.py).
han_muc() {
  local may
  # Loai may cua phien $S, tu dong "... | Hardware: T4 | ..." cua colab status (CPU / T4 / ...).
  may=$(colab status -s "$S" 2>/dev/null | sed -n 's/.*Hardware: *\([^ |]*\).*/\1/p' | head -1)
  if [ -f ~/fz_han_muc.py ]; then python ~/fz_han_muc.py --may "$may"; else echo "[!] Thiếu ~/fz_han_muc.py -- chạy: bash ~/lay_ve.sh"; colab usage; fi
}

# Kich thuoc de doc (1.2M, 340K).
kich_thuoc() { numfmt --to=iec --suffix=B "$1" 2>/dev/null || echo "${1}B"; }

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
          echo "Tải về: ${dir%/}/$ten  ->  Download/FairyZero/$ten ($(kich_thuoc "$kt"))"
          if colab download -s "$S" "${dir%/}/$ten" "$TAI/$ten"; then
            echo "[xong] Download/FairyZero/$ten"
            # Bao cho Android: tep hien ngay trong Files / trinh chon tep.
            command -v termux-media-scan >/dev/null && termux-media-scan "$TAI/$ten" >/dev/null 2>&1
          fi
          dung
        fi ;;
    esac
  done
}

# Muc u: tai tep tu dien thoai len /content. Chon trong Download/FairyZero, hoac mo trinh chon
# tep cua Android (termux-storage-get, can app Termux:API + goi termux-api).
tai_len() {
  local ds i f x ten tam
  mapfile -t ds < <(find "$TAI" -maxdepth 1 -type f | sort)
  echo "== Tải lên Colab (/content) =="
  for i in "${!ds[@]}"; do printf " %2d  %s  (%s)\n" $((i + 1)) "$(basename "${ds[$i]}")" "$(kich_thuoc "$(stat -c %s "${ds[$i]}")")"; done
  [ ${#ds[@]} -eq 0 ] && echo "     (Download/FairyZero chưa có tệp nào)"
  echo "  c  Chọn tệp khác bằng trình chọn tệp của Android"
  read -rp "Chọn (Enter = huỷ): " x
  if [ "$x" = c ] || [ "$x" = C ]; then
    if ! command -v termux-storage-get >/dev/null; then
      echo "[!] Cần app Termux:API (cùng nguồn cài với Termux: F-Droid/GitHub) và: pkg install termux-api"
      return
    fi
    tam=$TAI/.dang_chon_$$
    rm -f "$tam"
    # Trinh chon tep cua Android (Files by Google) doc danh muc tep cua Android (MediaStore);
    # tep Termux tu ghi ra (vd colab download) chua co trong do -> an. Bao cho Android truoc.
    command -v termux-media-scan >/dev/null && termux-media-scan -r "$HOME/storage/downloads" >/dev/null 2>&1
    echo "Chọn tệp trong cửa sổ vừa mở... (không thấy tệp: ☰ -> bộ nhớ trong để duyệt thẳng thư mục)"
    termux-storage-get "$tam"
    for i in $(seq 120); do [ -s "$tam" ] && break; sleep 1; done   # cho toi 2 phut
    [ -s "$tam" ] || { echo "[!] Không nhận được tệp (huỷ chọn, hoặc tệp rỗng)"; rm -f "$tam"; return; }
    sleep 1   # cho ghi xong
    echo "Đã nhận tệp ($(kich_thuoc "$(stat -c %s "$tam")")). Android không cho biết tên gốc của tệp."
    read -rp "Tên tệp trên Colab (vd gen1.onnx): " ten
    [ -n "$ten" ] && colab upload -s "$S" "$tam" "/content/$ten" && echo "[xong] /content/$ten"
    rm -f "$tam"
  elif [[ "$x" =~ ^[0-9]+$ ]] && [ "$x" -ge 1 ] && [ "$x" -le ${#ds[@]} ]; then
    f=${ds[$((x - 1))]}
    colab upload -s "$S" "$f" "/content/$(basename "$f")" && echo "[xong] /content/$(basename "$f")"
  fi
}

# Chay lan luot cac o $@; dung chuoi khi nguoi dung Ctrl+C / huy.
chay_cac_o() {
  local id f
  for id in "$@"; do
    f=$(ls "$D"/"$id"_*.py 2>/dev/null | head -1)
    if [ -z "$f" ]; then echo "[!] Không có ô $id"; continue; fi
    chay_o "$f"
    case $? in
      0) ;;
      1) echo; echo "[về -- ô $id vẫn chạy nền; xem lại: fz -> l]"; return 1 ;;
      *) echo; echo "[dừng -- các ô sau không chạy]"; return 1 ;;
    esac
  done
}

if [ $# -gt 0 ]; then chay_cac_o "$@"; exit; fi

while true; do
  clear
  gen=$(doc "$D/00_cau_hinh.py" 2>/dev/null | sed -n 's/^GEN_CURRENT *= *\([0-9]*\).*/\1/p')
  echo "======== FairyZero trên Colab ========"
  echo " Phiên: $S   ·   Đời hiện tại: ${gen:-?}"
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
  echo " m    Xin máy T4"
  echo " c    Xin máy CPU (thử nghiệm, không tốn hạn mức T4)"
  echo " l    Log trực tiếp ô đang chạy nền"
  echo " k    Xem máy đang giữ"
  echo " h    Hạn mức GPU còn lại"
  echo " d    Duyệt tệp Colab, tải về điện thoại"
  echo " u    Tải tệp điện thoại -> Colab"
  echo " t    Trả máy (XOÁ /content)"
  echo " a    Đổi tài khoản Colab"
  echo " q    Thoát"
  echo "--------------------------------------"
  echo " Nhiều ô liền nhau: gõ cách nhau, vd: 01 02"
  read -rp "Chọn: " -a chon || continue
  [ ${#chon[@]} -eq 0 ] && continue

  case "${chon[0]}" in
  q|Q) exit 0 ;;
  m|M) colab new -s "$S" --gpu T4; colab status -s "$S"; dung; continue ;;
  c|C)
    # Khong --gpu = may CPU. O dung GPU (04, 07, 08: --provider cuda / --amp) se loi tren may nay.
    colab new -s "$S"; colab status -s "$S"
    echo; echo "[máy CPU] Hợp để thử menu, ô 01/02/03/05/06, tải lên/về. Ô 04/07/08 cần T4."
    echo "          Đổi sang T4: t (trả máy) rồi m."
    dung; continue ;;
  k|K) colab sessions; colab status -s "$S"; dung; continue ;;
  l|L) log_truc_tiep; continue ;;
  h|H) han_muc; dung; continue ;;
  a|A) doi_tai_khoan; dung; continue ;;
  t|T)
    read -rp "Trả máy '$S'? Mọi tệp trên Colab (/content) sẽ MẤT. Gõ 'co' để trả: " x
    [ "$x" = co ] && colab stop -s "$S"
    dung; continue ;;
  d|D) duyet_colab; continue ;;
  u|U) tai_len; dung; continue ;;
  esac

  chay_cac_o "${chon[@]}"
  dung
done
