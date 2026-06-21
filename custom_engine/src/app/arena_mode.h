#pragma once
#include <string>

// Plays model A vs model B for `games` games and prints the W/D/L tally.
void run_arena(const std::string& model_a, const std::string& model_b, int games,
               int visits, int max_moves, int temp_cutoff,
               const std::string& provider, int fixed_batch);
