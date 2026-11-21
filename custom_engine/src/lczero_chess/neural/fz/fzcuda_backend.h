#pragma once

#include <atomic>
#include <memory>
#include <string>
#include <vector>

#include "neural/backend.h"
#include "neural/fz/fz_net.h"
#include "utils/optionsdict.h"

namespace lczero {

// The Backend for the CUDA network runner (neural/fz/): the same role as OnnxBackend, with `--provider fzcuda --weights x.fzw`.
// Everything around it -- the NN cache, BatchingBackend, the search -- is unchanged; they only see Backend / BackendComputation.
//
// Backend options ("provider=fzcuda,fixed_batch=64,contexts=2,autotune=1"):
//   fixed_batch  the batch size the search aims for (and the most it may queue), 1..64; default 64. The runner itself takes any
//                batch from 1 to 64 without padding, so this is only the size the search is told about.
//   contexts     batches in flight at once (each keeps ~70 MB on the GPU); default 2.
//   autotune     0 to skip timing the cuBLASLt algorithms at start-up (saves ~1 s); default 1.
class FzCudaBackend : public Backend {
 public:
  FzCudaBackend() = default;
  ~FzCudaBackend() override = default;

  BackendAttributes GetAttributes() const override;
  std::unique_ptr<BackendComputation> CreateComputation() override;
  void UpdateConfiguration(const OptionsDict& opts) override;
  bool IsSameConfiguration(const OptionsDict& opts) const override;

  fz::Net* net() { return net_.get(); }  // for --test-fzcuda / --bench-fzcuda

 private:
  std::shared_ptr<fz::Net> net_;  // shared with the computations still alive
  std::string weights_path_, backend_opts_;
  float softmax_temp_ = 1.0f;
  int batch_ = fz::kMaxBatch;
};

}  // namespace lczero
