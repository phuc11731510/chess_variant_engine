# Luật cờ biến thể 10×10 (FairyZero)

Bản mô tả luật **đã được chủ dự án xác nhận** (2026-09-23), gồm cả các trường hợp biên. Định nghĩa
máy đọc nằm ở `src/app/variant_setup.cc` (INI của Fairy-Stockfish); bản viết lại độc lập để kiểm
chứng nằm ở `src/tests/test_rules_oracle.cc` (`custom_engine --audit-rules`). Đổi luật thì phải sửa
**cả ba chỗ**: file này, `variant_setup.cc` (hoặc code FSF nếu luật không diễn đạt được bằng INI) và
oracle.

## Luật mới (dự định, CHƯA CÀI)

Ghi ngày 2026-11-16 theo ý chủ dự án. **Chưa có mã nào được sửa**: toàn bộ các mục còn lại của tệp này
(bảng quân, thế cờ đầu, trường hợp biên, nhập thành, danh sách chỉnh sửa FSF) vẫn mô tả luật **đang cài**.
Khi cài luật mới phải sửa lại cả ba chỗ như ở đầu tệp (tệp này, `variant_setup.cc`/mã FSF, oracle).

### Quân cờ mới

Ký hiệu Betza dưới đây là bản dự kiến cho `variant_setup.cc`, cần kiểm lại khi cài. `m` = chỉ đi (không
ăn), `n` = bị cản ở ô giữa (với Mã `nN` là Mã cờ tướng: bị cản ở **ô liền kề theo hướng đi dài**, ví dụ
nước (2,1) bị cản bởi ô (1,0)).

| Ký hiệu | Tên | Cách đi | Betza |
|---|---|---|---|
| `k` | **Hoàng gia** (mất là thua) | **Đi hoặc ăn** 1 ô theo 8 hướng (viền 3×3). Trong viền 5×5 (16 ô ngoài) **chỉ đi, không ăn**, và chỉ khi không bị cản: đi 2 ô thẳng (cản bởi ô giữa), đi 2 ô chéo (cản bởi ô chéo giữa), nước kiểu Mã (cản chân như Mã cờ tướng) | `KmnDmnAmnN` |
| `p` | Tốt | không đổi | |
| `s` | Sergeant | không đổi | `fKifmnDifmnA` |
| `n` `r` `q` | Mã, Xe, Hậu | chuẩn | |
| `b` | **Tượng** | Tượng chuẩn + 1 ô thẳng (Wazir) **chỉ đi, không ăn** | `BmW` |
| `m` | **Centaur** | nước Vua + Mã **cờ tướng** (cản chân), đi và ăn | `KnN` |
| `v` | wildebeest | không đổi (Lạc đà (1,3) + Mã chuẩn) | `CN` |
| `y` | **Alibaba** | như hiện tại (nhảy (2,2) và (0,2)) + Wazir **chỉ đi, không ăn** | `ADmW` |
| `c` | **Pháo** (mới) | Pháo cờ tướng (đi như Xe, ăn bằng cách nhảy qua đúng 1 quân làm "ngòi") + Wazir | `mRcpRW` |
| `g` | **Grasshopper** (mới) | Grasshopper (8 hướng như Hậu: nhảy qua đúng 1 quân, đáp ngay ô sau nó, ô đó trống hoặc có quân địch để ăn) + nước Vua | `gQK` |

Bỏ: **Chancellor `e`, Archbishop `h`, Amazon `a`**. Chữ `c`, `g` là đề xuất của tôi. Quân chiến đấu
(không kể Tốt, Sergeant, Hoàng gia) còn **9**: Mã, Tượng, Xe, Hậu, Centaur, wildebeest, Alibaba, Pháo,
Grasshopper.

### Nhập thành

**Bỏ hẳn luật nhập thành.** FEN không còn trường quyền nhập thành (hoặc luôn là `-`); `BIbi` trong thế
đầu bỏ; không còn nước `CASTLING`, chỉ số policy nhập thành, plane quyền nhập thành, ghi ô Xe trong dữ
liệu huấn luyện.

### Phong cấp (hai tầng)

Áp cho Tốt và Sergeant. Trắng như dưới đây; Đen đối xứng (hàng 3 thay hàng 8, hàng 2 thay hàng 9).

- **Hàng 8 (Đen: 3):** phong cấp **tuỳ chọn**. Có thể đứng lại làm Tốt/Sergeant ở hàng 8, hoặc phong
  thành một trong 5 quân: **Mã, Alibaba, Grasshopper, Tượng, Pháo** (`n y g b c`).
- **Hàng 9 (Đen: 2):** phong cấp **bắt buộc**, thành một trong **9** quân chiến đấu
  (`n b r q m v y c g`). Vì vậy Tốt/Sergeant không bao giờ tới hàng 10 (Đen: 1).
- Mọi cách tới ô đó đều áp dụng: đi thẳng, ăn chéo, bước đôi, ăn ep.

### Hệ quả cho các luật khác (cần xem lại khi cài)

1. **Chiếu** chỉ do nước **ăn** được: Hoàng gia chỉ "tấn công" viền 3×3, không tấn công viền 5×5; Wazir
   chỉ-đi của Tượng/Alibaba không chiếu; Pháo chiếu qua đúng một ngòi; Grasshopper chiếu qua đúng một
   quân. Cách đếm chiếu giữ nguyên, ngưỡng thắng là 7.
2. **Hoàng gia không đứng ở ô bị tấn công** (trường hợp biên 10) nay tính theo ô **ăn**: hai Hoàng gia
   không thể đứng trong viền 3×3 của nhau, nhưng đứng cách 2 ô thì được.
3. **Trường hợp biên 6** (ăn ep + phong cấp bắt buộc 6 quân) đổi: ô ep ở hàng 8 → phong cấp tuỳ chọn 5
   quân; ô ep ở hàng 9 → bắt buộc 9 quân.
4. **Thế cờ đầu phải quyết định lại**: `vrhbqkberv/…` đang dùng `e`, `h` (bị bỏ). Chưa chọn quân thay.
5. **Mạng nơ-ron phải huấn luyện lại từ đầu**: tập quân đổi (bỏ `e h a`, thêm `c g`), không còn nhập
   thành, tập nước phong cấp đổi.

### Đếm chiếu: 7 lần

Thắng ngay khi đủ **7** lần chiếu (thay cho 8). Cách đếm không đổi (mỗi quân đang chiếu = 1 lần, chiếu
đôi = 2). Thế cờ đầu ghi `7+7` thay `8+8`; `checkCounting`/số chiếu còn lại trong FEN, oracle, dữ liệu
huấn luyện (plane đếm chiếu) phải đổi theo.

### Đã xác nhận (2026-11-16)

- Wazir của **Pháo đi và ăn được** (Betza `mRcpRW`).
- **Grasshopper nhảy 8 hướng** như Hậu (Grasshopper gốc).
- Ký hiệu Betza trong bảng trên đúng ý chủ dự án.
- Thế cờ đầu: chủ dự án sẽ nói sau (phải thay `e`, `h`).

### Bộ mã hoá mạng nơ-ron (đã làm, nhánh `luat-moi`, 2026-11-16)

Toàn bộ con số nằm ở `src/lczero_chess/chess/nn_layout.h` (nguồn chính) và `python/nn_layout.py` (`python/test_layout.py` kiểm hai bên khớp).

| | Cũ | Mới |
|---|---|---|
| Loại quân mỗi bên | 13 | **12**: Tốt, Mã, Tượng, Xe, Hậu, Hoàng gia, Centaur, wildebeest, Alibaba, Sergeant, Pháo, Grasshopper |
| Mặt phẳng mỗi bước lịch sử | 27 | **25** (12 + 12 + lặp thế) |
| Mặt phẳng phụ trợ | 10 | **5**: ep, rule50, toàn 1, số chiếu còn lại của hai bên (bỏ 4 mặt phẳng nhập thành và 1 mặt phẳng trống) |
| Đầu vào | 226 | **205** |
| Quân phong cấp có ô policy | 6 | **9**: Mã, Tượng, Xe, Hậu, Centaur, wildebeest, Alibaba, Pháo, Grasshopper |
| Chỉ số policy | 106 loại x 100 = 10600 | **115 loại x 100 = 11500** (88 loại nước đi như cũ + 9 quân x 3 hướng phong cấp) |
| Bản ghi huấn luyện | 45940 byte, version 6 | **49280 byte, version 7** (bỏ 4 byte nhập thành); container `.xz` bản 2 |

- Hình học nước đi không đổi: nước của Hoàng gia (viền 5×5), Pháo, Grasshopper, Alibaba, Centaur đều rơi vào các loại trượt / Mã / Lạc đà sẵn có. Nước Tốt đi lên hàng 8 **không phong cấp** dùng ô nước thường (trước đây không bao giờ xuất hiện), nên không đụng ô phong cấp.
- `EncoderCoversVariant` (encoder.cc) kiểm mọi quân và mọi quân phong cấp của luật có chỗ trong mạng; `setup_custom_variant()` gọi nó và thoát nếu thiếu. Vì vậy **engine không chạy với luật cũ trên nhánh này** cho tới khi `variant_setup.cc` đổi sang luật mới.
- Dữ liệu và mạng của các đời trước **không đọc được** (`KNOWN_VERSIONS = (7,)`). `python/chuyen_v6.py` (đổi dữ liệu cũ sang container) hết tác dụng.

Còn phải làm để chạy lại được: `variant_setup.cc` (luật mới, thế cờ đầu của chủ dự án), oracle luật và các test cũ dựa trên luật cũ (`test_board`, `test_ep`, `test_rules`, `test_app`, ...), `GUI`.

### FSF có làm được không

- **Đã thử (2026-11-16, FSF `014b0775` dựng riêng, `largeboards=yes`)**: mọi ký hiệu Betza trong bảng chạy đúng ý: Hoàng gia `KmnDmnAmnN` (viền 3×3 đi + ăn; 16 ô viền 5×5 chỉ đi, bị cản bởi ô giữa / ô chân đúng như đã mô tả), Centaur `KnN` (cản chân, ăn được), Alibaba `ADmW` và Tượng `BmW` (Wazir không ăn), Pháo `mRcpRW` (ăn qua đúng 1 ngòi, Wazir ăn được), Grasshopper `gQK`.
- **Quân**: dự kiến diễn đạt được bằng INI qua Betza (`customPiece` hoặc `king = k:…`): chỗ cần thử là
  Hoàng gia có nước đi không-ăn khác nước ăn, và `gQ` / `mRcpR` trong cùng một quân với `K`/`W`.
- **Phong cấp hai tầng: INI gốc của FSF không diễn đạt được, nên đã thêm vào bản FSF của dự án (2026-11-16, đã có test, chưa bật trong luật đang cài).** Xem mục 15 của phần chỉnh sửa FSF. Chỉ còn phần engine khi đổi luật thật: bộ mã hoá policy (`encoder.cc`: ô phong cấp cho Pháo, Grasshopper), `variant_setup.cc`, oracle.

## Quân cờ (luật đang cài)

| Ký hiệu | Tên | Cách đi (Betza) |
|---|---|---|
| `k` | **Hoàng gia** (quân vương, mất là thua) | `KN`: nước Vua + nước Mã. Chữ `k` chỉ vì FSF bắt quân vương phải ở ô "king". |
| `p` | Tốt | Tốt chuẩn |
| `s` | Sergeant | `fKifmnDifmnA` (xem dưới) |
| `n` `b` `r` `q` | Mã, Tượng, Xe, Hậu | chuẩn |
| `e` | chancellor | Xe + Mã |
| `h` | archbishop | Tượng + Mã |
| `m` | centaur | nước Vua + Mã (như Hoàng gia nhưng không phải quân vương) |
| `v` | **wildebeest** | `CN`: Lạc đà (1,3) + Mã |
| `y` | **alibaba** | `AD`: nhảy (2,2) + nhảy (0,2), đều nhảy qua quân |
| `a` | amazon | Hậu + Mã. Vẫn định nghĩa (giữ bố cục plane của mạng) nhưng không có trong thế cờ đầu, không được phong cấp thành |

Thế cờ đầu:
`vrhbqkberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHBQKBERV w BIbi - 8+8 0 1`

## Luật chính

- Bàn 10×10 (cột a–j, hàng 1–10). Trắng đi trước.
- **Tốt:** tiến 1 ô; từ hàng 1–3 (Đen: 8–10) được tiến 2 ô nếu cả hai ô trống; ăn chéo 1 ô.
- **Sergeant:** đi **và ăn** 1 ô theo 3 hướng tiến (thẳng, chéo trái, chéo phải). Từ hàng 1–3 (Đen:
  8–10) còn được **đi** (không ăn) 2 ô thẳng hoặc 2 ô chéo về phía trước, ô ở giữa phải trống.
- **Phong cấp:** Tốt hoặc Sergeant tới hàng 8–10 (Đen: 3–1) **bắt buộc** phong thành một trong
  `b m n r v y`.
- **Nhập thành:** Hoàng gia f1 + Xe i1 → Hoàng gia h1, Xe g1; Hoàng gia f1 + Xe b1 → Hoàng gia d1,
  Xe e1. Đen tương tự ở hàng 10. (Chỉ ở hàng 1/10 với Xe b/i và Hoàng gia f: không có thế khởi đầu xáo trộn.)
- **Đếm chiếu:** mỗi quân đang chiếu Hoàng gia đối phương sau một nước tính 1 lần chiếu. Đủ **8** thì
  thắng ngay.
- **Hết nước đi = thua** (dù bị chiếu hay không).
- **Luật 50 nước:** 100 ply không ăn quân, không đi Tốt/Sergeant, không phong cấp → hoà.
- **Lặp 3 lần → hoà.**

## Trường hợp biên (đã xác nhận)

1. **Bước đôi của Sergeant** được đi từ **bất kỳ** ô nào ở hàng 1–3 (Đen 8–10), kể cả khi Sergeant đã
   tiến một bước lên hàng 3. Bước đôi (thẳng hoặc chéo) chỉ để đi, không để ăn, ô giữa phải trống.
2. **Sergeant đi vào ô bắt tốt qua đường (ô ep) luôn là ăn quân** — không có lựa chọn đi thường vào ô
   đó. (Không làm mất nước hợp lệ nào: khi nước đi thường vào ô ep hợp lệ thì nước ăn ep cũng hợp lệ.)
3. **Tốt đi thẳng vào ô ep** (xảy ra sau bước đôi chéo của Sergeant) là nước đi thường, không ăn.
4. **Quân bị ăn ep có thể cách quân ăn hai cột.** Ví dụ Sergeant đen e9→c7 (chéo, qua d8); Tốt trắng
   e7 ăn chéo sang d8 và **quân ở c7** bị bắt.
5. Ăn ep chỉ được ở **nước ngay sau** bước đôi. Engine ghi ô ep sau mọi bước đôi, kể cả khi không ai ăn
   được — không đổi luật, chỉ đổi khoá Zobrist và plane ep của mạng.
6. **Ăn ep + phong cấp** chỉ xảy ra khi Sergeant đi đôi từ hàng 2/9 (ô bị vượt qua nằm trong vùng phong
   cấp của đối phương); bắt buộc chọn 1 trong 6 quân `b m n r v y`.
7. **Đếm chiếu theo số quân chiếu:** chiếu đơn = 1, **chiếu đôi = 2** (chiếu ba, nếu xảy ra, = 3). Tính
   cả chiếu phát hiện, chiếu bằng Xe sau nhập thành, chiếu bằng quân vừa phong cấp qua ep. Số lần chiếu
   còn lại không xuống dưới 0; về 0 là thắng ngay, trước mọi luật khác. (FSF gốc tính 1 cho mỗi nước
   chiếu; dự án sửa trong `Position::do_move`, 2026-09-23.)
8. **"Cùng một thế cờ" khi tính lặp 3 lần** gồm: vị trí quân, bên tới lượt, quyền nhập thành, ô ep **và
   số chiếu còn lại của hai bên**. Nếu có một nước chiếu xen giữa thì không còn là "lặp".
9. **Thứ tự kết thúc ván:** (a) đủ 8 lần chiếu → thắng; (b) 100 ply luật 50 nước → hoà, **trừ khi** bên
   tới lượt đang bị chiếu hết (vẫn thua); (c) lặp 3 lần → hoà; (d) hết nước đi → thua.
10. **Hoàng gia** không được đứng ở ô bị tấn công, kể cả ô cách Hoàng gia đối phương một nước Mã — nên
    hai Hoàng gia không bao giờ đứng cách nhau một nước Mã (hay một nước Vua).
11. **Nhập thành:** cần g1, h1 trống (cánh i) hoặc c1, d1, e1 trống (cánh b). Không nhập thành khi đang
    bị chiếu, không đi qua hay đứng vào ô bị tấn công. Mất quyền khi Hoàng gia đi, hoặc khi Xe đó rời
    ô gốc **hoặc bị ăn tại ô gốc**. Tổng quát: mọi ô mà Hoàng gia hoặc Xe đi qua hay đáp xuống (trên
    hàng của chúng) phải trống, trừ chính hai quân đó; ô đích của Hoàng gia xét **sau khi Xe đã rời ô**
    (Xe đang che đường chiếu tới ô đó thì không được nhập thành).
12. **Không có luật hoà do thiếu quân.** Kể cả Hoàng gia đối Hoàng gia vẫn thua được vì hết nước
    (Hoàng gia đen a10, Hoàng gia trắng c8, Đen tới lượt → Đen hết nước → Đen thua).

## Viết quyền nhập thành trong FEN

Trong FEN viết bằng **chữ cái cột của Xe** (Shredder-FEN): thế cờ bắt đầu là `BIbi` (Xe cột b và cột i; HOA = Trắng). FSF cũng hiểu `KQkq` bằng cách dò tìm: `K` = Xe đầu tiên gặp khi đi từ cột i về phía cột a, `Q` = Xe đầu tiên đi từ cột b về phía cột j; FSF in FEN ra ở dạng `KQkq`. Hai cách cho cùng một thế khi Xe đứng ở b/i. Khi Xe không ở b/i, `KQkq` có thể ra quyền khác, nhưng trong ván bắt đầu từ thế cờ chuẩn quyền nhập thành chỉ thuộc Xe b/i nên không xảy ra. `CheckStartFen` (`src/app/variant_setup.cc`) từ chối FEN khởi đầu mà một chữ nhập thành không ra đúng quyền nó ghi.

**Không hỗ trợ thế khởi đầu xáo trộn (kiểu Chess960)** từ 2026-11-16: nhập thành trên hàng bất kỳ, khoá Zobrist theo ô Xe và FEN in K/Q có kiểm đã được gỡ để trở về Fairy-Stockfish gốc (mã cũ nằm ở commit `9d8a37e`). Muốn xáo trộn phải khôi phục chúng.

## Chỉnh sửa riêng trong mã Fairy-Stockfish (`src/chess/`)

Mã bàn cờ ở `src/chess/` là Fairy-Stockfish (FSF) đã sửa cho luật trên. Phần dưới liệt kê **mọi chỗ khác
bản gốc và lý do**, để khi hợp nhất với FSF mới biết chỗ nào phải giữ. (Chỉ tính thư mục `src/chess/`;
luật diễn đạt được bằng INI nằm ở `src/app/variant_setup.cc`, không phải FSF.)

**Mốc hợp nhất gần nhất (2026-11-16):** gốc `1b5bdd40` (FSF 2026-05-23, "Add Georgian chess") →
`014b0775` (FSF 2026-11-15). Nhánh `hop-nhat-fairystockfish`, commit `9d8a37e`. Cách làm: hợp nhất ba
chiều từng tệp (`git merge-file`: gốc, mã của dự án, FSF mới) trong thư mục tạm, không xung đột; rồi
biên dịch và chạy `--test-*`, `--audit-rules`, `--audit-generation`, `fz_test`: đều qua.

**2026-11-16 (sau hợp nhất):** gỡ nhập thành trên hàng bất kỳ và khoá nhập thành theo ô Xe (mục 4 và 8), trở về FSF gốc ở các chỗ đó; bài kiểm `test_board` TEST 8 bị bỏ, các thế nhập thành ngoài hàng 1 bị bỏ khỏi `test_app`, `test_trainingdata`, `test_rules_oracle`.

### A. Luật của biến thể (đổi hành vi bàn cờ)

1. **Bắt tốt qua đường (ep) cho Sergeant** (`position.cpp`, `movegen.cpp`). `enPassantTypes = p s`:
   bước đôi thẳng hoặc chéo của Sergeant để lại ô ep; Sergeant đi vào ô ep luôn là ăn (movegen bỏ ô ep
   khỏi `quiets`, ô ep ăn được từ `attacks` thay vì `attacks & ~quiets`). Quân bị ăn có thể cách hai
   cột (trường hợp biên 2–4).
2. **Ăn ep kèm phong cấp** (`types.h`, `movegen.cpp`, `position.cpp`, `uci.cpp`). Khi ô ep nằm trong vùng
   phong cấp (Sergeant đi đôi từ hàng 2/9), nước ep mang thêm quân phong cấp: `ep_promotion_type(m)`
   dùng lại trường phong cấp của nước `EN_PASSANT`. `movegen` sinh một nước cho mỗi quân phong cấp,
   `do_move` / `undo_move` đổi quân và hoàn lại, `gives_check` tính chiếu trực tiếp theo quân mới,
   `UCI::move` thêm chữ quân phong cấp để các nước khác nhau có chuỗi khác nhau. (Tốt không gặp tình
   huống này vì Tốt bắt đầu hàng 3/8.)
3. **Đếm chiếu theo số quân chiếu** (`position.cpp`, `do_move`): chiếu đôi = 2. FSF gốc tính 1 cho mỗi
   nước chiếu; dự án tính ở cuối `do_move` khi đã biết `checkersBB`, số còn lại không âm, về 0 là thắng
   (trường hợp biên 7). `check_counting` bật bằng `checkCounting = true` trong INI.
4. ~~Nhập thành trên hàng bất kỳ~~ (`castlingAnyRank`): **đã gỡ 2026-11-16**, trở về FSF gốc (nhập thành chỉ trên `castlingRank`, hàng 1/10).
5. **Hết nước đi = thua, không hoà do thiếu quân**: cấu hình bằng INI (`stalemateValue = loss`), không
   sửa mã FSF. Ghi ở đây để biết luật này không nằm trong `src/chess/`.
6. **Định nghĩa biến thể** `[custom_10x10_variant]` trong `variants.ini` (bàn 10×10, thế cờ đầu, các quân
   `v`, `y`, `s`, vùng đi đôi, vùng phong cấp, `promotionPieceTypes = b m n r v y`...).
   Đây là bản dự phòng cho công cụ FSF; bản chính dùng bởi engine là `variant_setup.cc`.

### B. Khoá băm Zobrist (đúng luật lặp thế, bộ nhớ đệm mạng, tái lập)

7. **Khoá ep theo ô, không theo cột** (`Zobrist::enpassant[SQUARE_NB]`): bước đôi thẳng của Sergeant
   đánh dấu hai ô cùng một cột; khoá theo cột thì hai lần XOR triệt tiêu nhau, thế có quyền ep băm giống
   thế không có. Cập nhật ở `set_state`, `key_after`, `do_move`, `undo`.
8. ~~Khoá quyền nhập thành gắn với ô của Xe~~ (`Zobrist::castlingRook`): **đã gỡ 2026-11-16**, trở về `Zobrist::castling[cr]` của FSF.
9. **Bộ sinh khoá và hạt giống** (`Position::init(seed)`, `random_zobrist_seed`, `zobrist_seed`,
   `zobrist_cuckoo_max_kicks`): thay `PRNG` của FSF bằng xoshiro256** gieo bằng SplitMix64 (đầu ra
   không tuyến tính trên GF(2)); hạt giống 10 chữ số, ngẫu nhiên mỗi lần chạy, lặp lại bằng
   `--zobrist-seed`. Chèn vào bảng cuckoo có giới hạn 10000 lần đá, vượt thì thử hạt giống kế tiếp (FSF
   gốc để vòng lặp không giới hạn: 1 hạt giống trong 20.000 làm treo lúc khởi động).

### C. Chế độ `LCZERO_MCTS` (engine dùng bàn cờ này cho tìm kiếm MCTS kiểu lc0, không dùng đánh giá của FSF)

Mọi thứ dưới đây bọc trong `#ifdef LCZERO_MCTS` / `#ifndef LCZERO_MCTS` để bản FSF thường vẫn dựng được.

10. **Tắt NNUE và đánh giá cổ điển**: `evaluate.cpp` (`NNUE::init` đặt `useNNUE = false`, `verify` bỏ
    qua), `nnue/evaluate_nnue.cpp` (hàm rỗng), `nnue/features/half_ka_v2*.cpp` (bỏ cả tệp), bỏ
    `dirtyPiece`, `psq`, `pawnKey`, `materialKey`, `nonPawnMaterial` khỏi `StateInfo` / `Position`. Các
    hàm đọc chúng (`pawn_key`, `psq_score`, `non_pawn_material`) trả 0. `do_move` và `undo_move` bỏ
    mọi cập nhật liên quan (nhiều khối `#ifndef`).
11. **Tắt tính lặp thế trong `do_move`** (`st->repetition = 0`): lặp thế do `PositionHistory` của
    lc0 quản lý. **Hệ quả khi hợp nhất:** đường tắt của FSF "bỏ qua kiểm n-fold khi `st->repetition == 0`"
    (#1063, 2026-11) làm kiểm n-fold của `is_optional_game_end` không bao giờ chạy; nhánh `LCZERO_MCTS`
    dùng lại điều kiện cũ `if (n_fold_rule())`.
12. **`StateInfo` xếp lại cho bộ nhớ đệm**: các trường `Bitboard` (16 byte) trước, rồi `int` / `Square`,
    rồi nhỏ nhất; khối được chép mỗi nước phải nằm trong 128 byte (`static_assert(offsetof(StateInfo,
    key) <= 128)`). `Position` chia thành con trỏ (không chép) và vùng POD chép bằng một `memcpy`.
13. **`Position::copy_from(other, newSt)`**: sao chép bàn cờ bằng một `memcpy` (thay cho chép từng trường)
    ; `do_move` / `undo` chép `StateInfo` bằng `memcpy` thay vì gán từng trường.
    `Position::set_state` bỏ phần khởi tạo khoá tốt / vật chất.
14. **Phát hiện thả quân** trong `do_move`: điều kiện `st->materialKey != previous->materialKey` đổi
    thành `type_of(st->move) == DROP` (vì không còn `materialKey`).

15. **Phong cấp hai tầng** (`variant.h`, `parser.cpp`, `variant.cpp`, `position.h`, `movegen.cpp`, `position.cpp`; test trong `test_rules.cc`). Thêm hai tuỳ chọn INI: `optionalPromotionRegion{White,Black}` (tầng tuỳ chọn, tập con của `promotionRegion`) và `optionalPromotionPieceTypes` (quân được phong ở tầng đó; bỏ trống thì như `promotionPieceTypes`). Ở tầng tuỳ chọn Tốt/Sergeant được đứng lại hoặc phong; phần còn lại của vùng phong cấp theo `mandatoryPawnPromotion` và `promotionPieceTypes` như cũ. Luật dự định: `promotionRegionWhite = *8 *9`, `optionalPromotionRegionWhite = *8`, `optionalPromotionPieceTypes = n y g b c`, `promotionPieceTypes` = 9 quân. Mặc định (không khai báo) hành vi **y hệt trước**: mọi test cũ vẫn qua. Cách làm: `Position::compulsory_promotion_zone`, `optional_promotion_zone`, `promotion_piece_types(c, ô)`; trong `movegen.cpp` một hàm chung `make_promotions_to<>` dùng cho Tốt, quân kiểu Tốt (Sergeant), ăn ep kèm phong cấp; nước ep rơi vào tầng tuỳ chọn sinh thêm nước ep thường. Chi phí: một phép AND với bitboard rỗng mỗi lần sinh nước Tốt/ô phong cấp, không đổi gì ở đường nóng khác. Test: Tốt, Sergeant, ăn quân, ep (hàng 8 và 9), hai màu, do/undo, `pseudo_legal`.

### D. Khi hợp nhất với FSF mới

- Gốc ba chiều lần sau là `014b0775` (mã dự án hiện = FSF `014b0775` + các chỗ
  trên). `git merge-file ours base theirs` từng tệp; tệp trong git của dự án dùng LF, FSF có thể CRLF.
- Sau khi hợp nhất **bắt buộc** chạy: `custom_engine --test-board --test-ep --test-rules --test-perft
  --test-history --audit-rules --audit-generation --test-adapter --test-selfplay --test-mcts`
  và `fz_test`. Lần 2026-11-16 chính `--test-history` (kiểm n-fold ở mọi mốc luật 50 nước) bắt được
  lỗi mục 11; các bài kiểm không đổ lỗi chữ nên không xung đột cũng không có nghĩa đúng hành vi.
- Dễ gây hỏng nhất: tối ưu của FSF dựa vào trạng thái đã tắt ở mục C (`repetition`, `psq`, vật chất,
  khoá tốt) hoặc giả định cờ 8×8 / quân chuẩn (đường tắt `attackers_to`, `fastAttacks`, `SniperTypes`,
  `boardBB`, `blockers_for_king`).
