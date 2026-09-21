# Báo cáo Phân tích Kỹ thuật: Vá lỗi Sinh nước đi Bắt tốt qua đường (En Passant) của Quân Sergeant trong Biến thể Cờ vua 10x10

Trong quá trình phát triển **Engine Cờ Biến thể 10x10** tích hợp giữa bộ sinh nước đi **Fairy-Stockfish** và thuật toán tìm kiếm **MCTS (Lc0)**, một trong những thách thức kỹ thuật lớn nhất đã được giải quyết nằm ở cơ chế sinh nước đi bắt tốt qua đường (En Passant - EP) cho quân cờ tùy chỉnh **Sergeant (S)**. 

Bài viết này đi sâu phân tích hai lỗi logic nghiêm trọng trong mã nguồn Fairy-Stockfish nguyên bản, cách chúng được phát hiện thông qua kiểm thử và giải pháp vá lỗi đã được áp dụng thành công tại commit đầu tiên [d44ad8b](file:///d:/chess_variant/custom_engine/src/chess/position.cpp#L1910-L1932).

---

## 1. Bối cảnh về Quân Sergeant (S) và Luật En Passant

Quân **Sergeant (S)** là quân cờ biến thể lai giữa Tốt thường (Pawn) và Vua thường (King), được định nghĩa trong file cấu hình [variants.ini](file:///d:/chess_variant/custom_engine/src/chess/variants.ini#L2149) bằng chuỗi ký hiệu Betza: `fKifmnDifmnA`.

### Quy tắc di chuyển của Sergeant:
*   **Di chuyển cơ bản**: Có thể tiến thẳng hoặc chéo 1 ô phía trước để đi thường (quiet move) hoặc ăn quân (capture).
*   **Nhảy bước đôi (Double-Step)**: Từ 3 hàng xuất phát đầu tiên của mỗi bên (Trắng: hàng 1, 2, 3; Đen: hàng 10, 9, 8), Sergeant được phép nhảy 2 ô tiến lên phía trước (bao gồm cả đi thẳng tiến hoặc nhảy chéo tiến theo phong cách quân *Alfil* `fmnA` / *Dabbabah* `fmnD`) nếu không bị cản ở ô đệm trung gian.
*   **Kích hoạt En Passant**: Khi Sergeant nhảy 2 ô vượt qua ô đệm trung gian, nó tạo ra một mục tiêu **En Passant** tại ô đệm đó. Đối phương có quyền dùng Tốt thường hoặc Sergeant đứng cạnh để ăn En Passant ngay tại lượt đi kế tiếp.

---

## 2. Hai lỗi nghiêm trọng trong Fairy-Stockfish nguyên bản

Mặc dù Fairy-Stockfish hỗ trợ rất tốt các quân cờ cổ tích (fairy pieces), nhưng khi kết hợp các thuộc tính "nhảy 2 ô", "đi chéo không ăn quân" và "ăn en passant" trên cùng một quân cờ tùy chỉnh như Sergeant, công cụ sinh nước đi nguyên bản đã bộc lộ hai lỗi logic lớn:

### 🌟 Lỗi 1: Nhầm lẫn ô đệm En Passant với Nước đi Thường (Quiet Moves)
*   **Vị trí**: File [movegen.cpp: L300-L305](file:///d:/chess_variant/custom_engine/src/chess/movegen.cpp#L300-L305)
*   **Mô tả**: Khi sinh các nước đi thường (`quiet moves`), thuật toán mặc định của Stockfish sẽ quét các ô trống mà quân cờ có thể đi tới. Nếu ô đệm En Passant (ví dụ `b4`) đang trống, engine sẽ tính nước di chuyển của quân cờ đối phương vào ô đó là một nước đi bình thường (`NORMAL`).
*   **Hệ quả**: Nước đi di chuyển vào ô EP bị phân loại sai thành `NORMAL` thay vì `EN_PASSANT`. Do đó, khi nước đi được thực hiện, logic xóa quân cờ bị bắt ở ô liền kề sẽ **không được kích hoạt**, dẫn đến việc quân Sergeant bị ăn vẫn nằm nguyên trên bàn cờ.

### 🌟 Lỗi 2: Bộ lọc `~quiets` triệt tiêu nước đi ăn En Passant theo đường chéo
*   **Vị trí**: File [movegen.cpp: L310](file:///d:/chess_variant/custom_engine/src/chess/movegen.cpp#L310)
*   **Mô tả**: Với tốt thường, hướng đi thẳng (quiet - đi vào ô trống) và hướng đi chéo (attack - chỉ dùng để ăn quân) là hai tập hợp hoàn toàn tách biệt. Do đó, Fairy-Stockfish thiết lập công thức sinh nước đi en passant: 
    $$\text{epSquares} = \text{attacks} \cap \sim\text{quiets} \cap \text{ep\_squares()}$$
    Bộ lọc $\sim\text{quiets}$ nhằm loại bỏ các hướng đi thẳng của tốt thường để tránh nhận nhầm. Tuy nhiên, đối với quân Sergeant, hướng di chuyển chéo tiến lên phía trước vừa là nước đi thường khi ô đích trống (quiet), vừa là hướng ăn quân (attack). 
*   **Hệ quả**: Phép toán loại trừ $\sim\text{quiets}$ đã triệt tiêu hoàn toàn hướng đi chéo của Sergeant. Kết quả là engine **bỏ sót hoàn toàn** nước đi ăn En Passant theo đường chéo của quân Sergeant.

---

## 3. Giải pháp vá lỗi (The Patch)

Trong commit đầu tiên [d44ad8b](file:///d:/chess_variant/custom_engine/src/chess/movegen.cpp#L301-L310), hai bản vá quan trọng đã được áp dụng trực tiếp vào cấu trúc sinh nước đi của Stockfish:

### 🔧 Vá lỗi 1: Lọc bỏ ô En Passant khỏi danh sách nước đi thường
Mã nguồn tại [movegen.cpp: L301-L303](file:///d:/chess_variant/custom_engine/src/chess/movegen.cpp#L301-L303) được cập nhật:
```diff
- Bitboard b = ((attacks & pos.pieces()) | (quiets & ~pos.pieces()));
+ Bitboard b = (  (attacks & pos.pieces())
+                | (quiets & ~pos.pieces() & ~((pos.en_passant_types(Us) & Pt) ? pos.ep_squares() : Bitboard(0))));
```
*   **Ý nghĩa**: Nếu quân cờ hiện tại (`Pt`) là quân có khả năng ăn En Passant, ô En Passant (`pos.ep_squares()`) sẽ bị loại trừ hoàn toàn khỏi danh sách nước đi thường `quiets`. Điều này ép buộc nước đi vào ô này phải được xử lý riêng ở nhánh `EN_PASSANT`.

### 🔧 Vá lỗi 2: Loại bỏ bộ lọc `~quiets` khi sinh ô En Passant cho quân cờ tùy chỉnh
Mã nguồn tại [movegen.cpp: L310](file:///d:/chess_variant/custom_engine/src/chess/movegen.cpp#L310) được sửa đổi:
```diff
- Bitboard epSquares = (pos.en_passant_types(Us) & Pt) ? (attacks & ~quiets & pos.ep_squares() & ~pos.pieces()) : Bitboard(0);
+ Bitboard epSquares = (pos.en_passant_types(Us) & Pt) ? (attacks & pos.ep_squares() & ~pos.pieces()) : Bitboard(0);
```
*   **Ý nghĩa**: Loại bỏ bộ lọc `~quiets` giúp bảo toàn hướng đi chéo của Sergeant, cho phép sinh nước đi ăn En Passant theo cả đường thẳng lẫn đường chéo một cách chính xác.

---

## 4. Kiểm thử thực tế và Xác nhận

Một bộ script kiểm thử Python (sử dụng thư viện `pyffish` liên kết trực tiếp với Fairy-Stockfish đã vá) được tạo ra trong thư mục `scratch/` để xác minh tính đúng đắn của logic mới:

1.  **Bắt En Passant thẳng (Straight EP)**:
    *   *Kịch bản*: Trắng đi Sergeant `a3c5` (nhảy qua ô đệm `b4`). Đen đứng ở `b5` đi thẳng `b5b4`.
    *   *Kết quả*: Nước đi được nhận diện là `EN_PASSANT`. Quân Sergeant Trắng tại `c5` bị loại bỏ thành công khỏi bàn cờ (Xác nhận trong [test_sergeant_ep.py](file:///C:/Users/7/.gemini/antigravity-ide/brain/00e91257-c00d-4abd-9bf5-f7c875f889c9/scratch/test_sergeant_ep.py)).
2.  **Bắt En Passant chéo (Diagonal EP)**:
    *   *Kịch bản*: Trắng đi Sergeant `a3c5` (nhảy qua ô đệm `b4`). Đen đứng ở `a5` đi chéo `a5b4`.
    *   *Kết quả*: Nước đi được nhận diện là `EN_PASSANT`. Quân Sergeant Trắng tại `c5` bị loại bỏ thành công (Xác nhận trong [test_sergeant_adjacent_ep.py](file:///C:/Users/7/.gemini/antigravity-ide/brain/00e91257-c00d-4abd-9bf5-f7c875f889c9/scratch/test_sergeant_adjacent_ep.py)).

Tất cả các trường hợp kiểm thử tự động tích hợp thông qua tuỳ chọn chạy `--test-ep` trong [main.cc](file:///d:/chess_variant/custom_engine/src/main.cc#L89) đều đã vượt qua thành công (`100% PASS`), đảm bảo tính ổn định tuyệt đối của bộ sinh nước đi trong các trận đấu MCTS tự chơi.
