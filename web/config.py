import os
from pathlib import Path
from dotenv import load_dotenv

# Get the project root directory (parent of web folder)
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env.local"

# Load environment variables (override=True to override shell env vars)
load_dotenv(ENV_PATH, override=True)


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    # Force SQLite database - construct the path properly
    SQLALCHEMY_DATABASE_URI = (
        os.getenv("DATABASE_URL") or f"sqlite:///{BASE_DIR}/bharatquant.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_DISCOVERY_URL = os.getenv("GOOGLE_DISCOVERY_URL")

    STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY")
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

    STRIPE_PRICE_STARTER = os.getenv("STRIPE_PRICE_STARTER")
    STRIPE_PRICE_PRO = os.getenv("STRIPE_PRICE_PRO")
    STRIPE_PRICE_TEAM = os.getenv("STRIPE_PRICE_TEAM")

    BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")
    REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:5000/auth/callback")

    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True") == "True"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
