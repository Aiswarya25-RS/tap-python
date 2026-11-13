from datetime import datetime


def rename_columns(
    row: dict[str, str],
    mapping: dict[str, str],
) -> dict[str, str]:
    """Return a copy of a row with mapped column names."""
    return {
        mapping.get(column, column): value
        for column, value in row.items()
    }


def convert_item_values(row: dict[str, str]) -> dict[str, str | float]:
    """Return a copy of an item row with price and freight as floats."""
    converted: dict[str, str | float] = row.copy()
    converted["price"] = float(row["price"])
    converted["freight_value"] = float(row["freight_value"])
    return converted


def parse_timestamp(value: str) -> datetime:
    """Convert an ISO timestamp string to a datetime object."""
    return datetime.fromisoformat(value)


def calculate_order_totals(
    items: list[dict[str, str]],
) -> dict[str, float]:
    """Calculate each order's total item price plus freight."""
    totals: dict[str, float] = {}

    for item in items:
        order_id = item["order_id"]
        item_total = float(item["price"]) + float(item["freight_value"])
        totals[order_id] = totals.get(order_id, 0.0) + item_total

    return totals