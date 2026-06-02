import requests
import socket
#Check di imo ip address
#ip_address = "143.44.197.120" 
device_name = socket.gethostname()
ip_address = requests.get('https://api.ipify.org?format=json').json()['ip']

response = requests.get(f'http://ip-api.com/json/{ip_address}')
data = response.json()

print(f"""
Device Name: {device_name},
IP: {data['query']},
Country: {data['country']},
City: {data['city']},
Zip: {data['zip']},
ISP: {data['isp']},
Organisation: {data['org']},
Lon: {data['lon']},
Lat: {data['lat']}
""")
