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

void EncodePositionForNN(
    std::span<const Position> positions,
    int history_planes,
    FillEmptyHistory fill_empty_history,
    InputPlanes* output_planes,
    int* transform_out) {
    
    if (transform_out) {
        *transform_out = 0;
    }
    
    if (output_planes) {
        InputPlane zero_plane;
        zero_plane.mask = 0;
        zero_plane.value = 0.0f;
        output_planes->fill(zero_plane);
    }
}

void UnpackInputPlanes(
    const InputPlanes& planes,
    float* float_planes,
    int width,
    int height) {
    
    const int plane_size = width * height;
    assert(width <= Stockfish::FILE_NB && height <= Stockfish::RANK_NB);
    
    // 1. Khởi tạo toàn bộ tensor về 0.0f bằng một lệnh memset toàn cục duy nhất
    std::memset(float_planes, 0, planes.size() * plane_size * sizeof(float));
    
    // 2. Duyệt qua từng plane, chỉ ghi đè giá trị nếu plane đó không trống (mask != 0)
    for (size_t p = 0; p < planes.size(); ++p) {
        const auto& plane = planes[p];
        if (!plane.mask) {
            continue; // Bỏ qua nhanh vì vùng nhớ đã được zero-init toàn cục
        }
        
        float* dest = float_planes + p * plane_size;
        
        // 3. Nếu plane được lấp đầy hoàn toàn (mask == AllSquares), ta điền giá trị plane.value
        if (plane.mask == Stockfish::AllSquares) {
            std::fill_n(dest, plane_size, plane.value);
            continue;
        }
        
        // 4. Ngược lại, duyệt qua các bit 1 trong mask
        Stockfish::Bitboard b = plane.mask;
        while (b) {
            Stockfish::Square sq = Stockfish::pop_lsb(b);
            int f = Stockfish::file_of(sq);
            int r = Stockfish::rank_of(sq);
            dest[r * width + f] = plane.value;
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
