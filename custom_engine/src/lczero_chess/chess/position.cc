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
    history_size_ = 0;
    if (!positions.empty()) {
        starting_position_ = positions.front();
        last_position_ = positions.back();
        size_t limit = std::min(positions.size() - 1, history_.size());
        for (size_t i = 0; i < limit; ++i) {
            history_[history_size_++] = {
                positions[i].Hash(),
                positions[i].GetRule50Ply(),
                positions[i].GetRepetitions(),
                positions[i + 1].GetLastMove()
            };
        }
    }
}

void PositionHistory::Reset(const ChessBoard& board, int rule50_ply, int game_ply) {
    starting_position_ = Position(board, rule50_ply, game_ply);
    last_position_ = starting_position_;
    history_size_ = 0;
}

void PositionHistory::Reset(const Position& pos) {
    starting_position_ = pos;
    last_position_ = pos;
    history_size_ = 0;
}

void PositionHistory::Append(Move m) {
    // Lưu trạng thái trước nước đi và nước đi chuẩn bị thực hiện
    if (history_size_ < history_.size()) {
        history_[history_size_++] = {
            last_position_.Hash(),
            last_position_.GetRule50Ply(),
            last_position_.GetRepetitions(),
            m
        };
    }
    
    // Thực hiện nước đi m
    last_position_ = Position(last_position_, m);
    
    int repetitions = ComputeLastMoveRepetitions();
    last_position_.SetRepetitions(repetitions);
}

int PositionHistory::ComputeLastMoveRepetitions() const {
    const auto& last = last_position_;
    if (last.GetRule50Ply() < 4) return 0;
    
    int size = (int)history_size_;
    // Duyệt ngược lịch sử nén siêu nhanh
    for (int idx = size - 4; idx >= 0; idx -= 2) {
        const auto& pos = history_[idx];
        if (pos.hash == last.Hash()) {
            return 1 + pos.repetitions;
        }
        if (pos.rule50_ply < 2) return 0;
    }
    return 0;
}

bool PositionHistory::DidRepeatSinceLastZeroingMove() const {
    if (last_position_.GetRepetitions() > 0) return true;
    for (int i = (int)history_size_ - 1; i >= 0; --i) {
        if (history_[i].repetitions > 0) return true;
        if (history_[i].rule50_ply == 0) return false;
    }
    return false;
}

GameResult PositionHistory::ComputeGameResult() const {
    const auto& board = Last().GetBoard();
    const auto& raw_pos = board.GetRawPosition();
    
    // 1. Kiểm tra giới hạn 7-checks (O(1))
    // checks_remaining(color) là số lần chiếu MÀ color cần thực hiện để chiến thắng.
    // Nếu <= 0, color ĐÃ CHIẾU đủ 7 lần và chiến thắng!
    if (raw_pos.checks_remaining(Stockfish::WHITE) <= 0) {
        return GameResult::WHITE_WON; // Trắng đã chiếu đủ 7 lần -> Trắng thắng
    }
    if (raw_pos.checks_remaining(Stockfish::BLACK) <= 0) {
        return GameResult::BLACK_WON; // Đen đã chiếu đủ 7 lần -> Đen thắng
    }

    // 2. Luật 50 nước đi (100 plies) (O(1))
    if (Last().GetRule50Ply() >= 100) {
        return GameResult::DRAW;
    }

    // 3. Luật lặp thế cờ (3-fold repetition, repetitions >= 2) (O(1))
    if (Last().GetRepetitions() >= 2) {
        return GameResult::DRAW;
    }

    // 4. Kiểm tra nước đi hợp lệ (Chỉ chạy O(n) movegen khi thực sự cần thiết)
    auto legal_moves = board.GenerateLegalMoves();
    if (legal_moves.empty()) {
        if (board.IsUnderCheck()) {
            // Chiếu hết
            return IsBlackToMove() ? GameResult::WHITE_WON : GameResult::BLACK_WON;
        }
        // Stalemate = LOSS (Bên bị stalemate thua)
        return IsBlackToMove() ? GameResult::WHITE_WON : GameResult::BLACK_WON;
    }

    return GameResult::UNDECIDED;
}

std::vector<Position> PositionHistory::GetPositions() const {
    std::vector<Position> result;
    result.reserve(history_size_ + 1);
    result.push_back(starting_position_);
    for (size_t i = 0; i < history_size_; ++i) {
        result.push_back(Position(result.back(), history_[i].move));
    }
    return result;
}

void PositionHistory::Trim(size_t size) {
    if (size > 0 && size <= history_size_ + 1) {
        history_size_ = size - 1;
        last_position_ = starting_position_;
        for (size_t i = 0; i < history_size_; ++i) {
            last_position_ = Position(last_position_, history_[i].move);
        }
    }
}

void PositionHistory::Pop() {
    if (history_size_ > 0) {
        --history_size_;
        last_position_ = starting_position_;
        for (size_t i = 0; i < history_size_; ++i) {
            last_position_ = Position(last_position_, history_[i].move);
        }
    }
}

} // namespace lczero
