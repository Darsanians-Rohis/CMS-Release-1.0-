import os
from dotenv import load_dotenv

load_dotenv()


def _normalise_db_url(url: str) -> str:
    """Heroku / Render ships postgres://, SQLAlchemy needs postgresql://"""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url and "sslmode" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")

    _raw_db = os.environ.get("DATABASE_URL", "")
    SQLALCHEMY_DATABASE_URI = _normalise_db_url(_raw_db) if _raw_db else None
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "connect_args": {"sslmode": "require"},
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:8080")

    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    CRON_SECRET_TOKEN = os.environ.get("CRON_SECRET_TOKEN")

    # Mailjet
    MAILJET_API_KEY = os.environ.get("MAILJET_API_KEY")
    MAILJET_SECRET_KEY = os.environ.get("MAILJET_SECRET_KEY")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER")
