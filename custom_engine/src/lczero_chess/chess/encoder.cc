#include "encoder.h"
#include <cstring>
#include <algorithm>
#include <cassert>

namespace lczero {

void EncodePositionForNN(
    const PositionHistory& history,
    int history_planes,
    FillEmptyHistory fill_empty_history,
    InputPlanes* output_planes,
    int* transform_out) {
    
    if (transform_out) {
        *transform_out = 0; // NoTransform
    }
    
    if (!output_planes) return;
    
    InputPlane zero_plane;
    zero_plane.mask = 0;
    zero_plane.value = 0.0f;
    output_planes->fill(zero_plane);
    
    const auto& last_position = history.Last();
    const auto& starting_position = history.Starting();
    int history_size = static_cast<int>(history.GetPositions().size());
    
    Stockfish::Color us = last_position.IsBlackToMove() ? Stockfish::BLACK : Stockfish::WHITE;
    Stockfish::Color them = ~us;
    bool is_flipped = (us == Stockfish::BLACK);
    
    for (int d = 0; d < kMoveHistory; ++d) {
        bool has_board = false;
        std::array<uint8_t, 120> board_state{};
        int rep = 0;
        
        if (d == 0) {
            const auto& raw_board = last_position.GetBoard().GetRawPosition();
            for (int s = 0; s < 120; ++s) {
                board_state[s] = static_cast<uint8_t>(raw_board.piece_on(Stockfish::Square(s)));
            }
            rep = last_position.GetRepetitions();
            has_board = true;
        } else if (history_size >= d) {
            const auto& hist_pos = history.GetPositions()[history_size - d];
            board_state = hist_pos.board;
            rep = hist_pos.repetitions;
            has_board = true;
        } else if (fill_empty_history == FillEmptyHistory::ALWAYS) {
            const auto& raw_board = starting_position.GetBoard().GetRawPosition();
            for (int s = 0; s < 120; ++s) {
                board_state[s] = static_cast<uint8_t>(raw_board.piece_on(Stockfish::Square(s)));
            }
            rep = starting_position.GetRepetitions();
            has_board = true;
        }
        
        if (!has_board) {
            continue;
        }
        
        for (int s = 0; s < 120; ++s) {
            int file = s % 12;
            int rank = s / 12;
            if (file >= 10 || rank >= 10) continue;
            
            Stockfish::Piece pc = static_cast<Stockfish::Piece>(board_state[s]);
            if (pc == Stockfish::NO_PIECE) continue;
            
            Stockfish::PieceType pt = Stockfish::type_of(pc);
            Stockfish::Color c = Stockfish::color_of(pc);
            
            int plane_idx = -1;
            switch (pt) {
                case Stockfish::PAWN:           plane_idx = 0; break;
                case Stockfish::KNIGHT:         plane_idx = 1; break;
                case Stockfish::BISHOP:         plane_idx = 2; break;
                case Stockfish::ROOK:           plane_idx = 3; break;
                case Stockfish::QUEEN:          plane_idx = 4; break;
                case Stockfish::KING:           plane_idx = 5; break;
                case Stockfish::AMAZON:         plane_idx = 6; break;
                case Stockfish::CHANCELLOR:     plane_idx = 7; break;
                case Stockfish::ARCHBISHOP:     plane_idx = 8; break;
                case Stockfish::CENTAUR:        plane_idx = 9; break;
                case Stockfish::CUSTOM_PIECE_1: plane_idx = 10; break;
                case Stockfish::CUSTOM_PIECE_2: plane_idx = 11; break;
                case Stockfish::CUSTOM_PIECE_3: plane_idx = 12; break;
                default: break;
            }
            
            if (plane_idx != -1) {
                int plane_offset = (c == us) ? 0 : 13;
                int dest_plane = d * kPlanesPerBoard + plane_offset + plane_idx;
                
                Stockfish::Square dest_sq = static_cast<Stockfish::Square>(s);
                if (is_flipped) {
                    dest_sq = Stockfish::relative_square(Stockfish::BLACK, dest_sq, Stockfish::RANK_10);
                }
                
                output_planes->at(dest_plane).mask |= dest_sq;
            }
        }
        
        if (rep >= 1) {
            output_planes->at(d * kPlanesPerBoard + 26).Fill(1.0f);
        }
    }
    
    const auto& raw_pos = last_position.GetBoard().GetRawPosition();
    
    if (raw_pos.can_castle(Stockfish::WHITE_OOO)) {
        Stockfish::Square rook_sq = raw_pos.castling_rook_square(Stockfish::WHITE_OOO);
        if (is_flipped) rook_sq = Stockfish::relative_square(Stockfish::BLACK, rook_sq, Stockfish::RANK_10);
        output_planes->at(kAuxPlaneBase + 0).mask |= rook_sq;
    }
    if (raw_pos.can_castle(Stockfish::WHITE_OO)) {
        Stockfish::Square rook_sq = raw_pos.castling_rook_square(Stockfish::WHITE_OO);
        if (is_flipped) rook_sq = Stockfish::relative_square(Stockfish::BLACK, rook_sq, Stockfish::RANK_10);
        output_planes->at(kAuxPlaneBase + 1).mask |= rook_sq;
    }
    if (raw_pos.can_castle(Stockfish::BLACK_OOO)) {
        Stockfish::Square rook_sq = raw_pos.castling_rook_square(Stockfish::BLACK_OOO);
        if (is_flipped) rook_sq = Stockfish::relative_square(Stockfish::BLACK, rook_sq, Stockfish::RANK_10);
        output_planes->at(kAuxPlaneBase + 2).mask |= rook_sq;
    }
    if (raw_pos.can_castle(Stockfish::BLACK_OO)) {
        Stockfish::Square rook_sq = raw_pos.castling_rook_square(Stockfish::BLACK_OO);
        if (is_flipped) rook_sq = Stockfish::relative_square(Stockfish::BLACK, rook_sq, Stockfish::RANK_10);
        output_planes->at(kAuxPlaneBase + 3).mask |= rook_sq;
    }
    
    Stockfish::Bitboard ep = raw_pos.ep_squares();
    if (ep) {
        if (is_flipped) {
            Stockfish::Bitboard flipped_ep = 0;
            while (ep) {
                Stockfish::Square sq = Stockfish::pop_lsb(ep);
                flipped_ep |= Stockfish::relative_square(Stockfish::BLACK, sq, Stockfish::RANK_10);
            }
            ep = flipped_ep;
        }
        output_planes->at(kAuxPlaneBase + 4).mask = ep;
    }
    
    output_planes->at(kAuxPlaneBase + 5).Fill(static_cast<float>(last_position.GetRule50Ply()) / 100.0f);
    output_planes->at(kAuxPlaneBase + 7).Fill(1.0f);
    output_planes->at(kAuxPlaneBase + 8).Fill(static_cast<float>(raw_pos.checks_remaining(Stockfish::WHITE)) / 7.0f);
    output_planes->at(kAuxPlaneBase + 9).Fill(static_cast<float>(raw_pos.checks_remaining(Stockfish::BLACK)) / 7.0f);
}



namespace {

template <int W, int H, int FileNB, int SquareNB>
struct SqToTensorLUT {
    int lut[SquareNB];
    constexpr SqToTensorLUT() : lut{} {
        for (int sq = 0; sq < SquareNB; ++sq) {
            int f = sq % FileNB;
            int r = sq / FileNB;
            if (f < W && r < H) {
                lut[sq] = r * W + f;
            } else {
                lut[sq] = -1;
            }
        }
    }
};

constexpr auto sq_to_tensor_lut = SqToTensorLUT<10, 10, Stockfish::FILE_NB, Stockfish::SQUARE_NB>();

} // namespace

void UnpackInputPlanes(
    const InputPlanes& planes,
    float* float_planes,
    int width,
    int height) {
    
    const int plane_size = width * height;
    assert(width <= Stockfish::FILE_NB && height <= Stockfish::RANK_NB);
    
    // 1. Khởi tạo toàn bộ tensor về 0.0f bằng một lệnh memset toàn cục duy nhất
    std::memset(float_planes, 0, planes.size() * plane_size * sizeof(float));
    
    if (width == 10 && height == 10) {
        // 2. Nhánh tối ưu sử dụng LUT O(1) cho bàn cờ 10x10
        for (size_t p = 0; p < planes.size(); ++p) {
            const auto& plane = planes[p];
            if (!plane.mask) {
                continue; // Bỏ qua nhanh vì vùng nhớ đã được zero-init toàn cục
            }
            
            float* dest = float_planes + p * plane_size;
            
            if (plane.mask == Stockfish::AllSquares) {
                std::fill_n(dest, plane_size, plane.value);
                continue;
            }
            
            Stockfish::Bitboard b = plane.mask;
            while (b) {
                Stockfish::Square sq = Stockfish::pop_lsb(b);
                int idx = sq_to_tensor_lut.lut[sq];
                if (idx != -1) {
                    dest[idx] = plane.value;
                }
            }
        }
    } else {
        // 3. Nhánh Fallback động cho các kích thước bàn cờ khác
        for (size_t p = 0; p < planes.size(); ++p) {
            const auto& plane = planes[p];
            if (!plane.mask) {
                continue;
            }
            
            float* dest = float_planes + p * plane_size;
            
            if (plane.mask == Stockfish::AllSquares) {
                std::fill_n(dest, plane_size, plane.value);
                continue;
            }
            
            Stockfish::Bitboard b = plane.mask;
            while (b) {
                Stockfish::Square sq = Stockfish::pop_lsb(b);
                int f = Stockfish::file_of(sq);
                int r = Stockfish::rank_of(sq);
                dest[r * width + f] = plane.value;
            }
        }
    }
}

uint16_t MoveToNNIndex(Move move, int transform) {
    if (move.is_null()) return 0;

    Stockfish::Square from = Stockfish::from_sq(move);
    Stockfish::Square to = Stockfish::to_sq(move);

    int from_file = Stockfish::file_of(from);
    int from_rank = Stockfish::rank_of(from);
    int from_flat = from_rank * 10 + from_file;

    if (Stockfish::type_of(move) == Stockfish::PROMOTION) {
        Stockfish::PieceType promo_type = Stockfish::promotion_type(move);
        int piece_idx = -1;
        switch (promo_type) {
            case Stockfish::BISHOP:         piece_idx = 0; break;
            case Stockfish::ARCHBISHOP:     piece_idx = 1; break;
            case Stockfish::CENTAUR:        piece_idx = 2; break;
            case Stockfish::KNIGHT:         piece_idx = 3; break;
            case Stockfish::CUSTOM_PIECE_1: piece_idx = 4; break;
            case Stockfish::CUSTOM_PIECE_2: piece_idx = 5; break;
            default: break;
        }

        if (piece_idx != -1) {
            int to_file = Stockfish::file_of(to);
            int dir = to_file - from_file;
            int dir_idx = -1;
            if (dir == -1) dir_idx = 0;
            else if (dir == 0) dir_idx = 1;
            else if (dir == 1) dir_idx = 2;

            if (dir_idx != -1) {
                int type_idx = 100 + piece_idx * 3 + dir_idx;
                return type_idx * 100 + from_flat;
            }
        }
    }

    int to_file = Stockfish::file_of(to);
    int to_rank = Stockfish::rank_of(to);
    int to_flat = to_rank * 10 + to_file;
    return to_flat * 100 + from_flat;
}

Move MoveFromNNIndex(int idx, int transform) {
    if (idx < 0 || idx >= 11800) return Move(Stockfish::MOVE_NONE);

    int type_idx = idx / 100;
    int from_flat = idx % 100;
    int from_file = from_flat % 10;
    int from_rank = from_flat / 10;
    Stockfish::Square from = Stockfish::make_square(static_cast<Stockfish::File>(from_file), static_cast<Stockfish::Rank>(from_rank));

    if (type_idx >= 100) {
        int promo_val = type_idx - 100;
        int piece_idx = promo_val / 3;
        int dir_idx = promo_val % 3;

        Stockfish::PieceType promo_pt = Stockfish::NO_PIECE_TYPE;
        switch (piece_idx) {
            case 0: promo_pt = Stockfish::BISHOP; break;
            case 1: promo_pt = Stockfish::ARCHBISHOP; break;
            case 2: promo_pt = Stockfish::CENTAUR; break;
            case 3: promo_pt = Stockfish::KNIGHT; break;
            case 4: promo_pt = Stockfish::CUSTOM_PIECE_1; break;
            case 5: promo_pt = Stockfish::CUSTOM_PIECE_2; break;
            default: break;
        }

        Stockfish::Rank to_rank = Stockfish::RANK_1;
        if (from_rank > 5) {
            to_rank = Stockfish::RANK_10;
        } else if (from_rank < 4) {
            to_rank = Stockfish::RANK_1;
        }

        int to_file = from_file + (dir_idx - 1);
        if (to_file >= 0 && to_file < 10) {
            Stockfish::Square to = Stockfish::make_square(static_cast<Stockfish::File>(to_file), to_rank);
            return Stockfish::make<Stockfish::PROMOTION>(from, to, promo_pt);
        }
    } else {
        int to_flat = type_idx;
        int to_file = to_flat % 10;
        int to_rank = to_flat / 10;
        Stockfish::Square to = Stockfish::make_square(static_cast<Stockfish::File>(to_file), static_cast<Stockfish::Rank>(to_rank));
        return Stockfish::make_move(from, to);
    }

    return Move(Stockfish::MOVE_NONE);
}

} // namespace lczero
