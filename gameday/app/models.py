# This is Ai generated code so we will explain what it does in segments
# What it does: It pulls in external tools needed for the script.
# uuid and datetime are standard Python libraries used later for generating IDs and managing timestamps.
# The sqlalchemy imports provide core database operations and modern ORM (Object-Relational Mapping) features to map Python classes directly to database tables.
import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine, ForeignKey, String, Float, Integer, Boolean, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

import os
# Read the database URL from the environment
# If it isn't set (running locally), fall back to a SQLite file called gameday.db.
# e.g. postgresql+psycopg://postgres:YOURPASSWORD@localhost:5432/gameday  (falls back to SQLite if unset)
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///gameday.db")
# Render give URLs starting with postgres:// or postgresql://, which make
# SQLAlchemy look for the old psycopg2 driver
for old in ("postgres://", "postgresql://"):
    if DATABASE_URL.startswith(old):
        DATABASE_URL = DATABASE_URL.replace(old, "postgresql+psycopg://", 1)
        break
# The engine manages the actual connections to the database.  
# pool_pre_ping checks a connection is still alive before using it 
engine = create_engine(
    DATABASE_URL, pool_pre_ping=True,
    # check_same_thread=False is for SQLite-only
    **({"connect_args": {"check_same_thread": False}} if DATABASE_URL.startswith("sqlite") else {}),
)

 # What it does: It configures a factory for creating database database sessions.
 # Every time the application needs to talk to the database (add a user, fetch data), it will use a session spawned by SessionLocal.
 # expire_on_commit=False ensures that after saveing changes to the database, the data remains accessible in Python without immediately needing a slow re-fetch from the database.
SessionLocal = sessionmaker(engine, expire_on_commit=False)

# Makes short readable IDs like "u3f9a1c2e".
# a prefix plus 8 random hex characters.
def new_id(prefix: str) -> str:
    return prefix + uuid.uuid4().hex[:8]

# Every table class inherits from Base, which is how SQLAlchemy knows about them.
class Base(DeclarativeBase): pass

#  What it does: It defines the structure of the users table inside the database.
# __tablename__: Tells the database to name the actual table "users".
# id: Sets up a unique primary key using the custom function from Segment 4 (default=lambda: new_id("u")).
# username & email: Configured to be unique (no duplicates allowed) and indexed (index=True) so searching for users by email or username is extremely fast.
# role: Defaults to "guest" if not specified.
# address: The Mapped[str | None] type hint explicitly allows this field to be left empty (None/Null) in the database.
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
    lat: Mapped[float | None] = mapped_column(default=None)
    lng: Mapped[float | None] = mapped_column(default=None)

# What it does: It defines the events table: one row per game or concert.
# lat and lng are the venue's coordinates; every parking spot is measured from them.
# date ("2026-11-15") and time ("19:30") are stored as text because that format sorts correctly as plain text.
class Event(Base):
    __tablename__ = "events"
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    venue: Mapped[str]
    date: Mapped[str]   # YYYY-MM-DD
    time: Mapped[str]   # HH:MM
    lat: Mapped[float]
    lng: Mapped[float]

# What it does: It defines the listings table: one row per parking spot a host offers for one event.
# host_id and event_id are foreign keys, so they must match a real row in users / events.
# dist (metres) and walk (minutes) are worked out ONCE when the listing is created (see services.py),
# so browsing is a quick read and never needs a map or routing service.
class Listing(Base):
    __tablename__ = "listings"
    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: new_id("l"))
    host_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    address: Mapped[str]
    price: Mapped[float]
    start: Mapped[str]                                  # first time the spot is available, HH:MM
    end: Mapped[str]                                    # last time the spot is available, HH:MM
    overstay: Mapped[float] = mapped_column(default=0)  # fee per 15 minutes late
    security: Mapped[str] = mapped_column(default="")   # e.g. "Gated driveway"
    stacked: Mapped[bool] = mapped_column(default=False)  # True if cars may be parked behind each other
    lat: Mapped[float]
    lng: Mapped[float]
    dist: Mapped[int]   # metres from the venue
    walk: Mapped[int]   # walking minutes from the venue

# The events that are added the first time the app starts on an empty events table.
SEED_EVENTS = [
    dict(id="v1", name="Bears vs Packers", venue="Soldier Field", date="2026-11-15", time="12:00", lat=41.8623, lng=-87.6167),
    dict(id="v2", name="Bulls vs Celtics", venue="United Center", date="2026-11-02", time="19:30", lat=41.8807, lng=-87.6742),
    dict(id="v3", name="Night Lights Concert", venue="Wrigley Field", date="2026-11-07", time="20:00", lat=41.9484, lng=-87.6553),
]

# Creates any tables that don't exist yet. Safe to run on every startup as existing tables and their data are left alone
# (so your existing users table is not touched; only the new events and listings tables get created).
# Then, if the events table is empty, it adds the starting events.
def init_db():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as s:
        if not s.query(Event).first():
            s.add_all(Event(**e) for e in SEED_EVENTS)
            s.commit()



