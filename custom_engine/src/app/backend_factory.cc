#include <iostream>
#include <string>
#include <vector>
#include <sstream>
#include <cassert>

#include "bitboard.h"
#include "endgame.h"
#include "position.h"
#include "psqt.h"
#include "search.h"
#include "syzygy/tbprobe.h"
#include "thread.h"
#include "tt.h"
#include "uci.h"
#include "piece.h"
#include "variant.h"
#include "xboard.h"
#include "movegen.h"
#include "chess/board.h"
#include "chess/position.h"
#include "chess/gamestate.h"
#include "chess/encoder.h"
#include "trainingdata/trainingdata_v1.h"
#include "trainingdata/writer.h"
#include "selfplay/training_extract.h"
#include "selfplay/selfplay_game.h"
#include "selfplay/selfplay_driver.h"
#include <cstring>
#include <cstdlib>
#include <fstream>
#include <cstdio>
#include <cmath>
#include <thread>
#include <atomic>
#include <mutex>
#include <chrono>
#include <memory>
#include <map>
#include <functional>
#include <algorithm>
#include "search/classic/search.h"
#include "search/classic/params.h"
#include "neural/backend.h"
#include "neural/shared_params.h"
#include "neural/onnx_backend.h"
#ifdef USE_FZCUDA
#include "neural/fz/fzcuda_backend.h"
#endif
#ifdef USE_TFLITE
#include "neural/tflite_backend.h"
#endif
#include "utils/exception.h"
#include "neural/zero_heap_cache.h"
#include "utils/random.h"
#include "chess/callbacks.h"
#include "app/backend_factory.h"


using namespace Stockfish;


namespace {
bool WantsProvider(const lczero::OptionsDict& opts, const std::string& provider) {
    const std::string bopts = opts.GetOrDefault<std::string>(lczero::SharedBackendParams::kBackendOptionsId, "");
    std::istringstream in(bopts);
    for (std::string kv; std::getline(in, kv, ',');)
        if (kv == "provider=" + provider) return true;
    return false;
}
}  // namespace

std::unique_ptr<lczero::Backend> make_network_backend(const lczero::OptionsDict& opts) {
    if (WantsProvider(opts, "gpu")) {   // Android GPU: TFLite + GPU delegate, weights = a .tflite of python/khung_gpu.py
#ifdef USE_TFLITE
        auto raw = std::make_unique<lczero::TfliteBackend>();
        raw->UpdateConfiguration(opts);
        return raw;
#else
        throw lczero::Exception("provider gpu: only the Android build has the TFLite GPU backend");
#endif
    }
    if (WantsProvider(opts, "fzcuda")) {
#ifdef USE_FZCUDA
        auto raw = std::make_unique<lczero::FzCudaBackend>();
        raw->UpdateConfiguration(opts);
        return raw;
#else
        throw lczero::Exception("provider fzcuda: this binary was built without the CUDA runner (meson -Duse_fzcuda=true)");
#endif
    }
    auto raw = std::make_unique<lczero::OnnxBackend>();
    raw->UpdateConfiguration(opts);
    return raw;
}

std::unique_ptr<lczero::Backend> arena_make_backend(const lczero::OptionsDict& opts) {
    return lczero::CreateMemCache(make_network_backend(opts), opts);
}
