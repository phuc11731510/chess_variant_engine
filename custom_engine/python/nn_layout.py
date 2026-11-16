"""The shape of the network's input and output: ONE place on the python side.

Mirrors src/lczero_chess/chess/nn_layout.h, which is the source of truth; test_layout.py reads that header and
fails if any number here differs. Changing a number changes what a network means (old networks and old training
data become unreadable), so also bump kTrainingDataVersion in trainingdata_v1.h and KNOWN_VERSIONS in
trainingdata_reader.py.
"""

BOARD = 10
SQUARES = BOARD * BOARD

# Input: planes of 10 x 10. Per history position: our pieces, their pieces (PIECE_KINDS each, in the order of
# kPieceKindOrder in encoder.cc), then a repetition plane; after the history, the scalar planes below.
PIECE_KINDS = 12
MOVE_HISTORY = 8
PLANES_PER_BOARD = 2 * PIECE_KINDS + 1
HISTORY_PLANES = PLANES_PER_BOARD * MOVE_HISTORY
AUX_EN_PASSANT, AUX_RULE50, AUX_ONES, AUX_CHECKS_US, AUX_CHECKS_THEM = range(5)
AUX_PLANES = 5
AUX_BASE = HISTORY_PLANES
NUM_PLANES = AUX_BASE + AUX_PLANES

# Output: MOVE_TYPES planes of 10 x 10, flattened as type * 100 + from square.
SLIDE_TYPES = 8 * 9
KNIGHT_BASE = SLIDE_TYPES
CAMEL_BASE = KNIGHT_BASE + 8
PROMOTION_BASE = CAMEL_BASE + 8
PROMOTION_PIECES = 9
PROMOTION_DIRECTIONS = 3
MOVE_TYPES = PROMOTION_BASE + PROMOTION_PIECES * PROMOTION_DIRECTIONS
POLICY_SIZE = MOVE_TYPES * SQUARES
