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
