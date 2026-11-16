"""python/nn_layout.py must say what src/lczero_chess/chess/nn_layout.h says (C++ is the source of truth)."""
import os
import re
import sys

import nn_layout

HEADER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "lczero_chess", "chess", "nn_layout.h")

# C++ constant -> python name
NAMES = {
    "kBoardSize": "BOARD", "kBoardSquares": "SQUARES", "kPieceKinds": "PIECE_KINDS", "kMoveHistory": "MOVE_HISTORY",
    "kPlanesPerBoard": "PLANES_PER_BOARD", "kHistoryPlanes": "HISTORY_PLANES", "kAuxPlaneBase": "AUX_BASE",
    "kInputPlanes": "NUM_PLANES", "kSlideTypes": "SLIDE_TYPES", "kKnightBase": "KNIGHT_BASE", "kCamelBase": "CAMEL_BASE",
    "kPromotionBase": "PROMOTION_BASE", "kPromotionPieces": "PROMOTION_PIECES",
    "kPromotionDirections": "PROMOTION_DIRECTIONS", "kMoveTypes": "MOVE_TYPES", "kPolicySize": "POLICY_SIZE",
}


def evaluate(src):
    """Evaluate the `constexpr int kName = expression;` lines and the AuxPlane enum of the header."""
    values = {}
    text = re.sub(r"//[^\n]*", "", src)
    enum = re.search(r"enum AuxPlane : int \{(.*?)\};", text, re.S).group(1)
    for i, name in enumerate(n.strip() for n in enum.split(",") if n.strip()):
        values[name] = i
    for name, expr in re.findall(r"constexpr int (k\w+) = ([^;]+);", text):
        values[name] = eval(expr, {}, dict(values))
    return values


def main():
    with open(HEADER, encoding="utf-8") as f:
        cpp = evaluate(f.read())
    bad = 0
    for c_name, py_name in NAMES.items():
        if cpp[c_name] != getattr(nn_layout, py_name):
            print(f"[FAIL] {c_name} = {cpp[c_name]} in C++, {py_name} = {getattr(nn_layout, py_name)} in nn_layout.py")
            bad += 1
    for c_name, py_name in (("kAuxEnPassant", "AUX_EN_PASSANT"), ("kAuxRule50", "AUX_RULE50"), ("kAuxOnes", "AUX_ONES"),
                            ("kAuxChecksUs", "AUX_CHECKS_US"), ("kAuxChecksThem", "AUX_CHECKS_THEM"),
                            ("kAuxPlanesCount", "AUX_PLANES")):
        if cpp[c_name] != getattr(nn_layout, py_name):
            print(f"[FAIL] {c_name} = {cpp[c_name]} in C++, {py_name} = {getattr(nn_layout, py_name)} in nn_layout.py")
            bad += 1
    if bad:
        sys.exit(1)
    print(f"[PASS] nn_layout.py == nn_layout.h ({len(NAMES) + 6} numbers; input {nn_layout.NUM_PLANES} planes, "
          f"policy {nn_layout.POLICY_SIZE})")


if __name__ == "__main__":
    main()
