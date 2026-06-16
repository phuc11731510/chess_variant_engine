#pragma once

#include <chrono>
#include <memory>
#include <optional>
#include <vector>
#include <limits>
#include <algorithm>

namespace lczero {

class OptionsDict;
class Position;

namespace classic {

// Các thông số thống kê lượt tìm kiếm gửi cho stopper để đưa ra quyết định dừng
struct IterationStats {
  int64_t time_since_movestart = 0;
  int64_t time_since_first_batch = 0;
  int64_t total_nodes = 0;
  int64_t nodes_since_movestart = 0;
  int64_t batches_since_movestart = 0;
  int average_depth = 0;
  int mate_depth = std::numeric_limits<int>::max();
  std::vector<uint32_t> edge_n;

  bool win_found = false;
  bool may_resign = false;
  int num_losing_edges = 0;

  enum class TimeUsageHint { kNormal, kNeedMoreTime, kImmediateMove };
  TimeUsageHint time_usage_hint_ = TimeUsageHint::kNormal;
};

// Phản hồi gợi ý từ stopper ngược lại cho search engine
class StoppersHints {
 public:
  StoppersHints();
  void Reset();
  void UpdateEstimatedRemainingTimeMs(int64_t v);
  int64_t GetEstimatedRemainingTimeMs() const;
  void UpdateEstimatedRemainingPlayouts(int64_t v);
  int64_t GetEstimatedRemainingPlayouts() const;
  void UpdateEstimatedNps(float v);
  std::optional<float> GetEstimatedNps() const;

 private:
  int64_t remaining_time_ms_;
  int64_t remaining_playouts_;
  std::optional<float> estimated_nps_;
};

// Lớp cha cơ sở trừu tượng cho tất cả các bộ quản lý dừng tìm kiếm (Stopper)
class SearchStopper {
 public:
  virtual ~SearchStopper() = default;
  virtual bool ShouldStop(const IterationStats&, StoppersHints*) = 0;
  virtual void OnSearchDone(const IterationStats&) {}
};

}  // namespace classic
}  // namespace lczero
