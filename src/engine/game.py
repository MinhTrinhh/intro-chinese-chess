from xiangqi.board import Board
from xiangqi.constants import FULL_BOARD, Camp

class Game:
    RED_PIECES = {"俥", "傌", "相", "仕", "帥", "炮", "兵"}
    BLACK_PIECES = {"車", "馬", "象", "士", "將", "砲", "卒"}

    def __init__(self, red_agent, black_agent):
        self.board = Board(FULL_BOARD)
        self.agents = {
            Camp.RED: red_agent,
            Camp.BLACK: black_agent
        }
        self.current_turn = Camp.RED

    def _board_to_html(self):
        board_str = str(self.board)
        html_parts = []

        for ch in board_str:
            if ch in self.RED_PIECES:
                html_parts.append(f"<span style=\"color:red\">{ch}</span>")
            elif ch in self.BLACK_PIECES:
                html_parts.append(f"<span style=\"color:black\">{ch}</span>")
            else:
                html_parts.append(ch)

        return "".join(html_parts)

    def play(self, log_path="match_log.html"):
        turn_num = 1
        print(f"Match started! Writing game log to {log_path}...")

        with open(log_path, "w", encoding="utf-8") as f:
            f.write("<html>\n<body>\n<pre>\n")
            
            # Print initial board state
            print(f"{'='*40}", file=f)
            print("INITIAL BOARD", file=f)
            board_str = self._board_to_html()
            print(board_str, file=f)
            print(f"{'='*40}", file=f)

            while True:
                print(f"Turn {turn_num}: {self.current_turn.name}", file=f)
    
                agent = self.agents[self.current_turn]
                action = agent.get_action(self.board, self.current_turn)
    
                if action is None:
                    print(f"CHECKMATED: {self.current_turn.opponent().name} wins", file=f)
                    break
    
                piece = action['piece']
                dst = action['dst']
    
                print(f"{self.current_turn.name} moves {piece.force.name} to (col: {dst[0]}, row: {dst[1]})", file=f)
    
                captured, check = self.board.make_move(piece, dst)
    
                if captured:
                    print(f"CAPTURED: {captured.force.name}", file=f)
    
                if check:
                    print("CHECK", file=f)
    
                if captured and captured.force.name == "SHUAI":
                    print(f"CAPTURED GENERAL wins", file=f)
                    break
    
                if self.board.test_draw():
                    print("DRAW", file=f)
                    break
    
                # Print board state AFTER the move
                print(f"{'='*40}", file=f)
                board_str = self._board_to_html()
                print(board_str, file=f)
                print(f"{'='*40}\n", file=f)

                self.current_turn = self.current_turn.opponent()
                if self.current_turn == Camp.RED:
                    turn_num += 1
            f.write("</pre>\n</body>\n</html>\n")
                    
        print("Match finished!")
