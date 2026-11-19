"""trasgo: rule-based phonetic transcription and syllabification for Galician.

Example::

    from trasgo import Transcriber

    tr = Transcriber(complex_codas=True, thetacism=True, broad=True)
    tr.word("cabaza")                  # 'ka".Ba.Ta'
    tr.text("Unha casa na beira.")     # one transcription per word, space-separated
"""

from __future__ import annotations

from types import SimpleNamespace

from .text import SilabaText
from .word import Silaba, SilabaError

__version__ = "0.1.0"
__all__ = ["Transcriber", "make_options", "Silaba", "SilabaText", "SilabaError"]

ORTHOGRAPHIES = ("ilg", "portuguese")
OUTPUTS = ("phonetic", "phonological", "syllabic")


def make_options(
    orthography: str = "ilg",
    output: str = "phonetic",
    *,
    complex_codas: bool = False,
    thetacism: bool = False,
    rotacism: bool = False,
    gheada: bool = False,
    broad: bool = False,
) -> SimpleNamespace:
    """Translate readable option names into the flags used by Silaba 0.2.

    As in the original program, all variants are off by default and phonological
    output can only be combined with thetacism.
    """
    if orthography not in ORTHOGRAPHIES:
        raise ValueError(f"orthography must be one of {ORTHOGRAPHIES}")
    if output not in OUTPUTS:
        raise ValueError(f"output must be one of {OUTPUTS}")
    if output == "phonological" and (complex_codas or rotacism or gheada or broad):
        raise ValueError("phonological output can only be combined with thetacism")
    return SimpleNamespace(
        i=orthography == "ilg",
        l=orthography == "portuguese",
        d=output == "phonological",
        p=output == "phonetic",
        s=output == "syllabic",
        c=complex_codas,
        t=thetacism,
        r=rotacism,
        h=gheada,
        b=broad,
    )


class Transcriber:
    """Transcribe words or running text. Takes the same arguments as :func:`make_options`."""

    def __init__(self, orthography: str = "ilg", output: str = "phonetic", **variants: bool):
        self.options = make_options(orthography, output, **variants)
        self._text = SilabaText(self.options)

    def word(self, word: str) -> str:
        """Transcribe one word; raise :class:`SilabaError` if it cannot be transcribed."""
        return self._text.silaba.run(word)

    def text(self, text: str, *, prepro: bool = False) -> str:
        """Transcribe running text; words that cannot be transcribed come out as ``erro``."""
        return self._text.run(text, prepro=prepro)
