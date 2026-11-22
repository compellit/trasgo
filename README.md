# Trasgo 

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24443050.svg)](https://doi.org/10.5281/zenodo.24443050)

Transcription and Syllabification for Galician · 🧝

Trasgo is a rule-based tool, Python port and adaptation of Silaba 0.2, a Perl program by Marcos Garcia
(Garcia & González 2011, 2012). It transcribes single words or running text into a
SAMPA-like notation with syllable boundaries and stress. It has no dependencies
outside the Python standard library.

## Installation

```bash
git clone https://github.com/compellit/trasgo
cd trasgo
pip install .
```

Python 3.10 or later is required.

## Usage

### Command line

The flags are the same as in Silaba 0.2: one orthography flag and one output flag are
required, and the variant flags are optional.

```bash
trasgo -i -p -c -t -b "O can de Xoana durmía baixo unha árbore."
# o "kan de So".a.na Dur".mi.a "Baj.So "u.Na "ar.Bo.re

echo "cabaza" | trasgo -i -s -t
# k[At]a[Nc]".B[At]a[Nc].T[At]a[Nc]
```

Without a text argument, `trasgo` reads standard input and writes one line per input line.
Punctuation is omitted from the output, and words that cannot be transcribed come
out as `erro`.

| Flag | Meaning |
|---|---|
| `-i` | ILG/RAG orthography |
| `-l` | Portuguese orthography (experimental, see below) |
| `-p` | phonetic transcription |
| `-d` | phonological representation (can only be combined with `-t`) |
| `-s` | syllabic constituents: onset `[At]`, nucleus `[Nc]`, coda `[Cd]` |
| `-c` | complex codas |
| `-t` | thetacism (without it, the output has seseo) |
| `-r` | rotacism |
| `-h` | gheada (help is only available as `--help`) |
| `-b` | broad transcription |
| `--prepro` | normalize apostrophes and historical spelling first |

The evaluation below uses `-i -p -c -t -b`.

### Python

```python
from trasgo import Transcriber

tr = Transcriber(complex_codas=True, thetacism=True, broad=True)
tr.word("cabaza")                      # 'ka".Ba.Ta'
tr.text("As curvas de crecemento.")    # 'as "kur.Bas De kre.Te".men.to'
```

`Transcriber` takes `orthography` (`"ilg"` or `"portuguese"`), `output` (`"phonetic"`,
`"phonological"` or `"syllabic"`), and the variants `complex_codas`, `thetacism`,
`rotacism`, `gheada` and `broad`. All variants are off by default, as in Silaba 0.2.
`word()` raises `SilabaError` when a word cannot be transcribed.

### Notation

`"` precedes the stressed syllable and `.` separates syllables. In running text,
words are separated by spaces. Some of the symbols:

| Symbol | Sound | Symbol | Sound |
|---|---|---|---|
| `E`, `O` | open mid vowels | `j`, `w` | glides |
| `B`, `D`, `G` | approximants | `T` | voiceless interdental fricative |
| `S` | voiceless postalveolar fricative | `tS` | voiceless postalveolar affricate |
| `x` | voiceless velar fricative | `J`, `L` | palatal nasal, palatal lateral |
| `N` | velar nasal (word-final and in `unha`) | `r`, `R` | tap, trill |

## What Trasgo changes with respect to Silaba 0.2

- Python port of the Perl program, with the same options.
- Rule and list revisions for ILG orthography, developed on the Banco de Voces
  development set.
- Running-text transcription (`trasgo.text`): words are transcribed one by one, and
  two rules apply across word boundaries: place assimilation of word-final `N`, and
  approximant `B`, `D`, `G` at the start of a word after a vowel, `s` or `r`
  (and after `l` for `b` and `g` only).
- Portuguese orthography (`-l`) is kept but has not been evaluated. Since the
  Galician revisions are partly in shared code, its output differs from Silaba 0.2
  for many words.

## Evaluation

Everything needed to reproduce the results is in `evaluation/`. After installing
`trasgo`, run `evaluation/run_all.sh`. Results are in `evaluation/results/`.
Known problems that are not fixed yet are listed in
[`evaluation/KNOWN_ISSUES.md`](evaluation/KNOWN_ISSUES.md).

| Data | Unit | Exact match |
|---|---|---|
| Banco de Voces, development set | words | 95.92% |
| Banco de Voces, test set | words | 93.74% |
| Ilenia, adjudicated reference (100 sentences) | words in context | 93.78% |
| Iago (1,316 sentences) | words in context | 81.75% (92.59% also accepting the Banco de Voces form) |

**Data:**

- Banco de Voces: pronunciations from the *Dicionario de pronuncia da lingua galega*
  (<https://eira.mancomun.gal/mancomun/pronuncia>), randomly split into development
  and test sets, with all the pronunciations of a written form kept in the same set
  (`evaluation/data_prep/`). The dictionary has no syllable boundaries, so
  the evaluation script adds them (`syllabify_sampa` in `evaluate_words.py`).
- Iago: the Iago part of `CRPIH_UVigo-GL-Voices_extended` by Proxecto Nós
  (<https://huggingface.co/datasets/proxectonos/CRPIH_UVigo-GL-Voices_extended>).
  The gold transcriptions are of whole sentences, but the evaluation is word by word:
  Trasgo transcribes each word in isolation, so its cross-word rules are not applied,
  and word-initial approximants in the gold (`B`, `D`, `G`) are turned into stops before
  comparing. The Iago score therefore measures word-level transcription; only the
  Ilenia evaluation covers context.
- Ilenia: 100 sentences annotated independently by two annotators
  (`evaluation/data/ilenia/annotators/`), then adjudicated (`evaluation/data/ilenia/ilenia_reference.tsv`).

**Inter-annotator agreement on Ilenia** (`evaluation/interannotator_agreement.py`):

| Pair | Words | Sentences |
|---|---|---|
| annotator 1 vs annotator 2 | 85.65% | 18% |
| reference vs annotator 1 | 91.07% | 31% |
| reference vs annotator 2 | 94.07% | 45% |

**Known disagreements between sources:**

- The conjunction `e` is `E` in the Ilenia reference (21 of 22 tokens) but `e` in Iago
  (187 tokens, 1.8 points of the Iago score).
- Contractions such as `dun`, `nun` and `cunha` are unstressed in the Banco de Voces,
  but stressed in the Ilenia reference and in Iago.

## Citation

Anxo Alonso Pérez and Pablo Ruiz Fabo (2026). Trasgo: Transcription and Syllabification for Galician. CiTIUS, Universidade de Santiago de Compostela. https://doi.org/10.5281/zenodo.24443050

Based on Silaba 0.2 by Marcos Garcia (references below).

## References

Garcia, M., & González, I. J. (2012). Automatic Phonetic Transcription by Phonological
Derivation. In H. Caseli, A. Villavicencio, A. Teixeira, & F. Perdigão (Eds.),
*Computational Processing of the Portuguese Language* (Vol. 7243, pp. 350–361).
Springer. <https://doi.org/10.1007/978-3-642-28885-2_39>

Garcia, M., & González López, I. (2011). Conversión fonética automática con información
fonológica para el gallego. *Procesamiento del Lenguaje Natural*, 47, 283–291.

## License

Trasgo is licensed under GPLv3; see [LICENSE](LICENSE).

The Banco de Voces and Iago evaluation data are licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); see [Data](#evaluation) for
their sources and the changes made to them.
