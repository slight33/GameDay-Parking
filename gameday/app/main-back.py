import os, re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Literal

import bcrypt, jwt
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.orm import Session

from .models import Booking, Event, Listing, SessionLocal, User, init_db
from .services import PaymentError, charge_card, place

SECRET = os.environ.get("JWT_SECRET", "dev-only-change-me")
UPLOADS = Path("uploads"); UPLOADS.mkdir(exist_ok=True)
HHMM = r"^([01]\d|2[0-3]):[0-5]\d$"

app = FastAPI(title="gamedayParking")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])  # tighten in prod
bearer = HTTPBearer(auto_error=False)

@app.on_event("startup")
def _startup(): init_db()

def get_db():
    with SessionLocal() as s:
        yield s
DB = Annotated[Session, Depends(get_db)]

# ---------- auth ----------
def make_token(uid: str) -> str:
    return jwt.encode({"sub": uid, "exp": datetime.now(timezone.utc) + timedelta(days=7)}, SECRET, "HS256")

def current_user(db: DB, cred: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> User:
    try:
        uid = jwt.decode(cred.credentials, SECRET, ["HS256"])["sub"]
    except Exception:
        raise HTTPException(401, "Sign in required.")
    u = db.get(User, uid)
    if not u: raise HTTPException(401, "Sign in required.")
    return u
Me = Annotated[User, Depends(current_user)]

def require_host(u: Me) -> User:
    if u.role != "host": raise HTTPException(403, "Become a host first.")
    return u
Host = Annotated[User, Depends(require_host)]

class SignupIn(BaseModel):
    name: str = Field(min_length=1); username: str = Field(min_length=1)
    email: EmailStr; phone: str = Field(min_length=1); password: str = Field(min_length=8)
class LoginIn(BaseModel):
    username: str; password: str

class UserOut(BaseModel):
    id: str; name: str; username: str; email: str; phone: str; role: str; address: str | None
    model_config = {"from_attributes": True}
class TokenOut(BaseModel):
    token: str; user: UserOut

@app.post("/auth/signup", response_model=TokenOut, status_code=201)
def signup(d: SignupIn, db: DB):
    if db.query(User).filter(User.username == d.username.strip().lower()).first():
        raise HTTPException(409, "That username is taken. Choose another.")
    if db.query(User).filter(User.email == d.email.lower()).first():
        raise HTTPException(409, "An account with that email already exists.")
    u = User(name=d.name.strip(), username=d.username.strip().lower(), email=d.email.lower(),
             phone=d.phone.strip(), pw_hash=bcrypt.hashpw(d.password.encode(), bcrypt.gensalt()).decode())
    db.add(u); db.commit()
    return TokenOut(token=make_token(u.id), user=u)

@app.post("/auth/login", response_model=TokenOut)
def login(d: LoginIn, db: DB):
    u = db.query(User).filter(User.username == d.username.strip().lower()).first()
    if not u or not bcrypt.checkpw(d.password.encode(), u.pw_hash.encode()):
        raise HTTPException(401, "Username or password doesn't match. Check both and try again.")
    return TokenOut(token=make_token(u.id), user=u)

@app.get("/me", response_model=UserOut)
def me(u: Me): return u

# ---------- events & listings ----------
class EventOut(BaseModel):
    id: str; name: str; venue: str; date: str; time: str; lat: float; lng: float; spots: int = 0
class ListingOut(BaseModel):
    id: str; event_id: str; address: str; price: float; start: str; end: str; overstay: float
    security: str; stacked: bool; lat: float; lng: float; dist: int; walk: int; photo_url: str | None = None

def listing_out(l: Listing) -> ListingOut:
    return ListingOut(**{k: getattr(l, k) for k in ListingOut.model_fields if k not in ("photo_url",)},
                      photo_url=f"/uploads/{l.photo_path}" if l.photo_path else None)

@app.get("/events", response_model=list[EventOut])
def events(db: DB):
    counts = {e.id: db.query(Listing).filter(Listing.event_id == e.id).count() for e in db.query(Event)}
    return [EventOut(**{k: getattr(e, k) for k in ("id","name","venue","date","time","lat","lng")}, spots=counts[e.id])
            for e in db.query(Event).order_by(Event.date)]

@app.get("/events/{event_id}/listings", response_model=list[ListingOut])
def event_listings(event_id: str, db: DB):
    if not db.get(Event, event_id): raise HTTPException(404, "Event not found.")
    return [listing_out(l) for l in db.query(Listing).filter(Listing.event_id == event_id).order_by(Listing.dist)]

class UpgradeIn(BaseModel):
    address: str
@app.post("/hosts/upgrade", response_model=UserOut)
def upgrade(d: UpgradeIn, u: Me, db: DB):
    if not place(d.address, 41.8623, -87.6167):  # any anchor, only validity matters here
        raise HTTPException(422, "We couldn't find that address. Check the street number and name, then enter it again.")
    u.address, u.role = d.address.strip(), "host"
    db.merge(u); db.commit()
    return u

class ListingIn(BaseModel):
    event_id: str; price: float = Field(gt=0)
    start: str = Field(pattern=HHMM); end: str = Field(pattern=HHMM)
    overstay: float = Field(0, ge=0); security: str = ""; stacked: bool = False
@app.post("/listings", response_model=ListingOut, status_code=201)
def create_listing(d: ListingIn, h: Host, db: DB):
    e = db.get(Event, d.event_id)
    if not e: raise HTTPException(404, "Event not found.")
    if d.start >= d.end: raise HTTPException(422, "End time must be after start time.")
    p = place(h.address, e.lat, e.lng)
    l = Listing(host_id=h.id, event_id=e.id, address=h.address, price=d.price, start=d.start, end=d.end,
                overstay=d.overstay, security=d.security, stacked=d.stacked, **p)
    db.add(l); db.commit()
    return listing_out(l)

@app.post("/listings/{listing_id}/photo", response_model=ListingOut)
async def upload_photo(listing_id: str, h: Host, db: DB, file: UploadFile = File(...)):
    l = db.get(Listing, listing_id)
    if not l or l.host_id != h.id: raise HTTPException(404, "Listing not found.")
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"): raise HTTPException(415, "Upload a JPEG, PNG or WebP image.")
    data = await file.read()
    if len(data) > 2_000_000: raise HTTPException(413, "Image must be under 2 MB.")
    name = f"{l.id}.{file.content_type.split('/')[1]}"
    (UPLOADS / name).write_bytes(data); l.photo_path = name; db.commit()
    return listing_out(l)

@app.get("/uploads/{name}")
def get_upload(name: str):
    from fastapi.responses import FileResponse
    p = UPLOADS / Path(name).name
    if not p.exists(): raise HTTPException(404)
    return FileResponse(p)

# ---------- bookings ----------
class BookingIn(BaseModel):
    listing_id: str
    start: str = Field(pattern=HHMM); end: str = Field(pattern=HHMM)
    plate: str = Field(min_length=1)
    card: str; exp: str; cvc: str   # prod: replace with Stripe payment_method_id

class BookingOut(BaseModel):
    id: str; listing: ListingOut; event_name: str; venue: str; date: str; start: str; end: str
    plate: str; amount: float; last4: str; host_name: str; host_phone: str; host_email: str

def booking_out(b: Booking) -> BookingOut:
    l = b.listing
    return BookingOut(id=b.id, listing=listing_out(l), event_name=l.event.name, venue=l.event.venue, date=b.date,
                      start=b.start, end=b.end, plate=b.plate, amount=b.amount, last4=b.last4,
                      host_name=l.host.name, host_phone=l.host.phone, host_email=l.host.email)

def is_free(db: Session, listing_id: str, date: str, start: str, end: str) -> bool:
    return not db.query(Booking).filter(Booking.listing_id == listing_id, Booking.date == date,
                                        Booking.start < end, Booking.end > start).first()

@app.post("/bookings", response_model=BookingOut, status_code=201)
def create_booking(d: BookingIn, u: Me, db: DB):
    l = db.get(Listing, d.listing_id)
    if not l: raise HTTPException(404, "Listing not found.")
    if d.start < l.start or d.end > l.end or d.start >= d.end:
        raise HTTPException(422, "Choose a window within the listing's available hours.")
    if not is_free(db, l.id, l.event.date, d.start, d.end):
        raise HTTPException(409, "This spot is already reserved for part of that window. Pick another time.")
    try:
        charge = charge_card(l.price, d.card, d.exp, d.cvc)
    except PaymentError as e:
        raise HTTPException(402, str(e))
    # re-check after payment (prototype does the same). On Postgres, back this with an exclusion constraint.
    if not is_free(db, l.id, l.event.date, d.start, d.end):
        raise HTTPException(409, "Someone just booked that window. Pick another time.")  # TODO: refund charge.ref
    b = Booking(listing_id=l.id, guest_id=u.id, date=l.event.date, start=d.start, end=d.end,
                plate=d.plate.strip().upper(), amount=l.price, last4=charge.last4, payment_ref=charge.ref)
    db.add(b); db.commit()
    return booking_out(b)

@app.get("/bookings/{booking_id}", response_model=BookingOut)
def get_booking(booking_id: str, u: Me, db: DB):
    b = db.get(Booking, booking_id)
    if not b or (b.guest_id != u.id and b.listing.host_id != u.id): raise HTTPException(404, "Booking not found.")
    return booking_out(b)

# ---------- dashboard ----------
class Reservation(BaseModel):
    start: str; end: str; guest_name: str; guest_phone: str; guest_email: str; plate: str
class HostListing(BaseModel):
    listing: ListingOut; event_name: str; reservations: list[Reservation]
class Dashboard(BaseModel):
    upcoming: list[BookingOut]; past: list[BookingOut]; listings: list[HostListing] | None = None

@app.get("/me/dashboard", response_model=Dashboard)
def dashboard(u: Me, db: DB):
    now = datetime.now()
    mine = db.query(Booking).filter(Booking.guest_id == u.id).order_by(Booking.date, Booking.start).all()
    up = [b for b in mine if datetime.fromisoformat(f"{b.date}T{b.end}") > now]
    past = [b for b in mine if b not in up]
    hosted = None
    if u.role == "host":
        hosted = [HostListing(listing=listing_out(l), event_name=l.event.name, reservations=[
            Reservation(start=b.start, end=b.end, guest_name=b.guest.name, guest_phone=b.guest.phone,
                        guest_email=b.guest.email, plate=b.plate)
            for b in db.query(Booking).filter(Booking.listing_id == l.id)])
            for l in db.query(Listing).filter(Listing.host_id == u.id)]
    return Dashboard(upcoming=[booking_out(b) for b in up], past=[booking_out(b) for b in past], listings=hosted)
