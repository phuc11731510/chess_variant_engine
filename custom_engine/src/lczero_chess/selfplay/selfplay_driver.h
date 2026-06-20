#pragma once
#include <string>
#include <vector>

#include "neural/backend.h"
#include "utils/optionsdict.h"

namespace lczero {

// Configuration for a batch of self-play games.
struct SelfPlayConfig {
  std::string start_fen;          // starting position FEN (used if start_fens empty).
  std::vector<std::string> start_fens;  // opening book: pick one per game (diverse openings).
  std::string out_dir = "selfplay_data";  // output directory (1 .gz per game).
  int num_games = 100;            // total games to generate.
  int visits = 200;               // NEW MCTS playouts per move.
  int max_moves = 200;            // hard cap per game (cutoff -> draw).
  int temp_cutoff_ply = 30;       // plies below this use temperature sampling.
  int parallel = 1;               // games played concurrently (worker threads).
  int threads_per_game = 1;       // MCTS threads within each game.
};

// Generates `cfg.num_games` self-play games into `cfg.out_dir`. Games run on
// `cfg.parallel` worker threads pulling from a shared counter; ALL games share
// one `backend` (its ONNX session and ZeroHeapCache are thread-safe). Prints
// per-game progress and a final summary. Blocks until all games finish.
void RunSelfPlay(const SelfPlayConfig& cfg, Backend* backend,
                 const OptionsDict& options);

}  // namespace lczero
