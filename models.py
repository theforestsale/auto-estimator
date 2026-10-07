from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    plan = db.Column(db.String(20), nullable=False, default="free")
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

    labor_rate = db.Column(db.Float, nullable=True)
    tax_rate = db.Column(db.Float, nullable=True)
    shop_name = db.Column(db.String(200), nullable=False, default="")
    shop_phone = db.Column(db.String(50), nullable=False, default="")
    shop_address = db.Column(db.String(300), nullable=False, default="")

    estimates = db.relationship(
        "Estimate",
        backref="owner",
        lazy="select",
        cascade="all, delete-orphan",
        order_by="Estimate.created_at.desc()",
    )

    @property
    def is_pro(self):
        return self.plan == "pro"

    def has_rates(self):
        return self.labor_rate is not None or self.tax_rate is not None


class Estimate(db.Model):
    __tablename__ = "estimates"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    customer_name = db.Column(db.String(200), nullable=False)
    make = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    year = db.Column(db.String(20), nullable=False, default="")
    mileage = db.Column(db.String(40), nullable=False, default="")
    issue_desc = db.Column(db.Text, nullable=False)
    labor_rate = db.Column(db.Float, nullable=False)
    tax_rate = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="draft")
    ai_json = db.Column(db.Text, nullable=False, default="{}")
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )


class ShareToken(db.Model):
    __tablename__ = "share_tokens"

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    estimate_id = db.Column(db.Integer, db.ForeignKey("estimates.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

    estimate = db.relationship("Estimate")


class BillingEvent(db.Model):
    __tablename__ = "billing_events"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(200), unique=True, nullable=False, index=True)
    provider = db.Column(db.String(50), nullable=False, default="generic")
    payload_json = db.Column(db.Text, nullable=False, default="{}")
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())