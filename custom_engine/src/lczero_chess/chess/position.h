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
