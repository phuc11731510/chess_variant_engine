#pragma once
#include "variant.h"

// Full Fairy-Stockfish global init (bitboards/options/threads/NNUE/...). main.cc
// runs this sequence inline; the Android FFI path (no main) calls it. Idempotent.
void init_engine_globals();

// Registers the 10x10 custom variant with Fairy-Stockfish; returns its Variant*.
const Stockfish::Variant* setup_custom_variant();

#include <string>

// Checks a starting FEN given to self-play (--start-fen, one opening-book line).
// Returns "" when it is a valid start position of THIS variant, else the reason.
// Fairy-Stockfish accepts almost anything without complaint -- a FEN without
// the "N+N" check field is read as 1+1 (the first check wins), castling rights
// without their rook are dropped, a missing royal piece is not reported -- so a
// bad line would otherwise change the rules of every game it starts, silently.
std::string CheckStartFen(const std::string& fen);

#include <vector>

// Reads the start positions given with --start-fen (self-play and arena): `arg` is either a FILE with one FEN per
// line ('#' comments and blank lines skipped, Windows line ends tolerated) or a single FEN string. Every position
// goes through CheckStartFen before the first game. Returns "" on success, else the reason (for a file with its
// name and line number). On success `book` holds the lines of a file (and `single` is untouched), or `book` is
// empty and `single` holds the one FEN.
std::string LoadStartFens(const std::string& arg, std::vector<std::string>* book, std::string* single);
