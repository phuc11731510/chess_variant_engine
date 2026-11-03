# Walkthrough: cây trò chơi và value target tổng hợp

Tệp này nối tiếp tệp [ngu-canh-sinh-nhan-hoc-tang-cuong.md](ngu-canh-sinh-nhan-hoc-tang-cuong.md). Tệp trước kết thúc ở hướng thiết kế "đồ thị thế cờ sống dùng chung". Tệp này đi từ câu hỏi vì sao công thức PUCT được viết như vậy, qua thiết kế cây trò chơi và cách tính value target, đến rủi ro value target quá trơn. Mọi công thức mới trong tệp này đều là đề xuất chưa được kiểm chứng bằng thực nghiệm, trừ những chỗ được ghi rõ là suy ra được.

## Mục lục

1. Trạng thái hiện tại của thiết kế
2. Bối cảnh cần nhớ từ tệp trước
3. Vì sao công thức PUCT được viết như vậy
4. Thiết kế cây trò chơi
5. Thay kết quả cuối ván bằng giá trị tổng hợp
6. Ba mức chọn trọng số
7. Rẽ nhánh bằng cách quét cây
8. Temperature khi tự chơi
9. Vai trò của giá trị MCTS trong value target
10. Bộ ba công thức khởi đầu và mức độ chắc chắn của chúng
11. Cắt tỉa cây
12. Các node gần gốc bị đóng băng
13. Ngân sách và tính nhất quán
14. Rủi ro value target quá trơn
15. Vòng lặp mỗi đời
16. Những việc còn mở

Phụ lục A: Ký hiệu. Phụ lục B: Những chỗ đã được sửa lại trong quá trình bàn. Phụ lục C: Dòng thời gian.

---

## 1. Trạng thái hiện tại của thiết kế

| Nội dung | Trạng thái |
|---|---|
| Dùng cây trò chơi, không gộp hai thế cờ giống nhau ở hai nhánh khác nhau | Bạn đã chọn |
| Rẽ nhánh bằng cách quét toàn cây với temperature 0.5 trên phân bố lượt thăm đã lưu | Bạn đã chọn |
| Lưu phân bố lượt thăm trong cây, đời mới ghi đè các node mà nó search | Bạn đã chọn |
| Lấy mẫu huấn luyện theo số ván $m$ để giữ nguyên tỉ trọng cũ | Bạn đã chọn |
| Trọng số $\rho_s$ dùng mức 1 hoặc mức 2, không dùng mức 3 | Bạn đã thu hẹp, mức 2 được khuyến nghị |
| Value target dùng cách 1 với tỉ lệ thay đổi theo $m$ | Khuyến nghị, bạn chưa chốt |
| Temperature bằng 0 khi tự chơi | Khuyến nghị, bạn chưa chốt |
| Search lại các node theo công thức ưu tiên | Khuyến nghị, bạn chưa chốt |
| Cắt lá nhưng giữ thống kê ở node cha, và giảm dần $m$ cũ | Đề xuất, bạn chưa chốt |
| Nhãn policy | Chưa bàn |

Bạn ưu tiên một thiết kế tối ưu, ổn định và ít phải tinh chỉnh. Đơn giản không phải là tiêu chí ưu tiên. Bạn đọc hiểu được toán nhưng muốn được hỗ trợ khi cần phát triển công thức mới.

---

## 2. Bối cảnh cần nhớ từ tệp trước

**Mục tiêu.** Giảm số ván tự chơi mà mạng vẫn đạt sức mạnh tương đương, bằng cách làm nhãn chính xác hơn thay vì dùng số lượng ván để đè bẹp nhiễu. Hệ thống vẫn là học tăng cường thuần túy và không được tốn thêm nhiều compute.

**Trường hợp quan sát gốc.** Trong engine tự viết của bạn, tại một thế cờ, MCTS duyệt 8000 node và dồn nhiều lượt thăm hơn vào một nước thí quân vô lý (nước a), trong khi nước b tốt hơn. Cả policy tiên nghiệm lẫn value đều sai, nên không yếu tố nào trong mạng kéo được yếu tố nào lên. Thế cờ chỉ được sửa sau khi mạng tiến bộ nhờ học nhiều thế cờ khác.

**Hai kiểu hỏng của nhãn.**

- **Nhiễu** là việc từng nhãn riêng lẻ lệch khỏi giá trị đúng, nhưng trung bình của nhiều nhãn thì đúng. Thế cờ khởi đầu của mạng non là trường hợp điển hình. Số lượng ván chữa được nhiễu.
- **Lệch** là việc nhãn sai theo cùng một hướng mỗi lần được tạo ra. Cái sai kỳ lạ trong trường hợp gốc thuộc loại này. Số lượng ván không chữa được lệch.

**Hai tính chất của một tín hiệu.** Tín hiệu là thông tin xuất hiện trong quá trình tự chơi mà nhãn được tính ra từ đó.

| Tín hiệu | Khoảng cách | Nguồn gốc | Kiểu hỏng của nhãn |
|---|---|---|---|
| Kết quả cuối ván | Xa, vì có nhiều nước chen giữa | Ở ngoài niềm tin của mạng | Ít lệch, nhiều nhiễu |
| Kết quả search | Gần, vì tính ngay tại thế cờ | Ở trong niềm tin của mạng | Ít nhiễu, có thể lệch |

Trộn hai tín hiệu chỉ trượt giữa nhiễu và lệch. Muốn giảm cả hai thì cần một tín hiệu vừa gần vừa ở ngoài.

**Hai đòn bẩy.** Search đã hỏi mạng về hàng nghìn thế cờ khác, nhưng các thế đó do chính niềm tin đang sai chọn ra và được hỏi cùng lúc với cùng một bộ trọng số. Vì vậy có hai đòn bẩy: thay đổi ai chọn thế cờ để hỏi, và thay đổi thời điểm hỏi. Việc giữ lại kết quả của mọi ván trong một cấu trúc chung nhắm vào cả hai đòn bẩy đó.

---

## 3. Vì sao công thức PUCT được viết như vậy

Công thức PUCT chọn nước tiếp theo cần thăm tại một thế cờ:

$$
a^* = \arg\max_a \left[ Q(a) + c\,P(a)\,\frac{\sqrt{N}}{1+n(a)} \right]
$$

Trong đó $Q(a)$ là giá trị trung bình search đang có cho nước $a$, $P(a)$ là prior của mạng, $n(a)$ là số lượt thăm của nước $a$, $N$ là tổng lượt thăm, và $c$ là một hằng số.

Câu hỏi của bạn không phải là xu hướng tăng giảm của công thức, vì có rất nhiều hàm có cùng xu hướng. Câu hỏi là dạng cụ thể này đến từ đâu. Về lịch sử, những người viết AlphaGo đã chỉnh từ công thức PUCB của Rosin (2011) và chọn dạng này chủ yếu theo thực nghiệm. Cách suy ra dưới đây đến sau, theo trí nhớ là từ Grill và cộng sự (2020), và nguồn này cần được kiểm chứng lại.

### 3.1 Hàm mục tiêu

Kết quả cuối của search là một phân phối $\pi$ trên các nước đi (phân phối này gán cho mỗi nước một tỉ lệ không âm, và tổng các tỉ lệ bằng 1). Search muốn $\pi$ dồn vào các nước có $Q$ cao, nhưng không muốn $\pi$ rời prior quá xa, vì $Q$ chưa hoàn toàn đáng tin:

$$
\max_{\pi} \; \sum_a \pi(a)\,Q(a) \;-\; \lambda \sum_a P(a)\log\frac{P(a)}{\pi(a)}
$$

- **Tổng thứ nhất** là giá trị trung bình của $Q$ khi các nước được lấy theo tỉ lệ $\pi$. Nếu chỉ có tổng này, $\pi$ sẽ dồn hết vào nước có $Q$ cao nhất.
- **Tổng thứ hai** đo độ xa giữa $\pi$ và prior, và có tên là độ phân kỳ KL. Nó luôn lớn hơn hoặc bằng 0 và bằng 0 đúng khi $\pi$ trùng với $P$. Mỗi số hạng có thừa số $P(a)$, nên bỏ rơi một nước có prior lớn bị phạt nặng, còn bỏ rơi một nước có prior nhỏ thì bị phạt rất nhẹ. Khi $\pi(a)$ tiến về 0 trong khi $P(a)$ dương, mức phạt tiến ra vô cùng.
- **Số $\lambda$** là mức tin vào prior. $\lambda$ lớn thì $\pi$ bám sát prior, còn $\lambda$ nhỏ thì $\pi$ chạy theo $Q$.

### 3.2 Điều kiện tối ưu

Lợi ích biên của nước $a$ (lợi ích biên này là mức tăng của hàm mục tiêu trên mỗi đơn vị tỉ lệ dồn thêm cho $a$) gồm hai phần. Tổng thứ nhất đóng góp $Q(a)$. Số hạng của nước $a$ trong tổng thứ hai tách được thành

$$
-\lambda P(a)\log\frac{P(a)}{\pi(a)} = \lambda P(a)\log \pi(a) - \lambda P(a)\log P(a)
$$

Số hạng cuối không phụ thuộc $\pi$, còn $\log \pi$ có tốc độ tăng đúng bằng $1/\pi$. Vì vậy lợi ích biên của nước $a$ là

$$
Q(a) + \lambda\frac{P(a)}{\pi(a)}
$$

Tổng tỉ lệ cố định, nên nếu một nước có lợi ích biên lớn hơn nước khác, chuyển tỉ lệ sang nước đó sẽ làm hàm mục tiêu tăng. Do đó tại điểm tối ưu, mọi nước có cùng một lợi ích biên $\beta$:

$$
Q(a) + \lambda\frac{P(a)}{\pi(a)} = \beta
$$

Khi mọi $Q$ bằng nhau, điều kiện này buộc $\pi$ trùng với prior. Nghĩa là nếu search không phát hiện được gì, nhãn policy chính là prior.

### 3.3 Từ điều kiện tối ưu đến PUCT

Search chỉ thêm được từng lượt thăm, và $\pi(a)=n(a)/N$. Quy tắc tự nhiên là cho lượt tiếp theo vào nước có lợi ích biên lớn nhất:

$$
Q(a) + \lambda P(a)\frac{N}{n(a)}
$$

Khi $N$ tăng, $Q$ đáng tin hơn. Sai số của trung bình trên $N$ mẫu giảm theo $1/\sqrt{N}$, nên người ta chọn $\lambda = c/\sqrt{N}$. Thay vào, ta được $c\,P(a)\sqrt{N}/n(a)$. Số 1 trong mẫu số chỉ để tránh chia cho 0.

| Thành phần | Nguồn gốc |
|---|---|
| $Q$ cộng với phần thưởng | Tổng thứ nhất tuyến tính theo $\pi$ |
| Dạng $P(a)/n(a)$ | Đạo hàm của độ phân kỳ KL |
| $\sqrt{N}$ | Lựa chọn $\lambda = c/\sqrt{N}$, có lý do nhưng không bắt buộc |

Hệ quả là một nước kém hơn nước tốt nhất một khoảng $\Delta$ nhận khoảng $c\,P(a)\sqrt{N}/\Delta$ lượt thăm, nhiều hơn hẳn mức $\ln N/\Delta^2$ của UCB1 khi $N$ lớn. Điều này hợp với cây search, nơi $Q$ thay đổi khi các nhánh sâu hơn được mở ra.

### 3.4 Phần nào là lựa chọn

Công thức chỉ được xác định sau khi đã chọn hàm mục tiêu, và hàm mục tiêu mới là phần tự do. Đảo chiều KL thành $\sum_a \pi(a)\log\frac{\pi(a)}{P(a)}$ sẽ cho nghiệm khác:

$$
\pi(a) \propto P(a)\,e^{Q(a)/\lambda}
$$

Phép suy ra coi $Q$ là cố định, trong khi $Q$ thay đổi sau mỗi lượt thăm, nên PUCT chỉ là xấp xỉ. Hàm mục tiêu cũng chỉ gồm $Q$ và $P$, đều đến từ mạng, nên bản thân công thức đã định nghĩa kết quả search là một tín hiệu ở trong niềm tin của mạng.

---

## 4. Thiết kế cây trò chơi

Bạn cụ thể hóa ý "đồ thị chung" thành một cấu trúc cây, gọi là **cây trò chơi** để phân biệt với cây mô phỏng của MCTS:

- Cây lưu nhiều ván cùng lúc. Hai ván đi chung một đoạn nước đi thì dùng chung các node của đoạn đó.
- Mỗi lần phân nhánh là việc sinh dữ liệu tự chơi thật để mở rộng cây.
- Hai thế cờ giống nhau nhưng đã khác nhánh từ trước vẫn là hai node khác nhau, nên cây không có chu trình. Cách này giữ đúng lịch sử ván và các luật liên quan đến lịch sử. Cái giá là hai node đó không dùng chung thống kê. Nếu cần, có thể tra chung các thống kê đó về sau mà không đổi cấu trúc.
- Mỗi node lưu phân bố lượt thăm của lần search gần nhất tại node đó.

Trực giác của bạn là dưới thế khởi đầu có rất nhiều ván củng cố cho nó, nên value target có thể tổng hợp từ các ván phía sau một node. Với mạng non, 1000 ván gần như thắng thua cân bằng sẽ cho một nhãn gần 0, mạng học được thế khởi đầu cân bằng từ rất sớm, và bớt phải học từ dữ liệu nhiễu.

---

## 5. Thay kết quả cuối ván bằng giá trị tổng hợp

Engine của bạn đang dùng 20% giá trị MCTS và 80% kết quả cuối ván $z$. Cách thay trực tiếp nhất là thay $z$ bằng một giá trị $G(s)$ tính trên cây, sao cho khi dưới node chỉ có một ván thì $G(s)$ bằng đúng $z$. Như vậy nhánh hiếm như tàn cuộc không tệ hơn trước.

### 5.1 Trung bình thuần không thêm thông tin

Kỳ vọng của bạn về thế khởi đầu là đúng: với 1000 ván có tỉ lệ thắng, hòa, thua là 40%, 20%, 40%, sai số của trung bình chỉ cỡ 0.03. Nhưng cách cũ cũng hướng về cùng điểm đó. Với $m$ ván có kết quả $z_i$ và trung bình $\bar z$:

$$
\sum_{i=1}^{m}\big(f(s)-z_i\big)^2 = m\,\big(f(s)-\bar z\big)^2 + \text{hằng số}
$$

Vế trái là cách học cũ, vế phải là học từ nhãn đã tổng hợp, và hằng số không phụ thuộc vào mạng $f$. Hai cách có cùng điểm đến. Riêng phép lấy trung bình chỉ giảm độ gập ghềnh của quá trình học, vì mỗi batch của cách cũ chỉ lấy vài mẫu nhiễu.

### 5.2 Lợi ích thật đến từ đâu

- **Trọng số khác số ván.** Nhánh thử nghiệm không nhất thiết kéo lệch giá trị của node cha.
- **Nhãn cũ được cập nhật.** Ván mới ở dưới một node làm đổi nhãn của các thế cờ đã có. Replay buffer không làm được điều này.
- **Chi phí tính theo nước đi.** Rẽ nhánh ở nửa nước thứ 70 của một ván 80 nửa nước chỉ tốn 10 nửa nước, nên một ván đầy đủ đổi được khoảng 8 nhánh tàn cuộc. Điều này bù một phần cho việc tàn cuộc ít ván hơn khai cuộc.

---

## 6. Ba mức chọn trọng số

Mọi giá trị tính theo góc nhìn quân Trắng, với $z$ bằng +1 khi Trắng thắng, 0 khi hòa, -1 khi Đen thắng. Node kết thúc có $G$ bằng kết quả ván. Node khác có:

$$
G(s)=\sum_{a\in C(s)}\rho_s(a)\,G(sa)
$$

Trong đó $C(s)$ là các nước đã từng được chơi tại $s$, $sa$ là node con sau nước $a$, và $\rho_s(a)$ là trọng số không âm có tổng bằng 1. Cả ba mức đều trả lời một câu hỏi: khi một node có nhiều nhánh con, mỗi nhánh được tính bao nhiêu phần vào giá trị của node?

Để so sánh, xét một node với hai nhánh, và $G$ của hai con coi như đã tính xong:

| Nhánh | Tỉ lệ lượt thăm $\pi_s$ | Số ván $m$ | $G$ của con |
|---|---|---|---|
| a | 0.70 | 4 | -0.25 |
| b | 0.25 | 8 | +0.50 |

### 6.1 Mức 1: theo số ván

$$
\rho_s(a)=\frac{m(sa)}{m(s)}
$$

Kết quả là trung bình của mọi ván đi qua node. Trong ví dụ, $G(s)=\frac{4}{12}(-0.25)+\frac{8}{12}(+0.50)=0.25$. Câu nó trả lời là "kết quả trung bình của các ván đã chơi là bao nhiêu". Điểm yếu là số ván phản ánh cách ta đã phân bổ ván.

### 6.2 Mức 2: theo chính sách và độ tin cậy

$$
\rho_s(a)\propto \pi_s(a)\cdot\frac{m(sa)}{m(sa)+\kappa}
$$

Ký hiệu $\propto$ nghĩa là tính vế phải cho từng nhánh rồi chia cho tổng của chúng. Thừa số $\pi_s(a)$ làm $G$ ước lượng kết quả khi mạng chơi theo cách hiện tại. Thừa số thứ hai là độ tin cậy, gần 0 khi nhánh có ít ván so với $\kappa$ và gần 1 khi có nhiều ván.

Trong ví dụ, với $\kappa$ bằng 1, nhánh a có điểm $0.70\cdot\frac{4}{5}=0.56$ và nhánh b có điểm $0.25\cdot\frac{8}{9}\approx 0.22$. Sau khi chia cho tổng, $\rho_s(a)\approx 0.72$, $\rho_s(b)\approx 0.28$, và $G(s)\approx -0.04$. Câu nó trả lời là "mạng chơi theo cách hiện tại thì kết quả là bao nhiêu". Trọng số không dùng đến kết quả ván, nên các ván may mắn không được ưu ái một cách có hệ thống.

Nếu chỉ có một con, $\rho_s$ bằng 1, nên trên một đoạn chỉ có một ván $G$ trở về đúng $z$.

### 6.3 Mức 3: nghiêng về nhánh có kết quả tốt hơn

$$
\rho_s(a)\propto \pi_s(a)\cdot\frac{m(sa)}{m(sa)+\kappa}\cdot\exp\!\left(\frac{\sigma_s\,G(sa)}{\lambda_s}\right)
$$

Dấu $\sigma_s$ bằng +1 khi Trắng đi và -1 khi Đen đi, để trọng số nghiêng về nhánh tốt cho bên đang đi. $\lambda_s$ rất lớn thì trở về mức 2, còn rất nhỏ thì gần như chọn nhánh tốt nhất đã thử.

Trong ví dụ, với $\kappa$ bằng 1 và $\lambda_s$ bằng 0.5, khi Trắng đi: $\rho_s(a)\approx 0.36$, $\rho_s(b)\approx 0.64$, $G(s)\approx 0.23$. Khi Đen đi: $\rho_s(a)\approx 0.92$, $G(s)\approx -0.19$.

Gọi $w(a)$ là trọng số của mức 2. Mức 3 là nghiệm của bài toán

$$
\max_{\rho}\;\sum_a \rho(a)\,\sigma_s\,G(sa)\;-\;\lambda_s\sum_a \rho(a)\log\frac{\rho(a)}{w(a)}
$$

Bài toán này có cùng dạng với hàm mục tiêu của PUCT, chỉ khác chiều KL, và $G$ đến từ kết quả ván thật thay vì value của mạng.

**Cái giá là lạc quan giả.** Xét node do Trắng đi, nhánh a có $\pi_s$ bằng 0.70, 20 ván và $G$ bằng 0, còn nhánh b có $\pi_s$ bằng 0.25, đúng 1 ván thắng. Với cùng $\kappa$ và $\lambda_s$, mức 2 cho $G(s)\approx 0.16$, còn mức 3 cho $G(s)\approx 0.58$. Một ván có thể chỉ may mắn nhưng chiếm hơn nửa trọng số. Muốn dùng mức 3 thì phải có lịch cho $\lambda_s$, và đó là lý do bạn loại mức này.

### 6.4 Chọn giữa mức 1 và mức 2

Khi quét toàn cây, mỗi node đều có cơ hội rẽ nhánh, nên nhánh đã lớn có nhiều node hơn và nhận thêm nhiều ván hơn. Nhánh đó lại càng lớn hơn, bất kể tốt hay xấu. Vì trọng số ở mức 1 chính là số ván, giá trị của node cha dần bị chi phối bởi nhánh mọc to nhất. Mức 2 không có vòng tự khuếch đại này. Đây là suy luận, chưa được đo.

$\kappa$ chỉ có tác dụng đáng kể khi nhánh có rất ít ván: với $\kappa$ bằng 1, thừa số là 0.5 ở 1 ván, 0.8 ở 4 ván, và xấp xỉ 0.95 ở 20 ván. Vì vậy có thể cố định $\kappa$ bằng 1.

Mức 1 chỉ tốt khi mỗi ván mới được chọn bằng cách đi từ gốc xuống và lấy mẫu theo $\pi_s$, vì số ván khi đó tự tiến về tỉ lệ $\pi_s$. Nhưng node tàn cuộc sẽ ít được rẽ nhánh hơn, nên bạn đã chọn quét toàn cây.

Mức 2 có một giới hạn cần nhớ: nếu mạng vẫn nghiêng về a, value của node khó phản ánh rằng b đã cho kết quả tốt hơn. Tín hiệu đó sẽ cần một cơ chế cho nhãn policy.

---

## 7. Rẽ nhánh bằng cách quét cây

### 7.1 Đề xuất của bạn

Ở đầu mỗi đời, xem mọi node trong cây và lấy mẫu một nước từ phân bố lượt thăm đã lưu với temperature 0.5. Nếu nước đó khác quyết định đã lưu, bắt đầu tự chơi từ nước đó. Xác suất theo temperature $\tau$ là

$$
\Pr(a)=\frac{n(a)^{1/\tau}}{\sum_b n(b)^{1/\tau}}
$$

Với $\tau$ bằng 0.5, số lượt thăm được bình phương, nên phân phối sắc hơn. Khi tỉ lệ thăm là 70% và 25%, nước thứ hai vẫn có khoảng 11%. Khi chênh lệch cực đoan như 7900 và 80 lượt, nước thứ hai chỉ còn khoảng 0.0001.

Bạn làm rõ rằng đó là điều bạn muốn, vì cần rẽ nhánh ở những chỗ phân vân. Trường hợp gốc thực chất ở mức vừa phải nếu tính độ phân vân, chỉ là không yếu tố nào giúp được yếu tố nào. Nhánh thứ hai cần tồn tại để có kết quả thật của cả hai hướng. Cách rẽ này cũng làm nhánh rất tệ ít xuất hiện hơn.

### 7.2 Không cần search lại để quét

Bước quét chỉ đọc phân bố đã lưu nên không cần chạy mạng. Đời mới ghi đè phân bố ở những nhánh nó chơi qua.

### 7.3 Quét cây và MCTS trong MCTS

Bạn từng nghĩ tới ý MCTS trong MCTS. Có thể coi mỗi ván mới là một lượt thăm trên cây trò chơi. Khi đi từ gốc xuống, tại mỗi node chọn nước có điểm lớn nhất:

$$
\sigma_s\,G(sa)+c_T\,\tilde\pi_s(a)\,\frac{\sqrt{m(s)}}{1+m(sa)}
$$

Ở đây $\tilde\pi_s$ là $\pi_s$ đã được làm phẳng với $\tau$ lớn hơn 1. Khi gặp nước chưa thử, chơi nước đó rồi tự chơi đến hết ván, sau đó cập nhật $G$ ngược lên. $G$ đến từ kết quả ván thật, nên nếu a thực sự dẫn đến thua, $G(sa)$ tụt dù mạng tin a đến đâu. Giới hạn là cái sai vẫn sống sót nếu cả hai bên cùng mù sau nước a.

Cách quét của bạn là phiên bản đơn giản của ý này:

| | Quét toàn cây | Đi xuống từ gốc |
|---|---|---|
| Chọn nhánh dựa vào | Chỉ độ phân vân | Độ phân vân và kết quả thật |
| Node nào được rẽ | Mọi node có cơ hội như nhau | Node càng dễ đi tới càng được ưu tiên |

Điểm thứ hai có thể là lợi thế của cách quét, vì node tàn cuộc hiếm gặp vẫn được rẽ nhánh và lại rẻ. Cách quét cần thêm ngân sách rẽ nhánh mỗi đời, vì số nhánh sẽ tăng theo kích thước cây nếu không giới hạn. Khi đã chạy được, có thể thêm dần kết quả thật vào việc chọn nhánh.

---

## 8. Temperature khi tự chơi

Khuyến nghị là đặt temperature bằng 0 khi chơi và chuyển toàn bộ việc tạo đa dạng sang bước quét. Temperature không biến mất mà chỉ đổi chỗ. Engine của bạn vốn đã chơi temperature 0 sau 30 nửa nước, nên quyết định này chỉ ảnh hưởng khai cuộc, nơi cây dày nhất.

Trong cách cũ, mỗi lần temperature chọn nước khác nước tốt nhất là đã tạo một nhánh ẩn, không để lại dấu vết, làm nhiễu nhãn phía trước và không nằm trong ngân sách nào. Trên cây, mỗi lần rẽ là một node có nhiều con, nên $G$ cân lại được bằng $\rho_s$, và đoạn tự chơi sau điểm rẽ ít nhiễu hơn.

Những điểm cần lưu ý:

- **Đời đầu tiên.** Cây còn trống và bước quét chỉ diễn ra đầu đời. Đề xuất là cho bước quét lặp ngay trong đời đó: chơi một ván, quét để lấy nhánh mới, chơi tiếp, đến khi hết ngân sách. Mạng non có phân bố khá phẳng nên cây tự mọc rộng nhanh.
- **Vẫn giữ Dirichlet.** Nó giúp search nhìn tới nước có prior thấp, nên phân bố lượt thăm mới phản ánh được độ phân vân.
- **Độ phủ tàn cuộc.** Temperature 0 làm các ván sau điểm rẽ dễ đi về những kiểu tàn cuộc giống nhau, nên cần theo dõi số thế cờ khác nhau theo độ sâu của cây.
- **Sự lệch giữa trọng số và cách chơi.** Mức 2 dùng phân bố mềm, trong khi ván thật chơi nước có lượt thăm nhiều nhất. Nghĩa thật của $G$ là chơi theo nước tốt nhất ở những chỗ chưa rẽ, và cân theo độ phân vân ở những chỗ đã rẽ.

Để kiểm chứng, chạy cùng ngân sách số nước đi với hai cấu hình, temperature 0 và giữ temperature ở khai cuộc, rồi so sức mạnh sau cùng số đời.

---

## 9. Vai trò của giá trị MCTS trong value target

Bạn đặt câu hỏi: có nhất thiết là $0.2q(s)+0.8G(s)$ không? Câu trả lời là không, vì tỉ lệ cố định hợp với cách cũ, nơi $z$ luôn đến từ một ván. Trên cây, độ tin cậy của $G$ khác nhau theo từng node.

### 9.1 Cách 1: tỉ lệ thay đổi theo từng node

$q(s)$ và $G(s)$ là hai ước lượng của cùng một giá trị. Gọi $\sigma^2$ là phương sai kết quả của một ván, $\tau^2$ là sai số bình phương của $q$. Nếu coi hai sai số là độc lập, cách trộn có sai số nhỏ nhất là lấy trọng số tỉ lệ nghịch với phương sai:

$$
\text{value target}(s)=\frac{\kappa_q\,q(s)+m(s)\,G(s)}{\kappa_q+m(s)},\qquad \kappa_q=\frac{\sigma^2}{\tau^2}
$$

Với $\kappa_q$ bằng 0.25:

| Số ván dưới node | Tỉ lệ từ $q$ | Tỉ lệ từ $G$ |
|---|---|---|
| 1 | 20% | 80% |
| 4 | khoảng 6% | khoảng 94% |
| 20 | khoảng 1% | khoảng 99% |
| 1000 | khoảng 0.025% | gần 100% |

Dòng đầu trùng với engine hiện tại, nên số 0.25 không phải một tham số mới. $G$ vẫn được tính hoàn toàn từ kết quả các ván.

Với mức 2, số đúng theo phép suy ra là số ván hiệu dụng $n$, tính từ dưới lên, với node kết thúc có $n$ bằng 1:

$$
n(s)=\frac{1}{\sum_a \rho_s(a)^2/n(sa)}
$$

Khi trọng số là $m(sa)/m(s)$, công thức trả về đúng $m(s)$. Trọng số càng lệch thì $n(s)$ càng nhỏ. Bộ công thức khởi đầu dùng $m$ cho gọn.

Đọc ngược công thức, tỉ lệ 20/80 ngầm giả định sai số bình phương của $q$ gấp 4 lần phương sai của một ván, điều này nghe quá bi quan về $q$. Suy đoán là tác dụng thật của 80% $z$ có lẽ là giữ một điểm neo ở ngoài niềm tin của mạng, chứ không phải giảm phương sai.

### 9.2 Cách 2: đưa $q$ vào ngay trong phép đệ quy

$$
V(s)=\frac{\kappa_q\,q(s)+n(s)\sum_a\rho_s(a)\,V(sa)}{\kappa_q+n(s)}
$$

Xét đoạn không rẽ $s_1$, $s_2$, $s_3$, rồi kết thúc ván. Với cách 1, nhãn của $s_1$ chỉ gồm $q(s_1)$ và $z$. Với cách 2, nhãn của $s_1$ được trộn từ $q(s_1)$ và nhãn của $s_2$, nhãn của $s_2$ lại được trộn từ $q(s_2)$ và nhãn của $s_3$. Với $\kappa_q$ bằng 0.25:

$$
V(s_t)=0.2\,q(s_t)+0.8\,V(s_{t+1})
$$

Trọng số của $z$ ở khoảng cách $k$ nửa nước là $0.8^k$, tức chỉ còn khoảng 1% sau 20 nửa nước. Nhãn ít nhiễu nhưng dễ mất điểm neo từ kết quả thật. Với $\kappa_q$ bằng 0.02, con số này còn khoảng 67%. Cách 2 cần chỉnh cẩn thận nên không hợp để bắt đầu.

### 9.3 Chi tiết chung

- Mạng non có $q$ kém, nên có thể cho $\kappa_q$ nhỏ ở những đời đầu.
- $q$ ở node không được ghi đè là của đời cũ, nên có thể cho nó mất dần trọng lượng.
- Search tại một node đã nhìn vào các thế cờ bên dưới, nên sai số không thực sự độc lập, và công thức tỉ lệ nghịch với phương sai chỉ là xấp xỉ.

---

## 10. Bộ ba công thức khởi đầu và mức độ chắc chắn của chúng

$$
\rho_s(a)\propto \pi_s(a)\cdot\frac{m(sa)}{m(sa)+1}
$$

$$
G(s)=\sum_{a\in C(s)}\rho_s(a)\,G(sa)
$$

$$
\text{value target}(s)=\frac{0.25\,q(s)+m(s)\,G(s)}{0.25+m(s)}
$$

Tại node chỉ có một ván, bộ công thức cho đúng $0.2q+0.8z$. Đây là kết quả thay số trực tiếp nên chắc chắn, và nó cho phép so trực tiếp với engine hiện tại.

| Thành phần | Tình trạng | Dựa trên điều gì |
|---|---|---|
| Công thức tổng của $G$ | Suy ra được | Nếu nước $a$ được chọn với xác suất $\rho_s(a)$ thì giá trị kỳ vọng của node đúng bằng tổng này. |
| $\rho_s(a)$ tỉ lệ với $\pi_s(a)$ | Suy ra có điều kiện | Đúng nếu mục tiêu là kết quả khi chơi theo $\pi_s$. Chia lại trên các nước đã thử ngầm giả định nước chưa thử có giá trị như các nước đã thử. |
| Thừa số $m/(m+1)$ | Chọn, không suy ra | Nó thể hiện ý "ít ván thì tin ít hơn", giảm dao động nhưng làm trọng số lệch khỏi $\pi_s$. |
| Dạng trộn của value target | Suy ra có điều kiện | Tối ưu nếu $q$ và $G$ không lệch, sai số độc lập và phương sai của $G$ là $\sigma^2/m$. Thực tế $q$ có lệch và các sai số có tương quan. |
| Dùng $m$ trong công thức trộn | Đơn giản hóa | Với mức 2, số đúng là số ván hiệu dụng $n$. |
| Hằng số 0.25 | Kế thừa | Nó giữ công thức trùng với tỉ lệ 20/80, không phải giá trị tối ưu. |

Như bạn nhận xét, thuật toán không phải lúc nào cũng chờ toán học chứng minh. Điều làm được là biết rõ phần nào đã suy ra được và phần nào đang đặt cược.

Trước khi huấn luyện đầy đủ, có thể kiểm tra bộ công thức trên một phiên bản rất nhỏ của biến thể cờ, nhỏ đến mức tính được giá trị chính xác của các thế cờ. Khi đó so trực tiếp sai số của $z$, của $G$ và của value target mới, tách theo $m$. Nếu giữ mục tiêu "chơi theo $\pi_s$", giá trị chính xác cần tính theo đúng cách chơi đó thay vì giá trị khi chơi hoàn hảo.

---

## 11. Cắt tỉa cây

Bạn đưa ra một ví dụ minh họa, với số và cơ chế chỉ là giả định: cây giữ khoảng 1 triệu node lúc đầu mỗi đời, và đầu đời mới cắt 250000 node lá ngẫu nhiên, mỗi lần một node.

### 11.1 Vì sao cắt node làm đổi $m$, $G$ và $\rho_s$

Ba đại lượng này được tính từ những gì nằm bên dưới node, nên khi phần bên dưới mất đi thì chúng phải tính lại. Nếu $s$ có nhánh a với 4 ván và nhánh b với 8 ván, và nhánh b bị xóa hẳn, thì $m(s)$ giảm từ 12 xuống 4, $\rho_s(a)$ tăng lên 1, và $G(s)$ đổi thành $G(sa)$. Các thay đổi còn lan lên mọi node phía trên. Không cần cập nhật trong lúc cắt, chỉ cần cắt xong rồi tính lại một lượt từ dưới lên.

### 11.2 Hai vấn đề của cắt lá ngẫu nhiên

1. **Mất phán quyết cuối ván.** Node lá thường là thế kết thúc ván, nơi duy nhất có kết quả thật. Cắt nó đi thì node cha thành lá mới nhưng không có kết quả, nên $G$ không còn định nghĩa.
2. **Tàn cuộc bị ăn trước.** Node gần gốc không bao giờ là lá nên không bị cắt, trong khi các đầu nhánh bị gặm dần mỗi đời.

### 11.3 Đề xuất: cắt mà giữ thống kê

Mỗi node cha lưu sẵn cho từng nước đã thử bộ ba $\pi_s(a)$, $m(sa)$, $G(sa)$. Khi cắt node con, chỉ bỏ phần tốn bộ nhớ của nó (thế cờ và nhãn huấn luyện), và giữ bộ ba ở node cha. Như vậy $m$, $\rho_s$, $G$ phía trên không đổi, và phán quyết cuối ván vẫn còn dưới dạng thống kê. Thứ mất đi chỉ là mẫu huấn luyện của node bị cắt.

Làm vậy thì bằng chứng cũ không mất, nên kết quả từ các đời rất non vẫn nằm trong $G$ của node gần gốc. Có thể mỗi đời nhân mọi $m$ đã lưu với 0.75, đúng bằng tỉ lệ cắt 25% trong ví dụ, để không thêm tham số mới.

---

## 12. Các node gần gốc bị đóng băng

### 12.1 Vấn đề

$\pi_s$ và $q$ chỉ được ghi đè khi đời mới search tại node đó. Nhưng ván mới bắt đầu từ điểm rẽ nhánh, tức đi thẳng tới node sâu mà không search lại đoạn đường từ gốc. Thế khởi đầu có thể giữ nguyên số liệu của đời 1 mãi mãi. Ở đời 50, các hậu quả xếp từ nặng đến nhẹ như sau:

1. **Khai cuộc bị kẹt.** Nếu mạng đời 50 thích một nước mà mạng đời 1 gần như không thăm, nước đó gần như không bao giờ được rẽ ra.
2. **Nhãn policy dạy ngược.** Mạng đời 50 bị dạy theo phân bố của mạng đời 1. Vì lấy mẫu theo $m$, các node này lại được lấy mẫu nhiều nhất.
3. **Trọng số phản ánh cách chơi cũ.** $G$ ở các node này phản ánh cách chọn nước của mạng cũ, dù kết quả các ván bên dưới là mới.
4. **$q$ cũ gần như vô hại với value target**, vì ở node có nhiều ván $q$ chỉ chiếm tỉ lệ rất nhỏ.

### 12.2 Cách xử lý được khuyến nghị

Mỗi đời dành một phần ngân sách để search lại các node, ưu tiên theo

$$
\text{ưu tiên}(s)=m(s)\times\big(\text{đời hiện tại}-\text{đời search gần nhất tại } s\big)
$$

Tổng $m$ ở mỗi độ sâu không vượt quá tổng số ván, nên mỗi độ sâu đóng góp tỉ trọng mẫu tương đương nhau, trong khi các độ sâu nhỏ có rất ít node. Vì vậy search lại một số ít node cũng làm mới được phần đáng kể tỉ trọng ở khai cuộc. Đây là đòn bẩy "hỏi vào lúc khác", và sự khác nhau giữa phân bố cũ và mới cho thấy mạng đã đổi ý ở đâu. Tỉ lệ ngân sách là tham số duy nhất, mình đoán cỡ 10% để bắt đầu.

### 12.3 Phương án khác đã xét

Dành 10% đến 20% số ván để tự chơi từ gốc. Cách này không cần công thức ưu tiên, nhưng chỉ làm mới các node trên đường đi của ván, nên các nhánh phụ gần gốc vẫn có thể bị đóng băng, và phần lớn ngân sách rơi vào node sâu. Theo tiêu chí tối ưu và ít tinh chỉnh của bạn, search lại theo ưu tiên phù hợp hơn. Sau khi search lại, bước quét đọc được $\pi_s$ mới nên nước mới vẫn có thể mọc nhánh.

---

## 13. Ngân sách và tính nhất quán

### 13.1 Ngân sách

Tổng số lần search do bạn đặt, nên có thể giữ đúng bằng cách cũ. Search lại, rẽ nhánh và tự chơi đều lấy từ ngân sách đó. Việc search lại cũng không hoàn toàn là chi phí cộng thêm: với 1000 ván, cách cũ search thế khởi đầu 1000 lần và search lặp nhiều lần các thế ở vài nước đầu. Nếu các ván thường tách nhau sau 5 đến 10 nửa nước trong ván 80 nửa nước, phần lặp này chiếm cỡ 10% tổng ngân sách. Đây là ước lượng, chưa đo trên engine của bạn.

Phần tốn thêm thật là bộ nhớ để giữ cây và tính toán phụ khi tính lại $G$ và quét cây, mỗi lượt cỡ một phép tính trên mỗi node, không cần chạy mạng. Rủi ro vì thế không nằm ở chi phí, mà ở câu hỏi cùng ngân sách đó có cho mạng học tốt hơn không.

### 13.2 Tính nhất quán

Hệ thống hiện tại đã không nhất quán, chỉ là không lộ ra: replay buffer chứa mẫu từ nhiều đời mạng, và nhãn không bao giờ được cập nhật. Với cây trò chơi, node có $m$ nhỏ không được search lại tương đương một mẫu cũ trong buffer. Node nguy hiểm là node có $m$ lớn, vì được lấy mẫu nhiều và không tự mất đi, nhưng nhóm này rất ít và chính là nhóm được làm mới. Việc $\rho_s$ của cha và con đến từ hai đời khác nhau cũng ít hại, vì $\rho_s$ chỉ là trọng số, còn giá trị vẫn đến từ kết quả ván thật.

### 13.3 Những cách vẫn có thể gây hại

- **Dữ liệu kém đa dạng**, khi các nhánh tập trung vào vài vùng.
- **Value target quá trơn**, được phân tích ở phần 14.
- **Bằng chứng cũ**, nếu $m$ cũ không giảm dần.
- **Cắt tỉa sai**, nếu làm mất phán quyết cuối ván hoặc ăn hết tàn cuộc.

Kết luận là ngân sách ổn gần như chắc chắn, còn "ít gây hại" là khả năng cao nhưng chưa được đo.

---

## 14. Rủi ro value target quá trơn

Rủi ro này là nguy cơ value target gần như không đổi giữa các node liền nhau, khiến mạng ít được học về khác biệt giữa chúng. Nó hẹp hơn cách nói "nhiều node nhận nhãn gần giống nhau".

### 14.1 Những gì không phải vấn đề

Các node trên một đoạn không rẽ có cùng $G$, nhưng cách cũ cũng gán cùng một $z$ cho mọi thế cờ trong một ván. Theo đẳng thức ở phần 5.1, thay nhãn từng ván bằng trung bình không làm mất thông tin về giá trị trung bình.

### 14.2 Điều thực sự thay đổi

Trên đoạn không rẽ, $q$ là thành phần duy nhất khác nhau giữa các node. Khi $m$ tăng, tỉ lệ của $q$ giảm nên nhãn gần như bằng nhau. Xét ba node liên tiếp, có 20 ván đi qua, $G$ bằng 0.30, và giả sử trung bình $z$ cũng bằng 0.30:

| Node | $q$ | Cách cũ: $0.2q+0.8\bar z$ | Công thức mới |
|---|---|---|---|
| $s_1$ | +0.1 | 0.26 | 0.298 |
| $s_2$ | +0.4 | 0.32 | 0.301 |
| $s_3$ | -0.2 | 0.20 | 0.294 |

Cách cũ có nhãn chênh nhau tới 0.12, công thức mới chỉ khoảng 0.007, vì tỉ lệ của $q$ giảm từ 20% xuống khoảng 1.2%.

### 14.3 Hai loại thế cờ liền nhau

**Hai nhánh con của cùng một node** vẫn có nhãn khác nhau, vì mỗi nhánh có $G$ riêng, và $G$ còn ít nhiễu hơn cách cũ. Loại này không bị mất.

**Một node và node ngay sau nó trên đoạn không rẽ** mới là chỗ bị mất. Mạng hầu như không được cho biết nước đi giữa chúng làm giá trị đổi bao nhiêu.

### 14.4 Cơ chế gây hại có thể xảy ra

Chuỗi suy luận sau chưa được đo:

1. MCTS so sánh giá trị các thế cờ sau từng nước, nên thứ nó cần là độ chênh giá trị giữa các thế cờ khác nhau một nước.
2. Ở khai cuộc, độ chênh này thường rất nhỏ, nên mạng cần phân biệt khá tinh.
3. Phần lớn các nước tại một node chưa từng được thử, nên mạng phải đánh giá chúng bằng tổng quát hóa.
4. Khả năng tổng quát hóa đó được nuôi một phần bằng các cặp thế cờ khác nhau một nước mà có nhãn khác nhau. Khi nhãn bị làm phẳng, các cặp như vậy ít hơn.
5. Hệ quả có thể là value head đánh giá kém hơn những nước chưa thử ở khai cuộc.

Trường hợp cụ thể nhất là một nước hơi kém mà search đã nhận ra, nên $q$ giảm nhẹ sau nước đó. Với công thức mới ở node có 20 ván, mạng gần như không thấy tín hiệu này.

### 14.5 Vì sao rủi ro không quá lớn

- Nhãn bằng nhau vẫn đúng theo định nghĩa của $G$. Nếu mạng luôn đi nước đó thì giá trị trước và sau nước đó bằng nhau theo cách chơi hiện tại. Việc phát hiện nước tốt hơn là nhiệm vụ của bước rẽ nhánh.
- Hiện tượng chỉ xảy ra ở node có $m$ lớn. Node một ván vẫn lấy 20% từ $q$. Node có nhiều ván chủ yếu nằm gần gốc, nơi giá trị giữa các nước liền nhau thường ít biến động hơn, và đây là suy đoán.
- Đây là một sự đánh đổi. Phần được là $G$ ít nhiễu hơn hẳn, giúp mạng học tốt mức giá trị chung của cả vùng. Phần mất vốn không mạnh, vì ở cách cũ tín hiệu từ $q$ cũng chỉ chiếm 20% và nằm cạnh $z$ có nhiễu lớn.

### 14.6 Cách đo và cách xử lý

Sau khi huấn luyện cùng số đời bằng hai cách, lấy một tập node khai cuộc. Với mỗi node, dùng search rất sâu để tính độ chênh giá trị giữa các nước, kể cả nước chưa thử, rồi đọc độ chênh tương ứng từ value head không qua search, và so sai số giữa hai cách.

Nếu sai số ở cách mới lớn hơn rõ rệt mà sức mạnh cũng giảm, có thể giữ tỉ lệ của $q$ không nhỏ hơn một mức sàn:

$$
w_q(s)=\max\!\left(\frac{0.25}{0.25+m(s)},\;w_{\min}\right)
$$

Khi đó value target là $w_q(s)\,q(s)+\big(1-w_q(s)\big)\,G(s)$. Cách này thêm một tham số và làm $q$ cũ gần gốc có ảnh hưởng trở lại, nên chỉ đáng thêm khi số liệu cho thấy cần thiết.

---

## 15. Vòng lặp mỗi đời

1. Cắt node lá, giữ thống kê ở node cha, rồi giảm các $m$ đã lưu.
2. Search lại các node có ưu tiên cao nhất, ghi đè $\pi_s$ và $q$.
3. Tính lại $G$ từ dưới lên.
4. Quét toàn cây với temperature 0.5 để chọn điểm rẽ nhánh, đến khi hết ngân sách.
5. Tự chơi với temperature 0 từ các điểm rẽ, thêm node mới vào cây.
6. Tính lại $G$ một lần nữa, rồi huấn luyện với mẫu lấy theo $m$.

Vòng lặp này còn thiếu phần nhãn policy, và phần đó cũng phải dùng $\pi_s$ đã làm mới ở bước 2.

---

## 16. Những việc còn mở

**Cần bạn quyết định:**

- Cắt mà giữ thống kê ở node cha, hay xóa hẳn ván khỏi cây.
- Có giảm dần $m$ cũ không, và với tốc độ nào.
- Xác nhận temperature 0 khi tự chơi.
- Tỉ lệ ngân sách search lại mỗi đời, và ngân sách rẽ nhánh mỗi đời.

**Chủ đề tiếp theo:** nhãn policy. Những ý cần mang theo:

- Lượt thăm là tín hiệu ở trong niềm tin của mạng, và khi không phát hiện được gì thì nhãn policy trùng với prior (phần 3.2).
- Mức 2 không đưa được tín hiệu "b tốt hơn a" vào value khi mạng vẫn nghiêng về a, nên tín hiệu này cần đi qua policy (phần 6.4).
- Node gần gốc được lấy mẫu nhiều nhất nên nhãn policy cũ ở đó đặc biệt có hại (phần 12.1).
- Cây trò chơi có kết quả thật của nhiều nhánh, là thứ cách cũ không có khi tạo nhãn policy.

**Thử nghiệm đề xuất:**

1. Kiểm tra bộ công thức trên phiên bản nhỏ có giá trị chính xác (phần 10).
2. So engine có cây trò chơi với engine hiện tại, cùng ngân sách số nước đi, trên phiên bản nhỏ của biến thể.
3. So temperature 0 với giữ temperature ở khai cuộc (phần 8).
4. Đo số thế cờ khác nhau theo độ sâu để theo dõi độ đa dạng.
5. Đo sai số độ chênh giá trị ở khai cuộc để đánh giá rủi ro quá trơn (phần 14.6).

---

## Phụ lục A: Ký hiệu

| Ký hiệu | Ý nghĩa |
|---|---|
| $s$ | Một node, tức một thế cờ trên cây trò chơi |
| $sa$ | Node con nhận được sau khi đi nước $a$ từ $s$ |
| $C(s)$ | Tập các nước đã từng được chơi tại $s$ |
| $m(s)$ | Số ván đi qua $s$ |
| $n(s)$ | Số ván hiệu dụng tại $s$ |
| $z$ | Kết quả cuối ván theo góc nhìn quân Trắng |
| $q(s)$ | Giá trị MCTS đã lưu tại $s$ |
| $\pi_s(a)$ | Tỉ lệ lượt thăm MCTS đã lưu của nước $a$ tại $s$ |
| $G(s)$ | Giá trị tổng hợp từ kết quả các ván dưới $s$ |
| $\rho_s(a)$ | Trọng số của nhánh $a$ khi tính $G(s)$ |
| $\kappa$ | Hằng số trong thừa số độ tin cậy của mức 2 |
| $\kappa_q$ | Hằng số quyết định tỉ lệ giữa $q$ và $G$ |
| $\sigma_s$ | +1 khi Trắng đi, -1 khi Đen đi |
| $\lambda_s$ | Mức nghiêng theo kết quả ở mức 3 |
| $Q(a)$, $P(a)$, $n(a)$, $N$ | Giá trị, prior, số lượt thăm và tổng lượt thăm trong MCTS |
| $\lambda$ | Mức tin vào prior trong hàm mục tiêu của PUCT |
| $\tau$ | Temperature |

---

## Phụ lục B: Những chỗ đã được sửa lại trong quá trình bàn

- **Lợi ích ở thế khởi đầu.** Tệp trước nói đồ thị chung làm giảm nhiễu nhãn ở thế khởi đầu, điều này nói quá. Theo đẳng thức ở phần 5.1, trung bình thuần có cùng điểm đến với cách cũ.
- **Temperature 0.5.** Có lúc mình kết luận temperature 0.5 đi ngược điều bạn muốn, dựa trên giả định lượt thăm chênh lệch cực đoan. Bạn làm rõ rằng bạn cần rẽ nhánh ở chỗ phân vân và trường hợp gốc ở mức vừa phải, nên kết luận đó không áp dụng.
- **Chi phí quét cây.** Có lúc mình tính việc quét như search lại toàn cây. Bạn chỉ ra rằng phân bố lượt thăm được lưu sẵn nên không cần search.
- **Nghĩa của $G$.** Có lúc mình nói mức 2 ước lượng đúng "kết quả khi mạng chơi theo cách hiện tại". Khi tự chơi với temperature 0, nghĩa chính xác là phần đã ghi ở phần 8.
- **Khuyến nghị làm mới node gần gốc.** Mình từng đề xuất tự chơi từ gốc vì đơn giản hơn. Theo tiêu chí tối ưu của bạn, khuyến nghị đổi thành search lại theo ưu tiên.

---

## Phụ lục C: Dòng thời gian

1. Bạn hỏi vì sao công thức PUCT viết như vậy, không phải theo xu hướng tăng giảm. Phần giải thích suy ra công thức từ một hàm mục tiêu tối ưu.
2. Bạn yêu cầu giữ mạch toán học, vì thiết kế có thể cần phát triển công thức mới. Bạn đưa ra cây trò chơi, ý tổng hợp value target, ý quét cây với temperature 0.5 và ý cắt tỉa.
3. Thống nhất thay $z$ bằng $G$, và làm rõ trung bình thuần không thêm thông tin. Đề xuất ba mức trọng số và MCTS trong MCTS.
4. Bạn làm rõ cách rẽ nhánh theo độ phân vân và cách lưu phân bố lượt thăm. Xuất hiện vấn đề node gần gốc bị đóng băng.
5. Giải thích chi tiết ba mức trọng số.
6. Bàn về temperature khi tự chơi.
7. Bạn hỏi có nhất thiết là tỉ lệ 20/80 không. Xuất hiện cách 1 và cách 2.
8. Bạn thu hẹp về mức 1 và mức 2 vì mức 3 khó chỉnh. Đề xuất mức 2 với $\kappa$ bằng 1 và cách 1, thành bộ ba công thức.
9. Bạn chọn quét toàn cây. Làm rõ phần nào của bộ công thức suy ra được và phần nào là lựa chọn.
10. Bạn chọn lấy mẫu theo $m$. Phân tích cắt tỉa và đóng băng, ghép thành vòng lặp mỗi đời.
11. Bạn lo về ngân sách và tính nhất quán. Làm rõ ngân sách có thể giữ nguyên và hệ thống cũ cũng không nhất quán. Khuyến nghị search lại theo ưu tiên.
12. Phân tích rủi ro value target quá trơn, là điểm cuối của tệp này. Chủ đề tiếp theo là nhãn policy.
