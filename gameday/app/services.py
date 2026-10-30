# Location helpers: how far a parking spot is from the venue, and how long it takes to walk.
# Everything here is plain maths on numbers we already store, so it makes NO calls to Google Maps or any
# routing service. That keeps it free and avoids rate limits (the risk noted in the task list).
import math
import json
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import URLError
import 

# returns if an address is vaild or not
CENSUS_URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"

# Great-circle distance in metres between two latitude/longitude points (the haversine formula).
def haversine_m(lat1, lng1, lat2, lng2) -> float:
    R, r = 6371e3, math.radians
    h = math.sin(r(lat2 - lat1) / 2) ** 2 + math.cos(r(lat1)) * math.cos(r(lat2)) * math.sin(r(lng2 - lng1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))

# Turns a street address into coordinates. THIS IS A MOCK: it checks the address looks like "123 Main St",
# then makes up repeatable coordinates within about 500 m of the anchor point (the venue).
# Replace the body with a real geocoder later and return None when the address can't be found.
class GeocoderUnavailable(Exception):
    pass

# Returns {"lat", "lng", "address"} for a real street address, or None if it can't be found.
# Raises GeocoderUnavailable if the Census service itself can't be reached.
def geocode(address: str) -> dict | None:
    params = urlencode({"address": address.strip(), "benchmark": "Public_AR_Current", "format": "json"})
    try:
        with urlopen(f"{CENSUS_URL}?{params}", timeout=10) as r:
            data = json.load(r)
    except (URLError, TimeoutError, ValueError) as e:
        print("Geocoder error:", repr(e))
        raise GeocoderUnavailable()
    matches = data.get("result", {}).get("addressMatches", [])
    if not matches:
        return None
    m = matches[0]
    return {"lat": m["coordinates"]["y"], "lng": m["coordinates"]["x"], "address": m["matchedAddress"]}

# Used by seed.py (and later by "create listing"): returns the spot's coordinates, its distance from the venue in metres,
# and walking minutes (assuming about 80 metres per minute), or None if the address can't be found.
def place(address: str, venue_lat: float, venue_lng: float):
    g = geocode(address)
    if not g:
        return None
    d = round(haversine_m(venue_lat, venue_lng, g["lat"], g["lng"]))
    return dict(lat=g["lat"], lng=g["lng"], dist=d, walk=max(1, round(d / 80)))