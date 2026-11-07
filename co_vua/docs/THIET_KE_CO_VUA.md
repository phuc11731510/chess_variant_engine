# Thiết kế học tăng cường cờ vua bằng cây trò chơi

Tệp này tổng hợp toàn bộ thiết kế đã bàn, áp dụng cho **cờ vua** với mạng tích chập có SE khoảng 1 triệu tham số. Mỗi công thức được ghi kèm ý nghĩa bằng lời và ví dụ, không đi vào phép suy ra.

**Lưu ý quan trọng:** chưa có phần nào trong thiết kế được kiểm chứng bằng thực nghiệm. Mọi con số trong ví dụ đều là số giả định để minh họa. Chữ "suy ra" nghĩa là công thức đến từ một phép tính dưới các giả định được nêu, chứ không phải bằng chứng rằng nó sẽ hiệu quả.

## Mục lục

1. Mục tiêu và trạng thái các quyết định
2. Vấn đề cần giải quyết
3. Cây trò chơi
4. Giá trị tổng hợp $G$ và độ sai $E$
5. Value target mới
6. Rẽ nhánh
7. Policy target mới
8. Cắt tỉa và làm cũ bằng chứng
9. Search lại
10. Lấy mẫu huấn luyện
11. Vòng lặp mỗi đời
12. Áp dụng cho cờ vua
13. Rủi ro và những điều chưa biết
14. Kế hoạch thử nghiệm
15. Quan sát, ghi log và tinh chỉnh

Phụ lục A: Bảng ký hiệu. Phụ lục B: Các ý tưởng đã loại hoặc đã thay.

---

## 1. Mục tiêu và trạng thái các quyết định

**Mục tiêu:** với cùng tổng số lần chạy mạng, mạng phải tiến bộ nhanh hơn cách học tăng cường truyền thống kiểu lc0. Dự án cố gắng mọi cách hợp lệ để đạt điều đó, nhưng kết luận phải đáng tin.

**Ràng buộc:**

- Đây vẫn là học tăng cường thuần túy, không đưa hiểu biết cờ của con người vào nhãn.
- Không làm tăng tổng lượng tính toán so với cách cũ.
- Không đưa vào thiết kế bất kỳ điều gì mà ta biết là hại nhiều hơn lợi. Không bắt buộc phải tối ưu: một lựa chọn chưa chắc tốt nhất vẫn được nhận, miễn là không biết nó hại nhiều hơn lợi. Ngoài ra, thiết kế ưu tiên ổn định và ít phải tinh chỉnh. Đơn giản không phải là tiêu chí chính.
- Mã và thiết kế luôn nhắm tốc độ cao nhất có thể. Điều này tính cả thời gian thật không nằm trong thước đo số lần chạy mạng, như thao tác trên cây, chuyển dữ liệu giữa điện thoại và Colab, và thời gian máy phải chờ. Bộ nhớ không cần tối ưu, chỉ cần không vượt quá 4 GB RAM; được dùng thêm bộ nhớ (chỉ mục, bộ đệm, mảng tính sẵn) để đổi lấy tốc độ. Tốc độ không được đổi lấy sai kết quả hay một phép so sánh kém tin cậy.
- Cách mới phải xử lý cùng lúc cả nhiễu và lệch của nhãn.

| Nội dung | Trạng thái |
|---|---|
| Làm trực tiếp cho cờ vua, thay cho biến thể và Connect6 | Bạn đã chốt |
| Mạng tích chập có SE, khoảng 1 triệu tham số | Bạn đã chốt |
| Mạng chỉ có hai đầu ra, policy và value; không có đầu ra số nước còn lại (12.1) | Bạn đã chốt |
| Cây trò chơi, không gộp hai thế cờ giống nhau ở hai nhánh khác nhau | Bạn đã chốt |
| Rẽ nhánh bằng cách quét toàn cây với temperature 0.5 | Bạn đã chốt |
| Temperature 0 khi tự chơi trong thử nghiệm ban đầu | Bạn đã chốt |
| Lấy mẫu huấn luyện theo số ván $m$ đi qua mỗi node (phần 3, 10) | Bạn đã chốt |
| Cắt lá nhưng giữ thống kê ở node cha, và có giảm dần $m$ cũ | Bạn đã chốt |
| Giảm mức search lại so với 125000 lần mỗi đời | Bạn đã đồng ý, mức cụ thể do điều kiện dừng ở phần 9 |
| Không dùng trọng số nghiêng theo kết quả ván, với hệ số nghiêng $\lambda_s$ đổi theo lịch (phụ lục B) | Bạn đã loại vì khó chỉnh |
| Dùng $E$, độ sai của giá trị tổng hợp (phần 4.2), thay cho số ván hiệu dụng cũ | Đề xuất mới nhất, chờ kiểm tra |
| Value target và policy target mới | Đề xuất, chờ kiểm tra |
| Phương châm: không đưa vào điều gì mà ta biết là hại nhiều hơn lợi (không bắt buộc tối ưu), ổn định, ít phải tinh chỉnh (15.1). Mình tự quyết định thay bạn nhiều việc, và phản biện khi một quyết định của bạn đi ngược phương châm này | Bạn đã giao |
| Cắt lá có $m$ nhỏ nhất, gần như là cắt lá cũ nhất trước (8.3) | Mình quyết định, thay cho cắt ngẫu nhiên mà bạn chọn trước đó; lý do ở 8.3 |
| Chọn điểm rẽ ngẫu nhiên khi số điểm rẽ quét được vượt ngân sách (6.3) | Bạn đã chốt, mình đã xem lại và đồng ý; lý do ở 6.3 |
| Kết luận chỉ dựa vào sức mạnh khi đấu trực tiếp, cùng tổng số lần chạy mạng; không dùng Syzygy (phần 14) | Bạn đã chốt |
| Stockfish chỉ dùng để đo nguyên nhân (nhãn sai, thời gian tồn tại của nhãn sai), không dùng cho nhãn hay cho kết luận (15.2) | Mình quyết định |
| Những gì chưa suy ra được (giá trị khởi đầu và độ hội tụ của $\omega^2$, mức biến thiên của $\omega^2$ giữa các thế cờ, mức trần search lại, ...) được chọn mặc định, chạy, ghi log, quan sát rồi sửa; mình theo dõi toàn bộ dự án và tinh chỉnh cách mới đến khi thành công nhất có thể (phần 15) | Bạn đã giao |
| Engine kế thừa từ lc0; tham số sinh dữ liệu và huấn luyện của mốc truyền thống lấy theo engine cờ biến thể, và cách mới giữ nguyên chúng ở mọi chỗ trùng (2.5, 12.2) | Bạn đã chốt |
| Temperature 1 trong 30 nửa nước đầu cho mốc truyền thống; $\alpha=0.3$ cho nhiễu Dirichlet (2.5) | Bạn đã chốt |
| Chạy trên nhiều máy Colab: phần làm việc với cây (gộp ván, tính nhãn, cắt lá, lập danh sách việc) chạy trên điện thoại, Colab chỉ sinh ván theo gói việc và huấn luyện; ngân sách đo bằng số lần chạy mạng cho cả hai bên (12.6) | Phần chạy trên điện thoại do bạn đề xuất, mình đồng ý; phần còn lại mình quyết định |

---

## 2. Vấn đề cần giải quyết

### 2.1 Từ vựng dùng xuyên suốt

Các từ dưới đây được dùng đi dùng lại. Hai từ dễ nhầm nhất là **thăm** (việc của search) và **chơi** (việc của ván tự chơi).

| Từ | Nghĩa |
|---|---|
| $s$, $a$, $sa$ | $s$ là một thế cờ đang xét (cũng là một node, xem dưới). $a$ là một nước đi từ thế cờ đó. $sa$ là thế cờ có được sau khi đi nước $a$ từ $s$. Trong các ví dụ, $a_1$, $a_2$, $a_3$ là ba nước cụ thể. |
| Giá trị | Một số từ -1 đến +1 đánh giá thế cờ. +1 là thắng chắc, 0 là hòa, -1 là thua chắc. |
| Nửa nước | Một nước đi của một bên. Ván 80 nửa nước là 40 nước của mỗi bên. |
| Policy, prior | Đầu ra của mạng cho từng nước: xác suất mạng cho là nên đi nước đó. **Prior** $P(a)$ là chính đầu ra thô này, trước khi search. |
| Search (MCTS) | Chuỗi nhiều **lượt thăm**. Mỗi lượt đi từ thế cờ đang xét xuống một thế sâu hơn, gọi mạng một lần ở đó, rồi cập nhật ngược lên. $N$ là tổng số lượt thăm đi qua các nước tại thế cờ gốc, $N=\sum_{a\in A(s)}\big(n(a)\big)$ (cộng $n(a)$ qua mọi nước đã thăm, $A(s)$ được định nghĩa ở dòng ngay dưới bảng này; ví dụ 800), đúng với `GetChildrenVisits()` mà lc0 dùng làm mẫu số của nhãn policy. |
| Thăm, $n(a)$ | Việc của search. **$n(a)$ là số lượt thăm của nước $a$**, tức trong một lần search, có bao nhiêu lượt đã đi qua nước $a$ ngay từ thế cờ gốc. Ví dụ search 800 lượt, trong đó 560 lượt đi qua nước $a$, thì $n(a)=560$. Search chia lượt thăm theo prior và theo giá trị đã tìm thấy, nên nước hứa hẹn có $n(a)$ lớn. Mọi $n(a)$ của các nước cộng lại bằng $N$. |
| $\pi(a)$ | **Tỉ lệ lượt thăm của nước $a$**, bằng $\dfrac{n(a)}{N}$ (số lượt thăm của $a$ chia tổng số lượt thăm). Ví dụ $n(a)=560$, $N=800$ thì $\pi(a)=0.70$. Các $\pi$ của mọi nước đã thăm cộng lại bằng 1. Đây là kết quả sau khi search sửa prior, không phải đầu ra thô của mạng. |
| Cây search | Cây tạm mà **một lần search** dựng ra, gốc là thế cờ đang xét $s$. Mỗi lượt thăm đi xuống cây, thêm một thế cờ mới ở đáy, và gọi mạng đánh giá thế cờ đó. Cây này bỏ đi sau khi chọn nước. Nó **khác cây trò chơi** ở phần 3, là cây lưu các ván thật qua nhiều đời. |
| Giá trị search của một thế cờ | MCTS gán cho **mỗi thế cờ trong cây search** một giá trị: trung bình các giá trị đánh giá ở đáy cây (do mạng cho, hoặc do luật cờ nếu thế đó đã hết ván), lấy trên mọi lượt thăm đã đi qua thế cờ đó. Đây là giá trị của **thế cờ**, không phải của nước đi: nước đi chỉ là cạnh nối hai thế cờ. Mỗi giá trị đánh giá ở đáy được chuyền ngược lên và đổi dấu ở mỗi nửa nước, vì điều tốt cho bên này là xấu cho bên kia. |
| $q(s)$ | **Giá trị search dùng làm nhãn value**, đúng với trường `best_q` của dữ liệu huấn luyện lc0 và là số mà mã huấn luyện của dự án dùng mặc định (`dataset.py`, hàm `search_q`). $q(s)=Q(sa^*)$, trong đó $a^*$ là nước có **nhiều lượt thăm nhất** tại $s$ (nước search chọn khi temperature bằng 0, dù ván thật có đi nước đó hay không; ngoại lệ là khi có một nước thắng đã được chứng minh thì nước đó được ưu tiên). Nghĩa là $q(s)$ là giá trị search của thế cờ con $sa^*$, đo theo góc nhìn bên đi tại $s$ (+1 là bên đó thắng chắc). |
| $Q(sa)$ | **Giá trị search của thế cờ con $sa$** (thế cờ có được sau nước $a$), trung bình trên $n(a)$ lượt thăm đi qua $sa$, cũng đo theo góc nhìn bên đang đi tại $s$ (tức bên vừa đi nước $a$). Ký hiệu $Q(sa)$ viết cùng kiểu với $G(sa)$, $E(sa)$, $m(sa)$ vì đều là số của thế cờ $sa$. Ví dụ $n(a)=560$ lượt đi qua $sa$ và trung bình giá trị ở đáy của chúng là +0.10 thì $Q(sa)=0.10$: theo search, bên đi tại $s$ hơi có lợi sau nước $a$. |
| $q(s)$ và $Q(sa)$ liên hệ thế nào | $q(s)$ chỉ là một $Q(sa)$ đặc biệt: $Q$ của con có nhiều lượt thăm nhất. Nên mỗi node chỉ cần lưu $Q(sa)$ và $\pi(a)$ cho các nước đã thăm, $q(s)$ đọc ra từ đó, không cần lưu thêm. Cả hai là **niềm tin của mạng sau khi nhìn sâu hơn**, chưa phải kết quả ván thật; kết quả ván thật là $G$ ở phần 4. |
| `root_q` (không dùng trong tài liệu này) | Còn một giá trị search khác trong dữ liệu lc0: giá trị search của **chính gốc $s$**, tức trung bình mọi giá trị đã chuyền qua gốc. Gọi $v_0$ là giá trị mạng đánh giá chính $s$ (lượt thăm đầu, không đi qua thế cờ con nào) và $N=\sum_{a\in A(s)}\big(n(a)\big)$ (cộng qua mọi nước đã thăm, tập $A(s)$ ở dòng bên dưới), thì `root_q` $=\dfrac{v_0+\sum_{a\in A(s)}\big(n(a)\,Q(sa)\big)}{1+N}$ (khớp `FinalizeScoreUpdate` và `MakeNotTerminal` trong `search/classic/node.cc`). Nó khác $q(s)$ vì là trung bình của mọi nước, kể cả nước kém, còn $q(s)$ chỉ lấy nước tốt nhất. Tài liệu này dùng $q(s)$ để khớp mô hình cũ; `root_q` chỉ là phương án thử thêm. |
| $A(s)$ | Tập các nước mà search **đã thăm** ít nhất một lượt tại thế cờ $s$, tức các nước có $n(a)\ge1$. Với nước không thuộc $A(s)$ thì $n(a)=0$ và $\pi(a)=0$. Tập các nước đã **chơi** $C(s)$ (dòng dưới) thường là tập con của $A(s)$. |
| Chơi | Việc của ván tự chơi. Một nước **đã chơi** tại thế cờ $s$ nếu có ít nhất một ván thật đã đi nước đó từ $s$. Ván chơi nước có nhiều lượt thăm nhất, nên nước đã chơi thường là nước đã thăm. Ngược lại, search thường thăm nhiều nước mà chưa ván nào chơi. |
| Node, nhánh | **Node** là một thế cờ cùng lịch sử đã xuất hiện trong ít nhất một ván. **Nhánh** $a$ của node $s$ là nước $a$ đã chơi cùng toàn bộ cây con bên dưới nó. |
| Lá | Node không có node con nào, tức nơi mọi ván đi qua đều kết thúc hoặc đã bị cắt. |
| Ván, $z$ | Một ván tự chơi từ đầu đến cuối. $z$ là kết quả cuối ván: +1, 0, -1 theo góc nhìn Trắng. |
| Đời | Một vòng lặp gồm huấn luyện mạng rồi tự chơi sinh dữ liệu mới (phần 11). Mạng đời $k$ là mạng sau $k$ vòng huấn luyện. |
| Nhãn | Đáp án mà mạng được dạy: nhãn policy cho đầu ra policy, nhãn value cho đầu ra value. |
| $\omega^2$, $\tau_q^2$, $\tau_d^2$ | Ba con số cố định cho cả cây trong mỗi đời, ước lượng từ chính cây, không chỉnh tay. $\omega^2$ (ô-mê-ga bình phương): các nước đi từ cùng một thế cờ có giá trị thật chênh nhau bao nhiêu (4.2). $\tau_q^2$ (tau-q bình phương): sai số bình phương trung bình của $q$ so với giá trị thật (phần 5). $\tau_d^2$ (tau-d bình phương): sai số bình phương trung bình của độ chênh $Q$ giữa hai nước do search tính (phần 7). Đơn vị của cả ba giống $E$, tức bình phương của giá trị. |

### 2.2 Vòng lặp truyền thống

Mạng nhận một thế cờ và cho ra **policy** (policy này là xác suất nên đi từng nước) và **value** (value này là đánh giá thế cờ). MCTS dùng hai đầu ra đó để search. Mỗi thế cờ được lưu thành một mẫu với nhãn policy là tỉ lệ lượt thăm $\pi$ (số lượt thăm mỗi nước chia tổng lượt thăm, xem 2.1), và nhãn value là $0.2q+0.8z$, trong đó $q$ là giá trị search của nước có nhiều lượt thăm nhất tại thế cờ đó (`best_q`, xem 2.1) còn $z$ là kết quả cuối ván (+1, 0 hoặc -1). Chi tiết mô hình cũ ở 2.5. Sau đó mạng học từ các mẫu này và vòng lặp tiếp tục. Cây search bị bỏ đi sau mỗi nước, nên mọi ván đều không biết các ván khác đã thấy gì.

### 2.3 Hai kiểu hỏng của nhãn

**Nhiễu** là việc từng nhãn lệch khỏi giá trị đúng, nhưng trung bình nhiều nhãn thì đúng. Ở thế cờ khởi đầu với mạng còn non, nhãn lúc là thắng, lúc là thua, trong khi giá trị thật gần cân bằng. Kết quả đó chủ yếu nói về việc bên nào hớ nhiều hơn ở phần sau ván. Số lượng ván chữa được nhiễu.

**Lệch** là việc nhãn sai theo cùng một hướng mỗi lần được tạo ra. Ở dự án cờ biến thể, từng có một thế cờ mà search 8000 node vẫn nghiêng về một nước thí quân vô lý. Cả policy lẫn value đều sai, nên không yếu tố nào kéo được yếu tố nào lên. Chạy lại search bao nhiêu lần vẫn ra nhãn đó, nên số lượng ván tại chỗ đó không chữa được. Nhãn sai này còn trông rất tự tin, và mạng học theo nó như sự thật.

### 2.4 Hai cách phân loại tín hiệu

**Tín hiệu** là thông tin xuất hiện trong lúc tự chơi mà nhãn được tính ra từ đó.

| Tín hiệu | Khoảng cách tới thế cờ | Nguồn gốc | Kiểu hỏng |
|---|---|---|---|
| Kết quả cuối ván | Xa, vì có nhiều nước chen giữa | Ở ngoài niềm tin của mạng, vì luật cờ phán quyết | Ít lệch, nhiều nhiễu |
| Giá trị search | Gần, vì tính ngay tại thế cờ | Ở trong niềm tin của mạng | Ít nhiễu, có thể lệch |

Trộn hai tín hiệu theo tỉ lệ cố định chỉ đổi nhiễu lấy lệch và ngược lại. Muốn giảm cả hai thì cần thêm một nguồn thông tin **vừa gần vừa ở ngoài**.

Search đã hỏi mạng về hàng nghìn thế cờ khác nhưng vẫn ở trong niềm tin của mạng, vì hai lẽ: chính niềm tin đó chọn thế cờ để hỏi, và tất cả được hỏi cùng lúc với một bộ trọng số. Do đó có hai đòn bẩy: **thay đổi ai chọn thế cờ để hỏi**, và **thay đổi thời điểm hỏi**. Cây trò chơi nhắm vào cả hai.

### 2.5 Mô hình cũ, theo mã lc0 và mã huấn luyện của dự án

Đây là mốc so sánh. Mọi điều trong bảng đầu đọc từ mã (đường dẫn tính từ thư mục dự án), không viết từ trí nhớ. Phần nhãn value dưới đây lấy từ mã huấn luyện của dự án cờ biến thể (`custom_engine/python`), vốn làm theo cách lc0. Về script huấn luyện gốc của lc0 (kho `LeelaChessZero/lczero-training`, không nằm trong thư mục này): mình đã tải về và `grep` trực tiếp. Trong `tf/chunkparser.py` (dòng 398 đến 403), hàm `convert_v6_to_tuple` trả về `(planes, probs, winner, best_q, plies_left)`, trong đó `winner` suy từ kết quả ván `result_q` (dòng 390) và $q$ là `best_q`; `root_q` chỉ xuất hiện trong phần mô tả định dạng, không được dùng. Trong `tf/tfprocess.py` (dòng 485 đến 491), nhãn value là `qMix(z, q) = q * q_ratio + z * (1 - q_ratio)`, với `q_ratio` đọc từ cấu hình huấn luyện và **mặc định trong mã là 0** (tức chỉ dùng $z$). Vậy dạng công thức của mô hình cũ trong tài liệu này khớp lc0, và $q$ là `best_q` đúng như lc0. Giá trị 0.2 chỉ là mặc định trong mã huấn luyện của dự án; giá trị mà các lần huấn luyện lc0 thật dùng nằm trong tệp cấu hình của chúng, mình không có. Khi dựng mốc cho cờ vua phải đặt $q_{\text{ratio}}$ rõ ràng và dùng giống nhau ở cả hai bên so sánh.

| Điều | Mô hình cũ làm gì | Nguồn |
|---|---|---|
| Cây search mỗi nước đi | Mỗi lượt đi, search bắt đầu từ một gốc trống. Tùy chọn `reuse-tree` mặc định tắt, và khi tắt, `TrimTreeAtHead` xóa hết thống kê của gốc. | `selfplay/game.cc` dòng 71 và 158; `search/classic/node.cc` dòng 483 |
| Nhãn policy | $\pi(a)=\dfrac{n(a)}{N}$ với $N=\sum_{a\in A(s)}\big(n(a)\big)$ là tổng lượt thăm của các nước con ($A(s)$ là tập các nước đã thăm, 2.1). Lấy từ phân bố lượt thăm đầy đủ, không phải từ nước đã đi. | `trainingdata/trainingdata.cc` dòng 137 đến 165 |
| Chọn nước để đi | Theo temperature trên số lượt thăm. Mã đặt mặc định temperature, decay và cutoff đều bằng 0 (chọn nước tốt nhất), nên cấu hình tự chơi thật phải đặt rõ. | `search/classic/params.cc` dòng 555 đến 562 |
| Nhiễu Dirichlet ở gốc | Hệ số $\epsilon$ mặc định 0 (tắt), $\alpha$ mặc định 0.3. Bật bằng cấu hình. | `search/classic/params.cc` dòng 563 và 564 |
| Giá trị search $q$ dùng làm nhãn | `best_q`: giá trị $Q$ của con tốt nhất tại gốc. Con tốt nhất là nước thắng đã được chứng minh nếu có, còn lại là nước nhiều lượt thăm nhất, bằng nhau thì $Q$ cao hơn. Tính bất kể temperature. | `search/classic/search.cc` dòng 651 và 735 đến 740; `custom_engine/python/dataset.py` dòng 54 |
| Nhãn value | $q_{\text{ratio}}\,q+(1-q_{\text{ratio}})\,z$, tính riêng cho thắng, hòa, thua; $q_{\text{ratio}}$ mặc định 0.2. | `custom_engine/python/dataset.py` dòng 3, 206 và 305 đến 308 |
| Xin thua và giới hạn ván | Xin thua mặc định tắt. Ván bị dừng ở nửa nước 450 và đánh dấu là bị phán xử. | `selfplay/game.cc` dòng 73 và 152 đến 155 |

**Tham số tự chơi của mốc truyền thống cho cờ vua.** Các mặc định trong mã lc0 ở bảng trên (temperature 0, nhiễu tắt) không phải cấu hình tự chơi thật. Mốc truyền thống dùng cấu hình mà bạn đã chạy thật với engine cờ biến thể (`custom_engine/scripts/colab_cells/04_sinh_du_lieu.py` và `07_huan_luyen.py`), chỉ đổi những gì phụ thuộc trò chơi. Engine biến thể dùng chính phần search của lc0, nên các tham số này có cùng nghĩa trong lc0.

| Tham số | Giá trị cho cờ vua | Nguồn |
|---|---|---|
| Số lượt thăm mỗi nước | 800 | Ô 04 |
| Chọn nước để đi | Trong 30 nửa nước đầu, lấy mẫu theo tỉ lệ lượt thăm (temperature 1); sau đó đi nước nhiều lượt thăm nhất | Bạn cho biết đã đổi từ 32 xuống 30. Các tệp trong kho (ô 04, ô 08, `colab_termux.sh`) vẫn ghi 32, có lẽ bản trên điện thoại mới hơn; cờ vua dùng 30 |
| Nhiễu Dirichlet ở gốc | $\epsilon=0.25$ (mặc định của engine biến thể), $\alpha=0.3$ | $\alpha$: bạn chốt 0.3 theo chuẩn cờ vua (bàn 10×10 dùng 0.15) |
| Cây search mỗi nước | Gốc trống mỗi nước | `custom_engine/src/lczero_chess/selfplay/selfplay_game.cc` dòng 94 đến 103 |
| Tham số search khi tự chơi | cpuct **cố định 1.3** (`cpuct-factor` bằng 0, nên không tăng theo số lượt thăm), FPU 0 (nước chưa thăm lấy giá trị bằng $Q$ của node cha), tắt `two-fold-draws` và `sticky-endgames`, `max-prefetch` 0, `minibatch-size` 32. Lc0 khi tự chơi mặc định cpuct 1.2 (`selfplay/tournament.cc` dòng 155 đến 172); 1.3 là lựa chọn của bạn cho engine biến thể | `custom_engine/src/app/selfplay_mode.cc` dòng 115 đến 139 và ô 04 |
| Giới hạn ván | 450 nửa nước như lc0 (engine biến thể dùng 400 cho bàn 10×10) | Bảng trên |
| Xin thua | Tắt | Ô 04 không bật |
| Huấn luyện mỗi đời | AdamW kèm SWA, tốc độ học cố định $10^{-3}$ (không có lịch giảm dần), các tham số khác để mặc định như ô 07: weight decay $10^{-4}$, batch 1024, 1 lượt qua cửa sổ dữ liệu, $q_{\text{ratio}}=0.2$. Cả hai bên dùng chung | Bạn chốt; giá trị cụ thể lấy từ ô 07 |

Thiết kế mới dùng đúng các giá trị này ở mọi chỗ trùng với cách cũ. Chỉ hai chỗ khác, vì đó chính là ý tưởng mới: chọn nước khi tự chơi (temperature 0, còn temperature được chuyển sang bước quét ở 6.1) và thế cờ bắt đầu ván (rẽ từ cây).

Bảng dưới so mô hình cũ với thiết kế này, để thấy chỗ nào giữ nguyên và chỗ nào đổi.

| Phần | Mô hình cũ | Thiết kế này |
|---|---|---|
| Một lần search tại một thế cờ | Gốc trống, $N$ lượt thăm, nhiễu Dirichlet nếu bật | **Giữ nguyên.** Search lại ở phần 9 cũng chạy từ gốc trống |
| Số search đã lưu | Dùng một lần rồi bỏ | Lưu $\pi(a)$, $Q(sa)$, $N$, $P_0$ ở node (phần 3) |
| Nhãn policy | $\pi$ của đúng lần search đó | Cùng $\pi$; chỉ đổi thành $\pi'$ ở bước 5 của kế hoạch (phần 14), và chỉ khi node có ít nhất hai nước đã chơi |
| $q$ | `best_q` | **Giữ nguyên** `best_q` |
| Nhãn value | $0.2\,q+0.8\,z$, $z$ là kết quả của đúng ván này | $w_q\,q+(1-w_q)\,G$, $G$ tổng hợp từ nhiều ván (phần 5) |
| Thế cờ bắt đầu ván | Luôn từ thế khởi đầu, đa dạng nhờ temperature 1 trong 30 nửa nước đầu | Rẽ từ cây (phần 6), tự chơi temperature 0 |
| Nhiễu Dirichlet | $\epsilon=0.25$, $\alpha=0.3$ | **Giữ nguyên** |
| Các tham số còn lại (lượt thăm, cpuct, giới hạn ván, huấn luyện) | Như bảng trên | **Giữ nguyên** |
| Dữ liệu cũ | Cửa sổ các ván gần nhất | Cây có $W$ đời (phần 8); mốc so sánh phải dùng cửa sổ cùng cỡ $W$ |
| Xin thua | Tắt | **Giữ nguyên** tắt |

---

## 3. Cây trò chơi

Cây trò chơi lưu **các ván tự chơi thật** trong một cây duy nhất, tồn tại qua nhiều đời mạng. Khác với cây MCTS chỉ dùng một lần, mỗi nhánh ở đây là các nước đã thực sự được chơi đến hết ván.

- Hai ván đi chung một đoạn nước thì dùng chung các node của đoạn đó.
- Hai thế cờ giống nhau ở hai nhánh khác nhau vẫn là hai node khác nhau, nên cây không có chu trình và giữ đúng lịch sử ván.
- Mọi ván mới đều bắt đầu bằng việc rẽ từ một node đã có.

**Mỗi node $s$ lưu hai nhóm số.**

Nhóm 1, lấy từ các lần search tại $s$ (lần đầu khi ván tạo ra node, thêm mỗi lần search lại ở phần 9). **Đổi ngày 4/11:** nhóm này không bị ghi đè mà là trung bình có trọng số của mọi lần search tại node, lần cũ bị nhân $\gamma$ mỗi đời (8.4), lưu kèm tổng trọng số; $N$ và $P_0$ lấy theo trung bình như vậy. Lý do ở 7.4: một lần search đơn lẻ mang nhiễu Dirichlet rất lớn. Mọi công thức dưới đây dùng các số trung bình này như thể chúng là của một lần search. Cách lưu không phình cây: mỗi nước đã thăm chỉ giữ hai số cộng dồn, tổng lượt thăm có trọng số và tổng (lượt thăm × $Q$) có trọng số, thay cho $\pi$ và $Q$; $\pi$ đọc ra bằng tổng lượt thăm của nước chia tổng của mọi nước, $Q$ đọc ra bằng tổng thứ hai chia tổng thứ nhất; lần search mới chỉ cộng thêm vào, và mỗi đời mọi tổng của node bị nhân $\gamma$. Nước được thăm ở lần search này mà không ở lần kia vẫn đúng (lần không thăm góp 0 lượt). Node chỉ lớn thêm khi một lần search lại thăm nước mà các lần trước chưa thăm, và chỉ các node được search lại (phần 9) mới gặp điều đó. Từ vựng ở 2.1.

- $N$: **tổng số lượt thăm** của lần search đó. Search là một chuỗi lượt thăm; mỗi lượt đi từ thế cờ $s$ xuống một thế sâu hơn và gọi mạng một lần. Ví dụ $N=800$.
- $n(a)$: **số lượt thăm của nước $a$**, tức trong $N$ lượt đó có bao nhiêu lượt đã đi qua nước $a$ ngay từ $s$. Ví dụ $n(a)=560$ trong 800 lượt. Các $n(a)$ của mọi nước đã thăm cộng lại bằng $N$.
- $\pi(a)$: **tỉ lệ lượt thăm của nước $a$**, bằng $\dfrac{n(a)}{N}$. Ví dụ $560/800=0.70$. Lưu cho mọi nước $a$ mà search đã thăm, kể cả nước chưa ván nào chơi. Đây là số lưu thay cho $n(a)$, vì tỉ lệ không phụ thuộc $N$.
- $Q(sa)$: **giá trị search của thế cờ con $sa$**, tức thế cờ có được sau nước $a$. Đó là trung bình các giá trị đánh giá ở đáy cây search, lấy trên $n(a)$ lượt thăm đã đi qua $sa$ (2.1). Đo theo góc nhìn bên đang đi tại $s$ (+1 là bên đó thắng chắc, -1 là thua chắc). Đây là giá trị của một **thế cờ** (con của $s$) chứ không phải của một nước đi, nên viết $Q(sa)$ cùng kiểu với $G(sa)$ và $E(sa)$. Nó là niềm tin của mạng, không dùng kết quả ván thật. Lưu cho cùng các nước như $\pi(a)$.
- $q(s)$: **giá trị search dùng làm nhãn value**, bằng $Q(sa^*)$ với $a^*$ là nước có nhiều lượt thăm nhất (`best_q`, 2.1 và 2.5). Không cần lưu thêm: đọc ra từ $\pi(a)$ và $Q(sa)$ đã lưu.
- $P_0$: tổng prior (đầu ra thô của mạng, 2.1) của các nước mà search **không** thăm lượt nào. Phần này cần để dựng lại nhãn ở phần 7.
- Đời của mạng đã chạy lần search đó (đời là một vòng huấn luyện cộng tự chơi, 2.1), để biết nhãn cũ đến đâu.
- Thế cờ đầu vào và lịch sử, phần này bỏ được khi node bị cắt (phần 8).

**Ví dụ một node:** Trắng đi, search $N=800$ lượt thăm và thăm ba nước.

| Nước $a$ | Số lượt thăm $n(a)$ | $\pi(a)=n(a)/800$ | $Q(sa)$ |
|---|---|---|---|
| $a_1$ | 560 | 0.70 | +0.10 |
| $a_2$ | 200 | 0.25 | +0.08 |
| $a_3$ | 40 | 0.05 | 0 |

$Q(sa_1)=+0.10$ nghĩa là: thế cờ con $sa_1$ (thế cờ sau khi Trắng đi nước $a_1$) có giá trị search +0.10. Cụ thể, 560 lượt thăm đã đi qua $sa_1$, và trung bình giá trị đánh giá ở đáy cây của chúng là +0.10 theo góc nhìn Trắng (bên đang đi tại $s$), tức Trắng hơi có lợi. Tương tự $Q(sa_2)=+0.08$ là giá trị search của $sa_2$ và $Q(sa_3)=0$ của $sa_3$. Nước nhiều lượt thăm nhất là $a_1$, nên nhãn value dùng $q(s)=Q(sa_1)=0.10$. (Để so sánh, `root_q`, trung bình của cả ba con theo tỉ lệ lượt thăm, khoảng $0.70(0.10)+0.25(0.08)+0.05(0)=0.09$; hai số gần nhau nhưng khác nhau.) Các nước còn lại mà search không thăm lượt nào có prior cộng lại là $P_0=0.10$, giả sử vậy.

Nhóm 2, lấy từ các ván thật đã đi qua $s$, lưu riêng cho **từng nước đã chơi** $a$ nhưng nói về node con $sa$:

- $m(sa)$: số ván đi qua $sa$. Mỗi đời con số này được nhân với $\gamma$ (một số nhỏ hơn 1, đã chốt 0.75 vì $W=4$) để ván cũ tính ít đi (phần 8.4). Ví dụ 3 ván đi qua $sa$ ở đời này thì $m=3$, sang đời sau còn $3\times0.75=2.25$.
- $G(sa)$: giá trị tổng hợp **từ kết quả cuối ván thật** của các ván đi qua $sa$ (trung bình có trọng số, góc nhìn Trắng, phần 4.1). Khác với $Q$ ở chỗ nó không dùng đánh giá của mạng, chỉ dùng phán quyết của luật cờ.
- $E(sa)$: sai số bình phương trung bình của $G(sa)$ so với giá trị thật (phần 4.2). Nhỏ thì $G(sa)$ đáng tin.

Ba số này nằm ở node cha $s$, nên khi node con $sa$ bị cắt thì chúng không mất.

**Ví dụ:** từ thế khởi đầu, ván thứ nhất đi 1.e4 e5 2.Nf3 rồi đi tiếp đến hết ván. Ở đời sau, bước quét (phần 6) chọn rẽ tại thế sau 1.e4 e5 với nước 2.f4. Ván mới dùng chung hai node đầu, và chỉ tốn search từ điểm rẽ trở đi.

---

## 4. Giá trị tổng hợp $G$ và độ sai $E$

### 4.1 $G$: giá trị được tổng hợp từ kết quả ván thật

$$
G(\text{node kết thúc})=\text{kết quả ván},\qquad G(s)=\sum_{a\in C(s)}\Big(\rho_s(a)\,G(sa)\Big)
$$

**Ký hiệu:** $C(s)$ là tập các nước **đã chơi** tại node $s$ (không phải các nước search đã thăm), $sa$ là node con sau nước $a$, và $\rho_s(a)$ là trọng số của nhánh $a$ (cách tính ở 4.3), với tổng các trọng số trên $C(s)$ bằng 1. Mọi giá trị tính theo góc nhìn quân Trắng: Trắng thắng là +1, hòa là 0, Đen thắng là -1.

**Ý nghĩa:** giá trị của một thế cờ là trung bình có trọng số của giá trị các thế cờ đi sau nó. Việc tính đi từ cuối ván ngược về gốc, nên phán quyết của luật cờ lan dần lên các node phía trên.

**Ví dụ:** node có hai nhánh với $G$ bằng -0.25 và +0.50, trọng số 0.47 và 0.53, thì $G(s)=0.47(-0.25)+0.53(0.50)\approx +0.15$. Nếu node chỉ có một nhánh thì trọng số bằng 1, nên trên đoạn không rẽ nhánh $G$ bằng đúng kết quả ván.

**Một điều cần nhớ:** trung bình thuần của các ván không giúp mạng biết thêm gì, vì học từng kết quả ván hay học trung bình của chúng đều đưa mạng về cùng một đích. Khác biệt chỉ là quá trình học bớt gập ghềnh. Lợi ích thật đến từ việc đặt trọng số thông minh, nhãn cũ được cập nhật khi có ván mới, và rẽ nhánh rẻ ở cuối ván.

### 4.2 $E$: độ sai của $G$

$$
E(\text{node kết thúc})=0,\qquad E(s)=\sum_{a\in C(s)}\Big(\rho_s(a)^2\,E(sa)\Big)+\omega^2\,U(s)
$$

$$
U(s)=\sum_{a\in C(s)}\Big(\big(\rho_s(a)-\pi_s(a)\big)^2\Big)+\sum_{a\in A(s)\setminus C(s)}\Big(\pi_s(a)^2\Big)
$$

**Đọc hai công thức, từng ký hiệu một:**

- $s$ là node đang tính, $a$ là một nước đi từ $s$, $sa$ là node con sau nước đó.
- **$C(s)$** là tập các nước **đã chơi** tại $s$, tức nước mà ít nhất một ván thật đã đi từ $s$. Ví dụ ván mới chơi một nước thì $C(s)$ chỉ có một phần tử.
- **$A(s)$** là tập các nước search **đã thăm** tại $s$, tức nước có ít nhất một lượt thăm đi qua (2.1). Ví dụ search thăm bốn nước thì $A(s)$ có bốn phần tử. Thường $C(s)$ là tập con của $A(s)$ vì ván đi nước search thăm nhiều.
- **$A(s)\setminus C(s)$** đọc là "$A(s)$ trừ $C(s)$": các nước thuộc $A(s)$ mà không thuộc $C(s)$, tức nước search đã thăm nhưng chưa ván nào chơi. Ví dụ search thăm bốn nước, ván đã chơi một nước, thì $A(s)\setminus C(s)$ có ba phần tử.
- $\rho_s(a)$ là trọng số của nhánh $a$ (công thức ở 4.3), $\pi_s(a)$ là tỉ lệ lượt thăm của nước $a$ tại $s$, tức $\dfrac{n(a)}{N}$ với $n(a)$ là số lượt thăm của $a$ và $N$ là tổng số lượt thăm (2.1, phần 3); ở các phần khác viết gọn $\pi(a)$ (cùng một đại lượng, chỉ khác là $\pi_s$ nhấn mạnh đang xét tại node $s$). Cộng $\pi_s(a)$ qua mọi nước $a\in A(s)$ thì bằng đúng 1, vì đó là phân bố lượt thăm; cộng chỉ qua các nước đã chơi $C(s)$ thì có thể nhỏ hơn 1. Còn $\rho_s(a)$ thì ngược lại: cộng qua $C(s)$ bằng đúng 1. Cả hai đều là số từ 0 đến 1.
- $E(s)$ là độ sai của $G(s)$ (đoạn "$E$ là gì" ngay dưới đây), còn $E(sa)$ là độ sai của node con.
- $U(s)$ là một số không âm đo trọng số $\rho$ đã dùng lệch khỏi $\pi$ bao nhiêu (giải thích dưới).
- $\omega^2$ là **một con số cố định cho cả cây trong mỗi đời** (chữ $\omega$ là "ô-mê-ga", chữ cái Hy Lạp; $\omega^2$ đọc là ô-mê-ga bình phương và là một số duy nhất, không phụ thuộc node). Nó đo **các nước đi khác nhau từ cùng một thế cờ có giá trị thật chênh nhau bao nhiêu**. Cụ thể là phương sai: lấy giá trị thật của thế cờ sau mỗi nước, tính độ lệch của từng giá trị so với trung bình của chúng, rồi lấy trung bình bình phương các độ lệch. Ví dụ ở một thế cờ có bốn nước, giá trị thật sau mỗi nước là +0.2, +0.2, -0.2, -0.2 thì trung bình là 0, mỗi độ lệch là 0.2, và $\omega^2=0.2^2=0.04$. Nếu mọi nước đều cho cùng giá trị thì $\omega^2=0$. Giá trị thật này không biết trước, nên $\omega^2$ được ước lượng từ cây (4.4).

**Vì sao $\omega^2$ nhân với $U$.** $G(s)$ chỉ gộp các nước đã chơi, với trọng số $\rho$. Giá trị thật lại là trung bình trên mọi nước theo $\pi$. Hai cách gộp này khác nhau bao nhiêu thì $G(s)$ sai bấy nhiêu, và mức khác nhau đó là $U(s)$. Nhưng nếu mọi nước đều có cùng giá trị ($\omega^2=0$) thì gộp thế nào cũng ra cùng kết quả, nên sai số bằng 0. Vì vậy sai số do bỏ sót nước là $\omega^2\times U(s)$: nước càng khác nhau về giá trị thì việc chọn thiếu nước càng gây sai. Công thức này suy ra được với giả định giá trị của các nước dao động độc lập quanh một mức chung, mỗi nước lệch với phương sai $\omega^2$.

**$E$ là gì.** Giá trị thật của một thế cờ $s$ ở đây được hiểu là kết quả trung bình nếu hai bên chơi tiếp theo $\pi$ (cách search chia lượt thăm) vô số ván. $G(s)$ chỉ là ước lượng của giá trị thật đó từ vài ván đã có. $E(s)$ là **sai số bình phương trung bình** của ước lượng ấy: $E(s)$ càng nhỏ thì $G(s)$ càng đáng tin.

Để đọc con số: căn bậc hai của $E$ là mức sai điển hình của $G$. $E=0.04$ nghĩa là $G$ thường lệch khoảng 0.2 so với giá trị thật, còn $E=0.8$ nghĩa là lệch khoảng 0.9, gần như không biết gì vì giá trị chỉ nằm trong khoảng -1 đến +1.

**Vì sao $E=0$ ở cuối ván:** phán quyết của luật cờ là chính xác, nên không có sai số.

**$E(s)$ gồm hai phần:**

- **Sai số thừa kế từ các nhánh con** $\sum_{a\in C(s)}\Big(\rho_s(a)^2\,E(sa)\Big)$. Nếu hai nhánh có sai số độc lập thì trung bình của chúng sai ít hơn từng nhánh. Ví dụ hai nhánh cùng $E=0.27$ và trọng số 0.5 mỗi bên cho phần này bằng $2\times0.5^2\times0.27=0.135$, chỉ bằng một nửa. Đó là lý do trọng số xuất hiện dưới dạng bình phương.
- **Sai số do không đi hết các nước** $\omega^2U(s)$. $U(s)$ đo trọng số $\rho$ đã dùng lệch khỏi $\pi$ bao nhiêu. Tổng thứ nhất của $U$ chạy trên $a\in C(s)$, tức các nước đã chơi, mỗi nước đóng góp $\big(\rho_s(a)-\pi_s(a)\big)^2$. Tổng thứ hai chạy trên $a\in A(s)\setminus C(s)$, tức các nước search có thăm nhưng chưa ván nào chơi: chúng có $\pi>0$ mà không có nhánh nên không được trọng số, và mỗi nước đóng góp $\pi_s(a)^2$. Nước search không thăm lượt nào có $\pi=0$ nên không đóng góp vào cả hai tổng. Ví dụ với $\omega^2=0.04$ và $U=0.235$ (ví dụ 1 dưới đây), phần này bằng $0.04\times0.235=0.0094$.

**Ví dụ 1, sai số tăng khi đi xa cuối ván.** Giả sử $\omega^2=0.04$. Mỗi node trên đường đi chỉ có một nước đã chơi (nên $\rho=1$ cho nước đó), nước ấy có $\pi=0.6$, còn ba nước search có thăm nhưng chưa chơi có $\pi$ bằng 0.25, 0.1, 0.05. Khi đó $U=\underbrace{(1-0.6)^2}_{\text{tổng thứ nhất, trên }C(s)}+\underbrace{0.25^2+0.1^2+0.05^2}_{\text{tổng thứ hai, trên }A(s)\setminus C(s)}=0.235$, nên mỗi nửa nước đi lên làm $E$ tăng $0.04\times 0.235=0.0094$ (giả sử mọi node trên đường đều có cùng $\pi$ như vậy).

| Số nửa nước cách cuối ván | $E$ |
|---|---|
| 0 | 0 |
| 10 | 0.094 |
| 30 | 0.282 |
| 85 | khoảng 0.8 |

Con số 0.8 ở dòng cuối cũng cỡ độ dao động kết quả của cả một ván (kết quả ván nằm giữa -1 và +1 nên dao động bình phương cỡ 0.8), nghĩa là ở xa như vậy $G$ gần như không nói thêm gì ngoài việc thế cờ nằm đâu đó trong khoảng giá trị có thể, và mô hình tự nhất quán với độ dài một ván.

**Ví dụ 2, rẽ sớm có giá trị hơn rẽ muộn.** Xét node cách cuối ván 30 nửa nước, với cùng giả định như ví dụ 1 ($\omega^2=0.04$, mỗi nửa nước đi lên của đoạn chỉ có một nước đã chơi làm $E$ tăng 0.0094). Tại node mà hai ván tách ra, giả sử hai nước đã chơi có trọng số 0.5 và 0.5, còn $\pi$ của các nước tại đó là 0.6, 0.25, 0.1, 0.05, nên $U=(0.5-0.6)^2+(0.5-0.25)^2+0.1^2+0.05^2=0.085$ và phần $\omega^2U=0.0034$.

| Trường hợp | $E$ |
|---|---|
| Một ván, không rẽ | 0.282 |
| Hai ván đi chung 20 nửa nước rồi mới tách (tách ở node cách cuối ván 10 nửa nước) | khoảng 0.234 |
| Hai ván tách ngay tại node đó | khoảng 0.140 |

Cách tính dòng cuối: mỗi nhánh con là một ván một mạch dài 29 nửa nước, nên $E=29\times0.0094=0.2726$. Do đó $E=0.5^2\times0.2726\times2+0.0034\approx0.140$. Dòng giữa: sau chỗ tách còn 9 nửa nước ($E=0.0846$ mỗi nhánh), nên $E$ tại chỗ tách là $0.5^2\times0.0846\times2+0.0034\approx0.046$, rồi đi lên thêm 20 nửa nước chung, mỗi nửa nước cộng 0.0094, ra khoảng 0.234.

Hai ván tách muộn gần như không thêm bằng chứng cho node ở xa phía trên, vì mọi điều xảy ra trong đoạn chung đều là của chung. Đây là lỗi mà công thức số ván cũ đã bỏ sót.

### 4.3 Trọng số $\rho$ của từng nhánh

$$
\rho_s(a)=\big(\pi(a)+\nu\big)\,f(sa),\qquad f(sa)=\frac{\omega^2}{\omega^2+E(sa)},\qquad \nu=\dfrac{1-\sum_{j\in C(s)}\Big(\pi(j)\,f(sj)\Big)}{\sum_{j\in C(s)}\Big(f(sj)\Big)}
$$

**Ký hiệu:** $a$ là một nước đã chơi bất kỳ tại $s$. $j$ chỉ là biến đếm chạy qua mọi nước đã chơi tại $s$ trong hai tổng của $\nu$, không phải một nước cụ thể. $E(sa)$ là độ sai của node con $sa$ (đã lưu ở node $s$, phần 3). $\omega^2$ là con số đã định nghĩa ở 4.2 (các nước đi từ cùng một thế cờ có giá trị thật chênh nhau bao nhiêu, ví dụ 0.04), ước lượng ở 4.4. Ở đây nó đóng vai thước so sánh: $E(sa)$ nhỏ hơn $\omega^2$ thì nhánh được coi là có nhiều bằng chứng, lớn hơn thì ít.

**Ý nghĩa của từng phần:**

- $\pi(a)$ là tỉ lệ lượt thăm của nước $a$ trong lần search tại $s$ (2.1), không phải đầu ra thô của mạng. Nó là điểm xuất phát của trọng số. Search có thể thăm nước mà chưa ván nào chơi, nên tổng $\pi$ của các nhánh đã chơi có thể nhỏ hơn 1.
- $f(sa)$ là độ tin cậy của nhánh, nằm giữa 0 và 1. Nó gần 1 khi $E(sa)$ nhỏ hơn nhiều so với $\omega^2$ (bằng chứng dày), và gần 0 khi $E(sa)$ lớn hơn nhiều (bằng chứng mỏng).
- $\nu$ là hằng số cộng chung cho mọi nhánh, chọn sao cho tổng các $\rho$ bằng đúng 1. Nó cũng gánh phần $\pi$ của các nước chưa chơi.

**$\rho$ chính là bộ trọng số làm $E(s)$ nhỏ nhất** (kiểm ngày 4/11 khi rà lại): tìm các $\rho_s(a)$ có tổng bằng 1 sao cho $E(s)$ ở 4.2 nhỏ nhất thì ra đúng công thức trên, với $\nu$ đóng vai hằng số giữ tổng bằng 1. Nên 4.2 và 4.3 là cùng một ý: chọn cách gộp các nhánh sao cho $G(s)$ sai ít nhất có thể.

Công thức cân bằng hai mong muốn trái ngược: bám sát cách chơi của search ($\pi$), và không tin nhánh có quá ít bằng chứng ($f$). Khi mọi nhánh đều có bằng chứng dày ($f$ gần 1), $\rho$ gần $\pi$. Khi bằng chứng mỏng ($f$ nhỏ), $\rho$ tỉ lệ gần với $f$, tức tỉ lệ nghịch với $E$: nhánh nào có nhiều bằng chứng hơn thì được tin hơn. Trọng số không dùng kết quả ván, nên các ván may mắn không được ưu ái có hệ thống.

**Ví dụ:** tại $s$ có hai nước đã chơi $a_1$, $a_2$ và một nước $a_3$ search đã thăm nhưng chưa ván nào chơi. Cho $\pi(a_1)=0.70$, $E(sa_1)=0.10$; $\pi(a_2)=0.25$, $E(sa_2)=0.05$; $\pi(a_3)=0.05$; $\omega^2=0.04$.

1. Độ tin cậy là $f(sa_1)=0.04/0.14\approx 0.286$ và $f(sa_2)=0.04/0.09\approx 0.444$.
2. Phần chia lại là $\nu\approx 0.943$. Hai tổng chỉ chạy qua $a_1$ và $a_2$, vì $a_3$ chưa chơi.
3. Trọng số là $\rho(a_1)\approx(0.70+0.943)(0.286)\approx 0.47$ và $\rho(a_2)\approx(0.25+0.943)(0.444)\approx 0.53$.

Khi bằng chứng còn mỏng, trọng số nghiêng về nhánh đáng tin hơn: $a_2$ có $\pi$ nhỏ hơn nhiều nhưng được trọng số lớn hơn. Nếu cả hai nhánh có nhiều bằng chứng, chẳng hạn $E(sa_1)=0.010$ và $E(sa_2)=0.004$, trọng số trở về khoảng 0.66 và 0.34, sát với $\pi$ hơn.

**Giới hạn:** với cách đặt trọng số này, nếu search vẫn nghiêng về $a_1$ thì value của node khó phản ánh rằng $a_2$ tốt hơn. Tín hiệu đó đi qua policy target ở phần 7.

### 4.4 Cách có $\omega^2$

$\omega^2$ (phương sai giá trị thật giữa các nước đi từ cùng một thế cờ, xem 4.2) không biết trước vì giá trị thật không biết, nên được ước lượng từ chính cây mỗi đời, không chỉnh tay. Có hai cách có thể đối chiếu với nhau:

- Lấy độ chênh $G$ giữa các nhánh của cùng một node (các nước đã chơi tại cùng một thế cờ), rồi trừ đi phần chênh chỉ do sai số của $G$ ($E$ của từng nhánh).
- Lấy phương sai kết quả của một ván (cỡ 0.8) chia cho tổng $U$ cộng dọc một ván điển hình. Cách này suy ra từ ví dụ 1 ở 4.2, nơi $E$ ở đầu ván bằng $\omega^2$ nhân tổng $U$.

**Số đo thật (4/11, 573 ván đời 0 của cách truyền thống):** phương sai kết quả ván là 0.608 (164 ván Trắng thắng, 185 Đen thắng, 224 hoà), $U$ trung bình mỗi thế cờ 0.678 (với $\rho=1$ cho nước đã chơi), tổng $U$ dọc một ván trung bình 162.6, nên cách thứ hai cho $\omega^2\approx0.0037$, nhỏ hơn khoảng mười lần con số minh hoạ 0.04 dùng trong các ví dụ của phần 4. Hệ quả: gần gốc, nhánh mang một ván có $E(sa)$ cỡ 0.1 đến 0.6, lớn hơn $\omega^2$ rất nhiều, nên $f$ rất nhỏ và $\rho$ gần như chia đều theo độ tin cậy, gần như không theo $\pi$. Điều này đúng với mô hình; mô phỏng (phần 14) phải xem nó có hợp lý trên cây thật không.

**Phương án B, mô hình có chặn tự nhiên (đề xuất 4/11, chờ mô phỏng so với phương án hiện tại).** Gốc của các chỗ phải chặn tay ở 4.4 và phần 5 là giả định mỗi nửa nước cộng thêm một lượng sai cố định $\omega^2U$ mãi mãi, trong khi kết quả ván bị chặn trong $[-1,1]$. Nếu coi giá trị thật $V(s)$ là kết quả trung bình khi chơi tiếp theo $\pi$, thì độ dao động của kết quả một ván từ $s$ là $(1-D(s))-V(s)^2$ ($D$ là xác suất hoà), luôn trong $[0,1]$ (ví dụ thắng 50% thua 50% cho 1; chắc hoà cho 0; thắng 70% hoà 30% cho 0.21), và nó tách đúng thành tổng dọc đường đi của độ toả có trọng số $\pi$ của giá trị các nước con, $\sum_a\pi(a)\big(V(sa)-V(s)\big)^2$. Phương án B thay $\omega^2$ chung bằng độ toả tại chính node, ước lượng từ $Q(sa)$ của lần search đã lưu ($\omega^2(s)=\sum_{a\in A(s)}\pi(a)\big(Q(sa)-\bar Q\big)^2$, $\bar Q$ là trung bình theo $\pi$). Khi các $Q$ nhất quán, tổng các độ toả dọc một ván không vượt độ dao động của kết quả, nên $E$ tự bị chặn mà không cần chặn tay, và thế cờ giằng co (các nước gần bằng nhau) tự cộng ít sai hơn thế cờ có đòn chiến thuật. Cái giá: độ lớn của sai số (không phải giá trị) dựa vào niềm tin của mạng. Mô phỏng (phần 14) chạy cả hai phương án trên cùng cây giả có giá trị thật biết trước và chọn theo bằng chứng. Số đo đời 0: độ dao động kết quả dự báo từ thắng/hoà/thua của search ở thế khởi đầu là 0.667, đo thật 0.608.

Mặc định dùng cách thứ nhất. Cách thứ hai dùng để đối chiếu, và để có giá trị khởi đầu ở đời đầu, khi cách thứ nhất chưa tính được vì $E$ của các nhánh lại cần $\omega^2$ (4.5, 15.1).

**$\omega^2$ là một số hay nhiều số.** Mỗi đời chỉ có **một** giá trị $\omega^2$, dùng chung cho mọi node trong cây; sang đời sau nó được ước lượng lại nên có thể khác (nó không được chỉnh tay). Dùng một số chung cho mọi node là một **giả định đơn giản hóa**: thực tế các nước ở thế cờ giằng co có thể chênh nhau ít hơn các nước ở thế cờ có thí quân, nên $\omega^2$ thật có thể khác nhau giữa các thế cờ. Mức khác biệt này chưa đo được trước khi chạy. Cách làm: mặc định dùng một số chung, và mỗi đời log thêm $\omega^2$ ước lượng riêng theo nhóm node (theo độ sâu và theo số quân, phần 15). Nếu log cho thấy các nhóm chênh nhau lớn thì chuyển sang dùng $\omega^2$ riêng cho từng nhóm, và ghi thay đổi đó vào nhật ký.

### 4.5 Thứ tự tính: $\rho$ và $E$ không đệ quy vòng, nhưng $\omega^2$ và $E$ thì có

**$\rho$ và $E$ không phụ thuộc vòng vào nhau.** Nhìn kỹ các công thức: $\rho_s(a)$ ở 4.3 chỉ cần $E(sa)$, tức $E$ của **các node con**, chứ không cần $E(s)$. Còn $E(s)$ ở 4.2 cần $\rho_s(a)$ và $E(sa)$ của các node con. Cây không có chu trình (phần 3), nên việc tính đi **từ dưới lên**, mỗi node chỉ dựa vào các node con đã tính xong:

1. Node kết thúc (hết ván theo luật cờ): $G=$ kết quả ván và $E=0$. Một node con đã bị cắt thì $G(sa)$, $E(sa)$ đã lưu sẵn ở node cha (phần 3 và 8.2), nên dùng được như giá trị gốc.
2. Với một node $s$ mà mọi node con đã có $G(sa)$ và $E(sa)$:
   1. Tính $f(sa)$ từ $E(sa)$, rồi $\nu$, rồi $\rho_s(a)$ (4.3).
   2. Tính $G(s)$ từ $\rho_s(a)$ và $G(sa)$ (4.1).
   3. Tính $U(s)$ từ $\rho_s(a)$ và $\pi_s(a)$, rồi $E(s)$ (4.2).
3. Đi lên node cha của $s$ và lặp lại. $E(s)$ vừa tính chỉ được dùng bởi node cha của $s$.

**Ví dụ**, dùng lại số của 4.3: tại $s$, $\omega^2=0.04$; ba nước có $\pi$ là 0.70, 0.25, 0.05; hai nước đầu đã chơi với $E(sa_1)=0.10$, $G(sa_1)=-0.25$ và $E(sa_2)=0.05$, $G(sa_2)=+0.50$ (hai cặp số này đã tính xong từ các node bên dưới).

| Bước | Kết quả |
|---|---|
| $f(sa_1)$, $f(sa_2)$ | 0.286 và 0.444 |
| $\nu$ | 0.943 |
| $\rho_s(a_1)$, $\rho_s(a_2)$ | 0.470 và 0.530 |
| $G(s)$ | $0.470(-0.25)+0.530(0.50)\approx 0.148$ |
| $U(s)$ | $(0.470-0.70)^2+(0.530-0.25)^2+0.05^2\approx 0.134$ (số hạng cuối là nước $a_3$ đã thăm nhưng chưa chơi) |
| $E(s)$ | $0.470^2(0.10)+0.530^2(0.05)+0.04\times0.134\approx 0.0361+0.0054=0.0415$ |

Chuỗi này chạy một lượt từ dưới lên, không cần lặp.

**Vòng lặp thật sự là giữa $\omega^2$ và $E$.** $E$ cần $\omega^2$ (4.2 và 4.3), mà $\omega^2$ lại được ước lượng từ $E$ và $U$ (4.4), và $U$ phụ thuộc $\rho$ vốn phụ thuộc $\omega^2$. Cách phá vòng lặp này trong thiết kế: mỗi đời, bước tính $\rho$, $G$, $E$ dùng $\omega^2$ **của đời trước**; sau đó $\omega^2$ được ước lượng lại từ kết quả vừa tính để dùng cho đời sau (phần 11). Mặc định cho hai việc chưa suy ra được: (1) ở đời đầu chưa có $\omega^2$ của đời trước, nên lấy giá trị khởi đầu bằng cách thứ hai ở 4.4 với $\rho=\pi$ (coi mọi nhánh đáng tin như nhau); (2) mỗi đời chỉ tính một lượt. Ngoài lượt chính, mình chạy thêm vài lượt lặp chỉ để log: tính $\rho$, $G$, $E$, ước lượng $\omega^2$, rồi lặp lại với $\omega^2$ mới. Các lượt này không chạy mạng nên rẻ. Dãy $\omega^2$ qua các lượt lặp cho biết vòng lặp có hội tụ hay không. Nếu log cho thấy hội tụ nhanh và giá trị hội tụ khác nhiều so với $\omega^2$ của đời trước, thì chuyển sang dùng giá trị hội tụ (phần 15). Còn $\tau_q^2$ và $\tau_d^2$ chỉ dùng $E$ để ước lượng và không được $E$ dùng lại, nên không tạo vòng lặp.

---

## 5. Value target mới

**Nhắc ký hiệu dùng trong phần này.** $s$ là thế cờ đang xét. $q(s)$ là giá trị search dùng làm nhãn value: $Q(sa^*)$ của nước $a^*$ có nhiều lượt thăm nhất tại $s$ (`best_q`, 2.1), theo góc nhìn bên đang đi tại $s$. Nó cần được đổi sang góc nhìn Trắng khi trộn với $G$. $z$ là kết quả cuối ván (+1, 0, -1 theo góc nhìn Trắng). $G(s)$ là giá trị tổng hợp từ kết quả các ván thật đi qua $s$ (4.1). $E(s)$ là sai số bình phương trung bình của $G(s)$ (4.2). $\tau_q^2$ được định nghĩa ngay dưới công thức.

Công thức cũ là $0.2q+0.8z$. Tỉ lệ cố định không còn hợp lý, vì độ tin cậy của $G$ khác nhau theo từng node.

$$
\text{value target}(s)=w_q\,q(s)+(1-w_q)\,G(s),\qquad w_q=\frac{E(s)}{E(s)+\tau_q^2}
$$

**Ý nghĩa:** $E(s)$ là độ sai của $G(s)$ (4.2), còn $\tau_q^2$ là độ sai của $q$, cùng đơn vị sai số bình phương trung bình. Hai giá trị $q$ và $G$ cùng ước lượng giá trị của một thế cờ, nên giá trị nào ít sai hơn thì được tin nhiều hơn. Vì thế phần của $q$ là $w_q=\dfrac{E(s)}{E(s)+\tau_q^2}$: $E$ lớn tức $G$ kém tin cậy thì $w_q$ gần 1 và nhãn nghiêng về $q$, còn $E$ nhỏ thì nhãn nghiêng về $G$. $\tau_q^2$ được ước lượng từ cây bằng độ chênh giữa $G$ và $q$ sau khi trừ $E$.

**Ví dụ:** giả sử $\tau_q^2=0.05$, và một thế cờ mà search cho $q=0.1$ còn các ván thật cho $G=1$ (cùng góc nhìn Trắng).

| Tình huống | $E$ | Tỉ lệ từ $q$ | Value target |
|---|---|---|---|
| Sát cuối ván | 0 | 0% | 1.00 |
| Nhiều ván tách sớm | 0.01 | 17% | 0.85 |
| Một ván, cách cuối 10 nửa nước | 0.094 | 65% | 0.41 |
| Một ván, cách cuối 30 nửa nước | 0.282 | 85% | 0.24 |

Thế cờ sát phán quyết gần như tin hẳn vào kết quả ván. Thế cờ khai cuộc có nhiều ván cũng vậy. Thế cờ ở giữa một nhánh dài ít bằng chứng thì tin search nhiều hơn.

**Rủi ro lớn nhất của phần này:** 65% và 85% khác rất xa mức $q_{\text{ratio}}=0.2$ của mô hình cũ (2.5), và làm yếu đi điểm neo từ kết quả ván. Phép trộn giả định sai số của $q$ độc lập với $G$ và không có lệch, trong khi $q$ có thể lệch đúng theo niềm tin của mạng. Phải kiểm tra phần này trước khi dùng thật. Một phương án dự phòng là giữ công thức cũ tại node có một ván, và chỉ giảm tỉ lệ của $q$ khi có nhiều bằng chứng độc lập.

**Kiểm trên số thật (4/11, 573 ván đời 0 của cách truyền thống, 137 435 thế cờ, mỗi thế cờ coi như một node chỉ có một ván đi qua nên $G=z$, $\omega^2=0.0037$ như 4.4).** Mỗi nửa nước đi lên làm $E$ tăng trung bình $0.0037\times0.678\approx0.0025$. Ước lượng $\tau_q^2$ bằng trung bình $(G-q)^2$ trừ trung bình $E$, theo nhóm khoảng cách tới cuối ván:

| Cách cuối ván (nửa nước) | Số thế cờ | $E$ trung bình | $(z-q)^2$ trung bình | $\tau_q^2$ ước lượng |
|---|---|---|---|---|
| 1 đến 9 | 5 146 | 0.009 | 0.391 | 0.382 |
| 10 đến 29 | 11 164 | 0.045 | 0.595 | 0.550 |
| 30 đến 79 | 26 062 | 0.132 | 0.569 | 0.437 |
| 80 đến 159 | 34 319 | 0.295 | 0.480 | 0.185 |
| từ 160 | 60 744 | 0.683 | 0.206 | **-0.477** |

Ước lượng gộp cả cây ra $-0.023$, tức vô nghĩa (phương sai âm, kéo $w_q$ lên quá 1). Hai nguyên nhân: $E$ cộng dồn tuyến tính theo khoảng cách nên ở ván dài vượt cả độ dao động của kết quả ván (0.608); và thế cờ cách cuối ván rất xa chỉ có trong ván dài, mà ván dài phần lớn là hoà, nên $(z-q)^2$ ở đó nhỏ. Mạng đời 0 còn ngẫu nhiên ($q$ theo góc Trắng có độ lệch chuẩn chỉ 0.086), nên phép đo này thô, nhưng nó cho thấy cách ước lượng $\tau_q^2$ gộp cả cây không đứng vững. **Mình quyết định (4/11):** $\tau_q^2$ chỉ ước lượng từ các node có $E$ nhỏ (mặc định $E<0.05$, nơi phần trừ $E$ ít ảnh hưởng), và không bao giờ nhỏ hơn 0.01; mỗi đời log thêm $\tau_q^2$ theo từng nhóm khoảng cách như bảng trên. Việc $E$ có nên bị chặn trên bởi độ dao động kết quả ván hay không để mô phỏng quyết định (phần 14), vì chặn hay không chặn đều chưa biết là hại hơn lợi. Với số đời 0 này, $w_q$ trung bình theo nhóm là khoảng 2%, 10%, 25%, 42% và 63% (với $\tau_q^2\approx0.4$), so với 20% cố định của cách truyền thống.

**Với cờ vua:** nếu value head cho ra thắng, hòa, thua, thì $G$, $q$ và value target được tính riêng cho từng thành phần với cùng các trọng số.

---

## 6. Rẽ nhánh

### 6.1 Quét toàn cây

Đầu mỗi đời, bước quét xem các node trong cây và lấy mẫu một nước từ phân bố lượt thăm đã lưu với temperature 0.5. Nếu ra một nước chưa từng chơi tại node đó, engine tự chơi từ nước đó đến hết ván.

$$
\Pr(a)=\dfrac{\big(n(a)\big)^{\frac{1}{T}}}{\sum_{j\in A(s)}\Big(\big(n(j)\big)^{\frac{1}{T}}\Big)}
$$

**Ý nghĩa:** $\Pr(a)$ là xác suất bước quét chọn nước $a$ tại node đang xét. $n(a)$ là số lượt thăm của $a$ trong lần search đã lưu tại node (số lượt đi qua nước $a$, ví dụ 560 trong 800 lượt; 2.1), $j$ chỉ là biến đếm chạy qua mọi nước search đã thăm tại node, tức $j\in A(s)$ (tập các nước đã thăm, 2.1), và $T$ là temperature (dùng chữ $T$ để không lẫn với $\tau_q^2$, $\tau_d^2$ ở các phần khác). Với $T=0.5$ thì $\dfrac{1}{T}=2$, số lượt thăm được bình phương, nên nước nhiều lượt thăm càng được ưu tiên. Node càng phân vân (lượt thăm dàn đều) thì càng dễ ra nước khác nước đã chơi, và nhánh rất tệ ít khi được thử.

**Ví dụ:** tỉ lệ thăm 0.70, 0.25, 0.05 trở thành xác suất khoảng 0.88, 0.11, 0.005. Nếu chỉ mới chơi nước đầu tiên, mỗi lần quét node này có khoảng 12% cơ hội ra một nước chưa chơi (tức rẽ nhánh). Sau khi nước thứ hai đã chơi, cơ hội chỉ còn khoảng 0.5%.

Bước quét chỉ đọc số đã lưu nên không cần chạy mạng. Mỗi node được quét một lần mỗi đời và mọi node có cơ hội như nhau, nên node tàn cuộc hiếm gặp vẫn được rẽ, và các nhánh đó rất rẻ vì ván ngắn: rẽ ở nửa nước 70 của ván 80 nửa nước chỉ tốn 10 nửa nước.

### 6.2 Tự chơi với temperature 0

Sau điểm rẽ, ở mỗi nước ván chơi nước có nhiều lượt thăm nhất (temperature 0). Temperature không biến mất mà được chuyển sang bước quét. Trong cách cũ, mỗi lần temperature chọn nước khác là một nhánh ẩn, không để lại dấu vết, và làm nhiễu nhãn phía trước. Trên cây, mỗi lần rẽ đều được ghi lại và $\rho$ cân lại được. Nhiễu Dirichlet vẫn được giữ: đó là nhiễu ngẫu nhiên cộng vào prior của thế cờ gốc mỗi lần search (như AlphaZero và lc0), để search thỉnh thoảng thăm cả nước có prior thấp.

Ở đời đầu cây còn trống, nên bước quét lặp ngay trong đời đó: chơi một ván, quét lấy nhánh mới, chơi tiếp, đến khi hết ngân sách. Theo số đo 4/11 thì chỉ cần hai lượt: lượt một chơi một đợt ván từ thế khởi đầu (mỗi máy một đợt 128 ván song song, chỉ khác nhau nhờ nhiễu Dirichlet); một ván đời 0 dài khoảng 240 nửa nước và mỗi node có khoảng 58% cơ hội ra điểm rẽ, nên mỗi ván cho khoảng 140 điểm rẽ, và vài trăm ván đã cho hàng chục nghìn điểm rẽ, dư cho khoảng 2 600 ván cả đời; lượt hai quét cây đó một lần rồi chơi các điểm rẽ đã xáo trộn tới hết ngân sách. Chủ dự án chấp nhận đời 0 chậm hơn một chút vì chỉ làm một lần (4/11).

### 6.3 Chọn điểm rẽ khi vượt ngân sách: ngẫu nhiên (đã chốt)

**Điểm rẽ** là một cặp (node, nước chưa chơi) mà bước quét ở 6.1 lấy ra. **Ngân sách** của một đời là số lần chạy mạng dành cho tự chơi trong đời đó. Trên một cây lớn, các điểm rẽ quét được thường cần nhiều lần chạy mạng hơn ngân sách, nên phải chọn chơi điểm rẽ nào.

**Quy tắc:** xáo trộn ngẫu nhiên danh sách điểm rẽ của đời, rồi chơi lần lượt theo thứ tự đó cho tới khi hết ngân sách. Như vậy điểm rẽ nào cũng có cùng cơ hội được chơi, không ưu tiên theo tín hiệu nào. Ván cuối cùng được chơi trọn dù vượt ngân sách một chút; số lần chạy mạng vượt được ghi lại và trừ vào ngân sách đời sau, nên tổng số lần chạy mạng vẫn khớp với bên so sánh. Nếu chơi hết danh sách mà còn ngân sách thì quét lại cây như ở đời đầu (6.2).

**Ví dụ:** bước quét lấy ra 3000 điểm rẽ, mỗi ván từ một điểm rẽ tốn trung bình 40 nửa nước × 800 lượt thăm = 32000 lần chạy mạng, và ngân sách là 40 triệu lần chạy mạng. Ngân sách chỉ đủ cho khoảng 40000000/32000 = 1250 ván, nên 1250 điểm rẽ đầu tiên trong danh sách đã xáo trộn được chơi, 1750 điểm còn lại bị bỏ ở đời này. Đời sau bước quét chạy lại từ đầu nên các điểm bị bỏ có thể được quét ra lần nữa.

**Số đo thật thay cho ví dụ trên (4/11, 137 435 thế cờ của 573 ván đời 0 cách truyền thống, coi mỗi thế cờ là một node đã chơi một nước):** với $T=0.5$, xác suất một lần quét ra nước chưa chơi trung bình 0.58 mỗi node (mạng đời 0 rải lượt thăm rất đều), nên cây khoảng 1.6 triệu node (phần 3) cho cỡ 900 nghìn điểm rẽ mỗi lần quét. Một ván rẽ trung bình dài 157 nửa nước kể từ điểm rẽ, tức khoảng 157 × 490 ≈ 77 nghìn lần chạy mạng, nên 200 triệu chỉ đủ cho khoảng 2 600 ván rẽ, tức chừng 0.3% số điểm rẽ quét được (mỗi ván thêm khoảng 157 node, cộng lại khớp 400 nghìn node mới mỗi đời ở phần 3). Trung bình mỗi node chỉ được rẽ thêm một lần sau vài trăm đời; node gần gốc thì có nhiều ván vì mọi ván rẽ bên dưới đều đi qua nó. Khi mạng mạnh lên, lượt thăm dồn hơn và xác suất rẽ mỗi node sẽ giảm. Ví dụ 3000 điểm rẽ ở trên dùng giả định cũ (40 triệu, 800 lần chạy mạng mỗi nửa nước).

**Vì sao chọn ngẫu nhiên:** bước quét ở 6.1 đã quyết định nên rẽ ở đâu và với xác suất bao nhiêu. Chọn ngẫu nhiên giữ nguyên phân bố đó, chỉ thu nhỏ số lượng cho vừa ngân sách, và không thêm giả định hay tham số nào phải chỉnh. Khác với cắt lá ngẫu nhiên (8.3), ở đây ngẫu nhiên không làm phí dữ liệu, vì điểm rẽ chưa được chơi thì chưa tốn lần chạy mạng nào và đời sau vẫn có thể được quét ra lại. Các quy tắc ưu tiên theo tín hiệu dưới đây đều dựa trên tín hiệu nhiễu và cần ngưỡng phải chỉnh, nên ngược với phương châm ít phải tinh chỉnh. Ngoài ra, nếu cách mới vẫn hơn cách cũ khi chọn ngẫu nhiên thì kết luận càng chắc. Các tín hiệu ưu tiên dưới đây được ghi lại làm phương án thử sau, chỉ dùng nếu log (phần 15) cho thấy chọn ngẫu nhiên là chỗ đang làm cách mới yếu đi.

**Phương án để sau: ưu tiên theo tín hiệu.** Muốn nhãn tại một node thay đổi rõ, node đó cần nhiều ván tách ngay bên dưới nó. Một thế cờ giữa ván thường chỉ có khoảng một ván độc lập cho mỗi nhánh, nên với cách chọn ngẫu nhiên cái sai hiếm vẫn chủ yếu phải chờ mạng tự tiến bộ. Các tín hiệu có thể dùng:

- **Giá trị search tụt mạnh vài nửa nước sau một nước.** Tín hiệu này ít nhiễu vì rất gần, và đã được lưu sẵn. Ví dụ, sau một nước thí quân vô lý, đối phương ăn quân và $q$ rơi mạnh. Mất quân là điều mạng dễ nhận ra ở các thế ngay sau đó, nên $q$ phản ánh được việc nước thí quân kia không đền bù.
- **Bất đồng giữa search và kết quả ván.** Tín hiệu này quá nhiễu khi mới có một ván: khoảng 32% trường hợp vượt 1 độ lệch chuẩn chỉ do ngẫu nhiên. Nên dùng nó để xác nhận hơn là để phát hiện.

Các ván thêm vào phải tách nhau ngay dưới node đang xét. Bản đánh giá từ một AI khác cũng dẫn một nghiên cứu về việc quay lại những thế có độ lệch lớn giữa đánh giá và kết quả: "Regret-Guided Search Control for Efficient Learning in AlphaZero" (Tsai và cộng sự, ICLR 2026, arXiv 2602.20809). Mình đã đối chiếu phần tóm tắt trên arXiv: bài lưu các thế từ ván tự chơi và từ các node MCTS vào một bộ nhớ ưu tiên theo "regret" (độ lệch giữa đánh giá của tác tử và kết quả thực), rồi dùng chúng làm điểm bắt đầu ván mới; hơn AlphaZero trung bình 77 Elo và hơn Go-Exploit 89 Elo trên cờ vây 9×9, Othello 10×10 và Hex 11×11. Công thức regret chính xác mình chưa đọc.

**Giới hạn không vượt qua được:** nếu sau nước sai cả hai bên cùng mù thì kết quả ván không xấu đi, nên không có tín hiệu nào cả.

---

## 7. Policy target mới

### 7.1 Ý tưởng

Nhắc lại hai đại lượng cùng nói về thế cờ con $sa$ (2.1, 4.1): $Q(sa)$ là **giá trị search** của $sa$, tức niềm tin của mạng sau khi nhìn sâu hơn, tính từ các lượt thăm trong một lần search; $G(sa)$ là **giá trị tổng hợp từ kết quả các ván thật** đã đi qua $sa$. Search chia lượt thăm chủ yếu theo **chênh lệch $Q$ giữa các thế cờ con**: thế cờ con nào có $Q$ cao hơn (đối với bên đang đi) thì nước dẫn tới nó được thăm nhiều hơn. Cây trò chơi có thêm **chênh lệch $G$** đến từ kết quả ván thật. Vì vậy ta sửa chênh lệch $Q$ về phía chênh lệch $G$, sửa nhiều hay ít tùy theo độ tin cậy của bằng chứng, rồi hỏi: nếu search có các giá trị đã sửa thì nó sẽ chia lượt thăm thế nào? Câu trả lời là nhãn mới.

Nếu tại node chưa có ít nhất hai nước đã chơi thì nhãn giữ nguyên là $\pi$, nên một ván đơn lẻ không làm nhiễu nhãn policy.

### 7.2 Công thức, theo từng bước

**Nhắc ký hiệu dùng trong phần này.** $s$ là thế cờ đang xét, $a$ là một nước đi từ $s$, $sa$ là thế cờ sau nước đó. $N=\sum_{a\in A(s)}\big(n(a)\big)$ là tổng số lượt thăm đi qua các nước tại $s$, $n(a)$ là số lượt thăm đi qua nước $a$, $\pi(a)=\dfrac{n(a)}{N}$ là tỉ lệ lượt thăm. $Q(sa)$ là giá trị search của thế cờ con $sa$ (trung bình các giá trị đánh giá ở đáy cây search qua $n(a)$ lượt thăm đi qua $sa$; niềm tin của mạng, góc nhìn bên đang đi tại $s$). $q(s)=Q(sa^*)$ là giá trị search dùng làm nhãn value, với $a^*$ là nước có nhiều lượt thăm nhất. $G(sa)$ là giá trị tổng hợp từ kết quả các ván thật đi qua $sa$ (góc nhìn Trắng), $E(sa)$ là sai số bình phương trung bình của nó. $C(s)$ là tập các nước đã chơi thật tại $s$, $A(s)$ là tập các nước search đã thăm tại $s$, $\rho_s(a)$ là trọng số của nhánh $a$ (4.3). $P(a)$ là prior thô của mạng cho nước $a$, $P_0$ là tổng prior của các nước search không thăm lượt nào. Đầy đủ ở 2.1 và phụ lục A.

Xét ví dụ dùng lại số của 4.3: node $s$ do Trắng đi, $N=800$ lượt thăm, $c=1.3$ (hệ số khám phá của search, tức cpuct; cấu hình tự chơi ở 2.5 đặt nó cố định 1.3, không tăng theo số lượt thăm), $P_0=0.10$ (tổng prior của các nước search không thăm lượt nào). Có ba nước search đã thăm, ký hiệu $a_1$, $a_2$, $a_3$. Hai nước đầu đã chơi, nước thứ ba chưa.

| Nước $a$ | $\pi(a)$ | $Q(sa)$ (góc nhìn bên đang đi) | $G(sa)$ (góc nhìn Trắng) | $E(sa)$ |
|---|---|---|---|---|
| $a_1$ | 0.70 | 0.10 | -0.25 | 0.10 |
| $a_2$ | 0.25 | 0.08 | +0.50 | 0.05 |
| $a_3$ | 0.05 | 0 | chưa chơi nên chưa có | chưa có |

Giả sử $\tau_d^2=0.002$. Đây là một số chung cho cả cây, giống $\omega^2$ ở 4.2: sai số bình phương trung bình của $d(sa)$ (bước 1 ngay dưới) so với chênh lệch giá trị thật giữa thế cờ con $sa$ và mức chung của các thế cờ con. Nó được ước lượng từ cây, và $\sqrt{0.002}\approx 0.045$ nghĩa là $d(sa)$ thường lệch khoảng 0.045. Trọng số đã tính ở 4.3 là 0.47 và 0.53, nên $G(s)\approx 0.148$.

**Bước 1: chênh lệch của search và của kết quả ván.**

$$
\bar Q=\sum_{j\in C(s)}\Big(\rho_s(j)\,Q(sj)\Big),\qquad d(sa)=Q(sa)-\bar Q,\qquad \delta(sa)=\sigma_s\big(G(sa)-G(s)\big)
$$

$j$ là biến đếm chạy qua các nước đã chơi tại $s$ (nên $sj$ là các thế cờ con đã chơi), còn $a$ là một nước đã chơi bất kỳ. $\bar Q$ là trung bình của $Q$ trên các thế cờ con đã chơi, tính theo trọng số $\rho$: đây là "mức chung" mà search đánh giá cho các thế cờ con. $d(sa)$ là điều search nói về thế cờ con $sa$ so với mức chung: dương nghĩa là search thấy $sa$ tốt hơn mức chung đối với bên đi tại $s$. $\delta(sa)$ là điều kết quả ván nói về $sa$ so với $G(s)$, mức chung của các ván thật. $\sigma_s$ bằng +1 khi Trắng đi và -1 khi Đen đi, để $\delta(sa)$ cũng ở góc nhìn bên đi tại $s$ như $Q$, vì $G$ tính theo góc nhìn Trắng.

Trong ví dụ, $\bar Q\approx 0.0894$. Thế cờ con $sa_1$ có $d\approx +0.011$, $\delta\approx -0.398$. Thế cờ con $sa_2$ có $d\approx -0.009$, $\delta\approx +0.352$. Search nói $sa_1$ nhỉnh hơn một chút, còn kết quả ván nói $sa_2$ tốt hơn nhiều: hai nguồn đang bất đồng.

**Bước 2: gộp hai chênh lệch.**

$$
D(sa)=d(sa)+\frac{\tau_d^2}{\tau_d^2+E(sa)}\,(\delta(sa)-d(sa))
$$

Phân số $\dfrac{\tau_d^2}{\tau_d^2+E(sa)}$ là **mức tin vào kết quả ván**: gần 0 khi $E(sa)$ lớn so với $\tau_d^2$ (ít bằng chứng), gần 1 khi $E(sa)$ rất nhỏ. $D(sa)$ là chênh lệch của search, dịch về phía chênh lệch của kết quả ván một đoạn bằng mức tin đó. Nếu mức tin bằng 0 thì $D(sa)=d(sa)$ (giữ nguyên search), nếu bằng 1 thì $D(sa)=\delta(sa)$ (tin hoàn toàn kết quả ván).

Trong ví dụ, mức tin khoảng 0.020 và 0.038, nên $D(sa_1)\approx +0.003$ và $D(sa_2)\approx +0.005$. Search đã đổi thứ tự rất nhẹ.

**Bước 3: giá trị mới.** Thế cờ con đã chơi có $Q'(sa)=\bar Q+D(sa)$, tức giá trị search được sửa một đoạn về phía kết quả ván. Thế cờ con chưa chơi không có $G$ nên giữ nguyên $Q$. Trong ví dụ, $Q'$ khoảng 0.092, 0.094 và 0 cho $sa_1$, $sa_2$, $sa_3$.

**Bước 4: dựng lại phần prior từ dữ liệu search.**

$$
\lambda=\dfrac{c}{\sqrt{N}},\qquad \beta=\sum_{a\in A(s)}\Big(\pi(a)\,Q(sa)\Big)+\lambda\,(1-P_0),\qquad w_a=\max\Big(\pi(a)\,\big(\beta-Q(sa)\big),\ \epsilon\Big)
$$

Ở bước này, $a$ chạy qua **mọi nước search đã thăm**, tức $a\in A(s)$ (kể cả nước chưa chơi như $a_3$), vì $\pi$ và $Q$ của chúng đều có trong node.

Search chọn mỗi lượt thăm bằng quy tắc PUCT: thăm nước có điểm lớn nhất, với điểm của nước $a$ là $Q(sa)+c\,P(a)\,\dfrac{\sqrt{N}}{1+n(a)}$ (giá trị search của thế cờ con $sa$ mà nước $a$ dẫn tới, cộng một phần thưởng khám phá), trong đó $P(a)$ là prior của mạng (đầu ra thô) và $n(a)$ là số lượt thăm hiện có. Số hạng sau là phần thưởng khám phá, giảm khi nước đã được thăm nhiều. Sau nhiều lượt, điểm của mọi nước được thăm gần bằng nhau, và $\beta$ là mức điểm chung đó. Từ đó suy ra $\pi(a)\approx\dfrac{\lambda\,P(a)}{\beta-Q(sa)}$, hay $\pi(a)\,\big(\beta-Q(sa)\big)\approx\lambda\,P(a)$.

Vì vậy $\lambda=\dfrac{c}{\sqrt{N}}$ là mức tin vào prior, giảm dần khi có nhiều lượt thăm. Vì cấu hình tự chơi giữ $c$ cố định (2.5), $\lambda$ tính đúng như vậy, không phải xấp xỉ. $w_a=\pi(a)(\beta-Q(sa))$ thực chất là prior $P(a)$ nhân với $\lambda$. Cách này dựng lại prior từ $\pi$ và $Q$ đã lưu, thay vì dùng thẳng prior mà engine ghi lại, vì nó có một tính chất cần thiết: khi $Q'=Q$ (không có bằng chứng nào) thì bước 5 cho lại đúng $\pi'=\pi$. Nếu dùng thẳng prior thì phép xấp xỉ "điểm của mọi nước gần bằng nhau" sẽ làm $\pi'$ lệch khỏi $\pi$ ngay cả khi không có bằng chứng nào. Chỉ $P_0$ cần prior thật: nó là tổng prior đã trộn nhiễu của các nước không được thăm (7.4). $\epsilon$ là số dương rất nhỏ để $w_a$ không âm.

Trong ví dụ, $\lambda\approx 0.0460$, $\beta\approx 0.1314$, và $w$ khoảng 0.0220, 0.0128, 0.0066 cho $a_1$, $a_2$, $a_3$.

**Bước 5 và 6: tìm $\beta'$ và đọc ra nhãn mới.**

$$
\pi'(a)=\frac{w_a}{\beta'-Q'(sa)},\qquad \beta'\text{ được chọn để tổng }\pi'\text{ bằng 1}
$$

Công thức này chính là câu hỏi "search sẽ chia lượt thăm thế nào nếu giá trị các nước là $Q'$ thay vì $Q$". Dùng cùng $w_a$ (tức cùng prior) nhưng thay $Q$ bằng $Q'$ trong mẫu số. $\beta'$ là mức điểm chung mới. Nó phải lớn hơn mọi $Q'(sa)$ để mẫu số dương, và tổng $\pi'$ giảm khi $\beta'$ tăng, nên tìm $\beta'$ bằng phép tìm nghiệm số (ví dụ chia đôi khoảng). Trong ví dụ, $\beta'\approx 0.1294$, và kết quả được so sánh trong bảng sau.

| Nước | Nhãn cũ $\pi$ | Ít bằng chứng ($E$ là 0.10, 0.05) | Nhiều bằng chứng ($E$ là 0.010, 0.004; $G$ là -0.20, +0.30) |
|---|---|---|---|
| $a_1$ | 0.70 | 0.59 | 0.16 |
| $a_2$ | 0.25 | 0.36 | 0.81 |
| $a_3$ | 0.05 | 0.05 | 0.03 |

Khi ít bằng chứng, nhãn chỉ dịch nhẹ. Khi bằng chứng đủ nhiều, nhãn lật sang $a_2$, dù search vẫn cho $a_1$ giá trị cao hơn một chút.

### 7.3 Tác dụng bằng lời

- **Phá vòng tự xác nhận.** Mạng không còn chỉ học từ ý kiến của search, vốn do chính nó dẫn đường.
- **Sửa theo bằng chứng.** Vài ván may mắn không lật được nhãn, nhưng nhiều ván thì có thể.
- **Tạo hiệu ứng dây chuyền.** Nhãn mới làm policy nghiêng về nước đã chứng tỏ mình, search đời sau thăm nước đó nhiều hơn, cây rẽ nhánh khác đi, và các ván mới đem thêm bằng chứng.

### 7.4 Những điều cần lưu ý

- **Công thức rất nhạy với $\tau_d^2$.** $\pi'$ tỉ lệ với $1/(\beta'-Q')$, mà hiệu $\beta'-Q'$ chỉ cỡ 0.05 trong ví dụ, nên một thay đổi 0.005 của $Q'$ đã làm nhãn đổi khoảng 10%. $\tau_d^2$ quyết định $Q'$ dịch bao nhiêu, nên con số này phải đo từ dữ liệu. **Quyết định 4/11:** ước lượng $\tau_d^2$ theo cùng cách đã chốt cho $\tau_q^2$ ở phần 5 (chỉ từ node có $E$ nhỏ, có sàn dương, mặc định 0.0005), vì nó cũng là một phép trừ $E$ khỏi một độ chênh thấy được và có cùng nguy cơ ra số âm; log $\tau_d^2$ theo từng nhóm khoảng cách tới cuối ván.
- **Lợi ích tập trung ở các node có nhiều bằng chứng.** Nhiều node sâu sẽ có $\pi'$ gần như bằng $\pi$.
- **$\tau_d^2$ là số trung bình toàn cây**, nên cái sai hiếm vẫn được sửa khá chậm.
- **Nhãn gần gốc chỉ đến từ một lần search có nhiễu Dirichlet**, trong khi cách cũ có nhiều mẫu nhiễu khác nhau. Số đo 4/11 trên 573 lần search thế khởi đầu ở đời 0 (mạng ngẫu nhiên, prior gần đều nên nhiễu chiếm phần lớn): một nước có tỉ lệ lượt thăm trung bình chỉ khoảng 0.055 nhưng độ lệch chuẩn giữa các lần search tới 0.08, có lần lên tới 0.55; nước được thăm nhiều nhất đổi liên tục (a2a4 40 lần, e2e3 39 lần, c2c4 33 lần, ...). Cách truyền thống search thế khởi đầu khoảng 1 700 lần mỗi đời nên nhãn trung bình gần hết nhiễu; cây trò chơi chỉ search mỗi node khi tạo ra và khi search lại. **Quyết định 4/11:** node lưu trung bình các lần search (phần 3, nhóm 1) thay vì lần gần nhất, với lần cũ bị nhân $\gamma$ mỗi đời ($\gamma$ là hệ số giảm bằng chứng cũ, định nghĩa ở 8.4); tính chất "không có bằng chứng thì $\pi'=\pi$" vẫn giữ, với $\pi$ là trung bình đó. Số lần search của các node gần gốc do phần 9 quyết định, và đây là một lý do chính để search lại các node gần gốc.
- **Prior nào được dùng ở bước 4.** Tại gốc của mỗi lần search, lc0 ghi đè prior của mạng bằng prior đã trộn nhiễu Dirichlet ($(1-\epsilon)P(a)+\epsilon\,\eta_a$, với $\eta_a$ là nhiễu; `upstream/lc0/src/search/classic/search.cc` dòng 202 đến 218 và 2191 đến 2194). PUCT chạy trên prior đã trộn nhiễu, nên $P_0$ ở bước 4 phải tính bằng prior đã trộn nhiễu. Còn $w_a$ được dựng lại từ $\pi$ và $Q$ nên tự phản ánh prior đã trộn nhiễu. Engine mới ghi cả prior đã trộn nhiễu lẫn prior thô của mạng (12.7); prior thô chỉ dùng cho log.
- **Nguồn tham khảo:** dạng $\pi'$ giống nghiệm của Grill và cộng sự (ICML 2020). Phần mới là $Q'$ sửa theo kết quả ván, cũng là phần ít được kiểm chứng nhất, nên được thử sau cùng.

---

## 8. Cắt tỉa và làm cũ bằng chứng

### 8.1 Giữ kích thước cây

$$
W=\frac{\text{kích thước cây}}{\text{số node mới mỗi đời}}
$$

**Ý nghĩa:** $W$ là số đời dữ liệu tồn tại, tương đương cửa sổ của replay buffer: mỗi đời cây được làm mới $1/W$ số node.

**Đã chốt (4/11, chủ dự án chọn sau khi đo):** $W=4$ cố định, để mỗi đời cây được làm mới một phần tư, như cửa sổ trượt 4 đời của cách truyền thống; ngân sách giữ 200 triệu lần chạy mạng mỗi đời. Kích thước cây vì thế không cố định mà bằng tổng số node mới của 4 đời gần nhất: sau khi gộp node của đời mới, cắt lá (8.3) cho tới khi số node còn bằng tổng đó; 4 đời đầu chưa cắt. Với số đo đời 0 (mỗi lần search khoảng 490 lần chạy mạng nhờ bộ nhớ đệm của mạng, nên 200 triệu cho khoảng 400 nghìn node mới mỗi đời, ít hơn một chút nếu tính phần ngân sách dành cho search lại ở phần 9), cây khoảng 1.4 đến 1.6 triệu node, khoảng 420 MB; nếu search lại dùng đủ 20% ngân sách như đã chốt ở 9.3 thì chỉ còn khoảng 160 triệu cho ván rẽ, tức khoảng 330 nghìn node mới mỗi đời và cây khoảng 1.3 triệu node, khoảng 340 MB. Con số 1 triệu node trước đây dựa trên giả định mỗi lượt thăm tốn một lần chạy mạng; nó không phải một nguyên tắc nên được bỏ. Khi số node mới mỗi đời thay đổi theo mạng, cây tự đổi theo mà vẫn giữ đúng 4 đời.

### 8.2 Cắt mà giữ thống kê

Khi cắt một lá $sa$ (node con của $s$ qua nước $a$), chỉ bỏ phần tốn bộ nhớ (thế cờ và nhãn huấn luyện của $sa$). Các số $\pi(a)$, $m(sa)$, $G(sa)$ và $E(sa)$ vẫn nằm ở node cha $s$ (phần 3). Nhờ vậy, phán quyết cuối ván không mất, và các giá trị phía trên không bị đảo lộn. Thứ mất đi chỉ là mẫu huấn luyện của node bị cắt.

### 8.3 Chọn lá nào để cắt: lá có $m$ nhỏ nhất (đã chốt)

**Quy tắc:** mỗi lần cắt lá có $m$ nhỏ nhất trong các lá hiện có (lá là node không có node con, 2.1; $m$ là số ván đi qua node, đã nhân $\gamma$ mỗi đời, phần 3 và 8.4), rồi lặp lại cho tới khi đủ số node cần cắt của đời (8.1). Khi mọi node con của một node đã bị cắt thì node đó trở thành lá và có thể bị cắt ở các lần sau. Vì số lá thường ít hơn số node cần cắt (mỗi ván chỉ kết thúc ở một lá), các nhánh bị ăn dần từ cuối ván lên. Hai lá có $m$ bằng nhau thì chọn ngẫu nhiên một lá.

**Cắt lá có $m$ nhỏ nhất gần như là cắt lá cũ nhất.** Một lá thường là node cuối của đúng một ván, nên $m$ của nó bằng $\gamma^{\text{số đời kể từ ván đó}}$. Ví dụ với $W=4$, $\gamma=0.75$: lá của ván chơi 1 đời trước có $m=0.75$, lá của ván chơi 4 đời trước có $m=0.75^4\approx0.316$, nên lá cũ bị cắt trước. Một node trở thành lá sau khi mất hết con mà có 2 ván đi qua thì có $m$ gấp đôi một lá một ván cùng tuổi, nên được giữ lâu hơn: chỗ có nhiều bằng chứng được giữ lâu hơn.

**Vì sao không cắt ngẫu nhiên.** Bạn đã chọn cắt ngẫu nhiên, nhưng mình đổi vì cắt ngẫu nhiên đem vào một cái hại đã biết mà không có lợi gì bù lại, nên trái phương châm (15.1). Cách cũ dùng replay buffer: mỗi mẫu được giữ đúng $W$ đời rồi bỏ, mẫu cũ nhất bỏ trước. Cắt ngẫu nhiên làm thời gian sống của mẫu tản ra, vì lá mới và lá cũ có cùng cơ hội bị cắt. Giả sử đơn giản mỗi đời cắt ngẫu nhiên 1/4 số lá. Khi đó một lá vừa sinh có 1/4 khả năng bị cắt ngay đời sau, tức ván vừa tốn search để chơi bị bỏ sau một lượt huấn luyện. Ngược lại, khoảng $0.75^{8}\approx10\%$ số lá còn sống sau 8 đời, gấp đôi $W$, tức nhãn của mạng rất cũ vẫn được học. Cắt lá có $m$ nhỏ nhất tránh được cả hai, không có tham số nào phải chỉnh, và giữ đúng ý của replay buffer là bỏ dữ liệu cũ nhất trước.

### 8.4 Giảm dần bằng chứng cũ

$$
\gamma=1-\frac{1}{W}
$$

Mỗi đời, mọi $m$ đã lưu ($m$ là số ván đi qua một node, phần 3) được nhân với $\gamma$. $W$ là số đời dữ liệu tồn tại, định nghĩa ở 8.1.

**Ý nghĩa:** ván cũ do mạng cũ chơi, nên càng cũ càng ít được tính. Tổng trọng lượng của một ván qua các đời bằng đúng $W$, nên cây nhớ lâu tương đương replay buffer cũ.

**Ví dụ:** với $W=4$ (đã chốt, 8.1), $\gamma=0.75$, nên một ván có trọng lượng 0.75 sau 1 đời, 0.56 sau 2 đời, và 0.32 sau 4 đời; cộng mọi đời lại là $1+0.75+0.56+\dots=4$, đúng bằng 4 lượt mà một mẫu của cách truyền thống được học trong cửa sổ 4 đời. Node cũ cũng tự được lấy mẫu ít đi. Cùng $\gamma$ này cũng làm nhẹ dần các lần search cũ trong trung bình search của node (phần 3, nhóm 1).

**Chưa giải quyết:** $E$ chưa tính đến việc ván cũ do mạng cũ chơi, nên độ sai thật của chúng lớn hơn số công thức cho ra.

---

## 9. Search lại

### 9.1 Vấn đề: các node gần gốc bị đóng băng

Ván mới bắt đầu từ điểm rẽ nên không search lại đoạn đường từ gốc. Nếu không xử lý, thế khởi đầu có thể giữ số liệu của đời 1 mãi mãi, gây ra các hậu quả:

1. **Khai cuộc bị kẹt.** Nước mà mạng mới thích nhưng mạng đời 1 gần như không thăm sẽ không bao giờ được rẽ ra.
2. **Nhãn policy dạy ngược.** Mạng mới bị dạy theo phân bố của mạng cũ, mà các node này lại được lấy mẫu nhiều nhất.
3. **Trọng số phản ánh cách chơi cũ.** $\rho$ dùng $\pi$ của lần search đời 1, nên $G$ gần gốc được tổng hợp theo cách chơi của mạng cũ chứ không phải mạng hiện tại.

### 9.2 Chọn node để search lại

$$
\text{ưu tiên}(s)=m(s)\times\hat\Delta\big(\text{tuổi}(s)\big)
$$

**Ý nghĩa:** $\text{tuổi}(s)$ là số đời đã trôi qua kể từ lần search gần nhất tại $s$. $m(s)$ là số ván đã đi qua $s$, đã nhân $\gamma$ theo mỗi đời (phần 3), cũng là tỉ lệ node được lấy mẫu huấn luyện (phần 10), nên là mức thường xuyên node được đem học. $\hat\Delta(\text{tuổi})$ là mức nhãn policy sai đi so với nhãn tính lại bằng mạng hiện tại khi nhãn đã cũ từng ấy đời. Tích của chúng là thiệt hại mà một lần search lại xóa được. Mọi lần search tốn như nhau, nên chọn tích lớn nhất là tối ưu.

$\hat\Delta$ được đo từ chính các node vừa search lại, bằng độ chênh giữa phân bố $\pi$ cũ và mới theo từng tuổi. Đời đầu chưa có số liệu thì lấy $\hat\Delta(\text{tuổi})=\text{tuổi}$.

**Sửa ngày 5/11, vì node lưu trung bình các lần search (phần 3, 7.4).** Search lại không còn thay nhãn mà cộng thêm một lần search vào trung bình, nên nhãn đang lưu chỉ dịch về phía lần search mới một phần $1/(k+1)$, với $k$ là số lần search đã có (đã nhân $\gamma$ mỗi đời). Độ chênh giữa trung bình đang lưu và một lần search mới gồm cả phần cũ (mạng đã đổi) lẫn phần nhiễu Dirichlet (số đo 7.4: ở đời 0 một nước có thể lệch từ 5.5% lên 55% chỉ vì nhiễu). Vì vậy $\hat\Delta$ được đo theo cả tuổi lẫn $k$, và

$$
\text{ưu tiên}(s)=m(s)\times\frac{\hat\Delta\big(\text{tuổi}(s),\,k(s)\big)}{k(s)+1}
$$

Đời đầu chưa có số liệu thì lấy $\hat\Delta=\text{tuổi}+1$. Ví dụ: gốc có $m=2600$, mới search $k=1$ lần, tuổi 0, ưu tiên $2600\times1/2=1300$; một node giữa ván có $m=3$, $k=1$, tuổi 3, ưu tiên $3\times4/2=6$. Gốc được search lại nhiều lần trước: sau 9 lần nữa ($k=10$) ưu tiên của nó còn $2600/11\approx236$, vẫn đứng trước. Như vậy search lại tự dồn vào các node được học nhiều nhất mà còn ít lần search, đúng chỗ nhiễu gây hại nhiều nhất.

**Ví dụ:** node A có $m=200$, tuổi 2, và node B có $m=3$, tuổi 8. Nếu $\hat\Delta$ bằng tuổi, ưu tiên là 400 và 24, nên A được search trước dù trẻ hơn.

### 9.3 Khi nào dừng

Search lại theo thứ tự ưu tiên đến khi **tuổi trung bình của nhãn, tính theo trọng số $m$, không vượt quá tuổi trung bình của nhãn trong cửa sổ dữ liệu của cách cũ**, với mức trần đề xuất là 20% ngân sách. Phần ngân sách còn dư chuyển sang sinh node mới.

**Tuổi trung bình của cách cũ.** Cửa sổ của cách cũ giữ dữ liệu của $W$ đời gần nhất. Nhãn của đời mới nhất có tuổi 0, nhãn của đời cũ nhất có tuổi $W-1$. Nếu mỗi đời đóng góp số mẫu như nhau thì tuổi trung bình là $\dfrac{W-1}{2}$; với $W=4$ đã chốt (8.1) là 1.5. (Bản trước ghi $W/2$, lỏng hơn nửa đời.) Với trung bình các lần search, tuổi của một node là tuổi trung bình của các lần search của nó theo trọng số đã giảm dần. Điều kiện dừng này bảo đảm nhãn trên cây không cũ hơn cách cũ, tức cách mới không mang một bất lợi đã biết về độ cũ của nhãn so với cách cũ.

**Vì sao thường không tốn nhiều.** Node sinh trong $W$ đời gần nhất tự có tuổi 0 đến $W-1$ như cách cũ, vì lá cũ nhất bị cắt trước (8.3). Chỉ các node sống lâu hơn $W$ đời mới làm tuổi trung bình vượt mức: đó là các node gần gốc, có nhiều ván đi qua nên không bị cắt. Các node này có $m$ lớn nên chiếm nhiều trọng số, và search lại vài node như vậy đã kéo tuổi trung bình xuống nhiều. Một lần search lại tốn bằng một nước của một ván, trong khi một ván rẽ tốn hàng chục nước. Đây là suy luận, chưa đo.

**Nhiễu là chỗ cách mới chịu thiệt có chủ ý (ghi 5/11).** Cách truyền thống search mỗi thế cờ một lần cho mỗi ván đi qua nó, nên thế cờ có $m$ ván đi qua được $m$ lần search với nhiễu độc lập. Cây trò chơi tiết kiệm đúng phần đó: ván rẽ không search lại đoạn chung từ gốc tới điểm rẽ. Với số đo đời 0 (ván dài khoảng 240 nửa nước, ván rẽ trung bình 157 nửa nước tính từ điểm rẽ, nên đoạn chung trung bình khoảng 83 nửa nước), 2 600 ván rẽ mỗi đời bỏ qua khoảng 2 600 × 83 ≈ 216 nghìn lần search, tức khoảng 106 triệu lần chạy mạng, hơn nửa ngân sách. Đưa mọi node về ngang cách truyền thống về nhiễu ($k=m$) sẽ xoá gần hết phần tiết kiệm của cây. Search lại theo ưu tiên ở 9.2 dồn vào các node có $m$ lớn nhất trước, nên một phần nhỏ ngân sách đã đưa vùng gần gốc (nơi nhiễu gây hại nhiều nhất vì được học nhiều nhất) về gần ngang. **Chủ dự án chốt (5/11): dùng tới 20% ngân sách mỗi đời cho search lại, cho cả nhiễu lẫn độ cũ.** Quy tắc: search lại theo thứ tự ưu tiên ở 9.2 cho tới khi dùng hết 20% ngân sách của đời, hoặc sớm hơn nếu mọi node đã có số lần search không ít hơn số ván đi qua ($k\ge m$, tức đã ngang cách truyền thống về nhiễu); điều kiện tuổi trung bình 1.5 ở trên trở thành một phép kiểm ghi vào log, không còn là điều kiện dừng. Log ghi mỗi đời trung bình theo trọng số $m$ của tỉ số $m/k$ (ngang cách truyền thống là 1) và độ dịch thật của nhãn sau mỗi lần search lại.

**Mức trần 20%** là con số duy nhất ở đây không suy ra được. Nó chỉ để chặn trường hợp search lại ăn gần hết ngân sách. Log ghi mỗi đời phần ngân sách đã dùng cho search lại và việc có chạm trần hay không (15.2). Nếu chạm trần thường xuyên, nhãn trên cây sẽ cũ hơn cách cũ; khi đó phải tìm nguyên nhân (ví dụ cây quá lớn so với số node mới mỗi đời) thay vì chỉ nâng trần.

Giá trị của search lại giảm rất nhanh theo thứ tự ưu tiên, vì node mới còn đem thêm kết quả ván, thế cờ mới và độ đa dạng. Mức 50% ngân sách trong đề xuất ban đầu vì thế có lẽ là quá nhiều.

---

## 10. Lấy mẫu huấn luyện

Mỗi node $s$ được lấy mẫu với xác suất tỉ lệ với $m(s)$, tức số ván đã đi qua $s$ (đã nhân $\gamma$ theo mỗi đời; đây chính là $m$ lưu ở node cha, phần 3).

**Ý nghĩa:** node có nhiều ván đi qua đứng thay cho nhiều ván, nên giữ được tỉ trọng theo độ sâu như cách cũ. Việc giảm $m$ cũng tự làm dữ liệu cũ rời khỏi quá trình học.

**Ví dụ:** thế khởi đầu có $m=1000$ được lấy mẫu nhiều gấp 1000 lần một node có $m=1$, đúng như 1000 ván của cách cũ đều có thế khởi đầu. Khác biệt là mọi lần đều dùng cùng một nhãn đã tổng hợp.

---

## 11. Vòng lặp mỗi đời

1. Huấn luyện mạng với mẫu lấy theo $m$.
2. Cắt lá có $m$ nhỏ nhất (8.3), giữ thống kê ở node cha, rồi nhân mọi $m$ với $\gamma$.
3. Search lại theo ưu tiên đến khi đạt điều kiện dừng hoặc chạm trần, và cập nhật bảng $\hat\Delta$.
4. Tính lại $\rho$, $G$, $E$ từ dưới lên theo thứ tự ở 4.5, dùng $\omega^2$ của đời trước (đời đầu dùng giá trị khởi đầu ở 4.5).
5. Quét cây với temperature 0.5, xáo trộn các điểm rẽ rồi chơi lần lượt (6.3), tự chơi với temperature 0 đến khi hết ngân sách.
6. Tính lại $\rho$, $G$, $E$ (4.5) với các ván mới, rồi ước lượng lại $\omega^2$, $\tau_q^2$, $\tau_d^2$ từ kết quả vừa tính để dùng cho đời sau, rồi tính value target và policy target.
7. Ghi log của đời (phần 15).

Khi chạy trên nhiều máy Colab, bước 3 và bước 5 được làm cùng lúc trên các máy Colab, bước 1 làm trên máy Colab huấn luyện, còn các bước khác làm trên điện thoại (12.6).

---

## 12. Áp dụng cho cờ vua

### 12.1 Mạng

Mạng chỉ có **hai đầu ra**: policy (xác suất cho 1858 nước) và value (thắng, hòa, thua). Không có đầu ra số nước còn lại (moves left head), là đầu ra thứ ba mà một số mạng lc0 có. Quy định này áp dụng cho cả hai bên so sánh.

Mạng là **11 khối × 64 kênh có SE** (tỉ lệ SE 8, như `FairyNet` của dự án cờ biến thể), đầu vào 112 mặt phẳng kiểu lc0 (`INPUT_CLASSICAL_112_PLANE`). Mã ở `co_vua/python/mang.py`. Hai đầu ra lấy theo mạng của engine biến thể (`custom_engine/python/model.py`), chỉ đổi cỡ bàn cờ và số loại nước, vì đây là phần trùng với cách cũ nên giữ như cách cũ:

- Policy head: tích chập 3×3 từ 64 về 64 kênh (có BN), rồi tích chập 1×1 từ 64 về 73 mặt phẳng, rồi lấy 1858 ô theo bảng `kConvPolicyMap` của lc0 (73 mặt phẳng × 64 ô, cách đánh số nước của AlphaZero).
- Value head: tích chập 1×1 từ 64 về 32 kênh (có BN), rồi hai lớp kết nối đầy đủ 2048 → 128 → 3 (thắng, hòa, thua).

Số tham số đếm trên mạng thật:

| Phần | Tham số |
|---|---|
| Lớp đầu, 112 mặt phẳng vào 64 kênh (kể cả BN) | 64640 |
| Thân 11 khối (mỗi khối 2 tích chập 3×3, BN, SE) | 832216 |
| Policy head | 41737 |
| Value head | 264771 |
| **Tổng** | **1203364**, khoảng 1.2 triệu |

Số phép nhân cho một lần đánh giá, tính tay: khoảng 59.1 triệu, trong đó thân mạng chiếm 51.9 triệu. Value head chiếm nhiều tham số (chủ yếu lớp 2048 → 128) nhưng ít phép nhân.

Mạng luôn chạy và xuất ở **fp32**, không dùng fp16 (bạn chốt). Khi xuất cho lc0, policy là logit (lc0 tự làm softmax trên các nước hợp lệ), còn WDL là xác suất: với mạng bọc bằng `onnx2leela`, backend ONNX của lc0 không làm softmax cho WDL (`neural/backends/onnx/network_onnx.cc` dòng 602 đến 624 và 945, 946). Mặt phẳng 109 (luật 50 nước) vào mạng dưới dạng số nửa nước thô, mạng tự chia cho 99.

**Đã kiểm khớp với lc0.** Script `co_vua/python/kiem_khop_lc0.py` so mạng chạy trong Python với mạng chạy trong lc0 trên 7 thế cờ: thế khởi đầu, Đen đi, Trắng đã nhập thành, có bắt tốt qua đường, thế lặp lại, phong cấp, Đen mất quyền nhập thành một cánh. Chỉ số policy của mọi nước hợp lệ trùng với chỉ số lc0 in ra. WL và D mà `lc0 treeplay` ghi lại trùng với Python tới 6 chữ số thập phân. Prior thô lệch tương đối tối đa khoảng 0.3%, vì lc0 lưu prior ở độ chính xác 16 bit; search cũng chạy trên chính các prior này. Như vậy bộ mã hoá 112 mặt phẳng (`co_vua/python/ma_hoa.py`), bảng chỉ số nước đi và việc xuất mạng đều đúng.

Tốc độ thực phải đo, vì với mạng nhỏ thì nút thắt có thể nằm ở CPU và chi phí mỗi lần gọi GPU, không nằm ở số phép nhân.

### 12.2 Nền mã nguồn (chưa chốt)

Dự án được làm trong `D:\chess_variant`, nơi đã có mã nguồn lc0 ở `upstream/lc0`, gồm sinh nước, search, định dạng đầu vào và self-play cho cờ vua. Thư mục này cũng có bản search đã chỉnh, kiểm thử và công cụ Colab của dự án cờ biến thể, nhưng các phần đó dựa trên Fairy-Stockfish và ghi cho bàn 10×10 (`custom_engine/python/model.py`: chính sách 10600 đầu ra, 106 loại nước × 100 ô). Đề xuất là lấy lc0 làm nền cho engine, rồi dùng lại quy trình huấn luyện và công cụ Colab. Phần self-play của lc0 mình đã đọc ở 2.5; phần còn lại cần đọc trước khi chốt. Lc0 dùng giấy phép GPL (tệp `upstream/lc0/COPYING`). Bạn đã chốt: engine kế thừa từ lc0, và tham số sinh dữ liệu cùng huấn luyện của mốc truyền thống lấy theo cách bạn đã chạy với engine cờ biến thể (2.5). Cách chạy trên nhiều máy Colab ở 12.6.

### 12.3 Những điều có lợi khi làm cờ vua

- Luật cờ, sinh nước và search đã có sẵn, được kiểm chứng rộng rãi, và hai bên đi luân phiên.
- Có sẵn lc0 làm mẫu cho cách truyền thống, nên mốc so sánh dựa trên một cấu hình đã được nhiều người tinh chỉnh.
- Có sẵn Stockfish, một engine rất mạnh, để **đo** nhãn sai và nước hớ. Nó không dùng để tạo nhãn và không dùng để kết luận bên nào hơn, nên hệ thống vẫn là học tăng cường thuần túy và phép so sánh không bị ảnh hưởng (15.2).

### 12.4 Những điều khác với các phương án trước

- **Hòa.** Dự án chỉ nhằm thử nghiệm mô hình, không nhắm tới mạng rất mạnh, nên tỉ lệ hòa cao ở trình độ đỉnh không phải mối lo hiện tại. Thứ cần xử lý là hòa do giới hạn số nước: đó không phải phán quyết chính xác của luật cờ, nên không nên coi $E$ tại đó bằng 0.
- **Không có phép xoay hay lật để tăng dữ liệu**, vì nhập thành và tốt làm bàn cờ không đối xứng. Điều này áp dụng như nhau cho cả hai bên so sánh.
- **Chuyển vị.** Nhiều thứ tự nước có thể dẫn đến cùng thế cờ, trong khi cây không gộp chúng. Chưa biết mức ảnh hưởng, nên chỉ đo khi có số liệu. Nếu cần, có thể tra chung thống kê về sau mà không đổi cấu trúc cây.
- **Temperature 0 không làm ván lặp lại.** Mỗi đời, bước quét với temperature 0.5 rẽ ra các nước mới, nên các ván tản ra, và mỗi nhánh mới luôn khác các ván đã có ngay từ điểm rẽ.
- **Ván dài hơn**, nên chi phí và tác dụng của rẽ nhánh muộn sẽ khác với các ví dụ.
- **Resign** nên tắt ở giai đoạn đầu, vì kết quả xin thua sẽ đi vào $G$ như kết quả thật.
- **Mỗi node chỉ có khoảng vài chục nước hợp lệ**, nên không cần lọc nước như phương án Connect6.

### 12.5 Quy mô

Con số 1 triệu node và 125000 node mới mỗi đời được bàn khi chưa chọn trò chơi. Đã đặt lại ngày 4/11 sau khi đo (8.1): ngân sách 200 triệu lần chạy mạng mỗi đời cho khoảng 400 nghìn node mới (khoảng 2 600 ván rẽ, 6.3), $W=4$, cây khoảng 1.4 đến 1.6 triệu node.

### 12.6 Chạy trên nhiều máy Colab cùng lúc

**Hạ tầng hiện có (engine cờ biến thể, `custom_engine/HUONG_DAN_TERMUX.md` mục 3.1, 4.1 và 9.1).**
- Mỗi cửa sổ Termux trên điện thoại lo một máy Colab T4 của một tài khoản Google. Máy có thể bị thu hồi bất cứ lúc nào, và khi đó `/content` mất sạch.
- Điện thoại là nơi lưu bền và là nơi điều phối. Các cửa sổ dùng chung thư mục `Download/FairyZero/` và tránh giẫm lên nhau bằng khóa thư mục (`mkdir`).
- Mỗi đời có ba giai đoạn. Giai đoạn 2: mọi máy sinh ván song song, và điện thoại cộng dồn số ván. Giai đoạn 3: một máy huấn luyện. Giai đoạn 4: đưa mạng mới lên GitHub.

**Vì sao cách cũ dễ chia việc.** Mỗi ván độc lập và chỉ cần mạng. Máy nào cũng chơi được ván nào, và mất một máy chỉ mất các ván dở của máy đó.

**Điều làm cách mới cũng chia được.** Phần tốn tính toán của cách mới vẫn độc lập như cách cũ:
- Một ván từ một điểm rẽ chỉ cần mạng, đường đi từ gốc tới điểm rẽ (dãy nước từ thế khởi đầu), và nước rẽ. Nó không cần cả cây.
- Một lần search lại chỉ cần đường đi tới node đó.

Phần cần cả cây gồm gộp ván vào cây, tính $\rho$, $G$, $E$, $\omega^2$ và nhãn, cắt lá, quét, lấy mẫu. Phần này không chạy mạng và không cần luật cờ: nó chỉ làm việc với dãy nước đi và các con số. Vì vậy nó chạy **trên điện thoại** (bạn đề xuất, mình đồng ý), vì các lý do sau:
- Không cần GPU, nên không tốn hạn mức T4 cho việc không dùng tới GPU.
- Điện thoại vốn là nơi lưu bền, nên cây không phải tải lên tải xuống Colab mỗi đời, và không mất khi một máy Colab bị thu hồi.
- Phía Colab giữ gần như y hệt cách cũ: máy sinh ván nhận gói việc, máy huấn luyện nhận một tệp dữ liệu.
- Điện thoại có thể lập danh sách việc của đời sau trong lúc máy Colab đang huấn luyện.

Điều kiện: cây phải lưu bằng các mảng số gọn (numpy, hoặc C++ biên dịch bằng `clang` có sẵn trên Termux, mục 2.2 của hướng dẫn Termux), không lưu mỗi node thành một đối tượng Python, vì như vậy 1 triệu node sẽ tốn cỡ vài GB bộ nhớ. Tốc độ và bộ nhớ của điện thoại chưa đo. Termux có gói `python-numpy`, nhưng mình chưa kiểm trên máy của bạn. Nếu điện thoại quá chậm, cùng đoạn mã đó chạy được trên một máy CPU Colab.

**Một đời của cách mới.**

1. **Điện thoại tính nhãn.** Điện thoại gộp các ván và kết quả search lại của đời vừa xong vào cây. Sau đó nó tính $\rho$, $G$, $E$, ước lượng lại $\omega^2$, và tính nhãn. Cuối cùng nó ghi **tệp dữ liệu huấn luyện** và tải lên máy huấn luyện, như cách cũ tải gói ván lên.
2. **Máy Colab huấn luyện (giai đoạn 3).** Máy dựng lại thế cờ bằng cách đi lại đường đi từ thế khởi đầu, huấn luyện, rồi trả mạng mới về như hiện nay. **Cách nhanh hơn (ghi 5/11):** máy sinh ván của `cv` đã mã hoá sẵn mặt phẳng đầu vào của mọi thế cờ nó search vào tệp `mau.npz` nén (khoảng 110 byte mỗi thế cờ, nạp 16 185 thế cờ mất 0.2 giây thay cho 8 giây mã hoá lại). Cách cây trò chơi giữ lại phần mặt phẳng đó cho mỗi node theo chỉ số node, nên tệp dữ liệu huấn luyện chỉ cần mang nhãn mới (value, policy) và chỉ số node; khoảng 1.3 triệu node tốn chừng 140 MB mặt phẳng, giữ trên điện thoại cùng cây và tải lên cùng nhãn. Việc này chỉ đổi tốc độ, không đổi nhãn.
3. **Điện thoại lập danh sách việc, cùng lúc với bước 2.** Điện thoại cắt lá (8.3), nhân mọi $m$ với $\gamma$, rồi lập **danh sách việc** của đời sau. Danh sách gồm các việc search lại (9.2) và các điểm rẽ (quét ở 6.1, xáo trộn ở 6.3), chia thành **gói**, ví dụ 20 việc một gói. Cắt lá phải làm sau khi đã ghi tệp dữ liệu huấn luyện, vì lá bị cắt thì mất mẫu.
4. **Bước song song, trên mọi máy (giai đoạn 2).** Mỗi máy nhận một gói chưa ai nhận. Việc giữ chỗ dùng cùng kiểu khóa thư mục mà điện thoại đang dùng để đặt tên gói ván. Máy làm xong gói thì trả kết quả về điện thoại: các ván (đường đi và số search tại mỗi nước) và kết quả search lại.
5. **Hết gói mà còn ngân sách.** Trường hợp này xảy ra chắc chắn ở đời đầu, vì cây khi đó chỉ có gốc. Máy tự quét trên các ván do chính nó chơi trong đời này rồi rẽ tiếp, giống 6.2, bằng cùng đoạn mã quét. Máy vẫn chơi nhiều ván song song như cách cũ (ô 04 của `cv` dùng 128 ván cùng lúc, cấu hình nhanh nhất đã đo ở 12.8). Ván nào xong thì kết quả quét thêm điểm rẽ vào hàng đợi của máy.

**Gộp kết quả từ nhiều máy.** Một node được xác định bằng đường đi từ gốc, nên gộp chỉ là hợp các ván theo đường đi.
- Hai máy cùng rẽ ra một cặp (node, nước) thì đó là hai ván đi qua cùng các node, và $m$ cộng lên 2. Cây vốn đã xử lý nhiều ván đi qua một node như vậy.
- Một node được search hai lần (cùng mạng hay khác mạng) thì cả hai lần đều được cộng vào trung bình search của node (phần 3, đổi 4/11), không bỏ lần nào, vì mỗi lần search thêm là thêm một mẫu nhiễu độc lập (7.4).

**Máy bị thu hồi giữa chừng.** Ván đã xong được tải về như hiện nay; việc dở trong gói bị bỏ, không làm lại. Vì danh sách đã xáo trộn ngẫu nhiên (6.3), bỏ một phần việc chỉ làm mẫu nhỏ đi, không làm lệch nó. Đây là thêm một lợi ích của việc chọn điểm rẽ ngẫu nhiên. Việc search lại bị bỏ thì node đó giữ nhãn cũ, và ưu tiên của nó tăng ở đời sau (9.2). Phần tính toán mất đi giống cách cũ: chỉ mất các ván dở.

**Ngân sách và so sánh công bằng.** Cả hai bên đo ngân sách mỗi đời bằng **số lần chạy mạng**, không bằng số ván, vì ván của cách mới bắt đầu giữa chừng nên ngắn hơn. Một lần chạy mạng là một thế cờ thực sự đưa qua mạng; lần lấy từ cache không tính. Hai bên dùng cùng engine nên đếm giống nhau. Mỗi máy ghi số lần chạy mạng của mình, và điện thoại cộng dồn như đang cộng số ván. Hai bên cũng dùng cùng số bước huấn luyện mỗi đời: cách cũ 1 lượt qua cửa sổ dữ liệu (2.5), cách mới lấy đúng chừng ấy bước, mẫu lấy theo $m$ (phần 10). Vì đo bằng số lần chạy mạng chứ không bằng thời gian, máy nhanh hay chậm, nhiều hay ít máy đều không ảnh hưởng phép so sánh.

**Máy dừng đúng phần giao (sửa 7/11, sau lần thử đầu trên Colab).** Mỗi máy được giao một số lần chạy mạng và phải ước phần còn lại của các việc đang dở để báo dừng sớm (như cách cũ ước nửa ván trung bình mỗi ván dở). Bản đầu lấy bộ đếm lần chạy mạng của engine chia cho số search đã xong để ra số lần chạy mạng mỗi search. Hai số này không cùng loại: bộ đếm gồm cả phần các việc đang dở, còn số search đếm từ tệp ván, đọc lại 10 giây một lần, chỉ gồm việc đã xong. Việc search lại xong trong vài giây nên tỉ số phồng lên hàng chục lần, và ở đời 1 của lần thử, máy dừng khi mới chạy 100 nghìn trên 1 triệu. Bản sửa:
- Số lần chạy mạng mỗi search lấy theo con số điện thoại đã đo ở đời trước (467 ở lần thử). Điện thoại ghi số này ở dòng đầu phần việc giao cho máy, cùng với chi phí trung bình một ván rẽ trong phần đó.
- Chi phí một ván rẽ đo trên máy từ các ván rẽ đã xong (từ 4 ván trở đi); trước đó dùng ước của điện thoại.
- Mỗi việc dở còn nửa chi phí của nó, như cách cũ.
- Trước khi nạp mỗi việc, máy cộng phần đã chạy, phần còn lại ước được và chi phí của việc sắp nạp; vượt phần giao thì thôi nạp và báo dừng. Không có bước này, một lượt tự quét có thể nạp một lúc hàng chục ván rẽ (thử trên máy tính: giao 300 nghìn, nạp 48 ván rẽ, chạy hết 2 triệu). Ở quy mô thật mỗi máy nhận cỡ 67 triệu và một ván rẽ cỡ 100 nghìn, nên máy dừng ở khoảng 99.8% phần giao; phần thiếu vòng lặp giao tiếp như cách cũ.
Cách cũ không đổi gì, vì nó đang chạy thật và phải giữ đúng như các đời trước.

**Máy không bị thu hồi khi đang chơi nốt (sửa 7/11, lần chạy thật đầu của cách cây).** Mỗi máy được giao một số giây (SECS) bằng hạn mức T4 còn lại trừ 6 phút gom và tải về, trừ thêm phần chừa cho đuôi ván (các ván còn đang chơi khi thôi nạp). Phần chừa này lấy theo lần vượt dài nhất đã đo với cùng số ván song song; với 128 ván chỉ có một lần đo, 408 giây, ở đời 2 của cách truyền thống (máy chạy 26 phút, ván trung bình 7,6 phút). Ván đời 0 của cách cây dài hơn nhiều (máy chơi khoảng 580 ván trong 105 phút, 128 ván cùng lúc, tức gần 23 phút một ván, vì sau điểm rẽ luôn đi nước nhiều lượt thăm nhất). Hai máy đầu chạm SECS, thôi nạp, chơi nốt hơn 130 ván, và Colab thu hồi máy khi hết hạn mức trước lúc gom: mất khoảng 110 triệu lần chạy mạng chưa tải về. Phần mất không tính vào ngân sách của đời (chỉ ván đã tải về mới tính), nên phép so không lệch, chỉ phí hạn mức. Bản sửa:
- Vòng lặp ghi thêm cho máy một hạn cứng: SECS cộng phần chừa đuôi ván, tức lúc phải bắt đầu gom.
- Máy đo độ dài từng ván (giây, từ lúc nạp tới lúc xong) và thôi nạp khi thời gian còn tới hạn cứng ít hơn 1,1 lần độ dài ván dài (phân vị 90 các ván đã xong). Như vậy phần chừa tự theo độ dài ván thật, không theo một lần đo cũ.
- Tới hạn cứng mà engine chưa thoát thì tắt engine, bỏ các việc còn dở, giữ mọi ván đã xong (cắt bản ghi dở ở cuối tệp ván nếu có), rồi gom và tải về như thường. Thà mất vài ván dở còn hơn mất cả máy.
- Lần chạy mạng của việc bị bỏ vẫn tính vào phần của máy (bộ đếm của engine gồm cả chúng), như việc chưa nạp bị bỏ khi máy dừng sớm: tính bất lợi cho cách đang chạy, không bao giờ có lợi.
Cả hai cách cùng dùng bản sửa này: nó chỉ đổi gì khi máy sắp hết hạn mức, lúc mà bản cũ có thể mất cả máy. Vòng lặp mở trước bản sửa không ghi hạn cứng; khi đó máy lấy hạn cứng bằng SECS cộng 400 giây, đúng phần chừa đuôi ván vòng lặp cũ đã trừ, nên không phải mở lại vòng lặp.

**Phần việc vừa sức máy (sửa 7/11, đời 1 cách cây).** Việc máy nhận mà không nạp kịp thì mất, nên phần nhận phải vừa với số giây máy còn chạy. Bản đầu chia theo ngân sách còn lại: máy khoa214102 chỉ còn 20 phút T4 nhận 58 668 trên 87 326 việc của đời 1 (ước 193 triệu lần chạy mạng, trong khi 20 phút chạy kịp cỡ 15 triệu). Mình trả tay 41 306 việc nó không thể tới về danh sách chung (con trỏ việc 58 668 -> 17 362, ghi trong nhật ký vòng lặp). Bản sửa: phần nhận không quá 1,3 lần (tốc độ đo được x số giây máy còn chạy); tốc độ là lần chạy mạng mỗi giây lớn nhất của các máy đã tải về ở đời này hoặc đời trước (đời 0 cách cây đo khoảng 8 000, nửa cách truyền thống). Nhận thiếu thì máy hết việc sớm và tự quét ván của nó, vẫn là việc hợp lệ.
Thêm nữa, mỗi lần nhận không quá phần còn lại của danh sách chia cho số cửa sổ vòng lặp đang chạy. Ở đời 1, ba máy đầu nhận theo sức chạy (36 207, 19 686 và 14 071 việc), danh sách hết khi máy thứ tư tới lúc 20:13, nên máy đó phải chơi ván từ gốc, trong khi việc của ba máy kia thừa và sẽ mất khi đủ ngân sách. Chia đều thì với bốn cửa sổ, bốn lần nhận đầu được khoảng 22, 16, 13 và 9 nghìn việc, danh sách còn lại cho các máy sau. Ngoài ra, máy nhận việc của đời 1 trở đi chờ tới 8 phút cho danh sách xuất hiện (sửa 8/11, đời 3): cửa sổ huấn luyện chuyển đời rồi mới lập danh sách, mất gần 2 phút, nên một cửa sổ khác tới nhận sớm 10 giây đã thấy "hết việc" và tự quét suốt cả đời. Quá 8 phút vẫn chưa có danh sách thì máy tự quét như cũ; chờ lâu hơn thì máy đang giữ có thể bị thu hồi, vì lúc chờ vòng lặp không nối ssh.

**Thứ tự so với phần 11.** Ở phần 11, search lại làm trước khi quét. Ở đây hai việc được làm cùng lúc trong bước song song, nên bước quét dùng số search của đời trước tại các node sắp được search lại. Mình chấp nhận điều này: phải tách thành hai lượt song song thì mỗi đời tốn thêm một lần chuyển dữ liệu giữa điện thoại và Colab, và máy phải ngồi chờ. Đó là hại chắc chắn, còn lợi của việc quét bằng số mới hơn một đời chỉ ở các node được search lại và có lẽ nhỏ.

**Kích thước cây và thời gian thao tác: đã đo trên một cây giả.** Script `co_vua/thu_nghiem/do_cay_gia.py` dựng một cây 1 triệu node có hình dạng giống cây thật: ván đầu đi từ gốc, các ván sau rẽ từ một node ngẫu nhiên và đi tới hết ván, sâu tối đa 449 nửa nước. Số liệu search trong cây là số ngẫu nhiên, nên chỉ dung lượng và thời gian là có ý nghĩa. Cây lưu bằng các mảng numpy:
- Mỗi node lưu con trỏ cha, chỉ số nước dẫn tới nó, độ sâu, $m$, $G$, $E$, `best_q`, đánh giá thô và kết quả ván.
- Mỗi nước đã thăm lưu nước, $n(a)$, $Q(sa)$, prior đã trộn nhiễu và prior thô, mỗi số 2 byte.
- Thế cờ không lưu, vì đi lại đường đi từ thế khởi đầu là dựng được.

Kết quả trên máy tính của bạn (Intel i5-1335U), một luồng:

| | 25 nước đã thăm mỗi node | 35 nước đã thăm mỗi node |
|---|---|---|
| Dung lượng cây | 271 MB (284 byte mỗi node) | 366 MB (384 byte mỗi node) |
| RAM cao nhất | 720 MB | 960 MB |
| Tính $\pi$, $m$, rồi $\rho$, $G$, $E$ từ dưới lên, và ước lượng $\omega^2$ | 2.3 giây | 2.6 giây |
| Quét toàn cây | 1.4 giây | 1.9 giây |
| Ghi tệp dữ liệu huấn luyện | 1.1 giây (tệp 112 MB, chưa nén) | 1.3 giây (tệp 151 MB) |
| Cắt 125000 lá có $m$ nhỏ nhất | 1.0 giây | 1.0 giây |
| Gộp 125000 node mới | 0.3 giây | 0.4 giây |
| **Tổng** | **6.1 giây** | **7.1 giây** |

Đọc bảng:
- **Số nước đã thăm mỗi node** với 800 lượt thăm ở cờ vua chưa đo, nên bảng chạy hai mức 25 và 35. Cờ vua thường có khoảng 30 đến 40 nước hợp lệ.
- **RAM cao nhất** xảy ra lúc gộp node mới. Script nối mảng cũ với phần mới, nên trong chốc lát có hai bản. Cây thật giữ số node cố định (cắt bao nhiêu thì thêm bấy nhiêu, 8.1), nên có thể cấp sẵn mảng đủ chỗ và dùng lại chỗ của node đã cắt; làm vậy chủ yếu để nhanh hơn, vì không phải sao chép cả cây. Giới hạn bộ nhớ của dự án là 4 GB RAM (mục 1), nên cả hai mức trong bảng đều dư sức, và còn chỗ để dùng thêm bộ nhớ (chỉ mục, mảng tính sẵn) nếu điều đó làm nhanh hơn.
- **Trên điện thoại** chưa đo. Nếu điện thoại chậm hơn máy tính 3 đến 5 lần, tổng thời gian cỡ 20 đến 40 giây mỗi đời. Phần nằm trên đường găng chỉ là tính nhãn và ghi tệp dữ liệu, cỡ một nửa tổng; cắt lá và quét làm trong lúc Colab huấn luyện (12.6).
- **Thứ có thể tốn thời gian hơn là tải tệp dữ liệu huấn luyện lên Colab.** Tệp 112 đến 151 MB chưa nén; ví dụ với mạng 20 Mbit/giây, 150 MB mất cỡ 1 phút. Cách cũ cũng tải dữ liệu của cả cửa sổ lên mỗi lần huấn luyện, nên đây không phải chi phí mới, nhưng phải đo, và có thể giảm bằng cách nén hoặc chỉ tải phần thay đổi.
- Con số "ít nhất 7 GB" mà bạn tính khớp với việc lưu mỗi node theo định dạng V6 của lc0: 8356 byte mỗi thế cờ (12.7), 1 triệu node thành 8.4 GB. Phần lớn của nó là $\pi$ trên đủ 1858 ô (7.4 KB) và 104 mặt phẳng đầu vào. Cây không cần cả hai: $\pi$ lưu thưa theo các nước đã thăm, còn mặt phẳng đầu vào thì dựng lại từ đường đi.

**Engine.** Kế thừa lc0: sinh nước, search, đầu vào 112 mặt phẳng, tự chơi. Cần thêm ba việc, dùng chung cho cả hai bên:
- Bắt đầu ván từ một đường đi cho trước, tức dãy nước từ thế khởi đầu tới điểm rẽ cộng thêm nước rẽ, rồi tự chơi tiếp từ đó. Không dùng sách khai cuộc. Hàm `NodeTree::ResetToPosition` của lc0 đã nhận sẵn một thế cờ bắt đầu và một dãy nước (`upstream/lc0/src/search/classic/node.h` dòng 650 và 651). Đi theo dãy nước thì lịch sử 8 thế cờ gần nhất mà đầu vào 112 mặt phẳng cần vẫn đầy đủ; nếu chỉ đưa một FEN thì lịch sử này mất.
- Ghi thêm $Q(sa)$ của mọi nước đã thăm và $P_0$. Dữ liệu huấn luyện của lc0 có $\pi$ và `best_q` nhưng không có $Q$ của từng nước con, mà policy target mới (phần 7) cần số này.
- Một chế độ chỉ search một thế cờ rồi ghi kết quả, dùng cho search lại.

Cách cũ chỉ dùng phần chung (ván từ thế khởi đầu) và bỏ qua các trường thêm, nên hai bên chạy cùng một engine.

### 12.7 Engine mới và script mới: kết quả đọc lc0

Dự án cờ biến thể tạm hoãn, nhưng engine và các script của nó không bị sửa. Dự án này có **engine riêng** và **bộ script Termux/Colab riêng**, đặt trong `co_vua/`. Engine mới là một bản sao lc0 (lấy từ `upstream/lc0`, commit `1227b4c`), thêm một chế độ tự chơi riêng, giữ nguyên các phần khác để dễ đối chiếu với lc0. Mọi dòng dưới đây đọc từ mã trong `upstream/lc0/src`.

**Tự chơi.**
- `SelfPlayGame` nhận một `Opening` gồm thế cờ bắt đầu và một dãy nước. Nó đi các nước đó mà không search, và chỉ ghi dữ liệu từ nước đầu tiên có search (`selfplay/game.cc` dòng 82 đến 129). Một ván rẽ từ cây vì thế là một `Opening` với dãy nước = đường đi tới điểm rẽ cộng nước rẽ, dựng thẳng trong mã, không đọc từ tệp sách khai cuộc. Search tại điểm rẽ đã có sẵn trong cây nên không search lại, đúng với thiết kế.
- Mỗi nước search từ gốc trống (`TrimTreeAtHead`, `game.cc` dòng 158 đến 160), nên nhiễu Dirichlet được trộn vào gốc ở mọi nước.
- Khi tự chơi, lc0 tắt "smart pruning" (`search/classic/stoppers/common.cc` dòng 91 và 92), nên mỗi nước chạy đủ số lượt thăm đã đặt.
- Ván dừng cứng ở nửa nước 450 (`game.cc` dòng 152).
- Temperature của lc0 tính theo **nước đầy đủ**: số nước được lấy bằng số nửa nước chia 2 (`search/classic/search.cc` dòng 693 đến 699). Engine biến thể tính theo nửa nước. Engine mới tự chọn nước như engine biến thể: lấy mẫu theo tỉ lệ lượt thăm trong 30 nửa nước đầu (chỉ ở mốc truyền thống), sau đó đi nước nhiều lượt thăm nhất.

**Dữ liệu ghi ra.**
- Dữ liệu huấn luyện V6 của lc0 tốn 8356 byte mỗi thế cờ (`trainingdata/trainingdata_v6.h`). Nó gồm $\pi$ trên đủ 1858 ô, `best_q`, `root_q`, `played_q`, `orig_q` (đánh giá thô của mạng tại thế cờ) và số lượt thăm. Nó **không có** $Q(sa)$ của từng nước con (`trainingdata/trainingdata.cc` dòng 114 đến 266).
- Engine mới ghi một định dạng riêng, dạng thưa. Với mỗi nước có search, nó ghi nước đã đi, $N$, `best_q` và `best_d`, đánh giá thô của mạng. Với mỗi nước đã thăm, nó ghi nước, $n(a)$, $Q(sa)$ (thắng trừ thua, và hòa), prior đã trộn nhiễu và prior thô. Các số này đọc từ các cạnh của node gốc, đúng như `game.cc` dòng 207 đến 217 đang đọc. Prior thô lấy từ cache của mạng như `game.cc` dòng 257 đến 259.
- Phần search lại dùng cùng đoạn ghi: dựng thế cờ từ đường đi, search một lần, ghi, không đi tiếp.

**Mạng.**
- Lc0 có backend `onnx-cuda` (`neural/backends/onnx/network_onnx.cc` dòng 1011), nạp một tệp mạng của lc0 chứa sẵn mô hình ONNX (dòng 945 và 946).
- Công cụ `onnx2leela` của lc0 (`tools/onnx2leela.cc`) bọc một tệp ONNX thành tệp mạng đó, kèm tên nút đầu vào và tên nút đầu ra policy, WDL. Mặc định của nó khớp với thiết kế: đầu vào 112 mặt phẳng, policy 1858 nước, value dạng thắng/hòa/thua.
- Đường đi của mạng vì thế là: huấn luyện bằng PyTorch, xuất ONNX, bọc bằng `onnx2leela`, chạy bằng lc0. Không có đầu ra số nước còn lại.
- Hai điều chưa kiểm: cách khai báo "không có đầu ra số nước còn lại" (mặc định của công cụ là `MOVES_LEFT_V1`), và đầu ra WDL cần là xác suất hay logit (công cụ có tùy chọn `fix-wdl-softmax`).

**Huấn luyện.** Mã huấn luyện viết mới cho cờ vua, dùng AdamW kèm SWA với tốc độ học cố định $10^{-3}$ như bạn chốt (2.5). Mã của engine biến thể (`custom_engine/python`) chỉ dùng để tham khảo, không sửa.

**Tình trạng engine (2026-11-03).** Engine nằm ở `co_vua/engine`, là bản sao lc0 cộng thêm chế độ `lc0 treeplay` (`co_vua/engine/src/treeplay/treeplay.cc`).
- **Cách dùng.** Chế độ này đọc danh sách việc từ đầu vào chuẩn, mỗi dòng một việc. Dòng `G <id> <temp_plies> <các nước UCI>` là một ván bắt đầu sau dãy nước đó. Dòng `S <id> <các nước UCI>` là một lần search lại. Engine chơi nhiều việc song song trên một backend dùng chung, ghi mỗi việc xong thành một bản ghi vào tệp kết quả, và in ra `XONG <id> <số lần chạy mạng cộng dồn>`.
- **Định dạng bản ghi** ghi ở đầu tệp mã nguồn. Trình đọc bằng Python ở `co_vua/python/ban_ghi.py`.
- **Kiểm nước hợp lệ.** Hàm dựng thế cờ của lc0 chỉ đọc chuỗi nước đi chứ không kiểm nước đó có hợp lệ không, vì khi dùng bình thường dãy nước do giao diện cờ gửi tới. Engine mới kiểm từng nước của việc với danh sách nước hợp lệ của thế cờ, và từ chối việc có nước sai.
- **Số lần chạy mạng** đếm các thế cờ thực sự đưa qua mạng, không tính lần lấy từ bộ nhớ đệm.
- **$N$ có thể vượt số lượt thăm đặt trước**, tối đa cỡ một lô (32 lượt): lc0 chỉ kiểm điều kiện dừng sau mỗi lô, nên một lần search 800 lượt thăm kết thúc ở khoảng 800 đến 832. Lc0 khi tự chơi cũng vậy. Engine ghi lại $N$ thật, và các công thức dùng $N$ thật.
- **Biên dịch cho Colab:** `co_vua/bien_dich_linux.bat` chạy `co_vua/scripts/bien_dich_linux.sh` trong Docker Ubuntu 24.04, giống Colab, với ONNX Runtime 1.20.1 bản GPU. Kết quả là `co_vua/ban_linux/lc0` kèm thư viện ONNX Runtime trong `co_vua/ban_linux/lib`. Binary chỉ đòi glibc 2.38, Colab có 2.39.
- **Đã kiểm** bằng backend `random` của lc0 (mạng ngẫu nhiên, chạy trên CPU) trong Docker:
  - Ván từ thế khởi đầu và ván từ một dãy nước đều chạy được, kể cả dãy có nhập thành và bắt tốt qua đường.
  - Search lại chạy được, kể cả ở thế đã chiếu hết (0 lần search).
  - Việc có nước sai hoặc chuỗi rác bị từ chối.
  - Trong dữ liệu đọc ra, tổng $n(a)$ bằng $N$, và tổng prior của nước đã thăm cộng $P_0$ bằng 1.
- **Đã chạy trên T4 với mạng thật** (mạng đời 0, khởi tạo ngẫu nhiên, fp32) qua backend `multiplexing` bọc `onnx-cuda`, sau khi kiểm mạng khớp với Python (12.1). Kết quả đo tốc độ ghi ở 12.8.


### 12.8 Tốc độ trên T4 (đo 2026-11-03)

**Cách đo.** Script `co_vua/scripts/colab_do_toc_do.sh` chạy `lc0 treeplay` trên một máy Colab T4 (2 nhân CPU) với mạng đời 0 (khởi tạo ngẫu nhiên, fp32). Các ván bắt đầu từ thế khởi đầu, theo cấu hình mốc truyền thống: 800 lượt thăm, temperature 1 trong 30 nửa nước đầu. Mỗi cấu hình chạy 75 đến 105 giây. Con số là số lần chạy mạng mỗi giây do engine tự đếm (không tính lần lấy từ bộ nhớ đệm), đọc ở dòng báo tiến độ cuối.

Backend là `multiplexing` bọc `onnx-cuda`. Nó gom thế cờ của nhiều ván vào một lô rồi gửi lên GPU. "Luồng gom lô" là số luồng làm việc gom và gửi đó.

| Ván song song | Luồng gom lô | Lần chạy mạng mỗi giây | GPU dùng |
|---|---|---|---|
| 32 | 2 | 9 144 | |
| 64 | 2 | 13 569 | 41% |
| 64 | 1 | 16 740 | 64% |
| 128 | 1 | **16 947** | 58% |
| 128 | 2 | khoảng 16 000 | 71% |
| 128 | 4 | 14 214 | 62% |
| 256 | 1 | 16 689 | 70% |
| 256 | 2 | 16 268 | 67% |
| 256 | 4 | 15 900 | 65% |
| 384 | 2 | 16 070 | 70% |

**Đọc bảng.**
- Cấu hình chọn: **128 ván song song, 1 luồng gom lô**, khoảng 17 000 lần chạy mạng mỗi giây. Cả hai bên so sánh dùng chung cấu hình này, và vì ngân sách đo bằng số lần chạy mạng nên cấu hình không ảnh hưởng phép so sánh, chỉ ảnh hưởng thời gian.
- Từ 64 ván trở lên với 1 luồng, tốc độ dừng ở khoảng 16 700 đến 17 000. GPU chỉ dùng 58 đến 70%, còn lc0 chỉ dùng khoảng 1.1 đến 1.2 trong 2 nhân CPU. Nghĩa là nút thắt là một phần chạy tuần tự trên CPU, không phải GPU. Thêm luồng gom lô còn làm chậm đi. Bạn đã khảo sát hiện tượng này nhiều lần trên engine cờ biến thể: có một mức trung gian nhanh nhất, tăng thêm thì lợi giảm. Vì vậy bạn chốt dùng cấu hình nhanh nhất đo được và không tìm nút thắt CPU nữa.
- Mỗi số chỉ đo một lần, nên chênh lệch dưới khoảng 5% giữa các cấu hình chưa chắc là thật.
- Với tốc độ này, 1 triệu lần chạy mạng mất khoảng 1 phút trên một máy T4. Ví dụ một đời 1000 ván, mỗi ván 100 nửa nước, 800 lượt thăm mỗi nửa nước, cần khoảng 80 triệu lần chạy mạng, tức khoảng 80 phút trên một máy T4. Độ dài ván thật với mạng còn yếu chưa đo, và có thể dài hơn nhiều.

### 12.9 Bộ script Termux/Colab: lệnh `cvt` (cách truyền thống) và `cvc` (cách cây trò chơi)

Mỗi cách có một lệnh riêng trên điện thoại, giống lệnh `fz` của engine cờ biến thể: **`cvt`** cho cách truyền thống (mốc so sánh) và **`cvc`** cho cách cây trò chơi (chưa viết). Hai bộ dùng chung phần điều khiển máy Colab và quy tắc log. Bộ script kế thừa những gì đã chạy tốt ở engine biến thể (`custom_engine/scripts/colab_cells`, `HUONG_DAN_TERMUX.md`) nhưng viết riêng, không sửa gì của engine biến thể.

**Cài và dùng trên Termux.**
- Cài hoặc cập nhật: `curl -fsSL https://raw.githubusercontent.com/phuc11731510/chess_variant_engine/main/co_vua/scripts/cai_dat.sh | bash`. Script này tải các tệp của `co_vua/scripts/dieu_phoi` vào `~/co_vua`, tạo lệnh `cvt`, và tải gói chạy trên Colab (`goi.tar.gz`) từ GitHub Release `co_vua` về `Download/CoVua/truyen_thong`. Gói được đăng bằng `co_vua/scripts/dong_goi.py --dang`, chỉ khi mọi thay đổi trong `co_vua` đã commit; trong gói có `goi_thong_tin.txt` ghi commit và sha256 của lc0.
- `cvt @B`: cửa sổ này chạy vòng lặp nhiều đời bằng tài khoản `B`. Tài khoản dùng đúng thư mục đăng nhập `~/.fz_tk/<tên>` mà điện thoại đã có từ engine biến thể; `cvt` hay `cvt @chinh` là tài khoản chính. Muốn chạy song song nhiều tài khoản thì mở nhiều cửa sổ, mỗi cửa sổ một tài khoản. Một khoá ngăn hai cửa sổ dùng cùng một tài khoản.
- `cvt dung`: dừng mềm mọi cửa sổ. Ván đang dở được chơi nốt và thu về, máy được trả, rồi cửa sổ thoát. Lần `cvt @...` tiếp theo tự gỡ lệnh dừng này.
- `cvt xem`: xem đời hiện tại, ngân sách đã dùng, các máy đang sinh ván, các khoá và vài dòng log cuối của mỗi cửa sổ.
- Dữ liệu và log nằm ở `Download/CoVua/truyen_thong` nên mở được bằng MT Manager. Lần chạy đầu tạo `cau_hinh.json` với cấu hình thật (80 triệu lần chạy mạng mỗi đời, 128 ván song song, 800 lượt thăm); muốn chạy thử nhỏ thì sửa tệp này trước.
- Mọi thứ tự chạy tiếp từ trạng thái trên đĩa: tắt Termux, mất mạng hay mất máy rồi chạy lại `cvt @B` là làm tiếp đúng chỗ.

**Một đời G của `cvt`** (`co_vua/scripts/dieu_phoi/truyen_thong.py`):
1. **Sinh ván.** Mỗi cửa sổ giữ một máy T4 chạy `colab/sinh.py` với mạng đời G (128 ván song song, 800 lượt thăm, temperature 1 trong 30 nửa nước đầu). Mỗi phút bộ điều phối hỏi tiến độ qua SSH và cộng số lần chạy mạng của mọi cửa sổ.
   - **Mục tiêu cộng dồn của đời G** là `max(ngan_sach_moi_doi × (G + 1), số lần chạy mạng của các đời trước + ngan_sach_moi_doi / 2)`. Phần vượt của đời trước được trừ vào đời này, nhưng đời nào cũng tự sinh ít nhất nửa ngân sách. Quy tắc tối thiểu này được thêm sau khi chạy thử: đời 0 vượt nhiều đến mức đời 1 không còn ngân sách để sinh ván.
   - **Báo dừng mềm sớm theo ước lượng.** Ván đang dở được chơi nốt sau khi báo dừng, nên bộ điều phối báo dừng khi tổng cộng dồn cộng phần còn lại ước lượng của các ván dở (nửa ván trung bình mỗi ván) đạt mục tiêu.
   - **Nạp vừa đủ.** `sinh.py` chỉ giữ số việc đã nạp bằng số ván song song cộng 4, vì việc đã nạp vẫn được chơi sau khi dừng. Lần chạy thử đầu nạp gấp đôi số ván song song, và vượt ngân sách gấp đôi.
2. **Thu về.** Bản ghi ván (`.bin.gz`) và mọi log của lần sinh được tải về điện thoại. Cứ 20 phút, bản ghi dở cũng được tải về một bản tạm, để nếu mất máy giữa chừng thì chỉ mất tối đa 20 phút.
3. **Huấn luyện.** Một cửa sổ giữ khoá `hl_doi<G>`, tải ván của cửa sổ 4 đời lên một máy, chạy `colab/huan_luyen_doi.sh` (tạo mẫu, huấn luyện như 2.5, xuất, bọc bằng `onnx2leela`), tải mạng đời G+1 về, ghi `tom_tat/doi<G>.json`, rồi chuyển sang đời G+1. Các cửa sổ khác chờ và trả máy nếu chờ lâu.

**Giữ máy và chạy lệnh trên Colab.**
- Colab thu hồi máy sau khoảng 10 đến 15 phút nếu không có kết nối SSH. Bộ điều phối mở một phiên SSH ngắn mỗi 60 giây (cách engine biến thể đã đo).
- SSH đi qua `proxy_ssh.py`, bản sửa của cầu SSH trong Colab CLI không cho tự xin máy mới khi phiên đã mất (lỗi engine biến thể từng gặp).
- Việc dài chạy nền trên Colab, bộ điều phối chỉ hỏi tiến độ, vì `colab exec` mất kết nối với lệnh chạy lâu.

**Log (giữ vĩnh viễn, 15.2).**
- `log/dieu_phoi_<cửa sổ>.log`: mọi việc của bộ điều phối (xin máy, tải lên và tải về kèm thời gian, tiến độ, lỗi), chỉ ghi thêm.
- `log/doi<G>/<cửa sổ>_<lần>/`: log thô của mỗi lần sinh (đầu ra engine, dòng tiến độ mỗi phút, nvidia-smi mỗi 5 phút, cấu hình).
- `log/hl/`: log huấn luyện và tóm tắt từng đời.
- `van/doi<G>/`: bản ghi từng ván, kèm số lần chạy mạng, số ván, thời gian.
- `tom_tat/doi<G>.json`: tóm tắt máy đọc được của mỗi đời, gồm cấu hình, seed, lần sinh, huấn luyện, thời gian, và thông tin gói (commit của mã, sha256 của lc0).
- Mỗi máy khi chuẩn bị in một dòng `MAY` (GPU, số CPU, RAM, phiên bản thư viện) vào log của bộ điều phối.
---

## 13. Rủi ro và những điều chưa biết

| Rủi ro | Hậu quả | Cách phát hiện |
|---|---|---|
| Các ván chồng lấn quá ít ngoài khai cuộc | $G$ gần bằng $z$ ở phần lớn node, nên lợi ích chính chỉ còn ở rẽ nhánh rẻ | Đo $E$ và số nhánh theo độ sâu |
| Value target quá tin $q$ | Mất điểm neo từ kết quả ván, mạng có thể tự xác nhận sai | Theo dõi phân bố $w_q$; sai số của nhãn value so với kết quả các ván đi qua node ở các đời sau (các ván này chưa có khi nhãn được tính) và so với Stockfish (15.2) |
| Value target quá trơn | Nhãn các node liền nhau gần như bằng nhau ở khai cuộc, mạng khó học độ chênh nhỏ | So độ chênh value head với search sâu |
| Dữ liệu kém đa dạng (chỉ là khả năng, chưa có dấu hiệu) | Mạng gặp ít kiểu thế cờ hơn | Đếm thế cờ khác nhau theo độ sâu |
| Ngân sách search lại quá lớn | Ít dữ liệu mới | Đã chốt dùng tới 20% (9.3); log độ dịch thật của nhãn sau mỗi lần search lại, hạ mức nếu nhãn gần như không dịch |
| Nhiễu Dirichlet ở các node gần gốc (đo 4/11: một nước 5.5% trung bình có lần lên 55%) | Node được học nhiều nhất mang nhãn nhiễu | Trung bình các lần search (phần 3), search lại tới 20% (9.3); log tỉ số $m/k$ theo trọng số $m$ |
| $\omega^2$ nhỏ (đo đời 0: 0.0037) làm $\rho$ gần gốc gần như chia theo độ tin cậy, không theo $\pi$ | $G$ gần gốc gộp các nhánh khác cách search chơi | Log độ chênh $\rho-\pi$ (15.2); phương án B ở 4.4 trong mô phỏng |
| Ước lượng $\tau_q^2$, $\tau_d^2$ ra số âm (đo đời 0 khi gộp cả cây) | Nhãn vô nghĩa | Chỉ ước lượng từ node có $E$ nhỏ, có sàn (phần 5, 7.4); log theo nhóm |
| $\pi'$ lật nhãn vì nhiễu | Policy dao động | Theo dõi độ chênh giữa $\pi'$ và $\pi$ qua các đời, đối chiếu với nước Stockfish chọn (15.2), thêm bước này sau cùng |
| Cái sai hiếm vẫn tồn tại lâu | Không đạt mục tiêu về lệch | Đo bằng Stockfish (chỉ để đo, 15.2): tỉ lệ nhãn sai và số đời một nhãn sai tồn tại, ở cả hai bên. Thêm tín hiệu nội bộ: các node có nhãn đổi mạnh khi được search lại hoặc khi có ván mới đi qua |
| Bằng chứng cũ từ mạng non | $G$ gần gốc bị lệch | So $G$ gần gốc với mạng hiện tại |
| Chọn điểm rẽ ngẫu nhiên tiêu ngân sách vào chỗ ít ích | Cách mới tiến bộ chậm hơn mức có thể | So phân bố độ sâu điểm rẽ và mức nhãn thay đổi sau rẽ (phần 15); nếu cần thì thử phương án ở 6.3 |
| Cách mới được tinh chỉnh nhiều hơn cách cũ | Kết luận bị thiên vị | Quy tắc so sánh công bằng ở 15.3 |

**Về độ mới:** từng thành phần đều có tiền lệ gần đó: Reanalyze của MuZero (làm mới nhãn), Go-Exploit và Tsai và cộng sự (bắt đầu ván từ thế đã lưu), Grill và cộng sự (nhãn tính từ $Q$), Monte-Carlo Graph Search (đồ thị trong một lần search). Bản đánh giá từ AI khác không tìm thấy công trình nào dùng một cây ván thật qua nhiều đời làm nguồn nhãn. Mức kiểm tra: mình đã tra phần tóm tắt của Tsai và cộng sự (arXiv 2602.20809), của Grill và cộng sự (ICML 2020, arXiv 2007.12509) và của Go-Exploit (Trudeau và Bowling, arXiv 2302.12359), và chúng khớp với cách tài liệu này nhắc tới. Reanalyze của MuZero và Monte-Carlo Graph Search mình nêu từ hiểu biết sẵn, chưa tra lại. Chưa đọc toàn văn nguồn nào. Câu "không tìm thấy công trình nào dùng một cây ván thật qua nhiều đời" là của bản đánh giá kia, mình chưa tự tìm để xác nhận.

---

## 14. Kế hoạch thử nghiệm

Thêm từng phần một, để khi kết quả xấu còn biết phần nào gây ra.

| Bước | Việc | Điều kiện đạt |
|---|---|---|
| 1 | Dựng cách truyền thống với mạng 1 triệu tham số, đo tốc độ | Mạng tiến bộ rõ, biết độ dao động giữa các seed. Đây là mốc so sánh. Nhãn value dùng `best_q` như mô hình cũ, tham số tự chơi và huấn luyện theo bảng ở 2.5, ngân sách mỗi đời đo bằng số lần chạy mạng (12.6) |
| 2 | Cây trò chơi với nhãn cũ, chỉ đổi cách rẽ nhánh (quét ở 6.1, chọn điểm rẽ ngẫu nhiên ở 6.3, cắt lá có $m$ nhỏ nhất ở 8.3) | Tách được lợi ích của việc chọn chỗ bắt đầu ván |
| 3 | Thêm value target mới ($G$, $E$, phần 4 và 5) | Hơn bước 2, hoặc tìm được nguyên nhân để sửa |
| 4 | Thêm search lại theo ưu tiên | Nhãn bớt cũ và ngân sách hợp lý |
| 5 | Thêm policy target $\pi'$ | Hơn bước trước |
| 6 | Xác nhận cuối với nhiều seed | Khoảng tin cậy của mức chênh Elo không chứa 0, hoặc kết luận rõ là không hơn |

Bản trước có một bước kiểm công thức trên tàn cuộc bằng Syzygy và một bước thêm quy tắc chọn điểm rẽ theo tín hiệu. Bước thứ nhất đã bỏ vì dự án không dùng Syzygy. Bước thứ hai đã bỏ vì điểm rẽ được chọn ngẫu nhiên ngay từ bước 2.

**Chi phí, ghi 5/11 (chờ chủ dự án chốt cách chạy).** Đo thật: một máy T4 chạy khoảng 14 500 lần chạy mạng mỗi giây, nên một đời 200 triệu tốn khoảng 3.8 giờ T4 cho mỗi cách, và tới đời 100 khoảng 380 giờ T4 mỗi cách. Chạy từng bước 2 đến 5 như bảng trên, mỗi bước từ đời 0, thì riêng các bước đó đã tốn nhiều lần chừng ấy. Bước 6 (chạy lại cả hai bên với seed mới) tốn thêm gấp đôi phần được chạy lại. **Chủ dự án chốt (5/11): một lần chạy chính với mọi phần bật**, so với cách truyền thống ở các đời 10, 20, ..., 100 (arena của `cv`); các bước 2 đến 5 ở bảng trên không chạy trước mà chỉ chạy (ngắn, vài chục đời) khi cần tìm nguyên nhân. "Mọi phần bật" nghĩa là ngay từ đời 0 của cách cây trò chơi, bốn cơ chế cùng chạy: rẽ nhánh từ cây (phần 6, 8), nhãn value mới (phần 4, 5), search lại tới 20% (phần 9), nhãn policy mới (phần 7); cơ chế nào chưa có dữ liệu để làm (ví dụ đời 0 chưa có node cũ để search lại) thì tự chưa có tác dụng. Mỗi cơ chế là một công tắc riêng trong mã, để các lần chạy tách riêng về sau chỉ cần tắt bớt. Bước 6 (chạy lại với seed mới) quyết định sau khi thấy kết quả.

**Thước đo chính:** Elo khi đấu trực tiếp giữa mạng của hai cách ở cùng tổng số lần chạy mạng, với cùng số bước huấn luyện. Ví dụ, sau 200 triệu lần chạy mạng mỗi bên, lấy mạng hiện tại của mỗi bên cho đấu với nhau với cùng số lượt thăm mỗi nước. Kết luận không dựa vào Syzygy hay Stockfish; Stockfish chỉ dùng để đo nguyên nhân (15.2). Mức chênh tối thiểu được chốt sau bước 1. Cách cũ phải được làm tốt thật, nếu không thì chiến thắng không có giá trị.

**Thước đo phụ, chỉ dùng để tìm nguyên nhân:** các log ở phần 15.

**Mô phỏng lần 1 (5/11, `co_vua/thu_nghiem/mo_phong_cay.py`).** Thế giới giả có giá trị thật biết trước: mỗi thế cờ 10 nước, giá trị thật của các con dao động quanh giá trị của cha (trung bình theo chính sách thật đúng bằng giá trị cha, độ toả $\omega^2$ thật khoảng 0.0047), ván kết thúc khi thế cờ đã rõ thắng thua hoặc hoà, nên kết quả ở lá gần như chắc chắn; "search" cho $Q$ bằng giá trị thật cộng lệch cố định (một phần node có một nước bị đánh giá cao sai 0.3) và nhiễu mỗi lần, rồi lượt thăm theo softmax trộn nhiễu Dirichlet. Cây chơi 300 ván từ gốc rồi 4 đời rẽ nhánh, khoảng 200 nghìn node. Hai thế giới: search khá đúng (nhiễu $Q$ 0.045, 5% node lệch) và search kém (nhiễu 0.15, 20% node lệch). Kết quả, chỉ là bằng chứng từ thế giới giả:

- **$E$ dự báo thấp hơn sai số thật của $G$.** Phương án A: trung bình 0.117 so với thật 0.198 (search đúng), 0.181 so với 0.370 (search kém); ở nhóm node có $E$ nhỏ nhất, sai số thật gấp 4 đến 5 lần dự báo. Phương án B: trung bình gần hơn nhưng sai theo hướng khác, dự báo quá cao ở nhóm $E$ lớn (gấp 2 đến 3 lần) và quá thấp ở nhóm $E$ nhỏ. Không phương án nào khớp.
- **Một phần do định nghĩa giá trị thật.** Đo trên 300 node, mỗi node 200 ván chơi tiếp độc lập đúng như ván của cây (đi nước nhiều lượt thăm nhất): giá trị khi chơi như vậy cao hơn giá trị trung bình theo chính sách mềm khoảng 0.022 cho bên đi, chênh bình phương khoảng 0.018. So với giá trị khi chơi thật, sai số của $G$ là 0.163 (dự báo A 0.122), gần hơn so với 0.186 khi so với định nghĩa hiện tại. Vậy định nghĩa hiện tại (chơi theo tỉ lệ lượt thăm) không phải thứ ván của cây đo; nhưng kể cả với định nghĩa đúng, $E$ vẫn thấp khoảng một phần tư, và lệch theo nhóm vẫn còn.
- **Ước lượng $\tau_q^2$ lệch xa giá trị thật** (thật 0.008 và 0.049, ước 0.09 và 0.10 đến 0.13), vì phép trừ $E$ dùng một $E$ đã sai. Đúng như lo ngại ở phần 5.
- **Nhãn value mới tốt hơn nhãn kiểu truyền thống nhiều** (sai số bình phương so với giá trị thật theo trọng số $m$: 0.178 xuống 0.044 với A, 0.021 với B ở thế giới search đúng; 0.365 xuống 0.082 và 0.052 ở thế giới search kém), nhưng chủ yếu vì trong cả hai thế giới $q$ chính xác hơn kết quả một ván rất nhiều (chỉ dùng $q$ còn tốt hơn nữa). Kết quả này phụ thuộc thế giới: với mạng đời 0 thật, $q$ gần như đoán bừa (phần 5), nên không được coi là bằng chứng.
- **Nhãn policy $\pi'$:** ở thế giới search đúng, tốt hơn $\pi$ một chút (giá trị thật kỳ vọng -0.055 lên -0.047, trúng nước tốt nhất 55.9% lên 56.4%); ở thế giới search kém thì **kém hơn** (-0.048 xuống -0.056, 29.3% xuống 26.0%), vì ở chỗ $E$ báo nhỏ mà sai số thật lớn, nhãn tin $G$ quá mức.

**Việc tiếp theo:** tìm vì sao $E$ thấp ở nhóm $E$ nhỏ; xét đổi định nghĩa giá trị thật sang "khi chơi như ván của cây" và sửa $U$ theo đó; xét hiệu chỉnh $E$ bằng chính phép kiểm mỗi đời ở 15.2 (so $E$ với kết quả các ván mới). Cho tới khi $E$ khớp trên mô phỏng, nhãn policy $\pi'$ là phần có bằng chứng gây hại trong một thế giới, nên mình đề nghị để công tắc của nó tắt ở lần chạy chính cho tới khi sửa xong. **Chủ dự án đồng ý (5/11): lần chạy chính của cách cây trò chơi tắt nhãn policy mới**, nhãn policy là trung bình $\pi$ các lần search của node. $E$ vẫn được tính mỗi đời vì nhãn value và trọng số $\rho$ dùng nó, nên phép kiểm $E$ trên dữ liệu thật ở 15.2 vẫn chạy đủ. Mô phỏng là nơi sửa $E$ trước khi viết mã cách cây trò chơi.

**Chẩn đoán $E$ (7/11, `co_vua/thu_nghiem/chan_doan_E.py`).** Trước hết sửa hai lỗi của chính thế giới giả làm hỏng phép đo lần 1: (1) giới hạn ván 400 nửa nước biến 17% số ván thành hoà trong khi giá trị thật của thế giới không biết luật đó (thế cờ ở lá có $|V|$ trung bình 0.46 mà kết quả là 0); (2) ngưỡng thắng chắc 0.95 luôn cho +1, nên gần cuối ván $V$ không còn là kết quả trung bình. Sau khi sửa (ngưỡng 0.99 với kết quả rút đúng trung bình $V$, bỏ giới hạn), thế giới cho ván dài trung bình 316 nửa nước, 34% hoà, độ dao động kết quả 0.66, gần số đo thật đời 0 (240, 39%, 0.61). Kết quả trên các node chỉ có một ván đi qua, theo khoảng cách tới cuối ván (sai số thật / dự báo):

| Cách cuối ván | 1-4 | 5-14 | 15-39 | 40-79 | 80-159 | từ 160 |
|---|---|---|---|---|---|---|
| Sai số thật của $G$ | 0.014 | 0.037 | 0.098 | 0.214 | 0.390 | 0.729 |
| A ($\omega^2$ chung) | 0.003 | 0.011 | 0.033 | 0.075 | 0.151 | 0.409 |
| B (độ toả tại node) | 0.006 | 0.024 | 0.079 | 0.194 | 0.428 | 1.273 |
| C (độ chênh đo thẳng, trừ nhiễu) | 0.008 | 0.034 | 0.114 | 0.285 | 0.634 | 1.911 |

Đọc bảng: phần lệch có hệ thống rất nhỏ (khoảng 0.01, bình phương dưới 0.0003), nên gần như toàn bộ sai số là dao động. A dự báo thấp khoảng 2.5 đến 3 lần ở mọi khoảng cách, vì hai lẽ: ván luôn đi nước nhiều lượt thăm nhất, nên nước được chọn lệch khỏi mức chung nhiều hơn một nước bốc ngẫu nhiên (mỗi nửa nước giá trị thật đổi trung bình +0.032 cho bên đi, bình phương 0.0030, trong khi A tính khoảng 0.0013); và cách thứ hai ở 4.4 ước $\omega^2$ là 0.0028 trong khi giá trị thật là 0.0049. B gần nhất ở khoảng giữa (lệch dưới 25% từ 15 tới 159 nửa nước), thấp gần cuối ván, cao gấp đôi ở rất xa vì $E$ cộng dồn không có trần. C (phương án mới: phần sai do chọn thiếu nước đo bằng độ chênh giữa cách gộp các nước đã chơi và cách gộp mọi nước đã thăm, dùng $Q$ của search) đúng gần cuối ván nhưng cao dần khi xa, vì phần "nước được chọn tốt hơn mức chung" đổi dấu mỗi nửa nước nên triệt tiêu trong kết quả ván, nhưng bình phương của nó thì cộng dồn. Hướng tiếp: B có trần tự nhiên (độ dao động kết quả không vượt $(1-D)-V^2$, ước từ thắng/hoà/thua của search), và hiệu chỉnh $E$ bằng các ván mới (15.2) thử trên mô phỏng.

**Thử thêm (7/11).** B có trần (gọi là D, trần $1-D-q^2$ với tỉ lệ hoà đếm theo $|q|$): kém hơn B, vì trần dùng $q$ thay cho giá trị thật nên ở thế cờ có $|q|$ lớn trần quá thấp (nhóm 20% $E$ nhỏ nhất: dự báo 0.030, thật 0.148); bỏ. **Ước lượng $\tau_q^2$ từ các node cách cuối ván không quá 4 nửa nước** (nơi $G$ gần như đúng, sai số thật khoảng 0.014) thay cho "node có $E<0.05$": gần giá trị thật hơn ở cả hai thế giới (thật 0.0081: cách mới 0.0168, cách cũ 0.026 đến 0.057; thật 0.049: cách mới 0.077, cách cũ 0.090 đến 0.128). Với B và $\tau_q^2$ ước theo cách mới, nhãn value mới có sai số so với giá trị thật 0.0083 và 0.0476, bằng hoặc tốt hơn chỉ dùng $q$ (0.0081 và 0.0488) và tốt hơn hẳn nhãn kiểu truyền thống (0.41 và 0.49). **Kiểm thêm khi search gần như đoán bừa (7/11, khi thử mã thật với mạng ngẫu nhiên thấy $E$ của B vượt 1):** thế giới thứ ba với nhiễu $Q$ 0.4 ($\tau_q^2$ thật 0.35, gần mức đo được ở đời 0 thật 0.38). B vẫn tốt nhất: nhãn mới sai 0.181, so với chỉ dùng $q$ 0.344, nhãn kiểu truyền thống 0.530, chỉ dùng kết quả ván 0.813. Bản B trừ nhiễu của $Q$ và chặn $E$ ở 1 (gọi là D) kém hơn B ở cả ba thế giới (0.0099, 0.0765, 0.222 so với 0.0091, 0.0474, 0.181), vì nó làm $E$ thấp hơn sai số thật. Nên giữ B nguyên. **Chủ dự án đã duyệt (7/11):** dùng B cho $E$, không trần; ước $\tau_q^2$ và $\tau_d^2$ từ các node cách cuối ván không quá 4 nửa nước, giữ sàn dương; tiếp tục log phép kiểm $E$ trên dữ liệu thật.

---

## 15. Quan sát, ghi log và tinh chỉnh

### 15.1 Cách làm với những gì chưa suy ra được

Nhiều thứ trong thiết kế không suy ra được trước khi chạy. Với mỗi thứ như vậy, cách làm là: chọn một giá trị mặc định, chạy, ghi log, đọc log, rồi sửa nếu log cho thấy có vấn đề. Mặc định có thể sai lúc đầu; điều quan trọng là log đủ để thấy chỗ sai. Mỗi thay đổi được ghi vào `co_vua/docs/NHAT_KY.md`: đổi gì, từ đời nào, log nào cho thấy cần đổi, và kết quả sau khi đổi.

Bạn giao cho mình làm người quan sát chính của dự án: mình đọc log sau mỗi lần chạy, tự quyết định tinh chỉnh cách mới để nó thành công nhất có thể, và báo lại bạn những gì thấy được. Mình cũng tự quyết định thay bạn nhiều việc, và phản biện khi một quyết định của bạn đi ngược phương châm của dự án.

**Phương châm.** Không đưa vào thiết kế bất kỳ điều gì mà ta biết là hại nhiều hơn lợi. Không bắt buộc phải tối ưu: một lựa chọn chưa chắc tốt nhất vẫn được nhận, miễn là không biết nó hại nhiều hơn lợi. Ngoài ra, ưu tiên ổn định và ít phải tinh chỉnh. Ba ví dụ:

- **Cắt lá ngẫu nhiên bị loại (8.3).** Ta biết nó bỏ sớm ván vừa chơi và giữ lâu nhãn rất cũ, mà không có lợi gì bù lại, nên nó hại nhiều hơn lợi.
- **Chọn điểm rẽ ngẫu nhiên được giữ (6.3).** Có thể nó chưa phải cách tốt nhất, nhưng ta không biết nó gây hại gì, nên được nhận.
- **Chia ngân sách giữa search lại và sinh ván mới (9.3)** không vi phạm phương châm. Cả hai phía đều có lợi, và mức chia được chọn theo quy tắc ở 9.3, không phải đưa vào một điều đã biết là hại nhiều hơn lợi.

**Sửa theo phương châm.** Khi log cho thấy có vấn đề, ưu tiên sửa bằng một quy tắc suy ra được hoặc một số ước lượng từ dữ liệu, thay vì thêm một núm chỉnh tay. Một lần sửa tốt làm số tham số phải chỉnh giảm đi hoặc giữ nguyên, không tăng lên. Ví dụ ở 8.3: cắt lá có $m$ nhỏ nhất không có tham số nào, và tránh được cả hai cái hại của cắt ngẫu nhiên mà không phải đổi cái này lấy cái kia.

| Chưa suy ra được | Mặc định | Log dùng để quyết định |
|---|---|---|
| $\omega^2$ ở đời đầu | Cách thứ hai ở 4.4 với $\rho=\pi$ (4.5) | $\omega^2$ các đời sau có trôi xa khỏi giá trị khởi đầu không |
| Vòng lặp $\omega^2$–$E$ trong một đời | Một lượt, dùng $\omega^2$ của đời trước (4.5) | Dãy $\omega^2$ qua các lượt lặp chỉ để log |
| $\omega^2$ chung hay theo nhóm node | Một số chung cho cả cây (4.4) | $\omega^2$ ước lượng riêng theo độ sâu và theo số quân |
| Hai cách ước lượng $\omega^2$ ở 4.4 có khớp nhau không | Dùng cách thứ nhất, cách thứ hai để đối chiếu | Giá trị của cả hai cách mỗi đời |
| $\tau_q^2$, $\tau_d^2$ | Ước lượng lại mỗi đời (phần 5 và 7) | Giá trị mỗi đời, phân bố $w_q$ |
| Mức search lại | Đã chốt (5/11): tới 20% ngân sách, theo ưu tiên, dừng sớm nếu $k\ge m$ ở mọi node (9.3) | Tuổi nhãn theo độ sâu, bảng $\hat\Delta$, tỉ số $m/k$, độ dịch nhãn |
| Kích thước cây, số node mới mỗi đời | Đã chốt (4/11): $W=4$, cây bằng tổng node mới của 4 đời (8.1) | Tỉ trọng mẫu và tuổi mẫu theo độ sâu |

Ở dòng thứ tư, cách thứ nhất được chọn làm mặc định vì nó dùng trực tiếp độ chênh $G$ giữa các nhánh, còn cách thứ hai dựa trên ví dụ 1 ở 4.2 có giả định riêng. Lựa chọn này có thể đổi nếu log cho thấy cách thứ nhất không ổn định.

### 15.2 Log mỗi đời

**Log là tệp lưu vĩnh viễn, không phải dòng chữ trên terminal.** Terminal Termux chỉ giữ khoảng 2000 dòng rồi xoá, còn `/content` của Colab mất sạch khi máy bị thu hồi. Vì vậy mọi log được ghi thành tệp, tải về điện thoại sau mỗi bước, và giữ mãi, kể cả log cũ nhất. Không có bước nào xoá log. Ngoài mục đích đối chiếu và cải thiện, log còn là minh chứng cho kết quả của dự án nếu nó thành công. Có hai bộ script Termux/Colab, một cho cách truyền thống và một cho cách cây trò chơi, và cả hai đều tuân theo quy tắc này.

Log gồm hai loại:
- **Log thô:** toàn bộ đầu ra của engine (kể cả dòng báo tiến độ), của script huấn luyện và của các script Colab, cùng các tệp kết quả `treeplay` (bản ghi từng ván, xem 12.7).
- **Bản tóm tắt mỗi đời:** dạng máy đọc được (JSON), mỗi đời một bản ghi, để vẽ biểu đồ qua các đời. Mỗi bản ghi kèm cấu hình đầy đủ, seed, commit của mã, và tên máy đã chạy.

- **Cây:** số node, số lá, số node mới, số node bị cắt và độ sâu của chúng; số điểm rẽ quét được, số điểm được chơi, và phân bố độ sâu của điểm rẽ; phân bố $m$, $E$ và $U$ theo độ sâu; tuổi nhãn theo độ sâu, tính theo trọng số $m$; tỉ trọng mẫu huấn luyện theo độ sâu.
- **Các số được ước lượng:** $\omega^2$ theo cả hai cách ở 4.4; $\omega^2$ theo từng nhóm độ sâu và nhóm số quân; dãy $\omega^2$ qua các lượt lặp chỉ để log (4.5); $\tau_q^2$, $\tau_d^2$; phân bố $w_q$.
- **Nhãn:** sai số của nhãn value so với kết quả các ván đi qua node ở các đời sau (các ván này chưa có khi nhãn được tính, nên đây là phép đo không dùng lại dữ liệu đã dùng để tính nhãn); độ chênh giữa $\pi'$ và $\pi$; số node có nhãn đổi mạnh khi được search lại; bảng $\hat\Delta$ theo tuổi.
- **Cơ chế $G$, $E$, $\rho$ (phần 4), log thật nhiều theo yêu cầu của chủ dự án (4/11) để khảo sát và sửa khi cần:** phân bố độ tin cậy $f$ và độ chênh $\rho-\pi$ theo độ sâu và theo số nước đã chơi tại node; tỉ lệ node mà nhánh có $\rho$ lớn nhất khác nhánh có $\pi$ lớn nhất; phép kiểm trực tiếp $E$: ở mỗi đời, so $E(s)$ đã tính ở đời trước với bình phương độ lệch giữa $G(s)$ cũ và kết quả các ván MỚI đi qua $s$ (tỉ số "sai số thấy được / sai số dự báo" theo nhóm độ sâu, đúng mô hình thì gần 1); $G$ và $E$ của gốc qua các đời; mỗi đời ghi một mẫu ngẫu nhiên cố định cỡ (mặc định 10 000 node) với đầy đủ số của node và các nhánh ($\pi$, $Q$, $\rho$, $f$, $G$, $E$, $U$, $m$) để soi bằng tay; ảnh chụp đầy đủ cây (nén) mỗi 10 đời. Tất cả giữ vĩnh viễn như mọi log khác.
- **Ngân sách:** số lần chạy mạng cho tự chơi và cho search lại, việc search lại có chạm trần 20% không (9.3), phần vượt chuyển sang đời sau (6.3), và tổng cộng dồn.
- **Ván và huấn luyện, ghi cho cả hai bên:** độ dài ván, tỉ lệ thắng, hòa, thua; số ván hòa do chạm giới hạn 450 nửa nước; loss của policy và value; số bước huấn luyện; thời gian chạy.
- **Đo bằng Stockfish, chỉ để tìm nguyên nhân:** lấy một mẫu thế cờ cố định số lượng ở mỗi đời của mỗi bên, cho Stockfish đánh giá, rồi so với nhãn value và nước có nhãn policy cao nhất. Từ đó ghi tỉ lệ nhãn sai theo độ sâu, và số đời một nhãn sai tồn tại trước khi được sửa. Kết quả Stockfish không đi vào nhãn hay vào quyết định bên nào hơn. Cách quy đổi đánh giá của Stockfish sang thang thắng, hòa, thua và ngưỡng coi là "sai" sẽ chốt khi làm; hai lựa chọn này chỉ ảnh hưởng tới log, không ảnh hưởng tới hệ thống.
- **Đấu trực tiếp:** Elo giữa hai bên ở các mốc cùng tổng số lần chạy mạng (phần 14).

### 15.3 So sánh công bằng khi tinh chỉnh nhiều

Nếu cách mới được thử nhiều cấu hình rồi lấy lần tốt nhất, còn cách cũ chỉ chạy một cấu hình, thì cách mới có thể hơn chỉ vì may ở lần chọn. Tinh chỉnh nhiều đến đâu cũng được, miễn giữ các quy tắc sau:

1. Tinh chỉnh dùng các lần chạy thử. Lượt so sánh cuối (bước 6 ở phần 14) chạy lại từ đầu với seed mới cho cả hai bên, và cấu hình được chốt trước khi chạy.
2. Tham số dùng chung (learning rate, kích thước batch, số lượt thăm, nhiễu Dirichlet, kích thước mạng) nếu đổi thì đổi cho cả hai bên, và chạy lại mốc truyền thống.
3. Cách cũ dùng mặc định của lc0 (2.5), vốn đã được nhiều người tinh chỉnh. Nếu một thay đổi tham số dùng chung giúp cách mới thì cũng thử nó cho cách cũ.
4. Nhật ký ghi số cấu hình đã thử cho cách mới, để người đọc biết mức tinh chỉnh.
5. Kết luận chỉ dựa vào thước đo chính ở phần 14; log chỉ dùng để tìm nguyên nhân.

---

## Phụ lục A: Bảng ký hiệu

| Ký hiệu | Ý nghĩa bằng lời |
|---|---|
| $s$, $sa$ | Một node (thế cờ cùng lịch sử), và node con sau nước $a$ |
| $a$, $j$ | $a$ là một nước cụ thể; $j$ chỉ là biến đếm chạy qua các nước trong một tổng. Trong các ví dụ, $a_1$, $a_2$, $a_3$ là ba nước cụ thể |
| $C(s)$ | Các nước đã **chơi** thật tại $s$ (khác với các nước search đã **thăm**) |
| $A(s)$ | Các nước search đã **thăm** ít nhất một lượt tại $s$; nước ngoài $A(s)$ có $n(a)=0$, $\pi(a)=0$ |
| $m(sa)$ | Số ván đi qua $sa$, đã nhân $\gamma$ theo mỗi đời |
| $z$ | Kết quả cuối ván |
| $q(s)$, $a^*$ | $q(s)=Q(sa^*)$, giá trị search của thế cờ con ứng với nước $a^*$ có nhiều lượt thăm nhất; tương ứng `best_q` của lc0 (chi tiết ở 2.1, 2.5) |
| $n(a)$ | Số lượt thăm của nước $a$: trong một lần search, số lượt đi qua nước $a$ từ thế cờ gốc (ví dụ 560) |
| $N$ | Tổng số lượt thăm của một lần search (ví dụ 800), bằng tổng mọi $n(a)$ |
| $\pi(a)$ | Tỉ lệ lượt thăm của nước $a$, bằng $\dfrac{n(a)}{N}$ (ví dụ 560/800 = 0.70) |
| $P(a)$ | Prior: xác suất đầu ra thô của mạng cho nước $a$ |
| $Q(sa)$ | Giá trị search của thế cờ con $sa$: trung bình các giá trị đánh giá ở đáy cây search trên $n(a)$ lượt thăm đi qua $sa$, theo góc nhìn bên đang đi tại $s$ (chi tiết ở 2.1) |
| $P_0$ | Tổng prior của các nước mà search không thăm lượt nào |
| $c$ | Hằng số khám phá của PUCT, là cpuct của engine; cố định 1.3 khi tự chơi (2.5) |
| $G(s)$ | Giá trị tổng hợp từ kết quả ván thật, theo góc nhìn Trắng |
| $E(s)$ | Sai số bình phương trung bình của $G(s)$ so với giá trị thật; căn bậc hai của nó là mức sai điển hình |
| $\rho_s(a)$ | Trọng số của nhánh $a$ khi tính $G(s)$ |
| $f(sa)$, $\nu$ | Độ tin cậy của nhánh (0 đến 1), và hằng số cộng chung để tổng $\rho$ bằng 1 |
| $U(s)$ | Mức trọng số $\rho$ lệch khỏi $\pi$, gồm cả các nước search có thăm mà chưa chơi |
| $\omega^2$ | Phương sai giá trị thật giữa các nước đi từ cùng một thế cờ (ví dụ 0.04 ứng với độ lệch điển hình 0.2); một số chung cho cả cây, ước lượng từ cây (4.2, 4.4) |
| $\tau_q^2$ | Sai số bình phương trung bình của $q$ so với giá trị thật (phần 5) |
| $\tau_d^2$ | Sai số bình phương trung bình của chênh lệch $Q$ giữa hai nước do search tính (phần 7) |
| $\sigma_s$ | +1 khi Trắng đi, -1 khi Đen đi |
| $\bar Q$ | $Q$ trung bình của các thế cờ con đã chơi, tính theo $\rho$ |
| $d(sa)$, $\delta(sa)$, $D(sa)$ | Chênh lệch của thế cờ con $sa$ so với mức chung: theo search, theo kết quả ván, và sau khi gộp |
| $Q'(sa)$, $\pi'(a)$ | Giá trị search của $sa$ sau khi sửa, và policy target mới của nước $a$ |
| $\lambda$, $\beta$, $\beta'$ | Mức tin vào prior; mức điểm PUCT chung của các nước được thăm, trước và sau khi sửa |
| $w_a$, $\epsilon$ | $\lambda P(a)$ dựng lại từ dữ liệu, và số dương rất nhỏ chặn giá trị âm |
| $T$ | Temperature của bước quét (khác $\tau_q^2$, $\tau_d^2$) |
| $W$, $\gamma$ | Số đời dữ liệu tồn tại, và hệ số nhân $m$ mỗi đời |
| $\text{tuổi}(s)$ | Số đời kể từ lần search gần nhất tại $s$ |
| $\hat\Delta$ | Mức nhãn policy sai đi theo tuổi, đo từ dữ liệu |

---

## Phụ lục B: Các ý tưởng đã loại hoặc đã thay

| Ý tưởng | Lý do |
|---|---|
| Hai mạng cùng sinh dữ liệu | Tốn compute |
| Đầu ra phụ đo độ chắc chắn của nhãn | Đầu ra này học từ chính nhãn do mạng sinh, nên dễ mù đúng ở chỗ cần nhìn thấy |
| Dùng phép đối xứng để phát hiện lỗi | Bạn thấy không có ý nghĩa với mạng tích chập |
| Tổng hợp nhãn bằng trung bình thuần | Không thêm thông tin, và dễ bị nhánh lớn chi phối khi quét toàn cây |
| Trọng số nghiêng theo kết quả ván, với hệ số nghiêng $\lambda_s$ (một con số đổi theo thời gian, gọi là lịch) | Khó chỉnh, và dễ lạc quan giả. Có thể thử lại bằng cách dùng $\pi'$ trong $\rho$ |
| Số ván hiệu dụng (ký hiệu cũ $n$, không liên quan $n(a)$ là số lượt thăm) | Đếm dư các ván đi chung một đoạn, nên được thay bằng $E$ |
| Trộn $q$ vào từng bước của phép tính $G$ từ cuối ván ngược về gốc (giá trị trộn ký hiệu cũ là $V$) | Dễ mất điểm neo từ kết quả ván, tạm gác lại. Một nghiên cứu năm 2026 gợi ý nên xem lại, nhưng đó chỉ là bằng chứng gián tiếp |
| Search lại bằng cách tự chơi từ gốc | Chỉ làm mới đường đi của ván, các nhánh phụ gần gốc vẫn đóng băng |
| Connect6 bàn 24×24 với 165600 nước | Bạn đã đổi sang cờ vua |
| Cắt lá ngẫu nhiên | Làm thời gian sống của mẫu tản ra: bỏ sớm ván vừa chơi và giữ lâu nhãn rất cũ. Thay bằng cắt lá có $m$ nhỏ nhất (8.3) |
| Chọn điểm rẽ theo tín hiệu (giá trị search tụt mạnh, bất đồng giữa search và kết quả ván) | Tín hiệu nhiễu và cần ngưỡng phải chỉnh. Thay bằng chọn ngẫu nhiên (6.3); giữ làm phương án thử sau nếu log cho thấy cần |
| Kiểm công thức trên tàn cuộc bằng Syzygy | Bạn không dùng Syzygy. Nhãn sai được đo bằng Stockfish (15.2) |
| Đầu ra số nước còn lại của mạng | Bạn chỉ dùng hai đầu ra, policy và value (12.1) |
