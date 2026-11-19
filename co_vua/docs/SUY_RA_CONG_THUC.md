# Các công thức của cách cây trò chơi được suy ra thế nào

Viết ngày 15/11/2026, bổ sung 18/11 và 19/11. Tài liệu được đối chiếu với mã đang chạy trong `co_vua/scripts/cv/cay.py` (lần chạy 5). Lịch sử các quyết định nằm ở tài liệu thiết kế `THIET_KE_CO_VUA.md`. Tài liệu này làm hai việc:

1. Với mỗi công thức hay quy tắc đang chạy, nói rõ mã làm gì từng bước, công thức được **suy ra** từ đâu hay được **ước lượng** từ dữ liệu hay chỉ được **đặt tay**, và nó dựa vào loại giả định nào (mục 1.1).
2. Ghi bản nâng cấp của chính cách cây đang chạy (mục 12). Bản này đối chiếu phần suy diễn thống kê với số đo thật của lần chạy 5, chỉ ra ba chỗ không khớp, và đề xuất cách sửa, giữ nguyên mục 8 và temperature 0. Đề xuất ngày 19/11, chưa viết mã.

**Cách đọc.**

- **Phần A, phương pháp đang chạy:**
  - mục 1 là bảng tổng hợp và tiêu chí phân loại giả định;
  - mục 2 mô tả cây, các số mỗi node lưu, và thứ tự các bước trong một đời;
  - các mục 3 đến 9 đi qua từng công thức theo đúng thứ tự mã tính.
- **Phần B, phương pháp thay thế và nền toán của nó:**
  - mục 10 suy ra nhãn policy mới của tài liệu thiết kế (đang tắt);
  - mục 11 là khung định lý theo kiểu Gumbel AlphaZero;
  - mục 12 là bản nâng cấp của cách cây đang chạy, dựa trên số đo thật. Mục này gồm công cụ đo, số liệu, ba chỗ suy diễn không khớp, định lý về lâu dài, nhãn value và nhãn policy mới, và thí nghiệm cặp ván. Mục này viết đủ chi tiết để làm theo.

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
- Mục 12 không dùng khung này. Nó giữ cách cây đang chạy và sửa những chỗ mà số đo thật cho thấy suy diễn lệch.

---

## 12. Nâng cấp cách cây đang chạy theo số đo thật (19/11, chưa viết mã)

Mục này đối chiếu phần suy diễn thống kê của cách cây đang chạy (mục 3 đến 7 và 9) với dữ liệu thật của lần chạy 5, chỉ ra chỗ nào không khớp, rồi đề xuất cách nâng cấp. Mọi con số ở đây đo trên dữ liệu thật trong điện thoại ngày 19/11. Chưa có dòng mã nào được sửa.

### 12.1 Phạm vi: giữ gì, nâng cấp gì

Chủ dự án chốt ngày 19/11:

- **Giữ nguyên toàn bộ mục 8:** cắt lá, làm cũ bằng $\gamma$ và $W$, quét điểm rẽ với $T=0{,}5$, khoá $-\ln(u)/m^2$, search lại tới 20% ngân sách, lập việc theo ngân sách.
- **Giữ temperature 0 trong ván rẽ.** Ván đi nước nhiều lượt thăm nhất ở mọi nửa nước (trong mã, `04_sinh_du_lieu.py` đặt `TEMP_PLIES = 0` cho cách cây). Lý do: engine dùng lại được cây search của nước vừa đi, và cùng ngân sách chơi được nhiều node hơn cách truyền thống.
- **Được nâng cấp hoặc thay:** mọi phần còn lại, gồm $G$, $E$, $\rho$, $\omega^2$ (mục 3 đến 5), $w_q$ và $\tau_q^2$ (mục 6, 7), và nhãn policy (mục 9). Nhãn policy trung bình $\pi$ được giữ nếu nó có cơ sở toán học về cải thiện chính sách (12.8 cho thấy là có).
- **Giả định không còn bị cấm.** Chủ dự án không còn phản đối G2 hay bất kỳ giả định nào, và không cần phân loại giả định nữa. Thước đo bây giờ là: suy diễn có khớp với kết quả thật không, và thiết kế có tối ưu theo thống kê suy diễn không.

### 12.2 Đích học, ván thuần và giá trị search lúc chơi

**Chính sách chơi $\beta$.** Gọi $\beta$ là đúng cách mà ván rẽ được chơi ở một đời: mỗi nước chạy search khoảng 800 lượt thăm bằng mạng của đời đó, có nhiễu Dirichlet ở gốc, có dùng lại cây của nước trước, rồi đi nước nhiều lượt thăm nhất. $\beta(a|s)$ là xác suất để cách chơi đó chọn nước $a$ tại $s$. Vì có nhiễu Dirichlet, $\beta$ không hoàn toàn tất định, nhưng gần như luôn chọn nước nhiều lượt thăm nhất. Mã không biết chính xác các xác suất $\beta(a|s)$, và phương pháp dưới đây không cần biết chúng.

**Đích học $V^\beta$.** $V^\beta(s)$ là kết quả trung bình, theo góc bên đang đi tại $s$, nếu từ $s$ hai bên cùng chơi theo $\beta$. $Q^\beta(s,a)$ là kết quả trung bình nếu đi $a$ trước rồi hai bên chơi theo $\beta$. Ván hữu hạn và kết quả bị chặn, nên đây là những con số xác định, và
$$V^\beta(s)=\sum_a\beta(a|s)\,Q^\beta(s,a).$$
Đây là đích học của đầu value trong phương pháp nâng cấp. Mục 3 định nghĩa giá trị thật bằng cách "mỗi nước bốc theo $\pi$". Định nghĩa đó không khớp với cách ván thật được chơi, và 12.5 cho thấy chỗ không khớp này gây lệch đo được.

**Ván thuần.** Một ván là **ván thuần từ node $s$** nếu nó đi qua $s$ và mọi nước của nó từ $s$ trở đi đều do $\beta$ chọn. Bản ghi của một ván rẽ gồm đường đi từ gốc tới thế bắt đầu (kể cả nước rẽ) và các lần search từ thế bắt đầu trở đi (mục 2.2). Vì vậy ván rẽ là ván thuần từ mọi node từ thế bắt đầu trở xuống trên đường của nó.

**Mỗi node có đúng một ván thuần.** Ván rẽ luôn bắt đầu ở một node mới, vì nước rẽ là nước chưa chơi tại điểm rẽ. Mọi node bên dưới thế bắt đầu cũng là node mới, vì node được định danh bằng cả đường đi. Vậy một ván rẽ không bao giờ đi qua node có sẵn từ thế bắt đầu trở xuống. Search lại thì không chơi ván. Từ đó, mọi node tạo sau đời 0 có **đúng một** ván thuần: ván đã tạo ra nó. Ngoại lệ duy nhất là các node gần gốc của đời 0, nơi nhiều ván cùng bắt đầu từ thế khởi đầu.

Hai hệ quả:

- Ở node chỉ có một nhánh đã chơi, $G$ của mã hiện tại đúng bằng kết quả ván thuần của node.
- Các ván rẽ đi qua một node $s$ đều sinh ra từ các điểm rẽ **bên dưới** $s$. Chúng không phải ván thuần từ $s$, và chúng không phải là mẫu của $V^\beta(s)$.

**Nhánh $\beta$ và nhánh rẽ.** Tại node $s$, nhánh $\beta$ là node con mà ván tạo ra $s$ đã đi tới. Nó được tạo trước mọi node con khác, nên là node con có chỉ số nhỏ nhất. Các node con còn lại là nhánh rẽ, mỗi nhánh do một ván rẽ sinh ra tại $s$ với nước do bước quét chọn (mục 8.3).

**Giá trị search lúc chơi.** Gọi $q(s)$ là $Q$ của nước nhiều lượt thăm nhất trong **lần search của ván thuần tại $s$**, tức lần search đã chọn nước đi ở $s$. Bản ghi ván lưu sẵn số này (trường `best_q`, cùng xác suất hoà `best_d`). $q(s)$ khác $q$ mà mã đang dùng trong nhãn: mã dùng trung bình gộp của mọi lần search tại node, trong đó có các lần search lại bằng mạng đã học từ chính kết quả ván của node.

### 12.3 Bốn công cụ đo không cần giả định

**Bổ đề thiết kế.** Xét một vị trí $s$ trên ván thuần của nó. Gọi $\mathcal F_s$ là mọi thứ đã biết lúc ván đang ở $s$: cây, mạng, lần search tại $s$ (nên có cả $q(s)$, $\hat Q(s,\cdot)$, $\pi(s)$). Gọi $z$ là kết quả ván theo góc bên đi tại $s$. Khi đó
$$\mathbb E\big[z\,\big|\,\mathcal F_s\big]=V^\beta(s).$$
**Chứng minh.** Từ $s$ trở đi ván được chơi đúng theo $\beta$, với số ngẫu nhiên mới (nhiễu Dirichlet của các lần search sau). Theo định nghĩa, trung bình của kết quả là $V^\beta(s)$. Những gì đã biết ở $s$ không ảnh hưởng tới số ngẫu nhiên về sau.

Hệ quả: với mọi đại lượng $X$ tính xong trước khi ván đi tiếp từ $s$, ta có $\mathbb E[(z-V^\beta(s))\,X]=0$.

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

### 12.4 Số đo trên lần chạy 5

**Nguồn dữ liệu.**

- Bản ghi mọi ván rẽ của các đời 10 đến 20, khoảng 5,1 triệu vị trí. Mỗi vị trí cho một bộ $(q,d,z)$, với $q$, $d$ lấy từ lần search lúc chơi và $z$ là kết quả của chính ván đó.
- Cây sau đời 20: 1,69 triệu node. Trong đó khoảng 1,58 triệu node sống đã search chỉ có một nhánh đã chơi, và khoảng 40 nghìn node rẽ có từ hai nhánh trở lên.
- Toàn bộ 1028 ván arena đời 20.

Mọi bảng chia theo khoảng cách tới cuối ván, đo bằng nửa nước, với các mốc của mục 7.1. Với dữ liệu ván, khoảng cách là số nửa nước còn lại của chính ván. Với dữ liệu cây, khoảng cách là `cach` của mã.

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

Phần thứ hai không giảm dù chạy bao lâu, nên nó đặt một cái sàn $2hb$ lên khoảng cách tới minimax. Với ván dài cỡ 100 nửa nước, sàn đó lớn hơn rất nhiều so với chính $b$. Đây là lý do chỗ 1 ở 12.5 phải sửa trước tiên.

**Mệnh đề 10 (trộn với chính giá trị của mạng không tạo lệch lâu dài).** Giả sử nhãn là $w\,q+(1-w)\,Y$, với $Y$ không lệch so với $V^\beta$. Giả sử thêm hai điều lý tưởng: mạng học đúng trung bình của nhãn, và lệch của $q$ đúng bằng lệch của mạng. Khi đó nếu mạng ở đời $k$ lệch $b_k$, thì nhãn lệch $w\,b_k$, nên $b_{k+1}=w\,b_k$. Lệch co lại theo cấp số nhân với công bội $w<1$.

**Chứng minh.** Trung bình của nhãn là $w(V^\beta+b_k)+(1-w)V^\beta=V^\beta+w\,b_k$.

Vậy dùng $q$ trong nhãn là an toàn về lâu dài: nó làm chậm việc sửa sai chứ không tạo sai mới. Cái tạo sai mới là $Y$ lệch, như $G$ ở node rẽ.

### 12.7 Nhãn value mới

Nhãn value giữ đúng dạng của mã đang chạy: $q$ trộn với một giá trị tổng hợp từ cây. Hai thay đổi: giá trị tổng hợp nhắm đúng $V^\beta$, và mọi trọng số lấy từ các phương sai **đo được**.

**Bước 1. Mỗi node con cho một ước lượng của $V^\beta(s)$.** Ký hiệu như 12.2: nhánh $\beta$ là $c_\beta$, các nhánh rẽ là $c_a$ với $a\in R(s)$. Mọi giá trị viết theo góc bên đi tại $s$, nên $G$ của node con phải đổi dấu (đổi chỗ thắng với thua).

- **Từ nhánh $\beta$:** $x_\beta=G(c_\beta)$. Nước của nhánh này được rút từ $\beta(\cdot|s)$, nên nếu $G(c_\beta)$ không lệch cho $V^\beta(c_\beta)$ thì $x_\beta$ không lệch cho $V^\beta(s)$.
- **Từ mỗi nhánh rẽ:** nhánh rẽ cho bằng chứng về $Q^\beta(s,a)$, không phải về $V^\beta(s)$. Muốn đổi nó thành bằng chứng về $V^\beta(s)$ thì phải cộng thêm khoảng chênh $V^\beta(s)-Q^\beta(s,a)$. Search ước khoảng chênh này là $q(s)-\hat Q(s,a)$, và ước đó lệch trung bình một lượng $o$ đo được. Vậy
$$x_a=G(c_a)+\big(q(s)-\hat Q(s,a)\big)-o(d),$$
với $d$ là khoảng cách tới cuối ván của $s$, và
$$o(d)=\text{trung bình}\Big[\big(z_a-\hat Q(s,a)\big)-\big(z_\beta-q(s)\big)\Big]$$
lấy trên các node rẽ trong cùng khoảng cách mà cả nhánh $\beta$ lẫn nhánh rẽ đều chỉ có một ván ($z_a$, $z_\beta$ là kết quả hai ván đó). Theo bổ đề thiết kế, hai kết quả là mẫu không lệch của $Q^\beta(s,a)$ và $V^\beta(s)$, nên $o(d)$ ước không lệch độ lệch trung bình của khoảng chênh mà search ước. Với số đo hiện có, $z_a-\hat Q$ khoảng $-0{,}02$ tới $-0{,}04$ và $z-q$ khoảng $-0{,}005$, nên $o$ vào khoảng $-0{,}02$ tới $-0{,}035$.

**Bước 2. Sai số của từng ước lượng.** Viết sai số của $x_a$ thành ba phần:
$$x_a-V^\beta(s)=\underbrace{\big(G(c_a)-Q^\beta(s,a)\big)}_{n_a}+\underbrace{\big(q(s)-V^\beta(s)\big)}_{u}-\underbrace{\big(\hat Q(s,a)-Q^\beta(s,a)+o\big)}_{w_a}.$$

- $n_a$ là độ may rủi của ván rẽ, phương sai $E(c_a)$.
- $u$ là sai số của $q(s)$, **chung cho mọi nhánh rẽ** của $s$, phương sai $A(d)$.
- $w_a$ là sai số riêng của $\hat Q$ ở nước $a$, phương sai $\sigma_w^2(d)$.

Ba phần không tương quan với nhau. $u$ và $w_a$ tính xong trước khi ván rẽ chơi, còn $n_a$ có trung bình 0 khi biết mọi thứ trước đó (bổ đề thiết kế). Các $n_a$ của các nhánh khác nhau độc lập vì là các ván khác nhau. Sai số của $x_\beta$ cũng có trung bình 0 khi biết mọi thứ ở $s$, nên không tương quan với $u$ hay $w_a$. Phương sai của nó là $v_\beta=E(c_\beta)+\Delta B(d)$, với $\Delta B(d)$ là phần may rủi do riêng nước đi ở $s$ (bước 4).

**Bước 3. Gộp tối ưu (định lý Gauss–Markov).** Với cấu trúc sai số ở bước 2, tổ hợp tuyến tính không lệch có phương sai nhỏ nhất được tính theo hai tầng.

1. **Gộp các nhánh rẽ với nhau.** Phần chung $u$ không đổi được trọng số tương đối giữa các nhánh rẽ, nên chúng được gộp theo nghịch đảo phần riêng $s_a=E(c_a)+\sigma_w^2$:
$$x_R=\frac{\sum_{a\in R}x_a/s_a}{\sum_{a\in R}1/s_a},\qquad v_R=A+\frac{1}{\sum_{a\in R}1/s_a}.$$
2. **Gộp với nhánh $\beta$.** $x_\beta$ và $x_R$ có sai số không tương quan, nên gộp theo nghịch đảo phương sai:
$$G(s)=\frac{x_\beta/v_\beta+x_R/v_R}{1/v_\beta+1/v_R},\qquad E(s)=\frac{1}{1/v_\beta+1/v_R}.$$

Định lý Gauss–Markov nói rằng trong mọi tổ hợp tuyến tính không lệch của các ước lượng này, $G(s)$ có phương sai nhỏ nhất, và phương sai đó là $E(s)$. Node không có nhánh rẽ thì $G(s)=x_\beta$ và $E(s)=v_\beta$.

Công thức này thay cho $\rho$ và $\nu$ của mục 5. Nó không còn đặt khối lượng lên nước rẽ chỉ vì nước rẽ có $E$ nhỏ: nước rẽ chỉ được tin sau khi đã trừ khoảng chênh, và mức tin vào nó trả giá cho cả sai số của khoảng chênh ($A+\sigma_w^2$).

**Bước 4. Phần may rủi $E$ lấy từ số đo.** Gọi $\hat B(d)$ là độ may rủi của **một** ván thuần chơi từ khoảng cách $d$, đo bằng thí nghiệm cặp ván (12.9). Nó phải không giảm theo $d$, vì theo luật phương sai toàn phần, phương sai có điều kiện của kết quả giảm dần (theo trung bình) khi ván tiến về cuối. Vì vậy $\hat B$ được khớp bằng hồi quy đơn điệu (isotonic regression: phép khớp chọn dãy không giảm gần dữ liệu nhất theo bình phương), với $\hat B(0)=0$. Đặt $\Delta B(d)=\hat B(d)-\hat B(d-1)\ge0$, là phần may rủi trung bình thêm vào bởi một nửa nước. Khi đó:

- Ở node kết thúc, $E=0$.
- Ở node một nhánh, $E(s)=E(c_\beta)+\Delta B(d)$. Dọc một đường chỉ có một ván, công thức này cộng dồn ra đúng $E(s)=\hat B(d)$, tức là độ may rủi đo được của một ván.
- Ở node rẽ, $E(s)$ theo bước 3.
- Node gốc cắt giữ $G$ và $E$ đã lưu như hiện nay.

Ba tham số còn lại đo như sau:

- $A(d)=S(d)-\hat B(d)$, với $S(d)$ là trung bình $(z-q)^2$ đo lại mỗi đời trên ván thuần (công cụ 2).
- $\sigma_w^2(d)$: ở các node rẽ mà cả hai nhánh chỉ có một ván, $\mathbb E\big[(x_a-x_\beta)^2\big]=E(c_a)+A+\sigma_w^2+v_\beta$, nên $\sigma_w^2=\text{trung bình}\big[(x_a-x_\beta)^2\big]-E(c_a)-A-v_\beta$ (phương pháp moment, các phương sai còn lại đã biết).
- $o(d)$ như ở bước 1.

**Bước 5. Trộn với $q$, có tính đúng hiệp phương sai.** Nhãn value là $w\,q(s)+(1-w)\,G(s)$. Khác với mục 6, sai số của $G(s)$ **có** tương quan với sai số của $q(s)$, vì các ước lượng từ nhánh rẽ chứa $u=q(s)-V^\beta(s)$ với trọng số $\rho_R=\dfrac{1/v_R}{1/v_\beta+1/v_R}$. Hiệp phương sai là $c=\rho_R\,A$, tính được chứ không phải giả định. Công thức của mục 6.1 với $c$ cho
$$w=\frac{E(s)-\rho_RA}{E(s)+A-2\rho_RA}.$$
Ở node không có nhánh rẽ, $\rho_R=0$ và $w=E/(E+A)$. Riêng ở node một ván, $w=\hat B(d)/S(d)$.

**Bước 6. Dùng $q$ lúc chơi.** Trong nhãn và trong mọi phép đo, $q(s)$ và $d(s)$ là của lần search ở ván thuần tại $s$, không phải trung bình gộp. Hai lý do: hiệp phương sai giữa $q$ và kết quả ván khi đó đúng là 0 (công cụ 2), và nhãn không bị kéo về các lần search lại bằng mạng đã học từ chính kết quả đó.

**Bước 7. Dạng thắng, hoà, thua.** Các trọng số ở bước 3 và 5 tính trên giá trị một chiều (thắng trừ thua), rồi dùng nguyên cho cả bộ ba. Phép trừ khoảng chênh ở bước 1 làm riêng cho số một chiều và cho xác suất hoà. Bộ ba được dựng lại bằng $\big((1+v-d)/2,\ d,\ (1-v-d)/2\big)$, chặn mỗi thành phần ở 0 rồi chuẩn hoá lại.

**Ví dụ** (số giả định để thấy phép tính). Node $s$ cách cuối ván 60 nửa nước, $q(s)=+0{,}10$.

- Nhánh $\beta$ có một ván, $G=-0{,}25$.
- Một nhánh rẽ có một ván, $\hat Q(s,a)=-0{,}05$, $G=+0{,}50$.
- Tham số: $\hat B(60)=0{,}070$, $\hat B(59)=0{,}069$, $A=0{,}02$, $\sigma_w^2=0{,}03$, $o=-0{,}03$.

1. $x_\beta=-0{,}25$, $v_\beta=0{,}069+0{,}001=0{,}070$.
2. $x_a=0{,}50+(0{,}10+0{,}05)+0{,}03=0{,}68$, $s_a=0{,}069+0{,}03=0{,}099$, $v_R=0{,}02+0{,}099=0{,}119$.
3. Trọng số: $1/0{,}070\approx14{,}3$ và $1/0{,}119\approx8{,}4$, nên $\rho_\beta\approx0{,}63$ và $\rho_R\approx0{,}37$.
4. $G(s)\approx0{,}63\times(-0{,}25)+0{,}37\times0{,}68\approx+0{,}094$, và $E(s)\approx1/22{,}7\approx0{,}044$.
5. $c=0{,}37\times0{,}02\approx0{,}0074$, nên $w=(0{,}044-0{,}0074)/(0{,}044+0{,}02-0{,}0148)\approx0{,}74$.
6. Nhãn value là $0{,}74\times0{,}10+0{,}26\times0{,}094\approx+0{,}098$.

Đọc ví dụ: ván rẽ đi một nước mà search chê ($-0{,}05$) nhưng lại thắng đậm ($+0{,}50$). Sau khi trừ khoảng chênh, đó là bằng chứng rằng thế cờ tốt hơn kết quả $-0{,}25$ của đúng một ván trên nhánh $\beta$. Cách đang chạy cho $G=+0{,}080$ chỉ vì $\rho$ trộn thẳng $+0{,}50$ của nước rẽ, không trừ khoảng chênh. Hai con số tình cờ gần nhau ở ví dụ này, nhưng trung bình trên nhiều node thì cách đang chạy lệch như bảng 2, còn cách mới không lệch.

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

1. **Bỏ phần lạc quan trung bình.** $\tilde Q(s,a)=\hat Q(s,a)+o_Q(d)$, với $o_Q(d)$ là trung bình $z_a-\hat Q(s,a)$ của các nhánh một ván cùng khoảng cách (bảng 3, dòng thứ hai). Với nhánh $\beta$ dùng trung bình $z-q$ (bảng 1).
2. **Kéo về phía kết quả ván theo nghịch đảo phương sai.**
$$Q'(s,a)=\tilde Q(s,a)+k_a\big(G(c_a)-\tilde Q(s,a)\big),\qquad k_a=\frac{\sigma_Q^2(d)}{\sigma_Q^2(d)+E(c_a)}.$$
   - $\sigma_Q^2(d)$ là phương sai sai số của $\hat Q$, đo bằng trung bình $(z_a-\tilde Q)^2$ trừ trung bình $E(c_a)$, theo cùng phép tách của công cụ 2.
   - Với nhánh $\beta$, $\sigma_Q^2=A(d)$.
   - Vì sai số của $\tilde Q$ và độ may rủi của ván không tương quan (bổ đề thiết kế), sai số bình phương của $Q'$ là $\sigma_Q^2E/(\sigma_Q^2+E)$, nhỏ hơn cả $\sigma_Q^2$ lẫn $E$. Đây là phép tính đúng tuyệt đối khi đã biết hai phương sai, không cần giả định phân phối chuẩn.
3. **Dựng lại đầu ra của search với $Q'$.** Dùng đúng công thức của mục 10. Dựng prior ngầm $w_a=\pi(a)\big(\beta_0-\hat Q(s,a)\big)$ từ $\pi$ và $\hat Q$ đã lưu, với $\beta_0$ chọn như mục 10.1. Rồi đặt $\pi'(a)=w_a/\big(\alpha-Q'(s,a)\big)$ với $\alpha$ chọn sao cho tổng bằng 1. Nước chưa chơi giữ $Q'=\hat Q$. Node không có nhánh rẽ giữ nhãn $\pi$.

**Điều phần sửa bảo đảm.**

- Theo mục 10.3: $\sum_a(\pi'-\pi)(a)\big(Q'(s,a)-\hat Q(s,a)\big)\ge0$, tức nhãn dịch về phía các nước mà kết quả ván cho thấy tốt hơn search nghĩ.
- Theo mục 10.2 và định lý 11: $\pi'$ là nghiệm của cùng bài toán có điều chuẩn, chỉ thay $\hat Q$ bằng $Q'$. Nên $\pi'$ có đúng loại bảo đảm của $\pi$, tốt hơn prior ngầm ít nhất $\lambda\mathrm{KL}$, nhưng đo bằng những giá trị có sai số nhỏ hơn (bước 2).
- Phản ví dụ ở mục 10.4 vẫn còn: $\pi'$ không phải lúc nào cũng tốt hơn chính $\pi$ khi đo bằng $Q'$. Vì vậy phần sửa là tuỳ chọn, chỉ bật khi phép thử offline (12.10) cho thấy nó tốt hơn.

Mục 10 từng tắt nhãn này vì mô phỏng cho thấy nó hại khi $E$ sai. Ở bản nâng cấp, $k_a$ dùng phương sai đo được thay cho $E$ của G2, nên lý do tắt cũ không còn. Nhưng chưa có phép thử mới thì chưa bật.

### 12.9 Thí nghiệm cặp ván: đo phần may rủi $B$

Đây là phép đo duy nhất mà lần chạy không tự cung cấp được (công cụ 3). Nó chạy một lần, ngoài vòng lặp, nên mục 8 không đổi.

**Thiết kế.**

1. **Chọn node.** Lấy các node sống, đã search, chưa kết thúc từ cây đời 20. Chia theo 7 khoảng cách, rồi bốc ngẫu nhiên đều trong mỗi khoảng. Bốc đều khớp với quy tắc học mỗi node một lần (mục 9).
2. **Chơi.** Từ mỗi node $s$ chơi **hai** ván độc lập bằng mạng đời 20, đúng thiết lập của ván rẽ: 800 lượt thăm, nhiễu Dirichlet ở gốc, đi nước nhiều lượt nhất, dùng lại cây trong ván. Mỗi ván là một việc dạng ván rẽ với đường đi từ gốc tới $s$ và không có nước ép. Vì vậy không phải sửa engine. Lần search đầu của mỗi ván nằm ngay tại $s$. Khác biệt nhỏ duy nhất so với ván thuần gốc: lần search đó bắt đầu với cây trống thay vì cây dùng lại.
3. **Ghi.** Với mỗi cặp: hai kết quả $z_1$, $z_2$ theo góc bên đi tại $s$, và $q_1$ là giá trị search lúc chơi tại $s$ của ván thứ nhất.

**Ước lượng (đúng tuyệt đối về trung bình, công cụ 3).** Trong mỗi khoảng cách:
$$\hat B=\text{trung bình}\ \tfrac12(z_1-z_2)^2,\qquad\hat A=\text{trung bình}\ (z_1-q_1)(z_2-q_1).$$
$q_1$ tính xong trước khi ván 1 đi tiếp, và ván 2 độc lập với ván 1, nên mỗi thừa số có trung bình đúng như công cụ 3 cần. Kiểm chéo: $\hat A+\hat B$ phải gần $S$ đo trên ván thường (bảng 4). Sau đó $\hat B(d)$ được khớp bằng hồi quy đơn điệu như 12.7, bước 4.

**Cần bao nhiêu cặp.** Đặt $X=\tfrac12(z_1-z_2)^2$. $X$ chỉ nhận ba giá trị 0, $\tfrac12$ và 2, nên $X^2\le2X$ và $\mathrm{Var}(X)\le2B$. Với $n$ cặp, sai số chuẩn của $\hat B$ không quá $\sqrt{2B/n}\le\sqrt{2S/n}$. Mà tỉ lệ trộn ở node một ván là $w=B/S$, nên sai số chuẩn của $\hat w$ không quá
$$\sqrt{\frac{2}{nS}},\qquad\text{tức là cần}\quad n\ge\frac{2}{\mathrm{SE}^2\,S}.$$
Bảng dưới lấy $S$ của bảng 4. Chi phí tính bằng số lần search, mỗi ván tốn khoảng (khoảng cách + 1) lần search, và mỗi lần search khoảng 490 lần chạy mạng (mục 8.6):

| Khoảng cách | 0–5 | 5–10 | 10–20 | 20–40 | 40–80 | 80–160 | từ 160 |
|---|---|---|---|---|---|---|---|
| $S$ | 0,018 | 0,040 | 0,050 | 0,065 | 0,090 | 0,130 | 0,191 |
| Số cặp cho SE của $w$ là 0,15 | 4 940 | 2 220 | 1 780 | 1 370 | 990 | 680 | 470 |
| Số lần search (nghìn) | 40 | 36 | 57 | 85 | 120 | 165 | 190 |

Tổng khoảng 690 nghìn lần search, tức khoảng $3{,}4\times10^8$ lần chạy mạng. Ván rẽ của đời 20 có khoảng 410 nghìn lần search, nên thí nghiệm tốn chừng 1,7 đời ngân sách. Có ba cách giảm:

- **Chạy thử 10% trước.** Cận $\mathrm{Var}(X)\le2B$ là trường hợp xấu nhất. Phương sai thật đo từ lần chạy thử sẽ cho số cặp cần thiết, thường ít hơn.
- **Nới độ chính xác.** Câu hỏi cần trả lời là $w$ đang ở 0,10–0,27 hay gần 1. Với SE 0,2 thì chi phí chỉ còn khoảng 56%.
- **Không phí ván.** Các ván của thí nghiệm là ván thuần chơi bằng mạng đời 20. Nếu muốn, chúng nạp được vào cây như ván rẽ, vì phần sau chỗ tách khỏi đường cũ là node mới.

**Đo lại.** Mỗi khoảng 5 đời, chạy lại một mẫu nhỏ (khoảng 10%) để theo dõi $B$ có trôi khi cách chơi mạnh lên hay không.

### 12.10 Thứ tự làm và cách kiểm

1. **Thí nghiệm cặp ván** (12.9). Có $\hat B(d)$ và $\hat A(d)$, rồi kiểm $\hat A+\hat B\approx S$.
2. **Tính lại nhãn offline trên cây đời 20** bằng 12.7, rồi kiểm:
   - ở node rẽ, trung bình $G-q$ phải về ngang node một nhánh (khoảng $-0{,}005$) thay vì $-0{,}01$ tới $-0{,}07$;
   - phân phối của $w$ theo khoảng cách;
   - nhãn mới khác nhãn cũ bao nhiêu, ở đâu.
3. **Huấn luyện lại từ cây** với nhãn cũ và nhãn mới, rồi so trên tập ván thuần giữ riêng. Cách so này đúng tuyệt đối. Với $z$ là kết quả của một ván thuần không dùng để làm nhãn, và $f$ là dự đoán của mạng, bổ đề thiết kế cho
$$\mathbb E\big[(f-z)^2\big]=\mathbb E\big[(f-V^\beta)^2\big]+B.$$
   $B$ không phụ thuộc mạng, nên mạng nào có sai số bình phương với $z$ nhỏ hơn thì gần $V^\beta$ hơn, không cần biết $B$.
4. **Phần sửa policy** (12.8) thử riêng, cùng cách: so mạng học nhãn $\pi$ với mạng học nhãn $\pi'$ trên tập giữ riêng, rồi arena.
5. **Chạy thật** từ cây đời 20 với nhãn mới, mục 8 giữ nguyên, arena với cách truyền thống như cũ. Mốc để so là 78,2% của đời 20.

**Chỗ sẽ phải sửa trong mã khi được duyệt** (chưa làm):

- `nap_lan`: lưu cho mỗi node $q$ và $d$ của lần search lúc chơi (lần search đầu tiên, thuộc ván tạo ra node).
- `tinh`: thay $\omega^2$, $\rho$, $\nu$ bằng bước 1 đến 4 của 12.7. Nhánh $\beta$ là node con được tạo sớm nhất.
- `nhan`: $w$ theo bước 5, và nhãn theo bước 6, 7. Thêm vào `meta` các bảng $\hat B(d)$, $S(d)$, $A(d)$, $\sigma_w^2(d)$, $o(d)$, $o_Q(d)$, $\sigma_Q^2(d)$, kèm log của mỗi đời.
- Một công tắc cho phần sửa policy, mặc định tắt.
- Không đụng tới phần nào của mục 8.

### 12.11 So sánh trước và sau

| Phần | Đang chạy | Nâng cấp |
|---|---|---|
| Đích học | Trung bình theo $\pi$ (mục 3), không khớp cách chơi | $V^\beta$, đúng cách ván được chơi |
| Gộp các nhánh | $\rho$ từ G2; đặt 32–66% lên nước rẽ; lệch tới 0,07 | Nhánh rẽ trừ khoảng chênh rồi gộp theo Gauss–Markov; không lệch |
| Phần may rủi $E$ | Cộng dồn $\omega^2U$ (G2); chưa từng kiểm | $\hat B(d)$ đo bằng cặp ván, khớp đơn điệu |
| Phần mạng sai | $\tau_q^2$ bằng phương pháp moment với $c=0$, có sàn | $A=S-\hat B$; $S$ đo lại mỗi đời |
| $c$ giữa $q$ và $G$ | Giả định bằng 0 | Tính được: $\rho_RA$ |
| $q$ trong nhãn | Trung bình gộp, có search lại | Giá trị lúc chơi |
| Nhãn policy | Trung bình $\pi$ | Trung bình $\pi$; tuỳ chọn sửa $\hat Q$ bằng kết quả ván rồi dựng lại |
| Mục 8 | | Giữ nguyên |

### 12.12 Phương án temperature 1 đã cân nhắc và không chọn

Sáng 19/11, mục này từng ghi một phương án khác: ván rẽ bốc nước theo tỉ lệ lượt thăm (temperature 1), kèm nhãn value dùng mạng làm biến kiểm soát và nhãn policy nghiêng bậc nhất với hệ số $\tfrac12$. Các định lý của phương án đó đúng khi ván được bốc theo một phân phối biết trước. Chủ dự án không chọn nó, vì temperature 0 dùng lại được cây search và chơi được nhiều node hơn với cùng ngân sách. Toàn văn còn trong lịch sử git (commit 6dd126a), để tra lại nếu sau này đổi cách chơi.
