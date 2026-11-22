#include "selfplay/selfplay_game.h"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstring>
#include <memory>
#include <numbers>
#include <vector>

#include "chess/callbacks.h"  // UciResponder
#include "chess/encoder.h"    // MoveToNNIndex
#include "search/classic/node.h"
#include "search/classic/search.h"
#include "selfplay/training_extract.h"
#include "trainingdata/writer.h"
#include "utils/random.h"

namespace lczero {

std::atomic<int64_t> g_live_playouts{0};

namespace {

// No-op responder so self-play searches don't print UCI info.
class SilentResponder : public UciResponder {
 public:
  void OutputBestMove(BestMoveInfo*) override {}
  void OutputThinkingInfo(std::vector<ThinkingInfo>*) override {}
};

// Stops after `max_new_playouts` NEW playouts this move (counts nodes since move
// start, not total tree size), and REPORTS that same counter back for the nps
// statistics. Self-play now searches every move on a fresh tree (see
// SearchSelfPlayMove), where the two are equal; the "new playouts" semantics is
// kept because it stays correct if a caller ever searches a reused tree, whose
// root already carries the visits of the previous move.
class PlayoutStopper : public classic::SearchStopper {
 public:
  explicit PlayoutStopper(int64_t max_new_playouts)
      : max_new_(max_new_playouts) {}
  bool ShouldStop(const classic::IterationStats& stats,
                  classic::StoppersHints*) override {
    // Recorded here as well as in OnSearchDone: a search that ends without the
    // bestmove path running (terminal root) never reaches OnSearchDone, and this
    // keeps the last observed value instead of reporting zero.
    new_playouts_.store(stats.nodes_since_movestart, std::memory_order_relaxed);
    return stats.nodes_since_movestart >= max_new_;
  }
  void OnSearchDone(const classic::IterationStats& stats) override {
    new_playouts_.store(stats.nodes_since_movestart, std::memory_order_relaxed);
  }

  int64_t new_playouts() const {
    return new_playouts_.load(std::memory_order_relaxed);
  }

 private:
  int64_t max_new_;
  // ShouldStop is called from the search threads; keep the store race-free.
  std::atomic<int64_t> new_playouts_{0};
};

}  // namespace

// Picks the move to play: drawn for EVERY move of the game with weight (N / N_max)^(1 / T) among the moves the
// Elo cutoff leaves (MoveChoiceProbabilities); the most visited move if nothing was visited. Used by self-play and
// by the arena (2026-11-20: the arena draws every move the same way).
classic::EdgeAndNode SelectMoveEdge(const classic::Node* root, float temperature, float elo_cutoff) {
  const bool cut = elo_cutoff > 0.0f;
  const size_t count = root->GetNumEdges();
  std::vector<classic::EdgeAndNode> edges;
  std::vector<uint32_t> visits;
  std::vector<float> values;  // only for the cutoff: Q = W - L of the root mover (draw score 0), read for visited moves
  edges.reserve(count);
  visits.reserve(count);
  if (cut) values.reserve(count);
  classic::EdgeAndNode best;
  uint32_t best_n = 0;
  for (const auto& e : root->Edges()) {
    const uint32_t n = e.GetN();
    edges.push_back(e);
    visits.push_back(n);
    if (cut) values.push_back(n > 0 ? e.GetQ(0.0f, 0.0f) : 0.0f);
    if (n >= best_n) {
      best_n = n;
      best = e;
    }
  }
  const int i = SampleIndex(MoveChoiceProbabilities(visits, values, temperature, elo_cutoff),
                            Random::Get().GetDouble(1.0));
  return i < 0 ? best : edges[i];
}

bool ChooseFastSearch(float fast_prob) {
  if (!(fast_prob > 0.0f)) return false;
  if (fast_prob >= 1.0f) return true;
  return Random::Get().GetDouble(1.0) < static_cast<double>(fast_prob);
}

double EloOfValue(double q) {
  constexpr double kClamp = 0.001;
  const double s = std::clamp(0.5 * (1.0 + q), kClamp, 1.0 - kClamp);
  return 400.0 / std::numbers::ln10 * std::log(s / (1.0 - s));
}

std::vector<double> MoveChoiceProbabilities(const std::vector<uint32_t>& visits, float temperature) {
  return MoveChoiceProbabilities(visits, {}, temperature, 0.0f);
}

std::vector<double> MoveChoiceProbabilities(const std::vector<uint32_t>& visits,
                                            const std::vector<float>& values, float temperature,
                                            float elo_cutoff) {
  std::vector<double> p(visits.size(), 0.0);
  uint32_t n_max = 0;
  for (const uint32_t n : visits) n_max = std::max(n_max, n);
  if (n_max == 0) return p;

  // The Elo below which a move is struck out: that of the most visited move (of equals, the best valued) less the cutoff.
  // NaN (a NaN value, a NaN cutoff) strikes out nothing: every comparison with it is false.
  const bool cut = elo_cutoff > 0.0f && values.size() == visits.size();
  double min_elo = 0.0;
  if (cut) {
    size_t best = 0;
    for (size_t i = 0; i < visits.size(); ++i)
      if (visits[i] > visits[best] || (visits[i] == visits[best] && visits[i] > 0 && values[i] > values[best])) best = i;
    min_elo = EloOfValue(values[best]) - elo_cutoff;
  }

  // (N / N_max) <= 1, so a small T underflows to 0 for every move but the best instead of
  // overflowing as N^(1/T) would; the best move always weighs exactly 1 and is never struck out.
  double sum = 0.0;
  for (size_t i = 0; i < visits.size(); ++i) {
    if (visits[i] == 0) continue;
    if (cut && EloOfValue(values[i]) < min_elo) continue;
    p[i] = temperature <= 0.0f
               ? (visits[i] == n_max ? 1.0 : 0.0)
               : std::pow(static_cast<double>(visits[i]) / n_max, 1.0 / temperature);
    sum += p[i];
  }
  for (double& x : p) x /= sum;
  return p;
}

int SampleIndex(const std::vector<double>& probabilities, double toss) {
  double acc = 0.0;
  int last = -1;
  for (size_t i = 0; i < probabilities.size(); ++i) {
    if (!(probabilities[i] > 0.0)) continue;
    last = static_cast<int>(i);
    acc += probabilities[i];
    if (toss < acc) return last;
  }
  return last;
}

int64_t SearchSelfPlayMove(classic::NodeTree* tree, Backend* backend,
                           const OptionsDict& options, int visits,
                           int search_threads) {
  // Every move gets a FRESH search tree, as in lc0's own self-play (ReuseTree
  // defaults to false there: selfplay/game.cc calls TrimTreeAtHead before each
  // move) and in the AlphaZero pseudocode (run_mcts builds a new root per move).
  // Dirichlet noise is only mixed into a root's priors when that root is
  // expanded (FetchSingleNodeResult). A reused root was expanded one move
  // earlier, as an ordinary child, so keeping the subtree meant that only the
  // first move of each game ever got root noise. The evaluations themselves
  // survive in the NN cache, so re-expanding the old subtree costs cache hits,
  // not GPU work.
  tree->TrimTreeAtHead();
  // Heap-allocated: Search/SearchWorker hold PositionHistory (512-ply arrays).
  auto stopper = std::make_unique<PlayoutStopper>(visits);
  // Borrowed before the unique_ptr moves into Search, which owns it until the
  // Search is destroyed at the end of this function.
  PlayoutStopper* stopper_ptr = stopper.get();
  auto search = std::make_unique<classic::Search>(
      *tree, backend, std::make_unique<SilentResponder>(), MoveList{},
      std::chrono::steady_clock::now(), std::move(stopper), /*infinite=*/false,
      /*ponder=*/false, options, /*syzygy_tb=*/nullptr);
  search->RunBlocking(search_threads);
  // NEW playouts this move (see PlayoutStopper), read while the Search (which
  // owns the stopper) is still alive. The Search is destroyed on return, i.e.
  // BEFORE the caller reads the tree or plays a move on it.
  return stopper_ptr->new_playouts();
}

GameResult PlayOneGame(const std::string& start_fen, Backend* backend,
                       const OptionsDict& options, const SelfPlaySearchPlan& plan,
                       int max_moves, const std::string& out_filename,
                       int search_threads, bool verbose,
                       float resign_threshold, int resign_consecutive,
                       bool allow_resign, int resign_earliest_move,
                       int64_t* out_nodes, int* out_final_pieces,
                       int64_t* out_white_attack, int64_t* out_black_attack,
                       int* out_moves, int* out_fast_moves) {
  auto tree = std::make_unique<classic::NodeTree>();
  tree->ResetToPosition(start_fen, {});

  std::vector<TrainingDataV1> records;
  std::vector<bool> stm_black;
  // Reserve up front: each TrainingDataV1 is ~46 KB, so growth-reallocations
  // would copy megabytes per game. We append at most max_moves records.
  records.reserve(max_moves);
  stm_black.reserve(max_moves);
  GameResult result = GameResult::UNDECIDED;
  int64_t local_nodes = 0;   // total MCTS playouts across this game's moves (NPS)
  int fast_moves = 0;        // moves searched with the reduced playout cap

  // Early-resign tracking: count consecutive own-moves where each side judged
  // itself badly losing. Index 0 = White, 1 = Black. Only active when the caller
  // allows resign AND the threshold is reachable (best_q in [-1,1]).
  const bool resign_active = allow_resign && resign_threshold > -1.0f;
  int resign_streak[2] = {0, 0};

  // Điểm hệ số tấn công tích luỹ (xem header). Mặt nạ nửa bàn tính một lần.
  int64_t white_attack = 0, black_attack = 0;
  static const Stockfish::Bitboard kWhiteHalf = []{
    Stockfish::Bitboard b = Stockfish::Bitboard(0);
    for (int r = Stockfish::RANK_1; r <= Stockfish::RANK_5; ++r)
      b |= Stockfish::rank_bb(Stockfish::Rank(r));   // nửa Trắng = hạng 1-5
    return b;
  }();
  static const Stockfish::Bitboard kBlackHalf = []{
    Stockfish::Bitboard b = Stockfish::Bitboard(0);
    for (int r = Stockfish::RANK_6; r <= Stockfish::RANK_10; ++r)
      b |= Stockfish::rank_bb(Stockfish::Rank(r));   // nửa Đen = hạng 6-10
    return b;
  }();

  for (int ply = 0; ply < max_moves; ++ply) {
    // Tích luỹ điểm tấn công ở thế cờ hiện tại (trước khi đi nước này).
    {
      const auto& rp =
          tree->GetPositionHistory().Last().GetBoard().GetRawPosition();
      white_attack += Stockfish::popcount(rp.pieces(Stockfish::WHITE) & kBlackHalf);
      black_attack += Stockfish::popcount(rp.pieces(Stockfish::BLACK) & kWhiteHalf);
    }

    // Playout cap randomization: the coin is tossed before EVERY move, independently. A shallow
    // search has its own visits and its own options (c_puct, noise epsilon); its record is marked
    // so the trainer leaves its policy target out.
    const bool fast = ChooseFastSearch(plan.fast_prob);
    {
      const OptionsDict& search_options =
          (fast && plan.fast_options != nullptr) ? *plan.fast_options : options;
      const int64_t n = SearchSelfPlayMove(
          tree.get(), backend, search_options,
          fast ? plan.fast_visits : plan.full_visits, search_threads);
      local_nodes += n;
      g_live_playouts.fetch_add(n, std::memory_order_relaxed);
    }
    const classic::Node* root = tree->GetCurrentHead();

    TrainingDataV1 rec;
    std::memset(&rec, 0, sizeof(rec));
    rec.version = kTrainingDataVersion;
    rec.input_format = kInputFormat10x10;
    rec.fast_search = fast ? 1 : 0;
    const bool black = tree->IsBlackToMove();

    // pi / value / orig_q / policy_kld (T2).
    const Move best =
        FillSearchTargets(root, tree->GetPositionHistory(), backend, rec);
    if (best.is_null()) break;  // terminal/no-move root (defensive).

    // Input planes + scalar aux (T3).
    EncodePlanesIntoRecord(tree->GetPositionHistory(), rec);

    // Move selection: weight (N / N_max)^(1 / T) for every move of the game, without the moves the Elo cutoff strikes out.
    const classic::EdgeAndNode played_edge = SelectMoveEdge(root, plan.temperature, plan.elo_cutoff);
    const Move played = RecordPlayedMove(played_edge, best, rec);

    records.push_back(rec);
    stm_black.push_back(black);
    if (fast) ++fast_moves;

    // --- Early resignation (plan A5) ---
    // best_q is from the side-to-move's perspective. If a side judges itself
    // badly losing for `resign_consecutive` of its own moves in a row, adjudicate
    // an immediate loss for that side (the just-recorded position is still kept).
    if (resign_active && ply >= resign_earliest_move) {
      const int s = black ? 1 : 0;
      if (rec.best_q <= resign_threshold) {
        if (++resign_streak[s] >= resign_consecutive) {
          result = black ? GameResult::WHITE_WON : GameResult::BLACK_WON;
          if (verbose) {
            std::cout << "  [resign] " << (black ? "black" : "white")
                      << " resigns (best_q=" << rec.best_q << ")" << std::endl;
          }
          break;
        }
      } else {
        resign_streak[s] = 0;
      }
    }

    // In nuoc co ra console de con nguoi doc duoc (lat lai ve he toa do ban co that neu la quan Den)
    if (verbose) {
      Move display_move = played;
      if (black) {
        display_move.Flip(Stockfish::RANK_10);
      }
      std::cout << "  Ply " << (ply + 1) << " (" << (black ? "black" : "white")
                << "): " << display_move.ToString() << std::endl;
    }

    tree->MakeMove(played);
    result = tree->GetPositionHistory().ComputeGameResult();
    if (result != GameResult::UNDECIDED) break;
  }

  // Cutoff without a natural finish is adjudicated as a draw.
  const GameResult final_result =
      (result != GameResult::UNDECIDED) ? result : GameResult::DRAW;

  for (size_t i = 0; i < records.size(); ++i) {
    AssignResult(records[i], final_result, stm_black[i]);
    // Moves-left target (lc0's plies_left): plies from this position to the end of the game, counting
    // the move played here, so the last record has 1. A game cut at --max-moves keeps its numbers as
    // they are (owner's decision, 2026-11-17).
    records[i].plies_left = static_cast<uint16_t>(std::min<size_t>(records.size() - i, 65535));
  }

  // Write all positions to one game file (.xz v6 / .gz, see trainingdata/writer.h).
  TrainingDataWriter writer(out_filename);
  for (const auto& r : records) writer.WriteChunk(r);
  writer.Finalize();

  if (out_nodes) *out_nodes = local_nodes;
  if (out_moves) *out_moves = static_cast<int>(records.size());
  if (out_fast_moves) *out_fast_moves = fast_moves;
  // Số quân còn lại trên bàn lúc ván kết thúc (cả Trắng + Đen, kể cả royal).
  if (out_final_pieces) {
    const auto& fb = tree->GetPositionHistory().Last().GetBoard();
    *out_final_pieces = fb.ours().count() + fb.theirs().count();
  }
  // Điểm hệ số tấn công tích luỹ cả ván (bên nào đóng quân trên sân địch nhiều/lâu hơn).
  if (out_white_attack) *out_white_attack = white_attack;
  if (out_black_attack) *out_black_attack = black_attack;
  return final_result;
}

}  // namespace lczero
