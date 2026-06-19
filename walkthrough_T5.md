# Walkthrough — Phase T5: Python reader + round-trip C++↔Python (chốt 3 quy ước)

> Ngày: 2026-06-19 · Dự án: FairyZero (`custom_engine`) — biến thể cờ 10×10.
> Phạm vi đợt này: hiện thực hóa **milestone T5** trong `implementation_plan phase training_1.md` (mục 8.1–8.3).
> DoD: tensor planes / π / z / orig_q / policy_kld **khớp bit & giá trị 100% giữa C++ và Python**; tích hợp Shuffle Buffer (8.2.2) + Down-sampling (8.2.3).
> Kết quả: ✅ Hoàn thành — và phép round-trip đã **phát hiện + sửa 2 lỗi NGẦM nghiêm trọng** mà mạng ngẫu nhiên che giấu. Tiếp nối T1–T4 (`walkthrough_3/4/5/6.md`).

---

## 0. T5 là gì & vì sao là "lưới an toàn" của toàn pipeline

Module A (C++, T1–T4) sinh dữ liệu `.gz`. Module B (Python/PyTorch) sẽ huấn luyện. **T5 là cây cầu** giữa hai phía — phải đảm bảo **3 quy ước bất biến** khớp tuyệt đối, nếu không mạng sẽ học sai mà không báo lỗi:

1. **policy index = `MoveToNNIndex`** (`probabilities[10600]`).
2. **value order = [Win, Draw, Loss]** từ góc side-to-move (`q = win − loss`).
3. **input planes = `[226,10,10]`**; bit ô cờ `s = rank*12 + file` (stride 12 của Stockfish); aux planes tái tạo từ scalar; castling: us→rank0, them→rank9.

**Tại sao T5 cực kỳ quan trọng:** với mạng `weights_0_elo` ngẫu nhiên, MCTS vẫn "chạy" và sinh nước hợp lệ (nước đi đến từ *movegen*, KHÔNG phải NN). Nghĩa là **một lỗi encode tensor đầu vào hoàn toàn vô hình** ở mọi test trước đó. T5 — bằng cách so khớp bit-exact giữa tái tạo Python và `UnpackInputPlanes` của C++ — là test ĐẦU TIÊN thực sự kiểm tra nội dung tensor. Và nó đã bắt được lỗi.

---

## 1. Thiết kế phép round-trip

Ý tưởng: **C++ phát "ground-truth", Python tái tạo rồi so khớp.**

- **Phía C++** (chế độ mới `--emit-roundtrip <prefix>`): với mỗi thế cờ, ghi RA HAI thứ cho CÙNG một vị trí:
  - `<prefix>_records.gz` — record `TrainingDataV1` (định dạng thưa, qua `EncodePlanesIntoRecord` + writer T1).
  - `<prefix>_dense.bin` — tensor `[226*100]` float lấy từ `UnpackInputPlanes(EncodePositionForNN(...))` — **chính xác cái NN nhìn thấy lúc inference**.
- **Phía Python**: đọc record thưa → `reconstruct_planes` dựng `[226,10,10]` → so với `_dense.bin`. Khớp ⇒ cả 3 quy ước đúng.

Chọn 2 thế cờ để phủ mọi loại plane:
- **Case 0 — startpos (Trắng đi):** phủ piece planes (nhiều quân), castling (quyền `BIbi` → xe ở file b,i), checks (7+7), board-edge, side=0. KHÔNG có ep (kiểm ep_mask=0 dựng ra plane rỗng).
- **Case 1 — Đen đi, en-passant Sergeant đang hoạt động:** từ FEN `5k4/.../1s8/.../S9/.../5K4 w - - 7+7 0 1`, áp nước `a3c5` (Sergeant đi đôi chéo) → ep_squares {b4,c5}. Phủ ep plane (khác rỗng), side=1, **kiểm logic lật bàn cờ cho quân Đen**, castling rỗng (file=0xFF).

---

## 2. Các file đã tạo / sửa

### 2.1. `[NEW] python/trainingdata_reader.py`
- **`_FMT`** — chuỗi `struct` little-endian, packed, khớp `TrainingDataV1` (#pragma pack(1)):
  `"<" + "II" + "10600f" + "432Q" + "5B" + "2Q" + "3B" + "11f" + "I" + "2H"` → `struct.calcsize == 45940` (assert).
- **`unpack_record(buf)`** — bung 1 record 45940 byte thành dict (version, probabilities[10600], piece_planes[432 u64], rule50, 4×castling-file, ep_mask[2], checks×2, side, các cặp q/d, policy_kld, visits, played/best_idx).
- **`reconstruct_planes(rec) -> [226,10,10] float32`** — tái dựng tensor:
  - 216 piece planes: bung mask `s = rank*12+file`, set 1.0 (lọc file/rank ≥ 10 = padding).
  - aux 4 = ep plane (từ ep_mask).
  - aux 0..3 = castling: `files=[us_ooo,us_oo,them_ooo,them_oo]`, `ranks=[0,0,9,9]` → set 1.0 tại (rank, file) nếu ≠ 0xFF.
  - aux 5 = rule50/100 (toàn plane); aux 7 = board-edge (toàn 1.0); aux 8/9 = checks/7.
- **`read_records(filename)`** — đọc tuần tự record từ `.gz` (hoặc `.bin` thô).
- **`ShuffleBuffer(capacity)`** — Fisher-Yates streaming (port từ lc0 `shufflebuffer.py`): `insert_or_replace` (đầy thì trả phần tử ngẫu nhiên bị thay), `extract`.
- **`downsample(records, keep_prob)`** — giữ mỗi record với xác suất p (giảm tương quan trong ván).

### 2.2. `[NEW] python/test_roundtrip.py`
Đọc `_records.gz` + `_dense.bin`, với mỗi case: `reconstruct_planes` rồi `np.allclose(recon, gt, atol=1e-6)`. Nếu lệch → in các ô sai (plane, rank, file, recon vs gt). Đồng thời kiểm field (sum(pi)=1, result_q, orig_q, policy_kld, visits, các index π synthetic). Cuối cùng smoke-test `ShuffleBuffer` (bảo toàn đủ phần tử) + `downsample`.

### 2.3. `[MODIFY] src/main.cc` — `run_roundtrip_emit(prefix)` + cờ `--emit-roundtrip`
Với mỗi case: `EncodePositionForNN` → `UnpackInputPlanes` → ghi dense; rồi `EncodePlanesIntoRecord` + gán field synthetic (π[100]=0.25, π[2005]=0.75, result_q=−1, orig_q=0.123, kld=0.456, visits=777) → `WriteChunk`. Hai thế cờ heap-alloc (`make_unique<ChessBoard>/<PositionHistory>`).

---

## 3. 🔴 Hai lỗi NGẦM nghiêm trọng do round-trip phát hiện

Lần chạy đầu **FAIL** với pattern lạ: pawn ở rank 2 lại hiện ở rank 7; gt dense piece planes **toàn 0** (chỉ aux planes khác 0). Dump bit chi tiết hé lộ 2 lỗi độc lập:

### Lỗi #1 — NN MÙ HOÀN TOÀN (nghiêm trọng nhất)
`encoder.cc` khởi tạo:
```cpp
InputPlane zero_plane;
zero_plane.value = 0.0f;     // <-- LỖI
output_planes->fill(zero_plane);
```
Rồi các plane **nhị phân** (quân cờ dòng 116, nhập thành 139–154, en-passant 168) **chỉ `mask |= ...`, KHÔNG đặt lại `value`** → value giữ 0.0. Mà `UnpackInputPlanes` ghi `dest[idx] = plane.value` (dòng 240) → **mọi ô có quân bung ra 0.0**.

⟹ **Tensor đầu vào NN có TOÀN 0 ở mọi plane quân cờ/nhập thành/ep. Mạng chưa từng "thấy" một quân nào.** Lỗi ảnh hưởng cả **inference** lẫn **dữ liệu train**. Bị che giấu hoàn toàn vì mạng ngẫu nhiên + nước đi đến từ movegen.

Bằng chứng: gt dense case 0 có đúng 300 ô khác 0 = board-edge(100) + 2 check planes(100×2) — toàn bộ là aux planes dùng `.Fill()` (có set value), còn piece planes = 0.

**Sửa:** `zero_plane.value = 1.0f;` — khôi phục đúng default của `InputPlane` (vốn là 1.0). Các plane vô hướng (rule50/checks/biên/lặp) tự `Fill()` đè value của chúng; các plane rỗng có `mask=0` nên `UnpackInputPlanes` bỏ qua (`if(!mask) continue`). An toàn.

### Lỗi #2 — Tráo word lo/hi khi serialize mask 128-bit
`Stockfish::Bitboard` ở build này KHÔNG phải `__int128` mà là `struct { uint64_t b64[2]; }` (vì macro `IS_64BIT` không được định nghĩa → rơi vào nhánh struct của `types.h`). Trong struct: **`b64[0] = HIGH 64 bit, b64[1] = LOW 64 bit`** (xem ctor `Bitboard(hi, lo)` và `operator ull` trả `b64[1]`).

`EncodePlanesIntoRecord` cũ dùng `memcpy(&mask, 16)` → lưu thứ tự [b64[0]=high, b64[1]=low]. Python đọc word[0] là "low" → **tráo**. Pawn ở square 25 (low word) bị đọc thành 89 (= 25 + 64).

**Sửa:** trích xuất tường minh, định nghĩa thứ tự **trên đĩa** độc lập layout nội bộ:
```cpp
const Stockfish::Bitboard low64 = Stockfish::Bitboard(0xFFFFFFFFFFFFFFFFULL);
out[0] = static_cast<uint64_t>(m & low64);  // squares 0-63
out[1] = static_cast<uint64_t>(m >> 64);    // squares 64-127
```
Đúng cho cả `struct` lẫn `__int128`; Python đọc word[0]=low → khớp thứ tự `pop_lsb` của `UnpackInputPlanes`.

### Lỗi #3 (hệ quả) — TEST 5 viết theo hành vi LỖI cũ
TEST 5 (`main.cc`) kỳ vọng "plane 1 (us KNIGHT) toàn 0.0" — sai, vì startpos có 2 Mã trắng ở e2,f2 (tensor idx 14,15). Trước đây "đúng" chỉ vì lỗi value=0. Sau khi sửa #1, plane 1 đúng = 1.0 tại 14,15 → TEST 5 báo lỗi. **Cập nhật kỳ vọng TEST 5** để kiểm Mã ở idx 14,15 = 1.0 (giờ TEST 5 trực tiếp kiểm encoding quân — mạnh hơn trước).

---

## 4. Build & chạy (PowerShell)

```
meson compile -C build           ->  [Linking target custom_engine.exe]
.\build\custom_engine.exe --emit-roundtrip python\rt
   -> python\rt_records.gz (362 B) + python\rt_dense.bin (180800 = 2*226*100*4)
python python\test_roundtrip.py
```
Kết quả sau khi sửa:
```
RECORD_SIZE = 45940 (expect 45940)
Loaded 2 cases from rt_records.gz
[OK] case 0: planes match exactly | side_to_move=0 rule50=0 checks=(7,7) castle_files=(1,8,1,8) non-empty planes=31 | sum(pi)=1.0000 result_q=-1.0 orig_q=0.123 kld=0.456 visits=777
[OK] case 1: planes match exactly | side_to_move=1 rule50=0 checks=(7,7) castle_files=(255,255,255,255) non-empty planes=12 | sum(pi)=1.0000 ...
[OK] ShuffleBuffer preserved all 10 items; downsample(0.5) kept ~479/1000
[PASS] T5 round-trip: Python reconstruction matches C++ UnpackInputPlanes exactly; record fields unpack correctly.
```
- `castle_files=(1,8,1,8)` = xe ở file b(1),i(8) cho cả us/them → đúng quyền `BIbi` + quy ước us→rank0, them→rank9.
- case 1 `castle_files=(255,...)` = không quyền nhập thành (FEN `- `); ep plane khác rỗng (đã khớp).

### Hồi quy (vì sửa encoder ảnh hưởng cả inference)
```
--test-board  : TEST 5 (encoder) ✅, TEST 7 (castling) ✅, ALL CHESSBOARD BRIDGE TESTS PASSED
--test-policy : POLICY BIJECTION TEST PASSED ✅
--test-extract: T2 (pi/kld/z) ✅
```

---

## 5. Đối chiếu DoD T5

| Tiêu chí (plan) | Trạng thái |
|-----------------|-----------|
| Tensor planes khớp bit/giá trị C++↔Python | ✅ (startpos + ep; gồm tái tạo castling us→rank0/them→rank9) |
| π, z, orig_q, policy_kld khớp | ✅ (field unpack đúng) |
| Shuffle Buffer (8.2.2) | ✅ (bảo toàn mọi phần tử) |
| Down-sampling (8.2.3) | ✅ |
| Không vỡ build / không hồi quy | ✅ (board/policy/extract pass) |

---

## 6. Bảng quyết định kỹ thuật & lý do

| Quyết định | Lý do |
|-----------|-------|
| C++ phát cả record + dense ground-truth | Round-trip bit-exact so với chính `UnpackInputPlanes` (cái NN thấy) |
| Sửa #1: `zero_plane.value = 1.0f` | Khôi phục default; plane nhị phân chỉ set mask nên value mặc định phải là 1.0 |
| Sửa #2: split bằng shift/mask (không memcpy) | Định dạng đĩa word0=low cố định, độc lập layout `Bitboard` (struct/`__int128`) |
| Sửa #3: cập nhật TEST 5 kỳ vọng | Test cũ dựa trên hành vi lỗi; nay kiểm encoding quân thật (mạnh hơn) |
| Reader giữ scalar THÔ, dựng plane ở Python | Khớp đúng `EncodePlanesIntoRecord`; gọn + linh hoạt Chess960 |
| 2 case (startpos + ep, trắng + đen) | Phủ piece/castling/checks/edge + ep + logic lật cho quân Đen |
| numpy cho so khớp | Tiện `allclose` + dùng lại cho T6 (PyTorch) |

---

## 7. Trạng thái & việc tiếp theo

- **CHƯA commit.** File mới/đổi: `python/trainingdata_reader.py`, `python/test_roundtrip.py` (MỚI); `src/lczero_chess/chess/encoder.cc`, `src/lczero_chess/selfplay/training_extract.cc`, `src/main.cc` (SỬA). `python/rt_*.gz/.bin` là fixture test (tái tạo bằng `--emit-roundtrip`).
- **Ý nghĩa:** 2 lỗi #1/#2 nếu lọt qua sẽ phá hỏng toàn bộ huấn luyện (mạng học trên input mù). T5 chặn lại đúng lúc — **giá trị cốt lõi của round-trip test**. Sửa #1 cũng cải thiện chất lượng inference của engine ngay lập tức.
- **Cần `numpy`** (đã có 2.2.6) cho phía Python.
- **Bước tiếp theo — T6:** model PyTorch **10×128 ResNet** (input 226, policy head 10600, value head WDL softmax in-graph), loss (policy CE + value + qMix), SWA, export ONNX khớp đúng I/O contract của engine. `trainingdata_reader.py` ở T5 là đầu vào trực tiếp cho dataset pipeline T6.
- Sau đó: **T6.5** (port Linux/CUDA cho Colab), **T7** (vòng lặp AlphaZero đầy đủ).

---

## 8. Cách chạy lại (ghi nhớ)
```powershell
cd D:\chess_variant\custom_engine
meson compile -C build
.\build\custom_engine.exe --emit-roundtrip python\rt
& "C:\Users\7\AppData\Local\Programs\Python\Python313\python.exe" python\test_roundtrip.py   # T5
.\build\custom_engine.exe --test-board     # hồi quy encoder (TEST 5) + castling (TEST 7)
.\build\custom_engine.exe --test-policy     # MoveToNNIndex bijection
```
> Engine chạy bằng PowerShell (có MSYS2 ucrt64 trên PATH). Python dùng Python313 (đã có numpy).
