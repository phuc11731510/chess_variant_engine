#include "selfplay/selfplay_driver.h"

#include <atomic>
#include <chrono>
#include <filesystem>
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

#include "selfplay/selfplay_game.h"
#include "trainingdata/writer.h"

namespace lczero {

void RunSelfPlay(const SelfPlayConfig& cfg, Backend* backend,
                 const OptionsDict& options) {
  std::error_code ec;
  std::filesystem::create_directories(cfg.out_dir, ec);  // best-effort

  const int workers = std::max(1, cfg.parallel);
  std::atomic<int> next_game{0};
  std::atomic<int> w_wins{0}, b_wins{0}, draws{0}, done{0};
  std::mutex log_mu;
  const auto t0 = std::chrono::steady_clock::now();

  std::cout << "[selfplay] Generating " << cfg.num_games << " games into '"
            << cfg.out_dir << "' (" << workers << " parallel x "
            << cfg.threads_per_game << " threads/game, visits=" << cfg.visits
            << ", max_moves=" << cfg.max_moves << ")" << std::endl;

  auto worker = [&]() {
    while (true) {
      const int g = next_game.fetch_add(1);
      if (g >= cfg.num_games) break;

      const std::string fname = cfg.out_dir + "/game_" + std::to_string(g) +
                                TrainingDataWriter::Extension();
      // Diverse openings: cycle through the opening book if provided.
      const std::string& fen = cfg.start_fens.empty()
          ? cfg.start_fen
          : cfg.start_fens[g % static_cast<int>(cfg.start_fens.size())];
      const GameResult r =
          PlayOneGame(fen, backend, options, cfg.visits,
                      cfg.max_moves, cfg.temp_cutoff_ply, fname,
                      cfg.threads_per_game, /*verbose=*/false);

      if (r == GameResult::WHITE_WON)
        w_wins.fetch_add(1);
      else if (r == GameResult::BLACK_WON)
        b_wins.fetch_add(1);
      else
        draws.fetch_add(1);

      const int d = done.fetch_add(1) + 1;
      {
        std::lock_guard<std::mutex> lk(log_mu);
        std::cout << "[selfplay] " << d << "/" << cfg.num_games
                  << "  (game " << g << " -> result=" << static_cast<int>(r)
                  << ")" << std::endl;
      }
    }
  };

  std::vector<std::thread> pool;
  pool.reserve(workers);
  for (int i = 0; i < workers; ++i) pool.emplace_back(worker);
  for (auto& t : pool) t.join();

  const double secs =
      std::chrono::duration_cast<std::chrono::milliseconds>(
          std::chrono::steady_clock::now() - t0)
          .count() /
      1000.0;
  std::cout << "\n[selfplay] Finished " << cfg.num_games << " games in " << secs
            << "s.\n"
            << "  White wins: " << w_wins.load()
            << " | Black wins: " << b_wins.load()
            << " | Draws: " << draws.load() << "\n"
            << "  Output dir: " << cfg.out_dir << std::endl;
}

}  // namespace lczero
