#!/data/data/com.termux/files/usr/bin/bash
# cay_chay_lai_moi.sh -- Bắt đầu lại cách cây từ mạng đời 0 bằng PHƯƠNG PHÁP MỚI (23/11, SUY_RA_CONG_THUC.md mục 12; mã
# cay_moi.py): cất dữ liệu lần chạy 5, dựng thư mục cay mới chỉ có mạng đời 0 chung và tệp đánh dấu phuong_phap_moi (cay.py
# thấy tệp này thì dùng CayMoi), cất kết quả arena cũ của cách cây, cho vòng lặp CHỈ làm cách cây (cách truyền thống đứng
# yên ở đời 21 làm mốc). Chạy trên điện thoại (Termux), không có cửa sổ vòng lặp nào đang mở:
#   bash cay_chay_lai_moi.sh            # làm thật
#   bash cay_chay_lai_moi.sh kiem       # chỉ in việc sẽ làm, không đổi gì
# Mẫu: cay_chay_lai.sh (lần chạy 2 đến 4, 9/11). Lần chạy 6 = lần chạy đầu tiên dùng phương pháp mới.
set -euo pipefail
C=~/storage/downloads/CoVua
TD=~/.fz_tk/.cv_tu_dong
LAN=5                                   # số hiệu lần chạy đang cất
DOI=$(cat "$C/cay/doi.txt" 2>/dev/null || echo "?")
CU=$C/cay_lan${LAN}_doi$((DOI - 1))     # doi.txt = đời đang làm, nên đời cuối đã xong là DOI - 1 (21 - 1 = 20)
KIEM=0; [ "${1:-}" = kiem ] && KIEM=1
lam() { if [ $KIEM = 1 ]; then echo "[kiem] $*"; else eval "$@"; fi; }

if ls $TD/w_* >/dev/null 2>&1; then echo "[!] còn cửa sổ vòng lặp đang chạy: $(ls $TD/w_*)"; exit 1; fi
[ -d "$C/cay" ] || { echo "[!] không có $C/cay"; exit 1; }
[[ "$DOI" =~ ^[0-9]+$ ]] || { echo "[!] không đọc được $C/cay/doi.txt"; exit 1; }
[ -e "$CU" ] && { echo "[!] đã có $CU"; exit 1; }
for f in gen0.pb.gz gen0.pt gen0.seed.txt; do [ -s "$C/cay/$f" ] || { echo "[!] thiếu $C/cay/$f"; exit 1; }; done
[ -f ~/cv/cay_moi.py ] && [ -f ~/cv/cay_gm.py ] || { echo "[!] chưa có ~/cv/cay_moi.py, cay_gm.py: chạy bash cv_lay_ve.sh trước"; exit 1; }
python3 -c "import sys; sys.path.insert(0, '$HOME/cv'); import cay, cay_moi, cay_gm; print('[ok] nạp được cay_moi (numpy', cay.np.__version__ + ')')"

echo "cất $C/cay -> $CU ($(du -sh "$C/cay" | cut -f1))"
lam "pkill -f 'kho.py len $C/cay ' 2>/dev/null || true"
lam "pkill -f 'cay.py don_mau' 2>/dev/null || true"
lam "mv '$C/cay' '$CU'"
lam "mkdir -p '$C/cay'"
lam "cp -p '$CU/gen0.pb.gz' '$CU/gen0.pt' '$CU/gen0.seed.txt' '$C/cay/'"
lam "echo 0 > '$C/cay/doi.txt'"
lam "touch '$C/cay/phuong_phap_moi'"
# arena: kết quả cũ của cách cây đổi tên, để vòng lặp không coi là đã làm xong
if [ -d "$C/arena" ]; then
  for f in "$C"/arena/tt_gen*_vs_cay_gen*; do
    [ -e "$f" ] || continue
    lam "mv '$f' '$C/arena/lan${LAN}_$(basename "$f")'"
  done
fi
lam "echo cay > '$TD/.cac_ben'"
lam "rm -rf '$TD'/hl_cay_* '$TD/kho_len_cay'"
lam "rm -f '$TD/dung_tay'"
echo "[xong] dữ liệu lần chạy $LAN: $CU"
echo "cay mới: $(ls "$C/cay" 2>/dev/null | tr '\n' ' ')"
echo "vòng lặp làm: $(cat "$TD/.cac_ben" 2>/dev/null)"
