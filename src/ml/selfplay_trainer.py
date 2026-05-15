"""
Self-Play Trainer: Generate training data via multiprocessing.

Process:
  1. Multiple worker processes play games in parallel
  2. Each worker: Red (depth=red_depth) vs Black (depth=black_depth)
  3. Save board states as FEN (lightweight) + outcome label
  4. After collection, convert FEN → numpy int8 for storage

Output format:
  List of (board_array, label) tuples saved as .pkl
  - board_array: np.ndarray(shape=(90,), dtype=np.int8)
  - label: np.int8 with values {-1, 0, +1}
  
  When training, convert to torch float32 using: load_training_batch()
  Benefits: 8x smaller file size, faster load, less RAM, scales to millions of samples
"""

from collections import Counter
from multiprocessing import Pool
import pickle 
import torch
import numpy as np
from pathlib import Path
from tqdm import tqdm

from xiangqi.board import Board
from xiangqi.constants import FULL_BOARD, Camp, Force
from src.agents.alphabeta_agent import AlphaBetaAgent
from src.agents.random_agent import RandomAgent
from src.ml.board_encoder import fen_to_tensor
from src.evaluation.heuristics import escape_loop, add_cache
import random
import argparse

  

RANDOM_OPENING_MOVES = 4


def _make_rng(base_seed: int | None, game_id: int) -> random.Random:
    """Create a deterministic per-game RNG."""
    if base_seed is None:
        base_seed = 42
    return random.Random(base_seed + game_id)


def play_one_game(args):
    game_id, red_depth, black_depth, base_seed = args
    rng = _make_rng(base_seed, game_id)
    
    # Create agents in worker process
    red_agent = AlphaBetaAgent(depth=red_depth, use_book=False)
    black_agent = AlphaBetaAgent(depth=black_depth, use_book=False)
    
    board = Board(FULL_BOARD)
    agents = {Camp.RED: red_agent, Camp.BLACK: black_agent}
    current_turn = Camp.RED
    history = []
    
    board_fens = []  # Lightweight FEN encoding
    move_count = 0
    max_moves = 400
    outcome = 'draw'
    
    # Position repetition tracking
    position_counts = Counter()
    
    while move_count < max_moves:
        fen_before = board.board_to_fen1()
        position_counts[fen_before] += 1
        
        # Detect draw by repetition
        if position_counts[fen_before] > 3:
            outcome = 'draw'
            break
        
        # Save FEN before move
        board_fens.append(fen_before)

        # Select action: random opening for first few moves, then agents
        if move_count < RANDOM_OPENING_MOVES:
            actions = board.get_final_valid_actions(current_turn)
            actions = escape_loop(history, actions)
            if not actions:
                winner = current_turn.opponent()
                outcome = 'red_win' if winner == Camp.RED else 'black_win'
                break
            action = rng.choice(actions)
        else:
            agent = agents[current_turn]
            action = agent.get_action(board, current_turn)
        
        # Checkmate
        if action is None:
            winner = current_turn.opponent()
            outcome = 'red_win' if winner == Camp.RED else 'black_win'
            break
        
        # Make move
        piece = action['piece']
        dst = action['dst']
        add_cache(history, action)
        captured, check = board.make_move(piece, dst)
        
        # Check if general captured
        if captured and captured.force.name == "SHUAI":
            outcome = 'red_win' if current_turn == Camp.RED else 'black_win'
        
        # Check for draw
        elif board.test_draw():
            outcome = 'draw'
        
        # Stop if game ended
        if (captured and captured.force.name == "SHUAI") or board.test_draw():
            break
        
        current_turn = current_turn.opponent()
        move_count += 1
    
    # Timeout
    if move_count >= max_moves:
        outcome = 'draw'
    
    # Convert outcome to label (perspective: RED)
    if outcome == 'red_win':
        label = 1
    elif outcome == 'black_win':
        label = -1
    else:  # draw or timeout
        label = 0
    
    # Encode FEN → tensor + label
    samples = []
    for fen in board_fens:
        try:
            tensor = fen_to_tensor(fen)  # Returns np.ndarray(shape=(90,), dtype=np.int8)
            label_int = np.int8(label)  # Convert label to int8
            samples.append((tensor, label_int))
        except Exception as e:
            # Skip malformed FEN
            continue
    
    return samples

def play_one_game_debug(args):
    game_id, red_depth, black_depth, base_seed = args
    rng = _make_rng(base_seed, game_id)

    # Create agents
    red_agent = AlphaBetaAgent(depth=red_depth, use_book=False)
    black_agent = AlphaBetaAgent(depth=black_depth, use_book=False)
    # black_agent = RandomAgent()

    board = Board(FULL_BOARD)
    agents = {Camp.RED: red_agent,Camp.BLACK: black_agent}

    current_turn = Camp.RED
    history = []
    board_fens = []
    move_count = 0
    max_moves = 400
    outcome = 'draw'

    # Logging setup
    log_dir = Path("logs/selfplay_debug")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"selfplay_game_{game_id + 1}.html"

    with open(log_path, 'w', encoding='utf-8') as log_file:
        log_file.write("""
        <html>
        <head>
            <title>Self-Play Debug Game</title>
            <style>
                body {
                    font-family: Arial;
                    padding: 20px;
                }
                table {
                    border-collapse: collapse;
                    width: 100%;
                }
                th, td {
                    border: 1px solid black;
                    padding: 8px;
                    vertical-align: top;
                }
                th {
                    background-color: #f0f0f0;
                }
                pre {
                    white-space: pre-wrap;
                    word-break: break-word;
                }
            </style>
        </head>
        <body>
        """)

        log_file.write(f"<h1>Self-Play Debug Game {game_id + 1}</h1>")
        log_file.write(f"<p><b>Red depth:</b> {red_depth}</p>")
        log_file.write(f"<p><b>Black depth:</b> {black_depth}</p>")
        log_file.write(f"<p><b>Random opening moves:</b> {RANDOM_OPENING_MOVES}</p>")

        log_file.write("""
        <table>
            <tr>
                <th>Move</th>
                <th>Turn</th>
                <th>Action</th>
                <th>FEN Before</th>
                <th>FEN After</th>
                <th>Event</th>
            </tr>
        """)

        from collections import Counter
        position_counts = Counter()

        consecutive_checks = {Camp.RED: 0, Camp.BLACK: 0}
        
        while move_count < max_moves:
            fen_before = board.board_to_fen1()
            position_counts[fen_before] += 1

            if position_counts[fen_before] > 3:
                outcome = 'draw'
                event_text = f"Draw by repetition (position repeated {position_counts[fen_before]} times)"
                log_file.write(f"""
                <tr>
                    <td>{move_count + 1}</td>
                    <td>{current_turn.name}</td>
                    <td>N/A</td>
                    <td><pre>{fen_before}</pre></td>
                    <td>N/A</td>
                    <td>{event_text}</td>
                </tr>
                """)
                break

            # Save FEN before move
            board_fens.append(fen_before)
            event_text = ""

            # Random opening
            if move_count < RANDOM_OPENING_MOVES:
                actions = board.get_final_valid_actions(current_turn)
                actions = escape_loop(history, actions)

                if not actions:
                    winner = current_turn.opponent()
                    outcome = (
                        'red_win'
                        if winner == Camp.RED
                        else 'black_win'
                    )
                    event_text = "No legal actions available"
                    log_file.write(f"""
                    <tr>
                        <td>{move_count + 1}</td>
                        <td>{current_turn.name}</td>
                        <td>N/A</td>
                        <td><pre>{fen_before}</pre></td>
                        <td>N/A</td>
                        <td>{event_text}</td>
                    </tr>
                    """)
                    break
                action = rng.choice(actions)
                event_text = "Random opening move"

            else:
                agent = agents[current_turn]
                action = agent.get_action(board, current_turn)
                event_text = "Agent move"

            # Checkmate / no move
            if action is None:
                winner = current_turn.opponent()
                outcome = (
                    'red_win'
                    if winner == Camp.RED
                    else 'black_win'
                )
                event_text += " | Agent returned None"
                log_file.write(f"""
                <tr>
                    <td>{move_count + 1}</td>
                    <td>{current_turn.name}</td>
                    <td>None</td>
                    <td><pre>{fen_before}</pre></td>
                    <td>N/A</td>
                    <td>{event_text}</td>
                </tr>
                """)

                break

            # Make move
            piece = action['piece']
            dst = action['dst']
            add_cache(history, action)
            captured, check = board.make_move(piece, dst)
            fen_after = board.board_to_fen1()

            # Check if general captured
            if captured and captured.force.name == "SHUAI":
                outcome = (
                    'red_win'
                    if current_turn == Camp.RED
                    else 'black_win'
                )
                event_text += " | General captured"

            # Draw detection
            elif board.test_draw():
                outcome = 'draw'
                event_text += " | Draw detected"
            # Check
            if check:
                event_text += " | Check"
            # Logging
            log_file.write(f"""
            <tr>
                <td>{move_count + 1}</td>
                <td>{current_turn.name}</td>
                <td>{piece} → {dst}</td>
                <td><pre>{fen_before}</pre></td>
                <td><pre>{fen_after}</pre></td>
                <td>{event_text}</td>
            </tr>
            """)
            # Stop if game ended
            if (
                (captured and captured.force.name == "SHUAI")
                or board.test_draw()
            ):
                break
            current_turn = current_turn.opponent()
            move_count += 1

        # Timeout
        if move_count >= max_moves:
            outcome = 'draw'

        log_file.write("</table>")
        log_file.write(f"<h2>Final Outcome: {outcome}</h2>")
        log_file.write("</body></html>")

    # Convert outcome to label (RED perspective)
    if outcome == 'red_win':
        label = 1
    elif outcome == 'black_win':
        label = -1
    else:
        label = 0

    # Encode samples
    samples = []
    for fen in board_fens:
        try:
            tensor = fen_to_tensor(fen)  # Returns np.ndarray(shape=(90,), dtype=np.int8)
            label_int = np.int8(label)  # Convert label to int8
            samples.append((tensor, label_int))
        except Exception:
            # Skip malformed FEN
            continue
    return samples

def collect_parallel(n_games=100, red_depth=3, black_depth=3, n_workers=8, base_seed: int | None = None):
    """Collect self-play data in parallel using multiprocessing."""

    print(f"\n[Self-Play Collection]")
    print(f"  Games: {n_games}")
    print(f"  Red depth: {red_depth}, Black depth: {black_depth}")
    print(f"  Workers: {n_workers}")
    print(f"  Seed: {base_seed if base_seed is not None else 42}")
    print("-" * 50)
    
    # Prepare arguments for workers
    args_list = [
        (game_id, red_depth, black_depth, base_seed)
        for game_id in range(n_games) 
    ]
    
    # Run games in parallel
    all_samples = []
    with Pool(processes=n_workers) as pool:
        results = tqdm(
            pool.imap_unordered(play_one_game, args_list),
            total=n_games,
            desc="Playing games"
        )
        
        for game_samples in results:
            all_samples.extend(game_samples) # Flatten list of lists
    print(f"\n✓ Collected {len(all_samples)} board states from {n_games} games")
    return all_samples


def save_dataset(dataset, path="data/training_data.pkl"):
    """
    Save dataset as pickle file.
    Data format: List of (X, y) tuples where:
      X: np.ndarray(shape=(90,), dtype=np.int8) - board state
      y: np.int8 - outcome label (-1, 0, +1)
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'wb') as f:
        pickle.dump(dataset, f)
    
    print(f"✓ Saved {len(dataset)} samples to {path}")
    print(f"  File size: {path.stat().st_size / (1024*1024):.2f} MB")

def test_selfplay_debug(n_games=8, red_depth=3, black_depth=3, n_workers=8, base_seed: int | None = None):
    print("\n[TEST] Self-Play Data Collection (Quick Test)")
    print("-" * 50)
    
    # Use different depths to reduce draws
    dataset = collect_parallel(
        n_games=n_games,
        red_depth=red_depth,
        black_depth=black_depth,
        n_workers=n_workers,
        base_seed=base_seed,
    )
    
    if len(dataset) == 0:
        print("❌ No data collected!")
        return
    
    # Extract labels (numpy int8)
    labels = np.array([d[1] for d in dataset], dtype=np.int8)
    red_wins = (labels > 0).sum()
    black_wins = (labels < 0).sum()
    draws = (labels == 0).sum()
    
    print(f"\nDataset Statistics:")
    print(f"  Total samples: {len(dataset)}")
    print(f"  Labels - Red wins: {red_wins}, Black wins: {black_wins}, Draws: {draws}")
    print(f"  Label unique values: {np.unique(labels).tolist()}")
    print(f"  Sample X shape: {dataset[0][0].shape}, dtype: {dataset[0][0].dtype}")
    print(f"  Sample y dtype: {dataset[0][1].dtype}")
    
    # Save test data
    save_dataset(dataset, "data/test_data.pkl")
    print("\n✅ Quick test passed!")


def main():
    parser = argparse.ArgumentParser(description="Self-play trainer")
    parser.add_argument("--seed", type=int, default=None, help="Base random seed for reproducible games")
    parser.add_argument("--games", type=int, default=8, help="Number of games to play")
    parser.add_argument("--red-depth", type=int, default=3, help="AlphaBeta depth for red")
    parser.add_argument("--black-depth", type=int, default=3, help="AlphaBeta depth for black")
    parser.add_argument("--workers", type=int, default=4, help="Number of worker processes")
    args = parser.parse_args()

    test_selfplay_debug(
        n_games=args.games,
        red_depth=args.red_depth,
        black_depth=args.black_depth,
        n_workers=args.workers,
        base_seed=args.seed,
    )


if __name__ == '__main__':
    main()

    
