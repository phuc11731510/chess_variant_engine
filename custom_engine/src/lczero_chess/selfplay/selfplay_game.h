#pragma once
#include <string>

#include "chess/position.h"  // GameResult
#include "neural/backend.h"
#include "utils/optionsdict.h"

namespace lczero {

// Plays one full self-play game from `start_fen` and writes a training record
// for EVERY position (no filtering) to `out_filename` via TrainingDataWriter.
//
//   backend        : the (caching) backend used for all searches.
//   options        : search options (noise, fpu, cpuct, ...).
//   visits         : NEW MCTS playouts per move.
//   max_moves      : hard cap on game length (cutoff -> adjudicated as draw).
//   temp_cutoff_ply: plies below this are sampled with temperature=1 (visit
//                    proportional) for opening diversity; greedy afterwards.
//   search_threads : threads per search.
//
// At game end, z (result_q/d) is assigned to all records with correct parity.
// Search/NodeTree are heap-allocated (PositionHistory has 512-ply static arrays).
// Returns the (possibly adjudicated) game result.
// `verbose`: print each played move to stdout (kept ON for single-game tests;
//            the parallel driver passes false to avoid interleaved log spam).
GameResult PlayOneGame(const std::string& start_fen, Backend* backend,
                       const OptionsDict& options, int visits, int max_moves,
                       int temp_cutoff_ply, const std::string& out_filename,
                       int search_threads = 1, bool verbose = true);

}  // namespace lczero
