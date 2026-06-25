# Implementation Plan — GUI Android (FairyZero Mobile)

> Mục tiêu: đưa bàn cờ FairyZero (đang chạy desktop bằng Flutter) lên **app Android chơi offline**,
> chạy engine **cục bộ trên điện thoại**. Tài liệu này vạch kiến trúc, thách thức, các mốc M0–M7,
> cách build, kỳ vọng hiệu năng, rủi ro, và các câu hỏi mở cần bạn chốt.

---

## Quyết định đã chốt (2026-06-25)

- **GPU**: CPU/XNNPACK trước; **chừa sẵn chỗ cho GPU**. Cụ thể: giữ trừu tượng provider trong
  `OnnxBackend` + tham số `provider` ở C ABI → thêm `"nnapi"`/`"gpu"` về sau **chỉ là một nhánh mới**,
  không đổi API, không động UI. (Xem M6.)
- **Model**: **giữ fp32**, không int8. Đánh đổi: bỏ qua tăng tốc NPU-int8 sau này; nhưng đường GPU
  Adreno tương lai dùng **fp16** (ORT tự hạ fp32→fp16 lúc nạp) nên **fp32 master vẫn hợp** — không mất gì.
- **Thiết bị**: Qualcomm **Snapdragon 6 Gen 3**, USB-debug. **Không root** → *không sao*, không cần root
  để `flutter run`/sideload/FFI.
- **Phạm vi**: **đúng bằng desktop** (chơi với máy, phong cấp, số chiếu, lật bàn, kéo/chạm).
- **Phân phối**: không lên store → **chỉ sideload**. Bản debug/profile của Flutter **tự ký** bằng khoá
  debug → cài lên máy mình không cần ký tay (chỉ Play Store mới cần ký release). Việc duy nhất: bật
  "cài app từ nguồn không xác định" một lần.
- **Thời điểm**: làm ngay, **song song việc sinh dữ liệu**; app dùng **net đời mới nhất**. ⇒ Nên cho
  app **nạp model từ một đường dẫn** (mặc định = asset đóng kèm; có thể *ghi đè* bằng file `adb push`
  vào thư mục app) → đổi net mỗi đời **không phải build lại app**.

---

## 0. Phạm vi & nguyên tắc

- **Tái sử dụng tối đa**: UI Flutter và lớp domain (board/move/game-controller) đã *độc lập nền tảng*.
  Phần phải làm mới gần như chỉ là **lớp engine** (cách app nói chuyện với engine trên Android).
- **Engine = nguồn chân lý luật chơi** (như desktop): app không cài lại luật, chỉ hỏi
  legalmoves/result/fen/bestmove.
- **Giữ giao thức UCI**: thay vì viết C ABI mới toanh, ta **bọc vòng lặp UCI hiện có** sau một
  C ABI mỏng. Lớp Dart bên trên gần như **giống hệt `UciProcessEngine`** của desktop, chỉ đổi
  *đường truyền* (FFI thay cho tiến trình con).
- **CPU trước, GPU sau**: bản chạy được/ổn định (XNNPACK, CPU-NEON) là mốc chính; GPU/NNAPI là
  thí nghiệm tăng tốc về sau (xem §7, và Câu hỏi mở).

---

## 1. Cái gì đã có / cái gì phải làm

| Thành phần | Trạng thái |
|---|---|
| UI Flutter (board_view, painter, promotion picker, checks digit, flip…) | ✅ Chạy desktop; **dùng lại gần như nguyên** cho Android |
| Lớp domain (BoardState/UciMove/GameController) | ✅ Độc lập nền tảng |
| `EngineService` (interface) + `UciProcessEngine` (desktop spawn .exe) | ✅ Có; Android cần **`NativeFfiEngine`** mới |
| Engine C++ (`custom_engine`) | ✅ Chạy x86 (Win/Linux); **chưa build cho Android ARM** |
| ONNX Runtime | ✅ Bản x86 (CPU/DML/CUDA); **cần bản Android arm64 (XNNPACK/NNAPI)** |
| Cầu nối Android (FFI, .so, asset model) | ❌ Phải làm |

**Bản chất công việc = 3 mảng:**
1. Làm engine **biên dịch được cho android-arm64** (gỡ phụ thuộc x86 + meson cross-file + NDK).
2. **ONNX Runtime Android** (chạy NN trên điện thoại).
3. **Cầu FFI**: bọc UCI sau C ABI → `libfairyzero.so` → `NativeFfiEngine` (Dart).

---

## 2. Kiến trúc

```
┌──────────────────────────────────────────────────────────────┐
│ Flutter (Dart)                                                │
│   UI widgets  ──  GameController  ──  EngineService (abstract) │
│                                          │            │        │
│                         UciProcessEngine │   NativeFfiEngine ◄─┼─ MỚI (Android)
│                         (desktop, .exe)  │   (FFI -> .so)      │
└──────────────────────────────────────────┼──────────────────-─┘
                                            │ dart:ffi
                              ┌─────────────▼──────────────┐
                              │ libfairyzero.so (arm64-v8a)│
                              │   C ABI: fz_create/send/   │
                              │          poll/destroy      │
                              │   └─ UCI engine (tái dùng) │
                              │        ├─ MCTS search       │
                              │        ├─ movegen (FSF)     │
                              │        └─ OnnxBackend ──────┼──► libonnxruntime.so
                              └────────────────────────────┘        (XNNPACK / NNAPI)
```

Cả `libfairyzero.so` lẫn `libonnxruntime.so` nằm trong `android/app/src/main/jniLibs/arm64-v8a/`;
Dart nạp bằng `DynamicLibrary.open("libfairyzero.so")`.

---

## 3. Thách thức cốt lõi & quyết định thiết kế

### 3.1 Android không cho spawn tiến trình → dùng FFI + C ABI bọc UCI
Desktop: GUI mở `custom_engine.exe` rồi nói UCI qua stdin/stdout. **Android cấm** chạy file thực thi
riêng. Giải pháp: biên dịch engine thành **thư viện .so** và gọi qua **dart:ffi**.
- Refactor nhỏ trong `uci_nn_engine.cc`: tách phần **dispatch một dòng lệnh** ra hàm
  `HandleLine(const std::string&)` (hiện đang nằm trong vòng `while(getline(cin))`).
- `Send()` (đang `cout << ... << flush`) → đẩy vào **hàng đợi output** thay vì stdout.
- `fz_send()` đẩy lệnh vào engine; `fz_poll()` lấy từng dòng output ra cho Dart.

### 3.2 Phụ thuộc x86 (AVX2/intrinsics) → NEON/scalar
Quét mã (đã làm): bề mặt cần xử lý **nhỏ**:
- `lczero_chess/neural/onnx_backend.cc`: `avx2_exp_approx` + `avx2_softmax` (xử lý output policy).
  → Thêm **bản scalar fallback** dưới `#ifdef __aarch64__` (hoặc NEON). *Chi phí ~0%* vì xử lý output
  chỉ chiếm ~0% thời gian (đã đo).
- `lczero_chess/utils/mutex.h`: `_mm_pause()` → `asm volatile("yield")` cho ARM.
- `chess/{bitboard.h,types.h,misc.cpp,nnue/*}` (lõi Stockfish): **vốn đã ARM-portable** — Stockfish
  chạy trên Android sẵn (có path NEON/scalar qua `#ifdef` của nó). Chỉ cần **không truyền cờ x86**.
- `meson.build`: hiện ép `/arch:AVX2` (MSVC) / `-mavx2 -mfma` (GCC). → Thêm nhánh **theo kiến trúc**:
  nếu host là `aarch64` thì dùng `-march=armv8-a` (+NEON sẵn có), KHÔNG truyền cờ AVX2.
- `-DPRECOMPUTED_MAGICS` đã bật → **không cần PEXT** (vốn là rào ARM lớn nhất, ta đã tránh từ đầu). 👍

### 3.3 ONNX Runtime cho Android
- Lấy **onnxruntime-android** (AAR/prebuilt) cho `arm64-v8a`: cung cấp `libonnxruntime.so` + headers.
- **EP (execution provider)**:
  - **XNNPACK** (CPU, tối ưu NEON) — *mặc định, ổn định, đa luồng*. Mốc chính.
  - **NNAPI** (uỷ quyền cho NPU/GPU/DSP qua Android Neural Networks API) — *tăng tốc tuỳ máy*, hay
    rớt về CPU cho conv; coi là **thí nghiệm** ở M6.
- `OnnxBackend::InitializeSession` cần thêm nhánh provider `xnnpack`/`nnapi` (giống cách đã có
  cpu/cuda/dml), biên dịch có điều kiện theo nền tảng.

### 3.4 Nạp model từ asset trong APK
File `.onnx` đóng trong `assets/` của app (chỉ đọc, không phải đường dẫn hệ thống). Hai cách:
- (Đơn giản) Lúc khởi động, **copy asset ra thư mục ghi được** của app
  (`getApplicationSupportDirectory()`), rồi truyền *đường dẫn* đó cho engine (đúng API hiện tại
  `weights_path`).
- (Gọn hơn) Thêm API **nạp từ buffer bytes** (`Ort::Session` từ mảng) để khỏi copy. Để sau nếu cần.

### 3.5 Bất đồng bộ (`go` → `info`/`bestmove`) qua FFI
`go` chạy search ở thread khác, phát `info`/`bestmove` bất đồng bộ. Hai lựa chọn truyền ra Dart:
- **(Chọn) Polling**: Dart định kỳ gọi `fz_poll()` lấy dòng output (đơn giản, không đụng chạm
  threading FFI). Một `Timer`/`Stream` bơm vào đúng pipeline mà `UciProcessEngine` đang dùng.
- (Nâng cao) `NativeCallable.listener` để native gọi ngược Dart — nhanh hơn nhưng phức tạp về thread.
  Để dành nếu polling không đủ mượt.

---

## 4. C ABI đề xuất (`fairyzero_ffi.h`)

```c
// Tất cả chuỗi là UTF-8, '\0'-terminated. Handle là con trỏ mờ.
void*  fz_create(const char* model_path, const char* provider); // "xnnpack"|"nnapi"|"cpu"
void   fz_send(void* h, const char* uci_line);    // vd "position startpos moves e2e4", "go nodes 200"
int    fz_poll(void* h, char* out, int out_cap);  // lấy 1 dòng output; trả độ dài, 0 nếu rỗng
void   fz_destroy(void* h);
```
- `fz_create`: dựng engine + nạp model (đồng bộ; trả handle hoặc NULL nếu lỗi).
- `fz_send`: đẩy một dòng UCI vào hàng đợi input → `HandleLine`.
- `fz_poll`: pop một dòng từ hàng đợi output (thread-safe). Dart gọi lặp tới khi trả 0.
- Toàn bộ logic UCI (uci/isready/setoption/position/go/stop/legalmoves/result/fen/quit) **tái dùng**.

`NativeFfiEngine` (Dart) implement `EngineService` đúng các method desktop đang có
(`start/newGame/applyMove/legalMoves/currentFen/gameResult/bestMove/dispose`), nhưng đẩy/nhận qua
`fz_send`/`fz_poll` thay vì pipe tiến trình.

---

## 5. Các mốc (M0 → M7)

> Mỗi mốc có **tiêu chí hoàn thành (DoD)** rõ ràng để bạn nghiệm thu từng bước.

### M0 — Flutter Android dựng & chạy khung (chưa engine)
- Bật target Android cho project `gui` (đã có cấu trúc Flutter). Cài Android SDK/NDK, chấp nhận license.
- Chạy UI-only trên **emulator hoặc máy thật** (bàn cờ tĩnh hiện ra, chạm/kéo hoạt động ở mức UI).
- **DoD:** `flutter run -d <android>` mở app, thấy bàn cờ; engine tạm là stub trả `bestmove 0000`.

### M1 — Engine ARM-portable (biên dịch cho android-arm64)
- Thêm **scalar fallback** cho `avx2_exp_approx`/`avx2_softmax` (`#ifdef __aarch64__`).
- `mutex.h`: `_mm_pause` → `yield` cho ARM.
- `meson.build`: cờ theo kiến trúc (không AVX2 trên aarch64; bật NEON của Stockfish).
- Viết **meson cross-file** `aarch64-linux-android` (tham khảo `lc0/lc0-master/cross-files/`), trỏ
  clang/llvm của NDK.
- **DoD:** engine biên dịch sạch cho `aarch64-linux-android` thành **thư viện tĩnh** (chưa cần ORT —
  có thể tạm stub backend), `--test-perft`/`--test-rules` chạy trên emulator/máy ARM cho PASS.

### M2 — ONNX Runtime Android + inference trên máy
- Lấy `onnxruntime-android` (arm64) + headers; thêm provider **xnnpack** vào `OnnxBackend`.
- Liên kết engine với `libonnxruntime.so`; chạy một inference thật trên thiết bị.
- **DoD:** trên máy thật, nạp `.onnx` và `--test-nn`/một eval đơn chạy đúng (output policy/value hợp lệ).

### M3 — C ABI + build `libfairyzero.so`
- Refactor `uci_nn_engine.cc`: tách `HandleLine`, đổi `Send()` sang hàng đợi output; thêm hàng đợi input.
- Viết `fairyzero_ffi.cc` (4 hàm §4); build **`libfairyzero.so` (arm64-v8a)** kèm phụ thuộc ORT.
- **DoD:** một test C nhỏ (hoặc adb shell) gọi `fz_create → fz_send("position…") → fz_send("go nodes 50")
  → fz_poll` ra được `bestmove`.

### M4 — Cầu Dart FFI (`NativeFfiEngine`)
- Khai báo binding dart:ffi cho 4 hàm; viết `NativeFfiEngine implements EngineService`, bơm output
  qua polling vào đúng pipeline `GameController` đang dùng.
- Chọn engine theo nền tảng: desktop→`UciProcessEngine`, Android→`NativeFfiEngine`.
- **DoD:** chạy headless (như `m2_smoke.dart` nhưng FFI) lấy được legalmoves + bestmove.

### M5 — Đóng gói model + ván chơi đầu tiên trên điện thoại
- Bỏ `.onnx` vào `assets/`; lúc khởi động copy ra thư mục ghi được, truyền path cho `fz_create`.
- Ráp UI + engine: **chơi trọn một ván với máy trên thiết bị thật**.
- **DoD:** mở app → chơi với máy được; phong cấp, số chiếu, lật bàn hoạt động như desktop.

### M6 — Tăng tốc GPU (tuỳ chọn, fp16): NNAPI → Adreno / Hexagon
- Thêm provider **NNAPI** (uỷ quyền **Adreno GPU / Hexagon NPU** của Snapdragon 6 Gen 3) vào
  `OnnxBackend` — nhờ "chỗ chừa sẵn" ở §0, đây chỉ là một nhánh provider mới.
- Adreno chuộng **fp16** → ORT tự hạ fp32→fp16 lúc chạy (**giữ nguyên model fp32 gốc**, không int8).
- **Fallback XNNPACK** nếu NNAPI chậm/không phủ hết op (đặc tính conv hay rớt CPU).
- **DoD:** so nps **XNNPACK-fp32 (CPU)** vs **NNAPI-fp16 (GPU)** trên máy thật; chọn cái nhanh hơn,
  vẫn giữ fallback an toàn. *(Không có hạng mục int8 — giữ độ mạnh nguyên bản theo yêu cầu.)*

### M7 — Hoàn thiện & đóng gói APK
- Khoá hướng màn hình/tỉ lệ bàn cờ cho mobile; icon; màn hình chờ "đang nạp model".
- Build **APK release** (ký debug để sideload là đủ ban đầu).
- **DoD:** một file `.apk` cài được lên máy, chạy offline, chơi mượt.

---

## 6. Build: meson cross-file + NDK + tích hợp Flutter

- **Cross-compile engine**: `meson setup build-android --cross-file cross/aarch64-linux-android.txt`
  với compiler = `aarch64-linux-android<API>-clang++` của NDK. Output `.so`/`.a`.
- **Liên kết ORT**: thêm `libonnxruntime.so` (arm64) + include dir vào meson deps.
- **Đưa vào app**: copy `libfairyzero.so` + `libonnxruntime.so` vào
  `gui/android/app/src/main/jniLibs/arm64-v8a/`. Flutter/Gradle tự đóng gói vào APK.
- **ABI**: bắt đầu chỉ **arm64-v8a** (mọi điện thoại đời mới); thêm `armv7a`/`x86_64` (emulator) sau nếu cần.

---

## 7. Hiệu năng kỳ vọng & đòn bẩy

- Net hiện tại (12b×144) trên 1 nhân ARM ≈ **chậm hơn 1 nhân desktop ~2–4×** → ~**8–15 eval/giây/nhân**;
  XNNPACK đa luồng (4–8 nhân) → vài chục eval/giây. Ở **visits thấp (100–400)**: vài giây/nước — **chơi được**.
- **Đòn bẩy lớn nhất cho phone = int8 quantization** (M6): nhanh đáng kể + model nhẹ (~¼ kích thước).
- GPU/NNAPI: *có thể* nhanh hơn cho conv, nhưng **tuỳ chip** (Snapdragon/MediaTek khác nhau) và hay
  rớt CPU. Đừng kỳ vọng chắc thắng; coi là bonus.
- Chỉnh `--visits`/movetime trong app để cân bằng độ mạnh ↔ thời gian nghĩ.

---

## 8. Rủi ro & giảm thiểu

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| ORT Android không hỗ trợ một op trong net | Trung bình | Dùng XNNPACK (phủ rộng); nếu kẹt, đơn giản hoá net/op khi export |
| Build NDK + meson cross trục trặc | Trung bình | Bám cross-file mẫu của lc0; cô lập M1 (build engine không-ORT trước) |
| Threading FFI (callback) gây crash | Thấp | Dùng **polling** thay callback; tránh gọi Dart từ native thread |
| Hiệu năng quá chậm để chơi | Trung bình | Visits thấp + int8 (M6); chấp nhận "đủ chơi" không phải "đủ mạnh" |
| Kích thước APK lớn (ORT + model ~30–40MB) | Thấp | int8 model; chỉ đóng arm64; bật minify |

---

## 9. Kiểm thử

- **Tái dùng** các `--test-*` của engine (perft/rules/ep/encoder/policy/nn) **chạy trên ARM** ở M1/M2 —
  bảo đảm luật/encoder không lệch khi đổi kiến trúc (đặc biệt phần SIMD fallback).
- `--audit-generation` chạy trên ARM: khẳng định movegen ARM == raw FSF.
- So **một eval** giữa desktop và Android (cùng input) → policy/value khớp (trong sai số float) →
  chứng minh scalar/NEON fallback đúng.
- Test FFI headless (Dart) trước khi ráp UI.

---

## 10. Câu hỏi mở (✅ đã trả lời 2026-06-25 — xem "Quyết định đã chốt" ở đầu file)

1. **Ưu tiên GPU tới mức nào?** Tôi đề xuất *CPU/XNNPACK trước* (chắc ăn, mọi máy), NNAPI/GPU là M6
   (bonus, kén máy). Bạn OK theo thứ tự này, hay muốn ép GPU ngay từ đầu (chấp nhận phức tạp & kén thiết bị)?
2. **Lượng tử hoá int8?** Cho phép ship model int8 (nhanh hơn nhiều trên phone, mất *chút* lực) hay
   phải giữ fp32 nguyên bản?
3. **Máy test:** bạn có điện thoại Android bật USB-debug để `flutter run` lên không? **Chip gì**
   (Snapdragon/MediaTek/Exynos)? — ảnh hưởng NNAPI/QNN và kỳ vọng tốc độ.
4. **Phạm vi bản đầu:** đúng bằng desktop (chơi với máy, phong cấp, số chiếu, lật bàn), hay tối giản
   trước (chỉ chơi được) rồi thêm dần?
5. **Phân phối:** chỉ cần **APK sideload** cho bạn dùng, hay tính lên Play Store (cần ký, chính sách,
   nhiều ABI…)?
6. **Thời điểm:** làm ngay song song việc sinh dữ liệu, hay để khi nào mạng đủ mạnh (vài đời nữa) rồi
   mới đóng app cho "đáng"? (App dùng net hiện tại vẫn chơi được, chỉ là chưa mạnh.)

---

*Ghi chú: kế hoạch này tái dùng ~90% UI/domain Flutter và toàn bộ logic UCI/engine; công việc thực chất
là lớp cầu nối Android (FFI + .so + ORT-mobile) + gỡ vài phụ thuộc x86 nhỏ. Rào "AVX2" thực ra hẹp vì
movegen đã dùng PRECOMPUTED_MAGICS (không PEXT) và phần AVX2 tự viết chỉ ở xử lý output (~0% thời gian).*
