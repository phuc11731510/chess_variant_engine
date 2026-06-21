#pragma once
#include <vector>
#include <chrono>
#include <cstdint>
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

class InfiniteStopper : public lczero::classic::SearchStopper {
public:
    bool ShouldStop(const lczero::classic::IterationStats&, lczero::classic::StoppersHints*) override {
        return false;
    }
    void OnSearchDone(const lczero::classic::IterationStats&) override {}
};

// Stopper by NEW playouts this search (nodes_since_movestart) — matches the
// self-play PlayoutStopper, which is proven to drive a real multi-playout search
// (NodeLimitStopper's total_nodes = playouts + initial_visits can mis-fire).
class PlayoutCountStopper : public lczero::classic::SearchStopper {
public:
    explicit PlayoutCountStopper(int64_t max_new) : max_new_(max_new) {}
    bool ShouldStop(const lczero::classic::IterationStats& s, lczero::classic::StoppersHints*) override {
        return s.nodes_since_movestart >= max_new_;
    }
    void OnSearchDone(const lczero::classic::IterationStats&) override {}
private:
    int64_t max_new_;
};

// Stopper that fires after a wall-clock budget (for `go movetime`).
class TimeStopper : public lczero::classic::SearchStopper {
public:
    explicit TimeStopper(int64_t ms)
        : deadline_(std::chrono::steady_clock::now() + std::chrono::milliseconds(ms)) {}
    bool ShouldStop(const lczero::classic::IterationStats&, lczero::classic::StoppersHints*) override {
        return std::chrono::steady_clock::now() >= deadline_;
    }
    void OnSearchDone(const lczero::classic::IterationStats&) override {}
private:
    std::chrono::steady_clock::time_point deadline_;
};

