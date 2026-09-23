# Luật cờ biến thể 10×10 (FairyZero)

Bản mô tả luật **đã được chủ dự án xác nhận** (2026-09-23), gồm cả các trường hợp biên. Định nghĩa
máy đọc nằm ở `src/app/variant_setup.cc` (INI của Fairy-Stockfish); bản viết lại độc lập để kiểm
chứng nằm ở `src/tests/test_rules_oracle.cc` (`custom_engine --audit-rules`). Đổi luật thì phải sửa
**cả ba chỗ**: file này, `variant_setup.cc` (hoặc code FSF nếu luật không diễn đạt được bằng INI) và
oracle.

## Quân cờ

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
  Xe e1. Đen tương tự ở hàng 10.
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
    ô gốc **hoặc bị ăn tại ô gốc**.
12. **Không có luật hoà do thiếu quân.** Kể cả Hoàng gia đối Hoàng gia vẫn thua được vì hết nước
    (Hoàng gia đen a10, Hoàng gia trắng c8, Đen tới lượt → Đen hết nước → Đen thua).
