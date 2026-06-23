# Walkthrough — GUI Mốc M2: `UciProcessEngine` (nối engine qua UCI)

> Đợt: **2026-06-23**. Mục tiêu M2 (plan §4/§11): lớp Flutter spawn engine, làm trình tự khởi động
> UCI, lấy `fen` + `legalmoves`. Tiêu chí: log Dart in ra FEN xuất phát + danh sách nước hợp lệ.
>
> **Kết quả: M2 ✅ HOÀN TẤT** — chạy thật ra FEN + 34 nước + result; bonus `go→bestmove` cũng OK.

---

## 0. TL;DR

| Việc | Kết quả |
|---|---|
| File thêm | `gui/lib/engine/engine_service.dart`, `gui/lib/engine/uci_process_engine.dart`, `gui/tool/m2_smoke.dart` |
| Kiểm tra | `flutter analyze` sạch · smoke headless (`dart run`) ra FEN+34 nước+result+bestmove |

---

## 1. Thiết kế (khớp kiến trúc 3 lớp của plan §4)

**`engine_service.dart` — interface trừu tượng** (`EngineService`) + `enum GameResult`:
`start / newGame / applyMove / legalMoves / currentFen / gameResult / bestMove / dispose`.
Lý do trừu tượng: desktop dùng tiến trình con UCI; **Android (GĐ2) dùng cùng interface** nhưng
gọi `.so` qua dart:ffi → lớp UI/điều phối không phải sửa.

**`uci_process_engine.dart` — bản DESKTOP** (Kiểu A):
- `Process.start(<engine>, ['--uci-nn'], workingDirectory: <thư mục engine>)` — workdir = thư mục
  engine để **DLL (onnxruntime…) + model tương đối** resolve đúng.
- **Đọc output BẤT ĐỒNG BỘ**: `stdout.transform(Utf8Decoder).transform(LineSplitter).listen(_onLine)`
  → không khựng UI.
- **Mẫu request→response**: gửi lệnh rồi `await` dòng phản hồi thoả predicate, qua `Completer` +
  hàng đợi `_pending` (+ timeout). Vì engine xử lý lệnh **tuần tự một luồng**, gửi/đợi tuần tự là an toàn.
- **Trình tự khởi động** (`start()`): `uci`→đợi `uciok`; `setoption WeightsFile/Provider/Visits`;
  `isready`→đợi `readyok`.
- **Vị trí**: luôn gửi `position startpos moves <toàn bộ lịch sử>` (giữ tree-reuse — plan §5.3).
  `newGame`/`applyMove` cập nhật `_moves` rồi đẩy lại; dùng `isready/readyok` làm **rào đồng bộ**
  (vì `position` không có phản hồi).
- **Truy vấn**: `legalMoves()` → parse dòng `legalmoves ...`; `currentFen()` → cắt sau `fen `;
  `gameResult()` → map `result ...`; `bestMove()` → `go nodes/movetime` rồi đợi `bestmove`.

**`tool/m2_smoke.dart`** — script headless (chỉ dùng dart:io, **không cần Flutter**) để kiểm tra
nhanh bằng `dart run`.

---

## 2. Kiểm thử & kết quả

```
dart run tool/m2_smoke.dart --engine D:\...\build\custom_engine.exe
```
→
```
handshake OK (uciok + readyok)
FEN xuat phat: vrhbakberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHBAKBERV w KQkq - 7+7 0 1
Nuoc hop le (34): b3b4 c3c4 ... a3a5 a3c5 j3h5 j3j5
Ket qua: GameResult.undecided
```
Kèm model (bonus go→bestmove, de-risk M4):
```
dart run tool/m2_smoke.dart --engine ...build\custom_engine.exe \
  --model ...\dist\FairyZero\models\12bx144fx8s_3.onnx --provider cpu --visits 40
-> ... Dang cho engine nghi (40 visits/nuoc)... ; bestmove: g3g5
```
`flutter analyze`: **No issues found**.

---

## 3. Cạm bẫy / lưu ý

- **Chạy headless bằng `dart run`** được vì `uci_process_engine.dart` chỉ import `dart:io/async/convert`
  (không Flutter). Rất tiện để test logic engine mà không cần mở cửa sổ.
- Khi **không truyền `--model`**, engine thử nạp model mặc định `weights_0_elo.onnx` (không có) → in
  cảnh báo ra **stderr**, nhưng `isready` vẫn trả `readyok` và `fen`/`legalmoves` chạy bình thường
  (không cần backend). Vô hại cho M2.
- `writeln` của Dart thêm `\n` (không `\r`) → khớp `std::getline` của engine.
- FEN trả về có castling `KQkq` (FSF nội bộ) — GUI chỉ dùng trường bố trí quân để vẽ (M3), không sao.

---

## 4. Trạng thái & bước tiếp

- **M2 ✅ DONE.** `EngineService` + `UciProcessEngine` sẵn sàng cho lớp UI.
- **Chưa wire vào `main.dart`** (cố ý) — sẽ nối khi có bàn cờ ở **M3**.
- **Chưa commit** (người dùng tự commit).
- **Mốc kế — M3:** parse FEN → `BoardState` (100 ô) → `BoardPainter` vẽ lưới 10×10 màu chess.com +
  quân (tạm render chữ cái khi chưa có ảnh), lật bàn nếu cầm Đen. Lúc này mới gắn `UciProcessEngine`
  vào app: `start()` → `currentFen()` → vẽ.

## Phụ lục — API `EngineService`
```
start()                  uci/setoption/isready handshake
newGame({fen})           ucinewgame + position (startpos|fen)
applyMove(uci)           them nuoc + position startpos moves ...
legalMoves() -> [uci]    parse dong "legalmoves ..."
currentFen() -> fen      parse dong "fen ..."
gameResult() -> enum     parse dong "result ..."
bestMove()  -> uci       go nodes/movetime -> "bestmove ..."
dispose()                quit + kill
```
