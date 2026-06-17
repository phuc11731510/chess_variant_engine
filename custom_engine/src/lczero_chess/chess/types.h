#pragma once
#include <cstdint>
#include <initializer_list>
#include "../../chess/types.h"
#include "../../chess/movegen.h"
#include "../../chess/uci.h"
#include "../../chess/variant.h"

namespace lczero {

struct FlipSquareLUT {
    Stockfish::Square lut[Stockfish::RANK_NB][Stockfish::SQUARE_NB + 1];
    constexpr FlipSquareLUT() : lut{} {
        for (int r = 0; r < Stockfish::RANK_NB; ++r) {
            for (int s = 0; s < Stockfish::SQUARE_NB; ++s) {
                int f = s % 12;
                int rank_val = s / 12;
                lut[r][s] = Stockfish::Square((r - rank_val) * 12 + f);
            }
            lut[r][Stockfish::SQUARE_NB] = Stockfish::SQ_NONE;
        }
    }
};
inline constexpr FlipSquareLUT flip_square_lut;

struct FlipFromToLUT {
    uint16_t lut[Stockfish::RANK_NB][16384];
    constexpr FlipFromToLUT() : lut{} {
        for (int r = 0; r < Stockfish::RANK_NB; ++r) {
            for (int from_to = 0; from_to < 16384; ++from_to) {
                int from = (from_to >> 7) & 127;
                int to = from_to & 127;
                
                int from_flipped = from;
                int to_flipped = to;
                
                if (from < Stockfish::SQUARE_NB) {
                    int f = from % 12;
                    int rank_val = from / 12;
                    from_flipped = (r - rank_val) * 12 + f;
                } else if (from == Stockfish::SQUARE_NB) {
                    from_flipped = Stockfish::SQ_NONE;
                }
                
                if (to < Stockfish::SQUARE_NB) {
                    int f = to % 12;
                    int rank_val = to / 12;
                    to_flipped = (r - rank_val) * 12 + f;
                } else if (to == Stockfish::SQUARE_NB) {
                    to_flipped = Stockfish::SQ_NONE;
                }
                
                lut[r][from_to] = (from_flipped << 7) | to_flipped;
            }
        }
    }
};
inline constexpr FlipFromToLUT flip_from_to_lut;

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
        
        uint32_t from_to = m_ & 0x3FFF;
        uint32_t from_to_flipped = flip_from_to_lut.lut[max_rank][from_to];
        
        uint32_t mt = m_ & (15 << 14);
        uint32_t is_drop = (mt == Stockfish::DROP) ? 1 : 0;
        uint32_t mask = 0x3FFF ^ (is_drop * (0x3FFF ^ 0x7F));
        
        uint32_t is_gate = Stockfish::is_gating(m_) ? 1 : 0;
        uint32_t gate_old = (m_ >> 24) & 127;
        uint32_t gate_flipped = flip_square_lut.lut[max_rank][gate_old];
        uint32_t gate_new = is_gate ? gate_flipped : gate_old;
        
        uint32_t preserved_bits = is_drop ? (m_ & (0x7F << 7)) : 0;
        
        m_ = Stockfish::Move((m_ & ~0x7F003FFF) | (gate_new << 24) | (from_to_flipped & mask) | preserved_bits);
    }
    
    std::string ToString(bool is_chess960 = false) const {
        if (m_ == Stockfish::MOVE_NONE) return "0000";
        if (m_ == Stockfish::MOVE_NULL) return "0000";
        
        Stockfish::Square from = Stockfish::from_sq(m_);
        Stockfish::Square to = Stockfish::to_sq(m_);
        
        auto get_sq_str = [](Stockfish::Square sq) -> const char* {
            static const char* str_lut[10][10] = {
                {"a1", "b1", "c1", "d1", "e1", "f1", "g1", "h1", "i1", "j1"},
                {"a2", "b2", "c2", "d2", "e2", "f2", "g2", "h2", "i2", "j2"},
                {"a3", "b3", "c3", "d3", "e3", "f3", "g3", "h3", "i3", "j3"},
                {"a4", "b4", "c4", "d4", "e4", "f4", "g4", "h4", "i4", "j4"},
                {"a5", "b5", "c5", "d5", "e5", "f5", "g5", "h5", "i5", "j5"},
                {"a6", "b6", "c6", "d6", "e6", "f6", "g6", "h6", "i6", "j6"},
                {"a7", "b7", "c7", "d7", "e7", "f7", "g7", "h7", "i7", "j7"},
                {"a8", "b8", "c8", "d8", "e8", "f8", "g8", "h8", "i8", "j8"},
                {"a9", "b9", "c9", "d9", "e9", "f9", "g9", "h9", "i9", "j9"},
                {"a10", "b10", "c10", "d10", "e10", "f10", "g10", "h10", "i10", "j10"}
            };
            int f = Stockfish::file_of(sq);
            int r = Stockfish::rank_of(sq);
            if (f >= 0 && f < 10 && r >= 0 && r < 10) return str_lut[r][f];
            return "??";
        };
        
        std::string s = std::string(get_sq_str(from)) + get_sq_str(to);
        
        if (Stockfish::type_of(m_) == Stockfish::PROMOTION) {
            Stockfish::PieceType pt = Stockfish::promotion_type(m_);
            char pt_c = ' ';
            if (pt == Stockfish::KNIGHT) pt_c = 'n';
            else if (pt == Stockfish::BISHOP) pt_c = 'b';
            else if (pt == Stockfish::ROOK) pt_c = 'r';
            else if (pt == Stockfish::QUEEN) pt_c = 'q';
            else if (pt == Stockfish::ARCHBISHOP) pt_c = 'h';
            else if (pt == Stockfish::CENTAUR) pt_c = 'm';
            else if (pt == Stockfish::CUSTOM_PIECE_1) pt_c = 'v';
            else if (pt == Stockfish::CUSTOM_PIECE_2) pt_c = 'y';
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
