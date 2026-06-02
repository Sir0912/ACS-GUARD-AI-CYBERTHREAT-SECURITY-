from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_socketio import SocketIO
from db import get_connection
from ipconfig import ip_address, device_name, data, MODE
from datetime import date

app = Flask(__name__)
app.secret_key = "blackpower"
socketio = SocketIO(app, cors_allowed_origins="*")

# ── Auth ─────────────────────────────────────────────────

@app.route("/")
def landing_page():
    return render_template("cyber_login.html")

@app.route("/home", methods=["POST"])
def home_page():
    admin    = request.form.get("admin")
    password = request.form.get("passcode")
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admin WHERE name=%s AND password=%s", (admin, password))
    account_found = cursor.fetchone()
    conn.close()
    if account_found:
        session["logged_in"] = True
        session["user"]      = admin
        return redirect(url_for("scan_page"))
    return redirect(url_for("landing_page"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing_page"))

# ── RFID ─────────────────────────────────────────────────

@app.route("/scan")
def scan_page():
    if not session.get("logged_in"):
        return redirect(url_for("landing_page"))
    return render_template("scan.html")

@app.route("/api/scan", methods=["POST"])
def api_scan():
    uid = request.form.get("uid") or (request.get_json(force=True) or {}).get("uid")
    if not uid:
        return jsonify({"status": "error"}), 400
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admin WHERE rfid = %s", (uid,))
    admin = cursor.fetchone()
    if admin:
        admin_name = admin["name"] if isinstance(admin, dict) else admin[1]
        cursor.execute("UPDATE admin SET last_scan = NOW() WHERE rfid = %s", (uid,))
        conn.commit()
        conn.close()
        socketio.emit("card_scanned", {"name": admin_name, "authorized": True})
        return jsonify({"status": "success", "message": "Access Granted"})
    else:
        conn.close()
        socketio.emit("card_scanned", {"name": "Unknown", "authorized": False})
        return jsonify({"status": "denied", "message": "Unauthorized Card"}), 401

# ── Dashboard ────────────────────────────────────────────

@app.route("/cyber_dash")
def cyber_dash():
    if not session.get("logged_in"):
        return redirect(url_for("landing_page"))

    # Date filter — defaults to today
    selected_date = request.args.get("date", str(date.today()))

    conn   = get_connection()
    cursor = conn.cursor()

    # Totals for the selected date
    cursor.execute("""
        SELECT
            COUNT(*)                  AS total,
            SUM(category = 'SAFE')    AS safe,
            SUM(category = 'WARNING') AS warning,
            SUM(category = 'THREAT')  AS threat
        FROM report
        WHERE DATE(time_date) = %s
    """, (selected_date,))
    totals = cursor.fetchone() or {}

    # Logs filtered by selected date
    cursor.execute("""
        SELECT * FROM report
        WHERE DATE(time_date) = %s
        ORDER BY id DESC
    """, (selected_date,))
    logs = cursor.fetchall()

    # Blacklist (not date-filtered)
    cursor.execute("SELECT * FROM blacklist ORDER BY id DESC")
    blacklist = cursor.fetchall()

    conn.close()

    return render_template(
        "cyber_dashboard.html",
        logs=logs,
        blacklist=blacklist,
        totals=totals,
        selected_date=selected_date,
        today=str(date.today()),
        ip_info=ip_address,
        device_name=device_name,
        country=data.get("country", "N/A"),
        city=data.get("city",    "N/A"),
        mode=MODE,
    )

# ── Ban / Unban ───────────────────────────────────────────

@app.route("/ban_ip", methods=["POST"])
def ban_ip():
    if not session.get("logged_in"):
        return redirect(url_for("landing_page"))

    ip_addr = request.form.get("ip_address", "").strip()
    reason  = request.form.get("reason", "Manual ban by admin").strip()

    if ip_addr:
        conn   = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT country FROM report WHERE ip = %s LIMIT 1", (ip_addr,))
        row     = cursor.fetchone()
        country = row["country"] if row else "Unknown"

        cursor.execute("SELECT id FROM blacklist WHERE ip = %s", (ip_addr,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO blacklist (ip, country, cause) VALUES (%s,%s,%s)",
                (ip_addr, country, reason)
            )

        cursor.execute("UPDATE report SET ban = 1 WHERE ip = %s", (ip_addr,))
        conn.commit()
        conn.close()

    # Go back to the same date the admin was viewing
    ref_date = request.form.get("date", str(date.today()))
    return redirect(url_for("cyber_dash", date=ref_date))

@app.route("/unban/<path:ip_addr>")
def unban(ip_addr):
    if not session.get("logged_in"):
        return redirect(url_for("landing_page"))
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM blacklist WHERE ip = %s", (ip_addr,))
    cursor.execute("UPDATE report SET ban = 0, auto_ban = 0 WHERE ip = %s", (ip_addr,))
    conn.commit()
    conn.close()
    return redirect(url_for("cyber_dash"))

if __name__ == "__main__":
    socketio.run(app, debug=True, port=5000)