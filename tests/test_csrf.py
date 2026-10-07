import hashlib
import hmac
import json

from models import User, db


def _sign(payload, secret):
    raw = json.dumps(payload).encode()
    return raw, hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()


def test_post_without_token_rejected(app):
    raw = app.test_client()
    resp = raw.post("/signup", data={
        "email": "csrf@example.com",
        "password": "password123",
        "confirm": "password123",
    })
    assert resp.status_code == 400
    with app.app_context():
        assert User.query.filter_by(email="csrf@example.com").first() is None


def test_post_with_wrong_token_rejected(app):
    raw = app.test_client()
    raw.get("/api/csrf")  # session now has a token
    resp = raw.post("/signup", data={
        "email": "csrf@example.com",
        "password": "password123",
        "confirm": "password123",
        "csrf_token": "totally-wrong-token",
    })
    assert resp.status_code == 400


def test_post_with_valid_token_accepted(app):
    raw = app.test_client()
    token = raw.get("/api/csrf").get_json()["csrf_token"]
    resp = raw.post("/signup", data={
        "email": "csrf@example.com",
        "password": "password123",
        "confirm": "password123",
        "csrf_token": token,
    })
    assert resp.status_code == 302
    with app.app_context():
        assert User.query.filter_by(email="csrf@example.com").first() is not None


def test_webhook_is_csrf_exempt(app, user):
    """Server-to-server webhooks don't have a browser session; signature is the auth."""
    payload = {"meta": {"webhook_id": "wh-csrf-1"}, "data": {"attributes": {"user_email": "shop@example.com"}}}
    raw, sig = _sign(payload, app.config["WEBHOOK_SECRET"])
    resp = app.test_client().post("/billing/webhook", data=raw, headers={"X-Signature": sig})
    assert resp.status_code == 200
    with app.app_context():
        assert db.session.get(User, user.id).plan == "pro"