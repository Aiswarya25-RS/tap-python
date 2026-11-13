from reader import read_csv
from validator import to_snake_case
from transformer import calculate_order_totals


def test_read_csv(tmp_path):
    file = tmp_path / "sample.csv"
    file.write_text("name,price\nbook,12\n", encoding="utf-8")

    assert read_csv(file) == [{"name": "book", "price": "12"}]


def test_to_snake_case():
    assert to_snake_case("Order Purchase Timestamp") == "order_purchase_timestamp"


def test_calculate_order_totals():
    items = [
        {"order_id": "A", "price": "10", "freight_value": "2"},
        {"order_id": "A", "price": "5", "freight_value": "1"},
    ]

    assert calculate_order_totals(items) == {"A": 18.0}