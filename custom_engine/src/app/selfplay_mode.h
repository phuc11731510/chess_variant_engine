#pragma once
#include "app/cli.h"

// Runs self-play data generation (--selfplay). Returns 0 on success, 1 on backend failure.
int run_selfplay(const EngineOptions& o);
