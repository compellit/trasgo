#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT_DIR = HERE.parent
RESULTS_DIR = PROJECT_DIR / "results"

DEFAULT_COMPARE_COLUMNS = ["correct_for_form"]
DEFAULT_CONTEXT_COLUMNS = ["forma", "fonetica", "gold_sampa_preproc"]
DEFAULT_BATCH_COLUMNS = ["silaba_output_raw", "silaba_output_preproc"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare two silaba_gl result batches under results/."
    )
    parser.add_argument(
        "batch_1",
        help="Baseline batch id or path. Bare numeric ids are zero-padded and read from results/.",
    )
    parser.add_argument(
        "batch_2",
        help="New batch id or path. Bare numeric ids are zero-padded and read from results/.",
    )
    parser.add_argument(
        "--results-dir",
        default=str(RESULTS_DIR),
        help="Directory containing numbered result TSVs. Default: silaba_gl/results",
    )
    parser.add_argument(
        "--output-file",
        help="Optional output path. Defaults to results/compare_<batch1>_<batch2>.tsv",
    )
    parser.add_argument(
        "--compare-column",
        action="append",
        dest="compare_columns",
        help="Column to compare with worse/better/same labels. Repeatable.",
    )
    return parser.parse_args()


def resolve_batch_path(value: str, results_dir: Path) -> Path:
    raw = Path(value)
    if raw.exists():
        return raw

    stem = value
    if value.isdigit():
        stem = f"{int(value):03d}"
    if not stem.endswith(".tsv"):
        stem = f"{stem}.tsv"
    return results_dir / stem


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() == "true"


def compare_bool_values(left: str, right: str) -> str:
    left_bool = parse_bool(left)
    right_bool = parse_bool(right)
    if left_bool and not right_bool:
        return "worse"
    if not left_bool and right_bool:
        return "better"
    return "same"


def unescape_quotes(value: str) -> str:
    return re.sub(r'\\+"', '"', value)


def ensure_alignment(
    rows_1: list[dict[str, str]],
    rows_2: list[dict[str, str]],
    path_1: Path,
    path_2: Path,
) -> None:
    if len(rows_1) != len(rows_2):
        raise ValueError(
            f"Batch sizes differ: {path_1.name} has {len(rows_1)} rows and "
            f"{path_2.name} has {len(rows_2)} rows."
        )

    for idx, (row_1, row_2) in enumerate(zip(rows_1, rows_2), start=1):
        key_1 = (row_1.get("forma", ""), row_1.get("fonetica", ""))
        key_2 = (row_2.get("forma", ""), row_2.get("fonetica", ""))
        if key_1 != key_2:
            raise ValueError(
                f"Row {idx} is not aligned.\n"
                f"  {path_1.name}: forma={key_1[0]!r}, fonetica={key_1[1]!r}\n"
                f"  {path_2.name}: forma={key_2[0]!r}, fonetica={key_2[1]!r}"
            )


def compare_batches(
    rows_1: list[dict[str, str]],
    rows_2: list[dict[str, str]],
    compare_columns: list[str],
    batch_1_label: str,
    batch_2_label: str,
) -> list[dict[str, str]]:
    output_rows: list[dict[str, str]] = []

    for row_1, row_2 in zip(rows_1, rows_2):
        result: dict[str, str] = {}

        for col in DEFAULT_CONTEXT_COLUMNS:
            if col in row_2:
                result[col] = unescape_quotes(row_2[col])

        for col in compare_columns:
            if col not in row_1 or col not in row_2:
                raise ValueError(f"Column {col!r} must exist in both batches.")
            comparison_col = "state" if compare_columns == DEFAULT_COMPARE_COLUMNS else f"C_{col}"
            result[comparison_col] = compare_bool_values(row_1[col], row_2[col])
            result[f"{col}_{batch_1_label}"] = unescape_quotes(row_1[col])
            result[f"{col}_{batch_2_label}"] = unescape_quotes(row_2[col])

        for col in DEFAULT_BATCH_COLUMNS:
            if col in row_1:
                result[f"{col}_{batch_1_label}"] = unescape_quotes(row_1[col])
            if col in row_2:
                result[f"{col}_{batch_2_label}"] = unescape_quotes(row_2[col])

        output_rows.append(result)

    return output_rows


def write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError("No comparison rows to write.")

    fieldnames = list(rows[0].keys())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=fieldnames,
            delimiter="\t",
            quoting=csv.QUOTE_NONE,
            quotechar=None,
            escapechar="\\",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    results_dir = Path(args.results_dir)

    batch_1_path = resolve_batch_path(args.batch_1, results_dir)
    batch_2_path = resolve_batch_path(args.batch_2, results_dir)
    if not batch_1_path.exists():
        raise SystemExit(f"Batch not found: {batch_1_path}")
    if not batch_2_path.exists():
        raise SystemExit(f"Batch not found: {batch_2_path}")

    rows_1 = read_tsv(batch_1_path)
    rows_2 = read_tsv(batch_2_path)
    ensure_alignment(rows_1, rows_2, batch_1_path, batch_2_path)

    compare_columns = args.compare_columns or DEFAULT_COMPARE_COLUMNS
    batch_1_label = batch_1_path.stem
    batch_2_label = batch_2_path.stem

    comparison_rows = compare_batches(
        rows_1,
        rows_2,
        compare_columns,
        batch_1_label,
        batch_2_label,
    )

    output_path = (
        Path(args.output_file)
        if args.output_file
        else results_dir / f"compare_{batch_1_label}_{batch_2_label}.tsv"
    )
    write_tsv(output_path, comparison_rows)
    print(f"Comparison saved to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
