# Kế hoạch triển khai GUI cho cờ biến thể 10×10 (FairyZero)

> Tài liệu kế hoạch sơ bộ — bản chi tiết. Mục tiêu: có một **bàn cờ tương tác** mở lên là chơi
> được với engine, đóng gói thành **file `.exe` portable trên Windows**, và **kiến trúc mở** để
> sau này thêm tính năng phụ + lên **app Android offline dùng GPU điện thoại**.
>
> Ngày lập: 2026-06-23. Engine: `custom_engine.exe` (Fairy-Stockfish movegen + lc0 MCTS + ONNX NN).

---

## 0. Các quyết định đã chốt (locked)

| Hạng mục | Quyết định | Ghi chú |
|---|---|---|
| **Stack (nền công nghệ)** | **Flutter (ngôn ngữ Dart)** | Khuyến nghị; xem §1 giải thích cho người mới. |
| **Cách nối engine** | **Kiểu A — tiến trình con qua UCI** | GUI mở `custom_engine.exe --uci-nn` chạy ẩn, trao đổi bằng văn bản UCI. |
| **Trọng tài luật** | **Engine là nguồn chân lý** | GUI KHÔNG tự tính luật; hỏi engine nước hợp lệ + kết quả. |
| **Màn hình MVP** | **Chỉ có bàn cờ** | Không nút bấm. Cấu hình qua cờ lệnh terminal khi mở GUI. |
| **Nhập nước đi** | **Cả kéo-thả lẫn chạm-chạm** | Quân dính giữa ô khi đặt; lúc kéo quân đi theo con trỏ. |
| **Phong cấp** | **Bảng chọn nhỏ nổi trên bàn cờ** | Hiện hình 6 quân được phép phong (`b h m n v y`). |
| **Cấu hình lúc chạy** | **Cờ lệnh terminal** | model, màu người cầm, thời gian máy nghĩ, provider GPU... |
| **Ảnh quân** | Người dùng cung cấp (chess.com) | Quân tiêu chuẩn có sẵn; quân biến thể cần art riêng (xem §13). |
| **Mục tiêu kế tiếp** | Android offline + GPU | Giai đoạn 2, workstream riêng (xem §12). |

**Ngoài phạm vi MVP (làm sau):** đồng hồ, lịch sử nước đi dạng bảng, undo/redo, lưu/đọc PGN,
phân tích, menu cài đặt trên màn hình, người-đấu-người, nhiều bàn cờ. Kiến trúc §3–§4 chừa sẵn
chỗ ("slot") để gắn các thứ này về sau mà không phải đập đi xây lại.

---

## 1. Giải thích thuật ngữ (cho người mới làm GUI)

- **Stack / nền công nghệ:** bộ gồm *ngôn ngữ lập trình* + *thư viện vẽ giao diện* + *cách đóng
  gói thành app*. Ta chọn **Flutter**.
- **Flutter:** một bộ công cụ (framework) của Google để viết **một bộ mã chạy nhiều nền**: Windows,
  Android, iOS, web... Bạn vẽ giao diện bằng các **widget** (khối dựng sẵn: nút, ô, vùng vẽ...).
- **Dart:** ngôn ngữ lập trình của Flutter. Cú pháp gần C++/Java/JS — bạn biết C++ thì học rất nhanh,
  nhất là cho một bàn cờ đơn giản.
- **Widget:** "viên gạch" giao diện. Bàn cờ của ta sẽ là một widget tự vẽ (`CustomPainter`), quân
  cờ là các widget ảnh chồng lên trên (lớp `Stack`/`Positioned`).
- **Hot reload:** sửa code → bấm lưu → giao diện cập nhật ngay trong ~1 giây mà không mất trạng thái.
  Cực hợp để dò UI bàn cờ.
- **Tại sao Flutter chứ không Python/C++/Web?**
  - *Python (Pygame):* bạn biết Python nhưng **đường lên Android offline + GPU gần như bế tắc** →
    sau này phải viết lại GUI. Loại.
  - *C++ + SDL:* cùng ngôn ngữ engine, nhưng bạn đã chọn **Kiểu A** (engine là tiến trình riêng,
    chỉ nói chuyện bằng văn bản) nên lợi thế "link thẳng" mất; mà C++ GUI cho người mới + dựng
    Android NDK rất cực. Loại cho MVP.
  - *Web + Tauri:* được, nhưng Tauri-trên-Android kèm engine native là đường ít người đi.
  - *Flutter:* **một bộ mã giao diện chạy cả `.exe` Windows lẫn app Android native**; dễ học; dễ
    thêm nút/panel sau này; nối engine native trên Android bằng `dart:ffi` rất chuẩn. → **Chọn.**

---

## 2. Phạm vi MVP (cái phải có)

1. Mở `gui.exe` (kèm cờ lệnh) → cửa sổ hiện **bàn cờ 10×10** với quân ở vị trí xuất phát.
2. Người chơi cầm một màu (mặc định Trắng, đổi bằng cờ lệnh). Đi quân bằng **kéo-thả** hoặc
   **chạm-chạm**; chỉ cho đi **nước hợp lệ** (engine xác nhận); tô sáng ô đi được.
3. Tới lượt máy, máy **tự nghĩ và đi** (thời gian/visits theo cờ lệnh).
4. **Phong cấp:** khi tốt/sergeant tới hàng cuối, hiện **bảng chọn 6 quân**; người chọn → đi.
5. Phát hiện **kết thúc ván** (chiếu hết / hết nước / hòa / luật biến thể) và hiện kết quả tối giản
   (vd overlay chữ "Trắng thắng" / "Hòa").
6. Đóng gói thành **thư mục portable Windows** double-click hoặc chạy từ terminal kèm cờ.

---

## 3. Nguyên tắc kiến trúc chủ đạo

1. **Engine là nguồn chân lý về luật & trạng thái.** GUI không tự quyết nước nào hợp lệ, không tự
   tính chiếu/hết/hòa. Mọi câu hỏi luật → hỏi engine. Lý do: luật biến thể phức tạp (sergeant đôi
   bước, en passant trực giao + chéo Alfil, nhập thành `BIbi`, 12 loại quân, phong `b h m n v y`).
   Code lại bên Dart = nguồn lỗi khổng lồ và phải đồng bộ mãi.
2. **GUI là "renderer + input handler" đơn giản.** Giữ một *bản sao hiển thị* của bàn cờ (dựng từ
   FEN engine trả về) chỉ để vẽ; không bao giờ tự suy luật.
3. **Tách lớp rõ ràng** (§4) để: (a) thêm tính năng phụ sau này chỉ là thêm widget vào "slot"; (b)
   đổi cách nối engine (desktop subprocess ↔ Android FFI) chỉ thay **một** lớp, phần còn lại giữ nguyên.
4. **Cấu hình bằng cờ lệnh** đọc một lần lúc khởi động, gói trong một đối tượng `LaunchConfig`
   bất biến, truyền xuống các lớp. Sau này muốn có màn cài đặt thì chỉ việc cho UI ghi vào cùng
   cấu trúc đó.

---

## 4. Kiến trúc phân lớp

```
┌───────────────────────────────────────────────────────────────┐
│  LỚP TRÌNH BÀY (Presentation - widget Flutter)                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ BoardView (Stack)                                        │ │
│  │  • BoardPainter        – vẽ lưới 10×10, ô sáng/tối        │ │
│  │  • HighlightLayer      – tô ô nguồn + ô đích hợp lệ       │ │
│  │  • PieceLayer          – 1 PieceWidget / quân (Positioned)│ │
│  │  • DragLayer           – quân đang kéo bám con trỏ        │ │
│  │  • PromotionPopup       – bảng chọn 6 quân nổi trên bàn   │ │
│  │  • GameOverOverlay      – chữ kết quả (tối giản)          │ │
│  │  • [SLOT: Sidebar/Controls — để trống cho tính năng phụ] │ │
│  └──────────────────────────────────────────────────────────┘ │
│              ▲ đọc state, ▼ gửi ý định (intent)                │
├───────────────────────────────────────────────────────────────┤
│  LỚP TRẠNG THÁI/ĐIỀU PHỐI (Domain - không phụ thuộc Flutter)   │
│  • GameController   – máy trạng thái 1 ván: lượt ai, đang chờ  │
│                       engine?, áp dụng nước, kích hoạt phong   │
│  • BoardState       – 10×10 ô (quân gì, màu gì) — DỰNG TỪ FEN  │
│  • Move / Square    – kiểu dữ liệu nước đi & toạ độ            │
│  • LegalMoveSet     – tập nước hợp lệ hiện tại (từ engine)     │
│  • LaunchConfig     – cấu hình từ cờ lệnh (bất biến)           │
├───────────────────────────────────────────────────────────────┤
│  LỚP NỐI ENGINE (Engine integration - interface trừu tượng)   │
│  • EngineService (abstract): newGame(fen) / setPosition(moves) │
│      / legalMoves() / bestMove(timeOrNodes) / gameResult()     │
│      / currentFen()                                            │
│   ├─ UciProcessEngine  (DESKTOP) – spawn custom_engine.exe,    │
│   │                      nói UCI qua stdin/stdout              │
│   └─ NativeFfiEngine    (ANDROID, giai đoạn 2) – gọi .so qua   │
│                          dart:ffi, cùng giao thức              │
└───────────────────────────────────────────────────────────────┘
                         │ (desktop: pipe văn bản UCI)
                         ▼
                 [ custom_engine.exe --uci-nn ]
                   Fairy-Stockfish + MCTS + ONNX
```

**Điểm mấu chốt về khả năng mở rộng:**
- Thêm tính năng phụ (đồng hồ, lịch sử nước, undo...) = thêm widget vào **SLOT** + thêm trường vào
  `GameController`. Bàn cờ lõi không đổi.
- Lên Android = viết **`NativeFfiEngine`** cài cùng interface `EngineService`; toàn bộ lớp trình bày
  và điều phối **dùng lại nguyên xi**.

---

## 5. Giao thức GUI ↔ Engine (UCI + 2 lệnh bổ sung)

### 5.1 Lệnh `--uci-nn` đã có sẵn (xác nhận trong `uci_nn_engine.cc`)
- `uci` → in `id`, danh sách option, `uciok`.
- `isready` → dựng backend (nạp ONNX) rồi `readyok`.
- `setoption name <X> value <Y>` → vd `WeightsFile`, `Provider`, `Visits`, `Temperature`,
  `TempCutoffPly`, `PolicySoftmaxTemp`, `Threads`, ... (và passthrough tham số lc0).
- `ucinewgame` → reset về thế xuất phát.
- `position startpos moves <m1> <m2> ...` **hoặc** `position fen <FEN> moves ...`.
- `go movetime <ms>` | `go nodes <N>` | `go infinite` | `go wtime/btime ...` → trả `bestmove <uci>`.
- `stop`, `ponderhit`, `quit`.
- `d` → in tranh bàn cờ + dòng `Fen: <FEN>` ở **toạ độ thật** (file a–j, hàng 1–10).

> Provider GPU desktop: chạy engine với `--provider dml` (Windows, mọi GPU DX12 kể cả NVIDIA) hoặc
> `--provider cuda` (Colab/NVIDIA Linux). GUI chỉ việc truyền cờ này khi spawn.

### 5.2 Hai lệnh CẦN BỔ SUNG vào engine (nhỏ, xem §6)
- **`legalmoves`** → in một dòng tất cả nước hợp lệ ở thế hiện tại, dạng UCI thật, cách nhau bởi
  dấu cách, **có tiền tố `legalmoves`**. Ví dụ:
  `legalmoves b3b4 c3c4 ... f2f1b f2f1h f2f1m f2f1n f2f1v f2f1y` (dòng chỉ có `legalmoves` nếu hết nước).
  Dùng để: tô ô đi được, kiểm tra nước người đi, **phát hiện phong cấp** (nhiều nước cùng
  from+to khác hậu tố), và phát hiện "hết nước".
- **`result`** → in trạng thái ván: `result undecided` | `result white` | `result black` |
  `result draw`. (Tận dụng `ComputeGameResult()` đã dùng trong arena.)

> *Tùy chọn (không bắt buộc):* lệnh `fen` in đúng dòng FEN (gọn hơn việc parse output của `d`).
> Nếu không thêm, GUI parse dòng `Fen:` từ `d`.

### 5.3 Trình tự chuẩn

**Khởi động:**
```
GUI → engine:  uci
              setoption name WeightsFile value models/<model>.onnx
              setoption name Provider value dml         (hoặc cpu/cuda)
              setoption name Visits value 800           (mặc định lực máy)
              isready
engine → GUI:  uciok ... readyok
GUI → engine:  ucinewgame
              position startpos
              legalmoves      → lưu tập hợp lệ ban đầu
              d (hoặc fen)    → dựng BoardState để vẽ
```

**Người đi một nước (uci = "f2f4"):**
```
1. GUI kiểm tra "f2f4" có trong LegalMoveSet không.
   - Nếu có ≥2 nước cùng from=f2,to=f1 (khác hậu tố) → đây là PHONG CẤP:
       hiện PromotionPopup; người chọn quân X → uci := "f2f1X".
2. GUI cập nhật moves_history += uci; vẽ lạc quan (optimistic) quân về ô đích.
3. GUI → engine: position startpos moves <... f2f4>
                 result        → nếu khác undecided: kết thúc ván, hiện overlay.
                 (nếu chưa kết thúc → tới lượt máy, sang khối dưới)
```

**Máy đi:**
```
GUI khoá nhập (đang là lượt máy).
GUI → engine:  go movetime <ms>        (hoặc go nodes <visits>)
engine → GUI:  info ... ; bestmove <uci>
GUI:           áp dụng <uci> vào BoardState (engine nhập thành/ăn qua đường/phong
               đều nằm trong chuỗi uci này), animate quân về ô đích (snap giữa ô).
GUI → engine:  position startpos moves <... bestmove>
               legalmoves   → tập hợp lệ mới cho người
               result       → kiểm tra kết thúc
Mở khoá nhập cho người.
```

**Lưu ý nhất quán:** luôn gửi `position startpos moves <toàn bộ lịch sử>` (engine có cơ chế
*tree-reuse* nhận ra phần mở rộng và giữ lại cây tìm kiếm — không tốn thêm chi phí). Tránh tự
"đoán" thế cờ phía GUI.

---

## 6. Phần engine cần bổ sung (C++, nhỏ)

> ✅ **ĐÃ TRIỂN KHAI (M1, 2026-06-23)** trong `src/app/uci_nn_engine.cc` (vòng lặp `Loop()`, ngay
> sau lệnh `d`). Đã build `build` (CPU) + `build-dml` và test tay. Định dạng output thực tế:
> - `legalmoves <m1> <m2> ...` (một dòng; chỉ `legalmoves` nếu hết nước)
> - `result undecided|white|black|draw`
> - `fen <FEN một dòng, toạ độ thật>`
> Hiệu năng `legalmoves`: movegen native `ChessBoard::GenerateLegalMoves()` + một `std::string`
> đã `reserve` + một lần `Send` (không flush từng token). Lưu ý: `fen` của FSF in castling dạng
> `KQkq` (nội bộ) thay cho nhãn `BIbi` — không ảnh hưởng GUI (chỉ dùng phần bố trí quân để vẽ).

Thêm vào `UciNnEngine::Loop()` trong `src/app/uci_nn_engine.cc` hai nhánh lệnh, theo đúng style
hiện có (đã có `CanonicalMoveToUci`, `ComputeGameResult`, movegen):

- **`legalmoves`**: lấy `board = tree_->GetPositionHistory().Last().GetBoard()`, sinh danh sách
  nước hợp lệ (qua lớp movegen/board sẵn có — cùng nguồn mà `UciToCanonicalMove` kiểm tra), đổi
  từng nước sang UCI bằng `CanonicalMoveToUci(m, blackToMove)`, in một dòng `legal m1 m2 ...`.
- **`result`**: gọi `tree_->GetPositionHistory().ComputeGameResult()` (enum
  `UNDECIDED/WHITE_WON/BLACK_WON/DRAW`) → in `result undecided|white|black|draw`.
- *(tuỳ chọn)* **`fen`**: in dòng FEN thật (rút từ cùng nguồn mà `d` dùng).

Đây là thay đổi cô lập, không đụng tới logic tìm kiếm; build lại `ninja -C build` (và `build-dml`).
Sau khi có 2 lệnh này, GUI **không cần biết một luật biến thể nào**.

> Kiểm tra nhỏ trước khi code GUI: chạy tay
> `custom_engine.exe --uci-nn` rồi gõ `position startpos` / `legalmoves` / `result` / `d` để xác
> nhận định dạng đầu ra, vì GUI sẽ parse đúng các dòng này.

---

## 7. Mô hình dữ liệu & hệ toạ độ

- **Bàn cờ:** 10×10. **File** a–j (cột, chỉ số 0..9), **rank** 1–10 (hàng, chỉ số 0..9).
  Lưu ý **hàng 10 là hai ký tự** trong UCI (vd `e10`, `f4e3h`). Parser UCI phải xử lý đúng:
  đọc file (1 ký tự a–j) rồi rank (1–2 ký tự số), có thể kèm **hậu tố phong** (một chữ trong
  `b h m n v y`). Ví dụ: `e10i6`, `f2f1h`.
- **FEN xuất phát:**
  `vrhbakberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHBAKBERV w BIbi - 7+7 0 1`
  (FEN liệt kê hàng 10 → hàng 1 từ trên xuống; HOA = Trắng ở hàng 1–2 dưới đáy, thường = Đen ở
  hàng 9–10 trên đỉnh).
- **12 loại quân (ký tự → tên):** `p` tốt, `n` mã, `b` tượng, `r` xe, `k` vua, `v` customPiece1,
  `h` archbishop (mã+tượng), `a` amazon (hậu+mã), `e` chancellor (xe+mã), `m` centaur, `s` sergeant
  (tốt đặc biệt, đôi bước), `y` customPiece2. HOA=Trắng, thường=Đen. (GUI chỉ cần ảnh theo
  ký tự+màu; **không cần biết cách đi**.)
- **BoardState** = mảng 100 ô, mỗi ô `null` hoặc `(letter, color)`, dựng bằng cách parse FEN engine
  trả về sau mỗi nước. Đây là dữ liệu DUY NHẤT để vẽ.
- **Hướng bàn:** mặc định Trắng ở đáy. Nếu người cầm Đen (`--play-black`-kiểu), lật bàn để quân
  người ở đáy (chỉ là phép ánh xạ toạ-độ-hiển-thị; logic & UCI vẫn dùng toạ độ thật).

---

## 8. Thiết kế tương tác chi tiết

**Kéo-thả (drag):**
- Nhấn xuống quân của mình → quân được "nhấc" lên `DragLayer` và **bám theo con trỏ/ngón tay**.
- Khi bắt đầu kéo, tô sáng ô nguồn + tất cả ô đích hợp lệ của quân đó (lọc từ `LegalMoveSet`).
- Thả: nếu rơi vào ô đích hợp lệ → áp dụng nước, quân **dính vào giữa ô** (animate ngắn về tâm ô).
  Nếu rơi vào ô không hợp lệ → quân **bật về** ô nguồn (animate về tâm).

**Chạm-chạm (tap):**
- Chạm ô nguồn (quân mình) → chọn, tô sáng ô nguồn + ô đích hợp lệ.
- Chạm ô đích hợp lệ → áp dụng nước (quân về giữa ô). Chạm chỗ khác → bỏ chọn. Chạm quân mình khác
  → đổi lựa chọn.

**Snap giữa ô:** mọi quân khi đứng yên luôn căn giữa ô (dùng `Positioned` theo tâm ô). Khi kéo thì
bám con trỏ; khi thả/chọn-xong thì animate về tâm ô đích.

**Phong cấp (PromotionPopup):**
- Kích hoạt khi nước người định đi có ≥2 biến thể cùng from+to khác hậu tố trong `LegalMoveSet`.
- Hiện bảng nhỏ **nổi ngay trên/cạnh ô đích**, gồm hình các quân được phép (đúng tập hậu tố engine
  liệt kê — thường `b h m n v y`, đúng màu người chơi). Chọn quân → ghép hậu tố → đi. Bấm ra ngoài
  → huỷ nước (quân về ô nguồn).

**Lượt máy:** khoá nhập trong lúc máy nghĩ (đơn giản: bỏ qua thao tác chuột; sau này có thể thêm
indicator "đang nghĩ..." vào SLOT). Khi có `bestmove` → animate quân máy về giữa ô đích.

**Kết thúc ván:** khi `result` ≠ undecided → `GameOverOverlay` hiện chữ kết quả; bàn cờ khoá. (Nút
"ván mới" để sau; tạm thời đóng app rồi mở lại, hoặc thêm sau vào SLOT.)

---

## 9. Cấu trúc thư mục mã nguồn Flutter (đề xuất)

```
gui/                              # dự án Flutter (tách khỏi custom_engine)
  pubspec.yaml                    # khai báo phụ thuộc + assets (ảnh quân)
  assets/pieces/                  # 24 ảnh: w_p.png,b_p.png,... w_v.png,b_v.png,...
  lib/
    main.dart                     # đọc cờ lệnh -> LaunchConfig -> chạy app
    config/launch_config.dart     # parse args: --model --provider --visits --movetime --black ...
    domain/
      square.dart  move.dart      # kiểu toạ độ & nước đi (parse UCI, kể cả hàng 10 + hậu tố)
      board_state.dart            # parse FEN -> 100 ô; tiện ích lật bàn
      legal_move_set.dart         # tra cứu theo ô nguồn; phát hiện phong cấp
      game_controller.dart        # máy trạng thái ván; điều phối engine
    engine/
      engine_service.dart         # interface trừu tượng
      uci_process_engine.dart     # DESKTOP: spawn + nói UCI (Process, stdin/stdout)
      (native_ffi_engine.dart)    # ANDROID giai đoạn 2
    ui/
      board_view.dart             # Stack ghép các lớp
      board_painter.dart          # vẽ lưới + ô sáng/tối
      piece_layer.dart  piece_widget.dart
      drag_layer.dart  highlight_layer.dart
      promotion_popup.dart  game_over_overlay.dart
  windows/                        # phần Flutter sinh ra để build .exe Windows
  android/                        # (giai đoạn 2)
```

---

## 10. Thư mục portable phát hành (Windows)

`flutter build windows` tạo ra một thư mục chạy được. Ta gói lại thành:

```
FairyZeroGUI/
  gui.exe                         # app Flutter (cửa sổ bàn cờ)
  flutter_windows.dll, data/...   # runtime Flutter (Flutter sinh tự động)
  engine/
    custom_engine.exe             # engine (build-dml để dùng GPU)
    DirectML.dll, onnxruntime*.dll# thư viện kèm engine
    models/<model>.onnx
  assets/pieces/...               # (đã nhúng trong data/ của Flutter)
  play.bat                        # ví dụ khởi chạy kèm cờ lệnh
```

`play.bat` ví dụ:
```bat
gui.exe --engine engine\custom_engine.exe --model engine\models\gen12.onnx ^
        --provider dml --movetime 5000
```
Hoặc double-click `gui.exe` để chạy với mặc định (CPU, model mặc định). Cờ lệnh GUI gồm tối thiểu:
`--engine <path>`, `--model <onnx>`, `--provider cpu|dml|cuda`, `--movetime <ms>` hoặc
`--visits <N>`, `--black` (người cầm Đen), `--start-fen <FEN>` (tuỳ chọn).

---

## 11. Lộ trình theo cột mốc (Windows MVP trước)

| Mốc | Nội dung | Tiêu chí hoàn thành |
|---|---|---|
| **M0** | Dựng khung Flutter chạy được cửa sổ trống trên Windows; parse cờ lệnh → `LaunchConfig`. | `flutter run -d windows` mở cửa sổ; in ra config đọc được. |
| **M1** ✅ | Engine bổ sung `legalmoves` + `result` (+ `fen`) (§6), build lại, test tay. | XONG: build CPU+DML, test tay ra đúng định dạng. |
| **M2** ✅ | `UciProcessEngine`: spawn engine, làm trình tự khởi động, lấy FEN + legalmoves. | XONG: `EngineService`+`UciProcessEngine`+`tool/m2_smoke.dart`; chạy thật ra FEN+34 nước+result; bonus go→bestmove OK. |
| **M3** ✅ | Vẽ bàn tĩnh từ FEN: lưới 10×10 + quân (SVG) căn giữa ô; lật bàn nếu `--black`; royal symbol góc quân vua. | XONG: golden PNG đúng màu/loại/royal; engine wired runtime OK; full test 4/4. |
| **M4** ✅ | Nhập nước: chạm-chạm, tô sáng ô hợp lệ, gửi nước, máy đáp. | XONG: GameController + tô sáng (golden); app thật `--demo-move` f3f5 → máy đáp b8b6; test 8/8. |
| **M5** ✅ | Kéo-thả: quân bám con trỏ, thả hợp lệ thì vào giữa ô, sai thì về chỗ cũ. | XONG: BoardView stateful + lớp kéo riêng; mô phỏng chuột kéo e3→e5 thật → máy đáp; test 11/11. (animate mượt = polish sau) |
| **M6** ✅ (sớm) | Phong cấp (bảng chọn) + phát hiện kết thúc (`result`) + overlay kết quả. | XONG: bảng chọn 6 quân (golden+test); overlay kết quả ở M4. |
| **M7** | Đóng gói portable Windows (§10) + `play.bat`; thử trên máy khác. | Bạn của bạn (NVIDIA/Windows) mở chơi được, dùng GPU (`--provider dml`). |

(Phong cấp đặt sau kéo-thả vì nó dựa trên `LegalMoveSet`, nhưng có thể làm sớm hơn nếu muốn.)

---

## 12. Định hướng Android (Giai đoạn 2 — workstream riêng)

Mục tiêu: app **offline**, engine chạy **cục bộ trên điện thoại**, **dùng GPU điện thoại**.

1. **Port engine sang Android (arm64) thành thư viện `.so`** qua Android NDK (engine vốn đã là C++,
   chủ yếu là dựng toolchain + meson cross-file + cross-compile Fairy-Stockfish core + MCTS).
   - **KHÔNG có rào cản PEXT:** build dùng `-DPRECOMPUTED_MAGICS` (magic bitboard dựng sẵn,
     C++ thuần) chứ không phải `-DUSE_PEXT` → chạy tốt trên ARM.
   - **Rào cản SIMD thật sự = AVX2:** `meson.build` thêm `/arch:AVX2` (MSVC) / `-mavx2 -mfma` (x86)
     và có intrinsic `_mm256_*` (vd softmax `onnx_backend.cc`) → trên ARM cần **fallback NEON hoặc
     scalar** (`#ifndef __AVX2__`). Việc vừa phải, vài hàm nhỏ.
2. **ONNX Runtime cho Android** thay cho bản desktop: dùng **execution provider tăng tốc phần cứng**
   — **NNAPI** (uỷ thác cho GPU/DSP/NPU của máy) hoặc **XNNPACK**/**QNN** tuỳ chip. Đây là phần
   "kích GPU điện thoại"; **độc lập với lựa chọn GUI**, là việc của lớp engine.
3. **Thay lớp nối:** viết **`NativeFfiEngine`** (cài cùng interface `EngineService`) gọi thẳng các
   hàm trong `.so` bằng **`dart:ffi`** — thay cho việc spawn tiến trình (Android không spawn process
   kiểu desktop). Giao thức nội bộ vẫn là chuỗi văn bản kiểu UCI (`setPosition`/`legalMoves`/
   `bestMove`/`result`) để tái dùng tối đa logic.
4. **Toàn bộ lớp trình bày + điều phối + parse dùng lại nguyên xi.** Cảm ứng (drag/tap) đã hỗ trợ
   sẵn vì Flutter dùng chung gesture cho chuột & ngón tay.
5. **Đóng gói:** nhúng `.so` + model `.onnx` + ảnh quân vào APK; build `flutter build apk`.

*Lưu ý độ chín:* đường NNAPI/GPU trên Android có thể cần tinh chỉnh theo từng dòng máy; nên coi
đây là giai đoạn tách bạch, làm sau khi MVP Windows ổn.

---

## 13. Tài sản cần bạn cung cấp (ảnh quân)

- Cần **24 ảnh PNG nền trong suốt** = 12 loại × 2 màu. Đặt tên theo quy ước:
  `w_<letter>.png` / `b_<letter>.png` với `<letter>` ∈ `p n b r k v h a e m s y`.
  (vd `w_p.png`, `b_v.png`, `w_a.png`...).
- **Quân tiêu chuẩn** (`p n b r k`) lấy từ chess.com được.
- **Quân biến thể** (`v h a e m s y`) chess.com **không có sẵn** (amazon/chancellor/centaur/sergeant/
  customPiece...). Phương án: mượn tạm ảnh quân tiêu chuẩn gần nghĩa (vd amazon ≈ hậu, archbishop ≈
  tượng+mã ghép, sergeant ≈ tốt khác nền...) hoặc tự thêm phù hiệu. **Trước khi có art**, M3 có
  thể render tạm bằng **chữ cái + màu** để không bị chặn tiến độ.
- Khi bạn gửi ảnh, cho biết kích thước (nên ≥ 128×128, vuông) để tôi cấu hình `pubspec.yaml` +
  `assets/pieces/`.

---

## 14. Rủi ro & cách giảm thiểu

| Rủi ro | Giảm thiểu |
|---|---|
| Bạn mới với Dart/Flutter | Bàn cờ đơn giản; đi từng mốc M0→M7; tận dụng hot reload; tôi đi kèm code mẫu từng bước. |
| Parse UCI sai (hàng 10, hậu tố phong) | Viết hàm parse + **unit test Dart** cho các ca: `e10`, `f2f1h`, nhập thành, ăn qua đường. |
| GUI tự suy luật → sai/lệch engine | Tuyệt đối theo §3: chỉ engine quyết. GUI chỉ dùng `legalmoves`/`result`. |
| Engine khởi động chậm (nạp ONNX) | Gọi `isready` lúc mở app, hiện bàn ngay; chỉ khoá khi thật sự chờ `bestmove`. |
| GPU desktop không bật | Truyền `--provider dml` (Windows) / `cuda`; GUI in cảnh báo nếu engine báo fallback CPU. |
| Android NNAPI/GPU khó | Tách hẳn Giai đoạn 2; chấp nhận fallback CPU nếu cần; thử trên máy thật sớm. |
| Định dạng output engine đổi | M1 chốt định dạng `legalmoves`/`result`/`d`; GUI parse phòng thủ (bỏ qua dòng lạ). |

---

## 15. Bước tiếp theo đề xuất

1. **Bạn:** xác nhận kế hoạch + quyết mặc định thời gian máy nghĩ (vd `movetime 5000ms`) và provider
   mặc định (cpu hay dml).
2. **Tôi (khi bạn đồng ý):** làm **M1** trước — thêm `legalmoves` + `result` vào `uci_nn_engine.cc`,
   build, test tay (đây là phần engine, không phụ thuộc Flutter, dùng được ngay).
3. Cài Flutter SDK (tôi sẽ hướng dẫn cụ thể Windows), dựng **M0** rồi tiến dần.
4. Bạn gửi ảnh quân khi tiện; trước đó M3 render bằng chữ cái.

> Các điểm còn để ngỏ (quyết khi tới mốc tương ứng): mặc định movetime/visits; có nút "ván mới"
> tối giản ở M6 hay để hẳn giai đoạn sau.

---

## 16. Chốt bổ sung sau khi bàn (2026-06-23)

**Quyết định UI đã chốt:**
- **Lật bàn khi cầm Đen:** CÓ (quân người luôn ở đáy).
- **Cửa sổ:** co giãn được nhưng **khoá tỉ lệ w:h** (bàn vuông); dùng `window_manager` (Flutter
  Windows) để set min-size + aspect ratio. Kích thước mặc định do GUI chọn.
- **Màu ô bàn cờ (chuẩn chess.com):** ô sáng `#eeeed2`, ô tối `#769656`. (Đưa vào `BoardPainter`.)

**"Ván mới" & điều khiển — không cần phần tử trên màn hình:**
- **Phím tắt trong cửa sổ** (luôn hoạt động): vd `N` = ván mới, `F` = lật bàn. Không phải "nút",
  không thêm UI.
- **Kênh điều khiển qua stdin của GUI** (tùy chọn, khi MỞ TỪ TERMINAL): GUI đọc stdin của *chính
  nó* ở một isolate nền, nhận lệnh gõ tay: `newgame`, `flip`, `fen <...>`, `movetime <ms>`... →
  "control plane" sơ khai, dễ mở rộng. *Đánh đổi:* double-click `gui.exe` không có stdin → kênh
  này không khả dụng (vẫn chơi được; ván mới = phím tắt/mở lại). Đừng nhầm kênh này với pipe
  GUI↔engine (pipe đó là UCI nội bộ, ẩn).

**Làm rõ hiệu năng & cơ chế (kết quả thảo luận):**
- **Nước hợp lệ của một quân** (chạm-chạm): KHÔNG hỏi engine riêng — **lọc `LegalMoveSet` theo ô
  nguồn** phía Dart, tức thì. Chỉ cần 1 lần `legalmoves`/lượt.
- **Hiệu năng pipe:** GUI↔engine qua **pipe trong bộ nhớ**, không phải terminal hiển thị. Truyền
  vài trăm byte + parse = micro-giây, không đáng kể so với thời gian `go` (giây). Đây là cách mọi
  GUI cờ điều khiển mọi engine UCI. Bắt buộc: **đọc output engine bất đồng bộ** (Stream/isolate).
- **`d` vs `fen`:** không parse ASCII của `d`; thêm lệnh `fen` in đúng 1 dòng FEN cho GUI vẽ.
- **GUI dựng lại bàn từ FEN sau mỗi nước** (thay vì tự áp dụng) để khỏi xử lý nhập thành/ăn qua
  đường/phong — chi phí micro-giây, đổi lấy "không cần biết luật". Có thể vẽ lạc quan rồi đồng bộ.

**Cơ chế "200 → 100" (đã truy ra) × tree-reuse:**
- Vị trí: `NodeTree::MakeMove` (`src/search/classic/node.cc:487`): khi `history_.GetLength() >= 200`
  gọi `history_.TrimHistory(100)` (giữ 100 ply cuối) → để **mảng tĩnh 512 ply** không đầy,
  Expand-copy luôn rẻ. `TrimHistory` (`position.cc:94`) yêu cầu `keep_count >= 100` (đủ luật 50
  nước = 100 ply; input lịch sử NN chỉ cần ~8 thế) → không mất chính xác.
- **Độc lập với tree-reuse:** trim chỉ tỉa *mảng lịch sử thế cờ*, KHÔNG đụng (a) cây MCTS
  (`current_head_`) và (b) sổ ghi `current_startfen_`/`current_moves_` trong `UciNnEngine`. Nên đi
  qua mốc ply 200 **không mất tree-reuse**.
- **Tree-reuse với `fen` + `moves`:** hữu dụng NẾU giữ **FEN gốc cố định** + chỉ **nối thêm** moves
  (`position fen <FEN_CỐ_ĐỊNH> moves ...` lớn dần). ⚠️ Cạm bẫy: gửi `position fen <FEN_MỚI mỗi lượt>`
  → đổi `current_startfen_` → reuse luôn fail → cây nguội mỗi nước. ⇒ GUI LUÔN gửi **gốc cố định +
  moves lớn dần** (đã nêu §5.3).
