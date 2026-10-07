from models import Estimate, User, db


def _post_estimate(client):
    return client.post("/estimates", data={
        "customer_name": "John Smith",
        "make": "Toyota",
        "model": "Camry",
        "year": "2016",
        "mileage": "82000",
        "issue_desc": "Squealing noise when braking in the mornings.",
        "labor_rate": "95",
        "tax_rate": "8",
    })


def test_create_estimate_redirects(client, user, fake_ai):
    client.post("/login", data={"email": "shop@example.com", "password": "password123"})
    resp = _post_estimate(client)
    assert resp.status_code == 302
    assert "/estimates/" in resp.headers["Location"]

    est = Estimate.query.first()
    assert est is not None
    assert est.customer_name == "John Smith"
    assert est.user_id == user.id


def test_dashboard_shows_estimate_and_usage(client, user, fake_ai):
    client.post("/login", data={"email": "shop@example.com", "password": "password123"})
    _post_estimate(client)
    body = client.get("/dashboard").data
    assert b"John Smith" in body
    assert b"1/3" in body


def test_quota_blocked_after_limit(client, user, fake_ai):
    client.post("/login", data={"email": "shop@example.com", "password": "password123"})
    for i in range(3):
        db.session.add(Estimate(
            user_id=user.id, customer_name=f"C{i}", make="Honda", model="Civic",
            issue_desc="x", labor_rate=95, tax_rate=8, ai_json="{}",
        ))
    db.session.commit()

    resp = _post_estimate(client)
    assert resp.status_code == 302
    assert "/upgrade" in resp.headers["Location"]

    assert b"3/3" in client.get("/dashboard").data


def test_pro_user_not_blocked_after_quota(client, user, fake_ai):
    db.session.get(User, user.id).plan = "pro"
    db.session.commit()
    client.post("/login", data={"email": "shop@example.com", "password": "password123"})
    for i in range(3):
        db.session.add(Estimate(
            user_id=user.id, customer_name=f"C{i}", make="Honda", model="Civic",
            issue_desc="x", labor_rate=95, tax_rate=8, ai_json="{}",
        ))
    db.session.commit()

    resp = _post_estimate(client)
    assert resp.status_code == 302
    assert "/upgrade" not in resp.headers["Location"]


def test_ownership_404(client, user, fake_ai):
    other = User(email="other@shop.com", password_hash="x")
    db.session.add(other)
    db.session.commit()
    est = Estimate(
        user_id=other.id, customer_name="O", make="Ford", model="F150",
        issue_desc="x", labor_rate=95, tax_rate=8, ai_json="{}",
    )
    db.session.add(est)
    db.session.commit()

    client.post("/login", data={"email": "shop@example.com", "password": "password123"})
    assert client.get(f"/estimates/{est.id}").status_code == 404
    assert client.get(f"/estimates/{est.id}/pdf").status_code == 404


def test_delete_estimate(client, user, fake_ai):
    client.post("/login", data={"email": "shop@example.com", "password": "password123"})
    _post_estimate(client)
    est_id = Estimate.query.first().id

    client.post(f"/estimates/{est_id}/delete")
    assert db.session.get(Estimate, est_id) is None


def test_status_toggle(client, user, fake_ai):
    client.post("/login", data={"email": "shop@example.com", "password": "password123"})
    _post_estimate(client)
    est_id = Estimate.query.first().id

    client.post(f"/estimates/{est_id}/status", data={"status": "sent"})
    assert db.session.get(Estimate, est_id).status == "sent"

    client.post(f"/estimates/{est_id}/status", data={"status": "draft"})
    assert db.session.get(Estimate, est_id).status == "draft"


def test_estimate_requires_fields(client, user, fake_ai):
    client.post("/login", data={"email": "shop@example.com", "password": "password123"})
    resp = client.post("/estimates", data={"customer_name": "", "make": "", "model": "", "issue_desc": ""})
    assert resp.status_code == 302
    assert Estimate.query.count() == 0