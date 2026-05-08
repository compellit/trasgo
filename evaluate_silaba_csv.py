#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from pathlib import Path
from types import SimpleNamespace

from silaba_py import Silaba, SilabaError

HERE = Path(__file__).resolve().parent
RESULTS_DIR = HERE / "results" / "silaba"
SUMMARY_PATH = RESULTS_DIR / "summary.tsv"
ASYLLABIC_DIACRITIC = "\u032f"  # IPA non-syllabic mark, e.g. o̯.
VOWELS = ["a", "e", "i", "o", "u", "O", "E"]
SEMIVOWELS = ["j", "w"]
VOWELS_SEMI = VOWELS + SEMIVOWELS
STOPS_F = ["G", "B", "D", "t", "p", "k", "f", "g"]


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
        ("ɱ", "F"),
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
        ("-", ""),
    ]
    for src, dst in replacements:
        value = value.replace(src, dst)

    # Remove combining IPA diacritics such as a̝, o̞, nasalization overlays, etc.,
    # while preserving asyllabic marks that carry segmental information.
    value = "".join(
        ch
        for ch in unicodedata.normalize("NFD", value)
        if unicodedata.category(ch) != "Mn" or ch == ASYLLABIC_DIACRITIC
    )

    value = value.replace(ASYLLABIC_DIACRITIC, "_^")
    value = value.replace("̃", "")
    value = value.replace("‿", "").replace(" ", "")
    value = value.replace("·", ".")
    return value


def check_semiconsonant(sylls: list[str], i: int) -> None:
    if i + 1 < len(sylls):
        if sylls[i + 1][0] in SEMIVOWELS:
            if not (len(sylls[i + 1]) > 1 and sylls[i + 1][1] in VOWELS):
                sylls[i] += sylls[i + 1][0]
                sylls[i + 1] = sylls[i + 1][1:]
        elif sylls[i + 1][0] == "N":
            sylls[i] += sylls[i + 1][0]
            sylls[i + 1] = sylls[i + 1][1:]


def mark_stress(sylls: list[str], stress_idx: int, deleted_syllables: int) -> None:
    if len(sylls) > 1:
        if stress_idx == 0:
            sylls[0] = f"\\\"{sylls[0]}"
        else:
            sylls[stress_idx - deleted_syllables - 1] += "\\\""
    else:
        sylls[0] = f"\\\"{sylls[0]}"


def syllabify_sampa(text: str) -> str:
    gold_s = text
    dots = 0

    # Add syllable break after each vowel, except inside asyllabic-vowel markers.
    for i, c in enumerate(gold_s):
        if c in VOWELS and not (
            re.search(r"^[eoEO]_\^([^aeiouEO]|$)", text[i + 1 :])
            or re.search(r"_\^[aeiouEO]", text[i + 1 : i + 4])
        ):
            dots += 1
            gold_s = gold_s[: i + dots] + "." + gold_s[i + dots :]

    sylls = re.split(r"\.|\\(\")", gold_s)
    sylls = [s for s in sylls if s]

    if "\"" not in sylls:
        stress = False
        stress_idx = 0
    else:
        stress = True
        stress_idx = sylls.index("\"")
        sylls = sylls[:stress_idx] + sylls[stress_idx + 1 :]

    deleted_syllables = 0
    for i, syll in enumerate(sylls):
        syll = re.sub(r"tS", "4", syll)

        if i == 0:
            check_semiconsonant(sylls, i)
            continue

        if all(c not in VOWELS for c in syll):
            sylls[i - 1] += syll
            if i < stress_idx:
                deleted_syllables += 1
            del sylls[i]
            check_semiconsonant(sylls, i)
            continue

        len_cons = next((x for x, c in enumerate(syll) if c in VOWELS_SEMI), len(syll))

        if len_cons > 3:
            sylls[i - 1] += syll[:2]
            sylls[i] = syll[2:]
        elif len_cons > 2:
            if syll[0] not in VOWELS and syll[1] not in VOWELS_SEMI and syll[2] not in VOWELS_SEMI:
                if (
                    syll[1] == "s"
                    or not (syll[1] in STOPS_F + ["b", "d", "g"] and syll[2] in ["l", "r"])
                    and not syll[1:3] == "dl"
                ):
                    sylls[i - 1] += syll[:2]
                    sylls[i] = syll[2:]
                else:
                    sylls[i - 1] += syll[:1]
                    sylls[i] = syll[1:]
        elif len_cons > 1:
            if syll[0] not in VOWELS and syll[1] not in VOWELS_SEMI:
                if not (syll[0] in STOPS_F and syll[1] in ["l", "r"] and not syll[:2] == "dl"):
                    sylls[i - 1] += syll[0]
                    sylls[i] = syll[1:]

        check_semiconsonant(sylls, i)

    if stress:
        mark_stress(sylls, stress_idx, deleted_syllables)
    

    return ".".join(sylls).replace("4", "tS").replace(".\\\"", "\\\".")


def collapse_open_close_vowels(text: str) -> str:
    return text.replace("A", "a").replace("E", "e").replace("O", "o")


def normalize_for_comparison(text: str, mode: str, *, ignore_open_close: bool = False) -> str:
    value = text.strip()
    value = value.replace("~", "")
    if ignore_open_close:
        value = collapse_open_close_vowels(value)
    if mode == "segmental":
        for ch in ['"', ".", " ", "/", "[", "]"]:
            value = value.replace(ch, "")
    elif mode == "no_dots":
        for ch in [".", " ", "/", "[", "]"]:
            value = value.replace(ch, "")
    return value


LOOKUP_LIST_SUBSTITUTIONS = [
    ("e_ton", [(r'"([^\.]+)?e', r'"\1E')]),
    ("e_pre", [(r'e([^\"e]*)"', r'E\1"')]),
    ("ee_pre", [(r'e([^\"e]*)e([^\"e]*)"', r'E\1e\2"')]),
    ("ee_caps_pre", [(r'e([^\"e]*)e([^\"e]*)"', r'E\1E\2"')]),
    ("o_ton", [(r'"([^\.]+)?o', r'"\1O')]),
    ("o_pre", [(r'o([^\"o]*)"', r'O\1"')]),
    ("oo_pre", [(r'o([^\"o]*)o([^\"o]*)"', r'O\1o\2"')]),
    ("oo_caps_pre", [(r'o([^\"o]*)o([^\"o]*)"', r'O\1O\2"')]),
    ("eo_ton", [(r'"([^\.]+)?o', r'"\1O'), (r'"([^\.]+)?e', r'"\1E')]),
]


def apply_substitutions(text: str, substitutions: list[tuple[str, str]]) -> str:
    value = text
    for pattern, replacement in substitutions:
        value = re.sub(pattern, replacement, value)
    return value


def lookup_list_reason(pred_norm: str, gold_norm: str) -> str | None:
    for reason, substitutions in LOOKUP_LIST_SUBSTITUTIONS:
        if apply_substitutions(pred_norm, substitutions) == gold_norm:
            return reason
    return None


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
        default="exact",
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

    output_path = Path(args.output_file) if args.output_file else next_numbered_results_path(RESULTS_DIR)
    total = 0
    exact = 0
    total_distance = 0
    total_ref_chars = 0
    silaba_errors = 0
    skipped_rows = 0
    output_rows: list[dict[str, str]] = []
    form_stats: dict[str, dict[str, object]] = {}

    for row in rows:
        word = (row.get(word_col) or "").strip()
        gold_phon = (row.get(phon_col) or "").strip()
        if should_skip_word(word):
            skipped_rows += 1
            continue
        if args.limit is not None and total >= args.limit:
            break

        total += 1
        pred_sampa_raw = predict_sampa(word, args.mode, c=args.c, t=args.t, r=args.r, h=args.h, b=args.b)
        gold_sampa = syllabify_sampa(ipa_to_silaba_sampa(gold_phon))
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

        if "\"" not in gold_norm:
            is_exact = pred_norm.replace('"', "") == gold_norm
        else:
            is_exact = pred_norm == gold_norm
        if not is_exact:
            print(f"Error {word}:\n pred:{pred_norm}\n gold:{gold_norm}")
        if pred_sampa_raw == "erro":
            silaba_errors += 1

        # Reasons
        if is_exact:
            reason = "exact"
        elif pred_sampa_raw == "erro":
            reason = "silaba_erro"
        elif re.sub(r'(\")?S', r"k\1s", pred_norm) == gold_norm:
            reason = "ks"
        elif pred_norm.replace('_^', "") == gold_norm:
            reason = "non assylabic"
        elif pred_norm == gold_norm.replace('_^', ""):
            reason = "assylabic"            
        elif pred_norm.replace("w", "u") == gold_norm:
            reason = "u hiat"
        elif pred_norm.replace("j", "i") == gold_norm:
            reason = "i hiat"
        elif pred_norm.replace("u", "w") == gold_norm:
            reason = "w diph"
        elif pred_norm.replace("j", "i") == gold_norm:
            reason = "j diph"
        elif "E" in gold_norm or "O" in gold_norm:
            closed_pred_norm = pred_norm.replace("E", "e").replace("O", "o")
            if (lookup_reason := lookup_list_reason(closed_pred_norm, gold_norm)) is not None:
                reason = lookup_reason
            elif closed_pred_norm == gold_norm.replace("E", "e").replace("O", "o"):
                reason = "open/close"
            else:
                reason = "other"
        else:
            reason = "other"

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

        annotated = {
            "forma": word,
            "fonetica": gold_phon,
            "silaba_output_raw": pred_sampa_raw,
            "silaba_output_preproc": pred_norm,
            "gold_sampa_preproc": gold_norm,
            "correct": str(is_exact),
            "reason": reason
        }
        output_rows.append(annotated)

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
                f'silaba_erro: {silaba_errors} | '
                f"accuracy: {running_accuracy:.4f} | "
                f"cer: {running_cer:.4f}"
            )

    form_correct = {forma for forma, stats in form_stats.items() if bool(stats["any_exact"])}
    for row in output_rows:
        correct_for_form = row["forma"] in form_correct
        row["correct_for_form"] = str(correct_for_form)
        if correct_for_form:
            row["reason"] = "exact"

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
    print(f'Silaba "erro" predictions: {silaba_errors}')

    write_rows(output_path, output_rows, "\t")
    print(f"Wrote annotated results to {output_path}")

    summary = {
        "input_file": str(input_path.resolve()),
        "annotated_output_file": str(output_path.resolve()),
        "delimiter": "\\t" if delimiter == "\t" else delimiter,
        "no_header": str(args.no_header),
        "word_col": word_col,
        "phon_col": phon_col,
        "mode": args.mode,
        "compare_mode": args.compare_mode,
        "ignore_open_close_vowels": str(args.ignore_open_close_vowels),
        "flag_c": str(args.c),
        "flag_t": str(args.t),
        "flag_r": str(args.r),
        "flag_h": str(args.h),
        "flag_b": str(args.b),
        "limit": "" if args.limit is None else str(args.limit),
        "rows_in_input_file": str(len(rows)),
        "rows_evaluated": str(total),
        "rows_skipped": str(skipped_rows),
        "unique_forms_evaluated": str(unique_forms),
        "exact_matches_by_form": str(exact),
        "accuracy": f"{accuracy:.6f}",
        "character_error_rate": f"{cer:.6f}",
        "silaba_erro_predictions": str(silaba_errors),
    }
    append_summary(SUMMARY_PATH, summary)
    print(f"Wrote summary results to {SUMMARY_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
