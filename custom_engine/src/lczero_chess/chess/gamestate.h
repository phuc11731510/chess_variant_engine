#pragma once
#include <vector>
#include <numeric>
#include <algorithm>
#include "position.h"

namespace lczero {

struct GameState {
    Position startpos;
    std::vector<Move> moves;

    Position CurrentPosition() const {
        Position result = startpos;
        for (Move m : moves) {
            result = Position(result, m);
        }
        return result;
    }

    std::vector<Position> GetPositions() const {
        std::vector<Position> positions;
        positions.reserve(moves.size() + 1);
        positions.push_back(startpos);
        for (Move m : moves) {
            positions.push_back(Position(positions.back(), m));
        }
        return positions;
    }
};

} // namespace lczero
