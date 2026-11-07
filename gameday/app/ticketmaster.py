# Pulls upcoming events for the stadiums in venues.py from the Ticketmaster Discovery API
# and saves them in the events table. Ticketmaster's event id is used as our Event.id,
# so running the sync again updates events instead of adding duplicates.
import json, os, threading, time
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import URLError

from .models import Event
from .venues import VENUES

TM_URL = "https://app.ticketmaster.com/discovery/v2/events.json"
SYNC_EVERY = 12 * 60 * 60   # seconds between syncs (12 hours)

# Ticketmaster lists add-ons like parking passes as their own "events". Any event whose name
# contains one of these words is skipped. The sync prints what it skips, so this list can be adjusted.
SKIP_WORDS = ("parking", "tailgate", "suite", "club pass", "premium", "upgrade",
              "stadium tour", "season ticket", "voucher", "gift card")

_last_sync = 0.0              # when the last sync finished (0 means "never" since the server started)
_lock = threading.Lock()      # stops two requests from syncing at the same time

# Asks Ticketmaster for one venue's upcoming events, soonest first.
def _fetch(venue_id: str, key: str) -> list:
    params = urlencode({
        "venueId": venue_id,
        "apikey": key,
        "size": 200,
        "sort": "date,asc",
        "startDateTime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    with urlopen(f"{TM_URL}?{params}", timeout=15) as r:
        return json.load(r).get("_embedded", {}).get("events", [])

# Returns why an event should be skipped, or None if it should be saved.
def _skip_reason(ev: dict) -> str | None:
    name = ev.get("name", "").lower()
    if any(word in name for word in SKIP_WORDS):
        return "add-on"
    if not ev.get("dates", {}).get("start", {}).get("localTime"):
        return "time TBA"   # skipped for now, since the pages need a start time
    return None

# Fetches every venue's events and saves them. If one venue fails, its existing events are kept
# and the sync moves on to the next venue.
def sync_events(db) -> None:
    key = os.environ.get("TICKETMASTER_API_KEY")
    if not key:
        print("Ticketmaster sync skipped: TICKETMASTER_API_KEY isn't set.")
        return

    saved = skipped = 0
    for venue in VENUES:
        try:
            events = _fetch(venue["tm_id"], key)
        except (URLError, TimeoutError, ValueError) as e:
            print(f"Ticketmaster sync failed for {venue['name']}:", repr(e))
            continue

        for ev in events:
            loc = (ev.get("_embedded", {}).get("venues") or [{}])[0].get("location")
            reason = _skip_reason(ev) or (None if loc else "no location")
            if reason:
                skipped += 1
                print(f"  skipped ({reason}): {ev.get('name')}")
                continue

            # Find the event if it's already saved, otherwise create it.
            e = db.get(Event, ev["id"])
            if not e:
                e = Event(id=ev["id"])
                db.add(e)

            start = ev["dates"]["start"]
            e.name = ev["name"]
            e.venue = venue["name"]
            e.venue_id = venue["tm_id"]
            e.date = start["localDate"]                    # "2026-11-15"
            e.time = start["localTime"][:5]                # "19:30:00" -> "19:30"
            e.lat = float(loc["latitude"])
            e.lng = float(loc["longitude"])
            e.status = ev["dates"].get("status", {}).get("code", "onsale")
            e.timezone = ev["dates"].get("timezone", "America/Chicago")
            saved += 1

        time.sleep(0.25)   # stays under Ticketmaster's limit of 5 requests per second

    db.commit()
    print(f"Ticketmaster sync done: {saved} saved, {skipped} skipped.")

# Runs the sync only if the last one was more than SYNC_EVERY ago.
# Called at the start of GET /events, so events stay fresh without a scheduled job.
def maybe_sync(db) -> None:
    global _last_sync
    if time.time() - _last_sync < SYNC_EVERY:
        return
    if not _lock.acquire(blocking=False):
        return   # another request is already syncing
    try:
        sync_events(db)
        _last_sync = time.time()
    finally:
        _lock.release()