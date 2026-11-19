"""Command line interface. The flags are the same as in Silaba 0.2 (Perl)."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .text import SilabaText


def parse_args(argv: list[str]) -> argparse.Namespace:
    # -h is gheada, as in Silaba 0.2, so help is only available as --help.
    parser = argparse.ArgumentParser(
        prog="trasgo",
        description=(
            "Transcribe Galician text (punctuation is omitted). "
            "Reads standard input, one text per line, if no text is given."
        ),
        add_help=False,
    )
    parser.add_argument("--help", action="help", help="show this help message and exit")
    parser.add_argument("--version", action="version", version=f"trasgo {__version__}")

    ortho = parser.add_mutually_exclusive_group(required=True)
    ortho.add_argument("-i", action="store_true", help="ILG/RAG orthography")
    ortho.add_argument("-l", action="store_true", help="Portuguese orthography (experimental, not evaluated)")

    out = parser.add_mutually_exclusive_group(required=True)
    out.add_argument("-d", action="store_true", help="phonological representation (only -t allowed)")
    out.add_argument("-p", action="store_true", help="phonetic transcription")
    out.add_argument("-s", action="store_true", help="syllabic constituents")

    parser.add_argument("-c", action="store_true", help="complex codas")
    parser.add_argument("-t", action="store_true", help="thetacism")
    parser.add_argument("-r", action="store_true", help="rotacism")
    parser.add_argument("-h", action="store_true", help="gheada")
    parser.add_argument("-b", action="store_true", help="broad transcription")
    parser.add_argument(
        "--prepro",
        action="store_true",
        help="normalize apostrophes and historical spelling before transcription",
    )
    parser.add_argument("text", nargs="?", help="text to transcribe; quote it if it contains spaces")
    args = parser.parse_args(argv)
    if args.d and (args.c or args.r or args.h or args.b):
        parser.error("-d cannot be combined with -c/-r/-h/-b")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    transcriber = SilabaText(args)
    if args.text is not None:
        print(transcriber.run(args.text, prepro=args.prepro))
    else:
        for line in sys.stdin:
            print(transcriber.run(line.rstrip("\n"), prepro=args.prepro))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
