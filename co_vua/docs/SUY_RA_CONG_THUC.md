# Các công thức của cách cây trò chơi được suy ra thế nào

Viết ngày 15/11/2026, bổ sung 18/11 và 19/11. Tài liệu được đối chiếu với mã đang chạy trong `co_vua/scripts/cv/cay.py` (lần chạy 5). Lịch sử các quyết định nằm ở tài liệu thiết kế `THIET_KE_CO_VUA.md`. Tài liệu này làm hai việc:

1. Với mỗi công thức hay quy tắc đang chạy, nói rõ mã làm gì từng bước, công thức được **suy ra** từ đâu hay được **ước lượng** từ dữ liệu hay chỉ được **đặt tay**, và nó dựa vào loại giả định nào (mục 1.1).
2. Ghi một phương pháp mới (mục 12), trong đó nhãn value và nhãn policy là định lý chứ không dựa vào giả định. Ván rẽ bốc nước theo tỉ lệ lượt thăm, nên trung bình của nhãn tính được chính xác, và mạng chỉ còn làm biến kiểm soát. Phương pháp đề xuất ngày 19/11 và chưa viết mã.

**Cách đọc.**

- **Phần A, phương pháp đang chạy:**
  - mục 1 là bảng tổng hợp và tiêu chí phân loại giả định;
  - mục 2 mô tả cây, các số mỗi node lưu, và thứ tự các bước trong một đời;
  - các mục 3 đến 9 đi qua từng công thức theo đúng thứ tự mã tính.
- **Phần B, phương pháp thay thế và nền toán của nó:**
  - mục 10 suy ra nhãn policy mới của tài liệu thiết kế (đang tắt);
  - mục 11 là khung định lý theo kiểu Gumbel AlphaZero;
  - mục 12 là phương pháp mới: nhãn value không lệch và nhãn policy cải thiện chắc chắn, chỉ với một điều kiện thiết kế là bốc nước theo phân phối đã biết. Mục này viết đủ chi tiết để làm theo.

---

## 1. Bảng tổng hợp

### 1.1 Ba loại giả định

Mỗi công thức có thể dựa vào một trong ba loại điều kiện. Cách chia này do chủ dự án đặt ra ngày 19/11.

- **Loại X: không có giả định.** Đây là toán thuần, ví dụ chuỗi hình học, hoặc một điều đúng theo cách chính mình xây hệ thống, ví dụ hai nhánh do hai nhóm ván khác nhau chơi ra thì độc lập.
- **Loại T: giả định trên đại lượng tính được.** Đại lượng tính được là thứ mã đọc hoặc tính ra được: số lượt thăm, $\pi$, $Q$, $q$, $G$, kết quả ván $z$, số ván $m$.
  - Những đại lượng này ngẫu nhiên vì chính quy trình của mình: nhiễu Dirichlet, bước quét, khoá rẽ nhánh, nước đi trong ván.
  - Một giả định về **phân phối** của chúng thuộc loại T, kể cả khi nó so với giá trị thật $V$. Ví dụ: "trung bình của $G$ qua nhiều lần lặp quy trình bằng $V$", hay "$q$ sai không quá $\varepsilon$".
  - $V$ là một con số xác định, đo được bằng cách chơi thêm nhiều ván. Vì vậy giả định loại T kiểm được, bằng dữ liệu có sẵn hoặc bằng thí nghiệm chơi thêm ván.
- **Loại K: mô hình lý tưởng đặt lên chính đại lượng không tính được.** Cụ thể là coi các giá trị thật $V$, vốn là những số cố định chưa biết, như thể chúng được bốc ngẫu nhiên từ một phân phối ("ngẫu nhiên, độc lập, trung bình 0, phương sai $\omega^2$"). Loại này không kiểm được, vì mỗi thế cờ chỉ có đúng một giá trị thật, không có lần lặp nào để so.

Chủ dự án chấp nhận loại X và T. Loại K bị coi là xa vời. Hai nhãn của phương pháp ở mục 12 chỉ dựa vào loại X: điều kiện duy nhất là cách bốc nước do chính mã đặt ra.

Chấp nhận được không có nghĩa là đúng. Một giả định loại T vẫn có thể sai. Lợi thế của nó là cái sai đó tìm ra được, bằng phân tích quy trình hoặc bằng đo. Trong phương pháp đang chạy, **chỉ G2 là loại K**. Một số giả định loại T thì đã biết là sai, hoặc chưa được kiểm (bảng 1.2).

### 1.2 Bảng các công thức

| Nhóm | Công thức hay quy tắc | Loại giả định | Mục |
|---|---|---|---|
| **Suy ra từ giả định** | Giá trị tổng hợp $G$, trung bình có trọng số $\rho$ của các nhánh con | Công thức tính được; lý do chọn $\rho$ là K | 3 |
| | Độ sai $E=\sum\rho^2E+\omega^2U$ | K: G2. T: G1, phần "$G$ không lệch", **đã biết là sai** (mục 4.1) | 4 |
| | Trọng số nhánh $\rho$ (bộ trọng số làm $E$ nhỏ nhất) | K, qua $E$ | 5 |
| | Tỉ lệ trộn nhãn value $w_q=E/(E+\tau_q^2)$ | T: $q$ và $G$ không lệch ($G$ không lệch đã sai), $c=0$ (đáng ngờ). Dùng $E$, nên kéo theo G2 | 6 |
| | Phép ước $\tau_q^2$ bằng trung bình $(G-q)^2-E$ (phương pháp moment) | T: như dòng trên, cộng "$E$ đúng" (sai ở xa cuối ván) | 7 |
| | Hệ số làm cũ $\gamma=1-1/W$ | X | 8.1 |
| | Khoá $-\ln(u)/w$ cho phép bốc không lặp tỉ lệ với $w$ | X | 8.4 |
| | Phần $1/(k+1)$ trong ưu tiên search lại | X | 8.5 |
| **Ước lượng từ dữ liệu** | Độ toả $\omega^2(s)$ từ $Q$ của search | T: độ toả của $Q$ ước được độ toả của giá trị thật; **đã biết là ước cao** | 4.3 |
| | $\tau_q^2$ của từng khoảng cách tới cuối ván | T: mọi node trong một khoảng có cùng sai số của mạng (chưa kiểm) | 7 |
| | Bảng $\hat\Delta$ (nhãn policy lệch bao nhiêu theo tuổi và số lần search) | T: độ chênh đã đo dự báo được độ chênh lần sau | 8.5 |
| **Đặt tay hoặc chọn qua thử** | Temperature quét $T=0{,}5$ | Lựa chọn | 8.3 |
| | Số mũ khoá điểm rẽ $m^2$ (chọn qua mô phỏng) | Lựa chọn | 8.4 |
| | $W=4$ đời (giống cửa sổ của cách truyền thống) | Lựa chọn | 8.1 |
| | Cắt lá có $m$ nhỏ nhất | Lựa chọn | 8.2 |
| | Trần search lại 20% ngân sách | Lựa chọn | 8.5 |
| | Mỗi node học một lần; số bước ít nhất bằng số mẫu chia 1024 | Lựa chọn | 9 |
| | Các mốc khoảng cách của $\tau_q^2$; sàn 0,01; khoảng ít hơn 1000 node mượn khoảng gần cuối hơn | Lựa chọn | 7.3 |
| | Ước chi phí ván rẽ $(\text{cách cuối}+1)\times490$, lập dư 1,5 lần | Lựa chọn | 8.6 |
| | Nhãn policy là trung bình $\pi$ các lần search | T: các lần search là mẫu nhiễu của cùng một phân phối | 9 |

Mã còn vài chặn số rất nhỏ, ví dụ $10^{-12}$ ở mẫu số và $10^{-6}$ cho $\omega^2$. Chúng chỉ để tránh chia cho 0 và không ảnh hưởng tới kết quả.

"Suy ra" nghĩa là công thức đúng **nếu** các giả định đúng. Hai chỗ đã bị số đo thật làm lung lay. Cả hai là giả định loại T, và đều đã thấy là sai:

- **$\omega^2(s)$ được coi là đo đúng độ toả của giá trị thật.** Thực tế nó bị ước cao vì $Q$ có nhiễu, nên $E$ ở xa cuối ván bị ước cao (mục 4.4).
- **Sai số của $q$ được coi là độc lập với sai số của $G$.** Thực tế mạng được học từ chính các nhãn chứa $G$, nên hai sai số có thể cùng chiều (mục 7.2).

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

### 2.1 Mã lưu cụ thể những gì

**Mỗi nước của một node** (vùng "pool" trong mã) lưu ba tổng, cộng dồn qua mọi lần search tại node:

- `ns`: tổng số lượt thăm $n(a)$.
- `nq`: tổng của $n(a)\times Q(sa)$.
- `nd`: tổng của $n(a)\times d(sa)$, với $d$ là xác suất hoà mà search đánh giá.

Từ ba tổng đó, mã tính:

- $\pi(a)=\texttt{ns}(a)/\sum_b\texttt{ns}(b)$;
- $Q(sa)=\texttt{nq}/\texttt{ns}$;
- $d(sa)=\texttt{nd}/\texttt{ns}$.

Vậy khi node được search nhiều lần, $\pi$ là trung bình **theo số lượt thăm** của các lần search, và $Q$ là trung bình của các lần, cân theo lượt thăm.

**Mỗi node** lưu:

- `cha`, `nuoc`, `sau`: node cha, nước dẫn tới node, và độ sâu tính từ thế khởi đầu. Độ sâu lẻ nghĩa là Đen đi.
- `trang`: trạng thái của node. 0 là đang sống. 1 là "gốc cắt": node đã bị cắt, nhưng còn giữ $G$, $E$, $m$ để node cha dùng. 2 là đã xoá.
- `het`, `z`: `het` bằng 0 nếu ván chưa kết thúc ở node này. Bằng 1 nếu ván kết thúc theo luật cờ, khi đó `z` là kết quả theo góc Trắng. Bằng 2 nếu ván bị dừng vì chạm độ dài tối đa của engine, khi đó ván **tính là hoà**.
- `m`: số ván đã đi qua node, mỗi ván cộng 1 cho mọi node trên đường đi của nó.
- `k`: số lần search tại node.
- `gsum`: tổng số thứ tự đời của các lần search. Tuổi của nhãn policy là đời hiện tại trừ $\texttt{gsum}/k$.
- `Gw`, `Gd`, `Gl`, `E`: giá trị tổng hợp dưới dạng xác suất thắng, hoà, thua theo góc Trắng, và độ sai của nó.
- `cach`: khoảng cách tới cuối ván (mục 7.1).
- `mau_tep`, `mau_hang`: chỗ lưu mặt phẳng đầu vào của thế cờ, dùng khi huấn luyện.

Mỗi đời, `m`, `k`, `gsum` và ba tổng của pool đều bị nhân với $\gamma$ (mục 8.1).

### 2.2 Một đời diễn ra theo thứ tự nào

1. **Máy Colab làm việc của đời.** Mỗi việc thuộc một trong hai kiểu.
   - **Ván rẽ**: chơi từ một điểm rẽ tới hết ván. Mỗi nước search khoảng 800 lượt thăm, có nhiễu Dirichlet ở gốc, rồi đi nước nhiều lượt thăm nhất.
   - **Search lại**: search thêm một lần tại một node đã có.
2. **Gộp vào cây** (`cap_nhat`, hàm `nap_lan`).
   - Với một ván: đi theo đường từ gốc tới điểm rẽ, rồi theo các nước của ván, tạo node mới khi cần. Cộng lần search của từng nước vào node tương ứng. Đánh dấu node cuối là node kết thúc. Cộng 1 vào $m$ của mọi node trên đường.
   - Với một lần search lại: trước khi cộng, đo độ chênh giữa $\pi$ cũ và $\pi$ mới (mục 8.5).
3. **Tính từ dưới lên** (hàm `tinh`): tính $\omega^2$, $\rho$, $G$, $E$ và khoảng cách tới cuối ván cho mọi node sống chưa kết thúc. Mục 3 đến 5 và 7.1.
4. **Lập nhãn** (hàm `nhan`): ước $\tau_q^2$ theo khoảng cách, tính $w_q$, rồi tính nhãn value và nhãn policy cho mọi node được học. Mục 6, 7, 9.
5. **Huấn luyện mạng** trên máy T4.
6. **Chuẩn bị đời sau** (`sau_hl`):
   1. Nhân $\gamma$.
   2. Cắt lá có $m$ nhỏ nhất cho tới khi cây còn đúng số node mới của 4 đời gần nhất.
   3. Quét điểm rẽ, xếp thứ tự bằng khoá.
   4. Chọn node để search lại.
   5. Lập danh sách việc theo ngân sách. Mục 8.

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

**Mã làm gì, từng bước** (hàm `tinh`):

1. **Node kết thúc:** $G$ là bộ ba có một số 1. Trắng thắng cho $(1,0,0)$, hoà cho $(0,1,0)$, Đen thắng cho $(0,0,1)$. Ván bị dừng vì quá dài cũng cho $(0,1,0)$. Ở những node này $E=0$.
2. **Node gốc cắt** (mục 8.2): giữ nguyên $G$ và $E$ đã tính lúc bị cắt, không tính lại.
3. **Các node còn lại:** đi từ độ sâu lớn nhất lên gốc. Ở mỗi độ sâu, mọi node sống, chưa kết thúc và có con đã chơi được tính cùng lúc: $G$ là tổng $\rho\times G(\text{con})$, tính cho từng thành phần thắng, hoà, thua.

**Loại giả định.** Bản thân công thức $G$ chỉ dùng số tính được. Giả định nằm ở câu "$G$ ước lượng tốt $V$ với $\rho$ này". Câu đó dựa vào mục 4 và 5: G1 là loại T, đã biết là sai; G2 là loại K.

---

## 4. Độ sai $E$ của $G$

### 4.1 Định nghĩa và các giả định

$E(s)$ là sai số bình phương trung bình của $G(s)$ so với $V(s)$, tức trung bình của $\big(G(s)-V(s)\big)^2$ nếu cùng một quá trình sinh ván được lặp lại nhiều lần. Ở node kết thúc ván, $E=0$ vì phán quyết của luật cờ không sai.

Phép suy ra dùng hai giả định.

- **Giả định G1.** Mỗi $G(sa)$ bằng $V(sa)$ cộng một sai số $e_a$ có trung bình 0 và phương sai $E(sa)$, và sai số của các nhánh khác nhau độc lập với nhau. Giả định này hợp lý khi các nhánh do các ván khác nhau chơi ra sau chỗ tách.
- **Giả định G2.** Giá trị thật của các nước con dao động quanh một mức chung: $V(sa)=\bar V+\delta_a$, với các $\delta_a$ độc lập, trung bình 0, phương sai $\omega^2(s)$, và độc lập với các $e_a$. Ta không biết các $\delta_a$, nên coi chúng là ngẫu nhiên; $\omega^2(s)$ là độ toả (độ toả này là phương sai của giá trị thật giữa các nước đi từ cùng thế cờ $s$).

**Tách G1 và G2 theo ba loại giả định của mục 1.1.**

| Mảnh | Loại | Vì sao |
|---|---|---|
| Sai số của các nhánh khác nhau độc lập với nhau | X | Sau chỗ tách, mỗi nhánh do những ván riêng chơi ra, với số ngẫu nhiên riêng |
| $\rho$ không phụ thuộc kết quả ván | X | $\rho$ chỉ tính từ $\pi$, $Q$ và $E$, mà $E$ cũng không dùng kết quả ván |
| $G(sa)$ không lệch: trung bình qua nhiều lần lặp quy trình bằng $V(sa)$ | T, **sai** với quy trình hiện tại | Xem đoạn ngay dưới bảng |
| Phương sai của $G(sa)$ bằng $E(sa)$ | Định nghĩa | $E$ được định nghĩa là sai số bình phương trung bình. Công thức để tính $E$ thì dựa vào G2 |
| Giá trị thật của các nước là ngẫu nhiên với phương sai $\omega^2$ (G2) | K | Giá trị thật là số cố định. G2 coi phần gộp lệch $\sum(\rho-\pi)V$, vốn là một độ lệch cố định, như nhiễu có trung bình 0 |

**Vì sao mảnh "không lệch" của G1 là loại T, và vì sao nó sai.**

- **Nó đặt lên đại lượng tính được.** Câu này nói về phân phối của $G(sa)$, một đại lượng mã tính ra. Sự ngẫu nhiên của $G(sa)$ đến từ chính quy trình sinh ván. $V(sa)$ chỉ là con số mà trung bình được so với, và con số đó đo được bằng cách chơi thêm nhiều ván từ $sa$. Vậy câu này kiểm được.
- **Nhưng với quy trình đang chạy, nó sai.** Phân tích quy trình là đủ để thấy điều này, không cần đo, như ví dụ dưới đây. Nó còn bị phá bởi các ván do mạng đời trước chơi. G2 là thứ che chỗ sai đó: G2 coi độ lệch cố định như nhiễu có trung bình 0.

Ví dụ ở node $sa$ có các con đều là node kết thúc:

1. $b_1$ có $\pi=0{,}7$, đã chơi, ván hoà ($z=0$). $b_2$ có $\pi=0{,}2$, đã chơi, Trắng thắng ($z=+1$). $b_3$ có $\pi=0{,}1$, chưa chơi, và giả sử giá trị thật là $-1$.
2. Node con kết thúc có $E=0$, nên $f=1$, và $\rho=\pi+\nu$ với $\nu=0{,}1/2=0{,}05$. Vậy $\rho$ là 0,75 và 0,25.
3. $G(sa)=0{,}25$, trong khi $V(sa)=0{,}7\times0+0{,}2\times1+0{,}1\times(-1)=0{,}1$.
4. Sai số là $+0{,}15$, và lần nào cây có đúng hình dạng này thì sai số cũng là $+0{,}15$.

Nước chưa chơi thường là nước ít lượt thăm, tức nước kém đối với bên đang đi. Bỏ chúng ra khỏi phép gộp nên có xu hướng làm $G$ nghiêng có lợi cho bên đang đi. Đây là suy luận, chưa đo.

Ở tầng thấp nhất, nếu mọi nước có $\pi>0$ đều đã chơi thì $\rho=\pi$, nên $G$ đúng bằng $V$ và mảnh này đúng.

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

**Mã tính $U$ thế nào.** Mã không duyệt từng nước chưa chơi. Nó tính $\sum_{A(s)}\pi_a^2$ một lần cho mỗi node (biến `pi2`), rồi viết
$$U(s)=\sum_{a\in C(s)}(\rho_a-\pi_a)^2+\Big(\sum_{a\in A(s)}\pi_a^2-\sum_{a\in C(s)}\pi_a^2\Big).$$
Con đã chơi gồm cả node con đang sống lẫn node con gốc cắt. Node con gốc cắt dùng $E$ đã lưu lúc bị cắt.

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

**Trong mã:**

- $Q$ là giá trị theo góc bên đang đi, và $\pi$ tính trên mọi nước có trong pool của node. Nước có 0 lượt thăm có $\pi=0$, nên không góp gì.
- Kết quả bị chặn dưới ở $10^{-6}$, để $f=\omega^2/(\omega^2+E)$ ở mục 5 không bằng 0 khi mọi $Q$ bằng nhau.

**Loại giả định: T, và đã biết là sai theo hướng ước cao.** Câu "độ toả của các $Q$ ước được độ toả của các giá trị thật" nói về $Q$, một đại lượng tính được. Nó kiểm được bằng cách chơi thêm ván từ các node con. Mục 4.4 cho thấy nó ước cao.

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

**Trong mã.** Ở mỗi độ sâu, mã tính cho mọi cặp (node cha, node con đã chơi) cùng lúc:

1. $f=\omega^2/(\omega^2+E_{\text{con}})$.
2. Hai tổng theo node cha: $A=\sum\pi f$ và $B=\sum f$.
3. $\nu=(1-A)/B$.
4. $\rho=(\pi+\nu)f$.

Ở đây $\pi$ là tỉ lệ lượt thăm của nước dẫn tới node con, đọc từ pool của node cha.

**Loại giả định: K**, vì bài toán cực tiểu dùng hàm $E$ của mục 4, mà hàm đó đến từ G2.

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

### 6.3 Từ $w_q$ tới nhãn mà mạng học (hàm `nhan`)

1. **$q$ và $d$ của node** là $Q$ và $d$ của nước có nhiều lượt thăm nhất. Nếu hai nước bằng lượt thì lấy nước đứng sau trong pool. Cả hai theo góc bên đang đi.
2. **Đổi $q$, $d$ sang bộ ba thắng, hoà, thua theo góc bên đang đi:** $\big((1+q-d)/2,\ d,\ (1-q-d)/2\big)$, mỗi số được chặn trong khoảng từ 0 đến 1.
3. **Đổi $G$ sang góc bên đang đi:** nếu Đen đi thì đổi chỗ thắng và thua.
4. **Nhãn value** là $w_q\times(\text{bộ ba của }q)+(1-w_q)\times(\text{bộ ba của }G)$.
5. **Node được học** là node đang sống, đã được search, chưa kết thúc ván, và còn mặt phẳng đầu vào.

**Loại giả định: T.** Phép gộp theo nghịch đảo phương sai cần hai điều về $q$ và $G$, cả hai đều tính được:

- $q$ và $G$ không lệch. Riêng "$G$ không lệch" đã biết là sai (mục 4.1).
- Sai số của $q$ và của $G$ độc lập ($c=0$). Điều này đáng ngờ (mục 7.2).

Ngoài ra $w_q$ dùng $E$, mà công thức của $E$ dựa vào G2 (loại K).

---

## 7. Ước lượng $\tau_q^2$

### 7.1 Suy ra: phương pháp moment

Phương pháp moment (phương pháp moment này là cách ước một tham số bằng cách viết trung bình lý thuyết của một đại lượng quan sát được theo tham số đó, rồi cho nó bằng trung bình đo được) dùng ở đây với đại lượng $(G-q)^2$. Giá trị thật $V$ không biết, nhưng nó triệt tiêu trong hiệu: $G-q=e_G-e_q$. Với hai sai số không lệch, hiệp phương sai $c$:
$$\mathbb{E}\big[(G-q)^2\big]=E+\tau_q^2-2c.$$
Mã giả sử $c=0$ và đảo lại:
$$\tau_q^2\approx\text{trung bình}\big[(G-q)^2\big]-\text{trung bình}\big[E\big],$$
lấy trung bình trên mọi node sống đã search thuộc cùng một khoảng cách tới cuối ván. Chia theo khoảng cách vì sai số của mạng phụ thuộc mạnh vào khoảng cách đó: gần cuối ván mạng thấy được kết quả, xa cuối ván thì không.

**Khoảng cách tới cuối ván trong mã** (biến `cach`, tính trong hàm `tinh`):

- Ở node kết thúc, `cach` bằng 0.
- Ở node khác, `cach` bằng `cach` của node con đã chơi có $\pi$ lớn nhất, cộng 1.

Vậy đây là độ dài của đường đi theo nước được search ưa nhất trong số các nước đã chơi. Nó không phải đường ngắn nhất, cũng không phải trung bình các đường.

**Từng bước ước $\tau_q^2$:**

1. Với mỗi node được học, lấy số một chiều $G_s=G_{\text{thắng}}-G_{\text{thua}}$ (góc Trắng) và $q$ đổi sang góc Trắng.
2. Tính $(G_s-q)^2-E$.
3. Chia node theo khoảng `cach`: $[0,5)$, $[5,10)$, $[10,20)$, $[20,40)$, $[40,80)$, $[80,160)$, $[160,\infty)$.
4. Khoảng có ít nhất 1000 node thì $\tau_q^2$ là trung bình của các số ở bước 2, chặn dưới ở 0,01. Khoảng ít node hơn thì dùng $\tau_q^2$ của khoảng ngay trước nó, tức khoảng gần cuối ván hơn.
5. $w_q$ của mỗi node dùng $\tau_q^2$ của khoảng chứa node đó.

**Loại giả định: T.** Phép ước cần bốn điều:

- $q$ và $G$ không lệch.
- $c=0$.
- $E$ do mã tính là đúng. Điều này sai ở xa cuối ván, và công thức của $E$ dựa vào G2.
- Mạng sai như nhau ở mọi node trong cùng một khoảng, vì cả khoảng dùng chung một $\tau_q^2$. Điều này chưa kiểm.

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

**Trong mã** (hàm `cat_la`). Lá là node đang sống không có node con đang sống. Mã lặp lại các bước sau:

1. Lấy lá có $m$ nhỏ nhất.
2. Đổi lá đó thành node gốc cắt: bỏ số liệu search của nó và bỏ mặt phẳng đầu vào, nên nó không còn được học. Nhưng nó giữ $m$, $G$, $E$ để node cha vẫn tính được.
3. Xoá các node con gốc cắt của nó.
4. Nếu node cha không còn node con đang sống thì node cha thành lá mới.

Mã dừng khi số node sống bằng tổng số node mới của 4 đời gần nhất. Gốc cây không bao giờ bị cắt.

### 8.3 Quét điểm rẽ với temperature $T=0{,}5$ (đặt tay)

**Quy tắc.** Đầu mỗi đời, mỗi node sống đã search bốc một nước theo xác suất
$$\Pr(a)=\frac{n(a)^{1/T}}{\sum_{j\in A(s)}n(j)^{1/T}}.$$
Với $T=0{,}5$ thì $1/T=2$, nên xác suất tỉ lệ với bình phương số lượt thăm. Nếu nước bốc được chưa từng chơi tại node, cặp (node, nước) thành một điểm rẽ (điểm rẽ này là chỗ một ván mới sẽ tách ra khỏi cây).

**Ví dụ trên node ví dụ.** Bình phương của 0,70; 0,25; 0,05 là 0,49; 0,0625; 0,0025, tổng 0,555, nên xác suất bốc là 0,883; 0,113; 0,0045.

1. Nếu chỉ $a_1$ đã chơi, xác suất node này thành điểm rẽ là $1-0{,}883\approx0{,}117$.
2. Với node ví dụ thật ($a_1$ và $a_2$ đã chơi), xác suất chỉ còn 0,0045 (chỉ khi bốc trúng $a_3$).

Mã quét mọi node đang sống, chưa kết thúc và đã được search, mỗi node một lần mỗi đời, mỗi node bốc đúng một nước. Phép bốc dùng số ngẫu nhiên của chính mã, nên xác suất mỗi node thành điểm rẽ là biết trước (loại X).

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

**Bảng $\hat\Delta$ được đo thế nào.**

1. Mỗi lần search lại, trước khi cộng lần mới vào node, mã đo độ chênh giữa $\pi$ cũ và $\pi$ mới bằng $\tfrac12\sum_a|\pi_{\text{cũ}}(a)-\pi_{\text{mới}}(a)|$. Con số này là phần xác suất phải dời chỗ để biến $\pi$ cũ thành $\pi$ mới: bằng 0 khi hai bên giống nhau, bằng 1 khi hai bên không chung nước nào.
2. Lần đo được xếp vào ô (tuổi, $k$). Cả tuổi lẫn $k$ được làm tròn xuống, và mọi giá trị từ 9 trở lên gộp chung vào ô 9.
3. Ô nào có ít nhất 30 lần đo thì dùng trung bình của ô đó.
4. Ô ít lần đo hơn dùng giá trị mặc định $(\text{tuổi}+1)\times\bar\Delta/2{,}5$, với $\bar\Delta$ là trung bình của các ô đã đủ lần đo.

**Loại giả định: T.** Bảng dùng độ chênh đã đo để dự báo độ chênh của lần search lại sau. Cả hai đều là đại lượng tính được, nên điều này kiểm được từ log.

### 8.6 Lập việc theo ngân sách (đặt tay)

Mỗi việc search lại được tính chi phí 490 lần chạy mạng (số lần chạy mạng trung bình mỗi lần search, đo ở đời 0). Mỗi ván rẽ được ước chi phí $(\text{cách cuối}+1)\times490$, với "cách cuối" là khoảng cách tới cuối ván của đường đang có dưới node. Danh sách được lập dư 1,5 lần ngân sách vì ước chi phí ván rẽ còn thô; máy Colab tự dừng khi thật sự hết ngân sách. Cả hai con số là quy ước vận hành, không ảnh hưởng tới nhãn.

---

## 9. Học từ cây

**Nhãn policy.** Nhãn policy của một node là trung bình $\pi$ của các lần search tại node, với các lần cũ đã nhân $\gamma$. Lấy trung bình nhiều lần search độc lập làm giảm phần nhiễu Dirichlet. Đây là một lựa chọn hợp lý, không phải lời giải tối ưu.

Nói chính xác, nhãn là $\texttt{ns}(a)/\sum_b\texttt{ns}(b)$ (mục 2.1), tức trung bình các lần search **cân theo số lượt thăm**. Vì mỗi lần search có số lượt thăm gần như nhau, kết quả gần bằng trung bình thường. Khi gửi lên máy huấn luyện, nhãn được lưu dưới dạng số nguyên 16 bit, với tổng mỗi node đúng 65535. Sai số mỗi số nhỏ hơn 1/65535.

**Loại giả định: T.** Lấy trung bình chỉ có lợi nếu các lần search là những mẫu nhiễu của cùng một phân phối.

- Nhiễu Dirichlet do mã tạo và độc lập giữa các lần, nên phần này đúng theo cách xây.
- Các lần search cũ dùng mạng cũ, nên chúng không cùng phân phối với lần mới. $\gamma$ làm lần cũ nhẹ đi nhưng không loại bỏ chỗ khác này. Nhãn policy "mới" của tài liệu thiết kế (mục 7) có suy ra riêng (mục 10 dưới đây) nhưng đang tắt, vì mô phỏng cho thấy nó có hại khi $E$ sai.

**Mỗi node học một lần.** Từ lần chạy 4, mỗi node sống đã search được bốc với cùng xác suất khi học. Trước đó node được bốc theo $m$, nên node gần gốc bị học lại rất nhiều lần, và cả cây chỉ tương đương khoảng 39 nghìn mẫu độc lập. Quy tắc mới được chọn qua phép thử 12/11: AUC tăng từ 0,80 lên 0,845. Không có phép suy ra nào nói học đều là tốt nhất; mục 16.1 của tài liệu thiết kế đề xuất một nguyên lý thay thế (học theo xác suất mạng hiện tại đi tới node).

**Số bước học.** Số bước là số lớn hơn giữa số bước của cách truyền thống ở cùng đời và số mẫu chia 1024 (batch 1024), để mọi node được học ít nhất một lần mỗi đời. Đây là quyết định của chủ dự án ngày 14/11, không phải phép suy ra.

---

## 10. Nhãn policy mới của tài liệu thiết kế (mục 7, đang tắt): suy ra và điều nó bảo đảm

Viết ngày 18/11. Nhãn này đang tắt trong lần chạy 5, nhưng nó có phép suy ra riêng nên ghi lại ở đây. Ký hiệu như mục 7 của tài liệu thiết kế: $n(a)$, $\pi(a)=n(a)/N$, $Q(sa)$, $P(a)$ là prior đã trộn nhiễu, $P_0$ là tổng prior của các nước không được thăm, $c$ là hệ số khám phá (cpuct) và $Q'(sa)$ là giá trị đã sửa về phía kết quả ván.

### 10.1 Dựng lại prior từ trạng thái cân bằng của PUCT

Search chọn mỗi lượt thăm bằng nước có điểm lớn nhất, với điểm là $Q(sa)+c\,P(a)\sqrt N/(1+n(a))$. Sau nhiều lượt, mọi nước được thăm có điểm gần bằng một mức chung $\beta$, vì nước nào điểm cao hơn mức chung sẽ được thăm tiếp tới khi điểm tụt xuống. Thay $n(a)\approx N\pi(a)$ và đặt $\lambda=c/\sqrt N$:
$$Q(sa)+\frac{\lambda P(a)}{\pi(a)}=\beta\quad\Longrightarrow\quad\pi(a)=\frac{\lambda P(a)}{\beta-Q(sa)}.$$
Cộng hai vế của $\pi(a)\big(\beta-Q(sa)\big)=\lambda P(a)$ trên mọi nước được thăm, với $\sum\pi=1$ và $\sum_{A(s)}P=1-P_0$, ta được
$$\beta=\sum_{a\in A(s)}\pi(a)Q(sa)+\lambda(1-P_0).$$
Mã không dùng thẳng $\lambda P(a)$. Nó dựng lại $w_a=\pi(a)\big(\beta-Q(sa)\big)$ từ $\pi$ và $Q$ đã lưu, nên đẳng thức $\pi(a)=w_a/(\beta-Q(sa))$ đúng tuyệt đối chứ không chỉ gần đúng. Phép cân bằng ở trên chỉ dùng để chọn $\beta$.

### 10.2 Nhãn là nghiệm của một bài toán tối ưu có điều chuẩn

Đặt $\tilde P(a)=w_a/\lambda$ (prior ngầm, tức prior mà nếu search dùng thì sẽ cho đúng $\pi$ đã lưu). Xét bài toán chọn một phân phối $y$ trên $A(s)$:
$$\max_y\;\Big(\sum_a y_a x_a+\lambda\sum_a\tilde P(a)\ln y_a\Big)\quad\text{với}\quad\sum_a y_a=1.$$
Số hạng đầu là giá trị kỳ vọng nếu bốc nước theo $y$, với $x_a$ là giá trị của nước $a$. Số hạng sau phạt $y$ khi nó xa prior. Nó bằng $-\lambda\,\mathrm{KL}(\tilde P\,\|\,y)$ cộng một hằng số. KL là độ lệch Kullback–Leibler, một số không âm đo hai phân phối khác nhau bao nhiêu.

Nhân tử Lagrange cho $x_a+\lambda\tilde P(a)/y_a=\alpha$, nên
$$y_a=\frac{\lambda\tilde P(a)}{\alpha-x_a}=\frac{w_a}{\alpha-x_a},$$
với $\alpha$ chọn sao cho tổng bằng 1. Hàm mục tiêu lõm chặt (tổng của hàm tuyến tính và các $\ln$ có hệ số dương), nên nghiệm là duy nhất. Từ đó có hai kết quả:

- Với $x=Q$, nghiệm là $\pi$, với $\alpha=\beta$.
- Với $x=Q'$, nghiệm là nhãn mới $\pi'$, với $\alpha=\beta'$, đúng như bước 5 và 6 của mục 7.

Vậy nhãn policy mới là **phân phối mà search sẽ cho ra nếu giá trị các nước là $Q'$ thay vì $Q$**, hiểu theo nghĩa chính xác là nghiệm của bài toán trên. Dạng nghiệm này là của Grill và cộng sự (ICML 2020), những người chỉ ra rằng tỉ lệ lượt thăm của AlphaZero bám theo nghiệm của bài toán đó.

### 10.3 Điều nhãn bảo đảm: dịch về phía nước được sửa tăng

**Mệnh đề.** $\sum_a\big(\pi'(a)-\pi(a)\big)\big(Q'(sa)-Q(sa)\big)\ge0$.

**Chứng minh.** Gọi hàm mục tiêu là $y\cdot x-R(y)$, với $R(y)=-\lambda\sum\tilde P\ln y$. $\pi$ là nghiệm khi $x=Q$, nên nó không thua $\pi'$: $\pi\cdot Q-R(\pi)\ge\pi'\cdot Q-R(\pi')$. $\pi'$ là nghiệm khi $x=Q'$, nên $\pi'\cdot Q'-R(\pi')\ge\pi\cdot Q'-R(\pi)$. Cộng hai bất đẳng thức, $R$ triệt tiêu, còn lại $(\pi'-\pi)\cdot(Q'-Q)\ge0$.

**Ví dụ (số của mục 7 tài liệu thiết kế, cột ít bằng chứng).** $Q$ là 0,10; 0,08; 0. $Q'$ là 0,092; 0,094; 0. $\pi$ là 0,70; 0,25; 0,05. $\pi'$ là 0,59; 0,36; 0,05. Tổng là $(-0{,}11)(-0{,}008)+(0{,}11)(0{,}014)+0\approx0{,}0024\ge0$.

### 10.4 Điều nhãn không bảo đảm: tốt hơn $\pi$ theo chính giá trị đã sửa

Nhãn này **không** bảo đảm $\sum\pi'Q'\ge\sum\pi Q'$. Nó chỉ bảo đảm tốt hơn prior ngầm. Lý do: thay $y=\tilde P$ vào bài toán thì số hạng KL bằng 0, nên $\pi'\cdot Q'\ge\tilde P\cdot Q'+\lambda\,\mathrm{KL}(\tilde P\|\pi')\ge\tilde P\cdot Q'$.

**Phản ví dụ.** Lấy hai nước với $w=0{,}05$ mỗi nước, $Q$ là 1 và 0, còn $Q'$ là 0,1 và 0.

1. Với $Q$: $\beta\approx1{,}0525$, nên $\pi\approx(0{,}952;\;0{,}048)$.
2. Với $Q'$: $\beta'\approx0{,}171$, nên $\pi'\approx(0{,}707;\;0{,}293)$.
3. Theo $Q'$, nước 1 vẫn tốt nhất, nhưng $\sum\pi Q'\approx0{,}095$ trong khi $\sum\pi'Q'\approx0{,}071$.

Nhãn mới kém hơn nhãn cũ theo chính giá trị đã sửa. Bằng lời: khi bằng chứng làm nước tốt nhất bớt nổi trội, nhãn bắt chước search và kéo xác suất về phía prior, kể cả khi nước đó vẫn tốt nhất.

**Phần mô hình.** Bước 1 và 2 của mục 7 (tính $Q'$ bằng cách co chênh lệch $d$ về phía $\delta$ với hệ số $\tau_d^2/(\tau_d^2+E)$) là phép gộp theo nghịch đảo phương sai, nên dựa vào cùng loại giả định G1, G2 như mục 4 và 6.

---

## 11. Khung chặt chẽ theo kiểu Gumbel AlphaZero (đề xuất 18/11, chưa chạy)

Các mục 3 đến 7 là **tầng mô hình**: công thức đúng nếu các giả định G1, G2 đúng, mà G2 là giả định mô hình (coi giá trị thật của các nước là ngẫu nhiên). Mục này dựng một khung mà mỗi kết quả là một định lý đúng tuyệt đối. Giả thiết duy nhất còn lại là **một con số đo được**: sai số tối đa $\varepsilon$ của $Q$ ở các chỗ cây chưa chơi. Đây đúng là mức chặt của Gumbel AlphaZero, vì định lý của bài đó cũng có giả thiết "$q$ đúng".

### 11.1 Gumbel AlphaZero chặt ở đâu

Bài "Policy improvement by planning with Gumbel" (Danihelka, Guez, Schrittwieser và Silver, ICLR 2022) có ba ý. Phần này ghi theo trí nhớ, nên tra lại bài gốc trước khi trích dẫn.

1. **Bốc nước bằng Gumbel.** Với $g(a)$ là các biến Gumbel độc lập ($g=-\ln(-\ln u)$, $u$ đều trong $(0,1)$), nước $\arg\max_a\big(g(a)+\text{logit}(a)\big)$ có đúng phân phối $\mathrm{softmax}(\text{logit})$. Lấy $k$ nước có $g+\text{logit}$ lớn nhất thì được một lần bốc $k$ nước không lặp. Khoá $-\ln(u)/m^2$ của mục 8.4 là cùng phép bốc này với $\text{logit}=2\ln m$, vì xếp $-\ln(u)/w$ tăng dần cũng là xếp $\ln w-\ln(-\ln u)$ giảm dần. Nhưng cây dùng phép bốc đó để chọn **điểm rẽ nào được chơi** (giữa các node, khi không đủ ngân sách), không phải để chọn **nước nào** tại một node. Nước tại node do bước quét $n(a)^{1/T}$ chọn (mục 8.3). Vì vậy định lý cải thiện ở ý 2 không áp dụng cho khoá này. Lịch sử của phần chọn điểm rẽ là: lần chạy 1 và 2 xáo đều, làm cây thiếu hẳn trung cuộc; lần chạy 3 và 4 dùng khoá $-\ln(u)/m$; từ lần chạy 5 dùng khoá $-\ln(u)/m^2$.
2. **Định lý cải thiện.** Bốc $k$ nước như trên, rồi chọn nước $A'$ làm $g+\text{logit}+\sigma(q)$ lớn nhất, với $\sigma$ là hàm tăng. Khi đó $\mathbb E[q(A')]\ge\sum_a\pi(a)q(a)$. **Chứng minh.** Cố định $g$, gọi $A$ là nước làm $g+\text{logit}$ lớn nhất. $A$ nằm trong $k$ nước đã bốc và có phân phối $\pi$. Vì $A'$ thắng $A$ khi cộng $\sigma(q)$, còn $A$ thắng $A'$ khi không cộng, trừ hai bất đẳng thức cho $\sigma(q(A'))\ge\sigma(q(A))$, nên $q(A')\ge q(A)$ với **mọi** $g$. Lấy trung bình hai vế là xong.
3. **Nhãn policy.** $\pi'=\mathrm{softmax}\big(\text{logit}+\sigma(\hat q)\big)$, với $\hat q$ là $q$ của nước đã thăm, còn nước chưa thăm dùng một giá trị thay thế. Nhãn này chắc chắn có $\sum\pi'\hat q\ge\sum\pi\hat q$ (bổ đề 11.5).

Cả ba kết quả đều đúng tuyệt đối, với giả thiết $q$ đúng. Bài không chứng minh rằng $q$ đúng, và cũng không chứng minh rằng mạng học được nhãn.

### 11.2 Định nghĩa giá trị thật

**Trò chơi.** Mỗi ván kết thúc sau hữu hạn nửa nước (luật hoà 50 nước và lặp thế cờ). Kết quả $z$ theo góc Trắng nằm trong khoảng từ $-1$ đến $+1$. Mỗi node là một thế cờ kèm cả đường đi tới nó (mục 2), nên kết quả ở node kết thúc được luật cờ xác định hoàn toàn.

**Chính sách.** Một chính sách $\mu$ gán cho mỗi thế cờ $s$ một phân phối $\mu(\cdot\,|\,s)$ trên các nước hợp lệ. Hai bên cùng chơi theo $\mu$.

**Giá trị thật.** $V^\mu(s)$ là trung bình của $z$ khi từ $s$ hai bên chơi theo $\mu$. Ván hữu hạn và $z$ bị chặn, nên $V^\mu(s)$ là một số xác định, tính được bằng quy nạp ngược từ các node kết thúc:
$$V^\mu(s)=z(s)\ \text{nếu }s\text{ kết thúc},\qquad V^\mu(s)=\sum_a\mu(a|s)\,V^\mu(sa)\ \text{nếu không}.$$

**Chọn $\mu$.** Bên trong cây, $\mu(\cdot|s)$ là $\pi$ đã lưu tại node, có thể mũ $1/T$ rồi chuẩn hoá (temperature $T$ của chính sách mục tiêu). Bên ngoài cây, $\mu$ là search của mạng đời hiện tại. Cách chọn này làm $V^\mu$ xác định ở mọi thế cờ. Mục 3 viết "mỗi nước bốc theo $\pi$" nhưng không nói $\pi$ ở thế cờ ngoài cây là gì. Đó là chỗ định nghĩa cũ còn hở.

**Ba đối tượng khác nhau.**

- $V^\mu(s)$ là một số cố định, không có gì ngẫu nhiên.
- Nhãn $Y(s)$ là thứ ta tính được từ cây.
- Sai số là $Y(s)-V^\mu(s)$.

"Độ tin cậy" là tính chất của nhãn, không phải của $V$. Trong khung này sai số bị chặn bằng một bất đẳng thức, không phải bằng một xác suất.

### 11.3 Định lý 1: mạng học trung bình của nhãn

**Định lý.** Với một thế cờ $s$ cố định và nhãn $y$ có trung bình $\bar y(s)$, với mọi giá trị dự đoán $v$:
$$\mathbb E\big[(v-y)^2\big]=\big(v-\bar y(s)\big)^2+\mathrm{Var}(y).$$
Vậy hàm mất mát bình phương nhỏ nhất khi $v=\bar y(s)$. Nếu $\bar y(s)=V^\mu(s)+b(s)$ thì đích học lệch đúng $b(s)$. Phương sai của nhãn chỉ cộng một hằng số: nó làm học chậm đi nhưng không đổi đích.

**Chứng minh.** Viết $v-y=(v-\bar y)+(\bar y-y)$ rồi bình phương. Số hạng chéo có trung bình 0 vì $\mathbb E[\bar y-y]=0$.

**Ví dụ.** Nhãn là $+1$, 0 hoặc $-1$ với xác suất 0,4; 0,4; 0,2. Trung bình là 0,2, phương sai là $0{,}6-0{,}04=0{,}56$. Mất mát là $(v-0{,}2)^2+0{,}56$, nhỏ nhất ở $v=0{,}2$.

Hệ quả: muốn mạng học đúng $V^\mu$ thì việc cần làm là **chặn độ lệch $b$**. Giảm phương sai là việc thứ hai.

### 11.4 Định lý 2: nhãn value kiểu tree backup và đẳng thức sai số

**Nhãn.** Gọi $C(s)$ là các nước đã chơi, $\hat Q(sa)$ là giá trị search của nước chưa chơi, theo góc Trắng. Tính từ cuối ván lên:
$$Y(s)=z(s)\ \text{nếu }s\text{ kết thúc},\qquad Y(s)=\sum_{a\in C(s)}\mu(a|s)\,Y(sa)+\sum_{a\notin C(s)}\mu(a|s)\,\hat Q(sa)\ \text{nếu không}.$$
Node gốc cắt (mục 8.2) giữ $Y$ và $P_{\text{ra}}$ đã tính lúc bị cắt, giống như mã hiện tại giữ $G$ và $E$. Đây là phép "tree backup" của Precup, Sutton và Singh (2000): trộn theo đúng $\mu$, nước nào đã chơi thì dùng cây, nước nào chưa chơi thì dùng mạng.

**Lối ra.** Lối ra (exit) là một cặp (node $s$ trong cây, nước $a$ chưa chơi). Đặt $P_\mu(s\to e)$ là xác suất đi từ $s$ tới lối ra $e$ khi chơi theo $\mu$, tức tích các $\mu$ dọc đường từ $s$ tới $e$.

**Định lý (đẳng thức, không cần giả định).**
$$Y(s)-V^\mu(s)=\sum_{e}P_\mu(s\to e)\,\big(\hat Q(e)-V^\mu(e)\big).$$
Do đó, nếu $|\hat Q(e)-V^\mu(e)|\le\varepsilon$ ở mọi lối ra thì
$$|Y(s)-V^\mu(s)|\le\varepsilon\,P_{\text{ra}}(s),\qquad P_{\text{ra}}(s)=\sum_eP_\mu(s\to e)\le1.$$

**Chứng minh.** Quy nạp từ cuối ván lên. Ở node kết thúc, $Y=z=V^\mu$, nên sai số bằng 0. Ở node khác, trừ công thức của $Y$ cho phương trình của $V^\mu$ ở 11.2:
$$Y(s)-V^\mu(s)=\sum_{a\notin C}\mu_a\big(\hat Q(sa)-V^\mu(sa)\big)+\sum_{a\in C}\mu_a\big(Y(sa)-V^\mu(sa)\big),$$
rồi thay giả thiết quy nạp vào tổng thứ hai.

Không có G1, G2, không có tính độc lập, không có xác suất. Ván do mạng đời nào chơi cũng không quan trọng, vì đẳng thức chỉ dùng kết quả ở node kết thúc, mà kết quả đó do luật cờ quyết định. $P_{\text{ra}}$ tính được chính xác trên cây: $P_{\text{ra}}=0$ ở node kết thúc, node gốc cắt giữ giá trị đã lưu, và $P_{\text{ra}}(s)=\sum_{a\notin C}\mu_a+\sum_{a\in C}\mu_aP_{\text{ra}}(sa)$.

**Ví dụ.** Node $s$ (Trắng đi) có $\mu=0{,}70;\ 0{,}25;\ 0{,}05$.

- Sau $a_1$, Đen có $b_1$ với $\mu=0{,}8$ đã chơi, ván hoà ngay ($z=0$), và $b_2$ với $\mu=0{,}2$ chưa chơi, $\hat Q=+0{,}2$.
- Sau $a_2$, Đen có $c_1$ với $\mu=0{,}6$, Trắng thắng ngay ($z=+1$), và $c_2$ với $\mu=0{,}4$, hoà ngay. Cả hai đã chơi.
- $a_3$ chưa chơi, $\hat Q=-0{,}30$.

1. $Y(sa_1)=0{,}8\times0+0{,}2\times0{,}2=0{,}04$, $Y(sa_2)=0{,}6\times1+0{,}4\times0=0{,}60$, nên $Y(s)=0{,}70\times0{,}04+0{,}25\times0{,}60+0{,}05\times(-0{,}30)=0{,}163$.
2. Hai lối ra có xác suất $0{,}70\times0{,}2=0{,}14$ và 0,05, nên $P_{\text{ra}}(s)=0{,}19$. Với $\varepsilon=0{,}3$, nhãn sai không quá $0{,}3\times0{,}19=0{,}057$.
3. Kiểm: giả sử giá trị thật ở hai lối ra là 0 và $-0{,}5$. Khi đó $V^\mu(s)=0{,}70\times0+0{,}25\times0{,}60+0{,}05\times(-0{,}5)=0{,}125$. Sai số $0{,}163-0{,}125=0{,}038$ bằng đúng $0{,}14\times(0{,}2-0)+0{,}05\times(-0{,}3+0{,}5)$.

**Cái giá.** Trên một đường không rẽ nhánh mà nước đã chơi có $\mu=0{,}7$ mỗi nửa nước, phần đi hết tới cuối ván sau 100 nửa nước là $0{,}7^{100}$, gần như 0. Khi đó $P_{\text{ra}}\approx1$, và nhãn gần như toàn là $\hat Q$ của các nước anh em gần $s$. Temperature $T$ của $\mu$ điều chỉnh việc này:

- $T$ nhỏ đưa $\mu$ dồn vào nước đã chơi, nên nhãn gần với kết quả ván $z$. Nhưng khi đó $V^\mu$ là giá trị của một người chơi gần như tất định.
- $T=1$ cho nhãn gần với $\hat Q$.

Chọn $T$ là chọn **học giá trị của chính sách nào**. Đây là quyết định về đích học, không phải một giả định về thế giới, và định lý đúng với mọi $T$.

### 11.5 Định lý 3: nhãn policy kiểu Gumbel và bảo đảm cải thiện

**Bổ đề (nghiêng theo hàm tăng).** Cho phân phối $\mu$, các số $x_a$ và hàm tăng $\sigma$. Đặt $\pi'(a)\propto\mu(a)\,e^{\sigma(x_a)}$. Khi đó $\sum\pi'x\ge\sum\mu x$.

**Chứng minh.** Đặt $f_a=e^{\sigma(x_a)}$, ta có $\sum\pi'x-\sum\mu x=\mathrm{Cov}_\mu(x,f)/\mathbb E_\mu[f]$. Hiệp phương sai viết được thành $\tfrac12\sum_{a,b}\mu_a\mu_b(x_a-x_b)(f_a-f_b)$. Mỗi số hạng không âm vì $f$ tăng theo $x$, nên $x_a-x_b$ và $f_a-f_b$ cùng dấu.

**Nhãn.** $\pi'(a)\propto\mu(a|s)\,e^{\sigma(x_a)}$, với $x_a=Y(sa)$ cho nước đã chơi và $x_a=\hat Q(sa)$ cho nước chưa chơi (theo góc bên đang đi). Mỗi nước có một cận sai số đã biết: $\varepsilon_a=\varepsilon P_{\text{ra}}(sa)$ cho nước đã chơi, $\varepsilon$ cho nước chưa chơi.

**Định lý.** Với $Q^\mu(s,a)=V^\mu(sa)$:
$$\sum_a\big(\pi'(a)-\mu(a)\big)Q^\mu(s,a)\;\ge\;g(s)=\sum_a\big(\pi'(a)-\mu(a)\big)x_a-\sum_a\big|\pi'(a)-\mu(a)\big|\,\varepsilon_a.$$

**Chứng minh.** Viết $Q^\mu=x+(Q^\mu-x)$, rồi chặn phần thứ hai bằng $|Q^\mu_a-x_a|\le\varepsilon_a$, theo Định lý 2.

**Dạng an toàn nhất.** Trong mọi $\pi'$, cái làm $g(s)$ lớn nhất có dạng đơn giản:

1. Gọi $b^*$ là nước có cận dưới $x_b-\varepsilon_b$ cao nhất.
2. Mọi nước có cận trên $x_a+\varepsilon_a$ thấp hơn cận dưới của $b^*$ bị bỏ, và xác suất của chúng dồn sang $b^*$.
3. Các nước còn lại giữ nguyên $\mu$.

Lý do: chuyển một lượng $\delta$ từ $a$ sang $b^*$ đổi $g$ một lượng $\delta\big[(x_{b^*}-\varepsilon_{b^*})-(x_a+\varepsilon_a)\big]$, và chuyển sang nước khác không lợi bằng chuyển sang $b^*$. Đây là quy tắc "chỉ đổi khi chắc chắn tốt hơn".

**Ví dụ trên cây ở 11.4**, với $\varepsilon=0{,}3$:

- $x$ là 0,04; 0,60; $-0{,}30$.
- Cận sai số là $0{,}3\times0{,}2=0{,}06$, 0 và 0,3.
- Ba khoảng là $[-0{,}02;\,0{,}10]$, $[0{,}60;\,0{,}60]$ và $[-0{,}60;\,0]$.

| Nhãn | $\pi'$ | $\sum(\pi'-\mu)x$ | Phần trừ | Bảo đảm $g(s)$ |
|---|---|---|---|---|
| Nghiêng kiểu Gumbel, $\sigma(x)=x/0{,}25$ | 0,229; 0,767; 0,004 | 0,305 | 0,042 | 0,263 |
| Dạng an toàn nhất | 0; 1; 0 | 0,437 | 0,057 | 0,380 |

Nhãn nghiêng mềm hơn và giữ lại thông tin về các nước khác. Dạng an toàn cho bảo đảm cao nhất nhưng là một nhãn cứng. Cả hai đều chắc chắn tốt hơn $\mu$ tại node này, miễn là cận $\varepsilon$ đúng.

### 11.6 Định lý 4: từ từng node tới arena

**Định lý (hiệu hiệu năng, dạng hai người chơi).** Cho Trắng chơi theo $\pi'$ và Đen chơi theo $\mu$. Gọi $J(\pi',\mu)$ là trung bình của $z$ khi đó. Khi đó
$$J(\pi',\mu)-V^\mu(s_0)=\mathbb E\Big[\sum_{t:\ \text{Trắng đi}}\ \sum_a\big(\pi'(a|s_t)-\mu(a|s_t)\big)Q^\mu(s_t,a)\Big],$$
với trung bình lấy trên các ván mà Trắng chơi $\pi'$ và Đen chơi $\mu$.

**Chứng minh.** Vì $V^\mu$ ở node kết thúc bằng $z$, ta có $z-V^\mu(s_0)=\sum_t\big(V^\mu(s_{t+1})-V^\mu(s_t)\big)$. Xét trung bình của số hạng thứ $t$ khi đã biết $s_t$:

- Ở nửa nước Đen đi, Đen chơi $\mu$, nên trung bình bằng 0 theo phương trình của $V^\mu$.
- Ở nửa nước Trắng đi, trung bình bằng $\sum_a\pi'(a|s_t)Q^\mu(s_t,a)-V^\mu(s_t)=\sum_a(\pi'-\mu)Q^\mu$.

Đổi màu cũng làm như vậy (với Đen, lợi thế tính theo $-Q^\mu$). Điểm arena của $\pi'$ là trung bình hai màu của $(1+z)/2$, theo góc bên chơi $\pi'$, nên
$$\text{điểm arena}(\pi'\text{ đấu }\mu)\;\ge\;\frac12+\frac14\,\mathbb E\Big[\sum_t g(s_t)\Big],$$
với $g=0$ ở các thế cờ ngoài cây (ở đó đặt $\pi'=\mu$). Nếu $g\ge0$ ở mọi node thì $\pi'$ đạt **ít nhất 50%** trước $\mu$.

### 11.7 Chuỗi bảo đảm và hai chỗ không thể là định lý

| Bước | Kết quả | Loại |
|---|---|---|
| Nhãn value $Y$ | Sai không quá $\varepsilon P_{\text{ra}}$ | Định lý 2, giả thiết duy nhất là $\varepsilon$ |
| Mạng học nhãn value | Đích học là trung bình của nhãn | Định lý 1 |
| Nhãn policy $\pi'$ | Tốt hơn $\mu$ tại node ít nhất $g(s)$ | Định lý 3, giả thiết $\varepsilon$ |
| Từ node tới cả ván | Điểm arena của $\pi'$ trước $\mu$ ít nhất $\tfrac12+\tfrac14\mathbb E\sum g$ | Định lý 4 |
| $\varepsilon$ có đúng không | Đo bằng thí nghiệm | Kiểm định thống kê |
| Mạng có học được $\pi'$ và $Y$ không | Đo bằng arena | Kiểm định thống kê |

**Chỗ thứ nhất: $\varepsilon$.** Không định lý nào cho biết mạng sai bao nhiêu ở thế cờ chưa chơi (ví dụ hai thế giới của nước $a_3$). Nhưng $\varepsilon$ đo được. Chọn ngẫu nhiên các lối ra, chơi từ mỗi lối ra $n$ ván theo $\mu$, rồi so trung bình với $\hat Q$. Bất đẳng thức Hoeffding cho khoảng tin cậy của trung bình, ví dụ $\pm0{,}27$ với 100 ván và $\pm0{,}009$ với 100 nghìn ván, gộp theo khoảng cách tới cuối ván.

**Chỗ thứ hai: mạng học.** Định lý "không có bữa trưa miễn phí" (No Free Lunch, Wolpert 1996) nói rằng không có bảo đảm nào cho việc mạng đoán đúng ở thế cờ chưa gặp nếu không giả định gì. Ngoài ra, arena đấu bằng search của mạng mới chứ không bằng chính $\pi'$, nên Định lý 4 nói về $\pi'$, không trực tiếp nói về mạng. Chỗ này chỉ kiểm định được, bằng arena.

### 11.8 So với công thức đang chạy, và việc cần làm trước khi dùng

- $G$, $E$, $\rho$ (mục 3 đến 5) và $w_q$ (mục 6) không có chỗ trong chuỗi định lý. Lý do là $\rho\ne\mu$ tạo ra phần gộp lệch $\sum(\rho-\mu)V$, mà phần này chỉ chặn được bằng mô hình G2 hoặc bằng cận rất thô $\|\rho-\mu\|_1$. Trong khung mới, chúng chỉ còn là một lựa chọn để giảm sai số. Một tổ hợp lồi (trung bình có trọng số không âm, tổng bằng 1) của các nhãn có cận sai số thì có cận bằng tổ hợp lồi của các cận. Vì vậy, nếu $q(s)$ cũng sai không quá $\varepsilon$, nhãn $w_q\,q+(1-w_q)\,Y$ sai không quá $w_q\varepsilon+(1-w_q)\varepsilon P_{\text{ra}}(s)$, với bất kỳ $w_q$ nào. Trộn như vậy vẫn giữ một bảo đảm, chỉ là bảo đảm yếu hơn của riêng $Y$.
- Vấn đề sàn của $\tau_q^2$ (mục 7.2) và $E$ ước cao (mục 4.4) biến mất, vì khung mới không dùng $\omega^2$, $E$, $\tau_q^2$.
- Rủi ro lớn nhất là nhãn gần như toàn $\hat Q$ ở xa cuối ván (11.4, phần cái giá). Lần chạy 1 đã thua vì nhãn value mềm theo mạng, nên temperature $T$ của $\mu$ phải được thử offline: đo $P_{\text{ra}}$ trung bình theo khoảng cách tới cuối ván trên cây thật với vài giá trị $T$ trước khi chọn.
- Định lý 2 cần biết $\mu$ ở mọi node trong cây. $\pi$ đã lưu có sẵn, nên không phải đổi gì ở phần chơi ván.
- Mục 12 thay khung này. Ở mục 12, sai số của mạng chỉ đi vào độ dao động của nhãn chứ không đi vào trung bình, nên cả nhãn value lẫn nhãn policy đều không cần cận $\varepsilon$.

---

## 12. Phương pháp mới: nhãn đúng theo cách xây (đề xuất 19/11, chưa viết mã, chưa thử)

Mục này thay toàn bộ phương pháp ở các mục 3 đến 7 và thay cả nhãn tree backup $Y$ của mục 11.4. Nó dùng thông tin từ các ván đã chơi trên cây để làm nhãn value và nhãn policy. Mỗi nhãn đi kèm một định lý đúng tuyệt đối.

### 12.1 Vì sao phải làm lại, và nguyên tắc mới

**Chỗ hỏng chung của các cách cũ.** Cả $G$ (mục 3 đến 7) lẫn $Y$ (mục 11.4) đều trộn đánh giá của mạng vào nhãn **như một số thay cho giá trị thật**. Khi đó sai số của mạng nằm luôn trong nhãn, và nó là sai số cố định, không có trung bình 0. Theo Định lý 1 (mục 11.3), mạng học trung bình của nhãn, nên sai số cố định đó trở thành đích học. Muốn chặn nó thì phải giả định về độ lớn của nó: G2 và $\omega^2$ ở cách đang chạy, $\varepsilon$ ở mục 11. Không có phép toán nào bỏ được giả định đó, vì nhãn thật sự phụ thuộc vào cái sai của mạng.

**Nguyên tắc mới: đặt mọi sự ngẫu nhiên vào tay mình.** Nếu mỗi nước trong ván được bốc từ một phân phối mà mã biết chính xác, thì trung bình của mọi đại lượng tính theo ván là một con số tính được bằng giải tích, giống như biết trước xác suất của một con xúc xắc do chính mình gieo. Khi đó "nhãn không lệch" không còn là giả định nữa mà là một định lý về cách bốc.

**Mạng chỉ còn là biến kiểm soát.** Biến kiểm soát (biến kiểm soát này là một đại lượng được trừ ra rồi cộng lại dưới dạng trung bình đã biết chính xác của nó, nên nó đổi độ dao động của nhãn mà không đổi trung bình) là vai trò duy nhất của mạng trong nhãn mới. Mạng tốt thì nhãn ít dao động. Mạng sai thì nhãn dao động nhiều hơn, nhưng **trung bình của nhãn vẫn đúng**. Như vậy sai số của mạng chỉ còn đi vào phần ngẫu nhiên, mà phần ngẫu nhiên thì triệt tiêu khi mạng học trên nhiều thế cờ.

**Chỗ duy nhất dùng thống kê.** Có đúng một hệ số $\kappa$ (12.3) cần ước từ dữ liệu. Ước nó sai chỉ làm nhãn dao động nhiều hơn, không bao giờ làm đích học lệch. Mọi phần khác là giải tích.

### 12.2 Điều kiện thiết kế: bốc nước theo phân phối đã biết

**Thay đổi duy nhất ở phần chơi.** Trong ván rẽ, sau nước rẽ, mỗi nước được **bốc ngẫu nhiên theo tỉ lệ lượt thăm** $\pi_t(a)=n_t(a)/N_t$ của chính lần search tại nước đó, thay vì đi nước nhiều lượt thăm nhất như hiện nay. Nhiễu Dirichlet ở gốc giữ nguyên; nó chỉ làm $\pi_t$ khác đi, và $\pi_t$ vẫn biết chính xác lúc bốc.

**Chính sách được đánh giá.** Gọi $\mu$ là chính sách "search bằng mạng đời hiện tại, rồi bốc nước theo tỉ lệ lượt thăm". $V^\mu(s)$ là kết quả trung bình (theo góc bên đang đi tại $s$) khi từ $s$ hai bên cùng chơi theo $\mu$, và $Q^\mu(s,a)$ là kết quả trung bình nếu đi $a$ trước rồi chơi theo $\mu$. Ván hữu hạn và kết quả bị chặn, nên đây là những con số xác định (mục 11.2). Ván chạm độ dài tối đa tính là hoà, như mã đang làm.

**Vì sao bốc theo $\pi$, tức temperature 1.** Search tính giá trị của một nước bằng trung bình các đánh giá bên dưới, **cân theo số lượt thăm**. Vậy giá trị mà search giả định cho một thế cờ là trung bình theo tỉ lệ lượt thăm, đúng là $V^\mu$. Nếu mạng học đúng $V^\mu$ thì các phép cộng dồn bên trong search nhất quán với chính mạng. Mọi định lý dưới đây vẫn đúng nếu thay $\pi$ bằng bất kỳ phân phối nào mã biết chính xác lúc bốc, ví dụ $\pi^{1/T}$ đã chuẩn hoá. Khi đó đích học đổi thành giá trị của chính phân phối đó. Chọn $T$ là chọn học giá trị của chính sách nào, không phải một giả định.

**Ván thuần.** Một ván là **ván thuần từ node $s$** nếu ván đi qua $s$ và mọi nước của nó từ $s$ trở đi đều được bốc theo $\pi$. Ván rẽ tại điểm rẽ $(b,a)$ là ván thuần từ mọi node nằm từ $ba$ trở xuống trên đường của nó, nhưng không thuần từ $b$, vì nước $a$ tại $b$ do bước quét chọn (mục 8.3) chứ không do $\pi$. Mỗi node trừ gốc có ít nhất một ván thuần, là ván đã tạo ra node đó.

**Dữ liệu cần có đều đã nằm trong bản ghi ván.** Với mỗi nước $t$ của một ván, bản ghi treeplay lưu lần search tại nước đó: số lượt thăm, $Q$ và xác suất hoà của từng nước được thăm. Từ đó có $\pi_t$, $\hat Q_t(a)$ (giá trị search của nước $a$, theo góc bên đang đi) và
$$\hat V_t=\sum_a\pi_t(a)\,\hat Q_t(a),$$
là đánh giá của search cho cả thế cờ, trộn theo đúng $\pi_t$. Nước được bốc $a_t$ luôn có $\pi_t(a_t)>0$, nên $\hat Q_t(a_t)$ luôn có.

### 12.3 Nhãn value

**Công thức.** Xét một ván thuần từ $s_t$, đi qua $s_t,s_{t+1},\dots,s_L$ với $s_L$ là node kết thúc. Mọi giá trị viết theo góc bên đang đi tại node của nó, nên giá trị của node con nhìn từ node cha phải đổi dấu. Tính từ cuối ván lên:
$$\hat Y_L=z_L,\qquad \hat Y_t=-\hat Y_{t+1}+\kappa\big(\hat V_t-\hat Q_t(a_t)\big),$$
với $z_L$ là kết quả theo góc bên đang đi tại $s_L$, và $\kappa$ là một hệ số cố định (bàn ở cuối mục này). Viết gọn lại:
$$\hat Y_t=z^{(t)}+\kappa\sum_{u\ge t}(-1)^{u-t}\big(\hat V_u-\hat Q_u(a_u)\big),$$
với $z^{(t)}$ là kết quả ván theo góc bên đang đi tại $s_t$.

**Đọc công thức.** $-\hat Y_{t+1}$ là bằng chứng của ván về **riêng nước $a_t$**. Số hạng $\hat V_t-\hat Q_t(a_t)$ là chỗ search cho biết trung bình các nước tốt hơn hay kém hơn nước $a_t$ bao nhiêu. Cộng nó vào là chuyển bằng chứng về một nước thành bằng chứng về cả thế cờ. Với $\kappa=0$ nhãn là kết quả ván $z$, đúng như AlphaZero.

**Định lý 5 (nhãn value không lệch, không cần giả định).** Với mọi $\kappa$ cố định và mọi mạng, dù mạng sai bao nhiêu:
$$\mathbb E\big[\hat Y_t\,\big|\,s_t\big]=V^\mu(s_t).$$

**Chứng minh.** Quy nạp từ cuối ván lên. Ở node kết thúc, $\hat Y_L=z_L=V^\mu(s_L)$. Ở node $s_t$, lấy trung bình theo hai bước.

1. Cố định lần search tại $s_t$ (tức $\pi_t$ và $\hat Q_t$) và nước $a_t$. Phần sau $s_{t+1}$ là một ván thuần, nên theo giả thiết quy nạp $\mathbb E[-\hat Y_{t+1}]=-V^\mu(s_{t+1})=Q^\mu(s_t,a_t)$.
2. Lấy trung bình theo phép bốc $a_t\sim\pi_t$. Vì $\hat Q_t$ đã tính xong trước khi bốc,
$$\mathbb E\big[\hat Q_t(a_t)\big]=\sum_a\pi_t(a)\hat Q_t(a)=\hat V_t,$$
nên số hạng $\kappa(\hat V_t-\hat Q_t(a_t))$ có trung bình đúng bằng 0, **bất kể $\hat Q_t$ đúng hay sai**.
3. Còn lại $\mathbb E[\hat Y_t]=\mathbb E\big[\sum_a\pi_t(a)Q^\mu(s_t,a)\big]$, và lấy trung bình theo lần search thì đây đúng là $V^\mu(s_t)$, vì $\mu$ chính là "search rồi bốc theo $\pi$".

Chỗ duy nhất dùng đến điều kiện thiết kế là bước 2: nước được bốc từ đúng phân phối $\pi_t$ đã biết.

**Ví dụ: mạng sai mà trung bình nhãn vẫn đúng.** Node $s$ có hai nước, $\pi=(0{,}5;\ 0{,}5)$. Cả hai node con kết thúc ván ngay: đi $a_1$ thì thắng ($+1$), đi $a_2$ thì thua ($-1$). Vậy $V^\mu(s)=0$. Mạng đánh giá sai: $\hat Q=(0{,}6;\ 0{,}2)$, nên $\hat V=0{,}4$. Lấy $\kappa=1$.

- Bốc trúng $a_1$: nhãn là $1+(0{,}4-0{,}6)=0{,}8$.
- Bốc trúng $a_2$: nhãn là $-1+(0{,}4-0{,}2)=-0{,}8$.
- Trung bình là 0, đúng bằng $V^\mu(s)$. Mạng nghĩ thế cờ đáng $+0{,}4$, nhưng điều đó không đi vào trung bình của nhãn.

So với nhãn tree backup $Y$ của mục 11.4 trên cùng node khi chưa nước nào được chơi: $Y=\hat V=0{,}4$, lệch $+0{,}4$ lần nào cũng như lần nào.

**Định lý 6 (sai số là tổng các bước có trung bình 0).** Gọi $A^\mu_u=Q^\mu(s_u,a_u)-V^\mu(s_u)$ là lợi thế thật của nước đã bốc, và $\hat A_u=\hat Q_u(a_u)-\hat V_u$ là lợi thế search đánh giá cho nó. Khi đó
$$\hat Y_t-V^\mu(s_t)=\sum_{u\ge t}(-1)^{u-t}\big(A^\mu_u-\kappa\hat A_u\big).$$
Mỗi số hạng có trung bình 0 khi biết mọi thứ trước nó, nên đây là tổng các bước của một martingale (martingale này là dãy mà bước tiếp theo luôn có trung bình 0 khi biết quá khứ).

**Chứng minh.** Vì $Q^\mu(s_u,a_u)=-V^\mu(s_{u+1})$, ta có $(-1)^{u-t}A^\mu_u=(-1)^{u+1-t}V^\mu(s_{u+1})-(-1)^{u-t}V^\mu(s_u)$. Cộng theo $u$ thì mọi số hạng giữa triệt tiêu, còn lại $(-1)^{L-t}V^\mu(s_L)-V^\mu(s_t)=z^{(t)}-V^\mu(s_t)$. Phần $\kappa C_t$ ở dưới bằng đúng $-\kappa\sum_u(-1)^{u-t}\hat A_u$.

Đọc định lý: với $\kappa=1$, nhãn chỉ sai ở chỗ search đánh giá sai **lợi thế của nước đã bốc so với trung bình**, và mỗi chỗ sai đó có trung bình 0. Với $\kappa=0$, nhãn sai bằng toàn bộ độ may rủi của ván. Bất đẳng thức Azuma–Hoeffding (một định lý cho tổng các bước martingale bị chặn) cho cận xác suất của sai số mà không cần giả định về phân phối.

**Chọn $\kappa$: chỗ duy nhất dùng thống kê, và nó không làm lệch đích.** Đặt $C_t=\sum_{u\ge t}(-1)^{u-t}(\hat V_u-\hat Q_u(a_u))$, nên $\hat Y_t=z^{(t)}+\kappa C_t$. Vì $C_t$ có trung bình 0, mọi $\kappa$ đều cho nhãn không lệch. Độ dao động nhỏ nhất khi
$$\kappa^*=-\frac{\mathrm{Cov}\big(z^{(t)},C_t\big)}{\mathrm{Var}(C_t)},$$
ước bằng hồi quy trên các ván thuần **của đời trước**. Dùng dữ liệu đời trước làm $\kappa$ cố định đối với các ván của đời này, nên Định lý 5 áp dụng nguyên vẹn. Nếu mạng đánh giá lợi thế tốt thì $\kappa^*$ gần 1. Nếu mạng vô dụng thì $\kappa^*$ gần 0 và nhãn trở về $z$. Trường hợp xấu nhất của phép ước là nhãn dao động hơn mức tốt nhất, không bao giờ là nhãn lệch.

**Dạng thắng, hoà, thua.** Mạng học bộ ba xác suất. Công thức giữ nguyên cho từng thành phần, với $z$ là bộ ba có một số 1 và $\hat Q$, $\hat V$ là bộ ba của search. Đổi góc nhìn là đổi chỗ thắng với thua. Từng thành phần của nhãn có thể ra ngoài khoảng từ 0 đến 1, nhưng tổng luôn bằng 1, và trung bình là bộ ba xác suất thật dưới $\mu$. Điều này không hại việc học. Với hàm mất mát cross-entropy trên softmax, đạo hàm theo logit là $p-y$, tuyến tính theo nhãn $y$, nên trung bình đạo hàm là $p-\mathbb E[y]$ và đích học vẫn là $\mathbb E[y]$. Nhãn phải lưu dưới dạng số thực có dấu.

**Node có nhiều ván thuần.** Nhãn của node là trung bình các $\hat Y$ của mọi ván thuần từ node đó. Trung bình của các nhãn không lệch vẫn không lệch, và dao động nhỏ đi.

### 12.4 Nhãn policy

**Công thức.** Tại node $s=s_t$ của một ván thuần, lần search cho $\pi$, $\hat Q$, $\hat V$, và nước đã bốc là $a^*=a_t$. Đặt
$$Z=-\hat Y_{t+1},\qquad D=Z-\hat Q(a^*).$$
$Z$ là bằng chứng của ván về nước $a^*$, theo góc bên đang đi tại $s$. Theo Định lý 5, $Z$ có trung bình $Q^\mu(s,a^*)$. $D$ là độ bất ngờ: kết quả của nước $a^*$ tốt hơn search nghĩ bao nhiêu. Nhãn policy là
$$\pi'(a)=\pi(a)\Big[1+\beta\big(\hat Q(a)-\hat V-D\big)\Big]+\beta\,D\cdot\mathbf 1[a=a^*],\qquad\beta=\tfrac12,$$
với $\mathbf 1[a=a^*]$ bằng 1 nếu $a$ là nước đã bốc và bằng 0 nếu không. Cộng lại theo $a$ thì được $1-\beta D+\beta D=1$, vì $\sum_a\pi(a)(\hat Q(a)-\hat V)=0$.

**Nhãn này đến từ đâu.** Có một ước lượng không lệch cho giá trị của **mọi** nước, kể cả nước không được bốc:
$$x_a=\hat Q(a)+\frac{\mathbf 1[a=a^*]}{\pi(a)}\big(Z-\hat Q(a)\big).$$
Lấy trung bình theo phép bốc: nước $a$ được bốc với xác suất $\pi(a)$, nên $\mathbb E[x_a]=\hat Q(a)+\pi(a)\cdot\frac{Q^\mu(s,a)-\hat Q(a)}{\pi(a)}=Q^\mu(s,a)$. Đây là phép cân theo nghịch đảo xác suất (importance weighting), và nó đúng vì xác suất bốc là do mã đặt ra. Nhãn policy là
$$\pi'=\pi+\beta\,\pi\odot\big(x-\bar x\big),\qquad\bar x=\sum_a\pi(a)x_a=\hat V+D,$$
với $\odot$ là nhân từng thành phần. Thay $x$ vào thì ra đúng công thức trên. Thừa số $1/\pi(a^*)$ bị nhân với $\pi(a^*)$ nên biến mất, vì vậy nhãn không phình to khi nước được bốc có ít lượt thăm.

**Định lý 7 (trung bình của nhãn policy).** Khi biết lần search tại $s$,
$$\mathbb E\big[\pi'(a)\big]=\pi(a)\Big[1+\beta\big(Q^\mu(s,a)-\bar Q\big)\Big],\qquad\bar Q=\sum_b\pi(b)\,Q^\mu(s,b).$$
**Chứng minh.** $\pi'$ là hàm bậc nhất của các $x_a$ (kể cả $\bar x$), và $\mathbb E[x_a]=Q^\mu(s,a)$. Trung bình của một hàm bậc nhất bằng hàm đó tại trung bình.

Vậy đích học của đầu policy là $\pi$ nghiêng theo **giá trị thật** $Q^\mu$, không phải theo $\hat Q$ của mạng. Mạng sai bao nhiêu cũng không đi vào đích này.

**Định lý 8 (cải thiện chắc chắn tại mọi thế cờ).** Gọi $\pi^*(s)=\mathbb E[\pi']$ là đích học của đầu policy và $\mu(s)=\mathbb E[\pi]$ là chính sách đã chơi, cả hai lấy trung bình theo cả lần search. Khi đó
$$\sum_a\big(\pi^*(a)-\mu(a)\big)Q^\mu(s,a)=\beta\,\mathbb E\Big[\sum_a\pi(a)\big(Q^\mu(s,a)-\bar Q\big)^2\Big]\;\ge\;0.$$
**Chứng minh.** Theo Định lý 7, vế trái bằng $\beta\,\mathbb E\big[\sum_a\pi(a)(Q^\mu_a-\bar Q)Q^\mu_a\big]$. Vì $\sum_a\pi(a)(Q^\mu_a-\bar Q)=0$, có thể trừ $\bar Q$ khỏi thừa số $Q^\mu_a$ cuối mà không đổi tổng, được tổng các bình phương.

Đại lượng trong ngoặc là phương sai của giá trị thật giữa các nước, theo trọng số $\pi$. Nó bằng 0 chỉ khi mọi nước được thăm có cùng giá trị thật, tức là khi không còn gì để cải thiện.

**Từ từng thế cờ tới arena.** Ghép Định lý 8 với Định lý 4 (mục 11.6), với $g(s)$ là vế trái của Định lý 8:
$$\text{điểm arena}(\pi^*\text{ đấu }\mu)\;\ge\;\frac12+\frac14\,\mathbb E\Big[\sum_tg(s_t)\Big]\;\ge\;\frac12.$$
Chuỗi này không có giả định nào về mạng hay về giá trị thật. Nó chỉ dùng điều kiện thiết kế của 12.2.

**Vì sao nhãn phải có dạng bậc nhất, và vì sao $\beta=\tfrac12$.** Ba bước, bước nào cũng là giải tích.

1. **Bậc nhất.** Phân phối của sai số trong $x$ phụ thuộc vào mạng và vào may rủi của ván, nên không biết trước. Muốn đích học không phụ thuộc vào phân phối đó thì cần $\mathbb E[f(x)]=f(\mathbb E[x])$ với **mọi** phân phối của $x$. Điều này đúng khi và chỉ khi $f$ là hàm bậc nhất (thử với phân phối hai điểm thì thấy $f$ phải vừa lồi vừa lõm). Nhãn nghiêng theo hàm mũ ở mục 11.5 không bậc nhất. Với nó, nước nào có ước lượng dao động nhiều thì dễ được ước cao nhất và được kéo lên quá mức. Đó là lý do mục 11.5 phải giả định cận $\varepsilon$.
2. **Hướng $\pi\odot(x-\bar x)$.** Đầu policy ra xác suất bằng softmax của các logit $\ell_a$. Đạo hàm của giá trị kỳ vọng $\sum_a\pi(a)Q_a$ theo $\ell_a$ là $\pi(a)(Q_a-\bar Q)$. Vậy nhãn là đúng một bước theo hướng tăng nhanh nhất của giá trị kỳ vọng, đo trong chính hệ toạ độ mà đầu policy dùng. Định lý 8 cho thấy bước này không bao giờ làm giảm giá trị.
3. **Độ dài bước $\beta$.** Mức cải thiện ở Định lý 8 tỉ lệ thuận với $\beta$, nên $\beta$ nên lớn nhất có thể, miễn là đích học vẫn là một phân phối xác suất với **mọi** bộ giá trị có thể có. Cần $1+\beta(Q^\mu_a-\bar Q)\ge0$, mà $Q^\mu_a-\bar Q$ có thể gần tới $-2$ (nước $a$ thua chắc, các nước khác thắng chắc). Vậy $\beta\le\tfrac12$, và lấy $\beta=\tfrac12$.

Viết theo điểm số $p_a=(1+Q^\mu_a)/2$ (thắng được 1, hoà được nửa, thua được 0), đích học là $\pi^*(a)=\mathbb E\big[\pi(a)\,(1+p_a-\bar p)\big]$: nước có điểm cao hơn trung bình bao nhiêu thì xác suất được nhân thêm đúng bấy nhiêu.

**Ví dụ (tiếp ví dụ ở 12.3).** $\pi=(0{,}5;\ 0{,}5)$, giá trị thật là $+1$ và $-1$, mạng đánh giá $\hat Q=(0{,}6;\ 0{,}2)$, $\hat V=0{,}4$. Hai node con kết thúc ván nên $Z$ là $+1$ hoặc $-1$.

| Nước được bốc | $Z$ | $D$ | $\pi'(a_1)$ | $\pi'(a_2)$ |
|---|---|---|---|---|
| $a_1$ | +1 | 0,4 | $0{,}5\times(1-0{,}1)+0{,}2=0{,}65$ | $0{,}5\times(1-0{,}3)=0{,}35$ |
| $a_2$ | $-1$ | $-1{,}2$ | $0{,}5\times(1+0{,}7)=0{,}85$ | $0{,}5\times(1+0{,}5)-0{,}6=0{,}15$ |
| Trung bình | | | 0,75 | 0,25 |

Định lý 7 cho $0{,}5\times(1+0{,}5\times1)=0{,}75$ và $0{,}5\times(1-0{,}5\times1)=0{,}25$, khớp. Mức cải thiện là $0{,}25\times1+(-0{,}25)\times(-1)=0{,}5$, bằng $\beta$ nhân phương sai (phương sai ở đây bằng 1). Mạng tưởng $a_2$ gần bằng $a_1$, nhưng điều đó không đi vào đích học.

**Ví dụ trên node ví dụ của mục 2.** $\pi$ là 0,70; 0,25; 0,05, $\hat Q$ là $+0{,}10$; $-0{,}05$; $-0{,}30$, nên $\hat V=0{,}0425$. Giả sử ván thuần bốc trúng $a_2$ và bằng chứng của ván về $a_2$ là $Z=+0{,}50$.

1. $D=0{,}50-(-0{,}05)=0{,}55$.
2. $\pi'(a_1)=0{,}70\times\big(1+0{,}5\times(0{,}10-0{,}0425-0{,}55)\big)\approx0{,}528$.
3. $\pi'(a_2)=0{,}25\times\big(1+0{,}5\times(-0{,}05-0{,}0425-0{,}55)\big)+0{,}5\times0{,}55\approx0{,}445$.
4. $\pi'(a_3)=0{,}05\times\big(1+0{,}5\times(-0{,}30-0{,}0425-0{,}55)\big)\approx0{,}028$.
5. Nhãn value với $\kappa=1$: $\hat Y=0{,}50+(0{,}0425+0{,}05)=0{,}5925$.

Đây là một lần bốc. Bảo đảm nói về trung bình qua các lần bốc, không nói về một nhãn riêng lẻ.

**Thành phần âm.** Một nhãn riêng lẻ có thể có thành phần âm, ví dụ khi nước được bốc có $\pi$ nhỏ mà $D$ âm lớn. Trung bình thì không âm (bước 3 ở trên). Như với nhãn value, đạo hàm của cross-entropy theo logit là $p-y$, tuyến tính theo $y$, nên mạng vẫn học đúng $\mathbb E[y]$. Nhãn phải lưu dưới dạng số thực có dấu, thay cho số nguyên 16 bit hiện nay.

**So với nhãn đang chạy.** Nhãn đang chạy là trung bình $\pi$, có trung bình đúng bằng $\mu$, nên mức cải thiện bằng 0: không hại, nhưng không dùng gì từ kết quả ván. Nhãn mới cộng thêm một phần cải thiện có bảo đảm, lấy từ kết quả ván.

**Node có nhiều ván thuần.** Nhãn là trung bình các $\pi'$. Node chỉ có lần search mà không có ván thuần đi tiếp (ví dụ search lại) thì nhãn là $\pi$. Không dùng nhãn nghiêng theo riêng $\hat Q$, vì khi không có $D$ thì sai số của mạng đi thẳng vào đích học.

### 12.5 Cây, ván rẽ và search lại trong phương pháp mới

**Nhãn tính theo từng ván, không theo cả cây.** Mọi thứ $\hat Y$ và $\pi'$ cần đều có trong bản ghi của chính ván đó. Vì vậy nhãn được tính một lần lúc nạp ván (hàm `nap_lan`), đi ngược từ cuối ván lên. Mỗi node lưu tổng các nhãn của những ván thuần đi qua nó và số ván thuần đó. Phép tính từ dưới lên trên cả cây ($G$, $E$, $\rho$, $\omega^2$) không còn cần.

**Cây còn giữ ba việc.**

- Chọn chỗ bắt đầu ván mới (quét điểm rẽ và khoá $-\ln(u)/m^2$), tức quyết định **thế cờ nào** có nhãn.
- Cho nhiều ván dùng chung một node, nên node gần gốc có nhiều ván thuần và nhãn ít dao động.
- Chọn node để học và để cắt.

**Điều kiện để chọn node mà không làm lệch nhãn.** Định lý 5 và 7 là trung bình **khi đã biết node được chọn**. Chúng vẫn đúng nếu quyết định giữ hay học một node chỉ dùng thông tin có trước phần ván thuần đi tiếp từ node đó: độ sâu, tuổi của node, số liệu ở các node cha. Nếu quy tắc nhìn vào chuyện xảy ra sau node, ví dụ kết quả ván, thì việc chọn có thể tương quan với kết quả và làm lệch nhãn.

- Học mỗi node một lần (mục 9) thoả điều kiện.
- Bước quét và khoá chọn điểm rẽ dựa vào số liệu tại điểm rẽ. Ván rẽ chỉ góp nhãn cho các node từ sau nước rẽ trở xuống, mà phần đó là ngẫu nhiên mới. Vậy hai bước này thoả điều kiện.
- Cắt lá có $m$ nhỏ nhất (mục 8.2) **gần** thoả. Với lá, $m$ chỉ phụ thuộc tuổi. Nhưng với node trong, $m$ đếm cả ván rẽ sinh ra bên dưới, mà việc sinh ra chúng phụ thuộc vào các lần search trong phần ván đi tiếp. Sửa cho chặt: cắt theo tuổi của ván thuần gần nhất đi qua node. Mục 8.2 đã cho thấy cắt theo $m$ vốn gần như là cắt theo tuổi.

**Search lại.** Một lần search lại cho $\pi$ mới nhưng không có ván đi tiếp, nên không đóng góp gì vào phần cải thiện của nhãn. Đề xuất: biến mỗi việc search lại thành "search lại tại node, rồi chơi tiếp một ván thuần tới hết". Việc này cho cả số liệu của mạng mới lẫn một mẫu không lệch, nhưng tốn một ván thay vì một lần search. Đây là quyết định về ngân sách, cần chủ dự án chốt.

### 12.6 Những chỗ còn lại không phải định lý

| Chỗ | Vì sao không là định lý được | Xử lý |
|---|---|---|
| Mạng có học được đích $V^\mu$ và $\pi^*$ không | Định lý "không có bữa trưa miễn phí": không có bảo đảm cho thế cờ chưa gặp nếu không giả định gì | Kiểm định bằng arena |
| Arena đấu bằng search của mạng mới, không bằng chính $\pi^*$ | Định lý 4 nói về $\pi^*$ | Kiểm định bằng arena |
| Ván của các đời mạng cũ | Ván do mạng đời $g$ chơi cho nhãn đúng với $\mu$ **của đời $g$**. Trộn các đời theo $\gamma$ cho đích là một trung bình của các $V^{\mu_g}$, và Định lý 8 đúng với từng đời so với chính sách của đời đó | Đo độ chênh giữa các đời bằng bảng $\hat\Delta$ (mục 8.5). Nếu chênh lớn thì giảm $W$ |
| Hệ số $\kappa$ | Ước từ dữ liệu | Chỉ đổi độ dao động, không đổi đích (12.3) |
| Chọn thế cờ: temperature quét, $m^2$, trần 20%, $W$, cắt lá | Quyết định **học ở đâu**, không phải học cái gì ở mỗi chỗ | Không đổi dấu của bảo đảm, chỉ đổi mức cải thiện. Kiểm bằng arena |

Hàng cuối đáng nói rõ. Theo Định lý 4, mức cải thiện của cả ván là tổng các $g(s_t)$ trên những thế cờ mà ván thật sự đi qua. Nhãn đúng ở một thế cờ không ai đi tới thì không giúp gì. Vậy các quy tắc chọn thế cờ quyết định phần lớn **lợi**, còn nhãn quyết định **không hại**. Điều này khớp với quy luật thực nghiệm của các lần chạy: tập thế cờ ảnh hưởng nhiều hơn công thức nhãn.

### 12.7 So với phương pháp đang chạy

| Phần | Đang chạy | Mới |
|---|---|---|
| Ván rẽ đi nước nào | Nước nhiều lượt thăm nhất | Bốc theo tỉ lệ lượt thăm |
| Nhãn value | $w_q\,q+(1-w_q)\,G$ | Trung bình $\hat Y$ của các ván thuần |
| Nhãn policy | Trung bình $\pi$ | Trung bình $\pi'$ của các ván thuần |
| Trung bình nhãn value bằng $V^\mu$ | Không: lệch do G1 sai, do $\rho\ne\pi$ và do mạng | Có, Định lý 5 |
| Đích policy tốt hơn chính sách đã chơi | Bằng (cải thiện 0) | Có, Định lý 8 |
| Giả định | G1 (sai), G2 (loại K), $\omega^2$ (ước cao), $c=0$, đồng nhất trong khoảng | Không có. Chỉ có điều kiện thiết kế ở 12.2 |
| Số đặt tay trong nhãn | Mốc khoảng cách, sàn 0,01, ngưỡng 1000 node | Không có. $\beta=\tfrac12$ suy ra được; $\kappa$ ước nhưng không đổi đích |
| Tính nhãn | Từ dưới lên trên cả cây, mỗi đời | Theo từng ván, lúc nạp ván |

Cái giá phải trả là độ dao động. Nhãn value mới dao động nhiều nhất khi $\kappa=0$, lúc đó bằng $z$ như AlphaZero; nhãn đang chạy dao động ít hơn vì nó tựa vào mạng. Đổi lại, nhãn đang chạy lệch một lượng không ai đo được, còn nhãn mới không lệch. Theo nguyên tắc giảm hại, lệch là cái hại cố định và tích luỹ qua các đời, còn dao động thì mạng tự trung bình hoá qua nhiều thế cờ.

### 12.8 Chỗ phải sửa trong mã (chưa viết)

1. **Engine, phần treeplay.** Sau nước rẽ, mỗi nước bốc theo tỉ lệ lượt thăm (temperature 1) thay vì đi nước nhiều lượt nhất. Cần kiểm engine đã có tuỳ chọn này cho treeplay chưa.
2. **`cay.py`, hàm `nap_lan`.** Với mỗi ván, đi ngược từ cuối ván lên tới node ngay sau nước rẽ, tính $\hat Y_t$ (bộ ba thắng, hoà, thua) và $\pi'_t$ từ số liệu search trong bản ghi. Cộng vào tổng của node. Chỉ cộng cho phần ván thuần, không cộng cho điểm rẽ và các node phía trên nó.
3. **`cay.py`, hàm `nhan`.** Nhãn value là tổng chia số ván thuần. Nhãn policy cũng vậy, và là $\pi$ ở node không có ván thuần. Bỏ $w_q$, $\tau_q^2$ và toàn bộ hàm `tinh`, trừ phần tính khoảng cách tới cuối ván nếu còn dùng để ghi log.
4. **Hệ số $\kappa$.** Mỗi đời ước một lần bằng hồi quy trên các ván thuần của đời trước: $\kappa=-\sum z\,C/\sum C^2$, lấy trên mọi cặp (nước, ván). Đời đầu tiên dùng $\kappa=0$. Ghi log $\kappa$ và độ dao động của nhãn theo khoảng cách tới cuối ván.
5. **Lưu nhãn.** Cả hai nhãn lưu dưới dạng số thực có dấu (float16 là đủ). Cần kiểm mã huấn luyện: hàm mất mát phải là cross-entropy với nhãn mềm, không chặn nhãn về 0 và không lấy logarit của nhãn (dạng KL sẽ hỏng khi nhãn âm).
6. **Cắt lá theo tuổi** của ván thuần gần nhất, thay cho $m$ (12.5).
7. **Giai đoạn chuyển.** Các node do ván cũ (đi nước nhiều lượt nhất) tạo ra không có ván thuần. Trong vài đời đầu sau khi đổi, các node đó hoặc giữ nhãn cũ, hoặc không được học. Đề xuất không học, để mọi nhãn đều có bảo đảm.

### 12.9 Kế hoạch thử

1. **Mô phỏng nhỏ, không cần mạng thật.** Dựng một cây trò chơi nhỏ có giá trị thật tính được chính xác. Cho "search" trả về $\hat Q$ cố tình sai, lệch có hệ thống. Chơi nhiều ván thuần, rồi so trung bình của $\hat Y$ và $\pi'$ với $V^\mu$ và với công thức của Định lý 7. Bước này kiểm cả định lý lẫn mã.
2. **Một đời trên điện thoại.** Chơi ván rẽ bằng cách bốc nước, ước $\kappa$, đo độ dao động của nhãn theo khoảng cách tới cuối ván. Định lý 6 dự đoán độ dao động tăng theo độ dài phần ván còn lại, và giảm khi $\kappa$ gần $\kappa^*$.
3. **Chạy thật và arena** như lần chạy 5. Mốc để so là 78,2% ở đời 20.

Rủi ro chính cần đo: ván bốc nước có nhiều nước kém hơn ván đi nước tốt nhất, nên tập thế cờ đổi. Theo quy luật thực nghiệm, tập thế cờ là thứ ảnh hưởng mạnh nhất, nên phải so số thế cờ trung cuộc mỗi đời với lần chạy 5 trước khi kết luận về nhãn.
