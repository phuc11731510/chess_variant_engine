// Bench: the CPU side of self-play, operation by operation (--bench-cpu).
//
// Self-play is GPU-bound on Colab, so these costs only matter when the CPU
// becomes the limit (few vCPUs, many parallel games, a faster GPU). This mode
// gives the numbers to decide whether an optimization of the rules layer, the
// bridge or the record writer is worth doing -- measure before rewriting.
//
//   custom_engine --bench-cpu [--games N]      (default 40 random games)
//
// Positions come from random games from the start position, so move counts and
// piece counts are those of real play. Each figure is the best of 3 rounds (a
// laptop's clock and core type change under the benchmark), and every timed
// loop feeds a checksum that is printed, so the compiler cannot drop the work.

#include "app/bench_cpu.h"

#include <algorithm>
#include <chrono>
#include <cstdio>
#include <functional>
#include <iostream>
#include <memory>
#include <random>
#include <string>
#include <vector>

#include "app/cli.h"
#include "app/variant_setup.h"
#include "chess/board.h"
#include "chess/encoder.h"
#include "chess/position.h"
#include "movegen.h"
#include "trainingdata/trainingdata_v1.h"
#include "trainingdata/writer.h"
#include "selfplay/training_extract.h"

namespace {

using Clock = std::chrono::steady_clock;

// Runs `round` (which returns how many operations it timed and adds the time it
// measured to *ns) three times and prints the best ns/op.
void bench(const char* what, const std::function<uint64_t(double*)>& round) {
  double best = 1e300;
  uint64_t ops = 0;
  for (int r = 0; r < 3; ++r) {
    double ns = 0.0;
    ops = round(&ns);
    if (ops) best = std::min(best, ns / double(ops));
  }
  std::printf("  %-48s %10.0f ns/op   (%llu ops/round)\n", what, ops ? best : 0.0,
              static_cast<unsigned long long>(ops));
}

double since(Clock::time_point t0) {
  return std::chrono::duration<double, std::nano>(Clock::now() - t0).count();
}

}  // namespace

int run_bench_cpu(const EngineOptions& o) {
  setup_custom_variant();
  const int games = o.sp_games > 0 && o.sp_games != 100 ? o.sp_games : 40;
  std::cout << "=== BENCH-CPU: CPU cost of self-play operations (" << games
            << " random games) ===" << std::endl;

  // Histories at every 8th ply of random games (up to 160 plies each).
  std::mt19937_64 rng(0xBE7C4ULL);
  std::vector<std::unique_ptr<lczero::PositionHistory>> snaps;
  for (int g = 0; g < games; ++g) {
    auto h = std::make_unique<lczero::PositionHistory>();
    h->Reset(lczero::Position::FromFen(lczero::ChessBoard::kStartposFen));
    for (int ply = 0; ply < 160; ++ply) {
      const lczero::MoveList lm = h->Last().GenerateLegalMoves();
      if (lm.empty() || h->ComputeGameResult() != lczero::GameResult::UNDECIDED) break;
      if (ply % 8 == 5) snaps.push_back(std::make_unique<lczero::PositionHistory>(*h));
      h->Append(lm[static_cast<size_t>(rng() % lm.size())]);
    }
  }
  uint64_t moves_total = 0;
  for (const auto& h : snaps) moves_total += h->Last().GenerateLegalMoves().size();
  std::cout << "  " << snaps.size() << " positions, "
            << double(moves_total) / double(std::max<size_t>(snaps.size(), 1))
            << " legal moves per position on average" << std::endl;
  uint64_t sink = 0;

  bench("Fairy-Stockfish MoveList<LEGAL>", [&](double* ns) {
    const auto t0 = Clock::now();
    for (const auto& h : snaps) sink += Stockfish::MoveList<Stockfish::LEGAL>(h->Last().GetBoard().GetRawPosition()).size();
    *ns += since(t0);
    return uint64_t(snaps.size());
  });
  bench("ChessBoard::GenerateLegalMoves (adapter)", [&](double* ns) {
    const auto t0 = Clock::now();
    for (const auto& h : snaps) sink += h->Last().GenerateLegalMoves().size();
    *ns += since(t0);
    return uint64_t(snaps.size());
  });
  bench("PositionHistory::Append + Pop (one ply)", [&](double* ns) {
    uint64_t ops = 0;
    for (auto& h : snaps) {
      const lczero::MoveList lm = h->Last().GenerateLegalMoves();
      const auto t0 = Clock::now();
      for (size_t i = 0; i < lm.size() && i < 16; ++i) {
        h->Append(lm[i]);
        sink += static_cast<uint64_t>(h->Last().GetRepetitions());
        h->Pop();
        ++ops;
      }
      *ns += since(t0);
    }
    return ops;
  });
  bench("ComputeMctsResult (legal moves given)", [&](double* ns) {
    for (const auto& h : snaps) {
      const lczero::MoveList lm = h->Last().GenerateLegalMoves();
      const auto t0 = Clock::now();
      sink += static_cast<uint64_t>(h->ComputeMctsResult(lm));
      *ns += since(t0);
    }
    return uint64_t(snaps.size());
  });
  bench("ComputeGameResult (incl. its move generation)", [&](double* ns) {
    const auto t0 = Clock::now();
    for (const auto& h : snaps) sink += static_cast<uint64_t>(h->ComputeGameResult());
    *ns += since(t0);
    return uint64_t(snaps.size());
  });
  lczero::InputPlanes planes;
  std::vector<float> dense((lczero::kAuxPlaneBase + lczero::kAuxPlanesCount) * 100);
  bench("EncodePositionForNN", [&](double* ns) {
    int t = 0;
    const auto t0 = Clock::now();
    for (const auto& h : snaps) {
      lczero::EncodePositionForNN(*h, lczero::kMoveHistory, lczero::FillEmptyHistory::FEN_ONLY, &planes, &t);
      sink += static_cast<uint64_t>(bool(planes[5].mask));
    }
    *ns += since(t0);
    return uint64_t(snaps.size());
  });
  bench("UnpackInputPlanes (22600 floats)", [&](double* ns) {
    int t = 0;
    for (const auto& h : snaps) {
      lczero::EncodePositionForNN(*h, lczero::kMoveHistory, lczero::FillEmptyHistory::FEN_ONLY, &planes, &t);
      const auto t0 = Clock::now();
      lczero::UnpackInputPlanes(planes, dense.data(), 10, 10);
      *ns += since(t0);
      sink += static_cast<uint64_t>(dense[500]);
    }
    return uint64_t(snaps.size());
  });
  bench("MoveToNNIndex (per move)", [&](double* ns) {
    uint64_t ops = 0;
    for (const auto& h : snaps) {
      const lczero::MoveList lm = h->Last().GenerateLegalMoves();
      const auto t0 = Clock::now();
      for (const auto& m : lm) sink += lczero::MoveToNNIndex(m, 0);
      *ns += since(t0);
      ops += lm.size();
    }
    return ops;
  });
  bench("ChessBoard copy", [&](double* ns) {
    const auto t0 = Clock::now();
    for (const auto& h : snaps) {
      lczero::ChessBoard b(h->Last().GetBoard());
      sink += b.Hash() & 1;
    }
    *ns += since(t0);
    return uint64_t(snaps.size());
  });
  {
    const lczero::PositionHistory* longest = snaps.front().get();
    for (const auto& h : snaps)
      if (h->GetLength() > longest->GetLength()) longest = h.get();
    auto copy = std::make_unique<lczero::PositionHistory>();
    char label[96];
    std::snprintf(label, sizeof(label), "PositionHistory copy-assign (%d plies)", longest->GetLength());
    bench(label, [&](double* ns) {
      const auto t0 = Clock::now();
      for (int r = 0; r < 100; ++r) {
        *copy = *longest;
        sink += copy->GetLength();
      }
      *ns += since(t0);
      return uint64_t(100);
    });
  }
  std::vector<lczero::TrainingDataV1> recs(snaps.size());
  bench("record: pi = -1 fill + EncodePlanesIntoRecord", [&](double* ns) {
    const auto t0 = Clock::now();
    for (size_t i = 0; i < snaps.size(); ++i) {
      std::fill_n(recs[i].probabilities, lczero::kPolicySize, -1.0f);
      lczero::EncodePlanesIntoRecord(*snaps[i], recs[i]);
      sink += recs[i].rule50_count;
    }
    *ns += since(t0);
    return uint64_t(snaps.size());
  });
  const std::string file = std::string("bench_cpu_tmp") + lczero::TrainingDataWriter::Extension();
  bench("TrainingDataWriter per record (gzip + disk)", [&](double* ns) {
    const auto t0 = Clock::now();
    lczero::TrainingDataWriter w(file);
    for (const auto& r : recs) w.WriteChunk(r);
    w.Finalize();
    *ns += since(t0);
    return uint64_t(recs.size());
  });
  if (FILE* f = std::fopen(file.c_str(), "rb")) {
    std::fseek(f, 0, SEEK_END);
    const long bytes = std::ftell(f);
    std::fclose(f);
    std::printf("  %-48s %10.0f bytes/record on disk (raw %zu)\n", "  (compressed size)",
                double(bytes) / double(recs.size()), sizeof(lczero::TrainingDataV1));
  }
  std::remove(file.c_str());

  std::cout << "  checksum " << sink << std::endl;
  return 0;
}
