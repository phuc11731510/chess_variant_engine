# Đề xuất Tối ưu hóa (Cập nhật sau khi kiểm tra logic Phase 3)

Dưới đây là các đề xuất tối ưu hóa bổ sung nhằm tối đa hóa hiệu năng cho việc sinh dữ liệu huấn luyện (Self-play Data Generation) và thiết kế kiến trúc MCTS kế thừa từ Lc0 trong tương lai.

## 🟢 Đề xuất 20: Tái cấu trúc (Reorder) Layout của Lớp `Position` cho 1-Shot Memcpy
- **Vị trí**: `custom_engine/src/chess/position.h`
- **Phân tích**: Hiện tại trong `copy_from`, chúng ta đã gộp các mảng (board, byTypeBB,...) thành một khối liên tục để dùng 1 lệnh `std::memcpy`. Tuy nhiên, các biến POD (Plain Old Data) khác như `gamePly`, `sideToMove`, `chess960`, `pieceCountInHand`, `virtualPieces`, `promotedPieces` vẫn đang nằm xen kẽ với các con trỏ như `thisThread`, `st`, `var`.
- **Đề xuất**:
  Nhóm toàn bộ các con trỏ (`thisThread`, `st`, `var`) lên đầu hoặc xuống cuối cùng của class `Position`. Nhóm **tất cả** các biến trạng thái còn lại thành một khối liên tục. Khi đó, hàm `copy_from` chỉ cần gọi ĐÚNG 1 lệnh `memcpy`:
  ```cpp
  std::memcpy(board, other.board, offsetof(Position, promotedPieces) + sizeof(promotedPieces) - offsetof(Position, board));
  ```
  Điều này tận dụng triệt để tập lệnh SIMD/AVX của CPU để sao chép toàn bộ trạng thái trong một chu kỳ đồng hồ.

## 🟢 Đề xuất 21: Sử dụng `pop_lsb` để Tăng Tốc `UnpackInputPlanes` (Cực kỳ quan trọng cho NN Backend)
- **Vị trí**: `custom_engine/src/lczero_chess/chess/encoder.cc`
- **Phân tích**: Trong hàm `UnpackInputPlanes`, mã hiện tại sử dụng 2 vòng lặp lồng nhau (Rank x File) với tổng cộng 100 lần lặp (bàn cờ 10x10) và 100 nhánh `if (plane.mask & sq)` cho mỗi mặt phẳng (plane). Khi tạo hàng ngàn tensor mỗi giây, việc rẽ nhánh này làm chậm quá trình điền dữ liệu.
- **Đề xuất**:
  Vì `plane.mask` thực chất là một `Bitboard`, ta có thể duyệt qua các bit 1 (các ô có quân) mà không cần lặp qua ô trống:
  ```cpp
  // 1. Gán toàn bộ mảng float bằng 0
  std::memset(dest, 0, plane_size * sizeof(float));
  // 2. Chỉ duyệt các bit 1
  Stockfish::Bitboard b = plane.mask;
  while (b) {
      Stockfish::Square sq = Stockfish::pop_lsb(b);
      int f = Stockfish::file_of(sq);
      int r = Stockfish::rank_of(sq);
      dest[r * width + f] = plane.value;
  }
  ```
  Cách này loại bỏ hoàn toàn rẽ nhánh (branching) và giảm số lần lặp từ 100 xuống chỉ còn đúng bằng số lượng quân cờ trên mặt phẳng đó (thường là 1-8).

## 🟢 Đề xuất 22: Loại bỏ danh sách liên kết `StateInfo->previous` bằng Flat Hash Array (Chuẩn bị cho MCTS)
- **Vị trí**: `custom_engine/src/lczero_chess/chess/board.h` & `position.h`
- **Phân tích**: Việc kiểm tra lặp lại 3 lần (3-fold repetition) của Stockfish dựa vào con trỏ `si->previous` để duyệt ngược lịch sử. Cách này gây ra cache-misses liên tục vì CPU phải "nhảy" qua các vùng nhớ khác nhau. Hiện tại `ChessBoard` đang dùng `std::array<StateInfo, 2>` là đủ cho 1 Node MCTS đơn lẻ, nhưng nếu muốn duyệt sâu xuống nhánh (Rollout) hoặc Play-out hết game, ta cần lịch sử.
- **Đề xuất**:
  Thiết kế một struct `PositionHistory` (giống kiến trúc cốt lõi của Lc0) chỉ chứa một mảng phẳng: `std::vector<uint64_t> past_hashes;` hoặc `std::array<uint64_t, 512>`.
  Mỗi khi `ApplyMove`, ta đẩy `pos.key()` (Zobrist Hash) vào mảng này. Việc check 3-fold repition sẽ biến thành một vòng lặp `for` lùi đơn giản trên mảng liên tục, cực kỳ thân thiện với Cache CPU L1. Đồng thời, Node MCTS sẽ trở nên hoàn toàn Stateless (không phụ thuộc vào `StateInfo`).
