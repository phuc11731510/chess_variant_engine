# Các công thức của cách cây trò chơi được suy ra thế nào

Viết ngày 15/11/2026, bổ sung 18/11, 19/11, 21/11 và 22/11. Tài liệu được đối chiếu với mã đang chạy trong `co_vua/scripts/cv/cay.py` (lần chạy 5). Lịch sử các quyết định nằm ở tài liệu thiết kế `THIET_KE_CO_VUA.md`. Tài liệu này làm hai việc:

1. Với mỗi công thức hay quy tắc đang chạy, nói rõ mã làm gì từng bước, công thức được **suy ra** từ đâu hay được **ước lượng** từ dữ liệu hay chỉ được **đặt tay**, và nó dựa vào loại giả định nào (mục 1.1).
2. Ghi bản nâng cấp của chính cách cây đang chạy (mục 12). Bản này đối chiếu phần suy diễn thống kê với số đo thật của lần chạy 5, chỉ ra ba chỗ không khớp, và đề xuất cách sửa, giữ temperature 0 và mục 8 trừ các quy tắc search lại. Đề xuất ngày 19/11, sửa ngày 21/11, chưa viết mã.

**Cách đọc.**

- **Phần A, phương pháp đang chạy:**
  - mục 1 là bảng tổng hợp và tiêu chí phân loại giả định;
  - mục 2 mô tả cây, các số mỗi node lưu, và thứ tự các bước trong một đời;
  - các mục 3 đến 9 đi qua từng công thức theo đúng thứ tự mã tính.
- **Phần B, phương pháp thay thế và nền toán của nó:**
  - mục 10 suy ra nhãn policy mới của tài liệu thiết kế (đang tắt);
  - mục 11 đã bỏ ngày 21/11 (khung định lý kiểu Gumbel AlphaZero, toàn văn còn trong lịch sử git);
  - mục 12 là bản nâng cấp của cách cây đang chạy, dựa trên số đo thật. Mục này gồm công cụ đo, số liệu, ba chỗ suy diễn không khớp, định lý về lâu dài, nhãn value và nhãn policy mới, ván lặp để đo phần may rủi ngay trong vòng lặp, và những chỗ còn hở. Mục này viết đủ chi tiết để làm theo.

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

Chủ dự án chấp nhận loại X và T. Loại K từng bị coi là xa vời. Từ chiều 19/11, chủ dự án không còn phản đối giả định nào, kể cả G2, và không cần phân loại nữa. Thước đo ở mục 12 là suy diễn có khớp với số đo thật hay không.

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

## 11. (Đã bỏ ngày 21/11)

Mục này từng ghi một khung định lý theo kiểu Gumbel AlphaZero (đề xuất 18/11, chưa chạy), gồm các định lý 1 đến 4. Ngày 21/11 chủ dự án bỏ khung này và chọn làm chặt chính cách cây đang chạy (mục 12). Số mục được giữ để các chỗ dẫn tới mục 12 không phải đổi. Toàn văn mục 11 còn trong lịch sử git (commit 34dd575).

---

## 12. Nâng cấp cách cây đang chạy theo số đo thật (19/11, sửa 21/11, đo 22/11, chưa viết mã)

Mục này đối chiếu phần suy diễn thống kê của cách cây đang chạy (mục 3 đến 7 và 9) với dữ liệu thật của lần chạy 5, chỉ ra chỗ nào không khớp, rồi đề xuất cách nâng cấp. Mọi con số ở đây đo trên dữ liệu thật trong điện thoại ngày 19/11. Chưa có dòng mã nào được sửa.

Ngày 21/11 mục này được sửa ở năm chỗ, mỗi chỗ có ghi "Sửa 21/11":

- bổ đề thiết kế được viết chính xác hơn (12.3);
- mọi nhóm được lập theo thông tin đã biết ở $s$, không theo độ dài còn lại của ván (12.3);
- cách đọc định lý 9 (12.6);
- nhãn value được gộp một lần thay vì hai tầng (12.7);
- phép đo phần may rủi chuyển vào vòng lặp bằng ván lặp (12.9).

12.12 ghi những chỗ còn hở.

### 12.1 Phạm vi: giữ gì, nâng cấp gì

Chủ dự án chốt ngày 19/11:

- **Giữ nguyên mục 8, trừ các quy tắc search lại:** cắt lá, làm cũ bằng $\gamma$ và $W$, quét điểm rẽ với $T=0{,}5$, khoá $-\ln(u)/m^2$, trần 20% ngân sách cho search lại, lập việc theo ngân sách.
- **Search lại được nới (21/11).** Chủ dự án giữ trần 20% nhưng cho đổi các quy tắc khác của search lại (mục 8.5). Search lại được phép chơi tiếp thành ván (ván lặp, 12.9), và công thức ưu tiên của 8.5 nhường chỗ cho cách chia trần ở 12.9.
- **Giữ temperature 0 trong ván rẽ.** Ván đi nước nhiều lượt thăm nhất ở mọi nửa nước (trong mã, `04_sinh_du_lieu.py` đặt `TEMP_PLIES = 0` cho cách cây). Lý do: engine dùng lại được cây search của nước vừa đi, và cùng ngân sách chơi được nhiều node hơn cách truyền thống.
- **Được nâng cấp hoặc thay:** mọi phần còn lại, gồm $G$, $E$, $\rho$, $\omega^2$ (mục 3 đến 5), $w_q$ và $\tau_q^2$ (mục 6, 7), và nhãn policy (mục 9). Nhãn policy trung bình $\pi$ được giữ nếu nó có cơ sở toán học về cải thiện chính sách (12.8 cho thấy là có).
- **Giả định không còn bị cấm.** Chủ dự án không còn phản đối G2 hay bất kỳ giả định nào, và không cần phân loại giả định nữa. Thước đo bây giờ là: suy diễn có khớp với kết quả thật không, và thiết kế có tối ưu theo thống kê suy diễn không.

### 12.2 Đích học, ván thuần và giá trị search lúc chơi

**Chính sách chơi $\beta$.** Gọi $\beta$ là đúng cách mà ván rẽ được chơi ở một đời: mỗi nước chạy search khoảng 800 lượt thăm bằng mạng của đời đó, có nhiễu Dirichlet ở gốc, có dùng lại cây của nước trước, rồi đi nước nhiều lượt thăm nhất. $\beta(a|s)$ là xác suất để cách chơi đó chọn nước $a$ tại $s$. Vì có nhiễu Dirichlet, $\beta$ không hoàn toàn tất định, nhưng gần như luôn chọn nước nhiều lượt thăm nhất. Mã không biết chính xác các xác suất $\beta(a|s)$, và phương pháp dưới đây không cần biết chúng.

**Đích học $V^\beta$.** $V^\beta(s)$ là kết quả trung bình, theo góc bên đang đi tại $s$, nếu từ $s$ hai bên cùng chơi theo $\beta$. $Q^\beta(s,a)$ là kết quả trung bình nếu đi $a$ trước rồi hai bên chơi theo $\beta$. Ván hữu hạn và kết quả bị chặn, nên đây là những con số xác định, và
$$V^\beta(s)=\sum_a\beta(a|s)\,Q^\beta(s,a).$$
Đây là đích học của đầu value trong phương pháp nâng cấp. Mục 3 định nghĩa giá trị thật bằng cách "mỗi nước bốc theo $\pi$". Định nghĩa đó không khớp với cách ván thật được chơi, và 12.5 cho thấy chỗ không khớp này gây lệch đo được.

**Ván thuần.** Một ván là **ván thuần từ node $s$** nếu nó đi qua $s$ và mọi nước của nó từ $s$ trở đi đều do $\beta$ chọn. Bản ghi của một ván rẽ gồm đường đi từ gốc tới thế bắt đầu (kể cả nước rẽ) và các lần search từ thế bắt đầu trở đi (mục 2.2). Vì vậy ván rẽ là ván thuần từ mọi node từ thế bắt đầu trở xuống trên đường của nó. Ván lặp (12.9) bắt đầu ở một node đã có và không có nước ép, nên nó là ván thuần từ node bắt đầu và từ mọi node bên dưới trên đường của nó.

**Mỗi node có đúng một ván thuần.** Ván rẽ luôn bắt đầu ở một node mới, vì nước rẽ là nước chưa chơi tại điểm rẽ. Mọi node bên dưới thế bắt đầu cũng là node mới, vì node được định danh bằng cả đường đi. Vậy một ván rẽ không bao giờ đi qua node có sẵn từ thế bắt đầu trở xuống. Search lại thì không chơi ván. Từ đó, mọi node tạo sau đời 0 có **đúng một** ván thuần: ván đã tạo ra nó. Ngoại lệ duy nhất là các node gần gốc của đời 0, nơi nhiều ván cùng bắt đầu từ thế khởi đầu. Đó là tình trạng của lần chạy 5. Khi bật ván lặp (12.9), một node có thể có nhiều ván thuần, và 12.7 dùng hết chúng.

Hai hệ quả:

- Ở node chỉ có một nhánh đã chơi, $G$ của mã hiện tại đúng bằng kết quả ván thuần của node.
- Các ván rẽ đi qua một node $s$ đều sinh ra từ các điểm rẽ **bên dưới** $s$. Chúng không phải ván thuần từ $s$, và chúng không phải là mẫu của $V^\beta(s)$.

**Nhánh $\beta$ và nhánh rẽ.** Tại node $s$, nhánh $\beta$ là node con mà ván tạo ra $s$ đã đi tới. Nó được tạo trước mọi node con khác, nên là node con có chỉ số nhỏ nhất. Các node con còn lại là nhánh rẽ, mỗi nhánh do một ván rẽ sinh ra tại $s$ với nước do bước quét chọn (mục 8.3). Khi có ván lặp, các ván thuần từ $s$ có thể đi tới những node con khác nhau, và mọi node con mà một ván thuần từ $s$ đi tới đều là nhánh $\beta$.

**Giá trị search lúc chơi.** Gọi $q(s)$ là $Q$ của nước nhiều lượt thăm nhất trong **lần search của ván thuần tại $s$**, tức lần search đã chọn nước đi ở $s$. Bản ghi ván lưu sẵn số này (trường `best_q`, cùng xác suất hoà `best_d`). $q(s)$ khác $q$ mà mã đang dùng trong nhãn: mã dùng trung bình gộp của mọi lần search tại node, trong đó có các lần search lại bằng mạng đã học từ chính kết quả ván của node. Khi node có nhiều ván thuần, $q(s)$ là của ván mới nhất (12.7, bước 6).

### 12.3 Bốn công cụ đo không cần giả định

**Bổ đề thiết kế.** Xét một vị trí $s$ trên ván thuần của nó. Gọi $\mathcal F_s$ là mọi thứ đã biết lúc ván đang ở $s$: cây, mạng, lần search tại $s$ (nên có cả $q(s)$, $\hat Q(s,\cdot)$, $\pi(s)$). Gọi $z$ là kết quả ván theo góc bên đi tại $s$. Khi đó
$$\mathbb E\big[z\,\big|\,\mathcal F_s\big]=V^\beta(s).$$
**Chứng minh.** Từ $s$ trở đi ván được chơi đúng theo $\beta$, với số ngẫu nhiên mới (nhiễu Dirichlet của các lần search sau). Theo định nghĩa, trung bình của kết quả là $V^\beta(s)$. Những gì đã biết ở $s$ không ảnh hưởng tới số ngẫu nhiên về sau.

Hệ quả: với mọi đại lượng $X$ tính xong trước khi ván đi tiếp từ $s$, ta có $\mathbb E[(z-V^\beta(s))\,X]=0$.

**Sửa 21/11: nước đi tại $s$ do chính lần search đó chọn.** $\mathcal F_s$ gồm cả lần search tại $s$, mà ở temperature 0 nước đi tại $s$ là nước nhiều lượt thăm nhất của lần search đó. Vì vậy, nói chính xác,
$$\mathbb E\big[z\,\big|\,\mathcal F_s\big]=Q^\beta(s,a_s)=:V^+(s),$$
với $a_s$ là nước lần search đó chọn. $V^\beta(s)$ là trung bình của $V^+(s)$ qua nhiễu Dirichlet của lần search tại $s$. Hiệu $\delta_s=V^+(s)-V^\beta(s)$ là phần may rủi của chính việc chọn nước ở $s$. Nó bằng 0 khi nhiễu không đổi được nước nhiều lượt thăm nhất, và ở temperature 0 điều đó thường xảy ra. Ba hệ quả:

- Bổ đề và hệ quả của nó đúng tuyệt đối khi thay $V^\beta(s)$ bằng $V^+(s)$. Mọi câu "đúng tuyệt đối" ở bốn công cụ dưới đây cũng vậy: công cụ 1 đo độ lệch của $q$ so với giá trị của chính nước nó chọn, và trong công cụ 2, $A=\mathbb E\big[(q-V^+)^2\big]$, $B=\mathbb E\big[\mathrm{Var}(z\,|\,\mathcal F_s)\big]$.
- Với đích học $V^\beta(s)$, nhãn $w\,q+(1-w)\,z$ lấy $q$ và $z$ từ cùng một ván có sai số $w\,(q-V^+)+(1-w)\,(z-V^+)+\delta_s$. Phần $\delta_s$ cộng một hằng số $\mathrm{Var}(\delta_s)$ vào sai số bình phương với mọi $w$. Vậy khi $\delta_s$ không tương quan với sai số của search, trọng số tốt nhất vẫn là $B/(A+B)$.
- Hai ván độc lập từ cùng $s$ có hai lần search riêng tại $s$, nên cặp ván (12.9) đo $B+\mathrm{Var}(\delta_s)$. Độ lớn của $\mathrm{Var}(\delta_s)$ kiểm được bằng tỉ lệ các cặp có nước đầu khác nhau.

**Công cụ 1: đo độ lệch của $q$.** Trung bình của $z-q(s)$ trên nhiều vị trí bằng trung bình của $V^\beta(s)-q(s)$, tức độ lệch của giá trị search so với đích học. Phép đo này không cần giả định gì.

**Công cụ 2: tách sai số tổng.** Đặt
$$S=\mathbb E\big[(z-q)^2\big],\quad A=\mathbb E\big[(q-V^\beta)^2\big],\quad B=\mathbb E\big[\mathrm{Var}(z\,|\,\mathcal F_s)\big].$$
$A$ là sai số của search so với đích học. $B$ là độ may rủi của một ván chơi từ $s$. Khai triển $z-q=(z-V^\beta)+(V^\beta-q)$ rồi bình phương. Số hạng chéo có trung bình 0 theo hệ quả của bổ đề, vì $V^\beta-q$ tính xong trước khi ván đi tiếp. Vậy
$$S=A+B\quad\text{đúng tuyệt đối.}$$
Đây là chỗ mục 6 và 7 phải giả định $c=0$. Với $q$ lúc chơi và kết quả ván thuần, $c=0$ là một định lý. Với $q$ gộp có các lần search lại, $c$ có thể dương, như mục 7.2 đã nghi.

**Công cụ 3: định lý không tách được.** Với dữ liệu mỗi thế cờ một ván, mọi cách chia $S$ thành $A+B$ với $A,B\ge0$ đều khớp dữ liệu như nhau.

**Chứng minh.** Dữ liệu là các cặp $(q,z)$, nên mọi điều dữ liệu cho biết đều nằm trong phân phối có điều kiện $P(z\,|\,q)$, một phân phối trên ba giá trị $+1$, 0, $-1$. Xét hai thế giới có cùng $P(z\,|\,q)$:

- **Thế giới I.** Giá trị thật đúng bằng $q$, và mọi khác biệt giữa $z$ với $q$ là may rủi. Khi đó $A=0$ và $B=S$.
- **Thế giới II.** Kết quả mỗi ván đã định sẵn từ thế cờ, nên $V^\beta(s)=z$ và không có may rủi. Mỗi thế cờ có $q$ cho trước nhận giá trị thật $+1$, 0 hay $-1$ đúng với xác suất $P(z\,|\,q)$. Khi đó $B=0$ và $A=S$.

Hai thế giới cho ra cùng phân phối của $(q,z)$, nên không phép thống kê nào trên dữ liệu đó phân biệt được chúng. Mọi thế giới trung gian cũng vậy.

Định lý này quan trọng vì tỉ lệ trộn tốt nhất giữa $q$ và kết quả ván phụ thuộc đúng vào cách chia $S$ thành $A$ và $B$ (12.7). Muốn biết cách chia thì cần thứ dữ liệu khác: **hai** ván thuần độc lập từ cùng một thế cờ (12.9). Với hai kết quả $z_1$, $z_2$ như vậy:
$$B=\tfrac12\,\mathbb E\big[(z_1-z_2)^2\big],\qquad A=\mathbb E\big[(z_1-q)(z_2-q)\big],$$
cả hai đúng tuyệt đối. Lý do: $z_1-z_2=(z_1-V^\beta)-(z_2-V^\beta)$ là hiệu của hai độ may rủi độc lập, cùng phương sai. Còn $(z_1-q)(z_2-q)$ có trung bình $(V^\beta-q)^2$, vì hai độ may rủi độc lập và có trung bình 0.

**Công cụ 4: kiểm WDL của mạng có đúng không.** Lần search lúc chơi còn cho xác suất hoà $d(s)$. Nếu cặp $(q,d)$ đúng trung bình, tức là trong các thế cờ có cùng $(q,d)$ thì kết quả trung bình đúng bằng $q$ và tỉ lệ hoà đúng bằng $d$, thì
$$\mathbb E\big[(z-q)^2\,\big|\,q,d\big]=\mathbb E[z^2\,|\,q,d]-2q\,\mathbb E[z\,|\,q,d]+q^2=(1-d)-2q^2+q^2=1-d-q^2.$$
Vậy khi đó $\mathbb E[1-d-q^2]=S$. Tỉ số $\mathbb E[1-d-q^2]/S$ bằng 1 khi WDL của mạng đúng trung bình, lớn hơn 1 khi mạng tưởng ván may rủi hơn thực tế, và nhỏ hơn 1 khi mạng tự tin quá mức. Đây chỉ là phép kiểm WDL, không phải cách tách $A$ với $B$: theo công cụ 3, mọi cách chia đều cho cùng tỉ số này.

**Sửa 21/11: nhóm phải lập theo thông tin đã biết ở $s$.** Bổ đề chỉ nói về trung bình khi biết những gì đã có ở $s$. Trung bình trên một nhóm vị trí vẫn đúng tuyệt đối nếu việc một vị trí thuộc nhóm nào chỉ phụ thuộc vào thông tin đã có ở $s$.

Khoảng cách tới cuối ván (số nửa nước còn lại của chính ván, hay `cach` trên cây) không thoả điều đó: nó chỉ biết được sau khi ván từ $s$ kết thúc. Vì vậy $\mathbb E[z-q\,|\,\text{khoảng cách}]$ không nhất thiết bằng độ lệch của $q$, kể cả khi $q$ không lệch. Trọng số trộn phụ thuộc khoảng cách còn tạo lệch cho nhãn: khi $w$ phụ thuộc độ dài của chính ván, nhãn $w\,q+(1-w)\,z$ có trung bình lệch thêm
$$\mathbb E\big[(1-w)(z-V)\big]=-\mathrm{Cov}(w,z).$$
Ví dụ, ở thế mà bên đi đang hơn, ván thắng thường kết thúc nhanh, còn ván dài hay là ván hoà. Nếu $w$ tăng theo khoảng cách như ở cách đang chạy (từ 0,10 lên 0,27), ván thắng nhanh được nhãn bám theo $z=+1$, còn ván hoà dài được nhãn bám theo $q>0$. Cả hai chiều đều đẩy nhãn lên trên giá trị thật. Độ lớn của hiệu ứng này chưa được đo.

Từ đây mọi nhóm lập theo thông tin đã có ở $s$. Mạng không có đầu dự đoán số nước còn lại (mạng được huấn luyện với `MOVES_LEFT_NONE`), nên nhóm $g(s)$ lập theo
$$p(s)=1-d(s)-q(s)^2,$$
là phương sai của kết quả mà WDL của lần search lúc chơi dự báo (công cụ 4). $p(s)$ được chia thành các khoảng có số vị trí bằng nhau, và có thể chia thêm theo số nửa nước đã đi từ đầu ván. Cách chia nhóm chỉ ảnh hưởng tới độ nhiễu của các số đo và độ tối ưu của trọng số, không làm số đo lệch.

### 12.4 Số đo trên lần chạy 5

**Nguồn dữ liệu.**

- Bản ghi mọi ván rẽ của các đời 10 đến 20, khoảng 5,1 triệu vị trí. Mỗi vị trí cho một bộ $(q,d,z)$, với $q$, $d$ lấy từ lần search lúc chơi và $z$ là kết quả của chính ván đó.
- Cây sau đời 20: 1,69 triệu node. Trong đó khoảng 1,58 triệu node sống đã search chỉ có một nhánh đã chơi, và khoảng 40 nghìn node rẽ có từ hai nhánh trở lên.
- Toàn bộ 1028 ván arena đời 20.

Mọi bảng chia theo khoảng cách tới cuối ván, đo bằng nửa nước, với các mốc của mục 7.1. Với dữ liệu ván, khoảng cách là số nửa nước còn lại của chính ván. Với dữ liệu cây, khoảng cách là `cach` của mã. Theo phần sửa 21/11 ở 12.3, khoảng cách là thông tin chỉ có sau khi ván kết thúc. Vì vậy số của từng khoảng không được bổ đề bảo đảm đúng tuyệt đối, chỉ trung bình trên toàn bộ là được bảo đảm. Các bảng cần đo lại theo nhóm $g(s)$ (12.10).

**Bảng 1. Độ lệch của giá trị search lúc chơi so với kết quả ván** (trung bình $z-q$, công cụ 1), và sai số RMS (căn của trung bình $(z-q)^2$):

| Khoảng cách | 0–5 | 5–10 | 10–20 | 20–40 | 40–80 | 80–160 | từ 160 |
|---|---|---|---|---|---|---|---|
| Lệch, đời 10 | −0,016 | +0,006 | −0,006 | −0,009 | −0,012 | −0,018 | −0,025 |
| Lệch, đời 15 | −0,012 | +0,004 | −0,004 | −0,006 | −0,007 | −0,010 | −0,014 |
| Lệch, đời 20 | −0,010 | +0,004 | −0,003 | −0,004 | −0,004 | −0,005 | −0,006 |
| RMS, đời 10 | 0,147 | 0,228 | 0,262 | 0,320 | 0,428 | 0,561 | 0,673 |
| RMS, đời 15 | 0,130 | 0,203 | 0,236 | 0,293 | 0,363 | 0,446 | 0,532 |
| RMS, đời 20 | 0,140 | 0,206 | 0,225 | 0,254 | 0,296 | 0,357 | 0,421 |

Mỗi đời có từ 410 đến 530 nghìn vị trí. Tách theo bên đi, độ lệch nằm trong khoảng $\pm0{,}03$ ở mọi ô, trừ khoảng từ 160 ở các đời đầu (đời 11: Trắng $-0{,}102$, Đen $+0{,}057$). Ở đời 20 khoảng đó còn $+0{,}011$ và $-0{,}022$. Đánh giá trộn theo $\pi$ (trung bình $Q$ của mọi nước, cân theo tỉ lệ lượt thăm) cũng lệch dưới 0,015 ở mọi ô.

**Bảng 2. $G$ so với $q$ trên cây đời 20** (trung bình $G-q$ theo góc bên đi, $q$ là $q$ gộp mà mã đang dùng):

| Khoảng cách | 0–5 | 5–10 | 10–20 | 20–40 | 40–80 | 80–160 | từ 160 |
|---|---|---|---|---|---|---|---|
| Node một nhánh: số node | 53 921 | 67 684 | 135 348 | 260 706 | 437 402 | 472 871 | 147 131 |
| Node một nhánh: $G-q$ | −0,009 | +0,004 | −0,004 | −0,005 | −0,006 | −0,008 | −0,009 |
| Node rẽ: số node | 540 | 1 108 | 2 551 | 6 147 | 12 203 | 13 889 | 4 048 |
| Node rẽ: $G-q$ | −0,012 | −0,009 | −0,019 | −0,035 | −0,055 | −0,073 | −0,064 |
| Node rẽ: phần $\rho$ ngoài nước nhiều lượt nhất | 0,32 | 0,39 | 0,43 | 0,51 | 0,58 | 0,62 | 0,66 |

**Bảng 3. Nước rẽ** (nhánh rẽ chỉ có một ván, nên kết quả $z$ của nhánh là mẫu của $Q^\beta(s,a)$; 41 498 nhánh, khoảng cách tính ở node cha):

| Khoảng cách | 0–5 | 5–10 | 10–20 | 20–40 | 40–80 | 80–160 | từ 160 |
|---|---|---|---|---|---|---|---|
| Số nhánh | 477 | 951 | 2 301 | 5 653 | 11 875 | 15 032 | 5 209 |
| $z-\hat Q(s,a)$ | +0,008 | −0,021 | −0,024 | −0,022 | −0,028 | −0,025 | −0,038 |
| $z-q(s)$ | −0,015 | −0,047 | −0,050 | −0,063 | −0,081 | −0,087 | −0,090 |
| Tỉ lệ $z>q(s)$ | 0,42 | 0,57 | 0,49 | 0,45 | 0,46 | 0,45 | 0,44 |

Theo mức $\hat Q$ của nước rẽ:

| $\hat Q$ của nước rẽ | từ −1 tới −0,6 | từ −0,6 tới −0,2 | từ −0,2 tới 0,2 | từ 0,2 tới 0,6 | từ 0,6 tới 1 |
|---|---|---|---|---|---|
| Số nhánh | 13 558 | 2 228 | 9 798 | 1 772 | 14 142 |
| $\hat Q$ trung bình | −0,939 | −0,386 | −0,001 | +0,388 | +0,955 |
| $z$ trung bình | −0,945 | −0,458 | −0,038 | +0,266 | +0,935 |

**Bảng 4. Cách mã chia sai số tổng** (công cụ 2 và 4; $S$ và tỉ số đo trên ván các đời 18 đến 20, khoảng 1,2 triệu vị trí; $E$, $\tau_q^2$, $w_q$ là số mã tính trên cây đời 20 ở node một nhánh):

| Khoảng cách | 0–5 | 5–10 | 10–20 | 20–40 | 40–80 | 80–160 | từ 160 |
|---|---|---|---|---|---|---|---|
| $S$ đo từ ván | 0,018 | 0,040 | 0,050 | 0,065 | 0,090 | 0,130 | 0,191 |
| $\mathbb E[1-d-q^2]/S$ | 1,23 | 1,01 | 1,02 | 1,02 | 1,00 | 0,91 | 0,75 |
| $E$ của mã (phần may rủi) | 0,003 | 0,005 | 0,007 | 0,013 | 0,023 | 0,040 | 0,064 |
| $\tau_q^2$ của mã (phần mạng sai) | 0,015 | 0,033 | 0,039 | 0,047 | 0,060 | 0,084 | 0,115 |
| Phần may rủi theo mã, $E/(E+\tau_q^2)$ | 0,15 | 0,12 | 0,16 | 0,21 | 0,27 | 0,32 | 0,36 |
| $w_q$ trung bình của mã | 0,10 | 0,10 | 0,13 | 0,17 | 0,21 | 0,24 | 0,27 |

Ở node một nhánh $G=z$, nên $E$ của mã chính là con số mã tin là $\mathrm{Var}(z\,|\,s)$, tức $B$. Còn $\tau_q^2$ là con số mã tin là $A$. Tổng $E+\tau_q^2$ khớp với trung bình $(G-q)^2$ trên cây, theo đúng cách xây phương pháp moment.

**Arena đời 20.** Tt thắng 205, hoà 38, thua 785. Ván dài trung vị 104 nửa nước. Ván được quyết định quanh nửa nước 40 (khoảng giữa từ 16 đến 65), lấy mốc là nửa nước đầu tiên mà bên thắng sau cùng tự đánh giá từ 0,5 trở lên và giữ tới hết ván. Giá trị của mỗi mạng lệch nhiều khi đem so với kết quả arena: tt lạc quan từ 0,8 đến 1,0 ở 60 nửa nước đầu, cây bi quan 0,5 ở 20 nửa nước đầu. Lý do là mỗi mạng học giá trị trong lúc tự chơi với chính nó, còn ở arena đối thủ là mạng kia. Vì vậy số liệu arena không dùng để đánh giá nhãn, chỉ dùng để biết ván được quyết định ở đâu.

### 12.5 Ba chỗ suy diễn không khớp thực tế

**Phần đứng vững.**

- Giá trị search lúc chơi gần như không lệch so với đích học $V^\beta$ ở mọi khoảng cách, và độ lệch nhỏ dần qua các đời (bảng 1).
- WDL của mạng đúng trung bình ở khoảng cách 5 đến 80 (bảng 4, tỉ số gần 1). Ở gần cuối ván mạng tưởng ván may rủi hơn thực tế (1,23), còn ở xa cuối ván thì mạng tự tin quá mức (0,91 và 0,75).
- Ở node một nhánh, $G$ là kết quả ván thuần, nên là nhãn không lệch cho $V^\beta$ (bảng 2, khớp với bảng 1).

**Chỗ 1: $G$ lệch có hệ thống ở node rẽ.** Bảng 2 cho thấy $G$ ở node rẽ thấp hơn $q$ từ 0,01 tới 0,07, và lệch tăng theo khoảng cách. Ở node một nhánh, lệch chỉ khoảng 0,005. Nguyên nhân có hai lớp.

1. **Sai đích.** Mục 3 coi giá trị thật là trung bình theo $\pi$. Nhưng ván thật đi nước nhiều lượt nhất, nên cả $z$ lẫn $q$ đều nói về $V^\beta$, mà $\beta$ dồn gần hết xác suất vào nhánh $\beta$.
2. **G2 sai đúng ở chỗ này.** G2 coi giá trị thật của các nước con dao động ngẫu nhiên quanh một mức chung, trung bình 0. Thực tế nước được search chọn có hệ thống tốt hơn nước rẽ, trung bình 0,05 đến 0,09 (bảng 3, dòng $z-q(s)$). Vì G2 coi chênh lệch đó là nhiễu trung bình 0, $\rho$ đặt 32% tới 66% khối lượng lên các nước rẽ, và $G$ bị kéo xuống khoảng (phần $\rho$ ngoài nhánh $\beta$) × (khoảng chênh). Ví dụ ở khoảng 80 đến 160: $0{,}62\times0{,}087\approx0{,}054$, cùng cỡ với lệch đo được 0,073.

Lệch này sinh ra từ công thức, không từ mạng, nên đời nào cây cũng tạo lại nó, và mạng học tốt hơn cũng không làm nó nhỏ đi. Mục 4.1 từng suy luận rằng bỏ nước chưa chơi làm $G$ lạc quan. Số đo cho thấy hiệu ứng bi quan ở trên mạnh hơn.

**Chỗ 2: cách chia sai số quyết định $w_q$ không được dữ liệu xác nhận.** Theo công cụ 3, dữ liệu của lần chạy không chứa thông tin nào để chia $S$ thành $A$ và $B$. Mã chia bằng cách cộng dồn $\omega^2U$ của G2 dọc đường đi, và kết quả là phần may rủi chỉ chiếm 12% đến 36% của $S$ (bảng 4). Từ đó $w_q$ chỉ từ 0,10 tới 0,27. Một cách chia khác, ví dụ phần may rủi chiếm gần hết $S$, khớp dữ liệu y như vậy, và nó cho $w_q$ gần 1. Như vậy con số quan trọng nhất của nhãn value đang dựa trên một lựa chọn mô hình chưa từng được kiểm. Các lần $\tau_q^2$ chạm sàn ở các đời 6, 8, 9 (mục 7.2) là triệu chứng của việc này. Ngoài ra $q$ gộp có cả các lần search lại bằng mạng đã học từ chính kết quả ván của node, nên giả định $c=0$ của mục 6 có thể sai. Với $q$ lúc chơi thì $c=0$ đúng tuyệt đối (công cụ 2).

**Chỗ 3: $\hat Q$ của nước không phải nước tốt nhất bị lạc quan, và nhãn policy mang theo cái lạc quan đó.** Ở mọi khoảng cách từ 5 trở lên, kết quả thật của nước rẽ thấp hơn $\hat Q$ của nó từ 0,02 tới 0,04. Ở vùng giữa, chênh lệch tới 0,12 (bảng 3: $\hat Q$ trung bình $+0{,}388$, kết quả $+0{,}266$). Đây đúng là kiểu lệch "lời nguyền người thắng": nước nào được search ước cao thì dễ được thăm thêm, nên các ước lượng cao thường cao quá. Nhãn policy trung bình $\pi$ là sản phẩm của search dùng chính các $\hat Q$ đó. Trong khi đó kết quả của 41 nghìn ván rẽ, mỗi kết quả là một mẫu không lệch của $Q^\beta(s,a)$, chưa được dùng cho nhãn policy.

### 12.6 Vì sao phải bỏ lệch có hệ thống: hai kết quả về lâu dài

**Định lý 9 (điểm dừng của vòng lặp nằm gần minimax).** Xét trò chơi hữu hạn, hai người, tổng bằng 0, thông tin đầy đủ, với luật hoà khi ván quá dài (đúng như cờ vua của dự án). Gọi $V^*$ là giá trị minimax và $Q^*(s,a)=-V^*(sa)$. Gọi độ cao $h(s)$ là số nửa nước nhiều nhất còn lại từ $s$ tới cuối ván. Giả sử vòng lặp sinh ván, học và search đã dừng ở một chính sách tất định $\beta$, tại mỗi thế cờ chọn nước làm một ước lượng $\tilde Q(s,\cdot)$ lớn nhất, với
$$\big|\tilde Q(s,a)-Q^\beta(s,a)\big|\le\varepsilon\quad\text{ở mọi }s,a.$$
Khi đó, ở mọi thế cờ,
$$\big|V^\beta(s)-V^*(s)\big|\le2\,h(s)\,\varepsilon.$$

**Chứng minh.** Quy nạp theo độ cao. Ở node kết thúc ($h=0$) cả hai giá trị bằng kết quả theo luật. Giả sử điều cần chứng minh đúng với mọi thế cờ có độ cao nhỏ hơn $h(s)$. Gọi $a=\beta(s)$ là nước $\beta$ chọn và $a^*$ là nước tốt nhất theo minimax.

- **Chặn trên.** $V^\beta(s)=Q^\beta(s,a)=-V^\beta(sa)\le-V^*(sa)+2(h-1)\varepsilon=Q^*(s,a)+2(h-1)\varepsilon\le V^*(s)+2(h-1)\varepsilon$.
- **Chặn dưới.** Vì $a$ làm $\tilde Q$ lớn nhất, $Q^\beta(s,a)\ge\tilde Q(s,a)-\varepsilon\ge\tilde Q(s,a^*)-\varepsilon\ge Q^\beta(s,a^*)-2\varepsilon$. Mà $Q^\beta(s,a^*)=-V^\beta(sa^*)\ge-V^*(sa^*)-2(h-1)\varepsilon=V^*(s)-2(h-1)\varepsilon$. Ghép lại được $V^\beta(s)\ge V^*(s)-2h\varepsilon$.

**Đọc định lý.** $\varepsilon$ là sai số mà search mắc khi đánh giá các nước theo chính cách chơi hiện tại. Nó gồm hai phần:

- **Sai số của mạng.** Phần này giảm khi mạng học thêm dữ liệu và có thêm sức chứa.
- **Lệch của nhãn.** Nếu nhãn lệch một lượng $b$ có hệ thống, thì mạng học đúng nhãn vẫn lệch $b$, và search mang theo lệch đó.

Định lý là một chặn trên. Phần thứ hai không giảm dù chạy bao lâu, nên chặn trên không bao giờ xuống dưới $2hb$, dù mạng tốt tới đâu. Nói cách khác, với lệch có hệ thống, vòng lặp mất bảo đảm tiến tới minimax. Định lý không chứng minh rằng khoảng cách thật lớn cỡ $2hb$. Nó cho thấy bỏ lệch có hệ thống là điều kiện để bảo đảm còn ý nghĩa khi sai số của mạng giảm. Đây là lý do chỗ 1 ở 12.5 được sửa trước tiên.

**Sửa 21/11.** Bản trước viết rằng lệch "đặt một cái sàn $2hb$ lên khoảng cách tới minimax". Câu đó nói quá điều định lý chứng minh: sàn đặt lên chặn trên, không đặt lên khoảng cách thật.

**Mệnh đề 10 (trộn với chính giá trị của mạng không tạo lệch lâu dài).** Giả sử nhãn là $w\,q+(1-w)\,Y$, với $Y$ không lệch so với $V^\beta$. Giả sử thêm hai điều lý tưởng: mạng học đúng trung bình của nhãn, và lệch của $q$ đúng bằng lệch của mạng. Khi đó nếu mạng ở đời $k$ lệch $b_k$, thì nhãn lệch $w\,b_k$, nên $b_{k+1}=w\,b_k$. Lệch co lại theo cấp số nhân với công bội $w<1$.

**Chứng minh.** Trung bình của nhãn là $w(V^\beta+b_k)+(1-w)V^\beta=V^\beta+w\,b_k$.

Vậy dùng $q$ trong nhãn là an toàn về lâu dài: nó làm chậm việc sửa sai chứ không tạo sai mới. Cái tạo sai mới là $Y$ lệch, như $G$ ở node rẽ.

### 12.7 Nhãn value mới

Nhãn value vẫn là một tổ hợp tuyến tính của $q(s)$ và các bằng chứng lấy từ cây, như mã đang chạy. Ba điều thay đổi:

- mọi bằng chứng nhắm đúng $V^\beta$;
- mọi trọng số lấy từ phương sai và hiệp phương sai **đo được** theo thiết kế;
- $q(s)$ và mọi bằng chứng được gộp trong **một** phép Gauss–Markov.

Bản 19/11 của mục này gộp hai tầng: gộp các nhánh thành $G(s)$ trước, rồi mới trộn $G(s)$ với $q(s)$. Ngày 21/11 tìm ra rằng cách gộp hai tầng đó không tối ưu, kể cả theo chính mô hình sai số của nó (cuối bước 3). Mọi tham số dưới đây tra theo nhóm $g(s)$ của 12.3, không theo khoảng cách tới cuối ván.

**Bước 1. Các bằng chứng tại $s$.** Mọi giá trị viết theo góc bên đi tại $s$, nên kết quả ván và $G$ của node con phải đổi dấu (đổi chỗ thắng với thua).

- **Các ván thuần từ $s$.** Gọi $P(s)$ là tập các ván thuần từ $s$, gồm ván đã tạo ra $s$ và các ván lặp đi qua $s$ (12.9). Ván $j$ có tuổi $t_j$ (số đời kể từ lúc ván được chơi) và nhận trọng số làm cũ $\gamma^{t_j}$ như mục 8.1. Bằng chứng là trung bình có trọng số của kết quả các ván đó:
$$x_P=\bar z(s)=\frac{\sum_{j\in P(s)}\gamma^{t_j}z_j}{\sum_{j\in P(s)}\gamma^{t_j}},\qquad N(s)=\frac{\big(\sum_{j}\gamma^{t_j}\big)^2}{\sum_{j}\gamma^{2t_j}}.$$
$N(s)$ là số ván hiệu dụng (số ván hiệu dụng này là số ván có trọng số bằng nhau cho cùng phương sai của trung bình). Ở lần chạy 5, mỗi node có $N=1$, và $x_P$ là kết quả của ván tạo ra node.
- **Giá trị search.** $q(s)$ và $\hat Q(s,\cdot)$ lấy từ lần search lúc chơi của ván thuần **mới nhất** tại $s$ (bước 6).
- **Mỗi nhánh rẽ.** Gọi $R(s)$ là tập các node con sinh ra từ ván rẽ có nước ép tại $s$. Nhánh rẽ cho bằng chứng về $Q^\beta(s,a)$, không phải về $V^\beta(s)$. Muốn đổi thành bằng chứng về $V^\beta(s)$ thì phải cộng khoảng chênh $V^\beta(s)-Q^\beta(s,a)$. Search ước khoảng chênh này là $q(s)-\hat Q(s,a)$, và ước đó lệch trung bình một lượng $o$ đo được. Vậy
$$x_a=G(c_a)+\big(q(s)-\hat Q(s,a)\big)-o(g),$$
với $G(c_a)$ tính ở bước 4 và
$$o(g)=\text{trung bình}\Big[\big(z_a-\hat Q(s,a)\big)-\big(z_\beta-q(s)\big)\Big],$$
lấy trên các node rẽ thuộc nhóm $g$ có đúng một ván thuần (kết quả $z_\beta$) và có nhánh rẽ chỉ một ván (kết quả $z_a$). Theo bổ đề thiết kế, hai kết quả là mẫu không lệch của $V^+(s)$ (12.3) và của $Q^\beta(s,a)$, nên $o(g)$ ước không lệch độ lệch trung bình của khoảng chênh mà search ước. Đo ngày 22/11 trên cây đời 20 (12.14) cho $o=+0{,}011$ chung và $+0{,}057$ ở nhóm $p$ cao. Ước tính cũ "$-0{,}02$ tới $-0{,}035$" sai dấu, vì nó lấy độ lệch của $z_\beta-q$ bằng trung bình mọi vị trí, trong khi ở các node có nhánh rẽ độ lệch này khác nhiều.

Ván rẽ không phải ván thuần từ $s$ (nước tại $s$ bị ép), nên nó không nằm trong $P(s)$. Vì vậy không kết quả nào bị đếm hai lần.

**Bước 2. Cấu trúc sai số.** Đặt bốn sai số:
$$u=q(s)-V^\beta(s),\qquad e_P=\bar z(s)-V^\beta(s),\qquad n_a=G(c_a)-Q^\beta(s,a),$$
$$g_a=\big(q(s)-\hat Q(s,a)\big)-\big(V^\beta(s)-Q^\beta(s,a)\big)-o(g).$$
$g_a$ là sai số của khoảng chênh. Khi đó $q-V^\beta=u$, $x_P-V^\beta=e_P$ và $x_a-V^\beta=n_a+g_a$.

Bổ đề thiết kế cho hai điều không cần giả định:

- $e_P$ có trung bình 0 khi biết mọi thứ ở $s$, nên không tương quan với $u$, $g_a$ hay $n_a$. Các ván trong $P(s)$ độc lập với nhau khi biết $s$, nên $\mathrm{Var}(e_P)=B(g)/N(s)$, với $B(g)$ là độ may rủi của một ván thuần ở nhóm $g$.
- $n_a$ có trung bình 0 khi biết mọi thứ trước lúc ván rẽ chơi, nên không tương quan với $u$ và $g_a$. Phương sai của nó là $E(c_a)$ (bước 4).

Hai chỗ xấp xỉ, ghi lại ở 12.12. Thứ nhất, ván thuần mới nhất dùng chung lần search tại $s$ với $q$, nên $e_P$ và $u$ chung phần may rủi $\delta_s$ của việc chọn nước tại $s$ (12.3). Phần này nhỏ khi nhiễu hầu như không đổi được nước đi. Thứ hai, các ván thuộc những đời khác nhau không cùng phân phối.

Riêng $u$ và $g_a$ thì có thể tương quan với nhau, vì cả hai cùng đến từ một lần search bằng một mạng. Đặt $w_a=\hat Q(s,a)-Q^\beta(s,a)$, sai số của search trên nước $a$, thì $g_a=u-w_a-o$. Có bốn tham số, mỗi tham số tra theo nhóm:

- $A(g)=\mathrm{Var}(u)$ là sai số của $q$;
- $\Gamma(g)=\mathrm{Var}(g_a)$ là sai số của khoảng chênh;
- $\kappa(g)=\mathrm{Cov}(u,w_a)$, nên $\mathrm{Cov}(u,g_a)=A-\kappa$;
- $\eta(g)=\mathrm{Cov}(g_a,g_b)$ với hai nước rẽ $a\ne b$ ở cùng một node.

Với vector bằng chứng $y=(q,\ x_P,\ x_{a_1},\dots,x_{a_k})$, ma trận hiệp phương sai sai số là
$$\Sigma=\begin{pmatrix}A&0&(A-\kappa)\,\mathbf 1^\top\\0&B/N&0\\(A-\kappa)\,\mathbf 1&0&D+\eta\,(\mathbf 1\mathbf 1^\top-I)\end{pmatrix},\qquad D=\mathrm{diag}\big(E(c_a)+\Gamma\big)_{a\in R(s)}.$$
Bản 19/11 ngầm đặt $\kappa=0$, $\Gamma=A+\sigma_w^2$ và $\eta=A$, tức là coi sai số của search tại $s$ và sai số trên nước rẽ không liên quan gì với nhau.

**Bước 3. Gộp tối ưu một lần (định lý Gauss–Markov).** Trọng số và nhãn là
$$\lambda=\frac{\Sigma^{-1}\mathbf 1}{\mathbf 1^\top\Sigma^{-1}\mathbf 1},\qquad \text{nhãn value}=\lambda^\top y,\qquad \text{sai số bình phương của nhãn}=\frac{1}{\mathbf 1^\top\Sigma^{-1}\mathbf 1}.$$
Định lý Gauss–Markov nói rằng trong mọi tổ hợp tuyến tính không lệch của các bằng chứng (tổ hợp không lệch này là tổ hợp có tổng trọng số bằng 1), tổ hợp này có phương sai nhỏ nhất. Phần nhánh rẽ của $\Sigma$ là một ma trận chéo cộng một ma trận hạng một, nên $\Sigma^{-1}$ có dạng đóng: công thức Sherman–Morrison cho khối nhánh rẽ, rồi nghịch đảo theo khối. Vì vậy mã tính được cho mọi node cùng lúc theo mảng, không phải giải hệ phương trình cho từng node.

Hai trường hợp riêng:

- **Node không có nhánh rẽ.** Nhãn là $w\,q+(1-w)\,\bar z$ với
$$w=\frac{B/N}{A+B/N}.$$
Khi $N=1$ thì $w=B/S$, đúng bằng tỉ lệ ở công cụ 2.
- **Khi $\kappa=0$, nhánh rẽ nhận trọng số 0.** Lý do: khi đó $x_a-q=n_a+g_a-u=n_a-w_a-o$, và hiệu này không tương quan với $V^\beta-q=-u$, tức là $x_a$ chỉ là $q$ cộng một nhiễu riêng. Viết nhãn là $\alpha\,q+b\,x_P+\sum_a c_ax_a$ với tổng hệ số bằng 1. Sai số của nó là $\big(\alpha+\sum_a c_a\big)u+b\,e_P+\sum_a c_a\,(n_a-w_a-o)$. Giữ cố định $\alpha+\sum_a c_a$ thì phương sai nhỏ nhất khi mọi $c_a=0$.

Như vậy nhánh rẽ chỉ giúp được $s$ khi $\kappa\ne0$, tức là khi sai số của search tại $s$ và sai số trên nước rẽ có tương quan. Thực tế $\kappa$ có lẽ dương: mạng đánh giá cao một thế cờ thì thường cũng đánh giá cao mọi nước đi từ thế đó. Chính lý do "search ước khoảng chênh tốt hơn ước từng giá trị", lý do để dùng khoảng chênh, cần $\kappa>0$. Đo ngày 22/11 (12.14): $\kappa$ dương ở các nhóm có sai số lớn, nhưng chỉ bằng khoảng 0,13 lần $S$, nên nhánh rẽ nhận trọng số 2,5% tới 10%, không phải 0 và cũng không phải 12,1% như ví dụ dưới đây.

**Sửa 21/11: vì sao bỏ cách gộp hai tầng.** Bản 19/11 tính $G(s)$ từ nhánh $\beta$ và nhánh rẽ, rồi trộn $w\,q+(1-w)\,G$ với $w=(E-\rho_RA)/(E+A-2\rho_RA)$. Theo chính mô hình của nó ($\kappa=0$), cách đó đặt trọng số $(1-w)\rho_R>0$ lên nhánh rẽ, trong khi trọng số tốt nhất là 0. Ở ví dụ bên dưới, cách gộp hai tầng có sai số bình phương 0,0168, còn gộp một lần cho 0,0156.

**Bước 4. Giá trị gửi lên node cha.** Node cha cần $G(s)$ và $E(s)$ khi $s$ là một nhánh rẽ của nó (bước 1 của node cha). $G(s)$ là tổ hợp Gauss–Markov của $(x_P,x_{a_1},\dots,x_{a_k})$, tức là cùng phép tính ở bước 3 nhưng bỏ hàng và cột của $q$. $E(s)$ là sai số bình phương của nó.

- Node không có nhánh rẽ có $G(s)=\bar z(s)$ và $E(s)=B(g)/N(s)$.
- Node kết thúc có $G$ là kết quả theo luật và $E=0$.
- Node gốc cắt giữ $G$ và $E$ đã lưu như hiện nay.

Node cha **không** dùng $G$ của nhánh $\beta$. Mọi ván thuần từ node cha đi qua nhánh $\beta$ cũng là ván thuần từ chính nhánh đó, và chúng đã nằm trong $x_P$ của node cha, nên dùng thêm $G$ của nhánh $\beta$ là đếm hai lần. Đây là chỗ khác bản 19/11 (bản đó dùng $x_\beta=G(c_\beta)$). Cái mất là các nhánh rẽ nằm bên dưới nhánh $\beta$ không còn góp vào nhãn của node cha. Theo bước 3, khi $\kappa=0$ chúng cũng chỉ mang thêm giá trị search ở tầng dưới. Giá trị search dọc ván thuần có thể đưa thẳng vào làm bằng chứng nếu cần (12.12).

**Bước 5. Đo các tham số.** Mọi phép đo dưới đây làm theo nhóm $g$, và mỗi phép đo đúng về trung bình theo bổ đề thiết kế:

- $S(g)$: trung bình $(z-q)^2$ trên các ván thuần, với $q$ lúc chơi (công cụ 2). Đo lại mỗi đời.
- $\hat B(g)$: đo từ cặp ván lặp (12.9). Khi đó $A(g)=S(g)-\hat B(g)$.
- $o(g)$: như bước 1.
- $\kappa(g)$: hiệp phương sai mẫu của $\big(z_\beta-q(s)\big)$ và $\big(z_a-\hat Q(s,a)\big)$, trên các node rẽ có một ván thuần và nhánh rẽ một ván. Lý do: $z_\beta-q=e_P-u$ và $z_a-\hat Q=n_a-w_a$, và trong bốn tích chéo chỉ còn $\mathrm{Cov}(u,w_a)$. Phép đo này làm được ngay trên cây đời 20, không cần chạy thêm. Đã đo ngày 22/11: $\hat\kappa$ dương, bằng khoảng 0,13 lần $S$ (12.14).
- $\Gamma(g)$: trên cùng các node đó, $\mathbb E\big[(x_a-z_\beta)^2\big]=E(c_a)+\Gamma+B$, nên $\Gamma=\text{trung bình}\big[(x_a-z_\beta)^2\big]-E(c_a)-\hat B(g)$.
- $\eta(g)$: trên các node có một ván thuần và hai nhánh rẽ một ván, $\mathbb E\big[(x_a-z_\beta)(x_b-z_\beta)\big]=\eta+B$. Nếu nhóm có quá ít node như vậy, đặt $\eta=A-2\kappa$. Cách đặt này giả định sai số của search trên hai nước khác nhau không tương quan.

Hai quy tắc khi số đo nhiễu:

- Một phương sai ước ra âm (do phép trừ) thì đặt bằng 0 và ghi log.
- $\Sigma$ không xác định dương thì co $\kappa$ về 0 cho tới khi xác định dương, và ghi log.

Nếu log cho thấy hai quy tắc này chạm thường xuyên ở một nhóm, nhóm đó chưa đủ dữ liệu.

**Bước 6. Dùng $q$ lúc chơi.** $q(s)$ và $d(s)$ là của lần search ở ván thuần tại $s$, không phải trung bình gộp có các lần search lại. Hai lý do: hiệp phương sai giữa $q$ và kết quả của chính ván đó đúng là 0 (công cụ 2, với $V^+$ của 12.3), và nhãn không bị kéo về các lần search bằng mạng đã học từ chính kết quả đó. Khi $s$ có nhiều ván thuần, lấy lần search của ván mới nhất, vì mạng mới nhất sai ít nhất. Sai số của $q$ đó có thể tương quan với độ may rủi của các ván cũ hơn, vì mạng mới đã học từ kết quả của chúng. Các ván cũ có trọng số $\gamma^{\text{tuổi}}$ nhỏ, và 12.12 ghi chỗ này là chỗ còn hở.

**Bước 7. Dạng thắng, hoà, thua.** Các trọng số ở bước 3 và 4 tính trên giá trị một chiều (thắng trừ thua), rồi dùng nguyên cho cả bộ ba. Phép trừ khoảng chênh ở bước 1 làm riêng cho số một chiều và cho xác suất hoà. Bộ ba được dựng lại bằng $\big((1+v-d)/2,\ d,\ (1-v-d)/2\big)$, chặn mỗi thành phần ở 0 rồi chuẩn hoá lại.

**Ví dụ** (số giả định để thấy phép tính). Node $s$ có $q(s)=+0{,}10$ và một ván thuần với kết quả $-0{,}25$. Node có một nhánh rẽ một ván, với $\hat Q(s,a)=-0{,}05$ và kết quả $+0{,}50$.

- Tham số: $B=0{,}070$, $A=0{,}02$, $E(c_a)=0{,}069$, $o=-0{,}03$.
- Bằng chứng: $x_P=-0{,}25$ và $x_a=0{,}50+(0{,}10+0{,}05)+0{,}03=0{,}68$.

Xét hai giá trị của $\kappa$. Ở cả hai trường hợp, $\Gamma=A+\sigma_w^2-2\kappa$ với $\sigma_w^2=0{,}03$:

| | $\kappa=0$, $\Gamma=0{,}05$ | $\kappa=0{,}015$, $\Gamma=0{,}02$ |
|---|---|---|
| Trọng số của $q$; ván thuần; nhánh rẽ | 0,778; 0,222; 0 | 0,677; 0,202; 0,121 |
| Nhãn value | $+0{,}022$ | $+0{,}099$ |
| Sai số bình phương của nhãn | 0,0156 | 0,0141 |
| $G(s)$ gửi lên node cha, kèm $E(s)$ | $+0{,}094$ (0,044) | $+0{,}159$ (0,039) |

Cũng với các số này và $\kappa=0$, cách gộp hai tầng của bản 19/11 cho nhãn $+0{,}098$ với sai số bình phương 0,0168. Cách đang chạy cho $G=+0{,}080$ ở cùng node (mục 3), vì $\rho$ trộn thẳng $+0{,}50$ của nước rẽ mà không trừ khoảng chênh.

Đọc ví dụ: ván rẽ đi một nước mà search chê ($-0{,}05$) nhưng lại thắng ($+0{,}50$). Nó chỉ làm nhãn của $s$ thay đổi khi $\kappa>0$. Khi $\kappa=0$, nó không cho biết gì về $s$ mà $q(s)$ chưa cho biết. Vì vậy $\kappa$ là con số quyết định nhánh rẽ có vào nhãn value hay không, và nó đo được ngay trên cây đang có.

### 12.8 Nhãn policy: giữ trung bình $\pi$, thêm phần sửa tuỳ chọn

**Định lý 11 (cơ sở của nhãn trung bình $\pi$).** Grill và cộng sự (ICML 2020) chỉ ra rằng tỉ lệ lượt thăm của search kiểu PUCT bám theo nghiệm của bài toán
$$\bar\pi=\arg\max_y\Big[\sum_ay_a\hat Q(s,a)-\lambda_N\,\mathrm{KL}(p\,\|\,y)\Big],$$
với $p$ là prior (đã trộn nhiễu), $\lambda_N>0$ là một hệ số giảm dần theo số lượt thăm $N$ (công thức cụ thể ở bài gốc), và KL là độ lệch Kullback–Leibler. Khi đó
$$\sum_a\big(\bar\pi(a)-p(a)\big)\hat Q(s,a)\;\ge\;\lambda_N\,\mathrm{KL}(p\,\|\,\bar\pi)\;\ge\;0.$$
**Chứng minh.** $\bar\pi$ là nghiệm, nên nó không thua lựa chọn $y=p$, mà với $y=p$ thì số hạng KL bằng 0: $\bar\pi\cdot\hat Q-\lambda_N\mathrm{KL}(p\|\bar\pi)\ge p\cdot\hat Q$.

Như vậy, đo bằng chính giá trị của search, đầu ra của search luôn tốt hơn prior ít nhất $\lambda_N\mathrm{KL}$. Nhãn trung bình $\pi$ là trung bình có trọng số của các đầu ra như vậy, và bất đẳng thức tuyến tính nên được giữ khi lấy trung bình. Đầu policy học trung bình của nhãn, nên prior đời sau là một chính sách tốt hơn prior đời trước theo nghĩa trên. Lặp lại qua các đời, đây là lặp chính sách trong không gian prior. Nó chỉ dừng khi KL bằng 0, tức là khi prior đã trùng với đầu ra của search. **Vậy nhãn trung bình $\pi$ có cơ sở toán học, và được giữ làm nền.**

**Chỗ yếu, đo bằng giá trị thật.** Đo bằng $Q^\beta$ thay cho $\hat Q$:
$$\sum_a(\bar\pi-p)(a)\,Q^\beta(s,a)=\sum_a(\bar\pi-p)(a)\,\hat Q(s,a)+\sum_a(\bar\pi-p)(a)\big(Q^\beta(s,a)-\hat Q(s,a)\big).$$
Số hạng đầu không âm. Số hạng sau âm khi search dồn xác suất vào những nước mà $\hat Q$ ước cao quá, và bảng 3 cho thấy điều đó xảy ra: nước không phải nước tốt nhất bị ước cao trung bình 0,02 tới 0,04, ở vùng giữa tới 0,12. Phần sửa dưới đây nhắm đúng số hạng này.

**Phần sửa tuỳ chọn: dùng kết quả ván để sửa giá trị, rồi dựng lại đầu ra của search.** Làm ở node có nhánh rẽ, với mọi nước đã chơi (cả nhánh $\beta$ lẫn nhánh rẽ). Với mỗi nước $a$ có node con $c_a$:

1. **Bỏ phần lạc quan trung bình.** $\tilde Q(s,a)=\hat Q(s,a)+o_Q(g)$, với $o_Q(g)$ là trung bình $z_a-\hat Q(s,a)$ của các nhánh một ván cùng nhóm $g$ (bảng 3, dòng thứ hai, là số đo theo khoảng cách). Với nhánh $\beta$ dùng trung bình $z-q$ của cùng nhóm (bảng 1).
2. **Kéo về phía kết quả ván theo nghịch đảo phương sai.**
$$Q'(s,a)=\tilde Q(s,a)+k_a\big(G(c_a)-\tilde Q(s,a)\big),\qquad k_a=\frac{\sigma_Q^2(g)}{\sigma_Q^2(g)+E(c_a)}.$$
   - $\sigma_Q^2(g)$ là phương sai sai số của $\hat Q$, đo bằng trung bình $(z_a-\tilde Q)^2$ trừ trung bình $E(c_a)$, theo cùng phép tách của công cụ 2.
   - Với nhánh $\beta$, $\sigma_Q^2=A(g)$.
   - $G(c_a)$ và $E(c_a)$ tính theo bước 4 của 12.7.
   - Vì sai số của $\tilde Q$ và độ may rủi của ván không tương quan (bổ đề thiết kế), sai số bình phương của $Q'$ là $\sigma_Q^2E/(\sigma_Q^2+E)$, nhỏ hơn cả $\sigma_Q^2$ lẫn $E$. Đây là phép tính đúng tuyệt đối khi đã biết hai phương sai, không cần giả định phân phối chuẩn.
3. **Dựng lại đầu ra của search với $Q'$.** Dùng đúng công thức của mục 10. Dựng prior ngầm $w_a=\pi(a)\big(\beta_0-\hat Q(s,a)\big)$ từ $\pi$ và $\hat Q$ đã lưu, với $\beta_0$ chọn như mục 10.1. Rồi đặt $\pi'(a)=w_a/\big(\alpha-Q'(s,a)\big)$ với $\alpha$ chọn sao cho tổng bằng 1. Nước chưa chơi giữ $Q'=\hat Q$. Node không có nhánh rẽ giữ nhãn $\pi$.

**Điều phần sửa bảo đảm.**

- Theo mục 10.3: $\sum_a(\pi'-\pi)(a)\big(Q'(s,a)-\hat Q(s,a)\big)\ge0$, tức nhãn dịch về phía các nước mà kết quả ván cho thấy tốt hơn search nghĩ.
- Theo mục 10.2 và định lý 11: $\pi'$ là nghiệm của cùng bài toán có điều chuẩn, chỉ thay $\hat Q$ bằng $Q'$. Nên $\pi'$ có đúng loại bảo đảm của $\pi$, tốt hơn prior ngầm ít nhất $\lambda\mathrm{KL}$, nhưng đo bằng những giá trị có sai số nhỏ hơn (bước 2).
- Phản ví dụ ở mục 10.4 vẫn còn: $\pi'$ không phải lúc nào cũng tốt hơn chính $\pi$ khi đo bằng $Q'$. Vì vậy phần sửa là tuỳ chọn, chỉ bật khi phép thử offline (12.10) cho thấy nó tốt hơn.

Mục 10 từng tắt nhãn này vì mô phỏng cho thấy nó hại khi $E$ sai. Ở bản nâng cấp, $k_a$ dùng phương sai đo được thay cho $E$ của G2, nên lý do tắt cũ không còn. Nhưng chưa có phép thử mới thì chưa bật.

### 12.9 Ván lặp: đo phần may rủi $B$ ngay trong vòng lặp

Theo công cụ 3, phần may rủi $B$ là phép đo duy nhất mà dữ liệu mỗi thế cờ một ván không tự cung cấp được: muốn đo nó phải có hai ván thuần độc lập từ cùng một thế cờ. Bản 19/11 đề xuất một thí nghiệm riêng, chạy một lần ngoài vòng lặp. Ngày 21/11 chủ dự án cho nới các quy tắc search lại (mục 8.5), chỉ giữ trần 20% ngân sách. Nhờ vậy phép đo này chạy được ngay trong vòng lặp, bằng ván lặp.

**Ván lặp** (ván lặp này là một ván bắt đầu tại một node đã có trong cây, không có nước ép, chơi tới hết bằng mạng của đời hiện tại với đúng thiết lập của ván rẽ: 800 lượt thăm, nhiễu Dirichlet ở gốc, đi nước nhiều lượt thăm nhất, dùng lại cây trong ván). Engine không phải sửa, vì đây là một việc dạng ván rẽ có đường đi từ gốc tới node và không có nước ép. Một ván lặp bắt đầu ở node $s$ tác động lên cây như sau:

1. Lần search đầu của ván nằm tại $s$. Nó là một lần search lại $s$, nên nhãn $\pi$ của $s$ được làm mới như hiện nay.
2. Khi ván còn đi qua các node đã có, mỗi lần search ở đó cũng được cộng vào node đó như một lần search lại.
3. Khi ván rời đường cũ, nó tạo node mới như ván rẽ, và là ván thuần của các node mới này.
4. Nó là ván thuần từ $s$ và từ mọi node nó đi qua, nên được cộng vào tập $P(\cdot)$ của các node đó (12.7, bước 1).

Lần search đầu của ván lặp bắt đầu với cây trống, trong khi ván thuần gốc có thể đã dùng lại cây của nước trước. Đây là khác biệt nhỏ duy nhất so với ván thuần gốc.

**Cặp ván lặp phải cùng một đời.** Hai ván do hai mạng khác nhau chơi từ cùng $s$ thì độc lập nhưng không cùng phân phối, và
$$\tfrac12\,\mathbb E\big[(z_1-z_2)^2\big]=\tfrac12\big(B_1+B_2\big)+\tfrac12\big(V^{\beta_1}(s)-V^{\beta_2}(s)\big)^2.$$
Số hạng sau làm $B$ đo được bị thổi lên theo độ thay đổi của cách chơi giữa hai đời. Vì vậy mỗi cặp gồm hai ván lặp từ cùng một node trong cùng một đời (cùng một mạng). Ván đã tạo ra node không dùng để ghép cặp. Hai ván trong cặp có thể chạy song song trên hai máy.

**Ước lượng (đúng về trung bình, công cụ 3).** Với mỗi cặp, ghi hai kết quả $z_1$, $z_2$ theo góc bên đi tại $s$, và $q_1$ là giá trị search lúc chơi tại $s$ của ván thứ nhất. Trong mỗi nhóm $g$:
$$\hat B=\text{trung bình}\ \tfrac12(z_1-z_2)^2,\qquad\hat A=\text{trung bình}\ (z_1-q_1)(z_2-q_1).$$
$q_1$ tính xong trước khi ván 1 đi tiếp, và ván 2 độc lập với ván 1, nên mỗi thừa số có trung bình đúng như công cụ 3 cần. Theo phần sửa ở 12.3, $\hat B$ đo $B+\mathrm{Var}(\delta_s)$.

Kiểm chéo: $\hat A+\hat B$ phải gần $S(g)$. Phần chênh bằng $\mathrm{Var}(\delta_s)+\mathrm{Cov}(q-V^+,\delta_s)$, và nhỏ khi hai ván trong cặp hầu như luôn đi cùng một nước đầu. Ghi tỉ lệ các cặp có nước đầu khác nhau để biết điều đó.

**Chọn node.** Nhóm $g(s)$ của một node tính từ $q$ và $d$ của lần search lúc chơi mới nhất đã có tại node, nên biết được trước khi cặp được chơi. Trong mỗi nhóm, node được bốc ngẫu nhiên đều trong các node sống, đã search, chưa kết thúc. Bốc đều khớp với quy tắc học mỗi node một lần (mục 9).

**Cần bao nhiêu cặp.** Đặt $X=\tfrac12(z_1-z_2)^2$. $X$ chỉ nhận ba giá trị 0, $\tfrac12$ và 2, nên $X^2\le2X$ và $\mathrm{Var}(X)\le2B$. Với $n$ cặp, sai số chuẩn của $\hat B$ không quá $\sqrt{2B/n}\le\sqrt{2S/n}$. Tỉ lệ trộn ở node một ván là $w=B/S$, nên sai số chuẩn của $\hat w$ không quá
$$\sqrt{\frac{2}{nS}},\qquad\text{tức là cần}\quad n\ge\frac{2}{\mathrm{SE}^2\,S}.$$
Bảng dưới lấy $S$ của bảng 4, tức là theo khoảng cách. Nhóm thật lập theo $p(s)$, nên số cặp sẽ được tính lại với $S(g)$ đo được; bảng chỉ cho biết cỡ. Chi phí tính bằng số lần search: mỗi cặp gồm hai ván, mỗi ván tốn khoảng (khoảng cách + 1) lần search, và mỗi lần search khoảng 490 lần chạy mạng (mục 8.6).

| Khoảng cách | 0–5 | 5–10 | 10–20 | 20–40 | 40–80 | 80–160 | từ 160 |
|---|---|---|---|---|---|---|---|
| $S$ | 0,018 | 0,040 | 0,050 | 0,065 | 0,090 | 0,130 | 0,191 |
| Số cặp cho SE của $w$ là 0,15 | 4 940 | 2 220 | 1 780 | 1 370 | 990 | 680 | 470 |
| Số lần search (nghìn) | 40 | 36 | 57 | 85 | 120 | 165 | 190 |

Tổng khoảng 690 nghìn lần search, tức khoảng $3{,}4\times10^8$ lần chạy mạng.

**Chi phí trong trần 20%.** Ván rẽ đời 20 dùng khoảng 410 nghìn lần search. Nếu đó là 80% ngân sách và trần 20% được dùng hết, phần dành cho search lại vào khoảng 100 nghìn lần search mỗi đời. Khi đó:

- sai số chuẩn 0,15 trên $w$ cần khoảng 7 đời dùng cả trần;
- sai số chuẩn 0,2 (khoảng 56% chi phí trên) cần khoảng 4 đời;
- một lần chạy thử bằng 10% kế hoạch vừa trong một đời.

Nếu muốn có $\hat B$ trước khi đổi vòng lặp, vẫn có thể chạy riêng một lần như bản 19/11. Cách đó dùng cùng ước lượng và tốn khoảng 1,7 đời ngân sách ván rẽ cho sai số chuẩn 0,15.

**Chia trần 20%.** Trong trần có ba loại việc: cặp ván lặp, ván lặp đơn, và search lại đơn như mục 8.5. Đề xuất chia như sau:

1. **Đời đầu:** chạy thử 10% kế hoạch cặp. Phương sai thật của $X$ đo được sẽ cho số cặp cần thiết, thường ít hơn cận $\mathrm{Var}(X)\le2B$ (cận này là trường hợp xấu nhất).
2. **Cho tới khi sai số chuẩn của $w$ ở mọi nhóm đạt 0,2:** dùng cả trần cho cặp ván lặp. Các lần search của cặp trên đoạn trùng đường cũ vẫn làm mới $\pi$ của các node đó.
3. **Sau đó:** khoảng 5% ngân sách cho các cặp duy trì, để $B$ được đo lại mỗi đời và theo dõi được độ trôi khi cách chơi mạnh lên. Khoảng 15% còn lại chia giữa ván lặp đơn và search lại đơn:
   - Ván lặp đơn đặt ở node làm sai số bình phương của nhãn giảm nhiều nhất trên mỗi lần search. Với node không có nhánh rẽ, thêm một ván làm sai số đi từ $f(N)$ xuống $f(N+1)$, với $f(N)=A\,(B/N)/(A+B/N)$. Chi phí ước như mục 8.6. Ví dụ với $A=0{,}03$ và $B=0{,}06$ (số giả định), $f$ lần lượt là 0,020; 0,015 và 0,012 khi node có 1, 2 và 3 ván.
   - Search lại đơn giữ công thức ưu tiên của 8.5.
   - Tỉ lệ chia giữa hai loại này quyết định bằng phép thử ở 12.10.

**Cái giá.** Một lần search lại đơn tốn một lần search và làm mới một node. Một ván lặp tốn (khoảng cách + 1) lần search, và chỉ làm mới các node trên đoạn nó trùng với đường cũ. Vì vậy số node có $\pi$ được làm mới mỗi đời sẽ giảm. Mức giảm sẽ đo trong lần chạy thử.

### 12.10 Thứ tự làm và cách kiểm

1. **Đo ngay trên dữ liệu đang có, không chạy thêm** (đã làm một phần ngày 22/11, kết quả ở 12.14):
   - làm lại bảng 1 đến 4 theo nhóm $g(s)$ thay cho khoảng cách;
   - đo phần lệch do chia theo khoảng cách ở cách đang chạy: hiệp phương sai giữa $w_q$ và $z$ trong mỗi nhóm $g$, và trung bình của nhãn cũ so với trung bình $z$ theo nhóm $g$;
   - đo $\kappa(g)$, $o(g)$, $\eta(g)$ và $\Gamma(g)$ (với $B$ tạm) trên cây đời 20. $\kappa$ quyết định nhánh rẽ có vào nhãn value hay không.
2. **Bật ván lặp theo cặp** trong trần 20%: chạy thử 10% kế hoạch, rồi chạy tiếp tới khi sai số chuẩn của $w$ đạt 0,2. Có $\hat B(g)$ và $\hat A(g)$; kiểm $\hat A+\hat B\approx S(g)$ và tỉ lệ cặp có nước đầu khác nhau.
3. **Tính lại nhãn offline trên cây** bằng 12.7, rồi kiểm:
   - ở node rẽ, trung bình $G-q$ phải về ngang node một nhánh (khoảng $-0{,}005$) thay vì $-0{,}01$ tới $-0{,}07$;
   - phân phối của các trọng số theo nhóm;
   - nhãn mới khác nhãn cũ bao nhiêu, ở đâu.
4. **Huấn luyện lại từ cây** với nhãn cũ và nhãn mới, rồi so trên tập ván thuần giữ riêng. Cách so này đúng tuyệt đối. Với $z$ là kết quả của một ván thuần không dùng để làm nhãn, và $f$ là dự đoán của mạng tại vị trí đầu của ván đó, ta có
$$\mathbb E\big[(f-z)^2\big]=\mathbb E\big[(f-V^\beta)^2\big]+\mathrm{Var}(z\,|\,s).$$
   $\mathrm{Var}(z\,|\,s)=B+\mathrm{Var}(\delta_s)$ không phụ thuộc mạng, nên mạng nào có sai số bình phương với $z$ nhỏ hơn thì gần $V^\beta$ hơn, không cần biết $B$.
5. **Phần sửa policy** (12.8) thử riêng theo cùng cách: so mạng học nhãn $\pi$ với mạng học nhãn $\pi'$ trên tập giữ riêng, rồi arena.
6. **Chạy thật** từ cây đời 20 với nhãn mới, mục 8 giữ nguyên trừ quy tắc search lại theo 12.9, arena với cách truyền thống như cũ. Mốc để so là 78,2% của đời 20.

**Chỗ sẽ phải sửa trong mã khi được duyệt** (chưa làm):

- `nap_lan`:
  - mỗi node lưu tổng trọng số và tổng kết quả (đã làm cũ) của các ván thuần, cùng $q$, $d$, $\hat Q$ của lần search lúc chơi mới nhất và số nửa nước tính từ đầu ván;
  - ván lặp đi qua node đã có thì cộng lần search vào node đó như search lại và cộng một ván thuần; rời đường cũ thì tạo node như ván rẽ.
- `lap_viec`: thêm việc ván lặp (đường đi tới node, không nước ép), lập cặp, và chia trần như 12.9.
- `tinh`: thay $\omega^2$, $\rho$, $\nu$ bằng bước 1 đến 4 của 12.7, dùng dạng đóng của $\Sigma^{-1}$ để tính theo mảng.
- `nhan`:
  - nhãn theo bước 3, 6, 7;
  - thêm vào `meta` các bảng theo nhóm $S$, $\hat B$, $A$, $o$, $\kappa$, $\Gamma$, $\eta$, $o_Q$, $\sigma_Q^2$, và số lần chạm các quy tắc ở bước 5, kèm log mỗi đời.
- Một công tắc cho phần sửa policy, mặc định tắt.
- Mục 8 chỉ đổi phần ưu tiên search lại (8.5); trần 20% giữ nguyên.

### 12.11 So sánh trước và sau

| Phần | Đang chạy | Nâng cấp |
|---|---|---|
| Đích học | Trung bình theo $\pi$ (mục 3), không khớp cách chơi | $V^\beta$, đúng cách ván được chơi |
| Nhóm cho mọi tham số | Khoảng cách tới cuối ván, chỉ biết sau khi ván kết thúc | $p(s)=1-d-q^2$, biết ngay ở $s$ |
| Bằng chứng tại node | $G$ trộn các nhánh theo $\rho$ của G2; 32–66% đặt lên nước rẽ; lệch tới 0,07 | Các ván thuần của node, và nhánh rẽ đã trừ khoảng chênh |
| Cách gộp | $G$ trước, rồi trộn với $q$ theo $w_q$ | Một phép Gauss–Markov gồm cả $q$; nhánh rẽ nhận trọng số theo $\kappa$ đo được |
| Phần may rủi $B$ | Cộng dồn $\omega^2U$ (G2); chưa từng kiểm | Đo bằng cặp ván lặp mỗi đời, trong trần 20% |
| Phần mạng sai $A$ | $\tau_q^2$ bằng phương pháp moment với $c=0$, có sàn | $A=S-\hat B$; $S$ đo lại mỗi đời |
| $q$ trong nhãn | Trung bình gộp, có search lại | Giá trị lúc chơi của ván thuần mới nhất |
| Search lại | Một lần search, không chơi ván | Thêm ván lặp; trần 20% giữ |
| Nhãn policy | Trung bình $\pi$ | Trung bình $\pi$; tuỳ chọn sửa $\hat Q$ bằng kết quả ván rồi dựng lại |
| Mục 8 | | Giữ, trừ quy tắc ưu tiên search lại |

### 12.12 Những chỗ còn hở

1. **Cách chơi đổi qua các đời.** Ván thuần và ván rẽ ở cùng một node thường do mạng của những đời khác nhau chơi. Các câu "đúng tuyệt đối" chỉ đúng trong một đời. Giữa các đời, mục 12 dùng trọng số làm cũ $\gamma$ như mục 8.1. Hai hệ quả chưa được đo:
   - sai số của $q$ mới nhất có thể tương quan với độ may rủi của các ván cũ, vì mạng mới đã học từ kết quả của chúng;
   - phép đo $\kappa$ có thể lệch, vì mạng chơi ván rẽ có thể đã học từ $z_\beta$.
2. **Phần may rủi của nước đi tại $s$.** $q$ và kết quả của cùng một ván chung phần $\delta_s$ (12.3), và 12.7 bỏ qua hiệp phương sai này. Nó nhỏ khi hai ván trong cặp hầu như luôn đi cùng nước đầu, và cặp ván lặp đo được điều đó.
3. **Tương quan giữa các tầng.** Sai số của $q$ ở $s$ và sai số bên trong $G(c_a)$ (sai số này đến từ $q$ của chính $c_a$, qua các nhánh rẽ bên dưới nó) được coi là không tương quan. Đây là chỗ xấp xỉ.
4. **Các quy tắc khi số đo nhiễu** (bước 5 của 12.7) vẫn là quy tắc đặt tay, giống cái sàn của $\tau_q^2$. Log cho biết chúng chạm bao nhiêu lần.
5. **Cách chia nhóm $g(s)$** (số khoảng của $p$, có chia thêm theo số nửa nước hay không) là lựa chọn tay. Nó ảnh hưởng tới độ nhiễu, không gây lệch.
6. **Giá trị search dọc ván thuần chưa dùng.** Các lần search lúc chơi ở những node sau $s$ trên ván thuần cũng là bằng chứng về $V^\beta(s)$, nhưng mục 12 chưa đưa chúng vào nhãn.
7. **Chưa kiểm gì.** Mọi số liệu đều từ lần chạy 5 của cách cũ. Định lý 9 chỉ là chặn trên, và không định lý nào trong mục này chứng minh arena sẽ hơn mốc 78,2%.
8. **Tuổi của mạng đã cho $q$.** Ở node gần gốc tạo ở đời 0, $q$ đến từ mạng đời 0 với WDL gần đều ($p$ quanh 0,667), còn node tạo ở các đời sau có $q$ của mạng tốt hơn. Cùng một nhóm theo $p$ có thể lẫn hai loại sai số $A$ rất khác nhau (12.14). Nhóm $g(s)$ nên tính tới đời của mạng cho $q$, hoặc tách riêng node đời 0.
9. **Node rẽ không phải mẫu ngẫu nhiên.** Ở node cha có nhánh rẽ, $\mathbb E[z_\beta-q]$ là $-0{,}020$ chung và $-0{,}099$ ở nhóm $p$ cao, so với $-0{,}005$ của mọi vị trí (12.14). Vì vậy $\kappa$ và $o$ đo ở đó đúng cho tập node do luật chọn điểm rẽ hiện tại tạo ra. Nếu luật đổi thì phải đo lại. Một phần độ lệch này do $q$ lạc quan khi search phân vân (12.14, kết quả 4); phần còn lại chưa giải thích.

### 12.13 Phương án temperature 1 đã cân nhắc và không chọn

Sáng 19/11, mục này từng ghi một phương án khác: ván rẽ bốc nước theo tỉ lệ lượt thăm (temperature 1), kèm nhãn value dùng mạng làm biến kiểm soát và nhãn policy nghiêng bậc nhất với hệ số $\tfrac12$. Các định lý của phương án đó đúng khi ván được bốc theo một phân phối biết trước. Chủ dự án không chọn nó, vì temperature 0 dùng lại được cây search và chơi được nhiều node hơn với cùng ngân sách. Toàn văn còn trong lịch sử git (commit 6dd126a), để tra lại nếu sau này đổi cách chơi.

### 12.14 Kết quả đo ngày 22/11 trên dữ liệu có sẵn (một phần của bước 1 ở 12.10)

Mục này ghi các số đo làm ngày 22/11. Chỉ đọc dữ liệu: không đổi mã, không chạy thêm ván nào, không ghi gì lên điện thoại. Các tập lệnh đo (đọc bản ghi, khớp vào cây, tính bảng) nằm tạm ở thư mục làm việc của phiên, chưa đưa vào kho.

**Dữ liệu và cách kiểm.** Bản ghi 114 436 ván của các đời 0 đến 20 (8,86 triệu vị trí), khớp từng ván vào cây đời 20 theo đường đi từ gốc. Cây có 40 468 node cha có ván rẽ, với 74 435 ván rẽ. Làm lại bảng 1 của 12.4 từ bản ghi thô cho ra đúng các số đã ghi ở cả ba đời 10, 15 và 20 (độ lệch và RMS, tới chữ số thập phân thứ ba). Vì vậy cách đọc dữ liệu là đúng.

**Kết quả 1: bảng theo nhóm $p(s)$.** Dùng 1,2 triệu vị trí của các đời 18 đến 20, chia 8 nhóm có số vị trí bằng nhau (150 215 vị trí mỗi nhóm), $p=1-d-q^2$ của lần search lúc chơi. Cột cuối là trung bình của (nhãn cũ trừ $z$), với nhãn cũ $=w\,q+(1-w)\,z$ và $w$ là $w_q$ trung bình theo khoảng cách ở bảng 4. Đây là nhãn của node một nhánh, và $w$ lấy xấp xỉ.

| Nhóm | $p$ trung bình | Lệch $z-q$ | $S$ | $\mathbb E[p]/S$ | Nhãn cũ trừ $z$ |
|---|---|---|---|---|---|
| 0 | 0,000 | −0,0016 | 0,0102 | 0,01 | +0,0004 |
| 1 | 0,000 | −0,0022 | 0,0156 | 0,02 | +0,0005 |
| 2 | 0,001 | −0,0031 | 0,0194 | 0,04 | +0,0007 |
| 3 | 0,002 | −0,0029 | 0,0224 | 0,08 | +0,0006 |
| 4 | 0,004 | +0,0008 | 0,0249 | 0,17 | −0,0003 |
| 5 | 0,011 | +0,0018 | 0,0298 | 0,37 | −0,0005 |
| 6 | 0,070 | −0,0062 | 0,0789 | 0,89 | +0,0012 |
| 7 | 0,627 | −0,0259 | 0,5738 | 1,09 | +0,0058 |
| Chung | 0,104 | −0,0049 | 0,0969 | 0,92 | +0,0011 |

Đọc bảng:

- Khoảng 74% sai số tổng $S$ nằm ở nhóm 7, tức một phần tám số vị trí. Chia nhóm đều theo số vị trí là chia quá thô ở phần đuôi trên của $p$, và quá mịn ở phần đuôi dưới.
- Lệch do chia theo khoảng cách (12.3, sửa 21/11) có thật nhưng nhỏ: trung bình của (nhãn cũ trừ $z$) là +0,0011 chung và lớn nhất +0,0058 ở nhóm 7. Nó nhỏ hơn nhiều so với các lệch của $G$ ở node rẽ (0,01 tới 0,07).
- $\mathbb E[p]/S$ chỉ từ 0,01 tới 0,37 ở sáu nhóm đầu, tức kết quả thật sai nhiều hơn WDL của mạng tin. Một phần chênh này là hiệu ứng chọn nhóm theo chính $p$ nhỏ, và chưa tách được. Ở hai nhóm cuối tỉ số là 0,89 và 1,09, chung toàn bộ là 0,92.

**Kết quả 2: $\kappa$, $o$ và các phương sai trên nhánh rẽ.** Với mỗi cặp (node cha $s$, nhánh rẽ $a$) ta lấy $Y_1=z_\beta-q(s)$ và $Y_2=z_a-\hat Q(s,a)$. Ở đây $z_\beta$ là kết quả của ván tạo ra $s$ (nhìn từ bên đi tại $s$), $q(s)$ và $\hat Q(s,a)$ lấy từ lần search lúc chơi của chính ván đó (bước 6 của 12.7), và $z_a$ là kết quả ván rẽ, cũng nhìn từ bên đi tại $s$. Khi đó $\kappa=\mathrm{Cov}(Y_1,Y_2)$ và $o=\mathbb E[Y_2-Y_1]$ theo bước 5 của 12.7. Đã kiểm $\hat Q$ cùng góc nhìn với $q$: với nước nhiều lượt thăm nhất, giá trị của nước trong bản ghi khác $q$ trung bình 0,0001.

Có 74 433 cặp dùng được (một cặp có nước ép trùng nước đã chơi, một cặp thiếu $\hat Q$). Trong đó 47 688 cặp, tức 64%, có node cha **tạo ở đời 0**. Đó là các node gần gốc của những ván đầu tiên: mạng đời 0 cho WDL gần đều ($q$ quanh 0 và $d$ quanh một phần ba, nên $p$ quanh 0,667), và mỗi node có rất nhiều ván thuần vì mọi ván đời 0 đều đi từ gốc. Chúng không theo giả thiết "mỗi node một ván thuần" của 12.2, nên bị loại khỏi phép đo. Trên tập bị loại, $\hat\kappa=+0{,}084\pm0{,}004$ nhưng không đại diện cho node thường. Phần còn lại là 26 745 cặp từ 22 162 node cha (đời tạo từ 1 đến 20), chia 6 nhóm có số cặp bằng nhau theo $p$. Sai số chuẩn lấy bằng bootstrap theo node cha.

| Nhóm | $p$ tb | Cặp | Var $Y_1$ | Var $Y_2$ | Tương quan | $\hat\kappa$ ± SE | $o$ |
|---|---|---|---|---|---|---|---|
| 0 | 0,000 | 4 458 | 0,0038 | 0,0086 | +0,04 | +0,0002 ± 0,0002 | −0,0009 |
| 1 | 0,001 | 4 457 | 0,0090 | 0,0108 | +0,02 | +0,0002 ± 0,0002 | +0,0046 |
| 2 | 0,002 | 4 458 | 0,0176 | 0,0166 | +0,03 | +0,0006 ± 0,0004 | +0,0012 |
| 3 | 0,008 | 4 457 | 0,0235 | 0,0092 | +0,03 | +0,0005 ± 0,0004 | −0,0021 |
| 4 | 0,052 | 4 457 | 0,0335 | 0,0410 | +0,17 | +0,0061 ± 0,0013 | +0,0039 |
| 5 | 0,562 | 4 458 | 0,5069 | 0,5241 | +0,13 | +0,0649 ± 0,0102 | +0,0573 |
| Chung | 0,104 | 26 745 | 0,1003 | 0,1019 | +0,13 | +0,0126 ± 0,0017 | +0,0106 |

Đọc bảng:

- $\kappa$ dương, và khác 0 rõ ở hai nhóm cuối, nơi phương sai lớn. Ở bốn nhóm đầu nó bằng 0 trong sai số, nhưng ở đó phương sai chỉ 0,004 tới 0,024 nên cũng không quan trọng. Vậy trường hợp $\kappa=0$, nơi nhánh rẽ có trọng số 0 (bước 3 của 12.7), không xảy ra ở chỗ có sai số lớn.
- Tỉ số $\hat\kappa/\mathrm{Var}(Y_1)$ là 0,18 ở nhóm 4, 0,13 ở nhóm 5 và 0,13 chung. Nó ổn định hơn bản thân $\kappa$, và đó là hệ số hồi quy của $Y_2$ theo $Y_1$.
- Chia thêm theo số đời giữa ván tạo node cha và ván rẽ, trong ba nhóm theo $p$ và lấy nhóm trên cùng: $+0{,}029\pm0{,}007$ khi cách 0 hoặc 1 đời, $+0{,}032\pm0{,}011$ khi cách 2 tới 5 đời, $+0{,}045\pm0{,}009$ khi cách 6 đời trở lên. $\kappa$ tăng nhẹ theo số đời, chưa tách được khỏi việc mạng đổi giữa hai ván (12.12, chỗ 1).
- $o=+0{,}011$ chung và $+0{,}057$ ở nhóm cao nhất. Ước tính "$-0{,}02$ tới $-0{,}035$" ở bước 1 của 12.7 sai dấu. Nó lấy độ lệch của $z_\beta-q$ bằng $-0{,}005$ như trung bình mọi vị trí. Thật ra ở các node cha có nhánh rẽ, $\mathbb E[Y_1]$ là $-0{,}020$ chung và $-0{,}099\pm0{,}011$ ở nhóm cao nhất: $q$ của ván tạo node lạc quan hơn nhiều so với mức trung bình của mọi vị trí. Một phần được giải thích ở kết quả 4 bên dưới. Vì vậy $\kappa$ và $o$ trên đây đúng cho tập node cha được chọn theo luật hiện tại, không phải cho mọi node.

**Kết quả 3: nhánh rẽ nhận bao nhiêu trọng số nếu $\kappa$ như đã đo.** Đây chỉ là tính toán với một giả định chưa đo: tỉ lệ $B/S$, phần may rủi trong sai số tổng. Lấy nhóm 5 ($S=0{,}507$, Var $Y_2=0{,}524$, $\hat\kappa=0{,}065$). Một nhánh rẽ, $N=1$, $B_a=B$, $\sigma_w^2=\mathrm{Var}(Y_2)-B$ và $\Gamma=A+\sigma_w^2-2\kappa$, rồi tính Gauss–Markov của 12.7:

| $B/S$ giả định | $A$ | $B$ | Trọng số $q$ | Trọng số ván thuần | Trọng số nhánh rẽ | Sai số bình phương của nhãn, có và không dùng nhánh rẽ |
|---|---|---|---|---|---|---|
| 0,2 | 0,406 | 0,101 | 0,178 | 0,797 | 0,025 | 0,0808 và 0,0811 |
| 0,4 | 0,304 | 0,203 | 0,356 | 0,594 | 0,050 | 0,1203 và 0,1217 |
| 0,6 | 0,203 | 0,304 | 0,534 | 0,390 | 0,075 | 0,1187 và 0,1217 |
| 0,8 | 0,101 | 0,406 | 0,712 | 0,187 | 0,101 | 0,0759 và 0,0811 |

Đọc bảng:

- Nhánh rẽ nhận 2,5% tới 10% trọng số, và chỉ hạ sai số bình phương của nhãn 0,4% tới 6,4%. Thấp hơn nhiều so với 12,1% ở ví dụ giả định của 12.7, và so với 32 tới 66% khối lượng mà $\rho$ của G2 đặt lên nước rẽ ở cách đang chạy. Với $\kappa/S$ cỡ 0,13, nhánh rẽ chỉ là phần phụ của nhãn $V^\beta$ tại node cha.
- Trọng số của $q$ gần bằng $B/S$ và chạy từ 0,18 tới 0,71. Vậy $B/S$ là con số quyết định chất lượng nhãn. Mã đang chạy tin $B/S$ trong khoảng 0,12 tới 0,36 (bảng 4, $E/(E+\tau_q^2)$) mà chưa từng kiểm. Nếu giá trị thật là 0,8 thì nhãn đang quá thiên về $z$; nếu là 0,2 thì mã gần đúng. Theo công cụ 3 của 12.3, dữ liệu hiện có không tách được $A$ khỏi $B$. Chỉ cặp ván lặp (12.9) tách được.

**Kết quả 4: $q$ lạc quan khi search phân vân, và nó giải thích một phần độ lệch ở node cha rẽ.** Tỉ lệ lượt thăm của nước nhiều lượt thăm nhất là thông tin có ngay tại $s$, và nó dự đoán độ lệch $z-q$ rất rõ. Với 131 452 vị trí có $p>0{,}3$ của các đời 18 đến 20:

| Tỉ lệ lượt thăm của nước nhiều nhất | dưới 0,3 | 0,3–0,5 | 0,5–0,7 | 0,7–0,85 | 0,85–0,95 | từ 0,95 |
|---|---|---|---|---|---|---|
| Số vị trí | 21 421 | 34 874 | 31 642 | 23 540 | 14 295 | 5 680 |
| Trung bình $z-q$ | −0,076 | −0,058 | −0,026 | +0,013 | +0,035 | +0,027 |

Search càng phân vân giữa nhiều nước thì $q$ càng lạc quan. Đây là hiệu ứng quen thuộc khi lấy giá trị của nước thắng trong nhiều ước lượng nhiễu. Luật chọn điểm rẽ bốc nước theo $\mathrm{ns}^{1/T}$ nên hay rơi vào node phân vân: ở nhóm $p>0{,}3$, tỉ lệ lượt thăm trung bình là 0,33 ở node cha rẽ và 0,54 ở node khác. Hồi quy $z-q$ theo tỉ lệ lượt thăm trên node khác dự đoán $-0{,}061$ cho cha rẽ, còn đo được $-0{,}099$. Trong từng ô tỉ lệ lượt thăm, cha rẽ vẫn lạc quan hơn node khác $0{,}04$ tới $0{,}05$ (sai số chuẩn 0,02 tới 0,04), phần dư chưa giải thích.

Ba hệ quả:

- Tỉ lệ lượt thăm là biến nhóm biết ngay tại $s$ và nên có trong $g(s)$ (12.12, chỗ 5).
- Có thể hiệu chỉnh $q$ bằng trung bình độ lệch của nhóm. Theo công cụ 1 của 12.3, hiệu chỉnh này đúng tuyệt đối khi nhóm lập theo thông tin biết tại $s$.
- Ở node rẽ, $G-q$ trung bình là $-0{,}055$ (bảng 2, cân theo số node). Trên chính các node đó, ván tạo node đã cho $z_\beta-q=-0{,}019$. Vậy khoảng một phần ba độ lệch của $G$ ở node rẽ là do $q$ lạc quan, hai phần ba còn lại là do cách trộn nhánh rẽ. So sánh này xấp xỉ, vì $q$ ở bảng 2 là $q$ gộp còn ở đây là $q$ lúc chơi.

**Điều đo này chưa làm được.**

- $B$, và vì vậy $A$, $\Gamma$ và $\eta$ ở các nhóm đại diện. Một thử $\eta+B$ ở node có hai nhánh rẽ cho kết quả lẫn với tập node đời 0 nên chưa dùng được.
- Bảng 2 và bảng 3 của 12.4 chia lại theo nhóm $p$.
- Tách ảnh hưởng của việc mạng đổi giữa hai ván khỏi $\kappa$.

**Hệ quả cho thiết kế.**

- Cấu trúc của 12.7 giữ nguyên. Mặc định không đặt $\kappa=0$ mà dùng $\hat\kappa$ đo được theo nhóm, như bước 5 đã ghi. Nhánh rẽ chỉ là phần phụ của nhãn.
- Việc đầu tiên bây giờ là đo $B/S$ bằng cặp ván lặp (bước 2 của 12.10), vì nó quyết định trọng số của $q$ so với $z$ trong nhãn của mọi node.
- Tỉ lệ lượt thăm của nước nhiều nhất nên vào nhóm $g(s)$ (kết quả 4), và $q$ nên được hiệu chỉnh theo trung bình độ lệch của nhóm.
- Nhóm lập theo $p$ chưa đủ: khối node đời 0 dồn ở một giá trị $p$ duy nhất (0,667), và $q$ của chúng đến từ mạng đời 0. Nhóm phải tính tới tuổi của mạng đã cho $q$ (12.12, chỗ 8).
