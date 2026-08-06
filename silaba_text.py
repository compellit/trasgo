#!/usr/bin/env python3
"""Transcribe complete texts with :mod:`silaba_py`.

Punctuation is omitted from the result. Numbers are retained, and phonetic
output receives the same word-boundary adjustments used by
``transcribe_with_silaba_no_punct.py``.
"""

from __future__ import annotations

import argparse
import re
import sys

try:
    from .silaba_py import Silaba, SilabaError
except ImportError:  # Direct execution: python silaba_gl/silaba_text.py ...
    from silaba_py import Silaba, SilabaError


LETTERS = "A-Za-zÁÉÍÓÚÜÑÏáéíóúüñïÂÊÎÔÛâêîôû"
APOSTROPHES = "'’‘"
WORD_RE = re.compile(rf"[{LETTERS}]+(?:[{APOSTROPHES}][{LETTERS}]+)?")
TOKEN_RE = re.compile(
    rf"[{LETTERS}]+(?:[{APOSTROPHES}][{LETTERS}]+)?|\d+(?:[.,]\d+)?|[^\w\s]"
)


def reset_silaba_state(silaba: Silaba) -> None:
    """Reset the mutable per-word state before reusing a Silaba instance."""
    silaba.entrada = ""
    silaba.entrada2 = None
    silaba.entrada_lem = None
    silaba.entrada_lem2 = None
    silaba.entrada_vbex = None
    silaba.input_word = ""
    silaba.palavra = ""
    silaba.deep = ""


def assimilate_final_nasal(previous: str, following: str) -> str:
    """Apply place assimilation to a word-final archiphoneme ``N``."""
    if not previous.endswith("N"):
        return previous

    onset_match = re.match(r"^[^A-Za-z]*(tS|[A-Za-z])", following)
    if onset_match is None:
        return previous
    onset = onset_match.group(1)
    if onset in {"p", "b", "B"}:
        nasal = "m"
    # elif onset in {"S", "tS"}:
    #     nasal = "J"
    elif onset in {"S"}:
        nasal = "n"
    elif onset in {"f", "F"}:
        nasal = "F"
    elif onset in {"g", "G", "k", "n", "m"}:
        nasal = "N"
    elif onset in {"d", "D", "t", "T", "R", "s", "tS"}:
        nasal = "n"
    else:
        return previous
    return previous[:-1] + nasal


def prepro_text(text: str) -> str:
    """Normalize apostrophes and historical spellings used by the source tool."""
    text = re.sub(rf"(?i)q(?:u)?[{APOSTROPHES}]\s*(?=[{LETTERS}])", "k", text)
    text = re.sub(rf"(?i)\bq(?:u)?\s+(?=[{LETTERS}])", "k", text)
    text = re.sub(rf"\b([{LETTERS}])\s+[{APOSTROPHES}](?=[{LETTERS}])", r"\1", text)
    text = re.sub(rf"[{APOSTROPHES}]\s+(?=[{LETTERS}])", "", text)
    text = text.translate(str.maketrans("", "", APOSTROPHES))
    text = re.sub(
        rf"\b([bcdfghjklmnñpqrstvwxzBCDFGHJKLMNÑPQRSTVWXZ])\s+(?=[{LETTERS}])",
        r"\1",
        text,
    )
    text = text.replace("-", "")
    return text.translate(
        str.maketrans("âêîôûÂÊÎÔÛàèìòùÀÈÌÒÙ", "aeiouAEIOUáéíóúÁÉÍÓÚ")
    )


class SilabaText:
    """Reusable full-text transcriber with a shared word-form cache."""

    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.silaba = Silaba(args)
        self.cache: dict[str, str] = {}

    def transcribe_token(self, token: str) -> str:
        if not WORD_RE.fullmatch(token):
            return token
        key = token.casefold()
        if key not in self.cache:
            try:
                reset_silaba_state(self.silaba)
                self.cache[key] = self.silaba.run(token)
            except SilabaError:
                self.cache[key] = "erro"
        return self.cache[key]

    def run(self, text: str, *, prepro: bool = False) -> str:
        """Return a space-separated transcription with punctuation removed."""
        if prepro:
            text = prepro_text(text)

        output: list[str] = []
        previous_word: str | None = None
        previous_output_index: int | None = None
        for token in TOKEN_RE.findall(text):
            if WORD_RE.fullmatch(token):
                transcription = self.transcribe_token(token)
                if self.args.p and previous_output_index is not None:
                    output[previous_output_index] = assimilate_final_nasal(
                        output[previous_output_index], transcription
                    )
                if (
                    self.args.p
                    and previous_word is not None
                    and re.search(r"[aeiouáéíóúü]$", previous_word, re.IGNORECASE)
                    and re.match(
                        r"^[^A-Za-z]*[bdg](?:[lr])?[aeiou]",
                        transcription,
                        re.IGNORECASE,
                    )
                ):
                    transcription = re.sub(
                        r"^([^A-Za-z]*)([bdg])",
                        lambda match: match.group(1) + match.group(2).upper(),
                        transcription,
                        count=1,
                    )
                output.append(transcription)
                previous_word = token
                previous_output_index = len(output) - 1
            elif token[0].isalnum():
                output.append(token)
        return " ".join(output)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe a complete text with silaba_py.py (punctuation is omitted).",
        add_help=False,
    )
    parser.add_argument("--help", action="help", help="show this help message and exit")
    ortho = parser.add_mutually_exclusive_group(required=True)
    ortho.add_argument("-l", action="store_true", help="Portuguese orthography")
    ortho.add_argument("-i", action="store_true", help="ILG/RAG orthography")

    out = parser.add_mutually_exclusive_group(required=True)
    out.add_argument("-d", action="store_true", help="Show phonological representation")
    out.add_argument("-p", action="store_true", help="Show phonetic transcription")
    out.add_argument("-s", action="store_true", help="Show syllabic transcription")

    parser.add_argument("-c", action="store_true", help="Complex codas")
    parser.add_argument("-t", action="store_true", help="Thetacism")
    parser.add_argument("-r", action="store_true", help="Rotacism")
    parser.add_argument("-h", action="store_true", help="Gheada")
    parser.add_argument("-b", action="store_true", help="Broad transcription")
    parser.add_argument(
        "--prepro",
        action="store_true",
        help="Normalize apostrophes and historical spelling before transcription.",
    )
    parser.add_argument("text", help="Text to transcribe; quote it if it contains spaces.")
    args = parser.parse_args(argv)
    if args.d and (args.p or args.s or args.c or args.r or args.h or args.b):
        parser.error("-d cannot be combined with -p/-s/-c/-r/-h/-b")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        print(SilabaText(args).run(args.text, prepro=args.prepro))
    except SilabaError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
