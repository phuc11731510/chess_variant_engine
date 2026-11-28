#!/bin/bash
# Test of scripts/colab_cells/fz_nap_som.sh (menu fz -> n, 2026-11-28): which accounts one round takes (only "nap_lai" ones that no loop
# window, no WSL borrow, no running request and no live session holds), that it rents, snapshots and returns the machine, that it does
# nothing while a loop window waits for a machine, and that it leaves no lock / no account mark behind. Colab is faked: no network.
# Linux / WSL / Termux:   bash python/test_fz_nap_som.sh      (exit code 0 = all checks passed)
set -u
CELLS="$(cd "$(dirname "$0")/../scripts/colab_cells" && pwd)"
N=$(mktemp -d)
for f in menu.sh fz_tu_dong.sh fz_nap_som.sh; do tr -d '\r' < "$CELLS/$f" > "$N/$f"; done
PASS=0; FAIL=0
check() { if eval "$1"; then PASS=$((PASS + 1)); echo "  [ok] $2"; else FAIL=$((FAIL + 1)); echo "  [FAIL] $2"; fi; }
bash -n "$N/fz_nap_som.sh" && bash -n "$N/menu.sh"; check '[ $? = 0 ]' "bash syntax of fz_nap_som.sh and menu.sh"

T=$(mktemp -d); export HOME=$T/home; TKG=$HOME/.fz_tk; TD=$TKG/.tu_dong; CS=$TKG/.cua_so; mkdir -p "$TD" "$CS"
tr -d '\r' < "$CELLS/fz_tu_dong.py" > "$HOME/fz_tu_dong.py"
now=$(date +%s)
mk() {   # name  snapshot-json
  mkdir -p "$TKG/$1/.config/colab-cli"
  echo "$2" > "$TKG/$1/.config/colab-cli/fz_han_muc.json"
  echo '{}' > "$TKG/$1/.config/colab-cli/token.json"
}
DUE="{\"luc\": $((now - 90000)), \"con\": 100, \"nap_lai\": $((now - 600)), \"tieu\": 1.07, \"so_may\": 0}"
mk b1 "$DUE"                                   # due and free: must be taken
mk b2 "$DUE"; date +%s > "$TD/may_b2"         # the loop holds a machine there
mk b3 "$DUE"                                   # open in another (live) window
mk b4 "$DUE"; date +%s > "$TD/khoa_ngoai_b4"  # borrowed by WSL (chay_t4_thu.py)
mk b5 "{\"luc\": $now, \"con\": 9000, \"nap_lai\": $((now + 36000)), \"tieu\": 1.07, \"so_may\": 0}"   # green: not due
mk b6 "$DUE"; echo "[fz] ep6 T4" > "$TKG/b6/sess"                                                # holds a session
bash -c 'exec -a menu.sh sleep 300' & OTHER=$!                  # a live "menu.sh" window that has b3 open
sleep 0.2; echo "@b3:fz" > "$CS/$OTHER"

# Fakes of what touches Colab / the phone's other tools.
LOG=$T/calls
M_DAM= M_XANH= M_VANG= M_DO= M_LAM= M_MO= M_HET=; NGAT=0; S=fz; TK=
python() { python3 "$@"; }
colab() {                                                      # sessions of the account set by dat_tk ($TKH)
  case "$1" in sessions) cat "$TKH/sess" 2>/dev/null ;; *) : ;; esac
}
xin_may() { echo "xin $(basename "$TKH") $1 $S" >> "$LOG"; echo "[$S] ep_$(basename "$TKH") T4" > "$TKH/sess"; }
tra_mot() { echo "tra $(basename "$TKH") $1" >> "$LOG"; rm -f "$TKH/sess"; }
chup_han_muc() {
  echo "chup $1" >> "$LOG"
  echo "{\"luc\": $(date +%s), \"con\": 15000, \"nap_lai\": $(( $(date +%s) + 86400 )), \"tieu\": 1.07, \"so_may\": 1}" \
    > "$TKG/$1/.config/colab-cli/fz_han_muc.json"
}
dong_han_muc() { python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print('con', d['con'], 'nap', d['nap_lai'])" \
                   "$TKG/$1/.config/colab-cli/fz_han_muc.json"; }
td_token_ok() { return 0; }
bat_ctrl_c() { :; }
for fn in dat_tk ten_chinh ten_tk tk_hop_le tim_tk ghi_cua_so cua_so_khac khoa_ngoai_con_han tk_dang_nhap; do
  eval "$(sed -n "/^$fn() {/,/^}/p; /^$fn() { .*}$/p" "$N/menu.sh")"
done
for fn in td_in td_home td_song td_ranh td_ds_tk td_mo_khoa_chon; do
  eval "$(sed -n "/^$fn() {/,/^}/p; /^$fn() { .*}$/p" "$N/fz_tu_dong.sh")"
done
source "$N/fz_nap_som.sh"
for fn in dat_tk tim_tk cua_so_khac td_ranh td_ds_tk ns_nhan ns_mot_luot; do declare -F $fn >/dev/null; check '[ $? = 0 ]' "$fn defined"; done

echo "[1] one round with no loop window waiting"
: > "$LOG"
ns_mot_luot > "$T/out1" 2>&1
cat "$T/out1" | sed 's/^/    /'
check 'grep -qx "xin b1 T4 fznap" "$LOG"' "b1 (due, free): a T4 is asked for, under the session name fznap"
check 'grep -q "^chup b1" "$LOG" && grep -q "^tra b1" "$LOG"' "...its quota is snapshotted while holding it, then it is returned"
check '[ ! -f "$TKG/b1/sess" ]' "...and no session of b1 is left"
check '[ "$(python3 -c "import json; print(json.load(open(\"$TKG/b1/.config/colab-cli/fz_han_muc.json\"))[\"luc\"] >= $now)")" = True ]' \
      "...b1's snapshot is new (no longer 'nap_lai' for the loop)"
for b in b2 b3 b4 b5 b6; do check '! grep -q " $b " "$LOG"' "$b is not touched"; done
check 'grep -q "bỏ qua b2: vòng lặp đang giữ máy" "$T/out1" && grep -q "bỏ qua b3: đang mở ở cửa sổ khác" "$T/out1" &&
       grep -q "bỏ qua b4: máy khác (WSL)" "$T/out1" && grep -q "bỏ qua b6: đang giữ máy" "$T/out1"' "the reasons are printed"
check '[ ! -d "$TD/.khoa_chon" ]' "the shared account lock is released"
check '[ "$(cat "$CS/$$")" = "@/:fznap" ]' "this window holds no account afterwards"
check 'grep -q "\[nạp sớm\] đã nạp sớm b1" "$TD/nhat_ky.txt" && grep -q "\[nạp sớm\] lượt này nạp sớm 1 / 5" "$TD/nhat_ky.txt"' \
      "the loop journal gets the before / after lines and the round's count"

echo "[2] a second round: nothing due any more"
: > "$LOG"
ns_mot_luot > "$T/out2" 2>&1
check '! grep -q "^xin" "$LOG"' "b1 is not taken twice (its new snapshot is after the refill time)"

echo "[3] a loop window waiting for a machine"
mk b7 "$DUE"
bash -c 'exec -a menu.sh sleep 300' & WAIT=$!
sleep 0.2; printf 'buoc=xin\n' > "$TD/w_$WAIT"
: > "$LOG"
ns_mot_luot > "$T/out3" 2>&1
check '! grep -q "^xin" "$LOG" && grep -q "đang chờ máy" "$T/out3"' "nothing is taken: the waiting window will ask for b7 itself"
kill "$WAIT" 2>/dev/null; wait "$WAIT" 2>/dev/null
ns_mot_luot > "$T/out4" 2>&1
check 'grep -qx "xin b7 T4 fznap" "$LOG"' "once that window is gone, b7 is taken"

kill "$OTHER" 2>/dev/null
rm -rf "$T" "$N"
echo "RESULT: $PASS passed, $FAIL failed"
[ $FAIL = 0 ]
