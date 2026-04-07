import pygame
import sys
import threading
from xiangqi.board import Board
from xiangqi.constants import Camp, FULL_BOARD

# UI Constants
WIDTH = 540
HEIGHT = 600
MARGIN = 40
CELL_SIZE = int((WIDTH - 2 * MARGIN) / 8) # 9 columns, so 8 cells between them. 
ROWS = 10
COLS = 9

# Colors
BG_COLOR = (248, 226, 187)  # Antique Wood
LINE_COLOR = (80, 50, 20)
RED_COLOR = (210, 20, 20)
BLACK_COLOR = (20, 20, 20)
HIGHLIGHT_COLOR = (0, 200, 0, 150)
SELECT_COLOR = (0, 100, 255, 100)

# Dictionary to map pieces to Chinese strings
PIECE_CHARS = {
    Camp.RED: {
        'SHUAI': '帥',
        'SHI': '仕',
        'XIANG': '相',
        'MA': '傌',
        'JU': '俥',
        'PAO': '炮',
        'BING': '兵'
    },
    Camp.BLACK: {
        'SHUAI': '將',
        'SHI': '士',
        'XIANG': '象',
        'MA': '馬',
        'JU': '車',
        'PAO': '砲',
        'BING': '卒'
    }
}

class GuiGame:
    def __init__(self, human_camp=Camp.RED, ai_agent=None):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Chinese Chess - AlphaBeta")
        
        # Look for a system font that natively supports Chinese characters
        sys_fonts = pygame.font.get_fonts()
        chinese_font_candidates = [
            "pingfanghk", "pingfangsc", "pingfangtc", "pingfang", 
            "stheititc", "stheitisc", "stheiti", 
            "arialunicodems", "arialunicode", 
            "microsoftyahei", "simhei"
        ]
        
        self.font = None
        for font_name in chinese_font_candidates:
            if font_name in sys_fonts:
                self.font = pygame.font.SysFont(font_name, int(CELL_SIZE * 0.6))
                break
                
        # Hardcoded fallback for modern macOS just in case SysFont fails
        if self.font is None:
            try:
                self.font = pygame.font.Font("/System/Library/Fonts/PingFang.ttc", int(CELL_SIZE * 0.6))
            except:
                # Ultimate fallback
                self.font = pygame.font.SysFont(None, int(CELL_SIZE * 0.6))
            
        self.board = Board(FULL_BOARD)
        self.ai_agent = ai_agent
        self.human_camp = human_camp
        self.current_turn = Camp.RED
        
        self.selected_piece = None
        self.valid_destinations = {} 
        self.ai_thinking = False
        self.last_move = None

    def get_pixel_pos(self, col, row):
        x = MARGIN + col * CELL_SIZE
        y = MARGIN + row * CELL_SIZE
        return x, y

    def get_board_pos(self, x, y):
        col = round((x - MARGIN) / CELL_SIZE)
        row = round((y - MARGIN) / CELL_SIZE)
        if 0 <= col < COLS and 0 <= row < ROWS:
            px, py = self.get_pixel_pos(col, row)
            if (x - px)**2 + (y - py)**2 <= (CELL_SIZE / 2)**2:
                return col, row
        return None, None

    def draw_board(self):
        self.screen.fill(BG_COLOR)
        
        # Horizontal lines
        for row in range(ROWS):
            pygame.draw.line(self.screen, LINE_COLOR, 
                             self.get_pixel_pos(0, row), 
                             self.get_pixel_pos(COLS - 1, row), 2)
                             
        # Vertical lines (broken by river)
        for col in range(COLS):
            pygame.draw.line(self.screen, LINE_COLOR, 
                             self.get_pixel_pos(col, 0), self.get_pixel_pos(col, 4), 2)
            pygame.draw.line(self.screen, LINE_COLOR, 
                             self.get_pixel_pos(col, 5), self.get_pixel_pos(col, 9), 2)
                             
        # Connect edge lines through river
        pygame.draw.line(self.screen, LINE_COLOR, self.get_pixel_pos(0, 4), self.get_pixel_pos(0, 5), 2)
        pygame.draw.line(self.screen, LINE_COLOR, self.get_pixel_pos(COLS - 1, 4), self.get_pixel_pos(COLS - 1, 5), 2)

        # Cross diagonals for palaces (Black Top, Red Bottom)
        pygame.draw.line(self.screen, LINE_COLOR, self.get_pixel_pos(3, 0), self.get_pixel_pos(5, 2), 2)
        pygame.draw.line(self.screen, LINE_COLOR, self.get_pixel_pos(5, 0), self.get_pixel_pos(3, 2), 2)
        
        pygame.draw.line(self.screen, LINE_COLOR, self.get_pixel_pos(3, 7), self.get_pixel_pos(5, 9), 2)
        pygame.draw.line(self.screen, LINE_COLOR, self.get_pixel_pos(5, 7), self.get_pixel_pos(3, 9), 2)

    def draw_pieces(self):
        for piece in self.board.situation.values():
            x, y = self.get_pixel_pos(piece.col, piece.row)
            color = RED_COLOR if piece.camp == Camp.RED else BLACK_COLOR
            
            # Draw piece cleanly
            pygame.draw.circle(self.screen, (250, 240, 220), (x, y), int(CELL_SIZE * 0.45))
            pygame.draw.circle(self.screen, color, (x, y), int(CELL_SIZE * 0.45), 2)
            
            # Select Highlight
            if self.selected_piece and piece.col == self.selected_piece.col and piece.row == self.selected_piece.row:
                s = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                pygame.draw.circle(s, SELECT_COLOR, (CELL_SIZE//2, CELL_SIZE//2), int(CELL_SIZE * 0.45))
                self.screen.blit(s, (x - CELL_SIZE//2, y - CELL_SIZE//2))

            char = PIECE_CHARS[piece.camp].get(piece.force.name, "?")
            text_surface = self.font.render(char, True, color)
            text_rect = text_surface.get_rect(center=(x, y))
            self.screen.blit(text_surface, text_rect)

    def draw_highlights(self):
        # Draw last move indicator
        if self.last_move:
            src, dst = self.last_move
            for (col, row) in [src, dst]:
                x, y = self.get_pixel_pos(col, row)
                s = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                pygame.draw.circle(s, (255, 165, 0, 100), (CELL_SIZE//2, CELL_SIZE//2), int(CELL_SIZE * 0.45))
                self.screen.blit(s, (x - CELL_SIZE//2, y - CELL_SIZE//2))
        
        # Draw valid destinations
        for dst in self.valid_destinations:
            x, y = self.get_pixel_pos(*dst)
            s = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
            pygame.draw.circle(s, HIGHLIGHT_COLOR, (CELL_SIZE//2, CELL_SIZE//2), int(CELL_SIZE * 0.3))
            self.screen.blit(s, (x - CELL_SIZE//2, y - CELL_SIZE//2))

    def handle_click(self, pos):
        if self.ai_thinking or self.current_turn != self.human_camp:
            return
            
        col, row = self.get_board_pos(*pos)
        if col is None:
            return

        piece = self.board.piece_at(col, row)
        
        if self.selected_piece:
            if (col, row) in self.valid_destinations:
                src_pos = (self.selected_piece.col, self.selected_piece.row)
                dst = (col, row)
                
                # Apply move to real board
                self.board.make_move(self.selected_piece, dst)
                self.last_move = (src_pos, dst)
                self.current_turn = self.current_turn.opponent()
                
                self.selected_piece = None
                self.valid_destinations = {}
                
                # Check if it was checkmate
                if not self.board.get_final_valid_actions(self.current_turn):
                    print(f"CHECKMATE! {self.human_camp.name} Wins!")
                    return
                
                if self.ai_agent:
                    self.ai_thinking = True
                    threading.Thread(target=self.ai_worker, daemon=True).start()
            
            elif piece and piece.camp == self.human_camp:
                self.selected_piece = piece
                actions = self.board.get_final_valid_actions(self.human_camp)
                self.valid_destinations = {a['dst'] for a in actions if a['piece'].col == piece.col and a['piece'].row == piece.row}
            else:
                self.selected_piece = None
                self.valid_destinations = {}
                
        elif piece and piece.camp == self.human_camp:
            self.selected_piece = piece
            actions = self.board.get_final_valid_actions(self.human_camp)
            self.valid_destinations = {a['dst'] for a in actions if a['piece'].col == piece.col and a['piece'].row == piece.row}

    def ai_worker(self):
        action = self.ai_agent.get_action(self.board, self.current_turn)
        
        if action:
            src_pos = (action['piece'].col, action['piece'].row)
            dst = action['dst']
            
            self.board.make_move(action['piece'], dst)
            
            self.last_move = (src_pos, dst)
            self.current_turn = self.current_turn.opponent()
        else:
            print(f"CHECKMATE! {self.human_camp.name} Wins!")
            
        self.ai_thinking = False

    def run(self):
        clock = pygame.time.Clock()
        
        # If the AI starts First, trigger it
        if self.current_turn != self.human_camp and self.ai_agent:
            self.ai_thinking = True
            threading.Thread(target=self.ai_worker, daemon=True).start()

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)

            self.draw_board()
            self.draw_highlights()
            self.draw_pieces()
            
            if self.ai_thinking:
                text_surface = self.font.render("AI Thinking...", True, RED_COLOR)
                self.screen.blit(text_surface, (10, 10))

            pygame.display.flip()
            clock.tick(60)
