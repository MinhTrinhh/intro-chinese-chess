"""
Board Encoder: Convert Xiangqi board state to tensor representation.

Integer Encoding Scheme (per cell):
  0: empty
  +1 to +7: red pieces (positive)
  -1 to -7: black pieces (negative)

Piece Mapping:
  1: BING (pawn/soldier)
  2: JU (rook/chariot)
  3: MA (knight/horse)
  4: SHI (advisor)
  5: XIANG (elephant)
  6: PAO (cannon)
  7: SHUAI (king/general)
"""

import torch
from xiangqi.constants import Camp, Force


# Mapping Force enum → integer
FORCE_TO_INT = {
    Force.BING: 1,
    Force.JU: 2,
    Force.MA: 3,
    Force.SHI: 4,
    Force.XIANG: 5,
    Force.PAO: 6,
    Force.SHUAI: 7,
}

# Reverse mapping
INT_TO_FORCE = {v: k for k, v in FORCE_TO_INT.items()}


# FEN Character Mapping: fen_char → (force, camp)
FEN_CHAR_MAP = {
    # Black pieces (lowercase)
    'r': (Force.JU, Camp.BLACK),      # Chariot
    'h': (Force.MA, Camp.BLACK),      # Horse
    'e': (Force.XIANG, Camp.BLACK),   # Elephant
    'a': (Force.SHI, Camp.BLACK),     # Advisor
    'k': (Force.SHUAI, Camp.BLACK),   # General/King
    'c': (Force.PAO, Camp.BLACK),     # Cannon
    'p': (Force.BING, Camp.BLACK),    # Pawn/Soldier
    # Red pieces (uppercase)
    'R': (Force.JU, Camp.RED),
    'H': (Force.MA, Camp.RED),
    'E': (Force.XIANG, Camp.RED),
    'A': (Force.SHI, Camp.RED),
    'K': (Force.SHUAI, Camp.RED),
    'C': (Force.PAO, Camp.RED),
    'P': (Force.BING, Camp.RED),
}


def fen_to_tensor(fen: str) -> torch.Tensor:
    """
    Convert FEN string directly to tensor (no Board object needed).
    Returns:
        torch.Tensor of shape [90], dtype=torch.float32
        Index mapping: i = col * 10 + row
    """
    tensor = torch.zeros(90, dtype=torch.float32)
    
    rows = fen.split('/')
    for row_idx, row in enumerate(rows):
        col_idx = 0
        for char in row:
            if char.isdigit():
                # Skip empty cells
                col_idx += int(char)
            else:
                if char in FEN_CHAR_MAP:
                    force, camp = FEN_CHAR_MAP[char]
                    idx = col_idx * 10 + row_idx
                    piece_val = FORCE_TO_INT.get(force, 0)
                    
                    # Apply sign based on camp
                    tensor[idx] = piece_val if camp == Camp.RED else -piece_val
                
                col_idx += 1
    
    return tensor


def board_to_tensor(board, camp=None):
    """
    Convert board state to torch tensor.
    
    Args:
        board: Xiangqi Board object
        camp: Optional. If provided, normalize perspective to this camp.
              If RED: red is positive, black is negative
              If BLACK: black is positive, red is negative (perspective flip)
    
    Returns:
        torch.Tensor of shape [90], dtype=torch.float32
        Index mapping: i = col * 10 + row
    """
    tensor = torch.zeros(90, dtype=torch.float32)
    
    # Iterate through all pieces on board
    for piece in board.situation.values():
        col, row = piece.col, piece.row
        idx = col * 10 + row
        
        # Get piece type integer
        piece_type_int = FORCE_TO_INT.get(piece.force, 0)
        
        # Apply sign based on camp
        if piece.camp == Camp.RED:
            value = piece_type_int
        else:  # Camp.BLACK
            value = -piece_type_int
        
        # If camp perspective is specified, flip if needed
        if camp is not None and camp == Camp.BLACK:
            value = -value
        
        tensor[idx] = value
    
    return tensor


def board_to_tensor_batch(boards, camp=None):
    """
    Convert multiple boards to tensor batch.
    
    Args:
        boards: List of Board objects
        camp: Optional camp perspective
    
    Returns:
        torch.Tensor of shape [batch_size, 90]
    """
    batch = torch.stack([board_to_tensor(board, camp) for board in boards])
    return batch


def get_piece_at(tensor, col, row):
    idx = col * 10 + row
    return int(tensor[idx].item()) #* Returns integer encoding of piece at (col, row) in the tensor


# def get_board_stats(tensor):
#     """
#     Get basic statistics about board state.
#     Returns:
#         dict with piece counts
#     """
#     red_pieces = {}
#     black_pieces = {}
    
#     for i in range(90):
#         val = int(tensor[i].item())
#         if val > 0:
#             piece_type = INT_TO_FORCE[val]
#             red_pieces[piece_type] = red_pieces.get(piece_type, 0) + 1
#         elif val < 0:
#             piece_type = INT_TO_FORCE[-val]
#             black_pieces[piece_type] = black_pieces.get(piece_type, 0) + 1
    
#     return {
#         "red": red_pieces,
#         "black": black_pieces,
#         "red_count": sum(red_pieces.values()),
#         "black_count": sum(black_pieces.values()),
#     }


# def test_board_encoding():
#     """
#     Unit test: board → tensor → verify consistency
#     """
#     from xiangqi.board import Board
#     from xiangqi.constants import FULL_BOARD
    
#     print("[TEST] Board Encoding")
#     print("-" * 50)
    
#     # Create initial board
#     board = Board(FULL_BOARD)
    
#     # Encode to tensor
#     tensor = board_to_tensor(board)
#     print(f"✓ Encoded board to tensor: shape {tensor.shape}")
    
#     # Verify tensor properties
#     assert tensor.shape == (90,), f"Expected shape (90,), got {tensor.shape}"
#     assert tensor.dtype == torch.float32, f"Expected float32, got {tensor.dtype}"
    
#     # Check initial board has pieces
#     stats = get_board_stats(tensor)
#     print(f"✓ Red pieces: {stats['red_count']}, Black pieces: {stats['black_count']}")
#     assert stats['red_count'] == 16, f"Expected 16 red pieces, got {stats['red_count']}"
#     assert stats['black_count'] == 16, f"Expected 16 black pieces, got {stats['black_count']}"
    
#     # Verify specific pieces exist
#     print(f"  Red pieces breakdown: {stats['red']}")
#     print(f"  Black pieces breakdown: {stats['black']}")
    
#     # Test perspective flip
#     tensor_black_perspective = board_to_tensor(board, camp=Camp.BLACK)
#     # Should be negative of original
#     assert torch.allclose(tensor_black_perspective, -tensor, atol=1e-6), \
#         "Perspective flip failed"
#     print(f"✓ Perspective flip works (RED perspective vs BLACK perspective)")
    
#     # Test with a moved board
#     actions = board.get_final_valid_actions(Camp.RED)
#     if actions:
#         action = actions[0]
#         piece, dst = action['piece'], action['dst']
#         is_ok, bak_pos, captured = board.virtual_move(piece, dst)
        
#         tensor_moved = board_to_tensor(board)
#         # Piece count should change if capture
#         stats_moved = get_board_stats(tensor_moved)
#         print(f"✓ After move - Red: {stats_moved['red_count']}, Black: {stats_moved['black_count']}")
        
#         # Verify difference
#         diff = torch.sum(torch.abs(tensor - tensor_moved))
#         print(f"✓ Tensor difference: {diff.item():.2f}")
        
#         board.undo_virtual_move(piece, bak_pos, captured)
    
#     # Test batch encoding
#     boards = [board] * 3
#     batch = board_to_tensor_batch(boards)
#     assert batch.shape == (3, 90), f"Expected shape (3, 90), got {batch.shape}"
#     print(f"✓ Batch encoding works: shape {batch.shape}")
    
#     print("-" * 50)
#     print("✅ All encoding tests passed!")


if __name__ == "__main__":
    # test_board_encoding()
    pass
