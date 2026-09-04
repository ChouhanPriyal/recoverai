"""
RecoverAI — AI Revenue Recovery Agent
Flask backend serving the dashboard UI and a JSON API backed by MySQL.

Core product flow:
Razorpay Payment Failure -> AI Analysis -> Recovery Score -> AI Decision -> Recovery Action -> Revenue Recovered
"""
import os
import pymysql
import pymysql.cursors
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, g

from config import Config

app = Flask(__name__)
app.config.from_object(Config)


# ---------------------------------------------------------------------------
# Database helpers (Universal Dual-Driver: MySQL + SQLite Fallback)
# ---------------------------------------------------------------------------
import re
import sqlite3

DB_MODE = "mysql"


def init_sqlite_db(conn):
    """Initializes schema and seeds dynamic data with relative timestamps into SQLite."""
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT,
        total_spent REAL DEFAULT 0,
        successful_payments INTEGER DEFAULT 0,
        failed_payments INTEGER DEFAULT 0,
        avg_order REAL DEFAULT 0,
        risk_level TEXT DEFAULT 'Low',
        repeat_customer INTEGER DEFAULT 0,
        last_payment_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        razorpay_payment_id TEXT NOT NULL,
        customer_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        failure_reason TEXT NOT NULL,
        attempts INTEGER DEFAULT 1,
        recovery_score INTEGER DEFAULT 0,
        status TEXT DEFAULT 'Low',
        recovery_state TEXT DEFAULT 'Pending',
        failed_at DATETIME NOT NULL,
        recovered_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS agent_activity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        payment_id INTEGER NOT NULL,
        activity TEXT NOT NULL,
        activity_type TEXT DEFAULT 'analysis',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ai_recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        payment_id INTEGER NOT NULL,
        strategy TEXT NOT NULL,
        reasoning TEXT,
        message_draft TEXT,
        confidence INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS campaigns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        target_audience TEXT,
        strategy TEXT,
        customer_count INTEGER DEFAULT 0,
        potential_revenue REAL DEFAULT 0,
        recovered_revenue REAL DEFAULT 0,
        status TEXT DEFAULT 'Draft',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS campaign_payments (
        campaign_id INTEGER NOT NULL,
        payment_id INTEGER NOT NULL,
        PRIMARY KEY (campaign_id, payment_id)
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        setting_key TEXT PRIMARY KEY,
        setting_value TEXT NOT NULL,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM customers")
    if cur.fetchone()[0] == 0:
        now = datetime.now()
        customers_data = [
            ("Priya Sharma", "priya@email.com", "+91 90000 10001", 42500, 14, 2, 3035, "Low", 1, (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")),
            ("Rahul Verma", "rahul@email.com", "+91 90000 10002", 38160, 12, 3, 3180, "Medium", 1, (now - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")),
            ("Aman Singh", "aman@email.com", "+91 90000 10003", 12990, 8, 3, 1623, "High", 0, (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")),
            ("Sneha Patel", "sneha@email.com", "+91 90000 10004", 65230, 16, 1, 4077, "Low", 1, (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")),
            ("Karan Mehta", "karan@email.com", "+91 90000 10005", 21450, 10, 2, 2145, "Medium", 0, (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")),
            ("Neha Gupta", "neha@email.com", "+91 90000 10006", 18300, 7, 2, 2614, "Medium", 0, (now - timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S")),
            ("Vikram Raj", "vikram@email.com", "+91 90000 10007", 27650, 9, 3, 3072, "High", 0, (now - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")),
        ]
        cur.executemany(
            "INSERT INTO customers (name, email, phone, total_spent, successful_payments, failed_payments, avg_order, risk_level, repeat_customer, last_payment_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            customers_data,
        )

        payments_data = [
            ("pay_Qw12ErX9", 1, 2999, "Bank Declined", 1, 91, "High", "Pending", (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"), None),
            ("pay_Lk34PoY8", 2, 5499, "Network Error", 2, 76, "Medium", "Pending", (now - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S"), None),
            ("pay_Zx56MnB2", 3, 1299, "Authentication Failed", 3, 32, "Low", "Pending", (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"), None),
            ("pay_Po98LmN3", 4, 8999, "Bank Declined", 1, 94, "High", "Recovered", (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"), (now - timedelta(days=2, hours=-1)).strftime("%Y-%m-%d %H:%M:%S")),
            ("pay_Ax9OQpQ7", 5, 4499, "Insufficient Funds", 2, 66, "Medium", "Pending", (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S"), None),
            ("pay_Bn23QwE1", 6, 2249, "Bank Declined", 1, 89, "High", "Pending", (now - timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S"), None),
            ("pay_Xc76UlM4", 7, 6499, "Network Error", 2, 58, "Medium", "Pending", (now - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S"), None),
        ]
        cur.executemany(
            "INSERT INTO payments (razorpay_payment_id, customer_id, amount, failure_reason, attempts, recovery_score, status, recovery_state, failed_at, recovered_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            payments_data,
        )

        activities = [
            (1, "Payment failed received from Razorpay", "analysis", (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")),
            (1, "Customer history analyzed", "analysis", (now - timedelta(hours=1, minutes=59)).strftime("%Y-%m-%d %H:%M:%S")),
            (1, "Recovery probability calculated (91%)", "analysis", (now - timedelta(hours=1, minutes=58)).strftime("%Y-%m-%d %H:%M:%S")),
            (1, "Best strategy selected: Payment Retry", "decision", (now - timedelta(hours=1, minutes=57)).strftime("%Y-%m-%d %H:%M:%S")),
            (1, "Personalized message generated", "action", (now - timedelta(hours=1, minutes=56)).strftime("%Y-%m-%d %H:%M:%S")),
        ]
        cur.executemany(
            "INSERT INTO agent_activity (payment_id, activity, activity_type, created_at) VALUES (?,?,?,?)",
            activities,
        )

        cur.execute("""
        INSERT INTO ai_recommendations (payment_id, strategy, reasoning, message_draft, confidence) VALUES
        (1, 'Payment Retry', 'Customer has strong payment history (14 successful out of 16). High lifetime value customer.', 'Hi Priya, we noticed your last payment of ₹2,999 did not go through. Please retry using a different card or UPI.', 91)
        """)

        campaigns_data = [
            ("High Value Recovery", "Payments above ₹5,000", "Payment Retry", 127, 812000, 306000, "Running"),
            ("24h Reminder Campaign", "Payments made < 24h", "Smart Reminder", 249, 213000, 88000, "Running"),
            ("Weekend Recovery", "Weekend Failures", "Reminder + Offer", 358, 154000, 54000, "Completed"),
            ("Low Value Recovery", "Payments under ₹1,000", "Smart Reminder", 358, 268000, 42000, "Running"),
            ("New Customer Recovery", "First-time Failures", "Personalized Retry", 156, 126000, 0, "Draft"),
        ]
        cur.executemany(
            "INSERT INTO campaigns (name, target_audience, strategy, customer_count, potential_revenue, recovered_revenue, status) VALUES (?,?,?,?,?,?,?)",
            campaigns_data,
        )

        settings_data = [
            ("auto_analyze_failed_payments", "true"),
            ("prioritize_high_value", "true"),
            ("automated_reminders", "true"),
            ("automated_recovery_actions", "true"),
            ("minimum_payment_amount", "500"),
            ("maximum_recovery_attempts", "3"),
            ("recovery_score_threshold", "70"),
            ("retry_after_hours", "24"),
            ("cost_per_recovery_attempt", "15"),
            ("business_name", "RecoverAI Demo Business"),
            ("admin_email", "priyal@recoverai.app"),
        ]
        cur.executemany("INSERT OR IGNORE INTO settings (setting_key, setting_value) VALUES (?,?)", settings_data)
        conn.commit()


def check_and_seed_mysql(db):
    """Ensures MySQL tables exist and seeds data if empty."""
    try:
        with db.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(120) NOT NULL,
                email VARCHAR(160) NOT NULL,
                phone VARCHAR(30),
                total_spent DECIMAL(12,2) DEFAULT 0,
                successful_payments INT DEFAULT 0,
                failed_payments INT DEFAULT 0,
                avg_order DECIMAL(12,2) DEFAULT 0,
                risk_level ENUM('Low','Medium','High') DEFAULT 'Low',
                repeat_customer BOOLEAN DEFAULT FALSE,
                last_payment_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
            """)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                razorpay_payment_id VARCHAR(64) NOT NULL,
                customer_id INT NOT NULL,
                amount DECIMAL(12,2) NOT NULL,
                failure_reason VARCHAR(60) NOT NULL,
                attempts INT DEFAULT 1,
                recovery_score INT DEFAULT 0,
                status VARCHAR(20) DEFAULT 'Low',
                recovery_state VARCHAR(20) DEFAULT 'Pending',
                failed_at DATETIME NOT NULL,
                recovered_at DATETIME NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
            """)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS agent_activity (
                id INT AUTO_INCREMENT PRIMARY KEY,
                payment_id INT NOT NULL,
                activity VARCHAR(255) NOT NULL,
                activity_type VARCHAR(20) DEFAULT 'analysis',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
            """)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS ai_recommendations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                payment_id INT NOT NULL,
                strategy VARCHAR(60) NOT NULL,
                reasoning TEXT,
                message_draft TEXT,
                confidence INT DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
            """)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                target_audience VARCHAR(120),
                strategy VARCHAR(60),
                customer_count INT DEFAULT 0,
                potential_revenue DECIMAL(14,2) DEFAULT 0,
                recovered_revenue DECIMAL(14,2) DEFAULT 0,
                status VARCHAR(20) DEFAULT 'Draft',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
            """)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS campaign_payments (
                campaign_id INT NOT NULL,
                payment_id INT NOT NULL,
                PRIMARY KEY (campaign_id, payment_id)
            ) ENGINE=InnoDB;
            """)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                setting_key VARCHAR(80) PRIMARY KEY,
                setting_value VARCHAR(255) NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
            """)

            cur.execute("SELECT COUNT(*) AS cnt FROM customers")
            row = cur.fetchone()
            cnt = row["cnt"] if isinstance(row, dict) else row[0]
            if cnt == 0:
                now = datetime.now()
                customers_sql = """
                INSERT INTO customers (name, email, phone, total_spent, successful_payments, failed_payments, avg_order, risk_level, repeat_customer, last_payment_at) VALUES
                ('Priya Sharma', 'priya@email.com', '+91 90000 10001', 42500, 14, 2, 3035, 'Low', 1, %s),
                ('Rahul Verma', 'rahul@email.com', '+91 90000 10002', 38160, 12, 3, 3180, 'Medium', 1, %s),
                ('Aman Singh', 'aman@email.com', '+91 90000 10003', 12990, 8, 3, 1623, 'High', 0, %s),
                ('Sneha Patel', 'sneha@email.com', '+91 90000 10004', 65230, 16, 1, 4077, 'Low', 1, %s),
                ('Karan Mehta', 'karan@email.com', '+91 90000 10005', 21450, 10, 2, 2145, 'Medium', 0, %s),
                ('Neha Gupta', 'neha@email.com', '+91 90000 10006', 18300, 7, 2, 2614, 'Medium', 0, %s),
                ('Vikram Raj', 'vikram@email.com', '+91 90000 10007', 27650, 9, 3, 3072, 'High', 0, %s)
                """
                cur.execute(customers_sql, [
                    now - timedelta(hours=2), now - timedelta(hours=5), now - timedelta(days=1),
                    now - timedelta(days=2), now - timedelta(days=3), now - timedelta(days=4), now - timedelta(days=5)
                ])

                payments_sql = """
                INSERT INTO payments (razorpay_payment_id, customer_id, amount, failure_reason, attempts, recovery_score, status, recovery_state, failed_at, recovered_at) VALUES
                ('pay_Qw12ErX9', 1, 2999, 'Bank Declined', 1, 91, 'High', 'Pending', %s, NULL),
                ('pay_Lk34PoY8', 2, 5499, 'Network Error', 2, 76, 'Medium', 'Pending', %s, NULL),
                ('pay_Zx56MnB2', 3, 1299, 'Authentication Failed', 3, 32, 'Low', 'Pending', %s, NULL),
                ('pay_Po98LmN3', 4, 8999, 'Bank Declined', 1, 94, 'High', 'Recovered', %s, %s),
                ('pay_Ax9OQpQ7', 5, 4499, 'Insufficient Funds', 2, 66, 'Medium', 'Pending', %s, NULL),
                ('pay_Bn23QwE1', 6, 2249, 'Bank Declined', 1, 89, 'High', 'Pending', %s, NULL),
                ('pay_Xc76UlM4', 7, 6499, 'Network Error', 2, 58, 'Medium', 'Pending', %s, NULL)
                """
                cur.execute(payments_sql, [
                    now - timedelta(hours=2), now - timedelta(hours=5), now - timedelta(days=1),
                    now - timedelta(days=2), now - timedelta(days=2, hours=-1),
                    now - timedelta(days=3), now - timedelta(days=4), now - timedelta(days=5)
                ])

                cur.execute("""
                INSERT INTO agent_activity (payment_id, activity, activity_type, created_at) VALUES
                (1, 'Payment failed received from Razorpay', 'analysis', %s),
                (1, 'Customer history analyzed', 'analysis', %s),
                (1, 'Recovery probability calculated (91%)', 'analysis', %s),
                (1, 'Best strategy selected: Payment Retry', 'decision', %s),
                (1, 'Personalized message generated', 'action', %s)
                """, [
                    now - timedelta(hours=2), now - timedelta(hours=1, minutes=59),
                    now - timedelta(hours=1, minutes=58), now - timedelta(hours=1, minutes=57),
                    now - timedelta(hours=1, minutes=56)
                ])

                cur.execute("""
                INSERT INTO ai_recommendations (payment_id, strategy, reasoning, message_draft, confidence) VALUES
                (1, 'Payment Retry', 'Customer has strong payment history (14 successful out of 16). High lifetime value customer.', 'Hi Priya, we noticed your last payment of ₹2,999 did not go through. Please retry using a different card or UPI.', 91)
                """)

                cur.execute("""
                INSERT INTO campaigns (name, target_audience, strategy, customer_count, potential_revenue, recovered_revenue, status) VALUES
                ('High Value Recovery', 'Payments above ₹5,000', 'Payment Retry', 127, 812000, 306000, 'Running'),
                ('24h Reminder Campaign', 'Payments made < 24h', 'Smart Reminder', 249, 213000, 88000, 'Running'),
                ('Weekend Recovery', 'Weekend Failures', 'Reminder + Offer', 358, 154000, 54000, 'Completed'),
                ('Low Value Recovery', 'Payments under ₹1,000', 'Smart Reminder', 358, 268000, 42000, 'Running'),
                ('New Customer Recovery', 'First-time Failures', 'Personalized Retry', 156, 126000, 0, 'Draft')
                """)

                cur.execute("""
                INSERT INTO settings (setting_key, setting_value) VALUES
                ('auto_analyze_failed_payments', 'true'),
                ('prioritize_high_value', 'true'),
                ('automated_reminders', 'true'),
                ('automated_recovery_actions', 'true'),
                ('minimum_payment_amount', '500'),
                ('maximum_recovery_attempts', '3'),
                ('recovery_score_threshold', '70'),
                ('retry_after_hours', '24'),
                ('cost_per_recovery_attempt', '15'),
                ('business_name', 'RecoverAI Demo Business'),
                ('admin_email', 'priyal@recoverai.app')
                ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value);
                """)
    except Exception as e:
        print(f"[MySQL Init Warning]: {e}")


def get_db():
    global DB_MODE
    if "db" not in g:
        is_vercel = bool(os.environ.get("VERCEL"))
        mysql_host = app.config.get("MYSQL_HOST", "")
        should_try_mysql = mysql_host and (not is_vercel or mysql_host not in ("localhost", "127.0.0.1"))

        if should_try_mysql:
            try:
                connect_kwargs = {
                    "host": app.config["MYSQL_HOST"],
                    "port": app.config["MYSQL_PORT"],
                    "user": app.config["MYSQL_USER"],
                    "password": app.config["MYSQL_PASSWORD"],
                    "database": app.config["MYSQL_DB"],
                    "cursorclass": pymysql.cursors.DictCursor,
                    "autocommit": True,
                    "connect_timeout": 3,
                }
                ssl_mode = os.environ.get("MYSQL_SSL_MODE") or os.environ.get("MYSQL_SSL")
                if ssl_mode:
                    connect_kwargs["ssl"] = {"rejectUnauthorized": False}
                elif app.config["MYSQL_HOST"] not in ("localhost", "127.0.0.1"):
                    connect_kwargs["ssl"] = {"rejectUnauthorized": False}

                db_conn = pymysql.connect(**connect_kwargs)
                check_and_seed_mysql(db_conn)
                g.db = db_conn
                DB_MODE = "mysql"
                return g.db
            except Exception as e:
                print(f"[MySQL Driver Warning]: MySQL connection failed ({e}). Falling back to SQLite.")

        # SQLite Fallback (Uses /tmp/recoverai.db on Linux/Vercel for write access)
        tmp_dir = "/tmp" if os.path.exists("/tmp") or os.name != "nt" else "."
        db_path = os.path.join(tmp_dir, "recoverai.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        init_sqlite_db(conn)
        g.db = conn
        DB_MODE = "sqlite"

    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql, args=None, fetch="all"):
    db = get_db()
    args = list(args) if args else []

    if DB_MODE == "sqlite":
        sqlite_sql = sql
        sqlite_sql = sqlite_sql.replace("%s", "?")
        sqlite_sql = sqlite_sql.replace("NOW() - INTERVAL 14 DAY", "datetime('now', '-14 days', 'localtime')")
        sqlite_sql = sqlite_sql.replace("NOW() - INTERVAL 7 DAY", "datetime('now', '-7 days', 'localtime')")
        sqlite_sql = sqlite_sql.replace("NOW() - INTERVAL 1 DAY", "datetime('now', '-1 day', 'localtime')")
        sqlite_sql = sqlite_sql.replace("NOW() - INTERVAL 24 HOUR", "datetime('now', '-24 hours', 'localtime')")
        sqlite_sql = sqlite_sql.replace("NOW()", "datetime('now', 'localtime')")
        sqlite_sql = sqlite_sql.replace("HOUR(recovered_at)", "CAST(strftime('%H', recovered_at) AS INTEGER)")
        sqlite_sql = sqlite_sql.replace(
            "AVG(TIMESTAMPDIFF(MINUTE, failed_at, recovered_at))",
            "AVG((julianday(recovered_at) - julianday(failed_at)) * 1440)"
        )
        sqlite_sql = sqlite_sql.replace("INSERT IGNORE INTO", "INSERT OR IGNORE INTO")
        sqlite_sql = re.sub(
            r"ON DUPLICATE KEY UPDATE setting_value\s*=\s*VALUES\(setting_value\)",
            "ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value",
            sqlite_sql,
            flags=re.IGNORECASE
        )

        cur = db.cursor()
        cur.execute(sqlite_sql, args)
        if fetch == "all":
            rows = cur.fetchall()
            return [dict(r) for r in rows]
        if fetch == "one":
            row = cur.fetchone()
            return dict(row) if row else None
        if fetch == "id":
            db.commit()
            return cur.lastrowid
        db.commit()
        return None
    else:
        with db.cursor() as cur:
            cur.execute(sql, args or ())
            if fetch == "all":
                return cur.fetchall()
            if fetch == "one":
                return cur.fetchone()
            if fetch == "id":
                return cur.lastrowid
            return None



# ---------------------------------------------------------------------------
# Settings & Gemini AI Engine
# ---------------------------------------------------------------------------
import json
import random
import urllib.request
import urllib.error


def get_setting(key, default=""):
    try:
        row = query("SELECT setting_value FROM settings WHERE setting_key=%s", [key], fetch="one")
        if row and row.get("setting_value") is not None:
            return row["setting_value"]
    except Exception:
        pass
    return default


def get_high_value_threshold():
    val = get_setting("minimum_payment_amount", "30000")
    try:
        return float(val)
    except (ValueError, TypeError):
        return 30000.0


def analyze_payment_with_gemini(customer, payment):
    """
    Dynamically analyzes payment failure, calculates score, determines strategy,
    and generates reasoning + personalized outreach draft message using Gemini API
    or dynamic fallback AI engine.
    """
    api_key = get_setting("gemini_api_key", "").strip() or app.config.get("GEMINI_API_KEY", "").strip()

    amount = float(payment.get("amount", 0))
    reason = payment.get("failure_reason", "Other")
    attempts = payment.get("attempts", 1)
    cust_name = customer.get("name", "Customer")
    first_name = cust_name.split()[0] if cust_name else "Customer"
    total_spent = float(customer.get("total_spent", 0))
    succ = customer.get("successful_payments", 0)
    failed = customer.get("failed_payments", 0)

    if api_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            prompt_text = f"""
You are RecoverAI, an AI Revenue Recovery Agent.
Analyze this payment failure and respond ONLY in valid JSON format with keys:
- "score": integer 1-99
- "bucket": string ("High", "Medium", "Low")
- "strategy": string ("Payment Retry", "Smart Reminder", "Incentive Offer", "Human Support")
- "reasoning": 1-2 sentence technical AI assessment of why this occurred
- "message_draft": 1-2 sentence personalized SMS outreach message with a recovery link placeholder.

Details:
Customer Name: {cust_name}
Total Spent: ₹{total_spent}
Successful Payments: {succ}
Failed Payments: {failed}
Payment Amount: ₹{amount}
Failure Reason: {reason}
Attempts: {attempts}
"""
            req_payload = json.dumps({
                "contents": [{"parts": [{"text": prompt_text}]}],
                "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
            }).encode("utf-8")

            req = urllib.request.Request(url, data=req_payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as response:
                res_body = json.loads(response.read().decode("utf-8"))
                text_content = res_body["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text_content)
                score = max(1, min(99, int(parsed.get("score", 50))))
                bucket = parsed.get("bucket", "High" if score >= 70 else "Medium" if score >= 45 else "Low")
                strategy = parsed.get("strategy", "Payment Retry")
                reasoning = parsed.get("reasoning", "")
                message = parsed.get("message_draft", "")
                if score and strategy and reasoning and message:
                    return score, bucket, strategy, reasoning, message
        except Exception as e:
            print(f"[Gemini Integration Fallback]: {e}")

    # Adaptive Dynamic Engine (runs if no API key or API call fails)
    score = 50
    if succ > 0:
        ratio = succ / max(1, succ + failed)
        score += int(ratio * 25)
    if total_spent >= get_high_value_threshold():
        score += 15
    if attempts <= 1:
        score += 5

    reason_weights = {
        "Bank Declined": 15,
        "Network Error": 20,
        "Insufficient Funds": -5,
        "Authentication Failed": -10,
        "Human Support": -25,
        "Other": 0,
    }
    score += reason_weights.get(reason, 0)
    score = max(1, min(99, score))

    if score >= 70:
        bucket, strategy = "High", "Payment Retry"
    elif score >= 45:
        bucket, strategy = "Medium", "Smart Reminder"
    else:
        bucket, strategy = "Low", "Incentive Offer"

    reasoning_map = {
        "Bank Declined": f"Customer {first_name} has high lifetime value (₹{total_spent:,.0f}). Bank decline is temporary; dynamic 1-click retry link recommended.",
        "Network Error": f"Payment of ₹{amount:,.0f} failed due to a connectivity timeout. Auto-retry link has a high recovery probability.",
        "Insufficient Funds": f"Insufficient funds detected. Scheduled reminder and flexible payment method option generated for {first_name}.",
        "Authentication Failed": f"Authentication/OTP error detected. Direct checkout link dispatches immediately to {first_name}.",
        "Human Support": f"Multiple repeated payment failures. Support agent intervention requested.",
        "Other": f"General checkout failure for ₹{amount:,.0f}. Scheduled automated recovery sequence.",
    }
    reasoning = reasoning_map.get(reason, f"AI evaluated payment history for {first_name} and selected {strategy}.")

    payment_id_str = str(payment.get("id") or random.randint(100, 999))
    messages_map = {
        "Payment Retry": f"Hi {first_name}, your payment of ₹{amount:,.0f} didn't go through due to a bank timeout. Click here to instantly complete your order: https://rcvr.ai/pay/{payment_id_str}",
        "Smart Reminder": f"Hello {first_name}, we saved your cart of ₹{amount:,.0f}! You can complete checkout anytime here: https://rcvr.ai/pay/{payment_id_str}",
        "Incentive Offer": f"Hi {first_name}, complete your order of ₹{amount:,.0f} today and get 5% cashback applied automatically: https://rcvr.ai/pay/{payment_id_str}",
        "Human Support": f"Hi {first_name}, our support team is standing by to help complete your purchase of ₹{amount:,.0f}: https://rcvr.ai/pay/{payment_id_str}",
    }
    message = messages_map.get(strategy, f"Hi {first_name}, tap here to retry your payment of ₹{amount:,.0f}: https://rcvr.ai/pay/{payment_id_str}")

    return score, bucket, strategy, reasoning, message


# Backward compatibility alias
def score_payment(customer, payment):
    score, bucket, strategy, _, _ = analyze_payment_with_gemini(customer, payment)
    return score, bucket, strategy


# ---------------------------------------------------------------------------
# AI Insights — derived from live queries against database
# ---------------------------------------------------------------------------
def build_insights():
    insights = []
    threshold = get_high_value_threshold()

    # 1) High-value customers with money still sitting in Pending recovery.
    hv = query(
        """
        SELECT COUNT(*) AS cnt, COALESCE(SUM(p.amount), 0) AS amt
        FROM payments p JOIN customers c ON c.id = p.customer_id
        WHERE p.recovery_state = 'Pending' AND c.total_spent >= %s
        """,
        [threshold],
        fetch="one",
    )

    if hv["cnt"]:
        insights.append({
            "type": "opportunity",
            "text": f"{hv['cnt']} high-value customer(s) have "
                    f"₹{float(hv['amt']):,.0f} in failed payments still pending recovery.",
        })

    # 2) Payments that failed over 24h ago and still have no recovery action.
    stale = query(
        """
        SELECT COUNT(*) AS cnt FROM payments
        WHERE recovery_state = 'Pending' AND failed_at <= NOW() - INTERVAL 24 HOUR
        """,
        fetch="one",
    )
    if stale["cnt"]:
        insights.append({
            "type": "warning",
            "text": f"{stale['cnt']} failed payment(s) haven't been retried within 24 hours.",
        })

    # 3) Week-over-week recovery rate comparison.
    weekly = query(
        """
        SELECT
          SUM(CASE WHEN failed_at >= NOW() - INTERVAL 7 DAY THEN amount ELSE 0 END) AS lost_this_week,
          SUM(CASE WHEN failed_at >= NOW() - INTERVAL 7 DAY AND recovery_state='Recovered' THEN amount ELSE 0 END) AS recovered_this_week,
          SUM(CASE WHEN failed_at >= NOW() - INTERVAL 14 DAY AND failed_at < NOW() - INTERVAL 7 DAY THEN amount ELSE 0 END) AS lost_last_week,
          SUM(CASE WHEN failed_at >= NOW() - INTERVAL 14 DAY AND failed_at < NOW() - INTERVAL 7 DAY AND recovery_state='Recovered' THEN amount ELSE 0 END) AS recovered_last_week
        FROM payments
        """,
        fetch="one",
    )
    lost_this = float(weekly["lost_this_week"] or 0)
    lost_last = float(weekly["lost_last_week"] or 0)
    if lost_this and lost_last:
        rate_this = (float(weekly["recovered_this_week"] or 0) / lost_this) * 100
        rate_last = (float(weekly["recovered_last_week"] or 0) / lost_last) * 100
        delta = round(rate_this - rate_last, 1)
        if delta > 0:
            insights.append({
                "type": "success",
                "text": f"Recovery rate is up {delta} points week over week "
                        f"({round(rate_last, 1)}% → {round(rate_this, 1)}%).",
            })
        elif delta < 0:
            insights.append({
                "type": "warning",
                "text": f"Recovery rate is down {abs(delta)} points week over week "
                        f"({round(rate_last, 1)}% → {round(rate_this, 1)}%).",
            })

    # 4) Time-of-day with the most successful recoveries.
    best_hour = query(
        """
        SELECT HOUR(recovered_at) AS hr, COUNT(*) AS cnt
        FROM payments
        WHERE recovery_state = 'Recovered' AND recovered_at IS NOT NULL
        GROUP BY HOUR(recovered_at)
        ORDER BY cnt DESC
        LIMIT 1
        """,
        fetch="one",
    )
    if best_hour:
        hr = best_hour["hr"]
        if 5 <= hr < 12:
            window = "morning (5 AM–12 PM)"
        elif 12 <= hr < 17:
            window = "afternoon (12 PM–5 PM)"
        elif 17 <= hr < 21:
            window = "evening (5 PM–9 PM)"
        else:
            window = "night (9 PM–5 AM)"
        insights.append({
            "type": "info",
            "text": f"Payment retries perform best in the {window} window "
                    f"({best_hour['cnt']} recoveries logged in that hour).",
        })

    return insights


# ---------------------------------------------------------------------------
# Page routes (server-rendered shell; each page hydrates via /api/* calls)
# ---------------------------------------------------------------------------
@app.route("/")
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", active="dashboard")


@app.route("/failed-payments")
def failed_payments_page():
    return render_template("failed_payments.html", active="failed_payments")


@app.route("/customers")
def customers_page():
    return render_template("customers.html", active="customers")


@app.route("/recovery-agent")
def recovery_agent_page():
    return render_template("recovery_agent.html", active="recovery_agent")


@app.route("/campaigns")
def campaigns_page():
    return render_template("campaigns.html", active="campaigns")


@app.route("/analytics")
def analytics_page():
    return render_template("analytics.html", active="analytics")


@app.route("/settings")
def settings_page():
    return render_template("settings.html", active="settings")


# ---------------------------------------------------------------------------
# API — Dashboard
# ---------------------------------------------------------------------------
@app.route("/api/dashboard")
def api_dashboard():
    totals = query(
        """
        SELECT
          COUNT(*) AS failed_count,
          COALESCE(SUM(amount),0) AS lost_revenue,
          COALESCE(SUM(CASE WHEN recovery_state='Recovered' THEN amount ELSE 0 END),0) AS recovered_revenue,
          COALESCE(SUM(CASE WHEN recovery_state='Pending' THEN amount ELSE 0 END),0) AS potential_revenue
        FROM payments
        WHERE failed_at >= NOW() - INTERVAL 7 DAY
        """,
        fetch="one",
    )
    failed = totals["failed_count"] or 0
    lost = float(totals["lost_revenue"] or 0)
    recovered = float(totals["recovered_revenue"] or 0)
    potential = float(totals["potential_revenue"] or 0)
    recovery_rate = round((recovered / lost) * 100, 1) if lost else 0

    trend = query(
        """
        SELECT DATE(failed_at) AS day, SUM(CASE WHEN recovery_state='Recovered' THEN amount ELSE 0 END) AS recovered
        FROM payments
        WHERE failed_at >= NOW() - INTERVAL 7 DAY
        GROUP BY DATE(failed_at)
        ORDER BY day
        """
    )

    insights = build_insights()

    return jsonify(
        {
            "failed_payments": failed,
            "lost_revenue": lost,
            "recovered_revenue": recovered,
            "recovery_rate": recovery_rate,
            "potential_recoverable": potential,
            "trend": trend,
            "insights": insights,
        }
    )


# ---------------------------------------------------------------------------
# API — Failed Payments
# ---------------------------------------------------------------------------
@app.route("/api/failed-payments")
def api_failed_payments():
    search = f"%{request.args.get('search', '')}%"
    bucket = request.args.get("bucket")  # High / Medium / Low / recent
    sql = """
        SELECT p.id, p.razorpay_payment_id, c.name AS customer_name, c.email,
               p.amount, p.failure_reason, p.attempts, p.recovery_score,
               p.status, p.recovery_state, p.failed_at
        FROM payments p JOIN customers c ON c.id = p.customer_id
        WHERE (c.name LIKE %s OR c.email LIKE %s OR p.razorpay_payment_id LIKE %s)
    """
    args = [search, search, search]
    if bucket in ("High", "Medium", "Low"):
        sql += " AND p.status = %s"
        args.append(bucket)
    elif bucket == "recent":
        sql += " AND p.failed_at >= NOW() - INTERVAL 1 DAY"
    sql += " ORDER BY p.failed_at DESC"
    rows = query(sql, args)
    return jsonify(rows)


@app.route("/api/failed-payments/<int:payment_id>")
def api_failed_payment_detail(payment_id):
    row = query(
        """
        SELECT p.*, c.name AS customer_name, c.email, c.phone
        FROM payments p JOIN customers c ON c.id = p.customer_id
        WHERE p.id = %s
        """,
        [payment_id],
        fetch="one",
    )
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify(row)


@app.route("/api/failed-payments/<int:payment_id>/recover", methods=["POST"])
def api_recover_payment(payment_id):
    query(
        "UPDATE payments SET recovery_state='In Progress' WHERE id=%s",
        [payment_id],
    )
    query(
        "INSERT INTO agent_activity (payment_id, activity, activity_type) VALUES (%s, %s, 'action')",
        [payment_id, "Recovery action triggered manually from Failed Payments"],
    )
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# API — Customers
# ---------------------------------------------------------------------------
@app.route("/api/customers")
def api_customers():
    search = f"%{request.args.get('search', '')}%"
    rows = query(
        """
        SELECT id, name, email, phone, total_spent, successful_payments,
               failed_payments, avg_order, risk_level, repeat_customer, last_payment_at
        FROM customers
        WHERE name LIKE %s OR email LIKE %s
        ORDER BY total_spent DESC
        """,
        [search, search],
    )
    return jsonify(rows)


@app.route("/api/customers/summary")
def api_customers_summary():
    threshold = get_high_value_threshold()
    row = query(
        """
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN total_spent >= %s THEN 1 ELSE 0 END) AS high_value,
               SUM(CASE WHEN risk_level='High' THEN 1 ELSE 0 END) AS at_risk,
               SUM(CASE WHEN repeat_customer THEN 1 ELSE 0 END) AS repeat_customers
        FROM customers
        """,
        [threshold],
        fetch="one",
    )
    return jsonify(row)


@app.route("/api/customers/<int:customer_id>")
def api_customer_detail(customer_id):
    cust = query("SELECT * FROM customers WHERE id=%s", [customer_id], fetch="one")
    if not cust:
        return jsonify({"error": "not found"}), 404
    history = query(
        "SELECT * FROM payments WHERE customer_id=%s ORDER BY failed_at DESC",
        [customer_id],
    )
    cust["payment_history"] = history
    return jsonify(cust)


# ---------------------------------------------------------------------------
# API — AI Recovery Agent
# ---------------------------------------------------------------------------
@app.route("/api/recovery-agent/queue")
def api_recovery_queue():
    rows = query(
        """
        SELECT p.id, c.name AS customer_name, c.email, p.amount, p.failure_reason,
               p.recovery_score, p.status, p.failed_at
        FROM payments p JOIN customers c ON c.id = p.customer_id
        WHERE p.recovery_state = 'Pending'
        ORDER BY p.recovery_score DESC
        """
    )
    return jsonify(rows)


@app.route("/api/recovery-agent/<int:payment_id>")
def api_recovery_detail(payment_id):
    payment = query(
        """
        SELECT p.*, c.name AS customer_name, c.email, c.phone,
               c.successful_payments, c.failed_payments, c.total_spent
        FROM payments p JOIN customers c ON c.id = p.customer_id
        WHERE p.id = %s
        """,
        [payment_id],
        fetch="one",
    )
    if not payment:
        return jsonify({"error": "not found"}), 404

    rec = query(
        "SELECT * FROM ai_recommendations WHERE payment_id=%s ORDER BY created_at DESC LIMIT 1",
        [payment_id],
        fetch="one",
    )
    if not rec:
        customer_obj = {
            "name": payment["customer_name"],
            "total_spent": payment["total_spent"],
            "successful_payments": payment["successful_payments"],
            "failed_payments": payment["failed_payments"],
        }
        score, bucket, strategy, reasoning, message = analyze_payment_with_gemini(customer_obj, payment)
        query(
            """
            INSERT INTO ai_recommendations (payment_id, strategy, reasoning, message_draft, confidence)
            VALUES (%s, %s, %s, %s, %s)
            """,
            [payment_id, strategy, reasoning, message, score],
        )
        rec = {
            "strategy": strategy,
            "reasoning": reasoning,
            "message_draft": message,
            "confidence": score,
        }

    activity = query(
        "SELECT * FROM agent_activity WHERE payment_id=%s ORDER BY created_at ASC",
        [payment_id],
    )

    payment["recommendation"] = rec
    payment["activity"] = activity
    return jsonify(payment)


@app.route("/api/recovery-agent/<int:payment_id>/recover", methods=["POST"])
def api_recovery_agent_recover(payment_id):
    payment = query(
        "SELECT p.*, c.name AS customer_name, c.email FROM payments p JOIN customers c ON c.id=p.customer_id WHERE p.id=%s",
        [payment_id],
        fetch="one"
    )
    if not payment:
        return jsonify({"error": "payment not found"}), 404

    rec = query("SELECT * FROM ai_recommendations WHERE payment_id=%s ORDER BY created_at DESC LIMIT 1", [payment_id], fetch="one")
    strategy = rec["strategy"] if rec else "Payment Retry"
    msg_draft = rec["message_draft"] if rec and rec.get("message_draft") else f"Hi {payment['customer_name'].split()[0]}, tap here to complete your order."

    query("UPDATE payments SET recovery_state='In Progress' WHERE id=%s", [payment_id])

    activity_steps = [
        ("AI Agent initialized recovery pipeline", "decision"),
        (f"Executing strategy: {strategy}", "action"),
        (f"Dispatched SMS/Outreach: \"{msg_draft}\"", "message"),
        (f"1-Click dynamic recovery link active for {payment['customer_name']}", "action"),
    ]
    for act, act_type in activity_steps:
        query(
            "INSERT INTO agent_activity (payment_id, activity, activity_type) VALUES (%s, %s, %s)",
            [payment_id, act, act_type],
        )
    return jsonify({"ok": True, "status": "In Progress"})


# ---------------------------------------------------------------------------
# API — Campaigns
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# API — Campaigns (Fully Dynamic DB Calculations)
# ---------------------------------------------------------------------------
def calculate_campaign_audience_metrics(target_audience):
    """
    Automatically queries database to find matching pending/in-progress payments and customers
    for a given target_audience selection.
    """
    threshold = get_high_value_threshold()
    audience = (target_audience or "").strip()

    if audience == "High Value Customers":
        where_clause = "WHERE p.recovery_state IN ('Pending', 'In Progress') AND c.total_spent >= %s"
        params = [threshold]
    elif audience == "High Recovery Probability":
        where_clause = "WHERE p.recovery_state IN ('Pending', 'In Progress') AND p.recovery_score >= 70"
        params = []
    elif audience == "Payments above ₹5,000":
        where_clause = "WHERE p.recovery_state IN ('Pending', 'In Progress') AND p.amount >= 5000"
        params = []
    elif audience == "Payments under ₹1,000":
        where_clause = "WHERE p.recovery_state IN ('Pending', 'In Progress') AND p.amount < 1000"
        params = []
    else:  # "Failed Payments — Last 24h" or default
        where_clause = "WHERE p.recovery_state IN ('Pending', 'In Progress') AND p.failed_at >= NOW() - INTERVAL 24 HOUR"
        params = []

    metrics = query(
        f"""
        SELECT COUNT(DISTINCT p.customer_id) AS cust_cnt,
               COALESCE(SUM(p.amount), 0) AS pot_rev
        FROM payments p JOIN customers c ON c.id = p.customer_id
        {where_clause}
        """,
        params,
        fetch="one",
    )

    matching_payments = query(
        f"""
        SELECT p.id FROM payments p JOIN customers c ON c.id = p.customer_id
        {where_clause}
        """,
        params,
    )
    payment_ids = [p["id"] for p in (matching_payments or [])]

    cust_cnt = int(metrics["cust_cnt"] or 0)
    pot_rev = float(metrics["pot_rev"] or 0.0)

    return cust_cnt, pot_rev, payment_ids


@app.route("/api/campaigns/preview")
def api_campaign_preview():
    audience = request.args.get("target_audience", "")
    cust_cnt, pot_rev, payment_ids = calculate_campaign_audience_metrics(audience)
    return jsonify({
        "customer_count": cust_cnt,
        "potential_revenue": pot_rev,
        "matching_payments_count": len(payment_ids),
    })


@app.route("/api/campaigns")
def api_campaigns():
    status = request.args.get("status")
    sql = "SELECT * FROM campaigns"
    args = []
    if status and status != "all":
        sql += " WHERE status=%s"
        args.append(status.capitalize())
    sql += " ORDER BY created_at DESC"
    rows = query(sql, args)

    # Recalculate recovered revenue dynamically for each campaign from linked payments
    for c in rows:
        rec_row = query(
            """
            SELECT COALESCE(SUM(p.amount), 0) AS recovered_amt
            FROM campaign_payments cp JOIN payments p ON p.id = cp.payment_id
            WHERE cp.campaign_id = %s AND p.recovery_state = 'Recovered'
            """,
            [c["id"]],
            fetch="one",
        )
        c["recovered_revenue"] = float(rec_row["recovered_amt"] or 0)
        query("UPDATE campaigns SET recovered_revenue=%s WHERE id=%s", [c["recovered_revenue"], c["id"]])

    summary = query(
        """
        SELECT COUNT(*) AS total_campaigns,
               SUM(CASE WHEN status='Running' THEN 1 ELSE 0 END) AS running,
               SUM(customer_count) AS total_customers,
               SUM(potential_revenue) AS potential_revenue,
               SUM(recovered_revenue) AS recovered_revenue
        FROM campaigns
        """,
        fetch="one",
    )
    return jsonify({"campaigns": rows, "summary": summary})


@app.route("/api/campaigns", methods=["POST"])
def api_create_campaign():
    data = request.get_json(force=True) or {}
    name = data.get("name", "New Recovery Campaign")
    target_audience = data.get("target_audience", "Failed Payments — Last 24h")
    strategy = data.get("strategy", "Payment Retry")
    status = (data.get("status") or "Draft").capitalize()
    if status not in ("Draft", "Running", "Completed", "Paused"):
        status = "Draft"

    # Automatically calculate customers and potential revenue from real matching payments
    cust_cnt, pot_rev, payment_ids = calculate_campaign_audience_metrics(target_audience)

    # Fallback to provided form inputs if no pending payments match in database
    if cust_cnt == 0 and data.get("customer_count"):
        try: cust_cnt = int(data.get("customer_count"))
        except: pass
    if pot_rev == 0.0 and data.get("potential_revenue"):
        try: pot_rev = float(data.get("potential_revenue"))
        except: pass

    campaign_id = query(
        """
        INSERT INTO campaigns (name, target_audience, strategy, customer_count,
                                potential_revenue, recovered_revenue, status)
        VALUES (%s, %s, %s, %s, %s, 0, %s)
        """,
        [name, target_audience, strategy, cust_cnt, pot_rev, status],
        fetch="id",
    )

    # Link matching payments to campaign_payments
    for pid in payment_ids:
        query("INSERT IGNORE INTO campaign_payments (campaign_id, payment_id) VALUES (%s, %s)", [campaign_id, pid])

    # If launched immediately as Running, execute AI recovery workflow on matching payments
    if status == "Running" and payment_ids:
        for pid in payment_ids:
            query("UPDATE payments SET recovery_state='In Progress' WHERE id=%s", [pid])
            query(
                "INSERT INTO agent_activity (payment_id, activity, activity_type) VALUES (%s, %s, 'action')",
                [pid, f"Bulk Campaign '{name}' Dispatched Strategy: {strategy}"],
            )

    return jsonify({"ok": True, "id": campaign_id, "customer_count": cust_cnt, "potential_revenue": pot_rev})


@app.route("/api/campaigns/<int:campaign_id>/status", methods=["POST"])
def api_update_campaign_status(campaign_id):
    data = request.get_json(force=True, silent=True) or {}
    new_status = (data.get("status") or "Running").capitalize()
    if new_status not in ("Draft", "Running", "Completed", "Paused"):
        new_status = "Running"
    query("UPDATE campaigns SET status=%s WHERE id=%s", [new_status, campaign_id])

    # If switching to Running, trigger recovery actions for linked payments
    if new_status == "Running":
        camp = query("SELECT * FROM campaigns WHERE id=%s", [campaign_id], fetch="one")
        linked = query("SELECT payment_id FROM campaign_payments WHERE campaign_id=%s", [campaign_id])
        if camp and linked:
            for item in linked:
                pid = item["payment_id"]
                query("UPDATE payments SET recovery_state='In Progress' WHERE id=%s AND recovery_state='Pending'", [pid])
                query(
                    "INSERT INTO agent_activity (payment_id, activity, activity_type) VALUES (%s, %s, 'action')",
                    [pid, f"Campaign '{camp['name']}' Launched Strategy: {camp['strategy']}"],
                )

    return jsonify({"ok": True, "status": new_status})


@app.route("/api/campaigns/<int:campaign_id>", methods=["DELETE"])
def api_delete_campaign(campaign_id):
    query("DELETE FROM campaigns WHERE id=%s", [campaign_id])
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# API — Analytics
# ---------------------------------------------------------------------------
@app.route("/api/analytics")
def api_analytics():
    totals = query(
        """
        SELECT COUNT(*) AS failed_count,
               COALESCE(SUM(amount),0) AS total_amount,
               COALESCE(SUM(CASE WHEN recovery_state='Recovered' THEN amount ELSE 0 END),0) AS recovered_amount
        FROM payments
        """,
        fetch="one",
    )
    by_reason = query(
        "SELECT failure_reason, COUNT(*) AS cnt FROM payments GROUP BY failure_reason"
    )
    by_strategy = query(
        """
        SELECT strategy, COUNT(*) AS cnt FROM ai_recommendations GROUP BY strategy
        """
    )
    trend = query(
        """
        SELECT DATE(failed_at) AS day,
               SUM(amount) AS lost,
               SUM(CASE WHEN recovery_state='Recovered' THEN amount ELSE 0 END) AS recovered
        FROM payments
        WHERE failed_at >= NOW() - INTERVAL 7 DAY
        GROUP BY DATE(failed_at) ORDER BY day
        """
    )

    # Funnel stages, each backed by a real count rather than an assumed ratio.
    analyzed = query(
        "SELECT COUNT(DISTINCT payment_id) AS c FROM agent_activity WHERE activity_type='analysis'",
        fetch="one",
    )["c"]
    attempted = query(
        "SELECT COUNT(*) AS c FROM payments WHERE recovery_state != 'Pending'",
        fetch="one",
    )["c"]
    recovered_count = query(
        "SELECT COUNT(*) AS c FROM payments WHERE recovery_state='Recovered'", fetch="one"
    )["c"]
    funnel = {
        "failed": totals["failed_count"],
        "analyzed": analyzed,
        "attempted": attempted,
        "recovered": recovered_count,
    }

    recovered = float(totals["recovered_amount"] or 0)
    total_amt = float(totals["total_amount"] or 0)
    rate = round((recovered / total_amt) * 100, 1) if total_amt else 0

    # Average time-to-recovery, computed only from payments that actually
    # transitioned to Recovered with a recorded recovered_at timestamp.
    recovery_time = query(
        """
        SELECT AVG(TIMESTAMPDIFF(MINUTE, failed_at, recovered_at)) AS avg_minutes
        FROM payments
        WHERE recovery_state = 'Recovered' AND recovered_at IS NOT NULL
        """,
        fetch="one",
    )
    avg_recovery_hours = (
        round(float(recovery_time["avg_minutes"]) / 60, 1)
        if recovery_time["avg_minutes"] is not None
        else 0
    )

    # ROI = recovered revenue vs. the cost of running recovery attempts.
    # Cost-per-attempt is a configurable business input stored in `settings`
    # (setting_key='cost_per_recovery_attempt'), not a value invented here —
    # change it via the Settings page/API and this recalculates automatically.
    cost_setting = query(
        "SELECT setting_value FROM settings WHERE setting_key='cost_per_recovery_attempt'",
        fetch="one",
    )
    cost_per_attempt = float(cost_setting["setting_value"]) if cost_setting else 0
    total_cost = attempted * cost_per_attempt
    roi_percent = round(((recovered - total_cost) / total_cost) * 100, 1) if total_cost else 0

    return jsonify(
        {
            "recovery_rate": rate,
            "recovered_revenue": recovered,
            "avg_recovery_hours": avg_recovery_hours,
            "roi_percent": roi_percent,
            "by_reason": by_reason,
            "by_strategy": by_strategy,
            "trend": trend,
            "funnel": funnel,
        }
    )


# ---------------------------------------------------------------------------
# API — Settings
# ---------------------------------------------------------------------------
@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    rows = query("SELECT setting_key, setting_value FROM settings")
    return jsonify({r["setting_key"]: r["setting_value"] for r in rows})


@app.route("/api/settings", methods=["POST"])
def api_save_settings():
    data = request.get_json(force=True)
    for key, value in data.items():
        query(
            """
            INSERT INTO settings (setting_key, setting_value) VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)
            """,
            [key, str(value)],
        )
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Razorpay webhook — where a failed payment enters the recovery pipeline
# ---------------------------------------------------------------------------
@app.route("/api/webhooks/razorpay", methods=["POST"])
def razorpay_webhook():
    """
    Receives Razorpay 'payment.failed' events, creates/updates the payment row,
    runs the AI scoring step with Gemini, and drops it into the recovery queue.
    """
    payload = request.get_json(force=True, silent=True) or {}
    entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    if not entity:
        return jsonify({"ok": False, "error": "no payment entity"}), 400

    email = entity.get("email", "unknown@customer.com")
    customer = query("SELECT * FROM customers WHERE email=%s", [email], fetch="one")
    if not customer:
        customer_id = query(
            "INSERT INTO customers (name, email, phone) VALUES (%s, %s, %s)",
            [entity.get("contact", email), email, entity.get("contact", "")],
            fetch="id",
        )
        customer = query("SELECT * FROM customers WHERE id=%s", [customer_id], fetch="one")

    amount = (entity.get("amount", 0) or 0) / 100
    failure_reason = entity.get("error_reason", "Bank Declined")
    payment_row = {
        "amount": amount,
        "failure_reason": failure_reason,
        "attempts": 1,
    }
    score, bucket, strategy, reasoning, message_draft = analyze_payment_with_gemini(customer, payment_row)

    payment_id = query(
        """
        INSERT INTO payments (razorpay_payment_id, customer_id, amount, failure_reason,
                               attempts, recovery_score, status, recovery_state, failed_at)
        VALUES (%s, %s, %s, %s, 1, %s, %s, 'Pending', NOW())
        """,
        [
            entity.get("id", f"pay_live_{random.randint(100000, 999999)}"),
            customer["id"],
            amount,
            failure_reason,
            score,
            bucket,
        ],
        fetch="id",
    )
    query(
        "UPDATE customers SET failed_payments = failed_payments + 1 WHERE id=%s",
        [customer["id"]],
    )
    query(
        "INSERT INTO agent_activity (payment_id, activity, activity_type) VALUES (%s, %s, 'analysis')",
        [payment_id, f"Razorpay Payment Failure Webhook Received (₹{amount:,.0f})"],
    )
    query(
        "INSERT INTO ai_recommendations (payment_id, strategy, reasoning, message_draft, confidence) VALUES (%s,%s,%s,%s,%s)",
        [payment_id, strategy, reasoning, message_draft, score],
    )

    # Check if automated recovery is enabled in settings
    auto_recover = get_setting("automated_recovery_actions", "true").lower() == "true"
    if auto_recover:
        query("UPDATE payments SET recovery_state='In Progress' WHERE id=%s", [payment_id])
        query(
            "INSERT INTO agent_activity (payment_id, activity, activity_type) VALUES (%s, %s, 'action')",
            [payment_id, f"Auto-Recovery Agent Dispatched Strategy: {strategy}"],
        )

    return jsonify({"ok": True, "payment_id": payment_id, "score": score, "strategy": strategy, "auto_recovered": auto_recover})


# ---------------------------------------------------------------------------
# API — Real-time Simulation Engine
# ---------------------------------------------------------------------------
@app.route("/api/simulate/failed-payment", methods=["POST"])
def api_simulate_failed_payment():
    """Simulates a live incoming Razorpay failed payment event in real-time."""
    data = request.get_json(force=True, silent=True) or {}
    sample_customers = [
        {"name": "Aarav Sharma", "email": "aarav.sharma@example.com", "phone": "+91 98765 43210"},
        {"name": "Diya Sengupta", "email": "diya.sengupta@example.com", "phone": "+91 98123 45678"},
        {"name": "Kabir Malhotra", "email": "kabir.m@example.com", "phone": "+91 97111 22334"},
        {"name": "Ananya Roy", "email": "ananya.roy@example.com", "phone": "+91 99000 11223"},
        {"name": "Rohan Verma", "email": "rohan.v@example.com", "phone": "+91 98444 55667"},
    ]
    reasons = ["Bank Declined", "Network Error", "Authentication Failed", "Insufficient Funds"]

    chosen_cust = random.choice(sample_customers)
    name = data.get("name") or chosen_cust["name"]
    email = data.get("email") or chosen_cust["email"]
    phone = data.get("phone") or chosen_cust["phone"]
    amount = float(data.get("amount") or random.choice([2499, 4999, 12500, 28000, 45000]))
    reason = data.get("failure_reason") or random.choice(reasons)

    customer = query("SELECT * FROM customers WHERE email=%s", [email], fetch="one")
    if not customer:
        customer_id = query(
            "INSERT INTO customers (name, email, phone, total_spent, successful_payments, failed_payments, avg_order, risk_level) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            [name, email, phone, random.randint(5000, 60000), random.randint(1, 10), 1, amount, "Low"],
            fetch="id",
        )
        customer = query("SELECT * FROM customers WHERE id=%s", [customer_id], fetch="one")
    else:
        query("UPDATE customers SET failed_payments = failed_payments + 1 WHERE id=%s", [customer["id"]])

    payment_row = {"amount": amount, "failure_reason": reason, "attempts": 1}
    score, bucket, strategy, reasoning, message_draft = analyze_payment_with_gemini(customer, payment_row)

    rzp_id = f"pay_sim_{random.randint(100000, 999999)}"
    payment_id = query(
        """
        INSERT INTO payments (razorpay_payment_id, customer_id, amount, failure_reason,
                               attempts, recovery_score, status, recovery_state, failed_at)
        VALUES (%s, %s, %s, %s, 1, %s, %s, 'Pending', NOW())
        """,
        [rzp_id, customer["id"], amount, reason, score, bucket],
        fetch="id",
    )

    query(
        "INSERT INTO agent_activity (payment_id, activity, activity_type) VALUES (%s, %s, 'analysis')",
        [payment_id, f"Live Payment Failure Event Received (Razorpay ID: {rzp_id})"],
    )
    query(
        "INSERT INTO ai_recommendations (payment_id, strategy, reasoning, message_draft, confidence) VALUES (%s,%s,%s,%s,%s)",
        [payment_id, strategy, reasoning, message_draft, score],
    )

    return jsonify({
        "ok": True,
        "payment_id": payment_id,
        "razorpay_payment_id": rzp_id,
        "customer_name": name,
        "amount": amount,
        "failure_reason": reason,
        "recovery_score": score,
        "status": bucket,
        "strategy": strategy,
        "message": f"Real-time payment failure simulated for {name} (₹{amount:,.0f})",
    })


@app.route("/api/simulate/recovery-success", methods=["POST"])
def api_simulate_recovery_success():
    """Simulates customer completing payment via AI recovery outreach link."""
    data = request.get_json(force=True, silent=True) or {}
    payment_id = data.get("payment_id")

    if not payment_id:
        target = query("SELECT id FROM payments WHERE recovery_state IN ('Pending', 'In Progress') ORDER BY failed_at DESC LIMIT 1", fetch="one")
        if target:
            payment_id = target["id"]

    if not payment_id:
        return jsonify({"ok": False, "error": "No pending or in-progress payments available to recover."}), 400

    payment = query("SELECT * FROM payments WHERE id=%s", [payment_id], fetch="one")
    if not payment:
        return jsonify({"ok": False, "error": "Payment not found"}), 404

    query("UPDATE payments SET recovery_state='Recovered', recovered_at=NOW() WHERE id=%s", [payment_id])
    query(
        "UPDATE customers SET total_spent = total_spent + %s, successful_payments = successful_payments + 1, last_payment_at = NOW() WHERE id=%s",
        [payment["amount"], payment["customer_id"]],
    )

    query(
        "INSERT INTO agent_activity (payment_id, activity, activity_type) VALUES (%s, %s, 'action')",
        [payment_id, f"Customer successfully completed payment of ₹{float(payment['amount']):,.0f} via AI outreach link!"],
    )

    customer = query("SELECT name FROM customers WHERE id=%s", [payment["customer_id"]], fetch="one")
    cust_name = customer["name"] if customer else "Customer"

    return jsonify({
        "ok": True,
        "payment_id": payment_id,
        "amount": float(payment["amount"]),
        "customer_name": cust_name,
        "message": f"Payment of ₹{float(payment['amount']):,.0f} by {cust_name} recovered successfully!",
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
