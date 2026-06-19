#pragma once
#include "trainingdata/trainingdata_v1.h"
#include "chess/position.h"
#include "neural/backend.h"
#include "search/classic/node.h"

namespace lczero {

// Fills the policy / value / diff-focus fields of `rec` from a completed search.
//
//   root    : the searched node (tree.GetCurrentHead()).
//   history : history whose Last() == the searched (root) position; used to
//             query the raw (un-noised) NN eval from the backend cache.
//   backend : the (caching) backend the search ran on (shared cache).
//
// Sets: probabilities[] (pi = visit distribution), visits, best_idx, played_idx
//       (= best_idx by default), root_q/d, best_q/d, played_q/d (= best by
//       default), orig_q/d, policy_kld. All value targets are from the
//       side-to-move perspective.
//
// Does NOT touch piece_planes / scalar-aux / castling / result_q-d (those are
// filled by the plane encoder and by AssignResult at game end).
//
// Returns the best (max-visit) move, for the caller's move-selection logic.
Move FillSearchTargets(const classic::Node* root,
                       const PositionHistory& history,
                       Backend* backend,
                       TrainingDataV1& rec);

// Assigns z (result_q/d) at game end.
//   abs_result    : absolute outcome (WHITE_WON / BLACK_WON / DRAW).
//   black_to_move : whose turn it was at this recorded position.
// Convention: z = +1 if the side-to-move ultimately won, -1 if lost, draw -> d=1.
void AssignResult(TrainingDataV1& rec, GameResult abs_result, bool black_to_move);

}  // namespace lczero
