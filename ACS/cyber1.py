from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_socketio import SocketIO # 1. Import the radio broadcaster tool
from db import get_connection
from ipconfig import ip_address, device_name, data, MODE

app = Flask(__name__)
app.secret_key = "blackpower"

socketio = SocketIO(app, cors_allowed_origins="*")

@app.route("/")
def landing_page():
    return render_template("cyber_login.html")

@app.route("/home", methods=["POST"])
def home_page():
    admin = request.form.get("admin")
    password = request.form.get("passcode")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admin WHERE name=%s AND password=%s", (admin, password))
    account_found = cursor.fetchone()
    conn.close()
    
    if account_found:
        session["logged_in"] = True
        session["user"] = admin
        return redirect(url_for("scan_page"))
    return redirect(url_for("landing_page"))

@app.route("/scan")
def scan_page():
    if not session.get("logged_in"):
        return redirect(url_for("landing_page"))
    return render_template("scan.html")

# This is where your physical hardware/RFID reader sends the scanned ID card
@app.route("/api/scan", methods=["POST"])
def api_scan():
    uid = request.form.get("uid") or request.get_json(force=True).get("uid")
    if not uid:
        return jsonify({"status": "error"}), 400
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admin WHERE rfid = %s", (uid,))
    admin = cursor.fetchone()
    if admin:
        admin_name = admin[1] if isinstance(admin, tuple) else admin.get('name')
        cursor.execute("UPDATE admin SET last_scan = NOW() WHERE rfid = %s", (uid,))
        conn.commit()
        socketio.emit('card_scanned', {"name": admin_name, "authorized": True})
        
        conn.close()
        return jsonify({"status": "success", "message": "Access Granted"})

    else:
        # --- 2. ACCESS DENIED ---
        # Emit 'authorized: False' -> This prevents redirect in JS
        socketio.emit('card_scanned', {"name": "Unknown", "authorized": False})
        
        conn.close()
        return jsonify({"status": "denied", "message": "Unauthorized Card"}), 401

from ipconfig import ip_address, device_name, data, MODE

#@app.route("/cyber_dash")
#def cyber_dash():
#    if not session.get("logged_in"):
#        return redirect(url_for("landing_page"))
#    
#    conn = get_connection()
#    cursor = conn.cursor()
#    cursor.execute("SELECT * FROM report ORDER BY id DESC LIMIT 50")
#    logs = cursor.fetchall()
#    conn.close()
    
#    return render_template("cyber_dashboard.html",
#                        logs=logs,
#                        ip_info=ip_address,
#                        device_name=device_name,
#                        country=data.get('country', 'N/A'),
#                        city=data.get('city', 'N/A'),
#                        mode=MODE)

@app.route("/cyber_dash")
def cyber_dash():
    if not session.get("logged_in"):
        return redirect(url_for("landing_page"))
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM report ORDER BY id DESC LIMIT 50")
    logs = cursor.fetchall()
    cursor.execute("SELECT * FROM blacklist ORDER BY id DESC")
    blacklist = cursor.fetchall()
    conn.close()
    
    return render_template("cyber_dashboard.html", logs=logs, blacklist=blacklist,
                        ip_info=ip_address, device_name=device_name,
                        country=data.get('country', 'N/A'), city=data.get('city', 'N/A'), mode=MODE)

@app.route("/ban_ip", methods=["POST"])
def ban_ip():
    if not session.get("logged_in"):
        return redirect(url_for("landing_page"))
    
    ip_addr = request.form.get("ip_address")
    reason = request.form.get("reason", "Manual ban")
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO dashboard (ip, banned_ip, time_date, threat) VALUES (%s, 1, NOW(), 1)", (ip_addr,))
    conn.commit()
    conn.close()
    
    return redirect(url_for("cyber_dash"))

@app.route("/unban/<ip_addr>")
def unban(ip_addr):
    if not session.get("logged_in"):
        return redirect(url_for("landing_page"))
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM blacklist WHERE ip = %s", (ip_addr,))
    conn.commit()
    conn.close()
    
    return redirect(url_for("cyber_dash"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing_page"))

if __name__ == "__main__":
    socketio.run(app, debug=True)