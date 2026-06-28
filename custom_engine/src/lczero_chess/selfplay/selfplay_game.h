#pragma once
#include <string>
#include <cstdint>

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
//
// Early resignation (throughput optimization, plan A5):
//   resign_threshold    : if the side-to-move's best_q stays <= this for
//                         `resign_consecutive` of ITS OWN consecutive moves, that
//                         side resigns (the opponent is awarded the win). A value
//                         <= -1.0 disables resign entirely (best_q in [-1,1]).
//   resign_consecutive  : how many consecutive own-moves below threshold trigger.
//   allow_resign        : per-game switch; the driver sets it false for a fraction
//                         of games ("no-resign") so the net still learns to defend
//                         lost positions and to convert won ones to the very end.
GameResult PlayOneGame(const std::string& start_fen, Backend* backend,
                       const OptionsDict& options, int visits, int max_moves,
                       int temp_cutoff_ply, const std::string& out_filename,
                       int search_threads = 1, bool verbose = true,
                       float resign_threshold = -2.0f,
                       int resign_consecutive = 3, bool allow_resign = true,
                       int resign_earliest_move = 0,
                       int64_t* out_nodes = nullptr,   // += total MCTS playouts (NPS)
                       int* out_final_pieces = nullptr,  // số quân còn lại trên bàn (cả 2 bên + royal) lúc ván kết thúc
                       // Điểm hệ số tấn công TÍCH LUỸ: ở mỗi thế cờ, đếm số quân của một bên đang
                       // ở NỬA BÀN đối phương; cộng dồn qua mọi thế cờ. Trắng tấn công = quân Trắng
                       // ở nửa Đen (hạng 6-10); Đen tấn công = quân Đen ở nửa Trắng (hạng 1-5).
                       int64_t* out_white_attack = nullptr,
                       int64_t* out_black_attack = nullptr);

}  // namespace lczero
