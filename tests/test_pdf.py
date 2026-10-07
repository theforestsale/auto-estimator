import json

from services.pdf import render_estimate_pdf


def test_pdf_renders():
    class FakeEstimate:
        id = 7
        customer_name = "Jane Doe"
        make = "Honda"
        model = "Civic"
        year = "2018"
        mileage = "64,000"
        issue_desc = "Vibration when braking at highway speed."
        labor_rate = 95.0
        tax_rate = 8.0
        status = "draft"

        def __str__(self):
            return "FakeEstimate"

    fake = FakeEstimate()
    fake.ai_json = json.dumps({
        "diagnosis": "Warped front rotors.",
        "customer_message": "Your front rotors need replacing.",
        "recommended_work": [
            {"item": "Replace front rotors", "category": "labor", "quantity": 1.5,
             "unit_label": "hr(s)", "unit_price": 95.0},
            {"item": "Front rotors pair", "category": "parts", "quantity": 1.0,
             "unit_label": "ea", "unit_price": 180.0},
        ],
        "parts": [{"name": "Front rotors pair", "est_price": 180.0}],
        "notes": ["Final price may vary."],
    })
    fake.created_at = __import__("datetime").datetime(2026, 9, 1, 12, 0, 0)

    data = render_estimate_pdf(fake, {"name": "Test Shop", "phone": "555", "email": "s@x.com", "address": "1 Main"})
    assert data[:5] == b"%PDF-"
    assert len(data) > 1000