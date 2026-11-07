# Prints the Ticketmaster venue ids for each stadium, so they can be copied into app/venues.py.
import json, os
from urllib.parse import urlencode
from urllib.request import urlopen

KEY = os.environ["TICKETMASTER_API_KEY"]
NAMES = ["Lambeau Field", "Highmark Stadium", "Raymond James Stadium", "Hard Rock Stadium", "Empower Field at Mile High"]
VENUES = [
    {"tm_id": "KovZpa3awe", "name": "Lambeau Field"},
    {"tm_id": "KovZ917AV54", "name": "Highmark Stadium"},
    {"tm_id": "KovZpZAFnl1A", "name": "Raymond James Stadium"},
    {"tm_id": "KovZpZAEkvtA", "name": "Hard Rock Stadium"},
    {"tm_id": "KovZpa3Wne", "name": "Empower Field at Mile High"},
]
for name in NAMES:
    params = urlencode({"keyword": name, "countryCode": "US", "apikey": KEY})
    with urlopen(f"https://app.ticketmaster.com/discovery/v2/venues.json?{params}", timeout=10) as r:
        data = json.load(r)
    print(f"\n{name}")
    for v in data.get("_embedded", {}).get("venues", []):
        city = v.get("city", {}).get("name", "")
        state = v.get("state", {}).get("stateCode", "")
        upcoming = v.get("upcomingEvents", {}).get("_total", 0)
        print(f"  {v['id']}  {v['name']}  ({city}, {state})  upcoming events: {upcoming}")