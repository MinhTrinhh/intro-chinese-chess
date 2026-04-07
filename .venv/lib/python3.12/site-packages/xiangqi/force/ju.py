from constants import Camp, Force, N_COLS, N_ROWS
from piece import Piece


class Ju(Piece):
    def __init__(self, camp: Camp, col: int, row: int):
        super().__init__(camp, Force.JU, col, row)

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
        pos = []
        for r in range(self.row + 1, N_ROWS):  # to bottom
            p = board_.piece_at(self.col, r)
            if p is not None:
                if p.camp != self.camp:
                    pos.append((self.col, r))
                break
            pos.append((self.col, r))
        for r in range(self.row - 1, -1, -1):  # to top
            p = board_.piece_at(self.col, r)
            if p is not None:
                if p.camp != self.camp:
                    pos.append((self.col, r))
                break
            pos.append((self.col, r))
        for c in range(self.col + 1, N_COLS):  # to right
            if self.will_cause_shuai_meet(board_, c, self.row):
                continue
            p = board_.piece_at(c, self.row)
            if p is not None:
                if p.camp != self.camp:
                    pos.append((c, self.row))
                break
            pos.append((c, self.row))
        for c in range(self.col - 1, -1, -1):  # to left
            if self.will_cause_shuai_meet(board_, c, self.row):
                continue
            p = board_.piece_at(c, self.row)
            if p is not None:
                if p.camp != self.camp:
                    pos.append((c, self.row))
                break
            pos.append((c, self.row))
        return pos
