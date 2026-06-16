#pragma once
#include <cstdint>
#include <initializer_list>
#include "../../chess/types.h"
#include "../../chess/movegen.h"
#include "../../chess/uci.h"
#include "../../chess/variant.h"

namespace lczero {

class Move {
public:
    constexpr Move() : m_(Stockfish::MOVE_NONE) {}
    constexpr Move(Stockfish::Move m) : m_(m) {}
    
    // Implicit conversion to Stockfish::Move
    constexpr operator Stockfish::Move() const { return m_; }
    
    bool operator==(const Move& other) const { return m_ == other.m_; }
    bool operator!=(const Move& other) const { return m_ != other.m_; }
    
    void Flip(Stockfish::Rank max_rank = Stockfish::RANK_10) {
        if (m_ == Stockfish::MOVE_NONE || m_ == Stockfish::MOVE_NULL) return;
        Stockfish::Square from = Stockfish::from_sq(m_);
        Stockfish::Square to = Stockfish::to_sq(m_);
        Stockfish::MoveType mt = Stockfish::type_of(m_);
        Stockfish::PieceType pt = Stockfish::promotion_type(m_);
        
        auto flip_sq = [max_rank](Stockfish::Square s) {
            return Stockfish::flip_rank(s, max_rank);
        };
        
        if (from != Stockfish::SQ_NONE) from = flip_sq(from);
        if (to != Stockfish::SQ_NONE) to = flip_sq(to);
        
        if (mt == Stockfish::NORMAL) {
            if (Stockfish::is_gating(m_)) {
                m_ = Stockfish::make_gating<Stockfish::NORMAL>(
                    from, to, Stockfish::gating_type(m_), flip_sq(Stockfish::gating_square(m_)));
            } else {
                m_ = Stockfish::make_move(from, to);
            }
        } else if (mt == Stockfish::PROMOTION) {
            m_ = Stockfish::make<Stockfish::PROMOTION>(from, to, pt);
        } else if (mt == Stockfish::EN_PASSANT) {
            m_ = Stockfish::make<Stockfish::EN_PASSANT>(from, to);
        } else if (mt == Stockfish::CASTLING) {
            if (Stockfish::is_gating(m_)) {
                m_ = Stockfish::make_gating<Stockfish::CASTLING>(
                    from, to, Stockfish::gating_type(m_), flip_sq(Stockfish::gating_square(m_)));
            } else {
                m_ = Stockfish::make<Stockfish::CASTLING>(from, to);
            }
        } else if (mt == Stockfish::DROP) {
            m_ = Stockfish::make_drop(to, Stockfish::in_hand_piece_type(m_), Stockfish::dropped_piece_type(m_));
        } else {
            m_ = Stockfish::make_move(from, to);
        }
    }
    
    std::string ToString(bool is_chess960 = false) const {
        if (m_ == Stockfish::MOVE_NONE) return "0000";
        if (m_ == Stockfish::MOVE_NULL) return "0000";
        
        Stockfish::Square from = Stockfish::from_sq(m_);
        Stockfish::Square to = Stockfish::to_sq(m_);
        
        auto sq_to_string = [](Stockfish::Square sq) {
            int f = Stockfish::file_of(sq);
            int r = Stockfish::rank_of(sq);
            char file_c = 'a' + f;
            std::string rank_s = std::to_string(r + 1);
            return file_c + rank_s;
        };
        
        std::string s = sq_to_string(from) + sq_to_string(to);
        
        if (Stockfish::type_of(m_) == Stockfish::PROMOTION) {
            Stockfish::PieceType pt = Stockfish::promotion_type(m_);
            char pt_c = ' ';
            if (pt == Stockfish::KNIGHT) pt_c = 'n';
            else if (pt == Stockfish::BISHOP) pt_c = 'b';
            else if (pt == Stockfish::ROOK) pt_c = 'r';
            else if (pt == Stockfish::QUEEN) pt_c = 'q';
            if (pt_c != ' ') s += pt_c;
        }
        return s;
    }
    
    bool is_null() const { return m_ == Stockfish::MOVE_NONE || m_ == Stockfish::MOVE_NULL; }
    Stockfish::Move raw() const { return m_; }

private:
    Stockfish::Move m_;
};

using Square = Stockfish::Square;

constexpr Move MOVE_NONE = Move(Stockfish::MOVE_NONE);
constexpr Move MOVE_NULL = Move(Stockfish::MOVE_NULL);

class MoveList {
public:
    using value_type = Move;
    using iterator = Move*;
    using const_iterator = const Move*;
    using reference = Move&;
    using const_reference = const Move&;

    MoveList() = default;

    MoveList(std::initializer_list<Move> init) {
        for (const auto& m : init) {
            push_back(m);
        }
    }

    void push_back(const Move& m) {
        if (size_ < 384) {
            moves_[size_++] = m;
        }
    }

    template<typename... Args>
    void emplace_back(Args&&... args) {
        if (size_ < 384) {
            moves_[size_++] = Move(std::forward<Args>(args)...);
        }
    }

    void reserve(size_t) {}
    void resize(size_t new_size) {
        if (new_size <= 384) {
            size_ = new_size;
        }
    }

    void clear() { size_ = 0; }
    size_t size() const { return size_; }
    bool empty() const { return size_ == 0; }

    const Move& operator[](size_t idx) const { return moves_[idx]; }
    Move& operator[](size_t idx) { return moves_[idx]; }

    const Move& at(size_t idx) const { return moves_[idx]; }
    Move& at(size_t idx) { return moves_[idx]; }

    iterator begin() { return moves_; }
    const_iterator begin() const { return moves_; }
    iterator end() { return moves_ + size_; }
    const_iterator end() const { return moves_ + size_; }

    const Move& front() const { return moves_[0]; }
    Move& front() { return moves_[0]; }
    const Move& back() const { return moves_[size_ - 1]; }
    Move& back() { return moves_[size_ - 1]; }

    const Move* data() const { return moves_; }
    Move* data() { return moves_; }

private:
    Move moves_[384];
    size_t size_ = 0;
};

} // namespace lczero
