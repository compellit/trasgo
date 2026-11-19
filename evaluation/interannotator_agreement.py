#!/usr/bin/env python3
"""Measure agreement between two annotations of the Ilenia sentence corpus.

Written by Anxo Alonso Pérez for his master's thesis; paths adapted for this repository.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from evaluate_words import levenshtein


HERE = Path(__file__).resolve().parent
ROOT = HERE
DEFAULT_REFERENCE = ROOT / "data" / "ilenia" / "annotators" / "ilenia_annotator_1.tsv"
DEFAULT_COMPARISON = ROOT / "data" / "ilenia" / "annotators" / "ilenia_annotator_2.tsv"
IAA_DIR = ROOT / "results" / "iaa"
DEFAULT_OUTPUT = IAA_DIR / "interannotator_agreement.tsv"
DEFAULT_SUMMARY = IAA_DIR / "iaa_summary.tsv"
DEFAULT_DISAGREEMENTS = IAA_DIR / "iaa_disagreements.tsv"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE))
    if not rows:
        raise SystemExit(f"Input contains no data rows: {path}")
    return rows


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "reference_word",
                "comparison_word",
                "sentence_index",
                "word_index",
                "ortho",
                "reference_phon",
                "comparison_phon",
                "agreement",
                "edit_distance",
                "status",
            ],
            delimiter="\t",
            quoting=csv.QUOTE_NONE,
            escapechar="\\",
        )
        writer.writeheader()
        writer.writerows(rows)


def write_summary(path: Path, summary: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(summary), delimiter="\t")
        writer.writeheader()
        writer.writerow(summary)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Measure interannotator agreement using the exact sentence, exact word, "
            "and character-error-rate metrics from evaluate_ilenia_tsv.py."
        )
    )
    parser.add_argument("reference_file", nargs="?", default=str(DEFAULT_REFERENCE))
    parser.add_argument("comparison_file", nargs="?", default=str(DEFAULT_COMPARISON))
    parser.add_argument("--output-file", default=str(DEFAULT_OUTPUT))
    parser.add_argument(
        "--summary-file",
        default=str(DEFAULT_SUMMARY),
        help="Aggregate IAA metrics TSV (default: %(default)s).",
    )
    parser.add_argument(
        "--disagreements-file",
        default=str(DEFAULT_DISAGREEMENTS),
        help="TSV containing only disagreements and alignment errors (default: %(default)s).",
    )
    parser.add_argument("--ortho-col", default="ortho")
    parser.add_argument("--phon-col", default="phon")
    parser.add_argument("--limit", type=int, help="Compare at most this many sentences.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    reference_path = Path(args.reference_file)
    comparison_path = Path(args.comparison_file)
    output_path = Path(args.output_file)
    summary_path = Path(args.summary_file)
    disagreements_path = Path(args.disagreements_file)
    reference_rows = read_rows(reference_path)
    comparison_rows = read_rows(comparison_path)

    for path, rows in (
        (reference_path, reference_rows),
        (comparison_path, comparison_rows),
    ):
        missing = [
            name for name in (args.ortho_col, args.phon_col) if name not in rows[0]
        ]
        if missing:
            raise SystemExit(f"Missing column(s) in {path}: {', '.join(missing)}")

    if len(reference_rows) != len(comparison_rows):
        raise SystemExit(
            "The files have different numbers of data rows: "
            f"{len(reference_rows)} != {len(comparison_rows)}"
        )

    paired_rows = list(zip(reference_rows, comparison_rows))
    if args.limit is not None:
        paired_rows = paired_rows[: args.limit]

    results: list[dict[str, str]] = []
    sentences_evaluated = sentence_exact = alignment_errors = 0
    words_evaluated = words_exact = 0
    total_distance = total_reference_chars = 0

    for sentence_index, (reference, comparison) in enumerate(paired_rows, start=1):
        reference_ortho = (reference.get(args.ortho_col) or "").strip()
        comparison_ortho = (comparison.get(args.ortho_col) or "").strip()
        reference_phon = (reference.get(args.phon_col) or "").strip()
        comparison_phon = (comparison.get(args.phon_col) or "").strip()
        reference_words = reference_phon.split()
        comparison_words = comparison_phon.split()
        sentences_evaluated += 1

        if reference_ortho != comparison_ortho or len(reference_words) != len(comparison_words):
            alignment_errors += 1
            reasons = []
            if reference_ortho != comparison_ortho:
                reasons.append("ortho_mismatch")
            if len(reference_words) != len(comparison_words):
                reasons.append(
                    f"word_count_mismatch:{len(reference_words)}:{len(comparison_words)}"
                )
            results.append(
                {
                    "sentence_index": str(sentence_index),
                    "word_index": "",
                    "ortho": reference_ortho,
                    "reference_phon": reference_phon,
                    "comparison_phon": comparison_phon,
                    "reference_word": "",
                    "comparison_word": "",
                    "agreement": "",
                    "edit_distance": "",
                    "status": ";".join(reasons),
                }
            )
            continue

        current_sentence_exact = True
        for word_index, (reference_word, comparison_word) in enumerate(
            zip(reference_words, comparison_words), start=1
        ):
            agrees = reference_word == comparison_word
            distance = levenshtein(comparison_word, reference_word)
            words_evaluated += 1
            words_exact += int(agrees)
            total_distance += distance
            total_reference_chars += len(reference_word)
            current_sentence_exact = current_sentence_exact and agrees
            results.append(
                {
                    "sentence_index": str(sentence_index),
                    "word_index": str(word_index),
                    "ortho": reference_ortho,
                    "reference_phon": reference_phon,
                    "comparison_phon": comparison_phon,
                    "reference_word": reference_word,
                    "comparison_word": comparison_word,
                    "agreement": str(agrees),
                    "edit_distance": str(distance),
                    "status": "ok",
                }
            )
        sentence_exact += int(current_sentence_exact)

    write_rows(output_path, results)
    disagreements = [
        row
        for row in results
        if row["agreement"] == "False" or row["status"] != "ok"
    ]
    write_rows(disagreements_path, disagreements)
    aligned_sentences = sentences_evaluated - alignment_errors
    word_agreement = words_exact / words_evaluated if words_evaluated else 0.0
    sentence_agreement = sentence_exact / aligned_sentences if aligned_sentences else 0.0
    cer = total_distance / total_reference_chars if total_reference_chars else 0.0
    write_summary(
        summary_path,
        {
            "reference_file": str(reference_path.resolve().relative_to(ROOT)),
            "comparison_file": str(comparison_path.resolve().relative_to(ROOT)),
            "sentences_evaluated": str(sentences_evaluated),
            "sentences_with_alignment_errors": str(alignment_errors),
            "aligned_sentences": str(aligned_sentences),
            "exact_sentence_agreements": str(sentence_exact),
            "sentence_agreement": f"{sentence_agreement:.6f}",
            "words_evaluated": str(words_evaluated),
            "exact_word_agreements": str(words_exact),
            "word_agreement": f"{word_agreement:.6f}",
            "total_edit_distance": str(total_distance),
            "reference_characters": str(total_reference_chars),
            "character_error_rate": f"{cer:.6f}",
        },
    )

    print(f"Reference annotation: {reference_path.resolve()}")
    print(f"Comparison annotation: {comparison_path.resolve()}")
    print(f"Sentences evaluated: {sentences_evaluated}")
    print(f"Sentences with alignment errors: {alignment_errors}")
    print(
        f"Exact sentence agreement: {sentence_exact}/{aligned_sentences} "
        f"({sentence_agreement:.4%})"
    )
    print(f"Exact word agreement: {words_exact}/{words_evaluated} ({word_agreement:.4%})")
    print(f"Character error rate: {cer:.6f}")
    print(f"Annotated results: {output_path.resolve()}")
    print(f"Disagreements: {disagreements_path.resolve()}")
    print(f"IAA summary: {summary_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
