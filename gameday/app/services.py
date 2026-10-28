# Location helpers: how far a parking spot is from the venue, and how long it takes to walk.
# Everything here is plain maths on numbers we already store, so it makes NO calls to Google Maps or any
# routing service. That keeps it free and avoids rate limits (the risk noted in the task list).
import math, re

# Great-circle distance in metres between two latitude/longitude points (the haversine formula).
def haversine_m(lat1, lng1, lat2, lng2) -> float:
    R, r = 6371e3, math.radians
    h = math.sin(r(lat2 - lat1) / 2) ** 2 + math.cos(r(lat1)) * math.cos(r(lat2)) * math.sin(r(lng2 - lng1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))

# Turns a street address into coordinates. THIS IS A MOCK: it checks the address looks like "123 Main St",
# then makes up repeatable coordinates within about 500 m of the anchor point (the venue).
# Replace the body with a real geocoder later and return None when the address can't be found.
def geocode(address: str, anchor: tuple[float, float]) -> tuple[float, float] | None:
    a = address.strip()
    if not re.match(r"^\d+\s+[A-Za-z]", a) or len(a) < 9 or re.search(r"nowhere|invalid|asdf", a, re.I):
        return None
    # Hash the text into a number so the same address always lands in the same place.
    h = 0
    for c in a.lower():
        h = (h * 31 + ord(c)) & 0xFFFFFFFF
    return anchor[0] + ((h % 1000) / 1000 - .5) * .010, anchor[1] + (((h >> 10) % 1000) / 1000 - .5) * .010

# Used by seed.py (and later by "create listing"): returns the spot's coordinates, its distance from the venue in metres,
# and walking minutes (assuming about 80 metres per minute), or None if the address is invalid.
def place(address: str, venue_lat: float, venue_lng: float):
    g = geocode(address, (venue_lat, venue_lng))
    if not g:
        return None
    d = round(haversine_m(venue_lat, venue_lng, *g))
    return dict(lat=g[0], lng=g[1], dist=d, walk=max(1, round(d / 80)))
