import json
from flask import Flask, request, jsonify
from flask_socketio import SocketIO
from openai import OpenAI
from db import get_connection
import requests as http_req
from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
app.secret_key = "blackpower"

# ── API key ──────────────────────────────────────────────
def get_api_key():
    with open("ip.txt", "r") as f:
        line = f.read().strip()
        if '=' in line:
            return line.split('=', 1)[1].strip().strip('"').strip("'")
        return line

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=get_api_key()
)

SYSTEM_PROMPT = """You are a cybersecurity analyst assistant. Analyze login activities and categorize threats:
- SAFE: Correct Gmail/password + recognized IP → Allow access
- WARNING: 10+ failed attempts → Report to admin for action
- THREAT: 20+ failed attempts OR unrecognized IP login → Auto-ban IP

Report format:
Cause: [reason]
Device: [device info]
IP Address: [ip]
Time and Date: [datetime]
City: [city]
Region: [region]
Country: [country]

note: Device info are optional, if not available just report "Unknown Devices" and also keep your sentences report not long as 4 sentences,
just give me an accurate information about the warning and threat activity
"""

# ── helpers ──────────────────────────────────────────────
def detect_system(ip):
    try:
        r = http_req.get(f"http://ip-api.com/json/{ip}", timeout=5)
        d = r.json()
        if d.get("status") == "success":
            return {
                "city":    d.get("city",       "Unknown"),
                "region":  d.get("regionName", "Unknown"),
                "country": d.get("country",    "Unknown"),
            }
    except Exception:
        pass
    return {"city": "Unknown", "region": "Unknown", "country": "Unknown"}

def call_ai(prompt_text):
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b:free",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt_text}
            ],
            max_tokens=100
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"AI analysis unavailable: {e}"

def determine_category(failed_attempts, recognized_ip, login_status):
    if login_status == "SUCCESS" and not recognized_ip:
        return "THREAT", "Login from unrecognized IP"
    if failed_attempts >= 20:
        return "THREAT", f"20+ failed login attempts ({failed_attempts})"
    if failed_attempts >= 10:
        return "WARNING", f"10+ failed login attempts ({failed_attempts})"
    if login_status == "FAILED":
        return "WARNING" if failed_attempts >= 5 else "SAFE", f"Failed login attempt ({failed_attempts} total)"
    return "SAFE", "Valid credentials from recognized IP"

def save_or_update_report(conn, cursor, email, ip, device_name, os_name, browser,
                           city, region, country, login_status, recognized,
                           category, cause, ai_report, auto_ban):
    """
    If a report row already exists for this IP today, UPDATE its failed_attempts
    and category. Otherwise INSERT a new row.
    This prevents endless new rows for the same attacking IP.
    """
    cursor.execute("""
        SELECT id, failed_attempts FROM report
        WHERE ip = %s AND DATE(time_date) = CURDATE()
        ORDER BY id DESC LIMIT 1
    """, (ip,))
    existing = cursor.fetchone()

    if existing and login_status == "FAILED":
        # UPDATE the existing row — increment count, refresh category/cause/ai
        new_failed = existing["failed_attempts"] + 1
        new_cat, new_cause = determine_category(new_failed, recognized, login_status)
        new_auto_ban = 1 if new_cat == "THREAT" else 0

        cursor.execute("""
            UPDATE report
            SET failed_attempts = %s,
                category        = %s,
                cause           = %s,
                ai_report       = %s,
                auto_ban        = %s,
                ban             = %s,
                time_date       = NOW()
            WHERE id = %s
        """, (new_failed, new_cat, new_cause, ai_report, new_auto_ban, new_auto_ban, existing["id"]))

        return new_failed, new_cat, new_cause, new_auto_ban
    else:
        # INSERT new row (new IP, or successful login, or first attempt today)
        cursor.execute("""
            INSERT INTO report
            (time_date, gmail, ip, device_name, operating_system, browser,
             city, region, country, login_status, failed_attempts,
             recognized_ip, category, cause, ai_report, ban, auto_ban)
            VALUES (NOW(),%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            email, ip, device_name, os_name, browser,
            city, region, country, login_status,
            0 if login_status == "SUCCESS" else 1,
            1 if recognized else 0,
            category, cause, ai_report, auto_ban, auto_ban
        ))
        return 1, category, cause, auto_ban

# ── routes ───────────────────────────────────────────────
@app.route("/")
def index():
    return jsonify({"status": "AI Report Service running", "port": 5001})

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(force=True) or {}

    email        = data.get("email",          "unknown")
    ip           = data.get("ip",             "unknown")
    login_status = data.get("login_status",   "FAILED")
    failed       = int(data.get("failed_attempts", 0))
    recognized   = bool(data.get("recognized_ip",  False))
    device_name  = data.get("device_name",    "Unknown Device")
    os_name      = data.get("os",             "Unknown")
    browser      = data.get("browser",        "Unknown")
    city         = data.get("city",           "Unknown")
    region       = data.get("region",         "Unknown")
    country      = data.get("country",        "Unknown")

    if city == "Unknown":
        geo     = detect_system(ip)
        city    = geo["city"]
        region  = geo["region"]
        country = geo["country"]

    category, cause = determine_category(failed, recognized, login_status)
    auto_ban = 1 if category == "THREAT" else 0

    ai_prompt = f"""Analyze this login event:
Email: {email} | IP: {ip} | Status: {login_status}
Failed Attempts: {failed} | Recognized IP: {recognized}
Device: {device_name} | OS: {os_name} | Browser: {browser}
Location: {city}, {region}, {country}
Category: {category} | Cause: {cause}
Write a concise 3-sentence security report."""

    ai_report = call_ai(ai_prompt)

    try:
        conn   = get_connection()
        cursor = conn.cursor()

        failed, category, cause, auto_ban = save_or_update_report(
            conn, cursor, email, ip, device_name, os_name, browser,
            city, region, country, login_status, recognized,
            category, cause, ai_report, auto_ban
        )

        # Dashboard row — always insert one summary entry per event
        cursor.execute("""
            INSERT INTO dashboard (safe, warning, threat, time_date, ip, banned_ip, total_attempt)
            VALUES (%s,%s,%s,NOW(),%s,%s,1)
        """, (
            1 if category == "SAFE"    else 0,
            1 if category == "WARNING" else 0,
            1 if category == "THREAT"  else 0,
            ip, auto_ban
        ))

        # Auto-ban into blacklist
        if auto_ban:
            cursor.execute("SELECT id FROM blacklist WHERE ip = %s", (ip,))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO blacklist (ip, country, cause) VALUES (%s,%s,%s)",
                    (ip, country, cause)
                )

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB error: {e}")

    socketio.emit("new_report", {"email": email, "ip": ip, "category": category, "cause": cause})
    return jsonify({"category": category, "cause": cause, "ai_report": ai_report})


@app.route("/chat", methods=["POST"])
def chat():
    """Called by emp.py on every login attempt."""
    try:
        data = request.get_json(force=True) if request.is_json else request.form.to_dict()

        email       = data.get("email",           "Unknown")
        message     = data.get("message",         "")
        ip          = data.get("ip",              "Unknown")
        failed      = int(data.get("failed_attempts", 0))
        device_name = data.get("device_name",     "Unknown Device")
        os_name     = data.get("os",              "Unknown")
        browser     = data.get("browser",         "Unknown")

        geo = detect_system(ip)

        conn   = get_connection()
        cursor = conn.cursor()

        # Check recognized IP
        cursor.execute("SELECT ip FROM employees WHERE ip = %s", (ip,))
        recognized = bool(cursor.fetchone())

        login_status = "SUCCESS" if "Success" in message else "FAILED"

        # For FAILED: get real cumulative count from existing report row today
        if login_status == "FAILED":
            cursor.execute("""
                SELECT failed_attempts FROM report
                WHERE ip = %s AND DATE(time_date) = CURDATE()
                ORDER BY id DESC LIMIT 1
            """, (ip,))
            row = cursor.fetchone()
            failed = (row["failed_attempts"] + 1) if row else 1

        category, cause = determine_category(failed, recognized, login_status)
        auto_ban = 1 if category == "THREAT" else 0

        ai_prompt = f"""Analyze login:
Email: {email} | IP: {ip} | Status: {login_status}
Failed: {failed} | Recognized: {recognized}
Location: {geo['city']}, {geo['region']}, {geo['country']}
Category: {category} | Cause: {cause}
Write 2-sentence security summary."""

        ai_report = call_ai(ai_prompt)

        save_or_update_report(
            conn, cursor, email, ip, device_name, os_name, browser,
            geo["city"], geo["region"], geo["country"],
            login_status, recognized, category, cause, ai_report, auto_ban
        )

        # Dashboard summary entry
        cursor.execute("""
            INSERT INTO dashboard (safe, warning, threat, time_date, ip, banned_ip, total_attempt)
            VALUES (%s,%s,%s,NOW(),%s,%s,1)
        """, (
            1 if category == "SAFE"    else 0,
            1 if category == "WARNING" else 0,
            1 if category == "THREAT"  else 0,
            ip, auto_ban
        ))

        # Auto-ban into blacklist
        if auto_ban:
            cursor.execute("SELECT id FROM blacklist WHERE ip = %s", (ip,))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO blacklist (ip, country, cause) VALUES (%s,%s,%s)",
                    (ip, geo["country"], cause)
                )

        conn.commit()
        conn.close()

        socketio.emit("new_report", {"email": email, "ip": ip, "category": category, "cause": cause})
        return jsonify({"status": "ok", "category": category, "failed_attempts": failed})

    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/reports", methods=["GET"])
def get_reports():
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM report ORDER BY id DESC LIMIT 100")
        rows = cursor.fetchall()
        conn.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5001)