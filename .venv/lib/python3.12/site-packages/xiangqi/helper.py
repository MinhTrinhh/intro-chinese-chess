from constants import N_COLS, N_ROWS


def toggle_view(col=None, row=None):
    col = N_COLS - 1 - col if col is not None else None
    row = N_ROWS - 1 - row if row is not None else None
    return col, row
