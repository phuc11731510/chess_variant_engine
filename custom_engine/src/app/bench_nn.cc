// Bench: PURE neural-network inference, with no MCTS, no tree, no cache.
//
// Why this exists. The self-play numbers mix two things that need separating:
// how fast the device evaluates positions, and how much throughput the engine
// loses coordinating CPU and GPU around those evaluations.
//
// Why it lives in the ENGINE and not in a Python script: it must use the exact
// ONNX Runtime the engine links (1.20.1), the same session options and the same
// buffers. A Python benchmark installs whatever `pip` resolves -- on a Python
// 3.13 Colab that is a much newer ORT built for a different CUDA major, which
// measures a stack the engine never runs.
//
// WHAT IT SWEEPS. The variable that matters is the BATCH PROFILE, not the
// number of inputs handed to one profile: on CUDA the backend always compiles a
// fixed-batch session (see onnx_backend.cc, "CUDA/TensorRT always use a
// fixed-batch profile"), so every Run() computes exactly fixed_batch slots no
// matter how many were enqueued. Sweeping inputs inside one profile therefore
// only measures padding waste. This builds a SEPARATE session per batch size
// and runs each one full.
//
//   custom_engine --bench-nn --weights net.onnx --provider cuda
//   custom_engine --bench-nn --weights net.onnx --provider cpu --backend-threads 2

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

// FLOPs per position for the 12x144 SE-ResNet on a 10x10 board, read off the
// ONNX graph by scripts/bench_ort.py. Only used to print TFLOP/s so the number
// is comparable with the device's nominal peak.
constexpr double kGFlopsPerPosition = 0.997;

struct Sample {
  int batch = 0;
  double ms_per_run = 0.0;
  double pos_per_sec = 0.0;
};

// Deliberately the RAW OnnxBackend: no ZeroHeapCache (a cache would turn every
// repeat of the same position into a hit, timing a hash lookup instead of the
// network) and no BatchingBackend (that is the coordination layer we want to
// exclude).
std::unique_ptr<lczero::Backend> MakeRawOnnx(const EngineOptions& o,
                                             int fixed_batch,
                                             std::string* opts_out) {
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
  if (opts_out) *opts_out = bo;

  auto be = std::make_unique<lczero::OnnxBackend>();
  be->UpdateConfiguration(parser.GetOptionsDict());
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
  std::cout << "the co      : startpos, " << legal.size() << " nuoc hop le\n";
  std::cout << "provider    : " << o.sp_provider << "\n";
  std::cout << "tran batch  : " << lczero::MaxBatchSize << " (MaxBatchSize)\n";

  // Time `batch` inputs through a session compiled for exactly that batch.
  auto measure = [&](lczero::Backend* backend, int batch) -> Sample {
    std::vector<lczero::EvalResult> res(batch);
    for (auto& r : res) r.p.resize(legal.size());

    auto one_run = [&]() {
      auto comp = backend->CreateComputation();
      for (int i = 0; i < batch; ++i) comp->AddInput(ep, res[i].AsPtr());
      comp->ComputeBlocking();
    };
    // Warm up: the first calls pay session setup and shape specialization.
    for (int i = 0; i < 5; ++i) one_run();

    const int iters = batch >= 64 ? 15 : 40;
    const auto t0 = std::chrono::steady_clock::now();
    for (int i = 0; i < iters; ++i) one_run();
    const double secs =
        std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();

    const double per_run = secs / iters;
    return Sample{batch, per_run * 1000.0, batch / per_run};
  };

  // ---- Main sweep: one SESSION PER BATCH SIZE, each run full ----------------
  std::cout << "\n--- Quet BATCH PROFILE (moi co batch = mot session rieng) ---\n";
  std::printf("%7s %13s %10s %11s %12s\n",
              "batch", "pos/giay", "TFLOP/s", "ms/Run", "us/vi tri");
  std::printf("%s\n", std::string(57, '-').c_str());

  std::vector<Sample> samples;
  for (int b : {1, 2, 4, 8, 16, 32, 64, 128, 256}) {
    if (static_cast<size_t>(b) > lczero::MaxBatchSize) continue;
    std::unique_ptr<lczero::Backend> backend;
    std::string bo;
    try {
      backend = MakeRawOnnx(o, b, &bo);
    } catch (const std::exception& e) {
      std::cerr << "  batch " << b << ": khong nap duoc backend: " << e.what() << "\n";
      continue;
    }
    const Sample s = measure(backend.get(), b);
    std::printf("%7d %13.1f %10.2f %11.3f %12.1f\n", s.batch, s.pos_per_sec,
                s.pos_per_sec * kGFlopsPerPosition / 1000.0, s.ms_per_run,
                s.ms_per_run * 1000.0 / s.batch);
    samples.push_back(s);
  }

  // ---- Separate the per-Run fixed cost from the per-position cost ----------
  // Least squares on ms = a + b*batch. `a` is what bigger batches amortize.
  if (samples.size() >= 3) {
    double n = 0, sx = 0, sy = 0, sxx = 0, sxy = 0;
    for (const auto& s : samples) {
      const double x = s.batch, y = s.ms_per_run;
      n += 1; sx += x; sy += y; sxx += x * x; sxy += x * y;
    }
    const double den = n * sxx - sx * sx;
    if (den != 0.0) {
      const double slope = (n * sxy - sx * sy) / den;      // ms per position
      const double intercept = (sy - slope * sx) / n;      // ms per Run, fixed
      std::printf("\nKhop tuyen tinh: ms/Run  ~=  %.3f + %.4f * batch\n",
                  intercept, slope);
      std::printf("  chi phi moi VI TRI      : %.4f ms  (=> %.2f TFLOP/s tiem can)\n",
                  slope, slope > 0 ? kGFlopsPerPosition / slope : 0.0);
      if (intercept > 0.05) {
        std::printf("  chi phi CO DINH moi Run : %.3f ms  <-- batch lon se pha loang\n",
                    intercept);
        const auto& big = samples.back();
        std::printf("  o batch %d no chiem %.1f%% thoi gian; o batch %d chiem %.1f%%\n",
                    samples.front().batch,
                    100.0 * intercept / samples.front().ms_per_run,
                    big.batch, 100.0 * intercept / big.ms_per_run);
      } else {
        std::printf("  chi phi CO DINH moi Run : ~0 (he so chan %.2f ms)\n", intercept);
        std::printf("  => THUAN compute-bound: batch lon KHONG pha loang duoc gi.\n");
      }
    }
  }

  // ---- Padding cost: same session, fewer inputs than the profile -----------
  const int prod = o.sp_fixed_batch > 0 ? o.sp_fixed_batch : 16;
  if (static_cast<size_t>(prod) <= lczero::MaxBatchSize) {
    std::string bo;
    std::unique_ptr<lczero::Backend> backend;
    try {
      backend = MakeRawOnnx(o, prod, &bo);
    } catch (const std::exception&) {
      backend.reset();
    }
    if (backend) {
      std::cout << "\n--- Chi phi PADDING: session fixed_batch=" << prod
                << " nhung nop it hon ---\n";
      std::printf("%7s %13s %11s\n", "nop", "pos/giay", "ms/Run");
      std::printf("%s\n", std::string(33, '-').c_str());
      for (int b : {1, prod / 4, prod / 2, prod}) {
        if (b < 1 || b > prod) continue;
        const Sample s = measure(backend.get(), b);
        std::printf("%7d %13.1f %11.3f\n", s.batch, s.pos_per_sec, s.ms_per_run);
      }
      std::cout << "  (ms/Run gan nhu khong doi = GPU van tinh du " << prod
                << " o; phan thua la phi)\n";
    }
  }

  std::cout << "\nMOC SO SANH: self-play dat ~2900 NN eval/giay o fixed_batch=16.\n"
               "  neu cot pos/giay o batch lon CAO HON HAN -> batch lon la don bay\n"
               "  neu no phang -> GPU da bao hoa tinh toan, batch khong giup\n";
  return 0;
}
