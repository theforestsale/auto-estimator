from decimal import Decimal

CENTS = Decimal("0.01")


def money(value):
    try:
        return f"${Decimal(str(value)).quantize(CENTS):,.2f}"
    except Exception:
        return "$0.00"


def estimate_totals(ai_data, labor_rate, tax_rate):
    """Compute line totals server-side (never trust the model's arithmetic).

    tax applies to parts + misc; labor and diagnostic fees are treated as labor.
    Returns a dict with lab/parts/misc/qty hours + subtotal, tax, total.
    """
    labor = Decimal("0")
    parts = Decimal("0")
    misc = Decimal("0")
    labor_hours = Decimal("0")

    for item in ai_data.get("recommended_work", []):
        qty = Decimal(str(item.get("quantity", 0) or 0))
        price = Decimal(str(item.get("unit_price", 0) or 0))
        amount = qty * price
        category = item.get("category", "misc")
        if category in ("labor", "diagnostic"):
            labor += amount
            labor_hours += qty
        elif category == "parts":
            parts += amount
        else:
            misc += amount

    subtotal = labor + parts + misc
    tax = (parts + misc) * Decimal(str(tax_rate)) / Decimal("100")
    total = subtotal + tax

    return {
        "labor": labor,
        "labor_hours": labor_hours,
        "parts": parts,
        "misc": misc,
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
    }