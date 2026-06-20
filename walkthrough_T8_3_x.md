# Walkthrough T8.3 + T8.x — Siêu tham số đầy đủ + Temperature + Tái dùng cây + `--play` ASCII

> Phạm vi: **T8.3** (mở khóa siêu tham số kiểu lc0: passthrough search-param + nối `Temperature` vào
> chọn nước + thêm cờ huấn luyện) và **T8.x** (giới hạn ở: **tái dùng cây giữa các nước** + chế độ
> **`--play` ASCII** trong terminal).
> Ngày: 2026-06-20. Thay đổi: `src/main.cc`, `python/train.py`, `python/loop.py`, `HUONG_DAN.md`.

---

## PHẦN A — T8.3

### A.1. Passthrough tham số tìm kiếm lc0 (`setoption name <tên-lc0>`)
**Vấn đề:** `OptionsParser` của ta là bản port rút gọn — set theo `OptionId`, **không có registry**
tra cứu theo tên UCI. Nên không thể "tự động" forward 75 tên.

**Giải pháp:** bảng dispatch tay `ApplySearchOpt(dict, name, value)` ánh xạ tên-lc0 → `OptionId` + kiểu:
```cpp
if (name=="cpuct")        d->Set<float>(BP::kCpuctId, F(...));
else if (name=="cpuct-base")   d->Set<float>(BP::kCpuctBaseId, ...);
else if (name=="fpu-value")    d->Set<float>(BP::kFpuValueId, ...);
else if (name=="fpu-strategy") d->Set<string>(BP::kFpuStrategyId, value);
else if (name=="draw-score")   d->Set<float>(BP::kDrawScoreId, ...);
else if (name=="two-fold-draws") d->Set<bool>(BP::kTwoFoldDrawsId, B());
... (curated set; mở rộng bằng cách thêm case)
```
- Engine lưu các option lạ vào `search_opts_` (map) khi `setoption`; **áp vào dict mỗi `go`** (không
  dựng lại backend). Tên không khớp → bỏ qua (robustness).
- Dùng được ngay: `setoption name cpuct value 2.5`, `setoption name draw-score value -0.2`. (Đã test:
  `cpuct` không crash, search bình thường.)

### A.2. ⭐ Nối `Temperature` vào CHỌN NƯỚC (điều chỉnh độ khó)
Trước đây `EmitBestMove` luôn chọn **greedy** (nước nhiều visit nhất) nên `Temperature` vô tác dụng.
Nay:
```cpp
chosen = edges[0];                                   // mặc định: hết sức
if (temperature_ > 0 && (cutoff==0 || ply < cutoff))
    chosen = SampleByTemperature(edges, temperature_);
```
`SampleByTemperature`: trọng số `w_i = N_i^(1/T)`, `T = temp_permille/1000` (kẹp [0.01,10]); lấy mẫu
theo `w`. `T→0` = greedy; `T=1` (Temperature 1000) = tỉ lệ thuận số visit; `T` lớn = phẳng/ngẫu nhiên.
**Kiểm chứng:** `Temperature 0` → luôn `d3d5`; `Temperature 800` → đa dạng (`j3j5`/`i3i5`/`g3g4`).
Thêm option `TempCutoffPly` (chỉ áp temperature N nước đầu). → Người dùng tự chỉnh độ khó (theo quyết
định: **không làm combo Skill**).

### A.3. Cờ huấn luyện thêm (lczero-training parity) — `train.py`
| Cờ | Ý nghĩa |
|----|---------|
| `--optimizer {adamw,sgd,nadam}` | chọn bộ tối ưu (sgd+nesterov-momentum = lc0 chuẩn) |
| `--momentum M` | momentum cho sgd |
| `--policy-weight W` | trọng số loss policy (đối xứng `--value-weight`) |
| `--grad-clip G` | clip grad-norm (`scaler.unscale_` rồi `clip_grad_norm_`) |
| `--seed S` | hạt giống tái lập |
| `--warmup-steps N` + `--lr-values a,b` + `--lr-boundaries i` | **lịch LR theo bước**: warmup tuyến tính → bậc thang; áp mỗi bước TRƯỚC pha SWA (SWA dùng SWALR như cũ) |

`loop.py` truyền thẳng tất cả. **Kiểm chứng:** train với `--optimizer sgd --grad-clip 1.0 --warmup-steps 3
--lr-values 0.02,0.002 --lr-boundaries 6 --seed 7` → `optimizer=sgd grad_clip=1.0 lr_sched=on`, loss giảm,
export+verify PASS.

---

## PHẦN B — T8.x

### B.1. ⭐ Tái dùng cây giữa các nước (`ReuseTree`, mặc định bật)
**Trước:** mỗi lệnh `position` dựng cây MỚI → vứt bỏ thống kê search của nước trước (lạnh).
**Nay** (`HandlePosition`): nếu `ReuseTree` && cùng `startfen` && danh sách nước mới là **mở rộng tiền
tố** của danh sách đang giữ → **advance cây hiện có** bằng `MakeMove` cho các nước mới (giữ lại cây con
+ visit), rồi `TrimTreeAtHead` (giải phóng nhánh thừa). Ngược lại → dựng lại.
```cpp
if (reuse_tree_ && fen==current_startfen_ && moves prefix-extends current_moves_) {
    for k in [current.size .. moves.size): tree_->MakeMove(parse(moves[k]));   // giữ subtree
    tree_->TrimTreeAtHead(); reused = true;
}
if (!reused) { rebuild fresh; }
current_startfen_ = fen; current_moves_ = moves;   // theo dõi để khớp tiền tố lần sau
```
- Lần `go` kế tiếp dùng `tree_->GetCurrentHead()` đã "ấm" (initial_visits = visit tái dùng); stopper dùng
  `nodes_since_movestart` nên vẫn chạy thêm N playout mới → khởi đầu nóng, nhanh/mạnh hơn.
- **An toàn:** advance bằng `MakeMove` cho ra **đúng thế cờ** như rebuild (chỉ khác là giữ subtree); chỉ
  tái dùng khi khớp tiền tố. `ucinewgame` xóa `current_*`.
- **Kiểm chứng:** luồng `moves b3b4` → `moves b3b4 c9a7` (đường reuse) → `ReuseTree false` +
  `moves b3b4 c9a7 d3d4` (đường rebuild) → **đều ra nước hợp lệ, không crash**.

> Lý do giờ mới làm (nhắc lại): cơ chế `NodeTree.MakeMove` *có sẵn* (giữ subtree), nhưng vòng lặp UCI
> trước đó *chủ động dựng lại*. Bật tái dùng là quyết định tầng-engine; ta hoãn tới T8.x vì "đúng-trước"
> (rebuild luôn đúng) và vì cache eval (MemCache) đã gánh một phần lợi ích.

### B.2. `--play` / `--play-black` — bàn cờ ASCII trong terminal
Tiện ích thử nhanh không cần GUI: `run_play` + `PrintAsciiBoard`.
- In bàn 10×10 (chữ HOA = Trắng dưới, thường = Đen trên; ký tự: `p n b r q k a e h m v y s`).
- Đọc nước người (tọa độ thật, vd `b3b4`, phong cấp `a9a10v`), validate qua `UciToCanonicalMove`; nước
  sai → báo và hỏi lại. AI chạy MCTS (`PlayoutCountStopper(visits)`, `RunBlocking(1)` đồng bộ) rồi đáp.
- Kết thúc ván qua `ComputeGameResult` (chiếu hết/hòa/7-check/rule50/lặp). `--play-black` để cầm Đen.
- **Kiểm chứng:**
```
=== FairyZero --play (visits=...) ===
You are WHITE (uppercase, bottom). ...
      a  b  c  d  e  f  g  h  i  j
  10  v  r  h  a  b  k  b  e  r  v
   9  m  s  y  s  n  n  s  y  s  m
   8  y  p  p  p  p  p  p  p  p  y
Your move:  b3b4
AI plays: a10b7  (121 nodes)
```

---

## C. Tổng hợp file đã đổi

| File | Thay đổi |
|------|----------|
| `src/main.cc` | `ApplySearchOpt` (passthrough), `SampleByTemperature`; UciNnEngine: options Temperature/TempCutoffPly/ReuseTree + lưu `search_opts_`, HandleGo áp passthrough, EmitBestMove chọn nước theo temperature, HandlePosition tái dùng cây + `current_startfen_/current_moves_`; `run_play`/`PrintAsciiBoard`; CLI `--play`/`--play-black` |
| `python/train.py` | `--optimizer/--momentum/--policy-weight/--grad-clip/--seed/--warmup-steps/--lr-values/--lr-boundaries`; chọn optimizer; lịch LR theo bước; clip-grad |
| `python/loop.py` | truyền thẳng các cờ training mới |
| `HUONG_DAN.md` | A.2b (`--play`); A.4 (Temperature/TempCutoffPly/MultiPV/ReuseTree + passthrough lc0) |

---

## D. Kết quả test (đã chạy)
- `--test-uci` + `--test-encoder`: **PASS** (không phá gì).
- Temperature: 0 → greedy tất định; 800 → đa dạng. `cpuct` passthrough: OK.
- Tái dùng cây (reuse + rebuild) + `--play`: nước hợp lệ, render đúng, không crash.
- `train.py` với optimizer/lr-schedule/grad-clip/seed: chạy, loss giảm, verify PASS.

> Nhắc lại khi tự test engine UCI: **giữ stdin mở (sleep) tới khi nhận `bestmove`** — pipe `go\nquit`
> sẽ Abort search (trông như "1 node").

---

## E. Kết luận & còn lại

**T8.3 hoàn tất**: chỉnh sâu kiểu lc0 (passthrough `setoption name <tên-lc0>`), **Temperature thực sự hạ
độ khó**, và bộ cờ huấn luyện đầy đủ hơn (optimizer/lr-schedule/grad-clip/seed). **T8.x (phần được giao)
hoàn tất**: **tái dùng cây** giữa các nước + **`--play` ASCII**.

Còn lại (tùy chọn, không chặn): ponder cấp ngân sách sau `ponderhit`, thêm search-param vào bảng
`ApplySearchOpt`, thêm cờ training hiếm dùng (renorm/ema/dropout). Bản portable nay đủ để chơi (UCI hoặc
ASCII), tự chỉnh độ khó/siêu tham số, sinh dữ liệu và huấn luyện trên Windows + Colab.

Thứ tự đã đi: **T8.1 ✓ → T8.4 ✓ → T8.6 ✓ → encoder-test ✓ → T8.2 ✓ → T8.5 ✓ → T8.3 ✓ → T8.x ✓**.
