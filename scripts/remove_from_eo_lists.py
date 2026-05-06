#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT_DIR = HERE.parent
LISTS_DIR = PROJECT_DIR / "listas"

DEFAULT_LIST_NAMES = [
    "E-tonico.txt",
    "E-pretonico.txt",
    "Ee-pretonico.txt",
    "EE-pretonico.txt",
    "O-tonico.txt",
    "O-pretonico.txt",
    "Oo-pretonico.txt",
    "OO-pretonico.txt",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove words from every top-level E/O lookup list."
    )
    parser.add_argument(
        "words",
        nargs="*",
        help="Words to remove. Use '-' to read newline-separated words from stdin.",
    )
    parser.add_argument(
        "--words-file",
        action="append",
        default=[],
        help="Read newline-separated words from a file. Repeatable.",
    )
    parser.add_argument(
        "--lists-dir",
        default=str(LISTS_DIR),
        help="Directory containing lookup lists. Default: silaba_gl/listas.",
    )
    parser.add_argument(
        "--include-novas-dev",
        action="store_true",
        help="Also remove from matching lists under listas/novas-dev.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report removals without changing files.",
    )
    parser.add_argument(
        "--case-sensitive",
        action="store_true",
        help="Match words exactly as given instead of lowercasing them first.",
    )
    return parser.parse_args()


def read_words_file(path: Path) -> list[str]:
    with path.open(encoding="utf-8") as fh:
        return [line.strip() for line in fh]


def collect_words(args: argparse.Namespace) -> set[str]:
    raw_words: list[str] = []

    for word in args.words:
        if word == "-":
            raw_words.extend(line.strip() for line in sys.stdin)
        else:
            raw_words.append(word)

    for value in args.words_file:
        raw_words.extend(read_words_file(Path(value)))

    words = {word for word in raw_words if word and not word.startswith("#")}
    if not args.case_sensitive:
        words = {word.lower() for word in words}
    return words


def list_paths(lists_dir: Path, include_novas_dev: bool) -> list[Path]:
    paths = [lists_dir / name for name in DEFAULT_LIST_NAMES]
    if include_novas_dev:
        paths.extend(lists_dir / "novas-dev" / name for name in DEFAULT_LIST_NAMES)
    return paths


def remove_words(path: Path, words: set[str], *, dry_run: bool, case_sensitive: bool) -> int:
    if not path.exists():
        return 0

    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    kept: list[str] = []
    removed = 0

    for line in lines:
        word = line.strip()
        key = word if case_sensitive else word.lower()
        if key in words:
            removed += 1
        else:
            kept.append(line)

    if removed and not dry_run:
        path.write_text("".join(kept), encoding="utf-8")

    return removed


def main() -> int:
    args = parse_args()
    words = collect_words(args)
    if not words:
        raise SystemExit("No words provided.")

    total_removed = 0
    for path in list_paths(Path(args.lists_dir), args.include_novas_dev):
        removed = remove_words(
            path,
            words,
            dry_run=args.dry_run,
            case_sensitive=args.case_sensitive,
        )
        total_removed += removed
        if removed:
            print(f"{removed}\t{path}")

    action = "Would remove" if args.dry_run else "Removed"
    print(f"{action} {total_removed} total line(s) for {len(words)} word(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
