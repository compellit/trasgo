#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS_DIR = HERE / "results_cotovia"
SUMMARY_PATH = RESULTS_DIR / "summary_cotovia.tsv"


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

    value = "".join(
        ch for ch in unicodedata.normalize("NFD", value) if unicodedata.category(ch) != "Mn"
    )
    value = value.replace("̃", "~")
    value = value.replace("‿", "").replace(" ", "")
    value = value.replace("·", ".")
    return value


def collapse_open_close_vowels(text: str) -> str:
    return text.replace("A", "a").replace("E", "e").replace("O", "o")


def normalize_for_comparison(text: str, mode: str, *, ignore_open_close: bool = False) -> str:
    value = text.strip()
    if ignore_open_close:
        value = collapse_open_close_vowels(value)
    if mode == "segmental":
        for ch in ['"', " ", "/", "[", "]", ".", "-"]:
            value = value.replace(ch, "")
    elif mode == "no_dots":
        for ch in [".", "-", " ", "/", "[", "]"]:
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

    raise SystemExit("No free output filenames left in results/ (001-999).")


def clean_cotovia_stdout(text: str) -> str:
    value = text.strip()
    if not value:
        return ""
    value = re.sub(r".*% ", "", value, flags=re.DOTALL)
    value = re.sub(r" #.*", "", value, flags=re.DOTALL)
    return value.strip()


def cotovia_raw_to_sampa(text: str) -> str:
    value = text.strip()
    if not value:
        return ""

    raw_syllables = re.split(r"[-\s]+", value)
    syllables: list[str] = []
    stress_idx: int | None = None
    for idx, syllable in enumerate(raw_syllables):
        if not syllable:
            continue
        if "^" in syllable and stress_idx is None:
            stress_idx = len(syllables)
        syllables.append(syllable.replace("^", ""))

    if not syllables:
        return ""

    if stress_idx is not None:
        syllables[stress_idx] = f'"{syllables[stress_idx]}'
    return ".".join(syllables)


def predict_cotovia_raw(word: str, lang: str, trace_level: int) -> str:
    try:
        completed = subprocess.run(
            ["cotovia", "-Sl", lang, f"-t{trace_level}"],
            input=f"{word}\n",
            text=True,
            capture_output=True,
            check=True,
        )
    except FileNotFoundError:
        raise SystemExit("cotovia was not found in PATH.")
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else ""
        return f"erro{': ' + stderr if stderr else ''}"

    cleaned = clean_cotovia_stdout(completed.stdout)
    return cleaned or "erro"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate Cotovia against a CSV/TSV with orthographic and phonetic columns.",
        add_help=False,
    )
    parser.add_argument("--help", action="help", help="show this help message and exit")
    parser.add_argument("input_file", help="CSV/TSV file with at least one orthographic column and one phonetic column.")
    parser.add_argument("--word-col", default="word", help="Column name for the orthographic word.")
    parser.add_argument("--phon-col", default="phonetic", help="Column name for the gold phonetic text (IPA or similar).")
    parser.add_argument("--no-header", action="store_true", help="Treat the input file as having no header row.")
    parser.add_argument("--word-col-index", type=int, help="0-based column index for the orthographic word when using --no-header.")
    parser.add_argument("--phon-col-index", type=int, help="0-based column index for the phonetic text when using --no-header.")
    parser.add_argument(
        "--compare-mode",
        choices=["segmental", "exact", "no_dots"],
        default="no_dots",
        help='segmental ignores stress marks and syllable separators; no_dots ignores separators but keeps stress; exact compares the normalized Cotovia-to-SAMPA string.',
    )
    parser.add_argument("--delimiter", choices=[",", ";", "\\t"], help="Override input delimiter.")
    parser.add_argument("--output-file", help="Optional TSV file to write row-level predictions and scores.")
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
    parser.add_argument("--cotovia-lang", default="gl", help="Language passed to cotovia with -Sl (default: gl).")
    parser.add_argument("--cotovia-trace", type=int, default=3, help="Trace level passed to cotovia as -tN (default: 3).")
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

    output_path = Path(args.output_file) if args.output_file else next_numbered_results_path(RESULTS_DIR)
    total = 0
    total_distance = 0
    total_ref_chars = 0
    cotovia_errors = 0
    skipped_rows = 0
    output_rows: list[dict[str, str]] = []
    form_stats: dict[str, dict[str, object]] = {}
    raw_cache: dict[str, str] = {}

    for row in rows:
        word = (row.get(word_col) or "").strip()
        gold_phon = (row.get(phon_col) or "").strip()
        if should_skip_word(word):
            skipped_rows += 1
            continue
        if args.limit is not None and total >= args.limit:
            break

        total += 1
        pred_raw = raw_cache.get(word)
        if pred_raw is None:
            pred_raw = predict_cotovia_raw(word, args.cotovia_lang, args.cotovia_trace)
            raw_cache[word] = pred_raw

        pred_sampa = cotovia_raw_to_sampa(pred_raw) if not pred_raw.startswith("erro") else "erro"
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
        if pred_raw.startswith("erro"):
            cotovia_errors += 1

        dist = levenshtein(pred_norm, gold_norm)
        if word not in form_stats:
            form_stats[word] = {
                "any_exact": is_exact,
                "best_dist": dist,
                "best_ref_len": max(len(gold_norm), 1),
            }
        else:
            form_stats[word]["any_exact"] = bool(form_stats[word]["any_exact"]) or is_exact
            if dist < int(form_stats[word]["best_dist"]):
                form_stats[word]["best_dist"] = dist
                form_stats[word]["best_ref_len"] = max(len(gold_norm), 1)

        output_rows.append(
            {
                "forma": word,
                "fonetica": gold_phon,
                "cotovia_output_raw": pred_raw,
                "cotovia_output_sampa": pred_sampa,
                "cotovia_output_preproc": pred_norm,
                "gold_sampa_preproc": gold_norm,
                "correct": str(is_exact),
            }
        )

        if args.progress_every and total % args.progress_every == 0:
            running_unique_forms = len(form_stats)
            running_exact = sum(1 for stats in form_stats.values() if bool(stats["any_exact"]))
            running_distance = sum(int(stats["best_dist"]) for stats in form_stats.values())
            running_ref_chars = sum(int(stats["best_ref_len"]) for stats in form_stats.values())
            running_accuracy = running_exact / running_unique_forms if running_unique_forms else 0.0
            running_cer = running_distance / running_ref_chars if running_ref_chars else 0.0
            print(
                f"Processed {total} rows | "
                f"unique_forms: {running_unique_forms} | "
                f"exact_forms: {running_exact} | "
                f"cotovia_erro: {cotovia_errors} | "
                f"accuracy: {running_accuracy:.4f} | "
                f"cer: {running_cer:.4f}"
            )

    form_correct = {forma for forma, stats in form_stats.items() if bool(stats["any_exact"])}
    for row in output_rows:
        row["correct_for_form"] = str(row["forma"] in form_correct)

    unique_forms = len(form_stats)
    exact = len(form_correct)
    total_distance = sum(int(stats["best_dist"]) for stats in form_stats.values())
    total_ref_chars = sum(int(stats["best_ref_len"]) for stats in form_stats.values())
    accuracy = exact / unique_forms if unique_forms else 0.0
    cer = total_distance / total_ref_chars if total_ref_chars else 0.0

    print(f"Rows evaluated: {total}")
    print(f"Rows skipped: {skipped_rows}")
    print(f"Unique forms evaluated: {unique_forms}")
    print(f"Exact matches by form: {exact}")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Character error rate: {cer:.4f}")
    print(f'Cotovia "erro" predictions: {cotovia_errors}')

    write_rows(output_path, output_rows, "\t")
    print(f"Wrote annotated results to {output_path}")

    summary = {
        "input_file": str(input_path.resolve()),
        "annotated_output_file": str(output_path.resolve()),
        "delimiter": "\\t" if delimiter == "\t" else delimiter,
        "no_header": str(args.no_header),
        "word_col": word_col,
        "phon_col": phon_col,
        "compare_mode": args.compare_mode,
        "ignore_open_close_vowels": str(args.ignore_open_close_vowels),
        "cotovia_lang": args.cotovia_lang,
        "cotovia_trace": str(args.cotovia_trace),
        "limit": "" if args.limit is None else str(args.limit),
        "rows_in_input_file": str(len(rows)),
        "rows_evaluated": str(total),
        "rows_skipped": str(skipped_rows),
        "unique_forms_evaluated": str(unique_forms),
        "exact_matches_by_form": str(exact),
        "accuracy": f"{accuracy:.6f}",
        "character_error_rate": f"{cer:.6f}",
        "cotovia_erro_predictions": str(cotovia_errors),
    }
    append_summary(SUMMARY_PATH, summary)
    print(f"Wrote summary results to {SUMMARY_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
