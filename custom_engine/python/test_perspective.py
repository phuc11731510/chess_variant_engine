import numpy as np
import onnxruntime as ort

# Board dimensions
BoardWidth = 10
BoardHeight = 10
PolicyOutputSize = 10600

# Square mapping helper (same as sq_to_tensor_lut in encoder.cc)
def sq_to_flat(sq):
    # s = rank * 12 + file
    # we want to map it to rank * 10 + file
    file = sq % 12
    rank = sq // 12
    if file < 10 and rank < 10:
        return rank * 10 + file
    return -1

def get_sq_index(file, rank):
    return rank * 12 + file

# Move helper
class Move:
    def __init__(self, from_sq, to_sq, promo_type=None):
        self.from_sq = from_sq
        self.to_sq = to_sq
        self.promo_type = promo_type

def move_to_nn_index(move, transform=False):
    from_sq = move.from_sq
    to_sq = move.to_sq
    
    if transform:
        # Flip move vertically
        # Flip from and to squares: (9 - rank) * 12 + file
        from_file = from_sq % 12
        from_rank = from_sq // 12
        to_file = to_sq % 12
        to_rank = to_sq // 12
        
        from_sq = (9 - from_rank) * 12 + from_file
        self_from_flat = (9 - from_rank) * 10 + from_file
        
        to_sq = (9 - to_rank) * 12 + to_file
    
    from_file = from_sq % 12
    from_rank = from_sq // 12
    from_flat = from_rank * 10 + from_file
    
    to_file = to_sq % 12
    to_rank = to_sq // 12
    
    dx = to_file - from_file
    dy = to_rank - from_rank
    
    # 1. Promotion
    if move.promo_type is not None:
        piece_idx = move.promo_type
        if dx == -1: dir_idx = 0
        elif dx == 0: dir_idx = 1
        elif dx == 1: dir_idx = 2
        else: dir_idx = -1
        
        if dir_idx != -1:
            type_idx = 88 + piece_idx * 3 + dir_idx
            return type_idx * 100 + from_flat
            
    # 2. Knight
    abs_dx = abs(dx)
    abs_dy = abs(dy)
    if (abs_dx == 1 and abs_dy == 2) or (abs_dx == 2 and abs_dy == 1):
        knight_idx = -1
        if      dx == 1  and dy == 2:  knight_idx = 0
        elif    dx == 2  and dy == 1:  knight_idx = 1
        elif    dx == 2  and dy == -1: knight_idx = 2
        elif    dx == 1  and dy == -2: knight_idx = 3
        elif    dx == -1 and dy == -2: knight_idx = 4
        elif    dx == -2 and dy == -1: knight_idx = 5
        elif    dx == -2 and dy == 1:  knight_idx = 6
        elif    dx == -1 and dy == 2:  knight_idx = 7
        
        if knight_idx != -1:
            return (72 + knight_idx) * 100 + from_flat
            
    # 3. Camel
    if (abs_dx == 1 and abs_dy == 3) or (abs_dx == 3 and abs_dy == 1):
        camel_idx = -1
        if      dx == 1  and dy == 3:  camel_idx = 0
        elif    dx == 3  and dy == 1:  camel_idx = 1
        elif    dx == 3  and dy == -1: camel_idx = 2
        elif    dx == 1  and dy == -3: camel_idx = 3
        elif    dx == -1 and dy == -3: camel_idx = 4
        elif    dx == -3 and dy == -1: camel_idx = 5
        elif    dx == -3 and dy == 1:  camel_idx = 6
        elif    dx == -1 and dy == 3:  camel_idx = 7
        
        if camel_idx != -1:
            return (80 + camel_idx) * 100 + from_flat
            
    # 4. Sliding
    dir_idx = -1
    distance = 0
    if dx == 0 and dy > 0:       dir_idx = 0; distance = dy
    elif dx > 0 and dy == dx:    dir_idx = 1; distance = dx
    elif dx > 0 and dy == 0:     dir_idx = 2; distance = dx
    elif dx > 0 and dy == -dx:   dir_idx = 3; distance = dx
    elif dx == 0 and dy < 0:     dir_idx = 4; distance = -dy
    elif dx < 0 and dy == dx:    dir_idx = 5; distance = -dx
    elif dx < 0 and dy == 0:     dir_idx = 6; distance = -dx
    elif dx < 0 and dy == -dx:   dir_idx = 7; distance = -dx
    
    if dir_idx != -1 and 1 <= distance <= 9:
        type_idx = dir_idx * 9 + (distance - 1)
        return type_idx * 100 + from_flat
        
    return 0

# Check some test moves
# FEN after 1. e3e4 (White to move has played e3e4)
# Now it is Black's turn.
# Black has a pawn on b8 (rank 7, file 1) which can go to b7 (rank 6, file 1).
# In absolute board coordinates:
# from = b8 = 7 * 12 + 1 = 85
# to = b7 = 6 * 12 + 1 = 73
# This is a move going South (dy = -1).
# Flipped coordinates (for Black):
# from_flipped = b3 = 2 * 12 + 1 = 25
# to_flipped = b4 = 3 * 12 + 1 = 37
# This is a move going North (dy = 1).

m_absolute = Move(85, 73)
m_flipped = Move(25, 37)

print("Let's check MoveToNNIndex outputs:")
print(f"Absolute move b8b7 (unflipped): MoveToNNIndex(m_absolute, 0) = {move_to_nn_index(m_absolute, False)}")
print(f"Absolute move b8b7 (flipped via transform): MoveToNNIndex(m_absolute, 1) = {move_to_nn_index(m_absolute, True)}")
print(f"Flipped move b3b4 (unflipped): MoveToNNIndex(m_flipped, 0) = {move_to_nn_index(m_flipped, False)}")
print(f"Flipped move b3b4 (flipped via transform): MoveToNNIndex(m_flipped, 1) = {move_to_nn_index(m_flipped, True)}")
