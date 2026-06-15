#pragma once

#include <vector>
#include <span>
#include "../../chess/position.h"
#include "types.h"
#include "position.h"

namespace lczero {

constexpr int kMoveHistory = 8;
constexpr int kPlanesPerBoard = 27; // 13 piece types for each side + 1 repetition plane
constexpr int kAuxPlanesCount = 10; // 8 standard Lc0 aux planes + 2 check count planes (White & Black)
constexpr int kAuxPlaneBase = kPlanesPerBoard * kMoveHistory;

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

using InputPlanes = std::vector<InputPlane>;

/*
 * Cấu trúc 10 mặt phẳng phụ trợ (Auxiliary Planes) bắt đầu từ chỉ số kAuxPlaneBase:
 * 
 * - Plane 0: Vị trí Rook trắng có quyền nhập thành Queenside (A-side)
 * - Plane 1: Vị trí Rook trắng có quyền nhập thành Kingside (H-side)
 * - Plane 2: Vị trí Rook đen có quyền nhập thành Queenside (A-side)
 * - Plane 3: Vị trí Rook đen có quyền nhập thành Kingside (H-side)
 * - Plane 4: Ô En Passant hiện tại (nếu có)
 * - Plane 5: Rule 50 (Chuẩn hóa: rule50_ply / 100.0f)
 * - Plane 6: Side to move (All ones if Black to move)
 * - Plane 7: All ones (Giúp Neural Network nhận biết biên bàn cờ)
 * - Plane 8: White check count remaining (Chuẩn hóa: checks_remaining / 7.0f)
 * - Plane 9: Black check count remaining (Chuẩn hóa: checks_remaining / 7.0f)
 */

// Hàm mã hóa lịch sử thế cờ thành các mặt phẳng đầu vào (InputPlanes) cho Neural Network.
// Chi tiết logic của hàm sẽ được cài đặt ở Giai đoạn 4.
InputPlanes EncodePositionForNN(
    const PositionHistory& history,
    int history_planes,
    FillEmptyHistory fill_empty_history,
    int* transform_out);

InputPlanes EncodePositionForNN(
    std::span<const Position> positions,
    int history_planes,
    FillEmptyHistory fill_empty_history,
    int* transform_out);

} // namespace lczero
