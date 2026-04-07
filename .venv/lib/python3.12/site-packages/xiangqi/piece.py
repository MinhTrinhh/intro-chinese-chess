import os

from constants import Camp, Force, Action, N_COLS, N_ROWS
from helper import toggle_view

APPEAR_BLACK = ''
APPEAR_RED = ''
ENDC = ''
APPEAR_CHECK = ''

if os.name == 'posix':
    APPEAR_BLACK = '\033[1;30;47m'
    APPEAR_RED = '\033[1;31;47m'
    ENDC = '\033[0m'
    APPEAR_CHECK = '\033[1;33;41m'

PIECE_CHARS = '將士象馬車砲卒帥仕相傌俥炮兵'
PIECE_CHARS_WXF = 'kabnrcpKABNRCP'
PLACE_CHARS = '＋Ｘ'

POINT_OUT_CHECK = APPEAR_CHECK + '将！！！' + ENDC

CAMP_ALIAS = {Camp.BLACK: 'b', Camp.RED: 'r'}
CAMP_ALIAS_INV = {v: k for k, v in CAMP_ALIAS.items()}

FORCE_ALIAS = {
    Force.SHUAI: tuple('将帅將帥kK'),
    Force.SHI: tuple('士仕aA'),
    Force.XIANG: tuple('象相bB'),
    Force.MA: tuple('马㐷馬傌nN'),
    Force.JU: tuple('车伡車俥rR'),
    Force.PAO: tuple('炮砲cC'),
    Force.BING: tuple('兵卒pP'),
}
FORCE_ALIAS_INV = {e: k for k, v in FORCE_ALIAS.items() for e in v}

COL_ALIAS = {
    1: tuple('1１一'),
    2: tuple('2２二'),
    3: tuple('3３三'),
    4: tuple('4４四'),
    5: tuple('5５五'),
    6: tuple('6６六'),
    7: tuple('7７七'),
    8: tuple('8８八'),
    9: tuple('9９九')
}
COL_ALIAS_INV = {e: k for k, v in COL_ALIAS.items() for e in v}


def piece_2_char(camp: Camp, force: Force):
    index = 7 * (camp.value - 1) + force.value - 1
    return PIECE_CHARS[index]


def piece_2_char_wxf(camp: Camp, force: Force):
    index = 7 * (camp.value - 1) + force.value - 1
    return PIECE_CHARS_WXF[index]


def recog_piece(piece: str):
    assert piece in PIECE_CHARS
    assert len(piece) == 1
    idx = PIECE_CHARS.index(piece)
    q, r = divmod(idx, len(Force))
    camp = Camp(q + 1)
    force = Force(r + 1)
    return camp, force


class Piece:
    def __init__(self, camp: Camp, force: Force, col: int, row: int):
        """xiangqi 术语参考 http://wxf.ca/xq/computer/XIANGQI_TERMS_IN_ENGLISH.pdf

        :param col: file
        :param row: rank
        :param camp: red or black
        :param force: piece type
        """
        self.col = col
        self.row = row
        self.camp = camp
        self.force = force
        self.heading = -1 if camp == Camp.RED else 1

    def __str__(self):
        c = piece_2_char(self.camp, self.force)
        appear = APPEAR_RED if self.camp == Camp.RED else APPEAR_BLACK
        c = appear + c + ENDC
        return c

    def can_move(self, board_, col, row):
        assert 0 <= col < N_COLS
        assert 0 <= row < N_ROWS
        pos = self.get_valid_pos(board_)
        return (col, row) in pos

    def calc_dst(self, action, act_param):
        """get the dst position

        :param action: with self perspective
        :param act_param: with self perspective
        :return: (col, row), in board coordinate system
        """
        d_fn = {Action.TRAVERSE: lambda x: self.traverse(x),
                Action.ADVANCE: lambda x: self.advance(x),
                Action.RETREAT: lambda x: self.retreat(x)}
        fn = d_fn[action]
        col, row = fn(act_param)
        return col, row

    def get_valid_pos(self, board_):
        raise NotImplementedError('left to subclass')

    def traverse(self, col):
        raise NotImplementedError('left to subclass')

    def advance(self, d):
        raise NotImplementedError('left to subclass')

    def retreat(self, d):
        raise NotImplementedError('left to subclass')

    def to_abs_col(self, col):
        m = (N_COLS - 1) // 2
        return self.heading * (col - m) + m

    def with_my_view(self, col=None, row=None):
        col = self.col if col is None else col
        row = self.row if row is None else row
        if self.camp == Camp.RED:
            return toggle_view(col, row)
        return col, row

    def move_to(self, board_, col, row):
        is_ok, captured = board_.naked_move(self, (col, row))
        if not is_ok or captured is not None:
            raise ValueError('dst pos nonempty')

    def will_cause_shuai_meet(self, board_, action_col, action_row):
        shuai1 = board_.get_shuai(self.camp)
        shuai2 = board_.get_shuai(self.camp.opponent())
        assert shuai1 is not None
        assert shuai2 is not None
        if shuai1.col != shuai2.col:
            return False
        if shuai1.col == action_col:
            return False
        return board_.test_shuai_meet((shuai1.col, shuai1.row), (shuai2.col, shuai2.row), ignore_piece=self)

    def encode(self):
        return self.camp.value * 10 + self.force.value

    @staticmethod
    def decode(num):
        camp, force = divmod(num, 10)
        return Camp(camp), Force(force)
