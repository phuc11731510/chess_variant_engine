#pragma once

#include <string>
#include <vector>
#include <span>
#include <array>
#include "../../chess/position.h"
#include "nn_layout.h"
#include "types.h"
#include "position.h"

namespace lczero {

enum class FillEmptyHistory { NO, FEN_ONLY, ALWAYS };

// Cấu trúc đại diện cho một mặt phẳng đầu vào (Plane) được tối ưu hóa cho bàn cờ 10x10.
// Sử dụng Stockfish::Bitboard (128-bit) thay vì uint64_t của Lc0 để lưu trữ đầy đủ 100 ô cờ.
struct InputPlane {
    InputPlane() = default;
    
    void SetAll() { mask = Stockfish::AllSquares; }
    
    void Fill(float val) {
        SetAll();
        value = val;
    }
    
    Stockfish::Bitboard mask = 0;
    float value = 1.0f;
};

using InputPlanes = std::array<InputPlane, kInputPlanes>;

// Bố cục mặt phẳng (nn_layout.h): với mỗi bước lịch sử d = 0..7: kPieceKinds mặt phẳng quân của bên đi,
// kPieceKinds của đối phương, 1 mặt phẳng lặp thế; sau đó các mặt phẳng phụ trợ (enum AuxPlane).

// Hàm mã hóa lịch sử thế cờ thành các mặt phẳng đầu vào (InputPlanes) cho Neural Network.
// Chi tiết logic của hàm sẽ được cài đặt ở Giai đoạn 4.
// Tối ưu hóa: Nhận vào một con trỏ tới InputPlanes đã được cấp phát sẵn để tránh cấp phát heap liên tục.
void EncodePositionForNN(
    const PositionHistory& history,
    int history_planes,
    FillEmptyHistory fill_empty_history,
    InputPlanes* output_planes,
    int* transform_out);

// Hàm chuyển đổi (unpack) từ cấu trúc thưa `InputPlanes` (chứa các bitmask/Bitboard)
// sang mảng float phẳng liên tục `float_planes` để đưa vào ONNX Runtime.
// `float_planes` phải được cấp phát sẵn với kích thước: planes.size() * width * height
// Does the encoder know every piece of `v` (an input plane each) and every piece a pawn of `v` can promote to
// (a policy slot each)? A piece it does not know would silently vanish from the network input; `why` says which.
bool EncoderCoversVariant(const Stockfish::Variant& v, std::string* why = nullptr);

void UnpackInputPlanes(
    const InputPlanes& planes,
    float* float_planes,
    int width,
    int height);

uint16_t MoveToNNIndex(Move move, int transform = 0);
Move MoveFromNNIndex(int idx, int transform = 0);

} // namespace lczero
