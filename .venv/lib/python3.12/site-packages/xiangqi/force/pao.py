from constants import Camp, Force, N_COLS, N_ROWS
from piece import Piece


class Pao(Piece):
    def __init__(self, camp: Camp, col: int, row: int):
        super().__init__(camp, Force.PAO, col, row)

    def traverse(self, col):
        col, _ = self.with_my_view(col, None)
        assert self.col != col
        return col, self.row

    def advance(self, d):
        row = self.row + self.heading * d
        assert 0 <= row <= 9
        return self.col, row

    def retreat(self, d):
        row = self.row - self.heading * d
        assert 0 <= row <= 9
        return self.col, row

    def get_valid_pos(self, board_):

        def op_at_row(p, x):
            return p.col, x

        def op_at_col(p, x):
            return x, p.row

        poses = []
        ranges = [range(self.row + 1, N_ROWS),  # to bottom
                  range(self.row - 1, -1, -1),  # to top
                  range(self.col + 1, N_COLS),  # to right
                  range(self.col - 1, -1, -1)]  # to left
        ops = [op_at_row, op_at_row, op_at_col, op_at_col]
        for line, op in zip(ranges, ops):
            bed = False
            for x in line:
                c, r = op(self, x)
                if self.will_cause_shuai_meet(board_, c, r):
                    continue
                p = board_.piece_at(c, r)
                if not bed:
                    if p is None:
                        poses.append((c, r))
                    else:
                        bed = True
                        continue
                else:
                    if p is None:
                        continue
                    if p.camp != self.camp:
                        poses.append((c, r))
                    break
        return poses
