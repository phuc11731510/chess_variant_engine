# FairyZero — Sách hướng dẫn sử dụng

FairyZero là một engine cờ AlphaZero cho **biến thể cờ 10×10** của bạn: nó tự học bằng cách
tự chơi (self-play) → huấn luyện mạng nơ-ron → mạnh dần qua từng đời. Bản portable này cho
phép bạn **chơi với AI**, **tự sinh dữ liệu huấn luyện**, và **huấn luyện** — trên **Windows
(CPU)** lẫn **Google Colab (GPU)**.

> Bạn **không cần biết lập trình** để dùng. Cứ làm theo từng bước, copy-paste lệnh.

---

## 0. Trong bản portable có gì?

```
FairyZero/
├─ custom_engine.exe         ← engine (chơi + sinh dữ liệu) cho Windows
├─ onnxruntime.dll, *.dll    ← thư viện đi kèm (đừng xóa)
├─ play.bat                  ← bấm đúp để chơi nhanh
├─ models/seed.onnx          ← mạng khởi đầu (đời 0) để chơi/huấn luyện
├─ python/                   ← bộ huấn luyện (train.py, loop.py, archive.py, …)
│   └─ requirements.txt
├─ engine_src/               ← mã nguồn engine (để build bản GPU trên Colab)
├─ scripts/colab_setup.sh    ← script dựng engine trên Colab
├─ VERSION.txt
└─ HUONG_DAN.md              ← tệp này
```

**3 việc bạn làm được:** (A) Chơi với AI · (B) Sinh dữ liệu tự chơi · (C) Huấn luyện đời mạnh hơn.

---

## A. CHƠI VỚI AI

### A.1. Cách nhanh nhất (Windows)
Mở thư mục `FairyZero`, **bấm đúp `play.bat`** (hoặc mở PowerShell tại đó và gõ `.\play.bat`).
Engine khởi động ở chế độ **UCI** và chờ lệnh. Gõ thử:
```
uci
isready
position startpos
go nodes 800
```
Engine trả về dòng `bestmove <nước đi>` — đó là nước AI chọn. Để AI đi mạnh hơn, tăng `go nodes`
(vd `go nodes 5000`); chậm hơn nhưng giỏi hơn. Gõ `quit` để thoát.

### A.2. Quy ước nước đi (QUAN TRỌNG cho GUI bạn tự viết)
- Ô cờ: **cột `a`–`j`** (10 cột) + **hàng `1`–`10`** (10 hàng). **Hàng 10 có HAI chữ số.**
- Nước đi = ô xuất phát + ô đích, vd `e2e4`, `a1a10`, `j9j10`.
- Phong cấp: thêm ký tự quân ở cuối, vd `a9a10v` (phong thành quân `v`).
- Trắng ở phía dưới (hàng 1,2,3…), Đen ở trên (hàng 8,9,10).

GUI của bạn chỉ cần **gửi/nhận đúng các chuỗi này** qua UCI là điều khiển được engine. Engine
tự xử lý việc lật bàn cho quân Đen — bạn luôn nói chuyện bằng tọa độ thật.

### A.2b. Chơi ngay trong terminal không cần GUI (`--play`)
Muốn thử nhanh, chạy bàn cờ ASCII trong terminal:
```
custom_engine.exe --play --weights models\seed.onnx --visits 800   (bạn cầm Trắng)
custom_engine.exe --play-black --weights models\seed.onnx           (bạn cầm Đen)
```
Engine in bàn cờ (chữ HOA = Trắng, thường = Đen), hỏi `Your move:`, bạn gõ nước (vd `b3b4`), AI đáp.
Gõ `quit` để thoát. Đây là tiện ích thử nhanh; đường chính để cắm GUI vẫn là `--uci-nn`.

### A.3. Một ván qua lệnh UCI (mẫu)
```
uci
isready
ucinewgame
position startpos
go nodes 1500           → engine: bestmove b3b4   (bạn cho AI cầm Trắng)
position startpos moves b3b4 <nước-của-bạn>
go nodes 1500           → engine: bestmove ...
... lặp lại ...
quit
```
Mỗi lượt: bạn cập nhật `position startpos moves <toàn bộ nước đã đi>` rồi `go` để AI nghĩ nước tiếp.

### A.4. Tinh chỉnh khi chơi (lệnh `setoption`)
Gõ trước khi `go`. Cú pháp: `setoption name <Tên> value <Giá trị>`.

| Tên | Mặc định | Ý nghĩa |
|-----|----------|---------|
| `WeightsFile` | seed.onnx | Đổi đời mạng (mạnh/yếu): `setoption name WeightsFile value models\model_gen5.onnx` |
| `Visits` | 800 | Số nước "nghĩ" mỗi lượt khi `go` không ghi `nodes` (mạnh hơn = chậm hơn) |
| `Threads` | 1 | Số luồng tìm kiếm (máy nhiều nhân → nhanh hơn) |
| `Provider` | cpu | `cpu` hoặc `cuda` (GPU — chỉ với bản build GPU) |
| `FixedBatch` | 16 | Cỡ batch GPU (khi `cuda`) |
| `BackendThreads` | 1 | Số luồng tính toán mạng (CPU) |
| `PolicySoftmaxTemp` | 1.0 | Làm "mềm" gợi ý nước đi của mạng |
| `MoveOverheadMs` | 30 | Trừ hao thời gian (khi dùng `go movetime`) |
| `Temperature` | 0 | **Hạ độ khó:** >0 (đơn vị ‰) → AI thỉnh thoảng đi nước hạng 2/3 (đa dạng, yếu đi). 0 = hết sức |
| `TempCutoffPly` | 0 | Chỉ áp Temperature trong N nước đầu (0 = luôn áp) |
| `MultiPV` | 1 | Số biến chính (PV) báo cáo trong `info` |
| `ReuseTree` | true | Giữ cây MCTS giữa các nước (nhanh hơn) |

Điều khiển thời gian: `go nodes N` · `go movetime 3000` (3 giây) · `go wtime W btime B` (cờ có đồng hồ) ·
`go infinite` rồi `stop`. Engine phát `info ... score cp ... wdl ... pv ...` để GUI hiển thị đánh giá/biến chính.

> **Độ khó gợi ý:** Dễ = `Visits 80` + `Temperature 500` · Vừa = `go nodes 400` · Khó = `go nodes 5000` + `Temperature 0`.

**Chỉnh sâu kiểu lc0 (tùy chọn):** đặt thẳng tham số tìm kiếm của lc0 bằng tên gốc, vd:
`setoption name cpuct value 2.5` · `setoption name draw-score value -0.2` · `setoption name fpu-value value 0.4`.

### A.5. Cắm vào GUI tự viết
GUI chỉ cần chạy tiến trình: `custom_engine.exe --uci-nn --weights models\seed.onnx` rồi nói
UCI qua stdin/stdout (uci → uciok; isready → readyok; position …; go …; nhận bestmove). Engine
tuân thủ giao thức UCI chuẩn, nên mọi GUI nói đúng UCI đều dùng được.

---

## B. SINH DỮ LIỆU TỰ CHƠI

Engine tự đánh với chính nó hàng trăm/ngàn ván và ghi lại để huấn luyện. **Phần này do engine
C++ làm (nhanh), không phải Python.**

### B.1. Trên Windows (CPU)
Mở PowerShell tại thư mục `FairyZero`:
```
.\custom_engine.exe --selfplay --games 200 --visits 200 --parallel 6 `
    --weights models\seed.onnx --out data\gen0
```
- `--games` số ván · `--visits` độ sâu mỗi nước · `--parallel` số ván chạy song song
  (đặt ≈ số nhân CPU) · `--out` thư mục lưu (mỗi ván 1 tệp `.gz`).
- Đời đầu nên để `--visits 200` cho nhanh; đời sau tăng `400`/`800`.

### B.2. Tự xin thua sớm (resign) — tăng tốc
Mặc định TẮT. Bật để bỏ qua các ván đã thua rõ (nhanh hơn), vẫn giữ ~10% ván đánh tới cùng:
```
... --resign-threshold -0.90 --resign-consecutive 3 --no-resign-frac 0.10
```

### B.3. Đóng gói dữ liệu để tải lên Google Drive
Hàng ngàn tệp `.gz` nhỏ tải lên Drive rất chậm. Gom thành **1 tệp**:
```
python python\archive.py pack data\gen0 --out data\gen0.zip
```
Tải `gen0.zip` lên Drive. Khi huấn luyện, có thể đọc thẳng tệp `.zip` (không cần giải nén).

---

## C. HUẤN LUYỆN ĐỜI MẠNH HƠN

### C.0. Cài thư viện Python (làm 1 lần)
```
pip install -r python\requirements.txt
```

### C.1. Huấn luyện một đời (`train.py`)
```
python python\train.py --data data\gen0 --epochs 10 --batch 256 `
    --init-from models\seed.pt --out models\model_gen1.onnx
```
- `--data` có thể là thư mục, nhiều thư mục (ngăn bằng dấu phẩy), hoặc tệp `.zip`.
- `--init-from <.pt>` = học tiếp từ đời trước (warm-start). Bỏ đi nếu train từ đầu.
- Kết quả: `model_gen1.onnx` (cho engine chơi) **và** `model_gen1.pt` (để train đời sau).

> **`.onnx` vs `.pt`:** `.onnx` = mạng engine C++ chạy (chơi). `.pt` = bản lưu để huấn luyện
> tiếp. Mỗi lần train sinh ra cả hai.

### C.2. Vòng lặp tự động nhiều đời (`loop.py`)
Tự làm: sinh dữ liệu → huấn luyện → đấu thử → lặp.
```
# Windows (CPU, để thử nhanh):
python python\loop.py --engine custom_engine.exe --gens 3 `
    --games-per-gen 40 --visits 64 --window-gens 3 --epochs 8 `
    --provider cpu --parallel 6 --eval-games 10
```

### C.3. Trên Google Colab (GPU — KHUYẾN NGHỊ để huấn luyện thật)
Windows của bạn không có GPU nên huấn luyện chậm. Colab có GPU miễn phí. Các bước:
1. Tải cả thư mục `FairyZero` lên Google Drive (hoặc đẩy mã nguồn lên GitHub rồi `git clone`).
2. Mở một Colab notebook mới, chọn **Runtime → Change runtime type → GPU**.
3. **Chép sang ổ local của Colab rồi build** (build trên Google Drive RẤT chậm và hay lỗi do FUSE):
   ```
   !cp -r /content/drive/MyDrive/FairyZero /content/FairyZero
   !bash /content/FairyZero/scripts/colab_setup.sh
   ```
   Script tự dò vị trí mã nguồn (chạy được cả khi bạn `cd` vào trong), tải onnxruntime GPU, build,
   chạy test. Engine Linux nằm ở `/content/FairyZero/engine_src/build-linux/custom_engine`.
   - Nếu Colab dùng CUDA 11.x: `!ORT_VER=1.18.0 bash /content/FairyZero/scripts/colab_setup.sh`
4. Sinh dữ liệu + huấn luyện trên GPU — **một lệnh** (tự dò đường dẫn, GPU mặc định):
   ```
   !bash /content/FairyZero/scripts/colab_loop.sh
   # tùy chỉnh:  !GENS=4 GAMES=400 VISITS=128 EPOCHS=15 bash /content/FairyZero/scripts/colab_loop.sh
   # lưu model thẳng về Drive:  !SAVE_DIR=/content/drive/MyDrive/FairyZero/models bash .../colab_loop.sh
   ```
   (provider=cuda tự bật FP16 mixed-precision cho nhanh.) Hoặc gọi trực tiếp `loop.py`:
   ```
   !python /content/FairyZero/python/loop.py \
       --engine /content/FairyZero/engine_src/build-linux/custom_engine \
       --gens 10 --games-per-gen 1000 --visits 200 --window-gens 4 --epochs 20 \
       --provider cuda --fixed-batch 32 --parallel 2 --batch 1024 --eval-games 40
   ```
5. Chép model về Drive để giữ rồi tải về máy, đặt vào `FairyZero\models\`, rồi chơi (Mục A):
   `!cp /content/FairyZero/python/loop_run/models/*.onnx /content/drive/MyDrive/FairyZero/models/`

---

## D. DANH MỤC SIÊU THAM SỐ (tra cứu nhanh)

> Mỗi phần ghi rõ **DÙNG ĐƯỢC** (chỉnh được ngay) và **CHƯA DÙNG ĐƯỢC** (chưa có nút, chạy ở
> giá trị mặc định) để bạn biết giới hạn hiện tại.

### D.1. Khi CHƠI (`--uci-nn`, lệnh `setoption name <X> value <Y>`)

**DÙNG ĐƯỢC — option thân thiện:**
| Option | Mặc định | Ý nghĩa |
|--------|----------|---------|
| `WeightsFile` | seed.onnx | đời mạng |
| `Visits` | 800 | playout/nước khi `go` không ghi `nodes` |
| `Threads` | 1 | luồng MCTS |
| `Provider` | cpu | cpu / cuda |
| `FixedBatch` | 16 | batch GPU |
| `BackendThreads` | 1 | luồng tính mạng (CPU) |
| `PolicySoftmaxTemp` | **1.359** (khớp lc0) | làm mềm gợi ý mạng |
| `MoveOverheadMs` | 30 | trừ hao thời gian |
| `Temperature` | 0 | **hạ độ khó** (‰): >0 → đôi khi đi nước hạng 2/3 |
| `TempCutoffPly` | 0 | chỉ áp Temperature N nước đầu (0 = luôn) |
| `MultiPV` | 1 | số biến chính (PV) báo cáo |
| `ReuseTree` | true | giữ cây MCTS giữa các nước |
| `Ponder` | false | suy nghĩ khi tới lượt đối thủ |

**DÙNG ĐƯỢC — chỉnh sâu kiểu lc0** (đặt bằng tên gốc, vd `setoption name cpuct value 2.5`) — ~35 tham số:
- **PUCT:** `cpuct` (1.745) · `cpuct-base` (38739) · `cpuct-factor` (3.894) + bản `*-at-root` ·
  `root-has-own-cpuct-params` · `fpu-value` (0.330) · `fpu-value-at-root` (1.0) · `fpu-strategy`
  (reduction/absolute) · `fpu-strategy-at-root`.
- **Hòa/khinh địch:** `draw-score` (0) · `two-fold-draws` (true) · `contempt-mode` · `contempt-max-value` ·
  `wdl-calibration-elo` · `wdl-contempt-attenuation` · `wdl-max-s` (1.4) · `wdl-eval-objectivity` ·
  `wdl-draw-rate-target`/`-reference` · `wdl-book-exit-bias` · `score-type`.
- **Nhiệt độ (lc0):** `tempdecay-moves` · `tempdecay-delay-moves` · `temp-cutoff-move` · `temp-endgame` ·
  `temp-value-cutoff` · `temp-visit-offset` · `policy-softmax-temp` (1.359).
- **Hiệu năng:** `minibatch-size` · `max-collision-events` · `max-collision-visits` · `out-of-order-eval` ·
  `max-out-of-order-evals-factor` · `cache-history-length` · `sticky-endgames` · `nps-limit` ·
  `max-concurrent-searchers` · `task-workers` · `search-spin-backoff` · `garbage-collection-delay` ·
  `per-pv-counters` · `verbose-move-stats`.

*(Mặc định mọi tham số search = đúng default lc0-master.)*

**Điều khiển `go`:** `nodes N` · `movetime ms` · `wtime W btime B winc Wi binc Bi movestogo M` ·
`infinite` (+`stop`) · `searchmoves m1 m2…` · `ponder` (+`ponderhit`). Engine phát `info ... score cp ...
wdl ... multipv ... pv ...`.

**CHƯA DÙNG ĐƯỢC:** vài tham số search hiếm/nội bộ chưa đưa vào (`max-prefetch`, `solid-tree-threshold`,
`minimum-*-work`…); `go depth N`/`go mate N` (nhận nhưng chưa giới hạn); `score mate N` (chưa phát);
ponder mới ở mức cơ bản (kết thúc khi `ponderhit`, chưa cấp thêm ngân sách thời gian).

### D.2. Khi SINH DỮ LIỆU (`custom_engine.exe --selfplay`)

**DÙNG ĐƯỢC — cờ CLI:**
| Cờ | Mặc định | Ý nghĩa |
|----|----------|---------|
| `--games N` | 100 | số ván |
| `--visits N` | 200 | độ sâu MCTS mỗi nước |
| `--parallel K` | 1 | số ván song song (≈ số nhân CPU) |
| `--threads-per-game T` | 1 | luồng MCTS mỗi ván |
| `--max-moves N` | 200 | giới hạn số nước/ván |
| `--temp-cutoff N` | 30 | số nước đầu lấy mẫu theo visit (đa dạng) |
| `--backend-threads N` | 1 | luồng tính mạng (CPU) |
| `--provider cpu\|cuda` | cpu | thiết bị |
| `--fixed-batch N` | 16 | batch GPU |
| `--weights FILE` | — | mạng tự chơi |
| `--out DIR` | selfplay_data | thư mục ghi |
| `--noise-epsilon F` | 0.25 | nhiễu Dirichlet |
| `--noise-alpha F` | 0.3 | tham số nhiễu |
| `--policy-temp F` | 1.0 | làm mềm gợi ý mạng |
| `--cpuct F` | auto(1.745) | hệ số khám phá MCTS |
| `--start-fen FEN\|FILE` | startpos | thế bắt đầu / sách FEN |
| `--resign-threshold F` | tắt | tự thua khi best_q≤F (bật: -0.90) |
| `--resign-consecutive N` | 3 | số lượt liên tiếp dưới ngưỡng |
| `--resign-earliest-move N` | 0 | không resign trước nước N |
| `--no-resign-frac F` | 0.10 | tỉ lệ ván KHÔNG resign |
| `--search-opt name=value` (lặp) | — | đặt **bất kỳ** search-param lc0 (xem danh sách ~35 ở D.1), vd `--search-opt cpuct-base=20000 --search-opt two-fold-draws=true` |

**CHƯA DÙNG ĐƯỢC từ CLI self-play:** `--resign-wdlstyle` (resign theo ngưỡng WDL) chưa viết.
*Lưu ý: self-play VỐN đã tái dùng cây trong một ván (không cần cờ riêng).*

### D.3. Khi HUẤN LUYỆN (`python train.py`)

**DÙNG ĐƯỢC — cờ CLI:**
| Cờ | Mặc định | Ý nghĩa |
|----|----------|---------|
| `--data X` | — | thư mục / nhiều thư mục (phẩy) / `.zip` |
| `--epochs N` | 20 | số vòng học |
| `--batch N` | 32 | cỡ lô (GPU đặt 512–2048) |
| `--lr F` | 1e-3 | tốc độ học (khi không dùng lịch LR) |
| `--q-ratio F` | 0.2 | trộn mục tiêu value (q & kết quả ván) |
| `--downsample F` | 1.0 | giữ ngẫu nhiên F thế cờ (chống trùng) |
| `--channels N` / `--blocks N` | 128 / 10 | kích thước mạng |
| `--init-from FILE.pt` | — | warm-start từ đời trước |
| `--out FILE.onnx` | model_gen1.onnx | mạng xuất ra |
| `--device auto\|cuda\|cpu` | auto | thiết bị |
| `--amp` | tắt | FP16 (chỉ GPU) |
| `--value-weight F` / `--policy-weight F` | 1.0 / 1.0 | trọng số loss |
| `--weight-decay F` | 1e-4 | L2 (chống quá khớp) |
| `--swa-start-frac F` | 0.75 | bắt đầu SWA |
| `--optimizer adamw\|sgd\|nadam` | adamw | bộ tối ưu (sgd+momentum = lc0 chuẩn) |
| `--momentum M` | 0.9 | momentum cho sgd |
| `--grad-clip G` | 0 (tắt) | clip grad-norm |
| `--seed S` | 0 | hạt giống tái lập |
| `--warmup-steps N` | 0 | warmup LR tuyến tính N bước |
| `--lr-values a,b` + `--lr-boundaries i` | — | **lịch LR bậc thang** (kiểu lc0; ghi đè `--lr`) |
| `--accum-steps K` | 1 | tích lũy gradient → batch hiệu dụng lớn trên GPU nhỏ |
| `--max-steps N` | 0 | dừng sau N bước tối ưu (thay/cạnh `--epochs`) |
| `--max-records N` | 0 | giới hạn số thế cờ nạp (0 = tất cả) |
| `--report-every N` | 0 | in loss mỗi N bước (0 = theo epoch) |
| `--save-every N` | 0 | lưu checkpoint `.pt` mỗi N bước |
| `--se-ratio R` | 8 | tỉ lệ nén SE block (CHỈ khi train từ đầu — đổi → không warm-start được) |
| `--dropout R` | 0 | dropout ở value head (warm-start an toàn) |
| `--diff-focus` (+ `--df-slope/--df-kld-w/--df-min`) | tắt | ưu tiên thế cờ "khó" |
| `--workers N` / `--pin-memory` | 0 | tăng tốc nạp dữ liệu |
| `--sparse-cache` / `--dense-cache` | sparse | cách cache (sparse chống OOM Colab) |

> **Để giống lc0-training:** mặc định của ta là **AdamW + LR hằng** (dễ/ổn cho quy mô nhỏ). Muốn khớp
> lc0 (SGD + lịch LR), dùng: `--optimizer sgd --momentum 0.9 --warmup-steps 250
> --lr-values 0.02,0.002,0.0005 --lr-boundaries 100000,130000` (theo `example.yaml`).

**CHƯA DÙNG ĐƯỢC (chưa có cờ):** `--loss-scale`, `--batch-renorm`, `--ema`, `--swa-max-n/--swa-every`,
`--val-split/--test-every`, `--shuffle-size`.

### D.4. Vòng lặp (`python loop.py`)
Cờ chung: `--engine --workdir --gens --start-gen --games-per-gen --visits --max-moves --window-gens
--epochs --batch --lr --provider --parallel --fixed-batch --eval-games --amp` và **truyền thẳng** mọi cờ
self-play (resign, noise, cpuct…) + training (value/policy-weight, optimizer, grad-clip, lr-values/boundaries,
warmup-steps, seed, diff-focus…) ở D.2/D.3.

---

## E. KHẮC PHỤC SỰ CỐ

- **`custom_engine.exe` không chạy / thiếu DLL:** đảm bảo các tệp `.dll` nằm **cùng thư mục**
  với `.exe` (đừng tách ra). Đây là bản đã đóng gói đủ DLL cho Windows.
- **`bestmove 0000`:** thế cờ đã hết (chiếu hết/hòa) hoặc nạp mạng thất bại — kiểm tra đường
  dẫn `--weights`.
- **Engine "đứng im" sau `go infinite`:** đúng vậy — nó nghĩ vô hạn; gõ `stop` để lấy nước.
- **Python báo thiếu thư viện:** chạy `pip install -r python\requirements.txt`.
- **Test engine còn nguyên vẹn:** `custom_engine.exe --test-uci` (kiểm tra I/O nước) phải in
  `[PASS]`.

---

Chúc bạn chơi vui và huấn luyện ra những đời mạng ngày càng mạnh! 🦊♟️
