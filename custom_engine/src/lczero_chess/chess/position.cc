#include "position.h"
#include <algorithm>
#include <iostream>

namespace lczero {

void Position::CopyFrom(const Position& other, Stockfish::StateInfo* external_state) {
    us_board_.CopyFrom(other.us_board_, external_state);
    rule50_ply_ = other.rule50_ply_;
    repetitions_ = other.repetitions_;
    ply_count_ = other.ply_count_;
    plies_since_prev_repetition_ = other.plies_since_prev_repetition_;
}

void Position::DoMove(Move m, Stockfish::StateInfo* external_state) {
    const bool is_zeroing = us_board_.ApplyMove(m, external_state);
    rule50_ply_ = is_zeroing ? 0 : rule50_ply_ + 1;
    ply_count_++;
}

void Position::UndoMove(int rule50_ply, int repetitions) {
    us_board_.UndoMove();
    rule50_ply_ = rule50_ply;
    repetitions_ = repetitions;
    ply_count_--;
}

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
        last_position_ = starting_position_;
        for (size_t i = 1; i < positions.size(); ++i) {
            Append(positions[i].GetLastMove());
        }
    }
}

PositionHistory::PositionHistory(const PositionHistory& other) {
    starting_position_ = other.starting_position_;
    history_size_ = other.history_size_;
    std::copy_n(other.history_.begin(), history_size_, history_.begin());
    
    if (history_size_ > 0) {
        std::copy_n(other.mcts_states_.begin(), history_size_, mcts_states_.begin());
        last_position_.CopyFrom(other.last_position_, &mcts_states_[history_size_ - 1]);
        mcts_states_[0].previous = const_cast<Stockfish::StateInfo*>(starting_position_.GetBoard().GetRawPosition().state());
        for (size_t i = 1; i < history_size_; ++i) {
            mcts_states_[i].previous = &mcts_states_[i - 1];
        }
    } else {
        last_position_ = other.last_position_;
    }
}

PositionHistory& PositionHistory::operator=(const PositionHistory& other) {
    if (this != &other) {
        starting_position_ = other.starting_position_;
        history_size_ = other.history_size_;
        std::copy_n(other.history_.begin(), history_size_, history_.begin());
        
        if (history_size_ > 0) {
            std::copy_n(other.mcts_states_.begin(), history_size_, mcts_states_.begin());
            last_position_.CopyFrom(other.last_position_, &mcts_states_[history_size_ - 1]);
            mcts_states_[0].previous = const_cast<Stockfish::StateInfo*>(starting_position_.GetBoard().GetRawPosition().state());
            for (size_t i = 1; i < history_size_; ++i) {
                mcts_states_[i].previous = &mcts_states_[i - 1];
            }
        } else {
            last_position_ = other.last_position_;
        }
    }
    return *this;
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
    if (history_size_ < history_.size()) {
        const auto& raw_board = last_position_.GetBoard().GetRawPosition();
        std::array<uint8_t, 120> board_state;
        for (int s = 0; s < 120; ++s) {
            board_state[s] = static_cast<uint8_t>(raw_board.piece_on(Stockfish::Square(s)));
        }
        history_[history_size_] = {
            last_position_.Hash(),
            last_position_.GetRule50Ply(),
            last_position_.GetRepetitions(),
            m,
            board_state,
            last_position_.IsBlackToMove()
        };
        
        last_position_.DoMove(m, &mcts_states_[history_size_]);
        history_size_++;
    } else {
        last_position_.DoMove(m, nullptr);
    }
    
    int plies_since_prev = 10000;
    int repetitions = ComputeLastMoveRepetitions(plies_since_prev);
    last_position_.SetRepetitions(repetitions);
    last_position_.SetPliesSincePrevRepetition(plies_since_prev);
}

int PositionHistory::ComputeLastMoveRepetitions(int& plies_since_prev) const {
    const auto& last = last_position_;
    plies_since_prev = 10000;
    if (last.GetRule50Ply() < 4) return 0;
    
    int size = (int)history_size_;
    // Duyệt ngược lịch sử nén siêu nhanh
    for (int idx = size - 4; idx >= 0; idx -= 2) {
        const auto& pos = history_[idx];
        if (pos.hash == last.Hash()) {
            plies_since_prev = size - idx;
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

GameResult PositionHistory::ComputeMctsResult(const MoveList& legal_moves) const {
    const auto& board = Last().GetBoard();
    const auto& raw_pos = board.GetRawPosition();
    
    // 1. Luật 7-checks (Kiểm tra O(1) siêu nhanh)
    if (raw_pos.checks_remaining(Stockfish::WHITE) <= 0) {
        // Trắng thắng. Nếu Đen chuẩn bị đi (Trắng vừa đi) -> Trắng thắng là WHITE_WON đối với MCTS
        return board.flipped() ? GameResult::WHITE_WON : GameResult::BLACK_WON;
    }
    if (raw_pos.checks_remaining(Stockfish::BLACK) <= 0) {
        // Đen thắng. Nếu Đen chuẩn bị đi (Trắng vừa đi) -> Đen thắng là BLACK_WON đối với MCTS
        return board.flipped() ? GameResult::BLACK_WON : GameResult::WHITE_WON;
    }

    // 2. Luật kết thúc do hết nước đi (Checkmate hoặc Stalemate)
    if (legal_moves.empty()) {
        // Cả Checkmate và Stalemate đều dẫn đến bên bị Stalemate/Checkmate thua (to_move thua),
        // tức là bên vừa đi thắng -> Trả về GameResult::WHITE_WON
        return GameResult::WHITE_WON;
    }

    return GameResult::UNDECIDED;
}

void PositionHistory::Trim(size_t size) {
    while (GetLength() > size) {
        Pop();
    }
}

void PositionHistory::Pop() {
    if (history_size_ > 0) {
        --history_size_;
        const auto& prev = history_[history_size_];
        last_position_.UndoMove(prev.rule50_ply, prev.repetitions);
    }
}

} // namespace lczero
