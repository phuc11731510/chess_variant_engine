# Walkthrough — Phase T2: Trích xuất π / policy_kld / z từ kết quả search

> Ngày: 2026-06-19 · Dự án: FairyZero (`custom_engine`) — biến thể cờ 10×10.
> Phạm vi đợt này: hiện thực hóa **milestone T2** trong `implementation_plan phase training_1.md` (mục A3–A5).
> DoD: chạy 1 ván ngắn, kiểm: **Σπ = 1.0**, **policy_kld > 0 hợp lệ** (dùng prior NN gốc chưa nhiễu), **z đảo dấu đúng theo parity lượt đi**.
> Kết quả: ✅ Hoàn thành và đã verify bằng test thực tế (PASS, PS-EXIT 0). Tiếp nối T1 ở `walkthrough_3.md`.

---

## 0. T2 là gì & vì sao quan trọng

T1 đã có "vỏ" (struct record + writer). T2 là phần "ruột giá trị huấn luyện" — biến **kết quả của một lượt MCTS search** thành các trường mục tiêu trong record:

- **π (policy target)** = phân bố visit của MCTS trên các nước hợp lệ (đây là cái policy head sẽ học, KHÔNG phải policy thô của NN).
- **value targets** (`root_q/d`, `best_q/d`, `played_q/d`) = ước lượng giá trị từ search.
- **orig_q/d + policy_kld** = phục vụ bộ lọc `diff_focus` (đo "độ bất ngờ" của thế cờ so với gợi ý thô của mạng).
- **z (`result_q/d`)** = kết quả ván thật, gán ở cuối ván, đảo dấu theo lượt đi.

Đây là chỗ **dễ sai dấu (sign convention)** nhất trong toàn pipeline. Nếu lệch dấu value/z, mạng sẽ học ngược (tối thiểu hóa thay vì tối đa hóa) mà không báo lỗi. Nên đợt này tập trung làm đúng dấu + test parity.

T2 KHÔNG đụng tới việc encode bàn cờ thành planes (đó là T3) — chỉ làm π/value/kld/z.

---

## 1. Khảo sát API trước khi code

Để trích xuất, cần đọc đúng API của cây MCTS và xác định **hệ quy chiếu của từng giá trị**.

### 1.1. `Node` (search/classic/node.h)
- `Node::GetN()` → tổng visit của node.
- `Node::GetWL()` → giá trị Win-Loss **từ góc nhìn bên-tới-lượt TẠI node đó** (`wl_`).
- `Node::GetD()` → xác suất hòa (bất biến theo góc nhìn).
- `Node::Edges()` → iterator các cạnh (mỗi cạnh là 1 nước hợp lệ).

### 1.2. `EdgeAndNode`
- `GetN()` → visit của node con.
- `GetWL(default)` → `node_con->GetWL()` nếu con đã thăm, ngược lại `default`.
  → **Đây là góc nhìn của CON (đối thủ của root).** Muốn về góc nhìn root phải **phủ định**.
- `GetD(default)`, `GetP()` (prior), `GetMove(flip)`.

### 1.3. `NodeTree`
- `GetCurrentHead()` → `Node*` root của lượt search hiện tại.
- `GetPositionHistory()` → `const PositionHistory&`, với `Last()` = thế cờ root.
- `MakeMove(move)` → đẩy nước đi, tự gọi `TrimHistory(100)`.
- `IsBlackToMove()`, `ResetToPosition(fen, moves)`.

### 1.4. Backend cache
- `Backend::GetCachedEvaluation(EvalPosition{history, legal_moves})` → `std::optional<EvalResult>`.
- `EvalResult` chứa `q` (= win−loss, **góc nhìn side-to-move** vì board canonical), `d` (draw), và `p` (policy NN **thô đã softmax trên nước hợp lệ, CHƯA nhiễu Dirichlet**), index theo thứ tự `GenerateLegalMoves()`.

**Chốt hệ quy chiếu (mọi value target ở góc nhìn side-to-move-at-root):**
| Giá trị | Công thức | Lý do |
|---------|-----------|-------|
| `root_q/d` | `root->GetWL()/GetD()` | wl_ của root đã là góc side-to-move |
| `best_q` | `−best.GetWL(0)` | con là góc đối thủ → phủ định |
| `best_d` | `best.GetD(0)` | draw bất biến góc nhìn |
| `orig_q/d` | `raw->q / raw->d` | NN q đã là góc side-to-move (board canonical) |

---

## 2. Các file đã tạo / sửa

### 2.1. `[NEW] src/lczero_chess/selfplay/training_extract.h`
Khai báo 2 hàm:
- `Move FillSearchTargets(const classic::Node* root, const PositionHistory& history, Backend* backend, TrainingDataV1& rec)` — điền π/value/orig/kld; trả về best move (max-visit) cho caller dùng để chọn nước.
- `void AssignResult(TrainingDataV1& rec, GameResult abs_result, bool black_to_move)` — gán z cuối ván.
- Comment ghi rõ: hàm KHÔNG đụng `piece_planes`/scalar-aux/`result_q-d` (để cho plane-encoder và AssignResult).

### 2.2. `[NEW] src/lczero_chess/selfplay/training_extract.cc`
Logic 3 bước trong `FillSearchTargets`:

**Bước 1 — π từ visits:**
```cpp
uint32_t total = 0;
for (e : root->Edges()) total += e.GetN();
for (e : root->Edges()) {
  idx = MoveToNNIndex(e.GetMove(), 0);
  rec.probabilities[idx] = total>0 ? float(e.GetN())/total : 0;
  if (e.GetN() >= best_n) { best_n = e.GetN(); best = e; }   // chọn best (>= để luôn có best dù N==0)
}
rec.visits = root->GetN();
rec.best_idx = rec.played_idx = MoveToNNIndex(best.GetMove(), 0);
```

**Bước 2 — value targets** (đúng dấu như bảng mục 1.4):
```cpp
rec.root_q = root->GetWL();  rec.root_d = root->GetD();
rec.best_q = -best.GetWL(0); rec.best_d = best.GetD(0);   // con đối thủ -> phủ định
rec.played_q = rec.best_q;   rec.played_d = rec.best_d;   // caller override nếu chơi nước khác best
```

**Bước 3 — orig_q + policy_kld qua cache (KHÔNG đụng Search):**
```cpp
MoveList legal = history.Last().GetBoard().GenerateLegalMoves();   // deterministic -> cùng thứ tự lúc cache
EvalPosition ep{&history, span(legal.data(), legal.size())};
optional<EvalResult> raw = backend->GetCachedEvaluation(ep);
if (raw && !raw->p.empty()) {
  rec.orig_q = raw->q; rec.orig_d = raw->d;
  // KLD(pi || p_nn) = sum pi_i log(pi_i / p_nn_i), GHÉP QUA MoveToNNIndex:
  for (i in legal) {
    idx = MoveToNNIndex(legal[i], 0);
    pi  = rec.probabilities[idx];      // pi dense đã điền ở bước 1
    if (pi>0) kld += pi * log(pi / max(raw->p[i], 1e-12));
  }
  rec.policy_kld = max(0, kld);        // KLD>=0 lý thuyết, clamp sai số fp
} else {
  rec.orig_q = rec.best_q; rec.orig_d = rec.best_d; rec.policy_kld = 0;  // fallback cache-miss
}
```

**3 quyết định kỹ thuật mấu chốt ở bước 3:**
1. **Lấy prior thô qua `GetCachedEvaluation` thay vì hook vào Search** — vì nhiễu Dirichlet được áp BÊN TRONG `Search::FetchSingleNodeResult`, không lộ ra ngoài. Cache lưu policy NN thô (chưa nhiễu) nên query lại là sạch nhất, không phải sửa Search.
2. **Ghép π↔p_NN qua `MoveToNNIndex`, KHÔNG theo vị trí mảng** — vì sau search `root->Edges()` đã bị `SortEdges` sắp lại theo prior, còn `raw->p` theo thứ tự `GenerateLegalMoves` gốc. Mẹo: dùng chính mảng dense `rec.probabilities[idx]` (đã điền π ở bước 1) làm "bảng tra π theo index", rồi với mỗi `legal[i]` tra `π = probabilities[MoveToNNIndex(legal[i])]` và `p_nn = raw->p[i]` → khớp theo NƯỚC ĐI. Không cần dựng map hay mảng dense phụ.
3. **Fallback cache-miss** (`raw` rỗng do va chạm hash ~1% hoặc backend không cache): `orig_q=best_q`, `policy_kld=0`. Vô hại vì 2 trường này chỉ phục vụ `diff_focus` (nâng cao); π và z luôn đúng.

`AssignResult` — gán z theo parity:
```cpp
if (abs == DRAW) { result_q=0; result_d=1; return; }
white_won  = (abs == WHITE_WON);
stm_white  = !black_to_move;
stm_won    = (white_won == stm_white);
result_q   = stm_won ? +1 : -1;  result_d = 0;
```

### 2.3. `[MODIFY] meson.build`
Thêm `'src/lczero_chess/selfplay/training_extract.cc'` vào `trainingdata_sources`.

### 2.4. `[MODIFY] src/main.cc`
- Thêm include `"selfplay/training_extract.h"` + `<cmath>`.
- Thêm `class SilentUciResponder` (override rỗng OutputBestMove/OutputThinkingInfo) để search không spam log.
- Thêm `run_extract_tests(weights_path)`:
  - Nạp variant qua chuỗi ini inline (giống `run_mcts_tests`, có castling + promotionRegion `*8 *9 *10` theo luật mới).
  - Dựng `OnnxBackend` → bọc `CreateMemCache` (để có cache); fallback `MockBackend` (không cache) nếu nạp weights lỗi.
  - **Chơi ván ngắn 6 nước, mỗi nước:** tạo `Search` (visits=64, 2 threads, noise ε=0.25), `RunBlocking` → `FillSearchTargets` → kiểm `Σπ≈1` và `policy_kld` hữu hạn/≥0 → in giá trị → `MakeMove(best)` → kiểm `ComputeGameResult`.
  - **Test z parity:** dùng kết quả ván thật nếu game kết thúc, ngược lại **inject WHITE_WON** để vẫn kiểm được logic parity; rồi `AssignResult` và verify từng record (white-to-move → +1, black-to-move → −1 khi WHITE_WON).
- Thêm cờ CLI `--test-extract` (biến `test_extract_mode`) + nhánh dispatch `run_extract_tests(weights_file)`.

---

## 3. Build & chạy test

### 3.1. Build
```
meson compile -C build
```
→ Biên dịch `training_extract.cc` + `main.cc`, **link `custom_engine.exe` thành công** (chỉ warning deprecated có sẵn).

> **Lưu ý về cảnh báo clangd:** trong lúc tạo file, language server (clangd) báo hàng loạt lỗi giả như `unknown type 'uintptr_t'`, `raw->p is not a pointer`, `Invalid operands Edge_Iterator`... Đây là **cascade do clangd không được cấu hình đúng flag `<cstdint>`** (cùng lỗi này xuất hiện cả ở `main.cc` vốn build tốt). **GCC build mới là nguồn chân lý** — và nó pass. (`raw->p` trên `std::optional` là hợp lệ chuẩn; range-for trên `Node::Edges()` giống hệt `search.cc`.)

### 3.2. Chạy (qua PowerShell — môi trường có DLL trên PATH)
```
> .\build\custom_engine.exe --test-extract
[T2] OnnxBackend + MemCache loaded.
  move 0 (white): sum(pi)=1 visits=84 root_q=0.000486 best_q=0.00409 orig_q=0.01023 kld=0.914
  move 1 (black): sum(pi)=1 visits=84 root_q=-0.00316 best_q=0.00341 orig_q=0.01023 kld=0.482
  move 2 (white): sum(pi)=1 visits=80 root_q=-0.00307 best_q=0.00730 orig_q=0.01022 kld=0.561
  move 3 (black): sum(pi)=1 visits=99 root_q=-0.00320 best_q=-4.9e-07 orig_q=0.01023 kld=0.465
  move 4 (white): sum(pi)=1 visits=95 root_q=-0.00097 best_q=0.00729 orig_q=0.01022 kld=0.510
  move 5 (black): sum(pi)=1 visits=91 root_q=-0.00056 best_q=0.00171 orig_q=0.01022 kld=0.682
[PASS] sum(pi)==1.0 and policy_kld valid for all 6 positions.
  policy_kld > 0 observed (search diverged from raw NN prior). OK.
  Assigning z with result=3 (injected for parity test)
[PASS] z parity correct for all positions.
ALL T2 (EXTRACT) TESTS PASSED!
PS-EXIT: 0
```
> (Nhắc lại từ T1: ĐỪNG chạy qua Git Bash thiếu MSYS2 ucrt64 trên PATH → sẽ ra exit 127 giả tạo do thiếu DLL.)

---

## 4. Phân tích kết quả (vì sao các con số hợp lý)

- **`sum(pi)=1`** ở mọi vị trí → chuẩn hóa visit đúng, ghép `MoveToNNIndex` không làm rơi nước nào.
- **`orig_q ≈ 0.0102` ổn định** ở mọi nước → đường `GetCachedEvaluation(root)` lấy đúng **eval NN thô** của mạng `weights_0_elo` (mạng "0 elo" ngẫu nhiên → giá trị gần 0). Chứng tỏ **cache hit** hoạt động (không rơi vào fallback).
- **`root_q` / `best_q` gần 0** → mạng ngẫu nhiên đánh giá thế cờ gần cân bằng. (`best_q` hơi dương hơn `root_q` — hợp lý vì best là nước tốt nhất, còn root là trung bình mọi nước.)
- **`policy_kld` 0.46–0.91 (>0, hữu hạn)** → sau 64–99 visits + nhiễu, phân bố visit π lệch khỏi prior gần-đều của mạng → KLD dương. Đúng kỳ vọng (chính là tín hiệu `diff_focus` sẽ dùng).
- **`visits` 80–99** (dù `NodeLimitStopper`=64) → MCTS gom batch + out-of-order nên `total_nodes` vượt mốc một chút trước khi dừng. Bình thường.
- **z parity**: với WHITE_WON inject, mọi record lượt-trắng nhận +1, lượt-đen nhận −1. Khớp `AssignResult`.

---

## 5. Đối chiếu DoD của T2

| Tiêu chí (plan) | Trạng thái |
|-----------------|-----------|
| Tổng π = 1.0 | ✅ (6/6 vị trí) |
| policy_kld > 0 hợp lệ, dùng prior NN gốc **không nhiễu** | ✅ (orig_q từ cache = NN thô; kld 0.46–0.91 hữu hạn, >0) |
| z đảo dấu chính xác theo lượt đi | ✅ (parity test pass) |
| Không vỡ build | ✅ |

---

## 6. Bảng quyết định kỹ thuật & lý do

| Quyết định | Lý do |
|-----------|-------|
| `best_q = −child->GetWL()` (phủ định) | Node con ở góc nhìn đối thủ; phủ định để về góc side-to-move của root |
| `root_q = root->GetWL()` (không phủ định) | wl_ của root vốn đã ở góc side-to-move |
| Lấy prior thô qua `GetCachedEvaluation` | Nhiễu Dirichlet nằm trong Search, không lộ ra; cache giữ prior chưa nhiễu → khỏi sửa Search |
| Ghép π↔p_NN qua `MoveToNNIndex` | Edges đã SortEdges (lệch thứ tự với cache `p[]`); ghép theo nước đi tránh lệch index âm thầm |
| Dùng `rec.probabilities[idx]` làm bảng tra π | Khỏi dựng map/mảng dense phụ; π và p_nn khớp theo cùng MoveToNNIndex |
| Fallback cache-miss (orig_q=best_q, kld=0) | Va chạm hash ~1%; 2 trường này chỉ cho diff_focus nâng cao, vô hại |
| Test inject WHITE_WON khi game chưa kết thúc | 6 nước từ startpos thường chưa có kết quả; vẫn kiểm được logic parity của AssignResult |
| SilentUciResponder | Search bắt buộc có responder; làm rỗng để test không spam log |

---

## 7. Việc còn lại / chuẩn bị cho T3

- **CHƯA commit** (T1 bạn đã tự commit). File T2 mới/đổi: `selfplay/training_extract.{h,cc}`, `meson.build`, `main.cc`.
- **T3 (kế tiếp)** — ghép T1 + T2 thành **vòng self-play hoàn chỉnh 1 ván**:
  1. Encode planes: rút 216 `InputPlane.mask` (128-bit) từ `EncodePositionForNN` → ghi vào `piece_planes[216][2]`; điền scalar (rule50, checks, side, ep_mask) và **castling theo FILE-INDEX** (0-9 / 0xFF).
  2. Mỗi nước: `FillSearchTargets` (đã có) + encode planes + đẩy record vào `training_array`; chọn nước (temperature đầu ván / greedy sau).
  3. Cuối ván: `AssignResult` cho mọi record theo `ComputeGameResult` + side-to-move; ghi ra `.gz` qua `TrainingDataWriter` (T1).
  4. Heap-alloc `Search`/`NodeTree` (chống tràn stack 512).
- Khi đó `--selfplay` (đang là placeholder) sẽ được nối vào vòng này.

---

## 8. Cách chạy lại test (ghi nhớ)
```powershell
cd D:\chess_variant\custom_engine
meson compile -C build
.\build\custom_engine.exe --test-extract     # T2
.\build\custom_engine.exe --test-trainingdata # T1
```
> Dùng PowerShell (có MSYS2 ucrt64 trên PATH), KHÔNG dùng Git Bash thiếu PATH.
