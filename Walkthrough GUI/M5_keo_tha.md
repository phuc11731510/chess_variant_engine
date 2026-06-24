# Walkthrough — GUI Mốc M5: Kéo-thả quân cờ

> Đợt: **2026-06-24**. Mục tiêu M5 (plan §8/§11): kéo-thả — quân bám con trỏ khi kéo, thả vào ô hợp
> lệ thì vào giữa ô, thả sai thì về chỗ cũ; **giữ song song chạm-chạm (M4)**.
>
> **Kết quả: M5 ✅ HOÀN TẤT** — unit test logic + mô phỏng chuột THẬT kéo e3→e5 (máy đáp) xác nhận.

---

## 0. TL;DR

| Việc | Kết quả |
|---|---|
| Sửa | `ui/board_view.dart` (→ StatefulWidget, thêm kéo-thả), `domain/game_controller.dart` (+beginDrag/endDrag/cancelDrag), `main.dart` (nối callback) |
| Verify | test 11/11 (gồm kéo-thả) + chụp app sau khi mô phỏng chuột kéo e3→e5 → máy đáp i8i6 |

---

## 1. Thiết kế

`BoardView` đổi thành **StatefulWidget** để giữ trạng thái kéo cục bộ:
- `GestureDetector` có **cả** `onTapUp` (chạm-chạm — M4 nguyên vẹn) lẫn `onPanStart/Update/End` (kéo).
  Flutter tự phân xử: chạm tại chỗ → tap; di chuyển quá ngưỡng → kéo. Hai cách **dùng song song**.
- **Logic chọn/đi dùng chung** với chạm-chạm, đặt trong `GameController`:
  - `bool beginDrag(int r,int f)` — nhấc quân (như chọn); true nếu được phép.
  - `void endDrag(int r,int f)` — thả: ô hợp lệ → đi (hoặc hiện bảng phong cấp); sai → bỏ chọn.
  - `void cancelDrag()`.
- **Quân đang kéo** vẽ ở **lớp riêng** bám con trỏ: vị trí giữ trong `ValueNotifier<Offset?>`, chỉ
  `ValueListenableBuilder` của lớp đó rebuild mỗi khung hình (không rebuild cả bàn). Quân gốc bị **ẩn
  khỏi ô nguồn** trong lúc kéo (lớp quân tĩnh bỏ qua ô `_dragFrom`).
- **Thả hợp lệ** → `endDrag` đi nước → bàn refresh từ FEN → quân hiện ở ô đích (≈ "snap giữa ô").
  **Thả sai** → bỏ chọn → quân gốc hiện lại ô cũ (≈ "bật về"). (Animate trượt mượt = polish sau.)

---

## 2. Kiểm thử

- **Unit** (`widget_test.dart`): `beginDrag` ô quân mình → true + tô ô đích; ô trống → false;
  `endDrag` ô hợp lệ → đi + máy đáp; ô sai → bỏ chọn, không đi.
- **Render tĩnh không đổi**: các golden bàn cờ vẫn **pass** (so khớp ảnh cũ) → refactor không phá hiển thị.
- **Kéo-thả THẬT trong app**: dùng `SetCursorPos` + `mouse_event` (Win32) mô phỏng chuột kéo tốt
  **e3→e5** trên cửa sổ app → ảnh chụp: tốt Trắng sang e5, e3 trống, **máy đáp i8→i6**. ✓
- `flutter analyze` sạch, `flutter test` **11/11**.

> Mẹo auto-test kéo: tính ô bàn cờ từ `GetWindowRect` (ước lượng title-bar + padding), `SetCursorPos`
> tới tâm ô nguồn → `mouse_event LEFTDOWN` → di từng bước tới ô đích (kích onPanUpdate) → `LEFTUP`.

---

## 3. Trạng thái & bước tiếp

- **M5 ✅ DONE.** Chơi được bằng **cả kéo-thả lẫn chạm-chạm**.
- **Chưa commit** (người dùng tự commit).
- Còn lại: **M7** = đóng gói portable (gói GUI + engine + model + DLL + assets) + `window_manager`
  khoá tỉ lệ w:h + min-size (cửa sổ hiện còn hơi cắt đáy trên màn hình thấp/DPI cao). (M6 phong cấp +
  kết thúc ván đã xong sớm.) Polish tuỳ chọn: animate quân máy trượt mượt.
