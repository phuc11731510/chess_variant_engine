#pragma once
#include <memory>
#include <string>
#include <vector>

#include "trainingdata/trainingdata_v1.h"

namespace lczero {

class GameV6Encoder;

// Writes the TrainingDataV1 records of ONE game to a single file.
//
// The file name's extension picks the format:
//   .xz  -- compact v6 game file (python/trainingdata_v6.py; needs HAVE_LZMA):
//           records are collected and the file is written once, at Finalize().
//   .gz  -- the 45940-byte records, gzip-compressed (needs HAVE_ZLIB).
//   else -- the 45940-byte records, uncompressed (.bin).
// Extension() is the best format this build can write; self-play uses it.
class TrainingDataWriter {
 public:
  // Open `filename` for writing (overwrites if it exists).
  explicit TrainingDataWriter(const std::string& filename);
  // Convenience: build "<dir>/game_<game_id>.<ext>" and open it.
  TrainingDataWriter(const std::string& dir, int game_id);
  ~TrainingDataWriter();

  TrainingDataWriter(const TrainingDataWriter&) = delete;
  TrainingDataWriter& operator=(const TrainingDataWriter&) = delete;

  // Append one record. No-op if the file failed to open or a write failed.
  void WriteChunk(const TrainingDataV1& data);

  // Flush, close and move the file to its final name. Returns false (and
  // leaves no file behind) if opening, any write or the close failed.
  // Idempotent; also invoked by the destructor.
  bool Finalize();

  bool IsOpen() const { return handle_ != nullptr || v6_ != nullptr; }
  const std::string& GetFileName() const { return filename_; }

  // File extension of the best format this build writes (".xz", ".gz" or ".bin").
  static const char* Extension();

 private:
  void Open();

  std::string filename_;
  std::string tmp_filename_;  // written first, renamed to filename_ on success
  void* handle_ = nullptr;  // gzFile (.gz) or std::ofstream* (.bin)
  bool gz_ = false;
  std::unique_ptr<GameV6Encoder> v6_;  // .xz: the game being collected
  bool finalized_ = false;
  bool failed_ = false;
};

// Reads every record of a game file written by TrainingDataWriter (.xz, .gz or
// .bin, by extension). Returns false on an open error or a damaged / truncated file.
bool ReadTrainingData(const std::string& filename,
                      std::vector<TrainingDataV1>& out);

}  // namespace lczero
