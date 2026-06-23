# Walkthrough T8.4 + T8.6 — Bản portable tất-cả-trong-một + Sách hướng dẫn

> Phạm vi: triển khai **T8.4** (đóng gói bản portable chạy trên Windows sạch) và **T8.6** (sách
> hướng dẫn `HUONG_DAN.md`) trong `implementation_plan phase T8.md`. Mục tiêu: một **thư mục
> duy nhất** copy-là-chạy, làm được **chơi / sinh dữ liệu / huấn luyện** trên **Windows (CPU)**
> lẫn **Colab (GPU)**, kèm tài liệu cho người không-dev.
> Ngày: 2026-06-20. Tiền đề: T8.1 (engine `--uci-nn`) đã xong.

---

## 0. Mục tiêu

Sau T8.1 ta đã có engine UCI chạy được, nhưng nó nằm rải rác trong cây mã nguồn + cần MSYS2 để
chạy (phụ thuộc DLL). T8.4/T8.6 biến nó thành **sản phẩm cầm tay**:
- Một thư mục `FairyZero/` chứa **đủ DLL** → chạy trên Windows **không cài MSYS2**.
- Kèm **mạng mồi**, **bộ Python huấn luyện**, **mã nguồn để build GPU trên Colab**, **launcher**.
- Kèm **sách hướng dẫn tiếng Việt** để bạn (hoặc người khác) tự dùng từ A→Z.

---

## 1. Tệp đã thêm

| Tệp | Vai trò |
|-----|---------|
| `scripts/package.ps1` | Script PowerShell dựng bản portable `dist/FairyZero/` |
| `scripts/play.bat` | Launcher: chạy engine UCI với mạng mặc định |
| `python/requirements.txt` | Thư viện Python cần cài (numpy/torch/onnx/onnxruntime) |
| `HUONG_DAN.md` | Sách hướng dẫn (chơi / sinh / huấn luyện / danh mục siêu tham số) |

---

## 2. Khảo sát then chốt trước khi đóng gói

### 2.1. Phụ thuộc DLL của `custom_engine.exe` (cho Windows sạch)
Chạy `ldd build/custom_engine.exe` cho thấy 6 DLL phải đi kèm:
```
onnxruntime.dll                 (từ build/, ~10 MB)
onnxruntime_providers_shared.dll(từ third_party win pkg)
libstdc++-6.dll                 (MSYS2 ucrt64)
libgcc_s_seh-1.dll              (MSYS2 ucrt64)
libwinpthread-1.dll             (MSYS2 ucrt64)
zlib1.dll                       (MSYS2 ucrt64)
```
`ucrtbase.dll` lấy từ `System32` (có sẵn trên mọi Windows 10/11) → **không cần** đóng gói.
Vì exe build bằng **MSYS2 ucrt64 g++**, nó cần 4 DLL runtime ucrt64; thiếu là máy người khác
không chạy được. Đây là điểm mấu chốt của "chạy trên Windows sạch".

### 2.2. Biến thể được NHÚNG trong code → không cần `variant.ini`
`setup_custom_variant()` định nghĩa biến thể bằng một chuỗi `ini` **inline** (raw string trong
`main.cc`), không đọc tệp ngoài. Nên bundle **không cần** `variant.ini` — gọn hơn plan ban đầu.

---

## 3. T8.4 — `scripts/package.ps1`

### 3.1. Bản portable sinh ra
```
dist/FairyZero/
├─ custom_engine.exe            ← engine (chơi + sinh dữ liệu)
├─ onnxruntime.dll + 5 .dll     ← đủ runtime cho Windows sạch
├─ play.bat                     ← launcher
├─ models/seed.onnx (+ .pt)     ← mạng mồi (tự sinh bằng make_seed.py nếu không truyền -Model)
├─ python/  (*.py + requirements.txt)
├─ engine_src/ (src/ + meson.build + meson_options.txt)   ← để build bản GPU trên Colab
├─ scripts/colab_setup.sh
├─ VERSION.txt                  ← ngày build + git hash + mạng
└─ HUONG_DAN.md
```

### 3.2. Tham số & logic
```
powershell -ExecutionPolicy Bypass -File scripts\package.ps1 [tùy chọn]
  -OutDir     thư mục ra (mặc định dist\FairyZero)
  -Model      .onnx muốn nhúng làm seed (mặc định: tự sinh qua make_seed.py)
  -Python     python.exe để sinh seed (mặc định: tự dò Python313)
  -Ucrt64Bin  nơi lấy 4 DLL runtime (mặc định C:\msys64\ucrt64\bin)
  -Zip        đóng thêm <OutDir>.zip (Store)
```
Các bước script làm:
1. Tự xác định **gốc repo** = thư mục cha của `scripts/` (`Split-Path -Parent $PSScriptRoot`).
2. Kiểm tra đã build (`build/custom_engine.exe`, `build/onnxruntime.dll`) — chưa thì báo lỗi.
3. Dọn sạch `OutDir`, tạo cây thư mục.
4. Copy exe + 6 DLL; **cảnh báo** nếu thiếu DLL runtime (gợi ý chỉnh `-Ucrt64Bin`).
5. Seed model: nếu `-Model` thì copy (kèm `.pt` nếu có); nếu không thì **gọi `make_seed.py`** sinh.
6. Copy `python/*.py` + `requirements.txt`.
7. Copy `src/` + `meson.build` + `meson_options.txt` vào `engine_src/` (để build trên Colab) +
   `scripts/colab_setup.sh`.
8. Copy `play.bat` + `HUONG_DAN.md`.
9. Ghi `VERSION.txt` (ngày, **git short hash**, mạng, ghi chú nền tảng).
10. In dung lượng; nếu `-Zip` thì `Compress-Archive`.

### 3.3. `play.bat`
```bat
custom_engine.exe --uci-nn --weights "%MODEL%"    REM MODEL mặc định = models\seed.onnx
```
Có kiểm tra tồn tại exe/model, `cd /d "%~dp0"` để DLL cạnh exe được tìm thấy, và in gợi ý cách
cắm GUI. Bấm đúp là vào phiên UCI; hoặc GUI tự viết trỏ thẳng tới `custom_engine.exe --uci-nn …`.

---

## 4. T8.6 — `HUONG_DAN.md`

Tài liệu tiếng Việt, từng bước, copy-paste được, cho người **không lập trình**. Bố cục:

- **Mục 0:** bản portable có gì.
- **A. Chơi với AI:** cách nhanh (`play.bat`); **quy ước nước đi 10×10** (cột a–j, hàng 1–10,
  **hàng 10 hai chữ số**, phong cấp hậu tố quân); một ván qua lệnh UCI; bảng `setoption`
  (WeightsFile/Visits/Threads/Provider/…); điều khiển thời gian (`nodes`/`movetime`/`infinite`+`stop`);
  cách cắm **GUI tự viết**.
- **B. Sinh dữ liệu tự chơi:** lệnh Windows; bật **resign** tăng tốc; gom `.zip` bằng `archive.py`.
- **C. Huấn luyện:** cài thư viện; `train.py` một đời; `loop.py` nhiều đời; **các bước Colab GPU**
  (đổi runtime → `colab_setup.sh` build → `loop.py --provider cuda`); giải thích `.onnx` vs `.pt`.
- **D. Danh mục siêu tham số:** 3 bảng (chơi `setoption` · sinh `--selfplay` · huấn luyện
  `train.py`/`loop.py`) kèm mặc định & ý nghĩa — để tra nhanh khi tinh chỉnh.
- **E. Khắc phục sự cố:** thiếu DLL, `bestmove 0000`, `go infinite` "đứng im", thiếu thư viện,
  cách tự kiểm tra engine (`--test-uci`).

> Danh mục siêu tham số phản ánh **đúng** những cờ hiện có (T1–T8.1). Phần mở khóa thêm siêu
> tham số kiểu lc0 sẽ cập nhật ở T8.3.

---

## 5. Kiểm thử (đã chạy thật)

### 5.1. Dựng bundle
`package.ps1 -OutDir <temp> -Python <py>` → tự sinh seed (make_seed.py PASS verify ONNX) →
**bundle 83.1 MB**. Liệt kê: đủ 6 DLL, `models/seed.onnx(+.pt)`, `python/`, `engine_src/`,
`scripts/colab_setup.sh`, `play.bat`, `VERSION.txt`, `HUONG_DAN.md`.

### 5.2. ⭐ Chạy standalone trên "Windows sạch"
Tháo `msys64` khỏi `PATH` rồi chạy **exe trong bundle**:
```
--test-uci  →  move round-trip 52/52 ... [PASS]
```
→ Exe **tự tìm DLL trong thư mục của nó** (Windows ưu tiên thư mục exe), không cần MSYS2.
Đây là tiêu chí "chạy trên máy Windows sạch" — **đạt**.

### 5.3. Chơi thật từ bundle
Phiên UCI dùng `custom_engine.exe --uci-nn --weights models/seed.onnx` trong bundle:
```
uciok / readyok
bestmove c2a4   (Trắng, go nodes 60)
bestmove c9a7   (Đen, sau b3b4)
```
`VERSION.txt` đúng (ngày, git `564332d`, model seed).

---

## 6. Lưu ý kỹ thuật

- **DLL phải nằm CÙNG thư mục exe.** Bundle đặt sẵn 6 DLL ở cấp gốc, cạnh `custom_engine.exe` →
  Windows nạp đúng dù PATH không có MSYS2.
- **`-Ucrt64Bin`:** nếu MSYS2 cài chỗ khác, truyền đường dẫn `...\ucrt64\bin` để script copy đúng
  4 DLL runtime; script cảnh báo nếu thiếu.
- **Colab dùng `engine_src/`:** bản exe đi kèm chỉ chạy CPU trên Windows. Muốn GPU thì trên Colab
  build lại từ `engine_src/` bằng `colab_setup.sh` (tự tải onnxruntime Linux GPU). Vì vậy bundle
  **không** kèm `third_party` Windows (thừa cho Colab, và Windows đã có exe dựng sẵn).
- **`VERSION.txt` có BOM** (PowerShell 5.1 `Set-Content -Encoding utf8`) — vô hại, vẫn đọc tốt.

---

## 7. Cách dùng

```powershell
# 1. Build engine (nếu chưa):  ninja -C build
# 2. Đóng gói:
powershell -ExecutionPolicy Bypass -File scripts\package.ps1            # -> dist\FairyZero
powershell ... -File scripts\package.ps1 -Model models\model_gen5.onnx -Zip   # nhúng mạng + zip
# 3. Copy thư mục dist\FairyZero đi đâu cũng chạy; bấm đúp play.bat để chơi.
```

---

## 8. Trạng thái & bước kế tiếp

**T8.4 + T8.6 HOÀN TẤT** — có bản portable chạy độc lập trên Windows (đã kiểm chứng PATH sạch) và
sách hướng dẫn đầy đủ. Còn lại theo thứ tự plan:
- **T8.2:** `info score cp/wdl + pv + multipv`, time-control `wtime/btime`, ponder.
- **T8.3:** mở khóa toàn bộ siêu tham số kiểu lc0 (passthrough `setoption`/`--search-opt`).
- **T8.5:** kiểm chứng đường Colab (build + gen + train GPU) ngay trong bundle.
- **T8.x:** `--play` ASCII, combo `Skill`, tái dùng cây, mate…

Thứ tự: **T8.1 ✓ → T8.4 ✓ → T8.6 ✓ → T8.2 → T8.3 → T8.5 → T8.x**.
