# Walkthrough — Phase T3: Vòng self-play 1 ván hoàn chỉnh + ghi `.gz`

> Ngày: 2026-06-19 · Dự án: FairyZero (`custom_engine`) — biến thể cờ 10×10.
> Phạm vi đợt này: hiện thực hóa **milestone T3** trong `implementation_plan phase training_1.md` (mục A5–A7).
> DoD: chơi trọn 1 ván tự đấu từ startpos → **sinh file `.gz` hợp lệ chứa MỌI nước đi** (không lọc) → đóng file an toàn (Search/NodeTree trên Heap).
> Kết quả: ✅ Hoàn thành và đã verify bằng test thực tế (PASS, PS-EXIT 0). Tiếp nối T1 (`walkthrough_3.md`) và T2 (`walkthrough_4.md`).

---

## 0. T3 ghép những gì đã có

- **T1** (`walkthrough_3.md`): struct `TrainingDataV1` (45940 byte) + `TrainingDataWriter` (gzip).
- **T2** (`walkthrough_4.md`): `FillSearchTargets` (π/value/orig_q/policy_kld) + `AssignResult` (z parity).
- **T3 (đợt này)** = phần CÒN THIẾU để có 1 ván hoàn chỉnh:
  1. **`EncodePlanesIntoRecord`** — điền `piece_planes[216][2]` + `ep_mask` + scalar aux (phần MỚI quan trọng nhất).
  2. **`PlayOneGame`** — vòng lặp: search → trích record → chọn nước → đi → lặp đến hết ván → gán z → ghi `.gz`.

T3 KHÔNG đụng đa luồng nhiều ván (đó là T4).

---

## 1. Khảo sát trước khi code

### 1.1. Kiểu `Stockfish::Bitboard` (để ghi `piece_planes[216][2]`)
Grep `chess/types.h`:
- `typedef unsigned __int128 Bitboard;` (nhánh GCC, LARGEBOARDS) ← **đang dùng**.
- `struct Bitboard { uint64_t b64[2]; }` (nhánh non-GCC).
- `typedef uint64_t Bitboard;` (nhánh 8×8).

→ Để **an toàn cho cả 2 biểu diễn 128-bit**, dùng **`memcpy` 16 byte** thay vì bit-shift. Trên little-endian, cả `__int128` lẫn `{u64[2]}` đều có layout `[lo64, hi64]` giống nhau, nên `memcpy(rec.piece_planes[p], &mask, 16)` cho `piece_planes[p][0]=bits 0-63`, `[1]=bits 64-127`. Khớp với cách Python unpack (`s = rank*12+file`, word = `s/64`, bit = `s%64`).

### 1.2. API encoder & position
- `EncodePositionForNN(history, kMoveHistory, FillEmptyHistory::FEN_ONLY, &planes, &transform)` → `InputPlanes planes` (`std::array<InputPlane,226>`); mỗi `InputPlane{ Stockfish::Bitboard mask; float value; }`.
- `kAuxPlaneBase = 216` → plane 0..215 là 216 history piece planes; plane EP = `kAuxPlaneBase + 4`.
- Scalar aux đọc thẳng từ position (giá trị THÔ, Python sẽ chuẩn hóa): `pos.side_to_move()`, `last.GetRule50Ply()`, `pos.checks_remaining(color)`, `pos.can_castle(cr)`, `pos.castling_rook_square(cr)`.

### 1.3. API cây MCTS cho vòng game
- `NodeTree::ResetToPosition(fen, {})`, `GetCurrentHead()`, `GetPositionHistory()`, `MakeMove(move)` (frame **canonical** — so khớp `edge.GetMove()`), `IsBlackToMove()`.
- `Search` ctor (10 tham số) như T2; `RunBlocking(threads)`.
- `SearchStopper` interface: `ShouldStop(IterationStats&, StoppersHints*)`, `OnSearchDone(...)`.
- `IterationStats` có `nodes_since_movestart` (playout MỚI lượt này) và `total_nodes` (gồm cả cây tái dụng).

---

## 2. Các file đã tạo / sửa

### 2.1. `[MODIFY] src/lczero_chess/selfplay/training_extract.{h,cc}` — thêm `EncodePlanesIntoRecord`
```cpp
void EncodePlanesIntoRecord(const PositionHistory& history, TrainingDataV1& rec) {
  InputPlanes planes; int transform = 0;
  EncodePositionForNN(history, kMoveHistory, FillEmptyHistory::FEN_ONLY, &planes, &transform);

  // 216 history planes -> 128-bit masks (memcpy 16B, đúng cho mọi biểu diễn Bitboard)
  static_assert(sizeof(planes[0].mask) == 16, "Bitboard != 128-bit");
  for (p in 0..215) memcpy(rec.piece_planes[p], &planes[p].mask, 16);
  memcpy(rec.ep_mask, &planes[kAuxPlaneBase + 4].mask, 16);   // plane EP

  // scalar aux từ position (THÔ)
  const auto& pos = history.Last().GetBoard().GetRawPosition();
  Color us = pos.side_to_move(), them = ~us;
  rec.side_to_move = (us == BLACK) ? 1 : 0;
  rec.rule50_count = clamp(last.GetRule50Ply(), 0, 255);
  rec.checks_remaining_us   = clamp((int)pos.checks_remaining(us), 0, 255);
  rec.checks_remaining_them = clamp((int)pos.checks_remaining(them), 0, 255);

  // castling: lưu FILE của xe (0-9), 0xFF nếu mất quyền. Flip dọc giữ file -> canonical=thật.
  castle_file(cr) = can_castle(cr) ? file_of(castling_rook_square(cr)) : 0xFF;
  rec.castling_us_ooo_file / us_oo / them_ooo / them_oo = ...;   // us_ooo theo side-to-move
}
```
**Lý do thiết kế:**
- **Tái dùng chính `EncodePositionForNN`** cho 216 piece planes + ep_mask → đảm bảo bit-khớp 100% với cái NN thấy lúc inference (và với `UnpackInputPlanes` mà Python tái hiện).
- **Scalar aux lưu THÔ** (count rule50/checks, file castling) thay vì plane float đã chuẩn hóa → Python reader tự dựng lại plane (rule50/100, checks/7, board-edge=1, castling-bit) → tiết kiệm và linh hoạt cho Chess960.
- **Castling = file-index** (không phải mask/boolean) → hỗ trợ thế cờ khởi đầu ngẫu nhiên sau này; vì lật dọc giữ nguyên file nên `file_of(rook thật)` = file ở khung canonical.

### 2.2. `[NEW] src/lczero_chess/selfplay/selfplay_game.{h,cc}` — `PlayOneGame`
Khai báo:
```cpp
GameResult PlayOneGame(start_fen, backend, options, visits, max_moves,
                       temp_cutoff_ply, out_filename, search_threads=1);
```
Hiện thực (`.cc`, có 3 helper trong anonymous namespace):

**(a) `SilentResponder`** — `UciResponder` rỗng (search bắt buộc có responder; không spam log).

**(b) `PlayoutStopper`** — dừng theo **`stats.nodes_since_movestart >= visits`** (playout MỚI), KHÔNG theo `total_nodes`.
> Vì sao: cây MCTS được **tái dụng** giữa các nước (MakeMove giữ subtree). Nếu dừng theo `total_nodes` thì các nước sau có sẵn visit từ subtree → search mới rất ít. Dùng `nodes_since_movestart` đảm bảo **đúng `visits` playout mới mỗi nước**, ổn định chất lượng π.

**(c) `SelectMoveEdge(root, ply, cutoff)`** — chọn nước:
- `ply < cutoff` → **temperature=1**: lấy mẫu theo visit (`Random::GetDouble(total)` rồi đi tích lũy) → đa dạng khai cuộc.
- `ply >= cutoff` → **greedy** (max-visit).

**Vòng `PlayOneGame`:**
```
tree = make_unique<NodeTree>(); tree->ResetToPosition(fen, {});
for ply in 0..max_moves:
   search = make_unique<Search>(*tree, ...PlayoutStopper(visits)...);  // HEAP
   search->RunBlocking(threads);
   root = tree->GetCurrentHead();
   rec = {0}; rec.version/input_format; black = IsBlackToMove();
   best = FillSearchTargets(root, history, backend, rec);   // T2
   if best.is_null() break;
   EncodePlanesIntoRecord(history, rec);                    // T3
   played_edge = SelectMoveEdge(root, ply, cutoff);
   played = played_edge.GetMove();  (fallback = best)
   if played != best: cập nhật played_idx/q/d (con -> phủ định WL)
   records.push(rec); stm_black.push(black);
   tree->MakeMove(played);
   result = history.ComputeGameResult();  if != UNDECIDED break;
final = (result != UNDECIDED) ? result : DRAW;   // cutoff -> hòa
for r in records: AssignResult(r, final, stm_black);
TrainingDataWriter w(out_filename); for r: w.WriteChunk(r); w.Finalize();
return final;
```
**Quyết định:**
- **Heap-alloc `Search`/`NodeTree`** (`make_unique`) — vì `PositionHistory` chứa mảng tĩnh 512-ply (~vài trăm KB), đặt trên stack dễ tràn (đã thống nhất ở các vòng review).
- **Cutoff = DRAW**: nếu hết `max_moves` mà ván chưa kết thúc tự nhiên → xử hòa (an toàn cho z; sau này T4 có thể thêm resign/adjudicate tinh hơn).
- **Ghi 1 file/ván** + `Finalize` đóng an toàn.

### 2.3. `[MODIFY] meson.build`
Thêm `'src/lczero_chess/selfplay/selfplay_game.cc'` vào `trainingdata_sources`.

### 2.4. `[MODIFY] src/main.cc`
- Include `"selfplay/selfplay_game.h"`.
- `run_selfplay_tests(weights)`: nạp variant (ini inline) + `OnnxBackend`+`MemCache` (noise ε=0.25) → `PlayOneGame(fen, ..., visits=32, max_moves=30, temp_cutoff_ply=8, "test_selfplay_game.gz", threads=2)` → **đọc lại file** (`ReadTrainingData`) → verify từng record (version, Σπ≈1, z đã gán: draw `d=1,q=0` hoặc decisive `d=0,q=±1`) → kiểm record[0] có piece-plane khác rỗng → in vài scalar aux → xóa file tạm.
- Cờ CLI `--test-selfplay` (biến `test_selfplay_mode`) + dispatch.

---

## 3. Build & sửa lỗi

### 3.1. Lỗi GCC thật (1 lỗi, đã sửa)
```
error: no matching function for call to 'clamp(Stockfish::CheckCount, int, int)'
```
`pos.checks_remaining()` trả **enum `Stockfish::CheckCount`**, còn `std::clamp` cần 3 tham số cùng kiểu. → Sửa: `std::clamp(static_cast<int>(pos.checks_remaining(us)), 0, 255)`.

### 3.2. Build OK
```
meson compile -C build   →   [2/2] Linking target custom_engine.exe
```
> **Lưu ý clangd (lặp lại từ T1/T2):** language server tiếp tục báo cascade giả (`unknown type 'uintptr_t'`, `raw->p is not a pointer`, `make_unique deleted`, `Invalid operands Edge_Iterator`...) do không cấu hình đúng flag stdlib. **GCC build là nguồn chân lý** — và nó pass.

---

## 4. Chạy test (PowerShell) → PASS

```
> .\build\custom_engine.exe --test-selfplay
[T3] OnnxBackend + MemCache loaded.
Playing 1 game (visits=32, max_moves=30, temp_cutoff_ply=8)...
Game finished: result=2 (DRAW — cutoff 30 nước), file=test_selfplay_game.gz
  Records written/read: 30 | side_to_move[0]=0 rule50[0]=0 checks_us[0]=7 castle_us_oo_file[0]=8
[PASS] All 30 records valid (pi=1, z assigned, planes non-empty).
ALL T3 (SELF-PLAY) TESTS PASSED!
PS-EXIT: 0
```

### Phân tích kết quả
- **`result=2` = DRAW** (enum `{UNDECIDED=0, BLACK_WON=1, DRAW=2, WHITE_WON=3}`): mạng ngẫu nhiên chơi 30 nước chưa có kết quả tự nhiên → adjudicate hòa. Mọi record nhận `result_d=1, result_q=0`.
- **`Records=30`** = đúng `max_moves` → ghi đầy đủ mọi nước, không lọc. ✓
- **`side_to_move[0]=0`** (trắng đi ở startpos) ✓
- **`rule50[0]=0`** (startpos) ✓
- **`checks_us[0]=7`** ✓ (khớp "7+7" trong FEN — còn 7 lần chiếu để thắng)
- **`castle_us_oo_file[0]=8`** = **file i** ✓✓ → xác nhận **encode castling file-index hoạt động** (`castlingRookKingsideFile=i`, i = chỉ số 8). Đây là bằng chứng phần T3 mới (plane/scalar encode) đúng.
- **piece planes record[0] khác rỗng** ✓ (startpos có quân).

> (Nhắc lại: chạy bằng **PowerShell**, KHÔNG dùng Git Bash thiếu MSYS2 ucrt64 trên PATH → exit 127 giả.)

---

## 5. Đối chiếu DoD của T3

| Tiêu chí (plan) | Trạng thái |
|-----------------|-----------|
| Sinh file `.gz` hợp lệ | ✅ (đọc lại được 30 records) |
| Chứa đầy đủ toàn bộ ván, ghi mọi nước, không lọc | ✅ (30 records = 30 nước) |
| Đóng file an toàn trên Heap | ✅ (Search/NodeTree `make_unique`, `Finalize`) |
| z gán cho mọi record | ✅ (draw → d=1, q=0) |
| Planes + scalar aux đúng | ✅ (castling file=8, checks=7, side=0, planes≠0) |
| Không vỡ build | ✅ |

---

## 6. Bảng quyết định kỹ thuật & lý do

| Quyết định | Lý do |
|-----------|-------|
| `memcpy` 16 byte cho `piece_planes` | An toàn cho cả `__int128` lẫn `{u64[2]}`; little-endian cho `[lo,hi]` đúng thứ tự word Python cần |
| Tái dùng `EncodePositionForNN` cho planes | Bit-khớp 100% với input NN lúc inference & `UnpackInputPlanes` Python |
| Scalar aux lưu THÔ (count/file) | Gọn; Python tự chuẩn hóa plane; file-index hỗ trợ Chess960 |
| `PlayoutStopper` theo `nodes_since_movestart` | Cây tái dụng giữa các nước → đếm playout MỚI mới cho đúng `visits` mỗi nước |
| Temperature=1 ply<cutoff, greedy sau | Đa dạng khai cuộc (giống AlphaZero) mà vẫn chơi mạnh về cuối |
| Heap-alloc Search/NodeTree | PositionHistory có mảng tĩnh 512-ply → tránh tràn stack |
| Cutoff → DRAW | An toàn để gán z khi ván chưa kết thúc tự nhiên |
| `SilentResponder` cục bộ (anonymous ns) | Search cần responder; làm rỗng, không phụ thuộc main.cc |

---

## 7. Việc còn lại / chuẩn bị cho T4

- **CHƯA commit** (T1/T2 bạn đã tự commit). File T3 mới/đổi: `selfplay/{training_extract.h, training_extract.cc, selfplay_game.h, selfplay_game.cc}`, `meson.build`, `main.cc`.
- **T4 (kế tiếp)** — driver đa ván song song:
  1. Cờ thật `--selfplay --games=N --out=dir --visits=V` (đang là placeholder trong `main()`).
  2. Thread pool K worker, mỗi worker chạy `PlayOneGame` cho 1 ván tại 1 thời điểm.
  3. **Chia sẻ chung 1 `OnnxBackend` + `ZeroHeapCache`** (cache lockless seqlock đã thiết kế cho đa luồng); mỗi search tự `CreateComputation()`.
  4. Đặt tên file theo `game_id` (đã có ctor `TrainingDataWriter(dir, game_id)`).
  5. DoD T4: sinh ~100 ván song song ổn định, không leak, không crash.
- Lưu ý cân bằng: trên CPU ít nhân, cân nhắc K ván × threads/search để không oversubscribe.

---

## 8. Cách chạy lại các test (ghi nhớ)
```powershell
cd D:\chess_variant\custom_engine
meson compile -C build
.\build\custom_engine.exe --test-selfplay      # T3 (1 ván -> .gz)
.\build\custom_engine.exe --test-extract       # T2 (pi/kld/z)
.\build\custom_engine.exe --test-trainingdata  # T1 (struct/writer round-trip)
```
> Dùng PowerShell (có MSYS2 ucrt64 trên PATH), KHÔNG dùng Git Bash thiếu PATH.
