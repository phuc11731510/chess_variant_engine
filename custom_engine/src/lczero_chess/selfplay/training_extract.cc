#include "selfplay/training_extract.h"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <optional>
#include <span>

#include "chess/encoder.h"  // MoveToNNIndex, EncodePositionForNN, InputPlanes

namespace lczero {

Move FillSearchTargets(const classic::Node* root,
                       const PositionHistory& history,
                       Backend* backend,
                       TrainingDataV1& rec) {
  // --- 1. Policy target pi from visit counts ---
  // Mark every slot illegal (-1) first. The root edges below are EXACTLY the
  // legal moves; each gets overwritten with its visit fraction (0 if unvisited).
  // Result: illegal = -1, legal-unvisited = 0, legal-visited = fraction. This
  // lets the trainer mask illegal moves (lc0 convention: pi < 0 => illegal).
  std::fill_n(rec.probabilities, kPolicySize, -1.0f);
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

void EncodePlanesIntoRecord(const PositionHistory& history,
                            TrainingDataV1& rec) {
  InputPlanes planes;
  int transform = 0;
  EncodePositionForNN(history, kMoveHistory, FillEmptyHistory::FEN_ONLY,
                      &planes, &transform);

  // 216 history piece planes -> 128-bit bitboard masks, split into a WELL-DEFINED
  // on-disk order: word[0] = squares 0-63, word[1] = squares 64-127. Extract via
  // shift/mask (NOT memcpy) so the format is independent of the internal
  // Stockfish::Bitboard layout (struct {hi,lo} vs __int128); Python then reads
  // word[0] as the low 64 squares, matching UnpackInputPlanes' pop_lsb order.
  static_assert(sizeof(planes[0].mask) == 2 * sizeof(uint64_t),
                "Bitboard is not 128-bit");
  const Stockfish::Bitboard low64 = Stockfish::Bitboard(0xFFFFFFFFFFFFFFFFULL);
  auto split = [&low64](const Stockfish::Bitboard& m, uint64_t out[2]) {
    out[0] = static_cast<uint64_t>(m & low64);  // squares 0-63
    out[1] = static_cast<uint64_t>(m >> 64);    // squares 64-127
  };
  for (int p = 0; p < kHistoryPlanes; ++p) {
    split(planes[p].mask, rec.piece_planes[p]);
  }
  // En-passant plane is aux index 4 (kAuxPlaneBase + 4).
  split(planes[kAuxPlaneBase + 4].mask, rec.ep_mask);

  // --- Scalar aux read directly from the position (raw; Python normalizes) ---
  const Position& last = history.Last();
  const Stockfish::Position& pos = last.GetBoard().GetRawPosition();
  const Stockfish::Color us = pos.side_to_move();
  const Stockfish::Color them = ~us;

  rec.side_to_move = (us == Stockfish::BLACK) ? 1 : 0;
  rec.rule50_count =
      static_cast<uint8_t>(std::clamp(last.GetRule50Ply(), 0, 255));
  rec.checks_remaining_us = static_cast<uint8_t>(
      std::clamp(static_cast<int>(pos.checks_remaining(us)), 0, 255));
  rec.checks_remaining_them = static_cast<uint8_t>(
      std::clamp(static_cast<int>(pos.checks_remaining(them)), 0, 255));

  // Castling: store the rook FILE (0-9) for each right, 0xFF if no right.
  // The vertical flip used for the canonical frame preserves file, so the file
  // of the actual rook square equals the file in the canonical frame.
  auto castle_file = [&](Stockfish::CastlingRights cr) -> uint8_t {
    if (!pos.can_castle(cr)) return kNoCastlingFile;
    return static_cast<uint8_t>(Stockfish::file_of(pos.castling_rook_square(cr)));
  };
  const Stockfish::CastlingRights us_ooo =
      (us == Stockfish::WHITE) ? Stockfish::WHITE_OOO : Stockfish::BLACK_OOO;
  const Stockfish::CastlingRights us_oo =
      (us == Stockfish::WHITE) ? Stockfish::WHITE_OO : Stockfish::BLACK_OO;
  const Stockfish::CastlingRights them_ooo =
      (us == Stockfish::WHITE) ? Stockfish::BLACK_OOO : Stockfish::WHITE_OOO;
  const Stockfish::CastlingRights them_oo =
      (us == Stockfish::WHITE) ? Stockfish::BLACK_OO : Stockfish::WHITE_OO;
  rec.castling_us_ooo_file = castle_file(us_ooo);
  rec.castling_us_oo_file = castle_file(us_oo);
  rec.castling_them_ooo_file = castle_file(them_ooo);
  rec.castling_them_oo_file = castle_file(them_oo);
}

}  // namespace lczero
