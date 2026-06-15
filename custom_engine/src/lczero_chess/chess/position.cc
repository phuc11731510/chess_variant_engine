#include "position.h"
#include <algorithm>
#include <iostream>

namespace lczero {

Position::Position(const Position& parent, Move m)
    : rule50_ply_(parent.rule50_ply_ + 1), ply_count_(parent.ply_count_ + 1) {
    us_board_ = parent.us_board_;
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
    int cycle_length = 0;
    int repetitions = ComputeLastMoveRepetitions(&cycle_length);
    positions_.back().SetRepetitions(repetitions, cycle_length);
}

int PositionHistory::ComputeLastMoveRepetitions(int* cycle_length) const {
    *cycle_length = 0;
    const auto& last = positions_.back();
    if (last.GetRule50Ply() < 4) return 0;
    for (int idx = (int)positions_.size() - 5; idx >= 0; idx -= 2) {
        const auto& pos = positions_[idx];
        if (pos.GetBoard().GetRawPosition().key() == last.GetBoard().GetRawPosition().key()) {
            *cycle_length = (int)positions_.size() - 1 - idx;
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
    
    // 1. Check limit checks (7-checks)
    if (raw_pos.checks_remaining(Stockfish::WHITE) <= 0) {
        return GameResult::BLACK_WON; // White ran out of checks -> Black wins
    }
    if (raw_pos.checks_remaining(Stockfish::BLACK) <= 0) {
        return GameResult::WHITE_WON; // Black ran out of checks -> White wins
    }

    // 2. Check legal moves
    auto legal_moves = board.GenerateLegalMoves();
    if (legal_moves.empty()) {
        if (board.IsUnderCheck()) {
            // Checkmate
            return IsBlackToMove() ? GameResult::WHITE_WON : GameResult::BLACK_WON;
        }
        // Stalemate: In our variant, stalemate = LOSS
        // The side who is in stalemate (whose turn it is but has no legal moves) loses the game.
        return IsBlackToMove() ? GameResult::WHITE_WON : GameResult::BLACK_WON;
    }

    // 3. Rule 50 moves (100 plies without pawn move or capture)
    if (Last().GetRule50Ply() >= 100) {
        return GameResult::DRAW;
    }

    // 4. Repetitions (3-fold repetition, repetitions_ >= 2)
    if (Last().GetRepetitions() >= 2) {
        return GameResult::DRAW;
    }

    return GameResult::UNDECIDED;
}

} // namespace lczero
