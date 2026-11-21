#pragma once

// The CUDA network runner ("fzcuda"): the transformer of python/model.py evaluated on the GPU with cuBLASLt matrix products and
// hand-written kernels (fz_kernels.cu), in place of ONNX Runtime. This header has no CUDA types, so the backend that uses it
// (fzcuda_backend.cc) is plain C++; everything CUDA lives in fz_net.cu, which is compiled by nvcc.
//
// Data flow of one batch: the engine encodes each position straight into a pinned `Stage` (the 204 planes as bitmasks + values,
// and the policy index of every legal move); Run() copies it to the GPU, expands the planes there, runs the network, gathers
// the logits of the legal moves only, and copies back those logits and the WDL / moves-left of each position.

#include <cstdint>
#include <memory>
#include <string>
#include <vector>

namespace lczero::fz {

constexpr int kMaxBatch = 64;     // positions per Run (== MaxBatchSize of neural/backend.h)
constexpr int kStagePlanes = 204;
constexpr int kStageMaxLegal = 384;
constexpr uint16_t kNoPolicySlot = 0xFFFF;

// Pinned host memory for one batch. The backend fills `planes` / `move_index` / `move_count` and reads `logits` / `wdlm`.
struct Stage {
  void* planes;           // [kMaxBatch][204] x 32 bytes: the InputPlanes (chess/encoder.h) of each position
  uint16_t* move_index;   // [kMaxBatch][384]: policy index (type * 100 + square) of each legal move, or kNoPolicySlot
  uint16_t* move_count;   // [kMaxBatch]: legal moves of each position (at most 384)
  float* logits;          // [kMaxBatch][384]: policy logit of each legal move (output)
  float* wdlm;            // [kMaxBatch][4]: W, D, L (a softmax) and moves left in plies (output)
};

struct NetOptions {
  int contexts = 2;        // batches in flight at once (each has its own stream and workspace, ~70 MB of GPU memory)
  bool autotune = true;    // time the candidate cuBLASLt algorithms of every product at the largest batch, keep the fastest
  bool verbose = true;
};

// Time per stage of one forward pass (Net::Profile).
struct StageTime {
  std::string name;
  double ms;
};

// A copy of an intermediate activation of the first position of a batch (Net::Taps), converted to float.
struct Tap {
  std::string name;
  int rows = 0, cols = 0;
  std::vector<float> values;  // [rows][cols]
};

class Net {
 public:
  // Loads the weights (a .fzw file, python/fzw.py) to the GPU and prepares the products. Throws lczero::Exception with a
  // readable reason when anything is missing: no GPU, no libcublasLt.so.12, an old GPU, a bad or foreign weights file.
  static std::unique_ptr<Net> Create(const std::string& fzw_path, const NetOptions& options);
  ~Net();

  Stage* AcquireStage();          // pooled pinned memory; the caller owns it until ReleaseStage
  void ReleaseStage(Stage* stage);

  // Evaluates the first `batch` (1 .. kMaxBatch) positions of `stage`, blocking until the results are in `stage`.
  // Thread-safe: concurrent calls use different contexts (a call waits when all are busy).
  void Run(Stage* stage, int batch);

  // GPU time of each stage of a forward pass at this batch size (average of `reps` runs after a warm-up), on all-empty
  // positions. For --bench-fzcuda and the T4 profile.
  std::vector<StageTime> Profile(int batch, int reps);

  // The intermediate activations of the first position of `stage` (the embedding, layer 0's qkv / attention / output, the final
  // LayerNorm, the head product ...), to find the first stage where the GPU leaves python/fzw.py `simulate`.
  std::vector<Tap> Taps(Stage* stage, int batch);

  std::string Describe() const;   // one line: GPU, net size, cuBLASLt version
  int d_model() const;
  int layers() const;

  struct Impl;

 private:
  explicit Net(std::unique_ptr<Impl> impl);
  std::unique_ptr<Impl> impl_;
};

}  // namespace lczero::fz
