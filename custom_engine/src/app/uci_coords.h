#pragma once
#include <string>
#include "chess/board.h"

// Variant start FEN + the canonical<->real move-coordinate mapping shared by the
// UCI-NN engine, play mode, and the UCI I/O tests.
extern const char* const kUciStartFen;
std::string CanonicalMoveToUci(lczero::Move m, bool black_to_move);
lczero::Move UciToCanonicalMove(const lczero::ChessBoard& board,
                                const std::string& uci, bool black_to_move);
