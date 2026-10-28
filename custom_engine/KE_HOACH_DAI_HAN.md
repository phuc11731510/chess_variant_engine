# Kế hoạch dài hạn (CHƯA LÀM)

Ghi lại mong muốn dài hạn của chủ dự án (2026-10-28). Chưa có mã nào được viết cho các mục dưới đây; vòng học tăng cường hiện tại giữ nguyên.

## 1. Lưu dữ liệu ván đấu đời 491–990

- Giữ toàn bộ ván tự đấu từ đời 491 tới đời 990, mỗi ván nguyên vẹn (không lọc bớt vị trí trước khi lưu). Gói zip hiện tại (mỗi ván một tệp con) đáp ứng điều này.
- Dung lượng ước tính: khoảng 20 MB mỗi đời, tức khoảng 10 GB cho 500 đời.
- Dùng cho: chưng cất (mục 2) và làm đích cho đầu dự đoán số nước còn lại.

## 2. Chưng cất mạng tích chập sang mạng transformer (sau đời 990)

- Mạng trò: transformer khoảng 1 GFLOP mỗi lần lượng giá.
- **Policy:** mạng trò học policy THÔ của mạng thầy, làm mềm ở phía thầy với $\tau = 1.1$: đích là $p_i^{1/\tau}$ chuẩn hoá lại; mạng trò học ở nhiệt độ 1, nên policy thô của trò phẳng hơn của thầy (có chủ đích: chuẩn bị cho việc gần như học lại với luật mới ở mục 3).
  - Phải đặt logits của nước KHÔNG hợp lệ thành −∞ trước khi chia nhiệt độ và tính softmax: lúc huấn luyện các ô đó bị che bằng −∞ nên logits thô của thầy ở đó không được huấn luyện, giá trị bất kỳ. Mặt nạ lấy từ phân phối đích trong dữ liệu (nước không hợp lệ = 0).
  - Ví dụ mức làm mềm: prior 0,60 / 0,30 / 0,10 thành khoảng 0,578 / 0,308 / 0,113.
- **Đầu dự đoán số nước còn lại (moves-left head):** thêm vào mạng trò. Đích = $n - i$ (ván dài $n$ nước, vị trí thứ $i$), tính từ dữ liệu ván ở mục 1 — không lấy từ mạng thầy (thầy không có đầu này).
  - Kiểm tra trên gen 109: 1002 ván, mọi bản ghi đổi bên đi đều đặn (không thiếu nước), dài 49–400 nước, trung vị 170; 1 ván chạm giới hạn 400 nước (kết thúc hoà, $n - i$ bị cắt ngắn).
  - Ván trong dữ liệu do mạng không có đầu này chơi, nên đích phản ánh cách chơi đó (bên thắng không vội kết thúc).
- **Engine:** phần tìm kiếm của lc0 cho đầu này đã có (`MEvaluator`, các tham số `moves-left-*` trong `src/search/classic/params.cc`). Hiện bộ nạp ONNX cố định `has_mlh = false` và điền M = 50 (`src/lczero_chess/neural/onnx_backend.cc`), nên số hạng này bằng 0 trong PUCT. Cần sửa bộ nạp để đọc đầu ra M từ tệp ONNX và bật `has_mlh`.
- **Mặt phẳng đầu vào vô dụng của mạng hiện tại** (tối ưu khi thiết kế mạng trò):
  - Amazon (`a`): không có trong FEN khởi đầu, không phải quân phong cấp → 2 mặt phẳng (mình / đối thủ) × 8 thế lịch sử luôn bằng 0.
  - Mặt phẳng phụ 6: không dùng (luôn 0). Mặt phẳng phụ 7: luôn bằng 1 (đánh dấu biên bàn cờ cho tích chập).
- Sau chưng cất: học tăng cường tiếp trên mạng trò. Lưu ý: đích policy khi đó là phân phối lượt thăm của MCTS với prior của trò, nên độ phẳng do $\tau$ chỉ ảnh hưởng mấy đời đầu.
- **Cần quyết định trước vòng học tăng cường của trò:** bật hiệu ứng số nước còn lại trong tìm kiếm khi tự đấu (dữ liệu mới có độ dài theo cách chơi mới) hay chỉ bật khi chơi GUI.

## 3. Đổi luật sau đợt chưng cất

Mỗi bên hiện có 4 Alibaba (`y:AD`, `customPiece2`): c2, h2, a3, j3 (bên kia c9, h9, a8, j8). Đổi 4 quân đó thành:

| Quân mới | Betza | Ghi chú |
|---|---|---|
| Alibaba + Wazir | `ADW` | |
| Grasshopper không ăn + King | `KmgQ` | phần King đi và ăn bình thường; phần grasshopper chỉ đi, không ăn; KHÔNG phải quân hoàng gia |

Bộ đọc Betza của Fairy-Stockfish nhận `m` và `g` (`src/chess/piece.cpp`).

- **Phong cấp:** tốt được phong thành cả hai quân mới; hai quân này thay chỗ Knight và Alibaba trong danh sách phong cấp (hiện `promotionPieceTypes = b m n r v y`). Vẫn 6 loại phong cấp → đầu ra policy giữ 106 kênh (72 hướng Hậu × khoảng cách + 8 Mã + 8 Lạc đà + 18 phong cấp). Nước của grasshopper (theo 8 hướng Hậu), Wazir/King (1 ô) và Alibaba (2 ô) nằm trong 72 kênh đầu.
- **Đầu vào:** bỏ Alibaba, thêm 2 loại quân; nếu một quân mới dùng chỗ của Alibaba và quân còn lại dùng chỗ của Amazon (vô dụng) thì mỗi bên vẫn 13 loại, 27 mặt phẳng mỗi thế, 226 mặt phẳng — không đổi kích thước. Nếu thiết kế lại đầu vào cho mạng trò thì tính sẵn chỗ cho 2 quân mới ngay từ lúc chưng cất (lúc đó các mặt phẳng này luôn 0), để khi đổi luật không phải sửa lớp đầu vào / đầu ra của mạng đã huấn luyện.
- **Còn phải quyết định:**
  - 4 ô Alibaba mỗi bên: ô nào thành quân nào (ví dụ 2 + 2).
  - Ký tự FEN của hai quân mới (`k` đã là Hoàng gia).
  - Quân nào nhận chỗ phong cấp của Knight, quân nào nhận chỗ của Alibaba.
- **Phải cập nhật khi làm:** `src/app/variant_setup.cc` (khai báo quân, phong cấp), FEN khởi đầu (`src/app/uci_coords.cc`), bảng loại quân → mặt phẳng (`src/lczero_chess/chess/encoder.cc`), mã hoá phong cấp trong `MoveToNNIndex`, `LUAT_BIEN_THE.md`, bộ kiểm tra luật độc lập `--audit-rules`, phiên bản dữ liệu nếu đổi định dạng, bộ đọc Python và bài kiểm tra round-trip, hình quân trong GUI (Windows và Android), `python/do_gia_tri_quan.py` (thứ tự mặt phẳng).
