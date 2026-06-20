# Walkthrough — Phase T1: Training Data Record + Writer (Self-play data generation)

> Ngày: 2026-06-19 · Dự án: FairyZero (`custom_engine`) — biến thể cờ 10×10.
> Phạm vi đợt này: hiện thực hóa **milestone T1** trong `implementation_plan phase training_1.md`:
> "Định nghĩa cấu trúc record `TrainingDataV1` & Writer" với DoD = ghi/đọc khứ hồi khớp 100% bit, kích thước đúng **45940 bytes**.
> Kết quả: ✅ Hoàn thành và đã verify bằng test thực tế (PASS).

---

## 0. Bối cảnh & mục tiêu

T1 là viên gạch đầu tiên của Module A (sinh dữ liệu self-play bằng C++). Nó KHÔNG đụng tới MCTS/encoder — chỉ gồm:
1. **Định dạng record nhị phân** `TrainingDataV1` (một thế cờ = một record), đóng gói chặt (`#pragma pack(1)`) để Python `struct.unpack` đọc lại không lệch byte.
2. **Writer** ghi nhiều record ra một file (1 file/ván), nén gzip.
3. **Test khứ hồi** (round-trip): ghi → đọc lại → so khớp từng byte, và xác nhận `sizeof == 45940`.

Đây là "chốt chặn layout" quan trọng: nếu struct C++ và format Python lệch nhau dù 1 byte, mạng nơ-ron sẽ học sai mà không báo lỗi (silent corruption). `static_assert` + test bit-exact khóa điều này lại ngay từ đầu.

---

## 1. Khảo sát trước khi code

### 1.1. Build system (`meson.build`)
- Dự án build bằng **Meson + Ninja**, toolchain **MSYS2 UCRT64 (GCC/MinGW)** trên Windows.
- Flag sẵn có: `-DLARGEBOARDS -DALLVARS -DLCZERO_MCTS -DNDEBUG -mavx2 -mfma`, `cpp_std=gnu++20`.
- Nguồn được gom theo nhóm: `chess_sources`, `search_sources`, `neural_sources`, `engine_sources`; link `thread_dep` + `onnx_dep`.
- `inc_dirs` có `'src/lczero_chess'` → include kiểu `"trainingdata/writer.h"` sẽ resolve đúng.

### 1.2. zlib có sẵn không?
- Grep toàn dự án: **zlib CHƯA được link** (chỉ `incbin` cho NNUE, không liên quan).
- → Rủi ro: nếu ép link zlib mà máy không có thì **vỡ build** của người dùng.
- Quyết định: làm **Writer dual-mode** — gzip nếu có zlib (`HAVE_ZLIB`), nếu không thì ghi raw `.bin`. Đảm bảo build & test luôn chạy được bất kể zlib.

### 1.3. Cách wiring test
- Các test sẵn có (`run_ep_tests`, `run_board_tests`, `run_policy_tests`, `run_mcts_tests`) đều theo pattern: 1 hàm `run_*_tests()` + 1 cờ CLI `--test-*` parse trong `main()`. → Theo đúng pattern này, thêm `--test-trainingdata`.

---

## 2. Các file đã tạo / sửa

### 2.1. `[NEW] src/lczero_chess/trainingdata/trainingdata_v1.h`
Định nghĩa struct record. Các điểm thiết kế:

- **`#pragma pack(push, 1)` / `pack(pop)`** quanh struct → không có padding chèn giữa các field; layout nhị phân = đúng tổng kích thước field.
- **`static_assert(sizeof(TrainingDataV1) == 45940, ...)`** ngay sau struct → nếu sau này ai đổi field làm lệch layout, **compile sẽ fail ngay** (không để lọt thành silent bug ở Python).
- Hằng số đặt tên rõ:
  - `kTrainingDataVersion = 1`, `kInputFormat10x10 = 1`
  - `kNoCastlingFile = 0xFF` (sentinel "mất quyền nhập thành")
  - `kPolicySize = 10600`, `kHistoryPlanes = 216`
- **Bố cục field (đúng mục A1 của plan):**

| Nhóm | Field | Bytes |
|------|-------|-------|
| Header | `version`, `input_format` (uint32×2) | 8 |
| Policy | `probabilities[10600]` (float) | 42400 |
| Planes (thưa) | `piece_planes[216][2]` (uint64) = 216 mask 128-bit | 3456 |
| Scalar aux | `rule50_count` (1) + 4×castling-file (4) + `ep_mask[2]` (16) + 2×checks (2) + `side_to_move` (1) | 24 |
| Value targets | `result_q/d`, `root_q/d`, `best_q/d`, `played_q/d`, `orig_q/d` (10 float) + `policy_kld` (1 float) + `visits` (uint32) | 48 |
| Index | `played_idx`, `best_idx` (uint16×2) | 4 |
| **Tổng** | | **45940** |

- **Quyết định lưu plane THƯA bằng bitboard mask** (216×16B = 3.5KB) thay vì dense 226×100 float (90KB) — comment giải thích rõ trong file. Aux plane dạng scalar (rule50/checks/board-edge) tái tạo ở Python, không lưu mask.
- **Castling lưu FILE-INDEX (0-9) thay vì boolean** — để hỗ trợ thế cờ khởi đầu Chess960-10×10 sau này (xe nhập thành ở cột bất kỳ). Comment ghi rõ quy ước Python reader: us → rank 0, them → rank 9.
- Comment đầu file liệt kê **3 quy ước phải khớp Python** (policy index = MoveToNNIndex; value = [W,D,L] side-to-move; plane = [ply][27 planes], bit `s = rank*12+file`).

### 2.2. `[NEW] src/lczero_chess/trainingdata/writer.h`
Khai báo `class TrainingDataWriter` + hàm `ReadTrainingData`:
- Ctor: `(const std::string& filename)` hoặc tiện ích `(dir, game_id)` → tự ghép tên `"<dir>/game_<id>.<ext>"`.
- `WriteChunk(const TrainingDataV1&)`, `Finalize()` (idempotent, gọi cả trong destructor), `IsOpen()`, `GetFileName()`, `static Extension()` (trả `.gz` hoặc `.bin` tùy mode).
- Cấm copy (`= delete`) vì giữ handle file thô.
- `ReadTrainingData(filename, vector<...>& out)` → đọc lại toàn bộ record (dùng cho test khứ hồi và sau này có thể dùng đối chiếu T5).
- **Handle lưu kiểu `void*`** trong header để KHÔNG phải include `<zlib.h>` ở header (giữ zlib là chi tiết của `.cc`).

### 2.3. `[NEW] src/lczero_chess/trainingdata/writer.cc`
Hiện thực dual-mode qua `#ifdef HAVE_ZLIB`:
- **Có zlib:** `gzopen/gzwrite/gzclose`; `ReadTrainingData` dùng `gzread` lặp tới EOF, phát hiện record cụt (`n != sizeof`).
- **Không zlib:** `std::ofstream`(binary)/`write`; `ReadTrainingData` dùng `ifstream::read`, kiểm tra `gcount()==0` để bắt file cụt.
- `Extension()` trả `.gz`/`.bin` theo mode.
- Xử lý lỗi mở file → in cảnh báo, `handle_ = nullptr`, các thao tác sau thành no-op (không crash).

> **Vì sao round-trip bit-exact dù có float:** Writer ghi **byte thô** của struct (`reinterpret_cast<const char*>`), không reinterpret float, nên đọc lại `memcmp` khớp tuyệt đối kể cả các bit-pattern NaN. Test do đó điền **toàn bộ struct bằng pattern byte tất định** rồi so toàn bộ 45940 byte → kiểm chứng mạnh nhất cho serialization.

### 2.4. `[MODIFY] meson.build`
Ba thay đổi:
1. Thêm nhóm nguồn:
   ```meson
   trainingdata_sources = files('src/lczero_chess/trainingdata/writer.cc')
   ```
2. Tự dò zlib (không bắt buộc → không vỡ build nếu thiếu):
   ```meson
   zlib_dep = dependency('zlib', required: false)
   if not zlib_dep.found()
     zlib_dep = cc.find_library('z', required: false)
   endif
   if zlib_dep.found()
     add_project_arguments('-DHAVE_ZLIB', language: 'cpp')
     message('zlib found: training data will be gzip-compressed (.gz)')
   else
     message('zlib NOT found: training data will be uncompressed (.bin)')
   endif
   ```
   và thêm vào `deps` nếu tìm thấy.
3. Thêm `trainingdata_sources` vào `sources:` của `executable(...)`.

→ Trên máy người dùng, Meson **tìm thấy zlib 1.3.1** qua pkg-config của MSYS2 ucrt64 → bật `HAVE_ZLIB` → ghi `.gz` thật.

### 2.5. `[MODIFY] src/main.cc`
- Thêm include: `"trainingdata/trainingdata_v1.h"`, `"trainingdata/writer.h"`, `<cstring>`, `<cstdio>`.
- Thêm helper `fill_deterministic(rec, seed)` — điền mọi byte của record theo pattern `(seed*131 + k*7 + 17) & 0xFF`, rồi set `version`/`input_format` cho dễ đọc.
- Thêm `run_trainingdata_tests()`:
  - **TEST 1:** in & kiểm `sizeof == 45940`.
  - **TEST 2:** tạo 5 record (mỗi cái pattern khác nhau) → `TrainingDataWriter` ghi ra file → `ReadTrainingData` đọc lại → kiểm số lượng + `memcmp` từng record == 0 → `std::remove` xóa file tạm.
- Thêm cờ `--test-trainingdata` (biến `test_trainingdata_mode`) vào vòng parse argv và nhánh dispatch (đặt giữa `--test-policy` và `--test-mcts`).

---

## 3. Build & chạy test

### 3.1. Build
```
meson compile -C build      # (tự reconfigure vì meson.build đổi)
```
- Kết quả: **link thành công** `custom_engine.exe`. Chỉ còn warning `-Wdeprecated-enum-enum-conversion` (có sẵn từ Fairy-Stockfish, không liên quan thay đổi này).
- (Các cảnh báo `clangd`/`constexpr_var_requires_const_init` là của **language server**, KHÔNG phải GCC build — build thật pass.)

### 3.2. Sự cố "exit code 127" ở Git Bash — và cách chẩn đoán
- Chạy `./build/custom_engine.exe --test-trainingdata` trong **Git Bash** (môi trường của tool Bash) → **exit 127** (không output).
- 127 ở bash = "không khởi động được chương trình". Vì exe + `onnxruntime.dll` đều tồn tại, nghi ngờ **thiếu DLL phụ thuộc**.
- `objdump -p build/custom_engine.exe | grep "DLL Name"` cho thấy phụ thuộc:
  ```
  libgcc_s_seh-1.dll, libstdc++-6.dll, libwinpthread-1.dll,
  onnxruntime.dll, zlib1.dll, KERNEL32.dll, ...
  ```
  → **`zlib1.dll`** (mới) + các DLL runtime MinGW nằm ở `C:\msys64\ucrt64\bin`. **Git Bash dùng PATH tối giản** không có thư mục này → không nạp được DLL → báo 127.
- Đây là **giả tạo do PATH của Git Bash**, KHÔNG phải lỗi thật: môi trường bình thường của người dùng (PowerShell / shell có MSYS2 trên PATH) nạp DLL được.

### 3.3. Chạy lại qua PowerShell (môi trường thật) → PASS
```
> .\build\custom_engine.exe --test-trainingdata
Fairy-Stockfish 190626 LB ... (Custom Variant Engine)

RUNNING TRAINING DATA (T1) TESTS...
TEST 1: sizeof(TrainingDataV1) = 45940 (expected 45940)   [PASS]
TEST 2: Writer/Reader round-trip (bit-exact)...
  - Wrote 5 records to test_trainingdata_t1.gz
  - Read back 5 records, all bytes match                  [PASS]
ALL TRAINING DATA (T1) TESTS PASSED!
PS-EXIT: 0
```
- `sizeof == 45940` ✓ · ghi/đọc `.gz` (gzip thật) ✓ · `memcmp` toàn bộ khớp ✓.

---

## 4. Đối chiếu DoD của T1

| Tiêu chí (plan) | Trạng thái |
|-----------------|-----------|
| Định nghĩa struct `TrainingDataV1` + Writer | ✅ |
| Ghi nhận dữ liệu thành công | ✅ (5 records → .gz) |
| So sánh khứ hồi C++ khớp 100% bit | ✅ (`memcmp` = 0) |
| Kích thước 45940 bytes | ✅ (compile-time `static_assert` + runtime check) |
| Không vỡ build hiện có | ✅ |

---

## 5. Quyết định kỹ thuật & lý do (tóm tắt)

| Quyết định | Lý do |
|-----------|-------|
| `#pragma pack(1)` + `static_assert(==45940)` | Khóa layout, chống lệch byte với Python (silent corruption guard) |
| Writer dual-mode gzip/raw qua `HAVE_ZLIB` | Không bắt buộc zlib → không vỡ build máy thiếu zlib; có zlib thì .gz thật |
| zlib dò bằng `required: false` | An toàn cho mọi máy; máy người dùng có zlib 1.3.1 nên tự bật gzip |
| Handle `void*` trong header | Giữ `<zlib.h>` chỉ ở `.cc`, header sạch |
| Test điền pattern byte tất định + `memcmp` toàn struct | Kiểm chứng serialization mạnh nhất, phủ mọi byte |
| Ghi byte thô (không reinterpret float) | Round-trip bit-exact kể cả NaN |

---

## 6. Việc còn lại / lưu ý cho các phase sau

- **Đóng gói phân phối:** exe nay phụ thuộc `zlib1.dll` (ngoài `onnxruntime.dll` và runtime MinGW). Khi giao engine cho máy khác, để các DLL này cạnh exe. Dev local của bạn không bị ảnh hưởng (đã có trên PATH).
- **CHƯA commit** (theo nguyên tắc chỉ commit khi được yêu cầu). Các file mới/đổi: `trainingdata/{trainingdata_v1.h, writer.h, writer.cc}`, `meson.build`, `main.cc`.
- **T2 (kế tiếp):** trích `π` từ visits (qua `MoveToNNIndex`), tính `policy_kld` từ `GetCachedEvaluation(root)` (có fallback cache-miss → `policy_kld=0`, `orig_q=best_q`), ghép cặp π↔p_NN qua MoveToNNIndex (không theo vị trí mảng vì edges đã SortEdges), và gán `z` đảo dấu theo parity ở cuối ván. Bước này mới bắt đầu đụng tới `Search`/`encoder`.

---

## 7. Cách chạy lại test (ghi nhớ)
```powershell
# Từ PowerShell (môi trường có MSYS2 ucrt64 trên PATH):
cd D:\chess_variant\custom_engine
meson compile -C build
.\build\custom_engine.exe --test-trainingdata
```
> Lưu ý: ĐỪNG chạy qua Git Bash mà thiếu MSYS2 trên PATH (sẽ ra exit 127 giả tạo do không nạp được DLL).
