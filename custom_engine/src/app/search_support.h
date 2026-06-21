#pragma once
#include <vector>
#include "search/classic/search.h"
#include "chess/callbacks.h"

class NodeLimitStopper : public lczero::classic::SearchStopper {
public:
    NodeLimitStopper(int64_t max_nodes) : max_nodes_(max_nodes) {}
    bool ShouldStop(const lczero::classic::IterationStats& stats, lczero::classic::StoppersHints*) override {
        return stats.total_nodes >= max_nodes_;
    }
    void OnSearchDone(const lczero::classic::IterationStats&) override {}
private:
    int64_t max_nodes_;
};

class SilentUciResponder : public lczero::UciResponder {
public:
    void OutputBestMove(lczero::BestMoveInfo*) override {}
    void OutputThinkingInfo(std::vector<lczero::ThinkingInfo>*) override {}
};
