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
#include "app/variant_setup.h"


using namespace Stockfish;


// Full Fairy-Stockfish global init — the exact sequence main.cc runs before any
// mode. The Android FFI path (fz_create) has no main(), so it must run this once
// itself; otherwise bitboards/magics/options/threads are uninitialized and the
// engine segfaults at startup. Idempotent.
void init_engine_globals() {
    static std::once_flag once;
    std::call_once(once, [] {
        static const char* kArgv[] = {"fairyzero"};
        pieceMap.init();
        variants.init();
        CommandLine::init(1, const_cast<char**>(kArgv));
        UCI::init(Options);
        Tune::init();
        PSQT::init(variants.find(Options["UCI_Variant"])->second);
        Bitboards::init();
        Position::init();
        Bitbases::init();
        Endgames::init();
        Threads.set(size_t(Options["Threads"]));
        Search::clear();
        Eval::NNUE::init();
    });
}

const Variant* setup_custom_variant() {
    std::string ini_text = R"(
[custom_10x10_variant]
maxRank = 10
maxFile = j
pawn = p
knight = n
bishop = b
rook = r
queen = q
king = k:KN
amazon = a
chancellor = e
archbishop = h
centaur = m
customPiece1 = v:CN
customPiece2 = y:AD
customPiece3 = s:fKifmnDifmnA
pawnTypes = p s
promotionPawnTypes = p s
enPassantTypes = p s
nMoveRuleTypes = p s
doubleStep = true
doubleStepRegionWhite = *1 *2 *3
doubleStepRegionBlack = *10 *9 *8
promotionRegionWhite = *8 *9 *10
promotionRegionBlack = *3 *2 *1
mandatoryPawnPromotion = true
promotionPieceTypes = b m n r v y
castling = true
castlingKingsideFile = h
castlingQueensideFile = d
castlingRookKingsideFile = i
castlingRookQueensideFile = b
stalemateValue = loss
checkCounting = true
)";
    std::istringstream ss(ini_text);
    variants.parse_istream<false>(ss);
    const Variant* v = variants.find("custom_10x10_variant")->second;
    if (!v) {
        std::cerr << "[FATAL] custom_10x10_variant not found!" << std::endl;
        std::exit(1);
    }
    UCI::init_variant(v);
    PSQT::init(v);
    return v;
}

// T5 helper: emit ground-truth round-trip data so the Python reader can be
// verified bit/value-exact. For each case writes BOTH:
//   <prefix>_records.gz  : TrainingDataV1 records (the sparse format).
//   <prefix>_dense.bin   : the [226*100] float tensor from UnpackInputPlanes
//                          (exactly what the NN sees) for the SAME position.
// Python reconstructs the dense tensor from the record and compares to _dense.bin.
