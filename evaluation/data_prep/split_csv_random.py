#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path


def guess_delimiter(path: Path) -> str:
    if path.suffix.lower() == ".tsv":
        return "\t"
    sample = path.read_text(encoding="utf-8")[:4096]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t").delimiter
    except csv.Error:
        return ","


def guess_has_header(path: Path, delimiter: str) -> bool:
    sample = path.read_text(encoding="utf-8")[:4096]
    try:
        return csv.Sniffer().has_header(sample)
    except csv.Error:
        return False


def build_output_path(input_path: Path, suffix: str) -> Path:
    return input_path.with_name(f"{input_path.stem}_{suffix}{input_path.suffix}")


def split_rows(rows: list[list[str]], ratio: float, seed: int | None) -> tuple[list[list[str]], list[list[str]]]:
    shuffled = rows[:]
    random.Random(seed).shuffle(shuffled)
    split_index = round(len(shuffled) * ratio)
    return shuffled[:split_index], shuffled[split_index:]


def write_rows(path: Path, rows: list[list[str]], delimiter: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter=delimiter)
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Divide un CSV/TSV en dous ficheiros collendo as filas de forma aleatoria."
    )
    parser.add_argument("input_file", help="CSV/TSV de entrada.")
    parser.add_argument(
        "--dev-output",
        help="Ficheiro de saída para o 75%%. Por defecto: <entrada>_dev.csv",
    )
    parser.add_argument(
        "--test-output",
        help="Ficheiro de saída para o 25%%. Por defecto: <entrada>_test.csv",
    )
    parser.add_argument(
        "--ratio",
        type=float,
        default=0.75,
        help="Proporción para o primeiro ficheiro. Por defecto: 0.75.",
    )
    parser.add_argument(
        "--delimiter",
        choices=[",", ";", "\\t"],
        help="Forza o delimitador de entrada e saída.",
    )
    parser.add_argument(
        "--no-header",
        action="store_true",
        help="Indica que o ficheiro non ten cabeceira.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Semente aleatoria para obter sempre a mesma partición.",
    )
    args = parser.parse_args()

    if not 0 < args.ratio < 1:
        parser.error("--ratio debe estar entre 0 e 1.")

    input_path = Path(args.input_file)
    delimiter = "\t" if args.delimiter == "\\t" else (args.delimiter or guess_delimiter(input_path))
    has_header = False if args.no_header else guess_has_header(input_path, delimiter)

    dev_output = Path(args.dev_output) if args.dev_output else build_output_path(input_path, "dev")
    test_output = Path(args.test_output) if args.test_output else build_output_path(input_path, "test")

    with input_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh, delimiter=delimiter)
        rows = list(reader)

    if not rows:
        parser.error("O ficheiro de entrada está baleiro.")

    header: list[str] | None = rows[0] if has_header else None
    data_rows = rows[1:] if has_header else rows
    dev_rows, test_rows = split_rows(data_rows, args.ratio, args.seed)

    if header is not None:
        dev_rows = [header] + dev_rows
        test_rows = [header] + test_rows

    write_rows(dev_output, dev_rows, delimiter)
    write_rows(test_output, test_rows, delimiter)

    print(f"Entrada: {input_path}")
    print(f"Total filas de datos: {len(data_rows)}")
    print(f"Saída 1 ({args.ratio:.0%}): {dev_output} ({len(dev_rows) - (1 if header else 0)} filas)")
    print(f"Saída 2 ({1 - args.ratio:.0%}): {test_output} ({len(test_rows) - (1 if header else 0)} filas)")
    if args.seed is not None:
        print(f"Seed: {args.seed}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
