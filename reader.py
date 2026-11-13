
import csv
from pathlib import Path


def read_csv(path: str | Path) -> list[dict[str, str]]:
    """Read a CSV file and return its rows as dictionaries."""
    with open(path, "r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))