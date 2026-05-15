"""
Self-Play Trainer with model-based evaluation.

This mirrors src.ml.selfplay_trainer but uses an optional neural model inside
AlphaBetaAgent instead of the static heuristic evaluation at leaf nodes.
"""

from collections import Counter
from multiprocessing import Pool
import argparse
import random
from pathlib import Path

from tqdm import tqdm

from xiangqi.board import Board
from xiangqi.constants import FULL_BOARD, Camp, Force

from src.agents.alphabeta_agent import AlphaBetaAgent
from src.ml.model import load_checkpoint
from src.evaluation.heuristics import escape_loop, add_cache


RANDOM_OPENING_MOVES = 4

_MODEL_CACHE = None
_MODEL_CACHE_PATH = None


def _make_rng(base_seed: int | None, game_id: int) -> random.Random:
    """Create a deterministic per-game RNG."""
    if base_seed is None:
        base_seed = 42
    return random.Random(base_seed + game_id)


def _get_model(model_path: str | None, device: str = "cpu"):
    global _MODEL_CACHE, _MODEL_CACHE_PATH

    if not model_path:
        return None

    if _MODEL_CACHE is None or _MODEL_CACHE_PATH != model_path:
        _MODEL_CACHE = load_checkpoint(model_path, device=device)
        _MODEL_CACHE_PATH = model_path

    return _MODEL_CACHE


def play_one_game(args):
    """Play one game and return outcome string ('red_win','black_win','draw').
    """
    game_id, red_depth, black_depth, base_seed, model_path, device = args
    rng = _make_rng(base_seed, game_id)

    model = _get_model(model_path, device=device)

    # ML agent (red) gets the model if provided; black is a pure search agent
    red_agent = AlphaBetaAgent(depth=red_depth, use_book=False, model=model)
    black_agent = AlphaBetaAgent(depth=black_depth, use_book=False, model=None)

    board = Board(FULL_BOARD)
    agents = {Camp.RED: red_agent, Camp.BLACK: black_agent}
    current_turn = Camp.RED
    history = []

    move_count = 0
    max_moves = 150
    outcome = 'draw'

    while move_count < max_moves:
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

        if action is None:
            winner = current_turn.opponent()
            outcome = 'red_win' if winner == Camp.RED else 'black_win'
            break

        piece = action['piece']
        dst = action['dst']
        add_cache(history, action)
        captured, check = board.make_move(piece, dst)

        if captured and captured.force.name == "SHUAI":
            outcome = 'red_win' if current_turn == Camp.RED else 'black_win'
            break

        if board.test_draw():
            outcome = 'draw'
            break

        current_turn = current_turn.opponent()
        move_count += 1

    return outcome


def play_one_game_debug(args):
    """Play one game with detailed HTML logging and return the outcome.

    The red agent receives the model (if provided) while black is a pure
    search agent. No datasets are produced.
    """
    game_id, red_depth, black_depth, base_seed, model_path, device = args
    rng = _make_rng(base_seed, game_id)

    model = _get_model(model_path, device=device)

    red_agent = AlphaBetaAgent(depth=red_depth, use_book=False, model=model)
    black_agent = AlphaBetaAgent(depth=black_depth, use_book=False, model=None)

    board = Board(FULL_BOARD)
    agents = {Camp.RED: red_agent, Camp.BLACK: black_agent}

    current_turn = Camp.RED
    history = []
    move_count = 0
    max_moves = 400
    outcome = 'draw'

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
        log_file.write(f"<p><b>Model path:</b> {model_path or 'None'}</p>")

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

        position_counts = Counter()

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

            event_text = ""

            if move_count < RANDOM_OPENING_MOVES:
                actions = board.get_final_valid_actions(current_turn)
                actions = escape_loop(history, actions)

                if not actions:
                    winner = current_turn.opponent()
                    outcome = 'red_win' if winner == Camp.RED else 'black_win'
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

            if action is None:
                winner = current_turn.opponent()
                outcome = 'red_win' if winner == Camp.RED else 'black_win'
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

            piece = action['piece']
            dst = action['dst']
            add_cache(history, action)
            captured, check = board.make_move(piece, dst)
            fen_after = board.board_to_fen1()

            if captured and captured.force.name == "SHUAI":
                outcome = 'red_win' if current_turn == Camp.RED else 'black_win'
                event_text += " | General captured"
            elif board.test_draw():
                outcome = 'draw'
                event_text += " | Draw detected"
            if check:
                event_text += " | Check"

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

            if (captured and captured.force.name == "SHUAI") or board.test_draw():
                break

            current_turn = current_turn.opponent()
            move_count += 1

        if move_count >= max_moves:
            outcome = 'draw'

        log_file.write("</table>")
        log_file.write(f"<h2>Final Outcome: {outcome}</h2>")
        log_file.write("</body></html>")

    return outcome


def collect_parallel(
    n_games=10,
    red_depth=3,
    black_depth=3,
    n_workers=8,
    base_seed: int | None = None,
    model_path: str | None = None,
    device: str = "cpu",
):
    """Run games in parallel and return list of outcome strings."""

    print(f"\n[Self-Play Matches - Model vs Negamax]")
    print(f"  Games: {n_games}")
    print(f"  Red depth: {red_depth}, Black depth: {black_depth}")
    print(f"  Workers: {n_workers}")
    print(f"  Seed: {base_seed if base_seed is not None else 42}")
    print(f"  Model: {model_path if model_path else 'None'}")
    print(f"  Device: {device}")
    print("-" * 50)

    args_list = [
        (game_id, red_depth, black_depth, base_seed, model_path, device)
        for game_id in range(n_games)
    ]

    outcomes = []
    with Pool(processes=n_workers) as pool:
        results = tqdm(
            pool.imap_unordered(play_one_game_debug, args_list),
            total=n_games,
            desc="Playing games"
        )

        for outcome in results:
            outcomes.append(outcome)

    print(f"\n✓ Completed {len(outcomes)} games")
    return outcomes


def test_selfplay_debug(
    n_games=10,
    red_depth=3,
    black_depth=3,
    n_workers=8,
    base_seed: int | None = None,
    model_path: str | None = None,
    device: str = "cpu",
):
    """Quick test running matches and printing win/draw statistics."""
    print("\n[TEST] Self-Play Matches (Quick Test - Model vs Negamax)")
    print("-" * 50)

    outcomes = collect_parallel(
        n_games=n_games,
        red_depth=red_depth,
        black_depth=black_depth,
        n_workers=n_workers,
        base_seed=base_seed,
        model_path=model_path,
        device=device,
    )

    if len(outcomes) == 0:
        print("X No games run!")
        return

    red_wins = sum(1 for o in outcomes if o == 'red_win')
    black_wins = sum(1 for o in outcomes if o == 'black_win')
    draws = sum(1 for o in outcomes if o == 'draw')

    print(f"\nMatch Statistics:")
    print(f"  Total games: {len(outcomes)}")
    print(f"  Red wins: {red_wins}, Black wins: {black_wins}, Draws: {draws}")
    print("\n Quick test passed!")


def main():
    parser = argparse.ArgumentParser(description="Self-play trainer with model evaluation")
    parser.add_argument("--seed", type=int, default=None, help="Base random seed for reproducible games")
    parser.add_argument("--games", type=int, default=8, help="Number of games to play")
    parser.add_argument("--red-depth", type=int, default=3, help="AlphaBeta depth for red")
    parser.add_argument("--black-depth", type=int, default=3, help="AlphaBeta depth for black")
    parser.add_argument("--workers", type=int, default=4, help="Number of worker processes")
    parser.add_argument("--model-path", type=str, default=None, help="Path to a model checkpoint")
    parser.add_argument("--device", type=str, default="cpu", help="Torch device for model inference")
    args = parser.parse_args()

    test_selfplay_debug(
        n_games=args.games,
        red_depth=args.red_depth,
        black_depth=args.black_depth,
        n_workers=args.workers,
        base_seed=args.seed,
        model_path=args.model_path,
        device=args.device,
    )


if __name__ == '__main__':
    main()