import os
from urllib.parse import urlparse

class Config:
    DATABASE_URL = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("MYSQL_URL")
        or os.environ.get("POSTGRES_URL")
        or os.environ.get("JAWSDB_URL")
        or os.environ.get("CLEARDB_DATABASE_URL")
        or os.environ.get("PLANETSCALE_DATABASE_URL")
        or ""
    )

    if DATABASE_URL:
        url = urlparse(DATABASE_URL)
        MYSQL_HOST = url.hostname or "localhost"
        MYSQL_PORT = url.port or (3306 if "mysql" in (url.scheme or "") else 5432)
        MYSQL_USER = url.username or "root"
        MYSQL_PASSWORD = url.password or ""
        MYSQL_DB = url.path.lstrip("/") or "recoverai"
    else:
        MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
        try:
            MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
        except (ValueError, TypeError):
            MYSQL_PORT = 3306
        MYSQL_USER = os.environ.get("MYSQL_USER", "root")
        MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "Pr@290105")
        MYSQL_DB = os.environ.get("MYSQL_DB", "recoverai")

    # Razorpay (wire up real keys via Settings page / env vars)
    RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")
    RAZORPAY_WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")

    # Gemini AI (used by the AI Recovery Agent to score + draft messages)
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
