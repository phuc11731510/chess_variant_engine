#include <iostream>
#include <string>
#include <vector>
#include <sstream>
#include <cassert>
#include <cerrno>

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
#include "neural/zero_heap_cache.h"
#include "utils/random.h"
#include "chess/callbacks.h"
#include "app/search_opts.h"


using namespace Stockfish;


namespace {

// One lc0 search parameter settable with --search-opt / the UCI passthrough.
// The ranges and choices are lc0's own (search/classic/params.cc, Populate).
// This project's OptionsParser is a stub that drops them, so they are enforced
// here: before, a malformed value silently became a hard-coded default
// (`max-prefetch=x` gave 32, `cpuct=abc` gave 1.745), an out-of-range one was
// used as is (`draw-score=5`), and a misspelt choice silently meant the default
// (lc0 tests `fpu-strategy == "absolute"`, so "absolut" meant "reduction").
enum class Kind { kFloat, kInt, kBool, kChoice };
struct SearchOpt {
    const char* name;
    Kind kind;
    const lczero::OptionId* id;
    double lo, hi;
    std::vector<std::string> choices;
};

const std::vector<SearchOpt>& SearchOptTable() {
    using BP = lczero::classic::BaseSearchParams;
    using SP = lczero::classic::SearchParams;
    static const std::vector<SearchOpt> table = {
        {"cpuct", Kind::kFloat, &BP::kCpuctId, 0.0, 100.0, {}},
        {"cpuct-at-root", Kind::kFloat, &BP::kCpuctAtRootId, 0.0, 100.0, {}},
        {"cpuct-base", Kind::kFloat, &BP::kCpuctBaseId, 1.0, 1e9, {}},
        {"cpuct-base-at-root", Kind::kFloat, &BP::kCpuctBaseAtRootId, 1.0, 1e9, {}},
        {"cpuct-factor", Kind::kFloat, &BP::kCpuctFactorId, 0.0, 1000.0, {}},
        {"cpuct-factor-at-root", Kind::kFloat, &BP::kCpuctFactorAtRootId, 0.0, 1000.0, {}},
        {"fpu-value", Kind::kFloat, &BP::kFpuValueId, -100.0, 100.0, {}},
        {"fpu-value-at-root", Kind::kFloat, &BP::kFpuValueAtRootId, -100.0, 100.0, {}},
        {"draw-score", Kind::kFloat, &BP::kDrawScoreId, -1.0, 1.0, {}},
        {"temp-endgame", Kind::kFloat, &BP::kTemperatureEndgameId, 0.0, 100.0, {}},
        {"temp-value-cutoff", Kind::kFloat, &BP::kTemperatureWinpctCutoffId, 0.0, 100.0, {}},
        {"temp-visit-offset", Kind::kFloat, &BP::kTemperatureVisitOffsetId, -1000.0, 1000.0, {}},
        {"max-out-of-order-evals-factor", Kind::kFloat, &BP::kMaxOutOfOrderEvalsFactorId, 0.0, 100.0, {}},
        {"contempt-max-value", Kind::kFloat, &BP::kContemptMaxValueId, 0.0, 10000.0, {}},
        {"wdl-calibration-elo", Kind::kFloat, &BP::kWDLCalibrationEloId, 0.0, 10000.0, {}},
        {"wdl-contempt-attenuation", Kind::kFloat, &BP::kWDLContemptAttenuationId, -10.0, 10.0, {}},
        {"wdl-max-s", Kind::kFloat, &BP::kWDLMaxSId, 0.0, 10.0, {}},
        {"wdl-eval-objectivity", Kind::kFloat, &BP::kWDLEvalObjectivityId, 0.0, 1.0, {}},
        {"wdl-draw-rate-target", Kind::kFloat, &BP::kWDLDrawRateTargetId, 0.0, 0.999, {}},
        {"wdl-draw-rate-reference", Kind::kFloat, &BP::kWDLDrawRateReferenceId, 0.001, 0.999, {}},
        {"wdl-book-exit-bias", Kind::kFloat, &BP::kWDLBookExitBiasId, -2.0, 2.0, {}},
        {"nps-limit", Kind::kFloat, &BP::kNpsLimitId, 0.0, 1e6, {}},
        {"garbage-collection-delay", Kind::kFloat, &BP::kGarbageCollectionDelayId, 0.0, 100.0, {}},
        // Read by the backend when it is built (OnnxBackend::UpdateConfiguration).
        {"policy-softmax-temp", Kind::kFloat, &lczero::SharedBackendParams::kPolicySoftmaxTemp, 0.1, 10.0, {}},
        // lc0 allows up to 1024, but one NN computation holds MaxBatchSize inputs:
        // more would throw "Maximum batch size exceeded" in the middle of a game.
        {"minibatch-size", Kind::kInt, &BP::kMiniBatchSizeId, 0, double(lczero::MaxBatchSize), {}},
        {"max-prefetch", Kind::kInt, &SP::kMaxPrefetchBatchId, 0, double(lczero::MaxBatchSize), {}},
        {"tempdecay-moves", Kind::kInt, &BP::kTempDecayMovesId, 0, 640, {}},
        {"tempdecay-delay-moves", Kind::kInt, &BP::kTempDecayDelayMovesId, 0, 100, {}},
        {"temp-cutoff-move", Kind::kInt, &BP::kTemperatureCutoffMoveId, 0, 1000, {}},
        {"cache-history-length", Kind::kInt, &BP::kCacheHistoryLengthId, 0, 7, {}},
        {"max-collision-events", Kind::kInt, &BP::kMaxCollisionEventsId, 1, 65536, {}},
        {"max-collision-visits", Kind::kInt, &BP::kMaxCollisionVisitsId, 1, 100000000, {}},
        {"max-concurrent-searchers", Kind::kInt, &BP::kMaxConcurrentSearchersId, 0, 128, {}},
        {"task-workers", Kind::kInt, &BP::kTaskWorkersPerSearchWorkerId, -1, 128, {}},
        {"two-fold-draws", Kind::kBool, &BP::kTwoFoldDrawsId, 0, 0, {}},
        {"root-has-own-cpuct-params", Kind::kBool, &BP::kRootHasOwnCpuctParamsId, 0, 0, {}},
        {"out-of-order-eval", Kind::kBool, &BP::kOutOfOrderEvalId, 0, 0, {}},
        {"sticky-endgames", Kind::kBool, &BP::kStickyEndgamesId, 0, 0, {}},
        {"per-pv-counters", Kind::kBool, &BP::kPerPvCountersId, 0, 0, {}},
        {"verbose-move-stats", Kind::kBool, &BP::kVerboseStatsId, 0, 0, {}},
        {"search-spin-backoff", Kind::kBool, &BP::kSearchSpinBackoffId, 0, 0, {}},
        {"fpu-strategy", Kind::kChoice, &BP::kFpuStrategyId, 0, 0, {"reduction", "absolute"}},
        {"fpu-strategy-at-root", Kind::kChoice, &BP::kFpuStrategyAtRootId, 0, 0,
         {"reduction", "absolute", "same"}},
        {"score-type", Kind::kChoice, &BP::kScoreTypeId, 0, 0,
         {"centipawn", "centipawn_with_drawscore", "centipawn_2019", "centipawn_2018",
          "win_percentage", "Q", "W-L", "WDL_mu"}},
        {"contempt-mode", Kind::kChoice, &BP::kContemptModeId, 0, 0,
         {"play", "white_side_analysis", "black_side_analysis", "disable"}},
    };
    return table;
}

std::string RangeText(const SearchOpt& o) {
    std::ostringstream s;
    s << "[" << o.lo << ", " << o.hi << "]";
    return s.str();
}

}  // namespace

std::string ApplySearchOptChecked(lczero::OptionsDict* d, const std::string& name,
                                  const std::string& value) {
    for (const SearchOpt& o : SearchOptTable()) {
        if (name != o.name) continue;
        const std::string what = "--search-opt " + name + "=" + value + ": ";
        switch (o.kind) {
            case Kind::kFloat: {
                char* end = nullptr;
                const double x = std::strtod(value.c_str(), &end);
                if (value.empty() || *end != '\0' || !std::isfinite(x) || x < o.lo || x > o.hi)
                    return what + "expected a number in " + RangeText(o);
                d->Set<float>(*o.id, static_cast<float>(x));
                return "";
            }
            case Kind::kInt: {
                char* end = nullptr;
                errno = 0;
                const long x = std::strtol(value.c_str(), &end, 10);
                if (value.empty() || *end != '\0' || errno == ERANGE || x < o.lo || x > o.hi)
                    return what + "expected an integer in " + RangeText(o);
                d->Set<int>(*o.id, static_cast<int>(x));
                return "";
            }
            case Kind::kBool:
                if (value == "true" || value == "1" || value == "on") d->Set<bool>(*o.id, true);
                else if (value == "false" || value == "0" || value == "off") d->Set<bool>(*o.id, false);
                else return what + "expected true/false (or 1/0, on/off)";
                return "";
            case Kind::kChoice: {
                std::string list;
                for (const auto& c : o.choices) {
                    if (value == c) {
                        d->Set<std::string>(*o.id, value);
                        return "";
                    }
                    list += (list.empty() ? "" : ", ") + c;
                }
                return what + "expected one of: " + list;
            }
        }
    }
    return "--search-opt " + name + ": unknown parameter";
}

bool ApplySearchOpt(lczero::OptionsDict* d, const std::string& name,
                    const std::string& value) {
    return ApplySearchOptChecked(d, name, value).empty();
}
