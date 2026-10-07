from pathlib import Path

from flask import Blueprint, jsonify, redirect, render_template, send_from_directory, url_for
from flask_login import current_user

main_bp = Blueprint("main", __name__)

AVATAR_DIR = Path(__file__).resolve().parent.parent.parent / "clothing-avatar"


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("estimates.dashboard"))
    return render_template("index.html")


@main_bp.route("/avatar")
@main_bp.route("/avatar/<path:filename>")
def avatar_app(filename=None):
    resp = send_from_directory(AVATAR_DIR, filename or "index.html")
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@main_bp.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@main_bp.route("/api/csrf")
def csrf():
    """Return a fresh CSRF token for AJAX/forms (also set by server-rendered forms)."""
    from utils.csrf import generate_token

    return jsonify({"csrf_token": generate_token()})