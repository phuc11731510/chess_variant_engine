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
    // Parses `fen` only (delegating to ChessBoard() first also parsed the
    // start position, doubling the cost of every board built from a FEN).
    ChessBoard(const std::string& fen) : variant_def(FindVariant()) { SetFromFen(fen); }
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

    void CopyFrom(const ChessBoard& other, Stockfish::StateInfo* external_state = nullptr);
    MoveList GenerateLegalMoves() const;
    bool ApplyMove(Move move, Stockfish::StateInfo* external_state = nullptr);
    void UndoMove();
    bool IsUnderCheck() const;

    std::string MoveToString(Move move) const;
    Move ParseMove(std::string_view move_str) const;

    // Trả về thuộc tính side to move để đồng bộ với Lc0
    bool flipped() const { return pos.side_to_move() == Stockfish::BLACK; }

    // Zobrist key of the position: pieces, side to move, castling rights, e.p.
    // squares and checks remaining -- NOT the rule-50 counter. Repetition
    // detection (PositionHistory) compares these keys, exactly like
    // Fairy-Stockfish compares st->key in its own n-fold check. Do not use
    // pos.key(): for rule50 >= 14 it XORs in a rule-50 bucket (a Stockfish
    // transposition-table trick), so a position repeated 4 plies later no
    // longer matches and threefold repetition went undetected (fixed 2026-09-23).
    // lc0's Position::Hash() leaves rule50 out as well.
    uint64_t Hash() const { return pos.state()->key; }
    uint64_t GetHash() const { return Hash(); }

    // Hỗ trợ neural network encoding sau này
    const Stockfish::Position& GetRawPosition() const { return pos; }

private:
    // The registered custom variant ("fairy" if missing, with a warning).
    static const Stockfish::Variant* FindVariant();

    Stockfish::Position pos;
    std::array<Stockfish::StateInfo, 2> states; // Mảng tĩnh thay thế deque để tránh heap allocation
    int state_index = 0; // Vị trí state đang hoạt động trong mảng states
    const Stockfish::Variant* variant_def = nullptr;
};

} // namespace lczero
