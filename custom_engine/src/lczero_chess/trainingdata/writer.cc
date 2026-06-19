#include "trainingdata/writer.h"

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

void TrainingDataWriter::Open() {
#ifdef HAVE_ZLIB
  handle_ = gzopen(filename_.c_str(), "wb");
#else
  auto* ofs = new std::ofstream(filename_, std::ios::binary | std::ios::trunc);
  if (!ofs->is_open()) {
    delete ofs;
    handle_ = nullptr;
  } else {
    handle_ = ofs;
  }
#endif
  if (!handle_) {
    std::cerr << "[TrainingDataWriter] Failed to open for writing: " << filename_
              << std::endl;
  }
}

TrainingDataWriter::~TrainingDataWriter() { Finalize(); }

void TrainingDataWriter::WriteChunk(const TrainingDataV1& data) {
  if (!handle_) return;
#ifdef HAVE_ZLIB
  gzwrite(static_cast<gzFile>(handle_), &data, sizeof(TrainingDataV1));
#else
  static_cast<std::ofstream*>(handle_)->write(
      reinterpret_cast<const char*>(&data), sizeof(TrainingDataV1));
#endif
}

void TrainingDataWriter::Finalize() {
  if (finalized_) return;
  finalized_ = true;
  if (!handle_) return;
#ifdef HAVE_ZLIB
  gzclose(static_cast<gzFile>(handle_));
#else
  auto* ofs = static_cast<std::ofstream*>(handle_);
  ofs->close();
  delete ofs;
#endif
  handle_ = nullptr;
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
