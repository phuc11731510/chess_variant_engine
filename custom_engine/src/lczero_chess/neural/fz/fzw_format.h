#pragma once

// The .fzw weight file of the CUDA network runner (fz/): layout and the reader's interface. python/fzw.py writes the file
// (its docstring is the long description); test_fzw.py reads this header and fails if the two disagree.

#include <cstddef>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

namespace lczero::fz {

constexpr char kFzwMagic[4] = {'F', 'Z', 'W', '1'};
constexpr uint32_t kFzwVersion = 1;
constexpr size_t kFzwHeaderBytes = 128;
constexpr size_t kFzwEntryBytes = 64;

enum FzwDType : uint32_t { kFzwF16 = 0, kFzwF32 = 1 };

#pragma pack(push, 1)
struct FzwHeader {
  char magic[4];
  uint32_t version;
  uint32_t d_model, layers, heads, ffn_mult;
  uint32_t planes, planes_padded, squares, move_types, head_cols;
  uint32_t value_tokens, mlh_tokens, hidden;
  uint32_t n_tensors;
  uint32_t crc32;       // of everything after the header (the directory and the data)
  uint64_t total_size;  // of the whole file
  uint8_t reserved[56];
};
struct FzwEntry {
  char name[32];  // NUL padded
  uint32_t dtype;
  uint32_t rows, cols;
  uint32_t pad;
  uint64_t offset;  // from the start of the file; a multiple of 256
  uint64_t nbytes;
};
#pragma pack(pop)
static_assert(sizeof(FzwHeader) == kFzwHeaderBytes, "FzwHeader must be 128 bytes");
static_assert(sizeof(FzwEntry) == kFzwEntryBytes, "FzwEntry must be 64 bytes");

// A whole .fzw file in memory, checked (magic, version, size, CRC-32, every tensor inside the file). Open() throws
// lczero::Exception with the reason.
class FzwFile {
 public:
  static std::unique_ptr<FzwFile> Open(const std::string& path);

  const FzwHeader& header() const { return header_; }

  // The whole file image (16-byte aligned), e.g. to copy to the GPU in one go: a tensor sits at Get(...) - data().
  const uint8_t* data() const { return bytes_.data(); }
  size_t size() const { return bytes_.size(); }

  // The tensor `name`, which must be of that dtype and shape: a pointer into the file image (16-byte aligned). Throws
  // lczero::Exception naming the tensor when it is missing or differs: an old or foreign file never gets this far.
  const void* Get(const std::string& name, FzwDType dtype, uint32_t rows, uint32_t cols) const;

 private:
  FzwFile() = default;
  std::vector<uint8_t> bytes_;
  FzwHeader header_{};
  std::vector<FzwEntry> entries_;
};

}  // namespace lczero::fz
