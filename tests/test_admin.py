from models import User, db


def test_admin_hidden_without_key(app):
    app.config["ADMIN_KEY"] = ""
    resp = app.test_client().get("/admin")
    assert resp.status_code == 404


def test_admin_requires_key(client):
    resp = client.get("/admin")
    assert b"Admin key" in resp.data

    resp = client.post("/admin/login", data={"admin_key": "wrong-key"}, follow_redirects=True)
    assert b"Invalid admin key" in resp.data
    assert b"Admin key" in client.get("/admin").data  # still locked


def test_admin_activate_flow(app, client, user):
    resp = client.post("/admin/login", data={"admin_key": app.config["ADMIN_KEY"]})
    assert resp.status_code == 302
    assert b"Customer email" in client.get("/admin").data

    resp = client.post("/admin/activate", data={"email": "shop@example.com", "plan": "pro"})
    db.session.expire_all()
    assert db.session.get(User, user.id).plan == "pro"

    resp = client.post("/admin/activate", data={"email": "shop@example.com", "plan": "free"})
    db.session.expire_all()
    assert db.session.get(User, user.id).plan == "free"


def test_admin_unknown_email(client, user):
    client.post("/admin/login", data={"admin_key": "test-admin-key"})
    resp = client.post("/admin/activate", data={"email": "nobody@x.com", "plan": "pro"}, follow_redirects=True)
    assert b"No account found" in resp.data


def test_activate_requires_authenticated_admin(app, client, user):
    # Don't log into admin: activation must be rejected.
    resp = client.post("/admin/activate", data={"email": "shop@example.com", "plan": "pro"})
    assert resp.status_code == 403
    db.session.expire_all()
    assert db.session.get(User, user.id).plan == "free"