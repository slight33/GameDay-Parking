# This is Ai generated code so I will explain what it does in segments
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

# Creates any tables that don't exist yet. Safe to run on every startup as existing tables and their data are left alone
def init_db():
    Base.metadata.create_all(bind=engine)



