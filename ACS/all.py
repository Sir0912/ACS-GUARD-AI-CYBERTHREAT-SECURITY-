import subprocess
import time
import sys
import os

#5000 is sa cyber side or admin
#5003 sa client or employee side

FLASK_SCRIPTS = [
    ("cyber.py",      "Port 5000 — Admin RFID login + dashboard"),
    ("emp.py",        "Port 5003 — Employee login portal"),
    ("ai_report.py",  "Port 5001 — AI threat analysis"),
    ("ipconfig.py",   " — IP configuration and geo-location"),
    ("db.py", "Database setup and connection handler")
]

processes = []

print("=" * 50)
print("  🛡️  ACS GUARD — Cyber Security Infrastructure")
print("=" * 50)

python = sys.executable

for script, label in FLASK_SCRIPTS:
    if not os.path.exists(script):
        print(f"⚠️  Skipping {script} — file not found")
        continue
    p = subprocess.Popen([python, script])
    processes.append(p)
    print(f"✅ Started {script:25s} ({label})")
    time.sleep(2)

arduino_script = "arduino.py"
if os.path.exists(arduino_script):
    p = subprocess.Popen([python, arduino_script])
    processes.append(p)
    print(f"✅ Started {arduino_script:25s} (Serial bridge — COM3)")
    time.sleep(1)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n🔴 Shutting down all services...")
    for p in processes:
        p.terminate()
    print("✅ Done.")