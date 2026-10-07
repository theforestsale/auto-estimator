import json
import logging

logging.getLogger("openai").setLevel(logging.WARNING)
logger = logging.getLogger("ai_estimator")

CATEGORIES = ("diagnostic", "labor", "parts", "misc")


class AIEstimateError(Exception):
    pass


def get_client(api_key, base_url):
    from openai import OpenAI

    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def build_prompt(data):
    system_prompt = (
        "You are a senior automotive service advisor and shop estimator. "
        "You turn a customer's complaint into a clear, honest, itemized work order estimate. "
        "Only include work the complaint plausibly implies; never upsell unnecessary jobs. "
        "Always respond with a single valid JSON object. "
        "Do not include explanations, markdown, or text outside the JSON."
    )

    user_prompt = (
        "Customer vehicle:\n"
        f"- Make: {data['make']}\n"
        f"- Model: {data['model']}\n"
        f"- Year: {data.get('year') or 'unknown'}\n"
        f"- Mileage: {data.get('mileage') or 'unknown'}\n\n"
        "Customer complaint/description:\n"
        f"{data['issue_desc']}\n\n"
        "Shop labor rate is fixed at "
        f"${data.get('labor_rate', 0):g}/hour. "
        "Use this exact rate as unit_price for every 'labor' and 'diagnostic' item.\n\n"
        "Return JSON in this exact format:\n"
        "{\n"
        '  "diagnosis": "short non-jargon explanation of the likely problem",\n'
        '  "customer_message": "2-3 sentence customer-friendly explanation of the needed work",\n'
        '  "recommended_work": [\n'
        "    {\n"
        '      "item": "e.g. Engine oil and filter change",\n'
        '      "category": "labor|diagnostic|parts|misc",\n'
        '      "quantity": 1.0,\n'
        '      "unit_label": "hr(s)|ea|job|ltr",\n'
        '      "unit_price": 0.0\n'
        "    }\n"
        "  ],\n"
        '  "parts": [{"name": "...", "est_price": 0.0}],\n'
        '  "notes": ["advice caveat for the customer"]\n'
        "}\n"
        "Rules:\n"
        "- category 'labor': shop labor, quantity in hours, unit_price = shop hourly rate.\n"
        "- category 'diagnostic': diagnostic fee, quantity in hours, unit_price = shop hourly rate.\n"
        "- category 'parts': parts, quantity = count, unit_price = price per unit.\n"
        "- category 'misc': shop supplies/fluids/disposal as one job quantity with unit_price = total.\n"
        "- 'item' must be a short line understandable by a car owner.\n"
        "- Use realistic 2026 pricing for a typical independent repair shop.\n"
        "- recommended_work should contain 2-6 items covering the likely fix."
    )

    return system_prompt, user_prompt


def generate_estimate(client, model, data, timeout=None):
    system_prompt, user_prompt = build_prompt(data)

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            timeout=timeout or 60,
        )
        raw = completion.choices[0].message.content
        return parse_estimate(raw)
    except AIEstimateError:
        raise
    except Exception as e:
        logger.error("AI API call failed: %s", e)
        raise AIEstimateError("The AI service could not be reached. Please try again.")


def parse_estimate(raw):
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON from AI: %s", e)
        raise AIEstimateError("The AI returned an invalid response. Please try again.")

    if not isinstance(data, dict):
        raise AIEstimateError("The AI returned an invalid response. Please try again.")

    recommended_work = []
    for item in data.get("recommended_work", []):
        if not isinstance(item, dict) or not str(item.get("item", "")).strip():
            continue
        category = str(item.get("category", "misc")).lower()
        if category not in CATEGORIES:
            category = "misc"
        recommended_work.append({
            "item": str(item.get("item", "")).strip()[:200],
            "category": category,
            "quantity": _to_float(item.get("quantity"), 1.0),
            "unit_label": str(item.get("unit_label", "ea"))[:20],
            "unit_price": _to_float(item.get("unit_price"), 0.0),
        })

    if not recommended_work:
        logger.warning("AI returned zero work items")
        raise AIEstimateError("The AI did not produce any line items. Please try again.")

    parts = []
    for part in data.get("parts", []):
        if isinstance(part, dict) and str(part.get("name", "")).strip():
            parts.append({
                "name": str(part.get("name", "")).strip()[:150],
                "est_price": _to_float(part.get("est_price"), 0.0),
            })

    notes = []
    for note in data.get("notes", []):
        text = str(note).strip()[:500]
        if text:
            notes.append(text)

    return {
        "diagnosis": str(data.get("diagnosis", "")).strip()[:500],
        "customer_message": str(data.get("customer_message", "")).strip()[:1000],
        "recommended_work": recommended_work,
        "parts": parts,
        "notes": notes,
    }


def _to_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default