#pragma once
#include <string>
#include <vector>
#include "trainingdata/trainingdata_v1.h"

namespace lczero {

// Writes a sequence of TrainingDataV1 records to a single file (one file/game).
//
// Output format:
//   - If built with HAVE_ZLIB: gzip-compressed (.gz), matching the Python reader.
//   - Otherwise: raw uncompressed binary (.bin) — still bit-identical records,
//     just larger on disk (fallback so the engine builds without zlib).
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

  bool IsOpen() const { return handle_ != nullptr; }
  const std::string& GetFileName() const { return filename_; }

  // File extension used by the active build mode (".gz" or ".bin").
  static const char* Extension();

 private:
  void Open();

  std::string filename_;
  std::string tmp_filename_;  // written first, renamed to filename_ on success
  void* handle_ = nullptr;  // gzFile (HAVE_ZLIB) or std::ofstream* otherwise
  bool finalized_ = false;
  bool failed_ = false;
};

// Reads every record from a file written by TrainingDataWriter (same build mode).
// Returns false on open error or a truncated/partial trailing record.
bool ReadTrainingData(const std::string& filename,
                      std::vector<TrainingDataV1>& out);

}  // namespace lczero
