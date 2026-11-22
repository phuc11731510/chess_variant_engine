#include "neural/fz/fz_selftest.h"

#include <cuda_fp16.h>
#include <cuda_runtime.h>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <iostream>
#include <random>
#include <vector>

#include "neural/fz/fz_kernels.cuh"
#include "utils/exception.h"

namespace lczero::fz {

namespace {

#define ST_CUDA(call)                                                                                  \
  do {                                                                                                 \
    const cudaError_t st_e = (call);                                                                   \
    if (st_e != cudaSuccess) throw Exception(std::string("fzcuda selftest: ") + #call + ": " + cudaGetErrorString(st_e)); \
  } while (0)

template <typename T>
struct Dev {
  T* p = nullptr;
  size_t n = 0;
  explicit Dev(size_t count) : n(count) { ST_CUDA(cudaMalloc(&p, n * sizeof(T))); }
  explicit Dev(const std::vector<T>& v) : Dev(v.size()) { ST_CUDA(cudaMemcpy(p, v.data(), n * sizeof(T), cudaMemcpyHostToDevice)); }
  ~Dev() { cudaFree(p); }
  Dev(const Dev&) = delete;
  std::vector<T> Get() const {
    std::vector<T> v(n);
    ST_CUDA(cudaMemcpy(v.data(), p, n * sizeof(T), cudaMemcpyDeviceToHost));
    return v;
  }
};

int g_failures = 0;
void Report(const char* name, bool ok, const std::string& detail) {
  std::cout << (ok ? "  [PASS] " : "  [FAIL] ") << name << ": " << detail << std::endl;
  if (!ok) ++g_failures;
}

float H(float x) { return __half2float(__float2half_rn(x)); }

std::vector<__half> HalfVec(const std::vector<float>& v) {
  std::vector<__half> out(v.size());
  for (size_t i = 0; i < v.size(); ++i) out[i] = __float2half_rn(v[i]);
  return out;
}

std::vector<float> RandomVec(std::mt19937& rng, size_t n, float scale, bool round_half) {
  std::normal_distribution<float> dist(0.0f, scale);
  std::vector<float> v(n);
  for (auto& x : v) x = round_half ? H(dist(rng)) : dist(rng);
  return v;
}

// ---------------------------------------------------------------------------------------------------------------------

void TestExpandInput() {
  std::mt19937 rng(1);
  const int B = 3;
  std::vector<PlaneGpu> planes(B * kPlanes);
  for (auto& p : planes) {
    p.lo = (uint64_t{rng()} << 32) | rng();
    p.hi = ((uint64_t{rng()} << 32) | rng()) & 0x00FFFFFFFFFFFFFFull;  // 120 square bits
    p.value = (rng() % 4 == 0) ? 0.37f : 1.0f;
    p.pad[0] = p.pad[1] = p.pad[2] = 0;
  }
  planes[5].lo = planes[5].hi = ~uint64_t{0};  // "all squares" (the scalar planes): padding columns set too
  Dev<PlaneGpu> d_planes(planes);
  Dev<__half> d_x0(size_t{B} * kTokens * kPlanesPadded);
  LaunchExpandInput(d_planes.p, d_x0.p, B, nullptr);
  ST_CUDA(cudaDeviceSynchronize());
  const auto x0 = d_x0.Get();
  size_t bad = 0;
  for (int b = 0; b < B; ++b)
    for (int t = 0; t < kTokens; ++t)
      for (int p = 0; p < kPlanesPadded; ++p) {
        float want = 0.0f;
        if (p < kPlanes) {
          const PlaneGpu& pl = planes[b * kPlanes + p];
          const int sq = (t / 10) * 12 + t % 10;
          const bool set = sq < 64 ? (pl.lo >> sq) & 1 : (pl.hi >> (sq - 64)) & 1;
          want = set ? pl.value : 0.0f;
        }
        if (__half2float(x0[(size_t(b) * kTokens + t) * kPlanesPadded + p]) != H(want)) ++bad;
      }
  Report("expand input", bad == 0, std::to_string(bad) + " wrong values of " + std::to_string(B * kTokens * kPlanesPadded));
}

// ---------------------------------------------------------------------------------------------------------------------

void TestAddLayerNorm(int d, bool with_y, int bias_rows) {
  std::mt19937 rng(2);
  const int rows = 300;
  const auto x = RandomVec(rng, size_t(rows) * d, 3.0f, true), y = RandomVec(rng, size_t(rows) * d, 2.0f, true);
  const auto bias = RandomVec(rng, size_t(bias_rows) * d, 1.0f, false);
  auto gamma = RandomVec(rng, d, 0.3f, false), beta = RandomVec(rng, d, 0.3f, false);
  for (auto& g : gamma) g += 1.0f;
  Dev<__half> d_x(HalfVec(x)), d_y(HalfVec(y)), d_xo(size_t(rows) * d), d_ln(size_t(rows) * d);
  Dev<float> d_b(bias), d_g(gamma), d_be(beta);
  LaunchAddLayerNorm(d_x.p, with_y ? d_y.p : nullptr, d_b.p, bias_rows, d_g.p, d_be.p, d_xo.p, d_ln.p, rows, d, nullptr);
  ST_CUDA(cudaDeviceSynchronize());
  const auto xo = d_xo.Get(), ln = d_ln.Get();
  double worst_x = 0, worst_ln = 0;
  for (int r = 0; r < rows; ++r) {
    std::vector<double> s(d);
    double mean = 0, var = 0;
    for (int c = 0; c < d; ++c) {
      s[c] = double(x[size_t(r) * d + c]) + (with_y ? y[size_t(r) * d + c] : 0.0) + bias[size_t(r % bias_rows) * d + c];
      mean += s[c];
    }
    mean /= d;
    for (int c = 0; c < d; ++c) var += (s[c] - mean) * (s[c] - mean);
    var /= d;
    for (int c = 0; c < d; ++c) {
      const double want_ln = (s[c] - mean) / std::sqrt(var + 1e-5) * gamma[c] + beta[c];
      worst_x = std::max(worst_x, std::fabs(double(__half2float(xo[size_t(r) * d + c])) - s[c]) / std::max(1.0, std::fabs(s[c])));
      worst_ln = std::max(worst_ln, std::fabs(double(__half2float(ln[size_t(r) * d + c])) - want_ln) / std::max(1.0, std::fabs(want_ln)));
    }
  }
  char buf[160];
  std::snprintf(buf, sizeof(buf), "d=%d y=%d bias_rows=%d: relative error x %.2e, layernorm %.2e (FP16 rounding is 4.9e-4)", d,
                with_y, bias_rows, worst_x, worst_ln);
  Report("add + layernorm", worst_x < 1.5e-3 && worst_ln < 2e-3, buf);
}

void TestLayerNorm(int d) {
  std::mt19937 rng(7);
  const int rows = 300;
  const auto x = RandomVec(rng, size_t(rows) * d, 3.0f, true);
  auto gamma = RandomVec(rng, d, 0.3f, false), beta = RandomVec(rng, d, 0.3f, false);
  for (auto& g : gamma) g += 1.0f;
  Dev<__half> d_x(HalfVec(x)), d_ln(size_t(rows) * d);
  Dev<float> d_g(gamma), d_be(beta);
  LaunchLayerNorm(d_x.p, d_g.p, d_be.p, d_ln.p, rows, d, nullptr);
  ST_CUDA(cudaDeviceSynchronize());
  const auto ln = d_ln.Get();
  double worst = 0;
  for (int r = 0; r < rows; ++r) {
    double mean = 0, var = 0;
    for (int c = 0; c < d; ++c) mean += x[size_t(r) * d + c];
    mean /= d;
    for (int c = 0; c < d; ++c) var += (x[size_t(r) * d + c] - mean) * (x[size_t(r) * d + c] - mean);
    var /= d;
    for (int c = 0; c < d; ++c) {
      const double want = (x[size_t(r) * d + c] - mean) / std::sqrt(var + 1e-5) * gamma[c] + beta[c];
      worst = std::max(worst, std::fabs(double(__half2float(ln[size_t(r) * d + c])) - want) / std::max(1.0, std::fabs(want)));
    }
  }
  char buf[120];
  std::snprintf(buf, sizeof(buf), "d=%d: relative error %.2e (FP16 rounding is 4.9e-4)", d, worst);
  Report("layernorm", worst < 2e-3, buf);
}

void TestGelu() {
  std::mt19937 rng(8);
  const size_t n = 100000;
  const auto x = RandomVec(rng, n, 2.0f, true);
  Dev<__half> d_x(HalfVec(x));
  LaunchGelu(d_x.p, n, nullptr);
  ST_CUDA(cudaDeviceSynchronize());
  const auto y = d_x.Get();
  double worst = 0;
  for (size_t i = 0; i < n; ++i) {
    const double v = x[i], want = 0.5 * v * (1.0 + std::tanh(0.7978845608028654 * (v + 0.044715 * v * v * v)));
    worst = std::max(worst, std::fabs(double(__half2float(y[i])) - want) / std::max(0.1, std::fabs(want)));
  }
  char buf[100];
  std::snprintf(buf, sizeof(buf), "relative error %.2e against the tanh form (FP16 rounding is 4.9e-4)", worst);
  Report("gelu", worst < 2e-3, buf);
}

// ---------------------------------------------------------------------------------------------------------------------

void TestAttention(int batch, int heads) {
  std::mt19937 rng(3);
  const int d = heads * kHeadDim, ld = 3 * d;
  auto qkv = RandomVec(rng, size_t(batch) * kTokens * ld, 1.0f, true);
  const auto rel = RandomVec(rng, size_t(heads) * kRelEntries, 1.0f, false);
  Dev<__half> d_qkv(HalfVec(qkv)), d_out(size_t(batch) * kTokens * d);
  Dev<float> d_rel(rel);
  LaunchAttention(d_qkv.p, d_rel.p, d_out.p, batch, heads, nullptr);
  ST_CUDA(cudaDeviceSynchronize());
  const auto out = d_out.Get();
  double worst = 0;
  for (int b = 0; b < batch; ++b)
    for (int h = 0; h < heads; ++h)
      for (int i = 0; i < kTokens; ++i) {
        const float* q = &qkv[(size_t(b) * kTokens + i) * ld + h * kHeadDim];
        std::vector<double> score(kTokens);
        double m = -1e300;
        for (int j = 0; j < kTokens; ++j) {
          const float* k = &qkv[(size_t(b) * kTokens + j) * ld + d + h * kHeadDim];
          double s = 0;
          for (int c = 0; c < kHeadDim; ++c) s += double(q[c]) * k[c];
          const int ri = i / 10, fi = i % 10, rj = j / 10, fj = j % 10;
          score[j] = s / std::sqrt(double(kHeadDim)) + rel[size_t(h) * kRelEntries + (rj - ri + 9) * 19 + (fj - fi + 9)];
          m = std::max(m, score[j]);
        }
        double sum = 0;
        for (int j = 0; j < kTokens; ++j) sum += (score[j] = std::exp(score[j] - m));
        for (int c = 0; c < kHeadDim; ++c) {
          double o = 0;
          for (int j = 0; j < kTokens; ++j) o += score[j] / sum * qkv[(size_t(b) * kTokens + j) * ld + 2 * d + h * kHeadDim + c];
          const double got = __half2float(out[(size_t(b) * kTokens + i) * d + h * kHeadDim + c]);
          worst = std::max(worst, std::fabs(got - o));
        }
      }
  char buf[120];
  std::snprintf(buf, sizeof(buf), "batch %d, %d heads: max |error| %.2e (FP16 probabilities and output: expect ~1e-3)", batch, heads, worst);
  Report("attention", worst < 6e-3, buf);
}

// ---------------------------------------------------------------------------------------------------------------------

void TestHeads() {
  std::mt19937 rng(4);
  const int B = 5, cols = 160;
  const auto head = RandomVec(rng, size_t(B) * kTokens * cols, 2.0f, false);
  std::vector<uint16_t> idx(size_t(B) * kMaxLegal, 0), cnt(B);
  for (int b = 0; b < B; ++b) {
    cnt[b] = static_cast<uint16_t>(20 + 60 * b);
    for (int i = 0; i < cnt[b]; ++i) idx[size_t(b) * kMaxLegal + i] = static_cast<uint16_t>(rng() % kPolicyEntries);
  }
  idx[7] = 0xFFFF;  // a move with no policy slot
  Dev<float> d_head(head), d_logits(size_t(B) * kMaxLegal);
  Dev<uint16_t> d_idx(idx), d_cnt(cnt);
  LaunchGatherPolicy(d_head.p, d_idx.p, d_cnt.p, d_logits.p, B, cols, nullptr);
  Dev<__half> d_vtok(size_t(B) * kTokens * kValueTokens), d_mtok(size_t(B) * kTokens * kMlhTokens);
  LaunchHeadTokens(d_head.p, d_vtok.p, d_mtok.p, B, cols, nullptr);
  ST_CUDA(cudaDeviceSynchronize());
  const auto logits = d_logits.Get();
  size_t bad = 0;
  for (int b = 0; b < B; ++b)
    for (int i = 0; i < cnt[b]; ++i) {
      const int ix = idx[size_t(b) * kMaxLegal + i];
      const float want = ix < kPolicyEntries ? head[(size_t(b) * kTokens + ix % kTokens) * cols + ix / kTokens] : -INFINITY;
      if (logits[size_t(b) * kMaxLegal + i] != want) ++bad;
    }
  Report("policy gather", bad == 0, std::to_string(bad) + " wrong logits");

  const auto vtok = d_vtok.Get(), mtok = d_mtok.Get();
  double worst = 0;
  auto gelu = [](double x) { return 0.5 * x * (1.0 + std::erf(x / std::sqrt(2.0))); };
  for (int row = 0; row < B * kTokens; ++row) {
    for (int f = 0; f < kValueTokens; ++f)
      worst = std::max(worst, std::fabs(double(__half2float(vtok[size_t(row) * kValueTokens + f])) - gelu(head[size_t(row) * cols + kMoveTypes + f])));
    for (int f = 0; f < kMlhTokens; ++f)
      worst = std::max(worst, std::fabs(double(__half2float(mtok[size_t(row) * kMlhTokens + f])) - gelu(head[size_t(row) * cols + kMoveTypes + kValueTokens + f])));
  }
  char buf[100];
  std::snprintf(buf, sizeof(buf), "max |error| %.2e (FP16 rounding of values up to ~8: expect < 5e-3)", worst);
  Report("head tokens (GELU)", worst < 5e-3, buf);

  // final heads: GELU, dot products, softmax
  const auto w_v2 = RandomVec(rng, 3 * kHidden, 0.2f, false), b_v2 = RandomVec(rng, 3, 0.5f, false);
  const auto w_m2 = RandomVec(rng, kHidden, 0.2f, false), b_m2 = RandomVec(rng, 1, 5.0f, false);
  const auto v1 = RandomVec(rng, size_t(B) * kHidden, 1.5f, false), m1 = RandomVec(rng, size_t(B) * kHidden, 1.5f, false);
  Dev<float> d_v1(v1), d_m1(m1), d_wv(w_v2), d_bv(b_v2), d_wm(w_m2), d_bm(b_m2), d_wdlm(size_t(B) * 4);
  LaunchFinalHeads(d_v1.p, d_m1.p, d_wv.p, d_bv.p, d_wm.p, d_bm.p, d_wdlm.p, B, nullptr);
  ST_CUDA(cudaDeviceSynchronize());
  const auto wdlm = d_wdlm.Get();
  worst = 0;
  for (int b = 0; b < B; ++b) {
    double z[3] = {b_v2[0], b_v2[1], b_v2[2]}, mlh = b_m2[0];
    for (int i = 0; i < kHidden; ++i) {
      const double av = gelu(v1[size_t(b) * kHidden + i]), am = gelu(m1[size_t(b) * kHidden + i]);
      for (int k = 0; k < 3; ++k) z[k] += w_v2[k * kHidden + i] * av;
      mlh += w_m2[i] * am;
    }
    const double mx = std::max({z[0], z[1], z[2]}), s = std::exp(z[0] - mx) + std::exp(z[1] - mx) + std::exp(z[2] - mx);
    for (int k = 0; k < 3; ++k) worst = std::max(worst, std::fabs(wdlm[b * 4 + k] - std::exp(z[k] - mx) / s));
    worst = std::max(worst, std::fabs(wdlm[b * 4 + 3] - mlh));
  }
  std::snprintf(buf, sizeof(buf), "max |error| %.2e", worst);
  Report("value / moves-left final layers", worst < 1e-4, buf);
}

}  // namespace

int RunKernelSelfTests() {
  g_failures = 0;
  ST_CUDA(cudaSetDevice(0));
  std::cout << "--- fzcuda kernels vs CPU references ---" << std::endl;
  TestExpandInput();
  TestAddLayerNorm(192, true, 1);
  TestAddLayerNorm(192, false, kTokens);
  TestAddLayerNorm(128, true, 1);
  TestLayerNorm(192);
  TestLayerNorm(128);
  TestGelu();
  TestAttention(1, 6);
  TestAttention(4, 6);
  TestHeads();
  return g_failures;
}

}  // namespace lczero::fz
