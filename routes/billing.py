import hashlib
import hmac
import json
import logging

from flask import Blueprint, current_app, jsonify, render_template, request
from flask_login import current_user

from models import BillingEvent, User, db

logger = logging.getLogger("billing")

billing_bp = Blueprint("billing", __name__)


@billing_bp.route("/upgrade")
def upgrade():
    quota = int(current_app.config.get("FREE_PLAN_QUOTA", 3))
    if not current_user.is_authenticated:
        return render_template("upgrade.html", checkout_url="", signed_in=False, quota=quota)
    return render_template(
        "upgrade.html",
        checkout_url=current_app.config["PRO_CHECKOUT_URL"],
        signed_in=True,
        quota=quota,
    )


@billing_bp.route("/billing/webhook", methods=["POST"])
def webhook():
    cfg = current_app.config
    raw = request.get_data(cache=True)

    if cfg.get("WEBHOOK_SECRET"):
        signature = request.headers.get("X-Signature", "")
        if not _valid_signature(signature, raw, cfg["WEBHOOK_SECRET"]):
            logger.warning("Rejected webhook with invalid signature")
            return jsonify({"ok": False, "error": "invalid signature"}), 403
    elif not cfg.get("TESTING"):
        logger.warning("WEBHOOK_SECRET not set; accepting webhook without verification")

    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "invalid json"}), 400

    event_id, email = _extract_event(payload)

    if not event_id or not email:
        logger.warning("Webhook missing event id or email: %s", str(payload)[:300])
        return jsonify({"ok": False, "error": "missing event data"}), 400

    if BillingEvent.query.filter_by(event_id=event_id).first():
        return jsonify({"ok": True, "duplicate": True}), 200

    user = User.query.filter_by(email=email.lower()).first()
    if user is None:
        logger.info("Webhook for unknown email %s; creating account placeholder is disabled", email)
        return jsonify({"ok": False, "error": "unknown user"}), 404

    user.plan = "pro"
    db.session.add(BillingEvent(event_id=event_id, provider="webhook", payload_json=json.dumps(payload)))
    db.session.commit()
    logger.info("Upgraded user %s via webhook %s", email, event_id)
    return jsonify({"ok": True}), 200


def _valid_signature(signature, raw_body, secret):
    if not signature:
        return False
    if signature.startswith("t="):
        computed = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        for part in signature.split(","):
            if part.startswith("v1=") and hmac.compare_digest(part[3:], computed):
                return True
        return False
    computed = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, computed)


def _extract_event(payload):
    """Work across Lemon Squeezy, Stripe, and generic webhooks."""
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}

    if isinstance(payload.get("meta"), dict):
        meta = payload["meta"]
        event_id = meta.get("webhook_id") or meta.get("event_id")
        attrs = data.get("attributes") if isinstance(data.get("attributes"), dict) else {}
        email = attrs.get("user_email") or attrs.get("customer_email") or attrs.get("email")
        if event_id and email:
            return event_id, email

    # Stripe-style: {"type": "checkout.session.completed", "data": {"object": {...}}}
    if payload.get("type"):
        obj = data.get("object") if isinstance(data.get("object"), dict) else {}
        email = obj.get("customer_email") or data.get("customer_email")
        return f"stripe:{payload['type']}:{obj.get('id') or ''}", email

    return data.get("id"), (data.get("customer_email") or data.get("user_email") or data.get("email"))