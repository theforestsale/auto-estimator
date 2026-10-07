from decimal import Decimal

from utils.helpers import money, estimate_totals


def test_money_formatting():
    assert money(1234.5) == "$1,234.50"
    assert money("99") == "$99.00"
    assert money(None) == "$0.00"


def test_totals():
    data = {
        "recommended_work": [
            {"category": "labor", "quantity": 2.0, "unit_price": 100.0},
            {"category": "diagnostic", "quantity": 0.5, "unit_price": 100.0},
            {"category": "parts", "quantity": 1.0, "unit_price": 60.0},
            {"category": "parts", "quantity": 2.0, "unit_price": 10.0},
            {"category": "misc", "quantity": 1.0, "unit_price": 12.5},
        ]
    }
    totals = estimate_totals(data, labor_rate=100, tax_rate=8)
    assert totals["labor"] == Decimal("250.0")
    assert totals["labor_hours"] == Decimal("2.5")
    assert totals["parts"] == Decimal("80.0")
    assert totals["misc"] == Decimal("12.50")
    assert totals["subtotal"] == Decimal("342.50")
    assert totals["tax"] == Decimal("7.40")  # (80 + 12.5) * 8%
    assert totals["total"] == Decimal("349.90")