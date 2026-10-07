import logging

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import db

logger = logging.getLogger("settings")

settings_bp = Blueprint("settings", __name__)


def _opt_float(raw, default=None):
    try:
        value = float(raw)
        return value if value > 0 else default
    except (TypeError, ValueError):
        return default


@settings_bp.route("/settings", methods=["GET", "POST"])
@login_required
def page():
    if request.method == "POST":
        current_user.labor_rate = _opt_float(request.form.get("labor_rate"))
        current_user.tax_rate = _opt_float(request.form.get("tax_rate"))
        current_user.shop_name = request.form.get("shop_name", "").strip()[:200]
        current_user.shop_phone = request.form.get("shop_phone", "").strip()[:50]
        current_user.shop_address = request.form.get("shop_address", "").strip()[:300]
        db.session.commit()
        flash("Settings saved.", "success")
        return redirect(url_for("settings.page"))

    defaults = {
        "labor_rate": current_user.labor_rate if current_user.labor_rate is not None else current_app.config["DEFAULT_LABOR_RATE"],
        "tax_rate": current_user.tax_rate if current_user.tax_rate is not None else current_app.config["DEFAULT_TAX_RATE"],
    }
    return render_template("settings.html", defaults=defaults)