# Walkthrough — GUI Mốc M3: Vẽ bàn cờ 10×10 từ FEN (quân SVG)

> Đợt: **2026-06-24**. Mục tiêu M3 (plan §11): vẽ bàn tĩnh từ FEN — lưới 10×10 màu chess.com + quân
> (SVG) căn giữa ô, lật bàn nếu cầm Đen, đánh dấu quân royal. Tiêu chí: thấy đúng thế xuất phát, đúng
> màu/loại quân.
>
> **Kết quả: M3 ✅ HOÀN TẤT** — golden PNG xác nhận trực quan (trắng/đen/royal đúng), engine wired
> runtime không crash, full test 4/4.

---

## 0. TL;DR

| Việc | Kết quả |
|---|---|
| Dep | `flutter_svg ^2.3.0` |
| Files | `domain/board_state.dart`, `ui/{board_painter,piece_assets,board_view}.dart`, `main.dart` (BoardScreen) |
| Ảnh quân | làm phẳng `<style>` CSS → `assets/pieces/` bằng `tool/flatten_svgs.dart` |
| Verify | golden `test/board_golden_test.dart` (xem PNG) + app thật chạy 11s không crash |

---

## 1. Quy ước ảnh quân (bạn cung cấp)

SVG nguồn ở `gui/fairyzero_piece_svg/`, tên `<color>-<name>-<L>.svg` (L = HOA cho Trắng / thường cho Đen):

| Ký tự | name | | Ký tự | name |
|---|---|---|---|---|
| p | pawn | | a | amazon |
| n | knight | | e | chancellor |
| b | bishop | | h | archbishop |
| r | rook | | y | alibaba (customPiece2 AD) |
| m | general (centaur) | | s | sergeant (customPiece3) |
| **k royal** | **general + `royal_symbol.svg`** | | v | wildebeest (customPiece1 CN) |

**Mấu chốt:** `k` (royal) và `m` (centaur) dùng chung art `*-general-M/m.svg`; quân `k` được dán
`royal_symbol.svg` ở **góc dưới-phải** để đánh dấu là "General royal" (đúng yêu cầu).

---

## 2. Mã (M3)

- **`domain/board_state.dart`** — `Piece(letter)` (HOA=Trắng) + `BoardState.fromFen()`. Parse trường
  bố trí quân; **xử lý số hai chữ số "10"** (gộp chữ số liên tiếp). Lưới `cells[r][f]`: r=0 là **hàng 1**
  (đáy Trắng), f=0 là **cột a**. FEN liệt kê hàng 10→1 nên `r = 9 - i`.
- **`ui/board_painter.dart`** — vẽ 100 ô, màu chess.com `#EEEED2`/`#769656`. Parity theo `(row+col)`:
  lẻ = ô tối (a1 tối, đúng chess.com). Parity **bất biến khi lật** nên painter không cần biết flip.
- **`ui/piece_assets.dart`** — `assetFor(letter)` → đường dẫn SVG; `isRoyal` (k); `royalSymbol`.
- **`ui/board_view.dart`** — `Stack`: nền painter + mỗi quân là `Positioned` (SVG căn giữa ô). Lật bàn:
  `row = flipped ? r : 9-r`, `col = flipped ? 9-f : f`. Royal: `Stack(general + royal_symbol góc dưới-phải)`.
- **`main.dart`** — `BoardScreen` (Stateful): `start()`→`newGame()`→`currentFen()`→`BoardState.fromFen`→vẽ;
  nếu engine lỗi thì **fallback startpos** để bàn vẫn hiện. Lật bàn khi `--black`.

---

## 3. Cạm bẫy LỚN: flutter_svg không đọc `<style>` CSS

Lần render đầu: **mọi quân ra đen + nền ô đen**. Nguyên nhân: SVG dùng
`<style>.cls-1{fill:none}.cls-2{fill:#f8f8f8}...</style>` + `class="cls-N"`, mà **flutter_svg bỏ qua
khối `<style>`** (cảnh báo `unhandled element <style/>`) → mọi `fill` về **đen mặc định** (kể cả nền
`cls-1` thành đen thay vì trong suốt).

**Cách sửa:** **làm phẳng** CSS thành thuộc tính inline. Viết `tool/flatten_svgs.dart` (dùng
`package:xml` có sẵn): đọc luật `<style>`, áp `class → fill/opacity` thành thuộc tính trên từng phần
tử, xoá `<style>`/`class`, ghi ra `assets/pieces/`. Rồi trỏ `PieceAssets._dir = 'assets/pieces'` +
khai báo `assets/pieces/` trong pubspec.
> ⚠️ **Nếu sửa SVG nguồn về sau, phải chạy lại** `dart run tool/flatten_svgs.dart`.

Sau khi làm phẳng → render đúng: quân Trắng trắng, Đen đen, nền trong suốt, royal symbol hiện.

---

## 4. Kiểm thử

- **Golden** `test/board_golden_test.dart` (white view + flipped) → `flutter test --update-goldens` →
  `test/goldens/board_startpos_{white,black}.png`. *Mẹo:* dùng `tester.runAsync` + delay để flutter_svg
  kịp tải/giải mã SVG trước khi chụp.
- **Unit** `test/widget_test.dart`: `LaunchConfig` parse + `BoardState.fromFen` (đúng ô a1=V, f1=K royal,
  f10=k, đếm 60 quân).
- `flutter test` **4/4 pass**; `flutter build windows` OK; app thật (`--engine --model`) chạy **11s không crash**.

---

## 4b. Tinh chỉnh: số chiếu còn lại trên mặt vua (check-counting)

Hiển thị **số lần bị chiếu còn lại trước khi thua** in MỜ lên mặt mỗi quân vua (vd luật 7-checks →
"7" lúc đầu). Vua Trắng: chữ `#333333`; vua Đen: `#cccccc`; **opacity 20%** (xuyên thấu thấy General).

**Số nào của bên nào — xác minh từ mã FSF** (`position.cpp`):
- FEN field `"A+B"` = `checksRemaining[WHITE]+checksRemaining[BLACK]` (line 498/859).
- `checksRemaining[c]` = số chiếu c **còn phải thực hiện để THẮNG**; giảm khi c chiếu (line 1632);
  `checksRemaining[c]==0` ⇒ c thắng, đối thủ thua (line 2932).
- ⇒ Vua TRẮNG còn bị chiếu được = `checksRemaining[BLACK]` = **số THỨ HAI (B)**; vua ĐEN = số thứ NHẤT (A).

Hiện thực: `BoardState` parse field `"A+B"` (getter `whiteRoyalChecks=checksBlack`,
`blackRoyalChecks=checksWhite`); `PieceWidget` vẽ `Text` mờ giữa-trên mặt quân (Align(0,-0.12)).
Đã kiểm chứng trực quan (tạm tăng opacity 0.85 → thấy "7" đúng chỗ → trả lại 0.20).

## 4c. Tinh chỉnh đợt 2 (theo mẫu chess.com)

- **Opacity số chiếu: sửa 0.20 → 0.80** (in rõ trên mặt General), font lớn hơn (0.52), Align(0,-0.10).
- **Nhãn toạ độ** (chess.com): số hàng (1–10) góc trên-trái cột ngoài cùng trái; chữ cột (a–j) góc
  dưới-phải hàng đáy; **màu nhãn = màu ô đối diện** (ô tối→chữ cream, ô sáng→chữ xanh). Vẽ trong
  `BoardPainter` bằng `TextPainter`; painter nhận `flipped` để đảo nhãn khi lật bàn.
- **Quân to hơn**: lề `pad` 0.06 → 0.04.
- **Layout**: `Center > Padding > AspectRatio(1) > BoardView` (bỏ Column/Flexible) để bàn cờ **vuông,
  canh giữa, vừa cạnh ngắn** — toàn bộ nhãn toạ độ + hàng đáy hiện đủ (trước đó bị cắt đáy ở cửa sổ 1280×720).

**Cạm bẫy xác minh — golden vs app thật:**
- `flutter test` render **mọi chữ thành Ô VUÔNG** (môi trường test không nạp font) → golden chỉ xác
  nhận **vị trí** nhãn/chữ số, KHÔNG xác nhận glyph.
- Glyph thật được xác minh bằng **chụp cửa sổ app thật** (PowerShell + System.Drawing CopyFromScreen
  theo `MainWindowHandle`). ⚠️ `SetForegroundWindow` từ tiến trình nền **hay bị Windows chặn** → có
  thể chụp nhầm cửa sổ đang ở trên màn hình; chỉ dùng ảnh khi chắc đúng cửa sổ app. (Đã thấy "7" trắng
  80% trên vua Đen + nhãn số hàng + quân to trong ảnh app thật.)

## 5. Trạng thái & bước tiếp

- **M3 ✅ DONE.** Bàn cờ hiện đúng từ FEN của engine, lật bàn, royal symbol.
- **Chưa commit** (người dùng tự commit). Lưu ý git: thêm `gui/assets/pieces/` (sinh ra) + `tool/flatten_svgs.dart`.
- **Mốc kế — M4:** nhập nước **chạm-chạm** trước: chạm quân → `legalMoves()` lọc theo ô nguồn → tô ô
  đích hợp lệ → chạm ô đích → `applyMove()` → máy đáp `bestMove()` → cập nhật bàn + `result()`. (Kéo-thả
  là M5, phong cấp+kết thúc M6.)

## Phụ lục — bố cục thư mục liên quan
```
gui/
  fairyzero_piece_svg/   # SVG NGUON (ban cung cap)
  assets/pieces/         # SVG da LAM PHANG (asset dung that)
  tool/flatten_svgs.dart # tool lam phang (chay lai khi sua nguon)
  lib/domain/board_state.dart
  lib/ui/{board_painter,piece_assets,board_view}.dart
  lib/main.dart          # BoardScreen
  test/{widget_test,board_golden_test}.dart
```
