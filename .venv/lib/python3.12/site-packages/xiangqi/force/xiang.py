from constants import Camp, Force, N_COLS, N_ROWS
from piece import Piece


class Xiang(Piece):
    def __init__(self, camp: Camp, col: int, row: int):
        super().__init__(camp, Force.XIANG, col, row)

    def traverse(self, col):
        raise ValueError('cannot do this')

    def advance(self, col):
        col, _ = self.with_my_view(col, None)
        d = abs(self.col - col)
        assert d == 2
        row = self.row + self.heading * 2
        _, row_in_my_view = self.with_my_view(None, row)
        assert 0 <= row_in_my_view <= 4
        return col, row

    def retreat(self, col):
        col, _ = self.with_my_view(col, None)
        d = abs(self.col - col)
        assert d == 2
        row = self.row - self.heading * 2
        _, row_in_my_view = self.with_my_view(None, row)
        assert 0 <= row_in_my_view <= 4
        return col, row

    def get_valid_pos(self, board_):
        test_pos = [(+2, +2), (+2, -2), (-2, +2), (-2, -2)]
        handicap = [(+1, +1), (+1, -1), (-1, +1), (-1, -1)]
        poses = []

        for pos, handi in zip(test_pos, handicap):
            handi_p = board_.piece_at(self.col + handi[0], self.row + handi[1])
            if handi_p is not None:
                continue
            col, row = self.col + pos[0], self.row + pos[1]
            if not (0 <= col < N_COLS and 0 <= row < N_ROWS):
                continue
            _, row_in_my_view = self.with_my_view(col, row)
            if not 0 <= row_in_my_view <= 4:  # cannot cross river
                continue
            p = board_.piece_at(col, row)
            if p is None or p.camp != self.camp:
                if not self.will_cause_shuai_meet(board_, col, row):
                    poses.append((col, row))
        return poses
