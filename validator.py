import re


def to_snake_case(column_name: str) -> str:
    """Convert a column name to lowercase snake_case."""
    name = column_name.strip()
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    name = re.sub(r"[^A-Za-z0-9]+", "_", name)
    return name.strip("_").lower()