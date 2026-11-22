#pragma once

// The hand-written CUDA kernels of the network runner (fz_net.cu strings them together with cuBLASLt matrix products).
// Everything is FP16 in memory with FP32 arithmetic inside; python/fzw.py `simulate` repeats the same arithmetic on the CPU,
// including every place a value is rounded to FP16.

#include <cuda_fp16.h>
#include <cuda_runtime.h>

#include <cstdint>

namespace lczero::fz {

constexpr int kTokens = 100;         // squares of the board = tokens of the transformer
constexpr int kPlanes = 204;         // input planes (nn_layout.h kInputPlanes)
constexpr int kPlanesPadded = 208;   // ... padded to a multiple of 8 so the product with the embedding runs on tensor cores
constexpr int kHeadDim = 32;         // width of an attention head; AttentionKernel is written for exactly this
constexpr int kRelEntries = 361;     // 19 x 19 relative offsets of the position bias
constexpr int kMoveTypes = 115;      // policy planes (nn_layout.h kMoveTypes)
constexpr int kPolicyEntries = kMoveTypes * kTokens;
constexpr int kValueTokens = 32, kMlhTokens = 8, kHidden = 128;
constexpr int kMaxLegal = 384;       // legal moves of one position (backend.h: EvalResult::p)

// The memory image of lczero::InputPlane (chess/encoder.h): the 128-bit square mask of a plane (Stockfish numbering, 12 files
// per rank) and the value its squares carry. The engine encodes straight into this; the GPU expands it.
struct alignas(16) PlaneGpu {
  uint64_t lo, hi;
  float value;
  float pad[3];  // InputPlane's 12 bytes of alignment padding
};
static_assert(sizeof(PlaneGpu) == 32, "PlaneGpu must mirror InputPlane (32 bytes)");

// x0[b * 100 + token][plane] = value of the plane at that square (0 elsewhere), FP16, 208 columns (the last 4 are 0).
void LaunchExpandInput(const PlaneGpu* planes, __half* x0, int batch, cudaStream_t stream);

// s = x_in + bias[row % bias_rows]  (FP32);  x_out = FP16(s);  ln_out = FP16(LayerNorm(s) * gamma + beta). The embedding: x_in is the
// product with the embedding matrix and bias the position table (+ the embedding bias). d = width of a row (a multiple of 64, at most 512).
void LaunchAddLayerNorm(const __half* x_in, const float* bias, int bias_rows, const float* gamma, const float* beta, __half* x_out,
                        __half* ln_out, int rows, int d, cudaStream_t stream);

// ln_out = FP16(LayerNorm(x) * gamma + beta) for each of `rows` rows of x (FP16). d as above.
void LaunchLayerNorm(const __half* x, const float* gamma, const float* beta, __half* ln_out, int rows, int d, cudaStream_t stream);

// y[m, n] = FP16(GELU(x[m, k] * w[n, k]^T + bias[n])): the first feed-forward product with its activation (see FfnUpKernel).
// Needs n % 128 == 0 and k % 64 == 0 (FfnUpSupported) and a block that may use 64 KB of shared memory (Turing and later).
bool FfnUpSupported(int n, int k);
void LaunchFfnUp(const __half* x, const __half* w, const __half* bias, __half* y, int m, int n, int k, cudaStream_t stream);

// Multi-head attention with the learned relative-position bias, for every (position, head), from the qkv product
// [batch * 100, 3 * heads * 32] (q | k | v, heads of 32 side by side) to out [batch * 100, heads * 32].
void LaunchAttention(const __half* qkv, const float* relbias, __half* out, int batch, int heads, cudaStream_t stream);

// logits[b][i] = head[(b * 100 + index % 100) * head_cols + index / 100] for the i-th legal move of position b (index =
// move_index[b][i], a policy index type * 100 + square); -infinity for an index without a slot.
void LaunchGatherPolicy(const float* head, const uint16_t* move_index, const uint16_t* move_count, float* logits, int batch,
                        int head_cols, cudaStream_t stream);

// The value and moves-left token features from the head product: FP16(GELU(head[..., first .. first + 32 / 8])), laid out
// token-major [batch, 100 * 32] and [batch, 100 * 8].
void LaunchHeadTokens(const float* head, __half* vtok, __half* mtok, int batch, int head_cols, cudaStream_t stream);

// The last layers of the value and moves-left heads: GELU, the second linear layer, the softmax of the WDL.
// wdlm[b] = {W, D, L, moves left}.
void LaunchFinalHeads(const float* val_fc1, const float* mlh_fc1, const float* w_v2, const float* b_v2, const float* w_m2,
                      const float* b_m2, float* wdlm, int batch, cudaStream_t stream);

}  // namespace lczero::fz
