from models import User, db


def test_signup_creates_user_and_logs_in(client):
    resp = client.post("/signup", data={
        "email": "new@shop.com",
        "password": "password123",
        "confirm": "password123",
    })
    assert resp.status_code == 302
    with client.application.app_context():
        user = User.query.filter_by(email="new@shop.com").first()
        assert user is not None
        assert user.plan == "free"


def test_signup_rejects_duplicate(client, user):
    resp = client.post("/signup", data={
        "email": "shop@example.com",
        "password": "password123",
        "confirm": "password123",
    })
    assert b"already exists" in resp.data


def test_signup_requires_matching_passwords(client):
    resp = client.post("/signup", data={
        "email": "x@shop.com",
        "password": "password123",
        "confirm": "password124",
    })
    assert b"do not match" in resp.data


def test_login_and_logout(client, user):
    resp = client.post("/login", data={"email": "shop@example.com", "password": "password123"})
    assert resp.status_code == 302
    assert "/dashboard" in resp.headers["Location"]

    logged = client.get("/dashboard")
    assert b"shop@example.com" in logged.data

    client.get("/logout")
    resp = client.get("/dashboard")
    assert resp.status_code == 302


def test_login_wrong_password(client, user):
    resp = client.post("/login", data={"email": "shop@example.com", "password": "wrongpass"})
    assert b"Incorrect email or password" in resp.data