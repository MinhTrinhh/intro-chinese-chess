from constants import Camp, Force, N_COLS, N_ROWS
from piece import Piece


class Bing(Piece):
    def __init__(self, camp: Camp, col: int, row: int):
        super().__init__(camp, Force.BING, col, row)

    def traverse(self, col):
        col, row = self.with_my_view(col, self.row)
        assert abs(self.col - col) == 1
        assert 4 < row <= 9
        return col, self.row

    def advance(self, d):
        assert d == 1
        return self.col, self.row + self.heading * 1

    def retreat(self, d):
        raise ValueError('cannot do this')

    def is_cross_river(self):
        col, row = self.with_my_view()
        return row > 4

    def get_valid_pos(self, board_):
        test_pos = [(0, 1)]
        if self.is_cross_river():
            test_pos.extend([(1, 0), (-1, 0)])
        poses = []
        for pos in test_pos:
            col, row = self.col + pos[0], self.row + self.heading * pos[1]
            if not (0 <= col < N_COLS and 0 <= row < N_ROWS):
                continue
            p = board_.piece_at(col, row)
            if p is None or p.camp != self.camp:
                if not self.will_cause_shuai_meet(board_, col, row):
                    poses.append((col, row))
        return poses
