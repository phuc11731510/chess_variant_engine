#pragma once

#include "utils/optionsdict.h"
#include "utils/optionsparser.h"

namespace lczero {

struct SharedBackendParams {
  static const constexpr char* kEmbed = "<built in>";
  static const constexpr char* kAutoDiscover = "<autodiscover>";

  inline static const OptionId kPolicySoftmaxTemp{"policy-softmax-temp", "PolicySoftmaxTemp", ""};
  inline static const OptionId kHistoryFill{"history-fill", "HistoryFill", ""};
  inline static const OptionId kWeightsId{"weights", "Weights", ""};
  inline static const OptionId kBackendId{"backend", "Backend", ""};
  inline static const OptionId kBackendOptionsId{"backend-opts", "BackendOpts", ""};
  inline static const OptionId kNNCacheSizeId{"nn-cache-size", "NNCacheSize", ""};
  // Compact NN cache: priors of each entry in a shared ring arena (only the entry's
  // real move count) instead of a fixed 384-float slot -- ~6x more entries per MB.
  inline static const OptionId kNNCacheCompactId{"nn-cache-compact", "NNCacheCompact", ""};

  static void Populate(OptionsParser*) {}

 private:
  SharedBackendParams() = delete;
};

}  // namespace lczero
