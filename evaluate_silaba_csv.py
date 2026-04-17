#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from pathlib import Path
from types import SimpleNamespace

from silaba_py import Silaba, SilabaError


def guess_delimiter(path: Path) -> str:
    if path.suffix.lower() == ".tsv":
        return "\t"
    sample = path.read_text(encoding="utf-8")[:4096]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t").delimiter
    except csv.Error:
        return ","


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            ins = curr[j - 1] + 1
            delete = prev[j] + 1
            sub = prev[j - 1] + (ca != cb)
            curr.append(min(ins, delete, sub))
        prev = curr
    return prev[-1]


def build_silaba_args(mode: str, *, c: bool = False, t: bool = False, r: bool = False, h: bool = False, b: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        l=mode == "l",
        i=mode == "i",
        d=False,
        p=True,
        s=False,
        c=c,
        t=t,
        r=r,
        h=h,
        b=b,
    )


def predict_sampa(
    word: str,
    mode: str,
    *,
    c: bool = False,
    t: bool = False,
    r: bool = False,
    h: bool = False,
    b: bool = False,
) -> str:
    args = build_silaba_args(mode, c=c, t=t, r=r, h=h, b=b)
    try:
        return Silaba(args).run(word)
    except SilabaError:
        return "erro"


def ipa_to_silaba_sampa(text: str) -> str:
    value = text.strip()
    if not value:
        return ""

    for wrapper in [("/", "/"), ("[", "]")]:
        if value.startswith(wrapper[0]) and value.endswith(wrapper[1]):
            value = value[1:-1].strip()

    replacements = [
        ("tʃ", "tS"),
        ("dʒ", "dZ"),
        ("t͡ʃ", "tS"),
        ("d͡ʒ", "dZ"),
        ("ɲ", "J"),
        ("ʎ", "L"),
        ("ŋ", "N"),
        ("ɡ", "g"),
        ("ɣ", "G"),
        ("β", "B"),
        ("ð", "D"),
        ("ʃ", "S"),
        ("ʒ", "Z"),
        ("θ", "T"),
        ("ɫ", "5"),
        ("ɬ", "K"),
        ("χ", "X"),
        ("x", "x"),
        ("r", "R"),
        ("ɾ", "r"),
        ("ʧ", "tS"),
        ("ʤ", "dZ"),
        ("ə", "6"),
        ("ɐ", "6"),
        ("ɛ", "E"),
        ("ɔ", "O"),
        ("ʊ", "U"),
        ("ɪ", "I"),
        ("ˈ", '"'),
        ("ˌ", '"'),
        ("ː", ""),
        ("ˑ", ""),
    ]
    for src, dst in replacements:
        value = value.replace(src, dst)

    # Remove combining IPA diacritics such as a̝, o̞, nasalization overlays, etc.
    value = "".join(
        ch for ch in unicodedata.normalize("NFD", value) if unicodedata.category(ch) != "Mn"
    )

    value = value.replace("̃", "~")
    value = value.replace("‿", "").replace(" ", "")
    value = value.replace("·", ".")
    return value


def strip_syllable_dots(text: str) -> str:
    return text.replace(".", "")


def collapse_open_close_vowels(text: str) -> str:
    return text.replace("A", "a").replace("E", "e").replace("O", "o")


def normalize_for_comparison(text: str, mode: str, *, ignore_open_close: bool = False) -> str:
    value = text.strip()
    if ignore_open_close:
        value = collapse_open_close_vowels(value)
    if mode == "segmental":
        for ch in ['"', " ", "/", "[", "]"]:
            value = value.replace(ch, "")
    elif mode == "no_dots":
        for ch in [".", " ", "/", "[", "]"]:
            value = value.replace(ch, "")
    return value


def should_skip_word(word: str) -> bool:
    if not word:
        return True
    if re.search(r"\d", word):
        return True
    if len(word.split()) > 1:
        return True
    return False


def read_rows(path: Path, delimiter: str) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter=delimiter)
        return list(reader)


def read_rows_no_header(path: Path, delimiter: str) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh, delimiter=delimiter)
        rows: list[dict[str, str]] = []
        for row in reader:
            rows.append({f"col_{idx}": value for idx, value in enumerate(row)})
        return rows


def write_rows(path: Path, rows: list[dict[str, str]], delimiter: str) -> None:
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=fieldnames,
            delimiter=delimiter,
            quoting=csv.QUOTE_NONE,
            escapechar="\\",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate silaba_py.py against a CSV/TSV with orthographic and phonetic columns.",
        add_help=False,
    )
    parser.add_argument("--help", action="help", help="show this help message and exit")
    parser.add_argument("input_file", help="CSV/TSV file with at least one orthographic column and one phonetic column.")
    parser.add_argument("--word-col", default="word", help="Column name for the orthographic word.")
    parser.add_argument("--phon-col", default="phonetic", help="Column name for the gold phonetic text (IPA or similar).")
    parser.add_argument("--no-header", action="store_true", help="Treat the input file as having no header row.")
    parser.add_argument("--word-col-index", type=int, help="0-based column index for the orthographic word when using --no-header.")
    parser.add_argument("--phon-col-index", type=int, help="0-based column index for the phonetic text when using --no-header.")
    parser.add_argument("--mode", choices=["i", "l"], default="i", help="Silaba orthography mode: i=ILG/RAG, l=Portuguese.")
    parser.add_argument(
        "--compare-mode",
        choices=["segmental", "exact", "no_dots"],
        default="no_dots",
        help='segmental ignores stress marks and syllable dots; no_dots ignores dots but keeps stress; exact compares the full SAMPA string.',
    )
    parser.add_argument("--delimiter", choices=[",", ";", "\\t"], help="Override input delimiter.")
    parser.add_argument("--output-file", help="Optional TSV file to write row-level predictions and scores.")
    parser.add_argument("-c", action="store_true", help="Pass complex codas flag through to silaba.")
    parser.add_argument("-t", action="store_true", help="Pass thetacism flag through to silaba.")
    parser.add_argument("-r", action="store_true", help="Pass rotacism flag through to silaba.")
    parser.add_argument("-h", action="store_true", help="Pass gheada flag through to silaba.")
    parser.add_argument("-b", action="store_true", help="Pass broad transcription flag through to silaba.")
    parser.add_argument(
        "--ignore-open-close-vowels",
        action="store_true",
        help="Ignore open/close vowel contrasts in comparison by mapping A/E/O to a/e/o in both strings.",
    )
    parser.add_argument("--limit", type=int, help="Maximum number of words to evaluate.")
    parser.add_argument(
        "--progress-every",
        type=int,
        default=1000,
        help="Print progress every N evaluated words. Use 0 to disable periodic progress.",
    )
    args = parser.parse_args()

    input_path = Path(args.input_file)
    delimiter = "\t" if args.delimiter == "\\t" else args.delimiter
    if delimiter is None:
        delimiter = guess_delimiter(input_path)

    rows = read_rows_no_header(input_path, delimiter) if args.no_header else read_rows(input_path, delimiter)
    if not rows:
        print("No rows found.")
        return 1
    print(f"Rows in input file: {len(rows)}")

    word_col = args.word_col
    phon_col = args.phon_col
    if args.no_header:
        if args.word_col_index is None or args.phon_col_index is None:
            raise SystemExit("With --no-header you must provide --word-col-index and --phon-col-index.")
        word_col = f"col_{args.word_col_index}"
        phon_col = f"col_{args.phon_col_index}"

    missing = [col for col in [word_col, phon_col] if col not in rows[0]]
    if missing:
        raise SystemExit(f"Missing required columns: {', '.join(missing)}")

    output_path = Path(args.output_file) if args.output_file else input_path.with_name(f"{input_path.stem}_silaba_eval.tsv")

    total = 0
    exact = 0
    total_distance = 0
    total_ref_chars = 0
    silaba_errors = 0
    skipped_rows = 0
    output_rows: list[dict[str, str]] = []

    for row in rows:
        word = (row.get(word_col) or "").strip()
        gold_phon = (row.get(phon_col) or "").strip()
        if should_skip_word(word):
            skipped_rows += 1
            continue
        if args.limit is not None and total >= args.limit:
            break

        total += 1
        if args.progress_every and total % args.progress_every == 0:
            running_accuracy = exact / total if total else 0.0
            running_cer = total_distance / total_ref_chars if total_ref_chars else 0.0
            print(
                f"Processed {total} words | "
                f"exact: {exact} | "
                f'silaba_erro: {silaba_errors} | '
                f"accuracy: {running_accuracy:.4f} | "
                f"cer: {running_cer:.4f}"
            )
        pred_sampa_raw = predict_sampa(word, args.mode, c=args.c, t=args.t, r=args.r, h=args.h, b=args.b)
        pred_sampa = strip_syllable_dots(pred_sampa_raw)
        gold_sampa = ipa_to_silaba_sampa(gold_phon)
        pred_norm = normalize_for_comparison(
            pred_sampa,
            args.compare_mode,
            ignore_open_close=args.ignore_open_close_vowels,
        )
        gold_norm = normalize_for_comparison(
            gold_sampa,
            args.compare_mode,
            ignore_open_close=args.ignore_open_close_vowels,
        )

        is_exact = pred_norm == gold_norm
        if is_exact:
            exact += 1
        if pred_sampa_raw == "erro":
            silaba_errors += 1

        dist = levenshtein(pred_norm, gold_norm)
        total_distance += dist
        total_ref_chars += max(len(gold_norm), 1)

        annotated = {
            "forma": word,
            "fonetica": gold_phon,
            "silaba_output_raw": pred_sampa_raw,
            "silaba_output_preproc": pred_norm,
            "gold_sampa_preproc": gold_norm,
            "correct": str(is_exact),
        }
        output_rows.append(annotated)

    accuracy = exact / total if total else 0.0
    cer = total_distance / total_ref_chars if total_ref_chars else 0.0

    print(f"Rows evaluated: {total}")
    print(f"Rows skipped: {skipped_rows}")
    print(f"Exact matches: {exact}")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Character error rate: {cer:.4f}")
    print(f'Silaba "erro" predictions: {silaba_errors}')

    write_rows(output_path, output_rows, "\t")
    print(f"Wrote annotated results to {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
