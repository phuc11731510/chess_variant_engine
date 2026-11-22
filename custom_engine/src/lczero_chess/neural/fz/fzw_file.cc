#include "neural/fz/fzw_format.h"

#include <array>
#include <cstring>
#include <fstream>

#include "utils/exception.h"

namespace lczero::fz {

namespace {

// CRC-32 (the zlib / Python zlib.crc32 polynomial): the file is written by Python, which uses zlib.
uint32_t Crc32(const uint8_t* p, size_t n) {
  static const std::array<uint32_t, 256> table = [] {
    std::array<uint32_t, 256> t{};
    for (uint32_t i = 0; i < 256; ++i) {
      uint32_t c = i;
      for (int k = 0; k < 8; ++k) c = (c & 1) ? 0xEDB88320u ^ (c >> 1) : c >> 1;
      t[i] = c;
    }
    return t;
  }();
  uint32_t c = 0xFFFFFFFFu;
  for (size_t i = 0; i < n; ++i) c = table[(c ^ p[i]) & 0xFF] ^ (c >> 8);
  return c ^ 0xFFFFFFFFu;
}

std::string NameOf(const FzwEntry& e) { return std::string(e.name, strnlen(e.name, sizeof(e.name))); }

}  // namespace

std::unique_ptr<FzwFile> FzwFile::Open(const std::string& path) {
  std::ifstream in(path, std::ios::binary | std::ios::ate);
  if (!in) throw Exception("fzcuda: cannot open the weights file " + path);
  const std::streamoff size = in.tellg();
  if (size < static_cast<std::streamoff>(kFzwHeaderBytes)) throw Exception("fzcuda: " + path + " is too short to be a .fzw file");
  std::unique_ptr<FzwFile> f(new FzwFile);
  f->bytes_.resize(static_cast<size_t>(size));
  in.seekg(0);
  in.read(reinterpret_cast<char*>(f->bytes_.data()), size);
  if (!in) throw Exception("fzcuda: cannot read the weights file " + path);

  std::memcpy(&f->header_, f->bytes_.data(), sizeof(FzwHeader));
  const FzwHeader& h = f->header_;
  if (std::memcmp(h.magic, kFzwMagic, 4) != 0)
    throw Exception("fzcuda: " + path + " is not a .fzw file (wrong magic); make it with python/fzw.py convert");
  if (h.version != kFzwVersion)
    throw Exception("fzcuda: " + path + " is .fzw version " + std::to_string(h.version) + ", this engine reads version " +
                    std::to_string(kFzwVersion));
  if (h.total_size != f->bytes_.size())
    throw Exception("fzcuda: " + path + " is truncated or has extra bytes (" + std::to_string(f->bytes_.size()) +
                    " bytes, the header says " + std::to_string(h.total_size) + ")");
  if (Crc32(f->bytes_.data() + kFzwHeaderBytes, f->bytes_.size() - kFzwHeaderBytes) != h.crc32)
    throw Exception("fzcuda: " + path + " is corrupt (CRC-32 mismatch)");
  if (h.n_tensors == 0 || kFzwHeaderBytes + static_cast<uint64_t>(h.n_tensors) * kFzwEntryBytes > f->bytes_.size())
    throw Exception("fzcuda: " + path + " has a bad tensor directory");

  f->entries_.resize(h.n_tensors);
  std::memcpy(f->entries_.data(), f->bytes_.data() + kFzwHeaderBytes, h.n_tensors * kFzwEntryBytes);
  for (const FzwEntry& e : f->entries_) {
    const uint64_t elem = e.dtype == kFzwF16 ? 2 : 4;
    if ((e.dtype != kFzwF16 && e.dtype != kFzwF32) || e.nbytes != uint64_t{e.rows} * e.cols * elem ||
        e.offset % 256 != 0 || e.offset + e.nbytes > f->bytes_.size())
      throw Exception("fzcuda: " + path + ": tensor '" + NameOf(e) + "' has a bad directory entry");
  }
  return f;
}

const void* FzwFile::Get(const std::string& name, FzwDType dtype, uint32_t rows, uint32_t cols) const {
  for (const FzwEntry& e : entries_) {
    if (NameOf(e) != name) continue;
    if (e.dtype != dtype || e.rows != rows || e.cols != cols)
      throw Exception("fzcuda: weights tensor '" + name + "' is " + std::to_string(e.rows) + "x" + std::to_string(e.cols) +
                      (e.dtype == kFzwF16 ? " FP16" : " FP32") + ", expected " + std::to_string(rows) + "x" +
                      std::to_string(cols) + (dtype == kFzwF16 ? " FP16" : " FP32"));
    return bytes_.data() + e.offset;
  }
  throw Exception("fzcuda: the weights file has no tensor '" + name + "'");
}

}  // namespace lczero::fz
