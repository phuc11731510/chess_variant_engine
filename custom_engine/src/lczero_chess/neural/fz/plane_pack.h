#pragma once

// The input planes in the form the GPU reads: 32 bytes per plane, {u64 low 64 squares, u64 high 64 squares, f32 value, 12 zero
// bytes} (fz::PlaneGpu in fz_kernels.cuh). The encoder's InputPlane is NOT that: its 128-bit mask is a compiler-dependent type
// (unsigned __int128, or a struct of two words in the other order), so the planes are copied field by field, never as bytes.

#include <cstdint>
#include <cstring>

#include "chess/encoder.h"

namespace lczero::fz {

constexpr size_t kPackedPlaneBytes = 32;
constexpr size_t kPackedPlanesBytes = size_t{kInputPlanes} * kPackedPlaneBytes;

// Writes the kInputPlanes planes to dst (kPackedPlanesBytes bytes).
inline void PackPlanes(const InputPlanes& planes, void* dst) {
  uint8_t* out = static_cast<uint8_t*>(dst);
  std::memset(out, 0, kPackedPlanesBytes);
  for (size_t p = 0; p < planes.size(); ++p) {
    // `unsigned long long`, not uint64_t: the struct Bitboard converts to exactly that (and to unsigned and bool), so a cast to
    // Linux's `unsigned long` is ambiguous. Its conversion gives the low word; `>> 64` brings the high word down.
    const unsigned long long lo = static_cast<unsigned long long>(planes[p].mask);
    const unsigned long long hi = static_cast<unsigned long long>(planes[p].mask >> 64);
    std::memcpy(out + p * kPackedPlaneBytes, &lo, 8);
    std::memcpy(out + p * kPackedPlaneBytes + 8, &hi, 8);
    std::memcpy(out + p * kPackedPlaneBytes + 16, &planes[p].value, 4);
  }
}

}  // namespace lczero::fz
