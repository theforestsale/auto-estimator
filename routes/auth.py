import logging

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from models import User, db
from utils.ratelimit import rate_limit

logger = logging.getLogger("auth")

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/signup", methods=["GET", "POST"])
@rate_limit("auth", 30)
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("estimates.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not email or "@" not in email or "." not in email:
            flash("Please enter a valid email address.", "error")
        elif len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        elif User.query.filter_by(email=email).first():
            flash("An account with that email already exists. Sign in instead.", "error")
        else:
            user = User(email=email, password_hash=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Welcome! Your account is ready.", "success")
            return redirect(url_for("estimates.dashboard"))

    return render_template("auth.html", action="signup",
                           heading="Create your account",
                           button="Create account")


@auth_bp.route("/login", methods=["GET", "POST"])
@rate_limit("auth", 30)
def login():
    if current_user.is_authenticated:
        return redirect(url_for("estimates.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            next_url = request.args.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(url_for("estimates.dashboard"))

        flash("Incorrect email or password.", "error")

    return render_template("auth.html", action="login",
                           heading="Welcome back",
                           button="Sign in")


@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("main.index"))