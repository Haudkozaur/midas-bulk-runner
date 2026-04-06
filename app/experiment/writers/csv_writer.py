import csv
import os


class CsvWriter:
    def __init__(self, output_path: str):
        self.output_path = output_path

    def write(self, rows: list[dict]) -> None:
        if not rows:
            return

        output_dir = os.path.dirname(self.output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        fieldnames = list(rows[0].keys())

        with open(self.output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)