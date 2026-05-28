#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import re
import string
import unicodedata
from pathlib import Path

from evaluate_silaba_csv import (
    build_silaba_args,
    ipa_to_silaba_sampa,
    levenshtein,
    normalize_for_comparison,
    predict_sampa,
    syllabify_sampa,
)

HERE = Path(__file__).resolve().parent
DEFAULT_INPUT_PATH = HERE / "data" / "iago_all.csv"
DEFAULT_BANCO_PATH = HERE / "data" / "banco_de_voces_pronuncia.csv"
RESULTS_DIR = HERE / "results" / "iago_silaba"
SUMMARY_PATH = RESULTS_DIR / "summary.tsv"

EDGE_PUNCTUATION = string.punctuation + "¡¿«»“”‘’"
STRESSED_VOWELS = {
    "á",
    "é",
    "í",
    "ó",
    "ú",
    "Á",
    "É",
    "Í",
    "Ó",
    "Ú",
}
VOWELS = {"a", "e", "i", "o", "u", "A", "E", "I", "O", "U"}


def guess_delimiter(path: Path) -> str:
    if path.suffix.lower() == ".tsv":
        return "\t"
    sample = path.read_text(encoding="utf-8")[:4096]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t").delimiter
    except csv.Error:
        return ","


def read_rows(path: Path, delimiter: str) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=delimiter))


def banco_lookup_key(word: str) -> str:
    return word.strip().lower()


def banco_lookup_keys(word: str) -> list[str]:
    key = banco_lookup_key(word)
    keys = [key]
    without_number = re.sub(r"\d+$", "", key)
    if without_number and without_number not in keys:
        keys.append(without_number)
    return keys


def read_banco_pronunciations(path: Path) -> dict[str, list[dict[str, str]]]:
    pronunciations: dict[str, list[dict[str, str]]] = {}
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        for row in reader:
            if len(row) < 4:
                continue
            form = row[1].strip()
            phonetic = row[3].strip()
            if not form or not phonetic or phonetic == r"\N":
                continue
            entry = {
                "banco_id": row[0].strip(),
                "banco_form": form,
                "banco_phonetic": phonetic,
            }
            for key in banco_lookup_keys(form):
                pronunciations.setdefault(key, []).append(entry)
    return pronunciations


def write_rows(path: Path, rows: list[dict[str, str]], delimiter: str) -> None:
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)

    path.parent.mkdir(parents=True, exist_ok=True)
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


def append_summary(path: Path, summary: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(summary.keys()), delimiter="\t")
        if write_header:
            writer.writeheader()
        writer.writerow(summary)


def next_numbered_results_path(results_dir: Path) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    used_numbers: set[int] = set()
    for path in results_dir.glob("*.tsv"):
        if re.fullmatch(r"\d{3}", path.stem):
            used_numbers.add(int(path.stem))

    for number in range(1, 1000):
        if number not in used_numbers:
            return results_dir / f"{number:03d}.tsv"

    raise SystemExit("No free output filenames left in results/iago_silaba (001-999).")


def split_sentence_words(text: str) -> list[str]:
    words: list[str] = []
    for token in text.split():
        word = token.strip(EDGE_PUNCTUATION)
        if word:
            words.append(word)
    return words


def iago_transcription_to_sampa(text: str) -> tuple[str, int | None]:
    value = text.strip()
    stress_vowel_index: int | None = None
    vowel_index = 0
    chars: list[str] = []

    for char in value:
        normalized_chars = [
            ch for ch in unicodedata.normalize("NFD", char) if unicodedata.category(ch) != "Mn"
        ]
        normalized = "".join(normalized_chars)
        chars.append(normalized)
        if normalized in VOWELS:
            if char in STRESSED_VOWELS:
                stress_vowel_index = vowel_index
            vowel_index += 1

    normalized_value = "".join(chars)
    normalized_value = re.sub(r"rr", "R", normalized_value)
    normalized_value = normalized_value.replace("Z", "L")
    if normalized_value.startswith(("B", "D", "G")):
        normalized_value = normalized_value[0].lower() + normalized_value[1:]

    return normalized_value, stress_vowel_index


def add_stress_to_syllabified_sampa(text: str, stress_vowel_index: int | None) -> str:
    if stress_vowel_index is None:
        return text

    syllables = text.split(".")
    seen_vowels = 0
    for syllable_index, syllable in enumerate(syllables):
        syllable_vowels = sum(1 for char in syllable if char in VOWELS)
        if seen_vowels <= stress_vowel_index < seen_vowels + syllable_vowels:
            if syllable_index == 0:
                syllables[0] = f'"{syllables[0]}'
            else:
                syllables[syllable_index - 1] = f'{syllables[syllable_index - 1]}"'
            break
        seen_vowels += syllable_vowels

    return ".".join(syllables)


def normalize_silaba_output(text: str) -> str:
    return re.sub(r"ju$", "iw", text)


def compare_normalized(pred_norm: str, gold_norm: str) -> bool:
    if "\"" not in gold_norm:
        return pred_norm.replace("\"", "") == gold_norm
    return pred_norm == gold_norm


def banco_phonetic_to_sampa(text: str) -> str:
    return syllabify_sampa(ipa_to_silaba_sampa(text))


def comparison_source(iago_correct: bool, banco_found: str, banco_correct: str) -> str:
    if banco_found != "True":
        return "iago" if iago_correct else "none (iago only)"
    banco_is_correct = banco_correct == "True"
    if iago_correct and banco_is_correct:
        return "both"
    if iago_correct:
        return "iago"
    if banco_is_correct:
        return "banco"
    return "none"


def compare_with_banco(
    word: str,
    pred_norm: str,
    banco_pronunciations: dict[str, list[dict[str, str]]],
    compare_mode: str,
    *,
    ignore_open_close: bool = False,
) -> dict[str, str]:
    entries = banco_pronunciations.get(banco_lookup_key(word), [])
    if not entries:
        return {
            "banco_found": "False",
            "banco_correct": "",
            "banco_best_id": "",
            "banco_best_form": "",
            "banco_best_phonetic": "",
            "banco_best_sampa": "",
            "banco_best_preproc": "",
            "banco_best_distance": "",
            "banco_pronunciation_count": "0",
        }

    best: dict[str, str] | None = None
    for entry in entries:
        banco_sampa = banco_phonetic_to_sampa(entry["banco_phonetic"])
        banco_norm = normalize_for_comparison(
            banco_sampa,
            compare_mode,
            ignore_open_close=ignore_open_close,
        )
        banco_correct = compare_normalized(pred_norm, banco_norm)
        distance = levenshtein(pred_norm, banco_norm)
        candidate = {
            "banco_found": "True",
            "banco_correct": str(banco_correct),
            "banco_best_id": entry["banco_id"],
            "banco_best_form": entry["banco_form"],
            "banco_best_phonetic": entry["banco_phonetic"],
            "banco_best_sampa": banco_sampa,
            "banco_best_preproc": banco_norm,
            "banco_best_distance": str(distance),
            "banco_pronunciation_count": str(len(entries)),
        }
        if best is None or banco_correct or distance < int(best["banco_best_distance"]):
            best = candidate
        if banco_correct:
            break

    if best is None:
        raise AssertionError("Banco entries unexpectedly empty after lookup.")
    return best


def should_skip_word(word: str) -> bool:
    if not word:
        return True
    if re.search(r"\d", word):
        return True
    if len(word.split()) > 1:
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate silaba_py.py against Iago sentence-level normalized text "
            "and phonetic_transcription columns."
        ),
        add_help=False,
    )
    parser.add_argument("--help", action="help", help="show this help message and exit")
    parser.add_argument(
        "input_file",
        nargs="?",
        default=str(DEFAULT_INPUT_PATH),
        help=f"CSV/TSV input file. Default: {DEFAULT_INPUT_PATH}",
    )
    parser.add_argument("--text-col", default="normalized", help="Column with normalized orthographic sentences.")
    parser.add_argument("--phon-col", default="phonetic_transcription", help="Column with gold phonetic transcription.")
    parser.add_argument("--banco-file", default=str(DEFAULT_BANCO_PATH), help=f"Banco de voces CSV file. Default: {DEFAULT_BANCO_PATH}")
    parser.add_argument("--delimiter", choices=[",", ";", "\\t"], help="Override input delimiter.")
    parser.add_argument("--output-file", help="Optional TSV file for word-level predictions and scores.")
    parser.add_argument("--mode", choices=["i", "l"], default="i", help="Silaba orthography mode: i=ILG/RAG, l=Portuguese.")
    parser.add_argument(
        "--compare-mode",
        choices=["segmental", "exact", "no_dots"],
        default="exact",
        help='segmental ignores stress marks and syllable dots; no_dots ignores dots but keeps stress; exact compares the full SAMPA string.',
    )
    parser.add_argument(
        "--ignore-open-close-vowels",
        action="store_true",
        help="Ignore open/close vowel contrasts in comparison by mapping A/E/O to a/e/o in both strings.",
    )
    parser.add_argument("--limit", type=int, help="Maximum number of words to evaluate.")
    parser.add_argument(
        "--sentence-limit",
        type=int,
        help="Maximum number of input sentences to read before word-level --limit is applied.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=1000,
        help="Print progress every N evaluated words. Use 0 to disable periodic progress.",
    )
    parser.add_argument("-c", action="store_true", help="Pass complex codas flag through to silaba.")
    parser.add_argument("-t", action="store_true", help="Pass thetacism flag through to silaba.")
    parser.add_argument("-r", action="store_true", help="Pass rotacism flag through to silaba.")
    parser.add_argument("-h", action="store_true", help="Pass gheada flag through to silaba.")
    parser.add_argument("-b", action="store_true", help="Pass broad transcription flag through to silaba.")
    args = parser.parse_args()

    input_path = Path(args.input_file)
    delimiter = "\t" if args.delimiter == "\\t" else args.delimiter
    if delimiter is None:
        delimiter = guess_delimiter(input_path)

    rows = read_rows(input_path, delimiter)
    if not rows:
        print("No rows found.")
        return 1
    print(f"Rows in input file: {len(rows)}")

    missing = [col for col in [args.text_col, args.phon_col] if col not in rows[0]]
    if missing:
        raise SystemExit(f"Missing required columns: {', '.join(missing)}")

    banco_path = Path(args.banco_file)
    banco_pronunciations = read_banco_pronunciations(banco_path)
    print(f"Banco pronunciations loaded: {sum(len(values) for values in banco_pronunciations.values())}")

    # Validate the flag shape early, matching evaluate_silaba_csv.py behavior.
    build_silaba_args(args.mode, c=args.c, t=args.t, r=args.r, h=args.h, b=args.b)

    output_path = Path(args.output_file) if args.output_file else next_numbered_results_path(RESULTS_DIR)
    total = 0
    silaba_errors = 0
    skipped_words = 0
    alignment_errors = 0
    exact_rows = 0
    combined_exact_rows = 0
    output_rows: list[dict[str, str]] = []
    form_stats: dict[str, dict[str, object]] = {}
    combined_incorrect_sources = {"none", "none (iago only)"}

    for sentence_idx, row in enumerate(rows, start=1):
        if args.sentence_limit is not None and sentence_idx > args.sentence_limit:
            break

        text = (row.get(args.text_col) or "").strip()
        phon = (row.get(args.phon_col) or "").strip()
        text_words = split_sentence_words(text)
        phon_words = split_sentence_words(phon)

        if len(text_words) != len(phon_words):
            alignment_errors += 1

        for word_idx, (word, gold_raw) in enumerate(zip(text_words, phon_words), start=1):
            if should_skip_word(word):
                skipped_words += 1
                continue
            if args.limit is not None and total >= args.limit:
                break

            total += 1
            pred_sampa_raw = normalize_silaba_output(
                predict_sampa(word, args.mode, c=args.c, t=args.t, r=args.r, h=args.h, b=args.b)
            )
            gold_sampa_raw, stress_vowel_index = iago_transcription_to_sampa(gold_raw)
            gold_sampa = add_stress_to_syllabified_sampa(
                syllabify_sampa(gold_sampa_raw),
                stress_vowel_index,
            )
            pred_norm = normalize_for_comparison(
                pred_sampa_raw,
                args.compare_mode,
                ignore_open_close=args.ignore_open_close_vowels,
            )
            gold_norm = normalize_for_comparison(
                gold_sampa,
                args.compare_mode,
                ignore_open_close=args.ignore_open_close_vowels,
            )
            is_exact = compare_normalized(pred_norm, gold_norm)
            banco_comparison = compare_with_banco(
                word,
                pred_norm,
                banco_pronunciations,
                args.compare_mode,
                ignore_open_close=args.ignore_open_close_vowels,
            )

            source = comparison_source(
                is_exact,
                banco_comparison["banco_found"],
                banco_comparison["banco_correct"],
            )
            is_combined_exact = source not in combined_incorrect_sources

            if is_exact:
                exact_rows += 1
            if is_combined_exact:
                combined_exact_rows += 1

            if pred_sampa_raw == "erro":
                silaba_errors += 1

            dist = levenshtein(pred_norm, gold_norm)
            if word not in form_stats:
                form_stats[word] = {
                    "any_exact": is_exact,
                    "any_combined_exact": is_combined_exact,
                    "best_dist": dist,
                    "best_ref_len": max(len(gold_norm), 1),
                }
            else:
                form_stats[word]["any_exact"] = bool(form_stats[word]["any_exact"]) or is_exact
                form_stats[word]["any_combined_exact"] = bool(form_stats[word]["any_combined_exact"]) or is_combined_exact
                if dist < int(form_stats[word]["best_dist"]):
                    form_stats[word]["best_dist"] = dist
                    form_stats[word]["best_ref_len"] = max(len(gold_norm), 1)

            if is_exact:
                reason = "exact"
            elif pred_sampa_raw == "erro":
                reason = "silaba_erro"
            elif pred_norm.replace("_^", "") == gold_norm:
                reason = "non_assyllabic"
            elif pred_norm.replace("w", "u") == gold_norm:
                reason = "u_hiat"
            elif pred_norm.replace("j", "i") == gold_norm:
                reason = "i_hiat"
            elif pred_norm.replace("u", "w") == gold_norm:
                reason = "w_diph"
            elif pred_norm.replace("i", "j") == gold_norm:
                reason = "j_diph"
            else:
                reason = "other"

            output_rows.append(
                {
                    "sentence_index": str(sentence_idx),
                    "word_index": str(word_idx),
                    "file_name": row.get("file_name", ""),
                    "sentence_normalized": text,
                    "sentence_phonetic_transcription": phon,
                    "forma": word,
                    "fonetica_iago": gold_raw,
                    "fonetica_iago_sampa_raw": gold_sampa_raw,
                    "fonetica_iago_sampa": gold_sampa,
                    "silaba_output_raw": pred_sampa_raw,
                    "silaba_output_preproc": pred_norm,
                    "gold_sampa_preproc": gold_norm,
                    "correct": str(is_exact),
                    "reason": reason,
                    **banco_comparison,
                    "comparison_source": source,
                    "sentence_word_count": str(len(text_words)),
                    "phon_word_count": str(len(phon_words)),
                    "aligned_sentence": str(len(text_words) == len(phon_words)),
                }
            )

            if args.progress_every and total % args.progress_every == 0:
                running_unique_forms = len(form_stats)
                running_exact = sum(1 for stats in form_stats.values() if bool(stats["any_exact"]))
                running_distance = sum(int(stats["best_dist"]) for stats in form_stats.values())
                running_ref_chars = sum(int(stats["best_ref_len"]) for stats in form_stats.values())
                running_accuracy_unique = running_exact / running_unique_forms if running_unique_forms else 0.0
                running_cer = running_distance / running_ref_chars if running_ref_chars else 0.0
                print(
                    f"Processed {total} words | "
                    f"unique_forms: {running_unique_forms} | "
                    f"exact_forms: {running_exact} | "
                    f'silaba_erro: {silaba_errors} | '
                    f"accuracy_unique: {running_accuracy_unique:.4f} | "
                    f"cer: {running_cer:.4f}"
                )

        if args.limit is not None and total >= args.limit:
            break

    unique_forms = len(form_stats)
    form_correct = {forma for forma, stats in form_stats.items() if bool(stats["any_exact"])}
    exact_unique = len(form_correct)
    combined_exact_unique = sum(1 for stats in form_stats.values() if bool(stats["any_combined_exact"]))
    total_distance = sum(int(stats["best_dist"]) for stats in form_stats.values())
    total_ref_chars = sum(int(stats["best_ref_len"]) for stats in form_stats.values())
    accuracy = exact_rows / total if total else 0.0
    accuracy_combined = combined_exact_rows / total if total else 0.0
    accuracy_unique = exact_unique / unique_forms if unique_forms else 0.0
    accuracy_combined_unique = combined_exact_unique / unique_forms if unique_forms else 0.0
    cer = total_distance / total_ref_chars if total_ref_chars else 0.0

    print(f"Words evaluated: {total}")
    print(f"Words skipped: {skipped_words}")
    print(f"Sentences with alignment errors: {alignment_errors}")
    print(f"Unique forms evaluated: {unique_forms}")
    print(f"Exact matches: {exact_rows}")
    print(f"Combined exact matches: {combined_exact_rows}")
    print(f"Exact matches by form: {exact_unique}")
    print(f"Combined exact matches by form: {combined_exact_unique}")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Accuracy combined: {accuracy_combined:.4f}")
    print(f"Accuracy unique: {accuracy_unique:.4f}")
    print(f"Accuracy combined unique: {accuracy_combined_unique:.4f}")
    print(f"Character error rate: {cer:.4f}")
    print(f'Silaba "erro" predictions: {silaba_errors}')

    write_rows(output_path, output_rows, "\t")
    print(f"Wrote annotated results to {output_path}")

    summary = {
        "input_file": str(input_path.resolve()),
        "annotated_output_file": str(output_path.resolve()),
        "delimiter": "\\t" if delimiter == "\t" else delimiter,
        "text_col": args.text_col,
        "phon_col": args.phon_col,
        "banco_file": str(banco_path.resolve()),
        "mode": args.mode,
        "compare_mode": args.compare_mode,
        "ignore_open_close_vowels": str(args.ignore_open_close_vowels),
        "flag_c": str(args.c),
        "flag_t": str(args.t),
        "flag_r": str(args.r),
        "flag_h": str(args.h),
        "flag_b": str(args.b),
        "limit": "" if args.limit is None else str(args.limit),
        "sentence_limit": "" if args.sentence_limit is None else str(args.sentence_limit),
        "rows_in_input_file": str(len(rows)),
        "words_evaluated": str(total),
        "words_skipped": str(skipped_words),
        "sentences_with_alignment_errors": str(alignment_errors),
        "unique_forms_evaluated": str(unique_forms),
        "exact_matches": str(exact_rows),
        "combined_exact_matches": str(combined_exact_rows),
        "exact_matches_by_form": str(exact_unique),
        "combined_exact_matches_by_form": str(combined_exact_unique),
        "accuracy": f"{accuracy:.6f}",
        "accuracy_combined": f"{accuracy_combined:.6f}",
        "accuracy_unique": f"{accuracy_unique:.6f}",
        "accuracy_combined_unique": f"{accuracy_combined_unique:.6f}",
        "character_error_rate": f"{cer:.6f}",
        "silaba_erro_predictions": str(silaba_errors),
    }
    append_summary(SUMMARY_PATH, summary)
    print(f"Wrote summary results to {SUMMARY_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
