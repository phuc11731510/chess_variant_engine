// C ABI for the FairyZero engine — the seam Dart (dart:ffi) calls on Android via
// libfairyzero.so, instead of spawning custom_engine.exe (Android forbids that).
// The caller drives the SAME UCI protocol as the desktop process engine.
//
//   void* h = fz_create("/path/model.onnx", "cpu");   // or "xnnpack"/"nnapi" later
//   fz_send(h, "uci"); fz_send(h, "isready");          // isready loads the model
//   fz_send(h, "position startpos moves e2e4");
//   fz_send(h, "go nodes 200");
//   char buf[4096]; while (int n = fz_poll(h, buf, sizeof buf)) { /* a UCI line */ }
//   fz_destroy(h);
//
// Output (info/bestmove/legalmoves/result/fen) is produced asynchronously by the
// search worker thread and buffered; poll fz_poll to drain it (returns 0 when empty).
#ifndef FAIRYZERO_FFI_H
#define FAIRYZERO_FFI_H

#ifdef __cplusplus
extern "C" {
#endif

void* fz_create(const char* model_path, const char* provider);
void  fz_send(void* handle, const char* uci_line);
int   fz_poll(void* handle, char* out, int out_cap);
void  fz_destroy(void* handle);

#ifdef __cplusplus
}
#endif

#endif  // FAIRYZERO_FFI_H
