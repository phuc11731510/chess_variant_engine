# Hướng dẫn BUILD & SỬ DỤNG GUI FairyZero

> Giao diện đồ hoạ (Flutter, Windows; Android chỉ để XEM ván huấn luyện, xem mục 8) cho engine cờ biến thể 10×10. Cách dùng chính là **xem mạng tự
> đấu** (`--self-play`, xem `xem_tu_dau.bat`) và **xem lại ván đã lưu** (`--replay`, xem `xem_lai.bat`);
> chơi trực tiếp với máy (chạm-chạm, kéo-thả, bảng chọn phong cấp, lật bàn khi cầm Đen) vẫn chạy nhưng
> không được chăm kỹ. Số chiếu còn lại in trên quân Hoàng gia, cửa sổ khoá tỉ lệ vuông.
>
> **Bộ quân (12 loại, khớp `custom_engine/src/app/variant_setup.cc`):** Tốt `p`, Mã `n`, Tượng `b`, Xe `r`,
> Hậu `q`, Hoàng gia `k` (quân royal), Centaur `m`, Wildebeest `v`, Alibaba `y`, Sergeant `s`, Pháo `c`,
> Grasshopper `g`. Không còn Archbishop, Chancellor, Amazon.

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
| `--self-play` | Máy tự đấu cả hai bên, người chỉ xem; tham số tìm kiếm như lúc sinh dữ liệu (`LaunchConfig.trainingUciOptions`), chỉ khác số lượt thăm (`--visits`). Nhật ký ghi vào `tu_dau_log\`. | tắt |
| `--replay <tệp>` | Chỉ **xem lại** một ván đã lưu (không tìm kiếm): nhật ký `tu_dau_log\tu_dau_*.txt` hoặc tệp các nước UCI. Đường dẫn không được có khoảng trắng. | — |
| `--replay-dir <thư mục>` | **Xem lại nhiều ván** có bảng chọn ván bên trái (xem 4b): thư mục có `chi_muc.tsv` + `van_NNNN.txt` do `xem_du_lieu.py --xuat` ghi. | — |
| `--replay-game <N>` | (Với `--replay-dir`) mở sẵn ván có cột `so` = N. | ván đầu bảng |
| `--start-fen-file <tệp>` | Như `--start-fen`, đọc FEN (dòng đầu không rỗng, không bắt đầu bằng `#`) từ tệp; `xem_tu_dau.bat` dùng để bắt đầu từ thế ngẫu nhiên. | — |
| `--temperature <T>` | (Tự đấu) nhiệt độ chọn nước. | `0.5` (như sinh dữ liệu) |
| `--temp-cutoff <N>` | (Tự đấu) chỉ dùng nhiệt độ trong N nửa nước đầu; `0` = cả ván. | `0` (như sinh dữ liệu) |

> **Kiểm tra cờ đã ăn chưa:** khi mở, terminal in dòng `LaunchConfig:` — phải thấy `engine`, `model`,
> `provider` đúng (KHÔNG phải mặc định). Nếu engine không khởi động (sai đường dẫn) sẽ có dòng chữ
> **cam** ở đáy cửa sổ và chạm quân không thấy gì.

---

## 4. Cách chơi (tính năng)

- **Chạm-chạm:** chạm quân mình → các ô đi được **sáng lên** (ô đang chọn nền vàng, ô đích chấm
  tròn, ô ăn quân vòng tròn) → chạm ô đích để đi.
- **Kéo-thả:** bấm giữ quân rồi kéo — quân **giữ đúng điểm bạn đã bấm** (không nhảy về tâm con trỏ);
  **ô đích xác định theo VỊ TRÍ CON TRỎ** lúc thả. Thả vào ô hợp lệ thì đi; thả sai thì quân về chỗ cũ.
- **Phong cấp:** khi Tốt/Sergeant tới hàng 8 (tuỳ chọn) hoặc hàng 9 (bắt buộc), hiện **bảng chọn quân**
  tại cột ô đích (Hậu, Xe, Centaur, Wildebeest, Pháo, Grasshopper, Alibaba, Mã, Tượng) — chạm chọn
  (chạm nền tối = huỷ).
- **Số trên quân Hoàng gia:** số lần Hoàng gia bên đó **còn có thể bị chiếu trước khi thua** (luật
  8 lần chiếu). Bắt đầu là `8`, giảm dần mỗi lần bị chiếu. Ván của các đời trước 2026-11-22 bắt đầu từ `7`.
- **Lật bàn:** thêm `--black` để cầm Đen (quân bạn ở đáy).
- **Cửa sổ:** vuông, **khoá tỉ lệ** — kéo giãn vẫn giữ bàn cờ vuông, vừa khít.
- Máy đi xong nước của bạn sẽ hiện **"Máy đang nghĩ…"**; hết ván hiện **kết quả** (Trắng/Đen thắng / Hoà).

### 4b. Xem mạng tự đấu và xem lại ván (cách dùng chính)

- `xem_tu_dau.bat`: máy tự đấu cả hai bên với mạng ở `--model`, GPU tích hợp qua DirectML. Đổi mạng: sửa
  đường dẫn `--model` trong tệp. **Mạng phải là mạng của biến thể hiện tại** (`.onnx` đổi từ `genN.pt` bằng
  `custom_engine\python\lay_mang.py`, có đầu ra `mlh`) và **engine `build-dml` phải được dựng lại sau mỗi lần
  đổi luật** (`ninja -C build-dml`), nếu không engine đọc luật / thế xuất phát cũ.
- `xem_tu_dau.bat` bắt đầu từ **thế xuất phát ngẫu nhiên**, đúng như lúc sinh dữ liệu và arena (`python\sinh_the_khoi_dau.py --n 1`, mỗi lần bật một thế khác); thế cứng `kStartposFen` của engine chỉ là thế tạm. Không có `py -3` thì rơi về thế tạm.
- `xem_lai.bat` có ba cách dùng:
  - không tham số: ván mới nhất trong `tu_dau_log\` (nhật ký của `xem_tu_dau.bat`);
  - `xem_lai.bat tu_dau_log\tu_dau_XXXX.txt`: một nhật ký cụ thể;
  - **`xem_lai.bat "Dữ liệu huấn luyện\games_gen1" [số]`**: xem các ván tự đấu nằm trong **dữ liệu huấn luyện** (thư mục, gói `.zip` của vòng lặp hoặc một tệp `.xz`; kéo thả lên tệp `.bat` cũng được). Lần đầu `custom_engine\python\xem_du_lieu.py` đổi cả nguồn sang nhật ký + bảng chỉ mục trong `tu_dau_log\xem_<tên>` (463 ván ≈ 11 giây, ≈ 62 MB; engine được hỏi thế cuối để biết lý do kết thúc), các lần sau mở ngay. Thư mục đã đổi sẵn (có `chi_muc.tsv`) mở thẳng.
- **Bảng chọn ván** (xem lại nhiều ván, bên trái cửa sổ): lọc theo kết quả (Trắng thắng / Đen thắng / Hoà), theo lý do kết thúc (đủ 7 lần chiếu, hết nước đi, luật 50 nước, lặp thế, bị cắt) và theo **số quân còn lại ở cuối ván**; sắp xếp theo số nửa nước hoặc số quân; bấm một dòng để xem ván đó; **[** và **]** = ván trước / sau trong danh sách đang lọc; **G** = ẩn / hiện bảng. Tìm các ván "thắng thua mà còn gần đủ 60 quân": chọn Trắng thắng hoặc Đen thắng, kéo thanh "còn ít nhất N quân" lên cao, sắp xếp "Ít nửa nước nhất".
- Để hiểu vì sao ván kết thúc: dòng trên cùng ghi **lý do** ("Đen hết nước đi (thua)", "Trắng đủ số lần chiếu"...) và số quân hai bên ở thế đang xem; thanh nước đi đánh dấu nước **chiếu** (`+` chiếu, `++` chiếu đôi, tô đỏ), số trên quân Hoàng gia là số lần chiếu còn lại.
- **Xem xác suất chọn nước khi áp nhiệt độ:** cột **%N** của bảng tìm kiếm là tỉ lệ lượt thăm (N / tổng). **Rê chuột vào tiêu đề %N** thì hiện menu: %N^2 (T = 0,5, như sinh dữ liệu và arena), %N^4 (T = 0,25), %N^10 (T = 0,1), %N^0.5 (T = 2). Chọn một mức thì thêm một cột %N^e cạnh %N = N^e / ΣN^e: đúng xác suất engine chọn từng nước ở thế đó (engine chọn theo (N / N_max)^(1/T), `MoveChoiceProbabilities` trong selfplay_game.cc). Mức đã chọn giữ nguyên khi đổi nước; chọn lại %N (T = 1) để bỏ cột phụ. Số tính trên các nước đang liệt kê (dữ liệu huấn luyện: 8 nước nhiều lượt nhất).
- Nhật ký dựng từ dữ liệu huấn luyện: bảng tìm kiếm (phím L) cho **N** = số lượt thăm của 8 nước nhiều nhất, **Q** chỉ có ở nước đã đi và nước tốt nhất, không có P / Pnet (dữ liệu huấn luyện không lưu).
- Phím: **Space** = tạm dừng / tiếp (tự đấu) hoặc tự chạy 1 giây/nước (xem lại); **← →**, lăn chuột hoặc bấm nước ở
  thanh dưới = xem từng nước; **Home / End** = về đầu / về cuối; **PageUp / PageDown** = lùi / tiến 10 nước;
  **L** = bật / tắt bảng tìm kiếm bên phải (lượt thăm N, prior P, giá trị Q theo phía Trắng và điểm cp của nước đang xem; không có cột Trắng/Hòa/Đen %).

---

## 5. Phát triển / bảo trì

- **Chạy ở chế độ dev (hot reload):** `flutter run -d windows --dart-entrypoint-args "..."`. Sửa code
  Dart → lưu → bấm `r` để nạp lại nhanh.
- **Chạy test:** `flutter test` (logic + golden ảnh bàn cờ). Cập nhật ảnh golden khi đổi giao diện:
  `flutter test --update-goldens` (ảnh ở `test/goldens/`). *Lưu ý:* golden render CHỮ thành ô vuông
  (môi trường test không nạp font) — chữ thật chỉ thấy khi chạy app.
- **Đổi / thêm ảnh quân:** ảnh nguồn ở `fairyzero_piece_svg/` thường dùng `<style>` CSS mà `flutter_svg`
  không đọc; phải **làm phẳng** thành `assets/pieces/` bằng:
  ```powershell
  dart run tool/flatten_svgs.dart
  ```
  → chạy lại MỖI KHI sửa SVG nguồn (chép ảnh mới vào `fairyzero_piece_svg/`, KHÔNG chỉ vào `assets/pieces/`;
  tool ghi đè toàn bộ `assets/pieces/`, nên xem `git status` sau khi chạy). Quy ước tên:
  `<color>-<name>-<L>.svg`, L hoa cho Trắng / thường cho Đen; bảng `ký tự → name` ở
  `lib/ui/piece_assets.dart`. Hoàng gia `k` có ảnh riêng (`*-king-K/k.svg`), Centaur `m` dùng ảnh
  `general`, Grasshopper `g` dùng `*-grasshoper-G/g.svg` (tên tệp thiếu một chữ p, giữ nguyên).
- **Đổi / xem dữ liệu huấn luyện:** `custom_engine/python/xem_du_lieu.py` (có `--liet-ke`, `--kiem`, `--xuat`; chạy `py -3 xem_du_lieu.py --help`); test: `py -3 test_xem_du_lieu.py` (đặt `FZ_ENGINE` để so thế cuối với engine), `flutter test test/replay_picker_test.dart` (đặt `FZ_ENGINE` và `FZ_REPLAY_DIR` để chạy phần dùng engine thật).
- **Có ảnh quân dạng PNG/JPG (nền trắng, tranh phẳng)** thì đổi sang SVG bằng
  `python tool/png_to_piece_svg.py ảnh.png fairyzero_piece_svg/white-cannon-C.svg c` (cần
  `pip install vtracer pillow numpy scipy`): tách nền thành trong suốt, vector hoá nhiều màu, đưa vào khung
  180×180 đúng cỡ các quân khác; rồi chép tệp vào `assets/pieces/` (không cần `flatten_svgs.dart` vì SVG đầu ra
  không có CSS). Ảnh Pháo (`c`) làm bằng cách này từ hai PNG chủ dự án cấp (2026-11-21).
- `test/piece_assets_test.dart` kiểm: mỗi quân hai màu có ảnh, ảnh đã làm phẳng (không còn `<style>` / `class=`),
  không có ảnh mồ côi. `test/engine_integration_test.dart` (đặt `FZ_ENGINE=...\custom_engine.exe`) kiểm thế xuất
  phát của GUI khớp engine thật.
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
| Bảng phong cấp ra sai quân | Bảng theo luật hiện tại: `q r m v c g y n b` (hàng 9), `n m y g` (hàng 8, tuỳ chọn; từ 2026-11-24, trước đó `n b y c g`). |
| Đổi SVG quân nhưng app vẫn ảnh cũ | Chưa chạy `dart run tool/flatten_svgs.dart` (hoặc chưa build lại `flutter build windows --release`). |
| Xem lại dữ liệu huấn luyện báo "Nước thứ N không hợp lệ" | Engine `build-dml\custom_engine.exe` là bản cũ: từ 2026-11-21 engine ghi đúng chữ cái phong cấp (`n b r q m v y c g`); bản trước in 4 loại phong cấp thành nước trơn và nhầm chữ `v` / `y`. Dựng lại: `ninja -C build-dml`. |
| Quân hiện trống / không hiện | SVG còn `<style>` (chưa làm phẳng): `flutter test test/piece_assets_test.dart` báo tệp nào. |
| Engine thoát ngay khi mở / báo lỗi mạng | `--model` là mạng cũ (không có đầu ra `mlh` hoặc cỡ policy cũ), hoặc `build-dml\custom_engine.exe` là bản dựng của luật cũ: dựng lại engine và đổi mạng mới. |

---

## 8. Android: xem ván huấn luyện ngay trên điện thoại / máy tính bảng (2026-11-23)

App Android **"FairyZero Xem ván"** (gói `vn.fairyzero.xem`) đọc thẳng dữ liệu huấn luyện mà vòng lặp Termux ghi ở
`Download/FairyZero/games_genN` (cả gói `.zip`), không cần chuyển về máy tính và không cần Python. Chỉ để XEM
(bàn cờ, thanh nước đi, bảng chọn ván, bảng tìm kiếm N / %N / Q); không chơi với máy.

**Cách dùng.** Mở app → danh sách các đời dữ liệu (mới nhất trên cùng) → bấm một đời. Lần đầu mỗi đời được đổi sang bảng
ván (~10 giây cho 1000 ván, có thanh tiến độ; kết quả lưu đệm trong thư mục riêng của app); các lần sau mở ngay. Đời đang
được vòng lặp ghi thêm ván thì lần mở sau đổi lại (nguồn đã đổi). Trên màn hình xem: nút **Ván** (ngăn kéo trái) = bảng chọn
ván có lọc / sắp xếp như trên máy tính; nút biểu đồ (ngăn kéo phải) = bảng tìm kiếm của nước đang xem; nút ▶ = tự chạy
1 giây / nước; **vuốt ngang trên bàn** hoặc các nút ‹ › ở thanh dưới = lùi / tiến nước. Màn hình ngang đủ rộng thì bảng tìm
kiếm hiện cạnh bàn như bản máy tính. Menu ⋮ ở màn hình đầu: đổi thư mục dữ liệu, xoá bộ nhớ đệm.

**Quyền.** Android 11+ chỉ cho app đọc tệp do Termux ghi trong Download khi bật "Cho phép truy cập mọi tệp" cho app. Bản
cài bằng `adb install` đã có sẵn quyền; nếu không, màn hình đầu hiện thẻ "Cần quyền truy cập tệp" có nút mở đúng trang
Cài đặt (gạt một lần, quay lại app).

**Cách hoạt động** (mọi thứ nằm trong `lib/data/`, thuần Dart + engine trong tiến trình):
- `v6_game.dart` giải mã tệp ván `.xz` (định dạng v6, gói `archive`); `van.dart` dựng thế xuất phát, dãy nước, FEN, nhật ký
  xem lại (đúng định dạng `tu_dau_log`), lý do kết thúc. Đây là bản Dart của `custom_engine/python/xem_du_lieu.py`
  và **phải giống từng byte**: `flutter test test/data_van_test.dart` (ván mẫu trong `test/fixtures/v6`); đặt thêm
  `FZ_ENGINE`, `FZ_DATA` (thư mục / `.zip`), `FZ_DATA_REF` (thư mục do `xem_du_lieu.py --xuat` ghi) để so cả một đời.
- Lý do kết thúc (hết nước đi, đủ số lần chiếu, luật 50 nước, lặp thế) và số quân còn lại do ENGINE trả lời:
  `libfairyzero.so` (engine arm64, chế độ chỉ luật cờ, không cần mạng) qua dart:ffi, ở isolate nền (`generation_cache.dart`).
  Bảng ván tính trên máy bảng **giống hệt từng byte** bản Python trên máy tính (đã kiểm với đời 44, 1016 ván).
- Nhật ký từng ván (`van_NNNN.txt`, vài trăm KB) chỉ được ghi khi ván đó được mở (`GameFilePreparer`).
- Chuyển ngữ cảnh khác với máy tính: `NativeFfiEngine(rulesOnly: true)` (không nạp mạng, trả lời tức thì không qua bộ đếm giờ).

**Dựng và cài** (trong `D:\chess_variant\gui`, máy đã có Android SDK + NDK 28.2 + Flutter):
```powershell
powershell -ExecutionPolicy Bypass -File tool\dung_engine_android.ps1      # engine HIỆN TẠI -> jniLibs (*.so không nằm trong git)
flutter build apk --release --target-platform android-arm64
adb install -r build\app\outputs\flutter-apk\app-release.apk
```
**Đổi luật / bộ quân thì chạy lại `dung_engine_android.ps1` rồi dựng lại APK**: app dùng engine trong tiến trình để kiểm
nước đi và dựng FEN, bản `.so` cũ = luật cũ (bản tháng 6 còn bộ quân và luật chiếu cũ nên mọi ván mới đều "không hợp lệ").
Đổi định dạng dữ liệu huấn luyện (`trainingdata_v6.py`) thì sửa `lib/data/v6_game.dart` và chạy lại bài so với Python.
