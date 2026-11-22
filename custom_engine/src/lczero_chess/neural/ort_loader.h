#pragma once

namespace lczero {

// ONNX Runtime, loaded when first needed. In a Linux build made with -Donnxruntime_dlopen=true (the Colab binary) the binary is
// NOT linked against libonnxruntime.so: it starts without it, and a machine that only runs the CUDA runner (--provider fzcuda)
// never downloads the 79 MB package. Everywhere else (Windows, Android, a normal Linux build) ORT is linked as usual and this
// does nothing.
//
// Call it before the first `Ort::` object; OnnxBackend does. Throws lczero::Exception, saying how to avoid ONNX Runtime, when the
// library cannot be found or is too old.
void EnsureOnnxRuntime();

}  // namespace lczero
