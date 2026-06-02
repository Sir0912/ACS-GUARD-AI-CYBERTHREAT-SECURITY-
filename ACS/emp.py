from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from db import get_connection, verify_login, is_ip_banned, is_ip_recognized
import requests as http_req

from ipconfig import ip_address, MODE, MANUAL_IP, data

app = Flask(__name__)
app.secret_key = "blackpower"

#@app.route("/")
#def login_page():
#    if session.get("logged_in"):
#        return redirect(url_for("dashboard"))
#    return render_template("login.html", ip=request.remote_addr)
@app.route("/")
def login_page():
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))
    return render_template("login.html", ip=request.remote_addr)
    
@app.route("/login", methods=["POST"])
def login():
    # ... get email, password, ip ...
    email = request.form.get("email") or request.form.get("name")
    password = request.form.get("password") or request.form.get("passw")
    test_ip = request.form.get("test_ip")
    
    if test_ip:
        ip = test_ip
    elif MODE == "manual":
        ip = MANUAL_IP
    else:
        ip = ip_address

    # FIRST: Check if IP is recognized
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ip FROM employees WHERE ip = %s", (ip,))
    recognized = cursor.fetchone()
    
    # If IP not recognized, BLOCK login!
    if not recognized:
        conn.close()
        # Send to AI
        try:
            http_req.post("http://127.0.0.1:5001/chat", json={
                "email": email or "Unknown",
                "ip": ip,
                "message": f"BLOCKED - Unknown IP trying to login: {ip}, Email: {email}"
            }, timeout=5)
        except Exception:
            pass
        
        return render_template("login.html", error="Access Denied. Your IP is not recognized.", ip=ip)

    # If IP recognized, then check credentials
    employee = verify_login(email, password)
    
    if employee:
        session["logged_in"] = True
        session["email"] = employee["gmail"]
        session["name"] = employee["name"]
        session["ip"] = ip
        
        # Send to AI
        try:
            http_req.post("http://127.0.0.1:5001/chat", json={
                "email": employee["gmail"],
                "ip": ip,
                "message": f"Successful login - Email: {email}, IP: {ip}"
            }, timeout=5)
        except Exception:
            pass
        
        return redirect(url_for("dashboard"))
    
    # Failed login
    try:
        http_req.post("http://127.0.0.1:5001/chat", json={
            "email": email or "Unknown",
            "ip": ip,
            "message": f"Failed login - Email: {email}, IP: {ip}"
        }, timeout=5)
    except Exception:
        pass
    
    return render_template("login.html", error="Invalid email or password", ip=ip)

@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in") or not session.get("name"):
        return redirect(url_for("login_page"))
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM dashboard ORDER BY id DESC")
    logs = cursor.fetchall()
    conn.close()
    
    return render_template("dashboard.html",
                          name=session["name"],
                          email=session["email"],
                          ip=session["ip"],
                          my_ip=ip_address,
                          country=data.get('country', 'N/A'),
                          city=data.get('city', 'N/A'),
                          mode=MODE, 
                          logs=logs)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))

if __name__ == "__main__":
    app.run(debug=True, port=5003)