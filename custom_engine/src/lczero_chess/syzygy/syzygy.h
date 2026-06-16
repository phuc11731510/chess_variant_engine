#pragma once
#include <vector>
#include <string>
#include "chess/position.h"

namespace lczero {

enum WDLScore {
  WDL_LOSS = -2,
  WDL_BLESSED_LOSS = -1,
  WDL_DRAW = 0,
  WDL_CURSED_WIN = 1,
  WDL_WIN = 2,
};

enum ProbeState {
  FAIL = 0,
  OK = 1,
  CHANGE_STM = -1,
  ZEROING_BEST_MOVE = 2
};

class SyzygyTablebase {
 public:
  SyzygyTablebase() : max_cardinality_(0) {}
  virtual ~SyzygyTablebase() = default;
  int max_cardinality() const { return max_cardinality_; }
  bool init(const std::string& paths) { return false; }
  WDLScore probe_wdl(const Position& pos, ProbeState* result) {
    if (result) *result = FAIL;
    return WDL_DRAW;
  }
  int probe_dtz(const Position& pos, ProbeState* result) {
    if (result) *result = FAIL;
    return 0;
  }
  bool root_probe(const Position& pos, bool has_repeated, bool win_only,
                  std::vector<Move>* safe_moves) {
    return false;
  }
  bool root_probe_wdl(const Position& pos, std::vector<Move>* safe_moves) {
    return false;
  }

 private:
  int max_cardinality_;
};

}  // namespace lczero
