#!/bin/bash
# Test of tom_tat_tk() in scripts/colab_cells/menu.sh -- the account summary of menu item a (2026-11-20): fake accounts,
# the right count for every kind, ONE python call for the whole list, no network.
# Linux / WSL / Termux:   bash python/test_menu_tom_tat.sh      (exit code 0 = all checks passed)
set -u
CELLS="$(cd "$(dirname "$0")/../scripts/colab_cells" && pwd)"
N=$(mktemp -d); tr -d '\r' < "$CELLS/menu.sh" > "$N/menu.sh"      # a Windows checkout has CRLF line ends
bash -n "$N/menu.sh" && echo "[ok] menu.sh: bash syntax"
T=$(mktemp -d); export HOME=$T/home; TKG=$T/tk; mkdir -p "$HOME" "$TKG"
cp "$CELLS/fz_tu_dong.py" "$HOME/"
now=$(date +%s)
mk() {   # name  snapshot-json|none  login|nologin
  mkdir -p "$TKG/$1/.config/colab-cli"
  [ "$2" != none ] && echo "$2" > "$TKG/$1/.config/colab-cli/fz_han_muc.json"
  [ "$3" = login ] && echo '{}' > "$TKG/$1/.config/colab-cli/token.json"
}
# green: 5 and 6 CCU left (~4.7 and ~5.6 hours of T4), refill in the future
mk a1 "{\"luc\": $now, \"con\": 5000, \"nap_lai\": $((now+36000)), \"tieu\": 1.07, \"so_may\": 0}" login
mk a2 "{\"luc\": $now, \"con\": 6000, \"nap_lai\": $((now+36000)), \"tieu\": 1.07, \"so_may\": 0}" login
# refill time already passed since the snapshot
mk a3 "{\"luc\": $((now-90000)), \"con\": 100, \"nap_lai\": $((now-3600)), \"tieu\": 1.07, \"so_may\": 0}" login
# little left (0.5 CCU < 1 h 15 of T4)
mk a4 "{\"luc\": $now, \"con\": 500, \"nap_lai\": $((now+36000)), \"tieu\": 1.07, \"so_may\": 0}" login
mk a5 none login          # logged in, never snapshotted
mk a6 none nologin        # not logged in
echo '{"endpoint": "x"}' > "$TKG/a1/.config/colab-cli/sessions.json"                 # a1 holds a machine
mkdir -p "$HOME/.config/colab-cli"; echo '{}' > "$HOME/.config/colab-cli/token.json"   # the main account: logged in, no snapshot

M_DAM= M_XANH= M_VANG= M_DO= M_LAM= M_MO= M_HET=
TK=a2
ten_tk() { if [ -n "$1" ]; then echo "$1"; else echo chinh; fi; }
python() { python3 "$@"; }
tk_dang_nhap() { [ -f "$([ -n "$1" ] && echo "$TKG/$1" || echo "$HOME")/.config/colab-cli/token.json" ]; }
tk_co_phien() { local f; f="$([ -n "$1" ] && echo "$TKG/$1" || echo "$HOME")/.config/colab-cli/sessions.json"; [ -s "$f" ] && grep -q '"endpoint"' "$f" 2>/dev/null; }
eval "$(sed -n '/^tom_tat_tk() {/,/^}/p' "$N/menu.sh")"
ds=("" a1 a2 a3 a4 a5 a6)
s=$(date +%s.%N)
out=$(tom_tat_tk)
e=$(date +%s.%N)
echo "$out"
fail=0
chk() { if grep -q "$1" <<<"$out"; then echo "[ok] $2"; else echo "[FAIL] $2"; fail=1; fi; }
chk "7 tài khoản" "7 accounts in all"
chk "2  còn đủ hạn mức" "2 green (a1, a2)"
chk "1  đã tới giờ nạp lại" "1 past its refill time (a3)"
chk "1  còn ít / hết, chờ giờ nạp" "1 with little left (a4)"
chk "2  chưa chụp hạn mức" "2 never snapshotted (a5 and the main account)"
chk "1  đang giữ máy" "1 holding a machine (a1)"
chk "1  chưa đăng nhập" "1 not logged in (a6)"
chk "không hỏi mạng" "says it did not ask the network"
dt=$(echo "$e - $s" | bc 2>/dev/null || echo 0)
echo "time: ${dt} s"
rm -rf "$T" "$N"
exit $fail
