#include "encoder.h"
#include <cstring>
#include <algorithm>
#include <cassert>

namespace lczero {

namespace {
// The piece kinds of the variant in plane order (nn_layout.h: kPieceKinds). The same order is the plane
// index of a piece on the input, so changing it changes what a network means.
constexpr Stockfish::PieceType kPieceKindOrder[kPieceKinds] = {
    Stockfish::PAWN,           Stockfish::KNIGHT,         Stockfish::BISHOP,         Stockfish::ROOK,
    Stockfish::QUEEN,          Stockfish::KING,           Stockfish::CENTAUR,        Stockfish::CUSTOM_PIECE_1,
    Stockfish::CUSTOM_PIECE_2, Stockfish::CUSTOM_PIECE_3, Stockfish::CUSTOM_PIECE_4, Stockfish::CUSTOM_PIECE_5};

// The pieces a pawn can promote to, in the order of their policy slots (types kPromotionBase + 3 * i + direction).
constexpr Stockfish::PieceType kPromotionOrder[kPromotionPieces] = {
    Stockfish::KNIGHT,         Stockfish::BISHOP,         Stockfish::ROOK,           Stockfish::QUEEN,
    Stockfish::CENTAUR,        Stockfish::CUSTOM_PIECE_1, Stockfish::CUSTOM_PIECE_2, Stockfish::CUSTOM_PIECE_4,
    Stockfish::CUSTOM_PIECE_5};

// PieceType -> index in the two tables above, or -1. PieceType values are sparse (KING = 63, CUSTOM_PIECE_1 =
// 39, ...), so these are PIECE_TYPE_NB-wide tables: one load per lookup, no branches in the encode hot path.
struct PieceTypeLUT {
    int8_t plane[Stockfish::PIECE_TYPE_NB];
    int8_t promotion[Stockfish::PIECE_TYPE_NB];
    constexpr PieceTypeLUT() : plane{}, promotion{} {
        for (int i = 0; i < Stockfish::PIECE_TYPE_NB; ++i) plane[i] = promotion[i] = -1;
        for (int i = 0; i < kPieceKinds; ++i) plane[kPieceKindOrder[i]] = static_cast<int8_t>(i);
        for (int i = 0; i < kPromotionPieces; ++i) promotion[kPromotionOrder[i]] = static_cast<int8_t>(i);
    }
};
constexpr PieceTypeLUT kPieceLut;
}  // namespace

// Hàm mã hóa lịch sử thế cờ thành các mặt phẳng đầu vào (InputPlanes) cho Neural Network
void EncodePositionForNN(
    const PositionHistory& history,
    int history_planes,
    FillEmptyHistory fill_empty_history,
    InputPlanes* output_planes,
    int* transform_out) {
    
    if (transform_out) {
        *transform_out = 0; // Không áp dụng phép quay/lật ảnh (NoTransform)
    }
    
    if (!output_planes) return;
    
    // Khởi tạo: mask rỗng, value = 1.0f.
    // QUAN TRỌNG: các plane nhị phân (quân cờ, nhập thành, en passant) chỉ OR mask
    // mà KHÔNG đặt lại value, nên value mặc định phải là 1.0f để UnpackInputPlanes
    // ghi 1.0 tại các ô có bit. (value=0.0f trước đây khiến NN KHÔNG thấy quân nào.)
    // Các plane vô hướng (rule50/checks/biên/lặp) tự Fill() đè lại value của chúng.
    InputPlane zero_plane;
    zero_plane.mask = 0;
    zero_plane.value = 1.0f;
    output_planes->fill(zero_plane);
    
    const auto& last_position = history.Last();
    const auto& starting_position = history.Starting();
    int history_size = static_cast<int>(history.GetPositions().size());
    
    // Xác định màu quân của lượt đi hiện tại (us) và đối phương (them)
    Stockfish::Color us = last_position.IsBlackToMove() ? Stockfish::BLACK : Stockfish::WHITE;
    Stockfish::Color them = ~us;
    bool is_flipped = (us == Stockfish::BLACK); // Lật bàn cờ nếu quân đen đi để đồng bộ góc nhìn NN

    // Đặt bit của một quân `pc` tại ô `sq` vào mặt phẳng tương ứng cho bước lịch sử `d`.
    auto emit_piece = [&](Stockfish::Piece pc, Stockfish::Square sq, int d) {
        if (pc == Stockfish::NO_PIECE) return;
        const int plane_idx = kPieceLut.plane[Stockfish::type_of(pc)];
        if (plane_idx < 0) return;
        const int plane_offset = (Stockfish::color_of(pc) == us) ? 0 : kPieceKinds;  // mình / đối thủ
        const int dest_plane = d * kPlanesPerBoard + plane_offset + plane_idx;
        const Stockfish::Square dest_sq =
            is_flipped ? Stockfish::relative_square(Stockfish::BLACK, sq, Stockfish::RANK_10) : sq;
        (*output_planes)[dest_plane].mask |= Stockfish::square_bb(dest_sq);
    };

    // Duyệt qua lịch sử 8 nước đi (kMoveHistory = 8)
    for (int d = 0; d < kMoveHistory; ++d) {
        bool has_board = false;
        const Stockfish::Position* raw_board_ptr = nullptr;
        const uint8_t* hist_board_ptr = nullptr;
        int rep = 0;
        
        if (d == 0) {
            // Lấy bàn cờ ở trạng thái hiện tại
            raw_board_ptr = &last_position.GetBoard().GetRawPosition();
            rep = last_position.GetRepetitions();
            has_board = true;
        } else if (history_size >= d) {
            // Lấy bàn cờ từ lịch sử lưu trữ
            const auto& hist_pos = history.GetPositions()[history_size - d];
            hist_board_ptr = hist_pos.board.data();
            rep = hist_pos.repetitions;
            has_board = true;
        } else if (fill_empty_history == FillEmptyHistory::ALWAYS ||
                   (fill_empty_history == FillEmptyHistory::FEN_ONLY && history.StartingIsCustom())) {
            // Lịch sử chưa đủ sâu: chép thế ban đầu vào các bàn còn trống. FEN_ONLY (như lc0) chỉ làm
            // vậy khi thế ban đầu không phải thế xuất phát (vd. FEN tự đặt): ván tự chơi luôn bắt đầu
            // từ thế xuất phát nên dữ liệu huấn luyện không đổi (các bàn trước nước đầu vẫn để trống).
            raw_board_ptr = &starting_position.GetBoard().GetRawPosition();
            rep = starting_position.GetRepetitions();
            has_board = true;
        }
        
        if (!has_board) {
            continue;
        }
        
        // Với thế cờ sống (d==0 / điền FEN): duyệt CHỈ ô có quân qua bitboard
        // occupancy (~20-44 quân thay vì quét cả 100 ô). Đường lịch sử là mảng
        // byte (không có bitboard) nên quét 10x10 ô như cũ — vốn đã cache-friendly.
        if (raw_board_ptr) {
            Stockfish::Bitboard occ = raw_board_ptr->pieces();
            while (occ) {
                Stockfish::Square sq = Stockfish::pop_lsb(occ);
                emit_piece(raw_board_ptr->piece_on(sq), sq, d);
            }
        } else {  // hist_board_ptr
            for (int rank = 0; rank < 10; ++rank) {
                for (int file = 0; file < 10; ++file) {
                    int s = rank * 12 + file;  // mỗi hàng rộng 12 ô do LARGEBOARDS
                    emit_piece(static_cast<Stockfish::Piece>(hist_board_ptr[s]),
                               static_cast<Stockfish::Square>(s), d);
                }
            }
        }
        
        // Mặt phẳng cuối của mỗi bước lịch sử: Chỉ thị trạng thái lặp lại thế cờ
        if (rep >= 1) {
            (*output_planes)[d * kPlanesPerBoard + 2 * kPieceKinds].Fill(1.0f);
        }
    }
    
    // Mã hóa các mặt phẳng phụ trợ (enum AuxPlane, nn_layout.h) ở phần cuối
    const auto& raw_pos = last_position.GetBoard().GetRawPosition();

    // Các ô có thể bị ăn tốt qua đường (En Passant), lật góc nhìn khi Đen đi
    Stockfish::Bitboard ep = raw_pos.ep_squares();
    if (ep && is_flipped) {
        Stockfish::Bitboard flipped_ep = 0;
        while (ep) {
            Stockfish::Square sq = Stockfish::pop_lsb(ep);
            flipped_ep |= Stockfish::square_bb(Stockfish::relative_square(Stockfish::BLACK, sq, Stockfish::RANK_10));
        }
        ep = flipped_ep;
    }
    (*output_planes)[kAuxPlaneBase + kAuxEnPassant].mask = ep;

    // Đếm luật 50 nước đi (chuẩn hóa rule50 / 100.0f)
    (*output_planes)[kAuxPlaneBase + kAuxRule50].Fill(static_cast<float>(last_position.GetRule50Ply()) / 100.0f);

    // Đầy 1.0f giúp mạng nơ-ron nhận biết biên bàn cờ 10x10
    (*output_planes)[kAuxPlaneBase + kAuxOnes].Fill(1.0f);

    // Số lượt chiếu còn lại, chuẩn hóa checks / 10.0f.
    //
    // Mẫu số 10 CỐ Ý không bằng N của luật: nó là trần Fairy-SF biểu diễn được
    // (CHECKS_NB = 11, và FEN ghi 1 chữ số nên N tối đa 9), nên mọi N khả thi
    // (0-9) đều cho giá trị ≤ 1.0. Nhờ vậy thang chuẩn hóa ĐỘC LẬP với luật:
    // đổi N-checks không cần sửa encoder. Luật hiện tại là 7-checks.
    (*output_planes)[kAuxPlaneBase + kAuxChecksUs].Fill(static_cast<float>(raw_pos.checks_remaining(us)) / 10.0f);
    (*output_planes)[kAuxPlaneBase + kAuxChecksThem].Fill(static_cast<float>(raw_pos.checks_remaining(them)) / 10.0f);
}

bool EncoderCoversVariant(const Stockfish::Variant& v, std::string* why) {
    auto fail = [&](const char* what, Stockfish::PieceType pt) {
        if (why) *why = std::string(what) + " '" + v.pieceToChar[Stockfish::make_piece(Stockfish::BLACK, pt)] + "'";
        return false;
    };
    for (Stockfish::PieceSet ps = v.pieceTypes; ps;) {
        const Stockfish::PieceType pt = Stockfish::pop_lsb(ps);
        if (kPieceLut.plane[pt] < 0) return fail("the encoder has no input plane for the piece", pt);
    }
    for (const Stockfish::Color c : {Stockfish::WHITE, Stockfish::BLACK})
        for (Stockfish::PieceSet ps = v.promotionPieceTypes[c] | v.optionalPromotionPieceTypes[c]; ps;) {
            const Stockfish::PieceType pt = Stockfish::pop_lsb(ps);
            if (kPieceLut.promotion[pt] < 0) return fail("the encoder has no policy slot for promoting to", pt);
        }
    return true;
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

// Hàm giải nén (unpack) dữ liệu từ cấu trúc mặt phẳng thưa (InputPlanes)
// thành mảng float phẳng liên tục để truyền trực tiếp vào ONNX Runtime.
void UnpackInputPlanes(
    const InputPlanes& planes,
    float* float_planes,
    int width,
    int height) {
    
    const int plane_size = width * height;
    assert(width <= Stockfish::FILE_NB && height <= Stockfish::RANK_NB);
    
    // 1. Khởi tạo toàn bộ mảng đầu ra về 0.0f bằng một lệnh memset hiệu năng cao
    std::memset(float_planes, 0, planes.size() * plane_size * sizeof(float));
    
    if (width == 10 && height == 10) {
        // 2. Nhánh tối ưu hóa cho bàn cờ 10x10 sử dụng LUT (bảng tra cứu) O(1)
        for (size_t p = 0; p < planes.size(); ++p) {
            const auto& plane = planes[p];
            if (!plane.mask) {
                continue; // Bỏ qua nhanh các mặt phẳng trống để tiết kiệm thời gian
            }
            
            float* dest = float_planes + p * plane_size;
            
            if (plane.mask == Stockfish::AllSquares) {
                std::fill_n(dest, plane_size, plane.value);
                continue;
            }
            
            Stockfish::Bitboard b = plane.mask;
            while (b) {
                Stockfish::Square sq = Stockfish::pop_lsb(b);
                int idx = sq_to_tensor_lut.lut[sq]; // Ánh xạ nhanh chỉ số ô cờ 12-cột sang 10-cột
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

// Hàm mã hóa một nước đi thực tế (Move) thành một chỉ số index trong mảng phẳng NN kPolicySize phần tử
uint16_t MoveToNNIndex(Move move, int transform) {
    if (move.is_null()) return 65535;

    Stockfish::Square from = Stockfish::from_sq(move);
    Stockfish::Square to = Stockfish::to_sq(move);

    int from_file = Stockfish::file_of(from);
    int from_rank = Stockfish::rank_of(from);
    int to_file = Stockfish::file_of(to);
    int to_rank = Stockfish::rank_of(to);

    // Kiểm tra toạ độ nằm trong phạm vi bàn cờ 10x10
    if (from_file < 0 || from_file >= 10 || from_rank < 0 || from_rank >= 10 ||
        to_file < 0 || to_file >= 10 || to_rank < 0 || to_rank >= 10) {
        return 65535;
    }

    // Ô cờ xuất phát được làm phẳng từ 0 đến 99 (cho bàn cờ 10x10)
    int from_flat = from_rank * kBoardSize + from_file;

    // Tính toán khoảng cách và hướng đi dọc theo trục X và Y
    int dx = to_file - from_file;
    int dy = to_rank - from_rank;

    // 1. Nước đi Phong cấp (Promotion, KỂ CẢ EN_PASSANT bắt-qua-đường rơi vào hàng phong cấp)
    //    -> kênh kPromotionBase .. kMoveTypes - 1: quân phong cấp x hướng (ăn trái, đi thẳng, ăn phải)
    Stockfish::PieceType promo_type = Stockfish::promotion_type(move);
    if (promo_type == Stockfish::NO_PIECE_TYPE && Stockfish::type_of(move) == Stockfish::EN_PASSANT)
        promo_type = Stockfish::ep_promotion_type(move);   // ep capture landing on a promotion rank
    if (promo_type != Stockfish::NO_PIECE_TYPE) {
        const int piece_idx = kPieceLut.promotion[promo_type];
        const int dir_idx = dx + 1;   // dx = -1 / 0 / +1
        if (piece_idx >= 0 && dir_idx >= 0 && dir_idx < kPromotionDirections)
            return (kPromotionBase + piece_idx * kPromotionDirections + dir_idx) * kBoardSquares + from_flat;

        // GUARD: một nước PROMOTION không map được (quân phong cấp ngoài kPromotionOrder,
        // hoặc hướng lạ) TUYỆT ĐỐI không được rơi xuyên xuống nhánh nước-tia bên
        // dưới — nếu rơi xuyên sẽ trả nhầm index của một nước đi-thẳng. Báo lỗi rõ.
#ifndef NDEBUG
        assert(false && "Unmapped PROMOTION move in MoveToNNIndex!");
#endif
        return 65535;
    }

    // 2. Kiểm tra nước nhảy của Mã (Knight moves) -> kênh kKnightBase .. +7
    int abs_dx = std::abs(dx);
    int abs_dy = std::abs(dy);
    if ((abs_dx == 1 && abs_dy == 2) || (abs_dx == 2 && abs_dy == 1)) {
        // 8 hướng nhảy theo chiều kim đồng hồ
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
            return (kKnightBase + knight_idx) * kBoardSquares + from_flat;
        }
    }

    // 3. Kiểm tra nước nhảy của Lạc đà (Camel moves) -> kênh kCamelBase .. +7
    if ((abs_dx == 1 && abs_dy == 3) || (abs_dx == 3 && abs_dy == 1)) {
        // 8 hướng nhảy của Lạc đà theo chiều kim đồng hồ
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
            return (kCamelBase + camel_idx) * kBoardSquares + from_flat;
        }
    }

    // 4. Kiểm tra nước đi dạng tia (Sliding / Alibaba moves) -> kênh 0 .. kSlideTypes - 1
    int dir_idx = -1;
    int distance = 0;
    if (dx == 0 && dy > 0)       { dir_idx = 0; distance = dy; }       // Hướng Bắc
    else if (dx > 0 && dy == dx)  { dir_idx = 1; distance = dx; }       // Hướng Đông Bắc
    else if (dx > 0 && dy == 0)   { dir_idx = 2; distance = dx; }       // Hướng Đông
    else if (dx > 0 && dy == -dx) { dir_idx = 3; distance = dx; }       // Hướng Đông Nam
    else if (dx == 0 && dy < 0)   { dir_idx = 4; distance = -dy; }      // Hướng Nam
    else if (dx < 0 && dy == dx)  { dir_idx = 5; distance = -dx; }      // Hướng Tây Nam
    else if (dx < 0 && dy == 0)   { dir_idx = 6; distance = -dx; }      // Hướng Tây
    else if (dx < 0 && dy == -dx) { dir_idx = 7; distance = -dx; }      // Hướng Tây Bắc

    // Khoảng cách tối đa cho phép trên bàn cờ 10x10 là 9 ô cờ
    if (dir_idx != -1 && distance >= 1 && distance <= 9) {
        int type_idx = dir_idx * 9 + (distance - 1);
        return type_idx * kBoardSquares + from_flat;
    }

#ifndef NDEBUG
    assert(false && "Unmapped move in MoveToNNIndex!");
#endif
    return 65535;
}

// Hàm giải mã ngược từ chỉ số index của mảng phẳng NN kPolicySize phần tử thành nước đi thực tế (Move)
Move MoveFromNNIndex(int idx, int transform) {
    if (idx < 0 || idx >= kPolicySize) return Move(Stockfish::MOVE_NONE);

    // Tách chỉ số index thành loại nước đi (type_idx) và ô cờ xuất phát (from_flat)
    int type_idx = idx / kBoardSquares;
    int from_flat = idx % kBoardSquares;
    int from_file = from_flat % kBoardSize;
    int from_rank = from_flat / kBoardSize;
    Stockfish::Square from = Stockfish::make_square(static_cast<Stockfish::File>(from_file), static_cast<Stockfish::Rank>(from_rank));

    Move res = MOVE_NONE;
    // 1. Giải mã nước đi dạng tia (Sliding moves) -> kênh 0 .. kSlideTypes - 1
    if (type_idx >= 0 && type_idx < kSlideTypes) {
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
        // Kiểm tra toạ độ nằm trong phạm vi hợp lệ của bàn cờ 10x10
        if (to_file >= 0 && to_file < 10 && to_rank >= 0 && to_rank < 10) {
            Stockfish::Square to = Stockfish::make_square(static_cast<Stockfish::File>(to_file), static_cast<Stockfish::Rank>(to_rank));
            res = Stockfish::make_move(from, to);
        }
    }
    // 2. Giải mã nước nhảy của Mã (Knight moves) -> kênh kKnightBase .. +7
    else if (type_idx >= kKnightBase && type_idx < kCamelBase) {
        int knight_idx = type_idx - kKnightBase;
        static const int dx_list[] = {1, 2, 2, 1, -1, -2, -2, -1};
        static const int dy_list[] = {2, 1, -1, -2, -2, -1, 1, 2};
        int dx = dx_list[knight_idx];
        int dy = dy_list[knight_idx];
        int to_file = from_file + dx;
        int to_rank = from_rank + dy;
        if (to_file >= 0 && to_file < 10 && to_rank >= 0 && to_rank < 10) {
            Stockfish::Square to = Stockfish::make_square(static_cast<Stockfish::File>(to_file), static_cast<Stockfish::Rank>(to_rank));
            res = Stockfish::make_move(from, to);
        }
    }
    // 3. Giải mã nước nhảy của Lạc đà (Camel moves) -> kênh kCamelBase .. +7
    else if (type_idx >= kCamelBase && type_idx < kPromotionBase) {
        int camel_idx = type_idx - kCamelBase;
        static const int dx_list[] = {1, 3, 3, 1, -1, -3, -3, -1};
        static const int dy_list[] = {3, 1, -1, -3, -3, -1, 1, 3};
        int dx = dx_list[camel_idx];
        int dy = dy_list[camel_idx];
        int to_file = from_file + dx;
        int to_rank = from_rank + dy;
        if (to_file >= 0 && to_file < 10 && to_rank >= 0 && to_rank < 10) {
            Stockfish::Square to = Stockfish::make_square(static_cast<Stockfish::File>(to_file), static_cast<Stockfish::Rank>(to_rank));
            res = Stockfish::make_move(from, to);
        }
    }
    // 4. Giải mã nước đi Phong cấp (Promotion moves) -> kênh kPromotionBase .. kMoveTypes - 1
    else if (type_idx >= kPromotionBase && type_idx < kMoveTypes) {
        const int promo_idx = type_idx - kPromotionBase;
        const Stockfish::PieceType promo_pt = kPromotionOrder[promo_idx / kPromotionDirections];
        const int dir_idx = promo_idx % kPromotionDirections;

        // Tịnh tiến hàng đích lên 1 đơn vị: hỗ trợ chính xác cả việc phong cấp tại hàng 8 hay hàng 9
        Stockfish::Rank to_rank = static_cast<Stockfish::Rank>(from_rank + 1);

        int to_file = from_file + (dir_idx - 1);
        if (to_file >= 0 && to_file < 10 && to_rank >= 0 && to_rank < 10) {
            Stockfish::Square to = Stockfish::make_square(static_cast<Stockfish::File>(to_file), to_rank);
            res = Stockfish::make<Stockfish::PROMOTION>(from, to, promo_pt);
        }
    }

    return res;
}

} // namespace lczero
