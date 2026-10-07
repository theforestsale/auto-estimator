import hashlib
import hmac
import json

from models import User, db


def _sign(payload, secret):
    raw = json.dumps(payload).encode()
    return raw, hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()


def test_webhook_upgrades_user(client, app, user):
    payload = {
        "meta": {"event_name": "subscription_created", "webhook_id": "wh-123"},
        "data": {"attributes": {"user_email": "shop@example.com"}},
    }
    raw, sig = _sign(payload, app.config["WEBHOOK_SECRET"])
    resp = client.post("/billing/webhook", data=raw, headers={"X-Signature": sig})
    assert resp.status_code == 200
    db.session.expire_all()
    assert db.session.get(User, user.id).plan == "pro"


def test_webhook_rejects_bad_signature(client, app, user):
    payload = {"meta": {"webhook_id": "wh-1"}, "data": {"attributes": {"user_email": "shop@example.com"}}}
    raw = json.dumps(payload).encode()
    resp = client.post("/billing/webhook", data=raw, headers={"X-Signature": "deadbeef"})
    assert resp.status_code == 403
    db.session.expire_all()
    assert db.session.get(User, user.id).plan == "free"


def test_webhook_deduplicates(client, app, user):
    payload = {"meta": {"webhook_id": "wh-dupe"}, "data": {"attributes": {"user_email": "shop@example.com"}}}
    raw, sig = _sign(payload, app.config["WEBHOOK_SECRET"])
    assert client.post("/billing/webhook", data=raw, headers={"X-Signature": sig}).status_code == 200
    assert client.post("/billing/webhook", data=raw, headers={"X-Signature": sig}).status_code == 200
    db.session.expire_all()
    assert db.session.get(User, user.id).plan == "pro"


def test_webhook_stripe_style(client, app, user):
    payload = {
        "type": "checkout.session.completed",
        "data": {"object": {"id": "cs_1", "customer_email": "shop@example.com"}},
    }
    raw, sig = _sign(payload, app.config["WEBHOOK_SECRET"])
    assert client.post("/billing/webhook", data=raw, headers={"X-Signature": sig}).status_code == 200
    db.session.expire_all()
    assert db.session.get(User, user.id).plan == "pro"


def test_webhook_unknown_user(client, app):
    payload = {"meta": {"webhook_id": "wh-x"}, "data": {"attributes": {"user_email": "nobody@x.com"}}}
    raw, sig = _sign(payload, app.config["WEBHOOK_SECRET"])
    assert client.post("/billing/webhook", data=raw, headers={"X-Signature": sig}).status_code == 404


def test_webhook_missing_secret_rejected(client, user):
    # When WEBHOOK_SECRET set, missing X-Signature must be rejected.
    payload = {"meta": {"webhook_id": "wh-nosig"}, "data": {"attributes": {"user_email": "shop@example.com"}}}
    resp = client.post("/billing/webhook", data=json.dumps(payload).encode())
    assert resp.status_code == 403