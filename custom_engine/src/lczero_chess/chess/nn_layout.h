#pragma once

// The shape of the network's input and output, in one place: C++ (encoder, training records,
// self-play) and python/ (reader, model) must agree on every number below. The python side repeats
// them in python/nn_layout.py; test_encoder (C++) and python/test_layout.py check the two agree.
//
// Changing anything here changes what a network means: old networks and old training data are
// unreadable, so also bump kTrainingDataVersion (trainingdata/trainingdata_v1.h).

namespace lczero {

// ---- Input: kInputPlanes planes of 10 x 10 --------------------------------------------------------

constexpr int kBoardSize = 10;
constexpr int kBoardSquares = kBoardSize * kBoardSize;

// Piece kinds per side, in the order of kPieceKindOrder (encoder.cc): Pawn, Knight, Rook, Queen, royal,
// Bishop+Wazir, Centaur, wildebeest, Alibaba, Sergeant, Cannon, Grasshopper.
constexpr int kPieceKinds = 12;

constexpr int kMoveHistory = 8;                         // positions fed to the network (current + 7 before)
constexpr int kPlanesPerBoard = 2 * kPieceKinds + 1;    // our pieces, their pieces, repetition
constexpr int kHistoryPlanes = kPlanesPerBoard * kMoveHistory;

// Scalar planes after the history, in this order. (There used to be an all-ones plane here to mark the
// board edge of a zero-padded convolution; the transformer has no padding, so it was removed.)
enum AuxPlane : int {
  kAuxEnPassant,    // the en passant square(s) (a bitboard): the EMPTY square(s) the piece that just made a
                    // double step jumped over, where a capturing piece would land -- not the square of the
                    // piece that would be captured (that one is in the piece planes)
  kAuxRule50,       // rule-50 count / 100
  kAuxChecksUs,     // checks the side to move still needs / 10
  kAuxChecksThem,   // checks the other side still needs / 10
  kAuxPlanesCount
};
constexpr int kAuxPlaneBase = kHistoryPlanes;
constexpr int kInputPlanes = kAuxPlaneBase + kAuxPlanesCount;

// ---- Output: kMoveTypes planes of 10 x 10 (type * 100 + from square) -----------------------------

constexpr int kSlideTypes = 8 * 9;        // 8 directions x distance 1..9 (types 0-71)
constexpr int kKnightBase = kSlideTypes;  // 8 knight jumps (72-79)
constexpr int kCamelBase = kKnightBase + 8;   // 8 camel jumps (80-87)
constexpr int kPromotionBase = kCamelBase + 8;
constexpr int kPromotionPieces = 9;       // Knight, Bishop, Rook, Queen, Centaur, wildebeest, Alibaba, Cannon, Grasshopper
constexpr int kPromotionDirections = 3;   // capture left, straight, capture right
constexpr int kMoveTypes = kPromotionBase + kPromotionPieces * kPromotionDirections;
constexpr int kPolicySize = kMoveTypes * kBoardSquares;

}  // namespace lczero
