from models import Estimate, ShareToken, User, db


def _make(client, user):
    client.post("/estimates", data={
        "customer_name": "John Smith",
        "make": "Toyota",
        "model": "Camry",
        "year": "2016",
        "issue_desc": "Squealing when braking.",
        "labor_rate": "95",
        "tax_rate": "8",
    })
    return Estimate.query.first()


def test_duplicate_creates_draft_copy(client, user, fake_ai):
    client.post("/login", data={"email": "shop@example.com", "password": "password123"})
    est = _make(client, user)
    est.status = "sent"
    db.session.commit()

    resp = client.post(f"/estimates/{est.id}/duplicate")
    assert resp.status_code == 302

    copies = Estimate.query.filter(Estimate.id != est.id).all()
    assert len(copies) == 1
    copy = copies[0]
    assert copy.customer_name == est.customer_name
    assert copy.ai_json == est.ai_json
    assert copy.status == "draft"
    assert copy.user_id == user.id


def test_settings_saves_rates_and_shop(client, user):
    client.post("/login", data={"email": "shop@example.com", "password": "password123"})
    body = client.get("/settings").data
    assert b"Settings" in body

    client.post("/settings", data={
        "labor_rate": "110",
        "tax_rate": "8.5",
        "shop_name": "Al's Garage",
        "shop_phone": "555-0100",
        "shop_address": "1 Main St",
    })
    db.session.refresh(user)
    assert user.labor_rate == 110
    assert user.tax_rate == 8.5
    assert user.shop_name == "Al's Garage"

    client.post("/login", data={"email": "shop@example.com", "password": "password123"}, follow_redirects=False)
    form = client.get("/new").data
    assert b'name="labor_rate" value="110.0"' in form


def test_share_link_public_and_revocable(client, user, fake_ai):
    client.post("/login", data={"email": "shop@example.com", "password": "password123"})
    est = _make(client, user)

    assert client.get(f"/s/does-not-exist").status_code == 404

    client.post(f"/estimates/{est.id}/share")
    token = ShareToken.query.first()
    assert token is not None
    assert token.estimate_id == est.id

    public = client.get(f"/s/{token.token}")
    assert public.status_code == 200
    assert b"John Smith" in public.data
    assert b"Estimated total" in public.data

    client.post(f"/estimates/{est.id}/share/revoke")
    assert ShareToken.query.count() == 0
    assert client.get(f"/s/{token.token}").status_code == 404


def test_share_ownership_scoped(client, user, fake_ai):
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
    assert client.post(f"/estimates/{est.id}/share").status_code == 404
    assert client.post(f"/estimates/{est.id}/duplicate").status_code == 404


def test_new_uses_saved_rates(client, user):
    user.labor_rate = 120.0
    user.tax_rate = 9.0
    db.session.commit()
    client.post("/login", data={"email": "shop@example.com", "password": "password123"})

    form = client.get("/new").data
    assert b'name="labor_rate" value="120.0"' in form
    assert b'name="tax_rate" value="9.0"' in form