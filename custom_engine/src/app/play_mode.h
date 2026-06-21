#pragma once
#include <string>

// Terminal ASCII play loop (human vs engine).
void run_play(const std::string& weights, const std::string& provider, int fixed_batch,
              int visits, bool human_white);
