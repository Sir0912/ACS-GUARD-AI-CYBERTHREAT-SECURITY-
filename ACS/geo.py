import requests

# Step 1: Get the IP address
print("Getting your IP address...")
ip_address = requests.get('https://api.ipify.org?format=json').json()['ip']
print("Your IP address is:", ip_address)

# Step 2: Look up IP information
print("Looking up location...")
response = requests.get('http://ip-api.com/json/' + ip_address)
data = response.json()

# Step 3: Check if it worked
if data['status'] == 'fail':
    print("Error: " + data['message'])
else:
    # Step 4: Print all the information
    print("--------------------------------")
    print("GEOLOCATION RESULTS")
    print("--------------------------------")
    print("IP Address: " + data['query'])
    print("Country: " + data['country'])
    print("City: " + data['city'])
    print("Zip Code: " + data['zip'])
    print("ISP: " + data['isp'])
    print("Organisation: " + data['org'])
    print("Region: " + data['regionName'])
    print("Timezone: " + data['timezone'])
    print("--------------------------------")
    print("COORDINATES")
    print("--------------------------------")
    print("Latitude: " + str(data['lat']))
    print("Longitude: " + str(data['lon']))
    
    # Step 5: Create map link
    map_link = "https://www.google.com/maps?q=" + str(data['lat']) + "," + str(data['lon'])
    print("Map Link: " + map_link)
    print("--------------------------------")