# Walkthrough: công thức suy ra được, quy mô cây và policy target

Tệp này nối tiếp [walkthrough-cay-tro-choi.md](walkthrough-cay-tro-choi.md), vốn kết thúc ở rủi ro value target quá trơn. Tệp đầu tiên của chuỗi là [ngu-canh-sinh-nhan-hoc-tang-cuong.md](ngu-canh-sinh-nhan-hoc-tang-cuong.md).

Tệp này đi từ việc bạn lo về hai công thức chưa được suy ra, qua tốc độ giảm $m$, ngân sách, quy mô cây và cách cắt lá, đến công thức policy target và kết luận rằng thiết kế đã đủ để thử nghiệm. Mọi công thức trong tệp đều chưa được kiểm chứng bằng thực nghiệm. Những chỗ ghi "suy ra" nghĩa là suy ra dưới các giả định được nêu kèm, không phải chứng minh rằng thiết kế sẽ hiệu quả.

## Mục lục

1. Trạng thái hiện tại
2. Bối cảnh ngắn gọn
3. Suy ra công thức trọng số $\rho_s$
4. Suy ra công thức ưu tiên search lại
5. Tốc độ giảm $m$
6. Ngân sách search lại
7. Quy mô cây bạn đề xuất
8. Cắt lá ngẫu nhiên hay cắt lá có $m$ nhỏ nhất
9. Ý tưởng của policy target mới
10. Thiết lập công thức policy target
11. Công thức policy target đầy đủ
12. Những điểm mới phát sinh khi có policy target
13. Toàn bộ công thức sau khi cập nhật
14. Dữ liệu mỗi node cần lưu
15. Vòng lặp mỗi đời
16. Thiết kế đã đủ chưa, và thứ tự thử nghiệm

Phụ lục A: Ký hiệu. Phụ lục B: Những chỗ đã sửa lại. Phụ lục C: Dòng thời gian.

---

## 1. Trạng thái hiện tại

| Nội dung | Trạng thái |
|---|---|
| Mục tiêu: cùng lượng tính toán, mạng tiến bộ nhanh hơn cách cũ | Bạn đã làm rõ, thay cho cách nói "ít ván hơn" |
| Cắt lá nhưng giữ thống kê ở node cha | Bạn đã chốt |
| Temperature 0 khi tự chơi trong thử nghiệm ban đầu | Bạn đã chốt |
| Có giảm dần $m$ cũ | Bạn đã đồng ý, tốc độ theo đề xuất ở phần 5 |
| Giảm tỉ lệ search lại so với mức 125000 mỗi đời | Bạn đã đồng ý là nên giảm, con số cụ thể chưa chốt |
| Trọng số $\rho_s$ dạng mới, có $\nu$ | Bạn thấy ổn hơn vì có suy ra |
| Cách cắt lá | Chưa chốt, mặc định đề xuất là lá có $m$ nhỏ nhất |
| Dồn ngân sách rẽ nhánh vào chỗ bất đồng | Chưa quyết định, đề xuất làm sau khi có số liệu |
| Dùng $\pi'$ thay $\pi$ trong $\rho_s$ | Chưa quyết định, đề xuất giữ $\pi$ trước |

---

## 2. Bối cảnh ngắn gọn

Engine của bạn dùng kiểu lc0, với value target gồm 20% giá trị MCTS và 80% kết quả cuối ván $z$. Mục tiêu là làm nhãn chính xác hơn để cùng lượng tính toán thì mạng tiến bộ nhanh hơn, vẫn theo học tăng cường thuần túy.

**Cây trò chơi** lưu nhiều ván cùng lúc. Hai ván đi chung một đoạn nước thì dùng chung các node của đoạn đó. Hai thế cờ giống nhau ở hai nhánh khác nhau vẫn là hai node khác nhau. Đầu mỗi đời, bước quét đọc phân bố lượt thăm đã lưu ở mọi node, lấy mẫu với temperature 0.5, và nếu ra một nước khác với các nước đã lưu thì tự chơi từ nước đó với temperature 0.

**Giá trị tổng hợp** $G(s)$ được tính từ dưới lên, trong đó node kết thúc có $G$ bằng kết quả ván theo góc nhìn quân Trắng, còn node khác là trung bình có trọng số của các con:

$$
G(s)=\sum_{a\in C(s)}\rho_s(a)\,G(sa)
$$

Trong đó $C(s)$ là tập các nước đã thử tại $s$, $sa$ là node con sau nước $a$, và $\rho_s(a)$ là trọng số có tổng bằng 1. Value target trộn $G$ với giá trị MCTS $q$, với tỉ lệ của $q$ giảm khi có nhiều ván. Mẫu huấn luyện được lấy theo số ván $m(s)$ đi qua node, để giữ tỉ trọng như cách cũ.

Trước đó, trọng số dùng dạng $\rho_s(a)\propto\pi_s(a)\cdot m(sa)/(m(sa)+1)$, và ưu tiên search lại dùng dạng $m\times$tuổi. Bạn lo về hai công thức này vì chúng không được suy ra.

---

## 3. Suy ra công thức trọng số $\rho_s$

### 3.1 Bài toán

Xét một node, và bỏ chỉ số $s$ cho gọn. Gọi $\pi_a$ là tỉ lệ lượt thăm của nhánh $a$, đã chia lại trên các nước đã thử để có tổng bằng 1, và gọi $V_a$ là giá trị thật của nhánh đó. Ta muốn ước lượng $\sum_a\pi_a V_a$, tức kết quả khi chơi theo $\pi$, bằng $\sum_a\rho_a G_a$.

Hai giả định là:

- Sai số của $G_a$ độc lập giữa các nhánh, với phương sai $\sigma^2/n_a$, trong đó $\sigma^2$ là phương sai kết quả của một ván và $n_a$ là số ván hiệu dụng.
- Các $V_a$ dao động độc lập quanh một mức chung với phương sai $\omega^2$.

### 3.2 Hàm cần tối thiểu

Sai số của ước lượng gồm hai phần. Phần lệch xuất hiện khi $\rho$ khác $\pi$. Vì tổng $(\rho_a-\pi_a)$ bằng 0, mức chung của các $V_a$ bị triệt tiêu, nên kỳ vọng của phần lệch bình phương là $\omega^2\sum_a(\rho_a-\pi_a)^2$. Phần nhiễu là $\sigma^2\sum_a\rho_a^2/n_a$. Do đó:

$$
J=\omega^2\sum_a(\rho_a-\pi_a)^2+\sigma^2\sum_a\frac{\rho_a^2}{n_a}
$$

### 3.3 Nghiệm

Tối thiểu hóa $J$ với ràng buộc tổng $\rho_a$ bằng 1. Lấy đạo hàm theo $\rho_a$ và cho bằng cùng một hằng số ở mọi nhánh, ta có $\omega^2(\rho_a-\pi_a)+\sigma^2\rho_a/n_a$ bằng hằng số. Sắp xếp lại:

$$
\rho_a=(\pi_a+\nu)\,f_a,\qquad f_a=\frac{n_a}{n_a+\kappa},\qquad \kappa=\frac{\sigma^2}{\omega^2}
$$

Điều kiện tổng bằng 1 xác định $\nu$:

$$
\nu=\frac{1-\sum_b\pi_b f_b}{\sum_b f_b}
$$

Vì mọi $f_b$ không vượt quá 1 và tổng $\pi_b$ bằng 1, tử số không âm. Do đó $\nu$ không âm và $\rho_a$ không bao giờ âm.

### 3.4 Công thức nói gì

Thừa số độ tin cậy $n/(n+\kappa)$ không phải tự đặt, mà là hệ quả của bài toán. Hằng số $\kappa$ cũng có nghĩa rõ: tỉ lệ giữa nhiễu của một ván và độ khác biệt thật giữa các nhánh. Công thức cũ gần đúng nhưng thiếu $\nu$. $\nu$ là cách chia lại phần trọng số đã lấy khỏi các nhánh ít tin cậy.

Công thức nối liền hai cách đã phân vân trước đó:

- **Khi $\kappa$ tiến về 0**, tức các nhánh rất khác nhau, $f_a$ tiến về 1 và $\nu$ tiến về 0, nên $\rho_a$ tiến về $\pi_a$.
- **Khi $\kappa$ rất lớn**, tức các nhánh gần như bằng nhau, $f_a\approx n_a/\kappa$ và $\nu$ lấn át $\pi_a$, nên $\rho_a$ tiến về tỉ lệ số ván. Đây là mức 1, tức trung bình thuần của các ván.

Khi node chỉ có một con, $\pi$ bằng 1 và $\nu=(1-f)/f$, nên $\rho=(1+\nu)f=1$, và $G$ trên một đoạn không rẽ nhánh vẫn trở về đúng $z$.

### 3.5 Ví dụ so sánh

Xét node do Trắng đi, nhánh a có tỉ lệ thăm 0.70 và 4 ván, nhánh b có 0.25 và 8 ván, với $\kappa$ bằng 1. Sau khi chia lại, $\pi_a\approx 0.737$ và $\pi_b\approx 0.263$:

1. $f_a=0.8$ và $f_b\approx 0.889$.
2. $\sum_b\pi_b f_b\approx 0.823$ và $\sum_b f_b\approx 1.689$, nên $\nu\approx 0.105$.
3. $\rho_a\approx(0.737+0.105)\cdot 0.8\approx 0.67$ và $\rho_b\approx(0.263+0.105)\cdot 0.889\approx 0.33$.

Công thức cũ cho 0.72 và 0.28. Khác biệt lớn hơn ở những trường hợp lệch mạnh. Với $\pi$ bằng 0.9 và 0.1, số ván lần lượt 1 và 1000, công thức mới cho khoảng 0.60 và 0.40, còn công thức cũ cho khoảng 0.82 và 0.18. Công thức mới dịch nhiều trọng số hơn sang nhánh có nhiều bằng chứng.

### 3.6 Ước lượng $\kappa$ từ chính cây

$\kappa$ không cần chỉnh tay. Mỗi đời có thể ước lượng một giá trị chung:

- $\hat\sigma^2$ là phương sai kết quả các ván.
- $\hat\omega^2$ là phương sai giữa $G$ của các nhánh anh em, trừ đi phần do nhiễu $\sigma^2/n_a$, và không cho âm.

### 3.7 Số ván hiệu dụng

Với trọng số bất kỳ, độ tin cậy của $G(s)$ được đo bằng số ván hiệu dụng, tính từ dưới lên:

$$
n(s)=\frac{1}{\sum_a\rho_s(a)^2/n(sa)}
$$

Khi trọng số là $m(sa)/m(s)$, công thức trả về đúng $m(s)$. Khi node chỉ có một con, $n(s)$ bằng $n$ của con. Vì $m$ được giảm theo đời, node kết thúc nên có $n$ bằng $m$ hiện tại của nó, tức bằng 1 khi mới sinh rồi giảm dần.

### 3.8 Điểm yếu

Các giả định không hoàn toàn đúng, vì mạng thường thích nước tốt hơn nên $\pi_a$ và $V_a$ có liên hệ với nhau, và $\omega^2$ chưa chắc giống nhau ở mọi node. Nhưng bây giờ ta biết chính xác mình đang giả định gì, và có thể kiểm tra các giả định đó.

---

## 4. Suy ra công thức ưu tiên search lại

Gọi $\Delta_s$ là sai số bình phương của nhãn tại $s$ do đã cũ. Vì mẫu được lấy theo $m$, tổng thiệt hại khi huấn luyện là

$$
\sum_s m(s)\,\Delta_s
$$

Search lại một node xóa đúng phần $m(s)\Delta_s$ với cùng chi phí một lần search. Khi mọi lựa chọn có cùng chi phí và không ảnh hưởng lẫn nhau, cách tối ưu với ngân sách cố định là chọn các node có phần xóa được lớn nhất:

$$
\text{ưu tiên}(s)=m(s)\,\hat\Delta\big(\text{tuổi}(s)\big)
$$

Công thức $m\times$tuổi là trường hợp riêng, đúng khi mạng trôi như bước ngẫu nhiên, nên sai số tăng tuyến tính theo tuổi. Bạn không cần giả định điều đó, vì có thể đo $\hat\Delta$:

1. Sau mỗi đời, lấy các node vừa được search lại.
2. Với mỗi node, tính $\sum_a(\pi^{\text{mới}}_a-\pi^{\text{cũ}}_a)^2$.
3. Lấy trung bình theo từng tuổi để có bảng $\hat\Delta$.

Đời đầu chưa có số liệu thì dùng tạm $\hat\Delta$ bằng tuổi. Mức đo này dùng hiệu bình phương thay cho KL, vì KL có thể ra vô cùng khi một nước có lượt thăm cũ bằng 0.

---

## 5. Tốc độ giảm $m$

Mỗi đời nhân mọi $m$ đã lưu với $\gamma$. Một ván sau đó có tổng trọng lượng bằng chứng qua các đời là $1+\gamma+\gamma^2+\dots=1/(1-\gamma)$. Gọi $W$ là số đời mà dữ liệu được giữ lại. Đặt tổng đó bằng $W$:

$$
\gamma=1-\frac{1}{W}
$$

Ý nghĩa là cây nhớ lâu tương đương một replay buffer giữ $W$ đời. Kích thước cây và tỉ lệ cắt cũng theo cùng con số: kích thước cây khoảng $W$ lần số node mới mỗi đời, và mỗi đời cắt $1/W$ số node. Con số 0.75 từng nêu là ứng với $W$ bằng 4 trong một ví dụ, không phải giá trị chung.

Việc giảm $m$ có hai hệ quả:

- Node cũ tự được lấy mẫu ít đi, giống dữ liệu cũ dần rời buffer.
- Khi $m$ xuống dưới 1, value target nghiêng về $q$ nhiều hơn 20%, nên $q$ cũ cần được để ý.

---

## 6. Ngân sách search lại

Thay vì một con số cố định, đề xuất là một điều kiện dừng: search lại theo thứ tự ưu tiên cho đến khi **tuổi trung bình của nhãn, tính theo trọng số $m$, không vượt quá $W/2$**. Đây là tuổi trung bình của mẫu trong buffer cũ, nên nhãn trên cây sẽ không cũ hơn cách cũ.

Vẫn nên có một mức trần, đề xuất là 20% ngân sách, để việc làm mới không lấn hết dữ liệu mới. Mức trần là phần duy nhất chưa suy ra được. Tỉ lệ tối ưu thật phụ thuộc vào giá trị của dữ liệu mới so với nhãn mới, và hai giá trị này không cùng đơn vị, nên chỉ có thử nghiệm mới trả lời được.

---

## 7. Quy mô cây bạn đề xuất

### 7.1 Đề xuất

Cây giữ khoảng 1000000 node sau khi sinh dữ liệu. Sau huấn luyện, cắt 125000 lá ngẫu nhiên. Sau đó search lại 125000 trong 875000 node còn lại theo thứ tự ưu tiên. Rồi sinh thêm khoảng 125000 node mới. Mục tiêu là cùng lượng tính toán thì tiến bộ nhanh hơn cách cũ.

### 7.2 Các con số suy ra

Mỗi đời có 250000 lần search, chia đôi cho search lại và sinh node mới. Cây thay 125000 trên 1000000 node, nên $W$ bằng 8 và $\gamma$ bằng 0.875. Cấu trúc cân bằng, vì số node cắt bằng số node mới. Thứ tự cũng đúng, vì việc search lại dùng mạng vừa huấn luyện.

### 7.3 Vấn đề của mức 50% search lại

Một lần search lại và một lần sinh node mới tốn như nhau. So với search lại, node mới đem thêm ba thứ: kết quả ván thật cho mọi node phía trên, thế cờ mới, và độ đa dạng.

Search lại theo ưu tiên có giá trị giảm rất nhanh. Những node đầu có $m$ lớn nên đáng làm, còn càng về cuối càng là node có $m$ khoảng 1. Khi cắt theo $m$ nhỏ nhất, phần lớn node có tuổi không quá $W$, chỉ node gần gốc mới già hơn, nên điều kiện dừng ở phần 6 có lẽ đạt được sau rất ít lần search. Đây là dự đoán, cần đo trên cây thật.

Theo trí nhớ, MuZero Reanalyze dùng tỉ lệ làm mới rất cao, nhưng ở đó dữ liệu môi trường mới là thứ đắt. Ở cờ, chi phí chính là search, nên kết quả đó không chuyển thẳng sang đây được. Thông tin này chưa được tra cứu lại.

Bạn đã đồng ý rằng 125000 lần search lại là quá nhiều và nên giảm. Đề xuất là:

1. Search lại đến khi đạt điều kiện dừng, nhưng không quá mức trần.
2. Phần ngân sách còn dư chuyển sang sinh node mới.
3. Số node cắt lấy bằng số node sinh mới, rồi tính lại $W$ và $\gamma$ từ tỉ lệ đó.

Trong vài đời đầu, cây chưa đủ kích thước nên chưa cắt, và gần hết ngân sách dành cho node mới.

### 7.4 Cách so sánh với cách cũ

Trục hoành là **tổng số lần chạy mạng**, không phải số đời hay số ván. Cách cũ giữ nguyên cấu hình của nó, cùng số lần search mỗi đời và cùng số bước huấn luyện. Nên đo thêm số thế cờ khác nhau theo độ sâu, tỉ lệ mẫu theo độ sâu, và tỉ lệ ngân sách mà điều kiện dừng thực sự dùng.

---

## 8. Cắt lá ngẫu nhiên hay cắt lá có $m$ nhỏ nhất

Cách cắt chưa được chốt. Phần này ghi lại đầy đủ để bạn cân nhắc.

### 8.1 Đề xuất thay thế

Mỗi lần cắt chọn lá có $m$ nhỏ nhất, hòa thì chọn ngẫu nhiên. Vì $m$ giảm theo đời, lá như vậy thường thuộc nhánh cũ nhất. Một nhánh cũ được cắt trọn từ cuối lên đến điểm rẽ trước khi nhánh mới hơn bị động tới.

Vì $m$ của node cha không nhỏ hơn $m$ của node con, node có $m$ nhỏ nhất luôn có thể là một lá. Do đó, cách này giữ được tổng trọng lượng mẫu lớn nhất với số node cho trước. Đây là kết quả suy ra được.

### 8.2 Phản biện của bạn

Bạn chỉ ra rằng sau mỗi đời các node lá lại mọc ra, nên tàn cuộc không thực sự mất. Điều này đúng. Huấn luyện diễn ra ngay sau khi sinh dữ liệu, nên mỗi đời mạng luôn thấy node cuối ván vừa mọc với $m$ bằng 1. Những node cũ sống lâu thì đã bị giảm $m$, nên số lượng của chúng không chuyển hết thành tỉ trọng mẫu.

Nhận định trước đó rằng tàn cuộc "ít hơn cỡ 8 lần" là tính theo số node, nên đã nói quá về tỉ trọng mẫu.

### 8.3 Ước lượng thô

Với $\gamma$ bằng 0.875, mỗi nhánh dài 40 nửa nước, bị gặm 5 node mỗi đời. Với cắt ngẫu nhiên, node cách cuối ván $k$ nửa nước sống khoảng $k/5$ đời, nên tổng trọng lượng của nó là tổng các lũy thừa $\gamma$ qua số đời đó. Với cắt theo $m$ nhỏ nhất, cùng số node tương ứng cửa sổ khoảng 5 đời ở mọi độ sâu.

| | Cắt lá ngẫu nhiên | Cắt lá có $m$ nhỏ nhất |
|---|---|---|
| Tỉ trọng mẫu của 5 nửa nước cuối ván | khoảng 4% | khoảng 12.5% |
| Tổng trọng lượng mẫu giữ được | 141 | 158 (nhiều hơn khoảng 12%) |
| Tuổi của mẫu tàn cuộc | Rất mới | Cũ dần tới khoảng 5 đời |

Khác biệt ở tàn cuộc là cỡ 3 lần. Nếu nhánh thực tế ngắn hơn, vì cách quét rẽ cả ở node sâu, khác biệt có thể còn nhỏ hơn. Các con số này phụ thuộc vào giả định về độ dài nhánh.

### 8.4 Kết luận tạm

Cắt theo $m$ nhỏ nhất có ba lợi thế: nó suy ra được, nó giữ tỉ trọng theo độ sâu giống cách cũ nên so sánh sạch hơn, và nó không thêm tham số hay lần chạy mạng nào. Cắt ngẫu nhiên có một ưu điểm thật: mẫu tàn cuộc mới hơn, và các node cũ ở giữa nhánh còn được giữ lâu hơn. Chưa biết mạng được lợi hơn từ tàn cuộc nhiều hơn hay mới hơn. Hai cách chỉ khác nhau một dòng logic, nên đây là một thử nghiệm rất rẻ. Đây không phải quyết định sẽ định đoạt thành bại của thiết kế.

---

## 9. Ý tưởng của policy target mới

Nhãn policy hiện tại là phân bố lượt thăm $\pi$. MCTS tạo ra phân bố đó chủ yếu dựa vào **chênh lệch $Q$ giữa các nước**, mà $Q$ được tính bằng chính mạng. Nếu mạng sai ở một vùng, chênh lệch $Q$ có thể sai theo, và nhãn dạy lại đúng cái sai đó.

Cây trò chơi có thêm một thứ mà search không có: với những nước đã thử tại một node, cây có $G$ đến từ kết quả ván thật. Ý tưởng gồm hai câu:

1. Dùng $G$ để sửa chênh lệch $Q$, sửa nhiều hay ít tùy theo số ván làm bằng chứng.
2. Hỏi rằng nếu search có các giá trị đã sửa thì nó sẽ chia lượt thăm thế nào, và lấy kết quả đó làm nhãn mới.

Như vậy không có dạng công thức mới nào được đặt ra. Công thức dùng lại đúng điều kiện tối ưu đã sinh ra PUCT, nhắc lại ở phần 10.3.

---

## 10. Thiết lập công thức policy target

Để theo dõi, xét một node do Trắng đi, với $N$ bằng 8000 và $c$ bằng 2:

| Nước | $\pi$ | $Q$ | Số ván $n$ | $G$ của nhánh |
|---|---|---|---|---|
| a | 0.70 | 0.10 | 4 | -0.25 |
| b | 0.25 | 0.08 | 8 | +0.50 |
| c | 0.05 | 0 | chưa thử | không có |

### 10.1 Gộp hai chênh lệch

Với các nước đã thử, tính theo góc nhìn bên đang đi:

- $d_a=Q(a)-\bar Q$, với $\bar Q$ là trung bình $Q$ của các nước đã thử theo trọng số $\rho_s$.
- $\delta_a=\sigma_s\big(G(sa)-G(s)\big)$, với $\sigma_s$ bằng +1 khi Trắng đi và -1 khi Đen đi.

Lấy trọng số 0.67 và 0.33, ta có $\bar Q\approx 0.0934$ và $G(s)\approx 0$. Do đó nhánh a có $d\approx+0.007$, $\delta\approx-0.25$, và nhánh b có $d\approx-0.013$, $\delta\approx+0.50$.

Hai số này ước lượng cùng một đại lượng nhưng sai theo hai kiểu: $\delta_a$ có phương sai $\sigma^2/n_a$, còn $d_a$ có sai số của search với phương sai $\tau_d^2$. Khi có hai ước lượng độc lập, cách gộp có sai số nhỏ nhất là lấy trọng số tỉ lệ nghịch với phương sai. Trọng số của $\delta_a$ là

$$
\frac{n_a/\sigma^2}{n_a/\sigma^2+1/\tau_d^2}=\frac{n_a}{n_a+\kappa_d},\qquad \kappa_d=\frac{\sigma^2}{\tau_d^2}
$$

Viết phép gộp thành một lần sửa từ $d_a$ về phía $\delta_a$:

$$
D_a=d_a+\frac{n_a}{n_a+\kappa_d}\,(\delta_a-d_a)
$$

Giả sử $\kappa_d$ bằng 320. Nhánh a có mức tin khoảng 0.012, nên $D_a\approx+0.003$. Nhánh b có mức tin khoảng 0.024, nên $D_b\approx-0.001$. Cách biệt giữa a và b giảm từ khoảng 0.02 xuống khoảng 0.004.

### 10.2 Giá trị mới

$$
Q'(a)=\begin{cases}\bar Q+D_a & \text{nếu } a\in C(s)\\ Q(a) & \text{nếu } a\notin C(s)\end{cases}
$$

Trong ví dụ, $Q'(a)\approx 0.0968$, $Q'(b)\approx 0.0925$, và $Q'(c)=0$.

Nếu node chỉ có một nước đã thử, $d$ và $\delta$ đều bằng 0, nên $Q'$ trùng với $Q$. Vì vậy một ván đơn lẻ không thể làm nhiễu nhãn policy.

### 10.3 Giải lại điều kiện tối ưu của PUCT

Search dồn lượt thăm vào nước có $Q$ cao nhưng không rời prior $P$ quá xa. Tại nghiệm, lợi ích biên của mọi nước bằng nhau:

$$
Q(a)+\lambda\frac{P(a)}{\pi(a)}=\beta,\qquad \lambda=\frac{c}{\sqrt{N}}
$$

Nhân với $\pi(a)$ và chuyển vế, ta có $\lambda P(a)=\pi(a)\big(\beta-Q(a)\big)$. Lấy tổng theo mọi nước, với tổng $P$ và tổng $\pi$ đều bằng 1:

$$
\beta=\sum_a\pi(a)Q(a)+\lambda
$$

Trong ví dụ, $\lambda\approx 0.0224$ và $\beta\approx 0.1124$.

Giữ nguyên prior và thay $Q$ bằng $Q'$, phân bố mới phải thỏa $Q'(a)+\lambda P(a)/\pi'(a)=\beta'$. Thay $\lambda P(a)$ bằng biểu thức ở trên:

$$
\pi'(a)=\pi(a)\,\frac{\beta-Q(a)}{\beta'-Q'(a)}
$$

Số $\beta'$ làm tổng $\pi'$ bằng 1. Trong ví dụ, $\beta'\approx 0.1127$, và các nước nhận khoảng 0.55, 0.40, 0.05. Nhãn đổi từ 0.70 và 0.25 thành 0.55 và 0.40.

Khi $Q'$ trùng với $Q$ ở mọi nước, $\beta'$ bằng $\beta$ và $\pi'$ bằng đúng $\pi$.

### 10.4 Độ nhạy

Vì $\lambda$ rất nhỏ, thay đổi nhỏ trong $Q'$ cũng làm nhãn đổi nhiều:

| $\kappa_d$ | $\pi'$ của a | $\pi'$ của b |
|---|---|---|
| 40 | khoảng 0.09 | khoảng 0.88 |
| 320 | khoảng 0.55 | khoảng 0.40 |

Với chỉ 12 ván, kết quả có thể chỉ là nhiễu, nên $\kappa_d$ phải được ước lượng từ dữ liệu, không nên chọn tùy ý. Nếu search khá chính xác thì $\kappa_d$ lớn, và có lẽ cần hàng chục đến hàng trăm ván mới lật được nhãn. Phần lớn node sâu vì thế có $\pi'$ gần như bằng $\pi$, và lợi ích chủ yếu nằm ở những node có nhiều ván đi qua.

---

## 11. Công thức policy target đầy đủ

**Điều kiện áp dụng:** nếu $C(s)$ có ít hơn hai nước thì $\pi'(a)=\pi(a)$ và dừng.

**Bước 1.**

$$
\bar Q=\sum_{b\in C(s)}\rho_s(b)\,Q(b),\qquad d_a=Q(a)-\bar Q,\qquad \delta_a=\sigma_s\big(G(sa)-G(s)\big)
$$

**Bước 2.**

$$
D_a=d_a+\frac{n_a}{n_a+\kappa_d}\,(\delta_a-d_a)
$$

**Bước 3.** Với mọi nước có $\pi(a)>0$:

$$
Q'(a)=\begin{cases}\bar Q+D_a & \text{nếu } a\in C(s)\\ Q(a) & \text{nếu } a\notin C(s)\end{cases}
$$

**Bước 4.**

$$
\lambda=\frac{c}{\sqrt{N}},\qquad \beta=\sum_a\pi(a)Q(a)+\lambda,\qquad w_a=\max\big(\pi(a)\,(\beta-Q(a)),\;\epsilon\big)
$$

Trong đó $\epsilon$ là một số dương rất nhỏ. Số này cần có vì search thật không dừng đúng tại điểm tối ưu, nên có thể có nước có $Q(a)$ lớn hơn $\beta$.

**Bước 5.** Tìm $\beta'$:

$$
\sum_a\frac{w_a}{\beta'-Q'(a)}=1,\qquad \beta'\in\Big(\max_a Q'(a),\;\max_a Q'(a)+\sum_a w_a\Big]
$$

Tổng ở vế trái giảm dần khi $\beta'$ tăng, nên phương trình có đúng một nghiệm trong khoảng này, và chỉ cần chia đôi vài chục lần.

**Bước 6.**

$$
\pi'(a)=\frac{w_a}{\beta'-Q'(a)}
$$

Nước có $\pi(a)=0$ giữ nguyên $\pi'(a)=0$.

**Bước 7.** Mỗi node được lấy mẫu theo $m(s)$, với loss

$$
L_{\text{policy}}(s)=-\sum_a\pi'(a)\log p_\theta(a\mid s)
$$

**Ước lượng mỗi đời.** Tính trên mọi cặp node và nhánh, với node có ít nhất hai nước đã thử:

$$
\hat\tau_d^2=\max\Big(\text{trung bình}\big[(\delta_a-d_a)^2-\hat\sigma^2/n_a\big],\;\epsilon_\tau\Big),\qquad \kappa_d=\frac{\hat\sigma^2}{\hat\tau_d^2}
$$

Trong đó $\epsilon_\tau$ là một số dương nhỏ, chỉ để tránh chia cho 0.

**Lưu ý khi cài đặt.** $c$ phải là giá trị mà search đã dùng tại $N$ đó. Một kiểm tra đơn giản khi viết mã là cho $\kappa_d$ rất lớn: khi đó $\pi'$ phải gần như bằng $\pi$. Nếu có khác biệt lớn thì có lỗi, hoặc có nhiều nước bị chặn bởi $\epsilon$ ở bước 4.

---

## 12. Những điểm mới phát sinh khi có policy target

### 12.1 Nhãn gần gốc chỉ đến từ một lần search

Ở cách cũ, mỗi ván search thế khởi đầu một lần với một mẫu Dirichlet riêng, nên nhiễu tự triệt tiêu khi học. Trên cây, một phân bố có nhiễu được lấy mẫu $m$ lần. Một cách không thêm tham số là giữ $\pi$ và $Q$ dưới dạng trung bình của các lần search, trong đó lần cũ bị nhân $\gamma$ theo mỗi đời. Node gần gốc được search lại thường xuyên nhất, nên nhiễu sẽ giảm đúng ở nơi cần.

### 12.2 Cái sai hiếm vẫn được sửa chậm

$\kappa_d$ là số trung bình trên toàn cây, trong khi cái sai kiểu 8000 node chính là ngoại lệ ở đó sai số của search lớn hơn nhiều. Công thức sẽ tin search quá lâu ở đúng chỗ này. Có hai lựa chọn:

- Chấp nhận nhãn đổi chậm.
- Dùng độ lớn của $(\delta_a-d_a)$ so với nhiễu $\sigma/\sqrt{n_a}$ làm tín hiệu để dồn thêm ngân sách rẽ nhánh vào đúng node đó, vì nhiều ván hơn là cách chính đáng để lật nhãn sớm hơn.

Mình nghiêng về lựa chọn thứ hai, nhưng đề xuất chỉ làm sau khi có số liệu.

### 12.3 Có nên dùng $\pi'$ trong $\rho_s$ không

Nếu $\rho_s$ dùng $\pi'$ thay cho $\pi$, value cũng nhận được tín hiệu "b tốt hơn a" mà không cần lịch $\lambda_s$ của mức 3. Không có vòng lặp, vì $\pi'$ chỉ phụ thuộc vào các node con. Nhưng trọng số khi đó phụ thuộc vào kết quả, nên lạc quan giả có thể quay lại. Đề xuất là trước mắt giữ $\pi$, rồi thử $\pi'$ như một biến thể.

### 12.4 Giới hạn của phép suy ra

- Phép gộp ở phần 10.1 chỉ tối ưu nếu hai sai số độc lập, trong khi $\delta_a$ còn chứa nhiễu của $G(s)$ và sai số của search không giống nhau ở mọi node.
- Phần 10.3 giả định search ở đúng điểm tối ưu và prior không đổi. Search thật chỉ xấp xỉ điểm đó.

---

## 13. Toàn bộ công thức sau khi cập nhật

**Trọng số và giá trị tổng hợp, tính từ dưới lên:**

$$
f_a=\frac{n(sa)}{n(sa)+\kappa},\qquad \nu=\frac{1-\sum_b\pi_b f_b}{\sum_b f_b},\qquad \rho_s(a)=(\pi_a+\nu)f_a
$$

$$
G(s)=\sum_{a\in C(s)}\rho_s(a)\,G(sa),\qquad n(s)=\frac{1}{\sum_a\rho_s(a)^2/n(sa)}
$$

**Value target:**

$$
\text{value target}(s)=\frac{0.25\,q(s)+n(s)\,G(s)}{0.25+n(s)}
$$

Tại node có một ván với $n$ bằng 1, công thức cho đúng $0.2q+0.8z$. Bộ công thức trước đó dùng $m$ cho gọn. Dùng $n$ thì đúng với phép suy ra hơn, và hai số trùng nhau khi trọng số theo số ván.

**Policy target:** theo phần 11.

**Vận hành cây:**

| Thành phần | Công thức | Nguồn gốc |
|---|---|---|
| Ưu tiên search lại | $m(s)\hat\Delta(\text{tuổi})$ | Tối ưu với chi phí bằng nhau |
| Dừng search lại | Tuổi trung bình theo $m$ không vượt quá $W/2$, trần 20% | Khớp với buffer cũ, trần là lựa chọn |
| Giảm $m$ | $\gamma=1-1/W$ | Khớp với buffer cũ |
| $W$ | Kích thước cây chia số node mới mỗi đời | Từ cấu hình cây |
| Lấy mẫu huấn luyện | Tỉ lệ với $m(s)$ | Giữ tỉ trọng cũ |
| $\kappa$, $\kappa_d$ | Ước lượng từ cây mỗi đời | Từ phép suy ra |

**Các số còn phải tự chọn:** kích thước cây, mức trần search lại, cách cắt lá, $\epsilon$ và $\epsilon_\tau$. Hằng số 0.25 kế thừa từ tỉ lệ 20/80 của bạn, không phải giá trị tối ưu.

---

## 14. Dữ liệu mỗi node cần lưu

Phần này là hệ quả của các công thức trên, để dùng khi viết mã.

- **Dùng cho huấn luyện:** thế cờ đầu vào và giá trị $q$. Đây là phần có thể bỏ khi node bị cắt.
- **Dùng cho policy target:** $\pi(a)$ và $Q(a)$ của mọi nước đã thăm, cùng $N$. Prior không cần lưu.
- **Dùng cho cây:** với mỗi nước đã thử, bộ thống kê $m(sa)$, $n(sa)$, $G(sa)$, được giữ ở node cha kể cả khi node con đã bị cắt.
- **Dùng cho ưu tiên:** đời của lần search gần nhất tại node.

Nếu value head xuất ra thắng, hòa, thua thay vì một con số, $G$ và $q$ nên được tổng hợp cho từng thành phần theo cùng trọng số.

---

## 15. Vòng lặp mỗi đời

1. Huấn luyện mạng, với mẫu lấy theo $m$, dùng value target và policy target đã tính.
2. Cắt lá, giữ thống kê ở node cha, rồi nhân mọi $m$ với $\gamma$.
3. Search lại theo ưu tiên đến khi đạt điều kiện dừng hoặc chạm trần. Ghi lại độ lệch để cập nhật bảng $\hat\Delta$.
4. Tính lại $G$ và $n$ từ dưới lên, để bước quét đọc được $\pi$ mới.
5. Quét cây với temperature 0.5, rẽ nhánh và tự chơi với temperature 0 đến khi hết ngân sách search của đời.
6. Tính lại $G$, $n$, $\kappa$, $\kappa_d$, value target và policy target.

Trong vài đời đầu, cây chưa đủ kích thước nên chưa cắt. Ở đời đầu tiên, bước quét lặp ngay trong đời đó, vì cây còn trống.

---

## 16. Thiết kế đã đủ chưa, và thứ tự thử nghiệm

### 16.1 Kết luận

Thiết kế đã đủ để bắt đầu thử nghiệm. Những câu hỏi lớn còn lại, như $\kappa_d$ thực tế bao nhiêu hay cây có đủ chồng lấn không, chỉ có số liệu mới trả lời được. Thiết kế tiếp lúc này phần lớn là suy đoán chồng lên suy đoán.

### 16.2 Giá trị mặc định

| Mục | Mặc định đề xuất |
|---|---|
| Cách cắt lá | Lá có $m$ nhỏ nhất, rồi so với cắt ngẫu nhiên |
| Kích thước cây | 1 triệu node |
| Trần search lại | 20% ngân sách, kèm điều kiện dừng |
| Giảm $m$ | $\gamma=1-1/W$ |
| Nhãn gần gốc | Trung bình các lần search, lần cũ bị nhân $\gamma$ theo mỗi đời |
| Dồn ngân sách vào chỗ bất đồng | Chưa làm |

Một điểm chưa bàn là resign. Nếu engine có resign, kết quả đó sẽ đi vào $G$ như kết quả thật, nên cần có cách kiểm soát.

### 16.3 Thứ tự làm

Nên thêm từng phần một, vì nếu bật tất cả cùng lúc thì khi kết quả xấu sẽ không biết phần nào gây ra.

1. **Kiểm tra công thức trên một phiên bản rất nhỏ của biến thể cờ,** nơi tính được giá trị chính xác, để đo xem $G$ và value target mới có ít sai số hơn $z$ không.
2. **Thêm cây trò chơi chỉ cho value target,** với quét toàn cây, temperature 0, và policy target giữ nguyên là $\pi$.
3. **Thêm search lại theo ưu tiên,** rồi đo xem nhãn có bớt cũ không và ngân sách thực sự dùng là bao nhiêu.
4. **Thêm policy target $\pi'$.** Đây là phần nhạy nhất, nên để sau cùng.

Ở mỗi bước, so với engine hiện tại theo sức mạnh trên cùng tổng số lần chạy mạng, với cùng số bước huấn luyện. Theo dõi thêm số thế cờ khác nhau theo độ sâu, tỉ trọng mẫu theo độ sâu, và phân bố $m$ trong cây.

### 16.4 Điều chưa biết

Đây là một thiết kế có lý do rõ ràng, nhưng chưa có bằng chứng nào cho thấy nó nhanh hơn cách cũ. Rủi ro lớn nhất, theo đánh giá hiện tại, là các ván chồng lấn nhau quá ít ở ngoài khai cuộc. Khi đó $G$ gần như bằng $z$ ở phần lớn node, nên lợi ích chính sẽ đến từ việc rẽ nhánh rẻ ở tàn cuộc chứ không phải từ tổng hợp. Bước 2 sẽ cho thấy điều này khá sớm.

---

## Phụ lục A: Ký hiệu

| Ký hiệu | Ý nghĩa |
|---|---|
| $s$, $sa$ | Một node, và node con sau nước $a$ |
| $C(s)$ | Tập các nước đã thử tại $s$ |
| $m(s)$ | Số ván đi qua $s$, đã giảm theo đời |
| $n(s)$ | Số ván hiệu dụng tại $s$ |
| $\pi(a)$, $Q(a)$, $N$ | Tỉ lệ lượt thăm, giá trị của nước $a$, và tổng lượt thăm |
| $\pi_a$ | Tỉ lệ lượt thăm đã chia lại trên các nước đã thử |
| $q(s)$ | Giá trị MCTS của node |
| $G(s)$ | Giá trị tổng hợp từ kết quả các ván, góc nhìn quân Trắng |
| $\rho_s(a)$ | Trọng số của nhánh $a$ khi tính $G(s)$ |
| $f_a$, $\nu$ | Thừa số độ tin cậy, và phần trọng số được chia lại |
| $\sigma^2$ | Phương sai kết quả của một ván |
| $\omega^2$ | Phương sai giá trị thật giữa các nhánh |
| $\kappa$ | $\sigma^2/\omega^2$ |
| $\tau_d^2$ | Sai số bình phương của chênh lệch do search tính |
| $\kappa_d$ | $\sigma^2/\tau_d^2$ |
| $\sigma_s$ | +1 khi Trắng đi, -1 khi Đen đi |
| $d_a$, $\delta_a$, $D_a$ | Chênh lệch của search, của kết quả ván, và sau khi gộp |
| $Q'(a)$, $\pi'(a)$ | Giá trị đã sửa, và policy target mới |
| $\lambda$, $\beta$, $\beta'$ | Mức tin vào prior, và mức lợi ích biên chung trước và sau khi sửa |
| $\Delta_s$, $\hat\Delta$ | Sai số của nhãn do đã cũ, và bảng ước lượng theo tuổi |
| $W$, $\gamma$ | Cửa sổ tính bằng số đời, và hệ số giảm $m$ mỗi đời |

---

## Phụ lục B: Những chỗ đã sửa lại

- **Thừa số độ tin cậy.** Trước đây ghi là "chọn, không suy ra". Nay đã suy ra được, và công thức có thêm $\nu$.
- **Công thức ưu tiên.** $m\times$tuổi nay là trường hợp riêng của $m\hat\Delta(\text{tuổi})$.
- **Số 0.75 của $\gamma$.** Chỉ ứng với $W$ bằng 4, không phải giá trị chung.
- **"Tàn cuộc ít hơn cỡ 8 lần".** Đó là tính theo số node. Theo tỉ trọng mẫu, khác biệt ước lượng là cỡ 3 lần, và bạn đã chỉ ra đúng rằng các lá mọc lại mỗi đời.
- **"Không cần prior" trong policy target.** Vẫn đúng về dữ liệu cần lưu, nhưng cần thêm $\epsilon$ ở bước 4 cho trường hợp $Q(a)$ lớn hơn $\beta$.
- **Dùng $m$ trong value target.** Nay ghi rõ $n$ là số đúng theo phép suy ra.

---

## Phụ lục C: Dòng thời gian

1. Bạn lo về hai công thức không được suy ra, chốt giữ thống kê khi cắt, chốt temperature 0 cho thử nghiệm ban đầu, và nhờ đề xuất tốc độ giảm $m$ cùng tỉ lệ search lại.
2. Thừa số độ tin cậy và công thức ưu tiên được suy ra. Tốc độ giảm $m$ và điều kiện dừng được gắn với $W$. Bạn thấy công thức có suy ra thì ổn hơn.
3. Bạn đề xuất quy mô 1000000 node với các phần 125000, và làm rõ mục tiêu là cùng lượng tính toán thì tiến bộ nhanh hơn. Phần đánh giá đề nghị đổi cách cắt lá và coi 125000 là trần.
4. Bạn hỏi cắt theo $m$ nhỏ nhất có cải thiện nhiều không, vì lá mọc lại mỗi đời. Ước lượng cho thấy khác biệt vừa phải, cỡ 3 lần ở tỉ trọng tàn cuộc.
5. Bạn chưa chốt cách cắt, đồng ý giảm search lại, và chuyển sang policy target. Công thức $\pi'$ được đề xuất từ điều kiện tối ưu của PUCT.
6. Bạn yêu cầu giải thích lại từ ý tưởng, rồi yêu cầu công thức chi tiết.
7. Bạn hỏi thiết kế đã đủ chưa. Kết luận là đủ để thử nghiệm, kèm thứ tự thử từng phần. Đây là điểm cuối của tệp này.
