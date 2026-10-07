import hmac
import secrets

from flask import abort, current_app, request, session
from markupsafe import Markup

TOKEN_SESSION_KEY = "csrf_token"
CSRF_EXEMPT_ENDPOINTS = {"billing.webhook"}


def generate_token():
    token = session.get(TOKEN_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[TOKEN_SESSION_KEY] = token
    return token


def csrf_field():
    return Markup(f'<input type="hidden" name="csrf_token" value="{generate_token()}">')


def _provided():
    token = request.form.get("csrf_token")
    if not token:
        token = request.headers.get("X-CSRF-Token", "")
    return token or ""


def _valid(expected, provided):
    return bool(expected) and hmac.compare_digest(expected, provided)


def protect():
    if not current_app.config.get("CSRF_ENABLED", True):
        return
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return
    if request.endpoint in CSRF_EXEMPT_ENDPOINTS:
        return
    if not _valid(session.get(TOKEN_SESSION_KEY, ""), _provided()):
        abort(400, "Invalid or missing CSRF token")