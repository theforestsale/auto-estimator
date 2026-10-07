import json

import pytest

from services.ai import AIEstimateError, parse_estimate

VALID = json.dumps({
    "diagnosis": "Worn pads.",
    "customer_message": "Replace pads.",
    "recommended_work": [
        {"item": "Replace pads", "category": "labor", "quantity": 1.0,
         "unit_label": "hr(s)", "unit_price": 95.0},
        {"item": "Pads", "category": "parts", "quantity": 1, "unit_label": "ea", "unit_price": 50},
    ],
    "parts": [{"name": "Pads GXL", "est_price": 50}],
    "notes": ["Verify on inspection"],
})


def test_parse_valid():
    result = parse_estimate(VALID)
    assert result["diagnosis"] == "Worn pads."
    assert result["customer_message"] == "Replace pads."
    assert result["recommended_work"][0]["quantity"] == 1.0
    assert result["recommended_work"][0]["category"] == "labor"
    assert result["parts"][0]["est_price"] == 50.0
    assert result["notes"] == ["Verify on inspection"]


def test_parse_invalid_json():
    with pytest.raises(AIEstimateError):
        parse_estimate("not json at all")


def test_parse_missing_items():
    with pytest.raises(AIEstimateError):
        parse_estimate(json.dumps({"recommended_work": [], "diagnosis": "x"}))


def test_parse_normalizes_category_and_skips_bad_rows():
    data = json.dumps({
        "recommended_work": [
            {"item": "Brake pads", "category": "PARTS", "quantity": 2, "unit_price": "30"},
            {"item": "", "category": "labor", "quantity": 1, "unit_price": 10},
            {"item": "Fluids", "quantity": 1, "unit_price": 9.99},
        ]
    })
    result = parse_estimate(data)
    work = result["recommended_work"]
    assert len(work) == 2
    assert work[0]["category"] == "parts"
    assert work[1]["category"] == "misc"
    assert work[0]["quantity"] == 2.0
    assert work[0]["unit_price"] == 30.0