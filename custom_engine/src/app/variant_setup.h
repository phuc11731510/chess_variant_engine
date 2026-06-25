#pragma once
#include "variant.h"

// Full Fairy-Stockfish global init (bitboards/options/threads/NNUE/...). main.cc
// runs this sequence inline; the Android FFI path (no main) calls it. Idempotent.
void init_engine_globals();

// Registers the 10x10 custom variant with Fairy-Stockfish; returns its Variant*.
const Stockfish::Variant* setup_custom_variant();
