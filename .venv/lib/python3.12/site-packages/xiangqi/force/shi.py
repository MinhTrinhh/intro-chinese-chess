from constants import Camp, Force
from piece import Piece


class Shi(Piece):
    def __init__(self, camp: Camp, col: int, row: int):
        super().__init__(camp, Force.SHI, col, row)

    def traverse(self, col):
        raise ValueError('cannot do this')

    def advance(self, col):
        col, _ = self.with_my_view(col, None)
        d = abs(self.col - col)
        assert d == 1
        row = self.row + self.heading * 1
        _, row_in_my_view = self.with_my_view(None, row)
        assert 0 <= row_in_my_view <= 2
        return col, row

    def retreat(self, col):
        col, _ = self.with_my_view(col, None)
        d = abs(self.col - col)
        assert d == 1
        row = self.row - self.heading * 1
        _, row_in_my_view = self.with_my_view(None, row)
        assert 0 <= row_in_my_view <= 2
        return col, row

    def get_valid_pos(self, board_):
        black_palace = {(3, 0): [(4, 1)], (5, 0): [(4, 1)],
                        (4, 1): [(3, 0), (5, 0), (3, 2), (5, 2)],
                        (3, 2): [(4, 1)], (5, 2): [(4, 1)]}
        red_palace = {(3, 9): [(4, 8)], (5, 9): [(4, 8)],
                      (4, 8): [(3, 9), (5, 9), (3, 7), (5, 7)],
                      (3, 7): [(4, 8)], (5, 7): [(4, 8)]}

        palaces = {Camp.BLACK: black_palace, Camp.RED: red_palace}
        palace = palaces[self.camp]
        assert (self.col, self.row) in palace
        test_pos = palace[(self.col, self.row)]
        pos = []
        for c, r in test_pos:
            p = board_.piece_at(c, r)
            if p is None or p.camp != self.camp:
                if not self.will_cause_shuai_meet(board_, c, r):
                    pos.append((c, r))
        return pos
