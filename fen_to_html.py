from __future__ import annotations

import argparse
import html as html_lib
import re
from pathlib import Path
from typing import Iterable

from xiangqi.board import Board

RED_PIECES = {"俥", "傌", "相", "仕", "帥", "炮", "兵"}
BLACK_PIECES = {"車", "馬", "象", "士", "將", "砲", "卒"}

FEN_ROW = r"[rnbakabnrcpRNBAKABNRCP1-9]+"
FEN_PATTERN = re.compile(rf"(?:{FEN_ROW}/){{9}}{FEN_ROW}")
HTML_FEN_CELL_PATTERN = re.compile(
    rf"<pre>\s*(?P<fen>{FEN_PATTERN.pattern})\s*</pre>",
    re.IGNORECASE | re.DOTALL,
)


def board_html_from_fen(fen: str) -> str:
    """Render a Xiangqi FEN string as colored board HTML."""
    board = Board(fen)
    board_str = str(board)
    rendered: list[str] = []

    for char in board_str:
        if char in RED_PIECES:
            rendered.append(f'<span style="color:red">{char}</span>')
        elif char in BLACK_PIECES:
            rendered.append(f'<span style="color:black">{char}</span>')
        else:
            rendered.append(char)

    return "".join(rendered)


def board_block_from_fen(fen: str) -> str:
    return f"<pre>{board_html_from_fen(fen)}</pre>"


def pretty_html_from_existing_log(text: str) -> str:
    """Replace raw FEN cells inside an HTML log with rendered boards."""

    def replace_cell(match: re.Match[str]) -> str:
        fen = match.group("fen")
        try:
            return board_block_from_fen(fen)
        except Exception:
            return match.group(0)

    return HTML_FEN_CELL_PATTERN.sub(replace_cell, text)


def _escape_with_line_breaks(text: str) -> str:
    return html_lib.escape(text).replace("\n", "<br>")


def pretty_html_from_plain_text(text: str, title: str) -> str:
    """Create a standalone HTML page from plain text with rendered FEN boards."""
    parts: list[str] = []
    cursor = 0

    for match in FEN_PATTERN.finditer(text):
        before = text[cursor:match.start()]
        if before:
            parts.append(f"<span>{_escape_with_line_breaks(before)}</span>")
        parts.append(board_block_from_fen(match.group(0)))
        cursor = match.end()

    tail = text[cursor:]
    if tail:
        parts.append(f"<span>{_escape_with_line_breaks(tail)}</span>")

    body = "".join(parts) if parts else f"<pre>{_escape_with_line_breaks(text)}</pre>"

    return f"""<html>
<head>
    <meta charset=\"utf-8\" />
    <title>{html_lib.escape(title)}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            padding: 20px;
            background: #f8f8f8;
        }}
        .content {{
            background: white;
            border: 1px solid #ddd;
            padding: 16px;
            overflow-x: auto;
        }}
        pre {{
            white-space: pre;
            font-family: Consolas, 'Courier New', monospace;
            font-size: 18px;
            line-height: 1.35;
            margin: 0 0 16px 0;
        }}
    </style>
</head>
<body>
    <h1>{html_lib.escape(title)}</h1>
    <div class=\"content\">{body}</div>
</body>
</html>
"""


def convert_log_file(source_path: Path, output_path: Path | None = None) -> Path | None:
    """Convert one log file into a readable HTML version."""
    if source_path.name.endswith("_pretty.html"):
        return None

    text = source_path.read_text(encoding="utf-8", errors="ignore")
    output_path = output_path or source_path.with_name(f"{source_path.stem}_pretty.html")

    if source_path.suffix.lower() in {".html", ".htm"}:
        pretty_text = pretty_html_from_existing_log(text)
        if pretty_text == text:
            return None
    else:
        pretty_text = pretty_html_from_plain_text(text, source_path.name)

    output_path.write_text(pretty_text, encoding="utf-8")
    return output_path


def iter_log_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name.endswith("_pretty.html"):
            continue
        if path.suffix.lower() not in {".html", ".htm", ".log", ".txt"}:
            continue
        yield path


def process_logs(root: Path = Path("logs")) -> list[Path]:
    created: list[Path] = []
    if not root.exists():
        return created

    for log_file in iter_log_files(root):
        output_path = log_file.with_name(f"{log_file.stem}_pretty.html")
        result = convert_log_file(log_file, output_path)
        if result is not None:
            created.append(result)
    return created


def main() -> None:
    parser = argparse.ArgumentParser(description="Render Xiangqi FEN logs as readable HTML.")
    parser.add_argument("root", nargs="?", default="logs", help="Root folder containing log files.")
    args = parser.parse_args()

    created = process_logs(Path(args.root))
    if created:
        for path in created:
            print(path)
    else:
        print("No log files were converted.")


if __name__ == "__main__":
    main()
