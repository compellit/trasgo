"""Regression tests: expected values are trasgo outputs checked when the tests were written."""

import pytest

from trasgo import Transcriber, make_options
from trasgo.cli import main
from trasgo.word import LISTS_DIR, load_list

# Configuration used in the evaluation (complex codas, thetacism, broad transcription)
EVAL = dict(complex_codas=True, thetacism=True, broad=True)


@pytest.fixture(scope="module")
def tr():
    return Transcriber(**EVAL)


@pytest.mark.parametrize(
    "word, expected",
    [
        ("cabaza", 'ka".Ba.Ta'),
        ("pescadores", 'pes.ka".Do.res'),
        ("unha", '"u.Na'),       # stressed, N in the onset
        ("algunhas", 'al".Gu.Nas'),
        ("e", "E"),              # conjunction with open vowel
        ("Juan", "xu.aN"),       # j -> x
        ("Yolanda", 'jo".lan.da'),  # y is not affected by j -> x
    ],
)
def test_word(tr, word, expected):
    assert tr.word(word) == expected


def test_text(tr):
    assert tr.text("Unha casa de Juan en Bayona, e dun can.") == (
        '"u.Na "ka.sa De xu.aN em ba".jo.na E "DuN "kaN'
    )


def test_approximants_across_words(tr):
    # after s/r: b, d, g; after l: b, g but not d
    assert tr.text("as de") == 'as De'
    assert tr.text("mal de") == '"mal de'
    assert tr.text("mal bo") == '"mal "Bo'


def test_output_modes():
    assert Transcriber(output="phonological", thetacism=True).word("pescadores") == "peskadores"
    assert Transcriber(output="syllabic", thetacism=True).word("cabaza") == (
        'k[At]a[Nc]".B[At]a[Nc].T[At]a[Nc]'
    )


def test_portuguese_orthography():
    assert Transcriber(orthography="portuguese", thetacism=True, broad=True).text("cabeça") == 'ka".Be.Ta'


def test_phonological_only_allows_thetacism():
    with pytest.raises(ValueError):
        make_options(output="phonological", broad=True)


def test_unused_list_header_is_skipped():
    assert not any(line.startswith("#") for line in load_list(LISTS_DIR / "sufixos.txt"))


def test_cli(capsys):
    assert main(["-i", "-p", "-c", "-t", "-b", "cabaza"]) == 0
    assert capsys.readouterr().out == 'ka".Ba.Ta\n'
