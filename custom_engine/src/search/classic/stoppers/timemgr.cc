#include "search/classic/stoppers/timemgr.h"

namespace lczero {
namespace classic {

StoppersHints::StoppersHints() { Reset(); }

void StoppersHints::UpdateEstimatedRemainingTimeMs(int64_t v) {
  if (v < remaining_time_ms_) remaining_time_ms_ = v;
}
int64_t StoppersHints::GetEstimatedRemainingTimeMs() const {
  return remaining_time_ms_;
}

void StoppersHints::UpdateEstimatedRemainingPlayouts(int64_t v) {
  if (v < remaining_playouts_) remaining_playouts_ = v;
}
int64_t StoppersHints::GetEstimatedRemainingPlayouts() const {
  return std::max(decltype(remaining_playouts_){1}, remaining_playouts_);
}

void StoppersHints::UpdateEstimatedNps(float v) { estimated_nps_ = v; }

std::optional<float> StoppersHints::GetEstimatedNps() const {
  return estimated_nps_;
}

void StoppersHints::Reset() {
  remaining_time_ms_ = 100000000000;
  remaining_playouts_ = 4000000000;
  estimated_nps_.reset();
}

}  // namespace classic
}  // namespace lczero
