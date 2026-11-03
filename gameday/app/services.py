# Location helpers: how far a parking spot is from the venue, and how long it takes to walk.
# Everything here is plain maths on numbers we already store, so it makes NO calls to Google Maps or any
# routing service. That keeps it free and avoids rate limits (the risk noted in the task list).
import math
import json
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import URLError
import os
import threading
import stripe
from .models import Booking

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


# ================= Booking helpers (availability check and Stripe payments) =================
# Stripe is the payment company. Your SECRET key (starts with sk_test_ while testing) lets this server take payments.
# It is read from an environment variable so it is never written into the code. Never share it or put it in a web page.
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")

# Two kinds of payment problem, so the website can tell the guest what actually happened (same idea as GeocoderUnavailable above).
class PaymentDeclined(Exception):
    pass          # the card was refused or the payment didn't go through; the message is safe to show the guest

class PaymentUnavailable(Exception):
    pass          # Stripe couldn't be reached or is having an outage; the guest was NOT charged

# --- A lock for each parking spot ---
# Problem: two guests press "Pay" for the same spot at the same moment. Both checks say "free", and both get charged.
# Fix: before checking and paying, a request takes that spot's lock. Only one request can hold it at a time, so the second
# guest waits a moment, then sees the spot is taken and is told so BEFORE being charged.
# Limit: a lock like this only works inside ONE running copy of the server. If you later run several copies, move this
# protection into the database (for example a PostgreSQL "exclusion constraint").
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()   # protects the dictionary above while we add a new lock to it

def lock_for(listing_id: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(listing_id, threading.Lock())

# Task bchk: is this spot free for the whole window the guest asked for?
# Two time windows overlap when each one starts before the other one ends.
# Example: an existing booking 10:00-12:00 clashes with a request for 11:00-13:00, but NOT with 12:00-14:00 (back to back is fine).
# "HH:MM" text compares correctly as plain text ("09:30" < "10:00"), so no date maths is needed.
def is_available(db, listing_id: str, start: str, end: str) -> bool:
    clash = db.query(Booking).filter(
        Booking.listing_id == listing_id, Booking.start < end, Booking.end > start).first()
    return clash is None

# Task bpay: charge the card through Stripe and return Stripe's payment id.
# payment_method_id is a one-time token Stripe's own form made in the browser. The card number never touches our server.
# request_id is used as Stripe's "idempotency key". If the same request is sent twice (a double click, or a retry after a bad
# connection) Stripe returns the first result instead of charging again, which answers the "charged more than once" risk.
# metadata is notes stored on the payment. The webhook in main.py uses them to rebuild a booking if the server missed one.
# Raises PaymentDeclined if the card fails, or PaymentUnavailable if Stripe can't be reached. Nothing is saved here, so a failed
# charge never touches the database.
def charge(amount_cents: int, payment_method_id: str, request_id: str, metadata: dict) -> str:
    if not stripe.api_key:
        print("Stripe error: STRIPE_SECRET_KEY is not set")
        raise PaymentUnavailable()
    try:
        pi = stripe.PaymentIntent.create(
            amount=amount_cents, currency="usd", payment_method=payment_method_id,
            confirm=True,                                                         # try to take the payment right now
            automatic_payment_methods={"enabled": True, "allow_redirects": "never"},  # card only, no redirect pages
            metadata=metadata, idempotency_key=request_id)
    except stripe.CardError as e:          # declined, expired, wrong CVC, not enough money...
        raise PaymentDeclined(e.user_message or "Your card was declined. Try another card.")
    except stripe.StripeError as e:        # network problem, Stripe outage, bad key, too many requests
        print("Stripe error:", repr(e))
        raise PaymentUnavailable()
    if pi.status != "succeeded":           # e.g. the bank wants extra approval, which this simple form can't do
        raise PaymentDeclined("Your payment couldn't be completed. Try another card.")
    return pi.id

# Gives the guest their money back. Used when the payment worked but we couldn't save the booking.
# If even the refund fails we print it, so the payment can be refunded by hand in the Stripe dashboard.
def refund(payment_intent_id: str) -> None:
    try:
        stripe.Refund.create(payment_intent=payment_intent_id)
    except stripe.StripeError as e:
        print("REFUND FAILED, refund by hand in Stripe:", payment_intent_id, repr(e))
