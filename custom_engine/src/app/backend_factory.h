#pragma once
#include <memory>
#include "neural/backend.h"
#include "utils/optionsdict.h"

// Builds the ONNX backend wrapped in the lc0 memory cache (used by arena, the
// UCI-NN engine, and play mode).
std::unique_ptr<lczero::Backend> arena_make_backend(const lczero::OptionsDict& opts);
