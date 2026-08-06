#!/usr/bin/env python3
"""Evaluate silaba_text.py on the sentence-level Ilenia TSV corpus."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from evaluate_silaba_csv import build_silaba_args, levenshtein
from silaba_text import TOKEN_RE, WORD_RE, SilabaText


HERE = Path(__file__).resolve().parent
DEFAULT_INPUT = HERE / "data" / "corpus_100_gl_ilenia_silaba.tsv"
DEFAULT_OUTPUT = HERE / "results" / "ilenia_silaba" / "evaluation.tsv"
def orthographic_units(sentence: str) -> list[str]:
    """Return exactly the word/number units emitted by SilabaText."""
    return [
        token
        for token in TOKEN_RE.findall(sentence)
        if WORD_RE.fullmatch(token) or token[0].isalnum()
    ]


def gold_words(sentence: str) -> list[str]:
    return sentence.split()


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=list(rows[0]),
            delimiter="\t",
            quoting=csv.QUOTE_NONE,
            escapechar="\\",
        )
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate silaba_text.py using the Ilenia TSV's ortho column as input and phon as gold.",
        add_help=False,
    )
    parser.add_argument("--help", action="help", help="Show this help message and exit.")
    parser.add_argument("input_file", nargs="?", default=str(DEFAULT_INPUT))
    parser.add_argument("--output-file", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--ortho-col", default="ortho")
    parser.add_argument("--phon-col", default="phon")
    parser.add_argument("--mode", choices=["i", "l"], default="i")
    parser.add_argument("--limit", type=int, help="Evaluate at most this many sentences.")
    parser.add_argument(
        "-c", "--complex-codas", dest="c", action=argparse.BooleanOptionalAction, default=True,
        help="Allow complex codas (default: enabled).",
    )
    parser.add_argument(
        "-t", "--thetacism", dest="t", action=argparse.BooleanOptionalAction, default=True,
        help="Use thetacism (default: enabled).",
    )
    parser.add_argument("-r", action="store_true", help="Use rotacism.")
    parser.add_argument("-h", action="store_true", help="Use gheada.")
    parser.add_argument(
        "-b", "--broad", dest="b", action=argparse.BooleanOptionalAction, default=True,
        help="Use broad transcription (default: enabled).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input_file)
    output_path = Path(args.output_file)

    with input_path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    if not rows:
        raise SystemExit("Input contains no data rows.")
    missing = [name for name in (args.ortho_col, args.phon_col) if name not in rows[0]]
    if missing:
        raise SystemExit(f"Missing required column(s): {', '.join(missing)}")

    silaba_args = build_silaba_args(
        args.mode, c=args.c, t=args.t, r=args.r, h=args.h, b=args.b
    )
    evaluator = SilabaText(silaba_args)
    results: list[dict[str, str]] = []
    sentences_evaluated = sentence_exact = alignment_errors = 0
    words_evaluated = words_exact = silaba_errors = 0
    total_distance = total_gold_chars = 0

    selected_rows = rows if args.limit is None else rows[: args.limit]
    for sentence_index, row in enumerate(selected_rows, start=1):
        ortho = (row.get(args.ortho_col) or "").strip()
        phon = (row.get(args.phon_col) or "").strip()
        inputs = orthographic_units(ortho)
        golds = gold_words(phon)
        sentence_prediction = evaluator.run(ortho)
        predictions = sentence_prediction.split()
        sentences_evaluated += 1

        if len(inputs) != len(golds) or len(predictions) != len(golds):
            alignment_errors += 1
            results.append(
                {
                    "sentence_index": str(sentence_index),
                    "word_index": "",
                    "ortho": ortho,
                    "phon": phon,
                    "sentence_prediction": sentence_prediction,
                    "word": "",
                    "gold": "",
                    "prediction": "",
                    "correct": "",
                    "edit_distance": "",
                    "status": (
                        f"alignment_error:{len(inputs)}_ortho_units:"
                        f"{len(predictions)}_predicted_units:{len(golds)}_phon_units"
                    ),
                }
            )
            continue

        current_sentence_exact = True
        for word_index, (word, prediction, gold) in enumerate(
            zip(inputs, predictions, golds), start=1
        ):
            status = "silaba_error" if prediction == "erro" else "ok"
            silaba_errors += int(prediction == "erro")

            correct = prediction == gold
            distance = levenshtein(prediction, gold)
            words_evaluated += 1
            words_exact += int(correct)
            total_distance += distance
            total_gold_chars += len(gold)
            current_sentence_exact = current_sentence_exact and correct
            results.append(
                {
                    "sentence_index": str(sentence_index),
                    "word_index": str(word_index),
                    "ortho": ortho,
                    "phon": phon,
                    "sentence_prediction": sentence_prediction,
                    "word": word,
                    "gold": gold,
                    "prediction": prediction,
                    "correct": str(correct),
                    "edit_distance": str(distance),
                    "status": status,
                }
            )
        sentence_exact += int(current_sentence_exact)

    write_rows(output_path, results)
    aligned_sentences = sentences_evaluated - alignment_errors
    word_accuracy = words_exact / words_evaluated if words_evaluated else 0.0
    sentence_accuracy = sentence_exact / aligned_sentences if aligned_sentences else 0.0
    cer = total_distance / total_gold_chars if total_gold_chars else 0.0
    print(f"Sentences evaluated: {sentences_evaluated}")
    print(f"Sentences with alignment errors: {alignment_errors}")
    print(f"Exact sentences: {sentence_exact}/{aligned_sentences} ({sentence_accuracy:.4%})")
    print(f"Exact words: {words_exact}/{words_evaluated} ({word_accuracy:.4%})")
    print(f"Character error rate: {cer:.6f}")
    print(f'Silaba errors: {silaba_errors}')
    print(f"Annotated results: {output_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
