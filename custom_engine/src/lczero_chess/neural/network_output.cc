#include "neural/network_output.h"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <sstream>

#include "utils/exception.h"
#if defined(__x86_64__) || defined(__i386__) || defined(_M_X64) || defined(_M_IX86)
#define FZ_X86_SIMD 1
#include <immintrin.h>
#else
#define FZ_X86_SIMD 0   // ARM/Android (or other): use portable scalar fallbacks below
#endif

namespace lczero {

// ---- Output post-processing -------------------------------------------------
//
// Softmax over the legal moves' logits. It used to exponentiate with the
// approximation (1 + x/1024)^1024, whose error grows with the distance from the
// best move: -2% at x = -5, -5% at x = -10, -18% at x = -20. The priors of the
// weaker moves were therefore lower than the ones the network was trained to
// output (PyTorch uses the exact softmax). The gen-0/gen-1 nets are too flat for
// it to matter (their legal logits span ~1), a sharp policy is not. The version
// below is the Cephes expf (range reduction + degree-5 polynomial, a few ulp),
// at about the same cost. The padding lanes of the last vector are masked to 0;
// before, they were -100 and summed in, which only stayed harmless while the
// best logit was well above -100.
#if FZ_X86_SIMD
#if defined(__GNUC__) || defined(__clang__)
__attribute__((target("avx2,fma")))
#endif
static inline __m256 Exp256(__m256 x) {
    // Operand order matters: max/min return their SECOND operand when one is
    // NaN, so a NaN logit stays NaN (and the caller reports it) instead of
    // turning into a tiny probability. Below -87.3 exp() is denormal: those
    // lanes give 2^-126, i.e. nothing next to the best move's 1.
    x = _mm256_max_ps(_mm256_set1_ps(-87.3f), x);
    x = _mm256_min_ps(_mm256_set1_ps(88.3f), x);
    const __m256 k = _mm256_round_ps(_mm256_mul_ps(x, _mm256_set1_ps(1.44269504088896341f)),
                                     _MM_FROUND_TO_NEAREST_INT | _MM_FROUND_NO_EXC);
    __m256 r = _mm256_fnmadd_ps(k, _mm256_set1_ps(0.693359375f), x);   // x - k*ln2, in two
    r = _mm256_fnmadd_ps(k, _mm256_set1_ps(-2.12194440e-4f), r);        // parts (Cody-Waite)
    __m256 p = _mm256_set1_ps(1.9875691500e-4f);
    p = _mm256_fmadd_ps(p, r, _mm256_set1_ps(1.3981999507e-3f));
    p = _mm256_fmadd_ps(p, r, _mm256_set1_ps(8.3334519073e-3f));
    p = _mm256_fmadd_ps(p, r, _mm256_set1_ps(4.1665795894e-2f));
    p = _mm256_fmadd_ps(p, r, _mm256_set1_ps(1.6666665459e-1f));
    p = _mm256_fmadd_ps(p, r, _mm256_set1_ps(5.0000001201e-1f));
    p = _mm256_fmadd_ps(p, _mm256_mul_ps(r, r), r);
    p = _mm256_add_ps(p, _mm256_set1_ps(1.0f));
    const __m256i e = _mm256_slli_epi32(
        _mm256_add_epi32(_mm256_cvtps_epi32(k), _mm256_set1_epi32(127)), 23);  // 2^k
    return _mm256_mul_ps(p, _mm256_castsi256_ps(e));
}

#if defined(__GNUC__) || defined(__clang__)
__attribute__((target("avx2,fma")))
#endif
static float SoftmaxLegalAvx2(float* logits, size_t n, float inv_temp, float max_logit,
                              float* out_p, size_t max_out) {
    const __m256 vmax = _mm256_set1_ps(max_logit);
    const __m256 vinv = _mm256_set1_ps(inv_temp);
    const size_t full = n & ~size_t{7};
    __m256 vsum = _mm256_setzero_ps();
    for (size_t i = 0; i < full; i += 8) {
        const __m256 e = Exp256(_mm256_mul_ps(_mm256_sub_ps(_mm256_load_ps(logits + i), vmax), vinv));
        _mm256_store_ps(logits + i, e);
        vsum = _mm256_add_ps(vsum, e);
    }
    if (full < n) {  // last partial vector: zero the lanes past n
        const int rem = static_cast<int>(n - full);
        const __m256 keep = _mm256_castsi256_ps(_mm256_cmpgt_epi32(
            _mm256_set1_epi32(rem), _mm256_setr_epi32(0, 1, 2, 3, 4, 5, 6, 7)));
        const __m256 x = _mm256_mul_ps(_mm256_sub_ps(_mm256_load_ps(logits + full), vmax), vinv);
        const __m256 e = _mm256_and_ps(Exp256(x), keep);
        _mm256_store_ps(logits + full, e);
        vsum = _mm256_add_ps(vsum, e);
    }
    alignas(32) float lanes[8];
    _mm256_store_ps(lanes, vsum);
    const float sum = ((lanes[0] + lanes[1]) + (lanes[2] + lanes[3])) +
                      ((lanes[4] + lanes[5]) + (lanes[6] + lanes[7]));
    const float inv_sum = 1.0f / sum;
    const size_t out_n = std::min(n, max_out);
    for (size_t i = 0; i < out_n; ++i) out_p[i] = logits[i] * inv_sum;
    return sum;
}
#endif  // FZ_X86_SIMD

float SoftmaxLegal(float* logits, size_t n, float temp, float max_logit, float* out_p,
                   size_t max_out) {
    const float inv_temp = 1.0f / std::max(1e-3f, temp);
#if FZ_X86_SIMD
    return SoftmaxLegalAvx2(logits, n, inv_temp, max_logit, out_p, max_out);
#else  // ARM/Android: output processing is ~0% of the run time, scalar is fine.
    float sum = 0.0f;
    for (size_t i = 0; i < n; ++i) {
        logits[i] = std::exp((logits[i] - max_logit) * inv_temp);
        sum += logits[i];
    }
    const float inv_sum = 1.0f / sum;
    const size_t out_n = std::min(n, max_out);
    for (size_t i = 0; i < out_n; ++i) out_p[i] = logits[i] * inv_sum;
    return sum;
#endif
}

bool IsWdlDistribution(const float* v) {
    // Written so that NaN fails every test.
    // The sum tolerance is 5e-3 (was 1e-3): a softmax computed in half precision (TensorRT FP16, 2026-11-21) rounds each
    // probability to about 5e-4, so the three add up to 1 +- 1e-3 (seen: 0.9839 + 0.0004 + 0.0168 = 1.0011). 5e-3 still
    // refuses raw logits (almost never within 5e-3 of a sum of 1, and not all in [0, 1]) and NaN. The caller renormalises
    // the three values to sum to exactly 1 before using them.
    for (int i = 0; i < 3; ++i)
        if (!(v[i] >= -1e-3f && v[i] <= 1.0f + 1e-3f)) return false;
    return std::fabs(v[0] + v[1] + v[2] - 1.0f) <= 5e-3f;
}

void FillEvalResult(const EvalResultPtr& res, const float* wdl, float mlh, float* legal_logits, size_t num_legal,
                    float softmax_temp, const char* who) {
    // 1. WDL value. The graph must end with a softmax (python/train.py's ExportNet does; so does the CUDA runner); raw
    // logits here would give a meaningless q = W - L, and a NaN would spread through the tree, both without any error.
    if (!IsWdlDistribution(wdl)) {
        std::ostringstream msg;
        msg << who << ": the network's value output is not a W/D/L probability distribution (got " << wdl[0] << ", "
            << wdl[1] << ", " << wdl[2] << "). The model must end with a softmax over its 3 value outputs, as "
            << "python/train.py exports it; NaN means broken weights.";
        std::cerr << msg.str() << std::endl;
        throw Exception(msg.str());
    }
    // Renormalise (the sum may be off by up to 5e-3 from a half-precision softmax): q = (W - L) / (W + D + L),
    // d = D / (W + D + L).
    const float wdl_sum = wdl[0] + wdl[1] + wdl[2];
    if (res.q) *res.q = (wdl[0] - wdl[2]) / wdl_sum;
    if (res.d) *res.d = wdl[1] / wdl_sum;
    // 2. Moves left, in plies (the network's linear output; lc0 clamps it at 0 where it is used). A NaN here would spread
    // through the search through the moves-left utility, so it is refused like the other outputs.
    if (!std::isfinite(mlh)) {
        const std::string msg = std::string(who) + ": the network's moves-left output is not finite (NaN/inf); the weights are broken.";
        std::cerr << msg << std::endl;
        throw Exception(msg);
    }
    if (res.m) *res.m = std::max(mlh, 0.0f);

    // 3. Policy: softmax over the legal moves' logits.
    if (num_legal > 0 && !res.p.empty()) {
        float max_logit = -std::numeric_limits<float>::infinity();
        for (size_t i = 0; i < num_legal; ++i) max_logit = std::max(max_logit, legal_logits[i]);
        const float sum = SoftmaxLegal(legal_logits, num_legal, softmax_temp, max_logit, res.p.data(), res.p.size());
        if (!std::isfinite(sum) || !(sum >= 1.0f)) {  // >= 1: the best move gives exp(0)
            std::ostringstream msg;
            msg << who << ": the network's policy logits are not finite (NaN/inf) for a position with " << num_legal
                << " legal moves; the weights are broken.";
            std::cerr << msg.str() << std::endl;
            throw Exception(msg.str());
        }
    }
}

}  // namespace lczero
