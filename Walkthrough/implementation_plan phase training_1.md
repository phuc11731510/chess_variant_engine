# Implementation Plan — Phase Training (Sinh dữ liệu + Huấn luyện)

> Dự án: FairyZero (custom_engine) — biến thể 10×10, NN 226 planes / policy 10600 / value WDL.
> Mục tiêu: dựng vòng lặp AlphaZero hoàn chỉnh, kế thừa tối đa Lc0 nhưng hợp với dự án & tối ưu hiệu năng (CPU bây giờ, GPU/Colab sau).
> Ngày: 2026-06-19.

---

## 0. Vòng lặp AlphaZero (toàn cảnh)

```
   ┌─────────────────────────────────────────────────────────┐
   │ (1) SELF-PLAY  (C++, custom_engine, ONNX inference)      │
   │     model_N.onnx  →  chơi hàng nghìn ván tự đấu          │
   │     mỗi thế cờ ghi: (input planes, π = visits, z, q...)  │
   │            ↓ ghi ra file .gz                             │
   │ (2) TRAINING   (Python/PyTorch, Google Colab GPU)        │
   │     đọc data  →  Sparse Shuffle Buffer & Down-sample     │
   │     huấn luyện ResNet 10x128 (Loss = policy CE + qMix)    │
   │            ↓ export (áp dụng SWA)                         │
   │     model_{N+1}.onnx (khớp hợp đồng I/O + 10x128)         │
   │            ↑___________ lặp lại _______________________  │
   └─────────────────────────────────────────────────────────┘
```

**Điểm mấu chốt:** 
*   **Phần sinh dữ liệu (1):** Đã có nền tảng hạ tầng cốt lõi trong dự án (Search MCTS, ChessBoard, [EncodePositionForNN](file:///d:/chess_variant/custom_engine/src/lczero_chess/chess/encoder.cc), [MoveToNNIndex](file:///d:/chess_variant/custom_engine/src/lczero_chess/chess/encoder.cc), [OnnxBackend](file:///d:/chess_variant/custom_engine/src/lczero_chess/neural/onnx_backend.cc)). Ta cần lập trình thêm module ghi dữ liệu self-play nén gzip và tích hợp các trường thông tin phụ trợ.
*   **Phần huấn luyện (2):** Viết MỚI hoàn toàn bằng Python/PyTorch (repo `lc0-master` gốc không chứa code huấn luyện mà nằm ở repo `lczero-training`). Chương trình huấn luyện sẽ được thiết kế để chạy tối ưu trên GPU của Google Colab.

Để vòng lặp hoạt động hiệu quả, hội tụ nhanh và đạt được Elo cao, Module A (Self-play C++) và Module B (PyTorch Training) được thiết kế đồng bộ để tích hợp trực tiếp các kỹ thuật tinh hoa từ `lczero-training` (chi tiết ở Mục 8), bao gồm trộn mục tiêu giá trị (qMix - Mục 8.2.1), Streaming Shuffle Buffer (Mục 8.2.2), trích chọn thế cờ đột biến (diff_focus - Mục 8.2.6), Stochastic Weight Averaging (SWA - Mục 8.2.4), và Down-sampling vị trí (Mục 8.2.3).

---

## 1. Kế thừa gì từ Lc0 (và điều chỉnh gì)

| Thành phần Lc0 | Vị trí | Kế thừa? | Điều chỉnh cho dự án | Mối liên kết với tinh hoa Mục 8 |
|----------------|--------|----------|----------------------|---------------------------------|
| `V6TrainingData` (record) | `trainingdata/trainingdata_v6.h` | ✅ Kế thừa CẤU TRÚC | Đổi `probabilities[1858]→[10600]`, `planes[104]→` định dạng 226-plane 10×10. Bổ sung các trường `orig_q/d` và `policy_kld`. Bỏ trường `plies_left` (MLH) do mạng không dùng MLH head. | Cung cấp đầu vào cho các kỹ thuật **qMix (8.2.1)** và **diff_focus (8.2.6)**. |
| `TrainingDataWriter` (ghi gz) | `trainingdata/writer.h/.cc` | ✅ Kế thừa gần nguyên | Đổi struct ghi vào; giữ gzip + 1 file/ván để tối ưu I/O ghi đĩa. | Chuẩn bị dữ liệu nén thô cho **Streaming Shuffle Buffer (8.2.2)**. |
| `V6TrainingDataArray::Add/Write` | `trainingdata/trainingdata.cc` | ✅ Kế thừa LOGIC | $\pi$ tính từ visit-count; $z$ gán ở cuối ván; ghi nhận thêm `orig_q/d` và tính `policy_kld` sau khi search. | Lưu trữ trực tiếp $z$ (`result_q`) và $q$ (`best_q`) để phục vụ trộn target. |
| `SelfPlayGame::Play` (vòng ván) | `selfplay/game.h/.cc` | ✅ Kế thừa LOGIC | Bỏ phần PGN/UCI thừa; dùng Search hiện có; phân bổ Heap cho `Search` để tránh tràn stack Windows khi history đạt 512. | Tạo nguồn sinh dữ liệu chất lượng cao có nhiễu Dirichlet và Temperature. |
| `SelfPlayTournament` (đa ván song song) | `selfplay/tournament.cc` | ⚠️ Tham khảo | Đơn giản hóa: 1 pool thread chạy N ván song song, chia sẻ chung `OnnxBackend` và `ZeroHeapCache`. | Tận dụng cơ chế **Batch Splitting (5)** và **Safety Clamp (5)** để bảo vệ GPU. |
| Temperature/Dirichlet noise | đã có trong `search/classic` | ✅ Đã có sẵn | Dùng `kTemperature`, `kNoiseEpsilon/Alpha` để tạo tính ngẫu nhiên khám phá. | Bảo đảm độ đa dạng của phân bố nước đi $\pi$. |
| Reader dữ liệu | `trainingdata/reader.h/.cc` | ✅ Tham khảo | Viết lại bản Python tương ứng phục vụ DataLoader, tích hợp Shuffle Buffer và Down-sampling. | Hiện thực hóa **Streaming Shuffle Buffer (8.2.2)** và **Down-sampling (8.2.3)**. |
| **Code train NN** | KHÔNG có trong lc0-master | ❌ | Viết MỚI hoàn toàn bằng PyTorch, áp dụng các loss function và kỹ thuật tối ưu hóa tại Mục 8. | Sử dụng **SWA (8.2.4)**, **Loss tổng hợp (8.2.5)** và **Rolling Window (8.2.8)**. |
| Rescorer (TB rescore) | `trainingdata/rescorer.cc` | ❌ (giai đoạn sau) | Bỏ qua — chưa dùng Syzygy Tablebase cho biến thể này. | Không áp dụng. |

**Nguyên tắc vàng:** phần ghi dữ liệu (C++) và phần đọc/train (Python) PHẢI khớp 3 quy ước:
1. **Layout policy 10600** = đúng [MoveToNNIndex](file:///d:/chess_variant/custom_engine/src/lczero_chess/chess/encoder.cc) (type×100 + rank×10 + file).
2. **Thứ tự value = [Win, Draw, Loss]** theo side-to-move (không dùng định dạng Q-value đơn lẻ để tránh mất thông tin tỷ lệ hòa).
3. **Layout input = [plane][rank][file]** (226×10×10), khớp hoàn toàn với logic [UnpackInputPlanes](file:///d:/chess_variant/custom_engine/src/lczero_chess/chess/encoder.cc).

---

## 2. MODULE A — Sinh dữ liệu self-play (C++, trong custom_engine)

### A1. Định dạng record `TrainingDataV1` (adapt từ V6 — `#pragma pack(1)`)
Để tối ưu hóa dung lượng lưu trữ trên đĩa và tốc độ truyền tải lên Google Drive, chúng tôi đề xuất cấu trúc struct đóng gói chặt chẽ, tích hợp sẵn các trường dữ liệu nâng cao nhằm hỗ trợ qMix và bộ lọc diff_focus:
```cpp
#pragma pack(push, 1)
struct TrainingDataV1 {
    uint32_t version;                 // = 1
    uint32_t input_format;            // mã hóa biến thể 10x10
    float    probabilities[10600];    // π = phân bố visit sau search (chỉ nước hợp lệ != 0)
    
    // Input planes: lưu THƯA dạng bitboard mask để tiết kiệm dung lượng (giống lc0)
    uint64_t piece_planes[216][2];    // 216 planes lịch sử (27 loại planes x 8 ply), mỗi plane = mask 128-bit (2 x u64)
    
    // Các plane phụ trợ dạng scalar được lưu riêng để tái tạo tại Python Reader:
    uint8_t  rule50_count;
    uint8_t  castling_us_ooo_file, castling_us_oo_file, castling_them_ooo_file, castling_them_oo_file; // Cột của xe nhập thành (0-9), nếu mất quyền lưu 0xFF
    uint64_t ep_mask[2];              // plane nước đi en passant (128-bit)
    uint8_t  checks_remaining_us, checks_remaining_them;
    uint8_t  side_to_move;            // 0 = White-to-move-frame, 1 = Black (đã xoay canonical)
    
    // Value/eval targets phục vụ huấn luyện:
    float    result_q, result_d;      // z (kết quả ván thực tế: Win/Draw/Loss, theo side-to-move) — gán ở cuối ván đấu
    float    root_q, root_d;          // eval gốc của search (đánh giá trị tìm kiếm ban đầu)
    float    best_q, best_d;          // q (eval của nước đi tốt nhất sau khi kết thúc search, theo side-to-move)
    float    played_q, played_d;      // eval của nước đi thực tế được chọn để chơi
    
    // Bổ sung các trường kế thừa từ tinh hoa lczero-training (Mục 8.1 & 8.2.6):
    float    orig_q, orig_d;          // eval tĩnh của mạng nơ-ron thu được từ lần suy luận đầu tiên của root node (sau khi expand)
    float    policy_kld;              // KL divergence giữa policy visits (π) và prior NN gốc p_NN (trước khi áp Dirichlet noise)
    uint32_t visits;                  // tổng số visits tại root node của lượt đi
    uint16_t played_idx;              // index nước đi thực tế chọn trong probabilities[]
    uint16_t best_idx;                // index nước đi tốt nhất tìm thấy trong probabilities[]
};
#pragma pack(pop)
```
*   **Lý do lưu plane THƯA (bitboard) thay vì 226×100 float:** 226×100×4B = 90KB/thế cờ $\rightarrow$ quá lớn (1 triệu thế cờ sẽ ngốn 90GB). Sử dụng bitboard mask: 216×16B + scalar ≈ 3.5KB/thế cờ (tiết kiệm hơn **25 lần**). Python Reader sẽ tự động unpack mảng bitboard này thành định dạng tensor float giống hệt hàm [UnpackInputPlanes](file:///d:/chess_variant/custom_engine/src/lczero_chess/chess/encoder.cc) trong C++.
*   Board-edge plane (toàn 1) và các plane rule50/checks KHÔNG cần lưu mask — Python Reader tái tạo dễ dàng từ các trường scalar.
*   **Hỗ trợ đa dạng thế cờ khởi đầu (Chess960-10x10 / Random FEN):** Thay vì lưu boolean castling đơn giản, struct lưu trực tiếp **chỉ số cột (file index, từ 0 đến 9)** của quân xe nhập thành tương ứng (`castling_us_ooo_file`, v.v.). Nếu quyền nhập thành bị mất hoặc không tồn tại, giá trị này được gán bằng `0xFF` (255). Điều này cho phép Python Reader khôi phục và bật bit chính xác tại ô xe nhập thành thực tế trên các plane castling đối với **bất kỳ thiết lập thế cờ ngẫu nhiên nào** mà không làm phình to kích thước struct.
*   Giữ `pack(1)` kết hợp `static_assert(sizeof(TrainingDataV1) == 45940, "Layout size mismatch")` để đảm bảo tính đồng bộ hoàn hảo của cấu trúc dữ liệu nhị phân khi đọc bằng Python. (Tổng kích thước byte: 8 + 42400 + 3456 + 24 + 48 + 4 = 45940).

### A2. Writer (kế thừa `TrainingDataWriter`)
*   Mỗi ván đấu tự chơi sẽ ghi ra một file nén `.gz` độc lập (tên file chứa mã định danh ván đấu `game_id` và nhãn thời gian `timestamp`).
*   Hàm `WriteChunk(record)` ghi nhị phân record xuống buffer; `Finalize()` đóng và đồng bộ hóa tệp tin nén.
*   Tận dụng thư viện `zlib` sẵn có trong project để nén gzip với tỷ lệ nén cao, giảm thiểu overhead ghi đĩa (I/O).

### A3. Trích policy target $\pi$ và tính `policy_kld` từ cache (Không đụng Search)
*   Sau khi MCTS hoàn thành tìm kiếm thông qua `search.RunBlocking()`, tiến hành duyệt danh sách các cạnh của root node (`root_node_->Edges()`):
    *   Tính toán xác suất cho từng nước đi hợp lệ: $\pi_i = N_i / N_{\text{total}}$ (với $N_i$ là số lượt ghé thăm của cạnh và $N_{\text{total}}$ là tổng số visits của root).
    *   Gán giá trị vào probabilities: $\pi[\text{MoveToNNIndex(edge.GetMove(), 0)}] = \pi_i$.
*   **Truy vấn cache lấy gợi ý NN thô (chưa nhiễu Dirichlet)**:
    Do nhiễu Dirichlet được áp trực tiếp vào root node của cây MCTS bên trong `Search::FetchSingleNodeResult` (không lộ ra self-play loop), cách sạch và an toàn nhất để lấy phân bố prior gốc $p_{NN}$ thô là gọi **`GetCachedEvaluation(root)`** từ bộ đệm `ZeroHeapCache` sau khi kết thúc search. Lời gọi này trả về đối tượng `EvalResult` chứa mảng prior thô thuần túy từ mạng nơ-ron (không chứa nhiễu).
*   **⚠️ CẢNH BÁO CACHE MISS (Va chạm Hash ~1%)**:
    Do `ZeroHeapCache` là một bộ đệm direct-mapped lockless tĩnh (hash % cache_size), trong các lượt đi có số visits lớn (200-800), bucket lưu trữ của root node có thể bị một thế cờ ở nút lá ghi đè lên trước khi search kết thúc, khiến `GetCachedEvaluation` trả về `std::nullopt` (Cache Miss).
    
    *Giải pháp xử lý Fallback an toàn (Tránh crash null-dereferencing)*:
    Bắt buộc phải viết kiểm tra `if (!raw_eval)` để xử lý nhánh này: nếu miss cache, tiến hành gán fallback **`orig_q = best_q`** (hoặc `root_q`) và **`policy_kld = 0.0f`**. Việc miss cục bộ ~1% này hoàn toàn vô hại vì `orig_q` và `policy_kld` chỉ phục vụ bộ lọc huấn luyện nâng cao `diff_focus`, trong khi mục tiêu policy chính ($\pi$) và value thực tế ($z$) vẫn được ghi nhận chính xác 100% từ kết quả search và ván đấu.
*   **⚠️ CẢNH BÁO BẮT BUỘC: Ghép cặp (mapping) qua MoveToNNIndex khi tính KLD**:
    Sau khi kết thúc tìm kiếm, các cạnh của root node (`root_node_->Edges()`) đã bị hàm `SortEdges` sắp xếp lại (thứ tự visits/prior bị xáo trộn). Trong khi đó, mảng `p` nhận được từ cache được lưu theo thứ tự sinh nước đi hợp lệ gốc của `GenerateLegalMoves`.
    
    *Giải pháp an toàn tránh lỗi lệch index âm thầm*: 
    Không ghép trực tiếp theo vị trí mảng. Thay vào đó, ta ánh xạ cả $\pi$ và $p_{NN}$ vào không gian phẳng **10,600** qua `MoveToNNIndex` rồi mới tiến hành tính KL Divergence trên các chỉ số nước đi hợp lệ:
    $$policy\_kld = \sum_{j \in \text{legal\_nn\_indices}} \pi[j] \log \left( \frac{\pi[j]}{p_{NN}[j]} + \epsilon \right)$$
    Giá trị `policy_kld` phản ánh độ phân kỳ giữa MCTS visits thực tế và gợi ý ban đầu của mạng. Vị trí có `policy_kld` lớn là những thế cờ "đột biến" có giá trị học tập cao, phục vụ bộ lọc `diff_focus` ở phần huấn luyện.

### A4. Trích value target z + q
*   `orig_q/d` = evaluation tĩnh của mạng nơ-ron đối với root node. Vì không thể thực hiện eval NN khi root chưa được expand, giá trị này sẽ được lấy từ **lần suy luận đầu tiên của root node trong lượt mô phỏng thứ nhất của MCTS**, hoặc truy vấn qua `GetCachedEvaluation(root)` sau khi search kết thúc (có áp dụng fallback khi cache miss).
*   `best_q/d` = evaluation của nước đi tốt nhất sau khi kết thúc tìm kiếm (thể hiện giá trị $q$ - ước lượng tốt nhất của MCTS).
*   `z` (`result_q/d`): được gán ở CUỐI ván đấu dựa trên kết quả chung cuộc thực tế (WIN = 1.0, DRAW = 0.0, LOSS = -1.0) từ góc nhìn side-to-move của từng ply. Giá trị này được đảo dấu xen kẽ theo quy luật parity lượt đi (ply parity).
*   Lưu trữ đồng thời cả `best_q` ($q$) và `result_q` ($z$) cho phép Module B (PyTorch) thực hiện kỹ thuật trộn mục tiêu giá trị (qMix) ở Mục 8.2.1.

### A5. Vòng lặp 1 ván self-play (kế thừa `SelfPlayGame::Play`)
Quy trình thực thi của một ván đấu tự chơi:
1.  **Khởi tạo vị trí bắt đầu**:
    *   **Quyết định mặc định (Cho tới khi đạt ~2000 Elo)**: Khởi dựng bàn cờ từ vị trí xuất phát `startpos` tiêu chuẩn của biến thể 10x10. Quá trình tự đấu sẽ bắt đầu trực tiếp từ vị trí này và ghi nhận đầy đủ tất cả các nước đi từ nước 1 đến khi kết thúc ván (không lọc bỏ bất kỳ ply nào để đảm bảo mạng nơ-ron học hoàn chỉnh toàn bộ ván đấu, bao gồm cả các nước đi khai cuộc đầu tiên).
    *   **Phòng hờ cho tương lai**: Thiết kế cấu trúc bitboard thưa và chỉ số cột xe castling ở mục A1 đã sẵn sàng để sau này (khi AI đã đạt > 2000 Elo) có thể dễ dàng chuyển sang các thế cờ khởi đầu Chess960-10x10 mà không cần sửa đổi C++ engine.
2.  Khi ván đấu chưa kết thúc:
    a.  Chạy `Search` với số lượng visits được điều chỉnh linh hoạt theo chiến lược: **sử dụng `visits=200` ở các thế hệ đầu tiên để tăng tốc độ lặp**, sau đó tăng dần lên `visits=400` và `visits=800` ở các thế hệ huấn luyện tiếp theo nhằm tăng độ sâu nhìn xa. Kích hoạt nhiễu Dirichlet tại root node (`kNoiseEpsilon/Alpha`).
    b.  Sau khi search xong, gửi một truy vấn tới cache `GetCachedEvaluation(root)` để lấy lại kết quả eval thô và prior thô (chưa nhiễu Dirichlet) của root. 
        *   **Kiểm tra Cache Miss**: Nếu cache trả về giá trị hợp lệ, gán `orig_q` và prior $p_{NN}$ từ cache. Nếu cache miss (trả về `std::nullopt` do va chạm hash ~1%), tiến hành fallback an toàn: gán `orig_q = best_q` và vector $p_{NN}$ thô là phân bố đồng đều (hoặc gán `policy_kld = 0.0f`).
    c.  Ánh xạ visits và prior từ cache vào không gian phẳng 10,600 qua hàm `MoveToNNIndex`. Tính toán độ phân kỳ `policy_kld` trên các index nước đi hợp lệ.
    d.  Mã hóa vị trí hiện tại thông qua [EncodePositionForNN](file:///d:/chess_variant/custom_engine/src/lczero_chess/chess/encoder.cc) để trích xuất các thông tin bitboard mask lưu vào `piece_planes` cùng các thông tin scalar. Quyền nhập thành được trích xuất dưới dạng chỉ số cột xe (0-9) hoặc `0xFF` nếu mất quyền.
    e.  Đẩy record `TrainingDataV1` vào mảng tạm thời `training_array` cho **mọi nước đi** (không loại bỏ nước nào).
    f.  Chọn nước đi: Sử dụng cơ chế temperature-sampling (ở các nước đi đầu sau khi search xong) hoặc chọn greedy nước đi có số visits cao nhất (ở giai đoạn sau).
    g.  Thực hiện nước đi trên bàn cờ `NodeTree.MakeMove(move)`. Thao tác này tự động gọi hàm `TrimHistory(100)` để giải phóng bộ nhớ lịch sử không cần thiết.
    h.  Kiểm tra điều kiện kết thúc ván đấu thông qua `ComputeGameResult` (chiếu hết, stalemate, luật 7-check, luật 50 nước đi rule50, lặp lại thế cờ 3 lần).
3.  Khi ván đấu kết thúc, duyệt ngược `training_array`, gán giá trị kết quả ván đấu thực tế $z$ (`result_q/d`) cho từng record tương ứng với side-to-move của lượt đi đó.
4.  Ghi và nén toàn bộ mảng record ra file `.gz` thông qua `TrainingDataWriter`.

*   **Heap Allocation (Phòng vệ stack):** Vì kích thước lịch sử bàn cờ có thể tăng lên đến 512 ply, các đối tượng `Search` và `NodeTree` bắt buộc phải được cấp phát trên Heap thông qua `std::make_unique` để tránh nguy cơ tràn bộ nhớ stack trên môi trường Windows.
*   **Cơ chế đầu hàng sớm (Resign):** Để tối ưu hóa throughput sinh dữ liệu, nếu giá trị `best_q` của một bên tụt xuống dưới ngưỡng resign (ví dụ: -0.90) liên tiếp trong 3 lượt đi, ván đấu sẽ được xử thua sớm. Thiết lập tỷ lệ "no-resign" khoảng 10% các ván đấu để hệ thống vẫn học được cách chống đỡ ở các thế cờ yếu và lật ngược thế cờ.

### A6. Driver đa ván song song (đơn giản hóa `tournament.cc`)
*   Khởi tạo một thread pool gồm $K$ worker threads chạy song song. Mỗi worker thread chịu trách nhiệm thực hiện một ván đấu self-play tuần tự từ đầu đến cuối.
*   Các worker threads chia sẻ chung một thực thể suy luận duy nhất là `OnnxBackend` và một bộ đệm `ZeroHeapCache` (an toàn đa luồng nhờ cơ chế seqlock không khóa - lockless).
*   **Bảo vệ GPU khi chạy đa luồng sinh dữ liệu (Chống lỗi rác và tràn bộ đệm):**
    *   **Cơ chế Batch Splitting:** Khi chạy đa luồng, số lượng node được đẩy vào hàng đợi suy luận cùng một thời điểm `enqueued_` có thể vượt quá kích thước batch cố định `fixed_batch_size_` (gọi là MCTS Parallel Gather Overshoot). `OnnxBackend` đã được tích hợp vòng lặp chia nhỏ batch trong `ComputeBlocking`. Nó sẽ tự động phân tách hàng đợi thành các sub-batches kích thước chính xác là `fixed_batch_size_` và thực hiện `std::memset` về `0` cho các slot padding trống của `input_buffer_`. Điều này ngăn chặn việc đọc dữ liệu cũ/rác trên bộ nhớ GPU.
    *   **Cơ chế Safety Clamp:** Giới hạn cứng `fixed_batch_size_` không được vượt quá dung lượng buffer tĩnh `MaxBatchSize` (64) trong hàm `UpdateConfiguration` để loại bỏ hoàn toàn nguy cơ tràn bộ đệm khi người dùng cấu hình sai tham số.
    *   **Tối ưu hóa CPU:** Loại bỏ hoàn toàn các lệnh `memset` dư thừa đối với các buffer đầu ra (policy/value) vì chúng sẽ được hàm `Run` ghi đè trực tiếp. Đồng thời lược bỏ thao tác trùng lặp `SetGraphOptimizationLevel` trong constructor.
*   Kích hoạt tính năng thông qua giao diện dòng lệnh (CLI): `custom_engine.exe --selfplay --games=1000 --out=data/ --visits=200` (sử dụng 200 làm tham số khởi đầu trên CPU).

### A7. Tích hợp với code hiện có
*   Tạo mới thư mục chứa mã nguồn: `src/lczero_chess/trainingdata/` (chứa writer và record struct) và `src/lczero_chess/selfplay/` (chứa game loop và driver đa luồng).
*   Đấu nối trực tiếp cờ CLI `--selfplay` trong hàm khởi tạo của engine tại [main.cc:L1270](file:///d:/chess_variant/custom_engine/src/main.cc#L1270) (nằm trong phần xử lý CLI của hàm `main()`, dòng 1270 thực tế) để điều hướng luồng chương trình vào driver sinh dữ liệu tự chơi.

### A8. Proposed Changes (Đề xuất thay đổi cấu trúc mã nguồn để hỗ trợ Linux/CUDA)

Để hỗ trợ khả năng biên dịch đa nền tảng (Windows/Linux) và kích hoạt GPU thực sự trên Google Colab, chúng ta cần chỉnh sửa cấu trúc build Meson và file backend C++:

#### [MODIFY] [meson.build](file:///d:/chess_variant/custom_engine/meson.build)
*   Chỉnh sửa logic link ONNX Runtime theo host machine:
    *   Nếu `host_machine.system() == 'windows'`: Tiếp tục link tới `third_party/onnxruntime-win-x64-1.18.0`.
    *   Nếu `host_machine.system() == 'linux'`: Tải và liên kết thư viện động `onnxruntime.so` từ bản `onnxruntime-linux-x64-gpu-1.18.0` (tải tự động hoặc hướng dẫn người dùng giải nén vào thư mục `third_party` của Linux).
*   Bổ sung tham số macro compile điều kiện, ví dụ `-DUSE_CUDA` nếu Meson detect được thư viện ONNX GPU hoặc do người dùng truyền vào (ví dụ: `meson configure -Dcuda=true`).

#### [MODIFY] [onnx_backend.cc](file:///d:/chess_variant/custom_engine/src/lczero_chess/neural/onnx_backend.cc)
*   Include có điều kiện thư viện factory CUDA:
    ```cpp
    #ifdef USE_CUDA
    #include <cuda_provider_factory.h>
    #endif
    ```
*   Bỏ comment đoạn code gọi CUDA Provider trong `InitializeSession()` và bao quanh bằng macro bảo vệ `#ifdef USE_CUDA` để bảo đảm file vẫn build bình thường trên môi trường CPU Windows của người dùng:
    ```cpp
    #ifdef USE_CUDA
    if (provider_ == "cuda") {
        OrtCUDAProviderOptions options;
        options.device_id = 0;
        session_options_.AppendExecutionProvider_CUDA(options);
        std::cout << "[ONNX Backend] CUDA Execution Provider appended successfully." << std::endl;
    }
    #endif
    ```

---

## 3. MODULE B — Huấn luyện (Python / PyTorch, chạy Colab GPU)

> Viết mới hoàn toàn bằng PyTorch, tối ưu hóa để chạy trên GPU của Google Colab và tích hợp sâu các thuật toán huấn luyện nâng cao từ `lczero-training` (Mục 8).

### B1. Reader định dạng (Python)
*   Sử dụng thư viện `struct` của Python để đọc và giải nén (unpack) file nhị phân nén `.gz` theo đúng layout cấu trúc `TrainingDataV1` đã được thiết lập với thuộc tính `pack(1)`.
*   **Giải nén bitboard planes thưa:** Chuyển đổi dữ liệu `piece_planes` (bitboard masks) từ dạng nhị phân 128-bit thành tensor float kích thước `[226, 10, 10]`, khớp hoàn hảo với logic tái tạo của [UnpackInputPlanes](file:///d:/chess_variant/custom_engine/src/lczero_chess/chess/encoder.cc). Các plane phụ trợ (rule50, checks, board edge) được điền giá trị float từ các trường scalar tương ứng.
*   **Tái tạo Castling Planes (Đúng hệ tọa độ canonical):** Python Reader sẽ đọc 4 trường `castling_us_ooo_file`, v.v. Nếu giá trị của trường khác `0xFF` (255), Reader sẽ tự động bật bit 1.0f tại ô xe tương ứng theo đúng rank của quân đó từ góc nhìn canonical (side-to-move):
    *   Đối với **quân TA (us - planes 216/217)**: Xe nhập thành nằm ở hàng đáy $\rightarrow$ bật bit tại `(rank=0, file=castling_file_idx)`.
    *   Đối với **quân ĐỊCH (them - planes 218/219)**: Xe nhập thành nằm ở hàng đỉnh của đối phương $\rightarrow$ bật bit tại `(rank=9, file=castling_file_idx)` cho bàn cờ 10x10.
    Cách làm này đảm bảo tái tạo chính xác 100% các plane nhập thành cho mọi thế cờ khởi đầu ngẫu nhiên (Chess960-10x10).
*   **Phòng tránh lỗi tràn bộ nhớ Colab (Sparse Shuffle Buffer):** 
    Mảng `probabilities` dạng dense kích thước 10,600 chiếm 42.4KB (92% kích thước record). Nếu giữ nguyên mảng dense này cho Shuffle Buffer quy mô 100,000 thế cờ, hệ thống sẽ tiêu tốn tới **~4.6 GB RAM** (chưa tính overhead của multiprocessing và DataLoader workers), rất dễ gây sập RAM (OOM) trên máy ảo Colab (~12GB RAM).
    
    *Giải pháp tối ưu*: 
    1.  **Trên ĐĨA**: Giữ nguyên định dạng nhị phân dense nhắm tối ưu hóa I/O và tận dụng thuật toán nén gzip (các số 0 được nén cực tốt, chỉ còn 2-3KB/record).
    2.  **Trên RAM (Python Reader)**: Ngay khi giải nén record nhị phân từ đĩa, Python Reader lập tức **nén thưa (sparse-ify)** mảng `probabilities` thành một danh sách (list) chứa các cặp `(uint16_t index, float prob)` cho các nước đi hợp lệ (xác suất > 0, thường tối đa khoảng 100-150 nước). Việc này giảm kích thước phần policy xuống chỉ còn **~600 - 900 Bytes/record** (giảm kích thước Shuffle Buffer xuống còn **~400 MB** cho 100k records, tránh OOM).
    3.  **Tạo Batch**: Chỉ khi DataLoader tiến hành ghép batch để nạp vào GPU, ta mới thực hiện "dense-hóa" mảng thưa này trở lại thành Tensor Float kích thước `[batch, 10600]` chứa đầy đủ các số 0.
*   **Down-sampling vị trí (Mục 8.2.3):** Reader sẽ ngẫu nhiên loại bỏ khoảng 50% - 75% số lượng thế cờ trong một ván đấu để làm đa dạng hóa tập huấn luyện và tăng tốc độ học.
*   **Worker-based Parallel Parsing (Mục 8.2.7):** Cấu hình PyTorch DataLoader với tham số `num_workers > 0`.
*   **Đồng bộ hóa khứ hồi (Test Round-trip):** Viết script unit test đối chiếu: C++ sinh ra một thế cờ mẫu $\rightarrow$ ghi file nhị phân $\rightarrow$ Python Reader đọc lại và giải nén $\rightarrow$ so sánh khớp từng bit của planes, $\pi$, $z$, và các trường scalar. Đây là bước kiểm soát chất lượng bắt buộc.

### B2. Kiến trúc mạng (Chốt cấu hình ResNet 10x128)
Mặc dù về mặt kỹ thuật, engine C++ chỉ quan tâm đến hợp đồng giao tiếp I/O (tên và shape của tensors) của tệp ONNX, **quyết định thiết kế của dự án là bắt đầu ngay bằng mạng ResNet 10 blocks x 128 filters** để đảm bảo khả năng đánh giá sâu và nhìn xa của các chiến thuật từ những đời self-play đầu tiên. 

Mạng nơ-ron PyTorch sẽ được thiết lập chính xác như sau để tương thích 100% với `weights_0_elo.onnx` and engine:
*   **Input Tensor:** Tên bắt buộc là `"input"`, kích thước shape `[batch, 226, 10, 10]`, có trục batch động (dynamic axis) được đặt tên chính xác là `"batch"`.
*   **Conv/Residual Tower:** Xây dựng chính xác cấu hình **ResNet 10 blocks x 128 filters** (gồm 1 lớp Conv $3 \times 3$ ban đầu với 128 filters, theo sau là 10 khối Residual blocks tiêu chuẩn, mỗi khối sử dụng 128 filters và có skip connection).
*   **Policy Head:** Tên output bắt buộc là `"policy"`, kích thước shape `[batch, 10600]`. **Đặc biệt lưu ý: Không tích hợp lớp Softmax vào cuối đồ thị ONNX**.
*   **Value Head:** Tên output bắt buộc là `"value"`, kích thước shape `[batch, 3]` (Win, Draw, Loss). **Bắt buộc phải tích hợp lớp Softmax ở cuối đồ thị ONNX** để trả về trực tiếp xác suất WDL cho engine.

### B3. Loss + Vòng huấn luyện (AlphaZero tinh hoa)
*   **Hàm Loss tổng hợp (Mục 8.2.5):**
    $$\text{Loss} = \text{Loss}_{\text{policy}} + \text{Loss}_{\text{value}} + c \cdot L_2$$
    *   $\text{Loss}_{\text{policy}}$: Masked Cross-Entropy giữa logits đầu ra của policy và phân bố mục tiêu $\pi$.
    *   $\text{Loss}_{\text{value}}$: Cross-Entropy giữa phân bố WDL đầu ra của value head và mục tiêu value đã trộn.
    *   $c \cdot L_2$: Regularization chống quá khớp với hệ số decay $c \approx 10^{-4}$.
*   **Trộn mục tiêu Value (qMix - Mục 8.2.1):**
    $$\text{target\_value} = q\_ratio \cdot q + (1 - q\_ratio) \cdot z$$
    Sử dụng tỷ lệ trộn $q\_ratio \approx 0.2$ để kết hợp kết quả ván đấu thực tế $z$ (`result_q`) với giá trị ước lượng sau tìm kiếm $q$ (`best_q`).
*   **Stochastic Weight Averaging (SWA - Mục 8.2.4):** Áp dụng trung bình cộng trọng số của mô hình ở các epoch huấn luyện cuối cùng.
*   **Rolling Window (Shuffling Pool - Mục 8.2.8):** Duy trì một bể chứa dữ liệu động (FIFO queue). Để thực tế với tài nguyên tính toán ban đầu, quy mô rolling window được thiết lập nhỏ gọn hơn (ví dụ: gồm **5,000 đến 10,000 ván đấu** tự chơi mới nhất) giúp mô hình phản hồi nhanh chóng với dữ liệu mới sinh ra.
*   **Lọc chọn thế cờ khó (diff_focus - Mục 8.2.6):** Thực hiện tính toán xác suất lựa chọn huấn luyện dựa trên độ lệch giữa eval tĩnh của mạng `orig_q` và eval sau tìm kiếm `best_q` kết hợp với giá trị `policy_kld`.

### B4. Export ONNX
Xuất mô hình PyTorch đã được huấn luyện sang định dạng ONNX phục vụ engine C++:
```python
import torch

# dummy_input đại diện cho 1 thế cờ canonical
dummy_input = torch.randn(1, 226, 10, 10)
torch.onnx.export(
    model, 
    dummy_input, 
    "weights_N.onnx",
    input_names=["input"],
    output_names=["policy", "value"],
    dynamic_axes={
        "input": {0: "batch"},
        "policy": {0: "batch"},
        "value": {0: "batch"}
    },
    opset_version=15
)
```
*   **Kiểm tra tính tương thích:** Chạy công cụ Netron để xác nhận: trục batch của cả 3 tensors đều mang tên `"batch"`, policy head không chứa Softmax, value head kết thúc bằng Softmax, các tên I/O khớp 100% với cấu hình nạp của [OnnxComputation](file:///d:/chess_variant/custom_engine/src/lczero_chess/neural/onnx_backend.cc).

---

## 4. Phân kỳ / Milestones

| Phase | Nội dung công việc | Tiêu chí hoàn thành (Definition of Done) | Liên kết kỹ thuật Mục 8 |
|-------|--------------------|-------------------------------------------|--------------------------|
| **T1** | Định nghĩa cấu trúc record `TrainingDataV1` & Writer | Ghi nhận dữ liệu thành công, so sánh khứ hồi (C++ test) khớp 100% bit nhị phân (kích thước 45940 bytes). | Đóng gói cấu trúc bitboard thưa (8.1). |
| **T2** | Trích xuất $\pi$ từ visits + Tính `policy_kld` + Gán $z$ | Test chạy 1 ván ngắn: tổng $\pi = 1.0$, `policy_kld` > 0 hợp lệ (truy xuất prior NN thô qua cache, có xử lý fallback an toàn khi cache miss), $z$ đảo dấu chính xác theo lượt đi. | Khởi tạo dữ liệu cho **diff_focus (8.2.6)** và **qMix (8.2.1)**. |
| **T3** | Vòng tự chơi 1 ván hoàn chỉnh từ startpos | Sinh ra file `.gz` hợp lệ chứa đầy đủ dữ liệu toàn bộ ván đấu (ghi nhận mọi nước đi, không lọc bỏ) và đóng file an toàn trên Heap. | Heap Allocation để chống tràn stack Windows. |
| **T4** | Driver đa luồng song song (`--selfplay`) | Sinh thử 100 ván tự chơi song song ổn định, không rò rỉ bộ nhớ, không crash. | Kích hoạt Batch Splitting và Safety Clamp trên GPU. |
| **T5** | Reader Python + Test round-trip C++↔Python | Tensor planes (bao gồm cả việc tái tạo castling cho Chess960 từ chỉ số cột xe nhập thành: us ở rank 0, them ở rank 9), $\pi$, $z$, `orig_q`, `policy_kld` khớp bit 100% giữa C++ và Python (so sánh qua ánh xạ MoveToNNIndex 10600). | Tích hợp **Shuffle Buffer (8.2.2)** và **Down-sampling (8.2.3)**. |
| **T6** | Model PyTorch (10x128) + Loss + SWA + Export ONNX | Mạng 10x128 hội tụ trên tập dữ liệu nhỏ; export ONNX thành công và chạy thử được trong engine. | Áp dụng **SWA (8.2.4)** và **Loss tổng hợp (8.2.5)**. |
| **T6.5** | **Port engine sang Linux / CUDA cho Colab** | Tích hợp onnxruntime-linux-gpu, chỉnh sửa `meson.build` và bật CUDA EP thành công. Compile và chạy kiểm thử 100% pass trên môi trường GPU Linux của Google Colab. | Tách biệt cấu trúc đa nền tảng và bật thực tế CUDA Execution Provider. |
| **T7** | Vòng lặp đầy đủ trên Colab (gen $\rightarrow$ train $\rightarrow$ gen) | Chạy thử nghiệm thành công 3 thế hệ (generations); mô hình đời sau thắng mô hình đời trước. | Áp dụng **Rolling Window (8.2.8)**. |

*   **T1–T4:** Thực hiện hoàn toàn trên CPU máy cục bộ để kiểm tra tính đúng đắn của logic.
*   **T5–T6:** Thực hiện viết code Python và PyTorch phục vụ huấn luyện.
*   **T6.5–T7:** Thực hiện trên Google Colab (sử dụng GPU) để tối ưu hóa hiệu năng huấn luyện và tự chơi.

---

## 5. Hiệu năng & Throughput Thực tế (CPU cục bộ vs Colab GPU)

Do quyết định sử dụng cấu hình mạng tương đối nặng là **ResNet 10 blocks x 128 filters** ngay từ đầu trên bàn cờ $10 \times 10$ (100 ô cờ, phân nhánh lớn), hiệu năng suy luận (inference) sẽ trở thành điểm nghẽn chính khi chạy tự đấu trên máy cục bộ không có GPU. 

### 5.1. Ước lượng throughput trên CPU cục bộ (Module A - Self-play)
*   **Chi phí tính toán**: Mỗi nước đi cần chạy trung bình $200 - 800$ lượt MCTS visits. Trên CPU, mỗi lượt suy luận mạng 10x128 sẽ mất vài mili-giây.
*   **Chiến lược huấn luyện visits tăng dần (Chốt quyết định)**:
    Để tối ưu hóa thời gian sinh dữ liệu, chúng ta áp dụng **chiến lược tìm kiếm tăng dần theo năng lực mô hình**:
    *   **Thế hệ đời đầu (gen 0, gen 1)**: Cấu hình `visits=200`. Search nông giúp thời gian suy luận cực nhanh (nước đi chỉ mất **~50 - 100 ms**), đẩy nhanh tốc độ sinh 1,000 ván đấu thế hệ đầu xuống chỉ còn **~1 đến 1.5 giờ** trên CPU cục bộ. Chất lượng dữ liệu ở `visits=200` vẫn hoàn toàn đủ để mạng nơ-ron học các khái niệm luật chơi, phối hợp ngắn hạn và khai cuộc căn bản.
    *   **Thế hệ trung gian (gen 2, gen 3...)**: Tăng cấu hình lên `visits=400`. Khi mạng bắt đầu hiểu cờ sâu hơn, tăng visits giúp MCTS tìm ra các đòn chiến thuật tầm trung để dạy cho mạng.
    *   **Thế hệ tinh chỉnh sâu**: Tăng cấu hình lên `visits=800` (được chạy khi đã chuyển hệ thống self-play lên GPU Colab để bảo đảm throughput).

### 5.2. Chuyển sinh dữ liệu lên Colab GPU sớm (Giải pháp tối ưu)
*   Để đạt được tốc độ tối đa cho `visits=800` chuẩn AlphaZero, chúng ta nên đóng gói file thực thi C++ `custom_engine` thành bản build Linux (được thực hiện ở Milestone T6.5) và chuyển toàn bộ quy trình self-play lên Google Colab GPU sớm.
*   ONNX Runtime trên GPU Colab (sử dụng CUDA Provider kết hợp fixed batching) sẽ thực hiện suy luận song song mô hình 10x128 cực kỳ nhanh chóng. Việc kết hợp MCTS song song của C++ và Tensor Cores của GPU sẽ giúp throughput ván đấu tăng vọt gấp hàng chục lần so với CPU cục bộ.

### 5.3. Huấn luyện và Truyền tải dữ liệu
*   **Huấn luyện (Module B)**: Thực hiện 100% trên Colab GPU để tận dụng Mixed-Precision (FP16), đẩy batch size lên lớn (1024 - 2048) nhầm rút ngắn thời gian huấn luyện mỗi đời xuống còn vài chục phút.
*   **Truyền tải (Archiving)**: Gom hàng ngàn file `.gz` nhỏ thành một file `.zip` lớn (không nén thêm, chỉ đóng gói dạng Store để tối ưu I/O) trước khi upload lên Google Drive nhằm tránh bị Google Drive bóp băng thông do tải nhiều file nhỏ liên tiếp.

---

## 6. Rủi ro & Quyết định đã chốt

1.  **Đồng bộ quy ước C++↔Python (Rủi ro nghiêm trọng nhất):** Bất kỳ sự sai lệch nào về thứ tự trục, hướng xoay bàn cờ canonical hay index nước đi đều khiến mạng nơ-ron học sai lệch hoàn toàn mà không báo lỗi (silent failure). Giải quyết bằng quy trình kiểm thử round-trip nghiêm ngặt ở Phase T5.
2.  **Dấu của $z$ theo lượt (Parity):** Đã chốt logic gán giá trị ở cuối ván đấu: các thế cờ có lượt đi là bên Trắng sẽ nhận giá trị $z = \text{result}$ của Trắng; các thế cờ có lượt đi là bên Đen sẽ nhận giá trị $z = -\text{result}$ của Trắng.
3.  **Lưu trữ Plane Thưa (Sparse bitboards):** Đã quyết định phương án lưu trữ bitboard mask 128-bit cho 216 planes lịch sử để giảm dung lượng ghi đĩa. Quyền nhập thành được lưu trữ dưới dạng chỉ số cột xe (file index) để hỗ trợ Chess960 và thế cờ khởi đầu ngẫu nhiên.
4.  **Cơ chế sinh thế cờ khai cuộc và lộ trình đa dạng**: Mặc định chạy từ thế cờ xuất phát `startpos` tiêu chuẩn và ghi nhận đầy đủ 100% mọi nước đi trong ván đấu (không cắt bỏ nước đầu). Cơ chế Chess960 (Fairy Chess960 xáo trộn hàng cuối) chỉ được xem xét làm phương án nâng cấp trong tương lai dài hạn (khi AI đã đạt trình độ Elo > 2000 Elo trên bàn cờ chuẩn).
5.  **Kiến trúc mạng chốt:** Quyết định chốt bắt đầu ngay bằng cấu hình **ResNet 10 blocks x 128 filters** ở thế hệ đầu tiên để giữ vững sức mạnh chiến thuật, bảo đảm độ nhìn sâu của mạng nơ-ron ngay từ đầu.
6.  **An toàn bộ nhớ và suy luận GPU:** Tích hợp trực tiếp cơ chế **Safety Clamp** và **Batch Splitting** vào [onnx_backend.cc](file:///d:/chess_variant/custom_engine/src/lczero_chess/neural/onnx_backend.cc).
7.  **Porting đa nền tảng**: Đã quyết định chốt thêm một Milestone riêng (**T6.5**) để porting build system sang Linux GPU Colab, giải quyết độc lập việc tải thư viện `.so` của Linux, liên kết lại `meson.build` và kích hoạt CUDA EP.

---

## 7. Tóm tắt các bước thực hiện tiếp theo

1.  **Phát triển C++ (T1 $\rightarrow$ T4):** 
    *   Tạo struct `TrainingDataV1` trong thư mục `src/lczero_chess/trainingdata/`.
    *   Viết lớp ghi dữ liệu nén gzip `TrainingDataWriter`.
    *   Hiện thực hóa vòng lặp tự chơi tự động trong `SelfPlayGame` (MCTS search truy vấn cache lấy `p_NN` thô và `orig_q` thông qua `GetCachedEvaluation` sau search, có khối lệnh kiểm tra an toàn để xử lý fallback `orig_q = best_q` và `policy_kld = 0.0f` nếu xảy ra cache miss do va chạm hash. Thực hiện ánh xạ MoveToNNIndex 10,600 để so khớp chính xác thứ tự cạnh và tính `policy_kld`, ghi nhận đầy đủ mọi nước đi của ván đấu vào file nén, gán $z$ đảo dấu ở cuối ván).
    *   Tích hợp driver CLI `--selfplay` trong [main.cc](file:///d:/chess_variant/custom_engine/src/main.cc) tại [main.cc:L1270](file:///d:/chess_variant/custom_engine/src/main.cc#L1270). Tiến hành chạy thử nghiệm sinh dữ liệu cục bộ trên CPU với `visits=200` ở các thế hệ đầu để lặp nhanh.
2.  **Phát triển Python Reader (T5):** 
    *   Viết mã nguồn Python giải nén file `.gz`, unpack bitboard mask thành tensor float (tái tạo castling từ chỉ số cột xe nhập thành: us ở rank 0, them ở rank 9). Tích hợp cơ chế **Sparse Shuffle Buffer** trên RAM để tránh tràn bộ nhớ Colab.
    *   Lập trình bộ đệm trộn động Streaming Shuffle Buffer (Fisher-Yates) và bộ lọc Down-sampling.
    *   Thực hiện chạy thử nghiệm round-trip để xác thực tính đúng đắn của dữ liệu.
3.  **Phát triển Pipeline Huấn luyện (T6):** 
    *   Khởi dựng mạng **ResNet 10 blocks x 128 filters** trong PyTorch.
    *   Hiện thực hóa hàm loss tổng hợp (Masked Policy CE + qMix Value CE + L2 Regularization).
    *   Áp dụng bộ tối ưu hóa kết hợp SWA. Huấn luyện trên tập dữ liệu thử nghiệm nhỏ và xuất file ONNX.
4.  **Porting Engine sang Linux GPU (T6.5)**:
    *   Sửa đổi file `meson.build` để detect OS: tải và liên kết động với thư viện `onnxruntime.so` của Linux GPU khi build trên Linux.
    *   Bật CUDA Execution Provider trong `InitializeSession()` của `onnx_backend.cc` dưới cờ macro `#ifdef USE_CUDA`. Include tệp tiêu đề CUDA factory thích hợp.
    *   Chạy thử nghiệm compile và test trực tiếp trên Google Colab để kiểm tra tính ổn định của GPU backend.
5.  **Chạy trên Colab (T7):** 
    *   Đưa toàn bộ pipeline huấn luyện lên Google Colab, thiết lập vòng lặp huấn luyện AlphaZero khép kín. Chạy self-play trên Colab GPU ở visits=800 để lặp đời AI đạt Elo cao nhanh nhất.

---
---

## 8. KẾ THỪA TINH HOA TỪ `lczero-training` (cập nhật cho Module B + record)

> Nguồn: `D:\chess_variant\lczero-training-master` (repo train TF của Lc0). Tuy là TF, **các kỹ thuật xử lý dữ liệu + loss + pipeline đều port thẳng sang PyTorch được**. Đây là phần đáng kế thừa nhất.

### 8.1. Training tuple chuẩn (xác nhận từ `docs/training_tuple.md`)
`convert_v6_to_tuple` → `(planes, probs, winner, best_q, plies_left)`:
- `planes` (112×64 ở chess; với ta là **226×100**), `probs` (1858 → **10600**), `winner` = WDL theo side-to-move (z), `best_q` = WDL eval-sau-search (q), `plies_left` = MLH scalar.
→ Khớp record `TrainingDataV1` ở mục A1. **Bổ sung khuyến nghị:** thêm 2 field để bật được các kỹ thuật bên dưới: `orig_q/orig_d` (eval NN **trước** search của root) và `policy_kld`. Cả hai rẻ để ghi trong self-play (orig_q = lần eval NN đầu tiên của root; policy_kld = KL(π_visits ‖ π_nn)).
- Trường `plies_left` (khoảng cách mate-in-moves / MLH) không cần lưu trong struct do mạng nơ-ron hiện tại không cấu hình MLH head (`has_mlh = false`).

### 8.2. 🎯 Kỹ thuật ĐÁNG kế thừa nhất (port sang PyTorch)

| # | Kỹ thuật | Nguồn | Giá trị | Ghi chú port |
|---|----------|-------|---------|--------------|
| 1 | **q_ratio — trộn value target** `target = q_ratio·q + (1−q_ratio)·z` | `tfprocess.py:485-491` | ⭐⭐⭐ Học value nhanh & ổn định hơn dùng z thuần | Record đã giữ cả `best_q` (q) lẫn `result_q` (z) → trộn ở Python. Bắt đầu `q_ratio≈0.2` |
| 2 | **Streaming Shuffle Buffer** (Fisher-Yates) | `shufflebuffer.py` | ⭐⭐⭐ Train trên data >> RAM mà vẫn shuffle tốt | **Tối ưu tránh OOM Colab**: Trên đĩa nén gzip dạng dense. Trên RAM, Reader Python nén thưa (sparse) probabilities[10600] thành list các cặp `(idx, prob)` cho nước hợp lệ (~600B/record). Chỉ dense-hóa khi DataLoader tạo batch. Giữ buffer 100k records chỉ mất ~400MB RAM. |
| 3 | **Down-sampling vị trí (sample rate)** | `chunkparser.sample_record` | ⭐⭐⭐ Chống over-correlation (các thế cờ liên tiếp 1 ván rất giống nhau) | Bỏ ngẫu nhiên ~ (1 − 1/N) record mỗi ván; chỉ giữ rải rác. RẤT quan trọng, đừng bỏ qua |
| 4 | **SWA (Stochastic Weight Averaging)** | `tfprocess.py:322-391` | ⭐⭐ Net cuối khái quát tốt hơn | PyTorch có `torch.optim.swa_utils` sẵn |
| 5 | **Loss = policy CE (masked) + WDL value CE + L2** | `tfprocess.py:439-516` | ⭐⭐⭐ Công thức chuẩn | `cross_entropy(logits, π)` cho policy (nước phi pháp π=0 tự loại / hoặc mask −∞); `cross_entropy` WDL cho value; `weight_decay=1e-4` |
| 6 | **diff_focus** — ưu tiên thế cờ "khó/đáng học" | `chunkparser` (diff_focus_*) | ⭐ (nâng cao) | Bỏ xác suất theo độ lệch `orig_q` vs `best_q` + `policy_kld`. Cần 2 field ở 8.1. Làm SAU |
| 7 | **Worker-based parallel parsing** | `chunkparser` (multiprocessing) | ⭐⭐ Giữ GPU không đói data | PyTorch `DataLoader(num_workers>0)` lo sẵn việc này |
| 8 | **Rolling window (shuffling pool)** của các ván GẦN NHẤT | `docs/shuffling_pool_hanse_sampling.md` | ⭐⭐ Chất lượng vòng lặp AZ | Mỗi đời train trên FIFO N ván mới nhất (ví dụ: đặt khoảng **5,000 đến 10,000 ván đấu** gần nhất cho giai đoạn khởi đầu để lặp nhanh trên tài nguyên giới hạn) |

### 8.3. KHÔNG nên kế thừa (không hợp biến thể này)
- **Symmetry augmentation** (transpose/mirror/diagonal qua `invariance_info`): với cờ (tốt/nhập-thành phá đối xứng) Lc0 **cũng không augment** kiểu đó; chỉ có lật dọc Trắng/Đen — mà ta đã canonical-hóa trong encoder. → giữ `transform=0`, KHÔNG augment.
- **`attention_policy_map.py` / `lc0_az_policy_map.py`**: ánh xạ policy 1858 riêng của chess 8×8. Ta dùng `MoveToNNIndex` 10600 riêng → KHÔNG dùng map của Lc0, nhưng **học cách họ tách "map index" thành module** để Python tái tạo `MoveToNNIndex` một lần, dùng chung reader + export.
- **`net.py` / proto format** của Lc0 (định dạng .pb.gz riêng): ta xuất thẳng ONNX nên bỏ qua; chỉ tham khảo `make_model.py` cho kiến trúc.

### 8.4. Kiến trúc mạng — tham khảo `make_model.py`
- Lc0 dùng **SE-ResNet** (Squeeze-Excitation residual blocks) cho conv tower, rồi tách policy/value head. Đây là kiến trúc đáng kế thừa (SE block tăng chất lượng rõ rệt với chi phí nhỏ).
- **Tuy nhiên, weights_0_elo chỉ là khởi điểm**, ta có quyền thiết kế mạng nhỏ hơn hoặc cấu hình khác (như đã chốt là **10x128**) miễn là khớp I/O interface. Sau này muốn nâng cấp lên SE-ResNet hoặc tăng số blocks/filters thì đổi đồng bộ cả model gen lẫn train.

### 8.5. Cập nhật Module B (mục 3) theo các gem trên
- **B1 Reader:** chèn **ShuffleBuffer (#2)** + **down-sampling (#3)** giữa đọc-chunk và batch; dùng `DataLoader(num_workers>0)` (#7).
- **B3 Loss:** dùng công thức #5; value target = **qMix (#1)**; thêm **SWA (#4)** cho net xuất.
- **Pipeline vòng lặp:** dùng **rolling window (#8)** — mỗi đời chỉ train trên ~N ván mới nhất.

### 8.6. Tài liệu nên đọc trong repo (tự tham khảo khi code)
- `docs/training_tuple.md` (định dạng tuple) · `docs/loader.md` (loader/shuffling) · `docs/heads.md` (policy/value/MLH heads) · `docs/architecture.md` (tổng thể) · `tf/chunkparser.py` (lõi parse+sample+diff_focus) · `tf/tfprocess.py` (loss+optimizer+SWA) · `tf/make_model.py` (SE-ResNet).

> **Tóm tắt mục 8:** từ `lczero-training` kế thừa được **q_ratio, streaming shuffle, down-sampling, SWA, công thức loss, parallel loader, rolling-window, SE-ResNet** — toàn bộ port sang PyTorch dễ dàng. Bỏ qua phần map-policy 1858 và proto-net riêng của Lc0. Cần thêm 2 field record (`orig_q`, `policy_kld`) nếu muốn diff_focus về sau.
