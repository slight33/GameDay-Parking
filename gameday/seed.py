"""python seed.py  — recreates the prototype's demo data (host1/guest1, password1)."""
import bcrypt
from app.models import init_db, SessionLocal, User, Listing, Event
# place() works out a spot's coordinates, its distance from the venue and its walking time.
from app.services import place
# Make sure the tables exist (and that the starting events have been added).
init_db()
# Hash the demo password once; both demo accounts share it. Only the hash is ever stored.
pw = bcrypt.hashpw(b"password1", bcrypt.gensalt()).decode()
# Everything below happens in one database session and is saved together at the end.
with SessionLocal() as s:
    # Stop if sample parking spots were already added, so running this twice doesn't create duplicates.
    if s.query(Listing).first(): raise SystemExit("already seeded")
    # Add the demo accounts only if they don't exist yet (the database may already hold real users).
    h = s.query(User).filter_by(username="host1").first()
    if not h:
        h = User(id="u1", name="Harper Host", username="host1", email="host1@example.com", phone="555-0101", pw_hash=pw, role="host", address="100 S Michigan Ave")
        s.add(h)
    if not s.query(User).filter_by(username="guest1").first():
        s.add(User(id="u2", name="Gus Guest", username="guest1", email="guest1@example.com", phone="555-0102", pw_hash=pw))
    s.flush()
    # Each tuple is: event id, street address, price, available from, available until,
    # overstay fee per 15 minutes, security notes, stacked parking (True/False).
    # 'v1' and 'v2' have spots; 'v3' (the concert) deliberately has none, so the empty message can be tested.
    for ev, addr, price, st, en, ov, sec, stk in [
        ("v1","410 E 18th St",15,"09:00","18:00",0,"Gated driveway, camera on garage",True),
        ("v1","77 W Roosevelt Rd",25,"09:00","18:00",10,"Lit lot, attendant on site",False),
        ("v2","1900 W Madison St",30,"16:00","23:00",15,"Private driveway",True)]:
        # Look up the event so we know the venue's coordinates.
        e = s.get(Event, ev)
        # place() returns lat, lng, dist and walk; the ** unpacks them into the matching listing columns.
        s.add(Listing(host_id=h.id, event_id=ev, address=addr, price=price, start=st, end=en, overstay=ov, security=sec, stacked=stk, **place(addr, e.lat, e.lng)))
    # Save everything.
    s.commit()
print("seeded")
