import json
from flask import Flask, request, jsonify
from flask_socketio import SocketIO
from openai import OpenAI
from db import get_connection
import requests as http_req
from ipconfig import ip_address

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
app.secret_key = "blackpower"

def get_api_key():
    with open("ip.txt", "r") as f:
        return f.read().strip()
        
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=get_api_key()
)
prompt = """You are a cybersecurity analyst assistant. Analyze login activities and categorize threats:
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

note: Device info are optional, if not avaiable just report "Unknown Devices"
"""

def detect_system(ip):
    try:
        response = http_req.get(f"http://ip-api.com/json/{ip}")
        data = response.json()
        return {
            "Device": "Unknown Device",
            "IP Address": ip,
            "City": data.get("city", "Unknown City"),
            "Region": data.get("region", "Unknown Region"),
            "Country": data.get("country", "Unknown Country"),
            "Time and Date": "Unknown Time and Date"
        }
    except Exception:
        return {
            "Device": "Unknown Device",
            "IP Address": ip,
            "City": "Unknown City",
            "Region": "Unknown Region",
            "Country": "Unknown Country",
            "Time and Date": "Unknown Time and Date"
        }

def call_ai(prompt_text):
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b:free",
            messages=[{"role": "user", "content": prompt_text}],
            max_tokens=0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Ai Failed: {e}"

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    if data.get('manual_ip'):
        ip = data.get('manual_ip')
    else:
        ip = ip_address  # ← Uses IP from ipconfig.py
    
    system_info = detect_system(ip)
    
    prompt = f"""Analyze this potential threat:
    IP: {system_info['IP Address']}
    City: {system_info['City']}
    Region: {system_info['Region']}
    Country: {system_info['Country']}
    Time: {system_info['Time and Date']}

Is this a potential threat? What action should be taken?"""
    
    ai_response = call_ai(prompt)
    
    return jsonify({
        "status": "success",
        "system_info": system_info,
        "ai_analysis": ai_response
    })

@app.route('/chat', methods=['POST'])
def chat():
    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
        
        email = data.get('email', 'Unknown')
        message = data.get('message', '')
        ip = data.get('ip', 'Unknown')
        
        if not ip:
            ip = 'Unknown'
        
        # Check if IP is recognized in employees table
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ip FROM employees WHERE ip = %s", (ip,))
        recognized = cursor.fetchone()
        
        # Check category
        if 'Success' in message:
            if recognized:
                category = 'SAFE'
                safe_val = 1
                warning_val = 0
                threat_val = 0
            else:
                category = 'WARNING'
                safe_val = 0
                warning_val = 1
                threat_val = 0
        else:
            category = 'WARNING'
            safe_val = 0
            warning_val = 1
            threat_val = 0
        
        # Save to DASHBOARD table
        cursor.execute("""
            INSERT INTO dashboard (safe, warning, threat, time_date, ip, banned_ip, total_attempt)
            VALUES (%s, %s, %s, NOW(), %s, 0, 1)
        """, (safe_val, warning_val, threat_val, ip))
        
        # Save to REPORT table
        cursor.execute("""
            INSERT INTO report (time_date, gmail, ip, login_status, category)
            VALUES (NOW(), %s, %s, %s, %s)
        """, (email, ip, 'SUCCESS' if 'Success' in message else 'FAILED', category))
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "ok", "category": category})
    
    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({"status": "error", "message": str(e)})
    
    return jsonify({"status": "recorded", "category": category})
    
if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5001)