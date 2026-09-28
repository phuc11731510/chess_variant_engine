#pragma once
#include <cstdint>
#include <string>
#include <vector>

#include "trainingdata/trainingdata_v1.h"

namespace lczero {

// Compact per-game container (".xz", training-data version 6).
//
// The byte layout, and why it is small and still lossless, are documented once,
// in python/trainingdata_v6.py (the Python side reads what this writes, and both
// sides are tested against each other: --emit-roundtrip + test_roundtrip.py).
// In short: sparse policy as integer visit counts, ply-0 board only (plies 1-7
// are the previous record's plies 0-6 seen from the other side), column layout,
// xz. Every TrainingDataV1 record survives bit for bit -- including malformed
// ones, which fall back to wider storage (FLAG_FLOAT_PI / FLAG_DENSE_PI / FLAG_FULL).

constexpr char kGameV6Magic[4] = {'F', 'Z', 'D', '6'};
constexpr uint32_t kGameV6Revision = 1;
constexpr uint8_t kGameV6FlagFull = 1;
constexpr uint8_t kGameV6FlagFloatPi = 2;
constexpr uint8_t kGameV6FlagDensePi = 4;

// The same 27 board planes (128-bit masks as [lo, hi]) seen by the other side:
// us/them piece planes swapped, ranks mirrored; the repetition plane (26) copied.
void OtherFrame(const uint64_t in[27][2], uint64_t out[27][2]);

// Builds the uncompressed payload of one game, record by record.
class GameV6Encoder {
 public:
  // Appends one record (records must come in game order). Returns false if it
  // does not belong to the game (a different version / input format).
  bool Add(const TrainingDataV1& rec);
  size_t size() const { return flags_.size(); }
  // Header + columns (not compressed).
  std::string Payload() const;

 private:
  uint32_t version_ = 0, input_format_ = 0;
  bool have_prev_ = false;
  uint64_t expect_[7][27][2];  // plies 1..7 the next record has if the chain holds

  std::vector<uint8_t> flags_;
  std::vector<uint16_t> n_legal_, delta_, counts_;
  std::vector<float> pi_float_, pi_dense_;
  std::vector<uint64_t> cur_, hist_;
  std::vector<uint8_t> rule50_, castling_[4], checks_us_, checks_them_, stm_;
  std::vector<uint64_t> ep_;
  std::vector<float> floats_[11];
  std::vector<uint32_t> visits_;
  std::vector<uint16_t> played_idx_, best_idx_;
};

// Payload -> records. Returns false (with a reason in *err) on any inconsistency.
bool DecodeGameV6Payload(const std::string& payload, std::vector<TrainingDataV1>* out,
                         std::string* err);

// xz (LZMA2 preset 9e, 1 MiB dictionary, CRC64), as python/trainingdata_v6.py.
// Both return false when the engine was built without liblzma (HAVE_LZMA).
bool XzCompress(const std::string& in, std::string* out);
bool XzDecompress(const std::string& in, std::string* out);

}  // namespace lczero
