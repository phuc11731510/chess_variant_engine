// Tiny harness to verify the libfairyzero C ABI end-to-end: create -> handshake ->
// load model -> search -> drain output until bestmove. Mirrors what the Dart FFI
// NativeFfiEngine will do. Run on device:  LD_LIBRARY_PATH=. ./fz_test model.onnx
#include "app/fairyzero_ffi.h"

#include <chrono>
#include <cstdio>
#include <cstring>
#include <thread>

static void drain(void* h) {
    char buf[8192];
    while (fz_poll(h, buf, (int)sizeof buf) > 0) std::printf("  <<< %s\n", buf);
}

int main(int argc, char** argv) {
    const char* model = argc > 1 ? argv[1] : "model.onnx";
    const char* provider = argc > 2 ? argv[2] : "cpu";
    std::printf("[fz_test] fz_create(model=%s, provider=%s)\n", model, provider);

    void* h = fz_create(model, provider);
    if (!h) { std::printf("[fz_test] FAIL: fz_create returned null\n"); return 1; }

    fz_send(h, "uci");
    fz_send(h, "setoption name Threads value 1");
    fz_send(h, "setoption name BackendThreads value 4");
    fz_send(h, "isready");            // synchronous: loads the model here
    drain(h);                          // uciok / readyok / option lines

    fz_send(h, "position startpos");
    fz_send(h, "go nodes 40");         // async on a worker thread

    bool got_bestmove = false;
    char buf[8192];
    for (int i = 0; i < 1200 && !got_bestmove; ++i) {   // up to ~60s
        int n = fz_poll(h, buf, (int)sizeof buf);
        if (n > 0) {
            std::printf("  <<< %s\n", buf);
            if (std::strncmp(buf, "bestmove", 8) == 0) got_bestmove = true;
        } else {
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
        }
    }

    fz_send(h, "quit");
    fz_destroy(h);
    std::printf("[fz_test] %s\n", got_bestmove ? "PASS: got bestmove via C ABI" : "FAIL: no bestmove");
    return got_bestmove ? 0 : 1;
}
