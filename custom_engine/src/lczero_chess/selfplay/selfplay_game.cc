#include "selfplay/selfplay_game.h"

#include <chrono>
#include <cstring>
#include <memory>
#include <vector>

#include "chess/callbacks.h"  // UciResponder
#include "chess/encoder.h"    // MoveToNNIndex
#include "search/classic/node.h"
#include "search/classic/search.h"
#include "selfplay/training_extract.h"
#include "trainingdata/writer.h"
#include "utils/random.h"

namespace lczero {
namespace {

// No-op responder so self-play searches don't print UCI info.
class SilentResponder : public UciResponder {
 public:
  void OutputBestMove(BestMoveInfo*) override {}
  void OutputThinkingInfo(std::vector<ThinkingInfo>*) override {}
};

// Stops after `max_new_playouts` NEW playouts this move (tree-reuse safe:
// counts nodes since move start, not total tree size).
class PlayoutStopper : public classic::SearchStopper {
 public:
  explicit PlayoutStopper(int64_t max_new_playouts)
      : max_new_(max_new_playouts) {}
  bool ShouldStop(const classic::IterationStats& stats,
                  classic::StoppersHints*) override {
    return stats.nodes_since_movestart >= max_new_;
  }
  void OnSearchDone(const classic::IterationStats&) override {}

 private:
  int64_t max_new_;
};

// Picks the move to play: temperature=1 (visit-proportional) sampling for plies
// below the cutoff (opening diversity), greedy (max-visit) afterwards.
classic::EdgeAndNode SelectMoveEdge(const classic::Node* root, int ply,
                                    int temp_cutoff_ply) {
  classic::EdgeAndNode best;
  uint32_t best_n = 0;
  uint64_t total = 0;
  for (const auto& e : root->Edges()) {
    const uint32_t n = e.GetN();
    total += n;
    if (n >= best_n) {
      best_n = n;
      best = e;
    }
  }
  if (ply >= temp_cutoff_ply || total == 0) return best;

  // Sample proportional to visit counts.
  const double toss = Random::Get().GetDouble(static_cast<double>(total));
  double acc = 0.0;
  for (const auto& e : root->Edges()) {
    acc += static_cast<double>(e.GetN());
    if (acc > toss) return e;
  }
  return best;
}

}  // namespace

GameResult PlayOneGame(const std::string& start_fen, Backend* backend,
                       const OptionsDict& options, int visits, int max_moves,
                       int temp_cutoff_ply, const std::string& out_filename,
                       int search_threads, bool verbose) {
  auto tree = std::make_unique<classic::NodeTree>();
  tree->ResetToPosition(start_fen, {});

  std::vector<TrainingDataV1> records;
  std::vector<bool> stm_black;
  // Reserve up front: each TrainingDataV1 is ~46 KB, so growth-reallocations
  // would copy megabytes per game. We append at most max_moves records.
  records.reserve(max_moves);
  stm_black.reserve(max_moves);
  GameResult result = GameResult::UNDECIDED;

  for (int ply = 0; ply < max_moves; ++ply) {
    // --- Search (heap-allocated: PositionHistory holds 512-ply arrays) ---
    auto responder = std::make_unique<SilentResponder>();
    auto stopper = std::make_unique<PlayoutStopper>(visits);
    auto start = std::chrono::steady_clock::now();
    auto search = std::make_unique<classic::Search>(
        *tree, backend, std::move(responder), MoveList{}, start,
        std::move(stopper), /*infinite=*/false, /*ponder=*/false, options,
        /*syzygy_tb=*/nullptr);
    search->RunBlocking(search_threads);

    const classic::Node* root = tree->GetCurrentHead();

    TrainingDataV1 rec;
    std::memset(&rec, 0, sizeof(rec));
    rec.version = kTrainingDataVersion;
    rec.input_format = kInputFormat10x10;
    const bool black = tree->IsBlackToMove();

    // pi / value / orig_q / policy_kld (T2).
    const Move best =
        FillSearchTargets(root, tree->GetPositionHistory(), backend, rec);
    if (best.is_null()) break;  // terminal/no-move root (defensive).

    // Input planes + scalar aux (T3).
    EncodePlanesIntoRecord(tree->GetPositionHistory(), rec);

    // Move selection (temperature early, greedy late).
    classic::EdgeAndNode played_edge = SelectMoveEdge(root, ply, temp_cutoff_ply);
    Move played = played_edge.GetMove();
    if (played.is_null()) {
      played = best;
    } else if (!(played == best)) {
      // Played a non-best move: record its own value (child -> negate WL).
      rec.played_idx = MoveToNNIndex(played, 0);
      if (played_edge.GetN() > 0) {
        rec.played_q = -played_edge.GetWL(0.0f);
        rec.played_d = played_edge.GetD(0.0f);
      }
    }

    records.push_back(rec);
    stm_black.push_back(black);

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
  }

  // Write all positions to one gzip (.gz) file; destructor/Finalize closes it.
  TrainingDataWriter writer(out_filename);
  for (const auto& r : records) writer.WriteChunk(r);
  writer.Finalize();

  return final_result;
}

}  // namespace lczero
