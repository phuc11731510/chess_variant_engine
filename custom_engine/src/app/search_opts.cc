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
#include "neural/zero_heap_cache.h"
#include "utils/random.h"
#include "chess/callbacks.h"
#include "app/search_opts.h"


using namespace Stockfish;


bool ApplySearchOpt(lczero::OptionsDict* d, const std::string& name,
                           const std::string& value) {
    using BP = lczero::classic::BaseSearchParams;
    auto F = [&](float def) { try { return std::stof(value); } catch (...) { return def; } };
    auto I = [&](int def)   { try { return std::stoi(value); } catch (...) { return def; } };
    auto B = [&]() { return value == "true" || value == "1" || value == "on"; };
    // --- floats ---
    if      (name == "cpuct")                       d->Set<float>(BP::kCpuctId, F(1.745f));
    else if (name == "cpuct-at-root")               d->Set<float>(BP::kCpuctAtRootId, F(1.745f));
    else if (name == "cpuct-base")                  d->Set<float>(BP::kCpuctBaseId, F(38739.0f));
    else if (name == "cpuct-base-at-root")          d->Set<float>(BP::kCpuctBaseAtRootId, F(38739.0f));
    else if (name == "cpuct-factor")                d->Set<float>(BP::kCpuctFactorId, F(3.894f));
    else if (name == "cpuct-factor-at-root")        d->Set<float>(BP::kCpuctFactorAtRootId, F(3.894f));
    else if (name == "fpu-value")                   d->Set<float>(BP::kFpuValueId, F(0.330f));
    else if (name == "fpu-value-at-root")           d->Set<float>(BP::kFpuValueAtRootId, F(1.0f));
    else if (name == "draw-score")                  d->Set<float>(BP::kDrawScoreId, F(0.0f));
    else if (name == "temp-endgame")                d->Set<float>(BP::kTemperatureEndgameId, F(0.0f));
    else if (name == "temp-value-cutoff")           d->Set<float>(BP::kTemperatureWinpctCutoffId, F(100.0f));
    else if (name == "temp-visit-offset")           d->Set<float>(BP::kTemperatureVisitOffsetId, F(0.0f));
    else if (name == "max-out-of-order-evals-factor") d->Set<float>(BP::kMaxOutOfOrderEvalsFactorId, F(2.4f));
    else if (name == "contempt-max-value")          d->Set<float>(BP::kContemptMaxValueId, F(420.0f));
    else if (name == "wdl-calibration-elo")         d->Set<float>(BP::kWDLCalibrationEloId, F(0.0f));
    else if (name == "wdl-contempt-attenuation")    d->Set<float>(BP::kWDLContemptAttenuationId, F(1.0f));
    else if (name == "wdl-max-s")                   d->Set<float>(BP::kWDLMaxSId, F(1.4f));
    else if (name == "wdl-eval-objectivity")        d->Set<float>(BP::kWDLEvalObjectivityId, F(1.0f));
    else if (name == "wdl-draw-rate-target")        d->Set<float>(BP::kWDLDrawRateTargetId, F(0.0f));
    else if (name == "wdl-draw-rate-reference")     d->Set<float>(BP::kWDLDrawRateReferenceId, F(0.5f));
    else if (name == "wdl-book-exit-bias")          d->Set<float>(BP::kWDLBookExitBiasId, F(0.65f));
    else if (name == "nps-limit")                   d->Set<float>(BP::kNpsLimitId, F(0.0f));
    else if (name == "garbage-collection-delay")    d->Set<float>(BP::kGarbageCollectionDelayId, F(10.0f));
    else if (name == "policy-softmax-temp")         d->Set<float>(lczero::SharedBackendParams::kPolicySoftmaxTemp, F(1.359f));
    // --- ints ---
    else if (name == "minibatch-size")              d->Set<int>(BP::kMiniBatchSizeId, I(256));
    else if (name == "tempdecay-moves")             d->Set<int>(BP::kTempDecayMovesId, I(0));
    else if (name == "tempdecay-delay-moves")       d->Set<int>(BP::kTempDecayDelayMovesId, I(0));
    else if (name == "temp-cutoff-move")            d->Set<int>(BP::kTemperatureCutoffMoveId, I(0));
    else if (name == "cache-history-length")        d->Set<int>(BP::kCacheHistoryLengthId, I(0));
    else if (name == "max-collision-events")        d->Set<int>(BP::kMaxCollisionEventsId, I(917));
    else if (name == "max-collision-visits")        d->Set<int>(BP::kMaxCollisionVisitsId, I(80000));
    else if (name == "max-concurrent-searchers")    d->Set<int>(BP::kMaxConcurrentSearchersId, I(1));
    else if (name == "task-workers")                d->Set<int>(BP::kTaskWorkersPerSearchWorkerId, I(-1));
    // --- bools ---
    else if (name == "two-fold-draws")              d->Set<bool>(BP::kTwoFoldDrawsId, B());
    else if (name == "root-has-own-cpuct-params")   d->Set<bool>(BP::kRootHasOwnCpuctParamsId, B());
    else if (name == "out-of-order-eval")           d->Set<bool>(BP::kOutOfOrderEvalId, B());
    else if (name == "sticky-endgames")             d->Set<bool>(BP::kStickyEndgamesId, B());
    else if (name == "per-pv-counters")             d->Set<bool>(BP::kPerPvCountersId, B());
    else if (name == "verbose-move-stats")          d->Set<bool>(BP::kVerboseStatsId, B());
    else if (name == "search-spin-backoff")         d->Set<bool>(BP::kSearchSpinBackoffId, B());
    // --- strings / choices ---
    else if (name == "fpu-strategy")                d->Set<std::string>(BP::kFpuStrategyId, value);
    else if (name == "fpu-strategy-at-root")        d->Set<std::string>(BP::kFpuStrategyAtRootId, value);
    else if (name == "score-type")                  d->Set<std::string>(BP::kScoreTypeId, value);
    else if (name == "contempt-mode")               d->Set<std::string>(BP::kContemptModeId, value);
    else return false;
    return true;
}

// Picks a root move by temperature (difficulty knob). temp_permille in (0,..]:
// weight_i = N_i^(1/T), T = temp_permille/1000 (clamped). T->0 = greedy best;
// T=1 = proportional to visits; T large = flatter/random. Returns the best edge
// when temp<=0 or counts are empty.
