# Walkthrough — Phase T6.5: Port engine sang Linux / CUDA cho Google Colab

> Ngày: 2026-06-20 · Dự án: FairyZero (`custom_engine`) — biến thể cờ 10×10.
> Phạm vi: milestone **T6.5** trong `implementation_plan phase training_1.md` — build hệ thống đa nền tảng + bật CUDA Execution Provider để chạy self-play/train trên Colab GPU.
> DoD (plan): compile + test 100% pass trên Colab GPU.
> Trạng thái: ✅ **Mã & build-system SẴN SÀNG cho Linux/CUDA** (đã verify build Windows KHÔNG vỡ — phần tôi kiểm được từ Windows). ⏳ **Bước chạy thật trên Colab GPU do bạn thực hiện** bằng script đã chuẩn bị (`scripts/colab_setup.sh`).

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

`Stockfish::Bitboard` trên **Windows/MinGW** là `struct {b64[2]}` (vì `IS_64BIT` không định nghĩa), còn trên **Linux/GCC 64-bit** thường là `unsigned __int128` — **hai biểu diễn nội bộ KHÁC nhau**. Tuy nhiên:
- Mọi truy cập bit đi qua thao tác trừu tượng (`pop_lsb`, `square_bb`, `& / >>`) nên **kết quả logic giống hệt**.
- Quan trọng nhất: serialize record dùng **split tường minh** `out[0]=m & low64; out[1]=m >> 64` (đã làm ở T5) — **độc lập biểu diễn** → file `.gz` **bit-tương thích Windows↔Linux**.
→ Dữ liệu sinh trên Colab và đọc bằng Python (hoặc ngược lại) khớp nhau. (Khi chạy Colab, nên chạy lại `--emit-roundtrip` + `test_roundtrip.py` để xác nhận trên đúng môi trường đó.)

---

## 3. Đã verify (từ Windows) & cần verify (trên Colab)

| Hạng mục | Trạng thái |
|----------|-----------|
| Build Windows sau khi sửa meson/backend/main | ✅ link OK, `--test-extract` PASS (CPU profile) |
| Cờ `--provider/--fixed-batch` không vỡ Windows (mặc định cpu) | ✅ |
| CUDA EP code biên dịch khi `USE_CUDA` (Linux) | ⏳ cần build Colab |
| Test suite 100% pass trên Colab GPU | ⏳ chạy `colab_setup.sh` |
| Self-play GPU (`provider=cuda`) sinh dữ liệu | ⏳ chạy trên Colab |

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
| Split bit tường minh (từ T5) | Dữ liệu `.gz` bit-tương thích dù Bitboard là struct (Win) hay __int128 (Linux) |

---

## 6. Trạng thái & việc tiếp theo

- **CHƯA commit.** File đổi/mới: `meson.build`, `meson_options.txt`, `src/lczero_chess/neural/onnx_backend.cc`, `src/main.cc`, `scripts/colab_setup.sh` (MỚI).
- **Cần bạn chạy trên Colab** để hoàn tất DoD (test 100% pass trên GPU). Nếu gặp lỗi CUDA/cuDNN version, chỉnh `ORT_VER` cho khớp môi trường Colab.
- **Lưu ý hiệu năng GPU:** mỗi ván self-play hiện gom batch riêng; để đạt throughput "hàng chục lần" của GPU, bước tối ưu tiếp theo là **lớp gom-batch-eval xuyên ván** (nhiều ván chia sẻ một hàng đợi inference) — đây là tinh chỉnh thuộc T7/optimization, không chặn T6.5.
- **Bước tiếp theo:** **T7** — khép vòng lặp AlphaZero đầy đủ (self-play → train → model mới → lặp; rolling window, diff_focus), chạy chủ yếu trên Colab GPU.

---

## 7. Cách kiểm lại trên Windows (đảm bảo không hồi quy)
```powershell
cd D:\chess_variant\custom_engine
meson compile -C build
.\build\custom_engine.exe --test-extract --weights python\model_gen0.onnx   # CPU profile vẫn PASS
```
