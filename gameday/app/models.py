import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine, ForeignKey, String, Float, Integer, Boolean, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

import os
# e.g. postgresql+psycopg://postgres:YOURPASSWORD@localhost:5432/gameday  (falls back to SQLite if unset)
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///gameday.db")
engine = create_engine(
    DATABASE_URL, pool_pre_ping=True,
    **({"connect_args": {"check_same_thread": False}} if DATABASE_URL.startswith("sqlite") else {}),
)
SessionLocal = sessionmaker(engine, expire_on_commit=False)

def new_id(prefix: str) -> str:
    return prefix + uuid.uuid4().hex[:8]

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: new_id("u"))
    name: Mapped[str]
    username: Mapped[str] = mapped_column(String, unique=True, index=True)  # stored lowercase
    email: Mapped[str] = mapped_column(String, unique=True, index=True)     # stored lowercase
    phone: Mapped[str]
    pw_hash: Mapped[str]
    role: Mapped[str] = mapped_column(default="guest")                      # guest | host
    address: Mapped[str | None] = mapped_column(default=None)

class Event(Base):
    __tablename__ = "events"
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    venue: Mapped[str]
    date: Mapped[str]   # YYYY-MM-DD
    time: Mapped[str]   # HH:MM
    lat: Mapped[float]
    lng: Mapped[float]

class Listing(Base):
    __tablename__ = "listings"
    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: new_id("l"))
    host_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    address: Mapped[str]
    price: Mapped[float]
    start: Mapped[str]
    end: Mapped[str]
    overstay: Mapped[float] = mapped_column(default=0)
    security: Mapped[str] = mapped_column(default="")
    stacked: Mapped[bool] = mapped_column(default=False)
    photo_path: Mapped[str | None] = mapped_column(default=None)
    lat: Mapped[float]
    lng: Mapped[float]
    dist: Mapped[int]   # metres to venue
    walk: Mapped[int]   # minutes
    host: Mapped[User] = relationship()
    event: Mapped[Event] = relationship()

class Booking(Base):
    __tablename__ = "bookings"
    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: new_id("bk"))
    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.id"), index=True)
    guest_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[str]
    start: Mapped[str]
    end: Mapped[str]
    plate: Mapped[str]
    amount: Mapped[float]
    last4: Mapped[str]
    payment_ref: Mapped[str]
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    listing: Mapped[Listing] = relationship()
    guest: Mapped[User] = relationship()

SEED_EVENTS = [
    dict(id="v1", name="Bears vs Packers", venue="Soldier Field", date="2026-10-25", time="12:00", lat=41.8623, lng=-87.6167),
    dict(id="v2", name="Bulls vs Celtics", venue="United Center", date="2026-11-02", time="19:30", lat=41.8807, lng=-87.6742),
    dict(id="v3", name="Night Lights Concert", venue="Wrigley Field", date="2026-11-07", time="20:00", lat=41.9484, lng=-87.6553),
]

def init_db():
    Base.metadata.create_all(engine)
    with SessionLocal() as s:
        if not s.query(Event).first():
            s.add_all(Event(**e) for e in SEED_EVENTS)
            s.commit()
