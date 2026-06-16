#pragma once
#include <string>
#include <vector>
#include <array>
#include "types.h"
#include "../../chess/position.h"

namespace lczero {

struct BitboardWrapper {
    Stockfish::Bitboard b;
    BitboardWrapper(Stockfish::Bitboard bb) : b(bb) {}
    int count() const {
        return Stockfish::popcount(b);
    }
    BitboardWrapper operator|(BitboardWrapper other) const {
        return BitboardWrapper(b | other.b);
    }
};

struct CastlingsWrapper {
    bool no_legal_castle() const { return true; }
};

class ChessBoard {
public:
    ChessBoard();
    ChessBoard(const ChessBoard& other);
    ChessBoard(const std::string& fen) : ChessBoard() { SetFromFen(fen); }
    ChessBoard& operator=(const ChessBoard& other);

    BitboardWrapper ours() const {
        return BitboardWrapper(pos.pieces(pos.side_to_move()));
    }
    BitboardWrapper theirs() const {
        return BitboardWrapper(pos.pieces(~pos.side_to_move()));
    }
    CastlingsWrapper castlings() const { return CastlingsWrapper{}; }
    bool HasMatingMaterial() const { return true; }

    static const char* kStartposFen;

    void SetFromFen(std::string_view fen, int* rule50_ply = nullptr, int* moves = nullptr);
    void Clear();
    void Mirror() {} // Không cần làm gì vì Stockfish tự động xoay side_to_move khi do_move

    MoveList GenerateLegalMoves() const;
    bool ApplyMove(Move move);
    // NOTE: MCTS uses Copy->ApplyMove pattern, not ApplyMove->UndoMove.
    // UndoMove is kept only for unit testing/debugging purposes.
    [[deprecated("Do not use UndoMove in MCTS. Clone the ChessBoard before ApplyMove instead.")]]
    void UndoMove();
    bool IsUnderCheck() const;

    std::string MoveToString(Move move) const;
    Move ParseMove(std::string_view move_str) const;

    // Trả về thuộc tính side to move để đồng bộ với Lc0
    bool flipped() const { return pos.side_to_move() == Stockfish::BLACK; }
    
    // Hỗ trợ kiểm tra nước đi hợp lệ cực nhanh
    bool IsLegalMove(Move move) const { return pos.pseudo_legal(move) && pos.legal(move); }

    // Các phương thức lấy Hash thế cờ dùng cho Transposition Table trong MCTS
    uint64_t Hash() const { return pos.key(); }
    uint64_t GetHash() const { return Hash(); }

    // Hỗ trợ neural network encoding sau này
    const Stockfish::Position& GetRawPosition() const { return pos; }

private:
    Stockfish::Position pos;
    std::array<Stockfish::StateInfo, 2> states; // Mảng tĩnh thay thế deque để tránh heap allocation
    int state_index = 0; // Vị trí state đang hoạt động trong mảng states
    const Stockfish::Variant* variant_def = nullptr;
};

} // namespace lczero
