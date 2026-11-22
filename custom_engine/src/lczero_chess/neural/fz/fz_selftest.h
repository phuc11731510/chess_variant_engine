#pragma once

namespace lczero::fz {

// Self-tests of the hand-written kernels (fz_kernels.cu) on the GPU against plain CPU references, on random data: the input
// expansion (exact), residual + LayerNorm, attention, and the head kernels. Prints one line per test and returns the number of
// failures. A failure here pins a wrong result on one kernel, which --test-fzcuda's comparison of the whole network cannot.
int RunKernelSelfTests();

}  // namespace lczero::fz
