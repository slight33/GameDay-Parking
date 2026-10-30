"""python seed.py — adds sample parking listings for the starting events, owned by a demo host (host1 / password1)."""
import bcrypt
from app.models import init_db, SessionLocal, User, Listing, Event
from app.services import place

init_db()
with SessionLocal() as s:
    # Only run once: if any listings exist, leave the database alone.
    if s.query(Listing).first():
        raise SystemExit("Listings already exist, so nothing was added.")

    # Reuse the demo host if it's already there, otherwise create it.
    host = s.query(User).filter(User.username == "host1").first()
    if not host:
        pw = bcrypt.hashpw(b"password1", bcrypt.gensalt()).decode()
        host = User(name="Harper Host", username="host1", email="host1@example.com", phone="555-0101",
                    pw_hash=pw, role="host", address="100 S Michigan Ave, Chicago, IL")
        s.add(host)
        s.flush()   # gives host an id before the listings use it

    # event id, address, price, start, end, overstay fee, security, stacked
    for ev, addr, price, st, en, ov, sec, stk in [
            ("v1", "410 E 18th St, Chicago, IL", 15, "09:00", "18:00", 0, "Gated driveway, camera on garage", True),
            ("v1", "77 W Roosevelt Rd, Chicago, IL", 25, "09:00", "18:00", 10, "Lit lot, attendant on site", False),
            ("v2", "1900 W Madison St, Chicago, IL", 30, "16:00", "23:00", 15, "Private driveway", True)]:
        e = s.get(Event, ev)
        p = place(addr, e.lat, e.lng)   # real geocode, then distance and walking time from the venue
        if not p:
            raise SystemExit(f"Couldn't find {addr}, so nothing was added.")
        s.add(Listing(host_id=host.id, event_id=ev, address=addr, price=price, start=st, end=en,
                      overstay=ov, security=sec, stacked=stk, **p))
    s.commit()
    print("Added sample listings.")
