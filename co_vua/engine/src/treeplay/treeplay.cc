/*
  This file is part of the chess game-tree experiment, built on Leela Chess
  Zero (see co_vua/docs/THIET_KE_CO_VUA.md, sections 12.6 and 12.7). The game
  loop follows lc0's src/selfplay/game.cc and the recorded search statistics
  follow src/trainingdata/trainingdata.cc.

  Leela Chess is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  Record format (little endian), one record per finished job:
    char[4]  magic "CVG1"
    u32      record size in bytes, header included
    u64      job id
    u8       kind: 0 = game (G), 1 = re-search (S), 2 = arena game (A, white
             played by --weights if a_white = 1, else by --weights2)
    i8       result, white's view: +1 white won, 0 draw, -1 black won
    u8       end: 0 = game over by the rules, 1 = stopped at max ply (not an
             exact result), 2 = re-search record
    u8       reserved (0)
    u16      number of path moves (the job's moves)
    u16      number of searched positions
    u16[]    path moves
    then per searched position:
      u16    move played (for a re-search: the search's best move)
      u16    number of visited moves V
      u32    N, visits of the root's children
      f32    best_q, best_d   (side to move's view; lc0's best_q)
      f32    raw_q, raw_d     (network output at this position)
      f32    p0, sum of the noisy priors of the moves with no visit
      then V times:
        u16  move
        u16  visits n(a)
        f16  Q(sa) (win minus loss) and D(sa), side to move's view
        f16  prior after Dirichlet noise (what the search used)
        f16  raw prior of the network (NaN if not in the cache)
  Arena games (A jobs, like the arena mode of the chess-variant engine) play
  two networks against each other with no Dirichlet noise; their stdout line
  is "XONG <id> <evals> <result>", result from white's view. --stop-like soft
  stop: close the input, the games in progress are finished.
  Moves are lc0's 16-bit Move::raw_data() in absolute coordinates (white's
  side of the board): from = bits 6-11, to = bits 0-5, castling is encoded as
  king takes rook.
*/

#include "treeplay/treeplay.h"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <deque>
#include <iostream>
#include <limits>
#include <memory>
#include <mutex>
#include <optional>
#include <random>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

#include "chess/board.h"
#include "chess/callbacks.h"
#include "chess/gamestate.h"
#include "chess/position.h"
#include "neural/backend.h"
#include "neural/memcache.h"
#include "neural/register.h"
#include "neural/shared_params.h"
#include "search/classic/node.h"
#include "search/classic/params.h"
#include "search/classic/search.h"
#include "search/classic/stoppers/common.h"
#include "search/classic/stoppers/factory.h"
#include "search/classic/stoppers/stoppers.h"
#include "utils/exception.h"
#include "utils/fp16_utils.h"
#include "utils/optionsparser.h"

namespace lczero {
namespace {

const OptionId kVisitsId{"visits", "Visits", "Visits per search."};
const OptionId kParallelismId{"parallelism", "Parallelism",
                              "Number of games played at the same time."};
const OptionId kOutputId{"output", "Output",
                         "Binary file the finished jobs are appended to."};
const OptionId kMaxPlyId{"max-ply", "MaxPly",
                         "Games are stopped at this game ply (lc0: 450)."};
const OptionId kSeedId{"seed", "Seed",
                       "Seed of the move sampling; 0 = random seed."};
const OptionId kWeights2Id{
    "weights2", "Weights2",
    "Second network, for arena (A) jobs; empty = no arena jobs."};
const OptionId kReportSecondsId{
    "report-seconds", "ReportSeconds",
    "Print a progress line to stderr every this many seconds; 0 = off."};

// Counts the positions that actually reach the network: wraps the caching
// backend, so cache hits (FETCHED_IMMEDIATELY) are not counted.
class CountingBackend final : public Backend {
 public:
  explicit CountingBackend(Backend* inner) : inner_(inner) {}

  BackendAttributes GetAttributes() const override {
    return inner_->GetAttributes();
  }
  std::unique_ptr<BackendComputation> CreateComputation() override {
    return std::make_unique<Computation>(inner_->CreateComputation(),
                                         &evals_);
  }
  std::optional<EvalResult> GetCachedEvaluation(
      const EvalPosition& pos) override {
    return inner_->GetCachedEvaluation(pos);
  }
  int64_t evals() const { return evals_.load(std::memory_order_relaxed); }

 private:
  class Computation final : public BackendComputation {
   public:
    Computation(std::unique_ptr<BackendComputation> inner,
                std::atomic<int64_t>* evals)
        : inner_(std::move(inner)), evals_(evals) {}
    size_t UsedBatchSize() const override { return inner_->UsedBatchSize(); }
    AddInputResult AddInput(const EvalPosition& pos,
                            EvalResultPtr result) override {
      const AddInputResult r = inner_->AddInput(pos, result);
      if (r == ENQUEUED_FOR_EVAL) ++pending_;
      return r;
    }
    void ComputeBlocking() override {
      inner_->ComputeBlocking();
      evals_->fetch_add(pending_, std::memory_order_relaxed);
      pending_ = 0;
    }

   private:
    std::unique_ptr<BackendComputation> inner_;
    std::atomic<int64_t>* evals_;
    int64_t pending_ = 0;
  };

  Backend* inner_;
  std::atomic<int64_t> evals_{0};
};

struct Job {
  bool research = false;
  bool arena = false;
  bool a_white = true;  // arena: --weights plays white
  uint64_t id = 0;
  int temp_plies = 0;
  std::vector<std::string> moves;
};

// Parses one job line; returns false (with a message) for a malformed line.
bool ParseJob(const std::string& line, Job* job, std::string* error) {
  std::istringstream in(line);
  std::string kind;
  if (!(in >> kind >> job->id)) {
    *error = "expected '<G|S|A> <id> ...'";
    return false;
  }
  if (kind == "G") {
    job->research = false;
    if (!(in >> job->temp_plies) || job->temp_plies < 0) {
      *error = "G job needs <temp_plies> >= 0";
      return false;
    }
  } else if (kind == "S") {
    job->research = true;
  } else if (kind == "A") {
    int a_white = 0;
    job->arena = true;
    if (!(in >> job->temp_plies >> a_white) || job->temp_plies < 0 ||
        (a_white != 0 && a_white != 1)) {
      *error = "A job needs <temp_plies> >= 0 and <a_white> 0|1";
      return false;
    }
    job->a_white = a_white == 1;
  } else {
    *error = "unknown job kind '" + kind + "'";
    return false;
  }
  for (std::string m; in >> m;) job->moves.push_back(m);
  return true;
}

class Writer {
 public:
  explicit Writer(std::vector<uint8_t>* buf) : buf_(buf) {}
  template <typename T>
  void Put(T v) {
    const size_t at = buf_->size();
    buf_->resize(at + sizeof(T));
    std::memcpy(buf_->data() + at, &v, sizeof(T));
  }
  void PutAt(size_t at, uint32_t v) {
    std::memcpy(buf_->data() + at, &v, sizeof(v));
  }
  size_t size() const { return buf_->size(); }

 private:
  std::vector<uint8_t>* buf_;
};

// Moves from the start of the game to the tree's head, in absolute
// coordinates (as SelfPlayGame::GetMoves does).
std::vector<Move> AbsoluteMovesToHead(const classic::NodeTree& tree) {
  std::vector<Move> moves;
  for (classic::Node* node = tree.GetCurrentHead();
       node != tree.GetGameBeginNode(); node = node->GetParent()) {
    moves.push_back(node->GetParent()->GetEdgeToNode(node)->GetMove());
  }
  std::vector<Move> result;
  Position pos = tree.GetPositionHistory().Starting();
  while (!moves.empty()) {
    Move move = moves.back();
    moves.pop_back();
    pos = Position(pos, move);
    // The position is already flipped, so flip the move if white is to move.
    if (!pos.IsBlackToMove()) move.Flip();
    result.push_back(move);
  }
  return result;
}

class TreePlay {
 public:
  TreePlay(const OptionsDict& options, Backend* backend,
           CountingBackend* counter, Backend* backend_b,
           CountingBackend* counter_b, const OptionsDict& arena_options)
      : options_(options),
        arena_options_(arena_options),
        backend_(backend),
        counter_(counter),
        backend_b_(backend_b),
        counter_b_(counter_b),
        visits_(options.Get<int>(kVisitsId)),
        max_ply_(options.Get<int>(kMaxPlyId)) {
    const std::string out = options.Get<std::string>(kOutputId);
    out_ = std::fopen(out.c_str(), "ab");
    if (!out_) throw Exception("cannot open output file " + out);
    const int seed = options.Get<int>(kSeedId);
    seed_ = seed ? static_cast<uint64_t>(seed) : std::random_device{}();
  }
  ~TreePlay() {
    if (out_) std::fclose(out_);
  }

  void Run() {
    const int parallelism = options_.Get<int>(kParallelismId);
    std::cerr << "[treeplay] visits " << visits_ << ", parallelism "
              << parallelism << ", max ply " << max_ply_ << ", seed " << seed_
              << std::endl;
    const auto start = std::chrono::steady_clock::now();
    std::thread reader([this] { ReadJobs(); });
    std::vector<std::thread> workers;
    for (int i = 0; i < parallelism; ++i) {
      workers.emplace_back([this, i] { Work(i); });
    }
    std::thread reporter;
    const int report_seconds = options_.Get<int>(kReportSecondsId);
    if (report_seconds > 0) {
      reporter = std::thread([this, report_seconds, start] {
        std::unique_lock<std::mutex> lock(report_mutex_);
        while (!report_cv_.wait_for(lock, std::chrono::seconds(report_seconds),
                                    [this] { return finished_; })) {
          Report(start);
        }
      });
    }
    reader.join();
    for (auto& t : workers) t.join();
    {
      std::lock_guard<std::mutex> lock(report_mutex_);
      finished_ = true;
    }
    report_cv_.notify_all();
    if (reporter.joinable()) reporter.join();
    Report(start);
    std::lock_guard<std::mutex> lock(out_mutex_);
    std::cout << "HET " << Evals() << " " << jobs_done_
              << std::endl;
  }

 private:
  void Report(std::chrono::steady_clock::time_point start) {
    const double seconds =
        std::chrono::duration<double>(std::chrono::steady_clock::now() - start)
            .count();
    const int64_t evals = Evals();
    int64_t jobs;
    {
      std::lock_guard<std::mutex> lock(out_mutex_);
      jobs = jobs_done_;
    }
    std::fprintf(stderr,
                 "[treeplay] %.0f s, %lld evals, %.0f evals/s, %lld jobs done\n",
                 seconds, static_cast<long long>(evals),
                 seconds > 0 ? evals / seconds : 0.0,
                 static_cast<long long>(jobs));
  }

  void ReadJobs() {
    for (std::string line; std::getline(std::cin, line);) {
      if (!line.empty() && line.back() == '\r') line.pop_back();
      if (line.find_first_not_of(" \t") == std::string::npos) continue;
      Job job;
      std::string error;
      if (!ParseJob(line, &job, &error)) {
        std::lock_guard<std::mutex> lock(out_mutex_);
        std::cout << "LOI " << job.id << " " << error << std::endl;
        continue;
      }
      {
        std::lock_guard<std::mutex> lock(queue_mutex_);
        queue_.push_back(std::move(job));
      }
      queue_cv_.notify_one();
    }
    {
      std::lock_guard<std::mutex> lock(queue_mutex_);
      input_done_ = true;
    }
    queue_cv_.notify_all();
  }

  // Network evaluations of both networks (the second one only for arena jobs).
  int64_t Evals() const {
    return counter_->evals() + (counter_b_ ? counter_b_->evals() : 0);
  }

  std::optional<Job> NextJob() {
    std::unique_lock<std::mutex> lock(queue_mutex_);
    queue_cv_.wait(lock, [this] { return !queue_.empty() || input_done_; });
    if (queue_.empty()) return std::nullopt;
    Job job = std::move(queue_.front());
    queue_.pop_front();
    return job;
  }

  void Work(int index) {
    std::mt19937_64 rng(seed_ + 0x9e3779b97f4a7c15ULL * (index + 1));
    std::vector<uint8_t> record;
    while (auto job = NextJob()) {
      record.clear();
      int8_t res = 0;
      try {
        if (job->arena && !backend_b_) {
          throw Exception("A job needs --weights2");
        }
        res = PlayJob(*job, &rng, &record);
      } catch (const std::exception& e) {
        std::lock_guard<std::mutex> lock(out_mutex_);
        std::cout << "LOI " << job->id << " " << e.what() << std::endl;
        continue;
      }
      std::lock_guard<std::mutex> lock(out_mutex_);
      if (std::fwrite(record.data(), 1, record.size(), out_) !=
              record.size() ||
          std::fflush(out_) != 0) {
        throw Exception("cannot write the output file");
      }
      ++jobs_done_;
      std::cout << "XONG " << job->id << " " << Evals();
      if (job->arena) std::cout << " " << static_cast<int>(res);
      std::cout << std::endl;
    }
  }

  // Returns the result, white's view (0 when stopped at max ply).
  int8_t PlayJob(const Job& job, std::mt19937_64* rng,
                 std::vector<uint8_t>* record) {
    // Same as NodeTree::ResetToPosition(fen, moves), but rejects illegal
    // moves: lc0's ParseMove only decodes the string.
    GameState state;
    state.startpos = Position::FromFen(ChessBoard::kStartposFen);
    ChessBoard board = state.startpos.GetBoard();
    state.moves.reserve(job.moves.size());
    for (const auto& s : job.moves) {
      const Move m = board.ParseMove(s);
      const MoveList legal = board.GenerateLegalMoves();
      if (std::find(legal.begin(), legal.end(), m) == legal.end()) {
        throw Exception("illegal move " + s);
      }
      state.moves.push_back(m);
      board.ApplyMove(m);
      board.Mirror();
    }
    classic::NodeTree tree;
    tree.ResetToPosition(state);
    const std::vector<Move> path = AbsoluteMovesToHead(tree);

    Writer w(record);
    w.Put<char>('C');
    w.Put<char>('V');
    w.Put<char>('G');
    w.Put<char>('1');
    const size_t size_at = w.size();
    w.Put<uint32_t>(0);
    w.Put<uint64_t>(job.id);
    w.Put<uint8_t>(job.arena ? 2 : job.research ? 1 : 0);
    const size_t result_at = w.size();
    w.Put<int8_t>(0);
    w.Put<uint8_t>(0);
    w.Put<uint8_t>(0);
    w.Put<uint16_t>(static_cast<uint16_t>(path.size()));
    const size_t plies_at = w.size();
    w.Put<uint16_t>(0);
    for (Move m : path) w.Put<uint16_t>(m.raw_data());

    GameResult result = GameResult::UNDECIDED;
    uint8_t end = job.research ? 2 : 0;
    int plies = 0;
    while (true) {
      const PositionHistory& history = tree.GetPositionHistory();
      result = history.ComputeGameResult();
      if (result != GameResult::UNDECIDED) break;
      if (job.research && plies == 1) break;
      if (!job.research && history.Last().GetGamePly() >= max_ply_) {
        end = 1;
        break;
      }
      // Arena: the side to move's network searches, without noise.
      const bool by_a = !job.arena || (tree.IsBlackToMove() != job.a_white);
      const Move move = SearchAndRecord(&tree, job, rng, &w,
                                        by_a ? backend_ : backend_b_,
                                        job.arena ? arena_options_ : options_);
      ++plies;
      if (job.research) continue;
      Move to_play = move;
      if (tree.IsBlackToMove()) to_play.Flip();
      tree.MakeMove(to_play);
    }

    int8_t res = 0;
    if (!job.research && end == 0) {
      res = result == GameResult::WHITE_WON   ? 1
            : result == GameResult::BLACK_WON ? -1
                                              : 0;
    }
    std::memcpy(record->data() + result_at, &res, 1);
    std::memcpy(record->data() + result_at + 1, &end, 1);
    const uint16_t plies16 = static_cast<uint16_t>(plies);
    std::memcpy(record->data() + plies_at, &plies16, 2);
    w.PutAt(size_at, static_cast<uint32_t>(record->size()));
    return res;
  }

  // Runs one search at the tree's head, appends its statistics and returns
  // the move to play, in absolute coordinates.
  Move SearchAndRecord(classic::NodeTree* tree, const Job& job,
                       std::mt19937_64* rng, Writer* w, Backend* backend,
                       const OptionsDict& options) {
    // A fresh root every move, as in lc0 self-play: Dirichlet noise is mixed
    // into the root's priors when the root is expanded.
    tree->TrimTreeAtHead();
    auto stopper = std::make_unique<classic::ChainedSearchStopper>();
    stopper->AddStopper(
        std::make_unique<classic::VisitsStopper>(visits_, false));
    classic::PopulateIntrinsicStoppers(stopper.get(), options);
    auto responder = std::make_unique<CallbackUciResponder>(
        [](const BestMoveInfo&) {}, [](const std::vector<ThinkingInfo>&) {});
    auto search = std::make_unique<classic::Search>(
        *tree, backend, std::move(responder), MoveList(),
        std::chrono::steady_clock::now(), std::move(stopper),
        /*infinite=*/false, /*ponder=*/false, options, /*syzygy_tb=*/nullptr);
    search->RunBlocking(1);

    const classic::Eval best_eval = search->GetBestEval();
    const Move best_move = search->GetBestMove().first;
    classic::Node* node = tree->GetCurrentHead();
    const bool black = tree->IsBlackToMove();
    const PositionHistory& history = tree->GetPositionHistory();
    const int game_ply = history.Last().GetGamePly();

    const MoveList legal_moves = history.Last().GetBoard().GenerateLegalMoves();
    const std::optional<EvalResult> raw = backend->GetCachedEvaluation(
        EvalPosition{history.GetPositions(), legal_moves});

    // Move to play: visit-count sampling (temperature 1) before temp_plies,
    // otherwise the search's best move (most visits).
    Move played = best_move;
    if (!job.research && game_ply < job.temp_plies &&
        node->GetChildrenVisits() > 0) {
      std::uniform_int_distribution<uint32_t> dist(
          0, node->GetChildrenVisits() - 1);
      uint32_t pick = dist(*rng);
      for (const auto& edge : node->Edges()) {
        if (pick < edge.GetN()) {
          played = edge.GetMove(black);
          break;
        }
        pick -= edge.GetN();
      }
    }

    const float nan = std::numeric_limits<float>::quiet_NaN();
    float p0 = 0.0f;
    uint16_t visited = 0;
    for (const auto& edge : node->Edges()) {
      if (edge.GetN() == 0) {
        p0 += edge.GetP();
      } else {
        ++visited;
      }
    }
    w->Put<uint16_t>(played.raw_data());
    w->Put<uint16_t>(visited);
    w->Put<uint32_t>(node->GetChildrenVisits());
    w->Put<float>(best_eval.wl);
    w->Put<float>(best_eval.d);
    w->Put<float>(raw ? raw->q : nan);
    w->Put<float>(raw ? raw->d : nan);
    w->Put<float>(p0);
    for (const auto& edge : node->Edges()) {
      const uint32_t n = edge.GetN();
      if (n == 0) continue;
      float raw_p = nan;
      if (raw) {
        const auto it = std::find(legal_moves.begin(), legal_moves.end(),
                                  edge.GetMove());
        if (it != legal_moves.end()) raw_p = raw->p[it - legal_moves.begin()];
      }
      w->Put<uint16_t>(edge.GetMove(black).raw_data());
      w->Put<uint16_t>(static_cast<uint16_t>(std::min<uint32_t>(n, 65535)));
      w->Put<uint16_t>(FP32toFP16(edge.GetWL(0.0f)));
      w->Put<uint16_t>(FP32toFP16(edge.GetD(0.0f)));
      w->Put<uint16_t>(FP32toFP16(edge.GetP()));
      w->Put<uint16_t>(FP32toFP16(raw_p));
    }
    return played;
  }

  const OptionsDict& options_;
  const OptionsDict& arena_options_;
  Backend* backend_;
  CountingBackend* counter_;
  Backend* backend_b_;
  CountingBackend* counter_b_;
  const int visits_;
  const int max_ply_;
  uint64_t seed_ = 0;
  std::FILE* out_ = nullptr;

  std::mutex queue_mutex_;
  std::condition_variable queue_cv_;
  std::deque<Job> queue_;
  bool input_done_ = false;

  std::mutex out_mutex_;
  int64_t jobs_done_ = 0;

  std::mutex report_mutex_;
  std::condition_variable report_cv_;
  bool finished_ = false;
};

void PopulateOptions(OptionsParser* options) {
  SharedBackendParams::Populate(options);
  classic::SearchParams::Populate(options);
  classic::PopulateTimeManagementOptions(classic::RunType::kSelfplay, options);
  options->Add<IntOption>(kVisitsId, 1, 1000000) = 800;
  options->Add<IntOption>(kParallelismId, 1, 1024) = 16;
  options->Add<StringOption>(kOutputId) = "treeplay.bin";
  options->Add<IntOption>(kMaxPlyId, 1, 10000) = 450;
  options->Add<IntOption>(kSeedId, 0, std::numeric_limits<int>::max()) = 0;
  options->Add<IntOption>(kReportSecondsId, 0, 86400) = 0;
  options->Add<StringOption>(kWeights2Id) = "";

  // lc0's self-play defaults (src/selfplay/tournament.cc), with the choices
  // of the chess-variant project's self-play (THIET_KE_CO_VUA.md 2.5):
  // cpuct 1.3 instead of 1.2, no prefetch, Dirichlet alpha 0.3. Temperature
  // is 0 here because the move is chosen in SearchAndRecord, by game ply.
  auto* d = options->GetMutableDefaultsOptions();
  d->Set<int>(classic::SearchParams::kMiniBatchSizeId, 32);
  d->Set<float>(classic::SearchParams::kCpuctId, 1.3f);
  d->Set<float>(classic::SearchParams::kCpuctAtRootId, 1.3f);
  d->Set<float>(classic::SearchParams::kCpuctFactorId, 0.0f);
  d->Set<float>(classic::SearchParams::kCpuctFactorAtRootId, 0.0f);
  d->Set<float>(SharedBackendParams::kPolicySoftmaxTemp, 1.0f);
  d->Set<int>(classic::SearchParams::kMaxCollisionVisitsId, 1);
  d->Set<int>(classic::SearchParams::kMaxCollisionEventsId, 1);
  d->Set<int>(classic::SearchParams::kCacheHistoryLengthId, 7);
  d->Set<bool>(classic::SearchParams::kOutOfOrderEvalId, false);
  d->Set<float>(classic::SearchParams::kTemperatureId, 0.0f);
  d->Set<float>(classic::SearchParams::kNoiseEpsilonId, 0.25f);
  d->Set<float>(classic::SearchParams::kNoiseAlphaId, 0.3f);
  d->Set<float>(classic::SearchParams::kFpuValueId, 0.0f);
  d->Set<std::string>(SharedBackendParams::kHistoryFill, "no");
  d->Set<std::string>(SharedBackendParams::kBackendId, "multiplexing");
  d->Set<bool>(classic::SearchParams::kStickyEndgamesId, false);
  d->Set<bool>(classic::SearchParams::kTwoFoldDrawsId, false);
  d->Set<int>(classic::SearchParams::kTaskWorkersPerSearchWorkerId, 0);
  d->Set<int>(classic::SearchParams::kMaxPrefetchBatchId, 0);
}

}  // namespace

void RunTreePlay() {
  OptionsParser parser;
  PopulateOptions(&parser);
  if (!parser.ProcessAllFlags()) return;
  const OptionsDict& options = parser.GetOptionsDict();

  std::unique_ptr<Backend> cached =
      CreateMemCache(BackendManager::Get()->CreateFromParams(options), options);
  CountingBackend counter(cached.get());
  // Arena: the second network gets its own backend and cache, from the same
  // options with --weights replaced (a child dict falls back to its parent).
  OptionsDict options_b(&options);
  std::unique_ptr<Backend> cached_b;
  std::unique_ptr<CountingBackend> counter_b;
  const std::string weights2 = options.Get<std::string>(kWeights2Id);
  if (!weights2.empty()) {
    options_b.Set<std::string>(SharedBackendParams::kWeightsId, weights2);
    cached_b = CreateMemCache(BackendManager::Get()->CreateFromParams(options_b),
                              options_b);
    counter_b = std::make_unique<CountingBackend>(cached_b.get());
  }
  // Arena searches: same parameters as self-play, without Dirichlet noise
  // (as the arena of the chess-variant engine).
  OptionsDict arena_options(&options);
  arena_options.Set<float>(classic::SearchParams::kNoiseEpsilonId, 0.0f);
  TreePlay play(options, &counter, &counter, counter_b.get(), counter_b.get(),
                arena_options);
  play.Run();
}

}  // namespace lczero
