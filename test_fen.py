from xiangqi.board import Board
from xiangqi.constants import FULL_BOARD
import json

def display_board(board, title):
    # Same printing format your game.py uses to preserve terminal colors!
    print(f"\n{'-'*40}")
    print(f"{title}")
    print(f"{'-'*40}")
    print(str(board))

try:
    with open('move.json', 'r') as f:
        moves = json.load(f)
except:
    moves = {}

for fen, move_data in moves.items():
    print(f"\n{'='*50}")
    if "_comment" in move_data:
        print(f"COMMENT: {move_data['_comment']}")

    try:
        board = Board(fen)
    except Exception as e:
        print(f"ERROR LOAD FEN: {fen}")
        continue
    display_board(board, "BEFORE MOVE")
    
    src = tuple(move_data['src'])
    dst = tuple(move_data['dst'])
    
    # 1. Grab the actual piece object at the src coordinates
    piece = board.piece_at(*src)
    
    if not piece:
        print(f"ERROR: No piece found at {src} for FEN {fen}")
        continue
        
    print(f"\n>> PLAYING: {piece.camp.name} {piece.force.name} from {src} to {dst}")
    
    # 2. Make the move to update the board state
    board.make_move(piece, dst)
    
    display_board(board, "AFTER MOVE")

