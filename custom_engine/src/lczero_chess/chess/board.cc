#include "board.h"
#include "../../chess/variant.h"
#include "../../chess/uci.h"
#include "../../chess/thread.h"
#include <cstring>
#include <iostream>

namespace lczero {

const char* ChessBoard::kStartposFen = "vrhabkberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHABKBERV w - - 7+7 0 1";

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
    states = other.states; // Sao chép mảng tĩnh cực nhanh
    state_index = other.state_index;
    pos.copy_from(other.pos, &states[state_index]);
}

ChessBoard& ChessBoard::operator=(const ChessBoard& other) {
    if (this != &other) {
        variant_def = other.variant_def;
        states = other.states;
        state_index = other.state_index;
        pos.copy_from(other.pos, &states[state_index]);
    }
    return *this;
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
    pos.set(variant_def, "10/10/10/10/10/10/10/10/10/10 w - - 0 1", false, &states[state_index], th);
}

MoveList ChessBoard::GenerateLegalMoves() const {
    return MoveList(pos);
}

bool ChessBoard::ApplyMove(Move move) {
    int next_index = 1 - state_index;
    state_index = next_index;
    pos.do_move(move, states[state_index]);
    
    Stockfish::PieceType pt = Stockfish::type_of(pos.moved_piece(move));
    bool is_pawn_or_sergeant = (pt == Stockfish::PAWN || pt == Stockfish::CUSTOM_PIECE_3);
    return pos.capture(move) || is_pawn_or_sergeant;
}

void ChessBoard::UndoMove() {
    int prev_index = 1 - state_index;
    Move last_move = pos.state()->move;
    pos.undo_move(last_move);
    state_index = prev_index;
}

bool ChessBoard::IsUnderCheck() const {
    return (bool)pos.checkers();
}

std::string ChessBoard::MoveToString(Move move) const {
    return Stockfish::UCI::move(pos, move);
}

Move ChessBoard::ParseMove(std::string_view move_str) const {
    std::string s(move_str);
    return Stockfish::UCI::to_move(pos, s);
}

} // namespace lczero
