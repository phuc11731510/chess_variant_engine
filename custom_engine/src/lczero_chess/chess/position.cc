#include "position.h"
#include <algorithm>
#include <iostream>

namespace lczero {

Position::Position(const Position& parent, Move m)
    : us_board_(parent.us_board_),
      rule50_ply_(parent.rule50_ply_ + 1),
      ply_count_(parent.ply_count_ + 1) {
    const bool is_zeroing = us_board_.ApplyMove(m);
    if (is_zeroing) rule50_ply_ = 0;
}

Position::Position(const ChessBoard& board, int rule50_ply, int game_ply)
    : us_board_(board), rule50_ply_(rule50_ply), repetitions_(0), ply_count_(game_ply) {}

Position Position::FromFen(std::string_view fen) {
    Position pos;
    pos.us_board_.SetFromFen(fen, &pos.rule50_ply_, &pos.ply_count_);
    return pos;
}

PositionHistory::PositionHistory(std::span<const Position> positions) {
    if (!positions.empty()) {
        starting_position_ = positions.front();
        last_position_ = positions.back();
        history_.reserve(positions.size() - 1);
        for (size_t i = 0; i < positions.size() - 1; ++i) {
            history_.push_back({
                positions[i].Hash(),
                positions[i].GetRule50Ply(),
                positions[i].GetRepetitions(),
                positions[i + 1].GetLastMove()
            });
        }
    }
}

void PositionHistory::Reset(const ChessBoard& board, int rule50_ply, int game_ply) {
    starting_position_ = Position(board, rule50_ply, game_ply);
    last_position_ = starting_position_;
    history_.clear();
}

void PositionHistory::Reset(const Position& pos) {
    starting_position_ = pos;
    last_position_ = pos;
    history_.clear();
}

void PositionHistory::Append(Move m) {
    // Lưu trạng thái trước nước đi và nước đi chuẩn bị thực hiện
    history_.push_back({
        last_position_.Hash(),
        last_position_.GetRule50Ply(),
        last_position_.GetRepetitions(),
        m
    });
    
    // Thực hiện nước đi m
    last_position_ = Position(last_position_, m);
    
    int cycle_length = 0;
    int repetitions = ComputeLastMoveRepetitions(&cycle_length);
    last_position_.SetRepetitions(repetitions, cycle_length);
}

// MCTS WARNING: Pop() is O(n) due to replay. Avoid using this in performance-critical paths.
// In MCTS, copy-on-apply should be used instead of pop/undo.
void PositionHistory::Pop() {
    if (!history_.empty()) {
        history_.pop_back();
        // Tái dựng lại trạng thái của last_position_ từ starting_position_
        last_position_ = starting_position_;
        for (const auto& entry : history_) {
            last_position_ = Position(last_position_, entry.move);
        }
    }
}

int PositionHistory::ComputeLastMoveRepetitions(int* cycle_length) const {
    *cycle_length = 0;
    const auto& last = last_position_;
    if (last.GetRule50Ply() < 4) return 0;
    
    int size = (int)history_.size();
    // Duyệt ngược lịch sử nén siêu nhanh
    for (int idx = size - 4; idx >= 0; idx -= 2) {
        const auto& pos = history_[idx];
        if (pos.hash == last.Hash()) {
            *cycle_length = size - idx;
            return 1 + pos.repetitions;
        }
        if (pos.rule50_ply < 2) return 0;
    }
    return 0;
}

bool PositionHistory::DidRepeatSinceLastZeroingMove() const {
    if (last_position_.GetRepetitions() > 0) return true;
    for (auto iter = history_.rbegin(); iter != history_.rend(); ++iter) {
        if (iter->repetitions > 0) return true;
        if (iter->rule50_ply == 0) return false;
    }
    return false;
}

GameResult PositionHistory::ComputeGameResult() const {
    const auto& board = Last().GetBoard();
    const auto& raw_pos = board.GetRawPosition();
    
    // 1. Kiểm tra giới hạn 7-checks
    if (raw_pos.checks_remaining(Stockfish::WHITE) <= 0) {
        return GameResult::BLACK_WON; // Trắng hết lượt chiếu -> Đen thắng
    }
    if (raw_pos.checks_remaining(Stockfish::BLACK) <= 0) {
        return GameResult::WHITE_WON; // Đen hết lượt chiếu -> Trắng thắng
    }

    // 2. Kiểm tra nước đi hợp lệ
    auto legal_moves = board.GenerateLegalMoves();
    if (legal_moves.empty()) {
        if (board.IsUnderCheck()) {
            // Chiếu hết
            return IsBlackToMove() ? GameResult::WHITE_WON : GameResult::BLACK_WON;
        }
        // Stalemate = LOSS (Bên bị stalemate thua)
        return IsBlackToMove() ? GameResult::WHITE_WON : GameResult::BLACK_WON;
    }

    // 3. Luật 50 nước đi (100 plies)
    if (Last().GetRule50Ply() >= 100) {
        return GameResult::DRAW;
    }

    // 4. Luật lặp thế cờ (3-fold repetition, repetitions >= 2)
    if (Last().GetRepetitions() >= 2) {
        return GameResult::DRAW;
    }

    return GameResult::UNDECIDED;
}

} // namespace lczero
