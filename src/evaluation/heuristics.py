from xiangqi.constants import Camp, Force

PIECE_VALUES = {
    Force.SHUAI: 10000,
    Force.JU: 1000,
    Force.PAO: 700,
    Force.MA: 300,
    Force.SHI: 200,
    Force.XIANG: 200,
    Force.BING: 100
}

# Keep enough recent plies to detect A-B-A-B cycles on each side.
MAX_RECENT_MOVE_KEYS = 12
MAX_SAME_MOVE_REPEAT = 2

def evaluate_board(board, maximizing_camp):
    score = 0

    for piece in board.situation.values():
        piece_val = PIECE_VALUES.get(piece.force, 0)

        if piece.camp == maximizing_camp:
            score += piece_val
        else:
            score -= piece_val

    return score

def order_move(board, actions):
    def score_move(action):
        score = 0
        piece = action['piece']
        dst = action['dst']

        target_piece = board.piece_at(*dst)

        if target_piece is not None:
            victim_val = PIECE_VALUES.get(target_piece.force)
            attacker_val = PIECE_VALUES.get(piece.force)


            score = 10000 + victim_val - (attacker_val/100)
        
        return score
    
    actions.sort(key=score_move, reverse=True)
    return actions

def escape_loop(history, actions):
    candidate_actions = []
    for action in actions:
        move_key = ((action['piece'].col, action['piece'].row), action['dst'])
        if history.count(move_key) >= MAX_SAME_MOVE_REPEAT:
            continue
        candidate_actions.append(action)

    # Never return an empty list due to loop filter alone.
    return candidate_actions if candidate_actions else actions

def add_cache(history, best_action):
    best_move_key = ((best_action['piece'].col, best_action['piece'].row), best_action['dst'])
    history.append(best_move_key)
    if len(history) > MAX_RECENT_MOVE_KEYS:
        history.pop(0)