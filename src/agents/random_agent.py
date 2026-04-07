import random

class RandomAgent:
    def get_action(self, board, camp):

        actions = board.get_final_valid_actions(camp)

        if not actions:
            return None
        
        return random.choice(actions)
    