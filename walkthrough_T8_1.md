# Walkthrough T8.1 — Engine UCI điều khiển MCTS + ONNX (terminal)

> Phạm vi: triển khai **T8.1** trong `implementation_plan phase T8.md` — biến `custom_engine` thành một **engine tuân thủ UCI** chạy trên terminal, dùng đúng "bộ não" AlphaZero của ta (MCTS + mạng ONNX) thay vì alpha-beta của Stockfish. Đây là nền để bạn cắm vào **GUI tự viết** cho biến thể 10×10.
> Ngày: 2026-06-20. Toàn bộ thay đổi nằm trong `src/main.cc`. Đã build (ninja) + kiểm thử trên Windows.

---

## 0. Mục tiêu & bối cảnh

Trước T8, engine có 2 "bộ não" tách biệt:
- `UCI::loop` của **Stockfish** (alpha-beta + NNUE) — dùng để debug movegen, KHÔNG phải mạng ta huấn luyện.
- MCTS + ONNX — chỉ chạy trong `--selfplay` và `--arena` (máy đánh máy), **chưa có đường cho con người/GUI điều khiển**.

T8.1 viết một **vòng lặp UCI riêng** (`--uci-nn`) lái MCTS + ONNX, tái dùng đúng vòng chơi mà `run_arena` đã chứng minh. Yêu cầu cốt lõi (theo đính chính của bạn): **tuân thủ UCI đầy đủ + chạy ổn terminal** để GUI bất kỳ (gồm GUI bạn tự viết) cắm vào là chạy.

---

## 1. Tổng quan những gì đã thêm (tất cả trong `src/main.cc`)

| Thành phần | Vai trò |
|------------|---------|
| `--uci-nn` (cờ CLI) + `run_uci_nn()` | Vào chế độ engine UCI |
| `--test-uci` (cờ CLI) + `run_uci_tests()` | Bộ conformance khóa rủi ro #1 (I/O nước) |
| `kUciStartFen` | FEN xuất phát biến thể 10×10 |
| `CanonicalMoveToUci()` / `UciToCanonicalMove()` | Ánh xạ nước đi 2 chiều canonical ⇄ tọa độ thật |
| `InfiniteStopper` / `TimeStopper` | Điều kiện dừng cho `go infinite` / `go movetime` |
| `class UciNnEngine` | Máy trạng thái UCI + quản lý search đa luồng |

Thêm includes: `<thread> <atomic> <mutex> <chrono> <memory> <map>`.

---

## 2. Điểm đúng-sai #1: I/O nước đi & lật canonical

Đây là rủi ro lớn nhất của T8.1, đã được khóa.

### 2.1. Vấn đề
- Tầng lczero làm việc ở **canonical frame** (luôn xoay để bên-đang-đi ở phía dưới). `GenerateLegalMoves()` trả nước **canonical**.
- GUI/FEN dùng **tọa độ bàn cờ thật** (a1…j10, Trắng ở dưới). Khi **Đen đi**, hai hệ lệch nhau **một phép lật dọc** `RANK_10`.
- Bàn 10×10 còn có **rank 2 chữ số** (hàng 10): nước UCI dạng `a1a10`, phong cấp `a9a10v`.

### 2.2. Giải pháp (tái dùng phép lật đã test của self-play)
`self-play` vốn đã in nước cho người đọc bằng `display_move.Flip(RANK_10)` khi Đen đi, rồi `Move::ToString()`. T8.1 dùng **đúng** convention đó cho **cả 2 chiều**:

```cpp
// canonical -> chuỗi UCI tọa độ thật
static std::string CanonicalMoveToUci(lczero::Move m, bool black_to_move) {
    lczero::Move d = m;
    if (black_to_move) d.Flip(Stockfish::RANK_10);   // canonical -> real
    return d.ToString();                              // a1..j10 (+ hậu tố phong cấp)
}

// chuỗi UCI -> nước canonical (quét legal moves, khớp chuỗi)
static lczero::Move UciToCanonicalMove(const lczero::ChessBoard& board,
                                       const std::string& uci, bool black_to_move) {
    lczero::MoveList legal = board.GenerateLegalMoves();      // canonical
    for (size_t i = 0; i < legal.size(); ++i)
        if (CanonicalMoveToUci(legal[i], black_to_move) == uci) return legal[i];
    return lczero::MOVE_NONE;                                 // illegal/không khớp
}
```

**Vì sao cách này đúng chắc chắn:** parse là **nghịch đảo theo cấu trúc** của format (cùng một hàm `CanonicalMoveToUci` dùng cho cả ra lẫn so khớp). Nhập thành/phong cấp/rank-10 đều nằm trong tập legal nên đều khớp được. `Move::ToString()` của ta đã có bảng tọa độ 10×10 đầy đủ (gồm `a10..j10`) và hậu tố quân phong cấp.

> **Hệ quả cho GUI tự viết:** GUI phải gửi/nhận nước theo đúng quy ước này (from-square + to-square tọa độ thật, vd `e2e4`, `a1a10`, phong cấp `a9a10v`). Engine tự-nhất-quán; `--test-uci` khóa điều đó.

---

## 3. Kiến trúc đa luồng (U1.8) — `class UciNnEngine`

`run_arena` dùng `search->RunBlocking(1)` chặn luồng chính — đúng cho arena nhưng **sai cho UCI** vì `go infinite` cần luồng chính tiếp tục đọc stdin để nhận `stop`. Engine của ta **đã có sẵn** API bất đồng bộ (`Search::StartThreads/Stop/Abort/Wait`, cờ `std::atomic stop_`), chỉ cần dùng đúng.

### 3.1. Mô hình luồng (a)
- `go` → tạo `Search`, **chạy `RunBlocking(threads)` trên một `std::thread` riêng**; luồng chính quay lại đọc stdin ngay.
- Khi search xong (stopper kích hoạt **hoặc** `Stop()`), luồng search gọi `EmitBestMove()` → in `bestmove` **đúng một lần**, rồi đặt `searching_=false`.

```cpp
void HandleGo(std::istringstream& is) {
    StopSearch();                                  // dọn search cũ (nếu còn)
    if (!EnsureBackend()) { Send("bestmove 0000"); return; }
    // ... đọc nodes / movetime / infinite ...
    std::unique_ptr<SearchStopper> stopper =
        infinite ? InfiniteStopper
        : movetime>0 ? TimeStopper(movetime - move_overhead)
        : NodeLimitStopper(nodes>0 ? nodes : default_visits_);
    search_ = std::make_unique<Search>(*tree_, backend_.get(), SilentUciResponder,
                                       {}, now, std::move(stopper), infinite, false,
                                       parser_->GetOptionsDict(), nullptr);
    searching_.store(true);
    search_thread_ = std::thread([this, threads]{
        search_->RunBlocking(threads);             // chặn tới khi stopper/Stop()
        EmitBestMove();
        searching_.store(false);
    });
}
```

- `stop` → `StopSearch()`: nếu đang search thì `search_->Stop()` rồi `join()` (bestmove được phát trong luồng search). 
- `go infinite` → `InfiniteStopper::ShouldStop` luôn trả `false` ⇒ chỉ dừng khi `stop`/`quit`.
- `quit` → `AbortSearch()`: `Abort()` (không phát bestmove) + join, rồi thoát.
- `ReapIfDone()` (đầu mỗi vòng lặp): nếu search đã tự xong (`nodes`/`movetime`) thì `join()` để thu dọn luồng.

**Tự định dạng đầu ra:** ta truyền `SilentUciResponder` (không để search tự in theo định dạng lc0) và **tự** in `bestmove`/`info` để kiểm soát tọa độ canonical→real.

### 3.2. `EmitBestMove` — chọn nước hết sức (greedy max-visit)
```cpp
void EmitBestMove() {
    Node* root = tree_->GetCurrentHead();
    EdgeAndNode best; uint64_t best_n = 0;
    for (const auto& e : root->Edges())
        if (e.GetN() >= best_n) { best_n = e.GetN(); best = e; }
    Move m = best.GetMove();
    if (m.is_null()) { Send("bestmove 0000"); return; }   // hết cờ / không nước
    Send("bestmove " + CanonicalMoveToUci(m, tree_->IsBlackToMove()));
}
```
Chơi thật = **không nhiễu Dirichlet, không temperature** (mặc định), chọn nước nhiều visit nhất — giống `run_arena`.

### 3.3. Đồng bộ option ↔ backend (b)
- Theo đặc tả UCI, `setoption` chỉ gửi khi engine **rảnh** → không cần xử lý giữa search.
- Phân loại trong `HandleSetOption`:
  - **Rẻ:** `Visits/Threads/MoveOverheadMs` → chỉ ghi biến.
  - **Cấu trúc:** `WeightsFile/Provider/FixedBatch/BackendThreads/PolicySoftmaxTemp` → đặt `backend_dirty_=true`.
- `EnsureBackend()` **dựng lại lười** (chỉ khi dirty) ở `isready`/`go` kế tiếp; bọc try/catch để file weights thiếu không làm sập (in `info string failed to load backend: …`).

### 3.4. Quản lý bộ nhớ `ucinewgame` (c)
```cpp
else if (cmd == "ucinewgame") {
    StopSearch();
    tree_ = std::make_unique<NodeTree>();   // giải phóng cây cũ, dựng mới
    tree_->ResetToPosition(kUciStartFen, {});
}
```
`NodeTree::ResetToPosition` vốn đã tự giải phóng node không-tới-được (gardener của lc0) nên RAM bị chặn theo ván; ở đây ta dựng hẳn cây mới ở ranh giới ván cho chắc.

### 3.5. An toàn đầu ra đa luồng
Mọi dòng ra đi qua `Send()` có khóa `std::mutex io_mu_` + `std::flush`, nên `info`/`bestmove` từ luồng search không chen vào `readyok`/`uciok` từ luồng chính.

---

## 4. Tập lệnh UCI đã hỗ trợ (`UciNnEngine::Loop`)

| Lệnh | Hành vi |
|------|---------|
| `uci` | In `id name`, `id author`, **8 `option`** (WeightsFile/Visits/Provider/FixedBatch/Threads/BackendThreads/PolicySoftmaxTemp/MoveOverheadMs), `uciok` |
| `isready` | `EnsureBackend()` (đồng bộ) → `readyok` |
| `setoption name X value Y` | Đặt option; rẻ vs cấu trúc (Mục 3.3); tên lạ bỏ qua |
| `ucinewgame` | Dừng search + dựng cây mới |
| `position [startpos\|fen …] [moves …]` | Dựng thế; replay moves qua `UciToCanonicalMove` + `MakeMove` |
| `go [nodes\|movetime\|infinite]` | Search bất đồng bộ → `bestmove` |
| `stop` | Dừng search → `bestmove` |
| `ponderhit` / `debug` / `register` | Nhận & bỏ qua (chưa cần) |
| `quit` | Hủy search + thoát |

**Robustness (đặc tả UCI):** dòng rỗng / token lạ bị bỏ qua không treo; `cmd` tách bằng `>>` nên tự bỏ `\r` (CRLF) và khoảng trắng thừa; mọi đáp ra `\n` + flush; luôn kết thúc `go` bằng đúng một `bestmove` (hết cờ → `bestmove 0000`).

### Xử lý `position` (lưu ý canonical)
KHÔNG dùng cơ chế parse-move-string của `ResetToPosition` (nó parse theo canonical + Mirror nội bộ, không khớp tọa độ thật của GUI). Thay vào đó:
```cpp
tree_->ResetToPosition(fen, {});                 // chỉ set thế bắt đầu
while (is >> mv) {
    bool black = tree_->IsBlackToMove();
    auto& board = tree_->GetPositionHistory().Last().GetBoard();
    Move m = UciToCanonicalMove(board, mv, black);  // tự lật đúng
    if (m.is_null()) break;                          // nước lạ/phi pháp -> dừng
    tree_->MakeMove(m);
}
```
`IsBlackToMove()` được truy vấn lại sau mỗi nước (đổi lượt).

---

## 5. ⚠️ Hai lỗi đã gặp & sửa (ghi lại để khỏi vấp lại)

### 5.1. `NodeTree` trên stack → tràn stack (crash exit 253)
`PositionHistory` chứa mảng tĩnh 512-ply → một `NodeTree` rất to. Khai báo `lczero::classic::NodeTree tree;` **trên stack** (trong `run_uci_tests`) làm **tràn stack** trên Windows → crash ngay.
**Sửa:** heap-allocate **mọi** NodeTree bằng `std::make_unique` (giống self-play/arena). `UciNnEngine` vốn đã dùng `make_unique`; chỉ test bị sót.

### 5.2. Hiểu sai giá trị trả về của `ResetToPosition`
```cpp
bool NodeTree::ResetToPosition(...) { ... return seen_old_head; }
```
Giá trị trả về là **cờ "cây cũ có tái dùng được không"**, KHÔNG phải thành/bại. Với cây mới luôn `false`. Ban đầu tôi viết `if (!ResetToPosition(...)) FAIL` → mọi FEN (kể cả startpos) bị báo "bad FEN".
**Sửa:** bỏ kiểm tra giá trị trả về; FEN sai thì `Position::FromFen` **ném exception** → bọc `try/catch` (fallback về startpos + `info string`).

> Bài học: trong lc0, `ResetToPosition` trả về thông tin *tái dùng cây*; muốn bắt FEN sai phải bắt exception, không xem bool.

---

## 6. Bộ test `--test-uci` (khóa rủi ro #1, không cần backend)

`run_uci_tests()` chạy thuần logic (không nạp mạng), gồm:
1. **Round-trip nước 2 chiều** trên nhiều FEN (gồm **Đen-đi**, có quân ở rank 10): mọi nước hợp lệ `m` thỏa `UciToCanonicalMove(CanonicalMoveToUci(m)) == m` và chuỗi đúng định dạng.
2. **Absolute check:** từ startpos (Trắng, không lật) nước `b3b4` phải hợp lệ → chứng minh tọa độ Trắng không bị lật. *(Lưu ý biến thể: tốt Trắng `P` nằm ở **rank 3** — hàng `YPPPPPPPPY` — không phải rank 2; rank 2 là quân nhẹ.)*
3. **Position-sync:** startpos + `b3b4` → FEN kết quả dựng lại bằng `ResetToPosition` trùng khớp.

Kết quả:
```
=== UCI move-I/O conformance (--test-uci) ===
  move round-trip: 52/52 over 4 positions (incl Black-to-move)
  absolute check: startpos b3b4 is legal (White coords un-flipped) [OK]
  position-sync: startpos+b3b4 FEN round-trips [OK]
[PASS] UCI move-I/O conformance.
```

---

## 7. Kiểm thử chức năng (engine thật + seed model)

Chạy qua **Bash `< file`** (xem cảnh báo Mục 8). Tóm tắt kết quả:

| Kịch bản | Kết quả |
|----------|---------|
| `uci` | `id name/author` + 8 `option` + `uciok` ✓ |
| `isready` | nạp model → `readyok` ✓ |
| `position startpos moves b3b4` → `go nodes 30` | `bestmove c9a7` (nước **Đen**, lật đúng) ✓ |
| `go movetime 500` | `bestmove c2a4` (Trắng) ✓ |
| `go infinite` → `stop` | `bestmove c2a4` (dừng bất đồng bộ) ✓ |
| `isready` **trong khi** `go infinite` | `readyok` trả ngay (luồng riêng) ✓ |
| `setoption name WeightsFile value <seed>` | rebuild backend, dùng mạng mới ✓ |
| 10× `ucinewgame`+`go` | 10 `bestmove`, không crash ✓ |
| **Tất định cache-lạnh** (3 tiến trình riêng) | đều `c2a4` ✓ |
| Token lạ / `go` thiếu tham số / `setoption` tên lạ | bỏ qua, không treo (exit 0) ✓ |

**Về "tất định":** trong **cùng một tiến trình**, hai `go nodes 50` liên tiếp có thể ra nước khác nhau (`c2a4` rồi `j3j5`) — KHÔNG phải nhiễu, mà do **cache eval của MCTS còn ấm** từ lần search trước (giống lc0; là tính năng tái dùng, có lợi). Khi **cache lạnh** (mỗi tiến trình riêng), kết quả **trùng tuyệt đối** → engine tất định, không có ngẫu nhiên ẩn.

---

## 8. ⚠️ Cảnh báo khi tự test: PowerShell pipe nuốt dòng đầu

`@("uci","isready",...) | & engine.exe` của PowerShell **làm mất dòng/đầu ra ĐẦU TIÊN** (do tương tác pipeline + mã hóa UTF-16 + stdin tiến trình). Khi test bằng cách này, `uciok` "biến mất" làm tưởng engine lỗi. **Thực tế engine đúng** — kiểm bằng **Bash redirect file**:
```bash
printf 'uci\nisready\nquit\n' > in.txt
./build/custom_engine.exe --uci-nn < in.txt > out.txt 2>&1
```
cho ra đầy đủ, đúng thứ tự. (Đầu ra trên Windows là CRLF `\r\n` — GUI UCI xử lý được.)

---

## 9. Cách dùng nhanh

```bash
# Chạy engine UCI (mặc định weights_0_elo.onnx; đổi bằng --weights hoặc setoption)
custom_engine.exe --uci-nn --weights models/model_genN.onnx

# Phiên tay tối thiểu:
uci
setoption name WeightsFile value models/model_gen5.onnx
setoption name Visits value 800
isready
ucinewgame
position startpos moves b3b4 c9a7
go nodes 800
# -> bestmove <nước tọa độ thật>
stop            # nếu dùng go infinite
quit

# Chạy bộ conformance:
custom_engine.exe --test-uci
```

---

## 10. Trạng thái & bước kế tiếp

**T8.1 HOÀN TẤT** — engine UCI MCTS+NN chạy ổn terminal, tuân thủ giao thức (gồm `go infinite`/`stop` bất đồng bộ, rebuild backend động, robust), I/O nước 2 chiều đã khóa bằng `--test-uci`. Sẵn sàng cho **GUI tự viết** cắm vào.

Chưa làm (theo plan, để các phase sau):
- **T8.2:** `info score cp/wdl + pv + multipv`, time-control `wtime/btime`, `searchmoves`, ponder thật.
- **T8.3:** mở khóa toàn bộ siêu tham số kiểu lc0 (passthrough `setoption` cho 75 search-param).
- **T8.4:** đóng gói bản portable Windows + `play.bat` (bước kế tiếp đề xuất).
- **T8.6:** `HUONG_DAN.md`.

Theo thứ tự khuyến nghị: **T8.1 ✓ → T8.4 → T8.6 → T8.2 → T8.3 → T8.5 → T8.x**.
