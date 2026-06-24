# Walkthrough — GUI Mốc M4: Nhập nước chạm-chạm (chơi với máy)

> Đợt: **2026-06-24**. Mục tiêu M4 (plan §8/§11): chơi với máy bằng **chạm-chạm** — chạm quân mình →
> tô ô đích hợp lệ → chạm ô đích → đi nước → máy đáp. Tiêu chí: chơi tay vài nước người↔máy, bàn cập nhật đúng.
>
> **Kết quả: M4 ✅ HOÀN TẤT** — golden xác nhận tô sáng; app thật `--demo-move` đi nước người + máy đáp đúng; test 8/8.

---

## 0. TL;DR

| Việc | Kết quả |
|---|---|
| Files mới | `domain/uci_move.dart`, `domain/game_controller.dart` |
| Sửa | `board_state.dart` (+whiteToMove), `board_view.dart` (+tương tác/HighlightPainter), `main.dart` (ListenableBuilder), `config/launch_config.dart` (+--demo-move), `windows/runner/main.cpp` (cửa sổ 760×880) |
| Verify | 8 test (UCI parse, GameController, golden highlight) + app thật demo f3f5→máy đáp b8b6 |

---

## 1. Kiến trúc

- **`domain/uci_move.dart`** — `Sq{file,rank}` (getter `flat`=rank*10+file khớp BoardState, `name`=tên UCI),
  `UciMove.tryParse` (xử lý **hàng 2 chữ số** `e10` + **hậu tố phong** `f2f1h`).
- **`domain/game_controller.dart`** — `ChangeNotifier` điều phối một ván:
  - Lượt: `humansTurn = board.whiteToMove == humanIsWhite`.
  - `onTapSquare(r,f)`: chưa chọn → chọn quân mình + tô ô đích (lọc `legalMoves` theo ô nguồn);
    đã chọn → chạm ô đích hợp lệ thì đi; chạm quân mình khác thì đổi chọn; chạm chỗ khác thì bỏ chọn.
  - Đi nước người → `engine.applyMove` → refresh → **máy đáp** (`bestMove` rồi `applyMove`) → refresh.
  - `playHumanUci(uci)`: API đi nước người (dùng cho tap đã build sẵn hoặc `--demo-move`).
- **`board_view.dart`** — thêm `GestureDetector` (đổi toạ-độ-chạm → (r,f) có xét lật bàn) + `HighlightPainter`
  (ô chọn = vàng `0x80F6F669`; ô đích = chấm tròn, hoặc **vòng** nếu là ăn quân).
- **`main.dart`** — `ListenableBuilder` theo controller; chỉ báo "Máy đang nghĩ…"; overlay kết quả ván.
- **Engine là trọng tài**: GUI chỉ dùng `legalMoves()`/`applyMove()`/`bestMove()`/`gameResult()` — không tự suy luật.

---

## 2. Kiểm thử

- **Unit (FakeEngine)** `test/widget_test.dart`: parse UCI (`b3b5`, `f2f1h`, `e10i6`); GameController
  chọn quân tô đúng ô đích; đi nước người → máy đáp (đúng thứ tự `applied`, `bestCalls==1`, về lượt người).
- **Golden** `board_highlight.png`: ô b3 vàng + b4/b5 chấm tròn — xác nhận trực quan tô sáng.
- **App thật** (`--demo-move`, cờ gỡ lỗi tự đi 1 nước người lúc mở):
  - `--demo-move b3b4` → b4 có tốt Trắng, b3 trống, **máy đáp d8d6**.
  - `--demo-move f3f5` → f5 có tốt Trắng, **máy đáp b8b6**. (chụp cửa sổ xác nhận)
- `flutter analyze` sạch, `flutter test` **8/8**.

**Mẹo chụp cửa sổ app (Flutter/GPU):** `Start-Process` lấy `MainWindowHandle`, **minimize rồi restore**
(`ShowWindow 6→9`) để đưa lên trước (vì `SetForegroundWindow` từ tiến trình nền hay bị chặn), rồi
`Graphics.CopyFromScreen` theo `GetWindowRect`. (PrintWindow hay ra đen với nội dung GPU.)

---

## 3. Lưu ý

- **Phong cấp (M4 tạm):** khi ô đích có nhiều biến thể (f2f1b/h/m/n/v/y) tạm lấy **biến thể đầu**; M6 sẽ thêm bảng chọn.
- **Cửa sổ:** đổi mặc định 1280×720 → **760×880** cho vừa bàn vuông (vẫn kéo giãn được). Trên màn hình
  thấp/độ phân giải cao có thể vẫn hơi sát đáy — M7 sẽ dùng `window_manager` khoá tỉ lệ + min-size.

---

## 4. Trạng thái & bước tiếp

- **M4 ✅ DONE.** Chơi người↔máy bằng chạm-chạm, tô sáng, máy tự đáp, hiện kết quả.
- **Chưa commit** (người dùng tự commit).
- **Mốc kế — M5:** kéo-thả (quân bám con trỏ khi kéo, snap vào giữa ô khi thả hợp lệ, bật về nếu sai),
  giữ nguyên luồng GameController. Rồi M6 (bảng phong cấp + kết thúc ván rõ hơn), M7 (đóng gói portable).
