import math
import json
import os
from src.evaluation.heuristics import evaluate_board, order_move, escape_loop, add_cache

class AlphaBetaAgent:
    def __init__(self, depth=3):
        self.depth = depth
        self.history = []
        
        # Load opening book
        try:
            print('[DEBUG] load move')
            book_path = os.path.join(os.getcwd(), 'move.json')
            with open(book_path, 'r') as f:
                self.book = json.load(f)
        except Exception:
            print('[DEBUG] load move failed')
            self.book = {}

    def get_action(self, board, camp):
        best_score = -math.inf
        best_action = None
        alpha = -math.inf
        beta = math.inf

        actions = board.get_final_valid_actions(camp)
        if not actions:
            return None
        
        # --- Opening Book Move ---
        fen = board.board_to_fen1()
        if hasattr(self, 'book') and fen in self.book:
            book_move = self.book[fen]
            book_src = tuple(book_move['src'])
            book_dst = tuple(book_move['dst'])
            
            # Find the matching action from valid physical moves
            for action in actions:
                piece = action['piece']
                if (piece.col, piece.row) == book_src and action['dst'] == book_dst:
                    print(f"\n[AlphaBeta] Executing Book Move: {book_move.get('_comment', 'Standard Opening')}")
                    add_cache(self.history, action)
                    return action
        # ------------------------------

        if len(actions) > 1:
            actions = escape_loop(self.history, actions)
            actions = order_move(board, actions)

        
        for action in actions:
            piece = action['piece']
            dst = action['dst']

            is_ok, bak_pos, captured = board.virtual_move(piece, dst)

            score = -self._negamax(board, self.depth - 1, -beta, -alpha, camp.opponent())

            board.undo_virtual_move(piece, bak_pos, captured)

            if score > best_score:
                best_score = score
                best_action = action
            
            alpha = max(alpha, best_score)

        if best_action:
            add_cache(self.history, best_action)

        return best_action        

    def _negamax(self, board, depth, alpha, beta, current_turn_camp):
        if depth == 0:
            return evaluate_board(board, current_turn_camp)
        
        actions = board.get_final_valid_actions(current_turn_camp)
        if not actions:
            return -100000 - depth #lost
        
        actions = order_move(board, actions)

        max_eval = -math.inf

        for action in actions:
            piece, dst = action['piece'], action['dst']

            is_ok, bak_pos, captured = board.virtual_move(piece, dst)
            eval = -self._negamax(board, depth - 1, -beta, -alpha, current_turn_camp.opponent())

            board.undo_virtual_move(piece, bak_pos, captured)

            max_eval = max(max_eval, eval)
            alpha = max(alpha, eval)

            if alpha >= beta:
                break
            
        return max_eval
