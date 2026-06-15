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
    states.emplace_back();
    Stockfish::Thread* th = Stockfish::Threads.size() > 0 ? Stockfish::Threads.main() : nullptr;
    pos.set(variant_def, kStartposFen, false, &states.back(), th);
}

ChessBoard::ChessBoard(const ChessBoard& other) {
    variant_def = other.variant_def;
    states = other.states; // Copy deque of StateInfo
    pos.copy_from(other.pos, &states.back());
}

ChessBoard& ChessBoard::operator=(const ChessBoard& other) {
    if (this != &other) {
        variant_def = other.variant_def;
        states = other.states;
        pos.copy_from(other.pos, &states.back());
    }
    return *this;
}

void ChessBoard::SetFromFen(std::string_view fen, int* rule50_ply, int* moves) {
    states.clear();
    states.emplace_back();
    Stockfish::Thread* th = Stockfish::Threads.size() > 0 ? Stockfish::Threads.main() : nullptr;
    pos.set(variant_def, std::string(fen), false, &states.back(), th);
    if (rule50_ply) *rule50_ply = pos.rule50_count();
    if (moves) *moves = pos.game_ply();
}

void ChessBoard::Clear() {
    states.clear();
    states.emplace_back();
    Stockfish::Thread* th = Stockfish::Threads.size() > 0 ? Stockfish::Threads.main() : nullptr;
    pos.set(variant_def, "10/10/10/10/10/10/10/10/10/10 w - - 0 1", false, &states.back(), th);
}

MoveList ChessBoard::GenerateLegalMoves() const {
    return MoveList(pos);
}

bool ChessBoard::ApplyMove(Move move) {
    states.emplace_back();
    pos.do_move(move, states.back());
    // Return true if the rule50 ply counter should be reset (pawn move, customPiece3/Sergeant move, or capture)
    Stockfish::PieceType pt = Stockfish::type_of(pos.moved_piece(move));
    bool is_pawn_or_sergeant = (pt == Stockfish::PAWN || pt == Stockfish::CUSTOM_PIECE_3);
    return pos.capture(move) || is_pawn_or_sergeant;
}

void ChessBoard::UndoMove() {
    if (states.size() > 1) {
        Move last_move = pos.state()->move;
        pos.undo_move(last_move);
        states.pop_back();
    }
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
