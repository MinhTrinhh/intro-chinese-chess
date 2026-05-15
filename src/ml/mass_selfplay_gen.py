from __future__ import annotations

import argparse
import pickle
from pathlib import Path
from typing import Iterable

from src.ml.selfplay_trainer import collect_parallel


DEFAULT_CONFIGS = [
    {
        "name": "3v2",
        "red_depth": 3,
        "black_depth": 2,
        "seed": 42,
        "output": "batch_3v2.pkl",
    },
    {
        "name": "2v3",
        "red_depth": 2,
        "black_depth": 3,
        "seed": 123,
        "output": "batch_2v3.pkl",
    },
    {
        "name": "3v3",
        "red_depth": 3,
        "black_depth": 3,
        "seed": 456,
        "output": "batch_3v3.pkl",
    },
]


def save_dataset(dataset, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "wb") as file_handle:
        pickle.dump(dataset, file_handle)

    print(f"✓ Saved {len(dataset)} samples to {path}")


def load_dataset(path: str | Path):
    path = Path(path)
    with open(path, "rb") as file_handle:
        return pickle.load(file_handle)


def summarize_dataset(dataset, title: str) -> None:
    labels = [int(sample[1]) for sample in dataset]
    print(f"\n[{title}]")
    print(f"  Total samples: {len(dataset)}")
    print(f"  RED wins:   {labels.count(1)}")
    print(f"  BLACK wins: {labels.count(-1)}")
    print(f"  Draws:      {labels.count(0)}")
    if dataset:
        print(f"  Sample X shape: {dataset[0][0].shape}")
        print(f"  Sample X dtype:  {dataset[0][0].dtype}")
        print(f"  Sample y dtype:  {dataset[0][1].dtype}")


def run_single_config(
    *,
    name: str,
    red_depth: int,
    black_depth: int,
    seed: int | None,
    games: int,
    workers: int,
    output: str,
) -> str:
    print(f"\n=== Generating {name} ===")
    dataset = collect_parallel(
        n_games=games,
        red_depth=red_depth,
        black_depth=black_depth,
        n_workers=workers,
        base_seed=seed,
    )
    summarize_dataset(dataset, f"Config {name}")
    save_dataset(dataset, output)
    return output


def combine_pickles(input_paths: Iterable[str | Path], output_path: str | Path) -> None:
    all_samples = []
    input_paths = [Path(path) for path in input_paths]

    for path in input_paths:
        print(f"Loading {path}")
        all_samples.extend(load_dataset(path))

    labels = [int(sample[1]) for sample in all_samples]
    print("\n[Combined dataset]")
    print(f"  RED wins:   {labels.count(1)}")
    print(f"  BLACK wins: {labels.count(-1)}")
    print(f"  Draws:      {labels.count(0)}")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as file_handle:
        pickle.dump(all_samples, file_handle)

    print(f"✓ Saved combined dataset to {output_path}")
    print(f"  Total samples: {len(all_samples)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run multiple self-play configs and merge outputs")
    parser.add_argument("--games", type=int, default=100, help="Number of games per config")
    parser.add_argument("--workers", type=int, default=8, help="Number of worker processes")
    parser.add_argument("--output-dir", type=str, default="data", help="Directory for generated pickles")
    parser.add_argument(
        "--combined-output",
        type=str,
        default="data/combined_dataset.pkl",
        help="Path for merged pickle",
    )
    parser.add_argument(
        "--only-combine",
        action="store_true",
        help="Skip generation and only merge the expected batch files",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    config_outputs = []

    if not args.only_combine:
        for config in DEFAULT_CONFIGS:
            output_path = output_dir / config["output"]
            config_outputs.append(
                run_single_config(
                    name=config["name"],
                    red_depth=config["red_depth"],
                    black_depth=config["black_depth"],
                    seed=config["seed"],
                    games=args.games,
                    workers=args.workers,
                    output=str(output_path),
                )
            )
    else:
        config_outputs = [str(output_dir / "batch_3v2.pkl"), str(output_dir / "batch_2v3.pkl"), str(output_dir / "batch_3v3.pkl")]

    combine_pickles(config_outputs, args.combined_output)


if __name__ == "__main__":
    main()
