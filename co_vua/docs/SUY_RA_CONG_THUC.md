# Các công thức của cách cây trò chơi được suy ra thế nào

Viết ngày 15/11/2026, bổ sung 18/11 và 19/11. Tài liệu được đối chiếu với mã đang chạy trong `co_vua/scripts/cv/cay.py` (lần chạy 5). Lịch sử các quyết định nằm ở tài liệu thiết kế `THIET_KE_CO_VUA.md`. Tài liệu này làm hai việc:

1. Với mỗi công thức hay quy tắc đang chạy, nói rõ mã làm gì từng bước, công thức được **suy ra** từ đâu hay được **ước lượng** từ dữ liệu hay chỉ được **đặt tay**, và nó dựa vào loại giả định nào (mục 1.1).
2. Ghi một phương pháp mới (mục 12). Phương pháp này chỉ bỏ những giả định đặt lên thứ cần thời gian vô hạn mới tính được, tức giá trị thật $V$. Mọi phần khác được giữ, rà lại, hoặc thêm giả định khi cần. Phương pháp đề xuất ngày 19/11 và chưa viết mã.

**Cách đọc.**

- **Phần A, phương pháp đang chạy:**
  - mục 1 là bảng tổng hợp và tiêu chí phân loại giả định;
  - mục 2 mô tả cây, các số mỗi node lưu, và thứ tự các bước trong một đời;
  - các mục 3 đến 9 đi qua từng công thức theo đúng thứ tự mã tính.
- **Phần B, phương pháp thay thế và nền toán của nó:**
  - mục 10 suy ra nhãn policy mới của tài liệu thiết kế (đang tắt);
  - mục 11 là khung định lý theo kiểu Gumbel AlphaZero;
  - mục 12 là phương pháp mới: giữ $G$ và G1, bỏ G2, thêm giả định về sai số của $\hat Q$. Mục này viết đủ chi tiết để làm theo.

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

Chủ dự án chấp nhận loại X và T. Loại K bị coi là xa vời, nên phương pháp ở mục 12 bỏ nó.

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
- Mục 12 là phương pháp mới theo tiêu chí ngày 19/11. Nhãn tree backup $Y$ ở mục này là trường hợp riêng của nó, khi mọi nhánh đã chơi có $f=1$.

---

## 12. Phương pháp mới: chỉ bỏ giả định đặt lên thứ cần thời gian vô hạn (đề xuất 19/11, chưa viết mã, chưa thử)

### 12.1 Tiêu chí

Chủ dự án đặt tiêu chí ngày 19/11:

- **Tính được trong thời gian hữu hạn**: $G$, $q$, $\hat Q$, $\pi$, $z$, $m$, $E$ do mã tính ra. Đặt giả định lên những thứ này là chấp nhận được, kể cả giả định về sai số ngẫu nhiên của chúng, vì đó là việc của thống kê. Trong một giả định như vậy, giá trị thật $V$ được phép xuất hiện như cái đích mà ta so với.
- **Chỉ tính được nếu có thời gian vô hạn**: giá trị thật $V$ (phải chơi vô số ván), và những thứ định nghĩa bằng $V$ như độ toả thật của các $V$. Không đặt mô hình lên những thứ này.

Phương pháp mới **chỉ bỏ** những giả định vi phạm tiêu chí. Các giả định khác được giữ, được rà lại kỹ, và được thêm vào khi cần.

### 12.2 Rà từng giả định của phương pháp đang chạy

| Giả định | Đặt lên | Theo tiêu chí | Kết quả rà |
|---|---|---|---|
| Định nghĩa $V(s)$: "mỗi nước bốc theo $\pi$" | Định nghĩa, không phải giả định | | **Còn hở**: $\pi$ ở thế cờ ngoài cây chưa được định nghĩa. Sửa ở 12.3 |
| G1: $G$ không lệch, sai số các nhánh độc lập | $G$ (hữu hạn) | Giữ | Với cách gộp đang chạy, "không lệch" sai (mục 4.1). Phương pháp mới làm nó đúng trở lại, với điều kiện H đúng (12.5) |
| **G2: các $V(sa)$ ngẫu nhiên, độc lập, phương sai $\omega^2$** | $V$ (vô hạn) | **Bỏ** | |
| $\omega^2$ là độ toả thật, ước bằng độ toả của $Q$ | Độ toả của các $V$ (vô hạn) | **Bỏ** | Chỉ có nghĩa trong G2. Đã biết là ước cao |
| $w_q$: $q$ không lệch, $c=0$ | $q$, $G$ (hữu hạn) | Giữ được | Không còn cần, vì $G$ mới đã gộp sẵn đánh giá của mạng (12.8) |
| $\tau_q^2$: phương pháp moment với $c=0$, $E$ đúng | $q$, $G$, $E$ (hữu hạn) | Giữ được | Thay bằng phép ước $\tau^2$ của 12.7 |
| Mạng sai như nhau trong mỗi khoảng cách | $q$ (hữu hạn) | Giữ | Rà thêm: nên chia cả theo **số lượt thăm** (12.7) |
| Sàn 0,01, mượn khoảng gần cuối hơn | Đặt tay | | Sàn bỏ được. Quy tắc mượn giữ làm dự phòng |
| Nhãn policy: các lần search là mẫu của cùng phân phối | $\pi$ (hữu hạn) | Giữ | Không đổi |
| Bảng $\hat\Delta$ dự báo độ chênh lần sau | $\pi$ (hữu hạn) | Giữ | Không đổi |
| Ván chạm độ dài tối đa tính là hoà | Quy ước luật chơi | | Giữ, là một phần định nghĩa trò chơi |

Kết luận của bảng: hai thứ phải bỏ là G2 và $\omega^2$. Hai thứ được giữ nhưng không còn cần là $w_q$ và $\tau_q^2$. Thêm vào đó là một chỗ định nghĩa còn hở, và một chỗ cần chia mịn hơn.

### 12.3 Định nghĩa lại cho kín: $V$ của chính sách nào

Đích học là $V^\pi(s)$: kết quả trung bình (theo góc Trắng) khi từ $s$ hai bên cùng chơi theo một chính sách $\pi$ được định nghĩa ở **mọi** thế cờ.

- **Trong cây:** $\pi$ là tỉ lệ lượt thăm đã lưu tại node.
- **Ngoài cây:** $\pi$ là tỉ lệ lượt thăm của search mạng đời hiện tại, rồi bốc nước theo tỉ lệ đó.
- **Ván chạm độ dài tối đa** tính là hoà, đúng như mã đang làm.

Với định nghĩa này, mỗi ván hữu hạn, nên $V^\pi(s)$ là một con số xác định. Đây vẫn là đích mà phương pháp đang chạy nhắm tới (mục 3), chỉ là nay đã được nói kín.

Có một điểm phù hợp đáng ghi lại. $Q$ của search là trung bình các đánh giá ở đáy cây search, **cân theo số lượt thăm**. Vậy về cấu trúc, $Q$ trộn các nhánh gần giống cách $V^\pi$ trộn theo $\pi$. Đây là lý do để mong $\hat Q$ ước lượng $V^\pi$ khá đúng. Nó không phải chứng minh; giả định H ở 12.4 mới là chỗ nói điều này.

### 12.4 Giả định của phương pháp mới

Mọi giả định dưới đây đều đặt lên đại lượng tính được trong thời gian hữu hạn.

- **G1 (giữ).** $G(sa)=V^\pi(sa)+e_a$, với $e_a$ có trung bình 0 và phương sai $E(sa)$. Sai số của các nhánh khác nhau độc lập với nhau.
- **H (thêm, thay cho G2).** $\hat Q(sa)=V^\pi(sa)+b+\eta_a$, trong đó:
  - $b$ là độ lệch chung của mạng trong một nhóm (12.6);
  - $\eta_a$ có trung bình 0 và phương sai $\tau^2_a$;
  - các $\eta_a$ của những nước anh em độc lập với nhau, và độc lập với các $e$.
- **Đ (thêm, rà ra ở 12.2).** $b$ và $\tau^2$ giống nhau trong mỗi nhóm (khoảng cách tới cuối ván × số lượt thăm của nước).

**Rà kỹ hai chỗ "độc lập", vì đây là chỗ dễ sai nhất.**

1. **Sai số của các nhánh độc lập (G1).** Ở phương pháp đang chạy, điều này đúng theo cách xây cây, vì $G(sa)$ chỉ dùng kết quả ván. Ở phương pháp mới, $G(sa)$ còn chứa các $\hat Q$ bên trong cây con của $sa$. Mà cùng một mạng đánh giá mọi cây con, nên nếu mạng sai một cách có hệ thống (ví dụ đánh giá cao một kiểu thế tốt xuất hiện ở cả hai nhánh), sai số của hai nhánh sẽ cùng chiều. Vậy ở phương pháp mới, tính độc lập này **trở thành một giả định** về $\hat Q$, không còn đúng theo cách xây. Nó vẫn đặt lên đại lượng hữu hạn, nên vẫn hợp tiêu chí. Phần độ lệch chung $b$ trong H đã tách ra cái sai cùng chiều dễ thấy nhất.
2. **$\eta_a$ độc lập với $e_a$ ($c=0$).** Có một lý do **về cấu trúc** để nghi điều này: lần search ở node cha, lúc tính $\hat Q(sa)$, đã đánh giá chính những thế cờ nằm trong cây con của $sa$ bằng cùng một mạng. Vì vậy 12.7 đưa ra hai cách ước $\tau^2$: một cách dùng $c=0$, một cách không cần $c=0$ mà chỉ dùng bất đẳng thức Cauchy–Schwarz (toán thuần).

### 12.5 Suy ra $G$ và $E$

**Ước lượng.** Gọi $\tilde Q(sa)=\hat Q(sa)-\hat b$ là $\hat Q$ đã trừ độ lệch chung ước được (12.6). Lấy
$$G(s)=\sum_{a\in C(s)}\rho_a\,G(sa)+\sum_{a\in A(s)}(\pi_a-\rho_a)\,\tilde Q(sa),$$
với quy ước $\rho_a=0$ cho nước chưa chơi.

Hệ số của $\tilde Q$ là $\pi-\rho$. Đó chính là phần mà cách gộp theo $\rho$ lệch khỏi $\pi$. Nó được bù bằng một đại lượng tính được, thay vì được G2 coi là nhiễu. Nếu mọi $G(sa)$ và $\tilde Q(sa)$ cùng bằng một số $c$ thì $G(s)=c$, nên $\rho$ không cần cộng lại bằng 1.

**Sai số.** Thay G1 và H vào (sau khi trừ $\hat b$, coi như $\hat b$ đúng):
$$G(s)-V^\pi(s)=\sum_{a\in C}\rho_a e_a+\sum_{a\in A}(\pi_a-\rho_a)\,\eta_a.$$
Mọi số hạng chứa $V^\pi$ đều triệt tiêu, vì tổng hệ số của $V^\pi(sa)$ là $\rho_a+(\pi_a-\rho_a)=\pi_a$, đúng bằng hệ số của nó trong $V^\pi(s)=\sum\pi_aV^\pi(sa)$. Phần gộp lệch biến mất mà không cần G2. Có hai hệ quả:

- Sai số có trung bình 0, nên **$G(s)$ thoả G1**. Vậy G1 ở mỗi tầng được suy ra từ G1 ở tầng dưới cộng với H, xuất phát từ node kết thúc, nơi $G=z=V^\pi$ đúng tuyệt đối.
- Theo các giả định độc lập: $E(s)=\sum_{a\in C}\rho_a^2E(sa)+\sum_{a\in A}(\pi_a-\rho_a)^2\tau^2_a$.

**Chọn trọng số.** Cực tiểu $E(s)$ theo từng $\rho_a$, không có ràng buộc. Đạo hàm bằng 0 cho
$$\rho_a=\pi_a f_a,\qquad f_a=\frac{\tau^2_a}{\tau^2_a+E(sa)}.$$
Thay vào, đặt $x_a=f_aG(sa)+(1-f_a)\tilde Q(sa)$ cho nước đã chơi và $x_a=\tilde Q(sa)$ cho nước chưa chơi. Khi đó
$$G(s)=\sum_{a\in A(s)}\pi_a\,x_a,\qquad E(s)=\sum_{a\in C(s)}\pi_a^2\,\frac{\tau^2_aE(sa)}{\tau^2_a+E(sa)}+\sum_{a\notin C(s)}\pi_a^2\,\tau^2_a.$$

Phần $E$ của nước đã chơi đúng vì $f^2E+(1-f)^2\tau^2=\tau^2E/(\tau^2+E)$. Hai vế cùng mẫu số $(\tau^2+E)^2$, và tử số $\tau^4E+E^2\tau^2=\tau^2E(\tau^2+E)$.

**Đọc công thức.**

1. Ở mỗi nước đã chơi, $x_a$ gộp hai ước lượng của cùng $V^\pi(sa)$: kết quả ván $G$ (sai $E$) và đánh giá của search $\tilde Q$ (sai $\tau^2$), theo nghịch đảo phương sai.
2. $G(s)$ trộn các $x_a$ theo **đúng** $\pi$. Nước chưa chơi giữ phần $\pi$ của nó, thông qua $\tilde Q$.
3. So với cách đang chạy: $\omega^2$ (độ toả của các giá trị thật, cần thời gian vô hạn) được thay bằng $\tau^2$ (sai số của mạng, ước được). Bước dồn trọng số $\nu$ sang các nhánh đã chơi biến mất.

**Trường hợp biên.**

- $\tau^2=0$ (mạng đúng hoàn toàn): $G(s)=\sum\pi\tilde Q$.
- $E(sa)=0$ (node con là node kết thúc): $x_a=G(sa)$.
- Khi mọi nước đã chơi có $f=1$, $G$ trùng với nhãn tree backup của mục 11.4 (với $T=1$).

**Dạng tính trong mã:**
$$G(s)=\sum_{a\in A}\pi_a\tilde Q(sa)+\sum_{a\in C}\pi_af_a\big(G(sa)-\tilde Q(sa)\big).$$
Phần đầu là đánh giá của search trộn theo $\pi$. Phần sau là chỗ kết quả ván sửa đánh giá đó, ở từng nhánh, mạnh hay nhẹ theo $f$.

**Ví dụ trên node ví dụ** ($\hat b=0$, $\tau^2=0{,}0447$ dùng tạm):

1. $f$ là 0,817 và 0,899.
2. $x$ là −0,186; 0,445; −0,30.
3. $G(s)=0{,}70\times(-0{,}186)+0{,}25\times0{,}445+0{,}05\times(-0{,}30)\approx-0{,}034$.
4. $E(s)\approx0{,}0044$.

Phương pháp đang chạy cho $G=+0{,}080$ và $E=0{,}0047$. Chỗ khác chủ yếu nằm ở trọng số. Phương pháp đang chạy dồn $a_2$ từ 0,25 lên 0,44, và việc dồn đó là thứ G2 cho phép. Phương pháp mới giữ đúng $\pi$ và để $a_3$ góp phần của nó qua $\tilde Q$. Phần của kết quả ván trong $G(s)$ là $\sum_C\pi f\approx0{,}80$.

### 12.6 Ước độ lệch chung $b$ của mạng

Theo G1 và H, với một nhánh đã chơi: $G(sa)-\hat Q(sa)=e_a-b-\eta_a$, có trung bình $-b$. Vậy
$$\hat b=-\,\text{trung bình}\big[G(sa)-\hat Q(sa)\big]$$
lấy trên các nhánh đã chơi trong cùng nhóm, theo góc bên đang đi.

Bước này bắt được, ví dụ, việc mạng hay đánh giá lạc quan cho bên đang đi ở một khoảng cách nào đó. Nếu $\hat b$ gần 0 ở mọi nhóm thì bỏ bước này được. Đây là một phép kiểm H trên dữ liệu có sẵn.

### 12.7 Ước $\tau^2$

**Nhóm.** Chia theo hai thứ:

- **Khoảng cách tới cuối ván** của node con, với các mốc của mục 7.1. Nước chưa chơi không có node con, nên dùng khoảng cách của node cha trừ 1.
- **Số lượt thăm của nước** trong search ở node cha, chia làm ba nhóm: dưới 10, từ 10 đến 99, từ 100 trở lên.

Chia theo số lượt thăm là điều rà ra ở 12.2. Nước chưa chơi thường ít lượt thăm, nên $\hat Q$ của nó dựa trên ít đánh giá và sai nhiều hơn. Nếu chỉ ước $\tau^2$ từ nhánh đã chơi (phần lớn là nước nhiều lượt nhất) rồi dùng cho nước chưa chơi, $\tau^2$ của nước chưa chơi sẽ bị ước thấp. Dữ liệu cho nhóm ít lượt thăm đến từ các ván rẽ, vì bước quét chủ yếu chọn những nước không phải nước nhiều lượt nhất. Nhóm nào quá ít nhánh (dưới 1000) thì gộp với nhóm số lượt thăm kề bên.

**Phương pháp moment.** Trong một nhóm, đặt $M=\text{trung bình}\big[(G(sa)-\tilde Q(sa))^2\big]$ và $\bar E=\text{trung bình}\big[E(sa)\big]$. Theo G1 và H, $M=\bar E+\tau^2-2c$, với $c$ là hiệp phương sai giữa $e$ và $\eta$.

- **Cách 1, dùng $c=0$:** $\tau^2=M-\bar E$.
- **Cách 2, không cần giả định về $c$.** Bất đẳng thức Cauchy–Schwarz cho $|c|\le\sqrt{\bar E\,\tau^2}$, nên $M\ge(\sqrt{\tau^2}-\sqrt{\bar E})^2$, tức là
$$\tau^2\le\big(\sqrt{\bar E}+\sqrt M\big)^2.$$
  Cách 2 lấy đúng cận trên này.

**Chọn cách nào theo nguyên tắc giảm hại.** $\tau^2$ lớn hơn thì $f$ lớn hơn, tức tin kết quả ván nhiều hơn. Cái hại đã thấy thật là lần chạy 1, khi nhãn ngả theo đánh giá của mạng và mạng tự xác nhận mình. Cách 2 chặn đúng cái hại đó. Ví dụ khoảng 5 đến 10 ở đời 10: $\bar E\approx0{,}006$, $M\approx0{,}051$, nên cách 1 cho 0,045 còn cách 2 cho $(0{,}077+0{,}226)^2\approx0{,}092$. Mặc định đề xuất là thử cả hai offline (12.12), vì chưa biết cách nào cho nhãn tốt hơn.

**Vòng lặp.** $E$ phụ thuộc $\tau^2$, còn $\tau^2$ và $\hat b$ lại được ước bằng $E$ và $G$. Mã làm như sau:

1. Bắt đầu bằng $\tau^2$ và $\hat b$ của đời trước.
2. Tính $G$, $E$ từ dưới lên.
3. Ước lại $\hat b$ và $\tau^2$.
4. Lặp bước 2 và 3 tới khi các số đổi rất ít, thường 2 đến 3 lượt.

Một nhóm mà cách 1 vẫn ra số âm là dấu hiệu H sai ở nhóm đó. Khi đó dùng cách 2, và ghi log số lần xảy ra.

### 12.8 Nhãn value: dùng thẳng $G$

Nhãn value là $G(s)$, đổi sang góc bên đang đi như mục 6.3. Bước $w_q$ của mục 6 và phép ước $\tau_q^2$ của mục 7 được bỏ, vì hai lý do:

- $G$ mới đã gộp sẵn kết quả ván với đánh giá của search ở từng nhánh.
- $q$ của node đến từ cùng lần search với các $\hat Q$ nằm trong $G$. Trộn thêm $q$ là tính đánh giá của mạng hai lần, và giả định $c=0$ mà $w_q$ cần sẽ sai rõ.

**Ở xa cuối ván.** Trên một đường không rẽ nhánh với $\pi=0{,}7$, $E=0{,}3$ và $\tau^2=0{,}2$: $f=0{,}4$, nên phần của đánh giá mạng trong nhãn là $0{,}7\times0{,}6+0{,}3=0{,}72$. Phương pháp đang chạy ở cùng vùng có $w_q$ trung bình 0,25 (khoảng 80 đến 160) và 0,73 (từ 160). Vậy hai phương pháp cùng cỡ. Cách 2 của 12.7 làm $\tau^2$ lớn hơn, nên phần của mạng nhỏ đi.

### 12.9 Nhãn policy

Giữ trung bình $\pi$ như mục 9. Mọi giả định của phần này đặt lên $\pi$, một đại lượng hữu hạn. Nếu sau này muốn, có thể dùng nhãn nghiêng của mục 11.5 với $x_a$ ở 12.5. Phép nghiêng chắc chắn cho $\sum\pi'x\ge\sum\pi x$; đây là toán thuần.

### 12.10 So giả định: phương pháp đang chạy và phương pháp mới

| Giả định hay quy tắc | Đặt lên | Đang chạy | Phương pháp mới |
|---|---|---|---|
| G2: các $V$ ngẫu nhiên, phương sai $\omega^2$ | $V$, vô hạn | Có | **Bỏ** |
| $\omega^2$ là độ toả thật | Các $V$, vô hạn | Có | **Bỏ** |
| Định nghĩa $V$ ngoài cây | | Hở | Kín (12.3) |
| G1: $G$ không lệch | $G$, hữu hạn | Có, nhưng bị cấu trúc gộp phá | Có, và được suy ra lại từ H |
| G1: các nhánh độc lập | $G$, hữu hạn | Đúng theo cách xây | Thành giả định về $\hat Q$, vì $G$ chứa $\hat Q$ |
| H: $\hat Q$ lệch chung $b$, phần còn lại không lệch, các nước anh em độc lập | $\hat Q$, hữu hạn | Không có | Có, mới |
| Đ: $b$ và $\tau^2$ đồng nhất trong nhóm (khoảng cách × số lượt thăm) | $\hat Q$, hữu hạn | Chỉ theo khoảng cách | Theo khoảng cách và số lượt thăm |
| $c=0$ | $q$ hoặc $\hat Q$, và $G$, hữu hạn | Có | Cách 1 có, cách 2 không cần |
| $q$ không lệch, dùng trong $w_q$ | $q$, hữu hạn | Có | Không còn cần |
| Sàn 0,01 | Đặt tay | Có | Bỏ |
| Mượn khoảng hay nhóm kề bên khi ít dữ liệu | Đặt tay | Có | Giữ |
| Ràng buộc trọng số cộng bằng 1, số $\nu$ | | Có | Không cần |

### 12.11 Chỗ phải sửa trong mã (ước lượng, chưa viết)

**`cay.py`, hàm `tinh`:**

- Với mỗi node con, ngoài $\pi$ của nước dẫn tới nó (biến `pi_con`), đọc thêm từ cùng ô pool của node cha: $\hat Q$ (từ `nq/ns` và `nd/ns`, đổi sang bộ ba thắng, hoà, thua theo góc Trắng) và số lượt thăm (`ns`) để xếp nhóm.
- Ở mỗi độ sâu:
  - $f=\tau^2/(\tau^2+E_{\text{con}})$;
  - $G(s)=\sum_{\text{pool}}\pi\tilde Q+\sum_{\text{đã chơi}}\pi f(G_{\text{con}}-\tilde Q_{\text{con}})$, tính cho từng thành phần thắng, hoà, thua;
  - $E(s)=\sum_{\text{đã chơi}}\pi^2fE_{\text{con}}+\sum_{\text{chưa chơi}}\pi^2\tau^2$, với $\tau^2$ theo nhóm của từng nước.
- Bỏ phần tính $\omega^2$ và $\nu$. Thêm vòng lặp ước $\hat b$ và $\tau^2$ (12.6, 12.7). Node gốc cắt giữ $G$, $E$ như hiện nay.

**`cay.py`, hàm `nhan`:** nhãn value là $G$ theo góc bên đang đi. Bỏ $w_q$ và $\tau_q^2$, hoặc chỉ giữ để ghi log so sánh. Ghi log thêm: $\hat b$ và $\tau^2$ theo nhóm (cả cách 1 lẫn cách 2), số lượt lặp, $f$ trung bình, phần của kết quả ván trong nhãn.

**Công tắc mới** trong `CONG_TAC`: bật phương pháp mới, và chọn cách 1 hay cách 2 cho $\tau^2$.

**Không đổi:** engine, các ô Colab, huấn luyện, rẽ nhánh, cắt lá, search lại, nhãn policy.

### 12.12 Kế hoạch thử offline trước khi dùng thật

1. **Trên điện thoại, không tốn T4.** Chạy phương pháp mới trên cây sau đời 20 của lần chạy 5, với cả hai cách ước $\tau^2$. In ra:
   - $\hat b$ và $\tau^2$ theo nhóm;
   - nhóm nào cách 1 ra âm;
   - so sánh nhãn mới với nhãn đang chạy theo khoảng cách tới cuối ván;
   - phần của kết quả ván trong nhãn.
2. **Kiểm các giả định độc lập, trên dữ liệu có sẵn.**
   - Ở node có từ hai nhánh đã chơi trở lên: các độ lệch $G(sa)-\tilde Q(sa)$ của các nhánh anh em có cùng chiều không?
   - Khoảng cách giữa cách 1 và cách 2 lớn tới đâu? Khoảng cách lớn nghĩa là $c$ có thể đáng kể.
3. **Trên một máy T4.** Huấn luyện lại từ cây với ba bản nhãn (đang chạy, mới với cách 1, mới với cách 2), rồi làm phép thử AUC như ngày 12/11.
4. **Chỉ đưa vào lần chạy thật** nếu bản mới không kém bản đang chạy. Lần chạy 5, với 78,2% ở đời 20, là mốc để so.
