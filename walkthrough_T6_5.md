# Walkthrough — Phase T6.5: Port engine sang Linux / CUDA cho Google Colab

> Ngày: 2026-06-20 · Dự án: FairyZero (`custom_engine`) — biến thể cờ 10×10.
> Phạm vi: milestone **T6.5** trong `implementation_plan phase training_1.md` — build hệ thống đa nền tảng + bật CUDA Execution Provider để chạy self-play/train trên Colab GPU.
> DoD (plan): compile + test 100% pass trên Colab GPU.
> Trạng thái: ✅ **HOÀN TẤT** — đã chạy thật trên Colab (Tesla T4, CUDA 12.8): build Linux + **toàn bộ test PASS** + **self-play trên GPU chạy được** (~0.79s/ván, nhanh ~10× so với CPU). Hành trình qua 4 lần chạy Colab (xem §8). Build Windows vẫn xanh suốt.

---

## 0. Bối cảnh & ràng buộc thực tế

T6.5 là milestone **chạy trên Colab** (Linux + CUDA). Tôi làm việc trên Windows nên **không build/test Linux được tại chỗ**. Vì vậy deliverable là:
1. **Build-system đa nền tảng** (`meson.build` + `meson_options.txt`) — Windows dùng ORT CPU bundled, Linux dùng ORT GPU.
2. **CUDA Execution Provider** thật trong `onnx_backend.cc` (gated `#ifdef USE_CUDA` → Windows không ảnh hưởng).
3. **Cờ chọn provider** (`--provider cuda --fixed-batch N`) cho self-play để dùng GPU.
4. **Script Colab** tự động (`scripts/colab_setup.sh`): tải ORT GPU → build → test → smoke GPU.
5. **Bảo chứng:** build Windows vẫn xanh sau mọi thay đổi (đã verify).

---

## 1. Các thay đổi

### 1.1. `[MODIFY] meson_options.txt` — 2 option mới
- `onnxruntime_dir` (string, mặc định `third_party/onnxruntime-linux-x64-gpu-1.18.0`) — gốc ORT cho build non-Windows.
- `use_cuda` (boolean, mặc định `false`) — bật CUDA EP.

### 1.2. `[MODIFY] meson.build` — đa nền tảng
- **Gốc ORT theo nền tảng:**
  ```meson
  if host_machine.system() == 'windows'
    onnx_root = 'third_party/onnxruntime-win-x64-1.18.0'
  else
    onnx_root = get_option('onnxruntime_dir')
  endif
  ```
  → `inc_dirs` dùng `onnx_root / 'include'`; `onnx_lib_dir = .../onnx_root/'lib'`. Mỗi nền tảng dùng **header + thư viện của chính gói ORT của nó** (Linux ORT có thể khác version Windows mà không sao).
- **CUDA macro:** `if get_option('use_cuda') → add_project_arguments('-DUSE_CUDA')`.
- **DLL copy** chỉ chạy trên Windows (đã có sẵn). Linux không cần copy.
- **rpath Linux:** `executable(..., kwargs: {'build_rpath': onnx_lib_dir})` (chỉ non-Windows) → binary tự tìm `libonnxruntime.so`, không cần `LD_LIBRARY_PATH` (vẫn để LD_LIBRARY_PATH làm dự phòng trong script).

### 1.3. `[MODIFY] src/lczero_chess/neural/onnx_backend.cc` — bật CUDA EP
Thay placeholder (vốn comment) bằng đăng ký CUDA EP thật, **gated**:
```cpp
#ifdef USE_CUDA
    if (provider_ == "cuda") {
        OrtCUDAProviderOptions cuda_options{};
        cuda_options.device_id = 0;
        session_options_.AppendExecutionProvider_CUDA(cuda_options);
    }
#else
    std::cout << "WARNING: provider requested but built WITHOUT USE_CUDA -> CPU EP";
#endif
```
- Backend vốn đã parse `provider=` từ backend-options và có sẵn nhánh "GPU profile" (`EnableMemPattern` + `AddFreeDimensionOverrideByName("batch", fixed_batch)`), và load path đã đa nền tảng (`#ifdef _WIN32` wpath / else c_str). → Chỉ cần điền EP.
- **Windows:** `USE_CUDA` không định nghĩa → nhánh `#else` (no-op cảnh báo), không đụng symbol CUDA → build/CPU như cũ.

### 1.4. `[MODIFY] src/main.cc` — cờ provider cho self-play
- Thêm `--provider cpu|cuda` và `--fixed-batch N`. Dựng backend-options:
  - `cuda` → `"provider=cuda,fixed_batch=N"` (kích hoạt GPU profile + override trục `batch` của model — khớp model export trục `"batch"`).
  - `cpu` → `"threads=N"` (như cũ).

### 1.5. `[NEW] scripts/colab_setup.sh`
Một lệnh chạy trên Colab: `!bash custom_engine/scripts/colab_setup.sh`. Các giai đoạn:
1. `pip install meson ninja`.
2. Tải `onnxruntime-linux-x64-gpu-<ver>.tgz` vào `third_party/` (biến `ORT_VER/ORT_PKG/ORT_URL` chỉnh được).
3. `meson setup build-linux -Duse_cuda=true -Donnxruntime_dir=...` + `ninja`.
4. Chạy **bộ test** (board/policy/perft/bits/rules/adapter/nn/trainingdata).
5. Sinh seed gen-0 (Python) + **smoke self-play GPU** (`--provider cuda`).

---

## 2. Tính tương thích dữ liệu xuyên nền tảng (đã lường trước)

`Stockfish::Bitboard` là `struct {b64[2]}` trên **CẢ Windows/MinGW lẫn Linux/GCC** (thực tế Colab xác nhận: macro `IS_64BIT` không được định nghĩa ở cả hai → nhánh struct, không phải `__int128`). Struct này có 2 toán tử chuyển đổi (`operator unsigned long long` + `operator unsigned`).
- **Hệ quả lúc build Linux:** `uint64_t` = `unsigned long` trên Linux (khác `unsigned long long` trên Windows) → `static_cast<uint64_t>(bitboard)` **nhập nhằng** (2 toán tử cùng khả thi). Đây là lỗi biên dịch ĐẦU TIÊN gặp trên Colab → sửa bằng ép qua `unsigned long long` trước (xem §8).
- **Tương thích dữ liệu:** mọi truy cập bit đi qua thao tác trừu tượng (`pop_lsb`, `& / >>`) + serialize dùng **split tường minh** (T5) → file `.gz` **bit-tương thích Windows↔Linux**.
→ **Đã xác nhận thực tế:** bit-level test E1 (120 ô serialize) PASS trên Colab Linux → dữ liệu khớp 2 nền tảng.

---

## 3. Đã verify

| Hạng mục | Trạng thái |
|----------|-----------|
| Build Windows (CPU profile) sau mọi thay đổi | ✅ link OK, `--test-extract` PASS |
| Build Linux trên Colab (GCC 11.4, `-Duse_cuda=true`) | ✅ link OK |
| Toàn bộ test C++ trên Colab (board/policy/perft/**bit E1+E2**/rules/adapter/nn/T1) | ✅ **100% PASS** |
| `make_seed.py` → `model_gen0.onnx` + verify I/O | ✅ PASS |
| CUDA EP nạp trên Colab (Tesla T4) | ✅ "CUDA Execution Provider appended (device 0)" |
| Self-play GPU (`provider=cuda`) sinh dữ liệu | ✅ 2 ván / 1.577s (**~0.79s/ván, ~10× CPU**) |

---

## 4. Cách chạy trên Colab

```python
# Colab cell:
!git clone <repo>   # hoặc mount Drive
!bash custom_engine/scripts/colab_setup.sh
```
> **Khớp CUDA:** ORT 1.18.0 GPU = CUDA 11.8. Nếu Colab dùng CUDA 12, đặt `ORT_VER` sang bản ORT có `.so` cuda12 (vd 1.20.x) trước khi chạy: `!ORT_VER=1.20.1 bash custom_engine/scripts/colab_setup.sh`. (Build Linux dùng header của chính gói ORT đó nên đổi version an toàn.)

Sinh dữ liệu + train (GPU):
```bash
LD_LIBRARY_PATH=third_party/$ORT_PKG/lib ./build-linux/custom_engine \
  --selfplay --games 1000 --parallel 2 --visits 200 \
  --provider cuda --fixed-batch 32 --weights python/model_gen0.onnx --out python/selfplay_data

python python/train.py --data python/selfplay_data --epochs 20 --batch 256 \
  --init-from python/model_gen0.pt --out python/model_gen1.onnx --pin-memory --workers 2
```

---

## 5. Bảng quyết định kỹ thuật & lý do

| Quyết định | Lý do |
|-----------|-------|
| `onnx_root` theo `host_machine.system()` | Mỗi nền tảng dùng gói ORT riêng (header+lib), version độc lập |
| CUDA EP gated `#ifdef USE_CUDA` | Windows không link symbol CUDA → không vỡ build CPU |
| `build_rpath` ORT lib trên Linux | Binary tự tìm `.so`, đỡ phải set `LD_LIBRARY_PATH` |
| `--provider cuda,fixed_batch=N` | Kích hoạt GPU profile + override trục batch tĩnh (khớp model `"batch"`) |
| Script Colab tham số hóa ORT | Người dùng khớp CUDA của Colab dễ dàng |
| Default ORT 1.20.1 (CUDA 12) | Colab GPU runtime hiện là CUDA 12.x; 1.18 (CUDA 11) lệch → fail |
| Thêm nvidia-* libs của torch vào `LD_LIBRARY_PATH` | CUDA EP tìm được `libcublasLt.so.12`/`libcudnn.so.9` mà torch CUDA12 mang theo |
| Cast qua `unsigned long long` rồi mới `uint64_t` | Tránh nhập nhằng `Bitboard→uint64_t` trên Linux (uint64_t=`unsigned long`) |
| Split bit tường minh (từ T5) | Dữ liệu `.gz` bit-tương thích (Bitboard là struct trên cả 2 nền tảng) |

---

## 6. Trạng thái & việc tiếp theo

- **CHƯA commit phần engine** (`meson.build`, `meson_options.txt`, `onnx_backend.cc`, `main.cc`); người dùng đã commit dần để chạy Colab. File mới: `scripts/colab_setup.sh`.
- ✅ **DoD T6.5 ĐẠT** — đã chạy thật trên Colab GPU (Tesla T4, CUDA 12.8): build + test 100% pass + self-play GPU.
- **Lưu ý hiệu năng GPU:** mỗi ván self-play hiện gom batch riêng; để đạt throughput tối đa của GPU, bước tối ưu tiếp theo là **lớp gom-batch-eval xuyên ván** (nhiều ván chia sẻ một hàng đợi inference) — tinh chỉnh thuộc T7/optimization, không chặn T6.5.
- **Bước tiếp theo:** **T7** — khép vòng lặp AlphaZero đầy đủ (self-play → train → model mới → lặp; rolling window, diff_focus). Chạy được trên **CẢ Windows (CPU) lẫn Colab (GPU)** — Colab nhanh hơn nhiều nên dùng cho khối lượng lớn.

---

## 8. Hành trình port Colab thực tế (4 lần chạy)

Phần khó của T6.5 là **port lần đầu sang Linux/CUDA**; mỗi lỗi đều là loại điển hình đa-nền-tảng (KHÔNG phải lỗi logic — phần logic/bit được bộ test canh giữ):

| Lần | Lỗi gặp | Nguyên nhân | Sửa |
|-----|---------|-------------|-----|
| 1 | `error: conversion from 'Bitboard' to 'uint64_t' is ambiguous` | `uint64_t`=`unsigned long` trên Linux ≠ `unsigned long long` trên Windows; struct Bitboard có 2 toán tử chuyển đổi | Ép qua `unsigned long long` trước rồi `uint64_t` (`training_extract.cc` + `main.cc`) |
| 2 | Build + test C++ **PASS**; `ModuleNotFoundError: No module named 'onnx'` | Colab có torch/numpy nhưng thiếu `onnx`/`onnxruntime` (Python) | `pip install onnx onnxruntime` trong script |
| 3 | `make_seed` PASS; `libcublasLt.so.11: cannot open` khi nạp CUDA EP | ORT 1.18 cần CUDA 11, Colab là **CUDA 12.8** | Default ORT → **1.20.1 (CUDA 12)** + thêm nvidia libs của torch vào `LD_LIBRARY_PATH` |
| 4 | — | — | ✅ **GPU chạy thật**: `CUDA Execution Provider appended` → 2 ván/1.577s |

> Bài học: bộ test toàn diện (perft/bit-level/round-trip) cho phép **phân biệt rõ lỗi port (build/version) với lỗi logic** — mọi lỗi ở đây đều thuộc loại đầu, sửa nhanh và yên tâm.

---

## 7. Cách kiểm lại trên Windows (đảm bảo không hồi quy)
```powershell
cd D:\chess_variant\custom_engine
meson compile -C build
.\build\custom_engine.exe --test-extract --weights python\model_gen0.onnx   # CPU profile vẫn PASS
```
