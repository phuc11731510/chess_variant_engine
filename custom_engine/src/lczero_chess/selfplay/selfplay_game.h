#pragma once
#include <string>
#include <atomic>
#include <cstdint>
#include <vector>

#include "chess/position.h"  // GameResult
#include "neural/backend.h"
#include "search/classic/node.h"  // classic::NodeTree
#include "utils/optionsdict.h"

namespace lczero {

// Runs the MCTS search for ONE self-play move on `tree`'s current head: exactly
// the search PlayOneGame performs before each move (same stopper, options and
// thread count). The head's old subtree is discarded first, so every move is a
// fresh search whose root gets Dirichlet noise (as in lc0 self-play and
// AlphaZero). Returns the number of NEW playouts it performed. The Search is
// fully destroyed before this returns, so the caller may read the tree and play
// a move on it. Exposed so the tests exercise the production path.
int64_t SearchSelfPlayMove(classic::NodeTree* tree, Backend* backend,
                           const OptionsDict& options, int visits,
                           int search_threads);

// How every move of a self-play game is searched and chosen (2026-11-20, owner's decisions).
//
// Playout cap randomization (PCR, Wu 2019 "Accelerating Self-Play Learning in Go"): before EACH
// move a coin decides between a full search (`full_visits`, searched with the plain options) and a
// shallow one (`fast_visits`, searched with `fast_options`: its own c_puct and Dirichlet epsilon).
// Only full searches may train the policy head, so a shallow move's record carries fast_search = 1
// (the trainer masks its policy loss); its value and moves-left targets are trained as usual.
//
// The move actually played is drawn for EVERY move of the game with weight (N / N_max)^(1 / T) over
// the root moves' visit counts N (T = `temperature`; T <= 0 means the most visited move). The
// training label (the policy target) stays the visit fraction; the temperature only affects play.
struct SelfPlaySearchPlan {
  int full_visits = 800;
  int fast_visits = 200;
  float fast_prob = 0.0f;     // chance that a move is searched shallowly; 0 = PCR off
  float temperature = 0.5f;
  // Options of the shallow searches (a child of the full options that overrides c_puct and the
  // noise epsilon). nullptr = the shallow searches use the full options too.
  const OptionsDict* fast_options = nullptr;
};

// The coin of PCR: true with probability `fast_prob` (never for <= 0, always for >= 1).
bool ChooseFastSearch(float fast_prob);

// Probability of playing each root move, from the moves' visit counts: (N / N_max)^(1 / T),
// normalised. T <= 0: spread evenly over the most visited moves. Empty / all-zero visits: all
// zeros. Pure function (the sampling below uses it), exposed for the tests.
std::vector<double> MoveChoiceProbabilities(const std::vector<uint32_t>& visits,
                                            float temperature);

// Index drawn by `toss` in [0, 1) from `probabilities` (cumulative); the last non-zero entry
// when rounding leaves a gap at the top. -1 if every probability is 0.
int SampleIndex(const std::vector<double>& probabilities, double toss);

// Plays one full self-play game from `start_fen` and writes a training record
// for EVERY position (no filtering) to `out_filename` via TrainingDataWriter.
//
//   backend        : the (caching) backend used for all searches.
//   options        : search options of the FULL searches (noise, fpu, cpuct, ...).
//   plan           : visits of both search kinds, the PCR coin, the temperature of the move
//                    choice and the options of the shallow searches (see SelfPlaySearchPlan).
//   max_moves      : hard cap on game length (cutoff -> adjudicated as draw).
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
                       const OptionsDict& options, const SelfPlaySearchPlan& plan,
                       int max_moves, const std::string& out_filename,
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
                       int64_t* out_black_attack = nullptr,
                       // Records written (= moves played) and how many of them were shallow searches.
                       int* out_moves = nullptr, int* out_fast_moves = nullptr);

// Process-wide playouts searched so far, added after EVERY move (out_nodes only
// arrives when a game ends). For the driver's per-minute throughput lines.
extern std::atomic<int64_t> g_live_playouts;

}  // namespace lczero
