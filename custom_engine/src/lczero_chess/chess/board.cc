#include "board.h"
#include "../../chess/variant.h"
#include "../../chess/uci.h"
#include "../../chess/thread.h"
#include <cstring>
#include <iostream>
#include <cassert>

namespace lczero {

const char* ChessBoard::kStartposFen = "vrhabkberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHABKBERV w BIbi - 7+7 0 1";

ChessBoard::ChessBoard() {
    auto it = Stockfish::variants.find("custom_10x10_variant");
    if (it != Stockfish::variants.end()) {
        variant_def = it->second;
    } else {
        std::cerr << "Warning: custom_10x10_variant not found, falling back to fairy!" << std::endl;
        auto it_fairy = Stockfish::variants.find("fairy");
        if (it_fairy != Stockfish::variants.end()) {
            variant_def = it_fairy->second;
        } else {
            variant_def = nullptr;
        }
    }
    state_index = 0;
    // Tối ưu 1: Ở chế độ MCTS, truyền nullptr để tránh thread contention trên main thread
    Stockfish::Thread* th = nullptr;
    pos.set(variant_def, kStartposFen, false, &states[state_index], th);
}

ChessBoard::ChessBoard(const ChessBoard& other) {
    variant_def = other.variant_def;
    state_index = other.state_index;
    states[state_index] = other.states[state_index];
    pos.copy_from(other.pos, &states[state_index]);
}

ChessBoard& ChessBoard::operator=(const ChessBoard& other) {
    if (this != &other) {
        variant_def = other.variant_def;
        state_index = other.state_index;
        states[state_index] = other.states[state_index];
        pos.copy_from(other.pos, &states[state_index]);
    }
    return *this;
}

void ChessBoard::CopyFrom(const ChessBoard& other, Stockfish::StateInfo* external_state) {
    variant_def = other.variant_def;
    state_index = other.state_index;
    if (external_state) {
        pos.copy_from(other.pos, external_state);
    } else {
        states[state_index] = other.states[state_index];
        pos.copy_from(other.pos, &states[state_index]);
    }
}

void ChessBoard::SetFromFen(std::string_view fen, int* rule50_ply, int* moves) {
    state_index = 0;
    Stockfish::Thread* th = nullptr;
    pos.set(variant_def, std::string(fen), false, &states[state_index], th);
    if (rule50_ply) *rule50_ply = pos.rule50_count();
    if (moves) *moves = pos.game_ply();
}

void ChessBoard::Clear() {
    state_index = 0;
    Stockfish::Thread* th = nullptr;
    pos.set(variant_def, "10/10/10/10/10/10/10/10/10/10 w - - 7+7 0 1", false, &states[state_index], th);
}

MoveList ChessBoard::GenerateLegalMoves() const {
    Stockfish::MoveList<Stockfish::LEGAL> list(pos);
    if (list.size() > 384) {
        std::cerr << "CRITICAL ERROR: Legal moves count (" << list.size() 
                  << ") exceeded the 384 cap at FEN: " << pos.fen() << std::endl;
        assert(list.size() <= 384 && "Legal moves exceeded 384 cap - policy/data will be truncated!");
    }
    MoveList result;
    result.reserve(list.size());
    bool is_black = (pos.side_to_move() == Stockfish::BLACK);
    for (auto ext_move : list) {
        Move m(ext_move.move);
        if (is_black) m.Flip(pos.max_rank());
        result.push_back(m);
    }
    return result;
}

bool ChessBoard::ApplyMove(Move move, Stockfish::StateInfo* external_state) {
    if (pos.side_to_move() == Stockfish::BLACK) {
        move.Flip(pos.max_rank());
    }
    if (external_state) {
        pos.do_move(move, *external_state);
    } else {
        int next_index = 1 - state_index;
        state_index = next_index;
        pos.do_move(move, states[state_index]);
    }
    // Stockfish resets rule50 to 0 for all zeroing moves (captures, pawn/sergeant moves, drops, etc.)
    return pos.state()->rule50 == 0;
}

void ChessBoard::UndoMove() {
    Move last_move = pos.state()->move;
    pos.undo_move(last_move);
    if (pos.state() >= &states[0] && pos.state() <= &states[1]) {
        state_index = pos.state() - &states[0];
    }
}

bool ChessBoard::IsUnderCheck() const {
    return (bool)pos.checkers();
}

std::string ChessBoard::MoveToString(Move move) const {
    if (pos.side_to_move() == Stockfish::BLACK) {
        move.Flip(pos.max_rank());
    }
    return Stockfish::UCI::move(pos, move);
}

Move ChessBoard::ParseMove(std::string_view move_str) const {
    std::string s(move_str);
    Move m = Stockfish::UCI::to_move(pos, s);
    if (pos.side_to_move() == Stockfish::BLACK) {
        m.Flip(pos.max_rank());
    }
    return m;
}

} // namespace lczero
