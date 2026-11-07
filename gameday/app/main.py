# This Code Was Ai Generated
 # Standard Utilities: Sets up environment variables (os), text pattern matching (re), date formatting (datetime), file path management (Path), and advanced type hints (typing).
 # Security & Authentication: Imports bcrypt for password hashing and jwt for generating secure JSON Web Tokens.
 # FastAPI Ecosystem: Pulls in components to create the web app, manage cross-origin restrictions (CORS), and protect routes.
 # Data Validation & ORM: Imports pydantic to enforce data types and sqlalchemy to manage database sessions.
import os, re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Literal

import bcrypt, jwt
from fastapi import Depends, FastAPI, File, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import SessionLocal, User, Event, Listing, Booking, init_db
from fastapi.staticfiles import StaticFiles
from zoneinfo import ZoneInfo

CHICAGO = ZoneInfo("America/Chicago")

# Combines an event's date ("2026-11-15") with a time ("09:00") into a full Chicago date-time.
def at(date_str: str, hhmm: str) -> datetime:
    return datetime.fromisoformat(f"{date_str} {hhmm}").replace(tzinfo=CHICAGO)
# Environment Constants: Sets a secret key for security signatures.
# CORS Settings: Enables broad Cross-Origin Resource Sharing (*) so external frontend clients can communicate with the backend.
# Auth Protocol: Instantiates HTTPBearer to intercept incoming Authorization: Bearer <token> request headers.

SECRET = os.environ.get("JWT_SECRET", "dev-only-change-me")
STATIC = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="gamedayParking")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])  # tighten in prod
app.mount("/static", StaticFiles(directory=STATIC), name="static")
bearer = HTTPBearer(auto_error=False)
# App Startup: Triggers init_db() to automatically spin up or verify your database tables when the web server first boots.
# Session Lifecycle: get_db() yields a temporary database connection block. Using Python's context manager (with), it guarantees 
# the session automatically closes after a request finishes.

@app.on_event("startup")
def _startup(): 
    init_db()

def get_db():
    with SessionLocal() as s:
        yield s


DB = Annotated[Session, Depends(get_db)]
# make_token: Packages a user's unique ID (uid) into a secure JSON Web Token that expires exactly 7 days after issue.
# ---------- auth ----------
def make_token(uid: str) -> str:
    return jwt.encode({"sub": uid, "exp": datetime.now(timezone.utc) + timedelta(days=7)}, SECRET, "HS256")

# current_user: Intercepts incoming bearer credentials, decodes the JWT using the SECRET key, and grabs the user's ID. If the token is fake, expired,
# or doesn't map to a real database user, it immediately stops execution and drops a 401 Unauthorized error.
def current_user(db: DB, cred: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> User:
    try:
        uid = jwt.decode(cred.credentials, SECRET, ["HS256"])["sub"]
    except Exception:
        raise HTTPException(401, "Sign in required.")
    u = db.get(User, uid)
    if not u: raise HTTPException(401, "Sign in required.")
    return u
# Me Shortcut: Serves as a reusable dependency injection tag. Any API route featuring u: Me will automatically enforce authentication before running.
Me = Annotated[User, Depends(current_user)]

#  SignupIn: Validates the payload when a new user registers. It requires name, username, phone, and a password at least 8 characters long, plus a valid formatted email via Pydantic's EmailStr.
class SignupIn(BaseModel):
    name: str = Field(min_length=1); 
    username: str = Field(min_length=1)
    email: EmailStr; 
    phone: str = Field(min_length=1); 
    password: str = Field(min_length=8)

# LoginIn: Simple schema expecting a username and password for logging in.
class LoginIn(BaseModel):
    username: str; 
    password: str

# UserOut: Defines what user data is returned to the client (hiding sensitive fields like password hashes).
class UserOut(BaseModel):
    id: str; 
    name: str; 
    username: str; 
    email: str; 
    phone: str; 
    role: str; 
    address: str | None
    # allows it to read data straight from a SQLAlchemy database model instance:
    model_config = {"from_attributes": True}

# TokenOut: Wraps an authentication token string and the associated UserOut object together in the response.
class TokenOut(BaseModel):
    token: str; 
    user: UserOut



# Queries the database to make sure neither the username nor the email already exists. If found, it raises a 409 Conflict HTTP error.
# Strips whitespace and lowercases the username and email so logins are case-insensitive and clean.
@app.post("/auth/signup", response_model=TokenOut, status_code=201)
def signup(d: SignupIn, db: DB):
    if db.query(User).filter(User.username == d.username.strip().lower()).first():
        raise HTTPException(409, "That username is taken. Choose another.")
    if db.query(User).filter(User.email == d.email.lower()).first():
        raise HTTPException(409, "An account with that email already exists.")
    #Uses bcrypt with a generated salt to safely hash the plaintext password before saving it.
    u = User(name=d.name.strip(), username=d.username.strip().lower(), email=d.email.lower(),
             phone=d.phone.strip(), pw_hash=bcrypt.hashpw(d.password.encode(), bcrypt.gensalt()).decode())
    # Adds the new User object to the session and commits it
    db.add(u); 
    db.commit()
    return TokenOut(token=make_token(u.id), user=u)

# What it does: Authenticates existing users at POST /auth/login.
# Key details:
	# Looks up the user by their lowercase/trimmed username.
	# Verifies the submitted password against the stored bcrypt hash using bcrypt.checkpw().
	# If the user doesn't exist or the password fails, it raises an HTTP 401 Unauthorized error.
	# If valid, it generates and returns a new auth token and the user's data.
@app.post("/auth/login", response_model=TokenOut)
def login(d: LoginIn, db: DB):
    # Finds the user in the database by matching the lowercased, stripped username.
    u = db.query(User).filter(User.username == d.username.strip().lower()).first()
    # Checks if the user exists and verifies the incoming password against the stored bcrypt hash.
    if not u or not bcrypt.checkpw(d.password.encode(), u.pw_hash.encode()):
        #If the username or password fails to match, it throws a 401 Unauthorized error with a generic message.
        raise HTTPException(401, "Username or password doesn't match. Check both and try again.")
    # Token Issuance: If valid, it returns a new auth token and user profile via TokenOut.
    return TokenOut(token=make_token(u.id), user=u)

#Fetches the currently authenticated user's profile at GET /me.
@app.get("/me", response_model=UserOut)
def me(u: Me): 
    return u


# ---------- events and parking spots (public: no login needed) ----------
# EventOut: What the API sends for one event. spots is how many parking spots hosts have listed for it.
class EventOut(BaseModel):
    id: str; name: str; venue: str; date: str; time: str; lat: float; lng: float
    spots: int = 0

# ListingOut: What the API sends for one parking spot. dist is in metres and walk in minutes, both measured from the venue.
class ListingOut(BaseModel):
    id: str; address: str; price: float; start_at: datetime; end_at: datetime; overstay: float
    security: str; stacked: bool; lat: float; lng: float; dist: int; walk: int
    model_config = {"from_attributes": True}

# EventSpots: One event together with its spots, so the browse page needs only ONE request.
class EventSpots(BaseModel):
    event: EventOut
    listings: list[ListingOut]

# GET /events: upcoming events, soonest first, each with its spot count.
# cutoff is yesterday (in UTC) so an event happening tonight isn't dropped early because of time zones;
# the home page hides anything already past in the visitor's own time zone.
# Cache-Control lets the browser reuse the answer for 30 seconds, which cuts repeat requests to the database.
@app.get("/events", response_model=list[EventOut])
def events(db: DB, response: Response):
    response.headers["Cache-Control"] = "public, max-age=30"
    cutoff = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    # One grouped query counts the spots for every event at once (instead of one query per event).
    counts = dict(db.query(Listing.event_id, func.count(Listing.id)).group_by(Listing.event_id).all())
    rows = db.query(Event).filter(Event.date >= cutoff).order_by(Event.date, Event.time).all()
    return [EventOut(id=e.id, name=e.name, venue=e.venue, date=e.date, time=e.time,
                     lat=e.lat, lng=e.lng, spots=counts.get(e.id, 0)) for e in rows]

# GET /events/{event_id}/listings: the parking spots for one event, closest to the venue first.
# Distances and walking times were stored when each listing was created, so this is just a sorted read.
# Returns 404 if the event id doesn't exist. An event with no spots returns an empty list (the page shows the empty message).
@app.get("/events/{event_id}/listings", response_model=EventSpots)
def event_listings(event_id: str, db: DB, response: Response):
    e = db.get(Event, event_id)
    if not e:
        raise HTTPException(404, "Event not found.")
    response.headers["Cache-Control"] = "public, max-age=15"
    spots = db.query(Listing).filter(Listing.event_id == e.id).order_by(Listing.dist).all()
    return EventSpots(
        event=EventOut(id=e.id, name=e.name, venue=e.venue, date=e.date, time=e.time,
                       lat=e.lat, lng=e.lng, spots=len(spots)),
        listings=[ListingOut.model_validate(l) for l in spots])


# ---------- host upgrade ----------
from .services import geocode, GeocoderUnavailable

# AddressIn: the address fields the form sends. State must be 2 letters, ZIP must be 5 digits.
class AddressIn(BaseModel):
    street: str = Field(min_length=1)
    city: str = Field(min_length=1)
    state: str = Field(min_length=2, max_length=2)
    zip_code: str = Field(pattern=r"^\d{5}$")

# AddressCheckOut: whether the address was found, plus the cleaned-up address and coordinates if it was.
class AddressCheckOut(BaseModel):
    valid: bool
    matched_address: str | None = None
    lat: float | None = None
    lng: float | None = None

# Joins the form fields into the one-line format the Census Geocoder expects.
def one_line(d: AddressIn) -> str:
    return f"{d.street.strip()}, {d.city.strip()}, {d.state.strip().upper()} {d.zip_code.strip()}"

# Joins the form fields into one line and asks the Census Geocoder (in services.py) whether it's a real address.
@app.post("/host/validate-address", response_model=AddressCheckOut)
def validate_address(d: AddressIn):
    try:
        g = geocode(one_line(d))
    except GeocoderUnavailable:
        raise HTTPException(502, "Couldn't reach the address checker. Try again in a moment.")
    if not g:
        return AddressCheckOut(valid=False)
    return AddressCheckOut(valid=True, matched_address=g["address"], lat=g["lat"], lng=g["lng"])

# POST /host/upgrade: turns a logged-in guest into a host and saves their address and coordinates.
# The address is checked again here instead of trusting coordinates sent from the browser.
@app.post("/host/upgrade", response_model=UserOut)
def upgrade_to_host(d: AddressIn, u: Me, db: DB):
    if u.role != "guest":
        raise HTTPException(409, "This account is already a host.")
    try:
        g = geocode(one_line(d))
    except GeocoderUnavailable:
        raise HTTPException(502, "Couldn't reach the address checker. Try again in a moment.")
    if not g:
        raise HTTPException(422, "That address couldn't be found. Check it and try again.")
    u.address, u.lat, u.lng, u.role = g["address"], g["lat"], g["lng"], "host"
    db.commit()
    return u


# ---------- booking ----------
# The booking feature: a guest picks a parking spot, chooses their hours, enters a licence plate, pays by card (Stripe test mode)
# and gets a confirmation. POST /bookings does the work in the order of the task list: bchk (is it free?) -> bpay (charge) -> bsave (save).
import os
from fastapi import Request
from starlette.concurrency import run_in_threadpool
from .services import lock_for, is_available, charge, refund, PaymentDeclined, PaymentUnavailable

# Stripe's "webhook secret" proves a webhook message really came from Stripe. Set it as an environment variable.
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

# ListingDetail: one parking spot together with its event, so the booking page needs only ONE request.
class ListingDetail(BaseModel):
    event: EventOut
    listing: ListingOut

# GET /listings/{listing_id}: the details shown at the top of the booking page. Public, like the browse routes.
@app.get("/listings/{listing_id}", response_model=ListingDetail)
def listing_detail(listing_id: str, db: DB):
    l = db.get(Listing, listing_id)
    if not l:
        raise HTTPException(404, "That parking spot couldn't be found.")
    e = db.get(Event, l.event_id)
    return ListingDetail(
        event=EventOut(id=e.id, name=e.name, venue=e.venue, date=e.date, time=e.time, lat=e.lat, lng=e.lng),
        listing=ListingOut.model_validate(l))

# GET /booking/config: hands the browser Stripe's PUBLISHABLE key (starts with pk_test_). Unlike the secret key it is safe to expose.
@app.get("/booking/config")
def booking_config():
    return {"publishable_key": os.environ.get("STRIPE_PUBLISHABLE_KEY", "")}

# BookingIn: what the booking form sends. start and end must look like "HH:MM" (24-hour clock).
# payment_method_id comes from Stripe's card form. request_id is a random code the browser makes for each checkout attempt.
HHMM = r"^([01]\d|2[0-3]):[0-5]\d$"
class BookingIn(BaseModel):
    listing_id: str
    start: str = Field(pattern=HHMM)
    end: str = Field(pattern=HHMM)
    plate: str = Field(min_length=1, max_length=12)
    payment_method_id: str = Field(min_length=1)
    request_id: str = Field(min_length=8, max_length=64)

# BookingOut: the confirmed booking, with everything the confirmation screen shows. amount is in dollars here.
class BookingOut(BaseModel):
    id: str; event: str; venue: str; address: str; date: str
    start: str; end: str; plate: str; amount: float

# Builds a BookingOut by looking up the spot and event that a saved booking belongs to.
def booking_out(b: Booking, db: Session) -> BookingOut:
    l = db.get(Listing, b.listing_id)
    e = db.get(Event, l.event_id)
    return BookingOut(id=b.id, event=e.name, venue=e.venue, address=l.address, date=e.date,
                      start=b.start_at.astimezone(CHICAGO).strftime("%H:%M"),
                      end=b.end_at.astimezone(CHICAGO).strftime("%H:%M"),
                      plate=b.plate, amount=b.amount / 100)

# POST /bookings: book and pay for a spot. The guest must be signed in (u: Me).
@app.post("/bookings", response_model=BookingOut, status_code=201)
def create_booking(d: BookingIn, u: Me, db: DB):
    l = db.get(Listing, d.listing_id)
    if not l:
        raise HTTPException(404, "That parking spot couldn't be found.")
    e = db.get(Event, l.event_id)

    # Basic checks before any money is involved. (All errors from here to the charge mean "you were NOT charged".)
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")   # same cushion as GET /events
    if e.date < yesterday:
        raise HTTPException(422, "This event has already happened.")

    # The form sends "HH:MM" times. Combine them with the event's date to get full date-times.
    start_at = at(e.date, d.start)
    end_at = at(e.date, d.end)
    if end_at <= start_at:
        end_at += timedelta(days=1)   # the booking runs past midnight
    # The booking has to fit inside the host's available window.
    if start_at < l.start_at or end_at > l.end_at:
        opens = l.start_at.astimezone(CHICAGO).strftime("%H:%M")
        closes = l.end_at.astimezone(CHICAGO).strftime("%H:%M")
        raise HTTPException(422, f"Choose a time between {opens} and {closes}.")

    plate = re.sub(r"[^A-Z0-9 -]", "", d.plate.upper()).strip()   # keep letters, numbers, spaces and dashes only
    if not plate:
        raise HTTPException(422, "Enter your licence plate.")

    # Take this spot's lock so two guests can't check out for the same spot at the same time (see services.py).
    with lock_for(l.id):
        # Double-click protection: if this exact checkout attempt was already completed, just return that booking.
        done = db.query(Booking).filter(Booking.request_id == d.request_id).first()
        if done:
            if done.guest_id != u.id:
                raise HTTPException(409, "That checkout belongs to another account.")
            return booking_out(done, db)

        # bchk: is the spot free for the whole window? We ask BEFORE charging anyone.
        if not is_available(db, l.id, start_at, end_at):
            raise HTTPException(409, "Sorry, that spot is already booked for part of that time. Pick another time or spot. You have not been charged.")

        # bpay: charge the card. If it fails we stop here and the database is never touched.
        amount = round(l.price * 100)    # dollars to cents
        notes = dict(listing_id=l.id, guest_id=u.id, start=d.start, end=d.end, plate=plate, request_id=d.request_id)
        try:
            payment_id = charge(amount, d.payment_method_id, d.request_id, notes)
        except PaymentDeclined as ex:
            raise HTTPException(402, str(ex))
        except PaymentUnavailable:
            raise HTTPException(503, "Our payment system is having trouble right now. You have not been charged. Please try again in a few minutes.")

        # bsave: the money is taken, so save the booking. Once saved, the spot counts as taken for those hours
        # because is_available() looks at this table.
        try:
            b = Booking(listing_id=l.id, guest_id=u.id, plate=plate, start_at=start_at, end_at=end_at,
                        amount=amount, payment_intent_id=payment_id, request_id=d.request_id)
            db.add(b)
            db.commit()
        except Exception as ex:
            # Paid but not saved would be the worst outcome, so undo the payment and say so.
            print("Booking save failed:", repr(ex))
            db.rollback()
            refund(payment_id)
            raise HTTPException(500, "We couldn't save your booking, so your payment is being refunded. Please try again.")
    return booking_out(b, db)

# GET /bookings/{booking_id}: shows one booking on the confirmation screen. Only the guest who made it can see it.
@app.get("/bookings/{booking_id}", response_model=BookingOut)
def get_booking(booking_id: str, u: Me, db: DB):
    b = db.get(Booking, booking_id)
    if not b or b.guest_id != u.id:
        raise HTTPException(404, "Booking not found.")
    return booking_out(b, db)

# ---------- Stripe webhook (safety net) ----------
# A webhook is Stripe calling OUR server to say "this payment succeeded". We normally save the booking right away in
# POST /bookings, but a crash or a lost connection at the wrong moment could leave a paid guest with no booking.
# This catches that: when Stripe reports a successful payment we don't have a booking for, we create it (or refund it if
# the spot has since been taken). If Stripe can't reach us it retries for a few days, so a short outage is covered.
# To use it, add https://YOUR-SITE/stripe/webhook in the Stripe dashboard (event: payment_intent.succeeded)
# and copy its signing secret into STRIPE_WEBHOOK_SECRET.
def recover_booking(pi: dict) -> None:
    notes = pi.get("metadata") or {}
    if not notes.get("listing_id"):
        return                                           # not a payment made by our booking form
    with SessionLocal() as db:
        with lock_for(notes["listing_id"]):              # wait if a normal checkout is still saving
            if db.query(Booking).filter(Booking.payment_intent_id == pi["id"]).first():
                return                                   # already saved, nothing to fix
            if is_available(db, notes["listing_id"], notes["start"], notes["end"]):
                db.add(Booking(listing_id=notes["listing_id"], guest_id=notes["guest_id"], plate=notes["plate"],
                               start=notes["start"], end=notes["end"], amount=pi["amount"],
                               payment_intent_id=pi["id"], request_id=notes["request_id"]))
                db.commit()
            else:
                refund(pi["id"])                         # spot was taken meanwhile, so give the money back

@app.post("/stripe/webhook", include_in_schema=False)
async def stripe_webhook(request: Request):
    import stripe
    payload = await request.body()                       # the exact bytes Stripe sent (needed to check the signature)
    try:
        event = stripe.Webhook.construct_event(payload, request.headers.get("stripe-signature", ""), WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(400, "Bad webhook signature.")   # not really from Stripe, so ignore it
    if event["type"] == "payment_intent.succeeded":
        await run_in_threadpool(recover_booking, event["data"]["object"])
    return {"received": True}


# ---------- pages ----------
#Serves frontend HTML files for the root, login, and registration pages.
@app.get("/", include_in_schema=False)
def home():
    return FileResponse(STATIC / "index.html")
@app.get("/login", include_in_schema=False)
def login_page():
    return FileResponse(STATIC / "login.html")

@app.get("/register", include_in_schema=False)
def register_page():
    return FileResponse(STATIC / "register.html")

@app.get("/host_upgrade", include_in_schema=False)
def host_upgrade_page():
    return FileResponse(STATIC / "host.html")
