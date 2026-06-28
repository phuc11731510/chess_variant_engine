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
#include "utils/random.h"

namespace lczero {

void RunSelfPlay(const SelfPlayConfig& cfg, Backend* backend,
                 const OptionsDict& options) {
  std::error_code ec;
  std::filesystem::create_directories(cfg.out_dir, ec);  // best-effort

  const int workers = std::max(1, cfg.parallel);
  std::atomic<int> next_game{0};
  std::atomic<int> w_wins{0}, b_wins{0}, draws{0}, done{0};
  std::atomic<int64_t> total_nodes{0};   // sum of MCTS playouts (all workers) -> NPS
  std::atomic<int64_t> total_final_pieces{0};  // sum of pieces-left-on-board at game end
  std::atomic<int64_t> total_white_attack{0}, total_black_attack{0};  // cumulative attack scores
  std::atomic<int> w_more_aggr{0}, b_more_aggr{0};  // games where each side attacked more
  // P(bên công nhiều hơn thắng): chỉ tính ván CÓ thắng-bại VÀ có bên-công-rõ (wa != ba).
  std::atomic<int> aggr_decisive{0}, aggr_won{0};
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
      // Per-game no-resign decision: a fraction of games keep resign OFF so the
      // net still sees lost/won positions played to the very end (plan A5).
      const bool allow_resign =
          cfg.no_resign_frac <= 0.0f ||
          Random::Get().GetDouble(1.0) >= cfg.no_resign_frac;
      int64_t game_nodes = 0;
      int game_pieces = 0;
      int64_t game_wa = 0, game_ba = 0;
      const GameResult r =
          PlayOneGame(fen, backend, options, cfg.visits,
                      cfg.max_moves, cfg.temp_cutoff_ply, fname,
                      cfg.threads_per_game, /*verbose=*/false,
                      cfg.resign_threshold, cfg.resign_consecutive, allow_resign,
                      cfg.resign_earliest_move, &game_nodes, &game_pieces,
                      &game_wa, &game_ba);
      total_nodes.fetch_add(game_nodes);
      total_final_pieces.fetch_add(game_pieces);
      total_white_attack.fetch_add(game_wa);
      total_black_attack.fetch_add(game_ba);
      if (game_wa > game_ba) w_more_aggr.fetch_add(1);
      else if (game_ba > game_wa) b_more_aggr.fetch_add(1);
      // Joint: bên-công-nhiều-hơn có trùng bên-thắng không? (chỉ ván phân thắng-bại + công rõ)
      const bool decisive =
          (r == GameResult::WHITE_WON || r == GameResult::BLACK_WON);
      if (decisive && game_wa != game_ba) {
        aggr_decisive.fetch_add(1);
        const bool white_attacked_more = game_wa > game_ba;
        const bool white_won = (r == GameResult::WHITE_WON);
        if (white_attacked_more == white_won) aggr_won.fetch_add(1);
      }

      if (r == GameResult::WHITE_WON)
        w_wins.fetch_add(1);
      else if (r == GameResult::BLACK_WON)
        b_wins.fetch_add(1);
      else
        draws.fetch_add(1);

      const int d = done.fetch_add(1) + 1;
      {
        std::lock_guard<std::mutex> lk(log_mu);
        const char* more = game_wa > game_ba ? "W" : game_ba > game_wa ? "B" : "=";
        std::cout << "[selfplay] " << d << "/" << cfg.num_games
                  << "  (game " << g << " -> result=" << static_cast<int>(r)
                  << ", pieces=" << game_pieces
                  << ", cong W=" << game_wa << " B=" << game_ba
                  << " -> " << more << ")";
        if (cfg.show_nps) {
          const double el = std::chrono::duration_cast<std::chrono::milliseconds>(
                                std::chrono::steady_clock::now() - t0).count() / 1000.0;
          const long nps = el > 0.0 ? static_cast<long>(total_nodes.load() / el) : 0;
          std::cout << "  | " << nps << " nps (tong)";
        }
        std::cout << std::endl;
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
  std::cout << "\n[selfplay] Finished " << cfg.num_games << " games in " << secs << "s";
  if (cfg.show_nps) {
    const long nps_final = secs > 0.0 ? static_cast<long>(total_nodes.load() / secs) : 0;
    std::cout << "  (" << nps_final << " nps tong, " << total_nodes.load() << " playouts)";
  }
  const double avg_pieces =
      cfg.num_games > 0
          ? static_cast<double>(total_final_pieces.load()) / cfg.num_games
          : 0.0;
  const double avg_wa = cfg.num_games > 0
      ? static_cast<double>(total_white_attack.load()) / cfg.num_games : 0.0;
  const double avg_ba = cfg.num_games > 0
      ? static_cast<double>(total_black_attack.load()) / cfg.num_games : 0.0;
  // P(bên công nhiều hơn thắng) = số ván bên-công-nhiều THẮNG / số ván phân thắng-bại + công rõ.
  const int aggr_dec = aggr_decisive.load(), aggr_w = aggr_won.load();
  const double aggr_pct = aggr_dec > 0 ? 100.0 * aggr_w / aggr_dec : 0.0;
  std::cout << ".\n"
            << "  White wins: " << w_wins.load()
            << " | Black wins: " << b_wins.load()
            << " | Draws: " << draws.load() << "\n"
            << "  So quan con lai trung binh luc ket thuc: " << avg_pieces << "\n"
            << "  Diem tan cong tich luy trung binh moi van: Trang=" << avg_wa
            << "  Den=" << avg_ba << "\n"
            << "  So van moi ben choi the cong nhieu hon: Trang=" << w_more_aggr.load()
            << " | Den=" << b_more_aggr.load() << "\n"
            << "  Ben cong nhieu hon THANG: " << aggr_w << "/" << aggr_dec
            << " van (" << aggr_pct << "%)\n"
            << "  Output dir: " << cfg.out_dir << std::endl;
}

}  // namespace lczero
