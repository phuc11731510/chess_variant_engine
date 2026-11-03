/*
  This file is part of the chess game-tree experiment, built on Leela Chess
  Zero (see co_vua/docs/THIET_KE_CO_VUA.md, sections 12.6 and 12.7).

  Leela Chess is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.
*/

#pragma once

namespace lczero {

// "treeplay" mode: reads self-play jobs from stdin, plays them on parallel
// games that share one (multiplexed, cached) backend, and appends one binary
// record per finished job to the output file.
//
// Job lines (moves are UCI, absolute coordinates, from the standard start):
//   G <id> <temp_plies> [moves...]  play a game from the position after the
//                                   moves; plies before <temp_plies> (game
//                                   ply, counted from the start position)
//                                   sample the move by visit count.
//   S <id> [moves...]               search the position once (re-search).
// End of input = no more jobs: running games finish, then the program exits.
//
// Stdout lines: "XONG <id> <evals>" when a job's record is written, where
// <evals> is the total number of positions sent to the network so far (cache
// hits not counted); "LOI <id> <message>" for a rejected job; "HET <evals>
// <jobs>" at the end.
void RunTreePlay();

}  // namespace lczero
