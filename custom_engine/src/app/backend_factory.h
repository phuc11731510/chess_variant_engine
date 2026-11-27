#pragma once
#include <memory>
#include "neural/backend.h"
#include "utils/optionsdict.h"

// Builds and configures the network backend the options ask for: the CUDA runner when the backend options say
// "provider=fzcuda" (--provider fzcuda, weights a .fzw file), the TFLite GPU backend for "provider=gpu" (Android, weights a
// .tflite of python/khung_gpu.py), ONNX Runtime otherwise. Not wrapped in anything. Throws
// when it cannot (no GPU, unreadable weights, a binary built without the runner).
std::unique_ptr<lczero::Backend> make_network_backend(const lczero::OptionsDict& opts);

// make_network_backend wrapped in the lc0 memory cache (used by arena, the UCI-NN engine, and play mode).
std::unique_ptr<lczero::Backend> arena_make_backend(const lczero::OptionsDict& opts);
