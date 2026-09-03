import os

class Config:
    # MySQL connection settings — override with environment variables in production
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
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
