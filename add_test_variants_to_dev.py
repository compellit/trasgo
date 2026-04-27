#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from pathlib import Path


DEFAULT_DEV = Path(__file__).with_name("data") / "banco_de_voces_pronuncia_dev.csv"
DEFAULT_TEST = Path(__file__).with_name("data") / "banco_de_voces_pronuncia_test.csv"


def read_rows(path: Path) -> list[list[str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.reader(fh))


def write_rows(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerows(rows)


def rows_to_append(
    dev_rows: list[list[str]],
    test_rows: list[list[str]],
    form_column: int,
) -> list[list[str]]:
    dev_forms = {row[form_column] for row in dev_rows if len(row) > form_column}
    dev_row_keys = {tuple(row) for row in dev_rows}
    return [
        row
        for row in test_rows
        if len(row) > form_column
        and row[form_column] in dev_forms
        and tuple(row) not in dev_row_keys
    ]


def rows_to_remove_from_test(
    dev_rows: list[list[str]],
    test_rows: list[list[str]],
    form_column: int,
) -> list[list[str]]:
    dev_forms = {row[form_column] for row in dev_rows if len(row) > form_column}
    dev_row_keys = {tuple(row) for row in dev_rows}
    return [
        row
        for row in test_rows
        if len(row) > form_column
        and row[form_column] in dev_forms
        and tuple(row) in dev_row_keys
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Append rows from the test CSV to the dev CSV when their form is already "
            "present in dev, so dev contains all phonological realizations for those forms."
        )
    )
    parser.add_argument("--dev", type=Path, default=DEFAULT_DEV, help=f"Dev CSV. Default: {DEFAULT_DEV}")
    parser.add_argument("--test", type=Path, default=DEFAULT_TEST, help=f"Test CSV. Default: {DEFAULT_TEST}")
    parser.add_argument(
        "--form-column",
        type=int,
        default=2,
        help="1-based column number containing the written form. Default: 2.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report how many rows would be appended without changing files.",
    )
    parser.add_argument(
        "--update-test",
        action="store_true",
        help="Also remove appended rows from the test CSV.",
    )
    args = parser.parse_args()

    if args.form_column < 1:
        parser.error("--form-column must be 1 or greater.")

    form_column = args.form_column - 1
    dev_rows = read_rows(args.dev)
    test_rows = read_rows(args.test)
    append_rows = rows_to_append(dev_rows, test_rows, form_column)
    remove_rows = rows_to_remove_from_test(dev_rows + append_rows, test_rows, form_column)

    print(f"Dev rows before: {len(dev_rows)}")
    print(f"Test rows before: {len(test_rows)}")
    print(f"Rows to append from test to dev: {len(append_rows)}")
    if args.update_test:
        print(f"Rows to remove from test: {len(remove_rows)}")

    if args.dry_run:
        return 0

    if append_rows:
        write_rows(args.dev, dev_rows + append_rows)

    if args.update_test and remove_rows:
        remove_keys = {tuple(row) for row in remove_rows}
        write_rows(args.test, [row for row in test_rows if tuple(row) not in remove_keys])

    print(f"Dev rows after: {len(dev_rows) + len(append_rows)}")
    if args.update_test:
        print(f"Test rows after: {len(test_rows) - len(remove_rows)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
