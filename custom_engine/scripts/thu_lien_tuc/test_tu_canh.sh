#!/bin/bash
# test_tu_canh.sh -- thu cac ham TU CANH cua so huan luyen + nguong T4 theo so the (fz_lien_tuc.sh), khong can may Colab / dien thoai.
#   bash test_tu_canh.sh
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
SC=$HERE/../colab_cells
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
export TD=$T/td TAI=$T/tai HOME=$T/home
mkdir -p "$TD" "$TAI/goi" "$HOME"
ln -s "$SC/fz_tu_dong.py" "$HOME/fz_tu_dong.py"            # cua so tu canh goi `python ~/fz_tu_dong.py cua_so_luot`
command -v python >/dev/null || python() { python3 "$@"; }
export LT_THE_MIN=1000                                       # goi gia nho: khong de san 300000 keo them goi
PASS=0; FAIL=0
td_muc() { echo 1000; }
td_cac_cua_so() { :; }                                       # khong co cua so nao dang cho gui van
# shellcheck disable=SC1090
source "$SC/fz_lien_tuc.sh"
ck() {   # ck <mo ta> <thuc te> <mong doi>
  if [ "$2" = "$3" ]; then PASS=$((PASS + 1)); echo "  [ok] $1 = $2"; else FAIL=$((FAIL + 1)); echo "  [FAIL] $1: duoc '$2', mong '$3'"; fi
}
ghi() { printf '%s\n' "${@:2}" > "$1"; }
reset() { rm -f "$LT_THE_F" "$LT_DUNG_LAI_F" "$LT_THE_MOI_F" "$LT_LS_F" "$LT_MOC_F" "$LT_MOC_LS_F" "$TAI"/goi/*; LT_MOC_CU=; }
SEQ=0
them_goi() { local i; for i in $(seq 1 "$1"); do SEQ=$((SEQ + 1)); : > "$TAI/goi/goi_$(printf %05d $SEQ)_n7_10_${2:-1800}.zip"; done; }   # $1 goi, moi goi 10 van, $2 the

echo "A. cua so tu canh = goi cua 4 luot gan nhat"
reset; SEQ=0
them_goi 3 1700; them_goi 3 1750; them_goi 3 1800; them_goi 5 1800     # luot A 1-3, B 4-6, C 7-9 (xong), D 10-14 (dang chay)
ghi "$LT_MOC_F" 9; ghi "$LT_MOC_LS_F" 3 6 9; ghi "$LT_THE_MOI_F" 5100 5250 5400
ck "moc cac luot (moi nhat truoc)" "$(lt_moc_ls)" "9,6,3"
ck "the moi cac luot (moi nhat truoc)" "$(lt_the_ls)" "5400,5250,5100"
ck "cua so 4 luot (moc 0 uoc tu the moi luot A): ca 14 goi" "$(lt_the)" "$((3 * 1700 + 3 * 1750 + 8 * 1800))"
ghi "$LT_DUNG_LAI_F" 3
ck "muc tieu 3 lan: goi 4-14" "$(lt_the)" "$((3 * 1750 + 8 * 1800))"
ck "  danh sach goi" "$(lt_cua_so_luot 0 | grep -c '^GOI ')" "11"
ck "  moc tren 12 (goi 13, 14 den sau luc gom): 9 goi" "$(lt_cua_so_luot 0 12 | grep -c '^GOI ')" "9"
ghi "$LT_DUNG_LAI_F" 4
LT_MOC_CU=9; ghi "$LT_MOC_F" 14                               # luot D da gom xong: .lt_moc doi ngay, cua so van tinh tu moc luc bat dau
ck "trong luot dang chay: dung LT_MOC_CU" "$(lt_moc_ls)" "9,6,3"
LT_MOC_CU=
lt_moc_ls_ghi 14
ck "luot D thanh cong: ghi moc 14" "$(lt_moc_ls)" "14,9,6,3"
for m in $(seq 15 40); do lt_moc_ls_ghi "$m"; done
ck "lich su moc giu 20 dong" "$(wc -l < "$LT_MOC_LS_F" | tr -d ' ')" "20"
lt_moc_ls_ghi 30
ck "ghi moc nho hon moc cuoi (luot cu tra lai): bo cac moc lon hon" "$(tail -n 1 "$LT_MOC_LS_F")" "30"
ghi "$LT_THE_F" 760000
ck "tep .lt_cua_so_the = 760000: CO DINH" "$(lt_the)" "760000"
ghi "$LT_THE_F" 50
ghi "$LT_MOC_F" 9; ghi "$LT_MOC_LS_F" 3 6 9
ck "tep .lt_cua_so_the = 50 (< 100000): bo qua, tu canh" "$(lt_the)" "$((3 * 1700 + 3 * 1750 + 8 * 1800))"

echo "B. so cua so tang / giam DOT NGOT: moi goi vao DUNG 4 cua so huan luyen"
reset; SEQ=0
declare -A dem=()
moc=0
tre=0
for n in 3 3 3 3 6 6 1 1 8 2 2 5 1 4 4 4; do                  # so goi moi luot (so cua so dang chay doi lien tuc)
  them_goi "$n" $((1500 + 100 * n))
  LT_MOC_CU=$moc
  read -r _ tm ms <<<"$(lt_goi_moi "$moc")"                    # gom xong: moc moi = goi cuoi hien co
  ghi "$LT_MOC_F" "$ms"
  [ $((n % 3)) = 0 ] && { them_goi 1 1234; tre=$((tre + 1)); }   # mot goi den SAU luc gom (truoc khi tai cua so len may): thuoc luot SAU
  for g in $(lt_cua_so_luot 0 "$(lt_moc)" | sed -n 's/^GOI goi_\([0-9]*\)_.*/\1/p'); do dem[$((10#$g))]=$(( ${dem[$((10#$g))]:-0} + 1 )); done
  lt_ghi_lich_su 200 540 1 "$tm" 1; lt_moc_ls_ghi "$ms"; moc=$ms; LT_MOC_CU=
done
sai=""
for g in $(seq 1 $((SEQ - 12))); do [ "${dem[$g]:-0}" = 4 ] || sai="$sai $g:${dem[$g]:-0}"; done    # bo 12 goi cua 3 luot cuoi (4+4+4: chua het 4 luot)
ck "moi goi (tru 3 luot cuoi) vao dung 4 cua so" "${sai:-het}" "het"

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
