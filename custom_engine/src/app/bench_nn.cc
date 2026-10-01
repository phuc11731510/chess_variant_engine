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
//   custom_engine --bench-nn --weights net.onnx --provider cuda --fixed-batch 64 \
//       --cuda-opt prefer_nhwc=1      (sweep WITH the options + A/B vs ORT defaults)

#include "app/bench_nn.h"

#include <algorithm>
#include <array>
#include <cstring>
#include <functional>
#include <chrono>
#include <cmath>
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
#include <random>
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
                                             bool cuda_graph,
                                             std::string* opts_out,
                                             bool with_cuda_opts = true) {
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
  if (cuda_graph) bo += ",cuda_graph=1";
  if (with_cuda_opts && o.sp_provider == "cuda")
    for (const auto& kv : o.sp_cuda_opts) bo += ",cuda." + kv;
  d->Set<std::string>(lczero::SharedBackendParams::kBackendOptionsId, bo);
  if (opts_out) *opts_out = bo;

  auto be = std::make_unique<lczero::OnnxBackend>();
  be->UpdateConfiguration(parser.GetOptionsDict());
  return be;
}

// Runs ONE input through a backend and returns the raw result -- used to
// compare cuda_graph output against the non-graph path on the same position.
lczero::EvalResult RunOnce(lczero::Backend* backend, const lczero::EvalPosition& ep, size_t num_legal) {
  lczero::EvalResult res;
  res.p.resize(num_legal);
  auto comp = backend->CreateComputation();
  comp->AddInput(ep, res.AsPtr());
  comp->ComputeBlocking();
  return res;
}

// ---- Copy cost (E3 / E4) ----------------------------------------------------
// The backend hands ORT PAGEABLE host buffers: each Run() copies the input
// (batch x 22600 floats) to the GPU and the full policy (batch x 10600 floats)
// back. This times session->Run() alone (no encode, no softmax) four ways at
// the same fixed batch, so the gap is exactly the copy cost:
//   A  pageable in / pageable out          (what the backend does today)
//   B  pinned in / pinned out  (IoBinding)  (E3)
//   C  pinned in / GPU out                  (output copy removed: E4's upper bound)
//   D  GPU in / GPU out                     (no copy at all: floor)
// The input data is arbitrary (convolution time does not depend on values).
void BenchCopyCost(lczero::OnnxBackend* be, int batch) {
  Ort::Session* sess = be->SessionForBench();
  if (!sess) return;
  const std::array<int64_t, 4> ishape{batch, (int64_t)lczero::InputPlanesCount,
                                      (int64_t)lczero::BoardHeight, (int64_t)lczero::BoardWidth};
  const std::array<int64_t, 2> pshape{batch, (int64_t)lczero::PolicyOutputSize};
  const std::array<int64_t, 2> vshape{batch, (int64_t)lczero::ValueOutputSize};
  const size_t in_n = batch * lczero::InputBufferUnitSize;
  const size_t p_n = batch * lczero::PolicyOutputSize, v_n = batch * lczero::ValueOutputSize;
  std::vector<float> host_in(in_n), host_p(p_n), host_v(v_n);
  std::mt19937 rng(1);
  for (auto& x : host_in) x = (rng() & 1) ? 1.0f : 0.0f;

  Ort::MemoryInfo cpu_mi = Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault);
  Ort::MemoryInfo cuda_mi("Cuda", OrtDeviceAllocator, 0, OrtMemTypeDefault);
  Ort::MemoryInfo pin_mi("CudaPinned", OrtDeviceAllocator, 0, OrtMemTypeCPUOutput);
  std::unique_ptr<Ort::Allocator> cuda_alloc, pin_alloc;
  try { cuda_alloc = std::make_unique<Ort::Allocator>(*sess, cuda_mi); }
  catch (const std::exception& e) { std::cout << "  (khong co allocator Cuda: " << e.what() << ")\n"; return; }
  try { pin_alloc = std::make_unique<Ort::Allocator>(*sess, pin_mi); }
  catch (const std::exception& e) { std::cout << "  (khong co allocator CudaPinned: " << e.what() << ")\n"; return; }

  auto mk = [&](Ort::Allocator& a, const int64_t* shape, size_t rank) {
    return Ort::Value::CreateTensor<float>(a, shape, rank);
  };
  // Pinned input filled with the same data (content does not matter, but keep it equal).
  Ort::Value pin_in = mk(*pin_alloc, ishape.data(), 4);
  std::memcpy(pin_in.GetTensorMutableData<float>(), host_in.data(), in_n * sizeof(float));
  Ort::Value pin_p = mk(*pin_alloc, pshape.data(), 2), pin_v = mk(*pin_alloc, vshape.data(), 2);
  Ort::Value gpu_in = mk(*cuda_alloc, ishape.data(), 4);
  Ort::Value gpu_p = mk(*cuda_alloc, pshape.data(), 2), gpu_v = mk(*cuda_alloc, vshape.data(), 2);
  const char* in_names[] = {"input"};
  const char* out_names[] = {"policy", "value"};
  auto run_plain = [&]() {
    Ort::Value in = Ort::Value::CreateTensor<float>(cpu_mi, host_in.data(), in_n, ishape.data(), 4);
    Ort::Value outs[] = {
        Ort::Value::CreateTensor<float>(cpu_mi, host_p.data(), p_n, pshape.data(), 2),
        Ort::Value::CreateTensor<float>(cpu_mi, host_v.data(), v_n, vshape.data(), 2)};
    sess->Run(Ort::RunOptions{nullptr}, in_names, &in, 1, out_names, outs, 2);
  };
  auto make_bound = [&](Ort::Value& in, Ort::Value& p, Ort::Value& v) {
    auto io = std::make_unique<Ort::IoBinding>(*sess);
    io->BindInput("input", in);
    io->BindOutput("policy", p);
    io->BindOutput("value", v);
    return io;
  };
  auto io_b = make_bound(pin_in, pin_p, pin_v);
  auto io_c = make_bound(pin_in, gpu_p, gpu_v);
  auto io_d = make_bound(gpu_in, gpu_p, gpu_v);

  auto time_ms = [&](const std::function<void()>& f) {
    for (int i = 0; i < 20; ++i) f();  // warm-up
    double best = 1e30;                // best of 5 rounds of 200 (noise-robust)
    for (int r = 0; r < 5; ++r) {
      const auto t0 = std::chrono::steady_clock::now();
      for (int i = 0; i < 200; ++i) f();
      best = std::min(best, std::chrono::duration<double, std::milli>(
                                std::chrono::steady_clock::now() - t0).count() / 200);
    }
    return best;
  };
  const Ort::RunOptions ro{nullptr};
  const double a = time_ms(run_plain);
  const double b = time_ms([&] { sess->Run(ro, *io_b); });
  const double c = time_ms([&] { sess->Run(ro, *io_c); });
  const double d = time_ms([&] { sess->Run(ro, *io_d); });
  // Correctness of B vs A (same input bytes): outputs must match.
  run_plain();
  sess->Run(ro, *io_b);
  double diff = 0;
  const float* bp = pin_p.GetTensorData<float>();
  for (size_t i = 0; i < p_n; ++i) diff = std::max(diff, (double)std::fabs(bp[i] - host_p[i]));

  std::printf("\n--- Chi phi CHEP du lieu (E3/E4), batch %d, chi session->Run() ---\n", batch);
  std::printf("  vao %.2f MB, policy ra %.2f MB, value ra %zu B moi Run\n",
              in_n * 4 / 1e6, p_n * 4 / 1e6, v_n * 4);
  std::printf("  A pageable vao/ra (hien tai)  : %.3f ms\n", a);
  std::printf("  B pinned vao/ra   (E3)        : %.3f ms  (%+.1f%%)  max|B-A|=%.2g\n", b,
              100 * (b / a - 1), diff);
  std::printf("  C pinned vao, ra o GPU (tran E4): %.3f ms  (%+.1f%%)\n", c, 100 * (c / a - 1));
  std::printf("  D vao/ra deu o GPU (san)      : %.3f ms  (%+.1f%%)  = toan bo chep chiem %.1f%%\n",
              d, 100 * (d / a - 1), 100 * (a - d) / a);
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
      backend = MakeRawOnnx(o, b, /*cuda_graph=*/false, &bo);
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
      backend = MakeRawOnnx(o, prod, /*cuda_graph=*/false, &bo);
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
      if (o.sp_provider == "cuda")
        BenchCopyCost(static_cast<lczero::OnnxBackend*>(backend.get()), prod);
    }
  }

  // Max |var - ref| over q, d and every policy entry: 12 Runs of `batch` slots,
  // rotating 6 DIFFERENT positions (graph replay bugs only show on replays).
  auto max_output_diff = [&](lczero::Backend* ref, lczero::Backend* var, int batch) {
    std::vector<std::unique_ptr<lczero::PositionHistory>> hs;
    {
      auto h = std::make_unique<lczero::PositionHistory>(*history);
      std::mt19937 rng(20260924);
      for (int k = 0; k < 6; ++k) {
        hs.push_back(std::make_unique<lczero::PositionHistory>(*h));
        for (int j = 0; j < 5; ++j) {
          const lczero::MoveList lm = h->Last().GetBoard().GenerateLegalMoves();
          if (lm.empty()) break;
          h->Append(lm[rng() % lm.size()]);
        }
      }
    }
    std::vector<lczero::MoveList> legals;
    std::vector<lczero::EvalResult> refs;
    for (const auto& h : hs) {
      legals.push_back(h->Last().GetBoard().GenerateLegalMoves());
      const lczero::EvalPosition epk{h.get(), std::span<const lczero::Move>(
                                                  legals.back().data(), legals.back().size())};
      refs.push_back(RunOnce(ref, epk, legals.back().size()));
    }
    double max_diff = 0.0;
    for (int run = 0; run < 12; ++run) {
      const size_t k = static_cast<size_t>(run) % hs.size();
      const lczero::EvalPosition epk{hs[k].get(), std::span<const lczero::Move>(
                                                      legals[k].data(), legals[k].size())};
      std::vector<lczero::EvalResult> res(batch);
      auto comp = var->CreateComputation();
      for (auto& r : res) {
        r.p.resize(legals[k].size());
        comp->AddInput(epk, r.AsPtr());
      }
      comp->ComputeBlocking();
      for (const auto& r : res) {
        max_diff = std::max({max_diff, static_cast<double>(std::fabs(r.q - refs[k].q)),
                             static_cast<double>(std::fabs(r.d - refs[k].d))});
        for (size_t i = 0; i < legals[k].size(); ++i)
          max_diff = std::max(max_diff, static_cast<double>(std::fabs(r.p[i] - refs[k].p[i])));
      }
    }
    return max_diff;
  };

  // ---- A1: --cuda-opt vs ORT defaults, same batch profile ------------------
  // The two sessions are measured alternately (A B A B ...) so GPU clock drift
  // hits both equally; the median of 5 rounds each is reported.
  if (!o.sp_cuda_opts.empty()) {
    if (o.sp_provider != "cuda") {
      std::cout << "\n--cuda-opt chi ap dung cho --provider cuda; bo qua.\n";
    } else if (static_cast<size_t>(prod) <= lczero::MaxBatchSize) {
      std::cout << "\n--- A1: --cuda-opt so voi mac dinh ORT (fixed_batch=" << prod << ") ---\n";
      std::string bo_ref, bo_var;
      std::unique_ptr<lczero::Backend> ref, var;
      try { ref = MakeRawOnnx(o, prod, false, &bo_ref, /*with_cuda_opts=*/false); }
      catch (const std::exception& e) { std::cerr << "  khong dung duoc backend mac dinh: " << e.what() << "\n"; }
      try { var = MakeRawOnnx(o, prod, false, &bo_var, /*with_cuda_opts=*/true); }
      catch (const std::exception& e) { std::cerr << "  khong dung duoc backend --cuda-opt: " << e.what() << "\n"; }
      if (ref && var) {
        std::cout << "  mac dinh : " << bo_ref << "\n  thu      : " << bo_var << "\n";
        const double d = max_output_diff(ref.get(), var.get(), prod);
        std::printf("  dung : max|thu - mac dinh| = %.6f  %s\n", d,
                    d > 1e-3 ? "[FAIL] lech qua nguong 1e-3" : "[OK] trong sai so lam tron fp32");
        std::vector<double> a, b;
        for (int round = 0; round < 5; ++round) {
          a.push_back(measure(ref.get(), prod).ms_per_run);
          b.push_back(measure(var.get(), prod).ms_per_run);
        }
        std::sort(a.begin(), a.end());
        std::sort(b.begin(), b.end());
        std::printf("  toc do (trung vi 5 vong xen ke): mac dinh %.3f ms/Run (%.1f pos/giay)"
                    "  vs  thu %.3f ms/Run (%.1f pos/giay)  -> %+.1f%%\n",
                    a[2], prod / a[2] * 1000.0, b[2], prod / b[2] * 1000.0,
                    100.0 * (a[2] / b[2] - 1.0));
        std::printf("  (min-max: mac dinh %.3f-%.3f, thu %.3f-%.3f ms/Run)\n",
                    a[0], a[4], b[0], b[4]);
        std::printf("FZ_A1 %.4f %.4f %.6f\n", a[2], b[2], d);
      }
    }
  }

  // ---- EXPERIMENTAL: CUDA Graph capture (--cuda-graph) ----------------------
  // Chua kiem chung tren phan cung that (moi viet, khong co GPU local de chay).
  // Kiem CA toc do LAN tinh dung dan truoc khi dung cho selfplay/arena that --
  // mot loi thinh lang o day se lam hong du lieu huan luyen, khong chi la crash.
  if (o.sp_cuda_graph) {
    if (o.sp_provider != "cuda") {
      std::cout << "\n--cuda-graph chi ap dung cho --provider cuda; bo qua.\n";
    } else if (static_cast<size_t>(prod) <= lczero::MaxBatchSize) {
      std::cout << "\n--- EXPERIMENTAL: CUDA Graph capture (fixed_batch=" << prod << ") ---\n";
      std::string bo_ref, bo_graph;
      std::unique_ptr<lczero::Backend> ref, graph;
      try { ref = MakeRawOnnx(o, prod, /*cuda_graph=*/false, &bo_ref); }
      catch (const std::exception& e) { std::cerr << "  khong dung duoc backend doi chung: " << e.what() << "\n"; }
      try { graph = MakeRawOnnx(o, prod, /*cuda_graph=*/true, &bo_graph); }
      catch (const std::exception& e) { std::cerr << "  khong dung duoc backend cuda_graph: " << e.what() << "\n"; }

      if (ref && graph) {
        // 1) Dung. ORT chup (capture) graph o mot trong nhung lan Run() dau roi
        //    PHAT LAI (replay) no o moi lan sau; loi can bat -- replay doc lai bo dem
        //    cu thay vi input moi -- chi lo ra o cac lan phat lai (max_output_diff: 12
        //    lan Run, 6 the co khac nhau, so MOI o voi duong khong-graph).
        const double max_diff = max_output_diff(ref.get(), graph.get(), prod);
        std::printf("  dung : 12 lan Run x %d o, 6 the co khac nhau: max|graph - khong graph| = %.6f\n",
                    prod, max_diff);
        if (max_diff > 1e-3) {
          std::cout << "  [FAIL] cuda_graph LECH ket qua qua nguong -- KHONG dung cho selfplay/arena "
                        "cho den khi dieu tra ro nguyen nhan.\n";
        } else {
          std::cout << "  [OK] cuda_graph khop duong khong-graph o moi lan phat lai (trong sai so lam tron).\n";
        }

        // 2) Toc do: dung lai measure() cua vong quet chinh, cung batch=prod.
        const Sample s_ref = measure(ref.get(), prod);
        const Sample s_graph = measure(graph.get(), prod);
        std::printf("  toc do: khong-graph %.1f pos/giay (%.3f ms/Run)  vs  graph %.1f pos/giay (%.3f ms/Run)"
                    "  -> %+.1f%%\n",
                    s_ref.pos_per_sec, s_ref.ms_per_run, s_graph.pos_per_sec, s_graph.ms_per_run,
                    100.0 * (s_graph.pos_per_sec / s_ref.pos_per_sec - 1.0));
      }
    }
  }

  std::cout << "\nMOC SO SANH: self-play dat ~2900 NN eval/giay o fixed_batch=16.\n"
               "  neu cot pos/giay o batch lon CAO HON HAN -> batch lon la don bay\n"
               "  neu no phang -> GPU da bao hoa tinh toan, batch khong giup\n";
  return 0;
}
