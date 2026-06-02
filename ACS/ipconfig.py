#mag present dri ka demonstrate kag mag run ano matabo di gid pag pakita ang
#imo api key sa ai kag kung pwede ma censored ang atun ip address sa demonstration
#sa all.py kaw run di kana mag tandog da iban iban akon iban claude halata man
#

MODE = "auto"           # ← Auto detect (uses ipify.org)
MODE = "manual"        # ← Manual (use your IP below)

MANUAL_IP = "153.44.197.120"

# ==========================================
#  AUTO DETECTION
# ==========================================
import requests
import socket

device_name = socket.gethostname()

if MODE == "manual":
    ip_address = MANUAL_IP
    data = {}
else:
    ip_address = requests.get('https://api.ipify.org?format=json').json()['ip']

if MODE == "auto":
    response = requests.get(f'http://ip-api.com/json/{ip_address}')
    data = response.json()
else:
    data = {}

# ==========================================
#  PRINT INFO
# ==========================================
print(f"""
==============================================
  🛡️  IP CONFIG - LOADED
==============================================
  Mode    : {MODE}
  Device  : {device_name}
  IP      : {ip_address}
  Country : {data.get('country', 'N/A')}
  City    : {data.get('city',    'N/A')}
  Zip     : {data.get('zip',     'N/A')}
  ISP     : {data.get('isp',     'N/A')}
  Org     : {data.get('org',     'N/A')}
  Lon     : {data.get('lon',     'N/A')}
  Lat     : {data.get('lat',     'N/A')}
==============================================
""")

map_link = f"https://www.google.com/maps?q={data.get('lat', '0')},{data.get('lon', '0')}"
print(f"Map Link: {map_link}")