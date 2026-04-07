from xiangqi.board import Board
from xiangqi.constants import FULL_BOARD, Camp

class Game:
    def __init__(self, red_agent, black_agent):
        self.board = Board(FULL_BOARD)
        self.agents = {
            Camp.RED: red_agent,
            Camp.BLACK: black_agent
        }
        self.current_turn = Camp.RED

    def play(self, log_path="match_log.html"):
        turn_num = 1
        print(f"Match started! Writing game log to {log_path}...")

        with open(log_path, "w", encoding="utf-8") as f:
            f.write("<html>\n<body>\n<pre>\n")
            
            # Print initial board state
            print(f"{'='*40}", file=f)
            print("INITIAL BOARD", file=f)
            board_str = str(self.board)
            board_str = board_str.replace("\x1b[1;31;47m", "<span style=\"color:red\">")
            board_str = board_str.replace("\x1b[1;30;47m", "<span style=\"color:black\">")
            board_str = board_str.replace("\x1b[0m", "</span>")
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
                board_str = str(self.board)
                board_str = board_str.replace("\x1b[1;31;47m", "<span style=\"color:red\">")
                board_str = board_str.replace("\x1b[1;30;47m", "<span style=\"color:black\">")
                board_str = board_str.replace("\x1b[0m", "</span>")
                print(board_str, file=f)
                print(f"{'='*40}\n", file=f)

                self.current_turn = self.current_turn.opponent()
                if self.current_turn == Camp.RED:
                    turn_num += 1
            f.write("</pre>\n</body>\n</html>\n")
                    
        print("Match finished!")
