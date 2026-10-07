from models import Estimate, db


def _post_estimate(client):
    return client.post("/estimates", data={
        "customer_name": "John Smith",
        "make": "Toyota",
        "model": "Camry",
        "issue_desc": "Squealing noise when braking.",
        "labor_rate": "95",
        "tax_rate": "8",
    })


def test_generate_rate_limited(app, client, user, fake_ai):
    app.config["RATE_LIMIT_GENERATE"] = 3
    client.post("/login", data={"email": "shop@example.com", "password": "password123"})

    for _ in range(3):
        assert _post_estimate(client).status_code == 302
    assert _post_estimate(client).status_code == 429

    # No estimate leaked through the blocked request.
    with app.app_context():
        assert Estimate.query.count() == 3


def test_auth_rate_limited(app, client, user, fake_ai):
    app.config["RATE_LIMIT_AUTH"] = 3
    for _ in range(3):
        resp = client.post("/login", data={"email": "shop@example.com", "password": "password123"})
        assert resp.status_code == 302
    resp = client.post("/login", data={"email": "shop@example.com", "password": "password123"})
    assert resp.status_code == 429