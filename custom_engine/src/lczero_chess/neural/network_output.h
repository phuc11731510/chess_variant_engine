#pragma once

#include <cstddef>

#include "neural/backend.h"

namespace lczero {

// What every network backend (ONNX Runtime, the CUDA runner) does with the raw outputs of one position: check them, and
// turn them into the EvalResult the search reads. One implementation, so a backend cannot differ from another in what
// it accepts or how it normalises.

// SoftmaxLegal: out_p[i] = exp((logits[i] - max_logit) / temp) / sum, for
// i < n (n <= 384). `logits` is scratch (overwritten) and must be 32-byte
// aligned with room for n rounded up to 8. `max_logit` is max(logits[0..n)).
// Returns the sum of the exponentials (>= 1 for finite input; not finite when
// the net produced NaN/inf). Accurate to a few float ulps on x86 (AVX2) and ARM.
float SoftmaxLegal(float* logits, size_t n, float temp, float max_logit, float* out_p, size_t max_out);

// True when a value-head row is a WDL distribution (finite, each in [0,1], sum 1 within 5e-3), i.e. the net ends with a
// softmax like python/train.py exports it (the CUDA runner does the same).
bool IsWdlDistribution(const float* wdl);

// One position: wdl[3] (W, D, L), mlh (moves left in plies), and the policy logits of its num_legal legal moves
// (-infinity for a move without a policy slot): legal_logits is scratch (overwritten), 32-byte aligned with room for
// num_legal rounded up to 8. Fills res.q / res.d / res.m / res.p. Throws lczero::Exception (after printing the reason
// to stderr; `who` names the backend) for a NaN, a value that is not a WDL distribution, or non-finite policy logits:
// the weights are broken and the search must not use them.
void FillEvalResult(const EvalResultPtr& res, const float* wdl, float mlh, float* legal_logits, size_t num_legal,
                    float softmax_temp, const char* who);

}  // namespace lczero
