// Bench: PURE neural-network inference, with no MCTS, no tree, no game logic.
//
// Why this exists. The self-play numbers mix two things that need separating:
// how fast the device evaluates positions, and how much throughput the engine
// loses coordinating CPU and GPU around those evaluations. Measuring inference
// alone tells us which one is the ceiling.
//
// Why it lives in the ENGINE and not in a Python script: it must use the exact
// same ONNX Runtime the engine links (1.20.1), the same session options and the
// same buffers. A Python benchmark installs whatever `pip` resolves -- which on
// a Python 3.13 Colab is a much newer ORT built for a different CUDA major, so
// it measures a stack the engine never runs.
//
//   custom_engine --bench-nn --weights net.onnx --provider cuda
//   custom_engine --bench-nn --weights net.onnx --provider cpu --backend-threads 2
//
// Reads --fixed-batch: 0/unset sweeps DYNAMIC batch shapes; a positive value
// additionally reports the production path, where every Run() is padded up to
// that size.

#include "app/bench_nn.h"

#include <algorithm>
#include <chrono>
#include <cstdio>
#include <iostream>
#include <memory>
#include <span>
#include <string>
#include <vector>

#include "app/cli.h"
#include "app/variant_setup.h"
#include "chess/board.h"
#include "chess/position.h"
#include "neural/backend.h"
#include "neural/onnx_backend.h"
#include "neural/shared_params.h"
#include "search/classic/params.h"
#include "utils/optionsparser.h"

namespace {

// FLOPs per position for the 12x144 SE-ResNet on a 10x10 board, measured from
// the ONNX graph by scripts/bench_ort.py. Only used to print TFLOP/s so the
// result is comparable with the GPU's nominal peak.
constexpr double kGFlopsPerPosition = 0.997;

struct Row {
  int batch;
  double pos_per_sec;
  double ms_per_run;
};

// Deliberately the RAW OnnxBackend: no ZeroHeapCache, no BatchingBackend.
// A cache would turn every repeat of the same position into a hit and we would
// be timing a hash lookup instead of the network.
std::unique_ptr<lczero::Backend> MakeRawOnnxBackend(
    const lczero::OptionsDict& opts) {
  auto be = std::make_unique<lczero::OnnxBackend>();
  be->UpdateConfiguration(opts);
  return be;
}

}  // namespace

int run_bench_nn(const EngineOptions& o) {
  std::cout << "=== Bench: PURE NN inference (khong MCTS, khong cay) ===\n";
  setup_custom_variant();

  // One real position is enough: we are timing the network, not the search.
  // The same position is submitted `batch` times -- ORT does not care, and the
  // per-position cost is what we want.
  lczero::ChessBoard board(std::string{lczero::ChessBoard::kStartposFen});
  auto history = std::make_unique<lczero::PositionHistory>();
  history->Reset(board, 0, 1);
  lczero::MoveList legal = history->Last().GetBoard().GenerateLegalMoves();
  const lczero::EvalPosition ep{
      history.get(),
      std::span<const lczero::Move>(legal.data(), legal.size())};
  std::cout << "the co: startpos, " << legal.size() << " nuoc hop le\n";

  auto run_sweep = [&](const std::string& label, int fixed_batch) {
    lczero::OptionsParser parser;
    lczero::classic::SearchParams::Populate(&parser);
    auto* d = parser.GetMutableDefaultsOptions();
    d->Set<std::string>(lczero::SharedBackendParams::kWeightsId, o.weights_file);

    std::string bo;
    if (o.sp_provider == "cuda") {
      bo = "provider=cuda";
    } else if (o.sp_provider == "dml") {
      bo = "provider=dml,threads=" + std::to_string(std::max(1, o.sp_backend_threads));
    } else {
      bo = "threads=" + std::to_string(std::max(1, o.sp_backend_threads));
    }
    if (fixed_batch > 0) bo += ",fixed_batch=" + std::to_string(fixed_batch);
    d->Set<std::string>(lczero::SharedBackendParams::kBackendOptionsId, bo);

    std::unique_ptr<lczero::Backend> backend;
    try {
      backend = MakeRawOnnxBackend(parser.GetOptionsDict());
    } catch (const std::exception& e) {
      std::cerr << "FATAL: khong nap duoc backend: " << e.what() << std::endl;
      return false;
    }

    const size_t cap = backend->GetAttributes().maximum_batch_size;
    std::cout << "\n--- " << label << "  (backend-opts: " << bo
              << ", tran batch = " << cap << ") ---\n";
    std::printf("%7s %13s %12s %11s %12s\n", "batch", "pos/giay", "TFLOP/s",
                "ms/Run", "us/vi tri");
    std::printf("%s\n", std::string(59, '-').c_str());

    std::vector<Row> rows;
    for (int b : {1, 2, 4, 8, 16, 32, 64, 128, 256}) {
      if (static_cast<size_t>(b) > cap) continue;
      std::vector<lczero::EvalResult> res(b);
      for (auto& r : res) r.p.resize(legal.size());

      auto one_run = [&]() {
        auto comp = backend->CreateComputation();
        for (int i = 0; i < b; ++i) comp->AddInput(ep, res[i].AsPtr());
        comp->ComputeBlocking();
      };

      // Warm up: first call pays session/kernel setup and, for a fixed-batch
      // GPU profile, the shape specialization.
      for (int i = 0; i < 5; ++i) one_run();

      // Fewer iterations for big batches so the sweep stays quick.
      const int iters = b >= 64 ? 20 : 40;
      const auto t0 = std::chrono::steady_clock::now();
      for (int i = 0; i < iters; ++i) one_run();
      const double secs =
          std::chrono::duration<double>(std::chrono::steady_clock::now() - t0)
              .count();

      const double per_run = secs / iters;
      const double pps = b / per_run;
      // pos/s * GFLOP/pos = GFLOP/s; /1000 -> TFLOP/s.
      const double tflops = pps * kGFlopsPerPosition / 1000.0;
      std::printf("%7d %13.1f %12.2f %11.3f %12.1f\n", b, pps, tflops,
                  per_run * 1000.0, per_run * 1e6 / b);
      rows.push_back({b, pps, per_run * 1000.0});
    }
    return true;
  };

  // Dynamic shapes: every Run() gets exactly the batch we hand it, no padding.
  if (!run_sweep("DYNAMIC batch (khong pad)", 0)) return 1;

  // The production path also pads every Run() up to --fixed-batch.
  if (o.sp_fixed_batch > 0) {
    run_sweep("FIXED batch = " + std::to_string(o.sp_fixed_batch) +
                  " (giong self-play that)",
              o.sp_fixed_batch);
  }

  std::cout << "\nMOC SO SANH: self-play dat ~2200 NN eval/giay = ~2.2 TFLOP/s\n"
               "  suy luan thuan CAO HON NHIEU -> engine mat hieu nang o khau\n"
               "                                  dieu phoi CPU/GPU (sua duoc)\n"
               "  xap xi 2200                  -> backend chinh la tran that su\n";
  return 0;
}
