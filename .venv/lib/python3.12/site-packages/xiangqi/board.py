import re
from collections import defaultdict
from enum import IntEnum
from typing import Dict, Tuple

import numpy as np

from constants import Camp, Force, Action, N_COLS, N_ROWS, EMPTY_BOARD_UCCI as EMPTY_BOARD
from force import FORCE_CLZ
from helper import toggle_view
from piece import PLACE_CHARS, PIECE_CHARS, PIECE_CHARS_WXF, FORCE_ALIAS_INV, COL_ALIAS_INV, COL_ALIAS, \
    Piece, recog_piece, piece_2_char_wxf

ACTION_ALIAS = {
    Action.ADVANCE: '进',
    Action.RETREAT: '退',
    Action.TRAVERSE: '平',
    Action.SUE_DRAW: '求和',
    Action.RESIGN: '认输',
}
ACTION_ALIAS_INV = {v: k for k, v in ACTION_ALIAS.items()}


class RowIndicator(IntEnum):
    FRONT = 1
    MID = 2
    REAR = 3
    SECOND = 4
    THIRD = 5
    FORTH = 6
    FIFTH = 7


ROW_INDICATOR_ALIAS = {
    RowIndicator.FRONT: '前',
    RowIndicator.REAR: '后',
    RowIndicator.MID: '中',
    RowIndicator.SECOND: '二',
    RowIndicator.THIRD: '三',
    RowIndicator.FORTH: '四',
    RowIndicator.FIFTH: '五',
}
ROW_INDICATOR_ALIAS_INV = {v: k for k, v in ROW_INDICATOR_ALIAS.items()}

ICCS_ACTION_COL_MAP = {c: i for i, c in enumerate('abcdefghi')}
ICCS_ACTION_ROW_MAP = {str(i): N_ROWS - 1 - i for i in range(N_ROWS)}
ICCS_ACTION_COL_INV_MAP = {v: k for k, v in ICCS_ACTION_COL_MAP.items()}
ICCS_ACTION_ROW_INV_MAP = {v: k for k, v in ICCS_ACTION_ROW_MAP.items()}

PAT_BOARD_ROW = re.compile(r'\s*(.)－(.)－(.)－(.)－(.)－(.)－(.)－(.)－(.).*')


class Board:
    """
           cxj
     012345678
    0         9
    1         8
    2         7
    3         6
    4         5
    5         4
    6         3
  r 7         2
  y 8         1
  i 9         0
     876543210
    """

    def __init__(self, situation):
        if isinstance(situation, str):
            if '/' in situation:
                situation = self._parse_fen1(situation.strip().split()[0])
            else:
                situation = self._parse(situation)
        elif isinstance(situation, np.ndarray):
            situation = self.decode(situation)
        elif isinstance(situation, list):
            sitd = {(p.col, p.row): p for p in situation}
            assert len(sitd) == len(situation)
            situation = sitd
        self.situation: Dict[Tuple[int, int], Piece] = situation
        self.checked = {Camp.RED: False, Camp.BLACK: False}

    def __str__(self):
        sit = {f'p{i}{j}': PLACE_CHARS[0] for i in range(N_ROWS) for j in range(N_ROWS)}
        for p in self.situation.values():
            k = f'p{p.row}{p.col}'
            sit[k] = str(p)
        return EMPTY_BOARD.format(**sit)

    def observe(self):
        return self.encode()

    def get_valid_actions(self, camp):
        valid_actions = []
        for p in self.situation.values():
            if p.camp != camp:
                continue
            poses = p.get_valid_pos(self)
            for pos in poses:
                valid_actions.append({'piece': p, 'dst': pos})
        return valid_actions

    def get_final_valid_actions(self, camp: Camp):
        """ a action is valid:
        1. must not ignore check by opponent
        2. must not to be checked actively
        :param camp:
        :return: list of action
        """
        valid_actions = self.get_valid_actions(camp)
        real_actions = []
        for a in valid_actions:
            is_ok, bak_pos, dst_p = False, None, None
            try:
                is_ok, bak_pos, dst_p = self.virtual_move(a['piece'], a['dst'])
                enemy_shuai_will_be_killed = is_ok and dst_p is not None and dst_p.force == Force.SHUAI
                if enemy_shuai_will_be_killed or not self.test_check(camp.opponent()):
                    real_actions.append(a)
            finally:
                if is_ok:
                    self.undo_virtual_move(a['piece'], bak_pos, dst_p)
        return real_actions

    def virtual_move(self, piece: Piece, dst):
        bak_pos = (piece.col, piece.row)
        is_ok, captured = self.naked_move(piece, dst)
        return is_ok, bak_pos, captured

    def undo_virtual_move(self, bak_piece: Piece, bak_pos, removed_piece):
        if bak_pos is not None:
            assert bak_pos not in self.situation
            is_ok, captured = self.naked_move(bak_piece, bak_pos)
            assert is_ok
            assert captured is None
        if removed_piece is not None:
            self.situation[(removed_piece.col, removed_piece.row)] = removed_piece

    def piece_at(self, col, row):
        return self.situation.get((col, row), None)

    def throw_away(self, piece):
        self.situation.pop((piece.col, piece.row), None)

    def get_shuai(self, camp):
        black_palace = [(4, 0), (3, 0), (5, 0),
                        (4, 1), (3, 1), (5, 1),
                        (4, 2), (3, 2), (5, 2)]
        red_palace = [(4, 9), (3, 9), (5, 9),
                      (4, 8), (3, 8), (5, 8),
                      (4, 7), (3, 7), (5, 7)]
        palaces = {Camp.BLACK: black_palace, Camp.RED: red_palace}
        palace = palaces[camp]
        for pos in palace:
            if pos in self.situation:
                p = self.situation[pos]
                if p.force == Force.SHUAI:
                    return p
        return None

    @staticmethod
    def _parse(board: str):
        board = board.strip()
        rows = board.splitlines()
        sit = {}
        i = -1
        for row in rows:
            m = PAT_BOARD_ROW.match(row)
            if not m:
                continue
            i += 1
            for j, c in enumerate(m.groups()):
                if c not in PIECE_CHARS:
                    continue
                camp, force = recog_piece(c)
                clz = FORCE_CLZ[force]
                sit[(j, i)] = clz(camp, j, i)
        return sit

    @staticmethod
    def _parse_fen1(board: str):
        assert '/' in board
        board = board.strip()
        rows = board.split('/')
        assert len(rows) == N_ROWS
        sit = {}
        for i, r in enumerate(rows):
            j = 0
            for e in r:
                if e in PIECE_CHARS_WXF:
                    camp = Camp.BLACK if e.islower() else Camp.RED
                    force = FORCE_ALIAS_INV[e]
                    clz = FORCE_CLZ[force]
                    sit[(j, i)] = clz(camp, j, i)
                    j += 1
                else:
                    assert e.isdigit()
                    j += int(e)
            assert j == N_COLS
        return sit

    def board_to_fen1(self):
        """first part of FEN string"""
        b = [[' ' for _ in range(N_COLS)] for _ in range(N_ROWS)]
        for p in self.situation.values():
            b[p.row][p.col] = piece_2_char_wxf(p.camp, p.force)
        rows = []
        for row in b:
            space_cnt = 0
            parts = []
            for e in row:
                if e == ' ':
                    space_cnt += 1
                else:
                    if space_cnt != 0:
                        parts.append(str(space_cnt))
                        space_cnt = 0
                    parts.append(e)
            if space_cnt != 0:
                parts.append(str(space_cnt))
            rows.append(''.join(parts))
        return '/'.join(rows)

    def filter(self, camp, force):
        d = defaultdict(list)
        for p in self.situation.values():
            if p.camp == camp and p.force == force:
                d[p.col].append(p)
        return d

    def get_piece(self, camp, force_, col, row_indicator: RowIndicator = None, action=None) -> Piece:
        pieces = []
        for p in self.situation.values():
            if p.camp == camp and p.force == force_ and p.col == col:
                pieces.append(p)
        n_pieces = len(pieces)
        if n_pieces == 1:
            return pieces[0]

        rev = camp == Camp.BLACK
        pieces.sort(key=lambda x: x.row, reverse=rev)
        if row_indicator == RowIndicator.FRONT:
            assert n_pieces > 1
            return pieces[0]
        elif row_indicator == RowIndicator.MID:
            assert n_pieces == 3
            return pieces[1]
        elif row_indicator == RowIndicator.REAR:
            assert n_pieces > 1
            return pieces[-1]
        elif row_indicator == RowIndicator.SECOND:
            assert n_pieces >= 2
            return pieces[1]
        elif row_indicator == RowIndicator.THIRD:
            assert n_pieces >= 3
            return pieces[2]
        elif row_indicator == RowIndicator.FORTH:
            assert n_pieces >= 4
            return pieces[3]
        elif row_indicator == RowIndicator.FIFTH:
            assert n_pieces == 5
            return pieces[4]

        if row_indicator is None and force_ in (Force.SHI, Force.XIANG):
            if action == Action.ADVANCE:
                return pieces[-1]
            elif action == Action.RETREAT:
                return pieces[0]
        raise ValueError(f'too many pieces {force_.name} in col {col} with indicator {row_indicator}')

    def make_move(self, piece: Piece, dst):
        """

        :param piece:
        :param dst:
        :return: captured piece, check
        """
        piece_at_dst = self.piece_at(*dst)
        if not piece.can_move(self, *dst):
            raise ValueError('cannot do this')

        is_ok, captured = self.naked_move(piece, dst)
        if not is_ok:
            raise ValueError('illegal move')
        check = False
        if self.test_check(piece.camp):
            self.checked[piece.camp.opponent()] = True
            check = True
        if self.checked[piece.camp] and not self.test_check(piece.camp.opponent()):
            self.checked[piece.camp] = False
        return captured, check

    def naked_move(self, piece, dst):
        piece_at_dst = self.piece_at(*dst)
        if piece_at_dst is not None and piece_at_dst.camp == piece.camp:
            return False, None  # our own, do nothing
        if piece_at_dst is not None:  # enemy
            del self.situation[dst]
        del self.situation[(piece.col, piece.row)]  # del original pos
        piece.col = dst[0]
        piece.row = dst[1]
        self.situation[(piece.col, piece.row)] = piece
        return True, piece_at_dst

    def test_shuai_meet(self, shuai1_pos, shuai2_pos, ignore_piece=None):
        col1, row1 = shuai1_pos
        col2, row2 = shuai2_pos
        if col1 != col2:
            return False
        lb, ub = min(row1, row2), max(row1, row2)
        for r in range(lb + 1, ub):  # have any piece in between
            p = self.piece_at(col1, r)
            if p is not None and p is not ignore_piece:
                return False
        return True

    def test_draw(self):
        piece_cnt = {Camp.RED: defaultdict(int), Camp.BLACK: defaultdict(int)}
        for p in self.situation.values():
            d = piece_cnt[p.camp]
            d[p.force] += 1
        defend = {Force.XIANG, Force.SHI, Force.SHUAI}
        if set(piece_cnt[Camp.RED].keys()).issubset(defend) and set(piece_cnt[Camp.BLACK].keys()).issubset(defend):
            return True

        attack = {Force.JU, Force.MA, Force.PAO, Force.BING}
        attack_red = set(piece_cnt[Camp.RED].keys()).intersection(attack)
        red_attack_weak = not attack_red or attack_red == {Force.BING} and piece_cnt[Camp.RED][Force.BING] <= 2
        attack_black = set(piece_cnt[Camp.BLACK].keys()).intersection(attack)
        black_attack_weak = not attack_black or attack_black == {Force.BING} and piece_cnt[Camp.RED][
            Force.BING] <= 2

        red_defend = set(piece_cnt[Camp.RED].keys()).intersection(defend)
        red_defend_num = sum([n for k, n in piece_cnt[Camp.RED].items() if k in red_defend])
        red_defend_strong = red_defend_num >= 4
        black_defend = set(piece_cnt[Camp.BLACK].keys()).intersection(defend)
        black_defend_num = sum([n for k, n in piece_cnt[Camp.BLACK].items() if k in black_defend])
        black_defend_strong = black_defend_num >= 4

        if red_attack_weak and black_defend_strong and black_attack_weak and red_defend_strong:
            return True

        return False

    def test_check(self, attacker):
        enemy_shuai = self.get_shuai(attacker.opponent())
        valid_actions = self.get_valid_actions(attacker)
        for act in valid_actions:
            if (enemy_shuai.col, enemy_shuai.row) == act['dst']:
                return True
        return False

    def encode(self):
        a = np.zeros((N_ROWS, N_COLS), dtype=np.int32)
        for p in self.situation.values():
            a[p.row, p.col] = p.encode()
        return a

    @staticmethod
    def decode(arr: np.ndarray):
        rows, cols = arr.nonzero()
        sit = {}
        for col, row in zip(cols, rows):
            n = arr[row, col]
            camp, force = Piece.decode(n)
            clz = FORCE_CLZ[force]
            sit[(col, row)] = clz(camp, col, row)
        return sit


def parse_action(cmd: str, camp: Camp, board: Board):
    """中式记法，参考 https://zh.wikipedia.org/wiki/%E8%B1%A1%E6%A3%8B

    :param cmd: str, assume has normalized
    :param camp: which side
    :param board:
    :return: locations (xiangqi, dst)
    """

    cmd = cmd.strip()
    if len(cmd) == 3:
        if cmd[-1] in {ACTION_ALIAS[Action.ADVANCE], ACTION_ALIAS[Action.RETREAT]}:  # 处理如“兵七进”
            cmd = cmd + '1'
    assert len(cmd) in (4, 5)
    n = set(cmd).intersection(FORCE_ALIAS_INV)
    assert len(n) == 1
    (p), = n  # get the unique element
    force = FORCE_ALIAS_INV[p]
    i = cmd.index(p)
    assert i in (0, 1)
    prefix = cmd[i - 1] if i > 0 else None
    if prefix is not None:
        assert prefix in ROW_INDICATOR_ALIAS_INV
        prefix = ROW_INDICATOR_ALIAS_INV[prefix]
    src_col = cmd[i + 1]
    if src_col in COL_ALIAS_INV:
        src_col = COL_ALIAS_INV[src_col]
        src_col -= 1  # to internal repr
        if camp == Camp.RED:  # from right to left
            src_col, _ = toggle_view(src_col, None)
    else:  # need ref board
        assert prefix is not None
        col2pieces = board.filter(camp, force)
        if len(col2pieces) == 1:
            (col, pieces), = col2pieces.items()
            sample = pieces[0]
            assert sample.force != Force.BING and prefix in (RowIndicator.FRONT, RowIndicator.REAR) \
                   or sample.force == Force.BING
            src_col = col
        else:
            assert force == Force.BING
            if prefix is None:
                raise ValueError('undistinguishable')
            if prefix in (RowIndicator.MID, RowIndicator.THIRD, RowIndicator.FORTH):
                src_col = max(col2pieces, key=lambda k: len(col2pieces[k]))
            else:
                col_num_ge2 = {col: len(p) for col, p in col2pieces.items() if len(p) > 1}
                if len(col_num_ge2) == 1:
                    src_col = next(iter(col_num_ge2))
                else:
                    raise ValueError('undistinguishable')

    n = set(cmd).intersection(ACTION_ALIAS_INV)
    assert len(n) == 1
    (a), = n  # get the unique element
    action = ACTION_ALIAS_INV[a]
    i = cmd.index(a)
    act_param = cmd[i + 1] if i + 1 < len(cmd) else '1'
    if act_param not in COL_ALIAS_INV:
        raise ValueError('invalid action param')
    act_param = COL_ALIAS_INV[act_param]
    param_must_be_col = {(Force.JU, Action.TRAVERSE),
                         (Force.MA, Action.ADVANCE), (Force.MA, Action.RETREAT),
                         (Force.XIANG, Action.ADVANCE), (Force.XIANG, Action.RETREAT),
                         (Force.SHI, Action.ADVANCE), (Force.SHI, Action.RETREAT),
                         (Force.SHUAI, Action.TRAVERSE),
                         (Force.PAO, Action.TRAVERSE),
                         (Force.BING, Action.TRAVERSE)}

    piece = board.get_piece(camp, force, src_col, prefix, action)
    if piece is None:
        raise ValueError('piece not found')

    if (piece.force, action) in param_must_be_col:
        act_param -= 1
    dst = piece.calc_dst(action, act_param)

    return piece, dst


def infer_action_and_param(piece, dst):
    '''inference some action info given piece and destination
    :param piece:
    :param dst:
    :return:
        action, Action
        param, with piece's view
        is_col, if the param is col
    '''
    param_must_be_col = {Force.MA, Force.XIANG, Force.SHI}
    col, row = piece.with_my_view()
    dst_col, dst_row = piece.with_my_view(*dst)
    if dst_row == row:
        return Action.TRAVERSE, dst_col, True
    if dst_row < row:
        if piece.force in param_must_be_col:
            return Action.RETREAT, dst_col, True
        return Action.RETREAT, row - dst_row, False
    if dst_row > row:
        if piece.force in param_must_be_col:
            return Action.ADVANCE, dst_col, True
        return Action.ADVANCE, dst_row - row, False


def to_chinese_action(piece, dst):
    # TODO, ref board for several same pieces in a col
    act, param, is_col = infer_action_and_param(piece, dst)
    col, _ = piece.with_my_view()
    piece_col_ex = col + 1
    param_ex = param + 1 if is_col else param
    if piece.camp == Camp.RED:
        piece_col_ex = COL_ALIAS[piece_col_ex][-1]
        param_ex = COL_ALIAS[param_ex][-1]
    s = f'{piece}{piece_col_ex}{ACTION_ALIAS[act]}{param_ex}'
    return s


def parse_action_iccs(cmd: str, board: Board):
    """https://www.xqbase.com/protocol/cchess_move.htm
    ICCS board coord sys:        
               cxj
         abcdefghi
        9         9
        8         8
        7         7
        6         6
        5         5
        4         4
        3         3
      r 2         2
      y 1         1
      i 0         0
         abcdefghi

    Args:
        cmd (str): str, e.g. h2e2
        board (Board):
    Returns:
        locations (xiangqi, dst)
    """
    cmd = cmd.strip().lower()
    src, dst = parse_iccs_action(cmd)
    piece = board.piece_at(src[0], src[1])
    if piece is None:
        raise ValueError('piece not found')
    return piece, dst


def parse_iccs_action(move):
    assert len(move) == 4
    src = ICCS_ACTION_COL_MAP[move[0]], ICCS_ACTION_ROW_MAP[move[1]]
    dst = ICCS_ACTION_COL_MAP[move[2]], ICCS_ACTION_ROW_MAP[move[3]]
    return src, dst


def to_iccs_action(action: dict):
    piece = action['piece']
    dst = action['dst']
    fc = ICCS_ACTION_COL_INV_MAP[piece.col]
    fr = ICCS_ACTION_ROW_INV_MAP[piece.row]
    tc = ICCS_ACTION_COL_INV_MAP[dst[0]]
    tr = ICCS_ACTION_ROW_INV_MAP[dst[1]]
    return fc + fr + tc + tr


def get_iccs_action_space():
    actions = []
    for i in range(N_ROWS):
        for j in range(N_COLS):
            for r in range(N_ROWS):  # at same col
                if r != i:
                    actions.append((j, i, j, r))
            for c in range(N_COLS):  # at same row
                if c != j:
                    actions.append((j, i, c, i))
            for r in (-2, -1, 1, 2):  # in 2 x 2 region
                for c in (-2, -1, 1, 2):
                    c_, r_ = j + c, i + r
                    if 0 <= c_ < N_COLS and 0 <= r_ < N_ROWS:
                        actions.append((j, i, c_, r_))
    dc = ICCS_ACTION_COL_INV_MAP
    dr = ICCS_ACTION_ROW_INV_MAP
    actions = [f'{dc[j]}{dr[i]}{dc[c]}{dr[r]}' for j, i, c, r in actions]
    return actions
