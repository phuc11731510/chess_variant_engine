#pragma once
#include <string>
#include "utils/optionsdict.h"

// Hand dispatch table that applies one lc0 search parameter (name=value) onto an
// OptionsDict; used by the UCI-NN engine and by --selfplay --search-opt.
bool ApplySearchOpt(lczero::OptionsDict* d, const std::string& name, const std::string& value);
