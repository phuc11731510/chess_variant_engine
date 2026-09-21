# Ghi chú rà soát — 2026-09-20

Kết quả một đợt rà soát code + đo hiệu năng. Chia hai phần độc lập:
**(A) rà soát tính đúng đắn**, **(B) điều tra tốc độ sinh dữ liệu**.

Nhánh khi rà soát: `mcts-capacity-256` @ `4c14aed` (trùng `origin/mcts-capacity-256`).

---

## A. Rà soát fork Fairy-Stockfish

Fork rất sạch: chỉ **6 file** khác bản gốc (`evaluate.cpp`, `movegen.cpp`,
`position.cpp`, `position.h`, `uci.cpp`, `variants.ini`). Phần lớn tuỳ biến
quân cờ nằm trong dữ liệu (`variant_setup.cc`) chứ không phải code.

### A1. Đã kiểm tra và thấy ĐÚNG

- **`Position::copy_from` memcpy an toàn.** Vùng copy từ `board` tới
  `promotedPieces` toàn POD. `thisThread` / `st` / `var` đã được nhấc lên đầu
  class nên nằm ngoài vùng memcpy. Làm chuẩn.
- **`ChessBoard::CopyFrom` xử lý `nullptr` đúng** — rơi về `states[state_index]`
  nội bộ, không deref null.
- **`thisThread->` được bọc kín** — chỉ còn 2 chỗ trong `position.cpp`
  (dòng 1592, 1722), cả hai đều trong `#ifndef LCZERO_MCTS`.
- **`st->repetition = 0`** dưới `LCZERO_MCTS` là cố ý; đã thay bằng mảng phẳng
  `PositionHistory::history_` bên lczero.
- **`NNUE::init()` ép `useNNUE = false`** → mọi nhánh `if (Eval::useNNUE)` chết
  ở runtime, chồng thêm lớp an toàn lên `#ifndef`.
- **Thay `st->materialKey != previous->materialKey` bằng `type_of(st->move) == DROP`**
  hợp lý về ngữ nghĩa; nhánh đó chết với biến thể này (không có drop).
- **`MoveToNNIndex()` xử lý ep+phong cấp đúng** (commit `52439cc`) — mỗi quân
  phong cấp một kênh riêng. **Dữ liệu huấn luyện KHÔNG bị ảnh hưởng.**

### A2. Bug — nước đi bị mất chữ cái phong cấp *(ĐÃ SỬA 2026-09-21)*

#### Vấn đề nói bằng lời thường

Engine phải đổi qua lại giữa **nước đi** (một con số trong bộ nhớ) và **chuỗi
văn bản** kiểu `"e7d8r"` để nói chuyện với GUI. Quy ước: 4 ký tự đầu là ô đi và
ô đến, ký tự thứ 5 là **quân được phong cấp**.

Biến thể này cho phép **bắt tốt qua đường rơi thẳng vào vùng phong cấp** —
`promotionRegionWhite = *8 *9 *10` và `doubleStepRegionBlack = *10 *9 *8` chồng
lên nhau nên chuyện này xảy ra trong ván thật. Khi đó người chơi có
**6 lựa chọn** (`promotionPieceTypes = b m n r v y`), tức **6 nước đi khác nhau**
cùng đi từ e7 tới d8.

Hàm đổi-nước-thành-chuỗi trong `src/chess/uci.cpp` chỉ nối chữ cái phong cấp cho
nước phong cấp *thường*, **quên mất trường hợp bắt tốt qua đường**. Nên cả 6 nước
đều ra đúng một chuỗi: `"e7d8"`.

Chiều ngược lại — đổi-chuỗi-thành-nước — tra bằng cách **duyệt mọi nước hợp lệ và
lấy nước ĐẦU TIÊN có chuỗi trùng**:

```cpp
for (const auto& m : MoveList<LEGAL>(pos))
    if (str == UCI::move(pos, m) || ...) return m;
```

Sáu nước cùng một chuỗi → **năm nước không bao giờ chạm tới được**. Người chơi
chọn phong Xe, engine lẳng lặng đi nước đầu tiên trong danh sách. Không báo lỗi,
không crash.

#### Vùng tác hại — thực tế là nhỏ

Điều may mắn: codebase có **hai** hàm đổi-nước-thành-chuỗi, và tầng ứng dụng
dùng hàm đúng.

| Đường | Nền tảng | Có chữ phong cấp? | Ai gọi |
|---|---|---|---|
| `CanonicalMoveToUci` / `UciToCanonicalMove`<br>(`app/uci_coords.cc`) | `lczero::Move::ToString()` | **Có** | `--uci-nn` (GUI), cả 2 chiều |
| `ChessBoard::MoveToString` / `ParseMove`<br>(`lczero_chess/chess/board.cc`) | `Stockfish::UCI::move` | **Thiếu** | chỉ test |

Và đường sai gần như không được gọi: `ChessBoard::ParseMove` chỉ xuất hiện trong
`NodeTree::ResetToPosition(fen, moves)`, mà **cả 17 lời gọi trong repo đều truyền
`{}`** (danh sách nước rỗng) → thân vòng lặp là code chết.

Vậy nên:

| Thành phần | Có hỏng không |
|---|---|
| Dữ liệu huấn luyện | **Không** — dùng `MoveToNNIndex()`, không dùng chuỗi |
| GUI / `--uci-nn` | **Không** — đi qua `uci_coords.cc` |
| Self-play, arena, engine chơi cờ | **Không** |
| `ChessBoard::MoveToString`/`ParseMove` | Có, nhưng chỉ test gọi |

**Rủi ro thật không nằm ở hôm nay mà ở tương lai.** `ChessBoard::MoveToString` và
`ParseMove` nằm ngay trên lớp bàn cờ, trông như API chính tắc. Ai (kể cả chủ dự
án sau này) gọi chúng sẽ dính lỗi im lặng.

#### Nguyên nhân gốc

Commit `52439cc` ("En Passant kèm phong cấp", 2026-06-27) sửa `movegen.cpp`,
`position.cpp`, `types.h`, `encoder.cc`, `lczero_chess/chess/types.h` — tức là
cài đủ *luật chơi* và *mã hoá cho mạng nơ-ron*, nhưng **không đụng
`custom_engine/src/chess/uci.cpp`**, tức tầng văn bản.

Xác nhận bằng pickaxe: chuỗi `ep_promotion_type` chưa từng tồn tại trong file đó
ở bất kỳ commit nào, trên mọi nhánh (kể cả `origin/main`).

> **Lưu ý:** `Fairy-Stockfish-master/` trong repo **không còn là bản gốc** — nó đã
> bị sửa và đang mới hơn `custom_engine` ở vài file (bản FSF *có* đoạn xử lý đúng,
> thêm riêng ngày 2026-06-27). Không dùng làm mốc so sánh được nữa. Nên clone một
> bản FSF sạch để ngoài repo khi cần diff.

#### Cách sửa đã áp dụng

`src/chess/uci.cpp`, thêm một nhánh cạnh nhánh phong cấp thường:

```cpp
else if (type_of(m) == EN_PASSANT && ep_promotion_type(m) != NO_PIECE_TYPE)
    move += pos.piece_to_char()[make_piece(BLACK, ep_promotion_type(m))];
```

Chiều đọc chuỗi tự động đúng theo, vì `UCI::to_move` so khớp bằng chính
`UCI::move`.

### A3. Lỗ hổng test *(ĐÃ SỬA 2026-09-21)*

`src/tests/engine_tests.cc` đã có sẵn bài round-trip đúng chỗ:

```cpp
std::string s = board.MoveToString(moves[i]);
lczero::Move back = board.ParseMove(s);
```

nhưng **đang pass** — vì không thế cờ test nào chứa nước ep rơi vào vùng phong
cấp. Test đúng, chỉ thiếu dữ liệu kích hoạt.

Đã thêm vào `run_adapter_tests()`:

**1. Bốn thế cờ** thực sự sinh ra nước ep+phong cấp. Phải phủ cả hai vai trò —
quân *tạo ra* ô en passant và quân *đi bắt* — vì Sergeant (`s:fKifmnDifmnA`)
khác Tốt ở cả hai:

| FEN | Ai tạo ô ep | Ai bắt | Kiểu bắt |
|---|---|---|---|
| `k9/10/10/3pP5/10/10/10/10/10/K9 w - d8 8+8 0 1` | Tốt đen d9-d7 | Tốt trắng e7 | chéo |
| `k9/10/10/3P1s4/10/10/10/10/10/K9 w - e8 8+8 0 1` | Sergeant đen d9-f7 (**Alfil**) | Tốt trắng d7 | chéo |
| `k9/10/10/2sS6/10/10/10/10/10/K9 w - d8 8+8 0 1` | Sergeant đen e9-c7 (**Alfil**) | **Sergeant** trắng d7 | **thẳng** |
| `k9/10/10/3sS5/10/10/10/10/10/K9 w - d8 8+8 0 1` | Sergeant đen d9-d7 (**Dabbaba**) | **Sergeant** trắng e7 | chéo |

Điểm dễ bỏ sót: `fK` (forward King) cho Sergeant bắt **cả thẳng lẫn chéo**, trong
khi Tốt chỉ bắt chéo. Ô ep cũng có thể sinh ra từ **hai** kiểu nước đôi khác nhau
của Sergeant (`D` thẳng và `A` chéo). Hai thế cờ đầu chỉ phủ Tốt đi bắt; hai thế
sau bù vào.

Mọi nước ep+phong cấp đều đáp xuống hạng 8, vì `mandatoryPawnPromotion = true`
khiến Tốt/Sergeant trắng không bao giờ đứng được trên hạng 8-10, nên ô xuất phát
luôn là hạng 7.

**2. Bất biến "chuỗi duy nhất"**: trong một thế cờ, không hai nước hợp lệ nào
được phép ra cùng một chuỗi. Tổng quát hơn round-trip — bắt được mọi va chạm
chuỗi trong tương lai, không riêng ep.

**3. Chốt bảo vệ dữ liệu test**: nếu tổng số nước ep+phong cấp trong mọi thế cờ
tụt về 0 thì test báo đỏ — để bất biến ở (2) không bao giờ pass rỗng.

Kiểm chứng: trước khi sửa `uci.cpp`, test báo đúng lỗi
`[FAIL] move round-trip mismatch: 'e7d8'`. Sau khi sửa, test xanh với
**24 nước ep+phong cấp được phủ** (4 thế cờ × 6 lựa chọn). Toàn bộ
`--test-adapter --test-ep --test-rules --test-board --test-perft --test-uci
--test-policy --test-bits --test-encoder --test-trainingdata` đều pass; perft
khớp Fairy-Stockfish gốc ở mọi độ sâu.

### A4. Mìn — eval cổ điển bị vô hiệu một nửa nhưng vẫn chạm tới được *(ĐÃ SỬA 2026-09-21)*

`-DLCZERO_MCTS` đặt ở `add_project_arguments` (meson.build:36) nên áp lên **mọi**
file. Dưới cờ đó:

```
pawn_key()          -> 0
material_key()      -> 0
psq_score()         -> SCORE_ZERO
non_pawn_material() -> VALUE_ZERO
```

Nhưng `evaluate.cpp`, `material.cpp`, `pawns.cpp`, `endgame.cpp`, `search.cpp`
**vẫn nằm trong `chess_sources`**, và `search.cpp:58` có `using Eval::evaluate;`.

`main.cc:121` có nhánh dự phòng `UCI::loop(argc, argv)` → chạy binary với cờ lạ
hoặc không cờ là rơi vào UCI cổ điển của Stockfish với eval trả về rác.
`Material::probe` / `Pawns::probe` tra bảng bằng khoá hằng 0 → mọi thế cờ trúng
cùng một ô bảng băm. Không crash, sai im lặng.

Tương tự: `syzygy/tbprobe.cpp` dùng `pos.material_key()` ở **6 chỗ**
(dòng 368, 387, 695, 1161, 1179) — giờ luôn bằng 0. Self-play truyền
`syzygy_tb=nullptr` nên chưa chạm, nhưng code vẫn sống.

**Đã xử lý (2026-09-21):** bỏ hẳn nhánh dự phòng `UCI::loop(argc, argv)` trong
`main.cc`. Chạy binary không mode (hoặc gõ nhầm cờ) giờ in danh sách mode hợp lệ
và thoát với mã 2, thay vì lặng lẽ rơi vào engine cổ điển chạy trên eval bằng 0.
Dự án đã chốt dùng MCTS+NN nên nhánh đó không còn lý do tồn tại.

`Eval::evaluate` / `Material::probe` / `Pawns::probe` vẫn được liên kết (các file
còn trong `chess_sources`) nhưng nay **không còn đường gọi tới** từ CLI.

### A5. Điểm nhỏ

`position.h`: `static_assert(offsetof(StateInfo, key) == 104)` quá cứng. Dòng
`< 128` ngay trên đã diễn đạt đủ ý định; dòng `== 104` sẽ vỡ khi thêm bất kỳ
trường nào hoặc đổi ABI — mà dự án có cross-compile Android ARM.

### A6. Việc cần làm (A)

- [x] Sửa `custom_engine/src/chess/uci.cpp` → hai đường chuyển chuỗi thống nhất. *(2026-09-21)*
- [x] Thêm thế cờ ep+phong cấp + bất biến "chuỗi duy nhất" vào test round-trip. *(2026-09-21)*
- [x] Bỏ nhánh dự phòng `UCI::loop` trong `main.cc` (xem A4). *(2026-09-21)*
- [ ] Bỏ `static_assert(... == 104)`, giữ `< 128` (xem A5).

---

## B. Điều tra tốc độ sinh dữ liệu

### B1. Cấu hình và số đo nền

Chạy thật trên Colab T4, mạng `12bx144fx8s_12` (12 block × 144 filter, SE8,
~1.0 GFLOP/lượt, fp32):

```
--games 400 --visits 800 --parallel 4 --max-moves 400 --temp-cutoff 32
--provider cuda --fixed-batch 16 --noise-alpha 0.15
```

Dữ liệu thật (đo trên `Dữ liệu huấn luyện/*.zip`, mẫu ~500 ván/đời):

| | gen10 | gen11 | gen12 |
|---|---|---|---|
| Hoà | 0.2% | 0.6% | ~0.6% |
| Dài TB | 160 ply | 165 ply | 161 ply |
| Quân còn lại cuối ván | TB 15.7 | TB 14.9 | TB 14.2 (min 2) |
| Chạm `max_moves` | — | — | không ràng buộc |

→ Dữ liệu **sạch và dứt khoát**. Không có vấn đề nhãn hoà. Tàn cuộc thưa quân
được phủ tốt. Không cần sửa adjudication.

### B2. Thí nghiệm gom batch — GIẢ THUYẾT BỊ BÁC BỎ

Giả thuyết: `--fixed-batch 16` + không `--batch-aggregate` khiến 4 luồng gọi
`session_->Run()` đồng thời trên một ORT session → tranh chấp, batch nhỏ.

Đo:

| Cấu hình | nps tổng |
|---|---|
| `fixed-batch 16`, không aggregate | ~2.900–3.000 |
| `fixed-batch 64` + `batch-aggregate` + `timeout 500µs` | **3.038** |

**Chênh +3%, trong sai số. Gom batch KHÔNG phải nút thắt.**

Hệ quả: các giả thuyết sau đều **không còn đứng vững** ở mức độ đã nêu:
- Trần `MaxBatchSize = 64` (`neural/backend.h:16`) — nới lên không giúp.
- Thiết kế stop-the-world của `BatchingBackend` (producer bị chặn khi
  `running_ == true`, `batching_backend.cc:69-71`) — có thật về mặt cấu trúc,
  nhưng không phải chỗ mất throughput chính.
- Convoy effect theo `expected_producers_` (`batching_backend.cc:111`) — như trên.

### B3. Ước lượng mức bão hoà GPU

3.038 nps = 3.038 playout/giây. Số NN eval mỗi playout chưa xác định chắc
(ghi chú profiling cũ nói ~2.1):

| evals/playout | TFLOP/s | % đỉnh fp32 T4 (8.1) |
|---|---|---|
| 1.0 | 3.0 | 37% |
| 2.1 | 6.4 | 79% |

Dù ở đầu nào của dải, **dư địa còn lại nhỏ hơn nhiều so với ước tính ban đầu**,
và phép đo B2 xác nhận điều đó theo hướng thực nghiệm.

**Phép đo còn thiếu để chốt:** `nvidia-smi dmon -s u` trong lúc self-play.
- `sm%` cao và phẳng → GPU thật sự bão hoà, chỉ còn đường giảm FLOP.
- `sm%` răng cưa dưới ~50% → vẫn còn chỗ ở khâu điều phối.

### B4. Cấu trúc dữ liệu — chưa được xác nhận là nút thắt

Đo bằng cách đọc code (chưa đo thực nghiệm):

`sizeof(StateInfo) ≈ 1.856 byte`, trong đó:
- `Bitboard checkSquares[PIECE_TYPE_NB=64]` = **1.024 byte** (hơn nửa)
- `Piece unpromotedBycatch[SQUARE_NB=120]` = **480 byte**

→ `std::array<StateInfo, 512> mcts_states_` ≈ 928 KB
→ `sizeof(PositionHistory) ≈ 1 MB`

`PositionHistory` copy ctor chỉ copy `history_size_` phần tử (đã tối ưu), nhưng
ván dài ~160 ply và `TrimHistory` giữ tối thiểu 100 → **mỗi lần copy ~300 KB**.

Lưu ý: `#ifdef LCZERO_MCTS` hiện chỉ cắt phần "copied when making a move";
**hai trường lớn nhất nằm ở phần "not copied" và vẫn bị `std::copy_n` copy
nguyên**.

Hướng nếu sau này xác nhận đây là nút thắt:
- `PIECE_TYPE_BITS = 6` → 64 loại quân. Biến thể thực tế dùng ít hơn nhiều.
  Hạ xuống 4 (16 loại) làm `checkSquares` còn 256 byte → `StateInfo` giảm ~41%.
- `unpromotedBycatch` là tính năng bycatch của FSF (Crazyhouse/Bughouse).
  Nếu biến thể không dùng, đưa vào `#ifndef LCZERO_MCTS`.

Điểm tốt đã xác nhận: `workspace->history` (`search.cc:1472`) là **tham chiếu**,
không copy.

### B5. Đòn bẩy còn lại

Xếp theo mức tác động ước tính:

1. **fp16** — đòn bẩy lớn nhất còn lại. T4 có tensor core, fp32 đỉnh 8.1 TFLOPS
   vs fp16 ~65 TFLOPS. Chuyển được mà **không sửa C++** nhờ `keep_io_types=True`:
   ```
   convert_float_to_float16(model, keep_io_types=True)
   ```
   *Hiện chủ dự án chọn giữ fp32 vì lý do độ chính xác.*
2. **TensorRT EP fp32** — fusion kernel, không đổi độ chính xác. Ước ~1,2-1,5×.
   Cần build lại với EP tương ứng.
3. **Giảm `--visits`** từ 800 xuống 400 — đây là đánh đổi chất lượng/số lượng,
   không phải tăng tốc thuần.
4. **Cắt tỷ lệ eval/playout** nếu con số 2.1 là thật. Cần đo lại trước.
5. **Thuê GPU rời** (3090/4090 trên Vast.ai/RunPod, ~$0,20-0,60/giờ, kèm 8-16 vCPU).

### B6. Vấn đề đo lường — arena 20 ván

`--arena --games 20` cho sai số Elo cỡ **±150**. Không đủ để biết đời sau có
mạnh hơn đời trước hay không.

Để phát hiện chênh lệch ~50 Elo cần cỡ 400-1000 ván. Với `--visits 800` thì quá
đắt → arena nên dùng visits thấp hơn nhiều (100-200) và nhiều ván hơn. Cùng ngân
sách GPU, 400 ván × 200 visits cho nhiều thông tin hơn hẳn 20 ván × 800 visits.

### B7. Nghi vấn chưa kiểm tra — tốc độ huấn luyện

`train.py` không đặt `--workers`; mặc định trên GPU là số nhân CPU = **2** trên
Colab. Mỗi mẫu phải dựng plane `226×10×10` từ bitboard bằng Python/numpy, với
`--batch 1024`. Nhiều khả năng GPU đang chờ CPU dựng plane.

Kiểm tra rẻ: chạy `--max-steps 50 --report-every 10`, so thời gian mỗi bước với
khi thêm `--dense-cache`.

---

## C. Dọn dẹp đã thực hiện (2026-09-20)

Đã xoá **2,93 GB** artifact tái tạo được:
`gui/build` (2280 MB), `gui/.dart_tool` (164 MB), `custom_engine/build-dml`
(304 MB), `custom_engine/build` (234 MB), `custom_engine/build-android` (16 MB).

Dựng lại: `cd custom_engine && meson setup build && ninja -C build`

Chưa đụng (chờ quyết định): `lc0-master` (1043 MB, phần lớn là `.git` của nó),
`gui_stock_study` (664 MB), `custom_engine/models` (252 MB — 6 đời × onnx+pt).
Giữ nguyên: `custom_engine/third_party` (440 MB, ONNX Runtime — cần cho build).
