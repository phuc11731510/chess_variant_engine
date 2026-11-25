#!/bin/bash
# test_tu_canh.sh -- thu cac ham TU CANH cua so huan luyen + nguong T4 theo so the (fz_lien_tuc.sh), khong can may Colab / dien thoai.
#   bash test_tu_canh.sh
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
SC=$HERE/../colab_cells
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
export TD=$T/td TAI=$T/tai
mkdir -p "$TD" "$TAI/goi"
PASS=0; FAIL=0
td_muc() { echo 1000; }
# shellcheck disable=SC1090
source "$SC/fz_lien_tuc.sh"
ck() {   # ck <mo ta> <thuc te> <mong doi>
  if [ "$2" = "$3" ]; then PASS=$((PASS + 1)); echo "  [ok] $1 = $2"; else FAIL=$((FAIL + 1)); echo "  [FAIL] $1: duoc '$2', mong '$3'"; fi
}
ghi() { printf '%s\n' "${@:2}" > "$1"; }
reset() { rm -f "$LT_THE_F" "$LT_DUNG_LAI_F" "$LT_THE_MOI_F" "$LT_LS_F" "$TAI"/goi/*; }

echo "A. cua so tu canh"
reset
ck "chua co lich su, chua co goi: 4 x (625447/4)" "$(lt_the)" "625444"
for i in $(seq 1 10); do : > "$TAI/goi/goi_$(printf %05d $i)_n7_50_8750.zip"; done     # 50 van, 8750 the = 175 the / van
ck "chua co lich su, co 10 goi (175 the / van, 1000 van / luot): the moi uoc" "$(lt_the_moi_uoc)" "175000"
ck "  -> cua so = 4 x 175000" "$(lt_the)" "700000"
ghi "$LT_THE_MOI_F" 180000 190000 200000 170000 160000
ck "lich su 5 lan (TB 180000): the moi uoc" "$(lt_the_moi_uoc)" "180000"
ck "  -> cua so" "$(lt_the)" "720000"
ghi "$LT_THE_MOI_F" 100 200 180000 190000 200000 170000 160000
ck "chi tinh $LT_NHO lan gan nhat" "$(lt_the_moi_uoc)" "180000"
ghi "$LT_DUNG_LAI_F" 3.5
ck "muc tieu 3.5 lan -> cua so" "$(lt_the)" "630000"
ghi "$LT_DUNG_LAI_F" 4
ghi "$LT_THE_MOI_F" 1000 1000 1000
ck "the moi rat it: kep duoi $LT_THE_MIN" "$(lt_the)" "$LT_THE_MIN"
ghi "$LT_THE_MOI_F" 900000 900000 900000
ck "the moi rat nhieu: kep tren $LT_THE_MAX" "$(lt_the)" "$LT_THE_MAX"
ghi "$LT_THE_F" 760000
ck "tep .lt_cua_so_the = 760000: CO DINH" "$(lt_the)" "760000"
ghi "$LT_THE_F" 50
ck "tep .lt_cua_so_the = 50 (< 100000): bo qua, tu canh" "$(lt_the)" "$LT_THE_MAX"

echo "B. it cua so chay hon -> the moi it hon -> cua so tu thu nho (so lan dung lai van ~4)"
reset
ghi "$LT_THE_MOI_F" 190000 190000 190000 190000 190000
w1=$(lt_the)
ghi "$LT_THE_MOI_F" 190000 190000 175000 175000 175000     # 3 lan sau chi con 175000 the moi
w2=$(lt_the)
ck "cua so 5 cua so (the moi 190000)" "$w1" "760000"
ck "cua so khi the moi giam ve 175000 (3/5 lan)" "$w2" "$((4 * (190000 * 2 + 175000 * 3) / 5))"
ck "so lan dung lai sau khi giam (w2 / TB the moi * 10)" "$((w2 * 10 / ((190000 * 2 + 175000 * 3) / 5)))" "40"

echo "C. nguong T4 theo cua so"
reset
ck "chua co lich su, cua so 632000: 240 + 568 + 360 giay" "$(lt_can_giay 632000)" "1168"
ck "chua co lich su, cua so 200000: duoi san -> $LT_HL_PHUT_MIN phut" "$(lt_can_giay 200000)" "$((LT_HL_PHUT_MIN * 60))"
ghi "$LT_LS_F" "200 540 600000" "200 540 600000"
ck "moi 2 lan (< 3): van dung gia tri do duoc" "$(lt_can_giay 632000)" "1168"
for i in $(seq 1 10); do echo "200 540 600000"; done > "$LT_LS_F"
ck "10 lan giong nhau, cua so 750000: 200 + 675 + 360" "$(lt_can_giay 750000)" "1235"
ck "  cua so 600000: 200 + 540 + 360" "$(lt_can_giay 600000)" "1100"
ck "  nguong TANG theo cua so (900000 > 600000)" "$([ "$(lt_can_giay 900000)" -gt "$(lt_can_giay 600000)" ] && echo tang || echo khong)" "tang"
{ for i in $(seq 1 9); do echo "200 540 600000"; done; echo "900 2000 600000"; } > "$LT_LS_F"
ck "co 1 lan ngoai le trong 10: phan vi 90% bo qua no" "$(lt_can_giay 750000)" "1235"
{ for i in $(seq 1 8); do echo "200 540 600000"; done; echo "900 2000 600000"; echo "900 2000 600000"; } > "$LT_LS_F"
ck "co 2 lan ngoai le trong 10: phan vi 90% bi keo len" "$(lt_can_giay 750000)" "$((900 + 2000 * 750000 / 600000 + 360))"
ghi "$LT_LS_F" "abc" "1 2" "-5 3 4"
ck "dong hong bi bo qua (khong du 3 lan)" "$(lt_can_giay 632000)" "1168"

echo "D. ghi lich su"
reset
for i in $(seq 1 12); do lt_ghi_lich_su 200 540 600000 "$((180000 + i))" 1; done
ck "lich su the moi giu 10 dong" "$(wc -l < "$LT_THE_MOI_F" | tr -d ' ')" "10"
ck "  dong cuoi" "$(tail -n 1 "$LT_THE_MOI_F")" "180012"
ck "lich su thoi gian giu 10 dong" "$(wc -l < "$LT_LS_F" | tr -d ' ')" "10"
lt_ghi_lich_su 999 999 600000 190000 0
ck "lan KHONG sach: the moi van ghi" "$(tail -n 1 "$LT_THE_MOI_F")" "190000"
ck "  nhung thoi gian KHONG ghi" "$(tail -n 1 "$LT_LS_F")" "200 540 600000"

echo
echo "KET QUA: $PASS pass, $FAIL fail"
[ "$FAIL" = 0 ]
