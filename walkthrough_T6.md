# Walkthrough — Phase T6: Model PyTorch 10×128 + Loss/qMix/SWA + Export ONNX

> Ngày: 2026-06-20 · Dự án: FairyZero (`custom_engine`) — biến thể cờ 10×10.
> Phạm vi đợt này: hiện thực hóa **milestone T6** trong `implementation_plan phase training_1.md` (mục B2–B4, kỹ thuật 8.2.1/8.2.4/8.2.5).
> DoD: mạng **10×128 hội tụ trên tập dữ liệu nhỏ**; **export ONNX thành công** và **chạy thử được trong engine**.
> Kết quả: ✅ Hoàn thành. Train hội tụ, export khớp hợp đồng I/O, và model đã **nạp + chạy thật trong engine C++**. Đây là **Module B (PyTorch Training)** đầu tiên — khép kín đường dữ liệu C++→Python→ONNX→C++.

---

## 0. T6 nằm ở đâu trong bức tranh lớn

Vòng lặp AlphaZero: **C++ self-play (T1–T4)** → `.gz` → **Python reader (T5)** → **PyTorch train (T6)** → `model_{N+1}.onnx` → quay lại engine. T6 là mắt xích **biến dữ liệu thành mạng mới**.

**Ràng buộc sống còn:** file ONNX xuất ra phải khớp **100% hợp đồng I/O** mà `OnnxComputation` (C++) nạp — nếu lệch tên/shape/thứ tự, engine không chạy hoặc chạy sai âm thầm.

---

## 1. Đối chiếu hợp đồng I/O (đọc thẳng `onnx_backend.cc`)

Trước khi code, xác minh chính xác engine mong đợi gì (`onnx_backend.cc`):
```cpp
const char* input_names[]  = { "input" };               // [batch,226,10,10]
char* output_names[]       = { "policy", "value" };
// policy: [batch,10600] -> engine tự softmax trên nước HỢP LỆ (raw logits, KHÔNG softmax in-graph)
float win  = raw_value[0];   // value[batch,3] = [W, D, L]
float draw = raw_value[1];
float loss = raw_value[2];
*res.q = win - loss;         // value PHẢI là xác suất -> value head CÓ softmax in-graph
*res.d = draw;
```
**Chốt 3 quy ước cho model:**
| Tensor | Tên | Shape | Ghi chú |
|--------|-----|-------|---------|
| input | `"input"` | `[batch,226,10,10]` (H=rank, W=file) | trục batch động tên `"batch"` |
| policy | `"policy"` | `[batch,10600]` | **logits thô** (engine softmax nước hợp lệ) |
| value | `"value"` | `[batch,3]` = [W,D,L] | **CÓ softmax in-graph** (engine đọc như xác suất) |

---

## 2. Các file đã tạo (Module B)

### 2.1. `[NEW] python/model.py` — `FairyNet` (**SE-ResNet 10×128**, lc0-faithful) + `ExportNet`
> ⚠️ **Cập nhật kiến trúc:** sau khi đọc mã nguồn lc0 (`lczero-training-master/tf/tfprocess.py`) và người dùng chốt, kiến trúc canonical là **SE-ResNet 10×128 trung thành với lc0** (xem §9). Bản T6 đầu tiên là plain ResNet (không SE) đã được thay. Tham số: **3.85M**.
- **Thân mạng:** conv stem 226→128 (3×3, no bias) + BN + ReLU → **10 SE-Residual blocks**, mỗi block: `conv-BN-ReLU → conv-BN → SE → +skip → ReLU`.
- **SE block (kiểu lc0 = scale + bias):** GAP `[B,128]` → FC(128→16) + ReLU → FC(16→**256**) → tách `(γ, β)` → **`out = sigmoid(γ)·x + β`** (ratio=8). Đây là dấu ấn lc0, mạnh hơn SE scale-only.
- **Policy head (mấu chốt):** conv 3×3 (128→128) → conv **1×1 ra 106 kênh** → tensor `[B,106,10,10]` → `flatten(1)` = index `c*100 + h*10 + w = type*100 + rank*10 + file`.
  > Đây **chính xác là `MoveToNNIndex`** (106 move-type × 100 from-square = 10600). Lợi: tránh FC khổng lồ `3200×10600` (~34M tham số), và **khớp index policy bằng cấu trúc** chứ không phải bằng tay.
- **Value head:** conv 1×1 (128→32) → FC(3200→128) → FC(128→3) **logits** (W,D,L).
- `forward` trả `(policy_logits, value_logits)` — **dùng cho train** (CE trên logits ổn định số học).
- **`ExportNet(net)`:** bọc cho export — policy giữ logits, **value += `softmax`** → đúng hợp đồng (engine đọc xác suất WDL). Tách train/export giúp loss train trên logits còn ONNX có softmax.

### 2.2. `[NEW] python/dataset.py` — `FairyDataset`
- Đọc `.gz` qua `trainingdata_reader.read_records` → mỗi record: `reconstruct_planes` (T5) ra `[226,10,10]`, `π = probabilities[10600]`.
- **qMix value target (8.2.1):** `wdl_from_qd(q,d)` đổi `(q=win−loss, d=draw)` → phân bố `[W,D,L]` chuẩn hóa; rồi
  `target_wdl = q_ratio·q_wdl + (1−q_ratio)·z_wdl` (mặc định `q_ratio=0.2`).
  > Trộn ở **mức phân bố WDL** (không phải scalar) cho ra phân bố hợp lệ để CE, mà scalar `q = target[0]−target[2]` vẫn đúng công thức plan.
- **Down-sampling (8.2.3):** giữ mỗi record với xác suất `downsample_keep`.
- **Cache RAM** cho tập nhỏ (epoch nhanh, không dựng lại tensor mỗi lần). (Quy mô Colab → chuyển streaming.)

### 2.3. `[NEW] python/train.py` — vòng train + SWA + export + verify
- **Loss tổng hợp (8.2.5):**
  - `policy_loss = −Σ π·log_softmax(logits)` (π=0 ở nước chưa thăm/phi pháp nên chỉ nước được search đóng góp; softmax chuẩn hóa trên cả 10600).
  - `value_loss = −Σ target_wdl·log_softmax(value_logits)` (CE WDL).
  - **L2** qua `AdamW(weight_decay=1e-4)`.
- **SWA (8.2.4):** `AveragedModel` + `SWALR`; bắt đầu trung bình trọng số từ epoch `0.75·epochs`; **`update_bn`** chạy lại thống kê BatchNorm cho model trung bình **trước khi export** (bắt buộc, nếu không BN sai).
- **Lưu checkpoint** `.pt` trước export (export lại không cần train lại).
- **Export ONNX** + **tự verify** (xem 2.4).

### 2.4. Export + tự kiểm (trong `train.py`)
```python
torch.onnx.export(ExportNet(net), dummy[1,226,10,10], path,
    input_names=["input"], output_names=["policy","value"],
    dynamic_axes={"input":{0:"batch"},"policy":{0:"batch"},"value":{0:"batch"}},
    opset_version=17, dynamo=False)
```
`verify_onnx`: `onnx.checker` + đọc graph (tên/shape input=`["batch",226,10,10]`, policy=`["batch",10600]`, value=`["batch",3]`) + chạy `onnxruntime` trên batch ngẫu nhiên, **khẳng định `value.sum(axis=1)==1`** (softmax WDL) và policy không bị ràng buộc tổng (logits).

---

## 3. Build dữ liệu + chạy + sửa lỗi

### 3.1. Sinh tập huấn luyện nhỏ (self-play thật)
```
custom_engine.exe --selfplay --games 12 --parallel 4 --visits 32 --max-moves 24 --out python\selfplay_data
-> 12 ván (toàn DRAW — mạng gen-0 ngẫu nhiên), 288 records
```

### 3.2. Lỗi export gặp phải & cách sửa (1 lỗi)
Lần đầu export **crash** ở bước logging:
```
UnicodeEncodeError: 'charmap' codec can't encode character '✅' (✅)
```
→ Exporter MỚI của torch 2.12 (dynamo) **in emoji "✅"** ra stdout, console Windows **cp1252** không mã hóa được → vỡ **ngay khi đang in** (model + graph đã capture xong, không phải lỗi mạng).
**Sửa (2 lớp):**
1. `dynamo=False` → dùng **legacy TorchScript exporter** (ổn định, không in emoji, graph sạch ORT nạp tốt) + `opset_version=17`.
2. Đặt `PYTHONIOENCODING=utf-8` khi chạy (phòng xa).
Đồng thời **lưu checkpoint `.pt` trước export** để không phải train lại nếu export lỗi.

### 3.3. Train + export + verify — PASS
```
[train] params=3.79M  swa_start_epoch=9
  epoch  1: policy_loss=7.7347  value_loss=0.7242
  epoch  2: policy_loss=5.7117  value_loss=0.4874
  ...
  epoch 12: policy_loss=3.0482  value_loss=0.4806
[ckpt] saved python\model_gen1.pt
[export] wrote python\model_gen1.onnx
[verify] inputs=[('input', ['batch', 226, 10, 10])]
[verify] outputs=[('policy', ['batch', 10600]), ('value', ['batch', 3])]
[verify] runtime OK: policy(2,10600) value(2,3) value_sum=[1.0, 1.0000001]
[verify] PASS: ONNX I/O contract matches engine.
```

### 3.4. Bằng chứng cuối: **nạp model vào engine C++**
```
custom_engine.exe --test-extract --weights python\model_gen1.onnx
[T2] OnnxBackend + MemCache loaded.       (chính là model_gen1.onnx của ta)
  move 0 (white): sum(pi)=1 ... orig_q=-0.000916 ...   <- eval của MẠNG MỚI (khác ~0.01 của net ngẫu nhiên)
ALL T2 (EXTRACT) TESTS PASSED!
```
`orig_q` đổi từ ~0.01 (net gen-0) sang ~−0.0009 → xác nhận engine đang inference **đúng model vừa train**, không phải net cũ. Tương thích I/O **thực tế** (không chỉ verify Python).

---

## 4. Phân tích kết quả

- **policy_loss 7.73 → 3.05:** giảm đều → mạng học được phân bố visit π. (log(10600)≈9.27 là loss "đoán đều"; 7.73→3.05 là tiến bộ rõ.)
- **value_loss 0.72 → 0.48 rồi phẳng:** dữ liệu **toàn DRAW** → value head nhanh chóng học "hòa" (CE của phân bố gần [0,1,0]). Đúng bản chất bootstrap gen-1; tín hiệu thắng/thua sẽ xuất hiện khi self-play mạnh dần.
- **3.79M params** cho 10×128 — gọn, chạy inference vài ms/lượt trên CPU (đúng dự toán plan).
- **SWA** chạy epoch 9–12 + `update_bn` → trọng số xuất khái quát hơn.

---

## 5. Đối chiếu DoD T6

| Tiêu chí (plan) | Trạng thái |
|-----------------|-----------|
| Mạng ResNet 10×128 | ✅ (3.79M params) |
| Hội tụ trên tập nhỏ | ✅ (policy 7.73→3.05, value 0.72→0.48) |
| Export ONNX thành công | ✅ (`model_gen1.onnx`) |
| I/O khớp engine: input/policy/value, batch động, **policy logits / value softmax** | ✅ (verify tự động + chạy engine) |
| **Chạy thử trong engine** | ✅ (`--test-extract --weights` PASS) |
| qMix (8.2.1) + SWA (8.2.4) + Loss tổng hợp (8.2.5) | ✅ |

---

## 6. Bảng quyết định kỹ thuật & lý do

| Quyết định | Lý do |
|-----------|-------|
| Policy head = conv 1×1 ra **106 kênh** rồi flatten | Index `type*100+rank*10+file` khớp `MoveToNNIndex` **bằng cấu trúc**; tránh FC 34M tham số |
| `forward` trả logits; `ExportNet` mới thêm softmax value | Train CE trên logits ổn định; ONNX vẫn có softmax đúng hợp đồng |
| qMix trộn ở mức **phân bố WDL** | Cho ra phân bố hợp lệ để CE; scalar q vẫn đúng công thức plan |
| `AdamW(weight_decay=1e-4)` | L2 (8.2.5) gọn trong optimizer |
| `update_bn` trước export | SWA chỉ trung bình tham số, không trung bình thống kê BN → phải tính lại |
| `dynamo=False` + opset 17 | Né crash emoji của exporter mới trên Windows; graph legacy ORT 1.18 nạp chắc |
| Lưu `.pt` trước export | Export lại không cần train lại |
| Verify bằng cả `onnx` + `onnxruntime` + **chạy engine thật** | "Tam giác hóa" — không tin một nguồn |

---

## 7. Trạng thái & việc tiếp theo

- **CHƯA commit.** File MỚI: `python/{model.py, dataset.py, train.py, make_seed.py}`. Output demo: `python/selfplay_data/*.gz`, `python/model_gen{0,1}.{onnx,pt}` — **nên gitignore** (`*.onnx`, `*.pt`, `selfplay_data/`).
- **Hạn chế còn lại (không chặn DoD):**
  - Dữ liệu gen-0 toàn hòa → value chưa có tín hiệu thắng/thua (sẽ tự cải thiện qua các đời).
  - *(Hai hạn chế về `reconstruct_planes` vòng lặp Python và policy CE không-mask đã được **XỬ LÝ** — xem §9.)*
- **Bước tiếp theo:**
  - **T6.5** — port engine sang **Linux/CUDA** để chạy self-play + train trên **Google Colab GPU** (tích hợp `onnxruntime-linux-gpu`, sửa `meson.build` theo `host_machine.system()`, bật CUDA EP). Đây là điều kiện để sinh dữ liệu khối lượng lớn + train nhanh.
  - **T7** — khép **vòng lặp AlphaZero đầy đủ** (self-play → train → model mới → lặp; rolling window 8.2.8, diff_focus 8.2.6).

---

## 8. Cách chạy lại (ghi nhớ)
```powershell
cd D:\chess_variant\custom_engine
$env:PYTHONIOENCODING = "utf-8"
$py = "C:\Users\7\AppData\Local\Programs\Python\Python313\python.exe"

# 1) sinh dữ liệu nhỏ
.\build\custom_engine.exe --selfplay --games 12 --parallel 4 --visits 32 --max-moves 24 --out python\selfplay_data
# 2) train + export + verify
& $py python\train.py --data python\selfplay_data --epochs 12 --batch 64 --out python\model_gen1.onnx
# 3) chạy thử trong engine
.\build\custom_engine.exe --test-extract --weights python\model_gen1.onnx
```
> Engine: PowerShell (PATH có MSYS2 ucrt64). Python: Python313 (torch 2.12+cpu, onnx 1.21, onnxruntime 1.23, numpy 2.2.6).

---

## 9. Cập nhật sau T6 — kiến trúc lc0 + 2 tối ưu hiệu năng

### 9.1. Kiến trúc canonical = SE-ResNet 10×128 (theo lc0) + warm-start
Sau khi đọc mã nguồn lc0 (`lczero-training-master/tf/tfprocess.py`) và người dùng chốt:
- **`python/model.py`** đổi từ plain ResNet → **SE-ResNet trung thành lc0** (SE scale+bias `sigmoid(γ)·x+β`, ratio=8). **3.85M params** (run thật: policy 7.55→ giảm, value→0.49).
- **`python/make_seed.py` (MỚI)** sinh seed gen-0 từ chính kiến trúc đó → `model_gen0.{onnx,pt}` → **thay `create_zero_elo_net.py`** (SE scale-only của script cũ không khớp → không warm-start được). `weights_0_elo.onnx` được thay bằng `model_gen0.onnx`.
- **`train.py --init-from <ckpt.pt>`** — **warm-start**: gen-N+1 train tiếp từ trọng số gen-N (đã verify: nạp seed → train → gen1 → chạy engine).
- Quy trình loop: `make_seed` (1 lần) → self-play với `model_gen0.onnx` → `train.py --init-from model_gen0.pt` → `model_gen1.onnx` → lặp.

### 9.2. Fix #1 — Vector hóa `reconstruct_planes` (tăng tốc NẠP dữ liệu train)
> Lưu ý: hạn chế này **chỉ ảnh hưởng phía huấn luyện** (tốc độ DataLoader), KHÔNG ảnh hưởng tốc độ sinh dữ liệu (C++ thuần đã nhanh).
- `trainingdata_reader.py`: thay vòng lặp bit Python bằng **numpy vector hóa** — tiền tính lưới `(word, bit)` cho 100 ô bàn cờ, rồi `sel = words[..., WORD_GRID]; bits = (sel >> BIT_GRID) & 1` bung **cả 216 plane một lần** (`_unpack_block`). ~10–50× nhanh hơn.
- Giữ `_set_mask_bits` làm **bộ giải mã tham chiếu** (test_bits.py kiểm), còn `reconstruct_planes` dùng đường vector.
- **Verify bit-identical:** `test_roundtrip.py` (3 case, gồm history 8 ply) + `test_bits.py` vẫn **PASS** sau khi đổi → output không lệch một bit.

### 9.3. Fix #2 — Legal-move masking cho policy loss (chuẩn lc0)
> Lưu ý: cải thiện **chất lượng/độ hội tụ** huấn luyện, không phải tốc độ sinh dữ liệu.
- **C++ `FillSearchTargets`:** điền `π = -1` cho MỌI slot trước, rồi root-edges (chính là nước hợp lệ) ghi đè bằng visit-fraction → **illegal = -1, legal-unvisited = 0, legal-visited = fraction** (quy ước lc0).
- **`--test-extract` / `--test-selfplay`:** check `sum(pi)` sửa thành **chỉ cộng π>0** (nước hợp lệ-đã-thăm) = 1.0.
- **`train.py policy_loss`:** masked CE — `masked_fill(pi<0, -inf)` trước log_softmax (mẫu số chỉ gồm nước hợp lệ); zero hóa logp của illegal để tránh `0·-inf=NaN`.
- **Hiệu quả thực đo:** loss policy giờ ở **thang đúng `~log(số nước hợp lệ)`**: với ~34 nước hợp lệ, masked loss **3.41 → 2.85** (thay vì unmasked ~7.7 chủ yếu "đè 10566 nước phi pháp"). Dữ liệu sinh ra: illegal=10566 (−1), legal-visited=9, legal-unvisited=25, sum(>0)=1.0000. Không NaN.
- **Tương thích ngược:** record FORMAT không đổi (vẫn float[10600]); chỉ giá trị illegal đổi 0→−1. Dữ liệu cũ (π=0 illegal) vẫn train được nhưng không có hiệu ứng mask — nên **sinh lại** dữ liệu bootstrap.
