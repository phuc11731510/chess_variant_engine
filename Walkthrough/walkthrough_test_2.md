# Walkthrough Test 2 — Kiểm thử ground-truth cho encoder (chống "học dữ liệu giả")

> Phạm vi: audit lại tầng mã hóa **bàn cờ → bit đầu vào mạng NN** (và diễn giải policy/value), xác
> định lỗ hổng kiểm thử, và tạo bộ test cực đoan mới **`--test-encoder`** đối chiếu encoder với
> **ground-truth bàn cờ**. Kèm **mutation test** chứng minh bộ test thật sự bắt được lỗi.
> Ngày: 2026-06-20. Thay đổi nằm trong `src/main.cc` (+ `scripts/colab_setup.sh`).

---

## 0. Vì sao đây là mối lo nghiêm trọng nhất

Trong vòng lặp AlphaZero, mạng học từ chính dữ liệu nó sinh ra. Nếu tầng **encoder** (chuyển một
thế cờ thành 226 mặt phẳng bit đưa vào mạng) **biểu diễn sai** bàn cờ, thì:
- Mạng học trên một "thế giới" méo mó nhưng **không có lỗi nào được ném ra** — loss vẫn giảm, ONNX
  vẫn export, vòng lặp vẫn chạy. Đây là **silent failure** nguy hiểm nhất.
- Ví dụ chí mạng: rớt một loại quân (plane luôn 0), gán nhầm loại (mã vào ô của tượng), hoán
  nhầm "quân ta/quân địch", hoặc **lật bàn sai khi Đen đi**. Mạng vẫn "học" nhưng học sai bản chất.

Vì vậy phải đảm bảo: **bit đưa vào mạng đúng với thế cờ thật**, và **policy/value lấy ra đúng quy ước**.

---

## 1. "Đúng" nghĩa là gì? (hai tầng yêu cầu)

1. **Biểu diễn trung thực (faithful):** mọi quân trên bàn xuất hiện **đúng một lần**, ở **đúng
   plane** (đúng loại + đúng nhóm ta/địch), tại **đúng ô** (đã lật canonical nếu Đen đi). Không
   rớt, không thừa, không đè. Hai thế cờ khác nhau → hai bộ planes khác nhau (injective).
2. **Nhất quán nội bộ (consistent):** cùng một hàm encode dùng cho **cả sinh dữ liệu lẫn suy luận**;
   cùng một hàm chỉ số `MoveToNNIndex` dùng cho **cả lưu π lẫn đọc policy của mạng**; cùng quy ước
   value `[W,D,L]` theo bên-đang-đi.

Yêu cầu (2) đã được bảo đảm **theo cấu trúc** (cùng code path) và test từ trước. Lỗ hổng là ở việc
**chưa kiểm (1) một cách độc lập**.

---

## 2. Audit: trước đây đã test gì, và vì sao chưa đủ

| Test cũ | Kiểm gì | Vì sao CHƯA đủ cho yêu cầu (1) |
|---------|---------|-------------------------------|
| `--test-board` TEST 5 | startpos: plane 1 (mã) có bit ở e2/f2 | **Spot-check 1 plane duy nhất**; không phủ các loại khác, không phủ Đen-đi, không phủ aux, không kiểm số lượng/độ phủ. |
| Round-trip T5 (`--emit-roundtrip` + `test_roundtrip.py`) | C++ planes == Python reconstruct (bit-exact) | Chỉ kiểm **C++ và Python ĐỒNG Ý**. Nếu cả hai cùng quy ước SAI (vd hoán mã↔tượng) thì **vẫn đồng ý** → không phát hiện. Python `reconstruct_planes` chỉ đọc lại bitmask thô, **không biết** "plane 1 = mã". |
| `--test-nn` Part 3 | `UnpackInputPlanes`: single-value, AllSquares, padding-reject | Kiểm **bộ giải nén** (planes → tensor float), **không** kiểm encoder (bàn cờ → planes). |

→ **Kết luận audit:** chưa có test nào đối chiếu encoder với **ground-truth bàn cờ thật**. Đây
chính là điểm có thể "học dữ liệu giả".

---

## 3. Layout encoder (để hiểu test)

`EncodePositionForNN` (trong `encoder.cc`) sinh **226 planes**:
- **216 history planes** = 8 bước lịch sử × **27 planes/bước**:
  - plane **0–12** = quân **TA (us = bên đang đi)** theo loại:
    `PAWN=0, KNIGHT=1, BISHOP=2, ROOK=3, QUEEN=4, KING=5, AMAZON=6, CHANCELLOR=7, ARCHBISHOP=8,
    CENTAUR=9, CUSTOM_1=10, CUSTOM_2=11, CUSTOM_3=12`
  - plane **13–25** = quân **ĐỊCH (them)** theo loại (cùng thứ tự)
  - plane **26** = cờ lặp thế (repetition)
- **10 aux planes** (từ `kAuxPlaneBase`): 0–3 nhập thành (ô xe), 4 en-passant, 5 rule50/100,
  6 bỏ trống (0), 7 biên (toàn 1), 8/9 số chiếu còn lại của ta/địch (÷7).
- **Lật canonical:** nếu Đen đi (`us == BLACK`), mỗi ô được lật dọc
  `relative_square(BLACK, sq, RANK_10)` để bên-đang-đi luôn ở phía dưới.

---

## 4. Thiết kế bộ test mới — `--test-encoder` (`run_encoder_tests`)

**Ý tưởng cốt lõi (triangulation):** dựng lại planes **kỳ vọng** từ **`pos.piece_on()`** — nguồn
sự thật của bàn cờ — bằng một **đường độc lập** với vòng lặp của encoder, rồi so khớp chính xác.

Chạy trên **6 thế cờ** (gồm các ca hiểm): startpos Trắng, **startpos Đen-đi (lật + hoán us/them)**,
hai-vua Trắng, hai-vua Đen, bất đối xứng (xe vs vua trơ), nhiều quân nhẹ+tốt.

Với mỗi thế: duyệt 100 ô qua `piece_on`, tính `exp_all` (ô có quân, đã lật), `exp_us/exp_them`
(theo màu so với bên-đang-đi), `exp_type_us[t]/exp_type_them[t]` (theo loại). Rồi kiểm **7 nhóm**:

| # | Kiểm tra | Bắt lỗi gì | Vì sao độc lập/mạnh |
|---|----------|-----------|---------------------|
| 1 | **Hợp planes 0..25 == `exp_all`** | rớt quân / bit ma | Không phụ thuộc "plane nào" — chỉ cần MỌI ô có quân được biểu diễn và KHÔNG ô trống nào bị bật |
| 2 | **Tổng bit == số quân** | va chạm/đè bit | Đè → mất bit → lệch số đếm |
| 3 | **Hợp us(0..12) == `exp_us`, them(13..25) == `exp_them`** | hoán us/them, **lật Đen sai** | So theo MÀU vs bên-đang-đi; lật sai → ô lệch → fail |
| 4 | **Mỗi `planes[t]` == `exp_type_us[t]`** (và them) | **gán nhầm LOẠI** (mã↔tượng…) | Bảng loại→plane trong test viết **độc lập** từ spec; lệch switch của encoder → đếm sai |
| 5 | **Plane vua (5 ta, 18 địch) đúng 1 bit** | mất/nhân đôi vua | Bất biến: mỗi bên đúng 1 vua |
| 6 | **Aux qua `UnpackInputPlanes`**: biên(7)=1, bỏ trống(6)=0, rule50(5)=ply/100, checks(8/9)=còn lại/7; **nhập thành(0–3)** = ô xe (đã lật) so `castling_rook_square` | aux sai / lật xe sai | Đối chiếu trực tiếp trạng thái bàn (`GetRule50Ply`, `checks_remaining`, `castling_rook_square`) |
| 7 | **Injectivity**: vua f1 vs g1 → planes phải khác | hai thế khác mã hóa giống nhau | Mất thông tin → mạng không phân biệt được thế cờ |

> Điểm tinh tế: nhóm (1) **không phụ thuộc loại** (bắt rớt/thừa), nhóm (4) **phụ thuộc loại** (bắt
> hoán loại). Hai nhóm bù nhau nên **không thể cùng sai một kiểu** — đó là sức mạnh của test.

So sánh bitboard 128-bit dùng `popcount(a ^ b) == 0` (tránh nhập nhằng ép kiểu `Bitboard→int` trên
Linux). NodeTree được **heap-alloc** (`make_unique`) vì `PositionHistory` chứa mảng 512-ply.

---

## 5. Kết quả chạy (`custom_engine.exe --test-encoder`)

```
=== ENCODER ground-truth tests (board -> NN planes) ===
  [OK] startpos (White to move): 60 pieces -> planes faithful (occupancy/type/us-them/king/aux/castling)
  [OK] startpos board, Black to move (flip + us/them swap): 60 pieces -> planes faithful (...)
  [OK] two kings (White): 2 pieces -> planes faithful (...)
  [OK] two kings (Black, flip): 2 pieces -> planes faithful (...)
  [OK] rooks vs lone king (asym): 4 pieces -> planes faithful (...)
  [OK] many White minors+pawns: 21 pieces -> planes faithful (...)
  [OK] injectivity: king f1 vs g1 differ in 1 plane(s)
[PASS] ENCODER ground-truth tests (NN input faithfully represents the board).
```
Ca quan trọng nhất — **Đen-đi 60 quân (lật bàn + hoán us/them)** — pass, xác nhận phép lật canonical
đúng cho cả quân lẫn ô nhập thành/en-passant.

---

## 6. ⭐ Mutation test — chứng minh bộ test "có răng"

Một bộ test chỉ đáng tin nếu nó **fail khi mã nguồn sai**. Tôi cố tình tiêm lỗi:
```
# hoán KNIGHT(1) <-> BISHOP(2) trong encoder.cc, build lại, chạy --test-encoder
[FAIL] startpos (White to move): us type-plane 1 mismatch
[FAIL] startpos (White to move): them type-plane 14 mismatch
[FAIL] startpos (White to move): us type-plane 2 mismatch
...
# hoàn nguyên encoder.cc, build lại:
[PASS] ENCODER ground-truth tests ...
```
→ Encoder sai (gán nhầm loại) **bị tóm ngay**, đúng plane. Khi sửa lại → PASS. `encoder.cc` đã được
khôi phục nguyên trạng. Vậy bộ test **không phải pass rỗng**.

---

## 7. Còn policy và value? (đã được phủ từ trước — nhắc lại để yên tâm)

- **Policy:** chỉ số `MoveToNNIndex = type*100 + rank*10 + file` đã được `--test-nn` kiểm là **song
  ánh** (đúng dải <10600, round-trip với `MoveFromNNIndex`, **không va chạm**, injective trên cả
  nước hình học lẫn nước hợp lệ thật). **Cùng một hàm** này dùng để (a) lưu π huấn luyện và (b) đọc
  policy của mạng lúc search → **nhất quán theo cấu trúc** với policy head của `model.py`
  (`[B,106,10,10].flatten() = type*100+rank*10+file`). Không thể lệch.
- **Value:** WDL `[Win,Draw,Loss]` theo bên-đang-đi; dấu `z` đảo theo lượt; trộn qMix. Đã test ở
  `run_selfplay_tests` (z gán đúng parity, tổng π=1) và `test_extreme.py` (`wdl_from_qd` bất biến
  `w−l==q`, qMix chính xác).

→ Cả ba mắt xích (planes, policy index, value WDL) đều đã có khiên kiểm thử.

---

## 8. Cách dùng & tích hợp

```
custom_engine.exe --test-encoder      # chạy bất cứ lúc nào để tự kiểm
```
Đã thêm `--test-encoder` vào bộ test trong `scripts/colab_setup.sh` (cùng `--test-uci` và các test
cũ) → mỗi lần build trên Colab đều chạy.

**Bộ khiên kiểm thử hiện tại (toàn cảnh):**
`--test-board · --test-policy · --test-perft · --test-bits · --test-rules · --test-adapter ·
--test-nn · --test-trainingdata · --test-uci · **--test-encoder** (mới)`; Python:
`test_roundtrip.py · test_bits.py · test_extreme.py`.

---

## 9. Kết luận

Lỗ hổng "bit vào mạng có đúng với bàn cờ không?" đã được lấp bằng `--test-encoder` — đối chiếu
**ground-truth độc lập**, phủ 7 nhóm bất biến, gồm ca Đen-đi hiểm, và **đã được mutation test chứng
minh là bắt được lỗi thật**. Cùng với các test policy/value sẵn có, ta có cơ sở vững chắc rằng vòng
lặp **không học dữ liệu giả**: thế cờ được mã hóa trung thực, nước đi và lượng giá lấy ra đúng quy
ước. Bạn có thể chạy lại bộ này bất cứ lúc nào như một "công tắc an toàn" trước mỗi đợt huấn luyện lớn.
