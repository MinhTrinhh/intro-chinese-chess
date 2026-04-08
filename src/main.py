from src.agents.alphabeta_agent import AlphaBetaAgent
from src.agents.random_agent import RandomAgent
from src.engine.game import Game
from src.ui.gui import GuiGame
from xiangqi.constants import Camp

import sys

def main():
    print("Welcome to Xiangqi AI Assignment!")
    print("1. Play Human (Red) vs Alpha-Beta (Black) in GUI")
    print("2. Simulate RandomAgent (Black) vs Alpha-Beta (Red) in Match Log") 
    choice = input("Enter choice (1 or 2): ").strip()

    agent_level = int(input("Choose agent level [from 1 to 4]:").strip())

    if agent_level not in range(1, 5):
        print("Invalid Level")
        sys.exit()
    
    if choice == '1':
        up = input("You want to go first [y/n]:").strip()

        black_ai = AlphaBetaAgent(depth=agent_level)

        if up == 'y':
            game = GuiGame(human_camp=Camp.RED, ai_agent=black_ai)
            game.run()
        
        elif up == 'n':
            game = GuiGame(human_camp=Camp.BLACK, ai_agent=black_ai)
            game.run()
        
        else:
            print("Invalid choice, exiting.")
            sys.exit()


    elif choice == '2':
        sec_choice = input("AlphaBeta goes first: 1\nRandom goes first: 2\nEnter:").strip()

        red_ai = AlphaBetaAgent(depth=agent_level)
        black_ai = RandomAgent()

        if sec_choice == '1':
            game = Game(red_ai, black_ai)
            game.play("match_log.html")
            print("Match complete! Check match_log.html.")
        
        elif sec_choice == '2':
            game = Game(black_ai, red_ai)
            game.play("match_log.html")
            print("Match complete! Check match_log.html.")
        
        else:
            print("Invalid choice, exiting.")
            sys.exit()

    else:
        print("Invalid choice, exiting.")
        sys.exit()

if __name__ == '__main__':
    main()