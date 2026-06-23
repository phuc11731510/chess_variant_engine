# Walkthrough — Đợt AUDIT + xây bộ test "lá chắn" cho tầng adapter

> Ngày: 2026-06-19 · Dự án: FairyZero (`custom_engine`) — biến thể cờ 10×10.
> Bối cảnh: sau khi round-trip T5 phát hiện **lỗi encoder nghiêm trọng** (`value=0` khiến NN "mù"), ta không còn dám tin "chạy được là đúng". Đợt này: **soi kỹ toàn bộ tầng adapter `src/lczero_chess/chess` + xây 6 bộ test cực đoan** để biến mọi giả định thành kiểm chứng bit-exact / vét-cạn.
> Kết quả: ✅ Tất cả test PASS. **Không phát hiện thêm lỗi logic/bit nào** ngoài 2 lỗi đã sửa ở T5. Hai ranh giới của adapter (xuống Fairy-Stockfish, lên MCTS/NN) đều đã được canh giữ.

---

## 0. Vì sao phải làm đợt này

**Bài học cốt lõi từ lỗi encoder:** mạng `weights_0_elo` ngẫu nhiên + nước đi đến từ *movegen* (không phải NN) ⟹ **mọi lỗi encode đầu vào hoàn toàn vô hình** với các test "chạy thử". Lỗi `value=0` (NN không thấy quân nào) sống sót qua nhiều vòng review chính vì lý do đó.

⟹ Nguyên tắc mới: **mọi đường dữ liệu phải được kiểm bằng so khớp bit-exact hoặc liệt kê vét cạn**, không tin vào "không crash".

Tầng adapter có **2 ranh giới** cần soi:
1. **Adapter ↔ Fairy-Stockfish** (dùng API: Bitboard, Square, Move, Position, do/undo, checks, rule50, repetition).
2. **Adapter ↔ MCTS/NN** (`MoveToNNIndex`, `MoveFromNNIndex`, `UnpackInputPlanes`).

---

## 1. AUDIT đọc-hiểu (trước khi viết test)

Đã đọc kỹ: `board.{h,cc}`, `position.{h,cc}`, `types.h` (Move/MoveList), `encoder.{h,cc}`.

### 1.1. Các điểm rủi ro cao — kết luận ĐÚNG
| Mối lo | Kiểm chứng khi đọc code | Kết luận |
|--------|------------------------|----------|
| `Piece` ép `uint8_t` trong `LightweightPosition.board[120]` có mất dữ liệu? | `PIECE_TYPE_BITS=6` → `PIECE_TYPE_NB=64`, `PIECE_NB=128`, `make_piece=(c<<6)+pt` ⟹ max **127 < 256** | ✓ Vừa khít, không cắt |
| `Move::Flip` (lật cho quân Đen) đúng? | LUT `flip_from_to_lut`/`flip_square_lut` dùng stride 12 (`s%12`, `s/12`), `new_rank=max_rank−rank`, giữ file | ✓ |
| Square `rank*12+file` khớp FS `Square`? | `FILE_NB=12`, `SQUARE_NB=120=10×12` | ✓ |
| Snapshot history `board[s]=piece_on(Square(s))` (s∈0..119) khớp encoder đọc `[rank*12+file]`? | Cùng hệ tọa độ tuyệt đối; encoder lật đồng nhất theo `us` hiện tại cho mọi ply | ✓ |
| `ApplyMove` phát hiện zeroing qua `state()->rule50==0`? | Khớp ngữ nghĩa FS (FS reset rule50=0 cho mọi nước zeroing) | ✓ |
| `ComputeGameResult` (checks/rule50/repetition/stalemate)? | `checks_remaining(c)<=0`→c thắng; rule50≥100→draw; rep≥2→draw; stalemate=loss | ✓ |

### 1.2. Điểm cần dọn — CODE CHẾT (rủi ro thấp, không có caller)
- `Position::GetLastMove()` trả move **frame FS** (chưa lật canonical). Nếu dùng trong ctor `PositionHistory(std::span<Position>)` sẽ **lật 2 lần**. Nhưng `grep` toàn `src/` cho thấy **cả hai không có caller** (vestige giao diện lc0).
- `ChessBoard::ours()/theirs()/castlings()/BitboardWrapper` cũng không được gọi.
→ Khuyến nghị xóa để tránh "mìn" tương lai (chưa làm).

---

## 2. Sáu bộ test mới — thiết kế & kết quả

> Tất cả là cờ CLI riêng trong `main.cc`, build qua meson, chạy bằng **PowerShell** (PATH có MSYS2 ucrt64). Phần Python dùng Python313 (numpy 2.2.6).

### 2.1. `--test-perft` — Perft đối chiếu (lá chắn vàng cho ranh giới FS)
**Ý tưởng:** so **số node** giữa 2 đường đi cùng một cây nước:
- **Đường adapter**: `GenerateLegalMoves` (+ `Flip`) → `ChessBoard` copy → `ApplyMove` (đúng hot-path MCTS) → đệ quy.
- **Đường raw FS**: `MoveList<LEGAL>` → `do_move`/`undo_move` → đệ quy.

Cùng movegen FS ⟹ **bất kỳ lệch số node nào = lỗi adapter** (flip / quản lý state / copy). Đây là test mạnh nhất cho cơ chế nước đi.

**Kết quả (khớp tuyệt đối mọi độ sâu):**
```
startpos        d1=34   d2=1156  d3=43870
Sergeant+kings  d1=13   d2=156   d3=2366   d4=43091
pawn tension    d1=9    d2=81    d3=1053   d4=13676
[PASS] adapter path matches raw Fairy-Stockfish at all depths.
```

### 2.2. `--test-bits` + `python/test_bits.py` — kiểm BIT cực đoan
Trọng tâm paranoid: chứng minh việc **tách/đặt từng bit** của Bitboard 128-bit là đúng tuyệt đối.

- **E1 (C++):** với **cả 120 ô**, `square_bb(s)` → split `[low64, high64]` (đúng logic `EncodePlanesIntoRecord`) → bit serialize phải đúng = `s`. Phủ ranh giới bit-64 và word cao.
- **E2 (C++):** với thế cờ Trắng-đi, **hợp của 26 piece-plane (ply 0) == occupancy bàn cờ, bit-exact, không chồng lấn** (mỗi quân đúng 1 plane tại đúng ô; startpos 60 quân).
- **Python `test_bits.py` (độc lập):** mỗi ô (rank,file) → đúng 1 cell; **padding (file 10,11) bị loại**; full-board mask = 100 cell.

**Vì sao mạnh:** C++ và Python được kiểm **độc lập** ở mức bit, rồi round-trip T5 **buộc 2 phía khớp nhau** → "tam giác hóa", khó sai mà lọt.

**Kết quả:**
```
[OK] E1: square_bb(s) -> exactly serialized bit s for ALL 120 squares
[OK] E2 occupancy: 60 / 4 / 4 pieces each on exactly 1 plane at the exact square
[PASS] BIT-LEVEL tests.
[PASS] Python decoder: all 100 board squares map exactly; padding rejected; full-board=100.
```

### 2.3. `--test-rules` — luật khó (perft không phủ)
- **Lặp 3 lần:** dựng `PositionHistory`, cho 2 vua đi qua-lại về thế xuất phát 2 lượt (8 nước) → kỳ vọng **DRAW** (kiểm `ComputeLastMoveRepetitions` rối rắm bằng hash lịch sử nén).
- **rule50:** FEN halfmove=99, `Reset(...,99,1)`, 1 nước vua không-zeroing → rule50_ply=100 → **DRAW**.
- **7-check ĐỘNG:** FEN `1+7` (Trắng cần 1 đòn chiếu), cho Trắng **giao đòn chiếu thật** (`Ra1-e1` chiếu vua e10) → FS giảm bộ đếm khi `do_move` → **WHITE_WON**. Mạnh hơn TEST 4 vốn chỉ kiểm tĩnh (FEN đã ở 0).

**Kết quả:** `[OK] repetition→DRAW`, `[OK] rule50→DRAW`, `[OK] 7th check→WHITE_WON`.

### 2.4. `--test-adapter` — round-trip FEN & nước đi
- **FEN idempotent:** `SetFromFen(fen)→fen1`, `SetFromFen(fen1)→fen2`, assert `fen1==fen2` (tránh lệch định dạng đầu vào). 4 thế cờ.
- **MoveToString ↔ ParseMove:** với mọi nước hợp lệ (cả Trắng và Đen): `s=MoveToString(m)`, `m2=ParseMove(s)`, assert `m2==m` (kiểm lật 2 chiều qua chuỗi).

**Kết quả:** `[OK] FEN idempotent (4 positions)`, `[OK] 56 legal moves round-trip (incl. Black-to-move)`.

### 2.5. `--test-nn` — ranh giới MCTS/NN (3 phần)
Lấp lỗ hổng của `--test-policy` cũ (vốn chỉ đi chiều `idx→move→idx`).

- **Phần 1 — liệt kê hình học VÉT CẠN:** sinh **mọi dạng nước** trên 10×10: trượt (8 hướng × 9 ô), mã (8), lạc đà (8), phong cấp (6 quân × 3 hướng). Mỗi nước: `MoveToNNIndex` in-range, `MoveFromNNIndex` round-trip **chính xác** (`back==m`), và **không va chạm** (2 nước khác nhau ⟹ idx khác nhau).
- **Phần 2 — mọi nước hợp lệ THẬT:** duyệt đệ quy depth-3 từ startpos + thế phong cấp. Mỗi nước: idx in-range (**không 65535** — vì 65535 sẽ ghi `pi[65535]` tràn mảng 10600!), hình học round-trip (`from/to` khớp, kể cả nhập thành mã hóa kiểu vua-bắt-xe), **đơn ánh trong từng thế** (2 nước hợp lệ không trùng idx → π không bị ghi đè).
- **Phần 3 — `UnpackInputPlanes` (giá trị, độc lập round-trip):** dựng `InputPlanes` thủ công, kiểm: giá trị 1 ô (vd (5,3)=0.7), fast-path `AllSquares` (=0.3 toàn plane), **loại bỏ padding** (bit ở file 10 → 0), độc lập giữa các plane, plane chưa chạm = 0.

**Kết quả:**
```
[OK] Part 1: 5532 geometric move-shapes -> all in-range, exact round-trip, ZERO collisions
[OK] Part 2: 45209 real legal moves -> none unmapped, geometry round-trips, injective per position
[OK] Part 3: UnpackInputPlanes -> single-value / AllSquares / padding-reject / plane-independence ALL correct
```

### 2.6. (Đã có từ T5) `--emit-roundtrip` + `python/test_roundtrip.py`
Round-trip C++↔Python bit-exact cho tensor `[226,10,10]`, π, z, orig_q, policy_kld. Đợt audit này đã **mở rộng** thêm **case 2 (thế cờ sau 7 nước)** → lấp đầy history plies 1-7 (199 plane khác rỗng) → kiểm serialize + encode **toàn bộ 8 ply lịch sử**.

---

## 3. Toàn cảnh "lá chắn" sau đợt này

| Ranh giới / Thành phần | Test | Phủ |
|------------------------|------|-----|
| Cơ chế nước đi (movegen + flip + do/undo + copy) | `--test-perft` | đối chiếu raw FS, mọi depth |
| Tách/đặt bit Bitboard 128-bit | `--test-bits` E1 + `test_bits.py` | vét cạn 120 ô, cả 2 phía |
| Đặt quân lên plane (occupancy) | `--test-bits` E2 | bit-exact, không chồng lấn |
| Luật cờ (rep / rule50 / 7-check động) | `--test-rules`, TEST 3/4 | có |
| FEN & nước đi (lật 2 chiều) | `--test-adapter` | idempotent + 56 nước |
| Policy codec (To/From NNIndex) | `--test-nn` P1-2 + `--test-policy` | **cả 2 chiều** + đơn ánh + 45209 nước thật |
| `UnpackInputPlanes` (giá trị) | `--test-nn` P3 + `--test-bits` E2 | độc lập round-trip |
| Encoder đầy đủ (8 ply, castling/ep) | `--emit-roundtrip` + `test_roundtrip.py` | bit-exact C++↔Python |
| Castling sinh/encode/thực thi | TEST 7 | có |

**Hai ranh giới của adapter giờ đều có test bit-exact / vét-cạn.** Không phát hiện sai sót nào về cách dùng API FS hay quản lý bit (ngoài 2 lỗi đã sửa ở T5).

---

## 4. Đánh giá thẳng thắn

- Lỗi encoder hôm trước là lỗi **ngữ nghĩa value** (init sai `value=0`), **KHÔNG phải hiểu sai Bitboard/API FS**. Các test mới chứng minh việc đọc/ghi/tách **từng bit** của Bitboard FS là **đúng** — kiểm vét cạn 120 ô + occupancy + round-trip 2 chiều, không sai lệch.
- Hai test "an toàn bộ nhớ" đáng giá nhất:
  - `--test-nn` Phần 2: 45209 nước thật **không bao giờ** trả 65535 → không tràn `pi[10600]`.
  - `--test-bits` E2 + Phần 3: padding (file 10/11) **luôn bị loại** → không rò dữ liệu rác vào tensor.
- Cách tiếp cận "tam giác hóa" (C++ độc lập + Python độc lập + round-trip buộc khớp) là mô hình nên giữ cho mọi đường dữ liệu về sau.

---

## 5. Cách chạy lại TOÀN BỘ test

```powershell
cd D:\chess_variant\custom_engine
meson compile -C build

# --- Ranh giới Adapter <-> Fairy-Stockfish ---
.\build\custom_engine.exe --test-perft     # node-count đối chiếu raw FS
.\build\custom_engine.exe --test-bits      # E1 (120 ô) + E2 (occupancy)
.\build\custom_engine.exe --test-rules     # repetition / rule50 / 7-check động
.\build\custom_engine.exe --test-adapter   # FEN + move-string round-trip
.\build\custom_engine.exe --test-board     # TEST 1-7 (encoder, stalemate, castling...)

# --- Ranh giới Adapter <-> MCTS/NN ---
.\build\custom_engine.exe --test-nn        # ToNNIndex/FromNNIndex/UnpackInputPlanes
.\build\custom_engine.exe --test-policy    # bijection idx->move->idx (10600)

# --- Cầu C++ <-> Python (encoder đầy đủ + bit decoder) ---
$py = "C:\Users\7\AppData\Local\Programs\Python\Python313\python.exe"
.\build\custom_engine.exe --emit-roundtrip python\rt
& $py python\test_roundtrip.py
& $py python\test_bits.py

# --- Lá chắn dữ liệu huấn luyện (T1-T3) ---
.\build\custom_engine.exe --test-trainingdata
.\build\custom_engine.exe --test-extract
.\build\custom_engine.exe --test-selfplay
```
> Engine: PowerShell (PATH có MSYS2 ucrt64), KHÔNG dùng Git Bash thiếu PATH (exit 127 giả).

---

## 6. Trạng thái & việc tiếp theo

- **CHƯA commit.** File đổi đợt này: `src/main.cc` (thêm `run_perft_tests`, `run_bits_tests`, `run_rules_tests`, `run_adapter_tests`, `run_nn_tests` + flags; mở rộng `run_roundtrip_emit` thêm case multi-move), `python/test_bits.py` (MỚI). (Các sửa lỗi encoder/serialize đã ở T5.)
- **Dead code** (`GetLastMove`, span-ctor, `ours/theirs/castlings`) nên dọn — tùy bạn.
- **Đề xuất kế tiếp:** sang **T6** (model PyTorch 10×128 + loss + SWA + export ONNX). Toàn bộ tầng adapter (xuống FS, lên MCTS/NN) giờ đã được canh giữ chắc chắn — nền tảng tin cậy để bước vào huấn luyện.
