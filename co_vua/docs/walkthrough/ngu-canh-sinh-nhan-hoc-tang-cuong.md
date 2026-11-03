# Sinh nhãn huấn luyện tốt hơn cho engine học tăng cường kiểu lc0

**Sổ tay ngữ cảnh của phiên trò chuyện ngày 29/10/2026**

Tệp này ghi lại toàn bộ mạch suy nghĩ của phiên, từ mục tiêu ban đầu, trường hợp quan sát gốc, những cách hiểu đã thử và bị loại, khung tư duy đã thống nhất, cho đến hướng thiết kế đang mở là **đồ thị thế cờ sống dùng chung**. Phiên tạm dừng ở đây để bạn tự suy nghĩ dài, có thể vài tuần, theo hướng đó và cân nhắc kỹ các trade-off. Khi quay lại, đọc phần 1 để nắm nhanh, rồi đọc phần 7 và phần 8 để vào lại đúng mạch.

---

## Mục lục

1. Tóm tắt một trang
2. Mục tiêu và ràng buộc
3. Cách cùng tư duy trong phiên này
4. Bối cảnh nền: vòng lặp tự chơi kiểu lc0
5. Trường hợp quan sát gốc
6. Hành trình các cách hiểu và vì sao chúng bị loại
7. Khung tư duy đã thống nhất
8. Hướng thiết kế đang mở: đồ thị thế cờ sống dùng chung
9. Câu hỏi mở để suy ngẫm
10. Những công trình có liên quan để tham khảo
11. Khi quay lại phiên này
- Phụ lục A: Thuật ngữ
- Phụ lục B: Những ý tưởng đã nêu ở đầu phiên, không phải hướng chính
- Phụ lục C: Cách nhìn theo gradient, đã thử và không phải hướng chính
- Phụ lục D: Dòng thời gian của phiên

---

## 1. Tóm tắt một trang

**Mục tiêu.** Giảm số ván tự chơi mà mạng vẫn đạt sức mạnh tương đương. Cách đạt được không phải là làm search nhanh hơn hay tối ưu phần cứng, mà là thay đổi cách sinh dữ liệu và cách mạng học, để **nhãn chính xác hơn** thay vì dùng số lượng ván để đè bẹp. Vẫn là học tăng cường thuần túy, không đưa hiểu biết của con người vào, và không được tốn thêm nhiều compute.

**Quan sát gốc.** Trong engine tự viết từ đầu của bạn (một biến thể cờ có quân hoàng gia), có một thế cờ mà MCTS duyệt 8000 node và dồn gần hết lượt thăm vào một nước thí quân vô lý (nước a), trong khi nước b tốt hơn. Cả policy tiên nghiệm lẫn value đều sai. Không tham số search nào, không Dirichlet noise, không temperature (vì đã qua 30 nửa nước) cứu được. Mạng đã biết lợi thế vật chất là gì, nhưng tại đây nó "quên hẳn". Thế cờ đó chỉ được sửa sau khi mạng học rất nhiều thế cờ khác, không liên quan, để tự tiến bộ lên rồi quay lại. Con đường đó tốn rất nhiều ván.

**Khung tư duy đã chốt.**

- Kiến thức của mạng hình thành ở những thế cờ này rồi chuyển hóa sang những thế cờ khác. Ranh giới giữa "cũ" và "mới" không cố định.
- Hiện tại nhãn có thể **sai hoàn toàn mà vẫn mang dáng vẻ rất chắc chắn**, và mạng học theo nó như học sự thật.
- Nhãn hỏng theo hai trục độc lập: **nhiễu** (thế khởi đầu) và **lệch** (cái sai kỳ lạ). Bạn muốn tác động vào cả hai cùng lúc.
- Nhãn được tính từ **tín hiệu**. Hai tín hiệu hiện có là kết quả cuối ván (xa nhưng ở ngoài niềm tin của mạng) và kết quả search (gần nhưng ở trong niềm tin của mạng). Trộn hai thứ này chỉ trượt giữa nhiễu và lệch. Muốn giảm cả hai thì cần một **tín hiệu thứ ba, vừa gần vừa ở ngoài**.
- Search vốn đã hỏi mạng về hàng nghìn thế cờ khác, nhưng vẫn "ở trong" vì hai lẽ: các thế cờ được hỏi là do chính niềm tin đang sai chọn ra, và tất cả được hỏi cùng một lúc với cùng một bộ trọng số. Vậy có hai đòn bẩy: **ai chọn thế cờ để hỏi** và **hỏi vào lúc nào**. Bạn nghiêng về cả hai.

**Hướng đang mở.** Thay vì mỗi lần search dựng một cây dùng một lần rồi vứt đi, giữ lại kết quả search của mọi ván, ở mọi thời điểm, trong một **đồ thị thế cờ chung**. Mọi ván vừa đọc vừa ghi vào đồ thị này. Nhãn được **đọc ra từ đồ thị**, tức là từ tất cả những gì mọi ván và mọi phiên bản của mạng đã thấy quanh thế cờ đó. Hướng này chạm đúng cảm giác của bạn. Trước đó bạn cũng đã le lói hai ý: cây search bị vứt đi là lãng phí, và cần giữ nhiều hướng chơi khác nhau trong cùng một bản ghi.

**Việc tiếp theo.** Bạn tự suy nghĩ sâu theo hướng đồ thị, cân nhắc các trade-off ở phần 8.7 và các câu hỏi mở ở phần 9, rồi quay lại tiếp tục phiên này.

---

## 2. Mục tiêu và ràng buộc

Những điều dưới đây là những gì bạn đã nói rõ trong phiên, nên chúng là "luật chơi" khi thiết kế.

### 2.1 Mục tiêu

- **Ít ván tự chơi hơn, sức mạnh tương đương.** Mỗi ván phải mang được nhiều bài học hơn.
- **Phá cách trong việc sinh dữ liệu và huấn luyện.** Sự phá cách này không nói về hiệu năng (search nhanh hơn, tối ưu GPU, tối ưu mã nguồn). Nó nói về chính cách dữ liệu được tạo ra và cách mạng học từ nó.
- **Nhãn chính xác hơn, thay vì dùng số lượng để đè bẹp.** Đây là trực giác xuất phát của bạn.
- **Tác động cùng lúc vào cả hai hiện tượng**: thế khởi đầu (nhiễu) và cái sai kỳ lạ (lệch). Một lời giải chỉ xử lý được một trong hai thì chưa đủ.
- **Có thể sửa được thế cờ đi sai ngay lúc đó.** Ý bạn là: tại thời điểm đó nhãn sai hoàn toàn nhưng hệ thống lại coi nó là rất đúng và cứ học theo. Bạn muốn hệ thống không bị mắc kẹt như vậy.

### 2.2 Ràng buộc

- **Học tăng cường thuần túy.** Không đưa hiểu biết của con người vào nhãn. "Thủ công" theo nghĩa của bạn là thiết kế thêm một cơ chế, chứ không phải nạp kiến thức cờ vào.
- **Không tốn thêm nhiều compute.** Ý dùng hai mạng khác nhau cùng sinh dữ liệu bị loại vì tốn compute.
- **Không nhắm tới giá trị khi chơi hoàn hảo.** Mục tiêu không phải là làm cho nhãn bằng kết quả lý thuyết của thế cờ khi cả hai bên chơi hoàn hảo.
- **Trộn nhãn MCTS với kết quả ván không phải lời giải.** Bạn đã biết kỹ thuật này từ trước, và nhìn chung nó không giải quyết được cùng lúc thế khởi đầu và cái sai kỳ lạ. Phần 7.5 giải thích vì sao.
- **Một đầu ra phụ để đo độ chắc chắn của nhãn**: bạn có le lói ý này nhưng có lẽ sẽ không chọn, vì lúc chơi thật đầu ra đó không được dùng tới. Trong phiên có nêu thêm một lý do khác để cân nhắc: đầu ra đó học từ chính những nhãn do mạng tự sinh, nên ở chỗ mạng sai một cách tự tin, nó dễ học được rằng "chỗ này chắc chắn", tức là mù đúng ở chỗ cần nhìn thấy. Đầu ra phụ không dùng lúc chơi thì vẫn có thể có ích khi huấn luyện (giống moves-left của lc0 hay ownership của KataGo), nên đây không phải lý do đủ mạnh để loại nó. Lý do mạnh hơn là cái mù chung.

---

## 3. Cách cùng tư duy trong phiên này

Phần này ghi lại những gì đã học được về cách trò chuyện cho hiệu quả, để khi tiếp tục không lặp lại những lối đi đã khiến bạn thấy lệch.

- **Luôn tư duy cùng nhau.** Đi theo mạch của bạn, hỏi lại khi chưa rõ, nói thẳng khi thấy có vấn đề, chỉ góp ý tưởng khi nó nối tiếp đúng điều bạn đang nghĩ.
- **Không bày ra nhiều hướng rời rạc.** Một danh sách nhiều ý độc lập không phải là cùng sáng tạo. Nên đào sâu một mạch.
- **Không vội đóng khung trực giác của bạn.** Trực giác thật thường là cảm giác về một cấu trúc chưa có ngôn ngữ để gọi tên. Nó không hiện ra nhờ một phép so sánh với đời sống. Ép nó vào một khung quen thuộc (các cặp tác động, thứ tự học, phép biện chứng theo nghĩa triết học) thì sẽ lệch.
- **Chữ "biện chứng" và "phạm trù"** là bạn dùng để diễn tả sự phức tạp, khi chưa tìm được từ khác. Bạn không muốn đi vào triết học. Bạn muốn giải quyết bằng logic.
- **Logic theo nghĩa của bạn** là suy luận bình thường nhưng sâu dần, không phải công thức toán khó. Bạn thích cách trình bày có chút toán học, nhưng các ký hiệu phải tự hiểu được. Công thức gradient với đại lượng $K$ không giúp được bạn, và cách giải thích không cần $K$ thì ổn hơn.
- **Không xoáy quá nhiều vào thế cờ ví dụ.** Trường hợp quan sát gốc là một cửa sổ để nhìn vào bản chất của quá trình tiến triển, không phải đối tượng duy nhất cần sửa.
- **Không cần ví dụ số giả lập** khi giải thích những thứ bạn đã nắm.
- **Đừng giải thích cơ chế khi việc cần là góp ý tưởng.** Có lúc mình giải thích mãi mà không giúp được việc giải bài toán.

---

## 4. Bối cảnh nền: vòng lặp tự chơi kiểu lc0

Bạn đã nắm rõ cơ chế của lc0. Phần này chỉ nhắc lại để các phần sau có chỗ dựa.

1. Mạng nhận một thế cờ và trả ra **policy** (phân phối xác suất trên các nước đi hợp lệ) và **value** (đánh giá thế cờ cho bên đang đi).
2. **MCTS** dùng policy làm prior để quyết định nhánh nào đáng xét, dùng value để đánh giá các thế ở đầu mút. Kết quả là số lượt thăm của từng nước và giá trị trung bình Q của từng nước. Phần thưởng khám phá trong PUCT có dạng
   $$U(s,a) = c \cdot P(s,a) \cdot \frac{\sqrt{N(s)}}{1 + N(s,a)}$$
   nên một nước có prior nhỏ thì rất ít được thăm.
3. Engine chọn nước dựa trên số lượt thăm, có thêm temperature (trong khoảng 30 nửa nước đầu) và Dirichlet noise ở gốc để đa dạng hóa.
4. Mỗi thế cờ trong ván được lưu thành một mẫu: thế cờ, phân phối lượt thăm (nhãn policy), kết quả ván $z$ (nhãn value, có thể trộn với Q).
5. Mạng được huấn luyện để policy gần nhãn policy và value gần nhãn value, rồi lặp lại.

Hai đặc điểm của vòng lặp này là gốc của mọi chuyện ở các phần sau:

- **Nhãn do chính mạng tạo ra**, thông qua search do chính mạng dẫn đường và đánh giá. Chỉ có kết quả cuối ván là do trò chơi tự phán quyết.
- **Cây search được dùng một lần rồi bỏ đi** (lc0 có tái sử dụng cây con giữa các nước trong cùng một ván, nhưng không giữ qua các ván, không giữ qua thời gian).

---

## 5. Trường hợp quan sát gốc

### 5.1 Mô tả

- Đây là dự án riêng của bạn, chạy từ đầu. Biến thể cờ của bạn có quân hoàng gia.
- Tại một thế cờ, MCTS duyệt 8000 node. Nước a có nhiều lượt thăm hơn nước b rất nhiều. Bạn biết chắc nước b tốt hơn.
- Nước a là một nước thí quân ngu xuẩn. Quân bị thí là quân mà ở tàn cuộc mạng giữ còn quý hơn cả quân hoàng gia. Cách di chuyển của quân đó không liên quan đến vấn đề.
- **Cả policy tiên nghiệm lẫn value đều sai, và sai tai hại.** Bạn không hiểu mạng học kiểu gì mà để cả hai đầu ra cùng sai như vậy.
- Thường thì bạn chỉ thấy **một bên sai**, và khi bên kia cải thiện thì nó kéo bên sai lên. Trường hợp này thì không.
- Không có dấu hiệu tích cực nào từ việc đổi tham số để search lại từ thế cờ đó cho ra kết quả đúng.
- Dirichlet noise không cứu được. Temperature cũng không, vì đã qua hơn 30 nửa nước.
- Mạng đã học được lợi thế vật chất là như thế nào, nhưng **tự dưng ở thế cờ này nó quên hẳn điều đó**. Có rất nhiều thế cờ mà nó không sai kiểu như vậy. Cái sai này hiếm và tai hại.
- Cách duy nhất bạn thấy để cải thiện là để mạng **tự tiến bộ nhờ học nhiều thế cờ không phải thế cờ này**, rồi quay lại thế cờ này thì mới thay đổi được. Cách đó tốn rất nhiều ván tự chơi.

### 5.2 Những điều đã được làm rõ trong phiên

Những điều dưới đây là các chỗ bạn đã sửa lại cách hiểu của mình, nên chúng là phần mô tả chính xác của trường hợp.

- Đây **không phải** chuyện policy và value che lỗi cho nhau.
- Đây **không phải** một trong hai kiểu thất bại quen thuộc: nước b bị bỏ đói khám phá, hoặc value đánh giá sai các thế sau b. Câu hỏi không nhắm vào thế sau b, vì ngay tại thế cờ này MCTS đã ra kết quả sai. Cũng không có lợi thế vật chất nào chỉ hiện ra sau vài nước.
- Làm ngược lại hai kiểu thất bại kia (cho b được thăm nhiều hơn, search sâu hơn) cũng không có dấu hiệu gì là sẽ cải thiện.
- Thế cờ này **không nằm ngoài tầm** của mạng theo kiểu mạng còn quá yếu, vì có nhiều thế tương tự mà mạng xử lý đúng.
- Những thế cờ không liên quan **không phải là "nguồn sửa sai"** theo nghĩa chúng mang lời giải trực tiếp. Mạng phải học nhiều hơn ở những nơi khác để tự cải thiện một cách tổng thể, rồi quay lại thì thế cờ này mới thay đổi được.

### 5.3 Vì sao trường hợp này quan trọng

Trường hợp này không phải là chỗ bế tắc, cũng không phải đối tượng duy nhất cần sửa. Nó là **một cửa sổ nhìn vào bản chất của quá trình tiến triển của mạng**: một hành vi cụ thể chỉ được sửa nhờ sự tiến triển chung trên rất nhiều thế cờ khác, và chính sự tiến triển chung đó là thứ đang tốn nhiều ván. Nó cũng cho thấy rõ hiện tượng **nhãn sai mà tự tin** (phần 7.2) và kiểu hỏng **lệch** (phần 7.3).

---

## 6. Hành trình các cách hiểu và vì sao chúng bị loại

Ghi lại để khi quay lại không đi vòng lại những lối này.

| Cách hiểu hoặc đề xuất đã thử | Vì sao không đúng ý bạn |
|---|---|
| Liệt kê 7 hướng không theo lối mòn ở đầu phiên | Cùng sáng tạo không phải là bày ra nhiều hướng độc lập. Cũng không phải là cố tránh các kỹ thuật quen thuộc. |
| Policy và value "che lỗi" cho nhau, hệ ổn định quanh lỗi | Không có dấu hiệu nào của việc lỗi bên này bị bên kia che đi. |
| Hai kiểu thất bại: bỏ đói khám phá, hoặc đánh giá sai có hệ thống | Không đúng. Ngay tại thế đó search đã ra kết quả sai, và làm ngược lại hai kiểu này cũng không có dấu hiệu cải thiện. |
| Các thế cờ khác là "nguồn sửa sai" | Không phải nguồn sửa sai. Mạng phải tự tiến bộ tổng thể rồi quay lại. |
| Thế cờ nằm ngoài tầm của mạng | Không đúng, vì có nhiều thế tương tự mà mạng xử lý đúng. |
| Liệt kê các cặp đối tượng tác động qua lại (policy với value, mạng với search, thế cờ với thế cờ...) | Phức tạp hơn các cặp tác động qua lại nhiều. Kéo nhau lên khi một bên đúng chỉ là một phạm trù rất nhỏ. |
| Gợi ý mô tả trực giác bằng hình ảnh hay phép so sánh với đời sống | Trực giác thật không giống như trong phim. Nó khó nghĩ hơn nhiều. |
| Kiến thức của mạng gắn với bối cảnh, ở đây bối cảnh khiến nó không được kích hoạt | Không phải. Đây là một điều tai hại và hiếm theo một kiểu nào đó. |
| Hỏi mạng sai ở khâu nào: value sau b, policy không nghĩ tới b, hay lợi thế hiện ra sau vài nước | Không cái nào đúng. Cả hai đầu ra đều sai ngay tại thế đó. |
| Đọc theo phép biện chứng triết học: lượng đổi dẫn tới chất đổi | Bạn không rõ triết học. Thuật ngữ chỉ là cách diễn tả sự phức tạp. Bạn muốn giải quyết bằng logic. |
| Ba bước suy luận bằng lời thường (mạng học chỗ này đổi chỗ khác, ván dạy cả những thế không có trong ván, dữ liệu được chọn theo diễn biến ván) | Không phải như vậy. Bạn thích cách trình bày kiểu toán học hơn. |
| Cách nhìn theo gradient với đại lượng $K$, rồi tách nhãn thành tín hiệu cộng nhiễu, rồi phân biệt nhiễu và lệch | Ký hiệu không tự hiểu được. Sau khi giải thích $K$ bằng ví dụ thì vẫn không giúp được. Bạn thấy giải thích không cần $K$ ổn hơn. |
| Hai mạng khác nhau cùng sinh dữ liệu, chỗ bất đồng là chỗ đáng ngờ | Không chạm tới điều bạn muốn, và tốn compute quá. |
| Sửa nhãn bằng nhận thức muộn: nước nào làm đánh giá tụt mạnh vài nước sau thì sửa nhãn tại đó | Không phải. Xoáy quá nhiều vào thế cờ ví dụ. |
| Nhãn "ba phần": niềm tin sẵn có, thông tin mới, nhiễu; và "chỉ có hai nguồn thông tin mới" | Không phải như vậy, các thành phần có quan hệ chuyển hóa với nhau, không tách rời và cộng dồn được. |
| Hỏi mạng về các phiên bản tương đương của thế cờ (đối xứng, thay đổi nhỏ không liên quan) | Rập khuôn, không có ý nghĩa gì. Mạng tích chập dùng phép đối xứng không có ý nghĩa nhiều. |
| Nhắm tới giá trị khi chơi hoàn hảo ("thế này thắng sau 40 nước") | Câu đó nói quá. Bạn không nhắm tới giá trị khi chơi hoàn hảo. |
| "Luật cờ" là thứ duy nhất ở ngoài niềm tin của mạng | Chữ "luật cờ" quá rộng. Luật di chuyển quân không giúp gì cho nhãn. Ý đúng là phán quyết ở thế kết thúc (phần 7.7). |

Điểm chung của phần lớn những lần lệch: mình cố đặt tên hoặc đóng khung cho trực giác của bạn bằng một cơ chế quen thuộc, hoặc đề xuất một kỹ thuật cục bộ, trong khi bạn đang tìm một thay đổi mang tính cấu trúc về cách nhãn được tạo ra.

---

## 7. Khung tư duy đã thống nhất

Đây là phần cốt lõi, được xây dần qua phiên và bạn đã đồng ý với từng bước.

### 7.1 Kiến thức chuyển hóa qua lại

Kiến thức không chỉ đi vào hệ thống từ vài nguồn cố định rồi cộng dồn. Nó **được sinh ra từ chính sự tác động qua lại**:

- Mạng học ở những thế cờ này, và nhờ trọng số chung, nó hình thành đánh giá đúng ở những thế cờ mà chưa có search hay phán quyết kết thúc nào chạm tới.
- Đánh giá mới đó được search dùng ở chỗ khác, kết hợp với những đánh giá khác, và tạo ra nhãn tốt hơn ở đó.
- Nhãn tốt hơn lại thay đổi mạng. Mạng thay đổi thì ván cờ đi khác. Ván đi khác thì mạng gặp những thế cờ khác.

Vì vậy cái gọi là "niềm tin sẵn có của mạng" ở chỗ này thực ra là kiến thức mới vừa hình thành từ chỗ khác. **Ranh giới giữa cũ và mới không cố định**, nó tùy vào đang xét ở đâu và vào lúc nào. Không có thành phần nào chỉ đơn thuần chép lại. Mỗi thành phần vừa là sản phẩm của các thành phần khác, vừa làm thay đổi chúng. Đây là ý mà bạn gọi là "quan hệ biện chứng", và nó nói về **bản chất của quá trình tiến triển của mạng** nói chung.

Từ đây câu hỏi có thể phát biểu là: **làm sao để vòng chuyển hóa này quay nhanh hơn, hoặc hiệu quả hơn, trên mỗi ván cờ?**

### 7.2 Nhãn sai mà tự tin

Vấn đề trong trường hợp quan sát gốc không nằm ở chỗ tìm ra nước đúng. Vấn đề là **nhãn sai hoàn toàn nhưng lại mang dáng vẻ của một nhãn rất chắc chắn**, và mạng học theo nó như học sự thật.

Cách làm hiện tại không phân biệt được hai thứ:

- **Chắc vì đã được kiểm chứng.** Search đã thử các khả năng phản bác và chúng đều thất bại.
- **Chắc vì không có gì phản bác.** Policy và value cùng nghiêng về một hướng, nên search cứ dồn lượt thăm vào đó mà không thực sự thử thách nó.

Cả hai trường hợp đều cho ra cùng một nhãn: 8000 node dồn gần hết vào một nước. Tệ hơn, nhãn càng tập trung thì mạng càng bị kéo mạnh về phía nó. Vì vậy **một nhãn sai mà tự tin được học mạnh hơn một nhãn đúng mà còn phân vân**.

Bạn thấy câu hỏi "làm sao để hệ thống biết được độ chắc chắn của nhãn đến từ đâu" là gần đúng, nhưng trực giác của bạn đi theo một hướng khác: **làm sao cho nhãn có giá trị đúng hơn**, bằng những cách nào.

### 7.3 Mục tiêu của nhãn value, nhiễu và lệch

Nhãn value của một thế cờ là con số mạng được huấn luyện để trả ra tại thế đó. Nó được dùng để ước lượng **mục tiêu** của nhãn: kết quả trung bình nếu từ thế cờ đó, chính mạng hiện tại tự chơi tiếp rất nhiều ván. Mục tiêu này phụ thuộc vào trình độ của mạng, và đó là điều bình thường. Một ván chỉ cho một kết quả, nên nhãn lấy từ một ván chỉ là một lần lấy mẫu của mục tiêu.

Một nhãn có thể khác mục tiêu theo hai cách:

**Trục thứ nhất, nhiễu.** Từng nhãn riêng lẻ lệch khỏi mục tiêu, nhưng trung bình của nhiều nhãn thì đúng. Thế khởi đầu thuộc trục này. Nếu mạng non chơi tiếp từ thế khởi đầu rất nhiều ván thì thắng, hòa, thua theo một tỉ lệ nào đó, mục tiêu là trung bình của chúng, nhưng mỗi nhãn riêng lẻ là thắng, hòa hoặc thua, nên phần lớn nhãn cách mục tiêu rất xa. Muốn học được mục tiêu thì phải gom thật nhiều ván. Đây là chỗ **số lượng dùng để đè bẹp**.

**Trục thứ hai, lệch.** Nhãn sai ngay cả khi lấy trung bình. Lặp lại việc tạo nhãn bao nhiêu lần cũng sai theo cùng một hướng. Cái sai kỳ lạ thuộc trục này: chạy lại search 100 lần thì cả 100 lần đều dồn vào nước a, vì search được dẫn đường bởi cùng một mạng đang sai. **Số lượng không chữa được lệch.**

Hai trục này độc lập với nhau. Một cơ chế làm nhãn đúng hơn có thể tác động vào trục này, trục kia, hoặc cả hai. **Bạn muốn tác động vào cả hai.**

### 7.4 Thế khởi đầu và cái sai kỳ lạ có chung một gốc

Bạn đã chỉ ra một điều quan trọng: khi mạng còn non, phương sai của nhãn value ở thế khởi đầu quá lớn nên buộc phải dùng số lượng để đè, và bạn muốn ngay cả thế khởi đầu cũng học được mà không cần phương sai lớn như vậy.

Phương sai lớn không phải vì thế khởi đầu khó. Nó lớn vì **nhãn của thế đó bị trộn với chất lượng chơi của chính mạng ở phía sau**:

$$z = \text{giá trị của } s + \text{sai lệch do những nước đi sau } s$$

Đặt cạnh cái sai kỳ lạ thì thấy cùng một gốc:

| | Nhãn thực sự đo cái gì | Kiểu hỏng |
|---|---|---|
| Thế khởi đầu | Cách mạng chơi tiếp *sau* thế đó | Nhiễu lớn |
| Cái sai kỳ lạ | Cách mạng nghĩ *tại* thế đó | Lệch, tự tin sai |

Trong cả hai trường hợp, **nhãn của một thế cờ được tạo ra bằng hành vi của chính mạng**. Bạn đồng ý rằng hướng này gần đúng, nhưng đặt câu hỏi đúng chỗ: làm nhãn đúng hơn thì có nhất thiết là làm nhãn ít phụ thuộc vào trình độ hiện tại của mạng hơn không? Câu trả lời đã thống nhất là không nhất thiết. Mục tiêu của nhãn vốn dĩ phụ thuộc vào trình độ. "Đúng hơn" có nghĩa là ít nhiễu hơn quanh mục tiêu và ít lệch hơn so với mục tiêu.

### 7.5 Tín hiệu, khoảng cách và nguồn gốc

Để có nhãn cho một thế cờ, hệ thống phải dựa vào một thông tin nào đó xuất hiện trong quá trình tự chơi, có liên quan đến việc thế cờ đó tốt hay xấu. Mỗi thông tin như vậy, tức là thứ mà nhãn được tính ra từ nó, được gọi là một **tín hiệu**. Hiện có hai tín hiệu: **kết quả cuối ván** và **kết quả search tại thế cờ**.

**Khoảng cách: gần hay xa.** Giữa lúc thế cờ xuất hiện và lúc tín hiệu được tạo ra, có thể có nhiều nước đi được chọn. Mỗi lần chọn có yếu tố ngẫu nhiên (temperature, Dirichlet noise, những nước hớ của mạng non). Mỗi lựa chọn như vậy có thể làm thay đổi tín hiệu mà không liên quan gì đến giá trị của thế cờ ban đầu.

- Kết quả cuối ván có hàng chục lựa chọn ngẫu nhiên chen vào, nên nó **ở xa**. Ở thế khởi đầu, con số này là cả ván cờ.
- Kết quả search không có nước đi thật nào chen vào, vì nó được tính ngay tại thế đó, nên nó **ở gần**.
- Tín hiệu càng gần thì nhãn càng ít nhiễu.

**Nguồn gốc: ở trong hay ở ngoài.** Một tín hiệu có thể được quyết định bởi chính niềm tin của mạng tại thế cờ đó, hoặc bởi một thứ nằm ngoài niềm tin ấy.

- Kết quả cuối ván do phán quyết kết thúc của trò chơi quyết định, bất kể mạng nghĩ gì, nên nó **ở ngoài**.
- Kết quả search được tính bằng policy và value của chính mạng, nên nó **ở trong**.
- Tín hiệu càng ở ngoài thì nhãn càng ít lệch.

| Tín hiệu | Khoảng cách | Nguồn gốc | Kiểu hỏng của nhãn |
|---|---|---|---|
| Kết quả cuối ván | Xa | Ở ngoài | Ít lệch, nhiều nhiễu |
| Kết quả search | Gần | Ở trong | Ít nhiễu, có thể lệch |

**Vì sao trộn nhãn không đủ.** Mỗi tín hiệu hiện có chỉ có một trong hai tính chất tốt. Trộn chúng theo một tỉ lệ nào đó chỉ là trượt giữa hai đầu: nghiêng về kết quả cuối ván thì bớt lệch nhưng thêm nhiễu, nghiêng về search thì bớt nhiễu nhưng thêm lệch. Không có tỉ lệ trộn nào giảm được cả hai. Đó là lý do việc trộn nhãn không giải quyết được đồng thời thế khởi đầu và cái sai kỳ lạ, đúng như bạn đã nhận thấy từ trước.

### 7.6 Yêu cầu: một tín hiệu thứ ba vừa gần vừa ở ngoài

Muốn giảm cả nhiễu lẫn lệch thì cần một **loại tín hiệu thứ ba**, có đủ cả hai tính chất cùng lúc:

1. **Gần**: ít lựa chọn ngẫu nhiên chen vào giữa thế cờ và tín hiệu, để nhãn ít nhiễu.
2. **Ở ngoài**: không do chính niềm tin đã tạo ra nhãn quyết định, để nhãn ít lệch.

Câu hỏi thiết kế mà bạn thấy rất hợp:

> **Trong quá trình tự chơi, ở đâu có thể tạo ra một tín hiệu vừa gần vừa ở ngoài?**

### 7.7 "Ở ngoài" có thể đến từ đâu

Ban đầu mình viết rằng thứ duy nhất ở ngoài niềm tin của mạng là "luật cờ". Bạn chỉ ra rằng chữ đó không rõ: luật di chuyển quân không giúp gì cho việc tạo nhãn. Ý đúng hẹp hơn nhiều và được làm rõ thành hai nguồn:

1. **Phán quyết ở thế kết thúc.** Đó là những luật quyết định một thế cờ là thắng, hòa hay thua, như bắt quân hoàng gia hay chiếu hết, hết nước đi, các luật hòa. Đây là chỗ duy nhất mà trò chơi tự nói ra một giá trị, không thông qua mạng. Kết quả cuối ván chính là phán quyết này được mang ngược về các thế cờ trước. Nguồn này tuyệt đối đúng nhưng thường ở xa.
2. **Kiến thức của mạng ở những nơi khác**: những thế cờ khác, hoặc chính mạng ở một thời điểm khác. Xét riêng tại một thế cờ, những đánh giá mà mạng hình thành ở nơi khác có thể coi là ở ngoài niềm tin tại thế đó, miễn là chúng không bị chi phối bởi cùng cái niềm tin đang sai. Nguồn này không tuyệt đối đúng, nhưng có thể ở gần, và không mắc cùng cái sai tại thế đang xét. Nguồn này nhất quán với ý chuyển hóa ở phần 7.1.

### 7.8 Search đã hỏi mạng ở thế cờ khác, vậy vì sao vẫn "ở trong"

Bạn hỏi: lấy kiến thức của mạng ở nơi khác bằng cách nào, chẳng lẽ đang đấu trận này ta thử hỏi mạng ở thế cờ khác? Câu trả lời là có, và **MCTS đang làm đúng việc đó**: để chọn nước tại thế đang đấu, search hỏi mạng về hàng nghìn thế cờ khác rồi tổng hợp lại.

Search vẫn ra tín hiệu "ở trong" vì hai lẽ:

1. **Thế cờ nào được hỏi là do chính niềm tin đang sai chọn ra.** Policy quyết định search đi vào nhánh nào. Nếu policy sai thì những thế được hỏi đều nằm trong vùng mà cái sai dẫn tới, còn những thế có thể phản bác thì ít khi được hỏi.
2. **Tất cả được hỏi cùng một lúc, với cùng một bộ trọng số**, nên các câu trả lời dễ mắc cùng một cái sai.

Do đó có **hai đòn bẩy** để kiến thức "ở nơi khác" thực sự ở ngoài:

- **Thay đổi ai chọn thế cờ để hỏi**: thế được hỏi không phải do policy tại thế đang xét chọn ra.
- **Thay đổi thời điểm hỏi**: câu trả lời đến từ mạng ở một trạng thái hiểu biết khác.

Bạn nghiêng về cả hai, nhưng lúc đó chưa có ý tưởng thiết kế nào thỏa mãn cả hai. Phần 8 là hướng ra đời từ đây.

---

## 8. Hướng thiết kế đang mở: đồ thị thế cờ sống dùng chung

### 8.1 Xuất phát từ trực giác của bạn

Trước khi hỏi ý tưởng thiết kế, bạn đã nghĩ tới hai điều:

- Hiện tại mỗi lần search là một cây được dựng tại một thế cờ, cho ra nhãn rồi bị vứt đi.
- Le lói việc phải **giữ nhiều hướng chơi khác nhau trong cùng một bản ghi**.

Hướng dưới đây gộp hai điều đó lại và nối chúng với hai đòn bẩy ở phần 7.8.

### 8.2 Ý tưởng

Hàng triệu ván tự chơi đi qua những vùng thế cờ chồng lấn lên nhau, nhưng không ván nào biết các ván khác đã thấy gì. Ý tưởng là **giữ lại toàn bộ kết quả search của mọi ván trong một đồ thị chung**:

- Mỗi nút là một thế cờ. Nút lưu những gì đã biết về thế đó: các đánh giá, số lượt thăm, các phán quyết kết thúc đã chạm tới bên dưới nó.
- Mọi ván tự chơi **vừa đọc từ đồ thị vừa ghi thêm vào nó**.
- Nhãn của một thế cờ không còn là kết quả của một lần search riêng lẻ hay của một ván riêng lẻ. **Nhãn được đọc ra từ đồ thị**, tức là từ tất cả những gì mọi ván và mọi phiên bản của mạng đã từng thấy quanh thế cờ đó.

Nói gọn: **nhãn được đọc ra từ một kiến thức tích lũy chung, thay vì từ từng lần search riêng lẻ.**

### 8.3 Nó đáp ứng hai đòn bẩy thế nào

- **Ai chọn thế cờ để hỏi.** Các nút quanh một thế cờ được thêm vào bởi rất nhiều lần search khác nhau, bắt đầu từ nhiều thế cờ khác nhau, trong nhiều ván khác nhau. Chúng không chỉ do policy tại thế đang xét chọn ra. Một nhánh mà policy tại đây bỏ qua vẫn có thể đã được một ván khác đi vào từ một hướng khác (chẳng hạn qua một thứ tự nước đi khác dẫn đến cùng thế cờ).
- **Thời điểm hỏi.** Các nút được đánh giá bởi mạng ở nhiều thời điểm khác nhau. Khi mạng mới đi qua một vùng, nó đánh giá lại các nút ở đó, nên kiến thức mới tự lan vào những thế cờ mà nó không trực tiếp chơi.

### 8.4 Nó tác động lên hai hiện tượng thế nào

- **Thế khởi đầu (nhiễu).** Mọi ván đều đi qua thế khởi đầu, nên trong đồ thị nó tổng hợp bằng chứng từ tất cả các ván thông qua cấu trúc của các nhánh bên dưới. Nhãn của nó không còn là kết quả của một ván đơn lẻ với hàng chục nước ngẫu nhiên phía sau. Tín hiệu trở nên gần, vì nhãn đến từ các nút con ngay sau nó.
- **Cái sai kỳ lạ (lệch).** Nếu bất kỳ ván nào khác, ở bất kỳ thời điểm nào, đã đi qua vùng đó và thấy được hậu quả của nước thí quân, thì thông tin ấy nằm sẵn trong đồ thị. Thông tin này ở ngoài niềm tin của mạng tại thế đó, vì nó đến từ những lần hỏi khác, do người khác chọn, vào lúc khác.

### 8.5 Nối lại với ý "phán quyết kết thúc lên tiếng ở gần hơn"

Ở phần 7.7, nguồn "ở ngoài" tuyệt đối là phán quyết kết thúc, nhưng hiện tại nó chỉ đến được một thế cờ qua kết quả của đúng một ván, tức là rất xa. Trong đồ thị, **một phán quyết kết thúc mà bất kỳ ván nào chạm tới sẽ được ghi vào nút kết thúc đó và lan ngược lên các nút cha**. Một thế cờ ở gần phán quyết đó trong đồ thị sẽ nhận được nó qua vài bước trong đồ thị, chứ không phải qua hàng chục nước ngẫu nhiên của một ván riêng. Như vậy đồ thị là một cách cụ thể để **phán quyết kết thúc lên tiếng ở gần hơn**, và để nguồn "kiến thức ở nơi khác" (phần 7.7, nguồn thứ hai) trở nên có cấu trúc.

### 8.6 Về compute

Đồ thị không cần thêm lần chạy mạng nào, vì nó chỉ giữ lại những gì đã tính. Nó còn có thể tiết kiệm compute, vì search ở ván sau dùng lại được đánh giá mà ván trước đã tính. Chi phí chuyển sang bộ nhớ và việc quản lý đồ thị.

### 8.7 Chỗ yếu và trade-off

Bạn đã biết trước là có trade-off. Đây là những chỗ đã nêu trong phiên, cộng thêm vài chỗ đáng cân nhắc khi bạn suy nghĩ dài:

- **Bộ nhớ.** Không thể giữ mọi thế cờ, nên phải có cách bỏ đi những vùng ít được ghé thăm. Vùng khai cuộc thì dày, vùng trung tàn cuộc thì thưa và ít trùng lặp.
- **Đánh giá cũ.** Đánh giá của mạng non có thể sai, nên đồ thị cần có cách cho đánh giá cũ mất dần trọng lượng khi mạng tiến bộ, hoặc cách làm mới chúng.
- **Lệch tập thể.** Nếu mọi ván và mọi phiên bản của mạng đều cùng tránh một vùng, thì đồ thị cũng không có thông tin về vùng đó. Đồ thị giảm lệch của một lần search, nhưng không tự động giảm lệch của cả quần thể.
- **Vòng phản hồi.** Đồ thị tạo nhãn, nhãn huấn luyện mạng, mạng ghi vào đồ thị. Một vòng như vậy có thể khuếch đại một sai lầm sớm, hoặc làm hệ thống ổn định quanh một vùng quen thuộc.
- **Mục tiêu bị trộn.** Đồ thị trộn đánh giá từ nhiều phiên bản mạng, tức là nhiều trình độ khác nhau. Nhãn đọc ra từ đồ thị vì vậy không còn đúng là "kết quả trung bình khi mạng hiện tại chơi tiếp". Điều này có thể có lợi hoặc có hại, và cần nghĩ kỹ.
- **Độ thưa ngoài khai cuộc.** Ở những vùng hiếm khi có hai ván cùng đi qua, đồ thị gần như chỉ còn là cây của một lần search, nên lợi ích giảm đi. Lợi ích của đồ thị phụ thuộc vào mức độ các ván chồng lấn nhau.
- **Phân tán.** Nếu tự chơi chạy trên nhiều máy, đồ thị chung cần được đồng bộ.

---

## 9. Câu hỏi mở để suy ngẫm

Các câu hỏi dưới đây không phải đáp án, mà là những chiều thiết kế mà hướng đồ thị mở ra. Chúng được nhóm lại để bạn có thể suy nghĩ từng nhóm một.

### A. Cấu trúc của đồ thị

- Đồ thị gộp các thế cờ trùng nhau (chuyển vị) thành một nút, hay giữ theo đường đi? Gộp thì tổng hợp được nhiều hơn nhưng mất thông tin về lịch sử (luật lặp lại, luật hòa theo số nước).
- Thế nào là "cùng một thế cờ" trong biến thể của bạn? Những trạng thái phụ nào (quyền đặc biệt, bộ đếm) phải nằm trong khóa của nút?
- Đồ thị là một cấu trúc toàn cục duy nhất, hay nhiều đồ thị cục bộ theo vùng, theo thời kỳ huấn luyện?
- "Giữ nhiều hướng chơi khác nhau trong cùng một bản ghi", ý le lói của bạn, có thể là một bản ghi kiểu gì: một ván kèm các nhánh phụ, một vùng đồ thị, hay một đơn vị dữ liệu hoàn toàn mới thay cho "một ván"?

### B. Mỗi nút lưu gì

- Chỉ lưu đánh giá và lượt thăm, hay lưu cả đánh giá đó do phiên bản mạng nào tạo ra và vào lúc nào?
- Có lưu riêng những gì đến từ phán quyết kết thúc (đã được chứng minh) và những gì chỉ là ước lượng của mạng không? Sự phân biệt này có thể nối với ý "chắc vì kiểm chứng" và "chắc vì không bị phản bác" ở phần 7.2.
- Có lưu mức độ bất đồng giữa các lần đánh giá khác nhau của cùng một nút không?

### C. Đọc nhãn value từ đồ thị

- Giá trị của một nút được tổng hợp từ các nút con bằng cách nào: trung bình theo lượt thăm, lấy theo nước tốt nhất, hay một cách kết hợp khác?
- Đánh giá từ các phiên bản mạng khác nhau được cân như thế nào?
- Với thế khởi đầu, nhãn đọc từ đồ thị có thực sự ít nhiễu hơn trung bình kết quả của nhiều ván không, và nếu có thì vì sao? Một gợi ý để soi: trung bình kết quả nhiều ván chỉ tổng hợp kết quả cuối, còn đồ thị tổng hợp được cả cấu trúc ở giữa.
- Nhãn đọc từ đồ thị nằm ở đâu trên bảng "gần, xa, trong, ngoài" ở phần 7.5?

### D. Đọc nhãn policy từ đồ thị

- Nhãn policy lấy từ lượt thăm tích lũy qua mọi ván, hay từ giá trị của các nút con?
- Lượt thăm tích lũy có nguy cơ thiên về những nhánh phổ biến chỉ vì chúng phổ biến không? Nếu có, nhãn policy có thể lại tự củng cố đúng kiểu sai ở phần 7.2.
- Có cách nào để nhãn policy phản ánh "nhánh này đã bị thử thách và đứng vững" thay vì "nhánh này được đi nhiều"?

### E. Thời gian và độ cũ

- Khi nào một nút được đánh giá lại bằng mạng mới: khi có ván đi qua, theo lịch cố định, hay khi có dấu hiệu bất đồng?
- Đánh giá cũ mất trọng lượng theo thời gian, theo số thế hệ mạng, hay theo mức độ mâu thuẫn với đánh giá mới?
- Sự bất đồng giữa đồ thị và một lần đánh giá mới của mạng tại cùng một nút có thể là chính tín hiệu báo nhãn đang sai mà tự tin không?

### F. Ai chọn thế cờ và lệch tập thể

- Làm sao để đồ thị không dần dần chỉ còn chứa những vùng mà mọi phiên bản mạng đều thích?
- Các ván tự chơi có nên được dẫn đường một phần bởi đồ thị, chẳng hạn đi vào những vùng đồ thị còn mỏng hoặc còn bất đồng, không?
- Thế cờ bắt đầu ván có nhất thiết phải luôn là thế khởi đầu không, khi đã có đồ thị?

### G. Vòng phản hồi và tính ổn định

- Điều gì ngăn một sai lầm sớm bị đồ thị lưu lại rồi khuếch đại qua các thế hệ mạng?
- Đồ thị có nên có "bộ phận quên" để thoát khỏi những vùng ổn định quanh lỗi không?

### H. Quan hệ với mục tiêu của nhãn

- Nhãn đọc từ đồ thị là kết quả kỳ vọng dưới trình độ nào, khi đồ thị trộn nhiều trình độ? Điều này có cần thiết phải "sạch" không, hay chính sự trộn lẫn là một phần của sự chuyển hóa ở phần 7.1?

### I. Kiểm tra lại với hai hiện tượng

- Với cái sai kỳ lạ: trong đồ thị, cần điều kiện gì để thông tin "nước a là thí quân vô lý" có mặt và đến được nút đó? Nếu không có ván nào đi qua vùng hậu quả của a, đồ thị có giúp được gì không?
- Với thế khởi đầu: ở giai đoạn mạng rất non, đồ thị chứa toàn đánh giá của mạng non. Khi đó nó còn giúp giảm nhiễu không, hay lợi ích chỉ xuất hiện sau một thời gian?

### J. Đo lường thành công

- Thước đo chính: số ván tự chơi (hoặc tổng compute) cần để đạt một mức sức mạnh nhất định, so với cách làm thông thường.
- Thước đo phụ: đo trực tiếp nhiễu và lệch của nhãn, chẳng hạn trên một tập thế cờ đã biết rõ giá trị trong biến thể của bạn.
- Đếm số lần xuất hiện những cái sai kỳ lạ kiểu trường hợp gốc, và thời gian để chúng tự biến mất.

### K. Thử nghiệm nhỏ

- Có thể thử trước trên một phiên bản thu nhỏ của biến thể (bàn nhỏ hơn, ít quân hơn) để các ván chồng lấn nhau nhiều và đồ thị dày không?
- So sánh ba cấu hình: cây dùng một lần (thông thường), đồ thị chỉ dùng để tái sử dụng search (không dùng làm nhãn), và đồ thị dùng làm nguồn nhãn. Cấu hình giữa giúp tách lợi ích về compute khỏi lợi ích về chất lượng nhãn.

---

## 10. Những công trình có liên quan để tham khảo

Phần này do mình nêu từ trí nhớ, chưa tra cứu lại trong phiên, nên **cần tự kiểm chứng** tên, tác giả và nội dung trước khi dựa vào. Mục đích là để biết hướng đồ thị giống và khác những gì đã có.

- **MuZero Reanalyze** (DeepMind): dữ liệu cũ được search lại bằng mạng mới để tạo nhãn mới. Đây là đòn bẩy **thời điểm hỏi**, nhưng làm theo từng thế cờ riêng lẻ, không có cấu trúc chung giữa các ván.
- **Monte-Carlo Graph Search** (Czech, Korus, Kersting, khoảng 2021, dùng cho engine CrazyAra): biến cây search thành đồ thị có hướng để gộp các thế cờ chuyển vị **bên trong một lần search**. Hướng của bạn khác ở chỗ đồ thị tồn tại **qua nhiều ván và qua thời gian**, và được dùng làm **nguồn nhãn**.
- **Go-Exploit** (Trudeau và Bowling, khoảng 2023): bắt đầu ván tự chơi từ những thế cờ lấy trong một kho lưu trữ. Đây là đòn bẩy **ai chọn thế cờ**, áp dụng cho thế bắt đầu ván, không phải cho nhãn.
- **Tái sử dụng cây giữa các nước trong lc0**: cây con được giữ lại sang nước tiếp theo, nhưng chỉ trong cùng một ván.
- **Các tệp "kinh nghiệm" hoặc "học" trong một số engine cổ điển** (một số bản phái sinh của Stockfish có cơ chế lưu kết quả search qua nhiều ván): là một dạng kho kiến thức tồn tại qua các ván, nhưng dùng để chơi, không dùng để huấn luyện mạng.

Theo những gì mình biết, sự kết hợp "đồ thị chung qua mọi ván và mọi thời điểm, dùng làm nguồn nhãn cho huấn luyện tự chơi" không phải là cách làm thông thường. Nhưng đây là đánh giá từ trí nhớ, nên đáng tra cứu thêm.

---

## 11. Khi quay lại phiên này

Khi bạn quay lại sau thời gian suy nghĩ, những thứ hữu ích để mang theo:

- Bạn đã đi sâu vào chiều nào của hướng đồ thị (các nhóm A đến K ở phần 9), và chiều nào bạn thấy là cốt lõi.
- Những trade-off nào bạn chấp nhận được, những cái nào bạn thấy là chí mạng.
- Hướng đồ thị có còn đúng với trực giác ban đầu của bạn không, hay trực giác đã dịch chuyển sang một hình dạng khác.
- Nếu đã thử nghiệm: cấu hình, kết quả, và những hiện tượng lạ.

Cách tiếp tục vẫn như cũ: cùng tư duy theo mạch của bạn, không bày ra nhiều hướng rời rạc, không vội đóng khung, và đi bằng logic sâu dần.

---

## Phụ lục A: Thuật ngữ

- **Policy**: phân phối xác suất trên các nước đi hợp lệ mà mạng trả ra cho một thế cờ.
- **Prior**: policy của mạng khi được search dùng để quyết định nhánh nào đáng xét.
- **Value**: con số mạng trả ra để đánh giá thế cờ cho bên đang đi.
- **MCTS**: thuật toán tìm kiếm cây Monte Carlo, xây dần một cây các biến cờ từ thế hiện tại.
- **PUCT**: công thức chọn nhánh trong MCTS, cân bằng giữa giá trị đã biết và phần thưởng khám phá tỉ lệ với prior.
- **Q**: giá trị trung bình mà search tính được cho một nước.
- **Dirichlet noise**: nhiễu cộng vào prior ở gốc để buộc search khám phá thêm.
- **Temperature**: tham số làm việc chọn nước theo lượt thăm trở nên ngẫu nhiên hơn, thường chỉ dùng trong khoảng 30 nửa nước đầu.
- **$z$**: kết quả cuối ván (thắng, hòa, thua).
- **Nhãn**: con số hoặc phân phối mà mạng được huấn luyện để trả ra tại một thế cờ.
- **Mục tiêu của nhãn value**: kết quả trung bình nếu từ thế cờ đó, mạng hiện tại tự chơi tiếp rất nhiều ván.
- **Nhiễu**: từng nhãn lệch khỏi mục tiêu nhưng trung bình nhiều nhãn thì đúng. Số lượng chữa được.
- **Lệch**: nhãn sai theo cùng một hướng mỗi lần được tạo ra. Số lượng không chữa được.
- **Tín hiệu**: thông tin xuất hiện trong quá trình tự chơi mà nhãn được tính ra từ đó.
- **Gần / xa**: ít hay nhiều lựa chọn ngẫu nhiên chen vào giữa thế cờ và tín hiệu.
- **Ở trong / ở ngoài**: tín hiệu được quyết định bởi chính niềm tin của mạng tại thế cờ đó, hay bởi thứ nằm ngoài niềm tin ấy.
- **Phán quyết ở thế kết thúc**: luật quyết định một thế cờ là thắng, hòa hay thua.
- **Đồ thị thế cờ sống dùng chung**: hướng thiết kế đang mở, giữ kết quả search của mọi ván, mọi thời điểm trong một cấu trúc chung và đọc nhãn từ đó.

---

## Phụ lục B: Những ý tưởng đã nêu ở đầu phiên, không phải hướng chính

Ở tin nhắn đầu tiên, mình đã liệt kê một loạt hướng. Bạn chỉ ra rằng cùng sáng tạo không phải là làm nhiều hướng độc lập như vậy. Ghi lại ở đây chỉ để biết chúng đã được nêu:

1. Phân nhánh theo độ "bất ngờ": dồn ngân sách rẽ nhánh vào các thế mà search và mạng lệch nhau nhiều.
2. Cặp tối thiểu: các cặp thế cờ chỉ khác nhau một chi tiết nhưng đánh giá khác hẳn.
3. Bộ sinh thế cờ đối kháng: tìm thế mà mạng đánh giá sai nhiều nhất so với search sâu.
4. Giáo trình ngược thời gian: bắt đầu ván từ các thế cuối ván cũ, lùi dần về sớm hơn.
5. Phẫu thuật nước hớ: cắt ván ở chỗ value nhảy vọt, gán lại nhãn phía trước.
6. Khai thác các nút bên trong cây search làm mẫu huấn luyện. Ý này có họ hàng với hướng đồ thị, vì cả hai đều không muốn vứt đi kết quả search. Khác biệt là hướng đồ thị giữ lại qua các ván và qua thời gian, và dùng cấu trúc đó làm nguồn nhãn.
7. Ván chấp có kiểm soát để giữ mức tranh chấp, giảm tỉ lệ hòa.

Ở đầu phiên cũng có nêu một cách đo hiệu quả: lượng học được trên mỗi đơn vị compute, và tỉ lệ tín hiệu trên nhiễu của nhãn value
$$\text{SNR} = \frac{\mathrm{Var}_s\big(\mathbb{E}[z \mid s]\big)}{\mathbb{E}_s\big[\mathrm{Var}(z \mid s)\big]}$$
Mẫu số lớn ở các thế khai cuộc chính là hiện tượng nhiễu ở thế khởi đầu.

---

## Phụ lục C: Cách nhìn theo gradient, đã thử và không phải hướng chính

Ghi lại cho đầy đủ, vì nó có trong phiên, dù bạn thấy nó không giúp được nhiều.

Khi mạng học một thế cờ $s'$ có nhãn $y(s')$ bằng một bước gradient, đầu ra tại một thế cờ khác $s^*$ thay đổi xấp xỉ
$$\Delta f(s^*) \approx -\eta \, K(s^*, s') \, \big(f(s') - y(s')\big)$$
Trong đó $\eta$ là tốc độ học. $K(s^*, s')$ được tính như sau: với mỗi trọng số, nhân độ nhạy của đầu ra tại $s^*$ với độ nhạy của đầu ra tại $s'$ đối với trọng số đó, rồi cộng lại trên mọi trọng số. $K$ dương thì học $s'$ kéo $s^*$ đi cùng chiều, $K$ âm thì ngược chiều, $K$ bằng 0 thì không ảnh hưởng.

Những kết luận rút ra từ cách nhìn này, và vẫn còn đúng trong khung chung:

- Hai thế cờ khác hẳn nhau trên bàn cờ vẫn có thể ảnh hưởng mạnh tới nhau qua trọng số chung. Đây là cách những thế cờ không liên quan sửa được thế cờ bị sai.
- Nếu nhãn tại chính một thế cờ gần như trùng với đánh giá của mạng (vì search sai cùng chiều với mạng), thì thế cờ đó không tự tạo ra lực sửa nào. Đây là cách viết bằng toán của câu "không có dấu hiệu tích cực nào từ chính thế cờ này".
- Nhiễu của nhãn triệt tiêu dần theo số lượng mẫu, nên cần cỡ $(\sigma/\mu)^2$ mẫu để tín hiệu thắng nhiễu. Đây là "số lượng để đè bẹp" theo nghĩa đen.

---

## Phụ lục D: Dòng thời gian của phiên

1. Bạn mở đầu: muốn bàn về cách sinh dữ liệu huấn luyện để engine kiểu lc0 học nhanh hơn, muốn cùng sáng tạo và không đi lối mòn, có trực giác từ một số trường hợp đã trải qua.
2. Mình liệt kê 7 hướng. Bạn sửa: không phải tránh danh sách quen thuộc, cũng không phải làm nhiều hướng độc lập. Chủ yếu là luôn tư duy cùng nhau.
3. Bạn nêu mục tiêu: ít ván hơn, sức mạnh tương đương, phá cách không liên quan đến hiệu năng. Mình liệt kê các giả định ngầm của vòng lặp lc0.
4. Bạn nói ý tưởng của mình phá cách hơn nhiều, liên quan đến làm nhãn chính xác hơn mà không dùng số lượng để đè, có nhiều thứ quan hệ biện chứng với nhau. Bạn kể trường hợp quan sát gốc.
5. Một loạt vòng làm rõ trường hợp gốc (phần 5.2) và loại dần các cách hiểu (phần 6).
6. Bạn nói chữ "biện chứng" nói về bản chất của quá trình tiến triển của mạng. Bạn không rõ triết học và muốn đi bằng logic.
7. Thử cách trình bày toán học bằng gradient và $K$. Bạn không hiểu $K$, mình giải thích lại bằng ví dụ, bạn thấy vẫn không giúp được, và giải thích không cần $K$ thì ổn hơn.
8. Thử đề xuất hai mạng (tốn compute), sửa nhãn bằng nhận thức muộn (xoáy vào ví dụ). Bạn yêu cầu giải thích lại từ đầu về bản chất.
9. Giải thích bản chất của vòng lặp: nhãn gồm ba phần. Bạn sửa: chúng có quan hệ biện chứng với nhau. Thống nhất ý kiến thức chuyển hóa qua lại (phần 7.1).
10. Bạn hỏi có cách nào làm nhãn chính xác hơn và sửa thế cờ sai ngay lúc đó. Thử đối xứng (bị loại). Thống nhất ý nhãn sai mà tự tin (phần 7.2).
11. Bạn nêu ý đầu ra phụ (tự gác lại) và ý thế khởi đầu. Thống nhất gốc chung của hai hiện tượng (phần 7.4), rồi hai trục nhiễu và lệch (phần 7.3). Bạn muốn tác động vào cả hai.
12. Thống nhất khung tín hiệu: gần hay xa, trong hay ngoài, vì sao trộn nhãn không đủ, yêu cầu tín hiệu thứ ba (phần 7.5, 7.6). Bạn thấy câu hỏi thiết kế rất hợp.
13. Làm rõ chữ "luật cờ" thành phán quyết ở thế kết thúc, và thêm nguồn "kiến thức ở nơi khác" (phần 7.7).
14. Bạn hỏi lấy kiến thức ở nơi khác bằng cách nào. Nhận ra search đã làm việc đó, và tách ra hai đòn bẩy: ai chọn thế cờ để hỏi, và thời điểm hỏi (phần 7.8). Bạn nghiêng về cả hai nhưng chưa có ý thiết kế.
15. Mình đề xuất đồ thị thế cờ sống dùng chung (phần 8). Bạn thấy rất chạm cảm giác mong muốn, và nó nối với hai ý bạn đã le lói từ trước. Bạn quyết định tự suy nghĩ dài theo hướng này và cân nhắc kỹ các trade-off.
