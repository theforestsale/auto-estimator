import csv
import io
import json
import logging
import secrets
from datetime import date, datetime, timedelta

from flask import (
    Blueprint,
    Response,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from models import Estimate, ShareToken, db
from services import ai
from utils.helpers import estimate_totals
from utils.ratelimit import rate_limit

logger = logging.getLogger("estimates")

estimates_bp = Blueprint("estimates", __name__)

MAX_ISSUE_LEN = 2000


def app_config():
    from flask import current_app

    return current_app.config


@estimates_bp.route("/dashboard")
@login_required
def dashboard():
    estimates = Estimate.query.filter_by(user_id=current_user.id).order_by(Estimate.created_at.desc()).all()
    quota = quota_of(app_config())
    used = len(estimates)

    sent_count = 0
    value_quoted = 0.0
    today_count = 0
    week_count = 0
    today = date.today()
    last_week = today - timedelta(days=7)

    makes = {}
    for est in estimates:
        if est.status == "sent":
            sent_count += 1
        try:
            totals = estimate_totals(json.loads(est.ai_json), est.labor_rate, est.tax_rate)
            value_quoted += float(totals["total"])
        except Exception:
            pass
        day = est.created_at.date() if isinstance(est.created_at, datetime) else est.created_at
        if day == today:
            today_count += 1
        if day >= last_week:
            week_count += 1
        makes[est.make] = makes.get(est.make, 0) + 1

    recent_makes = sorted(makes.items(), key=lambda kv: kv[1], reverse=True)[:4]

    return render_template(
        "dashboard.html",
        estimates=estimates,
        used=used,
        quota=quota,
        sent_count=sent_count,
        draft_count=used - sent_count,
        value_quoted=value_quoted,
        today_count=today_count,
        week_count=week_count,
        recent_makes=recent_makes,
    )


@estimates_bp.route("/estimates/export.csv")
@login_required
def export_csv():
    estimates = Estimate.query.filter_by(user_id=current_user.id).order_by(Estimate.created_at.desc()).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["id", "customer", "make", "model", "year", "mileage", "status", "created_at",
         "labor", "parts", "misc", "subtotal", "tax", "total"]
    )
    for est in estimates:
        try:
            t = estimate_totals(json.loads(est.ai_json), est.labor_rate, est.tax_rate)
            labor, parts, misc, subtotal, tax, total = (
                f"{t['labor']:.2f}", f"{t['parts']:.2f}", f"{t['misc']:.2f}",
                f"{t['subtotal']:.2f}", f"{t['tax']:.2f}", f"{t['total']:.2f}",
            )
        except Exception:
            labor = parts = misc = subtotal = tax = total = ""
        writer.writerow(
            [est.id, est.customer_name, est.make, est.model, est.year, est.mileage,
             est.status, est.created_at.strftime("%Y-%m-%d %H:%M"),
             labor, parts, misc, subtotal, tax, total]
        )

    data = buf.getvalue()
    return Response(
        data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=estimates.csv"},
    )


@estimates_bp.route("/new")
@login_required
def new():
    cfg = app_config()
    labor_rate = current_user.labor_rate if current_user.labor_rate is not None else cfg["DEFAULT_LABOR_RATE"]
    tax_rate = current_user.tax_rate if current_user.tax_rate is not None else cfg["DEFAULT_TAX_RATE"]
    return render_template(
        "estimate_form.html",
        labor_rate=labor_rate,
        tax_rate=tax_rate,
    )


@estimates_bp.route("/estimates", methods=["POST"])
@login_required
@rate_limit("generate", 10)
def create():
    cfg = app_config()

    if not current_user.is_pro:
        quota = quota_of(cfg)
        used = Estimate.query.filter_by(user_id=current_user.id).count()
        if used >= quota:
            flash(
                f"You've used all {quota} free estimates. Upgrade to Pro to generate unlimited estimates.",
                "warning",
            )
            return redirect(url_for("billing.upgrade"))

    customer_name = request.form.get("customer_name", "").strip()
    make = request.form.get("make", "").strip()
    model = request.form.get("model", "").strip()
    year = request.form.get("year", "").strip()[:20]
    mileage = request.form.get("mileage", "").strip()[:40]
    issue_desc = request.form.get("issue_desc", "").strip()

    if not customer_name or not make or not model or not issue_desc:
        flash("Customer, make, model, and issue description are required.", "error")
        return redirect(url_for("estimates.new"))

    if len(issue_desc) > MAX_ISSUE_LEN:
        flash("Issue description is too long.", "error")
        return redirect(url_for("estimates.new"))

    if not cfg.get("AI_API_KEY"):
        flash("AI key is not configured. Set GROQ_API_KEY in .env first.", "error")
        return redirect(url_for("estimates.new"))

    try:
        labor_rate = float(request.form.get("labor_rate", cfg["DEFAULT_LABOR_RATE"]))
        tax_rate = float(request.form.get("tax_rate", cfg["DEFAULT_TAX_RATE"]))
    except ValueError:
        labor_rate = cfg["DEFAULT_LABOR_RATE"]
        tax_rate = cfg["DEFAULT_TAX_RATE"]

    try:
        client = ai.get_client(cfg["AI_API_KEY"], cfg["AI_BASE_URL"])
        result = ai.generate_estimate(
            client,
            cfg["AI_MODEL"],
{
                    "make": make,
                    "model": model,
                    "year": year,
                    "mileage": mileage,
                    "issue_desc": issue_desc,
                    "labor_rate": labor_rate,
                },
            timeout=cfg.get("REQUEST_TIMEOUT", 60),
        )
    except ai.AIEstimateError as e:
        logger.error("Estimate generation failed for user %s: %s", current_user.email, e)
        flash(str(e), "error")
        return redirect(url_for("estimates.new"))

    estimate = Estimate(
        user_id=current_user.id,
        customer_name=customer_name,
        make=make,
        model=model,
        year=year,
        mileage=mileage,
        issue_desc=issue_desc,
        labor_rate=labor_rate,
        tax_rate=tax_rate,
        ai_json=json.dumps(result),
    )
    db.session.add(estimate)
    db.session.commit()
    logger.info("Created estimate %s for user %s", estimate.id, current_user.email)

    return redirect(url_for("estimates.view", estimate_id=estimate.id))


@estimates_bp.route("/estimates/<int:estimate_id>")
@login_required
def view(estimate_id):
    estimate = _get_owned(estimate_id)
    token = ShareToken.query.filter_by(estimate_id=estimate.id).first()
    return render_template("estimate_view.html", estimate=estimate, share_token=token)


@estimates_bp.route("/estimates/<int:estimate_id>/duplicate", methods=["POST"])
@login_required
def duplicate(estimate_id):
    original = _get_owned(estimate_id)
    copy = Estimate(
        user_id=current_user.id,
        customer_name=original.customer_name,
        make=original.make,
        model=original.model,
        year=original.year,
        mileage=original.mileage,
        issue_desc=original.issue_desc,
        labor_rate=original.labor_rate,
        tax_rate=original.tax_rate,
        ai_json=original.ai_json,
        status="draft",
    )
    db.session.add(copy)
    db.session.commit()
    flash("Estimate duplicated as a draft.", "success")
    return redirect(url_for("estimates.view", estimate_id=copy.id))


@estimates_bp.route("/estimates/<int:estimate_id>/share", methods=["POST"])
@login_required
def create_share(estimate_id):
    estimate = _get_owned(estimate_id)
    token = ShareToken.query.filter_by(estimate_id=estimate.id).first()
    if not token:
        token = ShareToken(estimate_id=estimate.id, token=secrets.token_hex(16))
        db.session.add(token)
        db.session.commit()
    return redirect(url_for("estimates.view", estimate_id=estimate.id))


@estimates_bp.route("/estimates/<int:estimate_id>/share/revoke", methods=["POST"])
@login_required
def revoke_share(estimate_id):
    estimate = _get_owned(estimate_id)
    ShareToken.query.filter_by(estimate_id=estimate.id).delete()
    db.session.commit()
    flash("Share link revoked.", "success")
    return redirect(url_for("estimates.view", estimate_id=estimate.id))


@estimates_bp.route("/s/<token>")
def share_view(token):
    share = ShareToken.query.filter_by(token=token).first()
    if not share:
        abort(404)
    estimate = db.session.get(Estimate, share.estimate_id)
    if not estimate:
        abort(404)
    owner = estimate.owner
    cfg = app_config()
    shop = {
        "name": owner.shop_name or cfg["SHOP_NAME"],
        "phone": owner.shop_phone or cfg["SHOP_PHONE"],
        "email": cfg.get("SHOP_EMAIL", ""),
        "address": owner.shop_address or cfg["SHOP_ADDRESS"],
    }
    return render_template("share_view.html", estimate=estimate, shop=shop)


@estimates_bp.route("/estimates/<int:estimate_id>/pdf")
@login_required
def pdf(estimate_id):
    estimate = _get_owned(estimate_id)
    from services.pdf import render_estimate_pdf

    cfg = app_config()
    shop = {
        "name": current_user.shop_name or cfg["SHOP_NAME"],
        "phone": current_user.shop_phone or cfg["SHOP_PHONE"],
        "email": cfg["SHOP_EMAIL"],
        "address": current_user.shop_address or cfg["SHOP_ADDRESS"],
    }
    try:
        data = render_estimate_pdf(estimate, shop)
    except Exception as e:
        logger.error("PDF render failed for estimate %s: %s", estimate_id, e)
        abort(500)

    return Response(
        data,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=estimate_{estimate_id}.pdf"},
    )


@estimates_bp.route("/estimates/<int:estimate_id>/delete", methods=["POST"])
@login_required
def delete(estimate_id):
    estimate = _get_owned(estimate_id)
    ShareToken.query.filter_by(estimate_id=estimate.id).delete()
    db.session.delete(estimate)
    db.session.commit()
    flash("Estimate deleted.", "success")
    return redirect(url_for("estimates.dashboard"))


@estimates_bp.route("/estimates/<int:estimate_id>/status", methods=["POST"])
@login_required
def set_status(estimate_id):
    estimate = _get_owned(estimate_id)
    new_status = request.form.get("status", "draft")
    estimate.status = "sent" if new_status == "sent" else "draft"
    db.session.commit()
    return redirect(url_for("estimates.view", estimate_id=estimate.id))


def _get_owned(estimate_id):
    estimate = db.session.get(Estimate, estimate_id)
    if not estimate or estimate.user_id != current_user.id:
        abort(404)
    return estimate


def quota_of(cfg):
    return int(cfg.get("FREE_PLAN_QUOTA", 3))