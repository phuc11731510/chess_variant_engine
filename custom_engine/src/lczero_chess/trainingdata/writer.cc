#include "trainingdata/writer.h"

#include <cstdio>
#include <fstream>
#include <iostream>

#ifdef HAVE_ZLIB
#include <zlib.h>
#endif

namespace lczero {

const char* TrainingDataWriter::Extension() {
#ifdef HAVE_ZLIB
  return ".gz";
#else
  return ".bin";
#endif
}

TrainingDataWriter::TrainingDataWriter(const std::string& filename)
    : filename_(filename) {
  Open();
}

TrainingDataWriter::TrainingDataWriter(const std::string& dir, int game_id)
    : filename_(dir + "/game_" + std::to_string(game_id) + Extension()) {
  Open();
}

// Records go to "<name>.tmp" first; Finalize() renames it to <name> only after
// every write and the close succeeded. A full disk or a killed process
// therefore never leaves a truncated file under the .gz/.bin name that
// archive.py and the Python reader pick up (they would fail mid-training).
void TrainingDataWriter::Open() {
  tmp_filename_ = filename_ + ".tmp";
#ifdef HAVE_ZLIB
  handle_ = gzopen(tmp_filename_.c_str(), "wb");
#else
  auto* ofs = new std::ofstream(tmp_filename_, std::ios::binary | std::ios::trunc);
  if (!ofs->is_open()) {
    delete ofs;
    handle_ = nullptr;
  } else {
    handle_ = ofs;
  }
#endif
  if (!handle_) {
    failed_ = true;
    std::cerr << "[TrainingDataWriter] Failed to open for writing: " << tmp_filename_
              << std::endl;
  }
}

TrainingDataWriter::~TrainingDataWriter() { Finalize(); }

void TrainingDataWriter::WriteChunk(const TrainingDataV1& data) {
  if (!handle_ || failed_) return;
#ifdef HAVE_ZLIB
  if (gzwrite(static_cast<gzFile>(handle_), &data, sizeof(TrainingDataV1)) !=
      static_cast<int>(sizeof(TrainingDataV1)))
    failed_ = true;
#else
  auto* ofs = static_cast<std::ofstream*>(handle_);
  ofs->write(reinterpret_cast<const char*>(&data), sizeof(TrainingDataV1));
  if (!*ofs) failed_ = true;
#endif
}

bool TrainingDataWriter::Finalize() {
  if (finalized_) return !failed_;
  finalized_ = true;
  if (handle_) {
#ifdef HAVE_ZLIB
    if (gzclose(static_cast<gzFile>(handle_)) != Z_OK) failed_ = true;
#else
    auto* ofs = static_cast<std::ofstream*>(handle_);
    ofs->close();
    if (!*ofs) failed_ = true;
    delete ofs;
#endif
    handle_ = nullptr;
  }
  if (!failed_) {
    // std::rename does not replace an existing file on Windows.
    std::remove(filename_.c_str());
    if (std::rename(tmp_filename_.c_str(), filename_.c_str()) != 0) failed_ = true;
  }
  if (failed_) {
    std::remove(tmp_filename_.c_str());
    std::cerr << "[TrainingDataWriter] FAILED to write " << filename_
              << " (disk full or I/O error?) -- the game's records were dropped."
              << std::endl;
  }
  return !failed_;
}

bool ReadTrainingData(const std::string& filename,
                      std::vector<TrainingDataV1>& out) {
  out.clear();
  TrainingDataV1 rec;
#ifdef HAVE_ZLIB
  gzFile f = gzopen(filename.c_str(), "rb");
  if (!f) return false;
  while (true) {
    int n = gzread(f, &rec, sizeof(rec));
    if (n == 0) break;  // clean EOF
    if (n != static_cast<int>(sizeof(rec))) {  // truncated / error
      gzclose(f);
      return false;
    }
    out.push_back(rec);
  }
  gzclose(f);
  return true;
#else
  std::ifstream f(filename, std::ios::binary);
  if (!f) return false;
  while (f.read(reinterpret_cast<char*>(&rec), sizeof(rec))) {
    out.push_back(rec);
  }
  // A partial trailing read (gcount in (0, size)) means the file is truncated.
  return f.gcount() == 0;
#endif
}

}  // namespace lczero
