import logging

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for

from models import User, db
from utils.ratelimit import rate_limit

logger = logging.getLogger("admin")

admin_bp = Blueprint("admin", __name__)

ADMIN_SESSION_KEY = "admin_authed"


def _ensure_enabled():
    if not current_app.config.get("ADMIN_KEY"):
        abort(404)


def _is_authed():
    return bool(session.get(ADMIN_SESSION_KEY))


@admin_bp.before_request
def _gate():
    _ensure_enabled()
    if request.endpoint == "admin.login" or _is_authed():
        return
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.endpoint != "admin.activate":
        abort(403)


@admin_bp.route("/admin/login", methods=["POST"])
@rate_limit("auth", 30)
def login():
    key = request.form.get("admin_key", "")
    if key and _safe_equals(key, current_app.config["ADMIN_KEY"]):
        session[ADMIN_SESSION_KEY] = True
        return redirect(url_for("admin.panel"))
    flash("Invalid admin key.", "error")
    return redirect(url_for("admin.panel"))


@admin_bp.route("/admin", methods=["GET"])
def panel():
    return render_template("admin.html", authed=_is_authed())


@admin_bp.route("/admin/logout", methods=["POST"])
def logout():
    session.pop(ADMIN_SESSION_KEY, None)
    return redirect(url_for("admin.panel"))


@admin_bp.route("/admin/activate", methods=["POST"])
def activate():
    if not _is_authed():
        abort(403)

    email = request.form.get("email", "").strip().lower()
    plan = request.form.get("plan", "pro")
    if plan not in ("pro", "free"):
        flash("Invalid plan.", "error")
        return redirect(url_for("admin.panel"))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash(f"No account found for {email}.", "error")
        return redirect(url_for("admin.panel"))

    user.plan = plan
    db.session.commit()
    logger.info("Admin set %s to %s", email, plan)
    flash(f"{email} is now {plan}.", "success")
    return redirect(url_for("admin.panel"))


def _safe_equals(a, b):
    import hmac

    return hmac.compare_digest(str(a), str(b))