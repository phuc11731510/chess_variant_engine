#include "encoder.h"

namespace lczero {

InputPlanes EncodePositionForNN(
    const PositionHistory& history,
    int history_planes,
    FillEmptyHistory fill_empty_history,
    int* transform_out) {
    
    if (transform_out) {
        *transform_out = 0; // NoTransform
    }
    
    // Giai đoạn 4: Triển khai chi tiết thuật toán mã hóa trạng thái bàn cờ 10x10.
    // Tạm thời trả về vector với số planes mặc định (kAuxPlaneBase + kAuxPlanesCount).
    return InputPlanes(kAuxPlaneBase + kAuxPlanesCount);
}

InputPlanes EncodePositionForNN(
    std::span<const Position> positions,
    int history_planes,
    FillEmptyHistory fill_empty_history,
    int* transform_out) {
    
    if (transform_out) {
        *transform_out = 0;
    }
    
    return InputPlanes(kAuxPlaneBase + kAuxPlanesCount);
}

} // namespace lczero
