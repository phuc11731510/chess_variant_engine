#include <cmath>
#include <cstring>

#include "neural/fz/fz_kernels.cuh"

namespace lczero::fz {

namespace {

constexpr unsigned kFullMask = 0xffffffffu;

__device__ __forceinline__ float GeluErf(float x) { return 0.5f * x * (1.0f + erff(x * 0.70710678118654752f)); }

__device__ __forceinline__ uint32_t PackHalf2(float lo, float hi) {
  const __half2 v = __floats2half2_rn(lo, hi);
  uint32_t r;
  __builtin_memcpy(&r, &v, sizeof(r));
  return r;
}

// ---------------------------------------------------------------------------------------------------------------------
// Input: planes -> the [token, plane] matrix the embedding multiplies
// ---------------------------------------------------------------------------------------------------------------------

constexpr int kTokensPerExpandBlock = 20;

// grid (batch, 100 / 20); one thread per plane column. Each thread reads its plane's mask once and writes its column for
// 20 tokens: consecutive threads write consecutive halves of a row, so the stores coalesce.
__global__ void ExpandInputKernel(const PlaneGpu* __restrict__ planes, __half* __restrict__ x0) {
  const int b = blockIdx.x, p = threadIdx.x, t0 = blockIdx.y * kTokensPerExpandBlock;
  uint64_t lo = 0, hi = 0;
  float v = 0.0f;
  if (p < kPlanes) {
    const PlaneGpu pl = planes[static_cast<size_t>(b) * kPlanes + p];
    lo = pl.lo;
    hi = pl.hi;
    v = pl.value;
  }
  const __half on = __float2half_rn(v), off = __float2half_rn(0.0f);
  __half* out = x0 + (static_cast<size_t>(b) * kTokens + t0) * kPlanesPadded + p;
  #pragma unroll
  for (int i = 0; i < kTokensPerExpandBlock; ++i) {
    const int t = t0 + i;
    const int sq = (t / 10) * 12 + (t % 10);  // Stockfish square: 12 files per rank
    const uint64_t word = sq < 64 ? lo : hi;
    out[static_cast<size_t>(i) * kPlanesPadded] = ((word >> (sq & 63)) & 1u) ? on : off;
  }
}

// ---------------------------------------------------------------------------------------------------------------------
// Residual add + LayerNorm: one warp per row, D / 64 half2 per lane
// ---------------------------------------------------------------------------------------------------------------------

constexpr float kLayerNormEps = 1e-5f;
constexpr int kLnWarpsPerBlock = 8;

template <int D>
__global__ void AddLayerNormKernel(const __half* x_in, const __half* __restrict__ y, const float* __restrict__ bias,
                                   int bias_rows, const float* __restrict__ gamma, const float* __restrict__ beta,
                                   __half* x_out, __half* __restrict__ ln_out, int rows) {
  constexpr int kPairs = D / 64;
  const int row = blockIdx.x * kLnWarpsPerBlock + (threadIdx.x >> 5);
  if (row >= rows) return;
  const int lane = threadIdx.x & 31;
  const size_t base = static_cast<size_t>(row) * D;
  const float* brow = bias + static_cast<size_t>(row % bias_rows) * D;

  float v[2 * kPairs];
  #pragma unroll
  for (int j = 0; j < kPairs; ++j) {
    const int c = 2 * lane + 64 * j;
    const float2 a = __half22float2(*reinterpret_cast<const __half2*>(x_in + base + c));
    const float2 bb = *reinterpret_cast<const float2*>(brow + c);
    float s0 = a.x + bb.x, s1 = a.y + bb.y;
    if (y != nullptr) {
      const float2 yy = __half22float2(*reinterpret_cast<const __half2*>(y + base + c));
      s0 += yy.x;
      s1 += yy.y;
    }
    v[2 * j] = s0;
    v[2 * j + 1] = s1;
  }
  float sum = 0.0f;
  #pragma unroll
  for (int i = 0; i < 2 * kPairs; ++i) sum += v[i];
  #pragma unroll
  for (int off = 16; off > 0; off >>= 1) sum += __shfl_xor_sync(kFullMask, sum, off);
  const float mean = sum * (1.0f / D);
  float sq = 0.0f;
  #pragma unroll
  for (int i = 0; i < 2 * kPairs; ++i) sq += (v[i] - mean) * (v[i] - mean);
  #pragma unroll
  for (int off = 16; off > 0; off >>= 1) sq += __shfl_xor_sync(kFullMask, sq, off);
  const float rstd = rsqrtf(sq * (1.0f / D) + kLayerNormEps);
  #pragma unroll
  for (int j = 0; j < kPairs; ++j) {
    const int c = 2 * lane + 64 * j;
    const float2 g = *reinterpret_cast<const float2*>(gamma + c);
    const float2 bt = *reinterpret_cast<const float2*>(beta + c);
    *reinterpret_cast<__half2*>(x_out + base + c) = __floats2half2_rn(v[2 * j], v[2 * j + 1]);
    *reinterpret_cast<__half2*>(ln_out + base + c) =
        __floats2half2_rn((v[2 * j] - mean) * rstd * g.x + bt.x, (v[2 * j + 1] - mean) * rstd * g.y + bt.y);
  }
}

// LayerNorm of rows that already hold the residual stream (the residual add happened in the cuBLASLt epilogue of the product
// before): one warp per row, reads x once, writes ln_out once.
template <int D>
__global__ void LayerNormKernel(const __half* __restrict__ x, const float* __restrict__ gamma, const float* __restrict__ beta,
                                __half* __restrict__ ln_out, int rows) {
  constexpr int kPairs = D / 64;
  const int row = blockIdx.x * kLnWarpsPerBlock + (threadIdx.x >> 5);
  if (row >= rows) return;
  const int lane = threadIdx.x & 31;
  const size_t base = static_cast<size_t>(row) * D;

  float v[2 * kPairs];
  #pragma unroll
  for (int j = 0; j < kPairs; ++j) {
    const float2 a = __half22float2(*reinterpret_cast<const __half2*>(x + base + 2 * lane + 64 * j));
    v[2 * j] = a.x;
    v[2 * j + 1] = a.y;
  }
  float sum = 0.0f;
  #pragma unroll
  for (int i = 0; i < 2 * kPairs; ++i) sum += v[i];
  #pragma unroll
  for (int off = 16; off > 0; off >>= 1) sum += __shfl_xor_sync(kFullMask, sum, off);
  const float mean = sum * (1.0f / D);
  float sq = 0.0f;
  #pragma unroll
  for (int i = 0; i < 2 * kPairs; ++i) sq += (v[i] - mean) * (v[i] - mean);
  #pragma unroll
  for (int off = 16; off > 0; off >>= 1) sq += __shfl_xor_sync(kFullMask, sq, off);
  const float rstd = rsqrtf(sq * (1.0f / D) + kLayerNormEps);
  #pragma unroll
  for (int j = 0; j < kPairs; ++j) {
    const int c = 2 * lane + 64 * j;
    const float2 g = *reinterpret_cast<const float2*>(gamma + c);
    const float2 bt = *reinterpret_cast<const float2*>(beta + c);
    *reinterpret_cast<__half2*>(ln_out + base + c) =
        __floats2half2_rn((v[2 * j] - mean) * rstd * g.x + bt.x, (v[2 * j + 1] - mean) * rstd * g.y + bt.y);
  }
}

// GELU, tanh form, as x * sigmoid(2 * sqrt(2 / pi) * (x + 0.044715 x^3)) (the same function: tanh(z) = 2 sigmoid(2z) - 1).
__global__ void GeluKernel(__half2* x, size_t n2) {
  const size_t i = static_cast<size_t>(blockIdx.x) * blockDim.x + threadIdx.x;
  if (i >= n2) return;
  float2 v = __half22float2(x[i]);
  v.x = v.x / (1.0f + __expf(-1.5957691216f * (v.x + 0.044715f * v.x * v.x * v.x)));
  v.y = v.y / (1.0f + __expf(-1.5957691216f * (v.y + 0.044715f * v.y * v.y * v.y)));
  x[i] = __floats2half2_rn(v.x, v.y);
}

// ---------------------------------------------------------------------------------------------------------------------
// Attention: S = q k^T / sqrt(32) + position bias, softmax over the 100 keys, O = P v. One block per (head, position),
// one warp per tile of 16 queries (7 tiles cover 100 queries). The scores and the probabilities never leave registers: the
// layout of the tensor-core accumulator of one 16x8 tile is also the layout of the next product's A operand (the trick of
// FlashAttention), so P goes from the softmax to the P v product without a trip through memory. Turing has m16n8k8 only.
//
// Fragment layout of mma.m16n8k8 (g = lane / 4, t = lane % 4): A (16 x 8, row): a0 = A[g][2t..2t+1], a1 = A[g+8][2t..2t+1];
// B (8 x 8, col): b0 = B[2t..2t+1][g]; C/D (16 x 8): c0,c1 = C[g][2t..2t+1], c2,c3 = C[g+8][2t..2t+1].
// ---------------------------------------------------------------------------------------------------------------------

constexpr int kAttnWarps = 7;
constexpr int kAttnThreads = kAttnWarps * 32;
constexpr int kKeyTiles = 14;      // 14 tiles of 8 keys = 112 >= 100
constexpr int kKeysPadded = kKeyTiles * 8;
constexpr int kLdK = 40;           // halves per row of K in shared memory (32 + 8: the fragment loads then hit 32 banks)
constexpr int kLdV = 120;          // halves per row of V^T (112 + 8)
static_assert(kAttnWarps * 16 >= kTokens && kKeysPadded >= kTokens);

__device__ __forceinline__ void Mma8(float (&c)[4], uint32_t a0, uint32_t a1, uint32_t b0) {
  asm volatile(
      "mma.sync.aligned.m16n8k8.row.col.f32.f16.f16.f32 {%0,%1,%2,%3}, {%4,%5}, {%6}, {%0,%1,%2,%3};\n"
      : "+f"(c[0]), "+f"(c[1]), "+f"(c[2]), "+f"(c[3])
      : "r"(a0), "r"(a1), "r"(b0));
}

__global__ void __launch_bounds__(kAttnThreads)
    AttentionKernel(const __half* __restrict__ qkv, const float* __restrict__ relbias, __half* __restrict__ out, int heads) {
  __shared__ __align__(16) __half ks[kKeysPadded * kLdK];   // K [key][dh]
  __shared__ __align__(16) __half vt[kHeadDim * kLdV];      // V transposed [dh][key]
  __shared__ float rel[kRelEntries];

  const int h = blockIdx.x, b = blockIdx.y;
  const int tid = threadIdx.x, warp = tid >> 5, lane = tid & 31;
  const int d = heads * kHeadDim, ld = 3 * d;
  const __half* base = qkv + static_cast<size_t>(b) * kTokens * ld + h * kHeadDim;  // q here, k at +d, v at +2d

  // Stage K (as is) and V (transposed), the 12 padding keys as zeros: a zero key scores 0 (masked below) and a zero value
  // row keeps the product with the masked probabilities exactly 0.
  for (int i = tid; i < kKeysPadded * 4; i += kAttnThreads) {
    const int key = i >> 2, c = (i & 3) * 8;
    uint4 kv = make_uint4(0, 0, 0, 0), vv = make_uint4(0, 0, 0, 0);
    if (key < kTokens) {
      kv = *reinterpret_cast<const uint4*>(base + static_cast<size_t>(key) * ld + d + c);
      vv = *reinterpret_cast<const uint4*>(base + static_cast<size_t>(key) * ld + 2 * d + c);
    }
    *reinterpret_cast<uint4*>(ks + key * kLdK + c) = kv;
    const __half* vh = reinterpret_cast<const __half*>(&vv);
    #pragma unroll
    for (int e = 0; e < 8; ++e) vt[(c + e) * kLdV + key] = vh[e];
  }
  for (int i = tid; i < kRelEntries; i += kAttnThreads) rel[i] = relbias[h * kRelEntries + i];
  __syncthreads();

  const int g = lane >> 2, t = lane & 3;
  const int qi0 = warp * 16 + g, qi1 = qi0 + 8;  // the two query rows this thread holds

  // A operand of the scores: the 16 queries of this warp, 4 steps of 8 along the head width.
  uint32_t qa0[4], qa1[4];
  #pragma unroll
  for (int kk = 0; kk < 4; ++kk) {
    qa0[kk] = qi0 < kTokens ? *reinterpret_cast<const uint32_t*>(base + static_cast<size_t>(qi0) * ld + 8 * kk + 2 * t) : 0u;
    qa1[kk] = qi1 < kTokens ? *reinterpret_cast<const uint32_t*>(base + static_cast<size_t>(qi1) * ld + 8 * kk + 2 * t) : 0u;
  }

  // S = q k^T, in 14 tiles of 8 keys. The step along the head width is the OUTER loop: the 14 products of one step are
  // independent of each other, so they issue back to back; with the step inside, each tile waited for its own previous step
  // (the asm is volatile, so the compiler keeps the order written here).
  float s[kKeyTiles][4];
  #pragma unroll
  for (int j = 0; j < kKeyTiles; ++j) s[j][0] = s[j][1] = s[j][2] = s[j][3] = 0.0f;
  #pragma unroll
  for (int kk = 0; kk < 4; ++kk) {
    #pragma unroll
    for (int j = 0; j < kKeyTiles; ++j) {
      const uint32_t b0 = *reinterpret_cast<const uint32_t*>(ks + (8 * j + g) * kLdK + 8 * kk + 2 * t);
      Mma8(s[j], qa0[kk], qa1[kk], b0);
    }
  }

  // Scale, add the bias of the relative offset (row, column of the key minus those of the query), mask the padding keys,
  // and take the row maxima. Rows of padding queries (>= 100) use square 99's offsets: their results are discarded.
  constexpr float kScale = 0.17677669529663687f;  // 1 / sqrt(32)
  const int qc0 = min(qi0, kTokens - 1), qc1 = min(qi1, kTokens - 1);
  const int r0 = qc0 / 10, f0 = qc0 % 10, r1 = qc1 / 10, f1 = qc1 % 10;
  float m0 = -INFINITY, m1 = -INFINITY;
  #pragma unroll
  for (int j = 0; j < kKeyTiles; ++j) {
    #pragma unroll
    for (int e = 0; e < 2; ++e) {
      const int key = 8 * j + 2 * t + e;
      if (key < kTokens) {
        const int rk = key / 10, fk = key - rk * 10;
        s[j][e] = s[j][e] * kScale + rel[(rk - r0 + 9) * 19 + (fk - f0 + 9)];
        s[j][2 + e] = s[j][2 + e] * kScale + rel[(rk - r1 + 9) * 19 + (fk - f1 + 9)];
        m0 = fmaxf(m0, s[j][e]);
        m1 = fmaxf(m1, s[j][2 + e]);
      } else {
        s[j][e] = s[j][2 + e] = -INFINITY;
      }
    }
  }
  m0 = fmaxf(m0, __shfl_xor_sync(kFullMask, m0, 1));
  m0 = fmaxf(m0, __shfl_xor_sync(kFullMask, m0, 2));
  m1 = fmaxf(m1, __shfl_xor_sync(kFullMask, m1, 1));
  m1 = fmaxf(m1, __shfl_xor_sync(kFullMask, m1, 2));

  // P~ = exp(S - max) (not yet divided by the sum: O is divided at the end), packed to FP16 as the A operand of P v.
  constexpr float kLog2e = 1.4426950408889634f;
  float l0 = 0.0f, l1 = 0.0f;
  uint32_t pa0[kKeyTiles], pa1[kKeyTiles];
  #pragma unroll
  for (int j = 0; j < kKeyTiles; ++j) {
    const float p00 = exp2f((s[j][0] - m0) * kLog2e), p01 = exp2f((s[j][1] - m0) * kLog2e);
    const float p10 = exp2f((s[j][2] - m1) * kLog2e), p11 = exp2f((s[j][3] - m1) * kLog2e);
    l0 += p00 + p01;
    l1 += p10 + p11;
    pa0[j] = PackHalf2(p00, p01);
    pa1[j] = PackHalf2(p10, p11);
  }
  l0 += __shfl_xor_sync(kFullMask, l0, 1);
  l0 += __shfl_xor_sync(kFullMask, l0, 2);
  l1 += __shfl_xor_sync(kFullMask, l1, 1);
  l1 += __shfl_xor_sync(kFullMask, l1, 2);

  // O = P v: 4 tiles of 8 along the head width, 14 steps of 8 keys (the 4 tiles of a step are the independent products).
  float o[4][4];
  #pragma unroll
  for (int nt = 0; nt < 4; ++nt) o[nt][0] = o[nt][1] = o[nt][2] = o[nt][3] = 0.0f;
  #pragma unroll
  for (int j = 0; j < kKeyTiles; ++j) {
    #pragma unroll
    for (int nt = 0; nt < 4; ++nt) {
      const uint32_t b0 = *reinterpret_cast<const uint32_t*>(vt + (8 * nt + g) * kLdV + 8 * j + 2 * t);
      Mma8(o[nt], pa0[j], pa1[j], b0);
    }
  }
  const float inv0 = 1.0f / l0, inv1 = 1.0f / l1;
  __half* orow0 = out + (static_cast<size_t>(b) * kTokens + qi0) * d + h * kHeadDim + 2 * t;
  __half* orow1 = out + (static_cast<size_t>(b) * kTokens + qi1) * d + h * kHeadDim + 2 * t;
  #pragma unroll
  for (int nt = 0; nt < 4; ++nt) {
    if (qi0 < kTokens) *reinterpret_cast<__half2*>(orow0 + 8 * nt) = __floats2half2_rn(o[nt][0] * inv0, o[nt][1] * inv0);
    if (qi1 < kTokens) *reinterpret_cast<__half2*>(orow1 + 8 * nt) = __floats2half2_rn(o[nt][2] * inv1, o[nt][3] * inv1);
  }
}

// ---------------------------------------------------------------------------------------------------------------------
// Heads
// ---------------------------------------------------------------------------------------------------------------------

__global__ void GatherPolicyKernel(const float* __restrict__ head, const uint16_t* __restrict__ move_index,
                                   const uint16_t* __restrict__ move_count, float* __restrict__ logits, int head_cols) {
  const int b = blockIdx.x;
  const int n = min(static_cast<int>(move_count[b]), kMaxLegal);
  for (int i = threadIdx.x; i < n; i += blockDim.x) {
    const int index = move_index[b * kMaxLegal + i];
    logits[b * kMaxLegal + i] =
        index < kPolicyEntries ? head[(static_cast<size_t>(b) * kTokens + index % kTokens) * head_cols + index / kTokens] : -INFINITY;
  }
}

constexpr int kTokenFeatures = kValueTokens + kMlhTokens;

// One thread per (position, token, feature): the 40 columns after the policy columns of the head product.
__global__ void HeadTokensKernel(const float* __restrict__ head, __half* __restrict__ vtok, __half* __restrict__ mtok,
                                 int batch, int head_cols) {
  const int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i >= batch * kTokens * kTokenFeatures) return;
  const int row = i / kTokenFeatures, f = i - row * kTokenFeatures;  // row = b * 100 + token
  const float x = GeluErf(head[static_cast<size_t>(row) * head_cols + kMoveTypes + f]);
  if (f < kValueTokens) vtok[static_cast<size_t>(row) * kValueTokens + f] = __float2half_rn(x);
  else mtok[static_cast<size_t>(row) * kMlhTokens + (f - kValueTokens)] = __float2half_rn(x);
}

// One block of 128 threads per position: GELU of the two hidden layers, four dot products of 128, the WDL softmax.
__global__ void FinalHeadsKernel(const float* __restrict__ val_fc1, const float* __restrict__ mlh_fc1,
                                 const float* __restrict__ w_v2, const float* __restrict__ b_v2,
                                 const float* __restrict__ w_m2, const float* __restrict__ b_m2, float* __restrict__ wdlm) {
  const int b = blockIdx.x, i = threadIdx.x;
  const float av = GeluErf(val_fc1[b * kHidden + i]), am = GeluErf(mlh_fc1[b * kHidden + i]);
  float acc[4] = {av * w_v2[i], av * w_v2[kHidden + i], av * w_v2[2 * kHidden + i], am * w_m2[i]};
  #pragma unroll
  for (int off = 16; off > 0; off >>= 1) {
    #pragma unroll
    for (int k = 0; k < 4; ++k) acc[k] += __shfl_xor_sync(kFullMask, acc[k], off);
  }
  __shared__ float part[4][kHidden / 32];
  if ((i & 31) == 0) {
    #pragma unroll
    for (int k = 0; k < 4; ++k) part[k][i >> 5] = acc[k];
  }
  __syncthreads();
  if (i == 0) {
    float z[4];
    #pragma unroll
    for (int k = 0; k < 4; ++k) z[k] = part[k][0] + part[k][1] + part[k][2] + part[k][3] + (k < 3 ? b_v2[k] : b_m2[0]);
    const float m = fmaxf(z[0], fmaxf(z[1], z[2]));
    const float e0 = expf(z[0] - m), e1 = expf(z[1] - m), e2 = expf(z[2] - m);
    const float inv = 1.0f / (e0 + e1 + e2);
    wdlm[b * 4 + 0] = e0 * inv;
    wdlm[b * 4 + 1] = e1 * inv;
    wdlm[b * 4 + 2] = e2 * inv;
    wdlm[b * 4 + 3] = z[3];
  }
}

}  // namespace

// ---------------------------------------------------------------------------------------------------------------------
// Launchers
// ---------------------------------------------------------------------------------------------------------------------

void LaunchExpandInput(const PlaneGpu* planes, __half* x0, int batch, cudaStream_t stream) {
  ExpandInputKernel<<<dim3(batch, kTokens / kTokensPerExpandBlock), kPlanesPadded, 0, stream>>>(planes, x0);
}

void LaunchAddLayerNorm(const __half* x_in, const __half* y, const float* bias, int bias_rows, const float* gamma,
                        const float* beta, __half* x_out, __half* ln_out, int rows, int d, cudaStream_t stream) {
  const int blocks = (rows + kLnWarpsPerBlock - 1) / kLnWarpsPerBlock;
  const int threads = kLnWarpsPerBlock * 32;
#define FZ_LN_CASE(DD)                                                                                              \
  case DD:                                                                                                          \
    AddLayerNormKernel<DD><<<blocks, threads, 0, stream>>>(x_in, y, bias, bias_rows, gamma, beta, x_out, ln_out, rows); \
    break;
  switch (d) {
    FZ_LN_CASE(64)
    FZ_LN_CASE(128)
    FZ_LN_CASE(192)
    FZ_LN_CASE(256)
    FZ_LN_CASE(320)
    FZ_LN_CASE(384)
    FZ_LN_CASE(448)
    FZ_LN_CASE(512)
    default:
      break;  // fz_net.cu refuses such a width when the weights are loaded
  }
#undef FZ_LN_CASE
}

void LaunchLayerNorm(const __half* x, const float* gamma, const float* beta, __half* ln_out, int rows, int d, cudaStream_t stream) {
  const int blocks = (rows + kLnWarpsPerBlock - 1) / kLnWarpsPerBlock;
  const int threads = kLnWarpsPerBlock * 32;
#define FZ_LN_CASE(DD)                                                                       \
  case DD:                                                                                   \
    LayerNormKernel<DD><<<blocks, threads, 0, stream>>>(x, gamma, beta, ln_out, rows);       \
    break;
  switch (d) {
    FZ_LN_CASE(64)
    FZ_LN_CASE(128)
    FZ_LN_CASE(192)
    FZ_LN_CASE(256)
    FZ_LN_CASE(320)
    FZ_LN_CASE(384)
    FZ_LN_CASE(448)
    FZ_LN_CASE(512)
    default:
      break;  // fz_net.cu refuses such a width when the weights are loaded
  }
#undef FZ_LN_CASE
}

void LaunchGelu(__half* x, size_t n, cudaStream_t stream) {
  const size_t n2 = n / 2;
  GeluKernel<<<static_cast<unsigned>((n2 + 255) / 256), 256, 0, stream>>>(reinterpret_cast<__half2*>(x), n2);
}

void LaunchAttention(const __half* qkv, const float* relbias, __half* out, int batch, int heads, cudaStream_t stream) {
  AttentionKernel<<<dim3(heads, batch), kAttnThreads, 0, stream>>>(qkv, relbias, out, heads);
}

void LaunchGatherPolicy(const float* head, const uint16_t* move_index, const uint16_t* move_count, float* logits, int batch,
                        int head_cols, cudaStream_t stream) {
  GatherPolicyKernel<<<batch, 128, 0, stream>>>(head, move_index, move_count, logits, head_cols);
}

void LaunchHeadTokens(const float* head, __half* vtok, __half* mtok, int batch, int head_cols, cudaStream_t stream) {
  const int n = batch * kTokens * kTokenFeatures;
  HeadTokensKernel<<<(n + 255) / 256, 256, 0, stream>>>(head, vtok, mtok, batch, head_cols);
}

void LaunchFinalHeads(const float* val_fc1, const float* mlh_fc1, const float* w_v2, const float* b_v2, const float* w_m2,
                      const float* b_m2, float* wdlm, int batch, cudaStream_t stream) {
  FinalHeadsKernel<<<batch, kHidden, 0, stream>>>(val_fc1, mlh_fc1, w_v2, b_v2, w_m2, b_m2, wdlm);
}

}  // namespace lczero::fz
