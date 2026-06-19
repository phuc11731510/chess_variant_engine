#include "selfplay/training_extract.h"

#include <algorithm>
#include <cmath>
#include <optional>
#include <span>

#include "chess/encoder.h"  // MoveToNNIndex

namespace lczero {

Move FillSearchTargets(const classic::Node* root,
                       const PositionHistory& history,
                       Backend* backend,
                       TrainingDataV1& rec) {
  // --- 1. Policy target pi from visit counts ---
  // Total child visits (denominator for pi). root->GetN() includes the root's
  // own visit, so sum the edges directly.
  uint32_t total = 0;
  for (const auto& e : root->Edges()) total += e.GetN();

  classic::EdgeAndNode best;
  uint32_t best_n = 0;
  for (const auto& e : root->Edges()) {
    const uint32_t n = e.GetN();
    const uint16_t idx = MoveToNNIndex(e.GetMove(), 0);
    if (idx < kPolicySize) {
      rec.probabilities[idx] = (total > 0) ? static_cast<float>(n) /
                                                 static_cast<float>(total)
                                           : 0.0f;
    }
    if (n >= best_n) {  // >= so a valid edge is always picked even if all N==0
      best_n = n;
      best = e;
    }
  }

  rec.visits = root->GetN();
  rec.best_idx = MoveToNNIndex(best.GetMove(), 0);
  rec.played_idx = rec.best_idx;  // caller overrides after temperature sampling

  // --- 2. Value targets (all from side-to-move-at-root perspective) ---
  // root->GetWL()/GetD() are already from the root's side-to-move view.
  rec.root_q = root->GetWL();
  rec.root_d = root->GetD();
  // A child node's value is from the OPPONENT's perspective -> negate WL to get
  // the value (for us) of playing that move. Draw probability is perspective-
  // invariant so it is not negated.
  if (best.GetN() > 0) {
    rec.best_q = -best.GetWL(0.0f);
    rec.best_d = best.GetD(0.0f);
  } else {
    rec.best_q = rec.root_q;
    rec.best_d = rec.root_d;
  }
  rec.played_q = rec.best_q;  // caller overrides if a non-best move is played
  rec.played_d = rec.best_d;

  // --- 3. Raw (un-noised) NN eval + policy_kld via the backend cache ---
  // The cache stores the NN policy in GenerateLegalMoves() order (deterministic),
  // so raw->p[i] corresponds to legal[i]. We map both pi and p_nn through
  // MoveToNNIndex (NOT by array position, since the root edges have been sorted).
  MoveList legal = history.Last().GetBoard().GenerateLegalMoves();
  EvalPosition ep{&history,
                  std::span<const Move>(legal.data(), legal.size())};
  std::optional<EvalResult> raw = backend->GetCachedEvaluation(ep);

  if (raw && !raw->p.empty()) {
    rec.orig_q = raw->q;
    rec.orig_d = raw->d;
    // KLD( pi || p_nn ) = sum_i pi_i * log( pi_i / p_nn_i ), over legal moves.
    double kld = 0.0;
    const size_t count = std::min(legal.size(), raw->p.size());
    for (size_t i = 0; i < count; ++i) {
      const uint16_t idx = MoveToNNIndex(legal[i], 0);
      if (idx >= kPolicySize) continue;
      const float pi = rec.probabilities[idx];  // dense pi filled above
      if (pi <= 0.0f) continue;
      const double pnn = std::max(static_cast<double>(raw->p[i]), 1e-12);
      kld += static_cast<double>(pi) * std::log(static_cast<double>(pi) / pnn);
    }
    // Clamp tiny negative values from floating-point error (KLD >= 0 in theory).
    rec.policy_kld = static_cast<float>(std::max(0.0, kld));
  } else {
    // Cache miss (~1% hash collision) or non-caching backend: safe fallback.
    rec.orig_q = rec.best_q;
    rec.orig_d = rec.best_d;
    rec.policy_kld = 0.0f;
  }

  return best.GetMove();
}

void AssignResult(TrainingDataV1& rec, GameResult abs_result,
                  bool black_to_move) {
  if (abs_result == GameResult::DRAW) {
    rec.result_q = 0.0f;
    rec.result_d = 1.0f;
    return;
  }
  const bool white_won = (abs_result == GameResult::WHITE_WON);
  const bool stm_is_white = !black_to_move;
  const bool stm_won = (white_won == stm_is_white);
  rec.result_q = stm_won ? 1.0f : -1.0f;
  rec.result_d = 0.0f;
}

}  // namespace lczero
