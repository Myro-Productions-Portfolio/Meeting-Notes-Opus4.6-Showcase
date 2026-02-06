"""CLI entry point for ``python -m actionize``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from actionize.parser import parse_meeting_notes
from actionize.formatter import format_markdown, format_json


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="actionize",
        description="Parse meeting notes and extract structured action items.",
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to the meeting-notes file (plain text or Markdown).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("out"),
        help="Output directory for generated files (default: ./out).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point called by the console script and ``python -m actionize``."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    input_path: Path = args.input_file.resolve()
    output_dir: Path = args.out.resolve()

    if not input_path.is_file():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        return 1

    text = input_path.read_text(encoding="utf-8")
    items = parse_meeting_notes(text)

    output_dir.mkdir(parents=True, exist_ok=True)

    md_path = output_dir / "action_items.md"
    md_path.write_text(format_markdown(items), encoding="utf-8")

    json_path = output_dir / "action_items.json"
    json_path.write_text(format_json(items), encoding="utf-8")

    print(f"Extracted {len(items)} action item(s).")
    print(f"  Markdown -> {md_path}")
    print(f"  JSON     -> {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
