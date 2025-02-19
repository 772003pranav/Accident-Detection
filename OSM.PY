import requests
from math import radians, sin, cos, sqrt, atan2

# Haversine formula to calculate distance between two lat-long coordinates
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in kilometers

    lat1, lon1, lat2, lon2 = radians(lat1), radians(lon1), radians(lat2), radians(lon2)
    
    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    return distance

def alert_nearest_services(location):
    lat, lon = location  # Use the latitude and longitude of the accident location

    # Query the OSM Overpass API to get nearby police stations and hospitals
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json];
    (
      node["amenity"="police"](around:5000,{lat},{lon});
      node["amenity"="hospital"](around:5000,{lat},{lon});
    );
    out body;
    """

    response = requests.get(overpass_url, params={'data': overpass_query})
    data = response.json()

    police_stations = []
    hospitals = []

    # Parse results from the Overpass API response
    for element in data['elements']:
        if 'tags' in element:
            name = element['tags'].get('name', 'Unnamed')
            lat_osm, lon_osm = element['lat'], element['lon']

            if element['tags'].get('amenity') == 'police':
                police_stations.append({'name': name, 'lat': lat_osm, 'lon': lon_osm})
            elif element['tags'].get('amenity') == 'hospital':
                hospitals.append({'name': name, 'lat': lat_osm, 'lon': lon_osm})

    # Find the nearest police station and hospital using Haversine distance
    nearest_police_station = min(police_stations, key=lambda p: haversine(lat, lon, p['lat'], p['lon']), default=None)
    nearest_hospital = min(hospitals, key=lambda h: haversine(lat, lon, h['lat'], h['lon']), default=None)

    if nearest_police_station:
        print(f"Nearest police station: {nearest_police_station['name']} at {nearest_police_station['lat']}, {nearest_police_station['lon']}")
    else:
        print("No police station found nearby.")

    if nearest_hospital:
        print(f"Nearest hospital: {nearest_hospital['name']} at {nearest_hospital['lat']}, {nearest_hospital['lon']}")
    else:
        print("No hospital found nearby.")

    return nearest_police_station, nearest_hospital

# Example of how to call the function
accident_location = (19.070, 72.877)  # Replace with actual accident location
alert_nearest_services(accident_location)
