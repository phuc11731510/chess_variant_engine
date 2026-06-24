# Hướng dẫn BUILD & SỬ DỤNG GUI FairyZero

> Giao diện đồ hoạ (Flutter, Windows) để **chơi với engine** cờ biến thể 10×10. Bàn cờ tương tác
> bằng **chạm-chạm** lẫn **kéo-thả**, có bảng chọn phong cấp, số chiếu còn lại trên quân vua, lật
> bàn khi cầm Đen, cửa sổ khoá tỉ lệ vuông.

---

## 0. Tóm tắt nhanh (chạy trong 30 giây)

```powershell
cd D:\chess_variant\gui
flutter build windows --release
.\build\windows\x64\runner\Release\fairyzero_gui.exe `
    --engine "D:\chess_variant\custom_engine\build-dml\custom_engine.exe" `
    --model  "D:\chess_variant\custom_engine\dist\FairyZero\models\12bx144fx8s_3.onnx" `
    --provider dml --movetime 5000
```
→ Mở cửa sổ bàn cờ, bạn cầm Trắng, chơi với máy. **Bắt buộc có `--engine` và `--model`** thì máy mới đi.

---

## 1. Cần gì để build

| Thứ | Ghi chú |
|---|---|
| **Flutter SDK** | Đã cài ở `D:\flutter` (kênh stable). Gõ `flutter` được nếu `D:\flutter\bin` đã trong PATH; nếu chưa, dùng `D:\flutter\bin\flutter.bat`. |
| **Visual Studio Build Tools** (C++ desktop) | Để Flutter biên dịch app Windows. Máy này đã có. `flutter doctor` báo `[√] Visual Studio - develop Windows apps` là đủ. |
| **Engine đã build** | File `custom_engine.exe` — xem `custom_engine\HUONG_DAN.md`. Bản **`build-dml`** để chạy GPU (provider `dml`), bản `build` cho CPU. |
| **Một model `.onnx`** | Mạng đã huấn luyện (vd `...\dist\FairyZero\models\12bx144fx8s_3.onnx`). |

> GUI **không tự chứa engine**: nó *mở* `custom_engine.exe` ở nền và nói chuyện qua giao thức UCI.
> Phải trỏ đúng `--engine` tới file engine và `--model` tới file `.onnx`.

---

## 2. Build

```powershell
cd D:\chess_variant\gui

# Bản phát hành (KHUYẾN NGHỊ để dùng/mang đi — nhanh, gọn):
flutter build windows --release
#   -> build\windows\x64\runner\Release\   (gồm fairyzero_gui.exe + data\ + *.dll)

# Bản gỡ lỗi (có hot-reload khi phát triển):
flutter build windows --debug
#   -> build\windows\x64\runner\Debug\
```

Cả thư mục `Release\` (hoặc `Debug\`) là **tự đủ để chạy** (đã kèm runtime Flutter + ảnh quân trong
`data\`). Muốn mang sang máy khác: copy nguyên thư mục đó **+** engine (`custom_engine.exe` và các
`.dll` đi kèm như `onnxruntime.dll`, `DirectML.dll`) **+** file model `.onnx`.

---

## 3. Cách chạy & cờ lệnh

### 3.1 Hai cách truyền cờ lệnh
- **Chạy thẳng exe (chuẩn, ít lỗi nhất):**
  ```powershell
  .\build\windows\x64\runner\Release\fairyzero_gui.exe --engine "..." --model "..." --provider dml
  ```
- **Qua `flutter run` (khi đang phát triển):** cờ lệnh phải bọc trong `--dart-entrypoint-args`:
  ```powershell
  flutter run -d windows --dart-entrypoint-args "--engine ... --model ... --provider dml --movetime 5000"
  ```
  > ⚠️ `flutter run` gửi cả cụm trong dấu nháy là **một chuỗi**; GUI đã tự tách theo khoảng trắng.
  > Nhưng nếu **đường dẫn có dấu cách** thì hãy chạy thẳng exe (cách trên).

### 3.2 Bảng cờ lệnh
| Cờ | Ý nghĩa | Mặc định |
|---|---|---|
| `--engine <path>` | Đường dẫn `custom_engine.exe`. **Bắt buộc để chơi với máy.** | `engine/custom_engine.exe` |
| `--model <onnx>` | File trọng số `.onnx`. **Bắt buộc để máy ĐI.** | (không nạp) |
| `--provider cpu\|dml\|cuda` | `dml` = GPU (cần bản `build-dml`); `cpu` = không GPU. | `cpu` |
| `--movetime <ms>` | Thời gian máy nghĩ mỗi nước (mili-giây). | `5000` |
| `--visits <N>` | Hoặc số node/nước cố định (ưu tiên hơn `--movetime`). | — |
| `--black` | Bạn cầm **Đen** (bàn tự lật, quân bạn ở đáy). | cầm Trắng |
| `--white` | Bạn cầm Trắng. | (mặc định) |
| `--start-fen "<FEN>"` | Thế cờ bắt đầu tuỳ chọn. | startpos biến thể |
| `--demo-move <uci>` | (Gỡ lỗi) tự đi 1 nước của NGƯỜI ngay khi mở, vd `--demo-move b3b4`. | — |

> **Kiểm tra cờ đã ăn chưa:** khi mở, terminal in dòng `LaunchConfig:` — phải thấy `engine`, `model`,
> `provider` đúng (KHÔNG phải mặc định). Nếu engine không khởi động (sai đường dẫn) sẽ có dòng chữ
> **cam** ở đáy cửa sổ và chạm quân không thấy gì.

---

## 4. Cách chơi (tính năng)

- **Chạm-chạm:** chạm quân mình → các ô đi được **sáng lên** (ô đang chọn nền vàng, ô đích chấm
  tròn, ô ăn quân vòng tròn) → chạm ô đích để đi.
- **Kéo-thả:** bấm giữ quân rồi kéo — quân **giữ đúng điểm bạn đã bấm** (không nhảy về tâm con trỏ);
  **ô đích xác định theo VỊ TRÍ CON TRỎ** lúc thả. Thả vào ô hợp lệ thì đi; thả sai thì quân về chỗ cũ.
- **Phong cấp:** khi tốt/sergeant tới hàng cuối, hiện **bảng chọn quân** (Rook, Wildebeest, General,
  Alibaba, Knight, Bishop) tại cột ô đích — chạm chọn (chạm nền tối = huỷ).
- **Số trên quân vua (General):** số lần vua bên đó **còn có thể bị chiếu trước khi thua** (luật
  7-checks). Bắt đầu là `7`, giảm dần mỗi lần bị chiếu.
- **Lật bàn:** thêm `--black` để cầm Đen (quân bạn ở đáy).
- **Cửa sổ:** vuông, **khoá tỉ lệ** — kéo giãn vẫn giữ bàn cờ vuông, vừa khít.
- Máy đi xong nước của bạn sẽ hiện **"Máy đang nghĩ…"**; hết ván hiện **kết quả** (Trắng/Đen thắng / Hoà).

---

## 5. Phát triển / bảo trì

- **Chạy ở chế độ dev (hot reload):** `flutter run -d windows --dart-entrypoint-args "..."`. Sửa code
  Dart → lưu → bấm `r` để nạp lại nhanh.
- **Chạy test:** `flutter test` (logic + golden ảnh bàn cờ). Cập nhật ảnh golden khi đổi giao diện:
  `flutter test --update-goldens` (ảnh ở `test/goldens/`). *Lưu ý:* golden render CHỮ thành ô vuông
  (môi trường test không nạp font) — chữ thật chỉ thấy khi chạy app.
- **Đổi ảnh quân:** ảnh nguồn ở `fairyzero_piece_svg/` dùng `<style>` CSS mà `flutter_svg` không đọc;
  phải **làm phẳng** thành `assets/pieces/` bằng:
  ```powershell
  dart run tool/flatten_svgs.dart
  ```
  → chạy lại MỖI KHI sửa SVG nguồn. Quy ước tên: `<color>-<name>-<L>.svg` (vua dùng art `general` +
  overlay `royal_symbol.svg`).
- **Đổi kích thước/tỉ lệ cửa sổ:** kích thước ban đầu ở `windows/runner/main.cpp`; khoá tỉ lệ vuông ở
  `windows/runner/win32_window.cpp` (xử lý `WM_SIZING`).
- **Kiểm thử nhanh lớp engine không cần mở cửa sổ:**
  ```powershell
  dart run tool/m2_smoke.dart --engine "..." --model "..." --provider cpu --visits 40
  ```

---

## 6. Cấu trúc thư mục

```
gui/
  lib/
    main.dart                     # điểm vào: cờ lệnh -> BoardScreen + GameController
    config/launch_config.dart     # parse cờ lệnh
    domain/
      board_state.dart            # parse FEN -> bàn cờ (+ lượt, số chiếu)
      uci_move.dart               # Sq, UciMove.tryParse (hàng 2 chữ số, hậu tố phong)
      game_controller.dart        # điều phối lượt người↔máy, chọn/đi, phong cấp
    engine/
      engine_service.dart         # interface (Android sau này tái dùng)
      uci_process_engine.dart     # DESKTOP: spawn engine, nói UCI bất đồng bộ
    ui/
      board_painter.dart          # nền 10×10 + nhãn toạ độ (màu chess.com)
      board_view.dart             # quân SVG + tô sáng + chạm/kéo + bảng phong cấp
      piece_assets.dart           # ký tự quân -> đường dẫn SVG
  fairyzero_piece_svg/            # SVG NGUỒN (do người dùng cấp)
  assets/pieces/                  # SVG đã LÀM PHẲNG (asset dùng thật)
  tool/
    flatten_svgs.dart             # làm phẳng SVG
    m2_smoke.dart                 # test lớp engine headless
  windows/runner/                 # main.cpp (kích thước), win32_window.cpp (khoá tỉ lệ)
  test/                           # widget_test.dart (logic) + board_golden_test.dart (ảnh)
  build/windows/x64/runner/Release/fairyzero_gui.exe   # KẾT QUẢ build
```

---

## 7. Lỗi thường gặp

| Hiện tượng | Nguyên nhân & cách sửa |
|---|---|
| Chạm quân không sáng gì, terminal in toàn cờ mặc định | Cờ lệnh không ăn / sai `--engine`. Chạy thẳng exe với đường dẫn đầy đủ; xem dòng `LaunchConfig:`. |
| Chọn quân được nhưng đi 1 nước rồi **kẹt** | **Thiếu `--model`** → engine không nghĩ được. Thêm `--model "...onnx"`. |
| Dòng chữ **cam** ở đáy cửa sổ | Engine không khởi động (sai đường dẫn exe / thiếu `.dll` của engine). Kiểm tra `--engine` và các `.dll` cạnh nó. |
| Muốn dùng **GPU** | Dùng bản engine **`build-dml`** + `--provider dml`. |
| Bảng phong cấp ra sai quân | Đã đổi luật `BMNRVY` (Rook thay Archbishop) — đúng là vậy. |
| Đổi SVG quân nhưng app vẫn ảnh cũ | Chưa chạy `dart run tool/flatten_svgs.dart`. |
