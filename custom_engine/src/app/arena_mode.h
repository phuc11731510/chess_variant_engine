#pragma once

struct EngineOptions;

// Plays model A vs model B (--model-a / --model-b) for --games games and prints
// the W/D/L tally. Honors the shared backend/search flags: --provider (cpu/cuda/
// dml), --backend-threads, --fixed-batch, --visits, --max-moves, --temp-cutoff,
// --cpuct, --policy-temp. Returns 0 on success, 1 on a usage/backend error.
int run_arena(const EngineOptions& o);
