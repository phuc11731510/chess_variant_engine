#include <iostream>
#include <string>
#include <vector>
#include <sstream>
#include <cassert>

#include "bitboard.h"
#include "endgame.h"
#include "position.h"
#include "psqt.h"
#include "search.h"
#include "syzygy/tbprobe.h"
#include "thread.h"
#include "tt.h"
#include "uci.h"
#include "piece.h"
#include "variant.h"
#include "xboard.h"
#include "movegen.h"
#include "chess/board.h"
#include "chess/position.h"
#include "chess/gamestate.h"
#include "chess/encoder.h"
#include "trainingdata/trainingdata_v1.h"
#include "trainingdata/writer.h"
#include "selfplay/training_extract.h"
#include "selfplay/selfplay_game.h"
#include "selfplay/selfplay_driver.h"
#include <cstring>
#include <cstdlib>
#include <fstream>
#include <cstdio>
#include <cmath>
#include <thread>
#include <atomic>
#include <mutex>
#include <chrono>
#include <memory>
#include <map>
#include <functional>
#include <algorithm>
#include "search/classic/search.h"
#include "search/classic/params.h"
#include "neural/backend.h"
#include "neural/shared_params.h"
#include "neural/onnx_backend.h"
#include "neural/zero_heap_cache.h"
#include "utils/random.h"
#include "chess/callbacks.h"
#include "app/uci_coords.h"


using namespace Stockfish;


extern const char* const kUciStartFen =
    "vrhbakberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHBAKBERV w BIbi - 7+7 0 1";

// --- Move I/O: 2-way canonical<->real mapping (locks risk #1). ---
// The lczero layer works in the canonical (side-to-move-flipped) frame; the GUI
// uses real board coords. Self-play already maps canonical->real for DISPLAY via
// Move::Flip(RANK_10) when Black is to move; we reuse the exact same convention
// for BOTH directions so format and parse are mutual inverses by construction.
std::string CanonicalMoveToUci(lczero::Move m, bool black_to_move) {
    lczero::Move d = m;
    if (black_to_move) d.Flip(Stockfish::RANK_10);  // canonical -> real coords
    return d.ToString();                            // a1..j10 (+ promo suffix)
}

// Finds the canonical legal move whose real-coord UCI string equals `uci`.
// Returns MOVE_NONE if no legal move matches (illegal / malformed input).
lczero::Move UciToCanonicalMove(const lczero::ChessBoard& board,
                                       const std::string& uci, bool black_to_move) {
    lczero::MoveList legal = board.GenerateLegalMoves();   // canonical frame
    for (size_t i = 0; i < legal.size(); ++i) {
        if (CanonicalMoveToUci(legal[i], black_to_move) == uci) return legal[i];
    }
    return lczero::MOVE_NONE;
}

// Stopper that never fires (for `go infinite`; ends only on Stop()).
