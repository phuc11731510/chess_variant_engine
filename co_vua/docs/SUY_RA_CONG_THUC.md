# Các công thức của cách cây trò chơi được suy ra thế nào

Viết ngày 15/11/2026, đối chiếu với mã đang chạy trong `co_vua/scripts/cv/cay.py` (lần chạy 5). Tài liệu thiết kế `THIET_KE_CO_VUA.md` ghi lịch sử các quyết định. Tài liệu này chỉ làm một việc: với mỗi công thức hay quy tắc đang chạy, nói rõ nó được **suy ra** từ giả định nào, hay được **ước lượng** từ dữ liệu, hay chỉ được **đặt tay**, và giả định nào trong đó đã bị số đo thật làm lung lay.

Mục 1 là bảng tổng hợp. Mục 2 nhắc lại cây và các số mỗi node lưu, kèm một node ví dụ dùng xuyên suốt. Các mục 3 đến 9 đi qua từng công thức theo đúng thứ tự mà mã tính chúng mỗi đời.

---

## 1. Bảng ba nhóm

| Nhóm | Công thức hay quy tắc | Mục |
|---|---|---|
| **Suy ra từ giả định rõ ràng** | Giá trị tổng hợp $G$ là trung bình có trọng số của các nhánh con | 3 |
| | Độ sai $E$ của $G$ (công thức $\sum\rho^2E+\omega^2U$) | 4 |
| | Trọng số nhánh $\rho$ (bộ trọng số làm $E$ nhỏ nhất) | 5 |
| | Tỉ lệ trộn nhãn value $w_q=E/(E+\tau_q^2)$ | 6 |
| | Phép ước $\tau_q^2$ bằng trung bình $(G-q)^2-E$ (phương pháp moment) | 7 |
| | Hệ số làm cũ $\gamma=1-1/W$ | 8.1 |
| | Khoá $-\ln(u)/w$ cho ra phép bốc không lặp tỉ lệ với $w$ | 8.4 |
| | Phần $1/(k+1)$ trong ưu tiên search lại | 8.5 |
| **Ước lượng từ dữ liệu** | Độ toả $\omega^2(s)$ của giá trị các nước tại mỗi node, từ $Q$ của search | 4.3 |
| | $\tau_q^2$ của từng khoảng cách tới cuối ván | 7 |
| | Bảng $\hat\Delta$ (nhãn policy lệch bao nhiêu theo tuổi và số lần search) | 8.5 |
| **Đặt tay hoặc chọn qua thử** | Temperature quét $T=0{,}5$ (chủ dự án chọn) | 8.3 |
| | Số mũ khoá điểm rẽ $m^2$ (chọn qua mô phỏng) | 8.4 |
| | $W=4$ đời (chọn để giống cửa sổ của cách truyền thống) | 8.1 |
| | Cắt lá có $m$ nhỏ nhất (lập luận, không tối ưu hoá) | 8.2 |
| | Trần search lại 20% ngân sách | 8.5 |
| | Mỗi node học một lần, số bước ít nhất bằng số mẫu chia 1024 | 9 |
| | Các mốc khoảng cách 0, 5, 10, 20, 40, 80, 160 của $\tau_q^2$; sàn 0,01; khoảng ít hơn 1000 node mượn khoảng gần cuối hơn | 7.3 |
| | Ước chi phí ván rẽ $(\text{cách cuối}+1)\times490$ và lập dư 1,5 lần | 8.6 |
| | Nhãn policy là trung bình $\pi$ các lần search (không suy ra tối ưu) | 9 |

Còn vài chặn số rất nhỏ trong mã (ví dụ $10^{-12}$ ở mẫu số, $10^{-6}$ cho $\omega^2$). Chúng chỉ để tránh chia cho 0 và không ảnh hưởng tới kết quả.

"Suy ra" ở đây nghĩa là công thức đúng **nếu** các giả định đúng. Hai giả định quan trọng nhất đang bị số đo thật làm lung lay, và mục 4.4 và 7.2 chỉ ra chỗ đó:

- Giả định thứ nhất là $\omega^2(s)$ đo đúng độ toả của giá trị thật. Thực tế nó bị ước cao vì $Q$ có nhiễu, nên $E$ ở xa cuối ván bị ước cao.
- Giả định thứ hai là sai số của $q$ độc lập với sai số của $G$. Thực tế mạng được học từ chính các nhãn chứa $G$, nên hai sai số có thể cùng chiều.

---

## 2. Cây và các số mỗi node lưu

Cây trò chơi (cây này là tập mọi ván tự chơi thật của cách cây, gộp chung sao cho hai ván đi chung một đoạn nước thì dùng chung các node của đoạn đó) giữ qua nhiều đời mạng. Mỗi node $s$ là một thế cờ trên đúng một đường đi từ thế khởi đầu, nên hai thế cờ giống nhau ở hai đường khác nhau vẫn là hai node khác nhau.

Mỗi node lưu hai nhóm số.

**Nhóm thứ nhất đến từ search tại node.** Một lần search (lần search này là một chuỗi khoảng 800 lượt thăm, mỗi lượt đi từ $s$ xuống một thế sâu hơn và chạy mạng một lần ở đó) cho ra, với mỗi nước $a$ mà search đã thăm:

- $n(a)$ là số lượt thăm đi qua nước $a$ ngay từ $s$.
- $\pi(a)=n(a)/N$ là tỉ lệ lượt thăm, với $N$ là tổng lượt thăm. Các $\pi(a)$ cộng lại bằng 1.
- $Q(sa)$ là giá trị search của thế cờ sau nước $a$ (giá trị này là trung bình đánh giá của mạng ở đáy các lượt thăm đã đi qua $sa$), theo góc nhìn bên đang đi tại $s$, trên thang từ $-1$ (thua chắc) đến $+1$ (thắng chắc).

Tập các nước search đã thăm gọi là $A(s)$. Giá trị dùng làm nhãn value là $q(s)=Q(sa^*)$ với $a^*$ là nước có nhiều lượt thăm nhất. Node được search nhiều lần thì lưu trung bình có trọng số của mọi lần (lần cũ bị nhân $\gamma$ mỗi đời, mục 8.1), và tổng trọng số của các lần search gọi là $k(s)$.

**Nhóm thứ hai đến từ các ván thật đã đi qua node.** Tập các nước mà ít nhất một ván thật đã chơi từ $s$ gọi là $C(s)$; thường $C(s)$ nằm trong $A(s)$. Với mỗi nước đã chơi $a$, node lưu $m(sa)$ (số ván đi qua $sa$, nhân $\gamma$ mỗi đời), $G(sa)$ và $E(sa)$ (định nghĩa ở mục 3 và 4).

**Node ví dụ dùng xuyên suốt.** Tại node $s$, Trắng đi. Search thăm ba nước:

| Nước | $\pi$ | $Q$ (góc Trắng) | Đã có ván chơi? | $G$ của node con (góc Trắng) | $E$ của node con |
|---|---|---|---|---|---|
| $a_1$ | 0,70 | +0,10 | có | $-0{,}25$ | 0,010 |
| $a_2$ | 0,25 | $-0{,}05$ | có | +0,50 | 0,005 |
| $a_3$ | 0,05 | $-0{,}30$ | chưa | | |

Vậy $A(s)=\{a_1,a_2,a_3\}$ và $C(s)=\{a_1,a_2\}$. Hai cặp $G$, $E$ của node con đã tính xong từ các node bên dưới, vì mã tính từ cuối ván ngược lên gốc.

---

## 3. Giá trị tổng hợp $G$

**Định nghĩa.** Ở node kết thúc ván, $G$ là kết quả ván theo luật cờ ($+1$ Trắng thắng, 0 hoà, $-1$ Đen thắng). Ở node khác,
$$G(s)=\sum_{a\in C(s)}\rho_s(a)\,G(sa),$$
với $\rho_s(a)$ là trọng số của nhánh $a$ (tính ở mục 5), các $\rho$ không âm và cộng lại bằng 1.

**Vì sao là trung bình có trọng số.** $G(s)$ muốn ước lượng giá trị thật $V(s)$ của thế cờ. Giá trị thật được định nghĩa là kết quả trung bình nếu từ $s$ hai bên chơi tiếp vô số ván, mỗi nước bốc theo $\pi$. Theo định nghĩa đó, ván đầu tiên từ $s$ đi nước $a$ với xác suất $\pi(a)$, rồi kết quả trung bình từ đó là $V(sa)$, nên
$$V(s)=\sum_{a\in A(s)}\pi(a)\,V(sa).$$
Ta không biết $V(sa)$, chỉ có $G(sa)$ cho các nước đã chơi. Vì vậy ước lượng tự nhiên nhất là một tổ hợp tuyến tính của các $G(sa)$ có tổng hệ số bằng 1 (tổng hệ số bằng 1 để nếu mọi nhánh cùng giá trị $c$ thì $G(s)$ cũng bằng $c$). Câu hỏi còn lại chỉ là chọn hệ số nào, và mục 5 trả lời.

**Ví dụ trên node ví dụ.** Mục 5 sẽ tính ra $\rho(a_1)=0{,}560$ và $\rho(a_2)=0{,}440$. Khi đó
$$G(s)=0{,}560\times(-0{,}25)+0{,}440\times0{,}50\approx+0{,}080.$$
Trên một đoạn không rẽ nhánh (chỉ một nước đã chơi), $\rho=1$ nên $G$ bằng đúng kết quả của ván duy nhất đi qua.

Trong mã, $G$ không phải một số mà là bộ ba xác suất (thắng, hoà, thua) theo góc Trắng, gộp bằng cùng các $\rho$. Số một chiều ở đây bằng thắng trừ thua.

---

## 4. Độ sai $E$ của $G$

### 4.1 Định nghĩa và các giả định

$E(s)$ là sai số bình phương trung bình của $G(s)$ so với $V(s)$, tức trung bình của $\big(G(s)-V(s)\big)^2$ nếu cùng một quá trình sinh ván được lặp lại nhiều lần. Ở node kết thúc ván, $E=0$ vì phán quyết của luật cờ không sai.

Phép suy ra dùng hai giả định.

- **Giả định G1.** Mỗi $G(sa)$ bằng $V(sa)$ cộng một sai số $e_a$ có trung bình 0 và phương sai $E(sa)$, và sai số của các nhánh khác nhau độc lập với nhau. Giả định này hợp lý khi các nhánh do các ván khác nhau chơi ra sau chỗ tách.
- **Giả định G2.** Giá trị thật của các nước con dao động quanh một mức chung: $V(sa)=\bar V+\delta_a$, với các $\delta_a$ độc lập, trung bình 0, phương sai $\omega^2(s)$, và độc lập với các $e_a$. Ta không biết các $\delta_a$, nên coi chúng là ngẫu nhiên; $\omega^2(s)$ là độ toả (độ toả này là phương sai của giá trị thật giữa các nước đi từ cùng thế cờ $s$).

### 4.2 Suy ra công thức

Viết $\rho_a=0$ cho các nước chưa chơi để mọi tổng chạy trên cùng tập $A(s)$. Sai số của $G(s)$ là
$$G(s)-V(s)=\sum_{a}\rho_a\big(V(sa)+e_a\big)-\sum_a\pi_a V(sa)=\sum_a\rho_a e_a+\sum_a(\rho_a-\pi_a)V(sa).$$
Thay $V(sa)=\bar V+\delta_a$ vào số hạng thứ hai. Vì $\sum_a\rho_a=1$ và $\sum_a\pi_a=1$ nên $\sum_a(\rho_a-\pi_a)=0$, và phần $\bar V$ triệt tiêu:
$$G(s)-V(s)=\sum_a\rho_a e_a+\sum_a(\rho_a-\pi_a)\,\delta_a.$$
Hai tổng gồm các số hạng độc lập, trung bình 0, nên bình phương trung bình bằng tổng các phương sai:
$$E(s)=\sum_{a\in C(s)}\rho_a^2\,E(sa)\;+\;\omega^2(s)\,U(s),\qquad U(s)=\sum_{a\in A(s)}(\rho_a-\pi_a)^2.$$
Tách $U$ theo nước đã chơi và chưa chơi (với nước chưa chơi $\rho_a=0$ nên số hạng là $\pi_a^2$):
$$U(s)=\sum_{a\in C(s)}(\rho_a-\pi_a)^2+\sum_{a\in A(s)\setminus C(s)}\pi_a^2.$$
Đây đúng là công thức trong mã (`E = Σ r²·E(con) + om2·U`).

**Đọc hai phần của $E$.**

- Phần thứ nhất là sai số thừa kế từ các nhánh con. Trọng số xuất hiện dưới dạng bình phương, nên gộp nhiều nhánh độc lập làm sai số nhỏ đi (ví dụ, hai nhánh cùng $E=0{,}01$ và trọng số 0,5 mỗi bên cho phần này bằng $2\times0{,}5^2\times0{,}01=0{,}005$, một nửa của từng nhánh).
- Phần thứ hai là sai số do cách gộp các nhánh đã chơi lệch khỏi cách gộp theo $\pi$ mà giá trị thật dùng. Nếu mọi nước có cùng giá trị thật ($\omega^2=0$) thì lệch thế nào cũng không sai, nên phần này tỉ lệ với $\omega^2$.

**Ví dụ trên node ví dụ** (dùng $\omega^2(s)=0{,}01032$ tính ở mục 4.3, và $\rho=0{,}560$, $0{,}440$ của mục 5):

1. Phần thừa kế là $0{,}560^2\times0{,}010+0{,}440^2\times0{,}005\approx0{,}00410$.
2. $U(s)=(0{,}560-0{,}70)^2+(0{,}440-0{,}25)^2+0{,}05^2\approx0{,}0196+0{,}0361+0{,}0025=0{,}0581$.
3. Phần lệch cách gộp là $0{,}01032\times0{,}0581\approx0{,}00060$.
4. Cộng lại, $E(s)\approx0{,}00470$, tức $G(s)=+0{,}080$ thường lệch cỡ $\sqrt{0{,}0047}\approx0{,}07$ so với giá trị thật.

**Ví dụ trên một đường không rẽ nhánh.** Trên đoạn mà mỗi node chỉ có một nước đã chơi, $\rho=1$ cho nước đó, nên phần thừa kế bằng đúng $E$ của node con và mỗi nửa nước đi lên cộng thêm $\omega^2U$. Giả sử mỗi node trên đường có $\omega^2=0{,}004$ (cỡ trung bình đo được trên cây thật, log `omega2_tb` khoảng 0,0039) và $U=0{,}5$:

1. Node cách cuối ván 1 nửa nước có $E=0+0{,}004\times0{,}5=0{,}002$.
2. Node cách cuối ván 10 nửa nước có $E=10\times0{,}002=0{,}02$.
3. Node cách cuối ván 160 nửa nước có $E=160\times0{,}002=0{,}32$.

Số đo trên cây sau đời 10 cho $E$ trung bình 0,305 ở các node cách cuối ván từ 160 nửa nước, khớp cỡ với cách cộng dồn này.

### 4.3 Ước lượng $\omega^2(s)$ từ search (phương án B)

$\omega^2(s)$ không biết được vì giá trị thật không biết. Mã ước nó tại từng node từ chính các $Q$ mà search đã lưu (cách này là "phương án B" của tài liệu thiết kế, mục 4.4, được duyệt 7/11; phần mô tả một $\omega^2$ chung cho cả cây ở mục 4.4 của tài liệu thiết kế là bản cũ):
$$\bar Q=\sum_{a\in A(s)}\pi_a Q(sa),\qquad \omega^2(s)=\sum_{a\in A(s)}\pi_a\big(Q(sa)-\bar Q\big)^2.$$
Đây là phương sai của $Q$ giữa các nước, tính theo trọng số $\pi$. Lý do là $Q(sa)$ là ước lượng của mạng cho $V(sa)$, nên độ toả của các $Q$ là ước lượng của độ toả của các $V$.

**Ví dụ trên node ví dụ.**

1. $\bar Q=0{,}70\times0{,}10+0{,}25\times(-0{,}05)+0{,}05\times(-0{,}30)=0{,}0425$.
2. Ba số hạng là $0{,}70\times0{,}0575^2\approx0{,}00231$, $0{,}25\times0{,}0925^2\approx0{,}00214$ và $0{,}05\times0{,}3425^2\approx0{,}00587$.
3. Cộng lại, $\omega^2(s)\approx0{,}01032$.

Nước $a_3$ chỉ có 5% lượt thăm nhưng đóng góp hơn một nửa $\omega^2$, vì giá trị của nó lệch xa nhất.

### 4.4 Chỗ giả định bị lung lay: $\omega^2$ ước cao, nên $E$ ước cao ở xa cuối ván

Mỗi $Q(sa)$ bằng $V(sa)$ cộng một nhiễu (nhiễu này đến từ việc mạng đánh giá sai và từ việc nước ít lượt thăm có $Q$ là trung bình của ít lượt). Phương sai của một đại lượng có nhiễu bằng phương sai của phần thật cộng phương sai của nhiễu, nên trung bình
$$\omega^2_{\text{ước}}(s)\approx\omega^2_{\text{thật}}(s)+\text{phần nhiễu của }Q.$$
Như vậy phép ước luôn nghiêng về phía cao. Mỗi node trên đường cộng thêm một chút phần dư đó vào $E$, và qua hàng trăm nửa nước phần dư cộng dồn thành lớn. Trong khi đó sai số thật của $G$ không thể lớn tuỳ ý: kết quả ván nằm trong $[-1,1]$, nên ở một thế cờ đã gần như chắc hoà, kết quả ván dao động rất ít dù thế cờ còn cách cuối ván rất xa.

Mô phỏng ngày 5/11 (tài liệu thiết kế, mục 14) đã thấy điều này: với phương án B, $E$ dự báo quá cao ở nhóm $E$ lớn, gấp 2 đến 3 lần sai số thật. Mục 7.2 cho thấy hậu quả của việc đó trên nhãn value.

---

## 5. Trọng số nhánh $\rho$

### 5.1 Bài toán

Mục 4 cho $E(s)$ như một hàm của các $\rho_a$. Chọn $\rho$ để $G(s)$ sai ít nhất, tức giải
$$\min_{\rho}\;\sum_{a\in C(s)}\Big(\rho_a^2E_a+\omega^2(\rho_a-\pi_a)^2\Big)\quad\text{với}\quad\sum_{a\in C(s)}\rho_a=1,$$
trong đó viết gọn $E_a=E(sa)$ và $\omega^2=\omega^2(s)$. Phần $\sum_{A\setminus C}\pi_a^2$ của $U$ không phụ thuộc $\rho$ nên bỏ ra ngoài.

### 5.2 Suy ra bằng nhân tử Lagrange

Nhân tử Lagrange (nhân tử Lagrange này là một biến phụ $\lambda$ được thêm vào để tìm cực tiểu khi các biến bị ràng buộc bởi một phương trình) cho điều kiện: đạo hàm của hàm cần cực tiểu theo mỗi $\rho_a$ bằng cùng một số $\lambda$ cho mọi $a$. Đạo hàm theo $\rho_a$ là $2\rho_aE_a+2\omega^2(\rho_a-\pi_a)$, nên
$$2\rho_aE_a+2\omega^2(\rho_a-\pi_a)=\lambda\;\Longrightarrow\;\rho_a(E_a+\omega^2)=\omega^2\pi_a+\tfrac{\lambda}{2}.$$
Đặt $\nu=\lambda/(2\omega^2)$ và $f_a=\dfrac{\omega^2}{\omega^2+E_a}$, ta được
$$\rho_a=(\pi_a+\nu)\,f_a.$$
Ràng buộc tổng bằng 1 cho $\sum_a(\pi_a+\nu)f_a=1$, nên
$$\nu=\frac{1-\sum_{a\in C(s)}\pi_af_a}{\sum_{a\in C(s)}f_a}.$$
Hàm cần cực tiểu là tổng các bình phương với hệ số dương, nên nghiệm này là cực tiểu duy nhất. $\nu$ không bao giờ âm, vì mỗi $f_a\le1$ và $\sum_C\pi_a\le1$ nên $\sum_C\pi_af_a\le1$; do đó mọi $\rho_a\ge0$.

### 5.3 Ví dụ trên node ví dụ

1. Độ tin cậy là $f_1=0{,}01032/(0{,}01032+0{,}010)\approx0{,}508$ và $f_2=0{,}01032/(0{,}01032+0{,}005)\approx0{,}674$.
2. $\nu=\dfrac{1-(0{,}70\times0{,}508+0{,}25\times0{,}674)}{0{,}508+0{,}674}\approx\dfrac{1-0{,}524}{1{,}181}\approx0{,}403$.
3. $\rho_1=(0{,}70+0{,}403)\times0{,}508\approx0{,}560$ và $\rho_2=(0{,}25+0{,}403)\times0{,}674\approx0{,}440$.

Kiểm rằng đây đúng là cực tiểu bằng cách so với hai bộ trọng số khác trên cùng node:

| $\rho_1$, $\rho_2$ | $E(s)$ |
|---|---|
| 0,560, 0,440 (công thức) | 0,00470 |
| 0,500, 0,500 | 0,00483 |
| 0,737, 0,263 (theo $\pi$, chuẩn hoá cho tổng bằng 1) | 0,00582 |

**Đọc kết quả.** $\pi$ nghiêng mạnh về $a_1$ (0,70 so với 0,25), nhưng nhánh $a_2$ có $E$ nhỏ hơn (bằng chứng chắc hơn), nên $\rho$ kéo về gần chia đôi. Khi mọi nhánh có $E$ rất nhỏ so với $\omega^2$ thì $f\approx1$ và $\rho\approx\pi$ cộng một phần chia đều. Khi mọi nhánh có $E$ rất lớn so với $\omega^2$ thì $f\approx\omega^2/E$ và $\rho$ gần tỉ lệ với $1/E$, tức là cách gộp theo nghịch đảo phương sai ở mục 6.

---

## 6. Tỉ lệ trộn nhãn value $w_q$

### 6.1 Suy ra

Tại node $s$ có hai ước lượng của cùng giá trị thật: $G(s)$ với sai số bình phương trung bình $E(s)$, và $q(s)$ của search với sai số bình phương trung bình $\tau_q^2$. Nhãn value là $w\,q+(1-w)\,G$. Giả sử cả hai ước lượng không lệch (trung bình sai số bằng 0) và sai số của chúng độc lập. Sai số của nhãn là $w\,e_q+(1-w)\,e_G$, nên
$$\text{MSE}(w)=w^2\tau_q^2+(1-w)^2E.$$
Đạo hàm theo $w$ bằng 0 cho $2w\tau_q^2-2(1-w)E=0$, nên
$$w_q=\frac{E}{E+\tau_q^2}.$$
Đây là cách gộp theo nghịch đảo phương sai (cách gộp này cho mỗi ước lượng trọng số tỉ lệ với một chia sai số bình phương của nó, nên ước lượng càng chắc thì càng được tin).

Nếu hai sai số có hiệp phương sai $c$ (hiệp phương sai này là trung bình của tích hai sai số, dương khi chúng hay lệch cùng chiều), cùng phép tính cho
$$w_q=\frac{E-c}{E+\tau_q^2-2c}.$$
Mã dùng công thức với $c=0$.

### 6.2 Ví dụ trên node ví dụ

Node ví dụ có $E(s)=0{,}00470$ và $q(s)=+0{,}10$ (Trắng đi nên góc bên đi trùng góc Trắng). Giả sử node cách cuối ván 7 nửa nước, nên dùng $\tau_q^2$ của khoảng 5 đến 10, ở đời 10 là 0,0447:

1. $w_q=0{,}00470/(0{,}00470+0{,}0447)\approx0{,}095$.
2. Nhãn value là $0{,}095\times0{,}10+0{,}905\times0{,}080\approx0{,}082$.

Nhãn gần như theo $G$, vì gần cuối ván kết quả các ván thật chắc hơn đánh giá của mạng.

Cùng node nhưng giả sử dùng $\tau_q^2=0{,}01$ (giá trị sàn ở mục 7.3) thì $w_q\approx0{,}32$. Còn với $\tau_q^2=0{,}2193$ (khoảng 80 đến 160 ở đời 10) thì $w_q\approx0{,}02$. Ví dụ này cho thấy $w_q$ nhạy với $\tau_q^2$ thế nào khi $E$ cố định.

---

## 7. Ước lượng $\tau_q^2$

### 7.1 Suy ra: phương pháp moment

Phương pháp moment (phương pháp moment này là cách ước một tham số bằng cách viết trung bình lý thuyết của một đại lượng quan sát được theo tham số đó, rồi cho nó bằng trung bình đo được) dùng ở đây với đại lượng $(G-q)^2$. Giá trị thật $V$ không biết, nhưng nó triệt tiêu trong hiệu: $G-q=e_G-e_q$. Với hai sai số không lệch, hiệp phương sai $c$:
$$\mathbb{E}\big[(G-q)^2\big]=E+\tau_q^2-2c.$$
Mã giả sử $c=0$ và đảo lại:
$$\tau_q^2\approx\text{trung bình}\big[(G-q)^2\big]-\text{trung bình}\big[E\big],$$
lấy trung bình trên mọi node sống đã search thuộc cùng một khoảng cách tới cuối ván. Chia theo khoảng cách vì sai số của mạng phụ thuộc mạnh vào khoảng cách đó: gần cuối ván mạng thấy được kết quả, xa cuối ván thì không.

**Ví dụ với ba node trong cùng một khoảng** (số giả định để thấy phép tính):

| Node | $G$ | $q$ | $(G-q)^2$ | $E$ |
|---|---|---|---|---|
| 1 | +1,00 | +0,70 | 0,090 | 0,010 |
| 2 | 0,00 | +0,20 | 0,040 | 0,020 |
| 3 | $-1{,}00$ | $-0{,}50$ | 0,250 | 0,030 |

Trung bình $(G-q)^2$ là 0,127, trung bình $E$ là 0,020, nên $\tau_q^2\approx0{,}107$.

### 7.2 Chỗ giả định bị lung lay: phép trừ có thể ra âm

Phép ước bằng $\tau_q^2-2c+(E_{\text{mã}}-E_{\text{thật}})$ ở dạng trung bình, nên nó nhỏ hơn $\tau_q^2$ thật khi:

- **$c>0$.** Mạng được huấn luyện từ các nhãn chứa $G$ của chính cây, nên chỗ $G$ lệch thì $q$ cũng dễ lệch cùng chiều.
- **$E$ của mã lớn hơn $E$ thật.** Mục 4.4 cho thấy điều này xảy ra ở xa cuối ván.

Khi hai phần này lớn hơn $\tau_q^2$ thật thì phép ước ra âm, và mã chặn ở sàn 0,01. Số đo thật (log `tau_theo_cach` mỗi đời):

| Cách cuối ván (nửa nước) | 0–5 | 5–10 | 10–20 | 20–40 | 40–80 | 80–160 | từ 160 |
|---|---|---|---|---|---|---|---|
| $\tau_q^2$ đời 6 | 0,012 | 0,043 | 0,067 | 0,121 | 0,218 | 0,276 | **0,010** |
| $\tau_q^2$ đời 9 | 0,017 | 0,045 | 0,060 | 0,096 | 0,171 | 0,238 | **0,010** |
| $\tau_q^2$ đời 10 | 0,017 | 0,045 | 0,058 | 0,086 | 0,151 | 0,219 | 0,032 |
| $E$ trung bình (cây sau đời 10) | 0,003 | 0,006 | 0,011 | 0,021 | 0,048 | 0,107 | 0,305 |
| $w_q$ trung bình (đời 10) | 0,10 | 0,10 | 0,12 | 0,16 | 0,19 | 0,25 | 0,73 |

Sai số của mạng tăng đều theo khoảng cách rồi rơi đột ngột ở khoảng cuối, đúng nơi $E$ lớn nhất. Ở đời 6, 8 và 9 phép ước của khoảng cuối âm và chạm sàn. Với sàn đó, $w_q$ trung bình của khoảng cuối là khoảng 0,86. Khoảng cuối chiếm 4,6% số node, và 27% số node đó là khai cuộc (trước nửa nước 40). Vậy ở các node đó nhãn value gần như là $q$ của chính mạng.

### 7.3 Phần đặt tay

Ba quy tắc sau không suy ra từ đâu cả:

- Các mốc khoảng cách 0, 5, 10, 20, 40, 80, 160 được chọn để mỗi khoảng có đủ node và để khoảng rộng dần khi xa cuối ván. Hệ quả là $\tau_q^2$ nhảy bậc giữa hai khoảng thay vì đổi trơn.
- Sàn 0,01 chỉ để phép ước âm không làm $w_q$ vượt quá 1.
- Khoảng có ít hơn 1000 node thì dùng giá trị của khoảng gần cuối ván hơn.

**Hướng sửa có cơ sở (chưa làm, tài liệu thiết kế mục 16).** Sửa gốc là làm $E$ không ước cao, ví dụ trừ phần nhiễu của $Q$ khỏi $\omega^2(s)$, hoặc chặn $E$ bởi độ dao động tối đa của kết quả ván. Sửa nhẹ là thay các khoảng bậc thang và sàn bằng một hàm trơn, luôn dương, tăng dần theo khoảng cách $c$, ví dụ $\tau_q^2(c)=a+b\left(1-e^{-c/L}\right)$, với $a$, $b$, $L$ khớp từ cây.

---

## 8. Chọn dữ liệu: cắt, làm cũ, rẽ, search lại

### 8.1 Làm cũ bằng chứng: $\gamma=1-1/W$ (suy ra) và $W=4$ (đặt tay)

**Yêu cầu.** Mỗi đời, mọi $m$, $k$ và các tổng của search bị nhân cùng một hệ số $\gamma$, và muốn tổng trọng lượng một ván nhận qua mọi đời bằng $W$, như một mẫu của cách truyền thống được học trong cửa sổ $W$ đời.

**Suy ra.** Một ván có trọng lượng 1 ở đời nó được chơi, $\gamma$ ở đời sau, $\gamma^2$ ở đời sau nữa, và cứ thế. Tổng là chuỗi hình học
$$1+\gamma+\gamma^2+\dots=\frac{1}{1-\gamma}.$$
Cho tổng bằng $W$ thì $\gamma=1-1/W$.

**Ví dụ.** $W=4$ cho $\gamma=0{,}75$, và trọng lượng một ván qua các đời là 1; 0,75; 0,5625; 0,4219; … cộng lại đúng bằng 4.

$W=4$ là con số chủ dự án chọn để giống cửa sổ 4 đời của cách truyền thống; nó không được suy ra là tốt nhất.

### 8.2 Cắt lá có $m$ nhỏ nhất (lập luận, không tối ưu hoá)

Mỗi đời cây được cắt về đúng tổng số node mới của $W$ đời gần nhất, bằng cách lặp lại việc bỏ lá có $m$ nhỏ nhất. Một lá thường là node cuối của đúng một ván, nên $m$ của nó bằng $\gamma^{\text{số đời kể từ ván đó}}$ (ví dụ, lá của ván chơi 1 đời trước có $m=0{,}75$, lá của ván chơi 4 đời trước có $m=0{,}75^4\approx0{,}32$). Vì vậy cắt lá có $m$ nhỏ nhất gần như là cắt lá cũ nhất trước, giống cửa sổ trượt của cách truyền thống. Đây là một lập luận "giống cách truyền thống", không phải lời giải của một bài toán tối ưu.

### 8.3 Quét điểm rẽ với temperature $T=0{,}5$ (đặt tay)

**Quy tắc.** Đầu mỗi đời, mỗi node sống đã search bốc một nước theo xác suất
$$\Pr(a)=\frac{n(a)^{1/T}}{\sum_{j\in A(s)}n(j)^{1/T}}.$$
Với $T=0{,}5$ thì $1/T=2$, nên xác suất tỉ lệ với bình phương số lượt thăm. Nếu nước bốc được chưa từng chơi tại node, cặp (node, nước) thành một điểm rẽ (điểm rẽ này là chỗ một ván mới sẽ tách ra khỏi cây).

**Ví dụ trên node ví dụ.** Bình phương của 0,70; 0,25; 0,05 là 0,49; 0,0625; 0,0025, tổng 0,555, nên xác suất bốc là 0,883; 0,113; 0,0045.

1. Nếu chỉ $a_1$ đã chơi, xác suất node này thành điểm rẽ là $1-0{,}883\approx0{,}117$.
2. Với node ví dụ thật ($a_1$ và $a_2$ đã chơi), xác suất chỉ còn 0,0045 (chỉ khi bốc trúng $a_3$).

Như vậy node mà search phân vân (lượt thăm dàn đều) dễ thành điểm rẽ, còn nước rất ít lượt thăm hầu như không được thử. $T=0{,}5$ là lựa chọn của chủ dự án; không có phép suy ra nào nói nó tốt nhất.

### 8.4 Khoá $-\ln(u)/m^2$: phần suy ra và phần đặt tay

**Phần suy ra.** Bước quét thường cho nhiều điểm rẽ hơn ngân sách chơi được, nên phải chọn. Mỗi điểm rẽ $i$ có một trọng số $w_i>0$; nhận khoá $X_i=-\ln(u_i)/w_i$ với $u_i$ bốc đều trong $(0,1)$; rồi chơi theo khoá tăng dần. Thứ tự này đúng bằng phép bốc không lặp với xác suất tỉ lệ với $w$. Lý do gồm ba bước:

1. $X_i$ có phân phối mũ với tham số $w_i$, vì $\Pr(X_i>x)=\Pr\big(u_i<e^{-w_ix}\big)=e^{-w_ix}$.
2. Với các biến mũ độc lập, xác suất $X_i$ nhỏ nhất bằng $w_i/\sum_jw_j$. Đây là tính chất chuẩn của phân phối mũ, suy ra bằng tích phân $\int_0^\infty w_ie^{-w_ix}\prod_{j\ne i}e^{-w_jx}\,dx=w_i/\sum_jw_j$.
3. Phân phối mũ không có trí nhớ (tính không trí nhớ này nghĩa là biết $X_j>x$ rồi thì phần dư $X_j-x$ vẫn có đúng phân phối mũ cũ), nên sau khi bỏ điểm nhỏ nhất, thứ tự của các điểm còn lại lại là một lần bốc theo $w$ trên các điểm còn lại.

**Ví dụ.** Ba điểm rẽ có $m=1$, 2 và 4.

- Với $w=m$, xác suất mỗi điểm đứng đầu là $1/7$, $2/7$ và $4/7$, tức 0,143; 0,286; 0,571.
- Với $w=m^2$, xác suất là $1/21$, $4/21$ và $16/21$, tức 0,048; 0,190; 0,762.

Một mô phỏng 200 nghìn lần với $w=m^2$ cho 0,048; 0,191; 0,761, khớp với tính toán.

**Phần đặt tay.** Phép bốc theo $w$ là đúng, nhưng chọn $w=m^2$ thay vì $m$ hay $m^3$ là một quyết định. Mô phỏng trên cây thật cho số node mới trước nửa nước 40 mỗi đời: 3,5 nghìn nếu bốc đều, 16,6 nghìn với $m$, 25,6 nghìn với $m^2$ và 28,0 nghìn với $m^3$. Số mũ 2 được chọn vì lợi thêm sau đó rất ít; đó vẫn là một núm vặn.

### 8.5 Ưu tiên search lại: phần $1/(k+1)$ suy ra được, trần 20% đặt tay

**Vì sao cần search lại.** Ván rẽ chỉ search từ điểm rẽ trở đi, nên các node gần gốc giữ số liệu search của mạng cũ và nhiễu Dirichlet của một vài lần search. Search lại (search lại này là chạy thêm một lần search tại một node đã có, bằng mạng hiện tại, rồi cộng kết quả vào trung bình của node) sửa hai việc đó.

**Suy ra phần $1/(k+1)$.** Node đã có trung bình của $k$ lần search (tính theo trọng số đã làm cũ), với nhãn policy $\pi_{\text{cũ}}$. Một lần search mới cho $\pi_{\text{mới}}$ và được cộng với trọng số 1, nên nhãn mới là
$$\frac{k\,\pi_{\text{cũ}}+\pi_{\text{mới}}}{k+1}=\pi_{\text{cũ}}+\frac{\pi_{\text{mới}}-\pi_{\text{cũ}}}{k+1}.$$
Nhãn chỉ dịch một phần $1/(k+1)$ của độ chênh. Ví dụ, nước $a_1$ có $\pi_{\text{cũ}}=0{,}70$ và lần search mới cho 0,50:

1. Nếu $k=1$, nhãn mới là $(0{,}70+0{,}50)/2=0{,}60$, dịch 0,10.
2. Nếu $k=3$, nhãn mới là $(3\times0{,}70+0{,}50)/4=0{,}65$, dịch 0,05.

**Ghép thành ưu tiên.** Gọi $\hat\Delta(\text{tuổi},k)$ là độ chênh trung bình giữa $\pi_{\text{mới}}$ và $\pi_{\text{cũ}}$, đo từ các lần search lại trước đó và tra theo tuổi của nhãn và theo $k$ (bảng ước lượng từ dữ liệu). Trong mã, các ô của bảng có ít hơn 30 lần đo thì dùng giá trị mặc định $(\text{tuổi}+1)$ nhân một hệ số chuẩn hoá. Nhãn của node được học với tần suất tỉ lệ với $m$ (mục 9 nói rõ phần này đã đổi). Nếu thiệt hại của một nhãn sai được đo bằng (tần suất học) × (độ sai), và mọi lần search lại tốn như nhau, thì lần search lại có lợi nhất là lần làm giảm tích đó nhiều nhất:
$$\text{ưu tiên}(s)=m(s)\times\frac{\hat\Delta\big(\text{tuổi}(s),k(s)\big)}{k(s)+1}.$$
Phần $1/(k+1)$ suy ra chặt. Hai chỗ còn là giả định: đo thiệt hại bằng tích tuyến tính đó, và dùng $m$ làm tần suất học trong khi từ lần chạy 4 mỗi node chỉ được học một lần (mục 9).

**Phần đặt tay.** Mã lấy các node có ưu tiên cao nhất cho tới khi dùng 20% ngân sách của đời, và bỏ qua node đã có $k\ge m$ mà tuổi dưới 1. Con số 20% do chủ dự án chốt (5/11), không suy ra từ đâu.

### 8.6 Lập việc theo ngân sách (đặt tay)

Mỗi việc search lại được tính chi phí 490 lần chạy mạng (số lần chạy mạng trung bình mỗi lần search, đo ở đời 0). Mỗi ván rẽ được ước chi phí $(\text{cách cuối}+1)\times490$, với "cách cuối" là khoảng cách tới cuối ván của đường đang có dưới node. Danh sách được lập dư 1,5 lần ngân sách vì ước chi phí ván rẽ còn thô; máy Colab tự dừng khi thật sự hết ngân sách. Cả hai con số là quy ước vận hành, không ảnh hưởng tới nhãn.

---

## 9. Học từ cây

**Nhãn policy.** Nhãn policy của một node là trung bình $\pi$ của các lần search tại node, với các lần cũ đã nhân $\gamma$. Lấy trung bình nhiều lần search độc lập làm giảm phần nhiễu Dirichlet. Đây là một lựa chọn hợp lý, không phải lời giải tối ưu. Nhãn policy "mới" của tài liệu thiết kế (mục 7) có suy ra riêng nhưng đang tắt, vì mô phỏng cho thấy nó có hại khi $E$ sai.

**Mỗi node học một lần.** Từ lần chạy 4, mỗi node sống đã search được bốc với cùng xác suất khi học. Trước đó node được bốc theo $m$, nên node gần gốc bị học lại rất nhiều lần, và cả cây chỉ tương đương khoảng 39 nghìn mẫu độc lập. Quy tắc mới được chọn qua phép thử 12/11: AUC tăng từ 0,80 lên 0,845. Không có phép suy ra nào nói học đều là tốt nhất; mục 16.1 của tài liệu thiết kế đề xuất một nguyên lý thay thế (học theo xác suất mạng hiện tại đi tới node).

**Số bước học.** Số bước là số lớn hơn giữa số bước của cách truyền thống ở cùng đời và số mẫu chia 1024 (batch 1024), để mọi node được học ít nhất một lần mỗi đời. Đây là quyết định của chủ dự án ngày 14/11, không phải phép suy ra.
