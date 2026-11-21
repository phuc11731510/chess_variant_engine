#include "neural/ort_loader.h"

#ifdef ORT_API_MANUAL_INIT
#include <dlfcn.h>

#include <mutex>
#include <string>

#include "onnxruntime_cxx_api.h"
#include "utils/exception.h"

namespace lczero {

void EnsureOnnxRuntime() {
  static std::once_flag once;
  static std::string error;
  std::call_once(once, [] {
    // RTLD_GLOBAL: the provider libraries ORT loads later (libonnxruntime_providers_cuda.so) resolve symbols against this one,
    // as they do when it is linked into the executable. The library is found through the executable's RUNPATH (the package
    // directory it was built against) or LD_LIBRARY_PATH (run.sh).
    void* lib = nullptr;
    for (const char* name : {"libonnxruntime.so.1.20.1", "libonnxruntime.so"}) {
      lib = dlopen(name, RTLD_NOW | RTLD_GLOBAL);
      if (lib) break;
    }
    if (!lib) {
      error =
          "ONNX Runtime (libonnxruntime.so) is not on this machine. The CUDA runner does not need it: use --provider fzcuda with a "
          ".fzw network (python/lay_mang.py fzw); for ONNX put the ONNX Runtime package's lib directory on LD_LIBRARY_PATH.";
      return;
    }
    using GetApiBase = const OrtApiBase* (*)();
    const auto get_base = reinterpret_cast<GetApiBase>(dlsym(lib, "OrtGetApiBase"));
    const OrtApi* api = get_base ? get_base()->GetApi(ORT_API_VERSION) : nullptr;
    if (!api) {
      error = "libonnxruntime.so found, but it is older than the ONNX Runtime this engine was built with (API version " +
              std::to_string(ORT_API_VERSION) + ")";
      return;
    }
    Ort::InitApi(api);
  });
  if (!error.empty()) throw Exception(error);
}

}  // namespace lczero

#else

namespace lczero {

void EnsureOnnxRuntime() {}

}  // namespace lczero

#endif
