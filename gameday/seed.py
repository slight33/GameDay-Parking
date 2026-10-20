"""python seed.py  — recreates the prototype's demo data (host1/guest1, password1)."""
import bcrypt
from app.models import init_db, SessionLocal, User, Listing, Event
from app.services import place
init_db()
pw = bcrypt.hashpw(b"password1", bcrypt.gensalt()).decode()
with SessionLocal() as s:
    if s.query(User).first(): raise SystemExit("already seeded")
    h = User(id="u1", name="Harper Host", username="host1", email="host1@example.com", phone="555-0101", pw_hash=pw, role="host", address="100 S Michigan Ave")
    g = User(id="u2", name="Gus Guest", username="guest1", email="guest1@example.com", phone="555-0102", pw_hash=pw)
    s.add_all([h, g]); s.flush()
    for ev, addr, price, st, en, ov, sec, stk in [
        ("v1","410 E 18th St",15,"09:00","18:00",0,"Gated driveway, camera on garage",True),
        ("v1","77 W Roosevelt Rd",25,"09:00","18:00",10,"Lit lot, attendant on site",False),
        ("v2","1900 W Madison St",30,"16:00","23:00",15,"Private driveway",True)]:
        e = s.get(Event, ev)
        s.add(Listing(host_id="u1", event_id=ev, address=addr, price=price, start=st, end=en, overstay=ov, security=sec, stacked=stk, **place(addr, e.lat, e.lng)))
    s.commit()
print("seeded")
