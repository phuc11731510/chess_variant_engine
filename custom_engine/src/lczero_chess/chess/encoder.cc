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
        const Stockfish::Position* raw_board_ptr = nullptr;
        const uint8_t* hist_board_ptr = nullptr;
        int rep = 0;
        
        if (d == 0) {
            raw_board_ptr = &last_position.GetBoard().GetRawPosition();
            rep = last_position.GetRepetitions();
            has_board = true;
        } else if (history_size >= d) {
            const auto& hist_pos = history.GetPositions()[history_size - d];
            hist_board_ptr = hist_pos.board.data();
            rep = hist_pos.repetitions;
            has_board = true;
        } else if (fill_empty_history == FillEmptyHistory::ALWAYS) {
            raw_board_ptr = &starting_position.GetBoard().GetRawPosition();
            rep = starting_position.GetRepetitions();
            has_board = true;
        }
        
        if (!has_board) {
            continue;
        }
        
        for (int rank = 0; rank < 10; ++rank) {
            for (int file = 0; file < 10; ++file) {
                int s = rank * 12 + file;
                
                Stockfish::Piece pc = Stockfish::NO_PIECE;
                if (hist_board_ptr) {
                    pc = static_cast<Stockfish::Piece>(hist_board_ptr[s]);
                } else if (raw_board_ptr) {
                    pc = static_cast<Stockfish::Piece>(raw_board_ptr->piece_on(static_cast<Stockfish::Square>(s)));
                }
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
        }
        
        if (rep >= 1) {
            output_planes->at(d * kPlanesPerBoard + 26).Fill(1.0f);
        }
    }
    
    const auto& raw_pos = last_position.GetBoard().GetRawPosition();
    
    Stockfish::CastlingRights us_ooo   = (us == Stockfish::WHITE) ? Stockfish::WHITE_OOO : Stockfish::BLACK_OOO;
    Stockfish::CastlingRights us_oo    = (us == Stockfish::WHITE) ? Stockfish::WHITE_OO  : Stockfish::BLACK_OO;
    Stockfish::CastlingRights them_ooo = (us == Stockfish::WHITE) ? Stockfish::BLACK_OOO : Stockfish::WHITE_OOO;
    Stockfish::CastlingRights them_oo  = (us == Stockfish::WHITE) ? Stockfish::BLACK_OO  : Stockfish::WHITE_OO;

    if (raw_pos.can_castle(us_ooo)) {
        Stockfish::Square rook_sq = raw_pos.castling_rook_square(us_ooo);
        if (is_flipped) rook_sq = Stockfish::relative_square(Stockfish::BLACK, rook_sq, Stockfish::RANK_10);
        output_planes->at(kAuxPlaneBase + 0).mask |= rook_sq;
    }
    if (raw_pos.can_castle(us_oo)) {
        Stockfish::Square rook_sq = raw_pos.castling_rook_square(us_oo);
        if (is_flipped) rook_sq = Stockfish::relative_square(Stockfish::BLACK, rook_sq, Stockfish::RANK_10);
        output_planes->at(kAuxPlaneBase + 1).mask |= rook_sq;
    }
    if (raw_pos.can_castle(them_ooo)) {
        Stockfish::Square rook_sq = raw_pos.castling_rook_square(them_ooo);
        if (is_flipped) rook_sq = Stockfish::relative_square(Stockfish::BLACK, rook_sq, Stockfish::RANK_10);
        output_planes->at(kAuxPlaneBase + 2).mask |= rook_sq;
    }
    if (raw_pos.can_castle(them_oo)) {
        Stockfish::Square rook_sq = raw_pos.castling_rook_square(them_oo);
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
    output_planes->at(kAuxPlaneBase + 8).Fill(static_cast<float>(raw_pos.checks_remaining(us)) / 7.0f);
    output_planes->at(kAuxPlaneBase + 9).Fill(static_cast<float>(raw_pos.checks_remaining(them)) / 7.0f);
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
                if (f < width && r < height) {
                    dest[r * width + f] = plane.value;
                }
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

    int to_file = Stockfish::file_of(to);
    int to_rank = Stockfish::rank_of(to);

    int dx = to_file - from_file;
    int dy = to_rank - from_rank;

    // 1. Kiểm tra nước đi Phong cấp (Promotion) -> Kênh 88 - 105
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
            int dir_idx = -1;
            if (dx == -1) dir_idx = 0;
            else if (dx == 0) dir_idx = 1;
            else if (dx == 1) dir_idx = 2;

            if (dir_idx != -1) {
                int type_idx = 88 + piece_idx * 3 + dir_idx;
                return type_idx * 100 + from_flat;
            }
        }
    }

    // 2. Kiểm tra nước nhảy của Mã (Knight) -> Kênh 72 - 79
    int abs_dx = std::abs(dx);
    int abs_dy = std::abs(dy);
    if ((abs_dx == 1 && abs_dy == 2) || (abs_dx == 2 && abs_dy == 1)) {
        // Clockwise offsets: (1,2), (2,1), (2,-1), (1,-2), (-1,-2), (-2,-1), (-2,1), (-1,2)
        int knight_idx = -1;
        if      (dx == 1  && dy == 2)  knight_idx = 0;
        else if (dx == 2  && dy == 1)  knight_idx = 1;
        else if (dx == 2  && dy == -1) knight_idx = 2;
        else if (dx == 1  && dy == -2) knight_idx = 3;
        else if (dx == -1 && dy == -2) knight_idx = 4;
        else if (dx == -2 && dy == -1) knight_idx = 5;
        else if (dx == -2 && dy == 1)  knight_idx = 6;
        else if (dx == -1 && dy == 2)  knight_idx = 7;

        if (knight_idx != -1) {
            return (72 + knight_idx) * 100 + from_flat;
        }
    }

    // 3. Kiểm tra nước nhảy của Lạc đà (Camel) -> Kênh 80 - 87
    if ((abs_dx == 1 && abs_dy == 3) || (abs_dx == 3 && abs_dy == 1)) {
        // Clockwise offsets: (1,3), (3,1), (3,-1), (1,-3), (-1,-3), (-3,-1), (-3,1), (-1,3)
        int camel_idx = -1;
        if      (dx == 1  && dy == 3)  camel_idx = 0;
        else if (dx == 3  && dy == 1)  camel_idx = 1;
        else if (dx == 3  && dy == -1) camel_idx = 2;
        else if (dx == 1  && dy == -3) camel_idx = 3;
        else if (dx == -1 && dy == -3) camel_idx = 4;
        else if (dx == -3 && dy == -1) camel_idx = 5;
        else if (dx == -3 && dy == 1)  camel_idx = 6;
        else if (dx == -1 && dy == 3)  camel_idx = 7;

        if (camel_idx != -1) {
            return (80 + camel_idx) * 100 + from_flat;
        }
    }

    // 4. Kiểm tra nước đi dạng tia (Sliding / Alibaba) -> Kênh 0 - 71
    int dir_idx = -1;
    int distance = 0;
    if (dx == 0 && dy > 0)       { dir_idx = 0; distance = dy; }
    else if (dx > 0 && dy == dx)  { dir_idx = 1; distance = dx; }
    else if (dx > 0 && dy == 0)   { dir_idx = 2; distance = dx; }
    else if (dx > 0 && dy == -dx) { dir_idx = 3; distance = dx; }
    else if (dx == 0 && dy < 0)   { dir_idx = 4; distance = -dy; }
    else if (dx < 0 && dy == dx)  { dir_idx = 5; distance = -dx; }
    else if (dx < 0 && dy == 0)   { dir_idx = 6; distance = -dx; }
    else if (dx < 0 && dy == -dx) { dir_idx = 7; distance = -dx; }

    if (dir_idx != -1 && distance >= 1 && distance <= 9) {
        int type_idx = dir_idx * 9 + (distance - 1);
        return type_idx * 100 + from_flat;
    }

    return 0;
}

Move MoveFromNNIndex(int idx, int transform) {
    if (idx < 0 || idx >= 10600) return Move(Stockfish::MOVE_NONE);

    int type_idx = idx / 100;
    int from_flat = idx % 100;
    int from_file = from_flat % 10;
    int from_rank = from_flat / 10;
    Stockfish::Square from = Stockfish::make_square(static_cast<Stockfish::File>(from_file), static_cast<Stockfish::Rank>(from_rank));

    // 1. Sliding / Alibaba moves -> Kênh 0 - 71
    if (type_idx >= 0 && type_idx <= 71) {
        int dir_idx = type_idx / 9;
        int distance = (type_idx % 9) + 1;
        int dx = 0, dy = 0;
        switch (dir_idx) {
            case 0: dx = 0;         dy = distance;  break;
            case 1: dx = distance;  dy = distance;  break;
            case 2: dx = distance;  dy = 0;         break;
            case 3: dx = distance;  dy = -distance; break;
            case 4: dx = 0;         dy = -distance; break;
            case 5: dx = -distance; dy = -distance; break;
            case 6: dx = -distance; dy = 0;         break;
            case 7: dx = -distance; dy = distance;  break;
            default: break;
        }

        int to_file = from_file + dx;
        int to_rank = from_rank + dy;
        if (to_file >= 0 && to_file < 10 && to_rank >= 0 && to_rank < 10) {
            Stockfish::Square to = Stockfish::make_square(static_cast<Stockfish::File>(to_file), static_cast<Stockfish::Rank>(to_rank));
            return Stockfish::make_move(from, to);
        }
    }
    // 2. Knight moves -> Kênh 72 - 79
    else if (type_idx >= 72 && type_idx <= 79) {
        int knight_idx = type_idx - 72;
        static const int dx_list[] = {1, 2, 2, 1, -1, -2, -2, -1};
        static const int dy_list[] = {2, 1, -1, -2, -2, -1, 1, 2};
        int dx = dx_list[knight_idx];
        int dy = dy_list[knight_idx];
        int to_file = from_file + dx;
        int to_rank = from_rank + dy;
        if (to_file >= 0 && to_file < 10 && to_rank >= 0 && to_rank < 10) {
            Stockfish::Square to = Stockfish::make_square(static_cast<Stockfish::File>(to_file), static_cast<Stockfish::Rank>(to_rank));
            return Stockfish::make_move(from, to);
        }
    }
    // 3. Camel moves -> Kênh 80 - 87
    else if (type_idx >= 80 && type_idx <= 87) {
        int camel_idx = type_idx - 80;
        static const int dx_list[] = {1, 3, 3, 1, -1, -3, -3, -1};
        static const int dy_list[] = {3, 1, -1, -3, -3, -1, 1, 3};
        int dx = dx_list[camel_idx];
        int dy = dy_list[camel_idx];
        int to_file = from_file + dx;
        int to_rank = from_rank + dy;
        if (to_file >= 0 && to_file < 10 && to_rank >= 0 && to_rank < 10) {
            Stockfish::Square to = Stockfish::make_square(static_cast<Stockfish::File>(to_file), static_cast<Stockfish::Rank>(to_rank));
            return Stockfish::make_move(from, to);
        }
    }
    // 4. Promotion moves -> Kênh 88 - 105
    else if (type_idx >= 88 && type_idx <= 105) {
        int promo_idx = type_idx - 88;
        int piece_idx = promo_idx / 3;
        int dir_idx = promo_idx % 3;

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

        Stockfish::Rank to_rank = static_cast<Stockfish::Rank>(from_rank + 1);

        int to_file = from_file + (dir_idx - 1);
        if (to_file >= 0 && to_file < 10) {
            Stockfish::Square to = Stockfish::make_square(static_cast<Stockfish::File>(to_file), to_rank);
            return Stockfish::make<Stockfish::PROMOTION>(from, to, promo_pt);
        }
    }

    return Move(Stockfish::MOVE_NONE);
}

} // namespace lczero
