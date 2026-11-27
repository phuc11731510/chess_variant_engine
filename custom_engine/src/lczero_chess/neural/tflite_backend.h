#pragma once

// Network backend for Android GPUs: TensorFlow Lite (LiteRT 1.4: libtensorflowlite_jni.so) with its GPU delegate
// (libtensorflowlite_gpu_jni.so, OpenCL on Mali / Adreno), both opened at run time with dlopen, so the engine builds and
// runs without them (the app ships them; "provider=gpu" is the only thing that needs them).
//
// The .tflite is the GPU graph of python/khung_gpu.py: a FIXED batch (GPU kernels are compiled for one shape), input NHWC
// [batch,10,10,204] (the encoder writes planes NCHW: transposed here), outputs "policy" [batch,11500] (logits), "value"
// [batch,3] (WDL, softmaxed), "mlh" [batch,1]. Arithmetic in FP16 on the GPU (precision loss allowed), like self-play on the
// T4s. Measured on a Helio G99 (Mali-G57 MC2), 10 layers d 192: batch 16 ~80 positions/s vs ~20 on the 4 CPU cores.
//
// The GPU delegate is used from ONE thread (the one that built it), as the delegate requires for OpenGL and as is safest
// for OpenCL: every Invoke() is handed to a worker thread owned by the backend.

#include <condition_variable>
#include <functional>
#include <memory>
#include <mutex>
#include <string>
#include <thread>

#include "neural/backend.h"
#include "utils/optionsdict.h"

namespace lczero {

class TfliteBackend : public Backend {
 public:
  TfliteBackend();
  ~TfliteBackend() override;

  BackendAttributes GetAttributes() const override;
  std::unique_ptr<BackendComputation> CreateComputation() override;
  void UpdateConfiguration(const OptionsDict& opts) override;
  bool IsSameConfiguration(const OptionsDict& opts) const override;

  size_t batch() const { return batch_; }
  // One full batch: `nchw` = batch() positions of encoder planes (NCHW); outputs batch() rows each. Thread-safe (serialized).
  void Run(const float* nchw, float* policy, float* value, float* mlh);
  float softmax_temp() const { return softmax_temp_; }

 private:
  struct Impl;
  void OnWorker(const std::function<void()>& f);   // runs f on the GPU thread and waits (rethrows its exception)
  void WorkerLoop();

  std::unique_ptr<Impl> impl_;
  std::string weights_path_, backend_opts_;
  size_t batch_ = 0;
  float softmax_temp_ = 1.0f;
  int cpu_threads_ = 2;

  std::mutex call_mu_;               // one OnWorker() call at a time (Run from several search threads)
  std::mutex mu_;
  std::condition_variable cv_;
  std::function<void()> job_;
  bool job_done_ = true, stop_ = false;
  std::exception_ptr job_error_;
  std::thread worker_;
};

}  // namespace lczero
