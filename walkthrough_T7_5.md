# Walkthrough T7.5 — Bù 3 khoảng trống so với Implementation Plan

> Phạm vi: triển khai các hạng mục mà bản audit (đối chiếu `implementation_plan phase training_1.md`) phát hiện là **đã ghi trong plan nhưng code chưa áp dụng**:
> 1. **Cơ chế đầu hàng sớm (Resign)** — plan Mục A5
> 2. **Huấn luyện FP16 Mixed-Precision (+ đưa train lên GPU)** — plan Mục 5.3
> 3. **Sparse Shuffle Buffer nối thẳng vào đường huấn luyện** — plan Mục B1 / 8.2.2
> 4. **Đóng gói `.gz` → `.zip` (Store) cho truyền tải Drive** — plan Mục 5.3 (bổ sung sau)
>
> Ngày: 2026-06-20. Tất cả thay đổi đã build (C++) và chạy thử (Python + engine) thành công trên Windows.
> (Lịch visits tăng dần — plan 5.1 — **bỏ qua theo yêu cầu**: `--visits` đã cho tự đặt mức tùy ý.)

---

## 0. Bối cảnh

Sau khi hoàn tất T7 (vòng lặp AlphaZero khép kín), ta đối chiếu lại từng dòng của implementation plan với mã nguồn thực tế. Ba thứ trên là **khoảng trống thật** (ảnh hưởng throughput, tốc độ train, và nguy cơ sập RAM Colab), nên được làm trước khi sang T8. Các điểm còn lại (lịch visits tăng dần, đóng gói `.zip`) là tiện ích, để sau.

Mỗi mục dưới đây trình bày theo cùng cấu trúc: **Plan nói gì → Thiếu gì → Đã làm gì (file + logic) → Vì sao thiết kế vậy → Kiểm thử**.

---

## 1. Cơ chế đầu hàng sớm (Resign)

### 1.1. Plan nói gì (Mục A5, dòng 145)
> *"Nếu `best_q` của một bên tụt xuống dưới ngưỡng resign (vd −0.90) liên tiếp trong 3 lượt đi, ván đấu sẽ được xử thua sớm. Thiết lập tỷ lệ 'no-resign' khoảng 10% các ván để hệ thống vẫn học được cách chống đỡ ở các thế cờ yếu và lật ngược thế cờ."*

Mục đích: **tăng throughput sinh dữ liệu** — không phí thời gian đánh đến tàn cuộc những ván đã thua rõ; đồng thời **giữ 10% ván không resign** để mạng vẫn học phòng thủ/lật kèo.

### 1.2. Thiếu gì
`selfplay_game.cc` hoàn toàn không có logic resign. Ván chỉ kết thúc khi `ComputeGameResult` báo hết cờ (chiếu hết/hòa/7-check/rule50/lặp 3 lần) hoặc chạm `max_moves`.

### 1.3. Đã làm gì

**`src/lczero_chess/selfplay/selfplay_game.h`** — mở rộng chữ ký `PlayOneGame`, thêm 3 tham số (đều có default để không phá các lời gọi cũ ở `main.cc`):
```cpp
GameResult PlayOneGame(..., int search_threads = 1, bool verbose = true,
                       float resign_threshold = -2.0f,
                       int resign_consecutive = 3, bool allow_resign = true);
```

**`src/lczero_chess/selfplay/selfplay_game.cc`** — bộ đếm chuỗi-resign theo từng bên + kiểm tra trong vòng lặp ply:
```cpp
// Resign chỉ bật khi caller cho phép VÀ ngưỡng nằm trong [-1,1] (best_q range).
const bool resign_active = allow_resign && resign_threshold > -1.0f;
int resign_streak[2] = {0, 0};      // [0]=White, [1]=Black
...
// sau khi đã ghi record (rec.best_q là eval theo góc nhìn bên-đang-đi):
if (resign_active) {
  const int s = black ? 1 : 0;
  if (rec.best_q <= resign_threshold) {
    if (++resign_streak[s] >= resign_consecutive) {
      result = black ? GameResult::WHITE_WON : GameResult::BLACK_WON;  // bên s thua
      break;
    }
  } else {
    resign_streak[s] = 0;           // eval hồi phục -> reset chuỗi
  }
}
```

**`src/lczero_chess/selfplay/selfplay_driver.{h,cc}`** — thêm 3 trường vào `SelfPlayConfig` và **quyết định no-resign theo từng ván** trong worker:
```cpp
// SelfPlayConfig:
float resign_threshold = -2.0f;   // <= -1.0 => tắt resign
int   resign_consecutive = 3;
float no_resign_frac = 0.10f;     // tỉ lệ ván tắt resign

// trong worker (mỗi ván tự bốc ngẫu nhiên):
const bool allow_resign =
    cfg.no_resign_frac <= 0.0f ||
    Random::Get().GetDouble(1.0) >= cfg.no_resign_frac;
```

**`src/main.cc`** — 3 cờ CLI mới: `--resign-threshold`, `--resign-consecutive`, `--no-resign-frac`; gán vào `cfg`; in cấu hình resign khi bật.

**`python/loop.py`** — truyền 3 cờ này xuống engine self-play (chỉ thêm vào lệnh khi người dùng đặt giá trị).

### 1.4. Vì sao thiết kế vậy (các quyết định then chốt)

- **`best_q` là eval theo góc nhìn bên-đang-đi** (đã có sẵn trong record). Vì vậy `best_q <= ngưỡng_âm` nghĩa là "chính bên sắp đi tự thấy mình đang thua nặng" → đúng ngữ nghĩa plan.
- **Đếm theo từng bên** (`resign_streak[2]`): "3 lượt liên tiếp" trong plan là **3 lượt của CÙNG một bên**. Lượt đối phương xen giữa không reset bộ đếm của bên kia (mỗi bên có counter riêng). Khi eval của một bên hồi phục (> ngưỡng) thì reset đúng bộ đếm của bên đó.
- **Không cần cờ bật/tắt riêng**: dùng chính ngưỡng làm công tắc — `best_q ∈ [-1,1]`, nên `resign_threshold <= -1.0` (mặc định `-2.0`) là **không bao giờ chạm = tắt hẳn**. Muốn bật thì truyền `-0.90`. Gọn, không thêm trạng thái.
- **Record của thế cờ resign vẫn được giữ**: ta resign *sau khi* đã push record của thế cờ hiện tại. Đây là dữ liệu hợp lệ (thế cờ thua thật) — không bỏ phí.
- **No-resign quyết định mức từng ván, trong worker** (không phải toàn batch): đảm bảo đúng ~10% ván rải đều, không phụ thuộc thứ tự. Dùng `Random::Get()` (PRNG sẵn có của lczero).

### 1.5. Kiểm thử (đã chạy thật)

Build lại engine bằng `ninja -C build` → **link `custom_engine.exe` thành công** (chỉ còn warning deprecation sẵn có của Stockfish).

Chạy self-play với ngưỡng ép resign (`--resign-threshold 0.0 --resign-consecutive 1`):

| Chế độ | Lệnh thêm | Kết quả ván (số ply mỗi ván) |
|--------|-----------|------------------------------|
| **Resign bật** | `--no-resign-frac 0.0` | game_1/2/3 = **1 ply** (Trắng đi 1 nước, best_q≤0 → đầu hàng ngay, Đen thắng); game_0 = 30 ply (best_q luôn >0 nên không resign → chạm max-moves) |
| **No-resign** | `--no-resign-frac 1.0` | cả 2 ván = **20 ply** (đi hết max-moves, KHÔNG resign dù cùng ngưỡng) |

→ Chứng minh: (a) resign kích hoạt và rút ngắn ván đúng theo `best_q`; (b) kết quả **quyết thắng** chứ không phải hòa-do-hết-nước; (c) đường no-resign tắt resign chính xác. Console cũng in đúng dòng cấu hình:
```
[selfplay] resign: best_q<=0 for 1 moves, no-resign frac=0
```

> Lưu ý dùng thật: ngưỡng khuyến nghị **−0.90** với **3 lượt** (như plan). Driver in cảnh báo per-game tắt (`verbose=false`) để tránh log chen nhau; muốn xem từng resign thì chạy 1 ván qua đường test verbose.

---

## 2. Huấn luyện FP16 Mixed-Precision (+ đưa train lên GPU)

### 2.1. Plan nói gì (Mục 5.3, dòng 296)
> *"Huấn luyện (Module B): Thực hiện 100% trên Colab GPU để tận dụng Mixed-Precision (FP16), đẩy batch size lên lớn (1024–2048) nhằm rút ngắn thời gian huấn luyện mỗi đời xuống còn vài chục phút."*

### 2.2. Thiếu gì (và phát hiện thêm một lỗi tiềm ẩn)
- `train.py` **không có** `autocast`/`GradScaler` → train FP32, chậm và tốn VRAM hơn ~1.5–2× trên GPU.
- **Phát hiện thêm:** `train.py` **chưa hề chuyển model/dữ liệu lên GPU** (`net = FairyNet(...)` không có `.to(device)`, batch cũng không `.to(cuda)`). Tức là kể cả trên Colab, train vẫn chạy trên CPU! Đây là lỗi nghiêm trọng hơn cả việc thiếu FP16.

### 2.3. Đã làm gì (`python/train.py`)

**Thêm cờ:**
```python
--device {auto,cuda,cpu}   # auto = cuda nếu có, ngược lại cpu
--amp                      # bật FP16 mixed-precision (chỉ có tác dụng trên cuda)
--sparse-cache / --dense-cache   # (xem Mục 3)
```

**Chọn device + bật AMP an toàn:**
```python
device = ("cuda" if torch.cuda.is_available() else "cpu") if args.device=="auto" else args.device
if device == "cuda" and not torch.cuda.is_available():
    print("WARNING: --device cuda but no CUDA; falling back to cpu"); device = "cpu"
use_amp = args.amp and device == "cuda"     # AMP chỉ bật trên GPU
```

**Đưa model lên device; vòng train dùng autocast + GradScaler:**
```python
net.to(device)
scaler = torch.amp.GradScaler("cuda", enabled=use_amp)   # no-op khi use_amp=False
...
for x, pi, val in dl:
    x = x.to(device, non_blocking=True)
    pi = pi.to(device, non_blocking=True)
    val = val.to(device, non_blocking=True)
    opt.zero_grad(set_to_none=True)
    with torch.autocast(device_type=device, enabled=use_amp):
        p_logits, v_logits = net(x)
        lp = policy_loss(p_logits, pi)
        lv = value_loss(v_logits, val)
        loss = lp + args.value_weight * lv
    scaler.scale(loss).backward()
    scaler.step(opt)
    scaler.update()
```

**SWA & export đồng bộ device:**
```python
update_bn(dl, swa_net, device=device)      # tính lại BN stats đúng device
final = swa_net.module.to("cpu")           # đưa về CPU trước khi save/export
torch.save(final.state_dict(), ckpt)
export_onnx(final, args.out)               # dummy input của export nằm ở CPU
```

**`python/loop.py`** — tự bật AMP khi `--provider cuda` (kèm `--pin-memory`); ngoài ra có cờ `--amp` để bật thủ công cả khi provider khác.

### 2.4. Vì sao thiết kế vậy

- **AMP chỉ bật trên CUDA** (`use_amp = args.amp and device=="cuda"`): FP16 trên CPU không lợi và dễ lỗi. Trên CPU, `autocast(enabled=False)` và `GradScaler(enabled=False)` thành **no-op** → code một nhánh, chạy đúng cả 2 môi trường.
- **`autocast` giữ softmax/log_softmax ở FP32 tự động**: hàm `policy_loss` của ta dùng `masked_fill(-inf)` + `log_softmax`. PyTorch autocast nằm trong danh sách "luôn FP32" cho các op softmax → **masked policy CE (có −inf) vẫn ổn định số học**, không NaN. Đây là lý do không cần sửa gì trong `policy_loss`.
- **`GradScaler`** chống underflow gradient FP16 (scale loss lên trước backward, unscale khi step). Bắt buộc cho FP16 train ổn định.
- **Đưa về CPU trước export**: `export_onnx` tạo `dummy = torch.randn(1,226,10,10)` trên CPU; nếu model còn ở CUDA sẽ lệch device. Đồng thời checkpoint `.pt` lưu từ CPU là **portable** (warm-start load với `map_location="cpu"`).
- **Dùng `torch.amp.GradScaler("cuda", ...)`** (API mới) thay cho `torch.cuda.amp.GradScaler` (đã deprecated, từng in FutureWarning).

### 2.5. Kiểm thử (đã chạy thật, CPU)

Tạo dữ liệu `.gz` tổng hợp (đúng layout 45940B, 3 ván × 8 ply) rồi chạy:
```
train.py --data _smoke_data --epochs 3 --batch 8 --blocks 2 --channels 16 --out smoke.onnx
```
Kết quả:
```
[train] device=cpu  amp=False  sparse_cache=True
[dataset] 3 files -> 24 records (... cached=True, sparse=True)
  epoch 1: policy_loss=3.7842  value_loss=0.7123
  epoch 2: policy_loss=3.6859  value_loss=0.4710
  epoch 3: policy_loss=3.6358  value_loss=0.4535
[swa] updating BatchNorm statistics on the averaged model...
[ckpt] saved smoke.pt
[export] wrote smoke.onnx
[verify] PASS: ONNX I/O contract matches engine (policy=logits, value=softmax WDL)
```
→ Toàn bộ đường device → autocast → scaler → SWA → update_bn → export → verify chạy trót lọt; loss giảm; ONNX khớp hợp đồng I/O. Sau khi đổi sang API `torch.amp.GradScaler` thì **hết FutureWarning**.

> Trên Colab GPU: `loop.py --provider cuda ...` sẽ tự thêm `--amp`; hoặc gọi trực tiếp `train.py --device cuda --amp --batch 1024`.

---

## 3. Sparse Shuffle Buffer nối vào đường huấn luyện

### 3.1. Plan nói gì (Mục B1 / 8.2.2, dòng 202–208 & bảng 8.2 #2)
Cảnh báo OOM Colab: giữ `probabilities[10600]` **dày đặc** trong buffer 100k thế cờ tốn **~4.6 GB RAM** → dễ sập. Giải pháp: trên RAM, Reader **nén thưa** policy thành list `(idx, prob)` cho nước hợp lệ (~600–900 B/record), chỉ **dày-hóa** khi tạo batch → buffer 100k chỉ còn **~400 MB**.

### 3.2. Thiếu gì
Lớp `ShuffleBuffer` và `downsample()` **đã tồn tại** trong `trainingdata_reader.py` nhưng **`dataset.py` không dùng**. `FairyDataset(cache=True)` cache **dày đặc** cả planes `[226,10,10]` (90 KB) lẫn `pi[10600]` (42 KB) = **~132 KB/record** → 100k record ≈ **13 GB** → đúng kịch bản OOM mà plan cảnh báo. Trước đó chỉ an toàn vì data demo nhỏ.

### 3.3. Đã làm gì (`python/dataset.py`)

Thêm chế độ cache **thưa** (mặc định BẬT) cho `FairyDataset`, giữ nguyên đường dày để đối chứng:

```python
def __init__(self, ..., sparse=True):
    ...
    if cache and sparse:
        self._cached = [self._compact(r) for r in records]   # nén + BỎ dict thô (drop pi dày 42KB)
    elif cache:
        self._cached = [self._build(r) for r in records]     # cache tensor dày (cũ)
    else:
        self._records = records                              # stream, dựng lại mỗi lần
```

**Dạng compact mỗi record** — chỉ giữ thứ tối thiểu để tái dựng:
```python
def _compact(self, r):
    pi = r["probabilities"]
    legal = np.nonzero(pi > -0.5)[0].astype(np.uint16)   # chỉ nước HỢP LỆ (pi>=0)
    return {
        "piece_planes": np.asarray(r["piece_planes"], np.uint64),   # ~3.5KB bitboard words
        "ep_mask": np.asarray(r["ep_mask"], np.uint64),
        "castling_*_file": ..., "rule50_count": ..., "checks_remaining_*": ...,  # scalar
        "pi_idx": legal,                       # uint16  (~ vài trăm nước)
        "pi_val": pi[legal].astype(np.float32),
        "value": self._value(r),               # WDL đã trộn qMix, [3] f32 (tính sẵn)
    }
```

**Dày-hóa khi lấy item** (tái dựng đúng quy ước policy: illegal=−1):
```python
def _build_from_compact(self, c):
    x  = torch.from_numpy(reconstruct_planes(c))   # planes [226,10,10] dựng từ bitboard
    pi = np.full(POLICY_SIZE, -1.0, np.float32)    # mọi ô = -1 (illegal)...
    pi[c["pi_idx"]] = c["pi_val"]                  # ...rồi ghi đè các ô hợp lệ
    return x, torch.from_numpy(pi), torch.from_numpy(c["value"])
```

`train.py` truyền `sparse=args.sparse_cache` (mặc định True; `--dense-cache` để quay lại đường cũ). `loop.py` có `--dense-cache` để chuyển ngược nếu cần.

### 3.4. Vì sao thiết kế vậy

- **Giữ nguyên quy ước mask policy**: trong record, `pi = -1` (illegal), `0` (hợp lệ chưa thăm), `>0` (hợp lệ đã thăm). Ta sparse hóa theo `pi > -0.5` → **giữ cả ô `0`** (hợp lệ-chưa-thăm vẫn phải có mặt để loss không mask nhầm). Khi dày-hóa: nền `-1`, ghi đè ô hợp lệ → **tái tạo y hệt** vector gốc. Masked policy CE hoạt động đúng nguyên vẹn.
- **Bỏ dict thô sau khi nén**: điểm mấu chốt tiết kiệm RAM. `read_records` trả về dict có `probabilities[10600]` dày 42 KB; sau `_compact` ta **không giữ** dict đó nữa → chỉ còn ~4 KB/record.
- **Không lưu planes dày trong cache**: `_compact` chỉ giữ `piece_planes` (216×2 uint64 = 3.5 KB) + scalar; planes `[226,10,10]` (90 KB) được **dựng lại mỗi getitem** từ bitboard (vốn đã có hàm `reconstruct_planes` nhanh, vector hóa). Đây là phần tiết kiệm lớn nhất.
- **Tính sẵn `value` (WDL đã trộn qMix)** ngay lúc compact: getitem rẻ, không lặp lại phép trộn.
- **Mặc định BẬT sparse**: vì đầu ra **giống hệt bit** đường dày (đã chứng minh) nên đổi mặc định an toàn, và chính là biện pháp chống-OOM "đinh" của plan. Đường dày vẫn giữ qua `--dense-cache` cho ai cần tốc-độ-per-item tối đa trên dữ liệu nhỏ.

### 3.5. Kiểm thử (đã chạy thật)

**(a) Bit-identical sparse vs dense** — record tổng hợp (130 nước hợp lệ, có cả ô `0`):
```
planes equal : True
pi equal     : True
value equal  : True
num legal kept: 130  (đúng kỳ vọng)
OK sparse==dense bit-identical
```

**(b) End-to-end**: train smoke ở Mục 2.5 chạy với `sparse=True` mặc định và export/verify PASS → đường sparse hoạt động trong pipeline thật.

**Ước lượng RAM** (buffer 100k record):
| Chế độ | Mỗi record | 100k record |
|--------|-----------|-------------|
| Dày (cũ) | ~132 KB (planes 90 + pi 42) | **~13 GB → OOM** |
| Thưa (mới, mặc định) | ~4 KB (bitboard 3.5 + sparse pi ~0.6) | **~0.4 GB** |

→ Khớp con số plan (~400 MB).

---

## 4. Tổng hợp file đã đổi

| File | Thay đổi |
|------|----------|
| `src/lczero_chess/selfplay/selfplay_game.h` | `PlayOneGame` thêm `resign_threshold / resign_consecutive / allow_resign` |
| `src/lczero_chess/selfplay/selfplay_game.cc` | Logic đếm chuỗi-resign theo từng bên + xử thua sớm |
| `src/lczero_chess/selfplay/selfplay_driver.h` | `SelfPlayConfig` thêm 3 trường resign |
| `src/lczero_chess/selfplay/selfplay_driver.cc` | Quyết định no-resign per-game (random) + truyền tham số |
| `src/main.cc` | 3 cờ CLI resign + in cấu hình |
| `python/train.py` | `--device/--amp/--sparse-cache/--dense-cache`; `.to(device)`; autocast + GradScaler; `update_bn(device=)`; export ở CPU |
| `python/dataset.py` | Chế độ cache **thưa** (`_compact`/`_build_from_compact`), mặc định BẬT; `_resolve_files` + nạp nhận `.zip` |
| `python/loop.py` | Truyền cờ resign xuống self-play; tự bật `--amp` khi `--provider cuda`; cờ `--dense-cache` |
| `python/archive.py` | **MỚI** — `pack`/`unpack`/`list` gom `.gz`→`.zip` (Store) cho truyền tải Drive (5.3) |
| `python/trainingdata_reader.py` | `read_records_from_zip()` + refactor `_read_stream` (đọc thẳng member trong `.zip`) |
| `python/.gitignore` | thêm `*.zip` |

Không đổi định dạng record `TrainingDataV1` (vẫn 45940 B) → **không phá** dữ liệu/round-trip đã có.

---

## 5. Bảng cờ mới (tra cứu nhanh)

**Self-play (engine / `loop.py`):**
| Cờ | Mặc định | Ý nghĩa |
|----|----------|---------|
| `--resign-threshold F` | `-2.0` (tắt) | `best_q <= F` cho N lượt của một bên → bên đó thua. Bật thật: `-0.90` |
| `--resign-consecutive N` | `3` | Số lượt liên tiếp của cùng một bên |
| `--no-resign-frac F` | `0.10` | Tỉ lệ ván tắt resign (học phòng thủ) |

**Training (`train.py` / `loop.py`):**
| Cờ | Mặc định | Ý nghĩa |
|----|----------|---------|
| `--device {auto,cuda,cpu}` | `auto` | Thiết bị train |
| `--amp` | tắt | FP16 mixed-precision (chỉ tác dụng trên cuda; `loop.py` tự bật khi `--provider cuda`) |
| `--sparse-cache` | **BẬT** | Cache policy thưa, chống OOM (8.2.2) |
| `--dense-cache` | — | Quay lại cache dày (cũ) |

---

## 6. Cách dùng (ví dụ)

**Windows (CPU, dev/iterate nhanh):**
```bash
python python/loop.py --engine build/custom_engine.exe --gens 3 \
    --games-per-gen 40 --visits 64 --window-gens 3 --epochs 8 \
    --provider cpu --parallel 6 --eval-games 10 \
    --resign-threshold -0.90 --resign-consecutive 3 --no-resign-frac 0.10
# (CPU: sparse cache mặc định BẬT; AMP tự tắt)
```

**Colab (GPU, quy mô lớn):**
```bash
python python/loop.py --engine build-linux/custom_engine --gens 10 \
    --games-per-gen 1000 --visits 200 --window-gens 4 --epochs 20 \
    --provider cuda --fixed-batch 32 --parallel 2 --eval-games 40 \
    --batch 1024 \
    --resign-threshold -0.90 --resign-consecutive 3 --no-resign-frac 0.10
# (cuda: tự thêm --amp + --pin-memory; sparse cache BẬT)
```

---

## 7. Đóng gói `.gz` → `.zip` (Store) cho truyền tải Drive

### 7.1. Plan nói gì (Mục 5.3, dòng 297)
> *"Gom hàng ngàn file `.gz` nhỏ thành một file `.zip` lớn (không nén thêm, chỉ đóng gói dạng Store để tối ưu I/O) trước khi upload lên Google Drive nhằm tránh bị Google Drive bóp băng thông do tải nhiều file nhỏ liên tiếp."*

### 7.2. Đã làm gì

**`python/archive.py`** — công cụ dòng lệnh 3 lệnh con:
```bash
# Gom mọi .gz dưới một thư mục thành 1 bundle (giữ cấu trúc gen-dir trong arcname)
python archive.py pack loop_run/games --out games_bundle.zip
# Gom riêng vài đời
python archive.py pack loop_run/games/gen0 loop_run/games/gen1 --out g0_1.zip
# Xem / khôi phục
python archive.py list   games_bundle.zip
python archive.py unpack games_bundle.zip --dest restored/
```

**`python/trainingdata_reader.py`** — thêm `read_records_from_zip()` (refactor phần đọc record thành `_read_stream` dùng chung cho file thường lẫn member trong zip).

**`python/dataset.py`** — `_resolve_files` nhận thêm `.zip`; khi nạp, member `.zip` được đọc qua `read_records_from_zip`. Nghĩa là **train trực tiếp trên bundle, không cần giải nén**:
```bash
python train.py --data games_bundle.zip --epochs 10 --out model.onnx
# loop.py cũng nhận: --data có thể là .zip hoặc thư mục chứa .zip
```

**`python/.gitignore`** — thêm `*.zip`.

### 7.3. Vì sao thiết kế vậy

- **`ZIP_STORED` (không nén thêm)**: payload `.gz` đã nén rồi; deflate lại chỉ tốn CPU mà gần như không nhỏ thêm. Store = chỉ "gói" lại → nhanh, và mục tiêu plan là **giảm số file** (Drive bóp băng thông khi tải nhiều file nhỏ), không phải giảm dung lượng.
- **Giữ cấu trúc gen-dir trong arcname** (vd `gen0/game_3.gz`): arcname tính theo `os.path.relpath` so với thư mục cha chung (`commonpath`) → `unpack` khôi phục đúng layout, và rolling-window theo đời vẫn dùng được sau khi giải nén.
- **Reader đọc thẳng `.zip`**: trên Colab, tải **1 file** bundle từ Drive rồi `train.py --data bundle.zip` luôn — bỏ hẳn bước giải nén hàng nghìn file (vốn cũng chậm trên Colab). Đọc member zip → `gzip.GzipFile(fileobj=...)` → cùng `_read_stream`, không đụng định dạng record.
- **`allowZip64=True`**: bundle thật có thể vượt 4GB / 65k file → bật Zip64 để an toàn.

### 7.4. Kiểm thử (đã chạy thật)

Tạo data tổng hợp (2 đời × 3 ván × 6 ply = 36 record) rồi:
```
pack   -> packed 6 files (136.4KB) -> bundle.zip (137.2KB, STORE)
list   -> 6 files, 136.4KB uncompressed, STORE   (arcname giữ gen0/gen1/…)
unpack -> unpacked 6 files
```
Đối chiếu record (so khớp không phụ thuộc thứ tự, qua hash của probabilities + piece_planes):
```
counts: dir=36 zip=36 restored=36
zip == dir      : True
restored == dir : True
OK archive round-trip bit-faithful
```
Train trực tiếp trên `.zip`:
```
[dataset] 1 files -> 36 records (... sparse=True)
  epoch 1: policy_loss=3.4990  value_loss=0.5976
  epoch 2: policy_loss=3.3658  value_loss=0.4458
[verify] PASS
```
→ Bundle round-trip **bit-faithful**; train đọc thẳng bundle chạy + verify PASS.

### 7.5. Quy trình khuyến nghị (Colab)
1. Local/Colab sinh self-play → thư mục `loop_run/games/genN/*.gz`.
2. `python archive.py pack loop_run/games --out games.zip` → upload **1 file** `games.zip` lên Drive.
3. Trên máy/phiên Colab khác: tải `games.zip` → `python train.py --data games.zip ...` (không cần giải nén), hoặc `archive.py unpack` nếu muốn cấu trúc thư mục.

---

## 8. Còn lại so với plan

| Hạng mục | Plan | Trạng thái |
|----------|------|-----------|
| Lịch visits tăng dần 200→400→800 theo đời | 5.1 | **Không làm theo yêu cầu** — đã có `--visits` để tự đặt mức tùy ý mỗi lần chạy (ramp thủ công qua `--start-gen` nếu muốn). |

Mục này không ảnh hưởng tính đúng đắn.

---

## 9. Kết luận

Các khoảng trống quan trọng trước khi chạy thật quy mô lớn đã được lấp:
- **#1 Resign** → throughput sinh dữ liệu cao hơn, vẫn giữ 10% ván học phòng thủ.
- **#2 FP16 + GPU device** → sửa luôn lỗi tiềm ẩn "train chạy CPU trên Colab"; train nhanh hơn, batch lớn hơn.
- **#3 Sparse cache** → giảm RAM buffer từ ~13 GB xuống ~0.4 GB, tránh sập Colab, **đầu ra giống hệt bit** đường cũ.
- **Đóng gói `.zip` (Store)** → upload Drive 1 file thay vì hàng nghìn; train đọc thẳng bundle, không cần giải nén; round-trip bit-faithful.

Tất cả đã build (C++) và chạy thử (Python + engine) thành công trên Windows; đường GPU/AMP sẵn sàng kích hoạt trên Colab. Định dạng dữ liệu giữ nguyên nên không phá test/round-trip cũ.

Còn lại duy nhất: lịch visits tăng dần (5.1) — **bỏ qua theo yêu cầu** vì `--visits` đã cho tự đặt mức tùy ý.
