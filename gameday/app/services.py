"""Swappable integrations: geocoding and payments. Replace the bodies, keep the signatures."""
import math, re, secrets
from dataclasses import dataclass

def haversine_m(lat1, lng1, lat2, lng2) -> float:
    R, r = 6371e3, math.radians
    h = math.sin(r(lat2 - lat1) / 2) ** 2 + math.cos(r(lat1)) * math.cos(r(lat2)) * math.sin(r(lng2 - lng1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))

def geocode(address: str, anchor: tuple[float, float]) -> tuple[float, float] | None:
    """MOCK, same rules as the prototype. Swap for Google Geocoding / Nominatim (return None on no match)."""
    a = address.strip()
    if not re.match(r"^\d+\s+[A-Za-z]", a) or len(a) < 9 or re.search(r"nowhere|invalid|asdf", a, re.I):
        return None
    h = 0
    for c in a.lower():
        h = (h * 31 + ord(c)) & 0xFFFFFFFF
    return anchor[0] + ((h % 1000) / 1000 - .5) * .010, anchor[1] + (((h >> 10) % 1000) / 1000 - .5) * .010

def place(address: str, venue_lat: float, venue_lng: float):
    g = geocode(address, (venue_lat, venue_lng))
    if not g:
        return None
    d = round(haversine_m(venue_lat, venue_lng, *g))
    return dict(lat=g[0], lng=g[1], dist=d, walk=max(1, round(d / 80)))

class PaymentError(Exception): pass

@dataclass
class Charge:
    ref: str
    last4: str

def charge_card(amount: float, card: str, exp: str, cvc: str) -> Charge:
    """MOCK Stripe. In production the browser tokenizes the card with Stripe.js and you only
    receive a PaymentMethod id, so raw card numbers never touch this server."""
    n = re.sub(r"\s", "", card)
    if not re.fullmatch(r"\d{16}", n) or not exp.strip() or not cvc.strip():
        raise PaymentError("Payment details look incomplete. Check the card and try again.")
    if n != "4242424242424242":
        raise PaymentError("Your card was declined. No booking was made. Try another card.")
    return Charge(ref="ch_" + secrets.token_hex(6), last4=n[-4:])
