# Implementation Plan — Phase T8 (Engine UCI hoàn chỉnh + Bản portable tất-cả-trong-một + Sách hướng dẫn)

> Dự án: FairyZero (custom_engine) — biến thể 10×10, NN 226 planes / policy 10600 / value WDL.
> Mục tiêu T8: biến pipeline thành **một sản phẩm cầm tay hoàn chỉnh** — (1) một engine **tuân thủ ĐẦY ĐỦ giao thức UCI** chạy ổn trên terminal (để bạn cắm vào **GUI tự viết** cho biến thể này); (2) **một bản portable duy nhất** chứa mọi thứ để **chơi / sinh dữ liệu / huấn luyện** trên **cả Windows (CPU) lẫn Colab (GPU)**, với **tối đa siêu tham số chỉnh tay** (mặc định hợp lý cho phần ít dùng).
> Ngày: 2026-06-20. Tiền đề: T1–T7 + T7.5 đã xong (self-play, training, rolling window, resign, FP16, sparse cache, archive). Audit + `test_extreme.py` (46 checks) PASS.

> **Đính chính phạm vi (theo yêu cầu người dùng):** KHÔNG nhắm tới việc tích hợp các GUI bên thứ ba (CuteChess/Banksia…). Người dùng sẽ **tự tạo GUI** riêng cho biến thể. Vì vậy tiêu chí cốt lõi của T8 đối với phần "chơi" là **độ tuân thủ UCI tuyệt đối** + chạy ổn định trên terminal; mọi GUI (gồm GUI tự viết) chỉ cần nói đúng UCI là dùng được.

---

## 0. Toàn cảnh: T8 = "đóng khung sản phẩm"

Pipeline AlphaZero đã khép kín ở phía máy học (self-play → train → model mới). T8 đóng khung nó thành sản phẩm dùng được:

```
  ĐÃ CÓ (T1–T7.5):                      T8 BỔ SUNG:
  ┌──────────────────────────┐        ┌─────────────────────────────────────────────┐
  │ self-play (C++ MCTS+ONNX)│        │ (U1) Engine UCI ĐẦY ĐỦ  (MCTS+ONNX, terminal)│
  │ training  (PyTorch)      │ ─T8─►  │ (U2) Tối đa siêu tham số chỉnh tay (3 luồng) │
  │ arena     (model vs model│        │ (U3) MỘT bản portable: Win(CPU)+Colab(GPU)   │
  └──────────────────────────┘        │ (U4) Sách hướng dẫn (chơi/sinh/huấn luyện)   │
                                       └─────────────────────────────────────────────┘
```

**Điểm mấu chốt:** engine HIỆN dùng `UCI::loop` của **Stockfish** (alpha-beta NNUE) — KHÔNG phải MCTS + mạng ONNX của ta. T8 viết một **vòng lặp UCI riêng điều khiển MCTS + ONNX**, tuân thủ đầy đủ đặc tả UCI, tái dùng đúng vòng chơi mà `run_arena` đã chứng minh chạy được.

---

## 1. Kế thừa gì từ phần đã có (tái dùng tối đa)

| Thành phần đã có | Vị trí | Dùng cho T8 |
|------------------|--------|-------------|
| Vòng chơi 1 nước = Search → chọn max-visit edge → MakeMove | `main.cc::run_arena` (L2180–2221) | Khung lõi của UCI engine: y hệt, chỉ thay "đối thủ B" bằng lệnh `go` từ stdin |
| `classic::NodeTree` + `Search` + `NodeLimitStopper` | `search/classic/` | Bộ máy MCTS; `TrimTreeAtHead()` + `MakeMove()` để **tái dùng cây** giữa các nước |
| Backend ONNX + MemCache (CPU/CUDA) | `neural/onnx_backend.cc` | Suy luận mạng; cờ `--provider cpu\|cuda --fixed-batch N` đã có |
| Parser nước đi của Fairy-Stockfish (`UCI::to_move`, `UCI::move`) trên `Stockfish::Position` | `src/uci.*` | I/O chuỗi nước **đúng chuẩn** (rank nhiều chữ số, nhập thành, phong cấp) — tránh tự lật canonical |
| `Move::Flip(RANK_10)` (lật giữa canonical ↔ tọa độ thật) | `selfplay_game.cc` | Map giữa `lczero::Move` (canonical) và nước tọa độ-thật của Stockfish |
| `setup_custom_variant()` + FEN startpos 10×10 | `main.cc` | Khởi tạo biến thể |
| `ComputeGameResult` (chiếu hết/hòa/7-check/rule50/lặp 3) | `chess/position.*` | Phát hiện ván kết thúc trong lúc chơi |
| Toàn bộ cờ self-play & training (visits, cpuct, noise, resign, q-ratio, SWA, diff_focus, sparse, amp…) | `--selfplay`, `train.py`, `loop.py` | Nền của "tối đa siêu tham số" (Mục U2) |

> **Nguyên tắc vàng:** KHÔNG viết lại MCTS/encoder. T8 chỉ là **một lớp I/O (UCI) mỏng** + đóng gói + tài liệu. Mọi quy ước (canonical frame, MoveToNNIndex…) đã khóa bởi test T5/adapter/`test_extreme` — không đụng.

---

## 2. MODULE U1 — Engine UCI đầy đủ (MCTS+NN), chạy terminal

### U1.0. Vì sao UCI (dù tự viết GUI)?
UCI là **hợp đồng stdin/stdout** chuẩn giữa engine và GUI. Tuân thủ đầy đủ UCI nghĩa là:
- **GUI tự viết** của bạn chỉ cần nói UCI là điều khiển được engine — không phải nhúng C++.
- Có thể đo Elo bằng cách cho 2 đời mạng (hoặc đấu Fairy-SF) qua bất kỳ trọng tài UCI nào.
- Tách bạch rõ engine (lõi) và GUI (giao diện) → bảo trì dễ.

### U1.1. Kích hoạt: cờ `--uci-nn`
```
custom_engine --uci-nn [--weights model_genN.onnx] [--provider cpu|cuda] [--fixed-batch N] [--threads T]
```
- Mặc định **tắt nhiễu Dirichlet, tắt temperature** → AI đánh hết sức (khác self-play).
- Giữ nguyên `UCI::loop` Stockfish cũ cho debug movegen; `--uci-nn` là engine "thật".
- Đọc stdin theo dòng, trạng thái: `NodeTree` + `Backend` + `OptionsDict` + bảng option runtime.

### U1.2. ⭐ TUÂN THỦ UCI ĐẦY ĐỦ (yêu cầu hạng nhất)
Engine phải hiện thực **toàn bộ** giao thức UCI, không chỉ tập tối thiểu. Bảng lệnh:

| Lệnh vào | Hành vi đúng chuẩn UCI |
|----------|------------------------|
| `uci` | In `id name FairyZero <ver>`, `id author …`, **liệt kê mọi option** (đúng cú pháp `option name <X> type <…> default <…> [min/max/var…]`), kết bằng `uciok` |
| `debug [on\|off]` | Bật/tắt log `info string` chi tiết (không lỗi nếu nhận) |
| `isready` | Trả `readyok` **sau khi** đã nạp xong backend (đồng bộ) — kể cả khi đang search |
| `setoption name <X> [value <Y>]` | Đặt option (gồm cả `button` không có value); bỏ qua an toàn nếu tên lạ |
| `register …` | Chấp nhận & no-op (`registration ok`) — engine không cần đăng ký |
| `ucinewgame` | Reset ván mới: xóa cây, clear cache nếu cần |
| `position [startpos \| fen <FEN>] [moves <m1> <m2> …]` | Dựng thế cờ; replay moves; **chấp nhận FEN biến thể 10×10** (gồm 7+7 check, castling rights) |
| `go <params>` | Chạy search theo **mọi tham số** (U1.4); trả `info …` định kỳ + `bestmove <m> [ponder <m>]` |
| `stop` | Dừng search ngay, trả `bestmove` của kết quả tới thời điểm đó |
| `ponderhit` | (nếu hỗ trợ ponder) chuyển ponder-search thành search thật |
| `quit` | Thoát sạch |

**Quy tắc bền vững (robustness) theo đặc tả UCI — bắt buộc:**
- **Bỏ qua token lạ**, không crash; lệnh không nhận diện được thì im lặng (vd GUI gửi `cp`, `Hash`…).
- Token có thể cách nhau nhiều khoảng trắng; thứ tự tham số trong `go`/`position` linh hoạt.
- Mọi đáp ra kết thúc bằng `\n` và **flush** ngay (GUI chờ theo dòng).
- Không in gì thừa ra stdout ngoài giao thức (log dùng `info string …`).
- Sau `go`, **luôn** kết thúc bằng đúng một `bestmove` (kể cả thế hết cờ → `bestmove 0000`).

### U1.3. `option` (khai báo ở `uci`) — kiểu đúng chuẩn
Tối thiểu (chi tiết giá trị ở Mục U2), đúng cú pháp UCI từng `type`:
```
option name WeightsFile type string default model_gen0.onnx
option name Visits type spin default 800 min 1 max 1000000
option name Provider type combo default cpu var cpu var cuda
option name Threads type spin default 1 min 1 max 256
option name Temperature type spin default 0 min 0 max 1000          # ‰
option name Cpuct type string default 0                              # 0 = dùng mặc định search
option name MultiPV type spin default 1 min 1 max 64
option name MoveOverheadMs type spin default 30 min 0 max 5000
option name Ponder type check default false
... (xem U2)
```

### U1.4. `go` — hỗ trợ đầy đủ tham số
| Tham số `go` | Xử lý |
|--------------|-------|
| `nodes <N>` | dừng sau N playout (NodeLimitStopper — đã có) |
| `movetime <ms>` | dừng theo đồng hồ (TimeStopper mới) |
| `depth <d>` | xấp xỉ qua ngân sách node, hoặc giới hạn độ sâu cây |
| `wtime/btime/winc/binc/movestogo` | **time management**: ước lượng ngân sách mỗi nước (vd ~ thời-gian-còn-lại/movestogo, trừ `MoveOverheadMs`) |
| `infinite` | search tới khi `stop` |
| `searchmoves <m…>` | chỉ xét tập nước này tại root |
| `ponder` | search ở nền trên nước dự đoán (nếu bật Ponder) |
| `mate <n>` | (tùy chọn) dừng nếu tìm thấy chiếu hết ≤ n |

> Bản đầu (T8.1) chốt chắc `nodes` + `movetime` + `infinite/stop`; phần time-control `wtime/btime` + `searchmoves` + `ponder` để T8.2/T8.x nhưng **đã khai báo trong `uci`** để GUI thấy.

### U1.5. ⚠️ ĐÚNG-SAI #1: tọa độ 10×10 & lật canonical
- **Quy ước tọa độ UCI cho bàn 10×10:** file `a–j` (luôn 1 ký tự), rank `1–10` (**rank 10 là HAI chữ số**). Nước long-algebraic: `e2e4`, `a1a10`, `j9j10`; phong cấp thêm hậu tố quân: `a9a10v`. Không nhập nhằng vì file luôn là chữ. **GUI tự viết PHẢI dùng đúng quy ước này** (ghi rõ trong sách hướng dẫn).
- **Lật canonical:** tầng lczero làm việc ở canonical frame (bên-đang-đi ở dưới); GUI/FEN dùng tọa độ thật. → I/O nước phải xử lý **2 chiều**.
- **Giải pháp chốt:** dùng **parser của Fairy-Stockfish** (`UCI::to_move`/`UCI::move`) trên `Stockfish::Position` thật để vào/ra chuỗi (đã xử lý đúng rank 2 chữ số + nhập thành king-to-rook + phong cấp), rồi map sang/khỏi `lczero::Move` qua quan hệ from/to (+ `Flip(RANK_10)` khi Đen đi). Tránh tự lật thủ công.
- **Khóa bằng test** (U1.7) — đây là rủi ro số 1.

### U1.6. `info` — đủ trường cho GUI hiển thị
Mỗi `go`, phát `info` định kỳ và một dòng cuối:
```
info depth <d> seldepth <sd> nodes <N> nps <nps> time <ms> \
     score cp <c> wdl <w> <d> <l> multipv <k> pv <m1> <m2> …
```
- `score cp`: quy đổi từ `q = root.GetWL()` (vd kiểu lc0 `cp ≈ 90·tan(1.5637·q)`); KÈM `score wdl` (‰) để GUI WDL-aware.
- `pv`: lần theo chuỗi max-visit từ root; `MultiPV>1` thì in k nhánh tốt nhất.
- `mate <n>` nếu phát hiện chiếu hết bắt buộc.

### U1.7. Test `--test-uci` (bắt buộc — bộ conformance)
1. **Round-trip nước 2 chiều** qua bridge cho nhiều FEN (gồm **Đen-đi**, nhập thành, phong cấp, nước tới/đi từ **rank 10**): `gui_str → lczero::Move → gui_str` bằng chính nó & là nước hợp lệ thật.
2. **`position` đồng bộ:** dựng cùng thế bằng `fen <X>` và `startpos moves …` → FEN cuối trùng.
3. **Kết thúc ván:** thế chiếu-hết-1-nước → engine đi → `ComputeGameResult` đúng; hòa/7-check/stalemate đúng loại; thế hết cờ → `bestmove 0000`.
4. **Tất định:** `go nodes N` hai lần (noise/temp off) → cùng `bestmove`.
5. **Kịch bản giao thức** (chạy như GUI gửi): `uci`→thấy `uciok` + mọi `option`; `isready`→`readyok`; `ucinewgame`; `position startpos moves e2e4`; `go nodes 200`→đúng 1 `bestmove`; token lạ bị bỏ qua không treo; `quit` thoát.
6. **Robustness:** dòng rỗng, nhiều khoảng trắng, `go` thiếu tham số (mặc định), `stop` khi không search → không crash.

### U1.8. ⚠️ Kiến trúc vòng đời engine & ĐA LUỒNG (bổ sung sau phản biện — bắt buộc)
`run_arena` hiện gọi `search->RunBlocking(1)` (chặn luồng chính) — đúng cho arena (không cần `stop`), **SAI cho UCI** vì `go infinite`/thời gian dài cần luồng chính tiếp tục đọc stdin để nhận `stop`. **Tin tốt:** `classic::Search` của ta **đã có sẵn API bất đồng bộ** (`search.h`): `StartThreads(n)`, `Stop()`, `Abort()`, `Wait()`, cờ `std::atomic<bool> stop_`. Chỉ cần DÙNG đúng:

**(a) Mô hình luồng cho `go` (chuẩn engine UCI, giống Stockfish):**
```
go:   search = new Search(...);  search->StartThreads(Threads);   // KHÔNG block
      // luồng chính KHÔNG join ngay; tiếp tục vòng đọc stdin.
stop:        search->Stop();      // search tự dừng -> phát bestmove
go nodes/movetime: stopper tự dừng -> phát bestmove (không cần stop)
ponderhit:   chuyển trạng thái ponder->thật (đổi stopper), search vẫn chạy
quit:        search->Abort(); search->Wait();  // hủy sạch rồi thoát
```
- Một **luồng "search-done watcher"** (hoặc callback `OnSearchDone`) phát `bestmove` đúng MỘT lần khi search kết thúc (dù do stopper hay do `stop`).
- `go infinite` = stopper "không bao giờ tự dừng" → chỉ dừng bởi `stop`/`quit`.
- Đảm bảo **không hai search song song**: trước mỗi `go`, nếu còn search cũ thì `Stop()+Wait()`.

**(b) Đồng bộ option ↔ trạng thái engine (`setoption`):**
- Theo đặc tả UCI, `setoption` chỉ gửi khi engine **rảnh** (không search) → không phải xử lý giữa chừng search. Nhưng phải phân loại:
  - **Rẻ (áp ở `go` kế tiếp):** `Visits/Temperature/Cpuct/MultiPV/DrawScore/...` → chỉ ghi vào `OptionsDict`.
  - **Cấu trúc (phải DỰNG LẠI backend):** `WeightsFile/Provider/FixedBatch/Threads` → đặt cờ **`backend_dirty=true`**; **dựng lại** `OnnxBackend`+MemCache **lười** ở `isready`/`go` kế tiếp (không reload mỗi lệnh). `isready` chỉ trả `readyok` **sau khi** rebuild xong (đồng bộ).
- Quy ước tên option ⇄ key OptionsDict rõ ràng (U2.0 passthrough) để set đúng chỗ.

**(c) Quản lý bộ nhớ ở `ucinewgame`:**
- `NodeTree::ResetToPosition` **đã tự giải phóng** các node không-tới-được từ thế mới (gardener của lc0) ⇒ RAM bị **chặn theo từng ván**, không rò rỉ tích lũy. Nhưng để chắc:
  - `ucinewgame` → **dựng lại NodeTree** (hoặc `ResetToPosition` về rỗng) để xóa cây cũ; **tùy chọn clear NN MemCache** để trả RAM sau nhiều ván.
  - Trong 1 ván (nếu bật `ReuseTree`) cây lớn dần là **chủ ý** (tái dùng); chỉ reset ở ranh giới ván.
- Test (thêm vào `--test-uci`): chạy N lần `ucinewgame`+vài `go` liên tiếp, RAM không tăng đơn điệu.

> Ba điểm (a)(b)(c) đến từ phản biện ngoài — đều **đúng và cần thiết**; engine đã có đủ API để hiện thực. Nâng chúng thành DoD bắt buộc của **T8.1** (a,b,c) thay vì để T8.2.

---

## 3. MODULE U2 — Tối đa siêu tham số chỉnh tay (đối chiếu lc0 + lczero-training)

Triết lý: **expose càng nhiều càng tốt; cái ít dùng đặt mặc định hợp lý.**

> **🔑 PHÁT HIỆN LỚN (đối chiếu lc0):** project ta đã gọi `classic::SearchParams::Populate(&parser)` → **toàn bộ 75 tham số tìm kiếm của lc0 ĐÃ được biên dịch sẵn** trong `src/search/classic/params.cc` và nạp vào `OptionsDict`. Hiện ta chỉ set ~6 cái. Vì self-play VÀ chơi thật **dùng chung** bộ search này, chỉ cần **một cơ chế passthrough** là có ngay **toàn bộ siêu tham số search của lc0** cho cả hai luồng — gần như miễn phí. Đây là cách đạt "giống lc0" rẻ nhất.

### U2.0. Cơ chế then chốt: passthrough option chung (làm 1 lần, expose tất cả)
- **UCI (chơi):** với mọi `setoption name <X> value <Y>`, nếu `<X>` khớp một OptionId của `SearchParams`/`SharedBackendParams` → set thẳng vào `OptionsDict` (không cần hard-code từng cái). Các option "thân thiện" (Visits/Provider…) vẫn khai báo riêng cho GUI thấy; phần còn lại nhận qua tên lc0 (`cpuct-base`, `fpu-value`…).
- **CLI (sinh dữ liệu/arena):** thêm `--search-opt name=value` (lặp nhiều lần) đẩy thẳng vào OptionsDict. Một cờ → mọi param search.
- **Lợi:** không phải bảo trì 75 cờ tay; tự động "bắt kịp lc0".

### U2.A. Khi CHƠI (UCI) — option thân thiện + passthrough lc0 đầy đủ
**Khai báo `option` cho GUI (thân thiện):**

| Option | Kiểu | Mặc định | Ý nghĩa |
|--------|------|----------|---------|
| `WeightsFile` | string | model_gen0.onnx | Đời mạng |
| `Visits`/`Nodes` | spin | 800 | Playout/nước |
| `Provider` | combo | cpu | cpu / cuda |
| `FixedBatch` | spin | 16 | Batch CUDA |
| `Threads` | spin | 1 | Luồng MCTS |
| `MiniBatchSize` | spin | — | Node/lần gom (lc0 `minibatch-size`) |
| `Temperature` | spin ‰ | 0 | Đa dạng/hạ độ khó |
| `Cpuct` / `CpuctBase` / `CpuctFactor` | string | auto | PUCT (lc0) |
| `FpuStrategy` / `FpuValue` | string | auto | First-Play-Urgency |
| `PolicySoftmaxTemp` | string | 1.0 | Làm mềm prior |
| `DrawScore` | string | 0 | Thiên về/né hòa (lc0 `draw-score`) |
| `Contempt` / `ContemptMode` | string | 0 | Khinh địch (lc0) |
| `ScoreType` | combo | centipawn | Kiểu `score` báo cáo (lc0 `score-type`) |
| `MultiPV` | spin | 1 | Số PV |
| `MoveOverheadMs` | spin | 30 | Trừ hao thời gian |
| `NoiseEpsilon`/`NoiseAlpha` | string | 0 | Dirichlet (tắt khi chơi) |
| `Ponder` | check | false | Ponder |
| `ReuseTree` | check | true | Tái dùng cây giữa nước (lc0) |
| `TwoFoldDraws` | check | true | Coi lặp 2 lần = hòa (lc0) |
| `ResignThreshold`/`ResignEarliestMove`/`ResignWDLStyle` | string/spin/check | tắt | Engine tự xin thua (lc0-style) |

**+ passthrough toàn bộ lc0 search** (qua U2.0): `cpuct-at-root, cpuct-base-at-root, cpuct-factor-at-root, root-has-own-cpuct-params, fpu-*-at-root, max-collision-visits, max-collision-events, max-out-of-order-evals-factor, max-prefetch, out-of-order-eval, nps-limit, task-workers, max-concurrent-searchers, solid-tree-threshold, cache-history-length, sticky-endgames, search-spin-backoff, temp-* (cutoff-move, endgame, value-cutoff, visit-offset, decay-*), wdl-* (calibration-elo, draw-rate-*, eval-objectivity, contempt-attenuation, max-s, book-exit-bias), per-pv-counters, verbose-move-stats, …` (75 cái). *Lưu ý: nhóm `moves-left-*` để mặc định/N-A — mạng ta không có MLH head.*

**Điều chỉnh độ khó = tự chỉnh các nút riêng (QUYẾT ĐỊNH NGƯỜI DÙNG: KHÔNG làm combo `Skill`).**
Người dùng tự đặt `Visits`/`go nodes` (đòn bẩy mạnh nhất), `Temperature` (đa dạng/blunder nhẹ), và
`WeightsFile` (đời mạng) theo ý muốn. Gợi ý: Dễ ≈ `Visits 80` + `Temperature` cao; Vừa ≈ `go nodes 400`;
Khó ≈ `go nodes 2000+` + `Temperature 0`.
> **Việc cần làm để đủ nút (gộp vào T8.3):** hiện `EmitBestMove` chọn nước **greedy** (max-visit) → option
> `Temperature` MỚI chỉ khai báo, **chưa nối** vào khâu chọn nước. Cần nối temperature-sampling (lấy mẫu
> theo số visit, như `SelectMoveEdge` của self-play) để `Temperature` thực sự hạ độ khó. `Visits` thì
> **đã chạy ngay**.

### U2.B. Khi SINH DỮ LIỆU (`--selfplay`)
**Đã có:** `--games --visits --parallel --threads-per-game --max-moves --temp-cutoff --backend-threads --provider --fixed-batch --weights --out --noise-epsilon --noise-alpha --policy-temp --cpuct --start-fen --resign-threshold --resign-consecutive --no-resign-frac`.

**Thêm theo lc0 (selfplay/game.cc + tournament.cc):**
| Cờ mới | Nguồn lc0 | Ý nghĩa | Mặc định |
|--------|-----------|---------|----------|
| `--search-opt k=v` (lặp) | (U2.0) | đẩy **bất kỳ** param search lc0 (full temperature-decay, fpu, cpuct-base/factor…) | — |
| `--resign-earliest-move N` | `resign-earliest-move` | cấm resign trước nước N | 0 |
| `--resign-wdlstyle` | `resign-wdlstyle` | resign theo ngưỡng WDL thay vì q | off |
| `--reuse-tree` | `reuse-tree` | tái dùng cây trong 1 ván self-play (nhanh hơn) | off |
| `--temp-decay-moves`/`--temp-decay-delay`/`--temp-endgame`/`--temp-cutoff-move`/`--temp-visit-offset`/`--temp-value-cutoff` | search temperature schedule | lịch hạ nhiệt độ giống lc0 (đa dạng đầu ván, sắc bén cuối ván) | lc0 defaults |
| `--two-fold-draws` | `two-fold-draws` | lặp 2 lần = hòa (rút ngắn ván) | off |
| `--game-movetime ms` / `--game-time-budget` | (time mgr) | giới hạn theo thời gian thay vì visits | — |

> **KHÔNG làm sách khai cuộc PGN** (phản biện đúng + theo ý người dùng): PGN dùng SAN (ký hiệu rút gọn, không ghi ô xuất phát) → cần bộ **giải mã SAN + disambiguation** quét cả bàn để tìm quân hợp lệ; viết lại cho bàn 10×10 + quân tùy biến là **cực rủi ro** (dễ crash/đi sai nước). `custom_engine` chỉ nhúng lõi MoveGen/Position, **không** nhúng trình quản lý PGN của Stockfish. → **Bỏ hẳn `--openings-pgn`/`--openings-mode`/`--mirror-openings`/`--discarded-start-chance`.** Đa dạng đầu ván (nếu cần về sau) chỉ qua **`--start-fen`** đã có sẵn — nhận **FEN** (1 FEN hoặc file FEN mỗi dòng), **không đụng SAN**, an toàn. Mặc định: **startpos thuần, NN tự gánh** (xem U2.D).

### U2.C. Khi HUẤN LUYỆN (`train.py`/`loop.py`)
**Đã có:** `--data --epochs --batch --lr --q-ratio --downsample --channels --blocks --out --init-from --threads --workers --pin-memory --no-cache --diff-focus --df-slope --df-kld-w --df-min --weight-decay --value-weight --swa-start-frac --swa-lr --device --amp --sparse-cache/--dense-cache`; loop: `--gens --start-gen --games-per-gen --window-gens --eval-games`.

**Thêm theo lczero-training (configs/example.yaml + tfprocess.py + chunkparser.py):**
| Cờ mới | Nguồn lczero-training | Ý nghĩa | Mặc định |
|--------|----------------------|---------|----------|
| `--lr-values a,b,c` + `--lr-boundaries i,j` | `lr_values`/`lr_boundaries` | **lịch LR bậc thang** (thay LR hằng) | =`--lr` |
| `--warmup-steps N` | `warmup_steps` | tăng LR tuyến tính lúc đầu | 0 |
| `--policy-weight W` | `policy_loss_weight` | trọng số loss policy (đối xứng `--value-weight`) | 1.0 |
| `--optimizer {adamw,sgd,nadam}` | `new_optimizer` | chọn bộ tối ưu (SGD+momentum giống lc0 chuẩn) | adamw |
| `--momentum M` | (SGD) | momentum khi dùng SGD | 0.9 |
| `--lookahead` | `lookahead_optimizer` | bọc Lookahead optimizer | off |
| `--grad-clip G` | (loss_scale/precision đi kèm) | clip norm gradient | off |
| `--accum-steps K` | (effective batch) | tích lũy gradient → batch hiệu dụng lớn trên GPU nhỏ | 1 |
| `--loss-scale S` / `--precision {fp32,fp16}` | `loss_scale`/`precision` | song hành với `--amp` | auto |
| `--dropout R` | `dropout_rate` | dropout trong head | 0 |
| `--batch-renorm` | `renorm`/`renorm_max_r`/`renorm_max_d` | batch renormalization | off |
| `--se-ratio R` | `se_ratio` | tỉ lệ nén SE block (kiến trúc) | 8 |
| `--ema D` | (alt SWA) | trung bình mũ trọng số (thay/cạnh SWA) | off |
| `--swa-max-n N` / `--swa-every K` | `swa_max_n`/`swa_steps` | số/nhịp ảnh SWA gộp | auto |
| `--max-steps N` | `total_steps` | dừng theo số bước (thay/cạnh `--epochs`) | — |
| `--val-split F` + `--test-every N` | `train_ratio`/`test_steps` | tách tập kiểm định + báo định kỳ | off |
| `--report-every N` | `train_avg_report_steps` | nhịp in loss trung bình | — |
| `--save-every N` | `checkpoint_steps` | lưu checkpoint định kỳ | cuối |
| `--shuffle-size N` | `shuffle_size` | cỡ ShuffleBuffer khi streaming (đã có lớp, nối vào `--no-cache`) | — |
| `--max-records N` / `--num-chunks N` | `num_chunks` | giới hạn dữ liệu nạp | tất cả |
| `--reg-term-weight` (alias `--weight-decay`) | `reg_term_weight` | L2 (đã có) | 1e-4 |
| `--seed S` | (tái lập) | hạt giống RNG | 0 |

### U2.D. KHÔNG kế thừa (không hợp kiến trúc — ghi rõ để khỏi nhầm)
- **Moves-Left Head (MLH):** `moves-left-*` (search) + `moves_left_loss_weight` (train) — bỏ. **Đã kiểm chứng vô hại:** MCTS của ta kế thừa toàn bộ máy MLH từ lc0, NHƯNG `OnnxBackend::GetAttributes()` đặt `.has_mlh=false` (`onnx_backend.cc:264`), và search **gate mọi logic moves-left theo cờ này** (`search.cc:554/966/1667`: khi `has_mlh=false` tạo `MEvaluator()` rỗng → `GetMUtility` trả 0). Nghĩa là **các param `moves-left-*` không bao giờ được dùng, không ảnh hưởng nước đi hay tốc độ** — đúng cách lc0 chạy mạng không có MLH head. Để mặc định, không expose, không lo.
- **Attention policy / Smolgen / encoder-* / arc_encoding:** kiến trúc transformer của lc0 mới; ta chốt **SE-ResNet 10x128** → bỏ (chỉ giữ `filters/blocks/se_ratio/dropout`).
- **Syzygy tablebase / sách tàn cuộc** (`syzygy-paths`, `syzygy-fast-play`, rescorer): **bỏ hẳn** — theo quyết định người dùng, **để NN tự gánh** tàn cuộc (không EGTB).
- **Sách khai cuộc PGN** (`--openings-pgn`, SAN parser, openings-mode/mirror/discard): **bỏ hẳn** — (1) SAN cho bàn 10×10 + quân tùy biến quá rủi ro (disambiguation, dễ crash/sai nước) và `custom_engine` không nhúng trình PGN của Stockfish; (2) theo quyết định người dùng **để NN tự gánh khai cuộc**. Mặc định **startpos thuần**; nếu sau này cần đa dạng thì chỉ dùng `--start-fen` (FEN, không SAN).
- **input_type/input_gate, value='wdl' variants, policy_channels (attention):** không áp dụng.

> **Sản phẩm phụ T8:** **DANH MỤC SIÊU THAM SỐ hợp nhất** (U2.A/B/C + tham chiếu tên lc0) đưa vào `HUONG_DAN.md` (U4.D), kèm kiểu/mặc định/khoảng để tra nhanh khi tinh chỉnh.

---

## 4. MODULE U3 — MỘT bản portable tất-cả-trong-một (Windows CPU + Colab GPU)

Khác plan cũ (3 bản rời) — theo yêu cầu, gộp thành **một bundle duy nhất** làm được cả chơi/sinh/huấn luyện trên cả 2 nền:

```
FairyZero/                          ← copy là chạy / clone lên Colab là chạy
├─ bin/
│   ├─ windows/custom_engine.exe            (build CPU sẵn cho Windows)
│   └─ onnxruntime*.dll                     (đủ DLL ORT CPU)
├─ src/ , meson.build , third_party/        (mã nguồn — để BUILD trên Colab GPU)
├─ scripts/
│   ├─ build_colab.sh   (= colab_setup.sh: build Linux+CUDA trên Colab)
│   ├─ package.ps1 / package.sh
│   └─ play.bat / play.sh                    (chạy --uci-nn với model mặc định)
├─ python/                                  (train.py, loop.py, dataset.py, archive.py, test_*…)
│   └─ requirements.txt
├─ models/model_genN.onnx (+ .pt)           (mạng mạnh nhất hiện có + seed)
├─ variant.ini                              (định nghĩa biến thể 10×10)
├─ VERSION.txt                              (đời mạng + git hash)
└─ HUONG_DAN.md                             (sách hướng dẫn — U4)
```

- **Windows (không GPU):** dùng `bin/windows/custom_engine.exe` để **chơi** (UCI) và **sinh dữ liệu** (CPU); **huấn luyện** bằng `python train.py --device cpu` (chậm nhưng chạy được — bản "hoàn hảo" như bạn muốn).
- **Colab (GPU):** chạy `bash scripts/build_colab.sh` để build engine Linux+CUDA, rồi sinh dữ liệu `--provider cuda` và huấn luyện `--device cuda --amp`. Truyền dữ liệu qua `archive.py` (Mục 7 T7.5).
- **Tự đóng gói lại:** `package.ps1`/`package.sh` gom đúng cây trên, kiểm tra đủ DLL/SO (test máy sạch).
- **Cùng một bộ mã** cho cả 2 nền (đã đa nền tảng từ T6.5) → không phân mảnh.

---

## 5. MODULE U4 — Sách hướng dẫn `HUONG_DAN.md` (người không-dev)

Một tài liệu tiếng Việt, từng bước, copy-paste được, 4 phần:

- **A. Chơi với AI (qua UCI/terminal hoặc GUI tự viết):**
  - Quy ước nước đi UCI cho bàn 10×10 (file a–j, rank 1–10, **rank 10 hai chữ số**, phong cấp hậu tố quân) — để GUI tự viết khớp.
  - Kịch bản UCI tối thiểu để chơi tay trong terminal; bảng `setoption` mức độ khó.
  - (Tùy chọn) lệnh `--play` ASCII để đánh ngay trong terminal không cần GUI.
- **B. Sinh dữ liệu tự chơi:** lệnh Windows (CPU) & Colab (GPU) + giải thích resign/no-resign, parallel, visits; gom `archive.py pack` rồi tải Drive.
- **C. Huấn luyện:** Windows CPU (chậm) vs Colab GPU (khuyến nghị, `--amp`); một đời (`train.py`) vs vòng lặp đầy đủ (`loop.py`); ý nghĩa `.onnx` vs `.pt`, rolling window, arena.
- **D. DANH MỤC SIÊU THAM SỐ** (bảng hợp nhất U2.A/B/C: tên, kiểu, mặc định, khoảng, ý nghĩa) để tra nhanh khi tinh chỉnh.

---

## 6. (Tùy chọn) Front-end `--play` ASCII trong terminal

Để chơi/thử ngay trong terminal **trước khi GUI riêng xong**:
- C++ `--play [--human-white|--human-black] [--visits N …]`: in bàn cờ ASCII 10×10, đọc nước người gõ (đúng quy ước UCI), gọi MCTS đáp, lặp tới hết ván. Tái dùng vòng arena, thay 1 bên bằng stdin. Nhẹ, không phụ thuộc.
- Đây là tiện ích phụ; **đường chính vẫn là `--uci-nn`** để GUI tự viết cắm vào.

---

## 7. Phân kỳ / Milestones T8

| Phase | Nội dung | Definition of Done |
|-------|----------|--------------------|
| **T8.1** | `--uci-nn` lõi + tuân thủ UCI: `uci/isready/setoption/ucinewgame/position/go(nodes,movetime,infinite)/stop/quit`, robust parsing, lật canonical 2 chiều, `option` khai báo đủ, **+ kiến trúc đa luồng U1.8: (a) search bất đồng bộ qua `StartThreads/Stop/Wait` để `stop`+`go infinite` hoạt động; (b) rebuild backend lười khi đổi WeightsFile/Provider/Threads; (c) reset cây ở `ucinewgame`** | `--test-uci` PASS (round-trip 2 chiều gồm Đen-đi/nhập thành/phong cấp/rank10; `position` đồng bộ; tất định; kịch bản giao thức; robustness; **`go infinite`→`stop` trả bestmove; đổi WeightsFile giữa ván OK; N×`ucinewgame` RAM không phình**). Điều khiển tay qua terminal đánh hết 1 ván hợp lệ. |
| **T8.2** | `info score cp/wdl + pv + multipv`, time-control `wtime/btime/winc/binc/movestogo`, `searchmoves`, `ponder/ponderhit` | GUI tự viết hiển thị eval/pv & chơi có đồng hồ; dừng/ponder đúng. |
| **T8.3** | **Siêu tham số đầy đủ kiểu lc0:** cơ chế passthrough chung (U2.0) → expose toàn bộ 75 search-param lc0 cho cả chơi (`setoption`) lẫn self-play (`--search-opt k=v`); **nối `Temperature` (+ TempCutoffPly) vào khâu chọn nước của `EmitBestMove`** (lấy mẫu theo visit) để tự chỉnh độ khó; thêm cờ self-play lc0 (resign-earliest/wdlstyle, reuse-tree, temperature-decay, two-fold-draws) (U2.B; KHÔNG sách khai cuộc PGN — để NN tự gánh); thêm cờ training lczero-training (lr-schedule+warmup, optimizer, grad-clip, accum, dropout, renorm, ema, save/test/report, shuffle-size…) (U2.C) | `setoption`/`--search-opt` đặt được mọi search-param lc0 (test: đặt `cpuct-base` đổi hành vi); `Temperature>0` thực sự đa dạng hóa nước đi; train chạy với lr-schedule + optimizer mới; DANH MỤC siêu tham số hợp nhất hoàn chỉnh trong U4.D. |
| **T8.4** | Bản portable tất-cả-trong-một + `package.ps1`/`package.sh` + `play.bat/sh` | Chạy trên Windows sạch (không MSYS2): chơi + sinh + train CPU OK. |
| **T8.5** | Đường Colab: `build_colab.sh` trong bundle; sinh + train GPU | Trên Colab: build → chơi/sinh/train GPU OK từ chính bundle. |
| **T8.6** | `HUONG_DAN.md` (A/B/C/D) | Người không-dev làm trọn chơi/sinh/huấn luyện trên Win + Colab. |
| **T8.x** (sau) | `--play` ASCII; **nối Temperature vào chọn nước** (đã chuyển trọng tâm sang T8.3); tái dùng cây giữa nước; `mate`; tinh chỉnh time-control | Tiện ích/đánh bóng, không chặn bản dùng được. (KHÔNG làm combo `Skill` — theo ý người dùng.) |

**Thứ tự khuyến nghị:** T8.1 → T8.4 (đã chơi + đóng gói chơi-được trên Windows) → T8.6 (hướng dẫn) → T8.2/8.3 (đầy đủ UCI + siêu tham số) → T8.5 (Colab) → T8.x.

---

## 8. Rủi ro & Quyết định đã chốt

1. **Tọa độ 10×10 + lật canonical (rủi ro #1):** sai lật/parse rank 2 chữ số ⇒ engine đi nước khác ý hoặc từ chối nước người, và GUI tự viết sẽ lệch. → Mượn parser Fairy-SF; khóa bằng `--test-uci` round-trip 2 chiều (gồm rank 10) **trước** mọi việc khác. Ghi quy ước vào sách hướng dẫn.
2. **Tuân thủ UCI tuyệt đối (yêu cầu cốt lõi):** thiếu/ sai một lệnh là GUI tự viết treo. → Hiện thực **đầy đủ** tập lệnh + quy tắc robustness; bộ `--test-uci` mô phỏng GUI; đối chiếu với đặc tả UCI gốc.
3. **Portable đủ phụ thuộc:** thiếu DLL/SO ⇒ không chạy máy khác. → Test máy Windows sạch + Colab tươi; `package.*` kiểm đủ.
4. **Time management:** sai có thể thua vì hết giờ. → Bản đầu `nodes/movetime` chắc chắn; `wtime/btime` ở T8.2 test kỹ với `MoveOverheadMs`.
5. **Không nhiễu khi chơi thật:** mặc định tắt Dirichlet + Temperature để AI hết sức; chỉ bật khi người dùng chủ động hạ độ khó.
6. **GUI do người dùng tự viết:** T8 KHÔNG làm GUI; chỉ đảm bảo engine + tài liệu quy ước đủ để GUI bất kỳ (UCI) cắm vào. (Đính chính phạm vi.)

---

## 9. Tóm tắt các bước thực hiện tiếp theo

1. **T8.1**: tách `uci_nn_loop()` trong `main.cc` (state = NodeTree + backend + options + bảng option). Hiện thực đầy đủ lệnh UCI + robust parsing. Chốt parser nước (Fairy-SF) + lật 2 chiều. Viết `--test-uci`. Đánh thử tay 1 ván trong terminal.
2. **T8.4**: `package.ps1`/`package.sh` → bundle tất-cả-trong-một + `play.bat/sh`; test Windows sạch.
3. **T8.6**: `HUONG_DAN.md` (A chơi / B sinh / C huấn luyện / D danh mục siêu tham số).
4. **T8.2/8.3**: info/score/pv/multipv, time-control, ponder, searchmoves; expose nốt siêu tham số chơi + rà gen/train.
5. **T8.5**: đường Colab trong bundle (build + gen + train GPU).
6. **T8.x**: `--play` ASCII, tái dùng cây, mate, tinh chỉnh time-control (nối Temperature vào chọn nước → gộp T8.3; KHÔNG làm combo Skill).

> **Kết quả cuối T8:** một engine **tuân thủ UCI đầy đủ** chạy ổn trên terminal (sẵn sàng cho GUI bạn tự viết), nằm trong **một bản portable duy nhất** cho **chơi / sinh dữ liệu / huấn luyện** trên **cả Windows (CPU) lẫn Colab (GPU)**, với **tối đa siêu tham số chỉnh tay** và một **sách hướng dẫn** đi kèm.
