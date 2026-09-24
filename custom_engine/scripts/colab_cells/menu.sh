#!/data/data/com.termux/files/usr/bin/bash
# menu.sh -- menu FairyZero tren Termux: chon o lenh bang so, chay tren may Colab.
# Mo bang lenh `fz` (lay_ve.sh them vao ~/.bashrc). O lenh: Download/FairyZero/o_lenh.
# `bash menu.sh 04 05` (lenh `o 04 05`): chay thang cac o do theo cung cach, khong hien menu.
#
# Cach chay mot o:
#   - O co dong "# fz: nhanh" (01, 05, 09): gui thang cho `colab exec`, ket qua hien ngay.
#   - O con lai: `colab exec` chi KHOI DONG o do chay nen tren may Colab (IPython rieng, log o
#     /content/fz_log/<o>.log) roi tra ve ngay; menu xem log truc tiep qua `ssh ... tail -F`.
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

# Khoi dong o $1 (so o) tu tep $2 chay nen tren Colab. In "FZ_PID=<pid>", hoac "FZ_BAN=<o>" neu
# dang co o khac chay nen (khi do khong khoi dong, tru khi $3 = ep).
khoi_dong() {
  local b
  b=$(ghep "$2" | base64 -w0)
  colab exec -s "$S" <<EOF
import base64, os, subprocess, time
ID, EP, D = "$1", "${3:-}" == "ep", "$LOGD"
os.makedirs(D, exist_ok=True)
ban = None
try:
    cu, pid_cu = open(f"{D}/dang_chay").read().split()
    if os.path.exists(f"/proc/{pid_cu}") and not EP:
        ban = cu
except (FileNotFoundError, ValueError):
    pass
if ban:
    print(f"FZ_BAN={ban}")
else:
    p, log = f"{D}/{ID}.ipy", f"{D}/{ID}.log"
    open(p, "w").write(base64.b64decode("$b").decode())
    with open(log, "w") as f:
        f.write(f"[fz] o {ID} bat dau {time.strftime('%H:%M:%S')}\n")
        f.flush()
        lenh = (f"cd /content && stdbuf -oL -eL python3 -m IPython --no-banner --colors=NoColor {p}; "
                f"rc=\$?; echo \"[fz] o {ID} xong \$(date +%H:%M:%S), ma thoat \$rc\"")
        pr = subprocess.Popen(["bash", "-c", lenh], stdout=f, stderr=subprocess.STDOUT,
                              stdin=subprocess.DEVNULL, start_new_session=True,
                              env=dict(os.environ, PYTHONUNBUFFERED="1"))
    open(f"{D}/dang_chay", "w").write(f"{ID} {pr.pid}\n")
    print(f"FZ_PID={pr.pid}")
EOF
}

# Xem log o $1 (pid $2) truc tiep den khi o xong. Tra ve 0 = o da xong, khac 0 = Ctrl+C.
xem() {
  echo "== Log trực tiếp ô $1 · Ctrl+C để về menu (ô vẫn chạy tiếp) =="
  ssh_colab "tail -n +1 -F --pid=$2 $LOGD/$1.log 2>/dev/null"
}

# Chay o tep $1: nhanh thi chay thang; con lai thi chay nen + xem log.
# Tra ve khac 0 neu nguoi dung Ctrl+C / huy (de dung chuoi nhieu o).
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
    [ "$x" = co ] || return 1
    out=$(khoi_dong "$id" "$f" ep)
  fi
  pid=$(sed -n 's/^FZ_PID=//p' <<<"$out")
  if [ -z "$pid" ]; then echo "$out"; echo "[!] Không khởi động được ô $id"; return 1; fi
  xem "$id" "$pid"
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

# Chay lan luot cac o $@; dung chuoi khi nguoi dung Ctrl+C / huy.
chay_cac_o() {
  local id f
  for id in "$@"; do
    f=$(ls "$D"/"$id"_*.py 2>/dev/null | head -1)
    if [ -z "$f" ]; then echo "[!] Không có ô $id"; continue; fi
    if ! chay_o "$f"; then
      echo; echo "[dừng -- ô chạy nền vẫn tiếp tục; xem lại: fz -> l]"
      return 1
    fi
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
  echo " l    Log trực tiếp ô đang chạy nền"
  echo " k    Xem máy đang giữ"
  echo " h    Hạn mức GPU (colab usage)"
  echo " d    Tải tệp Colab -> điện thoại"
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
  k|K) colab sessions; colab status -s "$S"; dung; continue ;;
  l|L) log_truc_tiep; continue ;;
  h|H) colab usage; dung; continue ;;
  a|A) doi_tai_khoan; dung; continue ;;
  t|T)
    read -rp "Trả máy '$S'? Mọi tệp trên Colab (/content) sẽ MẤT. Gõ 'co' để trả: " x
    [ "$x" = co ] && colab stop -s "$S"
    dung; continue ;;
  d|D)
    echo "Ví dụ: /content/games_gen${gen:-0}.zip   /content/gen$(( ${gen:-0} + 1 )).onnx"
    read -rp "Đường dẫn tệp trên Colab: " r
    [ -n "$r" ] && colab download -s "$S" "$r" "$TAI/$(basename "$r")" && echo "-> Download/FairyZero/$(basename "$r")"
    dung; continue ;;
  u|U)
    mapfile -t ds < <(find "$TAI" -maxdepth 1 -type f | sort)
    [ ${#ds[@]} -eq 0 ] && { echo "Download/FairyZero chưa có tệp nào."; dung; continue; }
    for i in "${!ds[@]}"; do printf " %2d  %s\n" $((i + 1)) "$(basename "${ds[$i]}")"; done
    read -rp "Số thứ tự tệp: " i
    if [[ "$i" =~ ^[0-9]+$ ]] && [ "$i" -ge 1 ] && [ "$i" -le ${#ds[@]} ]; then
      f=${ds[$((i - 1))]}
      colab upload -s "$S" "$f" "/content/$(basename "$f")"
    fi
    dung; continue ;;
  esac

  chay_cac_o "${chon[@]}"
  dung
done
