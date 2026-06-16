#include "encoder.h"
#include <cstring>
#include <algorithm>

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
        constexpr size_t target_size = kAuxPlaneBase + kAuxPlanesCount;
        if (output_planes->size() != target_size) {
            output_planes->resize(target_size);
        }
        // Khởi tạo/Reset lại các plane để tái sử dụng buffer cũ bằng std::fill_n (được compiler tối ưu thành memset/SIMD)
        InputPlane zero_plane;
        zero_plane.mask = 0;
        zero_plane.value = 0.0f;
        std::fill_n(output_planes->data(), target_size, zero_plane);
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
        constexpr size_t target_size = kAuxPlaneBase + kAuxPlanesCount;
        if (output_planes->size() != target_size) {
            output_planes->resize(target_size);
        }
        InputPlane zero_plane;
        zero_plane.mask = 0;
        zero_plane.value = 0.0f;
        std::fill_n(output_planes->data(), target_size, zero_plane);
    }
}

void UnpackInputPlanes(
    const InputPlanes& planes,
    float* float_planes,
    int width,
    int height) {
    
    const int plane_size = width * height;
    
    for (size_t p = 0; p < planes.size(); ++p) {
        const auto& plane = planes[p];
        float* dest = float_planes + p * plane_size;
        
        // 1. Nếu plane trống (mask == 0), ta gán toàn bộ = 0.0f
        if (!plane.mask) {
            std::memset(dest, 0, plane_size * sizeof(float));
            continue;
        }
        
        // 2. Nếu plane được lấp đầy hoàn toàn (mask == AllSquares), ta gán giá trị plane.value
        if (plane.mask == Stockfish::AllSquares) {
            std::fill_n(dest, plane_size, plane.value);
            continue;
        }
        
        // 3. Ngược lại, gán toàn bộ = 0.0f, sau đó duyệt qua các bit 1 trong mask
        std::memset(dest, 0, plane_size * sizeof(float));
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

} // namespace lczero
