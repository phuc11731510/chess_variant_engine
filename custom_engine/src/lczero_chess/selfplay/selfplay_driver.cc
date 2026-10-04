#include "selfplay/selfplay_driver.h"

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdio>
#include <filesystem>
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

#include "neural/onnx_backend.h"  // OnnxGetEvalCounters (throughput report)
#include "search/classic/search.h"  // g_playout_stats
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
  std::atomic<bool> stopped_by_time{false};  // set once when the wall-clock budget ends the run
  std::atomic<bool> stopped_by_file{false};  // set once when --stop-file ends the run
  std::mutex log_mu;
  const auto t0 = std::chrono::steady_clock::now();  // reference for --max-seconds (first game)

  std::cout << "[selfplay] Generating " << cfg.num_games << " games into '"
            << cfg.out_dir << "' (" << workers << " parallel x "
            << cfg.threads_per_game << " threads/game, visits=" << cfg.visits
            << ", max_moves=" << cfg.max_moves << ")";
  if (cfg.max_seconds > 0.0)
    std::cout << " [gioi han thoi gian: " << cfg.max_seconds << "s]";
  if (!cfg.stop_file.empty())
    std::cout << " [dung mem khi co tep: " << cfg.stop_file << "]";
  std::cout << std::endl;

  auto worker = [&]() {
    while (true) {
      // Optional wall-clock budget. Checked ONCE PER GAME here (this loop iterates
      // once per full game, ~seconds-to-minutes apart) — NEVER inside the MCTS/move
      // hot path. When off (max_seconds<=0) it's a single double-compare per game
      // and reads no clock, so the impact on self-play nps is effectively zero.
      // Hitting the budget only stops taking NEW games; in-flight games finish
      // normally (each still writes a complete game file — no truncated training data).
      if (cfg.max_seconds > 0.0) {
        const double el = std::chrono::duration_cast<std::chrono::milliseconds>(
                              std::chrono::steady_clock::now() - t0).count() / 1000.0;
        if (el >= cfg.max_seconds) {
          if (!stopped_by_time.exchange(true)) {
            std::lock_guard<std::mutex> lk(log_mu);
            std::cout << "[selfplay] Dat nguong thoi gian " << cfg.max_seconds
                      << "s -> ngung nhan van moi (da xong " << done.load()
                      << " van, cac van dang chay se hoan tat)." << std::endl;
          }
          break;
        }
      }
      // Soft stop on demand (--stop-file, e.g. the phone menu when several machines
      // together reached their target): same place and cost as the budget above --
      // one stat() per game, never in the search. In-flight games finish normally.
      if (!cfg.stop_file.empty()) {
        std::error_code fe;
        if (std::filesystem::exists(cfg.stop_file, fe)) {
          if (!stopped_by_file.exchange(true)) {
            std::lock_guard<std::mutex> lk(log_mu);
            std::cout << "[selfplay] Co tep dung " << cfg.stop_file
                      << " -> ngung nhan van moi (da xong " << done.load()
                      << " van, cac van dang chay se hoan tat)." << std::endl;
          }
          break;
        }
      }
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

  // Producers are registered BEFORE any worker starts (else the first batches
  // would launch with whatever the first thread submitted) and each worker
  // unregisters its threads when it stops taking games.
  const int tpg = std::max(1, cfg.threads_per_game);
  if (cfg.producer_enter)
    for (int i = 0; i < workers * tpg; ++i) cfg.producer_enter();
  std::atomic<int> active_workers{workers};
  auto worker_then_leave = [&]() {
    worker();
    active_workers.fetch_sub(1);
    if (cfg.producer_leave)
      for (int i = 0; i < tpg; ++i) cfg.producer_leave();
  };
  std::vector<std::thread> pool;
  pool.reserve(workers);
  for (int i = 0; i < workers; ++i) pool.emplace_back(worker_then_leave);

  // --show-nps: one throughput line per minute over THAT minute (playouts are
  // counted per move, NN counters per Run), so the steady phase can be told
  // apart from the soft-stop tail when comparing configurations.
  std::mutex tick_mu;
  std::condition_variable tick_cv;
  bool all_joined = false;
  std::thread ticker;
  if (cfg.show_nps) {
    ticker = std::thread([&] {
      int64_t last_nodes = g_live_playouts.load();
      OnnxEvalCounters last_ev = OnnxGetEvalCounters();
      auto last_t = std::chrono::steady_clock::now();
      std::unique_lock<std::mutex> lk(tick_mu);
      while (!tick_cv.wait_for(lk, std::chrono::seconds(60), [&] { return all_joined; })) {
        const auto now = std::chrono::steady_clock::now();
        const double dt = std::chrono::duration<double>(now - last_t).count();
        const int64_t nodes = g_live_playouts.load();
        const OnnxEvalCounters ev = OnnxGetEvalCounters();
        const double runs = static_cast<double>(ev.runs - last_ev.runs);
        const double real = static_cast<double>(ev.real - last_ev.real);
        const double padded = static_cast<double>(ev.padded - last_ev.padded);
        const double el = std::chrono::duration<double>(now - t0).count();
        std::lock_guard<std::mutex> lg(log_mu);
        // GPU busy = share of the minute spent inside session->Run(); "tinh" adds
        // the CPU post-processing (softmax, copies) the batcher thread does after.
        const double run_s = static_cast<double>(ev.run_ns - last_ev.run_ns) * 1e-9;
        const double comp_s = static_cast<double>(ev.compute_ns - last_ev.compute_ns) * 1e-9;
        std::printf("[nhip] t=%.0fs  %d van dang chay  %.0f nps  %.0f eval/s  batch TB %.1f  pad %.1f%%"
                    "  GPU ban %.1f%%  tinh %.1f%%  Run TB %.2f ms\n",
                    el, active_workers.load(), (nodes - last_nodes) / dt, real / dt,
                    runs > 0 ? real / runs : 0.0,
                    padded > 0 ? 100.0 * (padded - real) / padded : 0.0,
                    100.0 * run_s / dt, 100.0 * comp_s / dt,
                    runs > 0 ? 1000.0 * run_s / runs : 0.0);
        std::fflush(stdout);
        last_nodes = nodes;
        last_ev = ev;
        last_t = now;
      }
    });
  }
  for (auto& t : pool) t.join();
  if (ticker.joinable()) {
    {
      std::lock_guard<std::mutex> lk(tick_mu);
      all_joined = true;
    }
    tick_cv.notify_all();
    ticker.join();
  }

  const double secs =
      std::chrono::duration_cast<std::chrono::milliseconds>(
          std::chrono::steady_clock::now() - t0)
          .count() /
      1000.0;
  // Games ACTUALLY finished (== game files written). Equals num_games normally, but
  // is smaller when --max-seconds ended the run early; ALL averages use this count.
  const int completed = done.load();
  std::cout << "\n[selfplay] Finished " << completed << "/" << cfg.num_games
            << " games in " << secs << "s";
  if (stopped_by_time.load())
    std::cout << " (dung som do dat nguong --max-seconds)";
  else if (stopped_by_file.load())
    std::cout << " (dung som do tep --stop-file)";
  if (cfg.show_nps) {
    const long nps_final = secs > 0.0 ? static_cast<long>(total_nodes.load() / secs) : 0;
    std::cout << "  (" << nps_final << " nps tong, " << total_nodes.load()
              << " playout MOI)";
  }
  const double avg_pieces =
      completed > 0
          ? static_cast<double>(total_final_pieces.load()) / completed
          : 0.0;
  const double avg_wa = completed > 0
      ? static_cast<double>(total_white_attack.load()) / completed : 0.0;
  const double avg_ba = completed > 0
      ? static_cast<double>(total_black_attack.load()) / completed : 0.0;
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
            << " van (" << aggr_pct << "%)\n";

  // --- Throughput: the numbers that actually decide where the time goes ------
  // van/gio is the objective. The NN counters below say whether the device is
  // the limit: eval/s is real GPU work, batch TB shows how full each Run() was,
  // and "phi do pad" is GPU time spent on fixed-batch zero padding.
  if (completed > 0 && secs > 0.0) {
    const auto ev = OnnxGetEvalCounters();
    std::cout << "  --- Throughput ---\n"
              << "  Van/gio            : " << (completed * 3600.0 / secs) << "\n"
              << "  Giay/van           : " << (secs / completed) << "\n";
    if (ev.runs > 0) {
      const double waste =
          ev.padded > 0 ? 100.0 * (ev.padded - ev.real) / ev.padded : 0.0;
      std::cout << "  NN eval/giay       : " << (ev.real / secs) << "\n"
                << "  NN eval/playout    : "
                << (total_nodes.load() > 0
                        ? static_cast<double>(ev.real) / total_nodes.load()
                        : 0.0) << "\n"
                << "  Batch TB moi Run() : " << (static_cast<double>(ev.real) / ev.runs)
                << "  (so lan Run: " << ev.runs << ")\n"
                << "  Phi do pad         : " << waste << "%  ("
                << (ev.padded - ev.real) << "/" << ev.padded << " o batch)\n";
    }
    // C1: where the playouts went. nn_evals should equal the ORT count above
    // (ev.real); more ORT evals than search nn_evals = evaluations nobody used.
    const auto& ps = classic::g_playout_stats;
    const double po = static_cast<double>(ps.playouts.load());
    if (po > 0) {
      std::cout << "  --- Luot tim (playout) ---\n"
                << "  Gui NN that        : " << 100.0 * ps.nn_evals.load() / po << "%\n"
                << "  Trung cache NN     : " << 100.0 * ps.cache_hits.load() / po << "%\n"
                << "  Khong goi NN       : " << 100.0 * ps.no_eval_playouts.load() / po
                << "%  (the co da ket thuc: " << 100.0 * ps.terminal_playouts.load() / po << "%)\n"
                << "  Va cham (rut lai)  : " << ps.collision_visits.load() / po << " / playout\n"
                << "  NN eval ORT / tim kiem: " << ev.real << " / " << ps.nn_evals.load() << "\n";
    }
  }
  std::cout << "  Output dir: " << cfg.out_dir << std::endl;
}

}  // namespace lczero
