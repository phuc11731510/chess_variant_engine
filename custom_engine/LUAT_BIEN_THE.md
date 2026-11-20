# Luật cờ biến thể 10×10 (FairyZero)

Bản mô tả luật **đã cài vào engine ngày 2026-11-16** (luật mới của chủ dự án). Định nghĩa máy đọc nằm ở
`src/app/variant_setup.cc` (INI của Fairy-Stockfish cộng một số chỗ trong mã FSF, xem cuối tệp); bản viết lại độc lập
để kiểm chứng nằm ở `src/tests/test_rules_oracle.cc` (`custom_engine --audit-rules`). Đổi luật thì phải sửa **cả ba chỗ**:
tệp này, `variant_setup.cc` (hoặc code FSF nếu luật không diễn đạt được bằng INI) và oracle.

**Thế cờ đầu chưa chốt**: `ChessBoard::kStartposFen` (`src/lczero_chess/chess/board.cc`) là thế **tạm**, là thế cũ với Archbishop
(cột c) và Chancellor (cột h) thay bằng Pháo `c` và Grasshopper `g`. Chủ dự án sẽ chọn thế thật sau; chỉ cần sửa một dòng đó.

## Quân cờ

Ký hiệu Betza: `m` = chỉ đi (không ăn), `n` = bị cản ở ô giữa (với `N`: Mã cờ tướng, bị cản ở ô liền kề theo hướng đi dài, ví dụ
nước (2,1) bị cản bởi ô (1,0)), `c` = chỉ ăn, `p` = ăn bằng cách nhảy qua đúng một quân, `g` = nhảy qua đúng một quân và đáp ngay sau nó.
Thứ tự `customPieceN` là thứ tự mặt phẳng đầu vào của mạng (xem "Bộ mã hoá"), **không được đánh số lại**.

| Ký hiệu | Tên | Cách đi | Betza |
|---|---|---|---|
| `k` | **Hoàng gia** (mất là thua) | **Đi hoặc ăn** 1 ô theo 8 hướng (viền 3×3). Trong viền 5×5 (16 ô ngoài) **chỉ đi, không ăn**, và chỉ khi không bị cản: 2 ô thẳng (cản bởi ô giữa), 2 ô chéo (cản bởi ô chéo giữa), nước kiểu Mã (cản chân như Mã cờ tướng). Chữ `k` vì FSF bắt quân vương ở ô "king" | `KmnDmnAmnN` |
| `p` | Tốt | tiến 1 ô; từ hàng 1–3 (Đen 8–10) được tiến 2 ô nếu cả hai ô trống; ăn chéo 1 ô | chuẩn |
| `s` | Sergeant | đi **và ăn** 1 ô theo 3 hướng tiến; từ hàng 1–3 (Đen 8–10) còn **đi** (không ăn) 2 ô thẳng hoặc 2 ô chéo về phía trước, ô giữa phải trống | `fKifmnDifmnA` |
| `n` | Mã | chuẩn | |
| `r` `q` | Xe, Hậu | chuẩn | |
| `b` | **Tượng** | Tượng chuẩn + 1 ô thẳng (Wazir) **chỉ đi, không ăn** | `BmW` |
| `m` | **Centaur** | nước Vua + Mã **cờ tướng** (cản chân), đi và ăn | `KnN` |
| `v` | wildebeest | Lạc đà (1,3) + Mã chuẩn, nhảy qua quân | `CN` |
| `y` | **Alibaba** | nhảy (2,2) và (0,2)/(2,0) qua quân + Wazir **chỉ đi, không ăn** | `ADmW` |
| `c` | **Pháo** | Pháo cờ tướng (đi như Xe không ăn; ăn bằng cách nhảy qua đúng 1 quân "ngòi", của bên nào cũng được, rồi ăn quân địch đầu tiên sau nó) + Wazir **đi và ăn** | `mRcpRW` |
| `g` | **Grasshopper** | theo 8 hướng như Hậu: dọc tia tới quân đầu tiên, nhảy qua nó, đáp ngay ô sau (trống: đi; quân địch: ăn) + nước Vua | `gQK` |

Đã bỏ Chancellor `e`, Archbishop `h`, Amazon `a`. Quân chiến đấu (không kể Tốt, Sergeant, Hoàng gia) còn 9:
Mã, Tượng, Xe, Hậu, Centaur, wildebeest, Alibaba, Pháo, Grasshopper.

## Luật chính

- Bàn 10×10 (cột a–j, hàng 1–10). Trắng đi trước. **Không có nhập thành.**
- **Phong cấp hai tầng** (Tốt và Sergeant; Đen đối xứng: hàng 3 thay hàng 8, hàng 2 thay hàng 9):
  - **Hàng 8:** tuỳ chọn: đứng lại làm Tốt/Sergeant, hoặc phong thành **Mã, Tượng, Alibaba, Pháo, Grasshopper** (`n b y c g`).
  - **Hàng 9:** bắt buộc, thành một trong 9 quân (`n b r q m v y c g`). Không bao giờ tới hàng 10.
  - Mọi cách tới ô đó đều áp dụng: đi thẳng, ăn chéo, bước đôi, ăn ep.
- **Đếm chiếu:** mỗi quân đang chiếu Hoàng gia đối phương sau một nước tính 1 lần chiếu, nên **chiếu đôi = 2, chiếu ba = 3** (có
  thể xảy ra, ví dụ Centaur nhảy kề Hoàng gia + Xe lộ ra + Pháo có Centaur làm ngòi). Đủ **7** thì thắng ngay.
  Chỉ nước **ăn** được mới chiếu: Hoàng gia chỉ chiếu viền 3×3; Wazir chỉ-đi của Tượng/Alibaba không chiếu; Pháo chiếu qua đúng một
  ngòi; Grasshopper chiếu bằng nước nhảy của nó. Ngòi xuất hiện hay biến mất (quân khác nhảy vào / rời đi) đều có thể tạo hay mất chiếu.
- **Hết nước đi = thua** (dù bị chiếu hay không).
- **Luật 50 nước:** 100 ply không ăn quân, không đi Tốt/Sergeant, không phong cấp → hoà (trừ khi bên tới lượt bị chiếu hết).
- **Lặp 3 lần → hoà.** "Cùng thế" gồm: vị trí quân, bên tới lượt, ô ep, và số chiếu còn lại của hai bên.
- **Thứ tự kết thúc ván:** (a) đủ 7 lần chiếu → thắng; (b) 100 ply → hoà, **trừ khi** bên tới lượt bị chiếu hết (vẫn thua); (c) lặp 3 lần → hoà;
  (d) hết nước đi → thua.
- **Không có luật hoà do thiếu quân.**

## Trường hợp biên

1. **Bước đôi của Sergeant** được đi từ **bất kỳ** ô nào ở hàng 1–3 (Đen 8–10). Bước đôi (thẳng hoặc chéo) chỉ để đi, không ăn, ô giữa phải trống.
2. **Sergeant đi vào ô bắt tốt qua đường (ô ep) luôn là ăn quân**, không có lựa chọn đi thường vào ô đó. **Tốt đi thẳng vào ô ep** (sau bước đôi
   chéo của Sergeant) là nước đi thường, không ăn.
3. **Quân bị ăn ep có thể cách quân ăn hai cột.** Ví dụ Sergeant đen e9→c7 (chéo, qua d8); Tốt trắng e7 ăn chéo sang d8 và **quân ở c7** bị bắt.
4. Ăn ep chỉ được ở **nước ngay sau** bước đôi. Engine ghi ô ep sau mọi bước đôi, kể cả khi không ai ăn được.
5. **Ăn ep rơi vào hàng phong cấp:** ở hàng 8 (Đen 3) là một lựa chọn như mọi nước tới đó (đứng lại, hoặc `n b y c g`); ở hàng 9 (Đen 2) bắt buộc phong cấp
   thành 1 trong 9 quân. Với Sergeant bước đôi từ hàng 2/9 (qua hàng 8/3) và hàng 1/10 (qua hàng 9/2).
6. **Hoàng gia không được đứng ở ô bị tấn công** (ô bị **ăn** được; ô viền 5×5 của Hoàng gia khác không tính). Hai Hoàng gia không thể đứng trong viền 3×3
   của nhau, nhưng đứng cách 2 ô thì được.
7. **Không có luật hoà do thiếu quân.** Hoàng gia đối Hoàng gia vẫn thua được vì hết nước.
8. **Hết nước đi (chiếu hết hoặc hết nước) = thua.** 100 ply: chiếu hết trên chính ply đó vẫn là thắng; hết nước (không bị chiếu) trên ply đó là **hoà** theo luật 50 nước.

## Ký hiệu nước đi (ASCII)

Một nước viết `<ô đi><ô đến>[chữ quân]`:
- ô = chữ cột `a`–`j` và hàng `1`–`10` (hàng 10 viết hai chữ số, ví dụ `a1a10`);
- chữ quân chỉ có khi **phong cấp** (kể cả ăn ep phong cấp), là một trong `n b r q m v y c g` (chữ thường, cùng chữ với quân trên bàn);
- Tốt/Sergeant lên hàng 8 (Đen 3) mà **không phong cấp** thì **không có chữ**: `e7e8`; phong cấp thì có: `e7e8c`. Lên hàng 9 (Đen 2) luôn có chữ: `e8e9c`;
- các chữ `b`, `c`, `g` cũng là tên cột nhưng chữ quân luôn đứng **sau số hàng của ô đến**, nên `e8e9c` đọc được duy nhất (ô e8, ô e9, quân c);
- mọi nước dùng đúng tọa độ **thật** của bàn (không lật cho Đen); engine lật nội bộ.

`--audit-rules` kiểm cho **mọi nước hợp lệ ở mọi thế** (hơn 400 nghìn nước mỗi lần): chuỗi đúng dạng trên, chữ quân có đúng khi và chỉ khi phong cấp, hai nước
trong cùng một thế không trùng chuỗi, `UCI::to_move` và `ChessBoard::ParseMove` đọc ngược ra đúng nước đó, `MoveToString` trùng `UCI::move`.

## Bộ mã hoá mạng nơ-ron (nhánh `luat-moi`, 2026-11-16)

Toàn bộ con số nằm ở `src/lczero_chess/chess/nn_layout.h` (nguồn chính) và `python/nn_layout.py` (`python/test_layout.py` kiểm hai bên khớp).

| | Cũ | Mới |
|---|---|---|
| Loại quân mỗi bên | 13 | **12**: Tốt, Mã, Tượng, Xe, Hậu, Hoàng gia, Centaur, wildebeest, Alibaba, Sergeant, Pháo, Grasshopper |
| Mặt phẳng mỗi bước lịch sử | 27 | **25** (12 + 12 + lặp thế) |
| Mặt phẳng phụ trợ | 10 | **4**: ep, rule50, số chiếu còn lại của hai bên (bỏ 4 mặt phẳng nhập thành, 1 mặt phẳng trống và mặt phẳng toàn số 1) |
| Đầu vào | 226 | **204** (bỏ mặt phẳng toàn số 1 ngày 2026-11-20; bản ghi không đổi vì nó không lưu mặt phẳng này) |
| Quân phong cấp có ô policy | 6 | **9**: Mã, Tượng, Xe, Hậu, Centaur, wildebeest, Alibaba, Pháo, Grasshopper |
| Chỉ số policy | 106 loại x 100 = 10600 | **115 loại x 100 = 11500** (88 loại nước đi như cũ + 9 quân x 3 hướng phong cấp) |
| Bản ghi huấn luyện | 45940 byte, version 6 | **49283 byte, version 7** (bỏ 4 byte nhập thành; thêm `plies_left` uint16 và `fast_search` uint8 ngày 2026-11-20); container `.xz` bản 3 |

- Hình học nước đi không đổi: nước của Hoàng gia (viền 5×5), Pháo, Grasshopper, Alibaba, Centaur đều rơi vào các loại trượt / Mã / Lạc đà sẵn có. Nước Tốt đi lên hàng 8 **không phong cấp** dùng ô nước thường (trước đây không bao giờ xuất hiện), nên không đụng ô phong cấp.
- `EncoderCoversVariant` (encoder.cc) kiểm mọi quân và mọi quân phong cấp của luật có chỗ trong mạng; `setup_custom_variant()` gọi nó và thoát nếu thiếu. Một quân hay quân phong cấp chưa có chỗ trong mạng thì engine thoát ngay lúc khởi động thay vì để quân biến mất khỏi đầu vào.
- **Lịch sử ở đầu ván (2026-11-20):** mạng và bản ghi mã hoá bằng `FillEmptyHistory::ALWAYS` (kiểu lc0): mỗi bàn lịch sử chưa có (7 bàn trước nước đầu tiên, 6 bàn trước nước thứ hai...) là bản sao của **thế đầu ván**, với mọi ván và mọi thế xuất phát; trước đó là `FEN_ONLY` nên ván bắt đầu từ thế xuất phát của biến thể có các bàn rỗng.
- **Thế khởi đầu ngẫu nhiên:** `python/sinh_the_khoi_dau.py` (xem Walkthrough) sinh tệp FEN cho `--start-fen`; `ChessBoard::kStartposFen` vẫn là thế tạm.
- Dữ liệu và mạng của các đời trước **không đọc được** (`KNOWN_VERSIONS = (7,)`). `python/chuyen_v6.py` (đổi dữ liệu cũ sang container) hết tác dụng.


## Trạng thái cài đặt (2026-11-16, nhánh `luat-moi`)

Đã làm và có test (`custom_engine --test-*`, `--audit-rules`, `--audit-generation`, `fz_test` đều qua): luật và mọi quân ở trên, phong cấp hai tầng,
đếm chiếu (7, chiếu ba), không nhập thành, ký hiệu nước đi, bộ mã hoá (204 plane, 11500 policy), bản ghi huấn luyện version 7.
Chưa làm: thế cờ đầu thật (chủ dự án chọn), GUI, mạng mới (cần huấn luyện từ đầu; `--test-selfplay` / `--test-mcts` cần một tệp
`.onnx` đúng cỡ vào/ra mới), và các tài liệu khác (`HUONG_DAN*.md`) còn nói tới luật cũ.

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
