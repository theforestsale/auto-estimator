import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from config import TestConfig
from models import User, db
from utils.ratelimit import reset_ratelimit


class CSRFClient:
    """Test client that auto-fetches and injects a CSRF token into form POSTs."""

    def __init__(self, inner):
        self._inner = inner

    def post(self, url, *args, **kwargs):
        data = kwargs.get("data")
        if data is None or isinstance(data, dict):
            token = self._inner.get("/api/csrf").get_json()["csrf_token"]
            if isinstance(data, dict):
                if "csrf_token" not in data:
                    kwargs["data"] = {**data, "csrf_token": token}
            else:
                kwargs["data"] = {"csrf_token": token}
        return self._inner.post(url, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._inner, name)


@pytest.fixture
def app():
    application = create_app(TestConfig)
    reset_ratelimit()
    with application.app_context():
        yield application
    with application.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return CSRFClient(app.test_client())


@pytest.fixture
def user():
    u = User(email="shop@example.com", password_hash=generate_password_hash("password123"))
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def logged_client(client, user):
    client.post("/login", data={"email": "shop@example.com", "password": "password123"})
    return client


@pytest.fixture
def fake_ai(monkeypatch):
    payload = {
        "diagnosis": "Worn brake pads causing the squeal.",
        "customer_message": "Your brakes need new pads soon.",
        "recommended_work": [
            {"item": "Front brake pad replacement", "category": "labor", "quantity": 2.0,
             "unit_label": "hr(s)", "unit_price": 100.0},
            {"item": "Brake pads (front set)", "category": "parts", "quantity": 1.0,
             "unit_label": "ea", "unit_price": 60.0},
            {"item": "Shop supplies", "category": "misc", "quantity": 1.0,
             "unit_label": "job", "unit_price": 12.5},
        ],
        "parts": [{"name": "Front brake pad set", "est_price": 60.0}],
        "notes": ["Final price depends on inspection."],
    }
    monkeypatch.setattr("services.ai.get_client", lambda *a, **k: object())
    monkeypatch.setattr("services.ai.generate_estimate", lambda *a, **k: payload)
    return payload