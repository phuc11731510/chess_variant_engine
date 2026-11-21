// --test-fzcuda | --bench-fzcuda | --fzcuda-dump FILE : the CUDA network runner (src/lczero_chess/neural/fz/, --provider fzcuda).
//
//   --fzcuda-dump P     Writes the positions P (encoded planes + the policy index of every legal move; the input of
//                       `python/fzw.py ref`) and P.txt (how to rebuild each position: start FEN and moves). --games N positions
//                       (default 256), --start-fen BOOK (one FEN per line) for varied starts.
//   --test-fzcuda --weights net.fzw [--fz-positions P]
//                       1. the hand-written kernels against CPU references (random data); 2. with P and P.ref (made by
//                       `python/fzw.py ref net.pt P P.ref`): the whole network against the FP32 PyTorch outputs for batches of
//                       1, 7, 16, 24, 48 and 64, and the backend (encoder, softmax over the legal moves) against the same;
//                       determinism and four threads at once; 3. speed. Writes P.taps for `python/fzw.py taps`.
//   --bench-fzcuda --weights net.fzw
//                       Speed only: time per batch and per stage.
//
// Needs a GPU and a binary built with -Duse_fzcuda=true; without it every mode says so and exits 0 (a CPU-only machine is not a
// failure of the runner).

#include "tests/test_common.h"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstring>
#include <fstream>
#include <random>
#include <sstream>
#include <thread>

#include "app/cli.h"
#include "chess/encoder.h"
#include "neural/fz/plane_pack.h"
#include "neural/network_output.h"
#include "neural/shared_params.h"
#include "tests/engine_tests.h"
#ifdef USE_FZCUDA
#include "neural/fz/fz_net.h"
#include "neural/fz/fz_selftest.h"
#include "neural/fz/fzcuda_backend.h"
#endif

namespace {

int g_fail = 0;
#define FZ_EXPECT(cond, msg)                                                      \
  do {                                                                            \
    if (!(cond)) {                                                                \
      ++g_fail;                                                                   \
      std::cerr << "  [FAIL] " << msg << std::endl;                               \
    }                                                                             \
  } while (0)

// ---------------------------------------------------------------------------------------------------------------------
// Positions: random games from a few start positions (and a book), recorded as start FEN + moves so they can be rebuilt
// ---------------------------------------------------------------------------------------------------------------------

struct Pos {
  std::string fen;
  std::vector<std::string> moves;
};

std::vector<Pos> MakePositions(size_t count, const std::string& book_path) {
  std::vector<std::string> fens = {
      lczero::ChessBoard::kStartposFen,
      "1r3k2r1/2p4p2/10/4n5/10/10/5B4/10/2P4P2/1R3K2R1 w BIbi - 8+8 0 1",
      "4k5/3s1s4/10/2P1S1P3/10/10/10/10/10/4K5 b - - 8+8 0 1",
      "k9/10/10/3pP5/10/10/10/10/10/K9 w - d8 8+8 0 1",
  };
  if (!book_path.empty()) {
    std::ifstream in(book_path);
    for (std::string line; std::getline(in, line);)
      if (line.size() > 10) fens.push_back(line);
  }
  std::vector<Pos> out;
  std::mt19937_64 rng(0xFA17CDA);
  size_t f = 0;
  while (out.size() < count) {
    const std::string& fen = fens[f++ % fens.size()];
    lczero::PositionHistory h;
    h.Reset(lczero::Position::FromFen(fen));
    std::vector<std::string> moves;
    for (int ply = 0; ply < 90 && out.size() < count; ++ply) {
      const lczero::MoveList lm = h.Last().GetBoard().GenerateLegalMoves();
      if (lm.empty() || h.ComputeGameResult() != lczero::GameResult::UNDECIDED) break;
      if (ply % 4 == 0 || ply < 3) out.push_back({fen, moves});
      const lczero::Move m = lm[static_cast<size_t>(rng() % lm.size())];
      moves.push_back(h.Last().GetBoard().MoveToString(m));
      h.Append(m);
    }
  }
  return out;
}

std::unique_ptr<lczero::PositionHistory> Rebuild(const Pos& p) {
  auto h = std::make_unique<lczero::PositionHistory>();
  h->Reset(lczero::Position::FromFen(p.fen));
  for (const std::string& s : p.moves) h->Append(h->Last().GetBoard().ParseMove(s));
  return h;
}

// One record of the positions file: the planes as the GPU reads them (per plane {u64 lo, u64 hi, f32 value, 12 zero bytes}: the
// same 32 bytes on every platform, whatever the compiler's layout of InputPlane), then the number of legal moves and their
// policy indices.
constexpr size_t kPlanesBytes = lczero::fz::kPackedPlanesBytes;
constexpr size_t kRecordBytes = kPlanesBytes + 2 + 384 * 2;

void EncodeRecord(const lczero::PositionHistory& h, uint8_t* rec, std::vector<lczero::Move>* legal_out) {
  alignas(64) lczero::InputPlanes planes;
  int transform = 0;
  lczero::EncodePositionForNN(h, lczero::kMoveHistory, lczero::FillEmptyHistory::ALWAYS, &planes, &transform);
  lczero::fz::PackPlanes(planes, rec);
  const lczero::MoveList lm = h.Last().GetBoard().GenerateLegalMoves();
  const uint16_t n = static_cast<uint16_t>(std::min<size_t>(lm.size(), 384));
  std::memcpy(rec + kPlanesBytes, &n, 2);
  uint16_t idx[384] = {};
  for (size_t i = 0; i < n; ++i) {
    const uint16_t v = lczero::MoveToNNIndex(lm[i], 0);
    idx[i] = v < lczero::kPolicySize ? v : 0xFFFF;
    if (legal_out) legal_out->push_back(lm[i]);
  }
  std::memcpy(rec + kPlanesBytes + 2, idx, sizeof(idx));
}

// The packed planes (what goes to the GPU) must say exactly what UnpackInputPlanes (what the ONNX path feeds the network) says:
// the cell (rank r, file f) of plane p is set iff bit r * 12 + f of the plane's 128-bit mask is, in the low word below 64 and
// the high word from 64 -- the rule the GPU's ExpandInputKernel applies. Needs no GPU.
int CheckPacking() {
  const auto positions = MakePositions(300, "");
  std::vector<uint8_t> rec(kRecordBytes);
  std::vector<float> want(size_t{lczero::kInputPlanes} * 100);
  size_t bad = 0, cells_set = 0;
  for (const Pos& p : positions) {
    const auto h = Rebuild(p);
    EncodeRecord(*h, rec.data(), nullptr);
    alignas(64) lczero::InputPlanes planes;
    int transform = 0;
    lczero::EncodePositionForNN(*h, lczero::kMoveHistory, lczero::FillEmptyHistory::ALWAYS, &planes, &transform);
    lczero::UnpackInputPlanes(planes, want.data(), 10, 10);
    for (int pl = 0; pl < lczero::kInputPlanes; ++pl) {
      uint64_t lo, hi;
      float value;
      std::memcpy(&lo, rec.data() + size_t(pl) * 32, 8);
      std::memcpy(&hi, rec.data() + size_t(pl) * 32 + 8, 8);
      std::memcpy(&value, rec.data() + size_t(pl) * 32 + 16, 4);
      for (int r = 0; r < 10; ++r)
        for (int f = 0; f < 10; ++f) {
          const int sq = r * 12 + f;
          const bool set = sq < 64 ? (lo >> sq) & 1 : (hi >> (sq - 64)) & 1;
          const float got = set ? value : 0.0f;
          cells_set += set;
          if (got != want[size_t(pl) * 100 + r * 10 + f]) ++bad;
        }
    }
  }
  std::cout << "--- packed planes against UnpackInputPlanes: " << positions.size() << " positions, " << cells_set << " set cells, " << bad
            << " different ---" << std::endl;
  FZ_EXPECT(bad == 0, bad << " cells of the packed planes differ from what the ONNX path feeds the network");
  FZ_EXPECT(cells_set > 0, "no cell set at all: the test did not look at anything");
  return bad == 0 ? 0 : 1;
}

int RunDump(const EngineOptions& o) {
  const size_t count = o.games_given ? static_cast<size_t>(o.sp_games) : 256;
  const auto positions = MakePositions(count, o.sp_start_fen);
  std::ofstream bin(o.fz_dump, std::ios::binary), txt(o.fz_dump + ".txt");
  if (!bin || !txt) {
    std::cerr << "cannot write " << o.fz_dump << std::endl;
    return 1;
  }
  std::vector<uint8_t> rec(kRecordBytes);
  for (const Pos& p : positions) {
    EncodeRecord(*Rebuild(p), rec.data(), nullptr);
    bin.write(reinterpret_cast<const char*>(rec.data()), static_cast<std::streamsize>(rec.size()));
    txt << p.fen << " |";
    for (const std::string& m : p.moves) txt << ' ' << m;
    txt << '\n';
  }
  std::cout << "[fzcuda] " << positions.size() << " positions -> " << o.fz_dump << " (" << kRecordBytes << " bytes each) and "
            << o.fz_dump << ".txt" << std::endl;
  return 0;
}

#ifdef USE_FZCUDA

using Clock = std::chrono::steady_clock;
double MsSince(Clock::time_point t) { return std::chrono::duration<double, std::milli>(Clock::now() - t).count(); }

struct Reference {
  int n = 0;
  std::vector<float> policy, wdl, mlh;  // [n][11500], [n][3], [n]
  bool Load(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    uint32_t head[2] = {0, 0};
    if (!in.read(reinterpret_cast<char*>(head), 8)) return false;
    n = static_cast<int>(head[0]);
    policy.resize(size_t(n) * lczero::kPolicySize);
    wdl.resize(size_t(n) * 3);
    mlh.resize(n);
    in.read(reinterpret_cast<char*>(policy.data()), static_cast<std::streamsize>(policy.size() * 4));
    in.read(reinterpret_cast<char*>(wdl.data()), static_cast<std::streamsize>(wdl.size() * 4));
    in.read(reinterpret_cast<char*>(mlh.data()), static_cast<std::streamsize>(mlh.size() * 4));
    return static_cast<bool>(in);
  }
};

// Total variation distance of softmax(a) and softmax(b) (two logit lists of the same legal moves).
double TotalVariation(const std::vector<double>& a, const std::vector<double>& b) {
  auto sm = [](const std::vector<double>& l) {
    double m = -1e300;
    for (double x : l) m = std::max(m, x);
    std::vector<double> p(l.size());
    double s = 0;
    for (size_t i = 0; i < l.size(); ++i) s += (p[i] = std::exp(l[i] - m));
    for (double& x : p) x /= s;
    return p;
  };
  const auto pa = sm(a), pb = sm(b);
  double tv = 0;
  for (size_t i = 0; i < a.size(); ++i) tv += std::fabs(pa[i] - pb[i]);
  return 0.5 * tv;
}

constexpr double kTvLimit = 0.01, kWdlLimit = 0.01, kMlhLimit = 1.0;  // python/train.py FP16_TOLERANCE

struct Worst {
  double tv = 0, wdl = 0, mlh = 0, logit = 0;
  void Add(const Worst& w) {
    tv = std::max(tv, w.tv);
    wdl = std::max(wdl, w.wdl);
    mlh = std::max(mlh, w.mlh);
    logit = std::max(logit, w.logit);
  }
};

bool ReadPositions(const std::string& path, std::vector<uint8_t>* raw) {
  std::ifstream in(path, std::ios::binary | std::ios::ate);
  if (!in) return false;
  raw->resize(static_cast<size_t>(in.tellg()));
  in.seekg(0);
  in.read(reinterpret_cast<char*>(raw->data()), static_cast<std::streamsize>(raw->size()));
  return static_cast<bool>(in);
}

void LoadStage(lczero::fz::Stage* st, const std::vector<uint8_t>& raw, int n, int first) {
  const int total = static_cast<int>(raw.size() / kRecordBytes);
  for (int b = 0; b < n; ++b) {
    const uint8_t* rec = raw.data() + size_t((first + b) % total) * kRecordBytes;
    std::memcpy(static_cast<uint8_t*>(st->planes) + size_t(b) * kPlanesBytes, rec, kPlanesBytes);
    std::memcpy(&st->move_count[b], rec + kPlanesBytes, 2);
    std::memcpy(st->move_index + size_t(b) * 384, rec + kPlanesBytes + 2, 384 * 2);
  }
}

// Compares the runner's outputs for the positions loaded with LoadStage(first) against the reference.
Worst CompareStage(const lczero::fz::Stage* st, const Reference& ref, const std::vector<uint8_t>& raw, int n, int first) {
  Worst w;
  const int total = static_cast<int>(raw.size() / kRecordBytes);
  for (int b = 0; b < n; ++b) {
    const int pos = (first + b) % total;
    const uint8_t* rec = raw.data() + size_t(pos) * kRecordBytes;
    uint16_t cnt;
    std::memcpy(&cnt, rec + kPlanesBytes, 2);
    const uint16_t* idx = reinterpret_cast<const uint16_t*>(rec + kPlanesBytes + 2);
    std::vector<double> got, want;
    for (int i = 0; i < cnt; ++i) {
      if (idx[i] == 0xFFFF) continue;
      got.push_back(st->logits[size_t(b) * 384 + i]);
      want.push_back(ref.policy[size_t(pos) * lczero::kPolicySize + idx[i]]);
      w.logit = std::max(w.logit, std::fabs(got.back() - want.back()));
    }
    if (!got.empty()) w.tv = std::max(w.tv, TotalVariation(got, want));
    for (int k = 0; k < 3; ++k) w.wdl = std::max(w.wdl, double(std::fabs(st->wdlm[b * 4 + k] - ref.wdl[size_t(pos) * 3 + k])));
    w.mlh = std::max(w.mlh, double(std::fabs(st->wdlm[b * 4 + 3] - ref.mlh[pos])));
  }
  return w;
}

void CheckWorst(const std::string& what, const Worst& w) {
  std::cout << "  " << what << ": TV policy " << w.tv << ", |WDL| " << w.wdl << ", |mlh| " << w.mlh << " plies, |logit| " << w.logit
            << std::endl;
  FZ_EXPECT(w.tv <= kTvLimit && w.wdl <= kWdlLimit && w.mlh <= kMlhLimit,
            what << ": farther from the FP32 network than the FP16 limits (" << kTvLimit << ", " << kWdlLimit << ", " << kMlhLimit << ")");
}

void WriteTaps(const std::string& path, const std::vector<lczero::fz::Tap>& taps) {
  std::ofstream out(path, std::ios::binary);
  for (const auto& t : taps) {
    char name[16] = {};
    std::strncpy(name, t.name.c_str(), 15);
    const uint32_t rc[2] = {static_cast<uint32_t>(t.rows), static_cast<uint32_t>(t.cols)};
    out.write(name, 16);
    out.write(reinterpret_cast<const char*>(rc), 8);
    out.write(reinterpret_cast<const char*>(t.values.data()), static_cast<std::streamsize>(t.values.size() * 4));
  }
  std::cout << "  activations of the first position -> " << path << " (python/fzw.py taps compares them)" << std::endl;
}

void TimeBatches(lczero::fz::Net* net, const std::vector<uint8_t>* raw) {
  std::cout << "--- speed (Run: copy in, network, copy out, blocking; one thread) ---" << std::endl;
  lczero::fz::Stage* st = net->AcquireStage();
  if (raw && !raw->empty()) {
    LoadStage(st, *raw, lczero::fz::kMaxBatch, 0);
  } else {
    std::memset(st->planes, 0, size_t(lczero::fz::kMaxBatch) * kPlanesBytes);
    std::memset(st->move_count, 0, lczero::fz::kMaxBatch * 2);
  }
  for (int batch : {64, 48, 32, 16, 8, 1}) {
    for (int i = 0; i < 5; ++i) net->Run(st, batch);
    const int reps = 100;
    const auto t = Clock::now();
    for (int i = 0; i < reps; ++i) net->Run(st, batch);
    const double ms = MsSince(t) / reps;
    std::cout << "  batch " << batch << ": " << ms << " ms per batch, " << ms * 1000.0 / batch << " us per position, "
              << 1000.0 * batch / ms << " positions/s" << std::endl;
  }
  net->ReleaseStage(st);
  std::cout << "--- time per stage on the GPU, batch 64 (CUDA events) ---" << std::endl;
  std::vector<lczero::fz::StageTime> times = net->Profile(64, 20);
  for (const auto& t : times) std::cout << "  " << t.name << ": " << t.ms << " ms" << std::endl;
}

void BackendCheck(const lczero::OptionsDict& opts, const std::vector<Pos>& poses, const Reference& ref, int count, float temp) {
  lczero::FzCudaBackend backend;
  backend.UpdateConfiguration(opts);
  const int n = std::min<int>(count, ref.n);
  std::vector<std::unique_ptr<lczero::PositionHistory>> hist;
  std::vector<lczero::MoveList> legal;
  std::vector<lczero::EvalResult> res(n);
  auto comp = backend.CreateComputation();
  for (int i = 0; i < n; ++i) {
    hist.push_back(Rebuild(poses[i]));
    legal.push_back(hist.back()->Last().GetBoard().GenerateLegalMoves());
    res[i].p.resize(legal.back().size());
    comp->AddInput(lczero::EvalPosition{hist.back().get(), std::span<const lczero::Move>(legal.back().data(), legal.back().size())},
                   res[i].AsPtr());
  }
  comp->ComputeBlocking();
  double worst_p = 0, worst_q = 0, worst_d = 0, worst_m = 0;
  for (int i = 0; i < n; ++i) {
    // The reference's priors: an exact softmax (at `temp`) of the FP32 network's logits of the legal moves.
    std::vector<double> l;
    for (const auto& m : legal[i]) l.push_back(ref.policy[size_t(i) * lczero::kPolicySize + lczero::MoveToNNIndex(m, 0)] / temp);
    double mx = -1e300, s = 0;
    for (double x : l) mx = std::max(mx, x);
    for (double& x : l) s += (x = std::exp(x - mx));
    double tv = 0;
    for (size_t k = 0; k < l.size(); ++k) tv += std::fabs(l[k] / s - res[i].p[k]);
    worst_p = std::max(worst_p, 0.5 * tv);
    const double w = ref.wdl[size_t(i) * 3], dr = ref.wdl[size_t(i) * 3 + 1], lo = ref.wdl[size_t(i) * 3 + 2];
    worst_q = std::max(worst_q, std::fabs(double(res[i].q) - (w - lo)));
    worst_d = std::max(worst_d, std::fabs(double(res[i].d) - dr));
    worst_m = std::max(worst_m, std::fabs(double(res[i].m) - std::max(ref.mlh[i], 0.0f)));
  }
  std::cout << "  backend, " << n << " positions, policy temperature " << temp << ": TV priors " << worst_p << ", |q| " << worst_q
            << ", |d| " << worst_d << ", |m| " << worst_m << " plies" << std::endl;
  FZ_EXPECT(worst_p <= kTvLimit && worst_q <= 2 * kWdlLimit && worst_d <= kWdlLimit && worst_m <= kMlhLimit,
            "the backend's results are farther from the FP32 network than the FP16 limits");
}

#endif  // USE_FZCUDA

}  // namespace

int run_fzcuda(const EngineOptions& o) {
  setup_custom_variant();  // the rules of the game (the encoder and the move generator need them)
  if (o.fzcuda_dump_mode) return RunDump(o);
  if (o.test_fzcuda_mode) CheckPacking();
#ifndef USE_FZCUDA
  std::cout << "[SKIP] the GPU part of --test-fzcuda / --bench-fzcuda: this binary was built without the CUDA runner (meson -Duse_fzcuda=true)"
            << std::endl;
  if (g_fail) std::cerr << "[FAIL] --test-fzcuda: " << g_fail << " check(s) failed" << std::endl;
  return g_fail ? 1 : 0;
#else
  try {
    if (!o.weights_given) {
      std::cerr << "--test-fzcuda / --bench-fzcuda need --weights <net.fzw> (python/fzw.py convert gen<N>.pt gen<N>.fzw)" << std::endl;
      return 2;
    }
    if (o.test_fzcuda_mode) {
      g_fail += lczero::fz::RunKernelSelfTests();
    }
    lczero::OptionsParser parser;
    auto* d = parser.GetMutableDefaultsOptions();
    d->Set<std::string>(lczero::SharedBackendParams::kWeightsId, o.weights_file);
    d->Set<std::string>(lczero::SharedBackendParams::kBackendOptionsId, "provider=fzcuda,fixed_batch=64,contexts=2");
    d->Set<float>(lczero::SharedBackendParams::kPolicySoftmaxTemp, 1.0f);
    lczero::FzCudaBackend backend;
    backend.UpdateConfiguration(parser.GetOptionsDict());
    lczero::fz::Net* net = backend.net();

    std::vector<uint8_t> raw;
    Reference ref;
    std::vector<Pos> poses;
    const bool have_positions = !o.fz_positions.empty() && ReadPositions(o.fz_positions, &raw) && raw.size() % kRecordBytes == 0;
    if (!o.fz_positions.empty() && !have_positions) FZ_EXPECT(false, "cannot read the positions file " << o.fz_positions);
    if (o.test_fzcuda_mode && have_positions) {
      const int n = static_cast<int>(raw.size() / kRecordBytes);
      {
        std::ifstream txt(o.fz_positions + ".txt");
        for (std::string line; std::getline(txt, line);) {
          const auto bar = line.find(" |");
          Pos p;
          p.fen = line.substr(0, bar);
          std::istringstream ms(line.substr(bar + 2));
          for (std::string m; ms >> m;) p.moves.push_back(m);
          poses.push_back(std::move(p));
        }
      }
      FZ_EXPECT(static_cast<int>(poses.size()) == n, o.fz_positions << ".txt has " << poses.size() << " positions, the file " << n);
      // The text must rebuild exactly the planes that were dumped (the encoder or the move parser changed otherwise).
      int mismatched = 0;
      std::vector<uint8_t> rec(kRecordBytes);
      for (int i = 0; i < n && i < static_cast<int>(poses.size()); ++i) {
        EncodeRecord(*Rebuild(poses[i]), rec.data(), nullptr);
        if (std::memcmp(rec.data(), raw.data() + size_t(i) * kRecordBytes, kRecordBytes) != 0) ++mismatched;
      }
      FZ_EXPECT(mismatched == 0, mismatched << " of " << n << " positions rebuilt from " << o.fz_positions << ".txt differ from the dump");

      const bool have_ref = ref.Load(o.fz_positions + ".ref");
      if (!have_ref) {
        std::cout << "[SKIP] no " << o.fz_positions << ".ref (python/fzw.py ref net.pt " << o.fz_positions << " " << o.fz_positions
                  << ".ref): the comparison with the FP32 network is skipped" << std::endl;
      } else {
        FZ_EXPECT(ref.n == n, "the reference has " << ref.n << " positions, the dump " << n);
        std::cout << "--- the network against the FP32 PyTorch reference (" << n << " positions) ---" << std::endl;
        lczero::fz::Stage* st = net->AcquireStage();
        Worst all;
        int first = 0;
        for (int batch : {1, 7, 16, 24, 48, 64}) {
          LoadStage(st, raw, batch, first);
          net->Run(st, batch);
          const Worst w = CompareStage(st, ref, raw, batch, first);
          CheckWorst("batch " + std::to_string(batch), w);
          all.Add(w);
          first += batch;
        }
        // Every position, in batches of 64.
        Worst every;
        for (int b0 = 0; b0 < n; b0 += 64) {
          const int batch = std::min(64, n - b0);
          LoadStage(st, raw, batch, b0);
          net->Run(st, batch);
          every.Add(CompareStage(st, ref, raw, batch, b0));
        }
        CheckWorst("all " + std::to_string(n) + " positions", every);

        std::cout << "--- determinism and concurrency ---" << std::endl;
        LoadStage(st, raw, 64, 0);
        net->Run(st, 64);
        const std::vector<float> base_logits(st->logits, st->logits + 64 * 384), base_wdlm(st->wdlm, st->wdlm + 64 * 4);
        net->Run(st, 64);
        // Stale entries past a position's legal moves are not written by the GPU: compare only the legal ones.
        auto same = [&](const lczero::fz::Stage* s) {
          for (int b = 0; b < 64; ++b) {
            for (int i = 0; i < s->move_count[b]; ++i)
              if (s->logits[b * 384 + i] != base_logits[b * 384 + i]) return false;
            for (int k = 0; k < 4; ++k)
              if (s->wdlm[b * 4 + k] != base_wdlm[b * 4 + k]) return false;
          }
          return true;
        };
        FZ_EXPECT(same(st), "two runs of the same batch gave different numbers");
        std::atomic<int> differ{0};
        std::vector<std::thread> threads;
        for (int t = 0; t < 4; ++t)
          threads.emplace_back([&] {
            lczero::fz::Stage* s = net->AcquireStage();
            LoadStage(s, raw, 64, 0);
            for (int i = 0; i < 20; ++i) {
              net->Run(s, 64);
              if (!same(s)) ++differ;
            }
            net->ReleaseStage(s);
          });
        for (auto& t : threads) t.join();
        FZ_EXPECT(differ == 0, differ << " of 80 runs from 4 threads differed from the single-thread result");
        std::cout << "  repeatable, and 80 runs from 4 threads equal the single-thread run: " << (differ == 0 ? "ok" : "NO") << std::endl;

        std::cout << "--- the backend (encoder, legal-move softmax) against the same reference ---" << std::endl;
        BackendCheck(parser.GetOptionsDict(), poses, ref, 64, 1.0f);
        {
          lczero::OptionsParser p2;
          auto* d2 = p2.GetMutableDefaultsOptions();
          d2->Set<std::string>(lczero::SharedBackendParams::kWeightsId, o.weights_file);
          d2->Set<std::string>(lczero::SharedBackendParams::kBackendOptionsId, "provider=fzcuda,fixed_batch=37,contexts=1,autotune=0");
          d2->Set<float>(lczero::SharedBackendParams::kPolicySoftmaxTemp, 0.25f);
          BackendCheck(p2.GetOptionsDict(), poses, ref, 37, 0.25f);
        }
        net->ReleaseStage(st);
      }
      lczero::fz::Stage* st = net->AcquireStage();
      LoadStage(st, raw, 16, 0);
      WriteTaps(o.fz_positions + ".taps", net->Taps(st, 16));
      net->ReleaseStage(st);
    }
    TimeBatches(net, have_positions ? &raw : nullptr);
  } catch (const std::exception& e) {
    std::cerr << "[FAIL] fzcuda: " << e.what() << std::endl;
    return 1;
  }
  if (g_fail) {
    std::cerr << "[FAIL] --test-fzcuda: " << g_fail << " check(s) failed" << std::endl;
    return 1;
  }
  if (o.test_fzcuda_mode) std::cout << "[PASS] --test-fzcuda" << std::endl;
  return 0;
#endif
}
