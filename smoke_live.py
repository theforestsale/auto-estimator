"""Live smoke test: real Groq call through the full route stack + PDF."""
import json

from app import create_app
from services import ai

app = create_app()

with app.app_context():
    from models import db
    from services.pdf import render_estimate_pdf

    client = app.test_client()
    email = "live-test@example.com"

    def tok():
        return client.get("/api/csrf").get_json()["csrf_token"]

    if client.post("/signup", data={
        "email": email,
        "password": "password123",
        "confirm": "password123",
        "csrf_token": tok(),
    }).status_code != 302:
        login = client.post("/login", data={"email": email, "password": "password123", "csrf_token": tok()})
        if login.status_code != 302:
            raise SystemExit("login failed")

    resp = client.post("/estimates", data={
        "customer_name": "Marco Rivera",
        "make": "Toyota",
        "model": "Corolla",
        "year": "2015",
        "mileage": "128000",
        "issue_desc": "Check engine light is on and the car hesitates and stumbles when accelerating, especially going uphill. Smells a bit like rotten eggs sometimes.",
        "labor_rate": "95",
        "tax_rate": "8",
        "csrf_token": tok(),
    })
    print("create estimate ->", resp.status_code, resp.headers.get("Location"))
    assert resp.status_code == 302 and "/estimates/" in resp.headers["Location"]

    est_id = int(resp.headers["Location"].rsplit("/", 1)[1])

    view = client.get(f"/estimates/{est_id}")
    assert view.status_code == 200

    est = db.session.get(__import__("models").Estimate, est_id)
    data = json.loads(est.ai_json)
    totals = __import__("utils.helpers", fromlist=["estimate_totals"]).estimate_totals(
        data, est.labor_rate, est.tax_rate
    )
    print("diagnosis:", data["diagnosis"])
    for item in data["recommended_work"]:
        print(f"  - [{item['category']}] {item['item']}: {item['quantity']} {item['unit_label']} @ ${item['unit_price']:.2f}")
    print(f"totals: labor ${totals['labor']} parts ${totals['parts']} tax ${totals['tax']} TOTAL ${totals['total']}")

    pdf = render_estimate_pdf(est, {
        "name": "Example Auto Repair", "phone": "555-0100",
        "email": "billing@exampleautorepair.com", "address": "123 Main St",
    })
    assert pdf[:5] == b"%PDF-"
    print(f"PDF bytes: {len(pdf)}")

    webhook = json.dumps({
        "meta": {"event_name": "order_created", "webhook_id": "wh-live-1"},
        "data": {"attributes": {"user_email": email}},
    }).encode()
    secret = app.config["WEBHOOK_SECRET"]
    import hashlib, hmac
    sig = hmac.new(secret.encode(), webhook, hashlib.sha256).hexdigest()
    hw = client.post("/billing/webhook", data=webhook, headers={"X-Signature": sig})
    from models import User
    user = db.session.query(User).filter_by(email=email).first()
    print("webhook:", hw.status_code, "plan ->", user.plan)

print("LIVE SMOKE TEST OK")