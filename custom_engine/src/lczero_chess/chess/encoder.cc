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
    
    if (output_planes) {
        InputPlane zero_plane;
        zero_plane.mask = 0;
        zero_plane.value = 0.0f;
        output_planes->fill(zero_plane);
    }
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
    return 0;
}

Move MoveFromNNIndex(int idx, int transform) {
    return Move(Stockfish::MOVE_NONE);
}

} // namespace lczero
