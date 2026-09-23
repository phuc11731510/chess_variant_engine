#pragma once
struct EngineOptions;
// Times the CPU-side operations of a self-play playout and of writing training
// data (move generation, history append/pop, NN input encoding, game-result
// checks, record encoding, gzip) on positions from random games. No network.
int run_bench_cpu(const EngineOptions& o);
