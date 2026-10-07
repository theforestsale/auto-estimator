import os

from dotenv import load_dotenv
from sqlalchemy.pool import StaticPool

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "auto_estimate.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    AI_API_KEY = os.environ.get("GROQ_API_KEY", "")
    AI_MODEL = os.environ.get("AI_MODEL", "openai/gpt-oss-120b")
    AI_BASE_URL = os.environ.get("AI_BASE_URL", "https://api.groq.com/openai/v1")
    REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "60"))

    SHOP_NAME = os.environ.get("SHOP_NAME", "Your Auto Shop")
    SHOP_PHONE = os.environ.get("SHOP_PHONE", "")
    SHOP_ADDRESS = os.environ.get("SHOP_ADDRESS", "")
    SHOP_EMAIL = os.environ.get("SHOP_EMAIL", "")

    DEFAULT_LABOR_RATE = float(os.environ.get("DEFAULT_LABOR_RATE", "95"))
    DEFAULT_TAX_RATE = float(os.environ.get("DEFAULT_TAX_RATE", "8.0"))

    FREE_PLAN_QUOTA = int(os.environ.get("FREE_PLAN_QUOTA", "3"))
    PRO_CHECKOUT_URL = os.environ.get("PRO_CHECKOUT_URL", "")
    WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

    # Security
    CSRF_ENABLED = os.environ.get("CSRF_ENABLED", "1") == "1"
    RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "1") == "1"
    RATE_LIMIT_GENERATE = int(os.environ.get("RATE_LIMIT_GENERATE", "10"))
    RATE_LIMIT_AUTH = int(os.environ.get("RATE_LIMIT_AUTH", "30"))
    ADMIN_KEY = os.environ.get("ADMIN_KEY", "")

    LOG_FILE = os.path.join(BASE_DIR, "app.log")


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "poolclass": StaticPool,
        "connect_args": {"check_same_thread": False},
    }
    WEBHOOK_SECRET = "test-secret"
    PRO_CHECKOUT_URL = "https://checkout.test/autoestimate-pro"
    DEFAULT_LABOR_RATE = 100.0
    DEFAULT_TAX_RATE = 8.0
    FREE_PLAN_QUOTA = 3
    AI_API_KEY = "test-key"
    ADMIN_KEY = "test-admin-key"