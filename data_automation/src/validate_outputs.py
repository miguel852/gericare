from __future__ import annotations

import argparse
import csv
from pathlib import Path


def find_csv(folder: Path) -> Path:
    files = sorted(folder.glob("part-*.csv"))
    if not files:
        raise FileNotFoundError(f"No Spark CSV part file found in {folder}")
    return files[0]


def count_rows(path: Path) -> int:
    with path.open(encoding="utf-8") as file:
        return max(sum(1 for _ in file) - 1, 0)


def read_quality_report(output_dir: Path) -> list[dict[str, str]]:
    quality_root = output_dir / "quality" / "quality_report.csv"
    report_file = find_csv(quality_root)
    with report_file.open(encoding="utf-8") as file:
        return list(csv.DictReader(file))


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate generated GeriCare datasets")
    parser.add_argument("--output", default="output")
    args = parser.parse_args()

    output_dir = Path(args.output)
    shift_board = find_csv(output_dir / "gold" / "shift_board")
    family_follow_up = find_csv(output_dir / "gold" / "family_follow_up")

    if count_rows(shift_board) == 0:
        raise RuntimeError("shift_board has no rows")
    if count_rows(family_follow_up) == 0:
        raise RuntimeError("family_follow_up has no rows")

    failed_checks = [
        row for row in read_quality_report(output_dir) if int(row["failed_rows"]) > 0
    ]
    if failed_checks:
        print("Quality warnings found:")
        for row in failed_checks:
            print(f"- {row['check_name']}: {row['failed_rows']}")
    else:
        print("Quality checks passed with zero failed rows.")

    print("Output validation finished successfully.")


if __name__ == "__main__":
    main()

