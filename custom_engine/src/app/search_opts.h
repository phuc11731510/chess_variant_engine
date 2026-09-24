#pragma once
#include <string>
#include "utils/optionsdict.h"

// Applies one lc0 search parameter (name=value) onto an OptionsDict, with lc0's
// own type, range and choice checks. Returns "" on success, otherwise why nothing
// was set (unknown name, malformed or out-of-range value). Used by --selfplay and
// --arena --search-opt (an error stops the run) and by the UCI-NN engine.
std::string ApplySearchOptChecked(lczero::OptionsDict* d, const std::string& name,
                                  const std::string& value);
// Same, true when applied (the UCI engine ignores options it cannot apply).
bool ApplySearchOpt(lczero::OptionsDict* d, const std::string& name, const std::string& value);
