import json

import click
from flask import Flask
from flask_login import LoginManager
from sqlalchemy import text

from config import Config
from models import db
from utils.csrf import csrf_field, protect
from utils.helpers import estimate_totals, money
from utils.logging_config import setup_logging

login_manager = LoginManager()

USER_COLUMN_MIGRATIONS = [
    ("labor_rate", "FLOAT"),
    ("tax_rate", "FLOAT"),
    ("shop_name", "VARCHAR(200) DEFAULT ''"),
    ("shop_phone", "VARCHAR(50) DEFAULT ''"),
    ("shop_address", "VARCHAR(300) DEFAULT ''"),
]


def ensure_migrations(app):
    """Add columns introduced after the first deploy to an existing SQLite DB."""
    with app.app_context():
        inspector_cols = db.session.execute(text("PRAGMA table_info(users)")).fetchall()
        existing = {row[1] for row in inspector_cols}
        missing = [(name, dtype) for name, dtype in USER_COLUMN_MIGRATIONS if name not in existing]
        if missing:
            for name, dtype in missing:
                db.session.execute(text(f'ALTER TABLE users ADD COLUMN "{name}" {dtype}'))
            db.session.commit()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    app.jinja_env.filters["money"] = money
    app.jinja_env.filters["from_json"] = lambda s: json.loads(s if s else "{}")
    app.jinja_env.filters["totals"] = estimate_totals
    app.jinja_env.globals["csrf_field"] = csrf_field

    app.before_request(protect)

    @app.context_processor
    def inject_admin():
        return {"admin_enabled": bool(app.config.get("ADMIN_KEY"))}

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to continue."
    login_manager.login_message_category = "warning"

    with app.app_context():
        db.create_all()
    ensure_migrations(app)

    logging_listener = setup_logging(app)
    app.extensions["log_listener"] = logging_listener

    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.estimates import estimates_bp
    from routes.billing import billing_bp
    from routes.admin import admin_bp
    from routes.settings import settings_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(estimates_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(settings_bp)

    register_cli(app)

    return app


def register_cli(app):
    @app.cli.command("upgrade-user")
    @click.argument("email")
    def upgrade_user(email):
        """Manually activate the paid plan for a user (used for testing / manual activation)."""
        from models import User

        with app.app_context():
            user = User.query.filter_by(email=email).first()
            if not user:
                raise click.ClickException(f"No user found with email: {email}")
            user.plan = "pro"
            db.session.commit()
            click.echo(f"Upgraded {user.email} to pro.")

    @app.cli.command("downgrade-user")
    @click.argument("email")
    def downgrade_user(email):
        """Reset a user back to the free plan."""
        from models import User

        with app.app_context():
            user = User.query.filter_by(email=email).first()
            if not user:
                raise click.ClickException(f"No user found with email: {email}")
            user.plan = "free"
            db.session.commit()
            click.echo(f"Downgraded {user.email} to free.")


@login_manager.user_loader
def load_user(user_id):
    from models import User

    return db.session.get(User, int(user_id))


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)