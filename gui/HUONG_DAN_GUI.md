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

**Hai kiểu dữ liệu (2026-11-24).** Vòng lặp theo đời (menu `v`) ghi `games_genN`. Vòng lặp LIÊN TỤC (menu `w`) không có
`games_genN` nữa: mỗi máy Colab gửi các gói nhỏ `Download/FairyZero/goi/goi_<số thứ tự>_n<đời mạng>_<số ván>_<số thế>.zip`
(mỗi gói chứa ván của MỘT đời mạng, thành viên `games_gen<N>/...xz`). App quét cả `goi/`, gom mọi gói cùng `n<đời>` thành một
"Đời N" (dòng phụ: số ván, số gói, giờ gói mới nhất); thứ tự ván = thứ tự tên gói. Nhóm gói là một nguồn riêng
(`groupSource` trong `lib/data/game_library.dart`, dấu vân tay chỉ dựa vào tên / kích thước / giờ sửa nên quét nhanh); gói
hỏng hoặc đã bị vòng lặp dọn giữa chừng thì bị bỏ qua. Đời mạng mới nhất còn nhận thêm gói nên mỗi lần mở lại phải đổi lại
(~10 giây cho 1000 ván); các đời cũ mở ngay. Vòng lặp chỉ giữ gói đủ cho cửa sổ huấn luyện (khoảng 1,5 lần), nên các đời xa
sẽ biến mất khỏi danh sách theo thời gian. Bài thử: `flutter test test/goi_nhom_test.dart`.

**Số ván cố định + dọn bộ nhớ đệm (2026-11-25).** (1) Với ván của gói vòng lặp liên tục, app gọi ván bằng nhãn `<số gói>.<thứ tự
trong gói, từ 1>` (vd `985.1`; `992.8` = ván thứ 8 của gói `goi_00992_...zip`) thay cho `#<vị trí trong danh sách của đời>`: vị trí
đó đổi khi vòng lặp thêm / dọn gói và không khớp công cụ nào khác, còn nhãn đi theo ván mãi mãi và khớp tên gói trên điện thoại
(`ReplayLibrary.labelsFromSources`, đọc từ `nguon.txt` cạnh `chi_muc.tsv`; `xem_du_lieu.py --liet-ke` in cùng nhãn ở cuối mỗi dòng).
Nguồn không phải gói (thư mục `games_genN`, gói đơn) vẫn hiện `#<id>`. (2) Mỗi lần quét màn hình đầu, app xoá thư mục đệm
(`files/xem/<đời>`) không còn đúng với dữ liệu: đời đã bị vòng lặp dọn hết gói, hoặc đời đã thêm / bớt gói (bảng ván và nhật ký trong
đó nói về dữ liệu cũ); mở đời đó lần sau đổi lại từ nguồn. Không dọn đời đang đổi / đang xem, và không dọn gì khi quét lỗi hoặc
không có quyền đọc thư mục dữ liệu (`purgeStaleCaches` trong `lib/data/generation_cache.dart`).

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

**Hai bộ luật trong một app (2026-11-24).** Luật phong cấp hàng 8/3 đổi ngày 2026-11-24 (`n b y c g` thành `n m y g`) nên ván
của các đời trước có nước mà engine mới cấm (phong Tượng / Pháo ở hàng 8/3, ~14% ván đời 54) và ván luật mới có nước mà engine
cũ cấm (phong Centaur). Hai tập này không giao nhau, nên app mang CẢ HAI engine: `libfairyzero.so` (luật hiện tại) và
`libfzcu.so` (luật trước 2026-11-24; là bản dựng cũ đổi SONAME để hai thư viện cùng nạp được; bản sao lưu ở
`ban_linux\android\libfzcu.so`, vì `*.so` không nằm trong git; dựng lại từ commit `744dceb` bằng `dung_engine_android.ps1` ở
worktree đó rồi đổi chuỗi SONAME `libfairyzero.so` thành `libfzcu.so` (ngắn hơn, chèn byte 0 cho đủ độ dài)). Chỉ mục thế
cuối (`generation_cache.dart`): hỏi engine mới, nếu thế cuối lệch bản ghi thì hỏi engine cũ. Màn hình xem ván
(`GameController.initReplay` + `RuleSetSwitcher`, `NativeFfiEngine.switchRuleSet`): gặp nước "không hợp lệ" thì đổi sang bộ
luật kia và phát lại từ đầu một lần; engine giữ bộ luật vừa dùng cho ván kế tiếp. Khi không còn ván đời cũ nào cần xem thì
xoá `libfzcu.so` (app vẫn chạy: không có thư viện kia thì không đổi luật).

**Bảng tìm kiếm trên điện thoại (2026-11-24).** Màn hình dọc: bàn rộng hết bề ngang sát phía trên, bảng tìm kiếm nằm ngay
dưới thanh nước đi (khi còn từ 170 dp chiều cao; thấp hơn thì là ngăn kéo bên phải như trước). Màn hình ngang: cạnh bàn.
Bảng tự thu nhỏ vừa bề ngang (không còn tràn cột Q Trắng khi xoay ngang hoặc cỡ chữ hệ thống lớn); cột P / Pnet chỉ hiện khi
nhật ký có (dữ liệu huấn luyện không lưu prior); bảng nằm ngay dưới dòng tổng, các ghi chú xuống dưới; liệt kê MỌI nước có
lượt thăm (`nhatKy(..., tatCaNuocCoLuot: true)`, chỉ ở Android; bản Python và bài so byte vẫn 8 nước). **Q chỉ có ở nước đã đi
và nước nhiều lượt nhất**: bản ghi huấn luyện chỉ lưu `played_q`, `best_q`, `root_q` và phân bố lượt thăm, không lưu Q của nước khác
(chủ dự án đồng ý để vậy, 2026-11-24).

**Kho mạng, prior thô, phân tích MCTS trên máy bảng (2026-11-27).** App tự chạy mạng ngay trên máy bảng bằng engine trong tiến
trình (`libfairyzero.so` + `libonnxruntime.so` 1.18), không cần máy tính.
- **Kho mạng** (nút chip ở màn hình đầu): danh sách `gen<N>.pt` trên Release `NN_Model` (API GitHub, không đăng nhập, 60 lần
  hỏi / giờ), nút "Tải mạng mới nhất", tải đời bất kỳ, xoá đời không dùng; mạng nằm trong `Android/data/vn.fairyzero.xem/files/mang/gen<N>/`
  (gỡ app là sạch). Release chỉ có `.pt` mà máy bảng không có PyTorch, nên app tự đổi: `assets/mang/khung.onnx` là đồ thị
  dựng tay (`custom_engine/python/khung_mang.py dung`), mọi trọng số nằm ở tệp ngoài `trong_so.bin`, mỗi trọng số là ĐÚNG một
  tensor của state_dict (cùng tên, cùng byte); app đọc `.pt` (zip không nén + pickle, bộ đọc chỉ nhận đúng 3 tên toàn cục của
  một state_dict, `lib/mang/pt_doc.dart`) rồi chép byte theo `assets/mang/bang_ghep.json` (`lib/mang/doi_pt.dart`). Đổi
  kiến trúc mạng thì chạy lại `khung_mang.py dung` (`.pt` lệch hình dạng thì app báo lỗi, không chạy). Kiểm:
  `py khung_mang.py kiem gen201.pt` (so với PyTorch) và `flutter test test/doi_pt_test.dart` với `FZ_PT` / `FZ_PT_REF`
  (so từng byte với bản Python, cả đường đổi trong isolate như app).
- **Chọn mạng**: nút `gen<N>` trên thanh công cụ màn xem ván; mặc định là đời đã sinh dữ liệu đang xem nếu đã tải, không thì
  đời mới nhất đã tải.
- **Prior thô**: nút "Prior thô" ở đầu bảng tìm kiếm. Bật thì app chạy mạng MỘT lần cho đúng thế của lần tìm đang xem (đủ
  lịch sử: FEN đầu ván + các nước) bằng lệnh engine `nneval policy`, điền cột Pnet và giá trị thô (Q Trắng, hoà); chỉ tính thế
  đang xem, thế đã tính thì giữ lại.
- **Phân tích** (nút cây trên thanh công cụ): MCTS độc lập ở thế ĐANG HIỆN trên bàn với số lượt chọn được (200 … 20000), thông
  số như tìm sâu lúc sinh dữ liệu (c_puct 1,5, cpuct-factor 0, fpu 0, không two-fold, không sticky, PolicySoftmaxTemp 1,0) nhưng
  KHÔNG nhiễu; "Tìm thêm" cộng lượt vào cùng cây (ReuseTree). Xem cây: lệnh engine `tree <đường đi>` trả các con của một nút
  (N, P, Q, D), chạm một nước để đi xuống, đường dẫn phía trên để quay lên, bàn cờ nhỏ hiện thế của nút. Ở tầng gốc, cột
  "%N ghi" = tỉ lệ lượt thăm trong dữ liệu huấn luyện ở cùng thế, dòng tô vàng = nước ván đã đi.
- **GPU (2026-11-27).** App chạy mạng trên GPU (TFLite / LiteRT 1.4.2 + GPU delegate qua OpenCL, FP16, lô 16), không được thì
  tự lùi về CPU (ONNX Runtime); tiêu đề màn Phân tích và nút mạng ghi `GPU` / `CPU`. Mạng GPU `gen<N>/gpu_b16.tflite` (~22 MB)
  tạo lúc tải, hoặc lần dùng đầu tiên với mạng tải trước đó, từ `trong_so.bin` (không cần `.pt`): khung
  `assets/mang/khung_gpu_b16.tflite` (trọng số để 0) + `assets/mang/bang_ghep_gpu_b16.json` (mỗi chỗ ghép = một tensor qua phép
  `id` / `T` / `relb`), dựng bằng `custom_engine/python/khung_gpu.py dung --kiem <mạng thật>` trong môi trường có tensorflow +
  onnx2tf + ai-edge-litert + onnxruntime (không cần torch); `khung_gpu.py va` vá như app để thử bằng adb. Đồ thị GPU khác khung
  ONNX ở hai chỗ: chỉ tensor <= 4 chiều, không Gather (GPU delegate từ chối, cả attention rơi về CPU), và LayerNorm viết tay
  chia x cho 32 trước khi bình phương (dòng dư lệch tới ~625, bình phương tràn FP16: prior ra gần đều nhau). Engine:
  `src/lczero_chess/neural/tflite_backend.cc` (chỉ bản Android, dlopen `libtensorflowlite_jni.so` + `libtensorflowlite_gpu_jni.so`
  từ gói Maven `com.google.ai.edge.litert:litert(-gpu):1.4.2`; LiteRT 2.x không còn GPU delegate cổ điển), `provider=gpu`.
  Manifest khai `uses-native-library libOpenCL.so` (Android 12+). Kiểm: `flutter test test/doi_pt_test.dart` với `FZ_GPU_REF`
  (giống từng byte `khung_gpu.py va`).
- **Tốc độ** (SM-X110, Helio G99, mạng 10 lớp d 192). MCTS 800 lượt: GPU ~66–72 lượt / giây (~12 giây), CPU ~19 (~42 giây),
  tức GPU ~3,5 lần. Thuần mạng (`benchmark_model` của TFLite / `custom_engine --bench-nn --bench-batches 1,16` qua adb): GPU
  FP16 lô 1 / 8 / 16 / 32 = 28 / 73 / 80 / 81 thế / giây (GPU FP32 lô 16: 33); ORT CPU 4 luồng ≈ XNNPACK ≈ 15–20; NNAPI (GPU /
  APU qua trình điều khiển MediaTek; fp32, fp16, cấm CPU tham chiếu) chỉ ~3,8 ở lô 1. GPU và CPU ra cùng nước, cùng biến chính;
  Q lệch ~0,003, prior lệch ~0,001 (FP16, như tự đấu trên T4). Engine nhận thêm `--provider xnnpack|nnapi`,
  `--nnapi-opt fp16=1|cpu_disabled=1|cpu_only=1` (UCI `Provider`: `xnnpack`, `nnapi`, `nnapi-fp16`, `gpu`).
