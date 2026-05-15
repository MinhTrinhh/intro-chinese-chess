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
MAX_RECENT_MOVE_KEYS = 20
MAX_SAME_MOVE_REPEAT = 2

def evaluate_board(board, maximizing_camp):
    score = 0
    enemy_shuai_pos = None
    own_attack_pieces = []

    for pos, piece in board.situation.items():
        if piece.camp != maximizing_camp and piece.force == Force.SHUAI:
            enemy_shuai_pos = pos

        piece_val = PIECE_VALUES.get(piece.force, 0)
        if piece.camp == maximizing_camp:
            score += piece_val
            if piece.force in (Force.JU, Force.PAO, Force.MA, Force.BING):
                own_attack_pieces.append((pos, piece))
        else:
            score -= piece_val

    if enemy_shuai_pos:
        # Proximity scoring
        for pos, piece in own_attack_pieces:
            dist = abs(pos[0] - enemy_shuai_pos[0]) + abs(pos[1] - enemy_shuai_pos[1])
            score += max(0, (10 - dist)) * 15

        # King mobility
        enemy_shuai_piece = board.situation.get(enemy_shuai_pos)
        if enemy_shuai_piece:
            raw_moves = enemy_shuai_piece.get_valid_pos(board)
            score += (4 - len(raw_moves)) * 20

    # Check bonus: thưởng nếu đang chiếu tướng địch
    # board.test_check(camp) trả về True nếu camp đang bị chiếu
    # tức là maximizing_camp đang chiếu đối thủ
    try:
        if board.test_check(maximizing_camp.opponent()):
            score += 500
    except Exception:
        pass

    return score

def order_move(board, actions, history=None):
    def score_move(action):
        piece = action['piece']
        dst = action['dst']
        score = 0

        target_piece = board.piece_at(*dst)
        if target_piece is not None:
            victim_val = PIECE_VALUES.get(target_piece.force, 0)
            attacker_val = PIECE_VALUES.get(piece.force, 0)
            score = 10000 + victim_val - (attacker_val / 100)

        # Phạt nước đã đi gần đây để tránh lặp
        if history:
            move_key = ((piece.col, piece.row), dst)
            repeat_count = history.count(move_key)
            score -= repeat_count * 500  # mỗi lần lặp bị phạt nặng

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