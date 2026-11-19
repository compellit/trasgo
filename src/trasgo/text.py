"""Transcribe running text with :mod:`trasgo.word`.

Punctuation is omitted from the result and numbers are kept as they are.
In phonetic output, two rules apply across word boundaries: place assimilation
of a word-final N, and b/d/g approximants at the start of a word.
"""

from __future__ import annotations

import re
from types import SimpleNamespace

from .word import Silaba, SilabaError


LETTERS = "A-Za-zÁÉÍÓÚÜÑÏáéíóúüñïÂÊÎÔÛâêîôûÇçÃãÕõÀà"
APOSTROPHES = "'’‘"
WORD_RE = re.compile(rf"[{LETTERS}]+(?:[{APOSTROPHES}][{LETTERS}]+)?")
TOKEN_RE = re.compile(
    rf"[{LETTERS}]+(?:[{APOSTROPHES}][{LETTERS}]+)?|\d+(?:[.,]\d+)?|[^\w\s]"
)


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


def is_lenition_context(previous_word: str, stop: str) -> bool:
    """Return True if a word-initial b/d/g becomes an approximant after ``previous_word``.

    This happens after a vowel, s or r, and after l only for b and g
    (s/r/l contexts from A. Alonso's master's thesis).
    """
    last = previous_word[-1].casefold()
    if last in "aeiouáéíóúüsr":
        return True
    return last == "l" and stop.casefold() in "bg"


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

    def __init__(self, args: SimpleNamespace):
        self.args = args
        self.silaba = Silaba(args)
        self.cache: dict[str, str] = {}

    def transcribe_token(self, token: str) -> str:
        if not WORD_RE.fullmatch(token):
            return token
        key = token.casefold()
        if key not in self.cache:
            try:
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
                initial_stop = re.match(
                    r"^[^A-Za-z]*([bdg])(?:[lr])?[aeiou]", transcription, re.IGNORECASE
                )
                if (
                    self.args.p
                    and previous_word is not None
                    and initial_stop is not None
                    and is_lenition_context(previous_word, initial_stop.group(1))
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
