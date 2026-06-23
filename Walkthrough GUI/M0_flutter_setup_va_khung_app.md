# Walkthrough — GUI Mốc M0: Cài Flutter & dựng khung app chạy được

> Đợt chỉnh sửa: **2026-06-23**. Mục tiêu M0 (theo `implementation_plan_GUI.md` §11):
> *"Dựng khung Flutter chạy được cửa sổ trống trên Windows; parse cờ lệnh → `LaunchConfig`."*
> Tiêu chí hoàn thành: `flutter run -d windows` mở cửa sổ; in ra config đọc được.
>
> **Kết quả: M0 ✅ HOÀN TẤT** — build Windows thành công, chạy thật xác nhận cửa sổ mở + parse +
> in config đúng.

---

## 0. Tóm tắt nhanh (TL;DR)

| Việc | Kết quả |
|---|---|
| Cài Flutter SDK | `3.44.3 stable` (Dart 3.12.2) tại `D:\flutter`, đã thêm vào USER PATH |
| Điều kiện build Windows | Đủ: MSVC + CMake + Windows SDK 10.0.26100 (qua **VS Build Tools 2022**, không cần full Visual Studio) |
| Tạo project | `D:\chess_variant\gui` (package `fairyzero_gui`, chỉ platform windows) |
| Code M0 | `lib/config/launch_config.dart`, `lib/main.dart`, `test/widget_test.dart` |
| Kiểm thử | `flutter analyze` sạch · `flutter test` 2/2 pass · build Windows OK · chạy exe xác nhận |

---

## 1. Bối cảnh & quyết định nền tảng

Trước đợt này đã chốt (xem `implementation_plan_GUI.md`):
- **Stack:** Flutter (Dart) — vì là khung dễ học, *một bộ mã chạy cả `.exe` Windows lẫn app Android
  native*, dễ thêm tính năng phụ về sau.
- **Nối engine:** Kiểu A — GUI spawn `custom_engine.exe --uci-nn`, trao đổi bằng văn bản UCI qua
  pipe (chưa làm ở M0, là mốc M2).
- **Engine là trọng tài luật** — GUI không tự suy luật, sẽ hỏi `legalmoves`/`result` (mốc M1).

Người dùng chưa cài Flutter → đợt này tự cài giúp.

---

## 2. Kiểm tra môi trường

Lệnh kiểm tra phát hiện:

```
flutter : NOT FOUND
dart    : NOT FOUND
git     : 2.51.0  ✓
winget  : v1.28   ✓
Visual Studio : Build Tools 2022, v17.14   ✓ (có VC.Tools.x86.x64)
Disk    : D: 156.7GB free, C: 46.7GB free
```

Kiểm tra sâu các thành phần C++ mà Flutter Windows cần:

```
HAVE    Microsoft.VisualStudio.Workload.VCTools          (Build Tools)
HAVE    Microsoft.VisualStudio.Component.VC.Tools.x86.x64 (MSVC compiler)
HAVE    Microsoft.VisualStudio.Component.VC.CMake.Project (CMake)
HAVE    Microsoft.VisualStudio.Component.Windows10SDK
MISSING Microsoft.VisualStudio.Workload.NativeDesktop    (full VS workload — KHÔNG cần)
```

Windows SDK thực tế: **`10.0.26100.0`** (đầy đủ, có `ucrt\stdio.h`).

➡️ **Kết luận:** đủ toàn bộ điều kiện build Flutter Windows. Chỉ thiếu Flutter SDK.

---

## 3. Cài đặt Flutter

### 3.1 Tải SDK (git clone, chạy nền)
```bash
git clone -b stable https://github.com/flutter/flutter.git /d/flutter
```
Chọn `D:` vì còn nhiều dung lượng và project cũng ở `D:`. Clone đầy đủ (không `--depth`) để Flutter
nhận diện đúng phiên bản và `flutter upgrade` về sau hoạt động.

### 3.2 Bootstrap (lần chạy đầu tự tải Dart SDK + artifacts)
```powershell
& "D:\flutter\bin\flutter.bat" --version
# -> Flutter 3.44.3 • channel stable • Dart 3.12.2
```

### 3.3 Bật Windows desktop + tạo project
```powershell
& "D:\flutter\bin\flutter.bat" config --enable-windows-desktop --no-analytics
& "D:\flutter\bin\flutter.bat" create --platforms=windows --project-name fairyzero_gui --org com.fairyzero "D:\chess_variant\gui"
```
> Chỉ tạo platform `windows` cho gọn ở M0; Android sẽ thêm sau bằng
> `flutter create --platforms=android .` ở Giai đoạn 2.

### 3.4 Thêm Flutter vào PATH người dùng (vĩnh viễn)
Đã thêm `D:\flutter\bin` vào USER PATH ⇒ **terminal mở MỚI** sẽ gõ `flutter` trực tiếp được.
(Trong phiên đang chạy thì gọi bằng đường dẫn đầy đủ `D:\flutter\bin\flutter.bat`.)

---

## 4. Code đã viết (M0)

Cấu trúc thư mục liên quan:
```
D:\chess_variant\gui\
  lib\
    main.dart                  # điểm vào: đọc args -> in config -> mở cửa sổ
    config\launch_config.dart  # LaunchConfig: parse cờ lệnh (bất biến)
  test\widget_test.dart        # smoke test + test parse
```

### 4.1 `lib/config/launch_config.dart` — cấu hình từ cờ lệnh
Lớp **bất biến** đọc cờ lệnh **một lần** lúc khởi động. Đây là điểm mở rộng: thêm tính năng sau =
thêm trường vào đây.

Cờ lệnh hỗ trợ ở M0:

| Cờ | Ý nghĩa | Mặc định |
|---|---|---|
| `--engine <path>` | đường dẫn `custom_engine.exe` | `engine/custom_engine.exe` |
| `--model <onnx>` | file trọng số `.onnx` | (chưa đặt) |
| `--provider cpu\|dml\|cuda` | CPU hay GPU lượng giá | `cpu` |
| `--movetime <ms>` | thời gian máy nghĩ/nước | `5000` |
| `--visits <N>` | hoặc số visits/nước (ưu tiên) | — |
| `--black` / `--white` | người cầm Đen (lật bàn) / Trắng | Trắng |
| `--start-fen <FEN>` | thế cờ bắt đầu tuỳ chọn | startpos biến thể |

Điểm thiết kế:
- `LaunchConfig.fromArgs(List<String>)`: lặp args, đối số **lạ bị bỏ qua** (an toàn với wrapper của
  `flutter run --dart-entrypoint-args`).
- Provider không hợp lệ → ép về `cpu`. Không đặt cả `movetime` lẫn `visits` → dùng `movetime` mặc định.
- `toString()` in bảng config gọn để log + hiển thị.

### 4.2 `lib/main.dart` — điểm vào + cửa sổ M0
```dart
void main(List<String> args) {
  final config = LaunchConfig.fromArgs(args);
  print(config.toString());      // in ra terminal để kiểm tra
  runApp(FairyZeroApp(config: config));
}
```
- `M0Screen`: nền tối + tiêu đề "FairyZero — M0" + **preview bàn cờ 8×8** + bảng config (monospace).
- `_CheckerPreviewPainter` vẽ lưới 8×8 bằng **đúng hai màu chuẩn chess.com**, để xác nhận hằng số
  màu sẽ dùng lại cho `BoardPainter` ở M3:
  - ô sáng `light = Color(0xFFEEEED2)`
  - ô tối `dark  = Color(0xFF769656)`

### 4.3 `test/widget_test.dart` — thay test mặc định
File test auto-sinh còn tham chiếu `MyApp` (đã đổi tên) → thay bằng:
- **Smoke test:** dựng `FairyZeroApp`, kiểm tra hiện "FairyZero — M0" và "LaunchConfig:".
- **Test parse:** `--engine e.exe --model m.onnx --provider dml --visits 800 --black` → đúng giá trị;
  và mặc định (args rỗng) → `cpu` + movetime mặc định + cầm Trắng.

---

## 5. Kiểm thử & kết quả

### 5.1 Phân tích tĩnh
```powershell
flutter analyze    # -> No issues found!
```
(Đã sửa 2 loại cảnh báo trước đó: dấu `<>` trong doc comment → bọc khối ```; và lỗi `MyApp` trong
test cũ → viết lại test.)

### 5.2 Unit test
```
flutter test
00:01 +2: All tests passed!
```

### 5.3 Build Windows
```powershell
flutter build windows --debug
# √ Built build\windows\x64\runner\Debug\fairyzero_gui.exe
```
(Lần đầu ~100s vì biên dịch runner C++ + plugin.)

### 5.4 Chạy thật (mở ~6s rồi đóng), bắt stdout
Chạy với cờ mẫu `--engine engine\custom_engine.exe --model models\gen12.onnx --provider dml
--movetime 3000 --black`, kết quả in ra:
```
LaunchConfig:
  engine   = engine\custom_engine.exe
  model    = models\gen12.onnx
  provider = dml
  think    = 3000 ms/nuoc
  human    = Black (lat ban)
  startFen = (startpos mac dinh)
```
➡️ Cửa sổ mở được, parse cờ lệnh đúng, in config đúng → **đạt tiêu chí M0**.

---

## 6. Cách chạy lại (cho người dùng)

> Mở **terminal MỚI** để có PATH Flutter.

```powershell
cd D:\chess_variant\gui

# Dev (hot reload):
flutter run -d windows

# Dev kèm cờ lệnh:
flutter run -d windows --dart-entrypoint-args "--provider dml --movetime 3000 --black"

# Hoặc chạy exe đã build:
build\windows\x64\runner\Debug\fairyzero_gui.exe --provider dml --black
```

---

## 7. Trạng thái & bước tiếp theo

**Đã có:** khung Flutter chạy được trên Windows + `LaunchConfig` + cửa sổ + in config + màu bàn cờ
chess.com sẵn sàng cho M3.

**Chưa làm / cố ý hoãn:**
- Chưa nối engine (M2), chưa vẽ bàn cờ thật (M3).
- Chưa commit (theo thói quen người dùng tự commit). Lưu ý: `gui/` nằm ở `D:\chess_variant\gui`
  (NGOÀI thư mục `custom_engine`) — cần quyết đưa vào git/repo nào.
- Android: workload đủ cho Windows; Android toolchain còn thiếu cmdline-tools (Giai đoạn 2).

**Mốc kế tiếp — M1 (phần engine, độc lập Flutter):** thêm lệnh `legalmoves` + `result` vào
`src/app/uci_nn_engine.cc` (xem plan §5.2/§6). Đây là nền để M2 cho GUI spawn engine, lấy nước hợp
lệ và vẽ bàn.

---

## Phụ lục A — Vị trí quan trọng
- Flutter SDK: `D:\flutter` (bin: `D:\flutter\bin`)
- Project GUI: `D:\chess_variant\gui`
- Exe build: `D:\chess_variant\gui\build\windows\x64\runner\Debug\fairyzero_gui.exe`
- Kế hoạch tổng: `D:\chess_variant\implementation_plan_GUI.md`

## Phụ lục B — Thông tin phiên bản
- Flutter 3.44.3 stable · Dart 3.12.2 · DevTools 2.57.0
- Engine build C++: VS Build Tools 2022 (17.14) + Windows SDK 10.0.26100.0
- OS: Windows 11 Pro 25H2 (10.0.26200)
