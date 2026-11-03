# Nhật ký thí nghiệm

Mỗi lần chạy ghi: giả thuyết, cấu hình, seed, phiên bản mã, kết quả và kết luận. Lần thất bại cũng được ghi.

## 2026-11-02: Khởi tạo dự án

**Quyết định của chủ dự án:** Connect6 bàn 24×24, mạng khoảng 1 triệu tham số có SE, một nước đi là một cặp quân với 165600 khả năng.

**Tính toán cho Connect6 (chưa phải đo thật, phương án này đã bỏ):**

- 12 khối × 64 kênh có khoảng 0.97 triệu tham số và tốn khoảng 0.54 GMAC mỗi lần đánh giá.
- Theo mức 3.2 TFLOP/s đã đo trên Colab T4 ở dự án cờ biến thể, tốc độ ước lượng là khoảng 5900 lần đánh giá mỗi giây. Với 200 visits, con số này ứng với khoảng 30 nước đi mỗi giây.
- Gửi đủ 165600 điểm tốn 647 KB mỗi lần đánh giá, còn chỉ gửi top 512 cặp tốn khoảng 4 KB.

**Việc tiếp theo:** M0, luật cờ và bộ kiểm tra độc lập.

## 2026-11-02: Đổi sang cờ vua

**Quyết định của chủ dự án:** bỏ Connect6, làm trực tiếp cho cờ vua, mạng tích chập có SE khoảng 1 triệu tham số. Thiết kế tổng hợp nằm ở `co_vua/docs/THIET_KE_CO_VUA.md`. Chưa có mã engine nào được viết.

**Tính toán (chưa phải đo thật):** 11 khối × 64 kênh với 112 mặt phẳng đầu vào và policy 1858 nước có khoảng 0.97 triệu tham số và khoảng 59 triệu phép nhân mỗi lần đánh giá.

## 2026-11-03: Chốt các quy tắc còn mở và vai trò quan sát

Đây là quyết định thiết kế, chưa có lần chạy nào. Chi tiết nằm trong `THIET_KE_CO_VUA.md`.

**Quyết định của chủ dự án:**

- Phương châm của dự án: không đưa vào bất kỳ điều gì mà ta biết là hại nhiều hơn lợi; không bắt buộc phải tối ưu; ưu tiên ổn định và ít phải tinh chỉnh (chủ dự án mô tả lại cùng ngày, thay cho "tối ưu, không chấp nhận đánh đổi"). Claude tự quyết định thay chủ dự án nhiều việc, và phản biện khi một quyết định của chủ dự án đi ngược phương châm này.
- Claude là người quan sát chính: ghi log mọi thứ, đọc log, và tinh chỉnh cách mới đến khi thành công nhất có thể (phần 15).
- Kết luận chỉ dựa vào sức mạnh khi đấu trực tiếp, ở cùng tổng số lần chạy mạng. Không dùng Syzygy.
- Mạng chỉ có hai đầu ra là policy và value, không có đầu ra số nước còn lại.
- Khi số điểm rẽ vượt ngân sách thì chọn ngẫu nhiên (6.3).
- Cách sinh dữ liệu và huấn luyện: chủ dự án sẽ giải thích sau.

**Quyết định của Claude:**

- Cắt lá có $m$ nhỏ nhất, gần như là cắt lá cũ nhất trước, thay cho cắt ngẫu nhiên mà chủ dự án chọn trước đó (8.3). Lý do: cắt ngẫu nhiên làm thời gian sống của mẫu tản ra. Ván vừa chơi có thể bị bỏ ngay, còn nhãn rất cũ có thể được giữ rất lâu: nếu mỗi đời cắt 1/8 số lá, khoảng 12% số lá còn sống sau 16 đời. Cắt lá có $m$ nhỏ nhất không có tham số nào và giữ đúng ý của replay buffer.
- Chọn điểm rẽ ngẫu nhiên: Claude đã xem lại và đồng ý. Cách này giữ nguyên phân bố của bước quét, không phí dữ liệu và không có ngưỡng nào phải chỉnh.
- Stockfish chỉ dùng để đo nguyên nhân: nhãn sai và số đời một nhãn sai tồn tại. Nó không dùng cho nhãn hay cho kết luận (15.2).
- Giá trị mặc định cho những gì chưa suy ra được (15.1):
  - $\omega^2$ ở đời đầu lấy theo cách thứ hai ở 4.4 với $\rho=\pi$. Từ đời sau dùng cách thứ nhất.
  - Mỗi đời chỉ tính một lượt; vài lượt lặp thêm chỉ để log xem có hội tụ không.
  - $\omega^2$ là một số chung cho cả cây, và log thêm $\omega^2$ theo độ sâu và theo số quân.
- Kế hoạch thử nghiệm còn 6 bước (phần 14): bỏ bước kiểm bằng Syzygy, và bỏ bước thêm quy tắc chọn điểm rẽ.
- Chủ dự án giao thêm: Claude quyết định linh hoạt theo phương châm, và làm mọi cách cho thử nghiệm thành công, kể cả làm lại theo hướng khác khi phát hiện điều bất lợi. Phần lý thuyết thống kê của các công thức do Claude chịu trách nhiệm kiểm.

## 2026-11-03: Hạ tầng, tham số mốc và cách chạy nhiều máy

**Quyết định của chủ dự án:**

- Engine kế thừa từ lc0.
- Tham số sinh dữ liệu và huấn luyện của mốc truyền thống lấy theo engine cờ biến thể. Cách mới giữ nguyên chúng ở mọi chỗ trùng với cách cũ.
- Temperature 1 trong 30 nửa nước đầu. Chủ dự án cho biết đã đổi từ 32 xuống 30; các tệp trong kho vẫn ghi 32.
- $\alpha=0.3$ cho nhiễu Dirichlet, theo chuẩn cờ vua.

**Quyết định của Claude (12.6 trong thiết kế):**

- Chạy trên nhiều máy theo hai bước.
  - Bước tập trung: ban đầu đặt trên máy huấn luyện; sau đó chủ dự án đề xuất chuyển phần làm việc với cây (gộp kết quả, tính nhãn, cắt lá, lập danh sách việc chia thành gói) về điện thoại, Claude đồng ý (xem mục dưới). Máy Colab chỉ huấn luyện.
  - Bước song song: các máy nhận gói việc, giữ chỗ bằng khóa thư mục trên điện thoại như hiện nay.
- Hết gói mà còn ngân sách (chắc chắn xảy ra ở đời đầu) thì máy tự quét trên các ván của chính nó.
- Gộp kết quả theo đường đi từ gốc. Việc dở của máy bị thu hồi thì bỏ, không làm lệch mẫu vì danh sách đã xáo trộn.
- Cả hai bên đo ngân sách mỗi đời bằng số lần chạy mạng (không tính lần lấy từ cache), và dùng cùng số bước huấn luyện mỗi đời.
- Các tham số còn lại lấy từ ô 04 và 07 của engine biến thể. Riêng giới hạn ván lấy 450 nửa nước như lc0, thay cho 400 của bàn 10×10.

**Bổ sung cùng ngày:**

- Chủ dự án đề xuất chạy phần làm việc với cây trên điện thoại, vì phần này không chạy mạng. Claude đồng ý.
  - Không tốn hạn mức T4.
  - Cây không phải chuyển lên chuyển xuống Colab, và không mất khi máy bị thu hồi.
  - Phía Colab gần như y hệt cách cũ.
  - Điện thoại lập danh sách việc trong lúc Colab huấn luyện.
- Điều kiện: cây lưu bằng mảng số gọn (numpy hoặc C++). Tốc độ và bộ nhớ của điện thoại chưa đo.
- Không dùng sách khai cuộc. Engine nhận thẳng dãy nước từ thế khởi đầu bằng `NodeTree::ResetToPosition` của lc0, nên giữ đủ lịch sử cho đầu vào 112 mặt phẳng.

## 2026-11-03: Đọc lc0, engine và script mới

- Dự án cờ biến thể tạm hoãn. Engine và script của nó không bị sửa.
- Dự án này có engine riêng (bản sao lc0, commit `1227b4c`, thêm chế độ tự chơi riêng) và bộ script Termux/Colab riêng, đặt trong `co_vua/`.
- Huấn luyện: AdamW kèm SWA, tốc độ học cố định $10^{-3}$, các tham số khác mặc định như ô 07. Chủ dự án chốt.
- Kết quả đọc lc0 ghi ở mục 12.7 của thiết kế. Hai điều quan trọng:
  - Dữ liệu V6 của lc0 không có $Q$ của từng nước con, nên engine mới ghi định dạng riêng.
  - Prior tại gốc bị lc0 ghi đè bằng prior đã trộn nhiễu Dirichlet, nên engine mới ghi cả hai loại prior.
- Đường đi của mạng: PyTorch, xuất ONNX, bọc bằng `onnx2leela`, chạy bằng backend `onnx-cuda` của lc0. Chưa thử.

## 2026-11-03: Đo cây giả 1 triệu node

**Giả thuyết:** cây 1 triệu node lưu bằng mảng số gọn thì vừa RAM điện thoại, và thao tác trên cây mỗi đời mất vài giây đến vài chục giây. Chủ dự án lo cây cần ít nhất 7 GB; con số này khớp với việc lưu mỗi node theo định dạng V6 của lc0 (8356 byte), mà cây không cần.

**Cấu hình:** `co_vua/thu_nghiem/do_cay_gia.py`, numpy 2.2.6, Python 3.13.5, Intel i5-1335U, một luồng, seed 12345. Số liệu search trong cây là số ngẫu nhiên; chỉ dung lượng và thời gian có ý nghĩa.

**Kết quả:**

| Nước đã thăm mỗi node | Dung lượng cây | RAM cao nhất | Tổng thời gian | Tệp dữ liệu huấn luyện |
|---|---|---|---|---|
| 25 | 271 MB | 720 MB | 6.1 giây | 112 MB |
| 35 | 366 MB | 960 MB | 7.1 giây | 151 MB |

RAM cao nhất xảy ra lúc gộp node mới, vì script nối mảng tạo bản sao. Cây thật cấp sẵn mảng thì tránh được.

**Kết luận:** trên máy tính, dung lượng và thời gian không phải vấn đề. Chưa đo trên điện thoại. Việc tải tệp dữ liệu huấn luyện lên Colab có thể tốn thời gian hơn phần tính toán.

## 2026-11-03: Dựng engine mới

- `co_vua/engine`: bản sao lc0 (commit `1227b4c`), thêm chế độ `lc0 treeplay` (`src/treeplay/treeplay.cc`). Engine cờ biến thể không bị sửa.
- Biên dịch Linux cho Colab bằng Docker Ubuntu 24.04 và ONNX Runtime 1.20.1 GPU (`co_vua/bien_dich_linux.bat`). Binary đòi glibc 2.38, Colab có 2.39.
- Hai lỗi gặp khi biên dịch, đã sửa:
  - Lc0 không cho đặt ONNX Runtime trong cây mã nguồn.
  - Các script Python của bản sao có xuống dòng kiểu Windows. Thêm `.gitattributes` để giữ kiểu LF.
- Chạy thử bằng backend `random` trong Docker: ván, search lại và kiểm nước hợp lệ đều đúng; dữ liệu đọc ra khớp (tổng $n(a)$ bằng $N$, tổng prior bằng 1).
- Lần chạy thử đầu phát hiện hàm dựng thế cờ của lc0 không kiểm nước hợp lệ. Đã thêm bước kiểm.
- Phát hiện khi đối chiếu tham số: engine biến thể tự chơi với cpuct cố định 1.3 (không phải 1.745 tăng dần như tài liệu ghi trước đó), FPU 0, không prefetch. Đã sửa mục 2.5, 7.2 và tính lại ví dụ ở 7.2.
- Chưa chạy với mạng thật trên T4.

## 2026-11-03: Mạng đời 0, kiểm khớp với lc0, chạy trên T4

- Mạng `co_vua/python/mang.py`: 11 khối × 64 kênh SE, hai đầu ra theo engine biến thể. Tổng 1 203 364 tham số, nhiều hơn con số 0.97 triệu tính trước đây, vì value head 32 kênh (lớp 2048 → 128) giống engine biến thể. Luôn dùng fp32 (chủ dự án chốt).
- Bộ mã hoá 112 mặt phẳng (`ma_hoa.py`) và bảng chỉ số nước đi (`bang_lc0.py`, lấy thẳng từ mã lc0) viết lại bằng Python.
- Kiểm khớp (`kiem_khop_lc0.py`) trên 7 thế cờ, mạng đời 0 seed 1:
  - Chỉ số policy của mọi nước hợp lệ trùng với lc0.
  - WL và D mà `lc0 treeplay` ghi lại trùng Python tới 6 chữ số.
  - Prior thô lệch tương đối tối đa 0.3%, do lc0 lưu prior 16 bit.
- WL mà chế độ UCI của lc0 in ra thấp hơn khoảng 10%, trong khi trường V của nó khớp với Python. Dự án không dùng chế độ UCI nên không tìm tiếp nguyên nhân.
- Colab: dùng đăng nhập riêng `HOME=~/.fz_tk/t4` trong WSL, cài từ token chủ dự án đưa. Máy T4, ONNX Runtime 1.20.1 GPU tải từ GitHub của Microsoft (`co_vua/scripts/colab_chuan_bi.sh`). `lc0 treeplay` chạy được với `onnx-cuda`.
- Đo tốc độ lần đầu (`colab_do_toc_do.sh`, ván từ thế khởi đầu, 800 lượt thăm): 32 ván song song, 2 luồng gom lô cho khoảng 9 100 lần chạy mạng mỗi giây.
- `colab exec` bị mất kết nối với lệnh chạy lâu, nên các việc dài phải chạy nền.
