#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
PERL_SCRIPT = HERE / "silaba_0.2.pl"
PY_SCRIPT = HERE / "silaba_py.py"
LISTS_DIR = HERE / "listas"


def load_words_from_list(path: Path) -> list[str]:
    with path.open(encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip()]


def load_words_from_sentence_file(path: Path) -> list[str]:
    words: list[str] = []
    word_re = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)*", re.UNICODE)
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            words.extend(word_re.findall(line))
    return words


def default_words() -> list[str]:
    words = [
        "casa",
        "xente",
        "canción",
        "elixir",
        "mãe",
        "põe",
        "kiwi",
        "kuwait",
        "votarei",
        "equilibrio",
    ]
    for name in [
        "lista-x.txt",
        "lista-duplo-x.txt",
        "lista-np-EO.txt",
        "lista-vbo-EO-ton.txt",
        "lista-an.txt",
        "lista-ans.txt",
    ]:
        path = LISTS_DIR / name
        if path.exists():
            words.extend(load_words_from_list(path)[:20])
    seen: set[str] = set()
    unique: list[str] = []
    for word in words:
        if word not in seen:
            seen.add(word)
            unique.append(word)
    return unique


def run_tool(cmd: list[str], cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
    )
    output = (proc.stdout or proc.stderr).strip()
    return proc.returncode, output


def compare_one(flags: list[str], word: str) -> tuple[bool, str, str]:
    perl_code, perl_out = run_tool(["perl", str(PERL_SCRIPT), *flags, word], HERE)
    py_code, py_out = run_tool([sys.executable, str(PY_SCRIPT), *flags, word], HERE)
    ok = perl_out == py_out
    if not ok and perl_code == py_code and perl_out == py_out:
        ok = True
    return ok, perl_out, py_out


def expand_flag_sets(modes: list[str], outputs: list[str], extras: list[str]) -> list[list[str]]:
    out: list[list[str]] = []
    for mode in modes:
        for output in outputs:
            flags = [mode, output, *extras]
            out.append(flags)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare silaba_0.2.pl against silaba_py.py")
    parser.add_argument("words", nargs="*", help="Words to compare. Uses a built-in sample set if omitted.")
    parser.add_argument("--word-file", help="Read words from a UTF-8 text file, one per line.")
    parser.add_argument(
        "--sentence-file",
        help="Read a UTF-8 text file with one sentence per line and split each line into words before comparing.",
    )
    parser.add_argument("--mode", choices=["-i", "-l", "both"], default="both", help="Orthography mode to test.")
    parser.add_argument("--output", choices=["-d", "-p", "-s", "all"], default="all", help="Output mode to test.")
    parser.add_argument("--extra-flag", action="append", default=[], choices=["-c", "-t", "-r", "-h", "-b"], help="Optional extra flag to include.")
    parser.add_argument("--limit", type=int, help="Limit the number of words checked after loading inputs.")
    parser.add_argument(
        "--count-erro-only",
        action="store_true",
        help='Do not print per-word matches where both tools return "erro"; report only a final count.',
    )
    parser.add_argument(
        "--only-count-perl-erro",
        action="store_true",
        help='Do not print mismatch details when the Perl script returns "erro"; report only a final count of those cases.',
    )
    args = parser.parse_args(argv)

    words: list[str] = []
    if args.word_file:
        words.extend(load_words_from_list(Path(args.word_file)))
    if args.sentence_file:
        words.extend(load_words_from_sentence_file(Path(args.sentence_file)))
    words.extend(args.words)
    if not words:
        words = default_words()
    if args.limit is not None:
        words = words[: args.limit]

    modes = ["-i", "-l"] if args.mode == "both" else [args.mode]
    outputs = ["-d", "-p", "-s"] if args.output == "all" else [args.output]
    flag_sets = expand_flag_sets(modes, outputs, args.extra_flag)

    mismatches = 0
    total = 0
    erro_matches = 0
    perl_erro_cases = 0
    for flags in flag_sets:
        for word in words:
            total += 1
            ok, perl_out, py_out = compare_one(flags, word)
            both_erro = perl_out == "erro" and py_out == "erro"
            perl_erro = perl_out == "erro"
            if both_erro:
                erro_matches += 1
            if perl_erro:
                perl_erro_cases += 1
            if not ok:
                mismatches += 1
                if not (args.only_count_perl_erro and perl_erro):
                    print(f"Mismatch: {' '.join(flags)} {word}")
                    print(f"  perl: {perl_out}")
                    print(f"  python: {py_out}")
            elif both_erro and not args.count_erro_only:
                print(f'Erro match: {" ".join(flags)} {word}')

    if mismatches == 0:
        print(f"All {total} comparisons matched.")
        if args.count_erro_only:
            print(f'"erro" matches: {erro_matches}')
        if args.only_count_perl_erro:
            print(f'Perl "erro" cases: {perl_erro_cases}')
        return 0

    print(f"{mismatches} mismatches out of {total} comparisons.")
    if args.count_erro_only:
        print(f'"erro" matches: {erro_matches}')
    if args.only_count_perl_erro:
        print(f'Perl "erro" cases: {perl_erro_cases}')
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
