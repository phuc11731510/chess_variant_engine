# Danh sách quân cờ tiên (fairy chess) theo ký hiệu Betza

Nguồn: [List of fairy chess pieces — Wikipedia](https://en.wikipedia.org/wiki/List_of_fairy_chess_pieces) (cột **Betza**, lấy ngày 2026-11-07). Ký hiệu được giữ nguyên như Wikipedia ghi, kể cả các dạng tương đương (ví dụ `B = FF`, `A = (2,2)`). **Ngoại lệ:** ký hiệu của 15 quân đã được sửa theo quy ước chữ hướng ở mục 4 và định nghĩa `t[...]` ở mục 6 (Cannon (Musketeer), Debtor, Fibnif, Fortress (Musketeer); bỏ chữ `h` ở Charging Knight, Colonel, Forequeen; bỏ dạng viết thứ hai của Horned Falcon và Soaring Eagle; `lr` thành `s` ở Golden Bird; Ship và Twin Tower đổi `t[FvR]` thành `t[fFfR]t[bFbR]`; Unicornio bỏ dạng thay thế `t[NfB]`; tách thành phần `Q`, `K` có cụm hai chữ hướng thành `sbWbF` ở Charging Knight, `fsRfB` ở Forequeen, `sfWfF` ở Evil Wolf và Pawn (Jetan)), và 21 mục dùng `[cl]` đã đổi sang `[cj]` theo mục 5 (Sri Lankan Dām còn được thêm chữ `f` bị thiếu). Ký hiệu gốc của Wikipedia ghi ở mục 4.2 và 5.4.

- Có **412 mục** (quân/biến thể theo từng trò chơi) có ký hiệu Betza; các mục chưa có ký hiệu Betza (như Zigzag Nightrider, các quân Dragonchess, Chameleon, Duck…) đã bị bỏ qua.
- Có **57 ký hiệu bị nhiều quân dùng chung** (đã gộp cả dạng tương đương như `B` = `FF`); mỗi nhóm được giải thích ở phần 2.
- Mục "Spy" của Wikipedia ghi 3 ký hiệu cho 3 trò chơi nên được tách thành 3 dòng.

## Ký hiệu Betza trong 1 phút

| Ký hiệu | Ý nghĩa |
|---|---|
| `W` | Wazir: 1 ô ngang/dọc |
| `F` | Ferz: 1 ô chéo |
| `D` | Dabbaba: nhảy 2 ô ngang/dọc |
| `A` | Alfil: nhảy 2 ô chéo |
| `H` | Threeleaper: nhảy 3 ô ngang/dọc |
| `G` | Tripper: nhảy 3 ô chéo |
| `N` | Mã (1,2) |
| `C` / `L` | Camel (1,3) |
| `Z` / `J` | Zebra (2,3) |
| `(a,b)` | Leaper tổng quát |
| `R`, `B`, `Q`, `K` | Xe, Tượng, Hậu, Vua (`R = WW`, `B = FF`, `Q = RB`, `K = WF`) |
| chữ lặp hoặc số (`NN`, `W3`) | Lặp nước đi theo cùng hướng (rider); số giới hạn số ô |
| `m` / `c` | Chỉ đi / chỉ ăn |
| `f` `b` `s` `v` `l` `r` | Tiến / lùi / ngang / dọc / trái / phải |
| `n` | Không nhảy qua (bị cản chân, như Mã cờ tướng) |
| `p` / `g` | Nhảy qua đúng 1 quân (pháo) / nhảy rồi đáp ngay sau quân chắn (grasshopper) |
| `i` | Chỉ ở nước đầu |
| `t[...]` | Nước đi hai chặng theo cách Wikipedia dùng (bước ban đầu rồi trượt "ra xa") |
| `[cj]` | Bex: bắt quân bằng cách nhảy qua đúng một quân, có mở rộng tham số hạ cánh; định nghĩa ở mục 5 |
| `[cl]` | Bex: bắt quân bằng cách nhảy qua nhiều quân (Long Leaper); định nghĩa ở mục 5.3 |

Chi tiết đầy đủ: [Betza's funny notation](https://en.wikipedia.org/wiki/Betza%27s_funny_notation).

## 1. Bảng quân cờ và ký hiệu Betza (A–Z)

| Quân cờ | Betza | Trùng ký hiệu |
|---|---|---|
| Aanca | `t[FR]` | [Nhóm 1](#g1) |
| Abbot | `F4N` |  |
| Ace | `QC` |  |
| Acropolis | `RNC = RNL` |  |
| Actor | `BNC = BNL` |  |
| Actress | `QNC = QNL` |  |
| Admiral | `RF` | [Nhóm 2](#g2) |
| Advisor | `F` | [Nhóm 3](#g3) |
| Alfil | `A = (2,2)` | [Nhóm 4](#g4) |
| Alfilrider | `AA` |  |
| Alibaba | `AD` |  |
| Alibabarider | `AADD` |  |
| Amazon | `QN` | [Nhóm 5](#g5) |
| Amazonrider | `QNN` | [Nhóm 6](#g6) |
| Anchorite | `t[WB]` | [Nhóm 7](#g7) |
| Ancress | `Rt[WB]` |  |
| Angry Boar | `(0,1)` | [Nhóm 8](#g8) |
| Antelope | `(3,4)` |  |
| Anti-King | `K (captures friendly, not enemy pieces)` |  |
| Archbishop | `BN` | [Nhóm 9](#g9) |
| Archbishop (Fox-Dawson) | `B (bounce one edge)` |  |
| Archchancellor | `RNF` | [Nhóm 10](#g10) |
| Archer | `FA` | [Nhóm 11](#g11) |
| Archer (Modern) | `mBcpB` | [Nhóm 12](#g12) |
| Arrow (Duniho) | `mBcpB` | [Nhóm 12](#g12) |
| Arrow Pawn (Persson) | `mW2cF` |  |
| Assassin | `WFcAcD` |  |
| Astrologer | `t[CB]=t[LB]` |  |
| Atlantosaur | `cWcF` |  |
| Auroch | `N(1,4)` |  |
| B4nD | `B4nD` |  |
| Banshee | `BNN` | [Nhóm 13](#g13) |
| Barc | `fsNbbN` |  |
| Basilisk (Dragonchess) | `mfFfbWcfK` |  |
| Bear | `NAD` | [Nhóm 14](#g14) |
| Bede | `BD` |  |
| Berolina Pawn | `mfFcefWimfnA` |  |
| Berolina Plus Pawn | `mfFcfWcsWimfF2` |  |
| Biok | `mBcR` | [Nhóm 15](#g15) |
| Bion | `pB` |  |
| Bishight | `fBbN` |  |
| Bishop | `B = FF` | [Nhóm 16](#g16) |
| Bishop's dog | `F3` |  |
| Bishopper | `gB` |  |
| Bison | `CZ = LJ` |  |
| Blind Dog | `sbWfF` |  |
| Blind Monkey | `FsW` |  |
| Blind Tiger | `FsbW` |  |
| Boa | `zNN` |  |
| Boat | `A = (2,2)` | [Nhóm 4](#g4) |
| Bodyguard | `Q2 (Hia power)` | [Nhóm 17](#g17) |
| Boyscout | `zB` |  |
| Brontosaur | `cB` |  |
| Buffalo | `NCZ = NLJ` |  |
| Caliph | `BC = BL` | [Nhóm 18](#g18) |
| Caliph (Fairy) | `WA` | [Nhóm 19](#g19) |
| Camel | `C = L = (1,3)` | [Nhóm 20](#g20) |
| Camelrider | `CC = LL` | [Nhóm 21](#g21) |
| Cannon | `mRcpR` | [Nhóm 22](#g22) |
| Cannon (Korean) | `pR` | [Nhóm 23](#g23) |
| Cannon (Musketeer) | `DWFssN` |  |
| Canvasser | `RC = RL` |  |
| Cardinal | `BN` | [Nhóm 9](#g9) |
| Carpenter | `ND` | [Nhóm 24](#g24) |
| Castle | `NAD` | [Nhóm 14](#g14) |
| Cavalier | `t[RF]t[FR]` |  |
| Centaur | `KN` | [Nhóm 25](#g25) |
| Centaur (Carrera) | `BN` | [Nhóm 9](#g9) |
| Centurion | `NnAnD` |  |
| Champion (Begnis) | `WFD` | [Nhóm 26](#g26) |
| Champion (Carrera) | `RN` | [Nhóm 27](#g27) |
| Champion (Omega Chess) | `WAD` |  |
| Chancellor | `RN` | [Nhóm 27](#g27) |
| Charging Knight | `fNsbWbF` |  |
| Charging Rook | `fsRbK` |  |
| Chariot | `R = WW` | [Nhóm 28](#g28) |
| Checker King | `mB[cj]B` |  |
| Checker King | `mB[cj]B[cj]DD` |  |
| Checker King | `mF[cj]B` |  |
| Checker King | `mF[cj]F` |  |
| Checker King | `mK[cj]K or mQ[cj]Q` |  |
| Checker King | `mQ[cj]R` |  |
| Checker King | `mR[cj]R` |  |
| Checker Man | `mK[cj]K` |  |
| Checker Man | `mfF[cj]B` |  |
| Checker Man | `mfF[cj]F` |  |
| Checker Man | `mfF[cj]F` |  |
| Checker Man | `mfF[cj]F[cj]D` |  |
| Checker Man | `mfF[cj]fF` |  |
| Checker Man | `mfF[cj]fF[cj]fsW` |  |
| Checker Man | `mfK[cj]K` |  |
| Checker Man | `mfK[cj]fsW` |  |
| Checker Man | `mfKmsW[cj]fsW` |  |
| Checker Man | `mfsW[cj]fsW` |  |
| Cheetah | `CZGH = LJGH` | [Nhóm 29](#g29) |
| Chicken General | `fW4bF` |  |
| Cloud Eagle | `vRKfB3` |  |
| Cockatrice | `B` | [Nhóm 16](#g16) |
| Colonel | `KfsRfN` |  |
| Commoner | `WF` | [Nhóm 30](#g30) |
| Commuter | `(4,4)` |  |
| Congo Pawn | `fWfF (fWfFmbR2 past the river)` |  |
| Congo Superpawn | `sfWfFmbQ2` |  |
| Copper General | `fFvW` |  |
| Corporal | `fFmfWimfnD` |  |
| Counsellor | `F` | [Nhóm 3](#g3) |
| Courier | `B` | [Nhóm 16](#g16) |
| Crab | `ffNbsN` |  |
| Crocodile (Congo) | `fRbsWF or bRfsWF towards the river, sRvWF inside` |  |
| Crocodile (Modern) | `mBcpB` | [Nhóm 12](#g12) |
| Crown Princess | `BNW` | [Nhóm 31](#g31) |
| Crowned Bishop | `BW` | [Nhóm 32](#g32) |
| Crowned Rook | `RF` | [Nhóm 2](#g2) |
| Dabbaba | `D = (0,2)` |  |
| Dabbaba-checker | `D[cjmc]W` |  |
| Dabbabante | `(0,2n)` |  |
| Dabbabarider | `DD` |  |
| Dayrider | `mKAADD` |  |
| Debtor | `vDssN` |  |
| Dinosaur | `cQ` |  |
| Direwolf | `ANDHCZG=ANDHLJG` |  |
| Dog | `fWbF` |  |
| Dolphin | `R3mDmH` |  |
| Donkey | `sWfbD` |  |
| Dragon | `NmfWcfFimfnD` |  |
| Dragon Horse | `BW` | [Nhóm 32](#g32) |
| Dragon King | `RF` | [Nhóm 2](#g2) |
| Drunk Elephant | `FsfW` |  |
| Drunken Soldier | `sfW` | [Nhóm 33](#g33) |
| Duchess | `(1,1)(0,1)(2,2)(0,2)(3,3)(0,3) = KADGH = WFADGH` |  |
| Duke | `t[BW]t[WB]` |  |
| Duke (Jelliss) | `FD` | [Nhóm 34](#g34) |
| Duke (Musketeer chess) | `WDN` | [Nhóm 35](#g35) |
| Dullahan | `FN` | [Nhóm 36](#g36) |
| Dwarf (Dragonchess) | `msfWcfF` |  |
| Eagle | `fBbRWbB2` |  |
| Eagle | `t[FR]` | [Nhóm 1](#g1) |
| Edgehog | `Q (edges)` |  |
| Edgehog (Limited) | `Q (see notes)` |  |
| Elephant (Chinese) | `nA` |  |
| Elephant (Ciccolini) | `Z = J = (2,3)` | [Nhóm 37](#g37) |
| Elephant (Indian) | `FfW` | [Nhóm 38](#g38) |
| Elephant (Korean) | `t[WnA]` |  |
| Elephant (Modern) | `FA` | [Nhóm 11](#g11) |
| Elephant (Musketeer) | `KAD = WFAD` | [Nhóm 39](#g39) |
| Elephant (Persian) | `A = (2,2)` | [Nhóm 4](#g4) |
| Elephant (von Wilpert) | `QNN` | [Nhóm 6](#g6) |
| Emperor | `WN` | [Nhóm 40](#g40) |
| Empress | `RN` | [Nhóm 27](#g27) |
| Ensign | `mBcR` | [Nhóm 15](#g15) |
| Evil Wolf | `sfWfF` | [Nhóm 41](#g41) |
| FAD | `FAD` |  |
| Falafel | `FA` | [Nhóm 11](#g11) |
| Falcon | `fBbR` |  |
| Falcon (Falcon Chess) | `nCnZ = nLnJ` |  |
| Falcon (Falconry) | `CB3` |  |
| Faro | `cRmpR` |  |
| Ferfil | `FA` | [Nhóm 11](#g11) |
| Ferocious Leopard | `FvW` |  |
| Ferz | `F = (1,1)` | [Nhóm 3](#g3) |
| Fibnif | `vvNF` |  |
| Fiveleaper | `(0,5)(3,4)` | [Nhóm 42](#g42) |
| Flamingo | `(1,6)` |  |
| Flying Cock | `sWfF` |  |
| Flying Dragon | `B2` |  |
| Flying Dragon (Ganymede) | `BC = BL` | [Nhóm 18](#g18) |
| Flying Falcon | `BfW` |  |
| Flying Horse | `WnfA` |  |
| Flying Kingfisher | `KAADD = WFAADD` |  |
| Flying Ox | `vRB` |  |
| Flying Stag | `vRK` |  |
| Fool | `W = (0,1)` | [Nhóm 8](#g8) |
| Forequeen | `fsRfBbNbK` |  |
| Forfer | `FR4` |  |
| Fortress | `FD` | [Nhóm 34](#g34) |
| Fortress (Musketeer) | `F3DvvN` |  |
| Fourleaper | `(0,4)` |  |
| Free Bear | `sRBfA` |  |
| Free Boar | `sRB` |  |
| Free Gold | `RfB` |  |
| Free King | `Q = RB` | [Nhóm 43](#g43) |
| Free Silver | `BfR` |  |
| Frog | `FH` |  |
| Fusilier | `mWcF` | [Nhóm 44](#g44) |
| General (Chess.com) | `KN` | [Nhóm 25](#g25) |
| General (Chinese) | `kW, "Flying General": cfR (against enemy General)` |  |
| General (Ciccolini) | `BDD` |  |
| General (Paulovits) | `KC = KL = WFC` | [Nhóm 45](#g45) |
| Giraffe (Congo) | `ADmK` |  |
| Giraffe (Giraffe Chess) | `C = L = (1,3)` | [Nhóm 20](#g20) |
| Giraffe (Modern) | `(1,4)` |  |
| Giraffe (Zaraffa) | `Z = J = (2,3)` | [Nhóm 37](#g37) |
| Giraffe (Zurafa) | `t[(1,4)R]` |  |
| Girlscout | `zR` |  |
| Gliding Swallow | `R = WW` | [Nhóm 28](#g28) |
| Gnu | `NC = NL` | [Nhóm 46](#g46) |
| Gnurider | `NNCC = NNLL` |  |
| Go-Between | `vW` |  |
| Go-between (Chinese) | `mQ` | [Nhóm 47](#g47) |
| Godzilla | `t[FR]t[WB]` |  |
| Gold General | `WfF` |  |
| Golden Bird | `vRsW2F3` |  |
| Goose | `fAbD` |  |
| Gorilla | `FWC` | [Nhóm 45](#g45) |
| Grasshopper | `gQ` |  |
| Graz Pawn | `fKimfnDimfnA` |  |
| Great Horse | `fBvRsW2` |  |
| Gryphon | `t[FR]` | [Nhóm 1](#g1) |
| Guard | `WF (=K)` | [Nhóm 30](#g30) |
| Guard | `mRcB` | [Nhóm 48](#g48) |
| Half-Duck | `HFD` |  |
| Hare | `(2,4)` | [Nhóm 49](#g49) |
| Harvester | `Bt[WB]` |  |
| Hawk | `(2,2)(0,2)(3,3)(0,3) = ADGH` |  |
| Heavenly Horse | `ffbbN` |  |
| Heavenly Tetrarch | `Q4` |  |
| Heroine | `RNF` | [Nhóm 10](#g10) |
| Hia | `Q2 (Hia power)` | [Nhóm 17](#g17) |
| High Priestess | `FAN` |  |
| Hippopotamus | `cN` |  |
| Hobbit | `mWcF` | [Nhóm 44](#g44) |
| Horned Falcon | `BsbRfWfD` |  |
| Horse | `t[WF]` |  |
| Hospitaller | `NA` | [Nhóm 50](#g50) |
| Howling Dog | `fRbW` |  |
| Hunter | `fRbB` |  |
| Ibis | `(1,5)` |  |
| Immobilizer | `mQ (Immo-K)` |  |
| Impala | `N(3,4)` |  |
| Iron General | `fK` |  |
| Jester (Brybelly) | `mQ` | [Nhóm 47](#g47) |
| Joker | `KAND = WFAND` | [Nhóm 51](#g51) |
| Judge | `KN` | [Nhóm 25](#g25) |
| Kangaroo | `NA` | [Nhóm 50](#g50) |
| Khon | `FfW` | [Nhóm 38](#g38) |
| King | `K = WF` | [Nhóm 30](#g30) |
| Kirin | `FD` | [Nhóm 34](#g34) |
| Knave | `sDffbbN` |  |
| Kneen | `mNcQ` |  |
| Knight | `N = (1,2)` |  |
| Knight (Japanese) | `ffN` |  |
| Knishop | `fNbB` |  |
| Lance | `fR` |  |
| Lancer | `(2,4)` | [Nhóm 49](#g49) |
| Left General | `FvrW` |  |
| Left Quail | `fRbrBblF` |  |
| Leo | `mQcpQ` | [Nhóm 52](#g52) |
| Leon | `CH = LH` |  |
| Leopard (Musketeer) | `NB2` |  |
| Liberated Horse | `fRbR2` |  |
| Lion (Fairy) | `pQ` |  |
| Lion (Japanese) | `KANDcaKmabK` |  |
| Lion (Modern) | `KAND = WFAND` | [Nhóm 51](#g51) |
| Lion (Murray) | `ADcK` |  |
| Lion Dog | `Q3` |  |
| Llama | `CmfWcfFimfW2` |  |
| Loco | `cBmpB` |  |
| Locust | `mQ[cj1]Q` |  |
| Machine | `WD` | [Nhóm 53](#g53) |
| Maharaja | `QN` | [Nhóm 5](#g5) |
| Mammoth | `cR` |  |
| Mammoth (Winther) | `KAD = WFAD` | [Nhóm 39](#g39) |
| Mann | `WF = K` | [Nhóm 30](#g30) |
| Manticore | `t[WB]` | [Nhóm 7](#g7) |
| Mao | `nN` | [Nhóm 54](#g54) |
| Marquis | `WN` | [Nhóm 40](#g40) |
| Marshal | `RN` | [Nhóm 27](#g27) |
| Mastodon | `KAD = WFAD` | [Nhóm 39](#g39) |
| Megasaur | `cQcN` |  |
| Mehari | `CC = LL` | [Nhóm 21](#g21) |
| Metropolitan | `Bt[FR]` |  |
| Minister | `WDN` | [Nhóm 35](#g35) |
| Minister (G.Vicente Maura) | `BN` | [Nhóm 9](#g9) |
| Minister (Shatranj) | `F = (1,1)` | [Nhóm 3](#g3) |
| Missionary | `BW` | [Nhóm 32](#g32) |
| Moa | `nN` | [Nhóm 54](#g54) |
| N2R4 | `N2R4` |  |
| Nao | `mNNcpNN` |  |
| Newt | `AH` |  |
| Nightrider | `NN` |  |
| Nightriderhopper | `gNN` |  |
| Okapi | `NZ = NJ` |  |
| Old Monkey | `FbW` |  |
| Osprey | `t[DB]` |  |
| Ostrich | `t[AR]` |  |
| Paladin | `BN` | [Nhóm 9](#g9) |
| Paladin | `KN` | [Nhóm 25](#g25) |
| Pancake | `pNNK` |  |
| Pao | `mRcpR` | [Nhóm 22](#g22) |
| Pasha | `KAD = WFAD` | [Nhóm 39](#g39) |
| Pawn | `mfWcefFimfnD` |  |
| Pawn (Chinese) | `fW; fsW (after crossing the river)` |  |
| Pawn (Hiashatar) | `mfWcfFimfW3` |  |
| Pawn (Japanese) | `fW` |  |
| Pawn (Jetan) | `sfWfF` | [Nhóm 41](#g41) |
| Pawn (Korean) | `sfW` | [Nhóm 33](#g33) |
| Pawn (Shatranj) Pawn of piece(s) | `mfWcfF` |  |
| Pawn (Torpedo) | `mfW2cefF` |  |
| Pegasus | `NNgQ` |  |
| Pegasus (Beastmaster) | `Z(1,4) = J(1,4)` |  |
| Pegasus (Zacharias) | `t[NR]` |  |
| Pheasant | `fDbF` |  |
| Phoenix | `WA` | [Nhóm 19](#g19) |
| Popess | `BNW` | [Nhóm 31](#g31) |
| Priest | `FN` | [Nhóm 36](#g36) |
| Priestess | `NA` | [Nhóm 50](#g50) |
| Prince | `WF = K` | [Nhóm 30](#g30) |
| Prince (Fairy) | `FN` | [Nhóm 36](#g36) |
| Prince (Modern) | `WFmfW2` |  |
| Prince (The Ouroboros King) | `WF = K` | [Nhóm 30](#g30) |
| Prince Elephant (Betza) | `WFA` |  |
| Princess | `BN` | [Nhóm 9](#g9) |
| Princess (CEO) | `W2F2 = Q2` |  |
| Pterodactyl | `(3,3)(5,5)(0,15)` |  |
| Quadrapawn | `mWcF` | [Nhóm 44](#g44) |
| Quartermaster | `K = WF` | [Nhóm 30](#g30) |
| Queen | `Q = RB` | [Nhóm 43](#g43) |
| Queen of the Night | `QNN` | [Nhóm 6](#g6) |
| Quight | `mQcN` |  |
| Raiding Falcon | `vRWfF` |  |
| Raven | `RNN` | [Nhóm 55](#g55) |
| Reaper | `Rt[FR]` |  |
| Reflecting Bishop | `B (bounce edges)` |  |
| Revealer (Tamerlane) | `G = (3,3)` | [Nhóm 56](#g56) |
| Reverse Chariot | `vR` |  |
| Rhinoceros | `t[WB]` | [Nhóm 7](#g7) |
| Rhubarb | `RF3` |  |
| Right General | `FvlW` |  |
| Right Quail | `fRblBbrF` |  |
| Rion | `pR` | [Nhóm 23](#g23) |
| Roc | `AC = AL` |  |
| Rook | `R = WW` | [Nhóm 28](#g28) |
| Rook (Quang Trung) | `mR[cj1]R` |  |
| Rookhopper | `gR` |  |
| Root-25-leaper | `(0,5)(3,4)` | [Nhóm 42](#g42) |
| Root-50-leaper | `(1,7)(5,5)` |  |
| Rose | `qN` |  |
| Roshop | `mRcB` | [Nhóm 48](#g48) |
| Royal Guard | `cQmK` |  |
| Running Rabbit | `fRFbW` |  |
| Rutabaga | `W2B` |  |
| Saltador | `cnNmpN` |  |
| Scorpion | `KgQ` |  |
| Scorpion (Winther) | `mfWcefFimfnDmfsN` |  |
| Scout | `WH` |  |
| Sergeant | `fKimfnD` |  |
| Señora | `cQmpQ` |  |
| Ship | `t[fFfR]t[bFbR]` | [Nhóm 57](#g57) |
| Short Rook | `R4 = W4` |  |
| Side Mover | `WsR` |  |
| Silver General | `FfW` | [Nhóm 38](#g38) |
| Snake | `t[vWB]` |  |
| Soaring Eagle | `RbBfFfA` |  |
| Soldier (Chess.com) | `fWimfnD` |  |
| Soldier (Silberschmidt) | `mfWmsWcfF` |  |
| Sorcerer | `WZ` |  |
| Sorceress | `mQcpQ` | [Nhóm 52](#g52) |
| Spider (Musketeer) | `NDF2` |  |
| Spy (Chess Empire) | `fsDfF` |  |
| Spy (Courier Chess) | `W = (0,1)` | [Nhóm 8](#g8) |
| Spy (Waterloo, Amsterdam Medieval) | `WF = K` | [Nhóm 30](#g30) |
| Squire | `KAD = WFAD` | [Nhóm 39](#g39) |
| Squirrel | `NAD` | [Nhóm 14](#g14) |
| Stag | `(2,4)` | [Nhóm 49](#g49) |
| Steward | `mWcF` | [Nhóm 44](#g44) |
| Stone General | `fF` |  |
| Superpawn | `mfRcfB` |  |
| Templar | `ND` | [Nhóm 24](#g24) |
| Teutonic Knight | `WNC = WNL` |  |
| Threeleaper | `H = (0,3)` |  |
| Threerider | `HH` |  |
| Tiger | `t[ZB]=t[JB]` |  |
| Titan | `CZGH = LJGH` | [Nhóm 29](#g29) |
| Toad | `DH` |  |
| Treacherous Fox | `FfbWAfbD` |  |
| Tripper | `G = (3,3)` | [Nhóm 56](#g56) |
| Troll | `mfWcfFGH` |  |
| Twin Tower | `t[fFfR]t[bFbR]` | [Nhóm 57](#g57) |
| Ubi-Ubi | `NN (any direction)` |  |
| Unicorn (Grant Acedrex) | `BimN` |  |
| Unicorn (Musketeer) | `NC = NL` | [Nhóm 46](#g46) |
| Unicorn (Unicorn Chess) | `BNN` | [Nhóm 13](#g13) |
| Unicornio (Grant Acedrex) | `t[NB]` |  |
| Vanguard | `B (except F)` |  |
| Vao | `mBcpB` | [Nhóm 12](#g12) |
| Vertical Mover | `WfbR` |  |
| Violent Bear | `sWnfB2` |  |
| Violent Ox | `R2` |  |
| Vivi | `t[vWfB]` |  |
| Vouivre | `DNAC = DNAL` |  |
| Waffle | `WA` | [Nhóm 19](#g19) |
| Wallaby | `KgQ2 (over friendly pieces), KcjQ2` |  |
| War Machine | `WD` | [Nhóm 53](#g53) |
| Waran | `RNN` | [Nhóm 55](#g55) |
| Warrior | `WFD` | [Nhóm 26](#g26) |
| Wazir | `W = (0,1)` | [Nhóm 8](#g8) |
| Whale | `vRbB` |  |
| White Horse | `vRfB` |  |
| Wildebeest | `NC = NL` | [Nhóm 46](#g46) |
| Wildeguard | `KCZ = WFCZ = KLZ` |  |
| Withdrawer | `mQ[cw]Q` |  |
| Wizard | `FC = FL` |  |
| Wood General | `fB2` |  |
| Woody Rook | `WD` | [Nhóm 53](#g53) |
| Wyvern | `G(2,4)(1,5) = (3,3)(2,4)(1,5)` |  |
| Yaksha | `fFbWsW3` |  |
| Zabel Pawn | `mfWcfF final mfW2` |  |
| Zaraffa | `Z = J = (2,3)` | [Nhóm 37](#g37) |
| Zebra | `Z = J = (2,3)` | [Nhóm 37](#g37) |
| Zebrarider | `ZZ = JJ` |  |
| Zebu | `C(1,4) = L(1,4)` |  |
| Zero | `(0,0)` |  |

## 2. Các quân trùng ký hiệu Betza

Hầu hết các nhóm dưới đây chỉ là **cùng một quân có nhiều tên** (do mỗi trò chơi/tác giả đặt tên riêng); khi nước đi thật sự khác nhau thì được nêu rõ.

<a id="g1"></a>

### Nhóm 1: `t[FR]`

**Gồm:** Aanca, Eagle, Gryphon

Cùng một nước đi: bước 1 ô chéo rồi trượt như Xe theo hướng ra xa điểm xuất phát. **Aanca** là tên gốc trong Grant Acedrex (Alfonso X, 1283); **Gryphon** là tên Murray (1913) gán nhầm cho chính quân đó; **Eagle** là tên dùng trong Metamachy, Terachess. Chỉ khác tên/trò chơi. (Lưu ý: một số tác giả hiện đại gán nhầm tên Aanca cho `t[WB]`, xem nhóm của Manticore.)

<a id="g2"></a>

### Nhóm 2: `RF`

**Gồm:** Admiral, Crowned Rook, Dragon King

Cùng một quân (Xe + Ferz). **Dragon King** là tên trong shogi; **Crowned Rook** là tên trong cờ Rutland/shogi; **Admiral** là tên của Cazaux (Pacey gọi là Sailor). Chỉ khác tên.

<a id="g3"></a>

### Nhóm 3: `F / F = (1,1)`

**Gồm:** Advisor, Counsellor, Ferz, Minister (Shatranj)

Cùng nước đi một ô chéo. **Ferz** và **Minister (Shatranj)** là quân thường. **Counsellor** là tên khác của Ferz/Advisor. **Advisor** (cờ tướng) khác ở chỗ bị nhốt trong cung (vùng 3×3), không được ra ngoài.

<a id="g4"></a>

### Nhóm 4: `A = (2,2)`

**Gồm:** Alfil, Boat, Elephant (Persian)

Cùng nhảy đúng 2 ô chéo. **Alfil** (Chaturanga/Shatranj/Courier), **Elephant (Persian)** (Shatranj) và **Boat** (Chaturaji) chỉ khác tên theo trò chơi.

<a id="g5"></a>

### Nhóm 5: `QN`

**Gồm:** Amazon, Maharaja

Cùng sức mạnh Hậu + Mã. **Maharaja** là Amazon "hoàng gia" trong *Maharajah and the Sepoys* — quân duy nhất của bên Trắng, cách đi không đổi.

<a id="g6"></a>

### Nhóm 6: `QNN`

**Gồm:** Amazonrider, Elephant (von Wilpert), Queen of the Night

Cùng một quân (Hậu + Nightrider). Ba tên khác nhau theo tác giả/trò chơi: **Amazonrider**, **Queen of the Night** (Jelliss 1991), **Elephant (von Wilpert)** (Wolf Chess 1943).

<a id="g7"></a>

### Nhóm 7: `t[WB]`

**Gồm:** Anchorite, Manticore, Rhinoceros

Cùng một nước đi: bước 1 ô ngang/dọc rồi trượt chéo như Tượng ra xa điểm xuất phát. **Manticore** là tên hiện hành; **Rhinoceros** (Zanzibar, Gigachess, Terachess) và **Anchorite** (Gilman) là tên cũ/khác. Chỉ khác tên.

<a id="g8"></a>

### Nhóm 8: `(0,1) / W = (0,1)`

**Gồm:** Angry Boar, Fool, Spy (Courier Chess), Wazir

Cùng nước đi một ô ngang/dọc. **Wazir**, **Fool** (Courier Chess), **Angry Boar** (Dai shogi) và **Spy (Courier Chess)** chỉ khác tên theo trò chơi.

<a id="g9"></a>

### Nhóm 9: `BN`

**Gồm:** Archbishop, Cardinal, Centaur (Carrera), Minister (G.Vicente Maura), Paladin, Princess

Cùng sức mạnh Tượng + Mã. **Princess**, **Archbishop**, **Cardinal** (Grand Chess), **Centaur (Carrera)** (Carrera 1617), **Minister (G.Vicente Maura)**, **Paladin** (Cavalier Chess) chỉ là các tên khác nhau của cùng một quân. (Cẩn thận: Paladin trong Reformed Courier-Spiel lại là `KN`, xem nhóm của Centaur.)

<a id="g10"></a>

### Nhóm 10: `RNF`

**Gồm:** Archchancellor, Heroine

Cùng một quân (Empress/Chancellor + Ferz). **Heroine** (Pocket Mutation Chess, Nelson) và **Archchancellor** (Knappen) chỉ khác tên.

<a id="g11"></a>

### Nhóm 11: `FA`

**Gồm:** Archer, Elephant (Modern), Falafel, Ferfil

Cùng một quân (Ferz + Alfil). **Elephant (Modern)** là tên phổ biến (Shako…); **Archer** (Reformed Courierspiel), **Falafel** (Betza), **Ferfil** (Jelliss) là các tên khác.

<a id="g12"></a>

### Nhóm 12: `mBcpB`

**Gồm:** Archer (Modern), Arrow (Duniho), Crocodile (Modern), Vao

Cùng cách đi: đi như Tượng khi không ăn quân, nhưng ăn bằng cách nhảy qua đúng một quân chắn (cùng tuyến chéo) rồi hạ xuống ô quân bị ăn. **Vao** (Akenhead 1947), **Arrow** (Duniho, Yang Qi), **Archer (Modern)** (Bigorra), **Crocodile (Modern)** (Zanzibar/Terachess): chỉ khác tên/trò chơi.

<a id="g13"></a>

### Nhóm 13: `BNN`

**Gồm:** Banshee, Unicorn (Unicorn Chess)

Cùng sức mạnh Tượng + Nightrider. **Banshee** (Jelliss 1991) và **Unicorn (Unicorn Chess)** (Paulowich 2000) chỉ khác tên.

<a id="g14"></a>

### Nhóm 14: `NAD`

**Gồm:** Bear, Castle, Squirrel

Cùng nhảy tới mọi ô cách 2 "bước" (Mã + Alfil + Dabbaba). **Squirrel**, **Bear**, **Castle** (Mideast/Pacific/Renn Chess) chỉ khác tên theo tác giả/trò chơi.

<a id="g15"></a>

### Nhóm 15: `mBcR`

**Gồm:** Biok, Ensign

Cùng cách đi: đi như Tượng, ăn như Xe. **Biok** (Parton 1961) và **Ensign** (Hà Lan 1696) chỉ khác tên. (Ngược lại là `mRcB`, nhóm Guard/Roshop.)

<a id="g16"></a>

### Nhóm 16: `B = FF / B`

**Gồm:** Bishop, Cockatrice, Courier

Cùng cách đi của Tượng (trượt chéo). **Cockatrice** là tên trong Grant Acedrex, **Courier** là tiền thân của Tượng trong Courier Chess; không có khác biệt về nước đi.

<a id="g17"></a>

### Nhóm 17: `Q2 (Hia power)`

**Gồm:** Bodyguard, Hia

Cùng quân: đi như Hậu nhưng tối đa 2 ô, có "sức mạnh Hia" (quân trượt phải dừng nếu vào trong tầm một nước Vua của quân này). **Hia** là tên tiếng Mông Cổ của **Bodyguard**.

<a id="g18"></a>

### Nhóm 18: `BC = BL`

**Gồm:** Caliph, Flying Dragon (Ganymede)

Cùng sức mạnh Tượng + Camel. **Caliph** (Ecumenical Chess, Gilman) và **Flying Dragon (Ganymede)** (Ganymede Chess, Hedden) chỉ khác tên. (Cẩn thận: "Caliph (Fairy)" là `WA`, một quân hoàn toàn khác.)

<a id="g19"></a>

### Nhóm 19: `WA`

**Gồm:** Caliph (Fairy), Phoenix, Waffle

Cùng sức mạnh Wazir + Alfil. **Phoenix** (shogi lớn), **Waffle** (Chess with Different Armies), **Caliph (Fairy)** (các nhà soạn bài cờ) chỉ khác tên. (Khác với "Caliph" của Ecumenical Chess là `BC`.)

<a id="g20"></a>

### Nhóm 20: `C = L = (1,3)`

**Gồm:** Camel, Giraffe (Giraffe Chess)

Cùng nhảy kiểu (1,3): 2 ô ngang/dọc rồi 1 ô chéo. **Giraffe (Giraffe Chess)** (phổ biến ở Ấn Độ) chính là **Camel**; chỉ khác tên. (Giraffe ở các trò khác lại là `Z` hoặc `(1,4)`.)

<a id="g21"></a>

### Nhóm 21: `CC = LL`

**Gồm:** Camelrider, Mehari

Cùng là Camel đi nhiều lần cùng hướng (rider). **Mehari** là tên do các nhà soạn bài cờ đặt (mehari = lạc đà một bướu); **Camelrider** là tên mô tả.

<a id="g22"></a>

### Nhóm 22: `mRcpR`

**Gồm:** Cannon, Pao

Cùng pháo Trung Quốc: đi như Xe khi không ăn, ăn bằng cách nhảy qua đúng một quân chắn. **Cannon** (Xiangqi, Shako, Metamachy) và **Pao** (Akenhead 1947) chỉ khác tên. (Khác với Cannon (Korean) `pR`.)

<a id="g23"></a>

### Nhóm 23: `pR`

**Gồm:** Cannon (Korean), Rion

Cùng nước đi: di chuyển và ăn dọc đường Xe bằng cách nhảy qua đúng một quân chắn (không có "đi thường"). **Cannon (Korean)** (Janggi) chính là **Rion** (Rook-line-hopper) của các nhà soạn bài cờ.

<a id="g24"></a>

### Nhóm 24: `ND`

**Gồm:** Carpenter, Templar

Cùng sức mạnh Mã + Dabbaba. **Carpenter** (Gilman), **Templar** (Jelliss); còn gọi Doughnut (Betza), Ouroboros, Scribe. Chỉ khác tên.

<a id="g25"></a>

### Nhóm 25: `KN`

**Gồm:** Centaur, General (Chess.com), Judge, Paladin

Cùng sức mạnh Mã + Mann (Vua không hoàng gia). **Centaur**, **Judge** (Sac Chess), **General (Chess.com)** (XXL chess) và **Paladin** (Reformed Courier-Spiel) chỉ khác tên. (Paladin của Cavalier Chess lại là `BN`.)

<a id="g26"></a>

### Nhóm 26: `WFD`

**Gồm:** Champion (Begnis), Warrior

Cùng sức mạnh Mann + Dabbaba (Wazir + Ferz + Dabbaba). **Warrior** và **Champion (Begnis)** (Reformed Courier chess) là tên thay thế của nhau. ("Champion" còn dùng cho quân khác: `RN` trong Carrera, `WAD` trong Omega Chess.)

<a id="g27"></a>

### Nhóm 27: `RN`

**Gồm:** Champion (Carrera), Chancellor, Empress, Marshal

Cùng sức mạnh Xe + Mã. **Empress**, **Chancellor**, **Marshal** (Grand Chess), **Champion (Carrera)** chỉ là các tên khác nhau của cùng một quân.

<a id="g28"></a>

### Nhóm 28: `R = WW`

**Gồm:** Chariot, Gliding Swallow, Rook

Cùng nước đi của Xe (trượt ngang/dọc). **Chariot** (Chaturanga/Xiangqi) và **Gliding Swallow** (Taikyoku/Wa shogi) chỉ khác tên so với **Rook**.

<a id="g29"></a>

### Nhóm 29: `CZGH = LJGH`

**Gồm:** Cheetah, Titan

Cùng một quân leaper (Camel + Zebra + Threeleaper + Tripper). **Cheetah** là tên hiện đại (Silverman/Cazaux); **Titan** là tên trong Fantasy Grand Chess (Hatch 2000). Chỉ khác tên.

<a id="g30"></a>

### Nhóm 30: `WF / WF (=K) / K = WF / WF = K`

**Gồm:** Commoner, Guard, King, Mann, Prince, Prince (The Ouroboros King), Quartermaster, Spy (Waterloo, Amsterdam Medieval)

Tất cả đi một ô theo mọi hướng. Khác biệt nằm ở vai trò/luật phụ: **King** là quân hoàng gia (bị chiếu). **Mann**, **Commoner**, **Guard**, **Spy (Waterloo, Amsterdam Medieval)** là Vua không hoàng gia. **Prince** là Vua không hoàng gia do Tốt của Vua thăng lên (Tamerlane, shogi lớn). **Prince (The Ouroboros King)** có thêm khả năng làm các quân hoàng gia trong phạm vi 3 ô trở nên bất tử. **Quartermaster** khi đi thì biến thành Tốt và để lại một Tốt ở ô cũ.

<a id="g31"></a>

### Nhóm 31: `BNW`

**Gồm:** Crown Princess, Popess

Cùng sức mạnh Princess/Archbishop + Wazir. **Crown Princess** (Knappen 2009) và **Popess** (Nelson 2003) chỉ khác tên.

<a id="g32"></a>

### Nhóm 32: `BW`

**Gồm:** Crowned Bishop, Dragon Horse, Missionary

Cùng sức mạnh Tượng + Wazir. **Dragon Horse** (shogi), **Crowned Bishop**, **Missionary** (Pacey/Cazaux) chỉ khác tên.

<a id="g33"></a>

### Nhóm 33: `sfW`

**Gồm:** Drunken Soldier, Pawn (Korean)

Cùng nước đi: 1 ô tiến hoặc ngang. **Pawn (Korean)** là Tốt trong Janggi và Tốt cờ tướng sau khi qua sông; **Drunken Soldier** là tên khác của chính quân đó.

<a id="g34"></a>

### Nhóm 34: `FD`

**Gồm:** Duke (Jelliss), Fortress, Kirin

Cùng sức mạnh Ferz + Dabbaba. **Kirin** (shogi lớn), **Fortress** (Pacific Chess), **Duke (Jelliss)**. Chỉ khác tên.

<a id="g35"></a>

### Nhóm 35: `WDN`

**Gồm:** Duke (Musketeer chess), Minister

Cùng sức mạnh Wazir + Dabbaba + Mã. **Minister** (Joyce 2005) và **Duke (Musketeer chess)** chỉ khác tên. (Tên "Duke" ở các trò khác chỉ quân khác: `FD`, `t[BW]t[WB]`.)

<a id="g36"></a>

### Nhóm 36: `FN`

**Gồm:** Dullahan, Priest, Prince (Fairy)

Cùng sức mạnh Ferz + Mã. **Prince (Fairy)** (các nhà soạn bài cờ), **Priest** (Scirocco), **Dullahan** (Fearful Fairies) chỉ khác tên.

<a id="g37"></a>

### Nhóm 37: `Z = J = (2,3)`

**Gồm:** Elephant (Ciccolini), Giraffe (Zaraffa), Zaraffa, Zebra

Cùng nhảy kiểu (2,3): 1 ô ngang/dọc rồi 2 ô chéo. **Zebra** (cờ cổ/bài cờ), **Zaraffa** và **Giraffe (Zaraffa)** (Grant Acedrex, Zanzibar), **Elephant (Ciccolini)** chỉ khác tên. (Giraffe trong Giraffe Chess lại là `C`.)

<a id="g38"></a>

### Nhóm 38: `FfW`

**Gồm:** Elephant (Indian), Khon, Silver General

Cùng nước đi: 1 ô chéo mọi hướng hoặc 1 ô tiến thẳng. **Silver General** (shogi), **Khon** (Makruk), **Elephant (Indian)** (al-Biruni c.1030) chỉ khác tên theo trò chơi.

<a id="g39"></a>

### Nhóm 39: `KAD = WFAD`

**Gồm:** Elephant (Musketeer), Mammoth (Winther), Mastodon, Pasha, Squire

Cùng sức mạnh Mann + Alfil + Dabbaba (Vua không hoàng gia + Alibaba). **Pasha** (Paulovits), **Squire** (Renn Chess), **Mastodon**/**Mammoth (Winther)**, **Elephant (Musketeer)**: chỉ khác tên/trò chơi.

<a id="g40"></a>

### Nhóm 40: `WN`

**Gồm:** Emperor, Marquis

Cùng sức mạnh Wazir + Mã. **Emperor** (Jelliss) và **Marquis** (Scirocco, Opulent Chess…) chỉ khác tên.

<a id="g41"></a>

### Nhóm 41: `sfWfF`

**Gồm:** Evil Wolf, Pawn (Jetan)

Cùng nước đi: như Vua nhưng không đi lùi. **Evil Wolf** (shogi lớn) và **Pawn (Jetan)** (Martian chess của Burroughs) chỉ khác tên.

<a id="g42"></a>

### Nhóm 42: `(0,5)(3,4)`

**Gồm:** Fiveleaper, Root-25-leaper

Cùng quân leaper có bước dài 5 đơn vị ((0,5) và (3,4), tổng 12 hướng). **Fiveleaper** và **Root-25-leaper** chỉ khác tên.

<a id="g43"></a>

### Nhóm 43: `Q = RB`

**Gồm:** Free King, Queen

Cùng nước đi (trượt ngang/dọc/chéo). **Free King** (Chu shogi, gọi là Honno) và **Queen** (cờ vua) chỉ khác tên/trò chơi.

<a id="g44"></a>

### Nhóm 44: `mWcF`

**Gồm:** Fusilier, Hobbit, Quadrapawn, Steward

Cùng ký hiệu: đi 1 ô ngang/dọc (mọi hướng), ăn 1 ô chéo (mọi hướng) — "Tốt bốn hướng". **Fusilier** là tên gốc (1770), **Hobbit** (Hobbit Chess); **Steward**/**Quadrapawn** (Centennial Chess) còn được mô tả là có thể đi 2 ô về phía trước như Tốt, điều mà ký hiệu này không biểu diễn.

<a id="g45"></a>

### Nhóm 45: `KC = KL = WFC / FWC`

**Gồm:** General (Paulovits), Gorilla

Cùng sức mạnh Camel + Ferz + Wazir. **Gorilla** (Chexx chess) và **General (Paulovits)** (Paulovits's Game 1890) chỉ khác tên/trò chơi.

<a id="g46"></a>

### Nhóm 46: `NC = NL`

**Gồm:** Gnu, Unicorn (Musketeer), Wildebeest

Cùng sức mạnh Mã + Camel. **Gnu**/**Wildebeest** (Wildebeest Chess) và **Unicorn (Musketeer)** chỉ khác tên.

<a id="g47"></a>

### Nhóm 47: `mQ`

**Gồm:** Go-between (Chinese), Jester (Brybelly)

Cùng nước đi: đi như Hậu nhưng không ăn được, cũng không bị ăn. **Go-between (Chinese)** (Seven Kingdoms) và **Jester (Brybelly)** (Faerie Chess) chỉ khác tên.

<a id="g48"></a>

### Nhóm 48: `mRcB`

**Gồm:** Guard, Roshop

Cùng cách đi: đi như Xe, ăn như Tượng. **Roshop** (Parton 1961) và **Guard** (Enlarged & Improved Chess 1696) chỉ khác tên. (Ngược lại là `mBcR`, nhóm Biok/Ensign; không nhầm với Guard = Vua không hoàng gia `WF`.)

<a id="g49"></a>

### Nhóm 49: `(2,4)`

**Gồm:** Hare, Lancer, Stag

Cùng nhảy kiểu (2,4). **Stag**, **Hare** (Hase trong tiếng Đức), **Lancer**: chỉ khác tên.

<a id="g50"></a>

### Nhóm 50: `NA`

**Gồm:** Hospitaller, Kangaroo, Priestess

Cùng sức mạnh Mã + Alfil. **Hospitaller** (Jelliss), **Kangaroo** (Outback Chess), **Priestess** (Joyce, Bagley-Jones) chỉ khác tên.

<a id="g51"></a>

### Nhóm 51: `KAND = WFAND`

**Gồm:** Joker, Lion (Modern)

Cùng quân Lion "KAND" (đi/ăn mọi ô cách 1–2 ô theo mọi hướng, kể cả nước Mã). **Lion (Modern)** (Metamachy, Terachess, Scirocco) và **Joker** (Waterloo, Amsterdam Medieval Chess) giống hệt nhau.

<a id="g52"></a>

### Nhóm 52: `mQcpQ`

**Gồm:** Leo, Sorceress

Cùng cách đi: đi như Hậu khi không ăn, ăn bằng cách nhảy qua đúng một quân chắn. **Leo** (Dawson/Akenhead) và **Sorceress** (Akenhead, Terachess) chỉ khác tên.

<a id="g53"></a>

### Nhóm 53: `WD`

**Gồm:** Machine, War Machine, Woody Rook

Cùng sức mạnh Wazir + Dabbaba. **War Machine**, **Woody Rook** (Betza 1979) và **Machine** (Zanzibar, Terachess) chỉ khác tên.

<a id="g54"></a>

### Nhóm 54: `nN`

**Gồm:** Mao, Moa

Cùng ký hiệu theo Wikipedia nhưng khác thứ tự bước: **Mao** (Mã cờ tướng) bước 1 ô ngang/dọc (ô này phải trống, nếu không bị cản chân) rồi 1 ô chéo; **Moa** thì bước chéo trước rồi ngang/dọc. Ký hiệu `nN` không phân biệt được hai kiểu này.

<a id="g55"></a>

### Nhóm 55: `RNN`

**Gồm:** Raven, Waran

Cùng sức mạnh Xe + Nightrider. **Raven** và **Waran** (Varan) chỉ khác tên.

<a id="g56"></a>

### Nhóm 56: `G = (3,3)`

**Gồm:** Revealer (Tamerlane), Tripper

Cùng nhảy đúng 3 ô chéo (3,3). **Tripper** (Gecko trong tiếng Đức) và **Revealer (Tamerlane)** (Full Tamerlane Chess; còn gọi Sentinel) chỉ khác tên.

<a id="g57"></a>

### Nhóm 57: `t[fFfR]t[bFbR]`

**Gồm:** Ship, Twin Tower

Cùng một nước đi: bước 1 ô chéo rồi trượt dọc theo cột như Xe ra xa điểm xuất phát. **Ship** và **Twin Tower** (tên do Betza đặt theo hình dạng nước đi) chỉ khác tên, cùng trong Tamerlane II.

## 3. Các trường hợp biên của ký hiệu Betza

Phần này tổng hợp từ bài Wikipedia [Betza's funny notation](https://en.wikipedia.org/wiki/Betza%27s_funny_notation) và trang [XBoard Betza](https://www.gnu.org/software/xboard/Betza.html). Các trang trên chessvariants.com/.org (bản gốc của Betza, tài liệu Bex) chặn truy cập tự động (lỗi 403) nên **chưa đọc được trực tiếp**; những chỗ phụ thuộc vào đó được ghi rõ là chưa xác nhận.

### 3.1. Chữ chỉ hướng (`f b l r v s h`)

- Một chữ đơn thường chỉ **một cặp** hướng, nên muốn chỉ đúng một hướng phải dùng hai chữ: `fl` = chỉ hướng tiến-trái.
- Hễ đã dùng bất kỳ chữ hướng nào thì phải **liệt kê đủ mọi hướng** quân được đi. Ví dụ `fW` chỉ đi tiến; muốn tiến và ngang phải viết `fsW`.
- Chữ ghép được rút gọn: `v` = `f` + `b`, `s` = `l` + `r`.
- Với bước nhảy chéo kiểu Mã (hippogonal), **gấp đôi chữ hướng** nghĩa là chỉ lấy các nước có thành phần lớn hơn theo hướng đó. `fN` gồm mọi nước Mã có thành phần tiến (4 nước), còn `ffN` chỉ gồm 2 nước nhảy 2 ô tiến + 1 ô ngang (Mã trong shogi).
- XBoard: khi cần chỉ hướng thứ hai vuông góc thì viết **trước** hướng chính (`lfN` = nước Mã tiến xa nhất về bên trái). Các chữ liền nhau tự động ghép lại; muốn ngăn thì gấp đôi, ví dụ `ffrrN`.
- `h` (half) và hai hướng chiral `hr`, `hl`: trong XBoard 4.8.0 không ghép được với chữ hướng khác.
- Thứ tự modifier mà XBoard đòi hỏi: `i`, chữ hướng, `m`, `c`, `d`, `e`, `t`, `p`, `g`, `o`, `y`, `n`, `j`. Viết sai thứ tự thì phần sai bị **bỏ qua**, và gặp atom lạ thì việc đọc **dừng lặng lẽ**.

### 3.2. Quân nào dùng từ 3 chữ hướng liền nhau trở lên?

Có. Quét toàn bộ 412 mục (chỉ tính các chữ `f b l r v s h`):

| Quân | Ký hiệu | Chuỗi chữ hướng liền nhau | Ý nghĩa |
|---|---|---|---|
| Heavenly Horse | `ffbbN` | `ffbb` (4 chữ) | Hai cặp chữ gấp đôi: chỉ các nước Mã nhảy 2 ô tiến hoặc 2 ô lùi rồi 1 ô ngang |
| Knave | `sDffbbN` | `ffbb` (4 chữ) | Cùng nước Mã như trên, cộng thêm `sD` (nhảy 2 ô ngang) |
| Horned Falcon (dạng viết thứ hai) | `BrlbRdhfWfD` | `rlb` (3 chữ) | `rlb` = phải + trái + lùi, tức là cách viết khác của `sb` ở dạng thứ nhất `BsbRfWfD` (dạng viết này đã được bỏ khỏi bảng quân) |

- Mọi quân khác chỉ có tối đa 2 chữ hướng liền nhau (ví dụ `fs`, `sf`, `fb`, `bl`, `lr`).
- Trong dạng viết thứ hai của Horned Falcon và Soaring Eagle (`RbBdhfFfA`) còn có `dhf`. Chữ `d` ở đây **chưa xác định được nghĩa** (trong Betza 2.0, `d` là "phá quân mình"), nên mình không tính nó là chữ hướng. Các dạng viết này đã được bỏ khỏi bảng quân.
- Một số kết quả giả khi quét (như `fr` trong Anti-King, `ss` trong Pawn (Chinese)) đến từ chữ tiếng Anh trong phần chú thích, không phải ký hiệu.

### 3.3. `n` và `j` (nhảy / bị cản chân)

- Theo bài Wikipedia, `n` và `j` chỉ **không mơ hồ** trên atom thuần ngang/dọc hoặc thuần chéo.
- Trên Mã, `nN` mơ hồ: Mã cờ tướng bị cản ở ô liền kề theo hướng đi ngang/dọc trước, nhưng ký hiệu `nN` không nói được là đi theo thứ tự nào. Đây là lý do Mao và Moa trong danh sách đều ghi `nN`.
- Bex giải quyết bằng chuỗi nước, ví dụ `mW-F` cho Mã cờ tướng, và đọc `nN` là quân có nhiều đường đi, chỉ cần một trong các đường ngắn nhất không bị chặn.
- XBoard 4.8.0 chỉ kiểm tra **ô ở giữa** của nước nhảy, nên chỉ đúng với `N`, `A`, `D`.
- `j` trên quân trượt (`B`, `R`) nghĩa là bỏ qua ô đầu tiên của đường đi, bất kể ô đó có gì.

### 3.4. Số đi sau atom và chữ lặp

- Một chữ số sau atom là số bước tối đa (`F7` là Tượng trên bàn 8×8). Gấp đôi chữ (`FF`) là không giới hạn mà không cần biết cỡ bàn.
- XBoard: chữ số `0` là không giới hạn, tối đa 2 chữ số và không được bắt đầu bằng số 0 thừa.
- Bex: số 0 đứng đầu nghĩa là **đúng** số bước đó thay vì tối đa; dấu `*` làm số mũ nghĩa là số bước tùy ý.

### 3.5. `[cl]` và các ngoặc vuông khác (đã đối chiếu với tài liệu Bex gốc)

Nguồn: tệp *Proposed Betza Extended Notation (BEX Notation)* của David Howe (14/01/2012), bạn cung cấp. Tài liệu khá ngắn; phần liên quan nằm ở mục "Exotica".

**Định nghĩa gốc**

- `[...]` là *exotic operator* (toán tử "lạ"). Dạng `[c...]` là các kiểu bắt đặc biệt, kèm lưu ý quan trọng: "toán tử này **không ngầm định bắt kiểu thay thế**; muốn bắt thay thế phải ghi rõ".

| Ký hiệu | Nghĩa theo tài liệu Bex |
|---|---|
| `[ca]` | Bắt bằng cách tiến sát |
| `[cw]` | Bắt bằng cách lùi ra xa |
| `[cj]` | Bắt bằng cách nhảy qua **một** quân |
| `[cl]` | Bắt bằng cách nhảy qua **bao nhiêu quân cũng được** |
| `[ci]` | Bắt kiểu bắt chước (bắt theo cách quân bị bắt sẽ bắt) |
| `[ccM]` | Bắt kẹp (quân nằm giữa quân vừa đi và quân bạn có thể tới được bằng nước `M`) |
| `[cu]` | Tự bắt |
| `[crM]` | Bắt tầm xa quân mà nước `M` tới được |

- Ví dụ duy nhất của `[cl]` trong tài liệu: **Long Leaper** của Ultima `mQ+[cl]Q`, tức là đi như Hậu hoặc (`+` = "hoặc") bắt kiểu nhảy qua theo các đường của Hậu. Cùng cách viết: Withdrawer `mQ+[cw]Q`.
- Dấu `+` chỉ là cách viết tách ra cho dễ đọc; `AB` và `A+B` nghĩa như nhau. Vậy `mQ[cl]Q` (cách viết của Wikipedia) = `mQ+[cl]Q`: **hai thành phần nước đi độc lập**, không phải một chuỗi nước. Chữ hướng ở trước `[cl]` thuộc thành phần trước, nên sau `[cl]` phải viết lại chữ hướng riêng (`mfF[cl]fF`).
- Atom đứng ngay sau `[cl]` (ví dụ `Q`) chỉ ra **hình học các đường** mà quân nhảy qua. Với `[ccM]` và `[crM]`, atom `M` lại nằm **trong** ngoặc.

**Điểm sai trong cách mình trình bày trước đó:** mình đã mô tả `[cl]` là "bắt kiểu locust, lấy quân bị nhảy qua và hạ cánh ngay sau nó". Tài liệu gốc không nói như vậy: `[cl]` là nhảy qua *nhiều quân*, còn nhảy qua đúng một quân là `[cj]`. Bài Wikipedia về Betza 2.0 cũng viết Long Leaper của Ultima là `(cQ-mQ)4`: tối đa 4 lần bắt trên một đường thẳng, miễn là giữa các quân bị nhảy qua có ô trống.

**Điều tài liệu Bex không nói (phần còn lại thật sự mở)**

1. Ô hạ cánh nằm ở đâu, có được là ô trống hay ô có quân địch không. Tài liệu viết chung rằng "không ngầm định thay thế quân".
2. Luật cụ thể khi gặp quân bạn, hai quân liền kề, hay thay đổi hướng giữa các lần nhảy. Tài liệu chỉ nhắc rằng luật Ultima/Chu shogi "quá đặc thù để diễn đạt gọn trong ký hiệu".
3. Khi atom đi kèm là quân nhảy một bước (leaper như `F`, `W`): tài liệu chỉ cho ví dụ với atom trượt `Q`; "nhảy qua" bằng bước `F` không được định nghĩa.

**Hệ quả với bảng Wikipedia**

- Cách Wikipedia dùng `[cl]` cho cờ đam (`mfF[cl]fF`, `mB[cl]B`…) **mượn** ký hiệu của Bex nhưng lệch với định nghĩa gốc: cú nhảy của quân đam đúng một quân thì theo Bex phải là `[cj]`, và một cú nhảy bắt đúng một quân.
- Vì tài liệu gốc không quy định ô hạ cánh, các mâu thuẫn mà mình liệt kê trước đó (cùng chuỗi `mR[cl]R` nhưng Rook (Quang Trung) hạ cánh ngay sau còn Checker King hạ cánh tùy ý; Dabbaba-checker bắt thêm quân ở ô hạ cánh) **là lỗi/cách dùng lỏng của người viết bảng Wikipedia**, không phải một luật Bex bị mình hiểu sai.
- Locust (`mQ[cl]Q`, "hạ cánh ngay sau quân bị bắt") theo Bex nên là `mQ+[cj]Q` chứ không phải `[cl]`; `mQ+[cl]Q` là Long Leaper.
- Cách viết chặt chẽ hơn cho quân đam vẫn là các chuỗi nước: MBN `fcF-mF`, Betza 2.0 `cR-mR`, XBetza `fcafmF` (xem các nguồn ở các mục trên). Bex cũng có chuỗi tương tự bằng `-`/`--`: `A-B` là nước A rồi nước B cùng hướng chung, `A--B` là hướng bất kỳ.

**Các ký hiệu khác trong tài liệu Bex (đối chiếu với danh sách quân)**

- Atom: `O` (0,0), `W F D N A H L J G`, `(N,M)`. Bex dùng `L`, `J` thay cho `C`, `Z`; `R`, `B` là quân trượt, `Q` = `R`+`B`, `K` = `W`+`F`.
- Chữ hướng: chỉ có `f b r l s v`. **Không có `h`**.
- Modifier khác: `m` (chỉ đi, không bắt), `c` (phải bắt), `y` (hoàng gia, ví dụ Tướng cờ tướng `yW`), `e` (cho phép nhảy một nước vốn không nhảy, ví dụ Mã shogi `e(mfW-F)`), `n` (cấm nhảy, dùng đường ngắn nhất; Moo = Mao + Moa = `nN`), `i` (chỉ nước đầu), `j` (nhảy qua đúng một vật cản, ví dụ `j(mW-F)`), `p` (hop, ví dụ pháo `mR+cpR`), `g` (grasshopper), `z` (crooked, ví dụ `zB`), `q` (vòng tròn, ví dụ Rose `qN`).
- Không có `t`, `k`, `d`, `a`, `o` làm modifier trong tài liệu Bex. Vậy các ký hiệu như `t[FR]`, `kW`, `dhf` trong bảng Wikipedia là từ nơi khác hoặc do người biên tập đặt.
- Toán tử: nhóm `( )`, `-`, `--`, `+`, rider `*` (ví dụ `N*` = `NN`), giới hạn số lần `2-N` (từ 2 trở lên), đúng số lần `02`…`0N` (Tốt nước đầu `mfW02`), thăng cấp bằng `=Q,R,B,N`. Ví dụ Sư tử Chu shogi: `K+(DAN)+(K-K)+[crK]+(mK--[xo])`.

> **Đính chính (Frisian):** trước đây mục này coi `[cl]F` (chéo) cùng `[cl]D` (ngang/dọc) của Frisian Checkers là không nhất quán. Đó là hiểu sai: ghi chú của Wikipedia nói quân nhảy qua quân "cùng màu ô". Bàn cờ chỉ dùng ô một màu nên ô kề theo ngang/dọc cách nhau 2 ô, tức đúng atom `D`. Vì vậy `[cl]F` + `[cl]D` nhất quán: quân kề tính theo ô chơi được, hạ cánh ở ô chơi được kế tiếp. Mình chưa tra lại luật Frisian từ nguồn riêng.

**Trạng thái kiểm tra ý đồ của 21 mục dùng `[cl]`:** đã đối chiếu với định nghĩa ở mục 5. 18 mục cờ đam khớp ý đồ ngay với `[cj]` mặc định (kể cả hai mục Loca và Frisian); 3 mục lệch (Locust, Rook (Quang Trung), Dabbaba-checker) khớp sau khi thêm tham số hạ cánh. Cả 21 ký hiệu trong bảng đã được sửa theo mục 5.4; ký hiệu gốc của Wikipedia ghi ở đó.

### 3.6. Cùng một chữ nhưng nghĩa khác nhau tùy phiên bản

| Chữ | Các nghĩa gặp trong nguồn |
|---|---|
| `t` | `t[FR]`: chuỗi nước bẻ góc của Betza (dùng trong danh sách quân ở trên); XBoard: trên chặng cuối thì cấm bắt Vua (chỉ để xấp xỉ quân quá phức tạp); Betza 2.0: như `p` nhưng chỉ nhảy qua quân mình |
| `y` | XBetza: đổi trượt/nhảy trên ô trống; Bex: đánh dấu quân hoàng gia |
| `O` | XBetza: nhập thành (số kèm theo là số ô Vua đi); Bex: nước đi (0,0), tức bỏ lượt |
| `e` | Bex: cho phép nhảy một nước vốn không nhảy; XBetza: kiểu ăn en passant (`mfWcefF` trong Tốt); Betza 2.0: ép chặng trượt có độ dài bằng chặng trước |
| `d` | Betza 2.0: phá quân của chính mình; trong dạng `dhf` của Horned Falcon thì chưa rõ |
| `j` | Betza gốc: bắt buộc nhảy qua một ô không ghé; XBetza: với quân trượt thì bỏ qua ô đầu |
| `o` | Hình trụ (quấn quanh hai mép bàn); Betza 2.0: tạm ra khỏi bàn trên chặng giữa |
| `p`, `g` | Trên chặng không cuối: chặng đó phải **kết thúc** trên ô có quân (rồi đi tiếp), chứ không phải nhảy qua quân |
| `a` | XBetza: sau chặng này còn đi tiếp một chặng nữa (điểm bắt đầu của nước đi nhiều chặng) |
| `q`, `z` | Quân trượt vòng tròn / quân trượt zig-zag. XBoard 4.8.0 chưa hỗ trợ |

### 3.7. Mặc định khi đi nhiều chặng

- Chặng không cuối mặc định chỉ `m` (đi vào ô trống); chặng cuối mặc định `mc`.
- XBetza: hướng của chặng tiếp theo mặc định là mọi hướng **trừ** quay đầu hoàn toàn; chữ `f` ở chặng tiếp theo nghĩa là "đi tiếp cùng hướng". Betza 2.0 thì mặc định chỉ đi tiến.
- Ví dụ Sư tử trong Chu shogi viết `KNADcaKmcabK`: phần `KNAD` là các nước nhảy trực tiếp, `caK` là bắt rồi đi tiếp (đánh-và-chạy, bắt đôi), `mcabK` là bắn từ xa và bỏ lượt có điều kiện.

### 3.8. Những ký hiệu trong danh sách mà mình chưa giải mã được

- `k` trong `kW` của General (Chinese): không tìm thấy nghĩa trong nguồn đã đọc được.
- `(0,2n)` của Dabbabante: không phải toạ độ chuẩn; mình chỉ xếp vào `(a,b)`.
- `d` trong `dhf`: xem 3.2 (các dạng viết chứa `dhf` đã được bỏ khỏi bảng quân).
- `[cl]`, `[cj]`: đã có định nghĩa tự thiết kế ở mục 5 (Bex gốc không quy định ô hạ cánh).
- Tọa độ `(a,b)` là phần mở rộng của Bex (ví dụ `(1,4)` cho Giraffe), không có trong Betza gốc.

## 4. Quy ước chữ hướng và kiểm tra các quân

Phần này ghi lại quy ước chữ hướng do bạn đề ra (dựa trên cách đọc của Wikipedia) và kết quả đối chiếu với toàn bộ các quân trong bảng. Đây là quy ước **tự định nghĩa**, không phải chuẩn chính thức; mục tiêu là chặt chẽ, tương thích Betza truyền thống và khớp mô tả của Wikipedia.

### 4.1. Nguyên lí

Quy ước **tự định nghĩa** (không phải chuẩn chính thức), nhằm chặt chẽ, tương thích Betza truyền thống và khớp mô tả của Wikipedia.

**Hệ tọa độ.** Quân đứng ở gốc $(0,0)$, mỗi điểm nguyên $(x,y)$ là một ô, $y$ tăng theo hướng tiến của quân, $x$ tăng về bên phải.

**Sáu chữ, hai nghĩa.**

| Chữ | Nghĩa rộng | Nghĩa hẹp |
|---|---|---|
| `f` | $y > 0$ | $y \ge \lvert x \rvert$ |
| `b` | $y < 0$ | $-y \ge \lvert x \rvert$ |
| `l` | $x < 0$ | $-x \ge \lvert y \rvert$ |
| `r` | $x > 0$ | $x \ge \lvert y \rvert$ |
| `s` | $x \ne 0$ (hợp của `l`, `r`) | $\lvert x \rvert \ge \lvert y \rvert$ (hợp của `l`, `r` hẹp) |
| `v` | $y \ne 0$ (hợp của `f`, `b`) | $\lvert y \rvert \ge \lvert x \rvert$ (hợp của `f`, `b` hẹp) |

**Cụm chữ hướng** là các chữ hướng đứng liền nhau trước một atom; có ký hiệu khác chen vào thì thành cụm khác. Mỗi cụm chỉ có các dạng sau là hợp lệ:

| Dạng cụm | Ví dụ | Cách đọc |
|---|---|---|
| Một chữ | `f` | Nghĩa rộng |
| Hai chữ giống nhau (gấp đôi) | `ff` | Nghĩa hẹp |
| Hai chữ khác nhau | `fs` | Chữ đầu nghĩa rộng, chữ sau nghĩa hẹp. Lấy **giao**; nếu giao rỗng thì lấy **hợp**. Thứ tự có ý nghĩa |
| Bốn chữ: hai loại, mỗi loại gấp đôi | `llff` | **Ép lấy hợp**, không bao giờ lấy giao. Mỗi loại đọc nghĩa hẹp. Thứ tự không có ý nghĩa (`llff` = `ffll`) |
| Mọi dạng khác (ba chữ như `rlb`, `llf`; từ ba loại chữ; một chữ lặp từ ba lần) | | **Không hợp lệ.** Cần nhiều hơn 2 loại chữ hướng thì viết tách thành nhiều thành phần |

**Các nguyên tắc đi kèm.**

1. **Tách thành phần là lấy hợp.** Hai thành phần đứng cạnh nhau (như `lN` và `fN`) vốn là hợp của hai tập nước đi. Vì vậy mọi tập "hợp rộng-rộng" đều viết được mà không cần thêm cú pháp.
2. **Đánh giá trên toàn bộ tập nước đi của thành phần, không expand `R`, `B`, `Q`, `K` trước.** `R` có 4 hướng thẳng, `B` có 4 hướng chéo, `Q` và `K` có 8 hướng; cụm chữ hướng lọc trên cả tập đó, và việc "giao rỗng thì lấy hợp" cũng xét trên cả tập. Hệ quả: `fsQ` ra đúng 2 đường chéo tiến (giao không rỗng) chứ không phải "Xe tiến và sang ngang, Tượng tiến"; `sbK` ra đúng 2 đường chéo lùi; `sfK` ra đúng 2 đường chéo tiến. Muốn ý đồ khác thì tách thành phần: `fsRfB`, `sbWbF`, `sfWfF`. Cụm một chữ không bị ảnh hưởng (`fK`, `bK` vẫn đúng).
3. **Nghĩa rộng và nghĩa hẹp của một chữ trùng nhau trên atom thẳng hoặc chéo** (`W`, `F`, `D`, `A`, `H`, `G`), nên chỉ trên atom xiên (`N`, `C`, `Z` và `(a,b)` không thẳng/chéo) hai cách đọc mới cho kết quả khác nhau. Với atom chéo, nghĩa hẹp của hai chữ kề nhau có chung một đường chéo (ví dụ `f` hẹp và `l` hẹp cùng chứa tiến-trái), nên giao của chúng không rỗng; đó là lý do cần cụm bốn chữ để ép lấy hợp.
4. **Chữ `h` không nằm trong quy ước này**; các quân từng dùng `h` đã được viết lại không có `h`. **Chữ hướng ở chặng tiếp theo** trong `t[...]` tính theo hướng bàn cờ (định nghĩa ở mục 6); chuỗi `a` của XBetza chưa nằm trong quy ước.

**Ví dụ tính tay.**

- `fsW`: $f$ rộng giao $s$ hẹp trên $W$ là rỗng, nên lấy hợp: tiến, trái, phải.
- `fsF`: giao không rỗng (hai đường chéo tiến), nên chỉ lấy giao: tiến-trái, tiến-phải.
- `fsN`: $y>0$ và $\lvert x \rvert \ge \lvert y \rvert$, được $(\pm 2, 1)$. Còn `sfN`: $x \ne 0$ và $y \ge \lvert x \rvert$, được $(\pm 1, 2)$. **Thứ tự chữ có ý nghĩa** với atom xiên.
- `fbN`: $f$ rộng giao $b$ hẹp là rỗng, nên lấy hợp: 4 nước tiến cộng 2 nước lùi hẹp $(\pm 1, -2)$, tổng 6 nước (bất đối xứng).
- `vvN` (hay `ffbbN`): chỉ các nước $(\pm 1, \pm 2)$, 4 nước.
- `lfF`: $l$ rộng giao $f$ hẹp trên $F$ là $(-1,1)$, không rỗng nên chỉ lấy giao: một đường chéo tiến-trái.
- `llffF`: ép hợp, $l$ hẹp hợp $f$ hẹp trên $F$ là tiến-trái, lùi-trái, tiến-phải (3 đường chéo). Cụm hai chữ không viết được điều này.
- `llffN`: $l$ hẹp là $(-2,\pm 1)$, $f$ hẹp là $(\pm 1, 2)$, hợp được 4 nước. Để so sánh, `lfN` đọc $l$ rộng giao $f$ hẹp, chỉ còn đúng một nước $(-1,2)$.

**Vì sao cụm bốn chữ đọc hẹp-hẹp.**

1. Nhất quán với dạng gấp đôi: một chữ gấp đôi luôn có nghĩa hẹp, nên `ll` và `ff` trong `llff` được đọc đúng như khi đứng riêng.
2. Khớp dữ liệu: Heavenly Horse và Knave `ffbbN` ra đúng 4 nước Mã hẹp như mô tả; Crab `ffNbsN` và Knight (Japanese) `ffN` cũng đọc hẹp.
3. Không mất khả năng biểu diễn, vì tập "hợp rộng-rộng" viết được bằng cách tách thành phần (nguyên tắc 1).
4. Cụm bốn chữ có đúng một nghĩa, nên không cần quy ước phụ để phân biệt rộng hay hẹp ở từng vị trí.

### 4.2. Kết quả kiểm tra

Quét 110 mục có chữ hướng ngoài ngoặc `t[...]`, tính tập nước đi theo quy ước rồi đối chiếu với mô tả của Wikipedia. **99 mục khớp ngay từ đầu (tính theo cách đọc từng atom; 2 mục trong đó, Evil Wolf và Pawn (Jetan), cần tách thành phần sau khi chốt đọc theo toàn bộ tập của `K`), 4 mục sai ý đồ (đã sửa, xem dưới), 6 mục nằm ngoài phạm vi quy ước (đã sửa theo gợi ý, xem dưới) và 1 mục giữ nguyên (Lion (Japanese)).** Nhóm khớp gồm cả các quân khó như Barc `fsNbbN`, Crab `ffNbsN`, Scorpion (Winther) `mfsN`, Left/Right General `FvrW`/`FvlW`, Left/Right Quail, Blind Dog `sbWfF`, Charging Rook `fsRbK`.

**4 mục sai ý đồ — đã tra nguồn và sửa trong các bảng ở phần 1–2:**

| Quân | Ký hiệu Wikipedia | Ký hiệu đã sửa | Căn cứ |
|---|---|---|---|
| Cannon (Musketeer) | `DWFsN` | `DWFssN` | Trang luật chính thức [musketeerchess.net](https://musketeerchess.net/games/musketeer/rules/rules-short.php): đi 1 ô mọi hướng, nhảy 2 ô ngang/dọc, và nhảy Mã chỉ kiểu $(\pm 2, \pm 1)$ (không có $(\pm 1, \pm 2)$); tổng 16 ô từ d4. `sN` theo quy ước cho cả 8 nước Mã nên sai |
| Debtor | `vDsN` | `vDssN` | Knavish Chess của Charles Gilman ([chessvariants.org](https://chessvariants.org/tag/Piece:Debtor)): quân đối xứng xoay 90° của Knave, có Dabbaba dọc và các nước Mã "ngang nhất", tổng 6 hướng |
| Fibnif | `fbNF` | `vvNF` | [Piececlopedia: Fibnif](https://www.chessvariants.org/piececlopedia.dir/fibnif.html) (Betza): Mã chỉ các nước dài nhất tiến/lùi, tức $(\pm 1, \pm 2)$, cộng Ferz. `fbN` theo quy ước cho 6 nước nên sai |
| Fortress (Musketeer) | `F3DfbN` | `F3DvvN` | [musketeerchess.net](https://musketeerchess.net/games/musketeer/rules/rules-short.php): trượt chéo tối đa 3 ô, nhảy 2 ô ngang/dọc, nhảy Mã chỉ kiểu 2 ô dọc + 1 ô ngang $(\pm 1, \pm 2)$, không phân biệt tiến lùi. Có thể viết tương đương `F3DffbbN` |

Lưu ý: nguồn của Debtor và Fibnif là các trang cộng đồng trên chessvariants, mình chưa kiểm chứng độc lập. Với Cannon và Fortress, mình dùng trang luật chính thức; riêng ví dụ ô cờ của Fortress trên trang đó có một lỗi gõ (ô f8), không ảnh hưởng tới các nước đi đã nêu.

**4 mục sửa thêm sau khi chốt đánh giá trên toàn bộ tập nước đi của `Q`, `K`:**

| Quân | Ký hiệu trước | Kết quả theo quy ước | Đã sửa thành |
|---|---|---|---|
| Charging Knight | `fNsbK` | `sbK` trên cả tập `K`: $s$ rộng giao $b$ hẹp chỉ còn 2 đường chéo lùi, mất sang ngang và lùi thẳng | `fNsbWbF` (lùi thẳng, ngang, 2 chéo lùi) |
| Forequeen | `fsQbNbK` | `fsQ` chỉ còn 2 đường chéo tiến | `fsRfBbNbK` (Xe tiến và ngang, Tượng tiến) |
| Evil Wolf, Pawn (Jetan) | `sfK` | chỉ còn 2 đường chéo tiến, mất tiến thẳng và ngang | `sfWfF` (tiến thẳng, ngang, 2 chéo tiến) |

Colonel `KfsRfN` không bị ảnh hưởng vì cụm chữ hướng đi với `R`, một tập nước đi thẳng.

**Cách ghi `ffbbN` của Heavenly Horse và Knave là đúng** (cụm hai loại, mỗi loại gấp đôi, cho 4 nước hẹp), nhưng có thể rút gọn thành `vvN`.

**6 mục ngoài phạm vi quy ước đã được sửa theo gợi ý; 1 mục giữ nguyên:**

| Quân | Ký hiệu cũ | Vấn đề | Đã sửa thành |
|---|---|---|---|
| Charging Knight | `fhNsbK` | Chữ `h` không thuộc 6 chữ của quy ước. Mô tả: "forward as a Knight" | Bỏ `h` và tách `sbK`: `fNsbWbF` |
| Colonel | `KfsRfhN` | Như trên | `KfsRfN` |
| Forequeen | `fsQbhNbK` | Như trên (`bhN`) | `fsRfBbNbK` (bỏ `h`, tách `fsQ`) |
| Horned Falcon (dạng viết thứ hai) | `BrlbRdhfWfD` | Cụm `rlb` có 3 loại chữ hướng, không hợp lệ theo mục 4.1. Nếu mở rộng quy tắc (chữ đầu rộng, các chữ sau hẹp, lấy giao, rỗng thì lấy hợp) thì trên atom `W` cho cùng kết quả `L,R,B` với `sb` ($r$ rộng ∩ $l$ hẹp ∩ $b$ hẹp là rỗng, nên lấy hợp). Nhưng không tương đương tổng quát: trên `F` thì `rlb` ra cả 4 đường chéo còn `sb` chỉ ra 2 đường chéo lùi; trên `N` thì ra 7 nước còn `sb` chỉ ra 2. `d`, `h` không xác định | Dùng dạng thứ nhất `BsbRfWfD` (khớp quy ước) |
| Soaring Eagle (dạng viết thứ hai) | `RbBdhfFfA` | `dh` không xác định | Dùng dạng thứ nhất `RbBfFfA` (khớp) |
| Golden Bird | `vRlrW2F3` | `lr` đúng quy ước (giao rỗng, lấy hợp, ra `L,R`) nhưng thừa; ghi chú Wikipedia nói "forward diagonals" trong khi `F3` là cả 4 đường chéo | `vRsW2F3`; giữ `F3` theo Betza của Wikipedia (đã chốt, không xác minh luật) |
| Lion (Japanese) | `KANDcaKmabK` | `ab` là chặng nối (`a` = đi tiếp), chữ `b` ở chặng sau là *quay lại*, không phải hướng của quy ước. Nước đi của Lion nằm ngoài ký hiệu Bex | Giữ nguyên |

Golden Bird: giữ theo ký hiệu Betza của Wikipedia (chỉ đổi `lr` thành `s`, cùng nghĩa). Không xác minh luật đi vì nhiều quân shogi biến thể rất khó tra lại; ghi chú "forward diagonals" của Wikipedia mâu thuẫn với `F3` nhưng được bỏ qua theo quyết định của bạn.

**5 quân có chữ hướng nằm trong `t[...]`** đã được xử lý theo mục 6 (chữ hướng ở chặng sau tính theo hướng bàn cờ): Ship và Twin Tower đổi `t[FvR]` thành `t[fFfR]t[bFbR]`; Snake và Vivi giữ nguyên; Unicornio dùng `t[NB]`.

### 4.3. Các điểm cần bạn chốt thêm

1. **Đánh giá theo toàn bộ tập nước đi của `Q`, `K`:** đã chốt (xem 4.1, nguyên tắc 2); các quân bị ảnh hưởng đã được tách thành phần.
2. **Chữ `h`:** đã chốt bỏ; các quân từng dùng `h` đã được viết lại không có `h`.
3. **Chữ hướng ở chặng tiếp theo** trong `t[...]`: đã chốt theo hướng bàn cờ (mục 6). Chuỗi `a` của XBetza vẫn chưa nằm trong quy ước.

### 4.4. Danh mục để tính sau

Các mục chưa xử lý, ghi lại để quay lại sau:

- **Lion (Japanese) `KANDcaKmabK`:** giữ nguyên; nước đi của Lion nằm ngoài ký hiệu Bex (chữ `b` ở chặng nối là quay lại, không phải chữ hướng của quy ước).
- **Điểm mở:** chuỗi `a` của XBetza (hiện chỉ Lion (Japanese) dùng).

## 5. Định nghĩa `[cj]` và `[cl]`

Đây là định nghĩa **tự thiết kế**, dựa trên tài liệu Bex (nơi `[cj]` là "nhảy qua một quân" và `[cl]` là "nhảy qua nhiều quân") và bổ sung các tham số mà Bex không quy định. Mục tiêu: mỗi ký hiệu cho ra đúng một tập nước đi xác định. Chữ hướng trong `Y` đọc theo quy ước ở mục 4.1.

### 5.1. Cú pháp

```
nước-bắt-nhảy ::= "[cj" [ landing ] [ n ] "]" Y        (nhảy qua một quân)
nước-bắt-lặp  ::= "[cl" [ landing ] [ n ] "]" Y        (nhảy qua nhiều quân)
landing       ::= "m" | "mc" | "c"
n             ::= số nguyên dương
Y             ::= [cụm chữ hướng] [ "n" ] atom [ chữ số ]
```

- `Y` là một thành phần Betza thông thường: cụm chữ hướng (nếu có) rồi atom (`W F D N A H C Z G`, `(a,b)`, `R B Q K`, chữ lặp như `NN`) và chữ số giới hạn bước (nếu có). `Y` không chứa `m`, `c`, `p`, `g`, `i`.
- `landing` là modality của ô hạ cánh, viết đúng thứ tự `m`, `mc`, `c` (`cm` không hợp lệ). Bỏ trống thì mặc định là `m`.
- `n` là hệ số hạ cánh tối đa $B_{\max}$ (mục 5.2). Bỏ trống thì kế thừa từ `Y`. `n = 0` không hợp lệ; dạng số 0 đứng đầu của Bex không dùng ở đây.
- `X[cj…]Y` nghĩa là `X + [cj…]Y` (toán tử kết hợp của Bex): hai thành phần độc lập. Chữ hướng đứng trước ngoặc thuộc `X`; `Y` có chữ hướng riêng, vì vậy mới có `mfF[cj]fF`.

### 5.2. Ngữ nghĩa của `[cj]`

**Bước 1: tách `Y`.** Expand `R`=`WW`, `B`=`FF`, `Q`=`WWFF`, `K`=`WF`, `L`=`C`, `J`=`Z`. Với mỗi atom thu được, tập vector hướng $V$ lấy theo quy ước chữ hướng (mục 4.1). Vector $v \in V$ là vector bước của atom: quân nhảy dùng chính vector nhảy (ví dụ $N$ có $(1,2)$, $D$ có $(0,2)$), quân trượt dùng vector đơn vị (ví dụ $W$ có $(0,1)$).

Các nước đi nằm ở $s + a \cdot v$ và $h + b \cdot v$ với **hệ số nguyên** $a$, $b$ nhân vào $v$. Đây là hệ số trên vector, không phải số lần di chuyển của một quân nào. Hệ số tối đa của chặng tiếp cận là $A_{\max}$:

- $A_{\max} = 1$ nếu atom là quân nhảy (viết đơn, không số);
- $A_{\max} = k$ nếu atom có chữ số $k$ ($R4$ được hiểu là $W4$);
- $A_{\max} = \infty$ nếu atom là quân trượt (viết lặp hoặc đến từ `R`, `B`, `Q`).

Hệ số tối đa của chặng hạ cánh là $B_{\max} = n$ nếu có số $n$, ngược lại $B_{\max} = A_{\max}$ (kế thừa).

| Atom trong `Y` | $v$ | $A_{\max}$ | Các ô có thể là $h$ |
|---|---|---|---|
| `F` | $(\pm1,\pm1)$ | 1 | chỉ $s+v$ |
| `N` | $(\pm1,\pm2),(\pm2,\pm1)$ | 1 | chỉ $s+v$, ví dụ $s+(1,2)$ |
| `D` | $(\pm2,0),(0,\pm2)$ | 1 | chỉ $s+v$, ví dụ $s+(0,2)$ |
| `W3` | $(\pm1,0),(0,\pm1)$ | 3 | $s+v$, $s+2v$, $s+3v$ |
| `B` | $(\pm1,\pm1)$ | $\infty$ | $s+a \cdot v$ với mọi $a \ge 1$ |
| `NN` | $(\pm1,\pm2),\dots$ | $\infty$ | $s+a \cdot v$, ví dụ $s+(a,2a)$ |

**Bước 2: với mỗi atom và mỗi vector $v \in V$**, nước đi hợp lệ khi tồn tại số nguyên $a$ và $b$ với $1 \le a \le A_{\max}$, $1 \le b \le B_{\max}$ thỏa:

1. Ô $h = s + a \cdot v$ nằm trong bàn cờ và có **quân địch** (quân bị bắt).
2. Mọi ô $s + i \cdot v$ với $1 \le i < a$ đều **trống**.
3. Ô $l = h + b \cdot v$ nằm trong bàn cờ.
4. Mọi ô $h + i \cdot v$ với $1 \le i < b$ đều **trống**.
5. Ô $l$ thỏa modality hạ cánh: `m` (mặc định) thì trống; `mc` thì trống hoặc có quân địch; `c` thì có quân địch.

Ở đây $s$ là ô quân đang đứng và $v$ là vector bước của atom (ví dụ $(0,2)$ với `D`, $(1,2)$ với một nước `N`).

**Kết quả:** quân đi từ $s$ tới $l$; quân ở $h$ bị gỡ; nếu $l$ có quân địch (chỉ xảy ra với `mc`, `c`) thì quân đó cũng bị gỡ (bắt thay thế).

**Các điểm biên được chốt:**

1. **Cùng vector:** chặng tiếp cận và chặng hạ cánh dùng đúng một vector $v$; không đổi hướng giữa hai chặng. Với quân nhảy xiên như `N`, điều này nghĩa là $l = s + 2v$.
2. **Quân bạn và quân địch khác đều chặn đường:** các ô trong điều kiện 2 và 4 phải trống, không phải "không có quân bạn".
3. **Hai quân địch liền nhau:** với `m` (mặc định) không nhảy được vì ô hạ cánh bị chiếm; với `mc` thì hạ cánh lên quân thứ hai và bắt cả hai.
4. **Không có quân để nhảy thì không có nước đi.** `[cj]` không bao giờ là nước đi không bắt.
5. **Quân nhảy có vector dài** như `D`, `A`: $h$ cách $s$ đúng một vector và $l$ cách $h$ thêm một vector. Ô nằm giữa mỗi bước nhảy không được xét (trừ khi `Y` có chữ `n`, lúc đó áp dụng cho từng bước như định nghĩa thông thường).
6. **Ô ngoài bàn cờ:** hạ cánh ra ngoài thì nước đi không hợp lệ.
7. **Chỉ một cú nhảy.** Bắt liên tiếp nhiều cú (như cờ đam) nối bằng toán tử `--` của Bex. Luật bắt buộc bắt, bắt nhiều quân nhất, thăng cấp giữa chừng nằm ở tầng luật chơi, không thuộc ký hiệu.
8. **Quân bị bắt chỉ bị gỡ khi nước đi kết thúc.**

### 5.3. Ngữ nghĩa của `[cl]`

`[cl…]Y` là chuỗi gồm $m \ge 1$ cú nhảy cùng vector $v$:

1. Mỗi cú nhảy là một `[cj]` theo mục 5.2.
2. Mọi cú nhảy trừ cú cuối: ô hạ cánh phải **trống** (ép modality `m`) và hệ số hạ cánh tối đa là $B_{\max}$. Ô hạ cánh của cú thứ $i$ là ô xuất phát của cú thứ $i+1$.
3. Cú cuối cùng dùng đúng modality `landing` và số $n$ đã viết trong ngoặc.
4. Quân bị bắt là tất cả các ô $h$ của mọi cú nhảy; mỗi quân chỉ bị bắt một lần (tự nhiên, vì cùng vector).
5. Số cú nhảy $m$ không giới hạn. Giới hạn số cú nhảy (như `(cQ-mQ)4` của Long Leaper trong Betza 2.0) chưa có cú pháp riêng.

Hiện chưa có quân nào trong danh sách dùng `[cl]` theo nghĩa này. Long Leaper của Ultima (`mQ+[cl]Q`) nằm ngoài bảng Wikipedia.

### 5.4. Áp dụng cho 21 mục của Wikipedia

| Quân | Trò chơi | Ký hiệu Wikipedia | Ký hiệu mới |
|---|---|---|---|
| Checker Man | cờ đam Mỹ/Tây Ban Nha/Ý | `mfF[cl]fF` | `mfF[cj]fF` |
| Checker Man | Old German | `mfF[cl]fF[cl]fsW` | `mfF[cj]fF[cj]fsW` |
| Checker Man | Ossetian (Tama) | `mfK[cl]K` | `mfK[cj]K` |
| Checker Man | phần lớn các loại đam | `mfF[cl]F` | `mfF[cj]F` |
| Checker Man | Loca | `mfF[cl]B` | `mfF[cj]B` |
| Checker Man | Frisian | `mfF[cl]F[cl]D` | `mfF[cj]F[cj]D` |
| Checker Man | Hy Lạp/Thổ Nhĩ Kỳ | `mfsW[cl]fsW` | `mfsW[cj]fsW` |
| Checker Man | Croda, Dameo | `mfK[cl]fsW` | `mfK[cj]fsW` |
| Checker Man | Armenia | `mfKmsW[cl]fsW` | `mfKmsW[cj]fsW` |
| Checker Man | Sri Lankan Dām | `mF[cl]F` | `mfF[cj]F` (thêm `f` bị thiếu so với mô tả "forward") |
| Checker Man | Alquerque | `mK[cl]K` | `mK[cj]K` |
| Checker King | Mỹ/Ý | `mF[cl]F` | `mF[cj]F` |
| Checker King | Old German | `mK[cl]K or mQ[cl]Q` | `mK[cj]K or mQ[cj]Q` |
| Checker King | đam quốc tế (bay) | `mB[cl]B` | `mB[cj]B` |
| Checker King | Loca | `mF[cl]B` | `mF[cj]B` |
| Checker King | Frisian | `mB[cl]B[cl]DD` | `mB[cj]B[cj]DD` |
| Checker King | Hy Lạp/Thổ Nhĩ Kỳ, Harzdame | `mR[cl]R` | `mR[cj]R` |
| Checker King | Armenia | `mQ[cl]R` | `mQ[cj]R` |
| Dabbaba-checker | | `D[cl]W` | `D[cjmc]W` |
| Locust | bài cờ | `mQ[cl]Q` | `mQ[cj1]Q` |
| Rook (Quang Trung) | Quang Trung Chess | `mR[cl]R` | `mR[cj1]R` |

Ghi chú:

- Các dòng đam khớp mô tả với hệ số hạ cánh tối đa kế thừa: quân đi một ô thì hạ cánh ngay sau quân bị bắt; quân bay (`B`, `R`, `Q`) thì hạ cánh bao xa cũng được.
- **Frisian:** `[cj]D` nghĩa là hurdle ở ô $s + (0,2)$ và hạ cánh ở $s + (0,4)$. Đúng với bàn cờ một màu ô, nơi ô kề theo ngang/dọc cách nhau 2 ô.
- **Locust** và **Rook (Quang Trung)** dùng `1` để hạ cánh ngay sau quân bị bắt; **Dabbaba-checker** dùng `mc` để ô hạ cánh có thể có quân địch (bắt thêm quân thứ hai).
- Hai dòng Loca khớp mô tả "move short, capture long": quân bắt đi qua bao nhiêu ô trống cũng được cả trước lẫn sau quân bị nhảy qua. Phần nhiều lần nhảy liên tiếp của Loca nằm ngoài ký hiệu.

### 5.5. Ví dụ tính tay

- `mfF[cj]fF` (đam Mỹ): từ ô $s$, hai vector $v = (-1,1)$ và $v = (1,1)$, $A_{\max} = B_{\max} = 1$. Nước bắt khi ô $s + v$ có quân địch và ô $s + 2v$ trống.
- `mB[cj]B` (quân bay): bốn vector chéo, $A_{\max} = B_{\max} = \infty$. Quân trượt qua các ô trống tới quân địch đầu tiên, rồi hạ cánh vào bất kỳ ô trống nào liền sau nó trên cùng đường chéo (dừng khi gặp ô có quân).
- `mQ[cj1]Q` (Locust): tám vector, $A_{\max} = \infty$, $B_{\max} = 1$. Quân trượt tới quân địch đầu tiên rồi hạ cánh đúng ô liền sau, nếu ô đó trống.
- `D[cjmc]W` (Dabbaba-checker): bốn vector $W$, $A_{\max} = B_{\max} = 1$. Quân địch ở ô kề thì bị bắt; hạ cánh ở ô thứ hai, ô đó trống hoặc có quân địch (bị bắt thêm). Thành phần `D` đứng trước vẫn cho nước nhảy 2 ô thông thường.
- `mfF[cj]F[cj]D` (Frisian): `[cj]F` bắt chéo (hạ cánh $s + 2v$ với $v = (\pm 1, \pm 1)$) và `[cj]D` bắt ngang/dọc ($h = s + (0,\pm 2)$, $l = s + (0,\pm 4)$ hoặc tương tự theo trục ngang).

### 5.6. Quan hệ với chuỗi nước

Với cùng một vector hướng cho hai chặng, `[cj φ n]Y` tương đương `cY` rồi `φ Y′`, trong đó `Y′` là `Y` với hệ số tối đa $B_{\max}$ và hướng cố định theo chặng đầu. Cách viết `cY-mY` (Betza 2.0 qua Wikipedia, MBN `fcF-mF`) khớp với `[cj]Y` khi hiểu "cùng hướng" là *cùng vector*; nếu hiểu là "cùng hướng chung" như Bex (`-`) thì khác nhau với các atom xiên và với atom chéo/thẳng dùng lẫn nhau (ví dụ chặng đầu theo đường chéo, chặng sau theo bước thẳng).

## 6. Định nghĩa `t[A B]` (nước đi bẻ góc)

Quy ước tự thiết kế, chốt theo **hướng bàn cờ** cho chữ hướng ở chặng thứ hai. `t[A B]` là cách Betza viết "đi một bước `A`, rồi tiếp tục theo `B`" (ví dụ Gryphon `t[FR]`: một bước chéo rồi trượt như Xe ra xa).

### 6.1. Ngữ nghĩa

Gọi $s$ là ô xuất phát.

1. **Chặng 1:** một bước theo atom `A` (kèm chữ hướng của `A` nếu có, đọc theo mục 4.1). Gọi $u$ là vector bước và $p = s + u$ là ô đến. Nếu $p$ có quân bạn thì không đi được; nếu $p$ có quân địch thì chỉ bắt và dừng.
2. **Dừng ở chặng 1 là hợp lệ:** nước đi có thể kết thúc ngay tại $p$ (nếu $p$ trống hoặc có quân địch). Chặng 2 là tùy chọn. *(Theo mô tả Piececlopedia "optionally continuing" và Fairy-Stockfish; chưa đọc được bài gốc của Betza.)*
3. **Chặng 2 chỉ đi tiếp khi $p$ trống.** Hướng của chặng 2:
   - Nếu `B` **có chữ hướng**: tập hướng $V(B)$ lấy theo mục 4.1 trong **hệ tọa độ bàn cờ** (không tính theo hướng chặng 1). Mặc định "ra xa" **không** áp dụng.
   - Nếu `B` **không có chữ hướng**: các hướng $d$ của `B` thỏa $u \cdot d > 0$ ("ra xa": mỗi bước làm khoảng cách tới $s$ tăng).
4. **Đi theo hướng $d$:** `B` là quân trượt thì đi $c \ge 1$ bước, các ô đi qua phải trống, ô cuối trống hoặc có quân địch (bắt). `B` là quân nhảy thì đúng một bước.

**Vì sao chữ hướng ghi đè "ra xa".** Cách này biểu diễn được cả hai ý đồ khác nhau mà các nguồn đều dùng: "tiếp tục *ra xa*" (không có chữ hướng) và "tiếp tục *tiến*" theo bàn cờ (có chữ hướng). Ví dụ Snake "continues outwards", còn Vivi "continues forwards" (hai chữ này khác nghĩa trong cùng một bài của Betza). Nếu chữ hướng chỉ lọc thêm trên tập "ra xa" thì nhánh lùi của Vivi mất chặng 2.

### 6.2. Áp dụng cho 5 quân có chữ hướng trong `t[...]`

| Quân | Ký hiệu cũ | Ký hiệu mới | Kết quả theo định nghĩa |
|---|---|---|---|
| Ship, Twin Tower | `t[FvR]` | `t[fFfR]t[bFbR]` | Một bước chéo tiến rồi trượt thẳng lên; hoặc một bước chéo lùi rồi trượt thẳng xuống (ra xa theo cột). Giữ đúng mô tả "vertically outwards". Viết `t[FvR]` sẽ cho cả hướng vào trong (thêm các ô $(\pm 1, 0)$), vì chữ `v` ghi đè "ra xa" |
| Snake | `t[vWB]` | giữ nguyên | Một bước tiến hoặc lùi rồi trượt chéo ra xa. `B` không có chữ hướng nên dùng mặc định "ra xa" |
| Vivi | `t[vWfB]` | giữ nguyên | Một bước tiến hoặc lùi, rồi trượt chéo **tiến** theo bàn cờ (cả sau khi lùi một bước). Khớp mô tả của Betza: "forwards or backwards as Wazir then continues forwards as a Bishop" |
| Unicornio (Grant Acedrex) | `t[NB] (or t[NfB])` | `t[NB]` | Bước Mã rồi trượt chéo ra xa. Đã chốt chọn `t[NB]`; Wikipedia cũng ghi đây là cách hiểu "most probably", cách hiểu thay thế `t[NfB]` bị bỏ |

### 6.3. Điểm chưa chắc

- Việc dừng ở chặng 1 có hợp lệ (mục 6.1, điểm 2) lấy từ mô tả Gryphon của Piececlopedia và Fairy-Stockfish; các trang gốc của Betza chặn truy cập tự động nên chưa kiểm chứng.
- Nhánh lùi của Vivi (bước lùi rồi vẫn trượt chéo tiến) dựa vào câu mô tả của Betza qua tóm tắt tìm kiếm, chưa đọc nguyên bài.
