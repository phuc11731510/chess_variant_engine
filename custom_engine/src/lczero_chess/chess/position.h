#pragma once
#include <vector>
#include <span>
#include "board.h"

namespace lczero {

enum class GameResult : uint8_t { UNDECIDED, BLACK_WON, DRAW, WHITE_WON };

inline GameResult operator-(GameResult r) {
    if (r == GameResult::WHITE_WON) return GameResult::BLACK_WON;
    if (r == GameResult::BLACK_WON) return GameResult::WHITE_WON;
    return r;
}

struct LightweightPosition {
    uint64_t hash;
    int rule50_ply;
    int repetitions;
    Move move; // Lưu nước đi dẫn tới vị trí tiếp theo
    std::array<uint8_t, 120> board; // Quân cờ của vị trí trước đó (120 bytes)
    bool flipped; // side_to_move có phải là Black không
};

class Position {
public:
    Position() = default;
    Position(const Position& parent, Move m);
    Position(const ChessBoard& board, int rule50_ply, int game_ply);

    void CopyFrom(const Position& other, Stockfish::StateInfo* external_state = nullptr);
    void DoMove(Move m, Stockfish::StateInfo* external_state = nullptr);
    void UndoMove(int rule50_ply, int repetitions);

    static Position FromFen(std::string_view fen);

    bool IsBlackToMove() const { return us_board_.flipped(); }
    int GetGamePly() const { return ply_count_; }
    int GetRule50Ply() const { return rule50_ply_; }
    const ChessBoard& GetBoard() const { return us_board_; }

    Move GetLastMove() const { return us_board_.GetRawPosition().state()->move; }

    uint64_t Hash() const { return us_board_.GetRawPosition().key(); }
    uint64_t GetHash() const { return Hash(); }

    MoveList GenerateLegalMoves() const { return us_board_.GenerateLegalMoves(); }
    int GetPliesSincePrevRepetition() const { return plies_since_prev_repetition_; }
    void SetPliesSincePrevRepetition(int plies) { plies_since_prev_repetition_ = plies; }

    int GetRepetitions() const { return repetitions_; }
    void SetRepetitions(int repetitions) {
        repetitions_ = repetitions;
    }

    bool operator==(const Position& other) const { return Hash() == other.Hash(); }
    bool operator!=(const Position& other) const { return Hash() != other.Hash(); }

private:
    ChessBoard us_board_;
    int rule50_ply_ = 0;
    int repetitions_ = 0;
    int ply_count_ = 0;
    int plies_since_prev_repetition_ = 10000;
};

#include <array>

class PositionHistory {
public:
    PositionHistory() = default;
    PositionHistory(std::span<const Position> positions);
    
    // Custom copy constructor and copy assignment to optimize MCTS hot path
    PositionHistory(const PositionHistory& other);
    PositionHistory& operator=(const PositionHistory& other);

    const Position& Last() const { return last_position_; }
    const Position& Starting() const { return starting_position_; }
    int GetLength() const { return history_size_ + 1; }
    void Reserve(size_t) {}
    
    std::span<const LightweightPosition> GetPositions() const {
        return std::span<const LightweightPosition>(history_.data(), history_size_);
    }
    void Trim(size_t size);
    void Pop();

    void Reset(const ChessBoard& board, int rule50_ply, int game_ply);
    void Reset(const Position& pos);
    void Append(Move m);

    bool IsBlackToMove() const { return last_position_.IsBlackToMove(); }
    
    GameResult ComputeGameResult() const;
    GameResult ComputeMctsResult(const MoveList& legal_moves) const;
    bool DidRepeatSinceLastZeroingMove() const;

private:
    int ComputeLastMoveRepetitions(int& plies_since_prev) const;
    
    Position starting_position_;
    Position last_position_;
    std::array<LightweightPosition, 256> history_; // Mảng tĩnh tránh heap allocation
    std::array<Stockfish::StateInfo, 256> mcts_states_; // Stack lưu StateInfo dùng riêng cho MCTS
    size_t history_size_ = 0;
};

} // namespace lczero
