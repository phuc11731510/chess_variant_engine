#pragma once
struct EngineOptions;
// Times PURE neural-network inference through the engine's own ONNX Runtime:
// no MCTS, no tree, no cache. Separates "how fast the device evaluates" from
// "how much the engine loses coordinating CPU and GPU".
int run_bench_nn(const EngineOptions& o);
