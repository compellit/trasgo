# Known issues

Problems found while preparing the release that are not fixed yet. None of them
affects the scores in `results/` except where stated.

## `--prepro` (historical and poetic spelling) is not evaluated

`--prepro` (`prepro_text` in `src/trasgo/text.py`) normalizes the text before
transcription, in this order:

1. `q'`, `qu'`, `q `, `qu ` before a letter become `k`: `qu'a` → `ka`, `qu ela` → `kela`.
2. A single letter followed by a space and an apostrophe is joined to the next word: `d 'a` → `da`.
3. Apostrophe + space is deleted: `d' a casa` → `da casa`.
4. All remaining apostrophes are deleted: `n'o` → `no`.
5. A single consonant letter followed by a space is joined to the next word: `c o` → `co`.
6. All hyphens are deleted: `co-a` → `coa`, `dígoche-o` → `dígocheo`.
7. Circumflex accents are removed (`fôra` → `fora`) and grave accents become acute (`tèrra` → `térra`).

Examples (`-i -p -c -t -b`):

| Input | After prepro | With `--prepro` | Without |
|---|---|---|---|
| `n'o mar` | `no mar` | `no "mar` | `erro "mar` |
| `d' a casa` | `da casa` | `da "ka.sa` | `erro a "ka.sa` |
| `Vou co-a nena` | `Vou coa nena` | `"bow ko.a "ne.na` | `"bow ko a "ne.na` |
| `fôra` | `fora` | `"fo.ra` | `erro` |
| `qu'a nai` | `ka nai` | `"ka "naj` | `erro "naj` |
| `tèrra` | `térra` | `"te.Ra` | `erro "Ra` |

Problems:

- `q'` → `k` creates words that are not in the list of unstressed words, so
  `qu'a` and `q'o` come out stressed (`"ka`, `"ko`).
- Grave → acute changes the vowel: `tèrra` gives `"te.Ra` (closed `e`), while
  `terra` gives `"tE.Ra`.
- Deleting all hyphens also merges compounds (`catalano-aragonés`).
- Step 5 joins any single consonant letter to the next word.

None of the evaluation data uses `--prepro`.

## No stress in two-syllable words ending in an unaccented hiatus

Words such as `suan` or `Juan` come out without any stress (`su.aN`, `xu.aN`).
The rule for words ending in an unaccented `i`/`u` + `a`/`e`/`o` (+ `n`/`s`) stresses
the syllable before the `i`/`u` (`lingua` → `"lin.gu.a`). In two-syllable words that
syllable does not exist, and no stress is assigned (`_split_syllables_and_stress_ilg`
in `src/trasgo/word.py`).

In the evaluation data, this only affects `Juan` in Ilenia (3 tokens), which the
adjudicated reference transcribes as one syllable (`"xwaN`, `xwaN`, `xwan`).

## Spanish names with `j` + `u` + vowel get a hiatus

`Juana` → `xu".a.na`, `Juan` → `xu.aN`. The Spanish pronunciation has a diphthong
(`"xwa.na`). trasgo only makes `u` + vowel a diphthong after `k`/`g` (`cuan` → `"kwaN`).

## Portuguese orthography (`-l`) is not evaluated

`-l` works, but no evaluation data covers it. The Galician revisions are partly
in code shared by both orthographies, so its output differs from Silaba 0.2 for
many words: about a third of a 414-word sample in phonetic (`-p`) mode, mainly
`n`/`N` before consonants, glides in `-áceas`, and some open/closed vowels. All this
is why we call this option _experimental_.

## Numbered homographs and multi-word entries are not scored (Banco de Voces)

The word-level evaluation skips dictionary entries whose form contains a digit or a
space (`should_skip_word` in `evaluate_words.py`): 3,028 of 51,949 rows in the
development set and 892 of 14,793 in the test set. Among them are function words whose
pronunciation the dictionary distinguishes by part of speech, such as `e1`
(conjunction, `ɛ`) vs `e2` (the letter, `ˈɛ`), `pero1`/`pero2` and `que1`/`que2`.
trasgo gives one output per form, so one of the homographs would always count as
wrong. A possible change is to strip the number and accept a match with any of the
homographs, as the "combined" Iago score already does.
