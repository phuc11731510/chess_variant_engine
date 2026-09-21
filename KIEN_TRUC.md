# FairyZero — Bản đồ mã nguồn

Tài liệu tra cứu kiến trúc: từ cấp module → lớp → hàm, kèm vai trò từng phần.
Viết ngày 2026-09-21, theo nhánh `mcts-capacity-256`.

Đây là tài liệu **kiến trúc**. Cách *sử dụng* (cờ dòng lệnh, quy trình huấn
luyện) nằm ở `custom_engine/HUONG_DAN.md`. Các vấn đề đã rà soát nằm ở
`GHI_CHU_RA_SOAT.md`.

---

## 1. Ý tưởng tổng thể

FairyZero là một engine AlphaZero cho **biến thể cờ 10×10 tự thiết kế**. Nó được
ghép từ hai dự án mã nguồn mở, mỗi cái đóng góp đúng phần nó giỏi nhất:

| Nguồn | Đóng góp | Nằm ở |
|---|---|---|
| **Fairy-Stockfish** | luật cờ, sinh nước đi, bitboard 10×10, định nghĩa quân tuỳ biến | `src/chess/` |
| **Lc0 (Leela Chess Zero)** | MCTS, mã hoá đầu vào mạng nơ-ron, vòng lặp self-play | `src/lczero_chess/`, `src/search/classic/` |
| **Của riêng dự án** | lớp cầu nối giữa hai bên, backend ONNX, pipeline huấn luyện | `src/lczero_chess/chess/`, `src/lczero_chess/neural/`, `python/` |

Vấn đề cốt lõi phải giải: **Lc0 và Fairy-Stockfish có mô hình thế cờ không tương
thích.** Lc0 muốn sao chép thế cờ thoải mái (MCTS cần giữ nhiều thế cờ cùng lúc);
Fairy-Stockfish dùng cơ chế `do_move`/`undo_move` với con trỏ `StateInfo` liên
kết ngược, vốn giả định một dòng thời gian tuyến tính. Lớp cầu nối
`src/lczero_chess/chess/` giải quyết bằng **deep copy** (`Position::copy_from`).

---

## 2. Luật biến thể

Định nghĩa nằm trong `src/app/variant_setup.cc`, hàm `setup_custom_variant()`,
dưới dạng chuỗi INI kiểu Fairy-Stockfish:

```
maxRank = 10, maxFile = j          -> bàn 10×10, 100 ô
```

**Quân cờ:**

| Ký hiệu | Tên | Nước đi (Betza) |
|---|---|---|
| `p` | Tốt | tốt chuẩn |
| `n b r q` | Mã, Tượng, Xe, Hậu | chuẩn |
| `k` | Vua | `KN` — Vua **cộng nước Mã** |
| `a` | Amazon | Hậu + Mã |
| `e` | Chancellor | Xe + Mã |
| `h` | Archbishop | Tượng + Mã |
| `m` | Centaur | Vua + Mã |
| `v` | customPiece1 | `CN` — Camel (1,3) + Mã |
| `y` | customPiece2 | `AD` — Alfil (2,2) + Dabbaba (0,2) |
| `s` | **Sergeant** | `fKifmnDifmnA` |

**Sergeant** là quân đặc biệt nhất và là nguồn của nhiều ca biên:
- `fK` — đi/bắt 1 ô theo **ba** hướng tiến: thẳng và hai chéo trước.
  Khác Tốt: Sergeant **bắt được cả thẳng lẫn chéo**.
- `ifmnD` — nước đầu, tiến, **chỉ đi không bắt**, không nhảy: Dabbaba (0,2) → đi đôi thẳng.
- `ifmnA` — nước đầu, tiến, chỉ đi không bắt, không nhảy: Alfil (2,2) → **đi đôi chéo**.

**Các luật khác:**

```
pawnTypes / promotionPawnTypes / enPassantTypes / nMoveRuleTypes = p s
doubleStepRegionWhite = *1 *2 *3      doubleStepRegionBlack = *10 *9 *8
promotionRegionWhite  = *8 *9 *10     promotionRegionBlack  = *3 *2 *1
promotionPieceTypes = b m n r v y     (6 lựa chọn)
mandatoryPawnPromotion = true
castling = true   (Vua h/d, Xe i/b)
stalemateValue = loss                 (hết nước đi = THUA, không phải hoà)
checkCounting = true                  (luật N-checks; FEN ghi "7+7")
```

**Hệ quả đáng chú ý của thiết kế này:**

- Vùng phong cấp (*8 *9 *10) và vùng đi đôi của đối phương (*10 *9 *8) **chồng
  lên nhau** → nước bắt tốt qua đường có thể rơi thẳng vào vùng phong cấp.
  Đây là ca đã gây ra bug ở `GHI_CHU_RA_SOAT.md` mục A2.
- `mandatoryPawnPromotion = true` + vùng phong cấp sâu 3 hạng → Tốt/Sergeant
  trắng **không bao giờ đứng được trên hạng 8-10**. Nên mọi nước ep+phong cấp
  đều xuất phát từ hạng 7 và đáp xuống hạng 8.
- `checkCounting` làm ván **ngắn và dứt khoát**: dữ liệu thật cho tỉ lệ hoà
  0,2-0,9%, dài trung bình ~160 ply.

---

## 3. Luồng dữ liệu

```
                  ┌─────────────────────────────────────────┐
                  │  self-play (C++, engine)                │
   mạng .onnx ───▶│  MCTS 800 playout/nước, Dirichlet noise │──▶ game_N.gz
   đời trước      │  → ghi MỌI thế cờ ra file               │    (TrainingDataV1)
                  └─────────────────────────────────────────┘
                                                                     │
                            ┌────────────────────────────────────────┘
                            ▼
                  ┌─────────────────────────────────────────┐
                  │  train.py (Python, PyTorch)             │
                  │  SE-ResNet 12×144, loss = policy CE     │──▶ mạng .onnx
                  │  + value WDL CE, warm-start từ .pt      │    đời sau
                  └─────────────────────────────────────────┘
                            │
                            └──▶ arena: đời mới vs đời cũ → quyết định giữ hay bỏ
```

### Ba quy ước PHẢI khớp giữa C++ và Python

Ghi rõ trong `trainingdata_v1.h` và `trainingdata_reader.py`. Lệch một cái là
hỏng im lặng — mạng học sai mà không có lỗi nào hiện ra:

1. **Chỉ số policy** = `MoveToNNIndex` = `loại_nước*100 + hạng_từ*10 + cột_từ`,
   tổng 10600 ô (106 loại nước × 100 ô xuất phát).
2. **Thứ tự value** = `[Win, Draw, Loss]`, theo góc nhìn **bên tới lượt đi**.
3. **Thứ tự plane** = `[ply][27 plane]`, mỗi plane là mask 128-bit,
   bit ô `s = hạng*12 + cột` (Stockfish dùng bước nhảy 12, không phải 10).

Test `--test-trainingdata` và `python/test_roundtrip.py` khoá ba quy ước này.

---

## 4. `src/chess/` — Tầng luật (Fairy-Stockfish)

~15.000 dòng, gần như nguyên bản. **Chỉ 6 file khác bản gốc**:
`evaluate.cpp`, `movegen.cpp`, `position.cpp`, `position.h`, `uci.cpp`,
`variants.ini`.

### Các file chính

| File | Vai trò |
|---|---|
| `position.h/.cpp` (3482 dòng) | `Position` — trạng thái bàn cờ, `do_move`/`undo_move`, sinh khoá Zobrist |
| `movegen.cpp` | sinh nước đi giả hợp lệ theo định nghĩa Betza của từng quân |
| `bitboard.h/.cpp`, `magic.h` | bitboard **128-bit** (bàn 100 ô không vừa uint64), magic bitboard tra nước quân trượt |
| `variant.cpp/.h`, `parser.cpp` | đọc file INI định nghĩa biến thể → cấu trúc `Variant` |
| `types.h` | `Move`, `Square`, `Piece`… — `SQUARE_NB = 120`, `PIECE_TYPE_NB = 64` |
| `uci.cpp` | đổi nước đi ↔ chuỗi (`UCI::move`, `UCI::to_move`) |
| `search.cpp`, `evaluate.cpp`, `nnue/` | search alpha-beta + eval cổ điển — **được biên dịch nhưng không còn đường gọi tới** (xem mục 9) |

### `struct StateInfo` — tờ ghi chú của một thế cờ

Nhìn vào bàn cờ không biết được: còn bao nhiêu nước tới luật 50, ô nào bắt-qua-
đường được, quyền nhập thành, **mỗi bên còn phải chiếu mấy lần nữa**, quân vừa bị
ăn là gì. `StateInfo` giữ đúng phần thông tin đó. Mỗi thế cờ cần một tờ; các tờ
nối ngược nhau bằng con trỏ `previous`.

Dưới `#ifdef LCZERO_MCTS`, các trường chỉ eval cổ điển cần (`pawnKey`,
`materialKey`, `nonPawnMaterial`) bị **bỏ khỏi phần đầu**, và các trường còn lại
được xếp lại sao cho khối "chép ở mỗi nước đi" nằm gọn trong 128 byte đầu
(2 cache line) — có `static_assert` canh.

Kích thước thực tế: **~1.856 byte**, trong đó `checkSquares[64]` chiếm 1.024 và
`unpromotedBycatch[120]` chiếm 480.

### `Position::copy_from(const Position& other, StateInfo* newSt)`

Hàm **do dự án thêm vào**, không có trong bản gốc. Nó `memcpy` khối dữ liệu POD
từ `board` tới `promotedPieces`, rồi gán lại `thisThread` / `var` và trỏ `st`
sang tờ ghi chú mới. Các con trỏ đã được **nhấc lên đầu class** để nằm ngoài vùng
memcpy. Đây là thứ cho phép MCTS sao chép thế cờ thoải mái.

---

## 5. `src/lczero_chess/chess/` — Lớp cầu nối

1.657 dòng. Đây là phần **quan trọng nhất phải hiểu**, vì nó là nơi hai thế giới
gặp nhau.

### `class ChessBoard` (`board.h/.cc`)

Bọc một `Stockfish::Position` và trình ra API kiểu Lc0.

| Phương thức | Vai trò |
|---|---|
| `SetFromFen(fen, ...)` | dựng thế cờ từ FEN |
| `GenerateLegalMoves()` | trả `MoveList` các nước hợp lệ |
| `ApplyMove(move, st)` | đi một nước |
| `CopyFrom(other, st)` | sao chép sâu; `st == nullptr` thì dùng `states[]` nội bộ |
| `IsUnderCheck()` | bên tới lượt có đang bị chiếu không |
| `Hash()` | khoá Zobrist, dùng cho cache NN và phát hiện lặp thế |
| `flipped()` | có phải Đen tới lượt không |
| `MoveToString` / `ParseMove` | đổi nước đi ↔ chuỗi (uỷ thác cho `Stockfish::UCI`) |
| `GetRawPosition()` | lấy `Stockfish::Position` bên dưới |

Thành viên riêng: `Stockfish::Position pos` + `std::array<StateInfo, 2> states`
(mảng tĩnh 2 phần tử để tránh cấp phát heap).

> ⚠ `MoveToString`/`ParseMove` **chỉ test dùng**. Tầng ứng dụng đi qua
> `app/uci_coords.cc`. Xem `GHI_CHU_RA_SOAT.md` A2.

### `class Position` (`position.h/.cc`)

Một `ChessBoard` + siêu dữ liệu: `rule50_ply_`, `repetitions_`, `ply_count_`,
`plies_since_prev_repetition_`. Có `DoMove`, `UndoMove`, `FromFen`, `Hash`.

### `class PositionHistory` — chồng thế cờ của MCTS

Đây là lớp mà mục 4 nhắc tới "chồng tờ ghi chú". MCTS đi sâu xuống cây, và ở mỗi
độ sâu cần một thế cờ đầy đủ. `PositionHistory` giữ nguyên cả đường đi đó:

```cpp
Position starting_position_;                     // thế cờ gốc
Position last_position_;                         // thế cờ hiện tại
std::array<LightweightPosition, 512> history_;   // ~72 KB — lịch sử rút gọn
std::array<StateInfo, 512> mcts_states_;         // ~928 KB — tờ ghi chú mỗi ply
size_t history_size_;
```

`sizeof(PositionHistory) ≈ 1 MB`. Mảng tĩnh thay cho `std::vector` để tránh cấp
phát heap trong hot path — đánh đổi là object rất to, nên nó luôn được cấp phát
trên heap và truyền bằng **tham chiếu**.

| Phương thức | Vai trò |
|---|---|
| `Append(m)` | đi một nước, đẩy thế cờ mới lên chồng |
| `Pop()`, `Trim(n)` | quay lui |
| `TrimHistory(keep)` | cắt bớt lịch sử ván thật (giữ ≥100 vì luật 50 nước) |
| `Last()`, `Starting()` | thế cờ hiện tại / gốc |
| `ComputeGameResult()` | **hệ quy chiếu tuyệt đối** — dùng gán nhãn ván |
| `ComputeMctsResult()` | **hệ quy chiếu tương đối** theo bên vừa đi — dùng backup MCTS |
| `DidRepeatSinceLastZeroingMove()` | phát hiện lặp thế |

Hai hàm `Compute*Result` khác nhau ở hệ quy chiếu — **nhầm là sai dấu value**.
`ComputeGameResult` kiểm theo thứ tự: N-checks (O(1)) → luật 50 → lặp 3 lần →
mới sinh nước đi (O(n)) để xét chiếu hết/hết nước.

Copy constructor của `PositionHistory` chỉ chép `history_size_` phần tử (không
phải cả 512), rồi **nối lại chuỗi con trỏ `previous`** cho đúng.

### `encoder.cc` (503 dòng) — mã hoá đầu vào mạng

```
kMoveHistory   = 8    (8 ply lịch sử)
kPlanesPerBoard = 27   (13 loại quân × 2 bên + 1 plane lặp thế)
kAuxPlaneBase  = 216 = 27 × 8
kAuxPlanesCount = 10
tổng            = 226 plane × 10 × 10
```

10 plane phụ trợ: 4 plane quyền nhập thành (vị trí Xe), 1 plane ô en passant,
1 plane rule50 (chuẩn hoá /100), 1 plane trống, 1 plane toàn số 1 (cho mạng biết
biên bàn cờ), **2 plane số chiếu còn lại** của Trắng và Đen (chuẩn hoá /10).

| Hàm | Vai trò |
|---|---|
| `EncodePositionForNN(history, ...)` | lịch sử → 226 plane, luôn ở **hệ quy chiếu canonical** (lật dọc nếu Đen đi) |
| `UnpackInputPlanes(...)` | plane thưa → mảng float phẳng cho ONNX |
| `MoveToNNIndex(move, transform)` | nước đi → chỉ số policy 0..10599 |
| `MoveFromNNIndex(idx, ...)` | chiều ngược lại |

`MoveToNNIndex` xử lý **cả** phong cấp thường **và** ep+phong cấp (kênh 88-105).
Biến thể này chỉ đối xứng theo trục dọc (nhập thành/tốt phá đối xứng ngang), nên
`transform` luôn bằng 0 — không augment 8 chiều như lc0 cờ vua.

---

## 6. `src/search/classic/` — MCTS

5.404 dòng, fork từ `lc0-master/src/search/classic`, sửa rất ít. Đây là thuật
toán AlphaZero: PUCT + virtual loss + gom minibatch.

### `node.h/.cc` (1.365 dòng)

| Lớp | Vai trò |
|---|---|
| `Edge` | một nước đi từ nút cha: lưu `Move` + xác suất policy `P` |
| `Node` | một thế cờ trong cây: `n_` (số lần thăm), `wl_` (win-loss), `d_` (draw), `m_` (moves-left), con trỏ cha/con |
| `EdgeAndNode` | cặp (cạnh, nút) — nút có thể chưa tồn tại |
| `Edge_Iterator`, `VisitedNode_Iterator` | duyệt con |
| `NodeTree` | **cây gốc + `PositionHistory` của ván thật** |

Hàm `Node` đáng chú ý:
- `TryStartScoreUpdate()` / `CancelScoreUpdate()` / `FinalizeScoreUpdate()` —
  cơ chế **virtual loss**: đánh dấu nút "đang được thăm" để các luồng khác không
  dồn hết vào cùng một nhánh.
- `MakeTerminal(result, ...)` / `MakeNotTerminal()` — đánh dấu nút kết thúc ván.
- `CreateEdges(moves)`, `MakeSolid()`, `SortEdges()` — quản lý bộ nhớ cây.
- `num_edges_` là **`uint16_t`** (bản lc0 gốc là `uint8_t`) — cần thiết vì bàn
  10×10 có thể có hơn 255 nước hợp lệ.

`NodeTree::MakeMove(move)` — khi ván thật đi một nước, **giữ lại cây con** của
nước đó (tree reuse) và huỷ phần còn lại. Cũng gọi `TrimHistory(100)` khi lịch
sử vượt 200 ply.

### `search.h/.cc` (2.988 dòng)

| Lớp | Vai trò |
|---|---|
| `Search` | điều phối một lần tìm kiếm: khởi động luồng, dừng, chọn nước tốt nhất |
| `SearchWorker` | một luồng tìm kiếm — chứa toàn bộ vòng lặp MCTS |

**Vòng lặp MCTS**, `SearchWorker::ExecuteOneIteration()` gọi lần lượt:

1. `InitializeIteration()` — chuẩn bị
2. `GatherMinibatch()` — **đi từ gốc xuống lá nhiều lần** để gom một batch thế
   cờ cần đánh giá. Đây là nơi sinh ra *collision*: hai lần đi xuống rơi cùng
   một lá chưa được đánh giá.
3. `CollectCollisions()`
4. `MaybePrefetchIntoCache()`
5. `RunNNComputation()` — gọi backend một lần cho cả batch
6. `FetchMinibatchResults()`
7. `DoBackupUpdate()` — lan kết quả ngược lên gốc
8. `UpdateCounters()`

`PickNodeToExtend(collision_limit)` là hàm chọn nhánh theo công thức PUCT.

`struct TaskWorkspace` chứa một `PositionHistory history` (~1 MB) dùng chung cho
cả worker — truy cập bằng **tham chiếu**, không copy.

`params.h/.cc` (1.051 dòng) — khoảng 35 siêu tham số MCTS: `cpuct`, `fpu`,
`policy-softmax-temp`, `minibatch-size`, `max-collision-events`… Đặt được từ
dòng lệnh qua `--search-opt tên=giá_trị`.

### `stoppers/`

Điều kiện dừng tìm kiếm. Self-play dùng `PlayoutStopper` (định nghĩa ngay trong
`selfplay_game.cc`) — dừng khi đủ N playout **mới** (`nodes_since_movestart`),
nên tree reuse không làm sai số lượng.

---

## 7. `src/lczero_chess/neural/` — Tầng mạng nơ-ron

1.270 dòng. Thiết kế kiểu **decorator xếp chồng**: mỗi lớp bọc lớp dưới.

```
Search  ──▶  ZeroHeapCache  ──▶  BatchingBackend  ──▶  OnnxBackend  ──▶  ONNX Runtime
             (nhớ kết quả)       (gom batch,          (chạy mạng)        (CPU/CUDA/DML)
                                  tuỳ chọn)
```

### Giao diện chung (`backend.h`)

```cpp
constexpr size_t MaxBatchSize = 64;   // trần cứng, buffer tĩnh theo nó

struct EvalPosition  { const PositionHistory* history; span<const Move> legal_moves; };
struct EvalResult    { float q, d, m; vector<float> p; };   // WDL + policy
class  BackendComputation {                 // một "lô" đang gom
    virtual size_t UsedBatchSize() const;
    virtual AddInputResult AddInput(pos, result);
    virtual void ComputeBlocking();         // chạy mạng, điền kết quả
};
class  Backend {                            // nhà máy sinh Computation
    virtual unique_ptr<BackendComputation> CreateComputation();
    virtual optional<EvalResult> GetCachedEvaluation(pos);
};
```

`StaticVector<T, N>` — vector kích thước cố định, không cấp phát heap.

### `OnnxBackend` (`onnx_backend.cc`, 465 dòng)

Lớp dưới cùng, thật sự chạy mạng.

```
InputPlanesCount = 226    BoardWidth/Height = 10
InputBufferUnitSize = 22600 float  (≈90 KB mỗi thế cờ)
PolicyOutputSize = 10600   ValueOutputSize = 3 (WDL)
```

- `InitializeSession()` — nạp `.onnx`, gắn Execution Provider theo
  `provider=cpu|cuda|dml`. Với GPU + `fixed_batch` thì gọi
  `AddFreeDimensionOverrideByName("batch", N)` để cố định hình dạng.
- `OnnxComputation::AddInput()` — mã hoá thế cờ **ngay lúc gọi** vào buffer tĩnh.
- `OnnxComputation::ComputeBlocking()` — cắt buffer thành từng lô đúng
  `fixed_batch_size_`, **pad số 0 cho đủ**, gọi `session_->Run()` cho mỗi lô.
  Buffer được ánh xạ thẳng vào `Ort::Value` (zero-copy).

### `BatchingBackend` (`batching_backend.cc`, 143 dòng)

Tuỳ chọn (`--batch-aggregate`). Gom thế cờ từ **nhiều ván song song** vào một lô
để GPU no hơn. Có một luồng server riêng (`ServerLoop`).

Điều kiện phóng lô: buffer đầy `MaxBatchSize`, **hoặc** mọi producer đã nộp
(`submitted_groups_ >= expected_producers_`), **hoặc** hết `timeout_us_`.

> ⚠ Thiết kế hiện tại là *stop-the-world*: producer bị chặn khi `running_ == true`,
> tức CPU và GPU **không chạy chồng lấn**. Xem `GHI_CHU_RA_SOAT.md` B2 — đo thực
> nghiệm cho thấy đây **không** phải nút thắt chính, nhưng cấu trúc thì có thật.

### `ZeroHeapCache` (`zero_heap_cache.cc`, 278 dòng)

Cache kết quả NN theo khoá Zobrist, **không cấp phát heap** (bảng băm mở với
`CacheBucket` cố định). `TryRead(hash, num_moves, out)` / `Insert(...)`.
Yêu cầu khớp cả `num_moves` để tránh va chạm hash cho thế cờ khác số nước.

---

## 8. `src/lczero_chess/selfplay/` + `trainingdata/` — Sinh dữ liệu

### `selfplay_game.cc` — `PlayOneGame(...)`

Chơi **một** ván trọn vẹn và ghi ra một file `.gz`. Vòng lặp mỗi nước:

1. Cộng dồn "điểm tấn công" (đếm quân đang ở nửa sân địch).
2. Dựng `Search` + `PlayoutStopper(visits)`, chạy `RunBlocking()`.
3. `FillSearchTargets(root, history, backend, rec)` → policy π, các giá trị q/d.
4. `EncodePlanesIntoRecord(history, rec)` → 216 plane + các vô hướng.
5. `SelectMoveEdge(root, ply, temp_cutoff_ply)` — dưới ngưỡng ply thì **lấy mẫu
   theo số visit** (đa dạng khai cuộc), trên ngưỡng thì lấy nước nhiều visit nhất.
6. Kiểm tra resign (nếu bật).
7. `tree->MakeMove(played)` → `ComputeGameResult()`; khác `UNDECIDED` thì dừng.

Hết ván: `AssignResult()` gán z cho **mọi** bản ghi với đúng dấu theo bên đi.
Ván chạm `max_moves` bị xử hoà.

### `selfplay_driver.cc` — `RunSelfPlay(cfg, backend, options)`

Pool `cfg.parallel` luồng, mỗi luồng rút số ván từ một `atomic` dùng chung. Mọi
ván **dùng chung một `backend`**. Không có khoá nào trong hot path; thống kê
bằng atomic. Hỗ trợ `--max-seconds` (dừng mềm: không nhận ván mới, ván đang chạy
vẫn hoàn tất nên không có `.gz` cụt).

`struct SelfPlayConfig` giữ toàn bộ tham số: `visits`, `max_moves`,
`temp_cutoff_ply`, `parallel`, `threads_per_game`, các tham số resign,
`start_fens` (sách khai cuộc).

### `training_extract.cc`

| Hàm | Vai trò |
|---|---|
| `FillSearchTargets(root, history, backend, rec)` | π từ số visit; `root_q/d`, `best_q/d`; `orig_q/d` (đánh giá NN thô, lấy từ cache); `policy_kld` = KL(π‖p_nn) |
| `AssignResult(rec, abs_result, black_to_move)` | gán z: `result_q = ±1`, hoà thì `result_d = 1` |
| `EncodePlanesIntoRecord(history, rec)` | 216 plane → mask 128-bit tách thành `[lo64, hi64]`; các vô hướng (rule50, số chiếu còn lại, cột Xe nhập thành) |

Quy ước dấu quan trọng: giá trị của **nút con** là theo góc nhìn đối phương, nên
phải **đảo dấu** (`-best.GetWL()`) mới ra giá trị cho bên đang đi.

### `trainingdata/`

`struct TrainingDataV1` — bản ghi **45.940 byte**, `#pragma pack(1)`, có
`static_assert` khoá bố cục để Python `struct.unpack` không lệch.

`TrainingDataWriter` — ghi gzip (`.gz`) nếu có zlib, không thì nhị phân thô
(`.bin`). Một file mỗi ván.

---

## 9. `src/app/` — Các chế độ chạy

1.857 dòng. `main.cc` phân nhánh theo cờ dòng lệnh do `parse_cli()` đọc vào
`struct EngineOptions`.

| File | Chế độ | Vai trò |
|---|---|---|
| `cli.cc/.h` | — | `parse_cli()` → `EngineOptions` (mọi cờ dòng lệnh) |
| `variant_setup.cc` | — | `setup_custom_variant()` — định nghĩa biến thể; `init_engine_globals()` |
| `uci_nn_engine.cc` (654 dòng) | `--uci-nn` | **engine UCI cho GUI** — vòng lặp `position`/`go`/`stop`, phát `bestmove`, `info` |
| `selfplay_mode.cc` | `--selfplay` | dựng backend + `SelfPlayConfig`, gọi `RunSelfPlay` |
| `arena_mode.cc` | `--arena` | hai mạng đánh nhau, đếm thắng/thua/hoà |
| `play_mode.cc` | `--play` | chơi với engine ngay trong terminal |
| `uci_coords.cc` | — | `CanonicalMoveToUci` / `UciToCanonicalMove` — **đường đổi chuỗi mà tầng ứng dụng thật sự dùng** |
| `search_opts.cc` | — | `ApplySearchOpt` — áp `--search-opt tên=giá_trị` vào tham số lc0 |
| `backend_factory.cc` | — | dựng chồng backend (cache → batching → onnx) |
| `fairyzero_ffi.h` | — | C ABI cho GUI Android gọi qua `dart:ffi` |

**Không còn nhánh dự phòng `UCI::loop`.** Chạy không mode sẽ in danh sách mode
hợp lệ và thoát mã 2. Lý do: cả dự án build với `-DLCZERO_MCTS`, vốn ngừng duy
trì `psq` / `materialKey` / `pawnKey` / `nonPawnMaterial` (MCTS không đọc chúng)
và cho các hàm đọc trả về hằng 0 — eval cổ điển sẽ chạy trên số 0 mà không báo gì.

---

## 10. `src/tests/` — Bộ test

`engine_tests.cc`, 2.507 dòng. Chạy hoàn toàn trên CPU, không cần GPU.

| Cờ | Kiểm tra gì |
|---|---|
| `--test-perft` | **mạnh nhất** — đếm nước đi qua lớp cầu nối phải khớp Fairy-Stockfish thô ở mọi độ sâu |
| `--test-adapter` | FEN idempotent; `MoveToString`↔`ParseMove`; **chuỗi UCI duy nhất trong mỗi thế cờ**; phủ ep+phong cấp |
| `--test-ep` | bắt tốt qua đường (Sergeant thẳng + chéo Alfil) |
| `--test-rules` | luật biến thể |
| `--test-board` | nhập thành: sinh, mã hoá, thực thi, cả hai màu |
| `--test-policy` | song ánh `MoveToNNIndex` ↔ `MoveFromNNIndex` |
| `--test-encoder` | plane đầu vào phản ánh trung thực bàn cờ |
| `--test-trainingdata` | round-trip bản ghi bit-exact |
| `--test-bits` | thao tác bitboard 128-bit |
| `--test-nn`, `--test-mcts`, `--test-selfplay`, `--test-extract` | cần file mạng `.onnx` |
| `--audit-generation` | đối chiếu movegen với Fairy-Stockfish trên hàng trăm nghìn thế cờ |

---

## 11. `python/` — Pipeline huấn luyện

| File | Vai trò |
|---|---|
| `model.py` | **kiến trúc mạng** — SE-ResNet kiểu lc0. Nguồn chân lý duy nhất; warm-start đòi mọi đời cùng kiến trúc. Dùng 12 block × 144 filter, SE ratio 8 |
| `train.py` (14.547 dòng ký tự) | vòng huấn luyện: loss = policy CE + value WDL CE + L2; SWA; xuất ONNX; AdamW hoặc SGD+lịch LR kiểu lc0; `--diff-focus` ưu tiên thế cờ khó |
| `dataset.py` | `.gz` → `(input, pi, value_wdl)`. Trộn value target: `q_ratio*q + (1-q_ratio)*z` |
| `trainingdata_reader.py` | **bản sao Python của `TrainingDataV1`** — `struct.unpack` 45.940 byte, dựng lại 226 plane |
| `make_seed.py` | sinh mạng đời 0 (trọng số ngẫu nhiên) từ `model.py` |
| `archive.py` | gom hàng nghìn `.gz` thành một `.zip` (Drive rất chậm với file nhỏ) |
| `audit_generation.py` | kiểm tra tính toàn vẹn của cả một đời dữ liệu |
| `test_roundtrip.py` | Python dựng lại plane phải khớp `UnpackInputPlanes` của C++ |
| `test_bits.py` | giải mã mask 128-bit ở mức bit |
| `test_extreme.py` | ca biên của pipeline Python |
| `test_perspective.py` | kiểm hệ quy chiếu value qua onnxruntime |

---

## 12. Bẫy và bất biến cần nhớ

1. **Hệ quy chiếu canonical.** Encoder luôn lật bàn cờ nếu Đen tới lượt. Nước đi
   trong cây MCTS ở hệ canonical; `MoveToString`/`uci_coords` lật lại về toạ độ
   thật. Nhầm chỗ lật = nước đi sai màu.
2. **Dấu của value.** Giá trị nút con theo góc nhìn đối phương → phải đảo dấu.
   `ComputeGameResult` (tuyệt đối) ≠ `ComputeMctsResult` (tương đối).
3. **Ba quy ước C++↔Python** ở mục 3. Lệch = hỏng im lặng.
4. **`PositionHistory` nặng ~1 MB** — luôn truyền bằng tham chiếu, cấp phát heap.
5. **`num_edges_` phải là `uint16_t`** — bàn 10×10 vượt 255 nước.
6. **Bit ô cờ là `hạng*12 + cột`**, không phải `*10`. Stockfish dùng bước 12.
7. **`MaxBatchSize = 64` là trần cứng** với buffer tĩnh — đổi phải sửa
   `neural/backend.h` và cân nhắc bộ nhớ (90 KB/thế cờ).
8. **`--batch-aggregate` chỉ dành cho GPU.** Trên CPU nó dồn inference vào một
   luồng và **chậm hơn**. Trên DML, `--parallel ≥ 2` mà không bật nó thì **crash**.
9. **`Fairy-Stockfish-master/` trong repo KHÔNG còn là bản gốc** — đã bị sửa.
   Đừng dùng làm mốc diff; clone bản sạch để ngoài repo.
10. **`nps` mà engine in ra đang đếm trùng.** `selfplay_game.cc` cộng
    `root->GetN()` mỗi nước, mà giá trị đó bao gồm cả cây tái sử dụng từ nước
    trước → phóng đại ~2×. Xem `GHI_CHU_RA_SOAT.md` B3.
