#include "trainingdata/writer.h"

#include <cstdio>
#include <fstream>
#include <iostream>
#include <iterator>

#include "trainingdata/game_v6.h"

#ifdef HAVE_ZLIB
#include <zlib.h>
#endif

namespace lczero {

namespace {
bool EndsWith(const std::string& s, const char* suffix) {
  const std::string t(suffix);
  return s.size() >= t.size() && s.compare(s.size() - t.size(), t.size(), t) == 0;
}
}  // namespace

const char* TrainingDataWriter::Extension() {
#if defined(HAVE_LZMA)
  return ".xz";
#elif defined(HAVE_ZLIB)
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

TrainingDataWriter::~TrainingDataWriter() { Finalize(); }

// Records go to "<name>.tmp" first; Finalize() renames it to <name> only after
// every write and the close succeeded. A full disk or a killed process
// therefore never leaves a truncated file under the game's name that
// archive.py and the Python reader pick up (they would fail mid-training).
void TrainingDataWriter::Open() {
  tmp_filename_ = filename_ + ".tmp";
  if (EndsWith(filename_, ".xz")) {
#ifdef HAVE_LZMA
    // Nothing is opened yet: the game is collected in memory (a few hundred KB)
    // and compressed once, at Finalize().
    v6_ = std::make_unique<GameV6Encoder>();
    return;
#else
    failed_ = true;
    std::cerr << "[TrainingDataWriter] " << filename_
              << ": this build has no liblzma (.xz); use " << Extension() << std::endl;
    return;
#endif
  }
  if (EndsWith(filename_, ".gz")) {
#ifdef HAVE_ZLIB
    gz_ = true;
    handle_ = gzopen(tmp_filename_.c_str(), "wb");
#endif
  } else {
    auto* ofs = new std::ofstream(tmp_filename_, std::ios::binary | std::ios::trunc);
    if (!ofs->is_open()) {
      delete ofs;
    } else {
      handle_ = ofs;
    }
  }
  if (!handle_) {
    failed_ = true;
    std::cerr << "[TrainingDataWriter] Failed to open for writing: " << tmp_filename_
              << std::endl;
  }
}

void TrainingDataWriter::WriteChunk(const TrainingDataV1& data) {
  if (failed_) return;
  if (v6_) {
    if (!v6_->Add(data)) {
      failed_ = true;
      std::cerr << "[TrainingDataWriter] " << filename_
                << ": records of one game must share version and input format" << std::endl;
    }
    return;
  }
  if (!handle_) return;
#ifdef HAVE_ZLIB
  if (gz_) {
    if (gzwrite(static_cast<gzFile>(handle_), &data, sizeof(TrainingDataV1)) !=
        static_cast<int>(sizeof(TrainingDataV1)))
      failed_ = true;
    return;
  }
#endif
  auto* ofs = static_cast<std::ofstream*>(handle_);
  ofs->write(reinterpret_cast<const char*>(&data), sizeof(TrainingDataV1));
  if (!*ofs) failed_ = true;
}

bool TrainingDataWriter::Finalize() {
  if (finalized_) return !failed_;
  finalized_ = true;
  if (v6_) {
    if (!failed_) {
      std::string xz;
      if (!XzCompress(v6_->Payload(), &xz)) {
        failed_ = true;
      } else {
        std::ofstream ofs(tmp_filename_, std::ios::binary | std::ios::trunc);
        ofs.write(xz.data(), static_cast<std::streamsize>(xz.size()));
        ofs.close();
        if (!ofs) failed_ = true;
      }
    }
    v6_.reset();
  } else if (handle_) {
#ifdef HAVE_ZLIB
    if (gz_) {
      if (gzclose(static_cast<gzFile>(handle_)) != Z_OK) failed_ = true;
    } else
#endif
    {
      auto* ofs = static_cast<std::ofstream*>(handle_);
      ofs->close();
      if (!*ofs) failed_ = true;
      delete ofs;
    }
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
  if (EndsWith(filename, ".xz")) {
    std::ifstream f(filename, std::ios::binary);
    if (!f) return false;
    const std::string xz((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
    std::string payload, err;
    if (!XzDecompress(xz, &payload)) return false;
    if (!DecodeGameV6Payload(payload, &out, &err)) {
      std::cerr << "[ReadTrainingData] " << filename << ": " << err << std::endl;
      return false;
    }
    return true;
  }
  TrainingDataV1 rec;
  if (EndsWith(filename, ".gz")) {
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
    return false;
#endif
  }
  std::ifstream f(filename, std::ios::binary);
  if (!f) return false;
  while (f.read(reinterpret_cast<char*>(&rec), sizeof(rec))) {
    out.push_back(rec);
  }
  // A partial trailing read (gcount in (0, size)) means the file is truncated.
  return f.gcount() == 0;
}

}  // namespace lczero
