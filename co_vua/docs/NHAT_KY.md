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
- Đo tốc độ đầy đủ trên T4 (chi tiết ở mục 12.8 của thiết kế). Tốt nhất: 128 ván song song, 1 luồng gom lô, 16 947 lần chạy mạng mỗi giây. Từ 64 ván trở lên tốc độ chững ở 16 700 đến 17 000, GPU chỉ dùng 58 đến 70%, lc0 dùng khoảng 1.2 trên 2 nhân CPU: nút thắt là một phần tuần tự trên CPU, chưa xác định. Mỗi cấu hình đo một lần.
- Đã trả máy T4 sau khi đo.
- Chủ dự án chốt: dùng cấu hình nhanh nhất đã đo (128 ván song song, 1 luồng gom lô) và không tìm nút thắt CPU nữa. Lý do: đã khảo sát nhiều lần trên engine biến thể, có một mức trung gian nhanh nhất, tăng thêm thì lợi giảm.

## 2026-11-03: Mã huấn luyện, chạy thử đầu cuối trên máy

- Mã mới trong `co_vua/python`:
  - `du_lieu.py`: bản ghi treeplay thành mẫu nén bit (khoảng 840 byte mỗi thế cờ), nhãn của cách truyền thống ($\pi$ và $0.2q+0.8z$); toàn bộ mẫu nạp lên GPU một lần, mỗi lô giải nén ngay trên GPU.
  - `tao_mau.py`: tạo tệp mẫu.
  - `huan_luyen.py`: AdamW với tốc độ học cố định $10^{-3}$, SWA kiểu lc0 (25 bước, tối đa 10 bản), cập nhật BatchNorm, xuất `.pt` và ONNX. Huấn luyện hoàn toàn fp32 (engine biến thể dùng `--amp`; chủ dự án yêu cầu luôn fp32).
- Cửa sổ dữ liệu của cách truyền thống theo engine biến thể là 4 đời (đời hiện tại và 3 đời trước, `TD_SO_DOI=4`), nên $W=4$ cho cả hai bên.
- Chạy thử đầu cuối trên máy (CPU, Docker), không có kết luận gì về sức mạnh:
  - Mạng đời 0 sinh 6 ván (24 lượt thăm, tối đa 160 nửa nước), ra 516 mẫu.
  - `thu_nghiem/kiem_mau.py`: cả 516 mẫu khớp bộ mã hoá đã kiểm với lc0; số nước hợp lệ đúng; nước đã thăm đều hợp lệ; tổng xác suất bằng 1.
  - Huấn luyện 27 bước (batch 64), xuất mạng đời 1, bọc bằng `onnx2leela`: mạng đời 1 khớp với lc0 trên 7 thế cờ (WL, D trùng tới 6 chữ số).
- Chủ dự án yêu cầu: hai bộ script Termux/Colab (truyền thống và cây trò chơi); log là tệp lưu vĩnh viễn, không xoá, làm minh chứng (mục 15.2 của thiết kế).

## 2026-11-03: Chạy thử `cvt` (cách truyền thống) hai đời trên T4

**Cấu hình thử** (nhỏ, chỉ để kiểm đường đi, không nói gì về sức mạnh): ngân sách 1.5 triệu lần chạy mạng mỗi đời, 2 đời, 200 lượt thăm, tối đa 200 nửa nước, 32 ván song song. Bộ điều phối chạy trong WSL trên máy tính, tài khoản `t4b`. Dữ liệu ở `co_vua/chay/tt_thu` (không commit).

**Kết quả:** chạy trọn đời 0 và đời 1 rồi tự thoát, trả máy.
- Đời 0: tạo mạng đời 0 trên Colab; sinh 119 ván, 3 102 542 lần chạy mạng, 295 giây; huấn luyện 35 giây.
- Đời 1: sinh 53 ván, 1 408 303 lần chạy mạng, 141 giây; huấn luyện trên đời 0 và 1, 35 giây; ra mạng đời 2.
- Mọi log và dữ liệu đều về đủ: log bộ điều phối, log thô từng lần sinh, log huấn luyện, bản ghi ván, 3 mạng, tóm tắt JSON từng đời.

**Lỗi tìm thấy và đã sửa:**
1. Máy Colab không có gói `onnx` để PyTorch xuất mạng. Đã thêm vào `chuan_bi.sh`.
2. Lệnh SSH khởi động việc nền không trả về, vì `cd && setsid ... &` chạy trong shell con vẫn giữ kết nối. Đã đổi sang `setsid -f`.
3. Lệnh hỏi tiến độ có mã thoát 1 khi việc chưa xong (do `test -f`), nên bộ điều phối không bao giờ báo dừng. Lệnh kiểm huấn luyện có cùng lỗi. Đã thêm `; true` và tách lỗi kết nối riêng.
4. Vượt ngân sách gấp đôi, vì `sinh.py` nạp sẵn gấp đôi số ván song song, và việc đã nạp vẫn được chơi sau khi dừng. Đã đổi thành nạp bằng số ván song song cộng 4, và báo dừng sớm theo ước lượng phần còn lại của các ván dở.
5. Do phần vượt của đời 0, đời 1 không còn ngân sách để sinh, và huấn luyện gặp thư mục rỗng. Đã thêm quy tắc mỗi đời tự sinh ít nhất nửa ngân sách, và chỉ tải lên các đời có dữ liệu.
6. `gpu.log` không có nếu lần sinh ngắn hơn 5 phút. Đã ghi mẫu đầu sau 30 giây.
7. `pkill -f` trúng cả tiến trình `timeout` bọc ngoài nên bộ điều phối không kịp trả máy. Bộ điều phối giờ bắt SIGTERM để luôn trả máy và thả khoá.

**Ghi chú:** tài khoản `t4` hết hạn mức T4 ("Service Unavailable") sau khoảng 1 giờ dùng trong ngày; chủ dự án đưa token tài khoản thứ hai (`t4b`). Với 23 bước huấn luyện (ít hơn 25), SWA chưa gộp bản nào; với cấu hình thật (khoảng 390 bước mỗi đời) thì không gặp.
