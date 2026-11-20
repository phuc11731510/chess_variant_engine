#pragma once

struct EngineOptions;

// Plays model A vs model B (--model-a / --model-b) for --games games and prints
// the W/D/L tally. Honors the shared backend/search flags: --provider (cpu/cuda/
// dml), --backend-threads, --fixed-batch, --visits (the same playouts every move),
// --max-moves, --cpuct (default 1.25), --temperature (default 0.5: every move of the
// game is drawn with weight (N / N_max)^(1 / T), as in self-play), --policy-temp.
// No Dirichlet noise. Returns 0 on success, 1 on a usage/backend error.
int run_arena(const EngineOptions& o);
