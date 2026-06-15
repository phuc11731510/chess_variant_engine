# Kế hoạch Triển khai Chi tiết Giai đoạn 3 - Lớp Cầu nối (Bridge Board Class)

Tài liệu này vạch ra thiết kế chi tiết, cấu trúc dữ liệu, cơ chế quản lý bộ nhớ ngăn xếp và quy trình kiểm thử cho Giai đoạn 3 nhằm kết nối logic cờ 10x10 của Fairy-Stockfish với bộ tìm kiếm MCTS của Lc0.

---

## 1. Cấu trúc Thư mục và Sắp xếp File

Toàn bộ các tệp bọc cầu nối sẽ nằm trong thư mục biệt lập:
`custom_engine/src/lczero_chess/chess/`

```
custom_engine/src/lczero_chess/chess/
├── types.h        # Khai báo bí danh kiểu Move, Square, MoveList
├── board.h        # Lớp ChessBoard bọc Stockfish::Position
├── board.cc       # Triển khai các API bàn cờ và quản lý StateInfo
├── position.h     # Lớp Position và PositionHistory của lczero
├── position.cc    # Triển khai tính toán thế trận và kiểm tra kết quả game
└── gamestate.h    # Cấu trúc GameState làm tham số đầu vào cho MCTS
```

---

## 2. Kế hoạch Hiện thực hóa từng File

### 2.0. Bổ sung hàm sao chép nhanh cho Stockfish Position [MODIFY]
Để tối ưu hóa việc sao chép bàn cờ hàng triệu lần trong MCTS, chúng ta sẽ bổ sung phương thức `copy_from` cho lớp `Stockfish::Position` để sao chép trực tiếp bộ nhớ (memcpy) thay vì chuyển đổi qua chuỗi FEN.

#### [MODIFY] [position.h](file:///d:/chess_variant/custom_engine/src/chess/position.h)
Thêm khai báo phương thức `copy_from` trong lớp `Position`:
```cpp
  Position& copy_from(const Position& other, StateInfo* newSt);
```

#### [MODIFY] [position.cpp](file:///d:/chess_variant/custom_engine/src/chess/position.cpp)
Triển khai phương thức `copy_from` bằng `std::memcpy` cực nhanh:
```cpp
Position& Position::copy_from(const Position& other, StateInfo* newSt) {
  std::memcpy(this, &other, sizeof(Position));
  st = newSt;
  return *this;
}
```

### 2.1. [types.h](file:///d:/chess_variant/custom_engine/src/lczero_chess/chess/types.h) [NEW]
*   **Nhiệm vụ**: Định nghĩa các kiểu cơ bản tương thích với mã nguồn Lc0 và tối ưu hóa hiệu năng sinh nước đi (không dùng std::vector để tránh cấp phát bộ nhớ động).
*   **Mã nguồn phác thảo**:
    ```cpp
    #pragma once
    #include <cstdint>
    #include "../../chess/types.h"
    #include "../../chess/movegen.h"

    namespace lczero {

    using Move = Stockfish::Move;
    using Square = Stockfish::Square;

    constexpr Move MOVE_NONE = Stockfish::MOVE_NONE;
    constexpr Move MOVE_NULL = Stockfish::MOVE_NULL;

    // Lớp bọc MoveList tĩnh trên Stack của Stockfish (Zero-Overhead Abstraction)
    class MoveList {
    public:
        MoveList(const Stockfish::Position& pos) : list(pos) {}
        
        struct const_iterator {
            const Stockfish::ExtMove* ptr;
            Move operator*() const { return ptr->move; }
            const_iterator& operator++() { ++ptr; return *this; }
            bool operator!=(const const_iterator& other) const { return ptr != other.ptr; }
        };
        
        const_iterator begin() const { return { list.begin() }; }
        const_iterator end() const { return { list.end() }; }
        size_t size() const { return list.size(); }
        bool empty() const { return size() == 0; }
        Move operator[](size_t index) const { return list.begin()[index].move; }
        
    private:
        Stockfish::MoveList<Stockfish::LEGAL> list;
    };

    } // namespace lczero
    ```

### 2.2. [board.h](file:///d:/chess_variant/custom_engine/src/lczero_chess/chess/board.h) [NEW]
*   **Nhiệm vụ**: Khai báo lớp `ChessBoard` bọc `Stockfish::Position` và quản lý vòng đời của ngăn xếp `StateInfo`.
*   **Điểm mấu chốt về bộ nhớ**: 
    `Stockfish::Position` lưu một con trỏ `st` trỏ vào `StateInfo` hiện tại. Khi `ChessBoard` bị sao chép (copy), ta bắt buộc phải sao chép cả ngăn xếp `states` và gán lại con trỏ `pos.set_state(&states.back())` để đảm bảo con trỏ không trỏ sang đối tượng cũ gây crash bộ nhớ (`segmentation fault`).
*   **Mã nguồn phác thảo**:
    ```cpp
    #pragma once
    #include <string>
    #include <vector>
    #include <deque>
    #include "types.h"
    #include "../../chess/position.h"

    namespace lczero {

    class ChessBoard {
    public:
        ChessBoard();
        ChessBoard(const ChessBoard& other);
        ChessBoard(const std::string& fen) { SetFromFen(fen); }
        ChessBoard& operator=(const ChessBoard& other);

        static const char* kStartposFen;

        void SetFromFen(std::string_view fen, int* rule50_ply = nullptr, int* moves = nullptr);
        void Clear();
        void Mirror() {} // Không cần làm gì vì Stockfish tự động xoay side_to_move khi do_move

        MoveList GenerateLegalMoves() const;
        bool ApplyMove(Move move);
        void UndoMove();
        bool IsUnderCheck() const;

        std::string MoveToString(Move move) const;
        Move ParseMove(std::string_view move_str) const;

        // Trả về thuộc tính side to move để đồng bộ với Lc0
        bool flipped() const { return pos.side_to_move() == Stockfish::BLACK; }
        
        // Hỗ trợ kiểm tra nước đi hợp lệ cực nhanh
        bool IsLegalMove(Move move) const { return pos.pseudo_legal(move) && pos.legal(move); }

        // Các phương thức lấy Hash thế cờ dùng cho Transposition Table trong MCTS
        uint64_t Hash() const { return pos.key(); }
        uint64_t GetHash() const { return Hash(); }

        // Hỗ trợ neural network encoding sau này
        const Stockfish::Position& GetRawPosition() const { return pos; }

    private:
        Stockfish::Position pos;
        std::deque<Stockfish::StateInfo> states; // Dùng deque để đảm bảo con trỏ trỏ vào phần tử không bị mất hiệu lực khi thêm phần tử mới
        const Stockfish::Variant* variant_def = nullptr;
    };

    } // namespace lczero
    ```

### 2.3. [board.cc](file:///d:/chess_variant/custom_engine/src/lczero_chess/chess/board.cc) [NEW]
*   **Nhiệm vụ**: Hiện thực hóa các phương thức của `ChessBoard`.
*   **Mã nguồn phác thảo**:
    ```cpp
    #include "board.h"
    #include "../../chess/variant.h"
    #include "../../chess/parser.h"

    namespace lczero {

    const char* ChessBoard::kStartposFen = "vrhabkberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHABKBERV w - - 7+7 0 1";

    ChessBoard::ChessBoard() {
        variant_def = Stockfish::Variant::find("custom_10x10_variant");
        states.emplace_back();
        pos.set(variant_def, kStartposFen, false, &states.back(), nullptr);
    }

    ChessBoard::ChessBoard(const ChessBoard& other) {
        variant_def = other.variant_def;
        states = other.states; // Copy deque chứa các StateInfo
        // Thiết lập lại con trỏ trạng thái cho Position mới bằng copy_from cực nhanh
        pos.copy_from(other.pos, &states.back());
    }

    ChessBoard& ChessBoard::operator=(const ChessBoard& other) {
        if (this != &other) {
            variant_def = other.variant_def;
            states = other.states;
            pos.copy_from(other.pos, &states.back());
        }
        return *this;
    }

    void ChessBoard::SetFromFen(std::string_view fen, int* rule50_ply, int* moves) {
        states.clear();
        states.emplace_back();
        pos.set(variant_def, std::string(fen), false, &states.back(), nullptr);
        if (rule50_ply) *rule50_ply = pos.rule50_count();
        if (moves) *moves = pos.game_ply();
    }

    void ChessBoard::Clear() {
        states.clear();
        states.emplace_back();
        pos.set(variant_def, "10/10/10/10/10/10/10/10/10/10 w - - 0 1", false, &states.back(), nullptr);
    }

    MoveList ChessBoard::GenerateLegalMoves() const {
        return MoveList(pos);
    }

    bool ChessBoard::ApplyMove(Move move) {
        states.emplace_back();
        // Áp dụng nước đi và cập nhật accumulators
        pos.do_move(move, states.back());
        // Trả về true nếu là nước đi ăn quân hoặc đi tốt để reset luật 50 nước
        return pos.capture(move) || pos.moved_piece(move) == Stockfish::PAWN || pos.moved_piece(move) == variant_def->customPieces[2];
    }

    void ChessBoard::UndoMove() {
        if (states.size() > 1) {
            Move last_move = pos.state()->move;
            pos.undo_move(last_move);
            states.pop_back();
        }
    }

    bool ChessBoard::IsUnderCheck() const {
        return pos.checkers() != 0;
    }

    std::string ChessBoard::MoveToString(Move move) const {
        return Stockfish::UCI::move(move, false);
    }

    Move ChessBoard::ParseMove(std::string_view move_str) const {
        return Stockfish::UCI::to_move(pos, std::string(move_str));
    }

    } // namespace lczero
    ```

### 2.4. [position.h](file:///d:/chess_variant/custom_engine/src/lczero_chess/chess/position.h) [NEW]
*   **Nhiệm vụ**: Khai báo các cấu trúc `Position` và `PositionHistory` của Lc0, hỗ trợ kiểm tra kết thúc game.
*   **Mã nguồn phác thảo**:
    ```cpp
    #pragma once
    #include <vector>
    #include <span>
    #include "board.h"

    namespace lczero {

    enum class GameResult : uint8_t { UNDECIDED, BLACK_WON, DRAW, WHITE_WON };

    class Position {
    public:
        Position() = default;
        Position(const Position& parent, Move m);
        Position(const ChessBoard& board, int rule50_ply, int game_ply);

        static Position FromFen(std::string_view fen);

        bool IsBlackToMove() const { return us_board_.flipped(); }
        int GetGamePly() const { return ply_count_; }
        int GetRule50Ply() const { return rule50_ply_; }
        const ChessBoard& GetBoard() const { return us_board_; }

        // Trả về nước đi cuối cùng dẫn tới thế cờ này
        Move GetLastMove() const { return us_board_.GetRawPosition().state()->move; }

        // Các phương thức lấy Hash dùng cho MCTS Transposition Table
        uint64_t Hash() const { return us_board_.GetRawPosition().key(); }
        uint64_t GetHash() const { return Hash(); }

        // Sinh danh sách nước đi hợp lệ
        MoveList GenerateLegalMoves() const { return us_board_.GenerateLegalMoves(); }

        int GetRepetitions() const { return repetitions_; }
        void SetRepetitions(int repetitions, int cycle_length) {
            repetitions_ = repetitions;
            cycle_length_ = cycle_length;
        }

    private:
        ChessBoard us_board_;
        int rule50_ply_ = 0;
        int repetitions_ = 0;
        int cycle_length_ = 0;
        int ply_count_ = 0;
    };

    class PositionHistory {
    public:
        PositionHistory() = default;
        PositionHistory(std::span<const Position> positions)
            : positions_(positions.begin(), positions.end()) {}

        const Position& Starting() const { return positions_.front(); }
        const Position& Last() const { return positions_.back(); }
        int GetLength() const { return positions_.size(); }

        void Reset(const ChessBoard& board, int rule50_ply, int game_ply);
        void Reset(const Position& pos);
        void Append(Move m);
        void Pop() { positions_.pop_back(); }

        bool IsBlackToMove() const { return Last().IsBlackToMove(); }
        
        // Cực kỳ quan trọng: Định nghĩa luật kết thúc game (Stalemate = Loss, 7-checks)
        GameResult ComputeGameResult() const;
        bool DidRepeatSinceLastZeroingMove() const;

    private:
        int ComputeLastMoveRepetitions(int* cycle_length) const;
        std::vector<Position> positions_;
    };

    } // namespace lczero
    ```

### 2.5. [position.cc](file:///d:/chess_variant/custom_engine/src/lczero_chess/chess/position.cc) [NEW]
*   **Nhiệm vụ**: Triển khai logic tạo Position và xác định kết quả game đặc thù cho biến thể (Stalemate = Loss, 7-checks).
*   **Mã nguồn phác thảo**:
    ```cpp
    #include "position.h"
    #include <algorithm>

    namespace lczero {

    Position::Position(const Position& parent, Move m)
        : rule50_ply_(parent.rule50_ply_ + 1), ply_count_(parent.ply_count_ + 1) {
        us_board_ = parent.us_board_;
        const bool is_zeroing = us_board_.ApplyMove(m);
        us_board_.Mirror(); // Tương thích với interface của Lc0
        if (is_zeroing) rule50_ply_ = 0;
    }

    Position::Position(const ChessBoard& board, int rule50_ply, int game_ply)
        : us_board_(board), rule50_ply_(rule50_ply), repetitions_(0), ply_count_(game_ply) {}

    Position Position::FromFen(std::string_view fen) {
        Position pos;
        pos.us_board_.SetFromFen(fen, &pos.rule50_ply_, &pos.ply_count_);
        return pos;
    }

    void PositionHistory::Reset(const ChessBoard& board, int rule50_ply, int game_ply) {
        positions_.clear();
        positions_.emplace_back(board, rule50_ply, game_ply);
    }

    void PositionHistory::Reset(const Position& pos) {
        positions_.clear();
        positions_.push_back(pos);
    }

    void PositionHistory::Append(Move m) {
        positions_.push_back(Position(Last(), m));
        int cycle_length;
        int repetitions = ComputeLastMoveRepetitions(&cycle_length);
        positions_.back().SetRepetitions(repetitions, cycle_length);
    }

    int PositionHistory::ComputeLastMoveRepetitions(int* cycle_length) const {
        *cycle_length = 0;
        const auto& last = positions_.back();
        if (last.GetRule50Ply() < 4) return 0;
        for (int idx = positions_.size() - 5; idx >= 0; idx -= 2) {
            const auto& pos = positions_[idx];
            // So sánh Zobrist key của Stockfish Position bên dưới, cực kỳ nhanh
            if (pos.GetBoard().GetRawPosition().key() == last.GetBoard().GetRawPosition().key()) {
                *cycle_length = positions_.size() - 1 - idx;
                return 1 + pos.GetRepetitions();
            }
            if (pos.GetRule50Ply() < 2) return 0;
        }
        return 0;
    }

    bool PositionHistory::DidRepeatSinceLastZeroingMove() const {
        for (auto iter = positions_.rbegin(); iter != positions_.rend(); ++iter) {
            if (iter->GetRepetitions() > 0) return true;
            if (iter->GetRule50Ply() == 0) return false;
        }
        return false;
    }

    GameResult PositionHistory::ComputeGameResult() const {
        const auto& board = Last().GetBoard();
        const auto& raw_pos = board.GetRawPosition();
        
        // 1. Kiểm tra giới hạn 7-checks (Check Counting)
        // Lấy số check còn lại của 2 bên. MCTS Side to Move chuẩn hóa nên ta kiểm tra trực tiếp
        if (raw_pos.checks_remaining(Stockfish::WHITE) <= 0) {
            return GameResult::BLACK_WON; // Trắng hết lượt chiếu -> Đen thắng
        }
        if (raw_pos.checks_remaining(Stockfish::BLACK) <= 0) {
            return GameResult::WHITE_WON; // Đen hết lượt chiếu -> Trắng thắng
        }

        // 2. Sinh các nước đi hợp lệ
        auto legal_moves = board.GenerateLegalMoves();
        if (legal_moves.empty()) {
            if (board.IsUnderCheck()) {
                // Chiếu hết
                return IsBlackToMove() ? GameResult::WHITE_WON : GameResult::BLACK_WON;
            }
            // Hết nước đi hợp lệ nhưng không bị chiếu -> Stalemate
            // Biến thể quy định Stalemate = LOSS (Bên bị stalemate thua cuộc)
            return IsBlackToMove() ? GameResult::WHITE_WON : GameResult::BLACK_WON;
        }

        // 3. Luật 50 nước đi (tương đương 100 ply không đi tốt/ăn quân)
        if (Last().GetRule50Ply() >= 100) return GameResult::DRAW;

        // 4. Lặp lại thế cờ (Repetitions)
        if (Last().GetRepetitions() >= 2) return GameResult::DRAW;

        return GameResult::UNDECIDED;
    }

    } // namespace lczero
    ```

### 2.6. [gamestate.h](file:///d:/chess_variant/custom_engine/src/lczero_chess/chess/gamestate.h) [NEW]
*   **Nhiệm vụ**: Khai báo cấu trúc `GameState` dùng để khởi dựng cây MCTS.
*   **Mã nguồn phác thảo**:
    ```cpp
    #pragma once
    #include <vector>
    #include <numeric>
    #include <algorithm>
    #include "position.h"

    namespace lczero {

    struct GameState {
        Position startpos;
        std::vector<Move> moves;

        Position CurrentPosition() const {
            return std::accumulate(
                moves.begin(), moves.end(), startpos,
                [](const Position& pos, Move m) { return Position(pos, m); });
        }

        std::vector<Position> GetPositions() const {
            std::vector<Position> positions;
            positions.reserve(moves.size() + 1);
            positions.push_back(startpos);
            std::transform(moves.begin(), moves.end(), std::back_inserter(positions),
                           [&](Move m) {
                               return Position(positions.back(), m);
                           });
            return positions;
        }
    };

    } // namespace lczero
    ```

---

## 3. Cập nhật hệ thống Build ([meson.build](file:///d:/chess_variant/custom_engine/meson.build))

Để biên dịch các tệp tin cầu nối này và cho phép các tệp MCTS bao gồm chúng dễ dàng:
1.  Bổ sung thư mục `src/lczero_chess` vào include path của Meson:
    ```python
    inc_dirs = include_directories(
      'src',
      'src/chess',
      'src/chess/nnue',
      'src/chess/syzygy',
      'src/lczero_chess' # Thư mục chứa cầu nối
    )
    ```
2.  Bổ sung tệp `board.cc` và `position.cc` của lớp cầu nối vào danh sách nguồn biên dịch:
    ```python
    bridge_sources = files(
      'src/lczero_chess/chess/board.cc',
      'src/lczero_chess/chess/position.cc'
    )
    ```
3.  Cập nhật cấu hình build để biên dịch file exe chứa cả `bridge_sources`.

---

## 4. Kế hoạch Kiểm thử và Xác nhận (Giai đoạn 3)

Chúng ta sẽ tạo cờ lệnh `--test-board` trong [main.cc](file:///d:/chess_variant/custom_engine/src/main.cc) để chạy kiểm thử độc lập cho lớp cầu nối này trước khi kéo MCTS về. Bộ kiểm thử sẽ chạy các nội dung sau:

1.  **Khởi tạo từ FEN mặc định**: Xác nhận thế cờ bắt đầu tải thành công và đếm đúng 34 nước đi hợp lệ đầu tiên.
2.  **Đi thử nước đi & khôi phục (Apply/Undo)**: Thử đi nước đi và gọi `UndoMove()`, kiểm tra xem FEN có khôi phục chính xác 100% không để xác nhận bộ nhớ `StateInfo` được quản lý ổn định.
3.  **Xác nhận Stalemate = Loss**: Tải một FEN thế cờ stalemate nhân tạo, gọi `ComputeGameResult()` và kiểm tra xem nó có trả về đúng kết quả Thua cuộc (Won/Lost) thay vì Hòa (Draw) hay không.
4.  **Xác nhận 7-checks**: Giả lập đi thử các nước chiếu liên tiếp để kiểm tra xem khi đếm lượt chiếu giảm về 0 thì game có kết thúc ngay lập tức hay không.
