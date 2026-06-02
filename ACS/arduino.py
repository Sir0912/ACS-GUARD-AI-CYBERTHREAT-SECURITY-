import serial
import requests
import time

time.sleep(2)

ser = serial.Serial('COM3', 9600)
print("Connected! Waiting for scan...")

while True:
    try:
        line = ser.readline().decode().strip()
        
        if line.startswith("RFID:"):
            uid = line.replace("RFID:", "").strip()
            print("Scanned:", uid)
            
            # Send to /api/scan instead of /scan
            response = requests.post(
                "http://127.0.0.1:5000/api/scan",
                data={"uid": uid},
               
            )
            
            print(response.json())
            
    except Exception as e:
        print("Error:", e)
        break